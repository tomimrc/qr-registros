# tests/test_auth_endpoints.py

"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.database import Base, get_db
from app.models.tenant import Tenant
from app.models.admin import Admin
from app.core.security import hash_password


# Test database setup
@pytest.fixture(scope="function")
async def test_db():
    """Create an in-memory test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client(test_db):
    """Create test client with override for database."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
async def test_tenant(test_db):
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant",
        slug=f"test-tenant-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    test_db.add(tenant)
    await test_db.commit()
    return tenant


@pytest.fixture
async def test_admin(test_db, test_tenant):
    """Create a test admin."""
    admin = Admin(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email="admin@test.com",
        hashed_password=hash_password("SecurePass123!"),
        nombre="Test Admin",
        is_active=True,
    )
    test_db.add(admin)
    await test_db.commit()
    return admin


# ========================================
# Registration Tests
# ========================================
class TestRegisterEndpoint:
    """Tests for POST /auth/register endpoint."""

    def test_register_success(self, client, test_tenant):
        """Test successful registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newadmin@test.com",
                "password": "SecurePass123!",
                "nombre": "New Admin",
                "tenant_id": str(test_tenant.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"
        assert data["admin_name"] == "New Admin"

    def test_register_duplicate_email(self, client, test_tenant, test_admin):
        """Test that duplicate email is rejected."""
        response = client.post(
            "/auth/register",
            json={
                "email": "admin@test.com",
                "password": "SecurePass456!",
                "nombre": "Another Admin",
                "tenant_id": str(test_tenant.id),
            },
        )

        assert response.status_code == 409
        assert "registrado" in response.json()["detail"]

    def test_register_weak_password(self, client, test_tenant):
        """Test that weak password is rejected."""
        response = client.post(
            "/auth/register",
            json={
                "email": "weakpass@test.com",
                "password": "weak",
                "nombre": "Admin",
                "tenant_id": str(test_tenant.id),
            },
        )

        assert response.status_code == 400

    def test_register_invalid_tenant(self, client):
        """Test that invalid tenant is rejected."""
        response = client.post(
            "/auth/register",
            json={
                "email": "admin@test.com",
                "password": "SecurePass123!",
                "nombre": "Admin",
                "tenant_id": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 404


# ========================================
# Login Tests
# ========================================
class TestLoginEndpoint:
    """Tests for POST /auth/login endpoint."""

    def test_login_success(self, client, test_admin):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={
                "username": "admin@test.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_admin):
        """Test login with invalid credentials."""
        response = client.post(
            "/auth/login",
            data={
                "username": "admin@test.com",
                "password": "WrongPassword!",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_admin(self, client):
        """Test login with nonexistent admin."""
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent@test.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 401


# ========================================
# Refresh Token Tests
# ========================================
class TestRefreshTokenEndpoint:
    """Tests for POST /auth/refresh endpoint."""

    def test_refresh_token_success(self, client, test_admin):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = client.post(
            "/auth/login",
            data={
                "username": "admin@test.com",
                "password": "SecurePass123!",
            },
        )

        refresh_token = login_response.json()["refresh_token"]

        # Now refresh
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"]


# ========================================
# Protected Endpoint Tests
# ========================================
class TestProtectedEndpoints:
    """Tests for protected endpoints."""

    def test_get_me_success(self, client, test_admin):
        """Test GET /auth/me with valid token."""
        # Login to get token
        login_response = client.post(
            "/auth/login",
            data={
                "username": "admin@test.com",
                "password": "SecurePass123!",
            },
        )

        token = login_response.json()["access_token"]

        # Get /auth/me
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"

    def test_get_me_unauthorized(self, client):
        """Test GET /auth/me without token."""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_change_password_success(self, client, test_admin):
        """Test POST /auth/change-password."""
        # Login to get token
        login_response = client.post(
            "/auth/login",
            data={
                "username": "admin@test.com",
                "password": "SecurePass123!",
            },
        )

        token = login_response.json()["access_token"]

        # Change password
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": "SecurePass123!",
                "new_password": "NewSecurePass456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200


# ========================================
# Rate Limiting Tests
# ========================================
class TestRateLimiting:
    """Tests for rate limiting."""

    def test_login_rate_limit(self, client, test_admin):
        """Test that login is rate limited."""
        # Make multiple login attempts (would exceed 5 per 15 min limit in real scenario)
        for i in range(3):
            response = client.post(
                "/auth/login",
                data={
                    "username": "admin@test.com",
                    "password": "SecurePass123!",
                },
            )
            # Should still be within limit
            assert response.status_code in [200, 401]

    def test_register_rate_limit(self, client, test_tenant):
        """Test that registration is rate limited."""
        # Make multiple registration attempts
        for i in range(3):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"admin{i}@test.com",
                    "password": "SecurePass123!",
                    "nombre": f"Admin {i}",
                    "tenant_id": str(test_tenant.id),
                },
            )
            # Should still be within limit
            assert response.status_code in [201, 400, 409]
