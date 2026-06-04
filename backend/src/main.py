import sys
import asyncio

# aiomqtt usa add_reader/add_writer que não funcionam no ProactorEventLoop do Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.services import mqtt_service, redis_service, telegram_service
from src.api.routes import rooms, commands, events


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await mqtt_service.start()
    await telegram_service.start()
    yield
    await telegram_service.stop()
    await mqtt_service.stop()
    await redis_service.close()


app = FastAPI(
    title="Jolteon IoT API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(commands.router)
app.include_router(events.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
