# app/main.py

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote_plus
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text
from fastapi.responses import FileResponse, HTMLResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.bootstrap import validate_and_log_config
from app.database import engine, Base
from app.middleware.auth_middleware import AuthMiddleware

# === Importación de Routers (Limpios) ===
from app.routers import auth as auth_router
from app.routers import admin as admin_router
from app.routers import attendance as attendance_router
from app.routers import devices as devices_router
from app.routers import sales as sales_router
from app.routers import master as master_router
from app.routers import crm as crm_router
from app.routers import config as config_router

# === Import Modelos (Para que Alembic / create_all los detecte) ===
from app.models import (
    admin,
    tenant,
    employee,
    device,
    attendance,
    jornada,
    subscription,
    sales,
    super_admin,
    tenant_feature,
    audit_log,
    crm,
    auth_audit_log,
    admin_password_history,
)  # noqa: F401


def _serve_first_existing_file(*candidate_paths: str) -> FileResponse:
    for candidate_path in candidate_paths:
        if Path(candidate_path).exists():
            return FileResponse(candidate_path)
    raise FileNotFoundError(f"No se encontró ningún archivo entre: {', '.join(candidate_paths)}")


def _configure_logging() -> None:
    level_name = settings.LOG_LEVEL.upper().strip()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


_configure_logging()
logger = logging.getLogger(__name__)


async def _ensure_debug_schema_compatibility() -> None:
    """Aplica cambios mínimos de esquema en desarrollo para columnas nuevas."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) NOT NULL DEFAULT 'America/Argentina/Buenos_Aires'"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE admins ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE admins ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE admins ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE admins ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL"
            )
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate and log config on startup (before any database operations)
    validate_and_log_config()
    
    # En desarrollo, crea las tablas automáticamente si no existen
    if settings.DEBUG:
        await _ensure_debug_schema_compatibility()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Sistema de asistencia SaaS Multi-Tenant",
    lifespan=lifespan,
)

# === Initialize Rate Limiter ===
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    from fastapi import HTTPException
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later.",
    )

# === Middlewares ===
# Add auth middleware first to extract IP and user agent
app.add_middleware(AuthMiddleware)
cors_origins = settings.cors_origins_list
if settings.DEBUG and not cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

allowed_hosts = settings.allowed_hosts_list
if settings.is_production and allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# === Inclusión de Routers (Sin duplicados) ===
app.include_router(config_router.router)
app.include_router(auth_router.router, prefix="/auth", tags=["Autenticación"])
app.include_router(admin_router.router, prefix="/admin", tags=["Dashboard"])
app.include_router(attendance_router.router, prefix="/attendance", tags=["Asistencia"])
app.include_router(devices_router.router, prefix="/devices", tags=["Dispositivos"])
app.include_router(sales_router.router, prefix="/sales", tags=["Ventas"])
app.include_router(master_router.router, prefix="/master", tags=["Master"])
app.include_router(crm_router.router, tags=["CRM"])

# === Endpoints Globales / Frontend ===
@app.get("/", tags=["Health"])
async def root():
    landing_path = "app/frontend/landing.html"
    with open(landing_path, "r", encoding="utf-8") as landing_file:
        landing_html = landing_file.read()

    whatsapp_url = settings.LANDING_WHATSAPP_URL or (
        "https://wa.me/?text="
        + quote_plus("Hola, quiero una demo del sistema de asistencia y ventas de Agenciakaff.")
    )
    landing_html = landing_html.replace("__WHATSAPP_URL__", whatsapp_url)

    return HTMLResponse(content=landing_html)

@app.get("/sales-dashboard", tags=["Frontend"])
async def serve_sales_dashboard():
    return _serve_first_existing_file("app/frontend/sales.html", "app/sales.html")

@app.get("/dashboard", tags=["Frontend"])
async def serve_dashboard():
    return _serve_first_existing_file("app/frontend/dashboard.html", "app/dashboard.html")

@app.get("/qr-display", tags=["Frontend"])
async def serve_qr_display():
    return _serve_first_existing_file("app/frontend/qr-display.html", "app/qr-display.html")

@app.get("/crm", tags=["Frontend"])
async def serve_crm():
    return _serve_first_existing_file("app/frontend/crm.html", "app/crm.html")

@app.get("/master-dashboard", tags=["Frontend"])
async def serve_master_dashboard():
    return _serve_first_existing_file("app/frontend/master-dashboard.html", "app/master-dashboard.html")

@app.get("/app", tags=["Frontend"])
async def serve_frontend():
    return _serve_first_existing_file("app/frontend/index.html", "app/index.html")

@app.get("/health", tags=["Health"])
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.exception("Health check failed")
        if settings.DEBUG:
            return {"status": "error", "database": str(exc)}
        return {"status": "error", "database": "unavailable"}