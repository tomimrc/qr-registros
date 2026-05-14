## Context

**Current State**: Configuration is handled via Pydantic `BaseSettings` in `app/core/config.py`, loaded from environment files (`.env`, `.env.test`, `.env.production`). Frontend has no formalized config system—values are hardcoded in HTML templates or passed via API responses. Missing or invalid environment variables fail silently or cause runtime errors.

**Problem**: 
- No early validation on startup
- Frontend config is scattered and inconsistent
- Deployment errors due to missing config are not caught pre-deployment
- No audit trail or clear error messages for config issues

**Constraints**:
- Must use existing Pydantic setup (no major dependency changes)
- Must support strict layering (Services handle business logic, not config)
- Must work with FastAPI lifespan pattern already in place
- Frontend is React-based; config must be accessible to all components

## Goals / Non-Goals

**Goals:**
- Implement comprehensive config validation on backend startup that fails fast with clear error messages
- Create a frontend config module (React context) that validates API endpoints and exposes feature flags
- Add pre-deployment validation CLI tool to catch config errors before deployment
- Ensure both backend and frontend follow the same validation philosophy: fail early, be explicit

**Non-Goals:**
- Database schema changes
- Runtime hot-reloading of config (changes require restart)
- Config UI or admin panel for changing config
- Third-party secrets management (beyond env files)

## Decisions

### Decision 1: Backend Config Validation via Extended Pydantic Settings
**Chosen**: Extend `Settings` class with validation methods and environment-specific profiles.

**Rationale**: 
- Pydantic is already a project dependency
- Pydantic v2 supports field validators and root validators for complex checks
- Profiles (dev/test/prod) can be modeled as separate Settings subclasses or env-driven logic

**Alternatives Considered**:
- Use a separate validation library (e.g., marshmallow) → adds dependency, redundant with Pydantic
- YAML config files → adds file management burden, harder to deploy in containers

**Implementation**: 
- Add mandatory/optional field metadata to `Settings`
- Add `@field_validator` for cross-field validation (e.g., if EMAIL_NOTIFICATIONS_ENABLED, then SMTP_HOST must be set)
- Add config bootstrap method called during FastAPI lifespan that logs all validated config on startup

---

### Decision 2: Startup Validation Hook in FastAPI Lifespan
**Chosen**: Call config validation in the `lifespan` context manager before app readiness.

**Rationale**:
- Lifespan is the intended place for pre-startup initialization
- Fails fast (app doesn't start if config is invalid)
- Aligns with existing `_ensure_debug_schema_compatibility()` pattern

**Alternatives Considered**:
- Manual validation in main.py → less structured, easy to forget
- Event-based validation → harder to guarantee ordering

---

### Decision 3: Frontend Config via React Context Provider
**Chosen**: Create `app/frontend/context/ConfigContext.tsx` with a provider that validates and exposes config.

**Rationale**:
- React Context is built-in; no extra dependencies
- Config is typically needed at app root level
- Allows components to `useConfig()` hook for type-safe access

**Alternatives Considered**:
- Redux or Zustand → overkill for static config
- Global variables → not type-safe, harder to test

**Implementation**:
- Create `ConfigContext` that fetches config from backend API endpoint (e.g., `/api/config`)
- Validate against a TypeScript schema on load
- Throw error if critical config is missing (same fail-fast philosophy)

---

### Decision 4: Pre-Deployment Validation CLI Tool
**Chosen**: Create Python utility `scripts/validate_config.py` that runs as a deployment check.

**Rationale**:
- Catches issues before container starts
- Can be run in CI/CD pipeline
- Python-based (consistent with backend)

**Alternatives Considered**:
- Bash script → less portable, harder to maintain
- Separate Node.js tool → adds build step

---

### Decision 5: Configuration Structure
**Chosen**: Flat environment variable model with validation, no nested config files (yet).

**Rationale**:
- Current approach works well in containerized environments
- Pydantic Settings already supports this
- Simpler to deploy

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Missing env vars on first deployment | Pre-deployment validator script run in CI/CD. Provide `.env.example` with all required vars. |
| Frontend config endpoint not authenticated properly | Create a public `/api/config` endpoint that returns only safe, non-sensitive config. Never expose SECRET_KEY, DB_URL, etc. |
| Frontend gets stale config if backend restarts | Frontend config is loaded once on app init. If frequent reloads needed, add periodic refresh (future enhancement). |
| Tight coupling between backend and frontend config schema | Document the `/api/config` response schema clearly. Version if needed. |
| Validation errors are cryptic for deployment teams | Use clear, actionable error messages in validation. Example: `"ERROR: EMAIL_NOTIFICATIONS_ENABLED=true but SMTP_HOST is missing"` |

---

## Migration Plan

**Phase 1 - Backend (non-breaking)**:
1. Extend `Settings` class with validators (no removal of existing logic)
2. Add config bootstrap method to lifespan
3. Add logging of validated config on startup
4. Deploy to dev environment first to test

**Phase 2 - Frontend**:
1. Create ConfigContext and Provider
2. Add `/api/config` endpoint
3. Update HTML entry points to wrap with ConfigProvider
4. Test in staging environment

**Phase 3 - Deployment Validation**:
1. Create and test `scripts/validate_config.py`
2. Integrate into CI/CD pipeline as pre-deployment step

**Rollback Strategy**: 
- Changes are backward-compatible. If issues arise, remove bootstrap validation from lifespan and skip frontend config loading—app will still work.

---

## Open Questions

1. **Frontend Config Caching**: Should frontend cache config in localStorage to survive page reloads, or always fetch fresh?
2. **Config Versioning**: Should we version the `/api/config` response for future-proofing?
3. **Audit Logging**: Should failed config attempts be logged to audit table?
4. **Secrets Rotation**: Out of scope for this change, but noted for future.
