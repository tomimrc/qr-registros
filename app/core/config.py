from pathlib import Path
import os

from pydantic_settings import BaseSettings, SettingsConfigDict
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
    DATABASE_URL: str
    SECRET_KEY: str
    APP_ENV: str = "development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    ALLOWED_IP: Optional[str] = None
    APP_NAME: str = "QR Attendance System"
    DEBUG: bool = False
    BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    LOG_LEVEL: str = "INFO"
    WORKERS: int = 2
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    MASTER_BOOTSTRAP_KEY: Optional[str] = None
    EMAIL_NOTIFICATIONS_ENABLED: bool = False
    LANDING_WHATSAPP_URL: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 15
    N8N_WEBHOOK_ENABLED: bool = False
    N8N_WEBHOOK_URL: Optional[str] = None
    N8N_WEBHOOK_TIMEOUT_SECONDS: int = 8

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [item.strip() for item in self.ALLOWED_HOSTS.split(",") if item.strip()]

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()