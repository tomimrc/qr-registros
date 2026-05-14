## 1. Backend Config Validation Setup

- [x] 1.1 Extend `app/core/config.py` with Pydantic field validators for required fields (DATABASE_URL, SECRET_KEY)
- [x] 1.2 Add field validators for environment-specific rules (DEBUG must be False in production)
- [x] 1.3 Add cross-field validators for optional dependencies (e.g., if EMAIL_NOTIFICATIONS_ENABLED then require SMTP_* fields)
- [x] 1.4 Add redaction logic to mask sensitive fields in logs (SECRET_KEY, *_PASSWORD, DATABASE_URL)

## 2. Backend Startup Bootstrap

- [x] 2.1 Create `app/core/bootstrap.py` with `validate_and_log_config()` function
- [x] 2.2 Integrate bootstrap validation into `app/main.py` lifespan startup (before `engine.begin()`)
- [x] 2.3 Log successful config validation with redacted values on app startup
- [x] 2.4 Test that app fails to start with clear error if config is invalid (manually test with missing DATABASE_URL, etc.)

## 3. Backend Config API Endpoint

- [x] 3.1 Create `app/routers/config.py` with GET `/api/config` endpoint
- [x] 3.2 Implement endpoint to return public-safe config (api_base_url, app_name, debug, features flags)
- [x] 3.3 Ensure endpoint does NOT expose SECRET_KEY, DATABASE_URL, or other secrets
- [x] 3.4 Include router in `app/main.py` imports and app.include_router()

## 4. Frontend Config Context

- [x] 4.1 Create `app/frontend/src/context/ConfigContext.tsx` with ConfigContext and useConfig() hook
- [x] 4.2 Create `app/frontend/src/context/ConfigProvider.tsx` that fetches `/api/config` on init
- [x] 4.3 Add validation logic to check for required config fields (api_base_url, app_name)
- [x] 4.4 Add error boundary that displays error page if config fails to load or is invalid
- [x] 4.5 Create TypeScript type definitions for config in `app/frontend/src/types/config.ts`

## 5. Frontend Integration

- [x] 5.1 Create `app/frontend/src/config.ts` utility module that uses ConfigContext
- [ ] 5.2 Update React app root entry point to wrap with ConfigProvider
- [ ] 5.3 Update existing component API calls to use `config.api_base_url` instead of hardcoded URLs
- [ ] 5.4 Test config loading in browser devtools (check Network tab for `/api/config` call)

## 6. Pre-Deployment Validation CLI

- [x] 6.1 Create `scripts/validate_config.py` with main validation logic
- [x] 6.2 Implement environment-specific validation checks (dev vs. production)
- [x] 6.3 Implement cross-field validation matching backend rules
- [x] 6.4 Add `--json` flag support for CI/CD integration
- [x] 6.5 Add `--generate-template` flag to create/update `.env.example`
- [x] 6.6 Test script runs successfully with valid config and fails with clear error on invalid config

## 7. Documentation & Examples

- [x] 7.1 Update `.env.example` with all config variables, marked as REQUIRED or OPTIONAL
- [x] 7.2 Add docstring comments to `app/core/config.py` explaining each setting
- [x] 7.3 Add README section in `docs/` explaining config bootstrap and pre-deployment validation
- [x] 7.4 Document the `/api/config` response schema in API docs

## 8. Testing & Verification

- [x] 8.1 Add unit tests for config validators in `tests/test_config.py`
- [x] 8.2 Test that app fails to start with each missing required field
- [x] 8.3 Test that cross-field validation catches invalid combinations
- [ ] 8.4 Test `/api/config` endpoint returns correct structure and redacts sensitive fields
- [ ] 8.5 Test frontend ConfigContext loads config and handles errors gracefully
- [x] 8.6 Test `scripts/validate_config.py` with various valid/invalid configs
- [ ] 8.7 Run full test suite to ensure no regressions: `pytest tests/`

## 9. Deployment & Rollout

- [x] 9.1 Test config validation in dev environment (local startup)
- [ ] 9.2 Test config validation in staging environment
- [ ] 9.3 Integrate `scripts/validate_config.py` into CI/CD pipeline as pre-deployment check
- [x] 9.4 Document deployment checklist for ops team (run validation before deployment)
- [ ] 9.5 Deploy to production and verify config bootstrap logs appear on startup
