# Tasks: auth-endpoint-completion

## 1. Database & Models Setup

- [ ] 1.1 Create `admin_password_history` table migration: stores admin_id, tenant_id, hashed_password, changed_at, changed_by
- [ ] 1.2 Create `auth_audit_logs` table migration: stores id, tenant_id, admin_id, event_type, ip_address, user_agent, timestamp, details (JSON), success
- [ ] 1.3 Add fields to Admin model: `failed_login_attempts` (default 0), `locked_until` (datetime nullable), `must_change_password` already exists
- [ ] 1.4 Run `alembic revision --autogenerate` and `alembic upgrade head` to apply migrations

## 2. Core Auth Service & Utilities

- [ ] 2.1 Create `app/services/auth_service.py` with class `AuthService` containing methods: `register()`, `verify_credentials()`, `change_password()`, `get_admin()`
- [ ] 2.2 Create `app/utils/password_validator.py` with class `PasswordValidator` containing: `validate()` method with all password rules (min 8 chars, uppercase, number, special char, not similar to email, no reuse)
- [ ] 2.3 Create `app/models/auth_exceptions.py` with custom exceptions: `AuthError`, `PasswordValidationError` with specific error codes
- [ ] 2.4 Create `app/services/audit_service.py` with class `AuditService` containing: `log_event()` async method to write audit logs to database
- [ ] 2.5 Create `app/middleware/auth_middleware.py` to extract IP address and user agent from requests and store in request.state

## 3. Token Management & Blacklist

- [ ] 3.1 Implement token blacklist in-memory cache in `app/core/token_blacklist.py` with add/remove/check/cleanup methods
- [ ] 3.2 Create `app/core/token_manager.py` with methods: `create_access_token()`, `create_refresh_token()`, `verify_access_token()`, `verify_refresh_token()`, `decode_token_with_type_check()`
- [ ] 3.3 Update `app/core/security.py` to expose token type differentiation (access vs refresh tokens with different expirations)
- [ ] 3.4 Implement `get_current_admin_from_refresh_token()` in `app/core/dependencies.py` for `/auth/refresh` endpoint

## 4. Rate Limiting & Account Lockout

- [ ] 4.1 Install `slowapi` package via pip and add to requirements.txt
- [ ] 4.2 Create `app/utils/rate_limiter.py` with FastAPI route decorators: `@rate_limit_login()`, `@rate_limit_register()`, `@rate_limit_password_change()`
- [ ] 4.3 Implement account lockout logic in `AuthService.verify_credentials()`: check `locked_until`, increment `failed_login_attempts` on failure, lock account after 5 failed attempts in 15 minutes
- [ ] 4.4 Add lockout response header support (RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset)

## 5. Router & Endpoint Updates

- [ ] 5.1 Refactor `app/routers/auth.py` POST `/auth/register` to call `AuthService.register()` and remove direct business logic
- [ ] 5.2 Refactor `app/routers/auth.py` POST `/auth/login` to call `AuthService.verify_credentials()`, handle lockout exceptions, and log audit events
- [ ] 5.3 Refactor `app/routers/auth.py` POST `/auth/change-password` to call `AuthService.change_password()` and log audit events
- [ ] 5.4 Create new POST `/auth/refresh` endpoint: accepts refresh_token, calls token manager, returns new access/refresh token pair
- [ ] 5.5 Create new POST `/auth/logout` endpoint: accepts token, adds to blacklist, logs audit event, returns success
- [ ] 5.6 Add rate limiting decorators to all auth endpoints from 4.2
- [ ] 5.7 Update GET `/auth/me` endpoint to use refactored dependencies

## 6. Dependency Injection Updates

- [ ] 6.1 Update `app/core/dependencies.py` `get_current_admin()` to check token blacklist before validating
- [ ] 6.2 Add `get_current_admin_from_refresh_token()` function to handle refresh token validation
- [ ] 6.3 Create middleware registration in `app/main.py` to add auth_middleware to all requests

## 7. Audit Logging Integration

- [ ] 7.1 Call `AuditService.log_event()` in auth router after successful/failed login attempts
- [ ] 7.2 Call `AuditService.log_event()` in auth router after password changes
- [ ] 7.3 Call `AuditService.log_event()` in auth router on logout
- [ ] 7.4 Call `AuditService.log_event()` in token manager on successful token refresh
- [ ] 7.5 Verify audit logs include ip_address and user_agent from request.state

## 8. Configuration & Environment

- [ ] 8.1 Add to `config.py`: `REFRESH_TOKEN_EXPIRE_DAYS` (default 7), `MAX_FAILED_LOGIN_ATTEMPTS` (default 5), `LOCKOUT_DURATION_MINUTES` (default 15)
- [ ] 8.2 Update `.env.example` with new config keys
- [ ] 8.3 Add configuration for rate limiting thresholds in `config.py`
- [ ] 8.4 Configure token blacklist (in-memory vs Redis) based on environment

## 9. Testing

- [ ] 9.1 Write tests for `PasswordValidator`: valid password, missing uppercase, missing number, missing special char, too short, similar to email, reused password
- [ ] 9.2 Write tests for `AuthService.register()`: success, duplicate email, inactive tenant
- [ ] 9.3 Write tests for `AuthService.verify_credentials()`: valid credentials, invalid password, inactive admin
- [ ] 9.4 Write tests for token refresh: valid refresh token, expired token, blacklisted token
- [ ] 9.5 Write tests for logout: token blacklist, subsequent requests rejected
- [ ] 9.6 Write tests for rate limiting: exceeded limits return 429, headers included
- [ ] 9.7 Write tests for account lockout: locked after N attempts, auto-unlock after timeout
- [ ] 9.8 Write tests for audit logging: events logged with correct details
- [ ] 9.9 Run full test suite: `pytest tests/` and ensure no regressions

## 10. Code Quality & Documentation

- [ ] 10.1 Run `black app/` to format all new code
- [ ] 10.2 Run `flake8 app/` to check for linting issues
- [ ] 10.3 Add docstrings to all new methods in services and utilities (Google style)
- [ ] 10.4 Add type hints to all function parameters and returns
- [ ] 10.5 Create migration documentation in `MIGRATIONS.md`
- [ ] 10.6 Update API documentation with new endpoints and response schemas

## 11. Verification & Integration

- [ ] 11.1 Test full login → token refresh → logout flow manually with Postman/curl
- [ ] 11.2 Verify audit logs are created and queryable
- [ ] 11.3 Verify rate limiting works by exceeding limits and checking response headers
- [ ] 11.4 Verify account lockout triggers and auto-unlocks
- [ ] 11.5 Verify password validation works across all endpoints
- [ ] 11.6 Test with existing clients to ensure backward compatibility (old clients without refresh logic still work)
- [ ] 11.7 Run server: `uvicorn app.main:app --reload` and verify no startup errors

## 12. Cleanup & Final Steps

- [ ] 12.1 Remove any temporary debug code or print statements
- [ ] 12.2 Update CHANGELOG with new features and breaking changes (if any)
- [ ] 12.3 Create summary of new environment variables and required setup
- [ ] 12.4 Archive change when complete: `openspec archive auth-endpoint-completion`

