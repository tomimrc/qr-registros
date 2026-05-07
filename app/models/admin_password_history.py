# app/models/admin_password_history.py

from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.admin import Admin


class AdminPasswordHistory(Base):
    """Stores password history for admins to prevent password reuse."""
    __tablename__ = "admin_password_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admins.id"), nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    changed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    admin: Mapped["Admin"] = relationship("Admin")
