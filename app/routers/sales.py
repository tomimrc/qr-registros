# app/routers/sales.py

import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.admin import Admin
from app.models.sales import SalesUpload
from app.services.sales_service import SalesAnalyticsService
from app.core.dependencies import require_sales_analytics_access

router = APIRouter()


def _resolve_period_filters(
    month: date | None,
    from_date: date | None,
    to_date: date | None,
) -> tuple[date, date]:
    """Resuelve período de consulta para modo mensual o rango explícito."""
    if (from_date and not to_date) or (to_date and not from_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para usar fechas específicas debes enviar from_date y to_date",
        )

    if from_date and to_date:
        if from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date no puede ser mayor que to_date",
            )
        return from_date, to_date

    period_month = month or date.today()
    return SalesAnalyticsService.get_month_bounds(period_month)


def _resolve_manual_comparison_filters(
    compare_mode: str,
    compare_a_from: date | None,
    compare_a_to: date | None,
    compare_b_from: date | None,
    compare_b_to: date | None,
) -> tuple[tuple[date, date], tuple[date, date]] | None:
    """Valida y resuelve rangos de comparación manual (A vs B)."""
    if compare_mode != "manual":
        return None

    provided = [compare_a_from, compare_a_to, compare_b_from, compare_b_to]
    if any(value is None for value in provided):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para comparación manual debes enviar compare_a_from, compare_a_to, compare_b_from y compare_b_to",
        )

    assert compare_a_from is not None and compare_a_to is not None
    assert compare_b_from is not None and compare_b_to is not None

    if compare_a_from > compare_a_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="En rango A, compare_a_from no puede ser mayor que compare_a_to",
        )

    if compare_b_from > compare_b_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="En rango B, compare_b_from no puede ser mayor que compare_b_to",
        )

    return (compare_a_from, compare_a_to), (compare_b_from, compare_b_to)


# =============================================
# SCHEMAS (Pydantic models para request/response)
# =============================================

class SalesUploadRequest(BaseModel):
    """Metadata para procesar un CSV de ventas"""
    period_month: date  # Mes que cubre el CSV (ej: 2026-04-15 → usa april 2026)


class UploadResponse(BaseModel):
    """Respuesta después de procesar CSV"""
    success: bool
    upload_id: str | None
    rows_imported: int
    rows_total: int
    rows_errors: int
    total_sales: float
    covered_months: list[str] = []
    errors: list[dict] | None = None


class MonthlySummaryResponse(BaseModel):
    """Resumen de ventas de un mes"""
    period: str
    total_sales: float
    avg_ticket: float
    quantity_sold: float
    transaction_count: int
    top_products: list[dict]


class ChartsData(BaseModel):
    """Datos listos para renderizar en charts del frontend"""
    period: str
    daily_sales: list[dict]  # [{"date": "2026-04-01", "sales": 1500}]
    product_distribution: list[dict]  # [{"product": "...", "sales": 500}]
    summary: MonthlySummaryResponse
    daily_evolution: dict | None = None
    top_products_quantity: list[dict] | None = None
    weekday_distribution: dict | None = None
    period_comparison: dict | None = None


class SalesUploadMetadata(BaseModel):
    """Metadata de una importación en historial"""
    id: str
    filename: str
    period: str
    rows_imported: int
    rows_total: int
    total_sales: float
    uploaded_at: str


class UploadsHistoryResponse(BaseModel):
    uploads: list[SalesUploadMetadata]


# =============================================
# ENDPOINTS
# =============================================

@router.post(
    "/uploads",
    response_model=UploadResponse,
    summary="Subir y procesar CSV de ventas",
    tags=["Sales Analytics"]
)
async def upload_sales_csv(
    file: UploadFile = File(...),
    period_month: date = Query(..., description="Mes a importar: YYYY-MM-DD"),
    admin: Admin = Depends(require_sales_analytics_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Subir un archivo CSV de ventas.
    
    El usuario DEBE tener una suscripción activa a Sales Analytics.
    
    Validaciones:
    - CSV debe tener columnas: date, product, quantity, unit_price, total_amount
    - Columna opcional: seller
    - No mezclar datos: tenant_id se obtiene del token JWT, nunca del payload
    
    Ejemplo de CSV válido:
    ```
    date,product,quantity,unit_price,total_amount,seller
    2026-04-01,Cerveza,10,100.00,1000.00,Juan
    2026-04-01,Hamburguesa,5,250.00,1250.00,Maria
    ```
    """
    try:
        # Leer contenido del archivo
        content = await file.read()
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo vacío"
            )
        
        if len(content) > 5_000_000:  # 5 MB max
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Archivo demasiado grande (máx 5 MB)"
            )
        
        # Procesar CSV
        result = await SalesAnalyticsService.process_csv_upload(
            tenant_id=admin.tenant_id,  # ← Seguridad: derivado del admin
            csv_content=content,
            filename=file.filename or "upload.csv",
            period_month=period_month,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result.get("error", "Error desconocido al procesar CSV")
            )
        
        return UploadResponse(
            success=True,
            upload_id=result["upload_id"],
            rows_imported=result["rows_imported"],
            rows_total=result["rows_total"],
            rows_errors=result["rows_errors"],
            total_sales=result["total_sales"],
            covered_months=result.get("covered_months", []),
            errors=result.get("errors")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar archivo: {str(e)}"
        )


@router.get(
    "/summary",
    response_model=MonthlySummaryResponse,
    summary="Resumen de ventas de un mes",
    tags=["Sales Analytics"]
)
async def get_sales_summary(
    month: date | None = Query(None, description="Mes a consultar: YYYY-MM-DD"),
    from_date: date | None = Query(None, description="Fecha inicio: YYYY-MM-DD"),
    to_date: date | None = Query(None, description="Fecha fin: YYYY-MM-DD"),
    admin: Admin = Depends(require_sales_analytics_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener resumen de ventas (totales, ticket promedio, top productos).
    
    Solo retorna datos del tenant autenticado.
    """
    start_date, end_date = _resolve_period_filters(month, from_date, to_date)

    summary = await SalesAnalyticsService.get_summary_for_period(
        tenant_id=admin.tenant_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )
    
    return MonthlySummaryResponse(**summary)


@router.get(
    "/charts",
    response_model=ChartsData,
    summary="Datos formateados para gráficos",
    tags=["Sales Analytics"]
)
async def get_sales_charts(
    month: date | None = Query(None, description="Mes a consultar: YYYY-MM-DD"),
    from_date: date | None = Query(None, description="Fecha inicio: YYYY-MM-DD"),
    to_date: date | None = Query(None, description="Fecha fin: YYYY-MM-DD"),
    view: str = Query("overview", pattern="^(overview|evolution|products|heatmap|comparison)$"),
    compare_mode: str = Query("auto", pattern="^(auto|manual)$"),
    compare_a_from: date | None = Query(None, description="Comparacion manual rango A desde: YYYY-MM-DD"),
    compare_a_to: date | None = Query(None, description="Comparacion manual rango A hasta: YYYY-MM-DD"),
    compare_b_from: date | None = Query(None, description="Comparacion manual rango B desde: YYYY-MM-DD"),
    compare_b_to: date | None = Query(None, description="Comparacion manual rango B hasta: YYYY-MM-DD"),
    admin: Admin = Depends(require_sales_analytics_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener datos ya agregados y formateados para renderizar gráficos
    en el frontend (daily sales, product distribution, etc).
    
    Retorna series listas para Chart.js o similar.
    """
    from sqlalchemy import and_, func
    from app.models.sales import SalesRecord
    
    start_date, end_date = _resolve_period_filters(month, from_date, to_date)
    
    # Query: ventas diarias
    daily_query = await db.execute(
        select(
            SalesRecord.sale_date,
            func.sum(SalesRecord.total_amount).label("sales")
        ).where(
            and_(
                SalesRecord.tenant_id == admin.tenant_id,
                SalesRecord.sale_date >= start_date,
                SalesRecord.sale_date <= end_date
            )
        ).group_by(SalesRecord.sale_date)
        .order_by(SalesRecord.sale_date)
    )
    daily_sales_data = daily_query.all()
    
    # Query: distribución de productos
    products_query = await db.execute(
        select(
            SalesRecord.product,
            func.sum(SalesRecord.total_amount).label("sales")
        ).where(
            and_(
                SalesRecord.tenant_id == admin.tenant_id,
                SalesRecord.sale_date >= start_date,
                SalesRecord.sale_date <= end_date
            )
        ).group_by(SalesRecord.product)
        .order_by(func.sum(SalesRecord.total_amount).desc())
        .limit(10)
    )
    products_data = products_query.all()
    
    # Obtener resumen
    summary = await SalesAnalyticsService.get_summary_for_period(
        tenant_id=admin.tenant_id,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    daily_sales = [
        {
            "date": str(row.sale_date),
            "sales": float(row.sales)
        }
        for row in daily_sales_data
    ]
    product_distribution = [
        {
            "product": row.product,
            "sales": float(row.sales)
        }
        for row in products_data
    ]

    daily_evolution = None
    top_products_quantity = None
    weekday_distribution = None
    period_comparison = None

    manual_ranges = _resolve_manual_comparison_filters(
        compare_mode=compare_mode,
        compare_a_from=compare_a_from,
        compare_a_to=compare_a_to,
        compare_b_from=compare_b_from,
        compare_b_to=compare_b_to,
    )

    if view in ["overview", "evolution"]:
        daily_evolution = await SalesAnalyticsService.get_daily_evolution(
            tenant_id=admin.tenant_id,
            start_date=start_date,
            end_date=end_date,
            db=db,
        )

    if view in ["overview", "products"]:
        top_products_quantity = await SalesAnalyticsService.get_top_products_by_quantity(
            tenant_id=admin.tenant_id,
            start_date=start_date,
            end_date=end_date,
            db=db,
        )

    if view in ["overview", "heatmap"]:
        weekday_distribution = await SalesAnalyticsService.get_weekday_distribution(
            tenant_id=admin.tenant_id,
            start_date=start_date,
            end_date=end_date,
            db=db,
        )

    if view == "comparison" and manual_ranges is not None:
        (range_a_start, range_a_end), (range_b_start, range_b_end) = manual_ranges
        period_comparison = await SalesAnalyticsService.get_period_comparison_between_ranges(
            tenant_id=admin.tenant_id,
            range_a_start=range_a_start,
            range_a_end=range_a_end,
            range_b_start=range_b_start,
            range_b_end=range_b_end,
            db=db,
        )
    elif view in ["overview", "comparison"]:
        period_comparison = await SalesAnalyticsService.get_period_comparison(
            tenant_id=admin.tenant_id,
            current_start=start_date,
            current_end=end_date,
            db=db,
        )
    
    return ChartsData(
        period=summary["period"],
        daily_sales=daily_sales,
        product_distribution=product_distribution,
        summary=MonthlySummaryResponse(**summary),
        daily_evolution=daily_evolution,
        top_products_quantity=top_products_quantity,
        weekday_distribution=weekday_distribution,
        period_comparison=period_comparison,
    )


@router.get(
    "/uploads",
    response_model=UploadsHistoryResponse,
    summary="Historial de importaciones CSV",
    tags=["Sales Analytics"]
)
async def get_uploads_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Admin = Depends(require_sales_analytics_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Listar historial de archivos importados por este tenant.
    
    Útil para auditoría y para volver a descargar o referencia.
    """
    try:
        history = await SalesAnalyticsService.get_uploads_history(
            tenant_id=admin.tenant_id,
            limit=limit,
            offset=offset,
            db=db
        )

        return UploadsHistoryResponse(
            uploads=[SalesUploadMetadata(**u) for u in history["uploads"]]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener historial: {str(e)}"
        )


@router.delete(
    "/uploads/{upload_id}",
    summary="Eliminar una importación de ventas",
    tags=["Sales Analytics"],
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_sales_upload(
    upload_id: uuid.UUID,
    admin: Admin = Depends(require_sales_analytics_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Borrar un upload y todos sus registros de ventas.
    
    Importante: Solo puedes borrar uploads de tu propio tenant.
    """
    # Verificar que el upload existe y pertenece a este tenant
    upload = await db.execute(
        select(SalesUpload).where(
            SalesUpload.id == upload_id,
            SalesUpload.tenant_id == admin.tenant_id
        )
    )
    upload_obj = upload.scalar_one_or_none()
    
    if not upload_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Importación no encontrada o no tienes permisos para acceder"
        )
    
    # Borrar (cascade automático borra los sales_records también)
    await db.delete(upload_obj)
    await db.commit()
    
    return None  # 204 No Content
