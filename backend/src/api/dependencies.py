from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from src.config import settings

_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str = Security(_scheme)) -> str:
    if key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida")
    return key
