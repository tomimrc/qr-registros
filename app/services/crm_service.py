from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMAppointment, CRMClientFile, CRMClientFileProfessionalLink, CRMProfessional, CRMVisitReport

CRM_ALLOWED_SUBJECT_KINDS = {"patient", "client", "case", "company", "lead"}
CRM_ALLOWED_APPOINTMENT_STATUSES = {"scheduled", "confirmed", "completed", "cancelled", "no_show"}
CRM_ALLOWED_SOURCES = {"internal", "self_service"}
CRM_ALLOWED_COVERAGE_TYPES = {"particular", "obra_social", "prepaga"}
CRM_ALLOWED_FILE_STATUSES = {"active", "archived", "inactive"}

CRM_PROFESSIONAL_SUBJECT_KIND_RULES: list[tuple[set[str], set[str]]] = [
    (
        {
            "medic",
            "doctor",
            "psic",
            "terap",
            "kinesi",
            "nutri",
            "fono",
            "odont",
            "pediat",
            "gine",
            "salud",
            "enferm",
        },
        {"patient"},
    ),
    (
        {"abog", "legal", "jurid"},
        {"client", "case"},
    ),
    (
        {"contad", "contab", "impuest", "auditor"},
        {"client", "company"},
    ),
]


class CRMService:
    @staticmethod
    def normalize_subject_kind(subject_kind: str | None) -> str:
        normalized = (subject_kind or "client").strip().lower()
        return normalized if normalized in CRM_ALLOWED_SUBJECT_KINDS else "client"

    @staticmethod
    def normalize_appointment_status(status_value: str | None) -> str:
        normalized = (status_value or "scheduled").strip().lower()
        return normalized if normalized in CRM_ALLOWED_APPOINTMENT_STATUSES else "scheduled"

    @staticmethod
    def normalize_source(source_value: str | None) -> str:
        normalized = (source_value or "internal").strip().lower()
        return normalized if normalized in CRM_ALLOWED_SOURCES else "internal"

    @staticmethod
    def normalize_coverage_type(coverage_type: str | None) -> str:
        normalized = (coverage_type or "particular").strip().lower()
        return normalized if normalized in CRM_ALLOWED_COVERAGE_TYPES else "particular"

    @staticmethod
    def normalize_file_status(status_value: str | None) -> str:
        normalized = (status_value or "active").strip().lower()
        return normalized if normalized in CRM_ALLOWED_FILE_STATUSES else "active"

    @staticmethod
    def is_visit_report_archived(visit_report: CRMVisitReport) -> bool:
        return bool((visit_report.extra_data or {}).get("archived"))

    @staticmethod
    def allowed_subject_kinds_for_professional(professional: CRMProfessional) -> set[str]:
        role_text = f"{professional.role_label or ''} {professional.specialty or ''}".strip().lower()
        if not role_text:
            return set(CRM_ALLOWED_SUBJECT_KINDS)

        for keywords, allowed_kinds in CRM_PROFESSIONAL_SUBJECT_KIND_RULES:
            if any(keyword in role_text for keyword in keywords):
                return set(allowed_kinds)

        return set(CRM_ALLOWED_SUBJECT_KINDS)

    @staticmethod
    def ensure_professional_subject_kind_compatibility(
        professional: CRMProfessional,
        client_file: CRMClientFile,
    ) -> None:
        allowed_kinds = CRMService.allowed_subject_kinds_for_professional(professional)
        if client_file.subject_kind not in allowed_kinds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El profesional {professional.name} no puede operar expedientes tipo "
                    f"{client_file.subject_kind}. Tipos permitidos: {', '.join(sorted(allowed_kinds))}"
                ),
            )

    @staticmethod
    async def get_professional_or_404(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        professional_id: uuid.UUID,
    ) -> CRMProfessional:
        professional = await db.get(CRMProfessional, professional_id)
        if not professional or professional.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesional no encontrado")
        return professional

    @staticmethod
    async def get_client_file_or_404(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> CRMClientFile:
        client_file = await db.get(CRMClientFile, file_id)
        if not client_file or client_file.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expediente no encontrado")
        return client_file

    @staticmethod
    async def get_appointment_or_404(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> CRMAppointment:
        appointment = await db.get(CRMAppointment, appointment_id)
        if not appointment or appointment.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
        return appointment

    @staticmethod
    def serialize_professional(professional: CRMProfessional) -> dict:
        return {
            "id": str(professional.id),
            "name": professional.name,
            "role_label": professional.role_label,
            "specialty": professional.specialty,
            "calendar_color": professional.calendar_color,
            "active": professional.active,
            "extra_data": professional.extra_data or {},
            "created_at": professional.created_at.isoformat() if professional.created_at else None,
            "updated_at": professional.updated_at.isoformat() if professional.updated_at else None,
        }

    @staticmethod
    def serialize_client_file(client_file: CRMClientFile, linked_professionals: list[dict] | None = None) -> dict:
        return {
            "id": str(client_file.id),
            "subject_kind": client_file.subject_kind,
            "display_name": client_file.display_name,
            "reference_code": client_file.reference_code,
            "document_id": client_file.document_id,
            "email": client_file.email,
            "phone": client_file.phone,
            "status": client_file.status,
            "notes": client_file.notes,
            "coverage_type": client_file.coverage_type,
            "coverage_name": client_file.coverage_name,
            "affiliate_number": client_file.affiliate_number,
            "extra_data": client_file.extra_data or {},
            "linked_professionals": linked_professionals or [],
            "created_at": client_file.created_at.isoformat() if client_file.created_at else None,
            "updated_at": client_file.updated_at.isoformat() if client_file.updated_at else None,
        }

    @staticmethod
    def serialize_appointment(appointment: CRMAppointment) -> dict:
        return {
            "id": str(appointment.id),
            "subject_id": str(appointment.subject_id),
            "professional_id": str(appointment.professional_id),
            "created_by_admin_id": str(appointment.created_by_admin_id) if appointment.created_by_admin_id else None,
            "starts_at": appointment.starts_at.isoformat() if appointment.starts_at else None,
            "ends_at": appointment.ends_at.isoformat() if appointment.ends_at else None,
            "status": appointment.status,
            "source": appointment.source,
            "title": appointment.title,
            "location": appointment.location,
            "notes": appointment.notes,
            "extra_data": appointment.extra_data or {},
            "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
            "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
        }

    @staticmethod
    def serialize_visit_report(visit_report: CRMVisitReport) -> dict:
        return {
            "id": str(visit_report.id),
            "subject_id": str(visit_report.subject_id),
            "professional_id": str(visit_report.professional_id),
            "appointment_id": str(visit_report.appointment_id) if visit_report.appointment_id else None,
            "created_by_admin_id": str(visit_report.created_by_admin_id) if visit_report.created_by_admin_id else None,
            "occurred_at": visit_report.occurred_at.isoformat() if visit_report.occurred_at else None,
            "duration_minutes": visit_report.duration_minutes,
            "reason": visit_report.reason,
            "summary": visit_report.summary,
            "findings": visit_report.findings,
            "actions_taken": visit_report.actions_taken,
            "next_steps": visit_report.next_steps,
            "outcome": visit_report.outcome,
            "notes": visit_report.notes,
            "extra_data": visit_report.extra_data or {},
            "created_at": visit_report.created_at.isoformat() if visit_report.created_at else None,
        }

    @staticmethod
    async def get_professionals_by_ids(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        professional_ids: list[uuid.UUID],
    ) -> list[CRMProfessional]:
        if not professional_ids:
            return []
        stmt = select(CRMProfessional).where(
            CRMProfessional.tenant_id == tenant_id,
            CRMProfessional.id.in_(professional_ids),
        )
        rows = (await db.execute(stmt)).scalars().all()
        return rows

    @staticmethod
    async def list_professional_links_for_files(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        file_ids: list[uuid.UUID],
    ) -> dict[str, list[dict]]:
        if not file_ids:
            return {}

        stmt = (
            select(CRMClientFileProfessionalLink, CRMProfessional)
            .join(CRMProfessional, CRMProfessional.id == CRMClientFileProfessionalLink.professional_id)
            .where(
                CRMClientFileProfessionalLink.tenant_id == tenant_id,
                CRMClientFileProfessionalLink.client_file_id.in_(file_ids),
            )
            .order_by(CRMProfessional.name.asc())
        )
        rows = (await db.execute(stmt)).all()

        mapped: dict[str, list[dict]] = {}
        for link, professional in rows:
            file_key = str(link.client_file_id)
            mapped.setdefault(file_key, []).append(
                {
                    "id": str(professional.id),
                    "name": professional.name,
                    "role_label": professional.role_label,
                    "specialty": professional.specialty,
                    "calendar_color": professional.calendar_color,
                }
            )
        return mapped

    @staticmethod
    async def replace_file_professional_links(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        file_id: uuid.UUID,
        professional_ids: list[uuid.UUID],
    ) -> list[dict]:
        client_file = await CRMService.get_client_file_or_404(db, tenant_id, file_id)
        current_stmt = select(CRMClientFileProfessionalLink).where(
            CRMClientFileProfessionalLink.tenant_id == tenant_id,
            CRMClientFileProfessionalLink.client_file_id == file_id,
        )
        current_links = (await db.execute(current_stmt)).scalars().all()
        current_ids = {link.professional_id for link in current_links}
        desired_ids = set(professional_ids)

        remove_ids = current_ids - desired_ids
        add_ids = desired_ids - current_ids

        if remove_ids:
            for link in current_links:
                if link.professional_id in remove_ids:
                    await db.delete(link)

        if add_ids:
            professionals = await CRMService.get_professionals_by_ids(db, tenant_id, list(add_ids))
            existing_prof_ids = {professional.id for professional in professionals}
            missing_ids = add_ids - existing_prof_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uno o mas profesionales no pertenecen al tenant",
                )
            for professional in professionals:
                CRMService.ensure_professional_subject_kind_compatibility(professional, client_file)
            for professional_id in add_ids:
                db.add(
                    CRMClientFileProfessionalLink(
                        tenant_id=tenant_id,
                        client_file_id=file_id,
                        professional_id=professional_id,
                    )
                )

        await db.flush()
        mapped = await CRMService.list_professional_links_for_files(db, tenant_id, [file_id])
        return mapped.get(str(file_id), [])

    @staticmethod
    async def build_subject_timeline(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> dict:
        client_file = await CRMService.get_client_file_or_404(db, tenant_id, file_id)

        appointments_result = await db.execute(
            select(CRMAppointment).where(
                CRMAppointment.tenant_id == tenant_id,
                CRMAppointment.subject_id == file_id,
            ).order_by(CRMAppointment.starts_at.desc())
        )
        appointments = appointments_result.scalars().all()

        reports_result = await db.execute(
            select(CRMVisitReport).where(
                CRMVisitReport.tenant_id == tenant_id,
                CRMVisitReport.subject_id == file_id,
            ).order_by(CRMVisitReport.occurred_at.desc())
        )
        reports = [report for report in reports_result.scalars().all() if not CRMService.is_visit_report_archived(report)]

        timeline = []
        for appointment in appointments:
            timeline.append(
                {
                    "type": "appointment",
                    "occurred_at": appointment.starts_at.isoformat(),
                    "data": CRMService.serialize_appointment(appointment),
                }
            )

        for report in reports:
            timeline.append(
                {
                    "type": "visit_report",
                    "occurred_at": report.occurred_at.isoformat(),
                    "data": CRMService.serialize_visit_report(report),
                }
            )

        timeline.sort(key=lambda item: item["occurred_at"], reverse=True)

        linked_map = await CRMService.list_professional_links_for_files(db, tenant_id, [file_id])
        linked_professionals = linked_map.get(str(file_id), [])

        return {
            "subject": CRMService.serialize_client_file(client_file, linked_professionals=linked_professionals),
            "timeline": timeline,
        }
