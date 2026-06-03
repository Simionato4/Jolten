import sys
import os
import time
import paho.mqtt.client as mqtt

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("GESTOR_CHAT_ID")
BROKER = "localhost"
PORT = 1883
TIMEOUT_TESTE = 30

INFLUX_URL    = os.getenv("INFLUX_URL")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN")
INFLUX_ORG    = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

try:
    db_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = db_client.write_api(write_options=SYNCHRONOUS)
    print("✅ InfluxDB Configurado!")
except Exception as e:
    print(f"❌ Erro no InfluxDB: {e}")

salas = {
    "101": {"ultimo_movimento": time.time(), "alerta_enviado": False}
}

mqtt_client = mqtt.Client("Backend_Orquestrador")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Conectado com sucesso!")
        client.subscribe("sala/+/ocupacao")

def on_message(client, userdata, msg):
    topico = msg.topic
    payload = msg.payload.decode('utf-8')
    print(f"📡 MQTT Recebido -> {topico}: {payload}")
    
    partes = topico.split("/")
    if len(partes) == 3 and partes[2] == "ocupacao":
        sala_id = partes[1]
        valor_movimento = int(payload) if payload.isdigit() else (1 if payload.lower() == "true" else 0)

        try:
            ponto = Point("sensor_pir").tag("sala", sala_id).field("movimento", valor_movimento)
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=ponto)
            print(f"💾 Dado salvo no banco: Sala {sala_id} | Movimento: {valor_movimento}")
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
        
        if valor_movimento == 1:
            if sala_id in salas:
                salas[sala_id]["ultimo_movimento"] = time.time()
                salas[sala_id]["alerta_enviado"] = False

async def checar_timeouts(context):
    agora = time.time()
    for sala_id, dados in salas.items():
        tempo_vazia = agora - dados["ultimo_movimento"]
        
        if tempo_vazia > TIMEOUT_TESTE and not dados["alerta_enviado"]:
            print(f"⚠️ Sala {sala_id} estourou o timeout! Enviando alerta via Telegram...")
            
            keyboard = [
                [
                    InlineKeyboardButton("💡 Manter Ligado", callback_data=f"ligar_{sala_id}"),
                    InlineKeyboardButton("🛑 Desligar", callback_data=f"desligar_{sala_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            mensagem = f"⚠️ *Alerta:* A Sala {sala_id} está vazia há mais de {TIMEOUT_TESTE} segundos. Deseja desligar os equipamentos?"
            
            await context.bot.send_message(
                chat_id=CHAT_ID, 
                text=mensagem, 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
            salas[sala_id]["alerta_enviado"] = True

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    acao, sala_id = query.data.split("_")
    
    if acao == "desligar":
        mqtt_client.publish(f"sala/{sala_id}/comando", "OFF")
        print(f"🛑 Gestor clicou em DESLIGAR — Sala {sala_id}")
        novo_texto = f"🛑 *Ação executada:* Cargas da Sala {sala_id} foram DESLIGADAS remotamente."
    else:
        mqtt_client.publish(f"sala/{sala_id}/comando", "ON")
        print(f"💡 Gestor clicou em MANTER LIGADO — Sala {sala_id}")
        novo_texto = f"💡 *Ação executada:* Cargas da Sala {sala_id} foram MANTIDAS LIGADAS remotamente."
        
    await query.edit_message_text(text=novo_texto, parse_mode='Markdown')

async def comando_manual(update, context):
    if str(update.effective_chat.id) != CHAT_ID:
        return

    texto = update.message.text.lower().strip()
    sala_id = "101"

    if "desligar" in texto:
        mqtt_client.publish(f"sala/{sala_id}/comando", "OFF")
        print(f"🛑 Comando manual: Sala {sala_id} DESLIGADA via Telegram")
        await update.message.reply_text(
            f"🛑 *Luz da Sala {sala_id} DESLIGADA.*",
            parse_mode='Markdown'
        )
    elif "ligar" in texto:
        mqtt_client.publish(f"sala/{sala_id}/comando", "ON")
        salas[sala_id]["ultimo_movimento"] = time.time()
        salas[sala_id]["alerta_enviado"] = False
        print(f"💡 Comando manual: Sala {sala_id} LIGADA via Telegram")
        await update.message.reply_text(
            f"💡 *Luz da Sala {sala_id} LIGADA.* Monitoramento retomado.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❓ Comando não reconhecido. Envie *ligar luz* ou *desligar luz*.",
            parse_mode='Markdown'
        )

def iniciar_orquestrador():
    if not TOKEN or not CHAT_ID:
        print("❌ Erro fatal: Verifique seu arquivo .env! Estão faltando credenciais.")
        return
        
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.loop_start() 
    
    app = (Application.builder()
                      .token(TOKEN)
                      .read_timeout(30).write_timeout(30).connect_timeout(30)
                      .build())
    
    app.job_queue.run_repeating(checar_timeouts, interval=10, first=5)
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, comando_manual))
    
    print("🚀 Orquestrador IoT Iniciado! Monitorando as salas...")
    app.run_polling()

if __name__ == "__main__":
    iniciar_orquestrador()