import asyncio
import json
import aiomqtt

from src.config import settings
from src.services import influx_service, redis_service

_subscribers: set[asyncio.Queue] = set()
_task: asyncio.Task | None = None


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


async def _broadcast(event: dict) -> None:
    for q in list(_subscribers):
        await q.put(event)


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
                await log_event(sala_id, "✅ Alerta cancelado — movimento detectado", tipo="alerta")
                from src.services import telegram_service
                await telegram_service.send_movement_alert(sala_id)

        await _broadcast({"sala_id": sala_id, "ocupada": ocupada, "tipo": "ocupacao"})
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

        if luz_acendeu:
            await redis_service.get_redis().delete(f"alerta_enviado:{sala_id}")

        await _broadcast({"sala_id": sala_id, "luminosidade": acesa, "tipo": "luminosidade"})
        print(f"[MQTT] sala/{sala_id}/luminosidade → {acesa}")

    elif tipo == "info":
        try:
            info = json.loads(payload)
            await redis_service.set_room_info(
                sala_id,
                uptime=int(info.get("uptime", 0)),
                rssi=int(info.get("rssi", 0)),
                ip=str(info.get("ip", "")),
            )
            print(f"[INFO] sala/{sala_id} → uptime={info.get('uptime')}s rssi={info.get('rssi')}dBm ip={info.get('ip')}")
        except (json.JSONDecodeError, KeyError):
            pass

    elif tipo == "interruptor":
        desligado = payload.strip() == "0"
        if desligado:
            alerta_key = f"alerta_enviado:{sala_id}"
            r = redis_service.get_redis()
            if await r.get(alerta_key):
                await r.delete(alerta_key)
                await log_event(sala_id, "🔌 Luz apagada manualmente — alerta cancelado", tipo="alerta")
                from src.services import telegram_service
                await telegram_service.send_manual_off_alert(sala_id)
        return

    elif tipo == "log":
        from datetime import datetime, timezone
        p = payload.lower()
        if "movimento" in p:
            log_tipo = "movimento"
        elif "luz" in p:
            log_tipo = "luminosidade"
        else:
            log_tipo = "sistema"
        timestamp = datetime.now(timezone.utc).isoformat()
        await redis_service.add_log(sala_id, payload, log_tipo)
        await _broadcast({"sala_id": sala_id, "mensagem": payload, "timestamp": timestamp, "tipo": "log", "log_tipo": log_tipo})
        print(f"[LOG] sala/{sala_id} → {payload}")


async def log_event(sala_id: str, mensagem: str, tipo: str = "sistema") -> None:
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    await redis_service.add_log(sala_id, mensagem, tipo)
    await _broadcast({"sala_id": sala_id, "mensagem": mensagem, "timestamp": timestamp, "tipo": "log", "log_tipo": tipo})


async def publish(topic: str, payload: str) -> None:
    async with aiomqtt.Client(
        hostname=settings.mqtt_broker,
        port=settings.mqtt_port,
        username=settings.mqtt_user,
        password=settings.mqtt_pass,
    ) as client:
        await client.publish(topic, payload)


async def _run() -> None:
    retry_delay = 5
    while True:
        try:
            print("[MQTT] Conectando ao broker...")
            async with aiomqtt.Client(
                hostname=settings.mqtt_broker,
                port=settings.mqtt_port,
                username=settings.mqtt_user,
                password=settings.mqtt_pass,
            ) as client:
                await client.subscribe("sala/+/ocupacao")
                await client.subscribe("sala/+/luminosidade")
                await client.subscribe("sala/+/log")
                await client.subscribe("sala/+/info")
                await client.subscribe("sala/+/interruptor")
                print("[MQTT] Inscrito em sala/+/ocupacao, sala/+/luminosidade, sala/+/log, sala/+/info")
                retry_delay = 5
                async for message in client.messages:
                    topic = str(message.topic)
                    payload = message.payload.decode()
                    try:
                        await _handle_message(topic, payload)
                    except Exception as e:
                        print(f"[MQTT] Erro ao processar {topic}: {e}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[MQTT] Conexão perdida: {e}. Reconectando em {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


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
