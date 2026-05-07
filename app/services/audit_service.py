# app/services/audit_service.py

"""Service for logging authentication and security audit events."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.auth_audit_log import AuthAuditLog


class AuditService:
    """Handles audit logging for authentication events."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        event_type: str,
        admin_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> AuthAuditLog:
        """
        Log an authentication event to the audit trail.

        Args:
            db: Database session
            tenant_id: Tenant ID
            event_type: Type of event (login_success, login_failed, logout, password_changed, token_refreshed)
            admin_id: Admin ID (optional)
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details as dict
            success: Whether the event was successful

        Returns:
            AuthAuditLog: Created audit log entry
        """
        audit_log = AuthAuditLog(
            tenant_id=tenant_id,
            admin_id=admin_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
            details=details or {},
            success=success,
        )
        db.add(audit_log)
        await db.flush()
        return audit_log

    @staticmethod
    async def log_login_success(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        admin_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuthAuditLog:
        """Log successful login event."""
        return await AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="login_success",
            admin_id=admin_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=True,
        )

    @staticmethod
    async def log_login_failed(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        email: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AuthAuditLog:
        """Log failed login attempt."""
        details = {}
        if email:
            details["email"] = email
        if reason:
            details["reason"] = reason

        return await AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="login_failed",
            admin_id=None,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=False,
        )

    @staticmethod
    async def log_logout(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        admin_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthAuditLog:
        """Log logout event."""
        return await AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="logout",
            admin_id=admin_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )

    @staticmethod
    async def log_password_changed(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        admin_id: uuid.UUID,
        changed_by: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthAuditLog:
        """Log password change event."""
        details = {}
        if changed_by:
            details["changed_by"] = changed_by

        return await AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="password_changed",
            admin_id=admin_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=True,
        )

    @staticmethod
    async def log_token_refreshed(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        admin_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthAuditLog:
        """Log token refresh event."""
        return await AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            event_type="token_refreshed",
            admin_id=admin_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
