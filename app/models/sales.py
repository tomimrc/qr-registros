# app/models/sales.py

import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SalesUpload(Base):
    """
    Metadatos de cada importación de CSV que un tenant sube.
    Permite rastrear qué se importó, cuándo y con qué resultados.
    """
    __tablename__ = "sales_uploads"

    # === Identificación ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Aislamiento por tenant (crítico para multi-tenancy)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # === Metadata del archivo ===
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Período que cubre el archivo (ej: mayo 2026)
    period_month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Cantidad de filas procesadas exitosamente
    rows_imported: Mapped[int] = mapped_column(default=0)
    
    # Cantidad total de filas en el CSV (excluyendo header)
    rows_total: Mapped[int] = mapped_column(default=0)
    
    # Total de ventas en este archivo (validación rápida)
    total_sales: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00")
    )

    # === Auditoría ===
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # === Relaciones ===
    # Cada importación puede tener muchos registros de ventas
    sales_records: Mapped[list["SalesRecord"]] = relationship(
        "SalesRecord",
        back_populates="upload",
        cascade="all, delete-orphan"
    )


class SalesRecord(Base):
    """
    Cada línea normalizada del CSV de ventas.
    Separar del upload permite queries analíticas más precisas 
    (agregar, filtrar, comparar entre períodos).
    """
    __tablename__ = "sales_records"

    # === Identificación ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # FK al upload del que proviene esta fila
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Aislamiento por tenant (duplicado para queries directas sin join)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # === Datos de la venta (CSV normalizados) ===
    # Fecha de la transacción (para analítica diaria)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Nombre del producto/servicio vendido
    product: Mapped[str] = mapped_column(String(255), nullable=False)

    # Cantidad vendida
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    # Precio unitario en moneda del tenant (asumimos ARS)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Total de la venta (quantity * unit_price)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Quién vendió (opcional, puede venir null del CSV)
    seller_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # === Metadatos CSV ===
    # Número de fila en el archivo original (útil para debugging)
    csv_row_number: Mapped[int] = mapped_column(nullable=False)

    # Cualquier nota o error de validación que ocurrió
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Auditoría ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # === Relaciones ===
    upload: Mapped["SalesUpload"] = relationship(
        "SalesUpload",
        back_populates="sales_records"
    )
