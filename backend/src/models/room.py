from pydantic import BaseModel
from datetime import datetime


class RoomStatus(BaseModel):
    sala_id: str
    ocupada: bool
    luminosidade: bool
    ultimo_movimento: datetime
    tempo_vazia: int  # segundos desde o último movimento
    uptime: int | None = None   # segundos desde o boot do ESP32
    rssi: int | None = None     # sinal Wi-Fi em dBm
    ip: str | None = None       # IP do ESP32 na rede


class RoomHistory(BaseModel):
    timestamp: datetime
    movimento: int
    luminosidade: int | None = None


class CommandPayload(BaseModel):
    comando: str  # "ON" | "OFF"
