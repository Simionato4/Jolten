# Jolteon IoT — Monitoramento de Salas em Tempo Real

Sistema de automação e eficiência energética para ambientes corporativos. Monitora ocupação e iluminação de salas via sensores conectados a um ESP32, exibe o estado em tempo real num dashboard web e envia alertas via Telegram quando uma sala fica vazia com a luz acesa.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                         HARDWARE                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  ESP32 (Sala 101)                   │    │
│  │                                                     │    │
│  │   GPIO 2  ← Sensor PIR   (movimento)                │    │
│  │   GPIO 10 ← Sensor LDR   (luminosidade)             │    │
│  │   GPIO 4  → Relé         (iluminação)               │    │
│  └────────────────────────┬────────────────────────────┘    │
└───────────────────────────┼─────────────────────────────────┘
                            │ MQTT sobre TCP/IP (Wi-Fi)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAILWAY (Cloud)                          │
│                                                             │
│  ┌─────────────┐  MQTT  ┌──────────────────────────────┐   │
│  │  Mosquitto  │◄──────►│     Backend — FastAPI         │   │
│  │ MQTT Broker │        │                              │   │
│  └─────────────┘        │  mqtt_service   (subscreve)  │   │
│                         │  redis_service  (estado)     │   │
│  ┌─────────────┐        │  influx_service (histórico)  │   │
│  │    Redis    │◄──────►│  telegram_service (alertas)  │   │
│  │   (Estado)  │        │  SSE /events    (push→front) │   │
│  └─────────────┘        └──────────────┬───────────────┘   │
│                                        │                   │
│  ┌─────────────┐                       │                   │
│  │  InfluxDB   │◄──────────────────────┘                   │
│  │ (Histórico) │                                           │
│  └─────────────┘                                           │
└────────────────────────────────────────────────────────────┘
                            │ SSE (HTTP/HTTPS)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              VERCEL — Frontend (Next.js)                    │
│                   jolten.vercel.app                         │
└─────────────────────────────────────────────────────────────┘
                            │ Telegram Bot API
                            ▼
                    ┌───────────────┐
                    │    Telegram   │
                    │ (Bot do Gestor│
                    └───────────────┘
```

### Fluxo de dados

1. O **ESP32** lê os sensores a cada 500ms e publica no broker MQTT:
   - `sala/101/ocupacao` — `1` (movimento detectado) ou `0` (sem movimento)
   - `sala/101/luminosidade` — `1` (luz acesa) ou `0` (apagada)
   - `sala/101/log` — mensagens textuais de eventos
   - `sala/101/info` — JSON com `uptime`, `rssi` e `ip` (a cada 30s)
   - Também assina `sala/101/comando` para receber `ON`/`OFF` e acionar o relé

2. O **Backend** (FastAPI no Railway) está inscrito em todos esses tópicos via `aiomqtt`. A cada mensagem:
   - Persiste o estado atual no **Redis** (chave `sala:{id}`)
   - Grava a série histórica no **InfluxDB**
   - Faz broadcast do evento para todos os clientes SSE ativos

3. O **Frontend** (Next.js no Vercel) mantém uma conexão SSE aberta em `/events`. Ao conectar recebe o snapshot completo de todas as salas; em seguida recebe eventos incrementais em tempo real sem polling.

4. O **Telegram Bot** (embutido no backend) verifica a cada 10 segundos se alguma sala está vazia com luz acesa além do tempo configurado (`TIMEOUT_SALA`). Se sim, envia alerta com botões de ação. O gestor pode responder pelo Telegram ou pelo dashboard.

---

## Componentes

### Firmware — ESP32 (`/firmware`)

Desenvolvido em **C com ESP-IDF**.

| Arquivo | Descrição |
|---|---|
| `main/main.c` | Lógica principal: Wi-Fi, MQTT, leitura de GPIO, publicação e controle do relé |
| `main/credentials.h` | Credenciais locais — **gitignored** (ver `credentials.h.example`) |
| `main/credentials.h.example` | Template de credenciais para configuração |

**Pinos:**

| GPIO | Componente | Direção |
|---|---|---|
| 2 | Sensor PIR — detecção de movimento | Entrada |
| 4 | Relé — controle da iluminação | Saída |
| 10 | Sensor LDR — detecção de luz | Entrada |

---

### Backend — FastAPI (`/backend`)

```
src/
├── main.py                    # App FastAPI, lifespan, CORS, registro das rotas
├── config.py                  # Variáveis de ambiente via pydantic-settings
├── api/
│   ├── dependencies.py        # Autenticação por API Key (X-API-Key)
│   └── routes/
│       ├── events.py          # GET /events — SSE com pub/sub por subscriber
│       ├── rooms.py           # GET /rooms e detalhes de cada sala
│       └── commands.py        # POST /rooms/{id}/command — controle remoto
└── services/
    ├── mqtt_service.py        # Conexão MQTT com retry exponencial, broadcast SSE
    ├── redis_service.py       # Estado atual, logs e info do dispositivo
    ├── influx_service.py      # Escrita e consulta de séries históricas
    └── telegram_service.py    # Bot, alertas automáticos, comandos via texto
```

**Endpoints:**

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| `GET` | `/events` | — | Stream SSE com eventos em tempo real |
| `GET` | `/rooms` | — | Lista todas as salas com estado atual |
| `GET` | `/rooms/{id}` | — | Estado detalhado + info do dispositivo (uptime, rssi, ip) |
| `GET` | `/rooms/{id}/history?range_minutes=60` | — | Histórico de ocupação via InfluxDB |
| `GET` | `/rooms/{id}/logs` | — | Últimas 50 entradas de log da sala |
| `POST` | `/rooms/{id}/command` | X-API-Key | Envia `ON` ou `OFF` via MQTT para o relé |
| `GET` | `/health` | — | Health check |

---

### Frontend — Next.js (`/frontend`)

Deploy em: **https://jolten.vercel.app**

```
src/
├── app/
│   ├── page.tsx              # Dashboard — grid de salas em tempo real
│   └── rooms/[id]/page.tsx   # Detalhe da sala — métricas, gráfico, controle, logs
├── components/
│   ├── RoomCard.tsx          # Card de sala no dashboard
│   ├── CommandButtons.tsx    # Botões Ligar / Desligar
│   ├── OccupancyChart.tsx    # Gráfico histórico de ocupação
│   └── RoomLogs.tsx          # Feed de logs em tempo real
└── lib/
    ├── api.ts                # Funções de fetch e sendCommand
    └── hooks/useRealtime.ts  # Hook SSE com reconexão automática
```

**Páginas:**
- `/` — Dashboard com cards de todas as salas e indicador de conexão SSE
- `/rooms/[id]` — Detalhe com métricas (ocupação, iluminação, último movimento, tempo vazia), gráfico histórico, controle remoto e aba de logs

---

### Telegram Bot

O bot roda dentro do backend e responde apenas ao `GESTOR_CHAT_ID` configurado.

**Comandos por texto:**

| Mensagem | Ação |
|---|---|
| `ligar` | Liga a iluminação da Sala 101 via MQTT |
| `desligar` | Desliga a iluminação da Sala 101 via MQTT |
| `status` | Retorna o estado atual de ocupação e iluminação |

**Alerta automático:**

```
Sala vazia + luz acesa por mais de TIMEOUT_SALA segundos
                        │
                        ▼
      Bot envia mensagem ao gestor com botões inline:
      [ 💡 Manter Ligado ]  [ 🛑 Desligar ]
                        │
                        ▼
      Gestor responde → Backend publica MQTT → ESP32 aciona o relé
```

---

### Infraestrutura local — Docker Compose (`/infrastructure`)

Para desenvolvimento local sem Railway:

```bash
cd infrastructure
cp .env.example .env     # preencha as credenciais
docker compose up -d
```

Serviços disponíveis:

| Serviço | Porta | Descrição |
|---|---|---|
| Mosquitto | 1883 | Broker MQTT |
| InfluxDB | 8086 | Banco de dados de séries temporais |
| Redis | 6379 | Estado em memória |
| Backend | 8000 | API FastAPI |

---

## Deploy em produção

| Componente | Plataforma | Serviço |
|---|---|---|
| Backend (FastAPI) | Railway | `amiable-upliftment` — Root dir: `/backend` |
| Broker MQTT (Mosquitto) | Railway | `Jolten` — Root dir: `/infrastructure/mosquitto` |
| Redis | Railway | Gerenciado |
| InfluxDB | Railway | Gerenciado |
| Frontend (Next.js) | Vercel | `jolten.vercel.app` — Root dir: `/frontend` |

### Variáveis de ambiente — Backend (Railway)

| Variável | Descrição |
|---|---|
| `MQTT_BROKER` | Host do Mosquitto |
| `MQTT_PORT` | Porta do broker |
| `MQTT_USER` | Usuário MQTT |
| `MQTT_PASS` | Senha MQTT |
| `REDIS_URL` | URL de conexão do Redis |
| `INFLUX_URL` | URL do InfluxDB |
| `INFLUX_TOKEN` | Token de acesso |
| `INFLUX_ORG` | Organização |
| `INFLUX_BUCKET` | Bucket de dados |
| `TELEGRAM_TOKEN` | Token obtido no BotFather |
| `GESTOR_CHAT_ID` | Chat ID do gestor (use `/start` no bot para descobrir) |
| `API_KEY` | Chave para autenticar comandos remotos |
| `CORS_ORIGINS` | JSON array com origens permitidas — ex: `["https://jolten.vercel.app"]` |
| `TIMEOUT_SALA` | Segundos sem movimento para disparar alerta (padrão: `30`) |

### Variáveis de ambiente — Frontend (Vercel)

| Variável | Descrição |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL pública do backend no Railway |
| `NEXT_PUBLIC_API_KEY` | Mesma chave definida em `API_KEY` no backend |

---

## Desenvolvimento local

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
# configure backend/.env com as variáveis necessárias
python run.py
```

### Frontend

```bash
cd frontend
npm install
# configure frontend/.env.local com NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### Firmware

```bash
cd firmware
cp main/credentials.h.example main/credentials.h
# edite credentials.h com SSID, senha Wi-Fi e credenciais MQTT
idf.py build flash monitor
```

---

## Segurança

- Credenciais do firmware ficam em `firmware/main/credentials.h` — **gitignored**
- Credenciais da infra local ficam em `infrastructure/.env` — **gitignored**
- Todas as variáveis sensíveis do backend são injetadas via Railway — nunca commitadas
- O endpoint de comando requer header `X-API-Key`
- O bot Telegram só responde ao `GESTOR_CHAT_ID` configurado
