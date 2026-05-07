# app/models/jornada.py

import uuid
from datetime import datetime, date
from sqlalchemy import Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Jornada(Base):
    __tablename__ = "jornadas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ========== NUEVO: tenant_id ==========
    # Misma lógica: cuando el admin del Restaurante Pepe
    # pida "mostrame las jornadas de esta semana", la query será:
    #   SELECT * FROM jornadas WHERE tenant_id = 'uuid-pepe' AND fecha BETWEEN ...
    # Sin el índice en tenant_id, PostgreSQL revisaría las jornadas
    # de TODAS las empresas para encontrar las de Pepe. Inaceptable.
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
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    total_horas: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)

    # Relaciones
    tenant: Mapped["Tenant"] = relationship(back_populates="jornadas")
    employee: Mapped["Employee"] = relationship(back_populates="jornadas")