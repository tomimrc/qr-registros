## Why

The authentication system is currently functional but lacks critical production-ready features. The routers contain business logic mixed with HTTP handling, there's no dedicated auth service, error handling is inconsistent, and password validation rules are scattered across the code. Additionally, token refresh/revocation mechanisms and audit logging for security events are missing. This creates maintenance issues and security blind spots.

## What Changes

- Extract all auth business logic from the router into a dedicated `AuthService` (routers → services separation)
- Implement proper error handling with specific HTTP status codes and consistent error response format
- Add JWT token refresh mechanism with sliding window expiration
- Add token revocation/blacklist capability
- Add comprehensive audit logging for authentication events (login, logout, password changes, token refresh)
- Add rate limiting for auth endpoints (brute force protection)
- Implement password strength validation rules (min 8 chars, complexity requirements)
- Add support for admin account lockout after failed login attempts
- Add security headers and CORS configuration specific to auth endpoints

## Capabilities

### New Capabilities

- `auth-service`: Business logic layer for authentication operations (register, login, password management, token lifecycle)
- `auth-token-management`: Token generation, validation, refresh, and revocation with blacklisting
- `auth-audit-logging`: Logging and audit trail for all authentication events (logins, logouts, password changes, failed attempts)
- `auth-rate-limiting`: Brute force protection and rate limiting for auth endpoints
- `auth-password-validation`: Password strength validation and complexity enforcement

### Modified Capabilities

(No existing capabilities are being modified—this is a new auth layer being formalized)

## Impact

- **Affected Code**: `app/routers/auth.py`, `app/core/security.py`, `app/core/dependencies.py`
- **New Files**: `app/services/auth_service.py`, possibly new middleware and utilities
- **Dependencies**: Will require `python-jose`, `passlib` (likely already present), and possibly a cache/blacklist store (Redis recommended for production)
- **Database**: May require new tables for token blacklist and audit logs
- **API Contract**: No breaking changes to existing endpoints, but response formats may be enhanced with additional metadata
- **Security**: Improves application security posture significantly (audit logging, rate limiting, token management)

