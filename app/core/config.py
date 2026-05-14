from pathlib import Path
import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[2]


def _resolve_env_file() -> Path:
    app_env = os.getenv("APP_ENV", "development").lower().strip()
    if app_env == "production":
        return BASE_DIR / ".env.production"
    if app_env == "test":
        return BASE_DIR / ".env.test"
    return BASE_DIR / ".env"

class Settings(BaseSettings):
    """Application configuration with validation.
    
    Fields marked as required MUST be provided via environment variables.
    Optional fields have sensible defaults.
    """
    # ===== REQUIRED FIELDS =====
    DATABASE_URL: str
    """Database connection URL. Required in all environments."""
    
    SECRET_KEY: str
    """Secret key for JWT token generation and encryption. Required in all environments."""
    
    # ===== CORE APPLICATION SETTINGS =====
    APP_ENV: str = "development"
    """Application environment: 'development', 'test', or 'production'."""
    
    ALGORITHM: str = "HS256"
    """JWT algorithm for token generation."""
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    """Access token expiration time in minutes."""
    
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    """Refresh token expiration time in days."""
    
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    """Maximum login attempts before account lockout."""
    
    LOCKOUT_DURATION_MINUTES: int = 15
    """Account lockout duration after max failed attempts."""
    
    ALLOWED_IP: Optional[str] = None
    """Comma-separated list of allowed IP addresses (optional)."""
    
    APP_NAME: str = "QR Attendance System"
    """Application name for UI and documentation."""
    
    DEBUG: bool = False
    """Debug mode (must be False in production)."""
    
    BASE_URL: str = "http://localhost:8000"
    """Backend base URL, used by frontend for API calls."""
    
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
    """Comma-separated CORS origins."""
    
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    """Comma-separated allowed hosts for TrustedHostMiddleware."""
    
    LOG_LEVEL: str = "INFO"
    """Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL."""
    
    WORKERS: int = 2
    """Number of Uvicorn workers."""
    
    DB_POOL_SIZE: int = 5
    """Database connection pool size."""
    
    DB_MAX_OVERFLOW: int = 10
    """Database connection pool overflow size."""
    
    DB_POOL_TIMEOUT_SECONDS: int = 30
    """Database connection timeout in seconds."""
    
    DB_POOL_RECYCLE_SECONDS: int = 1800
    """Database connection recycle time in seconds."""
    
    MASTER_BOOTSTRAP_KEY: Optional[str] = None
    """Optional key for master bootstrap operations."""
    
    # ===== EMAIL SETTINGS =====
    EMAIL_NOTIFICATIONS_ENABLED: bool = False
    """Enable email notifications. If True, SMTP_* settings must be configured."""
    
    LANDING_WHATSAPP_URL: Optional[str] = None
    """WhatsApp URL for landing page."""
    
    SMTP_HOST: Optional[str] = None
    """SMTP server host (required if EMAIL_NOTIFICATIONS_ENABLED=True)."""
    
    SMTP_PORT: int = 587
    """SMTP server port."""
    
    SMTP_USERNAME: Optional[str] = None
    """SMTP username (required if EMAIL_NOTIFICATIONS_ENABLED=True)."""
    
    SMTP_PASSWORD: Optional[str] = None
    """SMTP password (required if EMAIL_NOTIFICATIONS_ENABLED=True)."""
    
    SMTP_FROM_EMAIL: Optional[str] = None
    """SMTP from email address."""
    
    SMTP_USE_TLS: bool = True
    """Use TLS for SMTP connection."""
    
    SMTP_USE_SSL: bool = False
    """Use SSL for SMTP connection."""
    
    SMTP_TIMEOUT_SECONDS: int = 15
    """SMTP connection timeout in seconds."""
    
    # ===== N8N WEBHOOK SETTINGS =====
    N8N_WEBHOOK_ENABLED: bool = False
    """Enable N8N webhook integration. If True, N8N_WEBHOOK_URL must be configured."""
    
    N8N_WEBHOOK_URL: Optional[str] = None
    """N8N webhook URL (required if N8N_WEBHOOK_ENABLED=True)."""
    
    N8N_WEBHOOK_TIMEOUT_SECONDS: int = 8
    """N8N webhook request timeout in seconds."""
    
    # ===== VALIDATORS =====
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that DATABASE_URL is provided and not empty."""
        if not v or not v.strip():
            raise ValueError("DATABASE_URL is required and cannot be empty")
        if not any(v.startswith(proto) for proto in ["postgresql://", "postgresql+asyncpg://"]):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        return v
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that SECRET_KEY is provided and has minimum length."""
        if not v or not v.strip():
            raise ValueError("SECRET_KEY is required and cannot be empty")
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long")
        return v
    
    @field_validator("DEBUG")
    @classmethod
    def validate_debug_mode(cls, v: bool, info) -> bool:
        """Validate that DEBUG is False in production."""
        if v and info.data.get("APP_ENV", "").lower() == "production":
            raise ValueError("DEBUG must be False in production environment")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that LOG_LEVEL is a valid logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = v.upper().strip()
        if level not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {v}")
        return level
    
    @model_validator(mode="after")
    def validate_email_config_dependencies(self) -> "Settings":
        """Validate cross-field dependencies for email configuration."""
        if self.EMAIL_NOTIFICATIONS_ENABLED:
            missing_fields = []
            if not self.SMTP_HOST:
                missing_fields.append("SMTP_HOST")
            if not self.SMTP_USERNAME:
                missing_fields.append("SMTP_USERNAME")
            if not self.SMTP_PASSWORD:
                missing_fields.append("SMTP_PASSWORD")
            
            if missing_fields:
                raise ValueError(
                    f"EMAIL_NOTIFICATIONS_ENABLED=true requires the following fields to be configured: {', '.join(missing_fields)}"
                )
        return self
    
    @model_validator(mode="after")
    def validate_n8n_config_dependencies(self) -> "Settings":
        """Validate cross-field dependencies for N8N webhook configuration."""
        if self.N8N_WEBHOOK_ENABLED:
            if not self.N8N_WEBHOOK_URL:
                raise ValueError(
                    "N8N_WEBHOOK_ENABLED=true requires N8N_WEBHOOK_URL to be configured"
                )
        return self

    def get_redacted_dict(self) -> dict:
        """Return config as a dict with sensitive fields redacted.
        
        Sensitive fields include:
        - SECRET_KEY
        - *_PASSWORD fields
        - DATABASE_URL
        
        Used for logging config on startup.
        """
        redacted = {}
        sensitive_keys = {"SECRET_KEY", "DATABASE_URL"}
        
        for key, value in self.__dict__.items():
            # Redact if key ends with _PASSWORD or is in sensitive_keys
            if key.endswith("_PASSWORD") or key in sensitive_keys:
                redacted[key] = "*****"
            else:
                redacted[key] = value
        
        return redacted
    
    def redact_string(self, text: str) -> str:
        """Redact sensitive values from a string.
        
        Replaces DATABASE_URL and SECRET_KEY values with ***** in log messages.
        """
        text = text.replace(self.SECRET_KEY, "*****")
        text = text.replace(self.DATABASE_URL, "*****")
        
        # Redact any SMTP password if present
        if self.SMTP_PASSWORD and self.SMTP_PASSWORD in text:
            text = text.replace(self.SMTP_PASSWORD, "*****")
        
        return text

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse ALLOWED_HOSTS into a list."""
        return [item.strip() for item in self.ALLOWED_HOSTS.split(",") if item.strip()]

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()