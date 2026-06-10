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
    await mqtt_service.log_event(sala_id, f"⚠️ Alerta enviado — vazia há {_formatar_tempo(tempo_vazia)}", tipo="alerta")


async def send_manual_off_alert(sala_id: str) -> None:
    if _app is None:
        return
    await _app.bot.send_message(
        chat_id=settings.gestor_chat_id,
        text=f"🔌 *Sala {sala_id}*: luz apagada manualmente pelo interruptor. Alerta cancelado automaticamente.",
        parse_mode="Markdown",
    )


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
        await mqtt_service.log_event(sala_id, "🛑 Luz desligada remotamente via Telegram", tipo="remoto")
        r = redis_service.get_redis()
        await r.delete(f"alerta_enviado:{sala_id}")
        texto = f"🛑 Cargas da Sala {sala_id} *desligadas* remotamente."
    else:
        await mqtt_service.publish(f"sala/{sala_id}/comando", "ON")
        await mqtt_service.log_event(sala_id, "💡 Luz ligada remotamente via Telegram", tipo="remoto")
        texto = f"💡 Sala {sala_id} mantida *ligada*. Monitoramento retomado."

    await query.edit_message_text(text=texto, parse_mode="Markdown")


async def _check_timeouts(context: ContextTypes.DEFAULT_TYPE) -> None:
    salas = await redis_service.get_all_rooms()
    agora = datetime.now(timezone.utc)
    timeout = await redis_service.get_timeout() or settings.timeout_sala

    for sala in salas:
        ultimo = datetime.fromisoformat(sala["ultimo_movimento"])
        tempo_vazia = int((agora - ultimo).total_seconds())

        if not sala["ocupada"] and sala["luminosidade"] and tempo_vazia > timeout:
            alerta_key = f"alerta_enviado:{sala['sala_id']}"
            r = redis_service.get_redis()
            ja_enviado = await r.get(alerta_key)
            if not ja_enviado:
                await send_alert(sala["sala_id"], tempo_vazia)
                await r.set(alerta_key, "1", ex=timeout)
                print(f"[TELEGRAM] Alerta enviado — Sala {sala['sala_id']} vazia há {tempo_vazia}s")


def _parse_timer(texto: str) -> int | None:
    import re
    match = re.search(r"(\d+)\s*(hora[s]?|minuto[s]?|segundo[s]?|h|min|s\b)", texto)
    if not match:
        return None
    valor = int(match.group(1))
    unidade = match.group(2)
    if unidade.startswith("hora") or unidade == "h":
        return valor * 3600
    if unidade.startswith("minuto") or unidade == "min":
        return valor * 60
    return valor


async def _texto_comando(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != settings.gestor_chat_id:
        return

    texto = update.message.text.lower().strip()
    sala_id = "101"

    if "desligar" in texto:
        await mqtt_service.publish(f"sala/{sala_id}/comando", "OFF")
        await mqtt_service.log_event(sala_id, "🛑 Luz desligada remotamente via Telegram", tipo="remoto")
        await update.message.reply_text(f"🛑 *Sala {sala_id} desligada.*", parse_mode="Markdown")
    elif "ligar" in texto:
        await mqtt_service.publish(f"sala/{sala_id}/comando", "ON")
        await mqtt_service.log_event(sala_id, "💡 Luz ligada remotamente via Telegram", tipo="remoto")
        await update.message.reply_text(f"💡 *Sala {sala_id} ligada.*", parse_mode="Markdown")
    elif "status" in texto:
        estado = await redis_service.get_room_state(sala_id)
        if estado:
            luz = "💡 *Ligada*" if estado["luminosidade"] else "🌑 *Desligada*"
            ocupacao = "🚶 *Ocupada*" if estado["ocupada"] else "💤 *Vazia*"
            timeout_atual = await redis_service.get_timeout() or settings.timeout_sala
            await update.message.reply_text(
                f"📊 *Estado atual — Sala {sala_id}*\n\nLuz: {luz}\nOcupação: {ocupacao}\n⏱ Timer de alerta: *{_formatar_tempo(timeout_atual)}*",
                parse_mode="Markdown",
            )
            luz_txt = "ligada" if estado["luminosidade"] else "desligada"
            ocup_txt = "ocupada" if estado["ocupada"] else "vazia"
            await mqtt_service.log_event(sala_id, f"📊 Estado consultado — Luz {luz_txt}, sala {ocup_txt}", tipo="sistema")
        else:
            await update.message.reply_text(f"❓ Sala {sala_id} não encontrada.", parse_mode="Markdown")
    elif "timer" in texto:
        segundos = _parse_timer(texto)
        if segundos is None or segundos <= 0:
            await update.message.reply_text(
                "⚠️ Não entendi o tempo informado.\n\n"
                "Use um dos formatos:\n"
                "• `timer 30 segundos`\n"
                "• `timer 5 minutos`\n"
                "• `timer 1 hora`",
                parse_mode="Markdown",
            )
            return
        await redis_service.set_timeout(segundos)
        await update.message.reply_text(
            f"⏱ Timer de alerta configurado para *{_formatar_tempo(segundos)}*.",
            parse_mode="Markdown",
        )
        await mqtt_service.log_event(sala_id, f"⏱ Timer de alerta alterado para {_formatar_tempo(segundos)}", tipo="sistema")
    else:
        await update.message.reply_text(
            "❓ Comando não reconhecido. Envie:\n"
            "• *ligar* — liga a iluminação\n"
            "• *desligar* — desliga a iluminação\n"
            "• *status* — estado atual da sala\n"
            "• *timer 5 minutos* — configura o tempo de alerta",
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
