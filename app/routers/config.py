"""Configuration API router.

Exposes a public endpoint that returns safe, non-sensitive configuration
to frontend clients.
"""

from fastapi import APIRouter, Response
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/api/config", tags=["Configuration"])


class ConfigResponse(BaseModel):
    """Public configuration response model.
    
    Only includes non-sensitive configuration that should be exposed to the frontend.
    Never includes: SECRET_KEY, DATABASE_URL, SMTP_PASSWORD, or other credentials.
    """
    api_base_url: str
    app_name: str
    debug: bool
    log_level: str
    features: dict


@router.get("/", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Get public configuration for frontend clients.
    
    This endpoint is unauthenticated and returns only safe configuration values.
    Sensitive values like SECRET_KEY, database credentials, and API keys are NEVER exposed.
    
    Returns:
        ConfigResponse: Public configuration data
    """
    return ConfigResponse(
        api_base_url=settings.BASE_URL,
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
        features={
            "email_notifications": settings.EMAIL_NOTIFICATIONS_ENABLED,
            "n8n_webhooks": settings.N8N_WEBHOOK_ENABLED,
        },
    )
