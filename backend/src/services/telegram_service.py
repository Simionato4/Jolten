import asyncio
from datetime import datetime, timezone

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, ContextTypes, filters

from src.config import settings
from src.services import mqtt_service, redis_service

_app: Application | None = None
_task: asyncio.Task | None = None


def _build_app() -> Application:
    return (
        Application.builder()
        .token(settings.telegram_token)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )


def _formatar_tempo(segundos: int) -> str:
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    partes = []
    if horas:
        partes.append(f"{horas} {'hora' if horas == 1 else 'horas'}")
    if minutos:
        partes.append(f"{minutos} {'minuto' if minutos == 1 else 'minutos'}")
    if segs or not partes:
        partes.append(f"{segs} {'segundo' if segs == 1 else 'segundos'}")
    return " e ".join(partes) if len(partes) <= 2 else ", ".join(partes[:-1]) + " e " + partes[-1]


async def send_alert(sala_id: str, tempo_vazia: int) -> None:
    if _app is None:
        return
    keyboard = [
        [
            InlineKeyboardButton("💡 Manter Ligado", callback_data=f"ligar_{sala_id}"),
            InlineKeyboardButton("🛑 Desligar", callback_data=f"desligar_{sala_id}"),
        ]
    ]
    await _app.bot.send_message(
        chat_id=settings.gestor_chat_id,
        text=f"⚠️ *Sala {sala_id}* está vazia e com luz acesa há *{_formatar_tempo(tempo_vazia)}*. O que deseja fazer?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    await mqtt_service.log_event(sala_id, f"⚠️ Alerta enviado — vazia há {_formatar_tempo(tempo_vazia)}")


async def send_movement_alert(sala_id: str) -> None:
    if _app is None:
        return
    await _app.bot.send_message(
        chat_id=settings.gestor_chat_id,
        text=f"✅ *Sala {sala_id}*: movimento detectado! Alerta cancelado automaticamente.",
        parse_mode="Markdown",
    )


async def _button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    acao, sala_id = query.data.split("_", 1)

    if acao == "desligar":
        await mqtt_service.publish(f"sala/{sala_id}/comando", "OFF")
        await mqtt_service.log_event(sala_id, "🛑 Luz desligada remotamente via Telegram")
        texto = f"🛑 Cargas da Sala {sala_id} *desligadas* remotamente."
    else:
        await mqtt_service.publish(f"sala/{sala_id}/comando", "ON")
        await mqtt_service.log_event(sala_id, "💡 Luz ligada remotamente via Telegram")
        texto = f"💡 Sala {sala_id} mantida *ligada*. Monitoramento retomado."

    await query.edit_message_text(text=texto, parse_mode="Markdown")


async def _check_timeouts(context: ContextTypes.DEFAULT_TYPE) -> None:
    salas = await redis_service.get_all_rooms()
    agora = datetime.now(timezone.utc)

    for sala in salas:
        ultimo = datetime.fromisoformat(sala["ultimo_movimento"])
        tempo_vazia = int((agora - ultimo).total_seconds())

        if not sala["ocupada"] and sala["luminosidade"] and tempo_vazia > settings.timeout_sala:
            alerta_key = f"alerta_enviado:{sala['sala_id']}"
            r = redis_service.get_redis()
            ja_enviado = await r.get(alerta_key)
            if not ja_enviado:
                await send_alert(sala["sala_id"], tempo_vazia)
                await r.set(alerta_key, "1", ex=settings.timeout_sala * 2)
                print(f"[TELEGRAM] Alerta enviado — Sala {sala['sala_id']} vazia há {tempo_vazia}s")


async def _texto_comando(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != settings.gestor_chat_id:
        return

    texto = update.message.text.lower().strip()
    sala_id = "101"

    if "desligar" in texto:
        await mqtt_service.publish(f"sala/{sala_id}/comando", "OFF")
        await mqtt_service.log_event(sala_id, "🛑 Luz desligada remotamente via Telegram")
        await update.message.reply_text(f"🛑 *Sala {sala_id} desligada.*", parse_mode="Markdown")
    elif "ligar" in texto:
        await mqtt_service.publish(f"sala/{sala_id}/comando", "ON")
        await mqtt_service.log_event(sala_id, "💡 Luz ligada remotamente via Telegram")
        await update.message.reply_text(f"💡 *Sala {sala_id} ligada.*", parse_mode="Markdown")
    elif "estado" in texto:
        estado = await redis_service.get_room_state(sala_id)
        if estado:
            luz = "💡 *Ligada*" if estado["luminosidade"] else "🌑 *Desligada*"
            ocupacao = "🚶 *Ocupada*" if estado["ocupada"] else "💤 *Vazia*"
            await update.message.reply_text(
                f"📊 *Estado atual — Sala {sala_id}*\n\nLuz: {luz}\nOcupação: {ocupacao}",
                parse_mode="Markdown",
            )
            luz_txt = "ligada" if estado["luminosidade"] else "desligada"
            ocup_txt = "ocupada" if estado["ocupada"] else "vazia"
            await mqtt_service.log_event(sala_id, f"📊 Estado consultado — Luz {luz_txt}, sala {ocup_txt}")
        else:
            await update.message.reply_text(f"❓ Sala {sala_id} não encontrada.", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "❓ Comando não reconhecido. Envie *ligar*, *desligar* ou *estado*.",
            parse_mode="Markdown",
        )


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, telegram.error.Conflict):
        return  # Sessão anterior ainda ativa — PTB reintenta automaticamente
    print(f"[TELEGRAM] Erro: {context.error}")


async def _run() -> None:
    global _app
    _app = _build_app()
    _app.add_error_handler(_error_handler)
    _app.add_handler(CallbackQueryHandler(_button_callback))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _texto_comando))
    _app.job_queue.run_repeating(_check_timeouts, interval=10, first=5)

    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)
    print("[TELEGRAM] Bot iniciado.")


async def start() -> None:
    global _task
    _task = asyncio.create_task(_run())


async def stop() -> None:
    global _app, _task
    if _app:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()
        _app = None
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
