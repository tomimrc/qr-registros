from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_feature_access
from app.database import get_db
from app.models.admin import Admin
from app.models.crm import CRMAppointment, CRMClientFile, CRMClientFileProfessionalLink, CRMProfessional, CRMVisitReport
from app.services.audit_service import AuditService
from app.services.crm_service import CRMService

FEATURE_CRM_CORE = "crm_core"
router = APIRouter(prefix="/crm", tags=["CRM"])


class CRMProfessionalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    role_label: str | None = Field(default=None, max_length=120)
    specialty: str | None = Field(default=None, max_length=120)
    calendar_color: str = Field(default="#1d4ed8", max_length=20)
    extra_data: dict | None = None


class CRMProfessionalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    role_label: str | None = Field(default=None, max_length=120)
    specialty: str | None = Field(default=None, max_length=120)
    calendar_color: str | None = Field(default=None, max_length=20)
    active: bool | None = None
    extra_data: dict | None = None


class CRMClientFileCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=255)
    subject_kind: str = Field(default="client", max_length=50)
    reference_code: str | None = Field(default=None, max_length=100)
    document_id: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    coverage_type: str = Field(default="particular", max_length=30)
    coverage_name: str | None = Field(default=None, max_length=255)
    affiliate_number: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    professional_ids: list[uuid.UUID] = Field(default_factory=list)
    extra_data: dict | None = None


class CRMClientFileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=255)
    subject_kind: str | None = Field(default=None, max_length=50)
    reference_code: str | None = Field(default=None, max_length=100)
    document_id: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    coverage_type: str | None = Field(default=None, max_length=30)
    coverage_name: str | None = Field(default=None, max_length=255)
    affiliate_number: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=30)
    notes: str | None = None
    professional_ids: list[uuid.UUID] | None = None
    extra_data: dict | None = None


class CRMAppointmentCreate(BaseModel):
    subject_id: uuid.UUID
    professional_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime | None = None
    status: str = Field(default="scheduled", max_length=30)
    source: str = Field(default="internal", max_length=30)
    title: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    extra_data: dict | None = None


class CRMAppointmentUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: str | None = Field(default=None, max_length=30)
    source: str | None = Field(default=None, max_length=30)
    title: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    extra_data: dict | None = None


class CRMVisitReportCreate(BaseModel):
    appointment_id: uuid.UUID | None = None
    subject_id: uuid.UUID
    professional_id: uuid.UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    reason: str | None = None
    summary: str = Field(min_length=2)
    findings: str | None = None
    actions_taken: str | None = None
    next_steps: str | None = None
    outcome: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    extra_data: dict | None = None


@router.post("/professionals", status_code=status.HTTP_201_CREATED)
async def create_professional(
    data: CRMProfessionalCreate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    professional = CRMProfessional(
        tenant_id=admin.tenant_id,
        name=data.name,
        role_label=data.role_label,
        specialty=data.specialty,
        calendar_color=data.calendar_color,
        extra_data=data.extra_data,
    )
    db.add(professional)
    await db.commit()
    await db.refresh(professional)

    await AuditService.log_event(
        db=db,
        action="crm.professional.created",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_professional",
        target_id=professional.id,
        tenant_id=admin.tenant_id,
        details={"name": professional.name},
    )

    return {"message": "Profesional creado", "professional": CRMService.serialize_professional(professional)}


@router.get("/professionals")
async def list_professionals(
    active: bool | None = Query(default=None),
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CRMProfessional).where(CRMProfessional.tenant_id == admin.tenant_id)
    if active is not None:
        stmt = stmt.where(CRMProfessional.active == active)
    stmt = stmt.order_by(CRMProfessional.active.desc(), CRMProfessional.name.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [CRMService.serialize_professional(row) for row in rows]}


@router.patch("/professionals/{professional_id}")
async def update_professional(
    professional_id: uuid.UUID,
    data: CRMProfessionalUpdate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    professional = await CRMService.get_professional_or_404(db, admin.tenant_id, professional_id)
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(professional, field, value)

    await db.commit()
    await db.refresh(professional)
    return {"message": "Profesional actualizado", "professional": CRMService.serialize_professional(professional)}


@router.post("/files", status_code=status.HTTP_201_CREATED)
async def create_client_file(
    data: CRMClientFileCreate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    client_file = CRMClientFile(
        tenant_id=admin.tenant_id,
        subject_kind=CRMService.normalize_subject_kind(data.subject_kind),
        display_name=data.display_name,
        reference_code=data.reference_code,
        document_id=data.document_id,
        email=data.email,
        phone=data.phone,
        coverage_type=CRMService.normalize_coverage_type(data.coverage_type),
        coverage_name=data.coverage_name,
        affiliate_number=data.affiliate_number,
        notes=data.notes,
        extra_data=data.extra_data,
    )
    db.add(client_file)
    await db.flush()

    linked_professionals = await CRMService.replace_file_professional_links(
        db,
        admin.tenant_id,
        client_file.id,
        data.professional_ids,
    )

    await db.commit()
    await db.refresh(client_file)

    await AuditService.log_event(
        db=db,
        action="crm.file.created",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_client_file",
        target_id=client_file.id,
        tenant_id=admin.tenant_id,
        details={"display_name": client_file.display_name, "subject_kind": client_file.subject_kind},
    )

    return {
        "message": "Expediente creado",
        "file": CRMService.serialize_client_file(client_file, linked_professionals=linked_professionals),
    }


@router.get("/files")
async def list_client_files(
    q: str | None = Query(default=None),
    subject_kind: str | None = Query(default=None),
    coverage_type: str | None = Query(default=None),
    affiliate_number: str | None = Query(default=None),
    professional_id: uuid.UUID | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CRMClientFile).where(CRMClientFile.tenant_id == admin.tenant_id)
    if q:
        stmt = stmt.where(CRMClientFile.display_name.ilike(f"%{q.strip()}%"))
    if subject_kind:
        stmt = stmt.where(CRMClientFile.subject_kind == CRMService.normalize_subject_kind(subject_kind))
    if coverage_type:
        stmt = stmt.where(CRMClientFile.coverage_type == CRMService.normalize_coverage_type(coverage_type))
    if affiliate_number:
        stmt = stmt.where(CRMClientFile.affiliate_number.ilike(f"%{affiliate_number.strip()}%"))
    if professional_id:
        stmt = stmt.join(
            CRMClientFileProfessionalLink,
            CRMClientFileProfessionalLink.client_file_id == CRMClientFile.id,
        ).where(
            CRMClientFileProfessionalLink.tenant_id == admin.tenant_id,
            CRMClientFileProfessionalLink.professional_id == professional_id,
        )
    if status_value:
        stmt = stmt.where(CRMClientFile.status == CRMService.normalize_file_status(status_value))
    else:
        stmt = stmt.where(CRMClientFile.status != "archived")
    stmt = stmt.order_by(CRMClientFile.display_name.asc()).distinct()
    rows = (await db.execute(stmt)).scalars().all()
    row_ids = [row.id for row in rows]
    linked_map = await CRMService.list_professional_links_for_files(db, admin.tenant_id, row_ids)
    return {
        "items": [
            CRMService.serialize_client_file(
                row,
                linked_professionals=linked_map.get(str(row.id), []),
            )
            for row in rows
        ]
    }


@router.get("/files/{file_id}")
async def get_client_file(
    file_id: uuid.UUID,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    return await CRMService.build_subject_timeline(db, admin.tenant_id, file_id)


@router.patch("/files/{file_id}")
async def update_client_file(
    file_id: uuid.UUID,
    data: CRMClientFileUpdate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    client_file = await CRMService.get_client_file_or_404(db, admin.tenant_id, file_id)
    payload = data.model_dump(exclude_unset=True)
    professional_ids = payload.pop("professional_ids", None)
    if "subject_kind" in payload:
        payload["subject_kind"] = CRMService.normalize_subject_kind(payload["subject_kind"])
    if "coverage_type" in payload and payload["coverage_type"] is not None:
        payload["coverage_type"] = CRMService.normalize_coverage_type(payload["coverage_type"])
    if "status" in payload and payload["status"] is not None:
        payload["status"] = CRMService.normalize_file_status(payload["status"])
    for field, value in payload.items():
        setattr(client_file, field, value)

    linked_professionals: list[dict] = []
    if professional_ids is not None:
        linked_professionals = await CRMService.replace_file_professional_links(
            db,
            admin.tenant_id,
            file_id,
            professional_ids,
        )

    await db.commit()
    await db.refresh(client_file)
    if professional_ids is None:
        linked_map = await CRMService.list_professional_links_for_files(db, admin.tenant_id, [file_id])
        linked_professionals = linked_map.get(str(file_id), [])
    return {
        "message": "Expediente actualizado",
        "file": CRMService.serialize_client_file(client_file, linked_professionals=linked_professionals),
    }


@router.patch("/files/{file_id}/archive")
async def archive_client_file(
    file_id: uuid.UUID,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    client_file = await CRMService.get_client_file_or_404(db, admin.tenant_id, file_id)
    client_file.status = "archived"
    await db.commit()
    await db.refresh(client_file)

    await AuditService.log_event(
        db=db,
        action="crm.file.archived",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_client_file",
        target_id=client_file.id,
        tenant_id=admin.tenant_id,
        details={"status": client_file.status},
    )

    return {"message": "Expediente archivado", "file": CRMService.serialize_client_file(client_file)}


@router.patch("/files/{file_id}/restore")
async def restore_client_file(
    file_id: uuid.UUID,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    client_file = await CRMService.get_client_file_or_404(db, admin.tenant_id, file_id)
    client_file.status = "active"
    await db.commit()
    await db.refresh(client_file)

    await AuditService.log_event(
        db=db,
        action="crm.file.restored",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_client_file",
        target_id=client_file.id,
        tenant_id=admin.tenant_id,
        details={"status": client_file.status},
    )

    return {"message": "Expediente restaurado", "file": CRMService.serialize_client_file(client_file)}


@router.post("/appointments", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    data: CRMAppointmentCreate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    client_file = await CRMService.get_client_file_or_404(db, admin.tenant_id, data.subject_id)
    professional = await CRMService.get_professional_or_404(db, admin.tenant_id, data.professional_id)
    CRMService.ensure_professional_subject_kind_compatibility(professional, client_file)

    appointment = CRMAppointment(
        tenant_id=admin.tenant_id,
        subject_id=data.subject_id,
        professional_id=data.professional_id,
        created_by_admin_id=admin.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        status=CRMService.normalize_appointment_status(data.status),
        source=CRMService.normalize_source(data.source),
        title=data.title,
        location=data.location,
        notes=data.notes,
        extra_data=data.extra_data,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    await AuditService.log_event(
        db=db,
        action="crm.appointment.created",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_appointment",
        target_id=appointment.id,
        tenant_id=admin.tenant_id,
        details={"subject_id": str(data.subject_id), "professional_id": str(data.professional_id)},
    )

    return {"message": "Turno creado", "appointment": CRMService.serialize_appointment(appointment)}


@router.get("/appointments")
async def list_appointments(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    professional_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    if (from_date and not to_date) or (to_date and not from_date):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes enviar from_date y to_date juntos")
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from_date no puede ser mayor que to_date")

    stmt = select(CRMAppointment).where(CRMAppointment.tenant_id == admin.tenant_id)
    if from_date and to_date:
        start_datetime = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        end_datetime = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(CRMAppointment.starts_at >= start_datetime, CRMAppointment.starts_at <= end_datetime)
    if professional_id:
        stmt = stmt.where(CRMAppointment.professional_id == professional_id)
    if subject_id:
        stmt = stmt.where(CRMAppointment.subject_id == subject_id)
    if status_value:
        stmt = stmt.where(CRMAppointment.status == CRMService.normalize_appointment_status(status_value))

    stmt = stmt.order_by(CRMAppointment.starts_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [CRMService.serialize_appointment(row) for row in rows]}


@router.patch("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: uuid.UUID,
    data: CRMAppointmentUpdate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    appointment = await CRMService.get_appointment_or_404(db, admin.tenant_id, appointment_id)
    payload = data.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] is not None:
        payload["status"] = CRMService.normalize_appointment_status(payload["status"])
    if "source" in payload and payload["source"] is not None:
        payload["source"] = CRMService.normalize_source(payload["source"])
    for field, value in payload.items():
        setattr(appointment, field, value)

    await db.commit()
    await db.refresh(appointment)
    return {"message": "Turno actualizado", "appointment": CRMService.serialize_appointment(appointment)}


@router.patch("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid.UUID,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    appointment = await CRMService.get_appointment_or_404(db, admin.tenant_id, appointment_id)
    appointment.status = "cancelled"
    await db.commit()
    await db.refresh(appointment)

    await AuditService.log_event(
        db=db,
        action="crm.appointment.cancelled",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_appointment",
        target_id=appointment.id,
        tenant_id=admin.tenant_id,
        details={"status": appointment.status},
    )

    return {"message": "Turno cancelado", "appointment": CRMService.serialize_appointment(appointment)}


@router.post("/visit-reports", status_code=status.HTTP_201_CREATED)
async def create_visit_report(
    data: CRMVisitReportCreate,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    client_file = await CRMService.get_client_file_or_404(db, admin.tenant_id, data.subject_id)
    professional = await CRMService.get_professional_or_404(db, admin.tenant_id, data.professional_id)
    CRMService.ensure_professional_subject_kind_compatibility(professional, client_file)
    if data.appointment_id:
        appointment = await CRMService.get_appointment_or_404(db, admin.tenant_id, data.appointment_id)
        if appointment.subject_id != data.subject_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El turno no pertenece al expediente")

    visit_report = CRMVisitReport(
        tenant_id=admin.tenant_id,
        subject_id=data.subject_id,
        professional_id=data.professional_id,
        appointment_id=data.appointment_id,
        created_by_admin_id=admin.id,
        occurred_at=data.occurred_at,
        duration_minutes=data.duration_minutes,
        reason=data.reason,
        summary=data.summary,
        findings=data.findings,
        actions_taken=data.actions_taken,
        next_steps=data.next_steps,
        outcome=data.outcome,
        notes=data.notes,
        extra_data=data.extra_data,
    )
    db.add(visit_report)
    await db.commit()
    await db.refresh(visit_report)

    await AuditService.log_event(
        db=db,
        action="crm.visit_report.created",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_visit_report",
        target_id=visit_report.id,
        tenant_id=admin.tenant_id,
        details={"subject_id": str(data.subject_id), "professional_id": str(data.professional_id)},
    )

    return {"message": "Reporte de visita guardado", "visit_report": CRMService.serialize_visit_report(visit_report)}


@router.get("/visit-reports")
async def list_visit_reports(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    professional_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    if (from_date and not to_date) or (to_date and not from_date):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes enviar from_date y to_date juntos")
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from_date no puede ser mayor que to_date")

    stmt = select(CRMVisitReport).where(CRMVisitReport.tenant_id == admin.tenant_id)
    if from_date and to_date:
        start_datetime = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        end_datetime = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(CRMVisitReport.occurred_at >= start_datetime, CRMVisitReport.occurred_at <= end_datetime)
    if professional_id:
        stmt = stmt.where(CRMVisitReport.professional_id == professional_id)
    if subject_id:
        stmt = stmt.where(CRMVisitReport.subject_id == subject_id)

    stmt = stmt.order_by(CRMVisitReport.occurred_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    if not include_archived:
        rows = [row for row in rows if not CRMService.is_visit_report_archived(row)]
    return {"items": [CRMService.serialize_visit_report(row) for row in rows]}


@router.patch("/visit-reports/{report_id}/archive")
async def archive_visit_report(
    report_id: uuid.UUID,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(CRMVisitReport, report_id)
    if not report or report.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reporte no encontrado")
    extra_data = report.extra_data or {}
    extra_data["archived"] = True
    report.extra_data = extra_data
    await db.commit()
    await db.refresh(report)

    await AuditService.log_event(
        db=db,
        action="crm.visit_report.archived",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_visit_report",
        target_id=report.id,
        tenant_id=admin.tenant_id,
        details={"archived": True},
    )

    return {"message": "Reporte archivado", "visit_report": CRMService.serialize_visit_report(report)}


@router.patch("/visit-reports/{report_id}/restore")
async def restore_visit_report(
    report_id: uuid.UUID,
    admin: Admin = Depends(require_feature_access(FEATURE_CRM_CORE)),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(CRMVisitReport, report_id)
    if not report or report.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reporte no encontrado")
    extra_data = report.extra_data or {}
    extra_data["archived"] = False
    report.extra_data = extra_data
    await db.commit()
    await db.refresh(report)

    await AuditService.log_event(
        db=db,
        action="crm.visit_report.restored",
        actor_type="admin",
        actor_id=admin.id,
        target_type="crm_visit_report",
        target_id=report.id,
        tenant_id=admin.tenant_id,
        details={"archived": False},
    )

    return {"message": "Reporte restaurado", "visit_report": CRMService.serialize_visit_report(report)}
