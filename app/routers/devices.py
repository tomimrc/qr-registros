# app/routers/devices.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel

from app.database import get_db
from app.models.tenant import Tenant
from app.models.device import Device
from app.models.employee import Employee
from app.services.feature_service import FeatureService

router = APIRouter()

class LinkDevicePayload(BaseModel):
    tenant_id: uuid.UUID
    employee_id: uuid.UUID
    device_token: str
    device_name: str

@router.post("/check")
async def check_device(
    tenant_id: uuid.UUID = Body(...),
    device_token: str = Body(...),
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Empresa no encontrada o inactiva.")

    has_qr_access = await FeatureService.has_active_feature_access(
        db=db,
        tenant_id=tenant_id,
        feature_code="qr_attendance",
    )
    if not has_qr_access:
        raise HTTPException(status_code=403, detail="Feature qr_attendance no habilitada para este tenant")

    query = select(Device).where(
        Device.tenant_id == tenant_id,
        Device.device_token == device_token,
        Device.activo == True
    )
    result = await db.execute(query)
    device = result.scalar_one_or_none()

    if device:
        employee = await db.get(Employee, device.employee_id)
        return {
            "status": "linked",
            "employee_name": employee.nombre,
            "employee_id": str(employee.id)
        }
    else:
        return {
            "status": "unlinked",
            "message": "Dispositivo nuevo. Seleccioná tu nombre para vincularte."
        }

@router.get("/employees/unlinked")
async def get_unlinked_employees(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Empresa no encontrada o inactiva.")

    has_qr_access = await FeatureService.has_active_feature_access(
        db=db,
        tenant_id=tenant_id,
        feature_code="qr_attendance",
    )
    if not has_qr_access:
        raise HTTPException(status_code=403, detail="Feature qr_attendance no habilitada para este tenant")

    linked_ids = select(Device.employee_id).where(
        Device.tenant_id == tenant_id,
        Device.activo == True
    ).scalar_subquery()

    query = select(Employee).where(
        Employee.tenant_id == tenant_id,
        Employee.activo == True,
        Employee.id.not_in(linked_ids)
    )
    result = await db.execute(query)
    employees = result.scalars().all()

    return [
        {"id": str(emp.id), "nombre": emp.nombre, "sector": emp.sector}
        for emp in employees
    ]

@router.post("/link")
async def link_device(payload: LinkDevicePayload, db: AsyncSession = Depends(get_db)):
    """Vincula un dispositivo (o actualiza el dueño si el token ya existía)"""
    tenant = await db.get(Tenant, payload.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Empresa no encontrada o inactiva.")

    has_qr_access = await FeatureService.has_active_feature_access(
        db=db,
        tenant_id=payload.tenant_id,
        feature_code="qr_attendance",
    )
    if not has_qr_access:
        raise HTTPException(status_code=403, detail="Feature qr_attendance no habilitada para este tenant")

    employee = await db.get(Employee, payload.employee_id)
    if not employee or employee.tenant_id != payload.tenant_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    # Usamos PostgreSQL UPSERT para evitar errores de concurrencia
    stmt = pg_insert(Device.__table__).values(
        tenant_id=payload.tenant_id,
        employee_id=payload.employee_id,
        device_token=payload.device_token,
        device_name=payload.device_name,
        activo=True,
        registered_at=datetime.now(timezone.utc),
        last_used_at=datetime.now(timezone.utc)
    ).on_conflict_do_update(
        index_elements=['device_token'],
        set_={
            "employee_id": payload.employee_id,
            "device_name": payload.device_name,
            "activo": True,
            "last_used_at": datetime.now(timezone.utc),
            "tenant_id": payload.tenant_id,
        }
    )

    try:
        await db.execute(stmt)
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al vincular dispositivo")
        
    return {"message": "Dispositivo vinculado exitosamente", "employee_name": employee.nombre}