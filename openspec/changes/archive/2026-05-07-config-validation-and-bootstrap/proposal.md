## Why

Currently, configuration management is fragmented: backend config is validated at runtime via Pydantic Settings (in `app/core/config.py`), but frontend config/environment is not formalized. Missing or invalid configurations cause silent failures, making debugging difficult in production. We need a unified, robust configuration system with early validation on startup and clear error messages to fail fast and prevent runtime errors.

## What Changes

- **Backend**: Enhance config validation with startup checks, environment-specific profiles, and mandatory vs. optional fields clearly marked. Add configuration bootstrap on application initialization.
- **Frontend**: Introduce a frontend config module that validates API endpoints, feature flags, and other runtime settings via JavaScript/TypeScript, matching backend validation patterns.
- **CLI/Deployment**: Add config validation scripts that can be run pre-deployment to catch errors before startup.

## Capabilities

### New Capabilities

- `backend-config-validation`: Pydantic-based configuration validation for backend services with environment-specific profiles (dev, test, production) and structured error reporting on startup.
- `frontend-config-bootstrap`: Frontend configuration manager that validates and exposes API endpoints, feature flags, and other runtime settings to React components.
- `config-validator-cli`: CLI tool or utility to validate all configuration files before deployment, supporting both backend and frontend configs.

### Modified Capabilities

<!-- No existing capabilities are being modified; this is a new feature suite -->

## Impact

- **Backend files affected**: `app/core/config.py`, `app/main.py` (lifespan startup)
- **Frontend files affected**: New module in `app/frontend/` (React context or utility)
- **Deployment**: May require pre-deployment config validation step in CI/CD
- **Dependencies**: No new third-party dependencies required (using existing Pydantic)
- **Database**: No schema changes
