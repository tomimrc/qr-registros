# Configuration Bootstrap and Validation

## Overview

The application uses a robust configuration system with early validation on startup and clear error messages to fail fast and prevent runtime errors.

## Key Features

- **Early Validation**: Configuration is validated when the application starts, not at first use
- **Environment-Specific Profiles**: Different validation rules for development, test, and production
- **Clear Error Messages**: Deployment teams see exactly what's missing or misconfigured
- **Redacted Logging**: Sensitive values (SECRET_KEY, passwords, DB URLs) are masked in logs
- **Pre-Deployment Checks**: CLI tool validates config before deployment

## Configuration Files

### `.env` (Development)

The main configuration file for local development:

```bash
cp .env.example .env
# Edit .env with your local values
```

Required fields:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key (at least 16 characters)

### `.env.production`

Production-specific configuration:

```bash
# Copy development .env to production version
cp .env .env.production
# Update values for production environment
```

In production:
- `DEBUG` must be `False`
- `SECRET_KEY` must be a strong random value (at least 32 characters)
- All required services must be properly configured

### `.env.test`

Test environment configuration (used by pytest):

```bash
cp .env .env.test
# Configure for test database, etc.
```

## Backend Configuration System

### Startup Bootstrap

When the FastAPI application starts, the `validate_and_log_config()` function is called during the lifespan startup phase:

1. **Validation**: Pydantic Settings validates all environment variables
2. **Logging**: Configuration is logged with sensitive values redacted
3. **Failure Handling**: If validation fails, the application exits with a clear error

Example startup log:

```
================================================================================
Config validation passed during startup
--------------------------------------------------------------------------------
APP_ENV: production
APP_NAME: QR Attendance System
DEBUG: False
BASE_URL: https://api.example.com
LOG_LEVEL: INFO
DATABASE_URL: *****
CORS_ORIGINS: https://example.com
ALLOWED_HOSTS: example.com
EMAIL_NOTIFICATIONS_ENABLED: True
N8N_WEBHOOK_ENABLED: False
================================================================================
```

### Configuration Validators

#### Required Fields

These fields must be provided in all environments:

- **`DATABASE_URL`** (string): PostgreSQL connection URL
  - Must be a valid PostgreSQL connection string
  - Example: `postgresql://user:password@localhost:5432/attendance_db`

- **`SECRET_KEY`** (string): JWT secret key for token generation
  - Minimum 16 characters (32+ recommended for production)
  - Generate with: `python -c 'import secrets; print(secrets.token_urlsafe(32))'`

#### Environment-Specific Validation

- **`DEBUG`**: Must be `False` in production
- **`LOG_LEVEL`**: Must be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

#### Cross-Field Validation

If certain features are enabled, their dependencies must be configured:

**Email Notifications**:
```python
if EMAIL_NOTIFICATIONS_ENABLED == True:
    # Then these are required:
    - SMTP_HOST
    - SMTP_USERNAME  
    - SMTP_PASSWORD
```

**N8N Webhooks**:
```python
if N8N_WEBHOOK_ENABLED == True:
    # Then this is required:
    - N8N_WEBHOOK_URL
```

### Configuration API Endpoint

The backend exposes a public `/api/config` endpoint that returns safe configuration to frontend clients:

```bash
curl http://localhost:8000/api/config
```

Response:
```json
{
  "api_base_url": "http://localhost:8000",
  "app_name": "QR Attendance System",
  "debug": false,
  "log_level": "INFO",
  "features": {
    "email_notifications": true,
    "n8n_webhooks": false
  }
}
```

**Security**: This endpoint is unauthenticated (public) but NEVER exposes sensitive values like `SECRET_KEY`, `DATABASE_URL`, or `SMTP_PASSWORD`.

## Frontend Configuration

### Loading Configuration

The frontend loads configuration from the backend when the app initializes:

```typescript
import { ConfigProvider, useConfig } from './config';

// Wrap your app with ConfigProvider
function App() {
  return (
    <ConfigProvider>
      <MyApp />
    </ConfigProvider>
  );
}
```

### Accessing Configuration

In any React component:

```typescript
import { useConfig } from './config';

function MyComponent() {
  const config = useConfig();
  
  return (
    <div>
      <h1>{config.app_name}</h1>
      <p>Debug: {config.debug}</p>
      {config.features.email_notifications && (
        <EmailSection />
      )}
    </div>
  );
}
```

### Error Handling

If configuration fails to load or is invalid, the app displays an error page:

```
Configuration Error
Failed to load application configuration. Please try again or contact support.
[Retry]
```

## Pre-Deployment Validation

### Using the Validation Script

Before deploying, validate your configuration:

```bash
# Check if config is valid
python scripts/validate_config.py

# Output JSON for CI/CD automation
python scripts/validate_config.py --json

# Generate .env.example template
python scripts/validate_config.py --generate-template
```

### Exit Codes

- **0**: Configuration is valid
- **1**: Configuration is invalid

### JSON Output

For CI/CD integration:

```bash
$ python scripts/validate_config.py --json

# Success:
{"status": "valid", "message": "Configuration validation passed"}

# Failure:
{
  "status": "invalid",
  "message": "DATABASE_URL is required and cannot be empty",
  "errors": ["DATABASE_URL is required and cannot be empty"]
}
```

### CI/CD Integration

Add to your deployment pipeline before starting the application:

```yaml
# Example GitHub Actions
- name: Validate Configuration
  run: python scripts/validate_config.py

- name: Start Application
  run: docker run -d my-app:latest
```

Or in a Dockerfile:

```dockerfile
# Validate config before starting
RUN python scripts/validate_config.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

## Troubleshooting

### Application Won't Start

If the application fails to start, check the logs for configuration errors:

```
ERROR: Config validation failed: DATABASE_URL is required and cannot be empty
```

**Solution**: Ensure all required environment variables are set in your `.env` file.

### "EMAIL_NOTIFICATIONS_ENABLED=true requires SMTP_*"

If you see this error:

```
ERROR: EMAIL_NOTIFICATIONS_ENABLED=true requires the following fields to be configured: SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD
```

**Solution**: Either:
1. Configure SMTP settings in your `.env` file, OR
2. Set `EMAIL_NOTIFICATIONS_ENABLED=false`

### "DEBUG must be False in production"

In production, the DEBUG flag cannot be enabled:

```
ERROR: DEBUG must be False in production environment
```

**Solution**: Ensure `DEBUG=false` in your `.env.production` file.

### Frontend Gets "Configuration Error"

If the frontend displays a configuration error:

**Check**:
1. Is the backend running? (`curl http://localhost:8000/api/config`)
2. Is the API URL correct in the frontend config?
3. Are CORS settings allowing the frontend domain?

**Debugging in Browser DevTools**:
- Open Network tab
- Look for `/api/config` request
- Check response status and content

## Key Files

- **Backend Config**: `app/core/config.py` - Settings class with validators
- **Bootstrap**: `app/core/bootstrap.py` - Startup validation and logging
- **Config Endpoint**: `app/routers/config.py` - Public `/api/config` endpoint
- **Frontend Config**: `app/frontend/src/config.ts` - Config exports and utilities
- **Frontend Context**: `app/frontend/src/context/ConfigContext.tsx` - React Context
- **Frontend Provider**: `app/frontend/src/context/ConfigProvider.tsx` - Provider component
- **CLI Tool**: `scripts/validate_config.py` - Pre-deployment validation
- **Template**: `.env.example` - Configuration template

## References

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [React Context API](https://react.dev/reference/react/useContext)
