# app/models/tenant.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.attendance import AttendanceLog
    from app.models.device import Device
    from app.models.employee import Employee
    from app.models.jornada import Jornada
    from app.models.subscription import Subscription
    from app.models.tenant_feature import TenantFeature


class Tenant(Base):
    __tablename__ = "tenants"

    # === Identificación ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Nombre visible: "Restaurante Don Pepe"
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Slug para URLs amigables: "don-pepe"
    # unique=True: No pueden existir dos tenants con el mismo slug.
    # Esto te protege si después querés hacer URLs tipo:
    #   tuapp.com/don-pepe/dashboard
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Timezone operativo del cliente
    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="America/Argentina/Buenos_Aires",
    )

    # === Control de acceso ===
    # Cliente deja de pagar → is_active = False → nadie de esa empresa puede fichar.
    # No borrás datos, solo "apagás" el tenant.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # === Auditoría ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # === Relaciones inversas ===
    # Estas NO crean columnas en la DB.
    # Son "atajos" para navegar desde Python:
    #
    #   tenant = await get_tenant(id)
    #   tenant.employees    → [Juan, Pedro, María]
    #   tenant.devices      → [iPhone de Juan, Android de Pedro]
    #   tenant.attendance_logs → [todos los fichajes de esa empresa]
    #   tenant.jornadas     → [todas las jornadas de esa empresa]
    #
    # back_populates conecta la relación en ambas direcciones:
    #   tenant.employees ↔ employee.tenant

    employees: Mapped[list["Employee"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    jornadas: Mapped[list["Jornada"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    # Agregar dentro de la clase Tenant, junto a las otras relaciones
    admins: Mapped[list["Admin"]] = relationship(
        "Admin", back_populates="tenant", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    features: Mapped[list["TenantFeature"]] = relationship(
        "TenantFeature", back_populates="tenant", cascade="all, delete-orphan"
    )