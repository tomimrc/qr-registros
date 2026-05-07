# app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.admin import Admin
from app.models.device import Device
from app.models.attendance import AttendanceLog
from app.core.dependencies import get_current_admin
from datetime import date
from fastapi import Query
from fastapi.responses import StreamingResponse
from app.models.employee import Employee
from app.models.jornada import Jornada
from app.core.security import create_qr_token# (Asegurate de importar tu dependencia get_current_admin si la usas)
import csv
import io
from datetime import datetime, timedelta, timezone

import uuid

router = APIRouter()


# =============================================
# SCHEMAS
# =============================================
class EmployeeCreate(BaseModel):
    nombre: str
    sector: str
    convenio: Optional[str] = None
    valor_hora: float = 0


class EmployeeUpdate(BaseModel):
    nombre: Optional[str] = None
    sector: Optional[str] = None
    convenio: Optional[str] = None
    valor_hora: Optional[float] = None
    activo: Optional[bool] = None



@router.get("/qr-data")
async def get_dynamic_qr(request: Request, admin = Depends(get_current_admin)):
    tenant_id_str = str(admin.tenant_id)
    token = create_qr_token(tenant_id_str)
    
    base_url = str(request.base_url).rstrip('/')
    
    # 👇 EL CAMBIO ESTÁ ACÁ: reemplazamos /index.html por /app
    url_fichaje = f"{base_url}/app?tenant_id={tenant_id_str}&qr_token={token}"
    
    return {
        "url": url_fichaje,
        "token": token
    }

# =============================================
# DASHBOARD - RESUMEN
# =============================================
@router.get("/summary")
async def get_daily_summary(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()

    jornadas_hoy = await db.execute(
        select(Jornada).where(
            Jornada.tenant_id == admin.tenant_id,
            func.date(Jornada.fecha) == today
        )
    )
    jornadas = jornadas_hoy.scalars().all()

    presentes = [j for j in jornadas if j.hora_fin is None]
    salieron = [j for j in jornadas if j.hora_fin is not None]

    return {
        "fecha": today.isoformat(),
        "total_entradas": len(jornadas),
        "presentes": len(presentes),
        "salieron": len(salieron),
    }


# =============================================
# DASHBOARD - ESTADO EMPLEADOS
# =============================================
@router.get("/employees/status")
async def get_employees_status(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()

    result = await db.execute(
        select(Employee).where(
            Employee.tenant_id == admin.tenant_id,
            Employee.activo == True
        )
    )
    employees = result.scalars().all()

    jornadas_result = await db.execute(
        select(Jornada).where(
            Jornada.tenant_id == admin.tenant_id,
            func.date(Jornada.fecha) == today,
            Jornada.hora_fin == None
        )
    )
    jornadas_abiertas = {j.employee_id: j for j in jornadas_result.scalars().all()}

    return [
        {
            "id": str(emp.id),
            "nombre": emp.nombre,
            "sector": emp.sector,
            "presente": emp.id in jornadas_abiertas,
            "hora_inicio": jornadas_abiertas[emp.id].hora_inicio.isoformat()
                if emp.id in jornadas_abiertas else None
        }
        for emp in employees
    ]


# =============================================
# DASHBOARD - LOGS DEL DÍA
# =============================================
@router.get("/logs")
async def get_recent_logs(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    today = date.today()

    result = await db.execute(
        select(AttendanceLog, Employee.nombre)
        .join(Employee, AttendanceLog.employee_id == Employee.id)
        .where(
            AttendanceLog.tenant_id == admin.tenant_id,
            func.date(AttendanceLog.timestamp) == today
        )
        .order_by(AttendanceLog.timestamp.desc())
        .limit(50)
    )
    rows = result.all()
    out = []

    for log, nombre in rows:
        # 1. Buscamos 'tipo_registro' primero, si no está caemos en 'tipo'
        tipo_attr = getattr(log, "tipo_registro", None) or getattr(log, "tipo", None)
        
        # 2. Extraemos el string correctamente manejando el Enum
        if hasattr(tipo_attr, "value"):
            tipo_str = tipo_attr.value
        else:
            tipo_str = str(tipo_attr) if tipo_attr is not None else "desconocido"
            
        # 3. Formateamos el timestamp de forma segura
        timestamp = getattr(log, "timestamp", None)
        
        out.append({
            "nombre": nombre,
            "tipo": tipo_str,
            "timestamp": timestamp.isoformat() if timestamp else None,
        })

    return out


@router.get("/alerts/anomalies")
async def get_anomalies(
    window_days: int = Query(default=3, ge=1, le=14),
    limit: int = Query(default=30, ge=1, le=100),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Detecta alertas operativas simples en ventana reciente sin persistir estado adicional."""
    now = datetime.now(timezone.utc)
    since_utc = now - timedelta(days=window_days)
    since_date = since_utc.date()
    today = date.today()
    long_shift_hours = 12.0
    duplicate_window_minutes = 3
    anomalies = []

    # 1) Jornadas abiertas muy largas o arrastradas de días anteriores (salida faltante)
    open_stmt = (
        select(Jornada, Employee.nombre)
        .join(Employee, Employee.id == Jornada.employee_id)
        .where(
            Jornada.tenant_id == admin.tenant_id,
            Jornada.hora_fin.is_(None),
            Jornada.fecha >= since_date,
        )
    )
    open_rows = (await db.execute(open_stmt)).all()
    for jornada, nombre in open_rows:
        hours_open = (now - jornada.hora_inicio).total_seconds() / 3600.0
        if jornada.fecha < today:
            anomalies.append(
                {
                    "type": "missing_checkout",
                    "severity": "high",
                    "employee_id": str(jornada.employee_id),
                    "employee_name": nombre,
                    "occurred_at": jornada.hora_inicio,
                    "message": "Jornada abierta desde un dia anterior sin registro de salida.",
                    "meta": {
                        "fecha": jornada.fecha.isoformat(),
                        "horas_abierta": round(hours_open, 2),
                    },
                }
            )
        elif hours_open >= long_shift_hours:
            anomalies.append(
                {
                    "type": "long_open_shift",
                    "severity": "medium",
                    "employee_id": str(jornada.employee_id),
                    "employee_name": nombre,
                    "occurred_at": jornada.hora_inicio,
                    "message": f"Jornada abierta por mas de {int(long_shift_hours)} horas.",
                    "meta": {
                        "fecha": jornada.fecha.isoformat(),
                        "horas_abierta": round(hours_open, 2),
                    },
                }
            )

    # 2) Jornadas cerradas excesivamente largas
    closed_stmt = (
        select(Jornada, Employee.nombre)
        .join(Employee, Employee.id == Jornada.employee_id)
        .where(
            Jornada.tenant_id == admin.tenant_id,
            Jornada.hora_fin.is_not(None),
            Jornada.fecha >= since_date,
        )
    )
    closed_rows = (await db.execute(closed_stmt)).all()
    for jornada, nombre in closed_rows:
        total_hours = (jornada.hora_fin - jornada.hora_inicio).total_seconds() / 3600.0
        if total_hours >= long_shift_hours:
            anomalies.append(
                {
                    "type": "long_shift",
                    "severity": "medium",
                    "employee_id": str(jornada.employee_id),
                    "employee_name": nombre,
                    "occurred_at": jornada.hora_fin,
                    "message": f"Jornada cerrada con duracion mayor a {int(long_shift_hours)} horas.",
                    "meta": {
                        "fecha": jornada.fecha.isoformat(),
                        "horas_totales": round(total_hours, 2),
                    },
                }
            )

    # 3) Doble fichaje cercano del mismo tipo (entrada/entrada o salida/salida)
    logs_stmt = (
        select(AttendanceLog, Employee.nombre)
        .join(Employee, Employee.id == AttendanceLog.employee_id)
        .where(
            AttendanceLog.tenant_id == admin.tenant_id,
            AttendanceLog.timestamp >= since_utc,
        )
        .order_by(AttendanceLog.employee_id.asc(), AttendanceLog.timestamp.asc())
    )
    log_rows = (await db.execute(logs_stmt)).all()
    last_log_by_employee: dict[uuid.UUID, tuple[str, datetime]] = {}
    for log, nombre in log_rows:
        tipo_attr = getattr(log, "tipo_registro", None) or getattr(log, "tipo", None)
        tipo_str = tipo_attr.value if hasattr(tipo_attr, "value") else str(tipo_attr)

        if log.employee_id in last_log_by_employee:
            prev_tipo, prev_ts = last_log_by_employee[log.employee_id]
            delta_minutes = (log.timestamp - prev_ts).total_seconds() / 60.0
            if prev_tipo == tipo_str and delta_minutes <= duplicate_window_minutes:
                anomalies.append(
                    {
                        "type": "duplicate_punch",
                        "severity": "low",
                        "employee_id": str(log.employee_id),
                        "employee_name": nombre,
                        "occurred_at": log.timestamp,
                        "message": "Fichaje duplicado en ventana corta.",
                        "meta": {
                            "tipo": tipo_str,
                            "delta_minutos": round(delta_minutes, 2),
                        },
                    }
                )

        last_log_by_employee[log.employee_id] = (tipo_str, log.timestamp)

    anomalies.sort(key=lambda item: item["occurred_at"], reverse=True)
    anomalies = anomalies[:limit]

    return {
        "window_days": window_days,
        "total": len(anomalies),
        "items": [
            {
                **item,
                "occurred_at": item["occurred_at"].isoformat(),
            }
            for item in anomalies
        ],
    }


# =============================================
# CRUD EMPLEADOS
# =============================================

@router.get("/employees")
async def list_employees(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los empleados del tenant (activos e inactivos)."""
    result = await db.execute(
        select(Employee).where(Employee.tenant_id == admin.tenant_id)
        .order_by(Employee.activo.desc(), Employee.nombre)
    )
    employees = result.scalars().all()

    first_day_of_month = date.today().replace(day=1)
    jornadas_mes_result = await db.execute(
        select(Jornada).where(
            Jornada.tenant_id == admin.tenant_id,
            Jornada.fecha >= first_day_of_month,
            Jornada.hora_inicio.is_not(None),
            Jornada.hora_fin.is_not(None)
        )
    )
    jornadas_mes = jornadas_mes_result.scalars().all()

    horas_por_empleado: dict[uuid.UUID, float] = {}
    for jornada in jornadas_mes:
        horas = (jornada.hora_fin - jornada.hora_inicio).total_seconds() / 3600.0
        horas_por_empleado[jornada.employee_id] = horas_por_empleado.get(jornada.employee_id, 0.0) + horas

    return [
        {
            "id": str(emp.id),
            "nombre": emp.nombre,
            "sector": emp.sector,
            "convenio": emp.convenio,
            "valor_hora": float(emp.valor_hora),
            "activo": emp.activo,
            "created_at": emp.created_at.isoformat(),
            "horas_acumuladas_mes": round(horas_por_empleado.get(emp.id, 0.0), 2),
            "pago_estimado_mes": round(horas_por_empleado.get(emp.id, 0.0) * float(emp.valor_hora), 2)
        }
        for emp in employees
    ]


@router.post("/employees", status_code=201)
async def create_employee(
    data: EmployeeCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo empleado vinculado al tenant del admin."""
    employee = Employee(
        tenant_id=admin.tenant_id,
        nombre=data.nombre,
        sector=data.sector,
        convenio=data.convenio,
        valor_hora=data.valor_hora,
        activo=True
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)

    return {"message": "Empleado creado", "id": str(employee.id)}


@router.put("/employees/{employee_id}")
async def update_employee(
    employee_id: uuid.UUID,
    data: EmployeeUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Actualiza datos de un empleado. Solo campos enviados son modificados."""
    employee = await db.get(Employee, employee_id)

    if not employee or employee.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    # Solo actualiza los campos que vienen en el request
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.commit()
    return {"message": "Empleado actualizado"}


@router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: uuid.UUID,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Baja lógica: marca el empleado como inactivo en vez de borrarlo."""
    employee = await db.get(Employee, employee_id)

    if not employee or employee.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    employee.activo = False

    devices_result = await db.execute(
        select(Device).where(
            Device.employee_id == employee_id,
            Device.tenant_id == admin.tenant_id,
            Device.activo == True
        )
    )
    active_devices = devices_result.scalars().all()
    for device in active_devices:
        device.activo = False

    await db.commit()
    return {
        "message": f"{employee.nombre} dado de baja",
        "devices_unlinked": len(active_devices)
    }


# =============================================
# GESTIÓN DE DISPOSITIVOS
# =============================================

@router.get("/employees/{employee_id}/device")
async def get_employee_device(
    employee_id: uuid.UUID,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Ver el dispositivo vinculado a un empleado."""
    result = await db.execute(
        select(Device).where(
            Device.employee_id == employee_id,
            Device.tenant_id == admin.tenant_id,
            Device.activo == True
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        return {"device": None, "message": "Sin dispositivo vinculado"}

    return {
        "device": {
            "id": str(device.id),
            "device_token": device.device_token,
            "device_name": device.device_name,
            "registered_at": device.registered_at.isoformat() if device.registered_at else None
        }
    }


@router.delete("/employees/{employee_id}/device")
async def unlink_device(
    employee_id: uuid.UUID,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Desvincula el dispositivo de un empleado.
    Útil cuando el empleado cambia de celular.
    El empleado podrá vincularse de nuevo desde el QR.
    """
    result = await db.execute(
        select(Device).where(
            Device.employee_id == employee_id,
            Device.tenant_id == admin.tenant_id,
            Device.activo == True
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="No hay dispositivo vinculado.")

    device.activo = False
    await db.commit()
    return {"message": "Dispositivo desvinculado. El empleado puede vincularse desde el QR."}
# =============================================
# EXPORTAR LIQUIDACIÓN (EXCEL / CSV)
# =============================================
@router.get("/export/attendance")
async def export_attendance(
    start_date: date = Query(...),
    end_date: date = Query(...),
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    # 1. Traer empleados y sus jornadas en ese rango de fechas
    stmt = select(Employee, Jornada).join(
        Jornada, Employee.id == Jornada.employee_id
    ).where(
        Employee.tenant_id == admin.tenant_id,
        Jornada.fecha >= start_date,
        Jornada.fecha <= end_date
    )
    result = await db.execute(stmt)
    rows = result.all()

    # 2. Procesar la matemática y agrupar por empleado
    data_map = {}
    for emp, jornada in rows:
        if emp.id not in data_map:
            data_map[emp.id] = {
                "nombre": emp.nombre,
                "sector": emp.sector,
                "valor_hora": float(emp.valor_hora or 0),
                "horas_totales": 0.0
            }

        # Calcular horas (solo sumamos si el empleado tiene hora_inicio y hora_fin registradas)
        if jornada.hora_inicio and jornada.hora_fin:
            diff = jornada.hora_fin - jornada.hora_inicio
            # Convertimos la diferencia de tiempo a horas decimales (ej: 1 hora 30 min = 1.5 hs)
            horas = diff.total_seconds() / 3600.0
            data_map[emp.id]["horas_totales"] += horas

    # 3. Armar el archivo para Excel
    output = io.StringIO()
    # Usamos ";" como delimitador, que es el estándar para el Excel en español
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    # Escribir la cabecera
    writer.writerow(["Empleado", "Sector", "Valor Hora ($)", "Horas Trabajadas", "Total a Pagar ($)"])

    # Escribir los datos de cada empleado
    for emp_id, info in data_map.items():
        horas = round(info["horas_totales"], 2)
        paga = round(horas * info["valor_hora"], 2)
        writer.writerow([
            info["nombre"],
            info["sector"],
            info["valor_hora"],
            horas,
            paga
        ])

    # 4. Magia para los Tildes: Forzar codificación BOM (Byte Order Mark) 
    # para que Excel detecte correctamente los caracteres como UTF-8
    csv_string = "\ufeff" + output.getvalue()

    headers = {
        "Content-Disposition": f"attachment; filename=liquidacion_{start_date}_al_{end_date}.csv"
    }
    
    return StreamingResponse(
        iter([csv_string]), 
        media_type="text/csv; charset=utf-8", 
        headers=headers
    )