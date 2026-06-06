import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.services import mqtt_service

router = APIRouter(tags=["events"])


async def _stream():
    from src.services import redis_service
    from datetime import datetime, timezone

    queue = mqtt_service.subscribe()
    try:
        try:
            salas = await redis_service.get_all_rooms()
            agora = datetime.now(timezone.utc)
            for sala in salas:
                ultimo = datetime.fromisoformat(sala["ultimo_movimento"])
                sala["tempo_vazia"] = int((agora - ultimo).total_seconds())
        except Exception as e:
            print(f"[SSE] Erro ao buscar estado inicial do Redis: {e}")
            salas = []

        yield f"data: {json.dumps({'tipo': 'sync', 'salas': salas})}\n\n"

        while True:
            try:
                evento = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(evento)}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        mqtt_service.unsubscribe(queue)


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
