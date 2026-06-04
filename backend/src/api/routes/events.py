import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.services.mqtt_service import sse_queue

router = APIRouter(tags=["events"])


async def _stream():
    # Ressincronização ao conectar/reconectar (IMPORT-004)
    from src.services import redis_service
    from datetime import datetime, timezone

    salas = await redis_service.get_all_rooms()
    agora = datetime.now(timezone.utc)
    for sala in salas:
        ultimo = datetime.fromisoformat(sala["ultimo_movimento"])
        sala["tempo_vazia"] = int((agora - ultimo).total_seconds())

    yield f"data: {json.dumps({'tipo': 'sync', 'salas': salas})}\n\n"

    while True:
        try:
            evento = await asyncio.wait_for(sse_queue.get(), timeout=30)
            yield f"data: {json.dumps(evento)}\n\n"
        except asyncio.TimeoutError:
            yield ": keep-alive\n\n"


@router.get("/events")
async def sse_endpoint():
    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
