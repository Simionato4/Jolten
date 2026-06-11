<div align="center">
  <img src="frontend/public/jolteon.png" alt="Jolteon IoT" width="180" style="border-radius:50%;object-fit:cover;" />

  # Jolteon IoT — Monitoramento de Salas em Tempo Real

  Sistema de automação e eficiência energética para ambientes corporativos. Monitora ocupação e iluminação de salas via sensores conectados a um ESP32, exibe o estado em tempo real num dashboard web e envia alertas via Telegram quando uma sala fica vazia com a luz acesa.
</div>

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
┌────────────────────────────────────────────────────────────┐
│                    RAILWAY (Cloud)                         │
│                                                            │
│  ┌─────────────┐  MQTT  ┌──────────────────────────────┐   │
│  │  Mosquitto  │◄──────►│     Backend — FastAPI        │   │
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
                    │ Bot do Gestor │
                    └───────────────┘
```

### Fluxo de dados

1. O **ESP32** lê os sensores a cada 500ms e publica no broker MQTT:
   - `sala/101/ocupacao` — `1` (movimento detectado) ou `0` (sem movimento)
   - `sala/101/luminosidade` — `1` (luz acesa) ou `0` (apagada)
   - `sala/101/log` — mensagens textuais de eventos
   - `sala/101/info` — JSON com `uptime`, `rssi` e `ip` (a cada 30s)
   - `sala/101/interruptor` — `1` (ligado) ou `0` (desligado), publicado sempre que a chave física é acionada
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
| 5 | Chave DPDT — sinal do interruptor físico | Entrada |
| 10 | Sensor LDR — detecção de luz | Entrada |

---

### Controle duplo — Interruptor físico + Telegram

O sistema integra uma **chave DPDT (Double Pole Double Throw)** que permite controlar a iluminação tanto fisicamente quanto via Telegram, sem que um sobrescreva o outro.

#### Como funciona

A chave DPDT possui dois polos que atuam simultaneamente ao ser acionada:

| Polo | Ligação | Função |
|---|---|---|
| **Polo 1 (AC)** | COM → fase / NO → circuito do relé/lâmpada | Controla o circuito elétrico da luz |
| **Polo 2 (sinal)** | COM → 3.3 V do ESP32 / NO → GPIO 5 | Informa ao ESP32 o estado físico da chave |

Quando o interruptor é acionado, os dois polos comutam juntos: a luz é ligada/desligada diretamente pelo polo AC, e o polo de sinal envia simultaneamente `HIGH` ou `LOW` ao GPIO 5 do ESP32.

#### Lógica de controle sem conflito

O ESP32 monitora continuamente o GPIO 5 para saber a posição física da chave. A lógica garante que os dois meios de controle coexistam:

- **Acionamento físico** → o ESP32 detecta a mudança no GPIO 5, atualiza o estado interno e publica em `sala/101/luminosidade` e `sala/101/interruptor` — o dashboard e o Telegram refletem o novo estado automaticamente.
- **Acionamento remoto (Telegram ou dashboard)** → o ESP32 inverte o sinal esperado da chave. Um único toque no interruptor físico é suficiente para retornar ao controle manual, pois o sistema passa a tratar aquela posição como o novo estado de referência.

Dessa forma, ligar pelo Telegram não "briga" com o interruptor na parede — ambos sempre convergem para um estado consistente com um toque.

#### Desligamento manual durante um alerta pendente

Se o interruptor físico for usado para apagar a luz **enquanto um alerta de "sala vazia com luz acesa" está em aberto**, o backend identifica que o problema já foi resolvido manualmente:

- O alerta é cancelado automaticamente (a flag de controle no Redis é removida, evitando reenvios).
- O bot avisa o gestor: *"🔌 Sala 101: luz apagada manualmente pelo interruptor. Alerta cancelado automaticamente."*
- O evento fica registrado nos logs da sala como `🔌 Luz apagada manualmente — alerta cancelado`.

Esse comportamento espelha o cancelamento já existente para detecção de movimento (veja "Alerta automático" abaixo) — em ambos os casos, qualquer ação que resolva a situação encerra o alerta sem exigir resposta aos botões do Telegram.

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
| `status` | Retorna o estado atual de ocupação, iluminação e timer configurado |
| `timer 30 segundos` | Configura o tempo de alerta para 30 segundos |
| `timer 5 minutos` | Configura o tempo de alerta para 5 minutos |
| `timer 1 hora` | Configura o tempo de alerta para 1 hora |

**Configuração do timer de alerta:**

O timer define por quanto tempo uma sala pode ficar vazia com a luz acesa antes de o bot enviar um alerta. O valor padrão é definido pela variável de ambiente `TIMEOUT_SALA`, mas pode ser alterado a qualquer momento via Telegram — sem necessidade de redeploy.

O novo valor é salvo no Redis e passa a valer imediatamente no próximo ciclo de verificação. Enquanto a sala permanecer no estado de alerta, o bot reenvia a mensagem no mesmo intervalo configurado.

Formatos aceitos: `segundos`, `minutos`, `horas` (e abreviações `s`, `min`, `h`). Mensagens fora desse formato recebem uma resposta de aviso com exemplos corretos.

**Alerta automático:**

```
Sala vazia + luz acesa por mais de [timer configurado]
                        │
                        ▼
      Bot envia mensagem ao gestor com botões inline:
      [ 💡 Manter Ligado ]  [ 🛑 Desligar ]
                        │
                        ├─ Gestor responde → Backend publica MQTT → ESP32 aciona o relé
                        │
                        ├─ Movimento detectado na sala → alerta cancelado automaticamente,
                        │  bot avisa "✅ movimento detectado!"
                        │
                        ├─ Luz apagada no interruptor físico → alerta cancelado automaticamente,
                        │  bot avisa "🔌 luz apagada manualmente"
                        │
                        └─ Sem resposta nem ação física → Bot reenvia o alerta após o mesmo intervalo
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
| `TIMEOUT_SALA` | Tempo padrão (em segundos) sem movimento para disparar alerta — pode ser sobrescrito via Telegram sem redeploy |

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
