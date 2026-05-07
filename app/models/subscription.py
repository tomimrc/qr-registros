# app/models/subscription.py

import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, Date, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    # === Identificación ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # FK a tenant - ÚNICA (1:1)
    # Si intenta crear otra suscripción para el mismo tenant, violará unique constraint
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # === Plan info ===
    # Códigos de plan: "basic", "pro", "enterprise", etc.
    # Por ahora solo usamos "sales_analytics" ya que es el único premium
    plan_code: Mapped[str] = mapped_column(String(50), default="sales_analytics", nullable=False)

    # === Control de acceso ===
    # Si active=False, el tenant no puede usar features premium
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # === Vigencia ===
    # Rango válido para el plan (ej: primer día del mes hasta último)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # === Auditoría ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # === Relación inversa ===
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="subscription",
        uselist=False  # 1:1 relationship
    )
