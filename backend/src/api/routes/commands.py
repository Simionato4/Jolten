from fastapi import APIRouter, Depends, HTTPException

from src.models.room import CommandPayload
from src.services import mqtt_service
from src.api.dependencies import require_api_key

router = APIRouter(tags=["commands"])


@router.post("/rooms/{sala_id}/command", dependencies=[Depends(require_api_key)])
async def send_command(sala_id: str, body: CommandPayload):
    comando = body.comando.upper()
    if comando not in ("ON", "OFF"):
        raise HTTPException(status_code=400, detail="Comando deve ser ON ou OFF")
    await mqtt_service.publish(f"sala/{sala_id}/comando", comando)
    return {"sala_id": sala_id, "comando": comando, "status": "enviado"}
