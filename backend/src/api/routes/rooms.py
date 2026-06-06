from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from src.services import redis_service, influx_service

router = APIRouter(tags=["rooms"])


@router.get("/rooms")
async def list_rooms():
    salas = await redis_service.get_all_rooms()
    agora = datetime.now(timezone.utc)
    for sala in salas:
        ultimo = datetime.fromisoformat(sala["ultimo_movimento"])
        sala["tempo_vazia"] = int((agora - ultimo).total_seconds())
    return salas


@router.get("/rooms/{sala_id}")
async def get_room(sala_id: str):
    sala = await redis_service.get_room_state(sala_id)
    if not sala:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    agora = datetime.now(timezone.utc)
    ultimo = datetime.fromisoformat(sala["ultimo_movimento"])
    sala["tempo_vazia"] = int((agora - ultimo).total_seconds())
    info = await redis_service.get_room_info(sala_id)
    if info:
        sala.update(info)
    return sala


@router.get("/rooms/{sala_id}/history")
async def get_room_history(sala_id: str, range_minutes: int = 60):
    historico = influx_service.query_history(sala_id, range_minutes)
    if not historico:
        raise HTTPException(status_code=404, detail="Nenhum histórico encontrado")
    return historico


@router.get("/rooms/{sala_id}/logs")
async def get_room_logs(sala_id: str):
    return await redis_service.get_logs(sala_id)
