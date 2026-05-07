import secrets
import string
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
import os
import re
import json
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_super_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.models.tenant_feature import TenantFeature
from app.services.email_service import send_client_credentials_email
from app.services.audit_service import AuditService

router = APIRouter()
logger = logging.getLogger(__name__)

FEATURE_QR_ATTENDANCE = "qr_attendance"
FEATURE_SALES_ANALYTICS = "sales_analytics"
FEATURE_CRM_CORE = "crm_core"
ALLOWED_FEATURES = {FEATURE_QR_ATTENDANCE, FEATURE_SALES_ANALYTICS, FEATURE_CRM_CORE}
DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"


def _resolve_runtime_module_flags() -> dict[str, bool]:
    profile = (settings.MODULE_PROFILE or "custom").strip().lower()
    if profile == "full":
        return {"crm": True, "booking": True, "sales": True, "qr": True}
    if profile == "booking":
        return {"crm": True, "booking": True, "sales": False, "qr": False}
    if profile == "crm":
        return {"crm": True, "booking": False, "sales": False, "qr": False}
    if profile == "sales":
        return {"crm": False, "booking": False, "sales": True, "qr": False}
    if profile == "qr":
        return {"crm": False, "booking": False, "sales": False, "qr": True}

    return {
        "crm": settings.MODULE_CRM_ENABLED,
        "booking": settings.MODULE_BOOKING_ENABLED,
        "sales": settings.MODULE_SALES_ENABLED,
        "qr": settings.MODULE_QR_ENABLED,
    }


def _validate_runtime_module_configuration(enabled_booking: bool) -> list[str]:
    issues: list[str] = []
    if enabled_booking and not settings.BOOKING_PUBLIC_BASE_URL:
        issues.append("BOOKING_PUBLIC_BASE_URL no esta configurada y booking esta habilitado")

    oauth_id = bool(settings.GOOGLE_OAUTH_CLIENT_ID)
    oauth_redirect = bool(settings.GOOGLE_OAUTH_REDIRECT_URI)
    if enabled_booking and oauth_id != oauth_redirect:
        issues.append(
            "Google OAuth incompleto para booking: define ambas GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_REDIRECT_URI"
        )

    return issues


class SuperAdminBootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombre: str = Field(min_length=2, max_length=100)
    bootstrap_key: str


class SuperAdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    super_admin_name: str


class MasterClientCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)
    email: EmailStr
    admin_nombre: str = Field(min_length=2, max_length=100)
    timezone: str = Field(default=DEFAULT_TIMEZONE, max_length=100)
    feature_codes: list[str] = Field(default_factory=list)
    feature_months: int = Field(default=1, ge=1, le=120)


class MasterClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)


class FeatureActivationRequest(BaseModel):
    months: int = Field(default=1, ge=1, le=120)


class ClientAdminUpdateRequest(BaseModel):
    email: EmailStr | None = None
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None


class ResetAdminPasswordResponse(BaseModel):
    temporary_password: str
    email_sent: bool


def _normalize_slug(raw_slug: str) -> str:
    slug = raw_slug.strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _generate_temporary_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "@#_$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _resolve_primary_admin(db: AsyncSession, tenant_id: uuid.UUID) -> Admin | None:
    result = await db.execute(
        select(Admin)
        .where(Admin.tenant_id == tenant_id)
        .order_by(Admin.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _activate_feature(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    feature_code: str,
    months: int,
) -> TenantFeature:
    if feature_code not in ALLOWED_FEATURES:
        raise HTTPException(status_code=400, detail=f"Feature {feature_code} no permitida")

    today = date.today()
    result = await db.execute(
        select(TenantFeature).where(
            TenantFeature.tenant_id == tenant_id,
            TenantFeature.feature_code == feature_code,
        )
    )
    feature = result.scalar_one_or_none()

    if feature is None:
        feature = TenantFeature(
            tenant_id=tenant_id,
            feature_code=feature_code,
            active=True,
            period_start=today,
            period_end=today + timedelta(days=30 * months),
        )
        db.add(feature)
        await db.flush()
        return feature

    base_end = feature.period_end if feature.period_end >= today else today
    feature.active = True
    feature.period_start = feature.period_start if feature.period_start <= today else today
    feature.period_end = base_end + timedelta(days=30 * months)
    await db.flush()
    return feature


async def _deactivate_feature(db: AsyncSession, tenant_id: uuid.UUID, feature_code: str) -> TenantFeature:
    result = await db.execute(
        select(TenantFeature).where(
            TenantFeature.tenant_id == tenant_id,
            TenantFeature.feature_code == feature_code,
        )
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature no encontrada para este cliente")

    feature.active = False
    await db.flush()
    return feature


def _resolve_bootstrap_key() -> str | None:
    key = settings.MASTER_BOOTSTRAP_KEY or os.getenv("MASTER_BOOTSTRAP_KEY")

    if key is None:
        return None
    stripped = key.strip()
    return stripped or None


def _parse_bootstrap_payload(payload: dict) -> tuple[str, str, str, str]:
    nombre = str(payload.get("nombre", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    bootstrap_key = str(payload.get("bootstrap_key", "")).strip()

    if settings.DEBUG:
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        if not email:
            raise HTTPException(status_code=400, detail="Email requerido")
        if not password:
            raise HTTPException(status_code=400, detail="Password requerida")
    else:
        if len(nombre) < 2:
            raise HTTPException(status_code=400, detail="Nombre inválido (mínimo 2 caracteres)")
        if "@" not in email:
            raise HTTPException(status_code=400, detail="Email inválido")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password inválida (mínimo 8 caracteres)")

    if not bootstrap_key:
        raise HTTPException(status_code=400, detail="Bootstrap key requerida")

    return nombre, email, password, bootstrap_key


@router.post("/auth/bootstrap", response_model=SuperAdminTokenResponse)
async def bootstrap_super_admin(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    nombre, email, password, provided_bootstrap_key = _parse_bootstrap_payload(payload)

    bootstrap_key = _resolve_bootstrap_key()

    # Fallback solo para desarrollo: evita bloquear bootstrap cuando la carga
    # de entorno del proceso no refleja el .env local.
    if not bootstrap_key and settings.DEBUG:
        bootstrap_key = provided_bootstrap_key or None

    if not bootstrap_key:
        raise HTTPException(
            status_code=403,
            detail="Bootstrap deshabilitado. Configura MASTER_BOOTSTRAP_KEY en entorno.",
        )

    if provided_bootstrap_key != bootstrap_key:
        raise HTTPException(status_code=401, detail="Bootstrap key inválida")

    existing = await db.execute(select(SuperAdmin).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe al menos un super admin")

    super_admin = SuperAdmin(
        email=email,
        hashed_password=hash_password(password),
        nombre=nombre,
        is_active=True,
    )
    db.add(super_admin)
    await db.flush()

    await AuditService.log_event(
        db=db,
        action="bootstrap_super_admin",
        actor_type="system",
        actor_id=None,
        target_type="super_admin",
        target_id=super_admin.id,
        details={"email": super_admin.email},
    )

    token = create_access_token({"sub": str(super_admin.id), "principal_type": "super_admin"})
    return SuperAdminTokenResponse(access_token=token, super_admin_name=super_admin.nombre)


@router.post("/auth/login", response_model=SuperAdminTokenResponse)
async def login_super_admin(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SuperAdmin).where(SuperAdmin.email == form_data.username.lower().strip()))
    super_admin = result.scalar_one_or_none()

    if not super_admin or not verify_password(form_data.password, super_admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos")

    if not super_admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta desactivada")

    super_admin.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token({"sub": str(super_admin.id), "principal_type": "super_admin"})
    return SuperAdminTokenResponse(access_token=token, super_admin_name=super_admin.nombre)


@router.get("/auth/me")
async def get_super_admin_me(
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return {
        "id": str(super_admin.id),
        "email": super_admin.email,
        "nombre": super_admin.nombre,
        "is_active": super_admin.is_active,
        "last_login_at": super_admin.last_login_at.isoformat() if super_admin.last_login_at else None,
    }


@router.get("/runtime/modules")
async def get_runtime_modules(
    _: SuperAdmin = Depends(get_current_super_admin),
):
    flags = _resolve_runtime_module_flags()
    issues = _validate_runtime_module_configuration(enabled_booking=flags["booking"])

    return {
        "profile": settings.MODULE_PROFILE,
        "strict_validation": settings.MODULE_STRICT_VALIDATION,
        "modules": flags,
        "issues": issues,
        "is_valid": len(issues) == 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/clients", status_code=201)
async def create_client_with_admin(
    payload: MasterClientCreateRequest,
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    slug = _normalize_slug(payload.slug)
    if not slug:
        raise HTTPException(status_code=400, detail="Slug inválido")

    slug_exists = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if slug_exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Slug ya existente")

    email = payload.email.lower().strip()
    admin_exists = await db.execute(select(Admin).where(Admin.email == email))
    if admin_exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email de admin ya en uso")

    temporary_password = _generate_temporary_password()

    tenant = Tenant(
        name=payload.name.strip(),
        slug=slug,
        timezone=payload.timezone.strip() or DEFAULT_TIMEZONE,
        is_active=True,
    )
    db.add(tenant)
    await db.flush()

    admin = Admin(
        tenant_id=tenant.id,
        email=email,
        hashed_password=hash_password(temporary_password),
        nombre=payload.admin_nombre.strip(),
        is_active=True,
        must_change_password=True,
    )
    db.add(admin)
    await db.flush()

    created_features: list[dict] = []
    for feature_code in set(payload.feature_codes):
        feature = await _activate_feature(
            db=db,
            tenant_id=tenant.id,
            feature_code=feature_code,
            months=payload.feature_months,
        )
        created_features.append(
            {
                "feature_code": feature.feature_code,
                "active": feature.active,
                "period_start": feature.period_start.isoformat(),
                "period_end": feature.period_end.isoformat(),
            }
        )

    await AuditService.log_event(
        db=db,
        action="client_created",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="tenant",
        target_id=tenant.id,
        tenant_id=tenant.id,
        details={
            "tenant_name": tenant.name,
            "tenant_slug": tenant.slug,
            "admin_email": admin.email,
            "feature_codes": sorted(set(payload.feature_codes)),
        },
    )

    email_sent = False
    email_error: str | None = None
    if settings.EMAIL_NOTIFICATIONS_ENABLED:
        dashboard_url = f"{settings.BASE_URL.rstrip('/')}/dashboard"
        try:
            await asyncio.to_thread(
                send_client_credentials_email,
                recipient_email=admin.email,
                client_name=tenant.name,
                admin_name=admin.nombre,
                temporary_password=temporary_password,
                dashboard_url=dashboard_url,
                login_email=admin.email,
            )
            email_sent = True
        except Exception as exc:
            email_error = str(exc)
            logger.exception("Failed to send client credentials email", extra={"tenant_id": str(tenant.id), "admin_email": admin.email})

    return {
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "timezone": tenant.timezone,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        },
        "admin": {
            "id": str(admin.id),
            "nombre": admin.nombre,
            "email": admin.email,
            "must_change_password": admin.must_change_password,
            "created_at": admin.created_at.isoformat() if admin.created_at else None,
        },
        "features": created_features,
        "temporary_password": temporary_password,
        "email_sent": email_sent,
        "email_error": email_error,
        "email_notifications_enabled": settings.EMAIL_NOTIFICATIONS_ENABLED,
    }

@router.get("/clients")
async def list_clients(
    q: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Tenant)

    if is_active is not None:
        query = query.where(Tenant.is_active == is_active)

    if q:
        q_like = f"%{q.lower().strip()}%"
        query = query.where(
            or_(
                func.lower(Tenant.name).like(q_like),
                func.lower(Tenant.slug).like(q_like),
                Tenant.id.in_(
                    select(Admin.tenant_id).where(func.lower(Admin.email).like(q_like))
                ),
            )
        )

    result = await db.execute(query.order_by(Tenant.created_at.desc()).limit(limit).offset(offset))
    tenants = result.scalars().all()

    items = []
    for tenant in tenants:
        primary_admin = await _resolve_primary_admin(db, tenant.id)
        feature_result = await db.execute(
            select(TenantFeature).where(TenantFeature.tenant_id == tenant.id).order_by(TenantFeature.feature_code)
        )
        features = feature_result.scalars().all()

        items.append(
            {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "timezone": tenant.timezone,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                "primary_admin_email": primary_admin.email if primary_admin else None,
                "features": [
                    {
                        "feature_code": feature.feature_code,
                        "active": feature.active,
                        "period_start": feature.period_start.isoformat(),
                        "period_end": feature.period_end.isoformat(),
                    }
                    for feature in features
                ],
            }
        )

    return {"items": items, "limit": limit, "offset": offset}


@router.get("/clients/{tenant_id}")
async def get_client_detail(
    tenant_id: uuid.UUID,
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    admin = await _resolve_primary_admin(db, tenant.id)
    feature_result = await db.execute(
        select(TenantFeature).where(TenantFeature.tenant_id == tenant.id).order_by(TenantFeature.feature_code)
    )
    features = feature_result.scalars().all()

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "timezone": tenant.timezone,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "admin": {
            "id": str(admin.id) if admin else None,
            "email": admin.email if admin else None,
            "nombre": admin.nombre if admin else None,
            "is_active": admin.is_active if admin else None,
            "must_change_password": admin.must_change_password if admin else None,
            "created_at": admin.created_at.isoformat() if admin and admin.created_at else None,
        },
        "features": [
            {
                "feature_code": feature.feature_code,
                "active": feature.active,
                "period_start": feature.period_start.isoformat(),
                "period_end": feature.period_end.isoformat(),
            }
            for feature in features
        ],
    }


@router.patch("/clients/{tenant_id}")
async def update_client(
    tenant_id: uuid.UUID,
    payload: MasterClientUpdateRequest,
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    before = {"name": tenant.name, "slug": tenant.slug, "timezone": tenant.timezone}

    if payload.name is not None:
        tenant.name = payload.name.strip()

    if payload.slug is not None:
        normalized_slug = _normalize_slug(payload.slug)
        if not normalized_slug:
            raise HTTPException(status_code=400, detail="Slug inválido")

        slug_exists = await db.execute(
            select(Tenant).where(Tenant.slug == normalized_slug, Tenant.id != tenant.id)
        )
        if slug_exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Slug ya existente")

        tenant.slug = normalized_slug

    if payload.timezone is not None:
        tenant.timezone = payload.timezone.strip() or DEFAULT_TIMEZONE

    await db.flush()

    await AuditService.log_event(
        db=db,
        action="client_updated",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="tenant",
        target_id=tenant.id,
        tenant_id=tenant.id,
        details={
            "before": before,
            "after": {
                "name": tenant.name,
                "slug": tenant.slug,
                "timezone": tenant.timezone,
            },
        },
    )

    return {"ok": True}


@router.post("/clients/{tenant_id}/status")
async def set_client_status(
    tenant_id: uuid.UUID,
    is_active: bool = Query(...),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    tenant.is_active = is_active

    result = await db.execute(select(Admin).where(Admin.tenant_id == tenant_id))
    admins = result.scalars().all()
    for admin in admins:
        admin.is_active = is_active

    await db.flush()

    await AuditService.log_event(
        db=db,
        action="client_status_changed",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="tenant",
        target_id=tenant.id,
        tenant_id=tenant.id,
        details={"is_active": is_active},
    )

    return {"ok": True, "is_active": tenant.is_active}


@router.post("/clients/{tenant_id}/features/{feature_code}/activate")
async def activate_feature(
    tenant_id: uuid.UUID,
    feature_code: str,
    payload: FeatureActivationRequest,
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    feature = await _activate_feature(
        db=db,
        tenant_id=tenant_id,
        feature_code=feature_code,
        months=payload.months,
    )

    await AuditService.log_event(
        db=db,
        action="feature_activated",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="tenant_feature",
        target_id=feature.id,
        tenant_id=tenant_id,
        details={
            "feature_code": feature.feature_code,
            "months": payload.months,
            "period_start": feature.period_start.isoformat(),
            "period_end": feature.period_end.isoformat(),
        },
    )

    return {
        "ok": True,
        "feature": {
            "feature_code": feature.feature_code,
            "active": feature.active,
            "period_start": feature.period_start.isoformat(),
            "period_end": feature.period_end.isoformat(),
        },
    }


@router.post("/clients/{tenant_id}/features/{feature_code}/deactivate")
async def deactivate_feature(
    tenant_id: uuid.UUID,
    feature_code: str,
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    feature = await _deactivate_feature(db=db, tenant_id=tenant_id, feature_code=feature_code)

    await AuditService.log_event(
        db=db,
        action="feature_deactivated",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="tenant_feature",
        target_id=feature.id,
        tenant_id=tenant_id,
        details={"feature_code": feature.feature_code},
    )

    return {"ok": True}


@router.post("/clients/{tenant_id}/admin/reset-password", response_model=ResetAdminPasswordResponse)
async def reset_client_admin_password(
    tenant_id: uuid.UUID,
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    admin = await _resolve_primary_admin(db, tenant_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin del cliente no encontrado")

    temporary_password = _generate_temporary_password()
    admin.hashed_password = hash_password(temporary_password)
    admin.must_change_password = True
    admin.password_changed_at = None

    await db.flush()

    await AuditService.log_event(
        db=db,
        action="client_admin_password_reset",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="admin",
        target_id=admin.id,
        tenant_id=tenant_id,
        details={"admin_email": admin.email},
    )

    return ResetAdminPasswordResponse(
        temporary_password=temporary_password,
        email_sent=False,
    )


@router.patch("/clients/{tenant_id}/admin")
async def update_client_admin(
    tenant_id: uuid.UUID,
    payload: ClientAdminUpdateRequest,
    super_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    admin = await _resolve_primary_admin(db, tenant_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin del cliente no encontrado")

    before = {
        "email": admin.email,
        "nombre": admin.nombre,
        "is_active": admin.is_active,
    }

    if payload.email is not None:
        new_email = payload.email.lower().strip()
        existing = await db.execute(
            select(Admin).where(Admin.email == new_email, Admin.id != admin.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email de admin ya en uso")
        admin.email = new_email

    if payload.nombre is not None:
        admin.nombre = payload.nombre.strip()

    if payload.is_active is not None:
        admin.is_active = payload.is_active

    await db.flush()

    await AuditService.log_event(
        db=db,
        action="client_admin_updated",
        actor_type="super_admin",
        actor_id=super_admin.id,
        target_type="admin",
        target_id=admin.id,
        tenant_id=tenant_id,
        details={
            "before": before,
            "after": {
                "email": admin.email,
                "nombre": admin.nombre,
                "is_active": admin.is_active,
            },
        },
    )

    return {"ok": True}


@router.get("/clients/{tenant_id}/audit")
async def get_client_audit(
    tenant_id: uuid.UUID,
    limit: int = Query(30, ge=1, le=200),
    _: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    events = []
    for row in rows:
        details = None
        if row.details_json:
            try:
                details = json.loads(row.details_json)
            except Exception:
                details = {"raw": row.details_json}

        events.append(
            {
                "id": str(row.id),
                "action": row.action,
                "actor_type": row.actor_type,
                "actor_id": str(row.actor_id) if row.actor_id else None,
                "target_type": row.target_type,
                "target_id": str(row.target_id) if row.target_id else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "details": details,
            }
        )

    return {"items": events}
