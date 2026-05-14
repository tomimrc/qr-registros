## ADDED Requirements

### Requirement: Backend configuration validation on startup

The system SHALL validate all environment configuration variables when the FastAPI application starts. If any required configuration is missing or invalid, the application SHALL fail to start with a clear, actionable error message.

#### Scenario: All required config is present and valid
- **WHEN** the FastAPI application starts with valid environment variables
- **THEN** the application initializes successfully and logs "Config validation passed" with a summary of active settings

#### Scenario: Required config is missing
- **WHEN** the FastAPI application starts but a required environment variable is missing (e.g., DATABASE_URL, SECRET_KEY)
- **THEN** the application fails to start and logs an error message naming the missing variable and its required format

#### Scenario: Config has invalid format
- **WHEN** the FastAPI application starts but a config value has an invalid format (e.g., DB_POOL_SIZE="abc" instead of integer)
- **THEN** the application fails to start and logs an error message describing the validation failure and the expected format

#### Scenario: Environment-specific config profiles
- **WHEN** the application starts with APP_ENV set to "production" vs. "development"
- **THEN** the application enforces environment-specific validation rules (e.g., DEBUG must be False in production, DEBUG can be True in development)

---

### Requirement: Cross-field config validation

The system SHALL validate dependencies between configuration fields. For example, if EMAIL_NOTIFICATIONS_ENABLED is True, then SMTP_HOST and SMTP_USERNAME must be provided.

#### Scenario: Email notifications enabled without SMTP config
- **WHEN** EMAIL_NOTIFICATIONS_ENABLED is True but SMTP_HOST is empty
- **THEN** the application fails to start with error: "EMAIL_NOTIFICATIONS_ENABLED=true requires SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD to be configured"

#### Scenario: Email notifications disabled without SMTP config
- **WHEN** EMAIL_NOTIFICATIONS_ENABLED is False
- **THEN** SMTP_* config fields are optional and the application starts successfully

#### Scenario: N8N webhook enabled without webhook URL
- **WHEN** N8N_WEBHOOK_ENABLED is True but N8N_WEBHOOK_URL is empty
- **THEN** the application fails to start with error: "N8N_WEBHOOK_ENABLED=true requires N8N_WEBHOOK_URL to be configured"

---

### Requirement: Config bootstrap logging

The system SHALL log all validated configuration on successful startup. Sensitive fields (SECRET_KEY, SMTP_PASSWORD, database credentials) SHALL be redacted in logs.

#### Scenario: Config logged on startup
- **WHEN** the application starts successfully
- **THEN** logs contain: "Config validated: APP_NAME=..., DEBUG=..., DATABASE_URL=*****, CORS_ORIGINS=[...]" (sensitive values masked)

#### Scenario: Secret redaction in logs
- **WHEN** logging configuration
- **THEN** fields named SECRET_KEY, *_PASSWORD, DATABASE_URL are replaced with "****" to prevent accidental exposure
