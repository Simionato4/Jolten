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


async def add_log(sala_id: str, mensagem: str, tipo: str = "sistema") -> None:
    r = get_redis()
    agora = datetime.now(timezone.utc).isoformat()
    entry = json.dumps({"timestamp": agora, "mensagem": mensagem, "tipo": tipo})
    await r.lpush(f"logs:{sala_id}", entry)
    await r.ltrim(f"logs:{sala_id}", 0, 49)


async def get_logs(sala_id: str) -> list[dict]:
    r = get_redis()
    entries = await r.lrange(f"logs:{sala_id}", 0, -1)
    return [json.loads(e) for e in entries]


async def set_room_info(sala_id: str, uptime: int, rssi: int, ip: str) -> None:
    r = get_redis()
    payload = json.dumps({"uptime": uptime, "rssi": rssi, "ip": ip})
    await r.set(f"info:{sala_id}", payload, ex=120)


async def get_room_info(sala_id: str) -> dict | None:
    r = get_redis()
    raw = await r.get(f"info:{sala_id}")
    return json.loads(raw) if raw else None


async def get_timeout() -> int | None:
    r = get_redis()
    raw = await r.get("config:timeout_sala")
    return int(raw) if raw else None


async def set_timeout(segundos: int) -> None:
    r = get_redis()
    await r.set("config:timeout_sala", str(segundos))


async def close() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
