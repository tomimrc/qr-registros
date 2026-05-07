## Context

The current authentication system (`app/routers/auth.py`) handles login, registration, and password changes directly in the router layer. This violates strict layering principles: business logic should live in services. Additionally, several production-critical features are missing:

- No token refresh mechanism (users must re-login when token expires)
- No token revocation/blacklist (logged-out tokens can still be used)
- No audit logging for security events
- No rate limiting (vulnerable to brute force attacks)
- Password validation rules are scattered and inconsistent
- No account lockout mechanism
- Error handling is inconsistent across endpoints

The current architecture also mixes concerns: JWT token operations, password hashing, and admin management are not modularized.

## Goals / Non-Goals

**Goals:**

1. Implement strict layering: Extract auth business logic into `AuthService` (routers → services separation)
2. Add JWT token refresh mechanism with sliding window expiration
3. Implement token blacklist/revocation for logout functionality
4. Add comprehensive audit logging for auth events (login, logout, password changes, failed attempts)
5. Add rate limiting for brute force protection on auth endpoints
6. Implement centralized password validation with complexity rules
7. Add account lockout mechanism after N failed login attempts
8. Ensure consistent error handling and response format across auth endpoints
9. Maintain full backward compatibility with existing endpoints

**Non-Goals:**

- OAuth2 social login (future capability)
- Multi-factor authentication (future capability)
- LDAP/SAML integration (future capability)
- Mobile-specific authentication flows
- API key authentication (different concern)

## Decisions

### Decision 1: Extract Auth Business Logic into `AuthService`

**Decision:** Create `app/services/auth_service.py` with the following responsibilities:
- User registration validation and creation
- Credential verification (login)
- Password change handling
- Token generation and validation
- Account lockout logic

**Rationale:** Follows strict layering rules (Routers → Services). Makes auth logic testable, reusable, and independent of HTTP concerns. Reduces router complexity.

**Alternatives Considered:**
- Keep logic in routers → violates layering, tightly couples HTTP to business logic
- Create separate micro-service → overengineering for current scale

### Decision 2: Token Refresh with Sliding Window Expiration

**Decision:** Implement two token types:
- **Access Token** (short-lived, 15 minutes default): Used for API requests
- **Refresh Token** (long-lived, 7 days default): Used to obtain new access tokens

**Rationale:** Reduces risk of stolen tokens; if access token is compromised, exposure window is small. Sliding window (new refresh token issued with each refresh) prevents token replay attacks.

**Alternatives Considered:**
- Single long-lived token → higher security risk
- No refresh mechanism → poor UX (users must re-login frequently)

### Decision 3: Token Blacklist/Revocation

**Decision:** Implement in-memory blacklist with optional Redis persistence:
- On logout: Add token to blacklist with expiration = token's original exp time
- On token validation: Check if token is in blacklist
- Cleanup: Periodic cleanup of expired entries (or rely on TTL)

**Rationale:** Enables logout and revocation. In-memory with optional Redis allows scaling to multiple workers.

**Alternatives Considered:**
- Database-backed blacklist → slower, doesn't scale well for high-frequency checks
- Stateless (no revocation) → no logout capability
- Redis required → adds infrastructure complexity for small deployments

### Decision 4: Audit Logging

**Decision:** Log auth events to database table `auth_audit_logs`:
- event_type: 'login', 'logout', 'login_failed', 'password_changed', 'token_refresh'
- admin_id, tenant_id, timestamp, ip_address, user_agent, details
- Service: `AuditService` (separate service, not in AuthService)

**Rationale:** Compliance requirement (SOC2, audit trails). Enables security investigations. Separate service maintains modularity.

**Alternatives Considered:**
- Log to files only → hard to query, analyze
- No logging → no audit trail, compliance violation

### Decision 5: Rate Limiting

**Decision:** Use `slowapi` (FastAPI rate limiting library):
- `/auth/login`: 5 attempts per 15 minutes per IP
- `/auth/register`: 3 per 1 hour per IP
- `/auth/change-password`: 10 per 1 hour per user

**Rationale:** Prevents brute force attacks. IP-based for login/register (unauthenticated), user-based for change-password (authenticated).

**Alternatives Considered:**
- Manual tracking in database → complex, slow
- No rate limiting → vulnerable to brute force

### Decision 6: Account Lockout

**Decision:** Add `failed_login_attempts` and `locked_until` fields to Admin model:
- Increment on failed login
- Reset to 0 on successful login
- Lock account if 5 failed attempts in 15 minutes
- Auto-unlock after 15 minutes or admin action

**Rationale:** Additional brute force protection. Self-healing (auto-unlock) improves UX.

**Alternatives Considered:**
- Rate limiting alone → less protection against distributed attacks
- No auto-unlock → poor UX

### Decision 7: Password Validation Rules

**Decision:** Centralize validation in `PasswordValidator` utility:
- Minimum 8 characters
- Must contain at least 1 uppercase letter
- Must contain at least 1 number
- Must contain at least 1 special character (!@#$%^&*)
- Cannot be similar to email
- Cannot reuse last 3 passwords (new table `admin_password_history`)

**Rationale:** Meets enterprise security standards. Centralized validator makes rules easy to audit and update.

**Alternatives Considered:**
- No validation → weak passwords
- Scattered validation → hard to enforce consistently

### Decision 8: Middleware for Common Auth Tasks

**Decision:** Create `app/middleware/auth_middleware.py`:
- Extract IP address and user agent from request
- Inject into request.state for use in auth service
- Handle CORS for auth endpoints

**Rationale:** Centralizes request context collection. Keeps routers clean.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| In-memory blacklist loses data on restart | Use Redis for production; accept minimal risk for dev/staging |
| Token refresh adds API call overhead | Sliding window is amortized; most users don't refresh frequently |
| Rate limiting may block legitimate users on shared IPs | IP-based only for public endpoints; provide bypass option for admins |
| Password history table grows over time | Implement cleanup policy (keep last 24 months only) |
| Account lockout can be DOS vector (if attacker knows email) | Combine with rate limiting; provide admin unlock capability |
| Audit logs table grows without cleanup | Implement archival policy (move old logs after 1 year) |

## Migration Plan

1. **Phase 1 (No breaking changes):**
   - Create `AuthService` with all new business logic
   - Update routers to use `AuthService` (no API changes)
   - Add audit logging (background task)
   - Deploy with FF for audit logging

2. **Phase 2 (Backward compatible):**
   - Add token refresh endpoint `/auth/refresh`
   - Add logout endpoint `/auth/logout` with blacklist
   - Add account lockout logic (inactive by default, enable via config)

3. **Phase 3 (Optional, breaking):**
   - If needed: Change token response format to include expiration times
   - Deprecate old endpoints (if any)

## Open Questions

1. Should refresh token be included in response or stored in HttpOnly cookie? → Recommend HttpOnly cookie for better security
2. Redis requirement for production? → Needs ops input
3. GDPR: How long to retain audit logs? → Check legal requirements
4. Should password history be per-tenant or global? → Per-tenant recommended
5. Should rate limiting be configurable per tenant? → For future

