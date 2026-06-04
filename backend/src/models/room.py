from pydantic import BaseModel
from datetime import datetime


class RoomStatus(BaseModel):
    sala_id: str
    ocupada: bool
    luminosidade: bool
    ultimo_movimento: datetime
    tempo_vazia: int  # segundos desde o último movimento


class RoomHistory(BaseModel):
    timestamp: datetime
    movimento: int
    luminosidade: int | None = None


class CommandPayload(BaseModel):
    comando: str  # "ON" | "OFF"
