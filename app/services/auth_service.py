# app/services/auth_service.py

"""Core authentication service handling user registration, login, password management."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.admin import Admin
from app.models.tenant import Tenant
from app.models.admin_password_history import AdminPasswordHistory
from app.core.security import hash_password, verify_password
from app.utils.password_validator import PasswordValidator
from app.models.auth_exceptions import (
    AuthError,
    DuplicateEmailError,
    AdminInactiveError,
    InvalidCredentialsError,
    TenantNotFoundError,
    InvalidOldPasswordError,
    AccountLockedError,
    PasswordValidationError,
)


class AuthService:
    """Handles authentication business logic (registration, login, password management)."""

    LOCKOUT_DURATION_MINUTES = 15
    MAX_FAILED_LOGIN_ATTEMPTS = 5

    @classmethod
    async def register(
        cls,
        db: AsyncSession,
        email: str,
        password: str,
        nombre: str,
        tenant_id: uuid.UUID,
    ) -> Admin:
        """
        Register a new admin user.

        Args:
            db: Database session
            email: Admin email address
            password: Password (will be validated)
            nombre: Admin full name
            tenant_id: Tenant ID

        Returns:
            Admin: Newly created admin user

        Raises:
            TenantNotFoundError: If tenant doesn't exist or is inactive
            DuplicateEmailError: If email already exists
            PasswordValidationError: If password doesn't meet requirements
        """
        # Verify tenant exists and is active
        tenant = await db.get(Tenant, tenant_id)
        if not tenant or not tenant.is_active:
            raise TenantNotFoundError()

        # Check if email already exists
        existing = await db.execute(select(Admin).where(Admin.email == email))
        if existing.scalar_one_or_none():
            raise DuplicateEmailError()

        # Validate password
        PasswordValidator.validate(password, email=email)

        # Create new admin
        admin = Admin(
            tenant_id=tenant_id,
            email=email,
            hashed_password=hash_password(password),
            nombre=nombre,
        )
        db.add(admin)
        await db.flush()

        # Store initial password in history
        await cls._store_password_history(db, admin.id, tenant_id, admin.hashed_password)

        return admin

    @classmethod
    async def verify_credentials(
        cls,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Admin:
        """
        Verify login credentials.

        Args:
            db: Database session
            email: Admin email
            password: Password to verify

        Returns:
            Admin: Authenticated admin user

        Raises:
            InvalidCredentialsError: If email/password invalid
            AdminInactiveError: If admin account is inactive
            AccountLockedError: If account is locked
        """
        # Find admin by email
        result = await db.execute(select(Admin).where(Admin.email == email))
        admin = result.scalar_one_or_none()

        if not admin or not verify_password(password, admin.hashed_password):
            raise InvalidCredentialsError()

        # Check if admin is active
        if not admin.is_active:
            raise AdminInactiveError()

        # Check if account is locked
        if admin.locked_until:
            if datetime.now(timezone.utc) < admin.locked_until:
                locked_until_str = admin.locked_until.isoformat()
                raise AccountLockedError(locked_until_str)
            else:
                # Auto-unlock if lockout time has passed
                admin.locked_until = None
                admin.failed_login_attempts = 0
                await db.flush()

        return admin

    @classmethod
    async def on_failed_login(
        cls,
        db: AsyncSession,
        admin: Optional[Admin] = None,
        email: Optional[str] = None,
    ) -> None:
        """
        Handle failed login attempt (increment counter, lock if necessary).

        Args:
            db: Database session
            admin: Admin object (if found)
            email: Email attempted (for logging purposes)
        """
        if not admin:
            return

        # Increment failed attempts
        admin.failed_login_attempts = (admin.failed_login_attempts or 0) + 1

        # Lock account if max attempts exceeded
        if admin.failed_login_attempts >= cls.MAX_FAILED_LOGIN_ATTEMPTS:
            admin.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=cls.LOCKOUT_DURATION_MINUTES
            )

        await db.flush()

    @classmethod
    async def on_successful_login(
        cls,
        db: AsyncSession,
        admin: Admin,
    ) -> None:
        """
        Handle successful login (reset failed attempts, unlock if necessary).

        Args:
            db: Database session
            admin: Admin who logged in
        """
        admin.failed_login_attempts = 0
        admin.locked_until = None
        await db.flush()

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        admin: Admin,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        Change admin password with validation.

        Args:
            db: Database session
            admin: Admin changing password
            old_password: Current password (for verification)
            new_password: New password (will be validated)

        Raises:
            InvalidOldPasswordError: If old password is incorrect
            PasswordValidationError: If new password doesn't meet requirements
        """
        # Verify old password
        if not verify_password(old_password, admin.hashed_password):
            raise InvalidOldPasswordError()

        # Validate new password
        PasswordValidator.validate(new_password, email=admin.email)

        # Check password history (can't reuse last 3 passwords)
        await cls._check_password_history(db, admin.id, new_password)

        # Update password
        admin.hashed_password = hash_password(new_password)
        admin.must_change_password = False
        admin.password_changed_at = datetime.now(timezone.utc)
        await db.flush()

        # Store in password history
        await cls._store_password_history(
            db, admin.id, admin.tenant_id, admin.hashed_password
        )

    @classmethod
    async def _check_password_history(
        cls,
        db: AsyncSession,
        admin_id: uuid.UUID,
        new_password: str,
    ) -> None:
        """
        Check if password has been used before (last 3 passwords).

        Args:
            db: Database session
            admin_id: Admin ID
            new_password: Password to check

        Raises:
            PasswordValidationError: If password was reused
        """
        # Get last 3 password hashes
        result = await db.execute(
            select(AdminPasswordHistory.hashed_password)
            .where(AdminPasswordHistory.admin_id == admin_id)
            .order_by(AdminPasswordHistory.changed_at.desc())
            .limit(3)
        )
        previous_hashes = result.scalars().all()

        # Check if new password matches any previous hash
        for old_hash in previous_hashes:
            if verify_password(new_password, old_hash):
                raise PasswordValidationError(
                    "PASSWORD_REUSED",
                    "No puedes reutilizar ninguna de tus últimas 3 contraseñas",
                )

    @classmethod
    async def _store_password_history(
        cls,
        db: AsyncSession,
        admin_id: uuid.UUID,
        tenant_id: uuid.UUID,
        hashed_password: str,
        changed_by: Optional[str] = "self",
    ) -> AdminPasswordHistory:
        """
        Store password in history table.

        Args:
            db: Database session
            admin_id: Admin ID
            tenant_id: Tenant ID
            hashed_password: Hashed password to store
            changed_by: Who changed it (default: "self")

        Returns:
            AdminPasswordHistory: Created history entry
        """
        history = AdminPasswordHistory(
            admin_id=admin_id,
            tenant_id=tenant_id,
            hashed_password=hashed_password,
            changed_by=changed_by,
        )
        db.add(history)
        await db.flush()
        return history

    @classmethod
    async def get_admin(
        cls,
        db: AsyncSession,
        admin_id: uuid.UUID,
    ) -> Optional[Admin]:
        """
        Get admin by ID.

        Args:
            db: Database session
            admin_id: Admin ID

        Returns:
            Admin: Admin user or None
        """
        return await db.get(Admin, admin_id)
