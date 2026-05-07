# Quick Start: Auth System with Docker

This is a quick reference for getting the auth system running with Docker.

## 5-Minute Setup

### Windows (PowerShell)

```powershell
# 1. Start environment
.\docker-dev.ps1 start

# 2. Watch logs (in another terminal)
.\docker-dev.ps1 logs app

# 3. Once you see "Application startup complete", it's ready!
# Access: http://localhost:8000
```

### Mac/Linux (Bash)

```bash
# 1. Make script executable
chmod +x docker-dev.sh

# 2. Start environment
./docker-dev.sh start

# 3. Watch logs (in another terminal)
./docker-dev.sh logs app

# 4. Once you see "Application startup complete", it's ready!
# Access: http://localhost:8000
```

## Verify It Works

### Check Migrations Applied

```powershell
# Windows
.\docker-dev.ps1 db-shell

# Then in psql:
\dt
# Should show: admin, admin_password_history, auth_audit_logs, tenant, etc.
\q
```

### Test Auth Endpoints

```bash
# 1. Get a token (you'll need a tenant ID first)
# For testing, use: 00000000-0000-0000-0000-000000000001

curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testadmin@example.com",
    "password": "TestPassword123!",
    "nombre": "Test Admin",
    "tenant_id": "00000000-0000-0000-0000-000000000001"
  }'

# 2. Response should be like:
# {
#   "access_token": "eyJ0eXAi...",
#   "refresh_token": "eyJ0eXAi...",
#   "token_type": "bearer",
#   "admin_name": "Test Admin",
#   "tenant_id": "00000000-0000-0000-0000-000000000001",
#   "must_change_password": false
# }

# 3. Test with that token (copy access_token value)
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ0eXAi..."

# Should return your admin info
```

## Run Tests

```powershell
# Windows
.\docker-dev.ps1 test

# Mac/Linux
./docker-dev.sh test
```

Expected output:
```
tests/test_auth_service.py::test_register_success PASSED
tests/test_auth_service.py::test_register_duplicate_email PASSED
tests/test_auth_service.py::test_verify_credentials PASSED
...
```

## Stop Everything

```powershell
# Windows
.\docker-dev.ps1 stop

# Mac/Linux
./docker-dev.sh stop
```

## Troubleshooting

### "Port 5432 already in use"

```powershell
# Find what's using it
netstat -ano | findstr :5432

# Either:
# 1. Stop the other process
# 2. Or change port in docker-compose.dev.yml: "5433:5432"
```

### "Cannot connect to database"

```powershell
# Check if database is running
.\docker-dev.ps1 status

# If not, restart it
.\docker-dev.ps1 restart db

# Wait a few seconds, then try again
```

### "Tests failing with connection errors"

```powershell
# Make sure app is healthy
.\docker-dev.ps1 status

# Check app logs
.\docker-dev.ps1 logs app

# If stuck, restart everything
.\docker-dev.ps1 stop
.\docker-dev.ps1 start
```

## What's Running

| Service | Port | Purpose |
|---------|------|---------|
| **PostgreSQL** | 5432 | Database with auth schema |
| **FastAPI App** | 8000 | REST API with auth endpoints |

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/register` | POST | Create new admin account |
| `/auth/login` | POST | Authenticate and get tokens |
| `/auth/me` | GET | Get current user (protected) |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/logout` | POST | Revoke current token |
| `/auth/change-password` | POST | Change admin password |

## Database Tables

Created automatically:

- `admin` - Admin user accounts
- `admin_password_history` - Password change history
- `auth_audit_logs` - Auth event audit trail
- `tenant` - Organization/company records
- Plus other existing tables

## Next Steps

1. **Review implementation**: Check the generated service files in `app/services/`
2. **Read specs**: See `openspec/changes/archive/2026-05-07-auth-endpoint-completion/specs/`
3. **Explore design**: Review `openspec/changes/archive/2026-05-07-auth-endpoint-completion/design.md`
4. **Test manually**: Use curl/Postman to test endpoints
5. **Check audit logs**: `docker-compose exec db psql -U postgres -d attendance_db -c "SELECT * FROM auth_audit_logs;"`

## Helpful Commands

```powershell
# View current user in database
.\docker-dev.ps1 db-shell
# SELECT id, email, nombre FROM admin;

# View audit logs
.\docker-dev.ps1 db-shell
# SELECT event_type, admin_id, timestamp FROM auth_audit_logs ORDER BY timestamp DESC LIMIT 10;

# Check password history
.\docker-dev.ps1 db-shell
# SELECT admin_id, changed_at FROM admin_password_history;

# Open Python REPL
.\docker-dev.ps1 shell
# from app.services.auth_service import AuthService
# from app.utils.password_validator import PasswordValidator
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application (Port 8000)             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Routers (HTTP)                                          │
│  └─ /auth/register, /auth/login, /auth/refresh, etc.   │
│         ↓                                                │
│  Services (Business Logic)                              │
│  ├─ AuthService (register, verify, password mgmt)      │
│  ├─ AuditService (log events)                          │
│  ├─ PasswordValidator (enforce rules)                  │
│  └─ TokenManager (JWT + refresh tokens)                │
│         ↓                                                │
│  Models (SQLAlchemy ORM)                               │
│  ├─ Admin (users)                                       │
│  ├─ AdminPasswordHistory (password change history)      │
│  └─ AuthAuditLog (security events)                      │
│         ↓                                                │
├─────────────────────────────────────────────────────────┤
│       PostgreSQL Database (Port 5432)                    │
└─────────────────────────────────────────────────────────┘
```

## More Information

- **Detailed Docker guide**: See `DOCKER_SETUP.md`
- **Implementation docs**: See `AUTH_IMPLEMENTATION.md`
- **Design decisions**: See `design.md` in archived change
- **API Specifications**: See `specs/` in archived change

---

**You're ready to go! Happy testing! 🚀**
