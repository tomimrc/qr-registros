# app/services/sales_service.py

import csv
import io
import uuid
from datetime import date, datetime
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.sql import text
from app.models.sales import SalesUpload, SalesRecord
from app.models.tenant import Tenant


class SalesAnalyticsService:
    """
    Servicio centralizado para:
    - Parsear y validar CSV de ventas
    - Persistir datos normalizados
    - Generar resúmenes y agregaciones
    
    Siempre recibe tenant_id como primer parámetro (seguridad multi-tenant).
    """

    # === CSV SCHEMA ===
    REQUIRED_COLUMNS = ["date", "product", "quantity", "unit_price", "total_amount"]
    OPTIONAL_COLUMNS = ["seller"]
    
    # Validaciones por columna
    COLUMN_TYPES = {
        "date": "YYYY-MM-DD",
        "product": "texto (max 255 chars)",
        "quantity": "número decimal",
        "unit_price": "número decimal",
        "total_amount": "número decimal",
        "seller": "texto opcional (max 100 chars)"
    }

    @staticmethod
    async def process_csv_upload(
        tenant_id: uuid.UUID,
        csv_content: bytes,
        filename: str,
        period_month: date,
        db: AsyncSession
    ) -> dict:
        """
        Procesa un CSV de ventas: parsea, valida, persiste.
        
        Retorna:
        {
            "success": bool,
            "upload_id": UUID (si success=True),
            "rows_imported": int,
            "rows_total": int,
            "rows_errors": int,
            "total_sales": Decimal,
            "errors": [{"row": int, "error": str}]
        }
        """
        # 1. Verificar que el tenant exista y esté activo
        tenant = await db.get(Tenant, tenant_id)
        if not tenant or not tenant.is_active:
            return {
                "success": False,
                "error": "Tenant no encontrado o inactivo"
            }

        # 2. Parsear CSV y validar encabezados
        parse_result = SalesAnalyticsService._parse_csv(csv_content)
        if not parse_result["success"]:
            return {
                "success": False,
                "error": parse_result["error"]
            }

        rows_data = parse_result["rows"]
        
        # 3. Crear registro de SalesUpload (metadata)
        upload = SalesUpload(
            tenant_id=tenant_id,
            filename=filename,
            period_month=period_month,
            rows_total=len(rows_data)
        )
        db.add(upload)
        await db.flush()  # Genera el ID del upload sin commitear

        # 4. Validar y crear SalesRecord por cada fila
        errors = []
        total_sales = Decimal("0.00")
        rows_imported = 0
        sale_dates_imported = []

        for row_number, row_data in enumerate(rows_data, start=2):  # Empieza en 2 (header es 1)
            validation = SalesAnalyticsService._validate_row(row_data, row_number)
            
            if not validation["valid"]:
                errors.append({
                    "row": row_number,
                    "error": validation["error"]
                })
                continue

            # Crear registro de venta
            record_data = validation["data"]
            sales_record = SalesRecord(
                upload_id=upload.id,
                tenant_id=tenant_id,
                sale_date=record_data["sale_date"],
                product=record_data["product"],
                quantity=record_data["quantity"],
                unit_price=record_data["unit_price"],
                total_amount=record_data["total_amount"],
                seller_name=record_data.get("seller_name"),
                csv_row_number=row_number
            )
            db.add(sales_record)
            rows_imported += 1
            total_sales += record_data["total_amount"]
            sale_dates_imported.append(record_data["sale_date"])

        # 5. Actualizar metadata del upload
        upload.rows_imported = rows_imported
        upload.total_sales = total_sales

        # 6. Persistir todo
        await db.commit()

        covered_months = SalesAnalyticsService.extract_covered_months(sale_dates_imported)

        return {
            "success": True,
            "upload_id": str(upload.id),
            "rows_imported": rows_imported,
            "rows_total": len(rows_data),
            "rows_errors": len(errors),
            "total_sales": float(total_sales),
            "covered_months": covered_months,
            "errors": errors if errors else None
        }

    @staticmethod
    def _parse_csv(csv_content: bytes) -> dict:
        """
        Parsea contenido CSV y valida estructura básica.
        
        Retorna:
        {
            "success": bool,
            "rows": [dict, ...] (si success),
            "error": str (si no success)
        }
        """
        try:
            # Decodificar bytes a string (asume UTF-8)
            csv_text = csv_content.decode("utf-8")
            
            # Parsear con csv.DictReader
            reader = csv.DictReader(io.StringIO(csv_text))
            
            if not reader.fieldnames:
                return {
                    "success": False,
                    "error": "CSV vacío o sin encabezados"
                }
            
            # Validar que existan columnas requeridas (case-insensitive)
            fieldnames_lower = [f.lower().strip() for f in reader.fieldnames]
            missing_columns = [
                col for col in SalesAnalyticsService.REQUIRED_COLUMNS
                if col.lower() not in fieldnames_lower
            ]
            
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Faltan columnas obligatorias: {', '.join(missing_columns)}"
                }
            
            # Convertir a lista de dicts normalizado (keys minúsculas)
            rows = []
            for row in reader:
                # Normalizar: llaves minúsculas, sin espacios
                normalized_row = {
                    k.lower().strip(): v.strip() if isinstance(v, str) else v
                    for k, v in row.items()
                }
                rows.append(normalized_row)
            
            if not rows:
                return {
                    "success": False,
                    "error": "CSV no contiene datos (solo encabezados)"
                }
            
            return {
                "success": True,
                "rows": rows
            }
        
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": "El archivo no es UTF-8. Por favor usa codificación UTF-8."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error al parsear CSV: {str(e)}"
            }

    @staticmethod
    def _validate_row(row: dict, row_number: int) -> dict:
        """
        Valida que una fila de CSV cumpla con tipos y rangos esperados.
        
        Retorna:
        {
            "valid": bool,
            "data": {parsed row dict} (si valid=True),
            "error": str (si valid=False)
        }
        """
        try:
            # Validar y convertir campos obligatorios
            
            # Date
            try:
                sale_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            except ValueError:
                return {
                    "valid": False,
                    "error": "Formato de fecha inválido. Usa YYYY-MM-DD (ej: 2026-04-15)"
                }
            except KeyError:
                return {
                    "valid": False,
                    "error": "Falta columna 'date'"
                }
            
            # Product
            product = row.get("product", "").strip()
            if not product or len(product) > 255:
                return {
                    "valid": False,
                    "error": "Producto debe ser texto no vacío (máx 255 caracteres)"
                }
            
            # Quantity
            try:
                quantity = Decimal(row.get("quantity", "0"))
                if quantity <= 0:
                    return {
                        "valid": False,
                        "error": "Cantidad debe ser mayor a 0"
                    }
            except (InvalidOperation, ValueError):
                return {
                    "valid": False,
                    "error": "Cantidad debe ser un número válido"
                }
            
            # Unit Price
            try:
                unit_price = Decimal(row.get("unit_price", "0"))
                if unit_price < 0:
                    return {
                        "valid": False,
                        "error": "Precio unitario no puede ser negativo"
                    }
            except (InvalidOperation, ValueError):
                return {
                    "valid": False,
                    "error": "Precio unitario debe ser un número válido"
                }
            
            # Total Amount
            try:
                total_amount = Decimal(row.get("total_amount", "0"))
                if total_amount < 0:
                    return {
                        "valid": False,
                        "error": "Total no puede ser negativo"
                    }
            except (InvalidOperation, ValueError):
                return {
                    "valid": False,
                    "error": "Total debe ser un número válido"
                }
            
            # Seller (opcional)
            seller_name = row.get("seller", "").strip() or None
            if seller_name and len(seller_name) > 100:
                seller_name = seller_name[:100]
            
            return {
                "valid": True,
                "data": {
                    "sale_date": sale_date,
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_amount": total_amount,
                    "seller_name": seller_name
                }
            }
        
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error de validación: {str(e)}"
            }

    @staticmethod
    def extract_covered_months(sale_dates: list[date]) -> list[str]:
        """Retorna meses únicos en formato YYYY-MM ordenados cronológicamente."""
        return sorted({sale_date.strftime("%Y-%m") for sale_date in sale_dates})

    @staticmethod
    def get_month_bounds(period_month: date) -> tuple[date, date]:
        """Retorna primer y último día del mes de la fecha recibida."""
        year = period_month.year
        month = period_month.month

        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        import datetime as dt
        month_end = month_end - dt.timedelta(days=1)
        return month_start, month_end

    @staticmethod
    def build_period_label(start_date: date, end_date: date) -> str:
        """Construye etiqueta de período para respuestas de API."""
        if start_date.day == 1:
            month_start, month_end = SalesAnalyticsService.get_month_bounds(start_date)
            if month_start == start_date and month_end == end_date:
                return f"{start_date.year}-{start_date.month:02d}"
        return f"{start_date.isoformat()} to {end_date.isoformat()}"

    @staticmethod
    async def get_summary_for_period(
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        db: AsyncSession,
        period_label: str | None = None,
    ) -> dict:
        """Retorna resumen de ventas para un período arbitrario (inclusive)."""
        # 1. Totales básicos
        basic_query = await db.execute(
            select(
                func.sum(SalesRecord.total_amount).label("total_sales"),
                func.avg(SalesRecord.total_amount).label("avg_ticket"),
                func.sum(SalesRecord.quantity).label("quantity_sold"),
                func.count(SalesRecord.id).label("transaction_count")
            ).where(
                and_(
                    SalesRecord.tenant_id == tenant_id,
                    SalesRecord.sale_date >= start_date,
                    SalesRecord.sale_date <= end_date
                )
            )
        )
        basic = basic_query.one()

        # 2. Top 5 productos
        top_products_query = await db.execute(
            select(
                SalesRecord.product,
                func.sum(SalesRecord.total_amount).label("sales"),
                func.count(SalesRecord.id).label("count")
            ).where(
                and_(
                    SalesRecord.tenant_id == tenant_id,
                    SalesRecord.sale_date >= start_date,
                    SalesRecord.sale_date <= end_date
                )
            ).group_by(SalesRecord.product)
            .order_by(func.sum(SalesRecord.total_amount).desc())
            .limit(5)
        )
        top_products = top_products_query.all()

        return {
            "period": period_label or SalesAnalyticsService.build_period_label(start_date, end_date),
            "total_sales": float(basic.total_sales or 0),
            "avg_ticket": float(basic.avg_ticket or 0),
            "quantity_sold": float(basic.quantity_sold or 0),
            "transaction_count": int(basic.transaction_count or 0),
            "top_products": [
                {
                    "product": row.product,
                    "sales": float(row.sales),
                    "count": int(row.count)
                }
                for row in top_products
            ]
        }

    @staticmethod
    async def get_monthly_summary(
        tenant_id: uuid.UUID,
        period_month: date,
        db: AsyncSession
    ) -> dict:
        """
        Retorna un resumen de ventas para un mes específico.
        
        Query: SalesRecord con sale_date en ese mes
        Agregaciones:
        - total_sales (SUM)
        - avg_ticket (AVG de total_amount)
        - quantity_sold (SUM)
        - transaction_count (COUNT)
        - top_products (TOP 5 by sales)
        """
        month_start, month_end = SalesAnalyticsService.get_month_bounds(period_month)
        return await SalesAnalyticsService.get_summary_for_period(
            tenant_id=tenant_id,
            start_date=month_start,
            end_date=month_end,
            db=db,
            period_label=f"{period_month.year}-{period_month.month:02d}",
        )

    @staticmethod
    async def get_daily_evolution(
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        db: AsyncSession,
    ) -> dict:
        """Retorna evolución diaria con múltiples métricas."""
        result = await db.execute(
            select(
                SalesRecord.sale_date.label("sale_date"),
                func.count(SalesRecord.id).label("transactions"),
                func.sum(SalesRecord.total_amount).label("sales"),
                func.sum(SalesRecord.quantity).label("quantity"),
                func.avg(SalesRecord.total_amount).label("avg_ticket"),
            ).where(
                and_(
                    SalesRecord.tenant_id == tenant_id,
                    SalesRecord.sale_date >= start_date,
                    SalesRecord.sale_date <= end_date,
                )
            ).group_by(SalesRecord.sale_date)
            .order_by(SalesRecord.sale_date)
        )

        rows = result.all()
        return {
            "dates": [row.sale_date.isoformat() for row in rows],
            "transactions": [int(row.transactions or 0) for row in rows],
            "sales": [float(row.sales or 0) for row in rows],
            "quantity": [float(row.quantity or 0) for row in rows],
            "avg_ticket": [float(row.avg_ticket or 0) for row in rows],
        }

    @staticmethod
    async def get_top_products_by_quantity(
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        db: AsyncSession,
        limit: int = 5,
    ) -> list[dict]:
        """Top productos por cantidad vendida."""
        result = await db.execute(
            select(
                SalesRecord.product,
                func.sum(SalesRecord.quantity).label("quantity"),
                func.count(SalesRecord.id).label("transactions"),
                func.sum(SalesRecord.total_amount).label("sales"),
            ).where(
                and_(
                    SalesRecord.tenant_id == tenant_id,
                    SalesRecord.sale_date >= start_date,
                    SalesRecord.sale_date <= end_date,
                )
            ).group_by(SalesRecord.product)
            .order_by(func.sum(SalesRecord.quantity).desc())
            .limit(limit)
        )

        rows = result.all()
        return [
            {
                "product": row.product,
                "quantity": float(row.quantity or 0),
                "transactions": int(row.transactions or 0),
                "sales": float(row.sales or 0),
            }
            for row in rows
        ]

    @staticmethod
    async def get_weekday_distribution(
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        db: AsyncSession,
    ) -> dict:
        """Distribución de ventas por día de semana (Lunes a Domingo)."""
        result = await db.execute(
            text(
                """
                SELECT
                    EXTRACT(ISODOW FROM sale_date)::int AS weekday,
                    SUM(total_amount) AS sales,
                    COUNT(*) AS transactions,
                    SUM(quantity) AS quantity
                FROM sales_records
                WHERE tenant_id = :tenant_id
                  AND sale_date >= :start_date
                  AND sale_date <= :end_date
                GROUP BY EXTRACT(ISODOW FROM sale_date)
                ORDER BY weekday
                """
            ),
            {
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        labels = [
            "Lunes",
            "Martes",
            "Miercoles",
            "Jueves",
            "Viernes",
            "Sabado",
            "Domingo",
        ]
        sales = [0.0] * 7
        transactions = [0] * 7
        quantity = [0.0] * 7

        for row in result.all():
            idx = int(row.weekday) - 1
            if 0 <= idx < 7:
                sales[idx] = float(row.sales or 0)
                transactions[idx] = int(row.transactions or 0)
                quantity[idx] = float(row.quantity or 0)

        total_sales = sum(sales)
        percentages = [((value / total_sales) * 100) if total_sales else 0 for value in sales]

        return {
            "labels": labels,
            "sales": sales,
            "transactions": transactions,
            "quantity": quantity,
            "percentages": percentages,
        }

    @staticmethod
    async def get_period_comparison(
        tenant_id: uuid.UUID,
        current_start: date,
        current_end: date,
        db: AsyncSession,
    ) -> dict:
        """Compara período actual contra período anterior equivalente."""
        days = (current_end - current_start).days
        prev_end = current_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days)

        current = await SalesAnalyticsService.get_summary_for_period(
            tenant_id=tenant_id,
            start_date=current_start,
            end_date=current_end,
            db=db,
        )
        previous = await SalesAnalyticsService.get_summary_for_period(
            tenant_id=tenant_id,
            start_date=prev_start,
            end_date=prev_end,
            db=db,
        )

        def pct_change(current_value: float, previous_value: float) -> float | None:
            if previous_value == 0:
                return None
            return ((current_value - previous_value) / previous_value) * 100

        return {
            "comparison_mode": "auto",
            "labels": {
                "current": "Periodo actual",
                "previous": "Periodo anterior",
            },
            "current_period": {
                "start": current_start.isoformat(),
                "end": current_end.isoformat(),
                "total_sales": current["total_sales"],
                "quantity_sold": current["quantity_sold"],
                "transaction_count": current["transaction_count"],
                "avg_ticket": current["avg_ticket"],
            },
            "previous_period": {
                "start": prev_start.isoformat(),
                "end": prev_end.isoformat(),
                "total_sales": previous["total_sales"],
                "quantity_sold": previous["quantity_sold"],
                "transaction_count": previous["transaction_count"],
                "avg_ticket": previous["avg_ticket"],
            },
            "changes": {
                "total_sales_pct": pct_change(current["total_sales"], previous["total_sales"]),
                "quantity_sold_pct": pct_change(current["quantity_sold"], previous["quantity_sold"]),
                "transaction_count_pct": pct_change(current["transaction_count"], previous["transaction_count"]),
                "avg_ticket_pct": pct_change(current["avg_ticket"], previous["avg_ticket"]),
            },
        }

    @staticmethod
    async def get_period_comparison_between_ranges(
        tenant_id: uuid.UUID,
        range_a_start: date,
        range_a_end: date,
        range_b_start: date,
        range_b_end: date,
        db: AsyncSession,
    ) -> dict:
        """Compara dos rangos arbitrarios A vs B."""
        range_a = await SalesAnalyticsService.get_summary_for_period(
            tenant_id=tenant_id,
            start_date=range_a_start,
            end_date=range_a_end,
            db=db,
        )
        range_b = await SalesAnalyticsService.get_summary_for_period(
            tenant_id=tenant_id,
            start_date=range_b_start,
            end_date=range_b_end,
            db=db,
        )

        def pct_change(current_value: float, previous_value: float) -> float | None:
            if previous_value == 0:
                return None
            return ((current_value - previous_value) / previous_value) * 100

        return {
            "comparison_mode": "manual",
            "labels": {
                "current": "Rango A",
                "previous": "Rango B",
            },
            "current_period": {
                "start": range_a_start.isoformat(),
                "end": range_a_end.isoformat(),
                "total_sales": range_a["total_sales"],
                "quantity_sold": range_a["quantity_sold"],
                "transaction_count": range_a["transaction_count"],
                "avg_ticket": range_a["avg_ticket"],
            },
            "previous_period": {
                "start": range_b_start.isoformat(),
                "end": range_b_end.isoformat(),
                "total_sales": range_b["total_sales"],
                "quantity_sold": range_b["quantity_sold"],
                "transaction_count": range_b["transaction_count"],
                "avg_ticket": range_b["avg_ticket"],
            },
            "changes": {
                "total_sales_pct": pct_change(range_a["total_sales"], range_b["total_sales"]),
                "quantity_sold_pct": pct_change(range_a["quantity_sold"], range_b["quantity_sold"]),
                "transaction_count_pct": pct_change(range_a["transaction_count"], range_b["transaction_count"]),
                "avg_ticket_pct": pct_change(range_a["avg_ticket"], range_b["avg_ticket"]),
            },
        }

    @staticmethod
    async def get_uploads_history(
        tenant_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        db: AsyncSession = None
    ) -> dict:
        """
        Retorna historial de importaciones del tenant.
        """
        query = await db.execute(
            select(SalesUpload)
            .where(SalesUpload.tenant_id == tenant_id)
            .order_by(SalesUpload.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        uploads = query.scalars().all()
        
        return {
            "uploads": [
                {
                    "id": str(u.id),
                    "filename": u.filename,
                    "period": u.period_month.isoformat(),
                    "rows_imported": int(u.rows_imported or 0),
                    "rows_total": int(u.rows_total or 0),
                    "total_sales": float(u.total_sales or 0),
                    "uploaded_at": u.uploaded_at.isoformat()
                }
                for u in uploads
            ]
        }
