"""Configuration bootstrap module.

Handles initialization and validation of application configuration on startup.
"""

import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_and_log_config() -> None:
    """Validate and log application configuration on startup.
    
    This function is called during FastAPI lifespan startup and:
    1. Validates that all required config is present (done by Pydantic)
    2. Logs successful config validation
    3. Redacts sensitive values in logs
    
    Raises:
        ValidationError: If config validation fails (from Pydantic)
    """
    try:
        # At this point, settings is already instantiated and validated by Pydantic
        # If we reach here, all validators have passed
        
        redacted_config = settings.get_redacted_dict()
        
        # Log successful validation
        logger.info("=" * 80)
        logger.info("Config validation passed during startup")
        logger.info("-" * 80)
        logger.info(f"APP_ENV: {settings.APP_ENV}")
        logger.info(f"APP_NAME: {settings.APP_NAME}")
        logger.info(f"DEBUG: {settings.DEBUG}")
        logger.info(f"BASE_URL: {settings.BASE_URL}")
        logger.info(f"LOG_LEVEL: {settings.LOG_LEVEL}")
        logger.info(f"DATABASE_URL: {redacted_config['DATABASE_URL']}")
        logger.info(f"CORS_ORIGINS: {settings.CORS_ORIGINS}")
        logger.info(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        logger.info(f"EMAIL_NOTIFICATIONS_ENABLED: {settings.EMAIL_NOTIFICATIONS_ENABLED}")
        logger.info(f"N8N_WEBHOOK_ENABLED: {settings.N8N_WEBHOOK_ENABLED}")
        logger.info("=" * 80)
        
    except Exception as exc:
        logger.error(f"Config validation failed: {exc}")
        raise
