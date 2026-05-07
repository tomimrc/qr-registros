# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.admin import Admin
from app.core.dependencies import get_current_admin, get_current_admin_from_refresh_token
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.core.token_manager import TokenManager
from app.core.token_blacklist import TokenBlacklist
from app.utils.rate_limiter import limiter
from app.models.auth_exceptions import AuthError
from datetime import datetime, timezone

router = APIRouter()


# =============================================
# SCHEMAS (forma de los datos que entran/salen)
# =============================================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    tenant_id: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin_name: str
    tenant_id: str
    must_change_password: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# =============================================
# REGISTRO DE ADMIN
# =============================================
@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("3/1 hour")
async def register_admin(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new admin user."""
    try:
        import uuid
        tenant_id = uuid.UUID(data.tenant_id)

        # Register via AuthService
        admin = await AuthService.register(
            db=db,
            email=data.email,
            password=data.password,
            nombre=data.nombre,
            tenant_id=tenant_id,
        )

        # Create tokens
        access_token = TokenManager.create_access_token(
            sub=str(admin.id),
            tenant_id=str(admin.tenant_id),
        )
        refresh_token = TokenManager.create_refresh_token(
            sub=str(admin.id),
            tenant_id=str(admin.tenant_id),
        )

        # Log registration success
        ip_address = getattr(request.state, "ip_address", None)
        user_agent = getattr(request.state, "user_agent", None)
        await AuditService.log_event(
            db=db,
            tenant_id=admin.tenant_id,
            event_type="admin_registered",
            admin_id=admin.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": admin.email},
            success=True,
        )
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            admin_name=admin.nombre,
            tenant_id=str(admin.tenant_id),
            must_change_password=admin.must_change_password,
        )

    except AuthError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# =============================================
# LOGIN
# =============================================
@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/15 minutes")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate admin and issue access/refresh tokens."""
    import uuid
    
    ip_address = getattr(request.state, "ip_address", None)
    user_agent = getattr(request.state, "user_agent", None)

    try:
        # Find admin by email to check lockout status
        from sqlalchemy import select
        from app.models.admin import Admin as AdminModel
        
        result = await db.execute(
            select(AdminModel).where(AdminModel.email == form_data.username)
        )
        admin = result.scalar_one_or_none()

        # Check account lockout
        if admin and admin.locked_until:
            if datetime.now(timezone.utc) < admin.locked_until:
                locked_until_str = admin.locked_until.isoformat()
                await AuditService.log_login_failed(
                    db=db,
                    tenant_id=admin.tenant_id if admin else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    email=form_data.username,
                    reason="account_locked",
                )
                await db.commit()
                raise HTTPException(
                    status_code=429,
                    detail=f"Cuenta bloqueada. Intenta de nuevo después de {locked_until_str}",
                )

        # Verify credentials via AuthService
        admin = await AuthService.verify_credentials(
            db=db,
            email=form_data.username,
            password=form_data.password,
        )

        # Reset failed login attempts on success
        await AuthService.on_successful_login(db=db, admin=admin)

        # Create tokens
        access_token = TokenManager.create_access_token(
            sub=str(admin.id),
            tenant_id=str(admin.tenant_id),
        )
        refresh_token = TokenManager.create_refresh_token(
            sub=str(admin.id),
            tenant_id=str(admin.tenant_id),
        )

        # Log successful login
        await AuditService.log_login_success(
            db=db,
            tenant_id=admin.tenant_id,
            admin_id=admin.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            admin_name=admin.nombre,
            tenant_id=str(admin.tenant_id),
            must_change_password=admin.must_change_password,
        )

    except AuthError as e:
        # Log failed login
        tenant_id = None
        try:
            from sqlalchemy import select
            from app.models.admin import Admin as AdminModel
            
            result = await db.execute(
                select(AdminModel).where(AdminModel.email == form_data.username)
            )
            admin = result.scalar_one_or_none()
            if admin:
                tenant_id = admin.tenant_id
                # Increment failed login attempts
                await AuthService.on_failed_login(db=db, admin=admin, email=form_data.username)
                
                # Log failed login only if we have a valid admin/tenant
                await AuditService.log_login_failed(
                    db=db,
                    tenant_id=tenant_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    email=form_data.username,
                    reason="invalid_credentials",
                )
        except Exception:
            pass

        # Only commit if we logged something
        if tenant_id:
            await db.commit()
        else:
            await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")


# =============================================
# TOKEN REFRESH
# =============================================
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    admin: Admin = Depends(get_current_admin_from_refresh_token),
    db: AsyncSession = Depends(get_db),
):
    """Issue new access and refresh tokens using valid refresh token."""
    try:
        # Create new tokens
        access_token = TokenManager.create_access_token(
            sub=str(admin.id),
            tenant_id=str(admin.tenant_id),
        )
        refresh_token = TokenManager.create_refresh_token(
            sub=str(admin.id),
            tenant_id=str(admin.tenant_id),
        )

        # Log token refresh
        ip_address = getattr(request.state, "ip_address", None)
        user_agent = getattr(request.state, "user_agent", None)
        await AuditService.log_token_refreshed(
            db=db,
            tenant_id=admin.tenant_id,
            admin_id=admin.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            admin_name=admin.nombre,
            tenant_id=str(admin.tenant_id),
            must_change_password=admin.must_change_password,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error refrescando token")


# =============================================
# LOGOUT
# =============================================
@router.post("/logout")
async def logout(
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Logout by revoking the current token."""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
            # Get token expiration and add to blacklist
            from app.core.token_manager import TokenManager
            
            payload = TokenManager.decode_token(token)
            if payload:
                token_jti = payload.get("jti")
                exp_timestamp = payload.get("exp", 0)
                
                if token_jti:
                    await TokenBlacklist.add(token_jti, exp_timestamp)

        # Log logout
        ip_address = getattr(request.state, "ip_address", None)
        user_agent = getattr(request.state, "user_agent", None)
        await AuditService.log_logout(
            db=db,
            tenant_id=admin.tenant_id,
            admin_id=admin.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()

        return {"ok": True, "message": "Logged out successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error en logout")


# =============================================
# PROTECTED ENDPOINTS
# =============================================
@router.get("/me")
async def get_me(admin: Admin = Depends(get_current_admin)):
    """Get current admin info."""
    return {
        "id": str(admin.id),
        "email": admin.email,
        "nombre": admin.nombre,
        "tenant_id": str(admin.tenant_id),
        "must_change_password": admin.must_change_password,
    }


@router.post("/change-password")
@limiter.limit("10/1 hour")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change password with validation."""
    try:
        # Change password via AuthService
        await AuthService.change_password(
            db=db,
            admin=admin,
            old_password=payload.current_password,
            new_password=payload.new_password,
        )

        # Log password change
        ip_address = getattr(request.state, "ip_address", None)
        user_agent = getattr(request.state, "user_agent", None)
        await AuditService.log_password_changed(
            db=db,
            tenant_id=admin.tenant_id,
            admin_id=admin.id,
            changed_by="self",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()

        return {"ok": True, "message": "Contraseña cambiada exitosamente"}

    except AuthError as e:
        await db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
