import uuid

import pytest
from fastapi import HTTPException

from app.models.crm import CRMClientFile, CRMProfessional, CRMVisitReport
from app.services.crm_service import CRMService


def build_professional(role_label: str | None = None, specialty: str | None = None) -> CRMProfessional:
    return CRMProfessional(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Profesional Demo",
        role_label=role_label,
        specialty=specialty,
        calendar_color="#1d4ed8",
        active=True,
    )


def build_file(subject_kind: str) -> CRMClientFile:
    return CRMClientFile(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        subject_kind=subject_kind,
        display_name="Expediente Demo",
        status="active",
        coverage_type="particular",
    )


def test_allowed_subject_kinds_health_role_maps_to_patient_only():
    prof = build_professional(role_label="Medico", specialty="Clinica")
    allowed = CRMService.allowed_subject_kinds_for_professional(prof)
    assert allowed == {"patient"}


def test_allowed_subject_kinds_legal_role_maps_to_client_and_case():
    prof = build_professional(role_label="Abogado")
    allowed = CRMService.allowed_subject_kinds_for_professional(prof)
    assert allowed == {"client", "case"}


def test_allowed_subject_kinds_accounting_role_maps_to_client_and_company():
    prof = build_professional(role_label="Contador")
    allowed = CRMService.allowed_subject_kinds_for_professional(prof)
    assert allowed == {"client", "company"}


def test_compatibility_raises_for_incompatible_pair():
    prof = build_professional(role_label="Medico")
    file_obj = build_file(subject_kind="company")

    with pytest.raises(HTTPException) as exc_info:
        CRMService.ensure_professional_subject_kind_compatibility(prof, file_obj)

    assert exc_info.value.status_code == 400
    assert "Tipos permitidos" in str(exc_info.value.detail)


def test_compatibility_passes_for_compatible_pair():
    prof = build_professional(role_label="Abogado")
    file_obj = build_file(subject_kind="case")
    CRMService.ensure_professional_subject_kind_compatibility(prof, file_obj)


def test_normalize_file_status_defaults_to_active():
    assert CRMService.normalize_file_status(None) == "active"
    assert CRMService.normalize_file_status("unknown") == "active"


def test_is_visit_report_archived_from_extra_data_flag():
    report = CRMVisitReport(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        professional_id=uuid.uuid4(),
        occurred_at=None,
        summary="ok",
        extra_data={"archived": True},
    )
    assert CRMService.is_visit_report_archived(report) is True

    report.extra_data = {"archived": False}
    assert CRMService.is_visit_report_archived(report) is False
