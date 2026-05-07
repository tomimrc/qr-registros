# app/models/attendance.py

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base





class TipoRegistro(str, enum.Enum):
    entrada = "entrada"
    salida = "salida"


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ========== NUEVO: tenant_id ==========
    # En los logs es CRÍTICO tener tenant_id directo.
    # ¿Por qué? Porque los logs son la tabla que MÁS crece.
    # Si tenés 50 empresas con 20 empleados cada una fichando 2 veces al día,
    # son 2000 registros DIARIOS. En un año: 730,000 filas.
    # Filtrar eso sin índice en tenant_id sería un desastre de performance.
    # Con el índice, PostgreSQL salta directo a los logs de ESA empresa.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    # =======================================

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    tipo: Mapped[TipoRegistro] = mapped_column(
        Enum(TipoRegistro), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    device_token: Mapped[str] = mapped_column(String(255), nullable=True)
    validacion_ok: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relaciones
    tenant: Mapped["Tenant"] = relationship(back_populates="attendance_logs")
    employee: Mapped["Employee"] = relationship(back_populates="attendance_logs")
    @property
    def tipo_registro(self):
        return self.tipo