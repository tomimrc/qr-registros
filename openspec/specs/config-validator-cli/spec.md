## ADDED Requirements

### Requirement: Pre-deployment config validation script

The system SHALL provide a command-line utility script `scripts/validate_config.py` that validates all configuration files before deployment. The script SHALL check for required environment variables and cross-field dependencies without starting the application.

#### Scenario: All config is valid
- **WHEN** the deployment team runs `python scripts/validate_config.py`
- **THEN** the script exits with code 0 and prints: "✓ Configuration validation passed"

#### Scenario: Config is invalid
- **WHEN** the deployment team runs `python scripts/validate_config.py` with missing required environment variables
- **THEN** the script exits with code 1 and prints: "✗ Configuration validation failed: DATABASE_URL is required but not set"

#### Scenario: Environment-specific validation
- **WHEN** the deployment team runs `python scripts/validate_config.py` with APP_ENV=production
- **THEN** the script enforces production-specific rules (e.g., DEBUG must be False) and fails if violated

#### Scenario: Cross-field validation in pre-deployment
- **WHEN** the deployment team runs `python scripts/validate_config.py` with EMAIL_NOTIFICATIONS_ENABLED=true but SMTP_HOST missing
- **THEN** the script exits with code 1 and prints: "✗ Configuration validation failed: EMAIL_NOTIFICATIONS_ENABLED=true requires SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD"

---

### Requirement: Config validation in CI/CD pipeline

The system SHALL support running config validation as a pre-deployment step in the CI/CD pipeline. The validation must complete quickly (< 5 seconds) and prevent deployment if config is invalid.

#### Scenario: CI/CD runs validation before deployment
- **WHEN** a deployment pipeline includes the config validation step before Docker build or container startup
- **THEN** the pipeline fails early if config is invalid, before any deployment actions occur

#### Scenario: Validation output is machine-readable
- **WHEN** the config validation script is run with a `--json` flag
- **THEN** the script outputs machine-readable JSON: `{ "status": "valid" }` or `{ "status": "invalid", "errors": ["DATABASE_URL is required"] }`

---

### Requirement: Config template generation

The system SHALL provide a command to generate a template `.env.example` file from configuration schema, serving as documentation for deployment teams.

#### Scenario: Generate config template
- **WHEN** the deployment team runs `python scripts/validate_config.py --generate-template`
- **THEN** the script creates or updates `..env.example` with all config variables, their types, and descriptions

#### Scenario: Template includes required vs. optional fields
- **WHEN** examining `.env.example`
- **THEN** the file clearly marks required fields with `# REQUIRED` and optional fields with `# OPTIONAL`
