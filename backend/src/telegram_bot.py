import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    mensagem = (
        f"Olá! Sou o Bot de Automação e Eficiência Energética.\n\n"
        f"Seu Chat ID é: {chat_id}\n\n"
        f"Guarde esse número! O sistema precisará dele para saber para quem enviar os alertas."
    )
    print(f"[INFO] Novo usuário conectado. Chat ID: {chat_id}")
    await update.message.reply_text(mensagem)

async def simular_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando temporário para testarmos os botões inline antes de integrar com o MQTT."""
    
    keyboard = [
        [
            InlineKeyboardButton("💡 Ligar Cargas", callback_data="comando_ligar"),
            InlineKeyboardButton("🛑 Desligar Cargas", callback_data="comando_desligar"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    mensagem = "⚠️ *Alerta:* A Sala 101 está vazia pelo tempo limite configurado. O que deseja fazer?"
    
    await update.message.reply_text(mensagem, reply_markup=reply_markup, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao = query.data
    
    if acao == "comando_ligar":
        # Futuramente, aqui publicaremos a ação de LIGAR no Mosquitto MQTT
        novo_texto = "✅ *Ação executada:* Você ligou a iluminação e a climatização."
        print("[COMANDO] Requisição para LIGAR cargas na Sala 101.")
        
    elif acao == "comando_desligar":
        # Futuramente, aqui publicaremos a ação de DESLIGAR no Mosquitto MQTT
        novo_texto = "🛑 *Ação executada:* Todas as cargas foram desligadas com sucesso."
        print("[COMANDO] Requisição para DESLIGAR cargas na Sala 101.")

    await query.edit_message_text(text=novo_texto, parse_mode='Markdown')

def iniciar_bot():
    if not TOKEN:
        print("❌ Erro: TELEGRAM_TOKEN não encontrado. Verifique seu arquivo .env!")
        return

    app = (Application.builder()
                      .token(TOKEN)
                      .read_timeout(30)
                      .write_timeout(30)
                      .connect_timeout(30)
                      .pool_timeout(30)
                      .build())

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alerta", simular_alerta))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot do Telegram iniciado! Aguardando comandos...")
    
    app.run_polling()

if __name__ == "__main__":
    iniciar_bot()