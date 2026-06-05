import asyncio
import aiomqtt

from src.config import settings
from src.services import influx_service, redis_service

# Fila compartilhada com o endpoint SSE (Tópico 5)
sse_queue: asyncio.Queue = asyncio.Queue()

_task: asyncio.Task | None = None


async def _handle_message(topic: str, payload: str) -> None:
    partes = topic.split("/")
    if len(partes) != 3:
        return

    _, sala_id, tipo = partes

    if tipo == "ocupacao":
        valor = int(payload) if payload.isdigit() else (1 if payload.lower() == "true" else 0)
        ocupada = valor == 1

        influx_service.write_movement(sala_id, valor)

        estado_atual = await redis_service.get_room_state(sala_id)
        luminosidade = estado_atual["luminosidade"] if estado_atual else True
        await redis_service.set_room_state(sala_id, ocupada=ocupada, luminosidade=luminosidade)

        if ocupada:
            alerta_key = f"alerta_enviado:{sala_id}"
            r = redis_service.get_redis()
            if await r.get(alerta_key):
                await r.delete(alerta_key)
                from src.services import telegram_service
                await telegram_service.send_movement_alert(sala_id)

        await sse_queue.put({"sala_id": sala_id, "ocupada": ocupada, "tipo": "ocupacao"})
        print(f"[MQTT] sala/{sala_id}/ocupacao → {ocupada}")

    elif tipo == "luminosidade":
        valor = int(payload) if payload.isdigit() else (1 if payload.lower() == "true" else 0)
        acesa = valor == 1

        influx_service.write_luminosity(sala_id, valor)

        estado_atual = await redis_service.get_room_state(sala_id)
        ocupada = estado_atual["ocupada"] if estado_atual else False
        era_acesa = estado_atual["luminosidade"] if estado_atual else False

        luz_acendeu = acesa and not era_acesa
        luz_apagou = not acesa and era_acesa
        await redis_service.set_room_state(sala_id, ocupada=ocupada, luminosidade=acesa, reset_timer=luz_acendeu)

        if luz_acendeu or luz_apagou:
            await redis_service.get_redis().delete(f"alerta_enviado:{sala_id}")

        await sse_queue.put({"sala_id": sala_id, "luminosidade": acesa, "tipo": "luminosidade"})
        print(f"[MQTT] sala/{sala_id}/luminosidade → {acesa}")


async def publish(topic: str, payload: str) -> None:
    async with aiomqtt.Client(
        hostname=settings.mqtt_broker,
        port=settings.mqtt_port,
        username=settings.mqtt_user,
        password=settings.mqtt_pass,
    ) as client:
        await client.publish(topic, payload)


async def _run() -> None:
    print("[MQTT] Conectando ao broker...")
    async with aiomqtt.Client(
        hostname=settings.mqtt_broker,
        port=settings.mqtt_port,
        username=settings.mqtt_user,
        password=settings.mqtt_pass,
    ) as client:
        await client.subscribe("sala/+/ocupacao")
        await client.subscribe("sala/+/luminosidade")
        print("[MQTT] Inscrito em sala/+/ocupacao e sala/+/luminosidade")

        async for message in client.messages:
            topic = str(message.topic)
            payload = message.payload.decode()
            await _handle_message(topic, payload)


async def start() -> None:
    global _task
    _task = asyncio.create_task(_run())


async def stop() -> None:
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
