#!/usr/bin/env python3
"""Configuration validation CLI tool.

This script validates application configuration before deployment.
It checks for required environment variables and cross-field dependencies
without starting the application.

Usage:
    python scripts/validate_config.py              # Validate with current environment
    python scripts/validate_config.py --json       # Output JSON for CI/CD
    python scripts/validate_config.py --generate-template  # Create .env.example
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure stdout handles Unicode properly (for Windows)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_config() -> Tuple[bool, List[str]]:
    """Validate configuration without instantiating FastAPI.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors: List[str] = []
    
    # Import config after adding to path
    try:
        from app.core.config import Settings
    except ImportError as e:
        errors.append(f"Failed to import Settings: {e}")
        return False, errors
    
    try:
        # Attempt to instantiate settings (triggers all Pydantic validators)
        settings = Settings()
        return True, []
    except Exception as e:
        # Pydantic validation error
        errors.append(str(e))
        return False, errors


def generate_env_template() -> str:
    """Generate a .env.example template file.
    
    Returns:
        Content of the template file
    """
    template = """# Application Configuration Template
# Copy this file to .env and fill in your values
# Fields marked REQUIRED must be provided; OPTIONAL fields have sensible defaults

# ===== REQUIRED SETTINGS =====
# Required in all environments

# Database connection URL (must be PostgreSQL)
# Example: postgresql://user:password@localhost:5432/attendance_db
DATABASE_URL=postgresql://user:password@localhost:5432/attendance_db  # REQUIRED

# Secret key for JWT token generation and encryption
# Should be a random 32+ character string (use: python -c 'import secrets; print(secrets.token_urlsafe(32))')
SECRET_KEY=your-secret-key-here-at-least-16-characters  # REQUIRED


# ===== CORE APPLICATION SETTINGS =====

# Application environment: development, test, or production
APP_ENV=development  # OPTIONAL (default: development)

# Debug mode (must be False in production)
DEBUG=false  # OPTIONAL (default: false)

# Base URL of the backend, used by frontend for API calls
BASE_URL=http://localhost:8000  # OPTIONAL (default: http://localhost:8000)

# Application name displayed in UI and documentation
APP_NAME=QR Attendance System  # OPTIONAL

# JWT token algorithm
ALGORITHM=HS256  # OPTIONAL (default: HS256)

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES=60  # OPTIONAL (default: 60)
REFRESH_TOKEN_EXPIRE_DAYS=7  # OPTIONAL (default: 7)

# Login attempt controls
MAX_FAILED_LOGIN_ATTEMPTS=5  # OPTIONAL (default: 5)
LOCKOUT_DURATION_MINUTES=15  # OPTIONAL (default: 15)

# Optional IP address restrictions
ALLOWED_IP=  # OPTIONAL (leave empty for no restriction)

# Logging configuration
LOG_LEVEL=INFO  # OPTIONAL (default: INFO, options: DEBUG, INFO, WARNING, ERROR, CRITICAL)

# Worker and connection pool settings
WORKERS=2  # OPTIONAL (default: 2)
DB_POOL_SIZE=5  # OPTIONAL (default: 5)
DB_MAX_OVERFLOW=10  # OPTIONAL (default: 10)
DB_POOL_TIMEOUT_SECONDS=30  # OPTIONAL (default: 30)
DB_POOL_RECYCLE_SECONDS=1800  # OPTIONAL (default: 1800)

# CORS configuration (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000  # OPTIONAL

# Allowed hosts for TrustedHostMiddleware
ALLOWED_HOSTS=localhost,127.0.0.1  # OPTIONAL

# Master bootstrap key (for initial system setup)
MASTER_BOOTSTRAP_KEY=  # OPTIONAL


# ===== EMAIL NOTIFICATION SETTINGS =====
# If EMAIL_NOTIFICATIONS_ENABLED=true, you MUST configure SMTP_* settings

# Enable email notifications
EMAIL_NOTIFICATIONS_ENABLED=false  # OPTIONAL (default: false)

# SMTP configuration (required if EMAIL_NOTIFICATIONS_ENABLED=true)
SMTP_HOST=smtp.gmail.com  # REQUIRED if EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_PORT=587  # OPTIONAL (default: 587)
SMTP_USERNAME=your-email@gmail.com  # REQUIRED if EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_PASSWORD=your-app-password  # REQUIRED if EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_FROM_EMAIL=noreply@example.com  # OPTIONAL
SMTP_USE_TLS=true  # OPTIONAL (default: true)
SMTP_USE_SSL=false  # OPTIONAL (default: false)
SMTP_TIMEOUT_SECONDS=15  # OPTIONAL (default: 15)

# WhatsApp URL for landing page
LANDING_WHATSAPP_URL=  # OPTIONAL


# ===== N8N WEBHOOK SETTINGS =====
# If N8N_WEBHOOK_ENABLED=true, you MUST configure N8N_WEBHOOK_URL

# Enable N8N webhook integration
N8N_WEBHOOK_ENABLED=false  # OPTIONAL (default: false)

# N8N webhook URL (required if N8N_WEBHOOK_ENABLED=true)
N8N_WEBHOOK_URL=https://n8n.example.com/webhook/attendance  # REQUIRED if N8N_WEBHOOK_ENABLED=true

# N8N webhook timeout
N8N_WEBHOOK_TIMEOUT_SECONDS=8  # OPTIONAL (default: 8)
"""
    return template


def main() -> int:
    """Main entry point for the validation script.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate application configuration before deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_config.py              # Validate configuration
  python scripts/validate_config.py --json       # Output JSON for CI/CD
  python scripts/validate_config.py --generate-template  # Generate .env.example
        """,
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output validation result as JSON (for CI/CD integration)",
    )
    
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Generate .env.example template file",
    )
    
    args = parser.parse_args()
    
    # Handle template generation
    if args.generate_template:
        template_content = generate_env_template()
        template_path = Path(__file__).parent.parent / ".env.example"
        try:
            template_path.write_text(template_content)
            if args.json:
                print(json.dumps({
                    "status": "success",
                    "message": f"Template generated at {template_path}",
                    "path": str(template_path),
                }))
            else:
                print(f"[OK] Template generated at {template_path}")
            return 0
        except Exception as e:
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "message": str(e),
                }))
            else:
                print(f"[ERROR] Failed to generate template: {e}")
            return 1
    
    # Validate configuration
    is_valid, errors = validate_config()
    
    if is_valid:
        if args.json:
            print(json.dumps({
                "status": "valid",
                "message": "Configuration validation passed",
            }))
        else:
            print("[OK] Configuration validation passed")
        return 0
    else:
        error_message = errors[0] if errors else "Unknown error"
        
        if args.json:
            print(json.dumps({
                "status": "invalid",
                "message": error_message,
                "errors": errors,
            }))
        else:
            print("[ERROR] Configuration validation failed:")
            print(f"  {error_message}")
            for error in errors[1:]:
                print(f"  {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
