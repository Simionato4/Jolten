import paho.mqtt.client as mqtt
import json

BROKER = "localhost"
PORT = 1883
TOPIC_OCUPACAO = "sala/+/ocupacao" # O '+' funciona como um coringa para qualquer ID de sala
TOPIC_LUMINOSIDADE = "sala/+/luminosidade"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado ao Broker MQTT local com sucesso!")
        client.subscribe(TOPIC_OCUPACAO)
        client.subscribe(TOPIC_LUMINOSIDADE)
        print(f"📡 Escutando os tópicos: {TOPIC_OCUPACAO} e {TOPIC_LUMINOSIDADE}")
    else:
        print(f"❌ Falha ao conectar. Código de erro: {rc}")

def on_message(client, userdata, msg):
    topico = msg.topic
    payload = msg.payload.decode('utf-8')
    
    print(f"\n[MENSAGEM RECEBIDA] Tópico: {topico} | Dados: {payload}")
    
    # Aqui, futuramente, vamos extrair o estado do sensor PIR para resetar o timeout de 60 minutos

def iniciar_mqtt():
    client = mqtt.Client("Backend_Orquestrador")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start() 
    except Exception as e:
        print(f"Erro ao iniciar MQTT: {e}")

if __name__ == "__main__":
    import time
    iniciar_mqtt()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Encerrando...")