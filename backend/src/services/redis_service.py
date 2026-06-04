import json
from datetime import datetime, timezone
from redis.asyncio import Redis

from src.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def set_room_state(sala_id: str, ocupada: bool, luminosidade: bool, reset_timer: bool = False) -> None:
    r = get_redis()
    agora = datetime.now(timezone.utc).isoformat()
    payload = {
        "sala_id": sala_id,
        "ocupada": ocupada,
        "luminosidade": luminosidade,
        "ultimo_movimento": agora if (ocupada or reset_timer) else await _get_last_movement(sala_id, agora),
    }
    await r.set(f"sala:{sala_id}", json.dumps(payload))


async def _get_last_movement(sala_id: str, fallback: str) -> str:
    r = get_redis()
    raw = await r.get(f"sala:{sala_id}")
    if raw:
        data = json.loads(raw)
        return data.get("ultimo_movimento", fallback)
    return fallback


async def get_room_state(sala_id: str) -> dict | None:
    r = get_redis()
    raw = await r.get(f"sala:{sala_id}")
    return json.loads(raw) if raw else None


async def get_all_rooms() -> list[dict]:
    r = get_redis()
    keys = await r.keys("sala:*")
    if not keys:
        return []
    values = await r.mget(*keys)
    return [json.loads(v) for v in values if v]


async def close() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
