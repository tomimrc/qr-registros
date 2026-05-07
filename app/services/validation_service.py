# app/services/validation_service.py

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tenant import Tenant
from app.models.device import Device
from app.core.config import settings
from app.services.feature_service import FeatureService
import uuid

# CORRECCIÓN 1: Importamos desde security.py (eliminamos la dependencia de utils.py)
from app.core.security import verify_qr_token


class ValidationService:

    @staticmethod
    async def validate_request(
        request: Request,
        tenant_id: uuid.UUID,
        device_token: str,
        qr_token: str,
        db: AsyncSession
    ):
        # ========== PASO 0: Validar Tenant y QR ==========
        tenant = await db.get(Tenant, tenant_id)
        if not verify_qr_token(str(tenant_id), qr_token, max_age_seconds=60):
            raise HTTPException(status_code=400, detail="Código QR expirado o inválido. Por favor, escaneá de nuevo.")
        
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail="Empresa no encontrada."
            )

        if not tenant.is_active:
            raise HTTPException(
                status_code=403,
                detail="Esta empresa tiene el servicio desactivado."
            )

        has_qr_access = await FeatureService.has_active_feature_access(
            db=db,
            tenant_id=tenant_id,
            feature_code="qr_attendance",
        )
        if not has_qr_access:
            raise HTTPException(
                status_code=403,
                detail="La feature qr_attendance no está activa para esta empresa.",
            )
        # ===================================================

        # CORRECCIÓN 2: Validar IP global desactivada para modelo SaaS
        client_ip = request.client.host
        # if settings.ALLOWED_IP and client_ip != settings.ALLOWED_IP:
        #     if not settings.DEBUG:
        #         raise HTTPException(
        #             status_code=403,
        #             detail=f"IP no autorizada: {client_ip}. Debe estar en el WiFi del local."
        #         )

        # ========== PASO 1: Buscar por tenant + token ==========
        query = select(Device).where(
            Device.tenant_id == tenant_id,
            Device.device_token == device_token,
            Device.activo == True
        )
        result = await db.execute(query)
        device = result.scalar_one_or_none()

        if not device:
            raise HTTPException(
                status_code=401,
                detail="Dispositivo no vinculado o no autorizado por el administrador."
            )
        # ==================================================================

        return client_ip, device.employee_id