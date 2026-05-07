# app/models/employee.py

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ========== NUEVO: Vínculo con el Tenant ==========
    # Esto es una Foreign Key: le dice a PostgreSQL que este valor
    # DEBE existir en la tabla tenants.id. Si intentás meter un
    # tenant_id inventado, la DB te lo rechaza. Seguridad a nivel DB.
    #
    # nullable=False: Un empleado SIEMPRE debe pertenecer a una empresa.
    # index=True: Crea un índice en esta columna. ¿Por qué?
    #   Porque TODAS las queries van a filtrar por tenant_id.
    #   Sin índice: PostgreSQL recorre TODA la tabla (lento).
    #   Con índice: Va directo a los registros de ese tenant (rápido).
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )
    # ===================================================

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    convenio: Mapped[str] = mapped_column(String(100), nullable=True)
    valor_hora: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ========== NUEVA RELACIÓN: Employee -> Tenant ==========
    # Esto NO crea una columna nueva en la DB.
    # Es un "atajo" de SQLAlchemy para que en Python puedas hacer:
    #   empleado.tenant.name  →  "Restaurante Don Pepe"
    # En vez de hacer otra query manual. SQLAlchemy lo resuelve solo.
    tenant: Mapped["Tenant"] = relationship(back_populates="employees")
    # =========================================================

    # Relaciones existentes (sin cambios)
    devices: Mapped[list["Device"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    attendance_logs: Mapped[list["AttendanceLog"]] = relationship(back_populates="employee")
    jornadas: Mapped[list["Jornada"]] = relationship(back_populates="employee")