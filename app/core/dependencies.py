from collections.abc import Callable
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.admin import Admin
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.services.feature_service import FeatureService

# Token de admins de cliente
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Token de super admins
super_admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/master/auth/login")
# Token de refresh
refresh_token_scheme = OAuth2PasswordBearer(tokenUrl="/auth/refresh")


async def get_current_admin(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check token blacklist
    from app.core.token_manager import TokenManager
    from app.core.token_blacklist import TokenBlacklist
    
    payload = TokenManager.decode_token(token)
    if not payload:
        raise credentials_exception

    # Check if token is blacklisted
    token_jti = payload.get("jti")
    if token_jti:
        is_blacklisted = await TokenBlacklist.is_blacklisted(token_jti)
        if is_blacklisted:
            raise credentials_exception

    admin_id = payload.get("sub")
    if not admin_id:
        raise credentials_exception

    admin = await db.get(Admin, uuid.UUID(admin_id))
    if not admin or not admin.is_active:
        raise credentials_exception

    tenant = await db.get(Tenant, admin.tenant_id)
    if not tenant or not tenant.is_active:
        raise credentials_exception

    allowed_paths = {"/auth/me", "/auth/change-password"}
    if admin.must_change_password and request.url.path not in allowed_paths:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes cambiar tu contraseña temporal antes de continuar",
            headers={"X-Password-Change-Required": "true"},
        )

    return admin


async def get_current_super_admin(
    token: str = Depends(super_admin_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> SuperAdmin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    if payload.get("principal_type") != "super_admin":
        raise credentials_exception

    super_admin_id = payload.get("sub")
    if not super_admin_id:
        raise credentials_exception

    super_admin = await db.get(SuperAdmin, uuid.UUID(super_admin_id))
    if not super_admin or not super_admin.is_active:
        raise credentials_exception

    return super_admin


def require_feature_access(feature_code: str) -> Callable:
    async def _dependency(
        admin: Admin = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
    ) -> Admin:
        has_access = await FeatureService.has_active_feature_access(
            db=db,
            tenant_id=admin.tenant_id,
            feature_code=feature_code,
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature {feature_code} no está habilitada para este tenant",
            )
        return admin

    return _dependency


async def require_sales_analytics_access(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    has_access = await FeatureService.has_active_feature_access(
        db=db,
        tenant_id=admin.tenant_id,
        feature_code="sales_analytics",
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sales Analytics no está habilitado para este tenant. Contáctate con soporte.",
        )

    return admin


async def get_current_admin_from_refresh_token(
    token: str = Depends(refresh_token_scheme),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """
    Validate refresh token and return admin.
    Used by /auth/refresh endpoint.
    """
    from app.core.token_manager import TokenManager
    from app.models.auth_exceptions import TokenExpiredError, InvalidTokenTypeError
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = TokenManager.verify_refresh_token(token)
    except (TokenExpiredError, InvalidTokenTypeError):
        raise credentials_exception
    except Exception:
        raise credentials_exception

    admin_id = payload.get("sub")
    if not admin_id:
        raise credentials_exception

    admin = await db.get(Admin, uuid.UUID(admin_id))
    if not admin or not admin.is_active:
        raise credentials_exception

    tenant = await db.get(Tenant, admin.tenant_id)
    if not tenant or not tenant.is_active:
        raise credentials_exception

    return admin
