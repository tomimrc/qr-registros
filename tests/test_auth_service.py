# tests/test_auth_service.py

"""Tests for authentication service and utilities."""

import uuid
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.services.auth_service import AuthService
from app.utils.password_validator import PasswordValidator
from app.models.admin import Admin
from app.models.tenant import Tenant
from app.models.admin_password_history import AdminPasswordHistory
from app.models.auth_exceptions import (
    PasswordValidationError,
    DuplicateEmailError,
    InvalidCredentialsError,
    AdminInactiveError,
    TenantNotFoundError,
    InvalidOldPasswordError,
)
from app.core.security import hash_password, verify_password
from app.database import Base


# Fixtures
@pytest.fixture
async def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_tenant(test_db: AsyncSession):
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        is_active=True,
    )
    test_db.add(tenant)
    await test_db.flush()
    return tenant


# ========================================
# PasswordValidator Tests
# ========================================
class TestPasswordValidator:
    """Tests for PasswordValidator utility."""

    def test_valid_password(self):
        """Test that valid password passes validation."""
        PasswordValidator.validate("SecurePass123!")
        # No exception raised = success

    def test_password_too_short(self):
        """Test that password less than 8 chars is rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            PasswordValidator.validate("Short1!")
        assert exc_info.value.code == "PASSWORD_TOO_SHORT"

    def test_missing_uppercase(self):
        """Test that password without uppercase is rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            PasswordValidator.validate("securep@ss123")
        assert exc_info.value.code == "MISSING_UPPERCASE"

    def test_missing_number(self):
        """Test that password without number is rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            PasswordValidator.validate("SecurePass@")
        assert exc_info.value.code == "MISSING_NUMBER"

    def test_missing_special_char(self):
        """Test that password without special char is rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            PasswordValidator.validate("SecurePass123")
        assert exc_info.value.code == "MISSING_SPECIAL_CHAR"

    def test_password_too_similar_to_email(self):
        """Test that password similar to email is rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            PasswordValidator.validate(
                "John@example123", email="john@example.com"
            )
        assert exc_info.value.code == "PASSWORD_TOO_SIMILAR_TO_EMAIL"


# ========================================
# AuthService Tests
# ========================================
class TestAuthService:
    """Tests for AuthService."""

    @pytest.mark.asyncio
    async def test_register_success(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test successful admin registration."""
        admin = await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        assert admin.email == "admin@test.com"
        assert admin.nombre == "Test Admin"
        assert admin.tenant_id == test_tenant.id
        assert admin.is_active is True

        # Verify password is hashed
        assert verify_password("SecurePass123!", admin.hashed_password)

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test that duplicate email is rejected."""
        # Register first admin
        await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        # Try to register with same email
        with pytest.raises(DuplicateEmailError):
            await AuthService.register(
                db=test_db,
                email="admin@test.com",
                password="SecurePass456!",
                nombre="Another Admin",
                tenant_id=test_tenant.id,
            )

    @pytest.mark.asyncio
    async def test_register_invalid_password(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test that invalid password is rejected."""
        with pytest.raises(PasswordValidationError):
            await AuthService.register(
                db=test_db,
                email="admin@test.com",
                password="weak",
                nombre="Test Admin",
                tenant_id=test_tenant.id,
            )

    @pytest.mark.asyncio
    async def test_register_inactive_tenant(self, test_db: AsyncSession):
        """Test that inactive tenant is rejected."""
        inactive_tenant = Tenant(
            id=uuid.uuid4(),
            name="Inactive Tenant",
            slug="inactive-tenant",
            is_active=False,
        )
        test_db.add(inactive_tenant)
        await test_db.flush()

        with pytest.raises(TenantNotFoundError):
            await AuthService.register(
                db=test_db,
                email="admin@test.com",
                password="SecurePass123!",
                nombre="Test Admin",
                tenant_id=inactive_tenant.id,
            )

    @pytest.mark.asyncio
    async def test_verify_credentials_success(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test successful credential verification."""
        # Register admin
        admin = await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        # Verify credentials
        verified_admin = await AuthService.verify_credentials(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
        )

        assert verified_admin.id == admin.id
        assert verified_admin.email == admin.email

    @pytest.mark.asyncio
    async def test_verify_credentials_invalid_password(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test that invalid password is rejected."""
        # Register admin
        await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        # Try with wrong password
        with pytest.raises(InvalidCredentialsError):
            await AuthService.verify_credentials(
                db=test_db,
                email="admin@test.com",
                password="WrongPassword!",
            )

    @pytest.mark.asyncio
    async def test_verify_credentials_inactive_admin(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test that inactive admin is rejected."""
        # Register and then deactivate
        admin = await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )
        admin.is_active = False
        await test_db.flush()

        with pytest.raises(AdminInactiveError):
            await AuthService.verify_credentials(
                db=test_db,
                email="admin@test.com",
                password="SecurePass123!",
            )

    @pytest.mark.asyncio
    async def test_change_password_success(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test successful password change."""
        # Register admin
        admin = await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        # Change password
        await AuthService.change_password(
            db=test_db,
            admin=admin,
            old_password="SecurePass123!",
            new_password="NewSecurePass456!",
        )

        # Verify new password works
        verified = await AuthService.verify_credentials(
            db=test_db,
            email="admin@test.com",
            password="NewSecurePass456!",
        )
        assert verified.id == admin.id

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test that wrong old password is rejected."""
        admin = await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        with pytest.raises(InvalidOldPasswordError):
            await AuthService.change_password(
                db=test_db,
                admin=admin,
                old_password="WrongPassword!",
                new_password="NewSecurePass456!",
            )

    @pytest.mark.asyncio
    async def test_account_lockout_after_failed_attempts(self, test_db: AsyncSession, test_tenant: Tenant):
        """Test account lockout after max failed login attempts."""
        admin = await AuthService.register(
            db=test_db,
            email="admin@test.com",
            password="SecurePass123!",
            nombre="Test Admin",
            tenant_id=test_tenant.id,
        )

        # Simulate failed login attempts
        for _ in range(AuthService.MAX_FAILED_LOGIN_ATTEMPTS):
            await AuthService.on_failed_login(db=test_db, admin=admin)
            await test_db.flush()

        # Check if account is locked
        assert admin.locked_until is not None
        assert admin.failed_login_attempts == AuthService.MAX_FAILED_LOGIN_ATTEMPTS


# ========================================
# TokenManager Tests
# ========================================
class TestTokenManager:
    """Tests for TokenManager."""

    def test_create_access_token(self):
        """Test access token creation."""
        from app.core.token_manager import TokenManager

        token = TokenManager.create_access_token(
            sub="admin-id-123",
            tenant_id="tenant-id-456",
        )

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        payload = TokenManager.decode_token(token)
        assert payload["sub"] == "admin-id-123"
        assert payload["tenant_id"] == "tenant-id-456"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        from app.core.token_manager import TokenManager

        token = TokenManager.create_refresh_token(
            sub="admin-id-123",
            tenant_id="tenant-id-456",
        )

        assert token is not None
        assert isinstance(token, str)

        # Decode and verify
        payload = TokenManager.decode_token(token)
        assert payload["sub"] == "admin-id-123"
        assert payload["type"] == "refresh"
