# app/services/attendance_service.py

from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
# DESPUÉS
from app.models.attendance import AttendanceLog, TipoRegistro
from app.models.jornada import Jornada
import uuid


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AttendanceService:
    @staticmethod
    async def register_event(
        tenant_id: uuid.UUID,   # NUEVO: primer parámetro
        employee_id: uuid.UUID,
        ip: str,
        device_token: str,
        db: AsyncSession
    ):
        hoy = date.today()

        # 1. Buscar jornada abierta hoy
        #    CAMBIO: Agregamos Jornada.tenant_id == tenant_id
        #    ¿Por qué? Imaginá este escenario sin el filtro:
        #      - Juan trabaja en Restaurante Pepe (tenant A)
        #      - Juan TAMBIÉN trabaja en Ferretería López (tenant B)
        #      - Ficha entrada en Pepe a las 9am
        #      - Va a López a las 14pm y escanea el QR
        #      - Sin filtro de tenant: el sistema encontraría la jornada
        #        abierta de Pepe y la cerraría. ERROR.
        #      - Con filtro de tenant: busca solo jornadas de López,
        #        no encuentra ninguna, crea una nueva. CORRECTO.
        query = select(Jornada).where(
            and_(
                Jornada.tenant_id == tenant_id,
                Jornada.employee_id == employee_id,
                Jornada.fecha == hoy,
                Jornada.hora_fin == None
            )
        )
        result = await db.execute(query)
        jornada_abierta = result.scalar_one_or_none()

        if not jornada_abierta:
            # --- ES UNA ENTRADA ---
            tipo = TipoRegistro.entrada
            nueva_jornada = Jornada(
                tenant_id=tenant_id,       # NUEVO
                employee_id=employee_id,
                fecha=hoy,
                hora_inicio=now_utc()
            )
            db.add(nueva_jornada)
        else:
            # --- ES UNA SALIDA ---
            tipo = TipoRegistro.salida
            jornada_abierta.hora_fin = now_utc()
            diff = jornada_abierta.hora_fin - jornada_abierta.hora_inicio
            jornada_abierta.total_horas = round(diff.total_seconds() / 3600, 2)

        # 2. Log de auditoría
        log = AttendanceLog(
            tenant_id=tenant_id,           # NUEVO
            employee_id=employee_id,
            tipo=tipo,
            ip_address=ip,
            device_token=device_token,
            validacion_ok=True,
            timestamp=now_utc(),
        )
        db.add(log)

        await db.commit()

        return {
            "tipo": tipo,
            "timestamp": now_utc(),
            "jornada_id": jornada_abierta.id if jornada_abierta else nueva_jornada.id
        }