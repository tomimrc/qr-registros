"""Unit tests for configuration validation.

Tests the Settings class validators and configuration bootstrap.
"""

import os
import pytest
from pydantic import ValidationError

# Use environment variables only for tests, override .env file
os.environ['_ENVFILE'] = '/dev/null'

from app.core.config import Settings


@pytest.fixture
def clean_env(monkeypatch):
    """Fixture to clean environment and use only what we set."""
    # Save original env
    original_env = dict(os.environ)
    
    # Clear all app-related env vars
    for key in list(os.environ.keys()):
        if key in [
            "DATABASE_URL", "SECRET_KEY", "APP_ENV", "DEBUG", "LOG_LEVEL",
            "EMAIL_NOTIFICATIONS_ENABLED", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
            "N8N_WEBHOOK_ENABLED", "N8N_WEBHOOK_URL"
        ]:
            monkeypatch.delenv(key, raising=False)
    
    yield
    
    # Restore original env
    for key, value in original_env.items():
        os.environ[key] = value


class TestSettingsValidation:
    """Test Settings class validator."""

    def test_required_fields_present(self, clean_env, monkeypatch):
        """Test that required fields must be present."""
        # Set only required fields
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        
        # Bypass loading .env file
        monkeypatch.setenv("_ENVFILE", "/nonexistent")
        
        settings = Settings(_env_file="/nonexistent")
        assert settings.DATABASE_URL == "postgresql://user:pass@localhost/db"
        assert settings.SECRET_KEY == "test-secret-key-1234567890"

    def test_database_url_required(self, clean_env, monkeypatch):
        """Test that DATABASE_URL validation fails if missing."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        assert "DATABASE_URL" in str(exc_info.value)

    def test_database_url_must_be_postgresql(self, clean_env, monkeypatch):
        """Test that DATABASE_URL must be PostgreSQL."""
        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        assert "PostgreSQL" in str(exc_info.value)

    def test_secret_key_required(self, clean_env, monkeypatch):
        """Test that SECRET_KEY validation fails if missing."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        assert "SECRET_KEY" in str(exc_info.value)

    def test_secret_key_minimum_length(self, clean_env, monkeypatch):
        """Test that SECRET_KEY must be at least 16 characters."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "short")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        assert "at least 16 characters" in str(exc_info.value)

    def test_debug_false_in_production(self, clean_env, monkeypatch):
        """Test that DEBUG cannot be True in production."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "true")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        assert "DEBUG must be False in production" in str(exc_info.value)

    def test_debug_true_in_development(self, clean_env, monkeypatch):
        """Test that DEBUG can be True in development."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("DEBUG", "true")
        
        settings = Settings(_env_file="/nonexistent")
        assert settings.DEBUG is True

    def test_log_level_validation(self, clean_env, monkeypatch):
        """Test that LOG_LEVEL must be valid."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        assert "LOG_LEVEL must be one of" in str(exc_info.value)

    def test_email_notifications_without_smtp(self, clean_env, monkeypatch):
        """Test that EMAIL_NOTIFICATIONS_ENABLED requires SMTP config."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("EMAIL_NOTIFICATIONS_ENABLED", "true")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        error_msg = str(exc_info.value)
        assert "EMAIL_NOTIFICATIONS_ENABLED" in error_msg
        assert "SMTP" in error_msg

    def test_email_notifications_with_smtp(self, clean_env, monkeypatch):
        """Test that EMAIL_NOTIFICATIONS_ENABLED works with SMTP config."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("EMAIL_NOTIFICATIONS_ENABLED", "true")
        monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
        monkeypatch.setenv("SMTP_USERNAME", "user@gmail.com")
        monkeypatch.setenv("SMTP_PASSWORD", "password123")
        
        settings = Settings(_env_file="/nonexistent")
        assert settings.EMAIL_NOTIFICATIONS_ENABLED is True
        assert settings.SMTP_HOST == "smtp.gmail.com"

    def test_n8n_webhook_without_url(self, clean_env, monkeypatch):
        """Test that N8N_WEBHOOK_ENABLED requires N8N_WEBHOOK_URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("N8N_WEBHOOK_ENABLED", "true")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file="/nonexistent")
        
        error_msg = str(exc_info.value)
        assert "N8N_WEBHOOK_ENABLED" in error_msg
        assert "N8N_WEBHOOK_URL" in error_msg

    def test_n8n_webhook_with_url(self, clean_env, monkeypatch):
        """Test that N8N_WEBHOOK_ENABLED works with N8N_WEBHOOK_URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("N8N_WEBHOOK_ENABLED", "true")
        monkeypatch.setenv("N8N_WEBHOOK_URL", "https://n8n.example.com/webhook")
        
        settings = Settings(_env_file="/nonexistent")
        assert settings.N8N_WEBHOOK_ENABLED is True
        assert settings.N8N_WEBHOOK_URL == "https://n8n.example.com/webhook"


class TestConfigRedaction:
    """Test configuration redaction for logging."""

    def test_get_redacted_dict(self, clean_env, monkeypatch):
        """Test that sensitive fields are redacted in get_redacted_dict()."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "super-secret-key-1234567890")
        monkeypatch.setenv("SMTP_PASSWORD", "email-password-123")
        
        settings = Settings(_env_file="/nonexistent")
        redacted = settings.get_redacted_dict()
        
        assert redacted["SECRET_KEY"] == "*****"
        assert redacted["DATABASE_URL"] == "*****"
        assert redacted["SMTP_PASSWORD"] == "*****"
        assert redacted["APP_NAME"] == "QR Attendance System"

    def test_redact_string(self, clean_env, monkeypatch):
        """Test that sensitive values are redacted from strings."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "super-secret-key-1234567890")
        
        settings = Settings(_env_file="/nonexistent")
        
        text = f"Connection: {settings.DATABASE_URL}, Key: {settings.SECRET_KEY}"
        redacted = settings.redact_string(text)
        
        assert "super-secret-key-1234567890" not in redacted
        assert "user:pass@localhost" not in redacted
        assert "*****" in redacted


class TestConfigProperties:
    """Test configuration properties."""

    def test_is_production_property(self, clean_env, monkeypatch):
        """Test is_production property."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("APP_ENV", "production")
        
        settings = Settings(_env_file="/nonexistent")
        assert settings.is_production is True
        
        monkeypatch.setenv("APP_ENV", "development")
        settings = Settings(_env_file="/nonexistent")
        assert settings.is_production is False

    def test_cors_origins_list(self, clean_env, monkeypatch):
        """Test cors_origins_list property parsing."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://example.com, http://test.com")
        
        settings = Settings(_env_file="/nonexistent")
        origins = settings.cors_origins_list
        
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "http://example.com" in origins
        assert "http://test.com" in origins

    def test_allowed_hosts_list(self, clean_env, monkeypatch):
        """Test allowed_hosts_list property parsing."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-1234567890")
        monkeypatch.setenv("ALLOWED_HOSTS", "localhost, 127.0.0.1, example.com")
        
        settings = Settings(_env_file="/nonexistent")
        hosts = settings.allowed_hosts_list
        
        assert len(hosts) == 3
        assert "localhost" in hosts
        assert "127.0.0.1" in hosts
        assert "example.com" in hosts
