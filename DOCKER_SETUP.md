# Docker Setup for QR Registros - Development Environment

This guide will help you set up and run the QR Registros application with PostgreSQL using Docker Compose.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Git (for cloning the repository)

## Quick Start

### 1. Start PostgreSQL Database Only (Fast)

```bash
# Start just the database
docker-compose up -d db

# Wait for database to be ready (check status)
docker-compose ps

# Verify connection
$env:PYTHONIOENCODING = "utf-8"
python apply_migrations.py
```

### 2. Start Full Stack (App + Database)

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# In a new terminal, check if services are running
docker-compose ps

# Once app is running, access it at http://localhost:8000
```

### 3. Apply Migrations (if not auto-applied)

```bash
# Run migrations manually
docker-compose exec app python -m alembic upgrade head

# Check current migration status
docker-compose exec app python -m alembic current
```

## Development Workflow

### Start Development Environment

```bash
# Start services in background
docker-compose -f docker-compose.dev.yml up -d

# Watch logs in real-time
docker-compose -f docker-compose.dev.yml logs -f app

# Or in separate terminal, tail specific service
docker-compose -f docker-compose.dev.yml logs -f db
```

### Run Tests

```bash
# Run auth tests
docker-compose exec app pytest tests/test_auth_service.py -v

# Run all tests
docker-compose exec app pytest tests/ -v

# Run with coverage
docker-compose exec app pytest tests/ --cov=app --cov-report=html
```

### Access Database

```bash
# Connect to PostgreSQL directly
docker-compose exec db psql -U postgres -d attendance_db

# Example queries once inside psql:
# \dt                          -- list all tables
# SELECT * FROM admin;         -- view admin users
# SELECT * FROM auth_audit_logs LIMIT 10;  -- view recent auth events
# \q                           -- quit
```

### Verify Auth System

```bash
# Check if migrations were applied
docker-compose exec db psql -U postgres -d attendance_db -c "\dt"

# Should see tables:
# - admin
# - admin_password_history
# - auth_audit_logs
# - tenant
# - etc.
```

## Common Commands

### Database Operations

```bash
# View database logs
docker-compose logs db

# Restart database
docker-compose restart db

# Clear database and start fresh
docker-compose down -v db
docker-compose up -d db

# Backup database
docker-compose exec db pg_dump -U postgres attendance_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres attendance_db < backup.sql
```

### Application Operations

```bash
# View app logs
docker-compose -f docker-compose.dev.yml logs app

# Execute command in running app container
docker-compose exec app python -c "print('Hello from Docker')"

# Access Python shell
docker-compose exec app python

# Format code (black)
docker-compose exec app black app/

# Lint code (flake8)
docker-compose exec app flake8 app/

# Restart app
docker-compose restart app
```

### Container Management

```bash
# Stop all services
docker-compose down

# Stop services without removing volumes (keeps data)
docker-compose down

# Stop services and remove all data
docker-compose down -v

# Remove unused Docker resources
docker system prune

# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# View container logs
docker logs <container_id>
```

## Troubleshooting

### Database Connection Refused

```bash
# Check if db container is running
docker-compose ps db

# If not running, start it
docker-compose up -d db

# Check db logs for errors
docker-compose logs db

# Force recreate db container
docker-compose up -d --force-recreate db
```

### Port 5432 Already in Use

```bash
# Find what's using port 5432
netstat -ano | findstr :5432  # Windows
lsof -i :5432                 # Mac/Linux

# Stop the conflicting service or change port in docker-compose.yml
# Change "5432:5432" to "5433:5432" to use port 5433 locally
```

### Migrations Not Applying

```bash
# Check migration status
docker-compose exec app python -m alembic current

# View migration history
docker-compose exec app python -m alembic history --verbose

# Manual upgrade
docker-compose exec app python -m alembic upgrade head

# Manual downgrade (last 1 migration)
docker-compose exec app python -m alembic downgrade -1
```

### App Container Won't Start

```bash
# View detailed error logs
docker-compose -f docker-compose.dev.yml logs app

# Try rebuilding image
docker-compose -f docker-compose.dev.yml build --no-cache app

# Restart with fresh image
docker-compose -f docker-compose.dev.yml up --build app
```

## Testing Auth System in Docker

### 1. Register a Tenant (One-time setup)

```bash
# Open Python in app container
docker-compose exec app python

# Inside Python:
from app.models.tenant import Tenant
from app.database import get_db
import uuid

# You'll need to set up a tenant first in the database
# This typically requires direct DB access or using an admin endpoint
```

### 2. Test Auth Endpoints

```bash
# From your local machine (not in Docker):

# Register admin
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "TestPassword123!",
    "nombre": "Admin User",
    "tenant_id": "00000000-0000-0000-0000-000000000001"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=TestPassword123!"

# Get current user (replace TOKEN with actual token from login)
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer TOKEN"

# Refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "REFRESH_TOKEN"}'

# Logout
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer TOKEN"
```

## Environment Variables

All variables can be set in `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/attendance_db

# Authentication
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_FAILED_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15

# Security
SECRET_KEY=your-secret-key-here
MASTER_BOOTSTRAP_KEY=your-bootstrap-key

# API
BASE_URL=http://localhost:8000
DEBUG=true
```

## Production vs Development

### Development (docker-compose.dev.yml)
- Auto-reloading app
- Full logging and debug output
- Volumes mapped for live code editing
- Development database

### Production (docker-compose.yml)
- Gunicorn WSGI server (2 workers)
- INFO level logging
- No volumes (image is self-contained)
- Proper restart policy
- Healthchecks enabled

## Performance Notes

### First Run
- First `docker-compose up` will take time:
  - Pulling base images (~500MB)
  - Installing dependencies (~5min)
  - Running migrations (~1min)
  - Total: ~10-15 minutes

### Subsequent Runs
- Should be instant (services start in ~10 seconds)
- Migrations only run if new ones exist

## Persistence

- PostgreSQL data is stored in Docker volume `postgres_dev_data`
- Survives container restarts
- Removed only when running `docker-compose down -v`

## Next Steps

After setup:

1. **Run tests**: `docker-compose exec app pytest tests/test_auth_*.py -v`
2. **Test endpoints**: Use curl commands from "Testing Auth System" section
3. **Verify migrations**: `docker-compose exec app python -m alembic current`
4. **Check audit logs**: `docker-compose exec db psql -U postgres -d attendance_db -c "SELECT * FROM auth_audit_logs LIMIT 5;"`

## Help & Support

If you encounter issues:

1. Check logs: `docker-compose logs [service-name]`
2. Rebuild image: `docker-compose build --no-cache`
3. Start fresh: `docker-compose down -v && docker-compose up --build`
4. Review this guide: README sections 2-3

---

**Happy developing! 🚀**
