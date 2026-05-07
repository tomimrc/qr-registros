# app/routers/attendance.py

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.validation_service import ValidationService
from app.services.attendance_service import AttendanceService
from app.services.webhook_service import WebhookService
import uuid
from pydantic import BaseModel

router = APIRouter()

# El modelo limpio. Usamos Optional para que no tire error 422 y lo manejemos nosotros con un 400
class AttendancePayload(BaseModel):
    tenant_id: uuid.UUID
    device_token: str
    qr_token: Optional[str] = None  

@router.post("/register")
async def register_attendance(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: AttendancePayload, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Validar tenant, dispositivo y el nuevo token QR
    ip, employee_id = await ValidationService.validate_request(
        request, payload.tenant_id, payload.device_token, payload.qr_token, db
    )

    # 2. Registrar evento (Entrada/Salida) usando los datos del payload
    result = await AttendanceService.register_event(
        payload.tenant_id, employee_id, ip, payload.device_token, db
    )

    tipo_raw = result.get("tipo", "")
    tipo = tipo_raw.value if hasattr(tipo_raw, "value") else str(tipo_raw)

    timestamp = result.get("timestamp")
    timestamp_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)

    background_tasks.add_task(
        WebhookService.send_event,
        "attendance.registered",
        {
            "tenant_id": str(payload.tenant_id),
            "employee_id": str(employee_id),
            "tipo": tipo,
            "timestamp": timestamp_str,
            "ip": ip,
            "device_token": payload.device_token,
        },
    )

    tipo = str(result.get("tipo", "")).upper()

    return {
        "message": f"Registro de {tipo} exitoso.",
        "data": result
    }