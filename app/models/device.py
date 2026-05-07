# app/models/device.py

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ========== NUEVO: tenant_id ==========
    # ¿Por qué también en Device si ya Employee tiene tenant_id?
    # Porque es REDUNDANCIA INTENCIONAL para seguridad.
    # Cuando alguien ficha, el backend recibe el device_token.
    # Si solo tuvieras tenant_id en Employee, tendrías que:
    #   1. Buscar el device → 2. Buscar el employee → 3. Verificar tenant
    # Con tenant_id directo en Device:
    #   1. Buscar device WHERE tenant_id = X → Listo. Una sola query.
    # Esto se llama "desnormalización controlada" y es MUY común en SaaS.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    # =======================================

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    device_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relaciones
    tenant: Mapped["Tenant"] = relationship(back_populates="devices")
    employee: Mapped["Employee"] = relationship(back_populates="devices")