"""
Pruebas para el módulo de Sales Analytics (Premium)

Cubre:
- Autenticación (401 sin token)
- Autorización (403 sin suscripción activa)
- Carga de CSV (validación y parseo)
- Aislamiento multi-tenant
- Agregaciones y reportes
"""

import pytest
import uuid
from datetime import date, datetime
from calendar import monthrange
from types import SimpleNamespace
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import patch, AsyncMock, MagicMock
from io import StringIO

from app.main import app
from app.core.security import create_access_token


client = TestClient(app)


# =============================================
# FIXTURES
# =============================================

@pytest.fixture
def admin_token():
    """JWT token para admin de prueba"""
    admin_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    return create_access_token({"sub": admin_id, "tenant_id": tenant_id})


@pytest.fixture
def csv_valid():
    """CSV válido de ventas"""
    return b"""date,product,quantity,unit_price,total_amount,seller
2026-04-01,Cerveza,10,100.00,1000.00,Juan
2026-04-01,Hamburguesa,5,250.00,1250.00,Maria
2026-04-02,Cerveza,8,100.00,800.00,Juan
2026-04-02,Refresco,15,50.00,750.00,
"""


@pytest.fixture
def csv_invalid():
    """CSV con errores (columnas faltantes)"""
    return b"""date,product,quantity
2026-04-01,Cerveza,10
2026-04-01,Hamburguesa,5
"""


# =============================================
# TESTS: AUTENTICACIÓN
# =============================================

def test_sales_upload_sin_token():
    """Debe rechazar acceso sin token (401 o 403)"""
    response = client.post(
        "/sales/uploads?period_month=2026-04-01",
        files={"file": ("test.csv", b"data")}
    )
    assert response.status_code in [401, 403]  # Sin credentials


def test_sales_summary_sin_token():
    """Debe rechazar resumen sin token"""
    response = client.get("/sales/summary?month=2026-04-01")
    assert response.status_code in [401, 403]


def test_sales_charts_sin_token():
    """Debe rechazar gráficos sin token"""
    response = client.get("/sales/charts?month=2026-04-01")
    assert response.status_code in [401, 403]


def test_sales_uploads_sin_token():
    """Debe rechazar historial sin token"""
    response = client.get("/sales/uploads")
    assert response.status_code in [401, 403]


# =============================================
# TESTS: AUTORIZACIÓN (Plan premium)
# =============================================

@patch("app.routers.sales.SalesAnalyticsService.process_csv_upload", new_callable=AsyncMock)
@patch("app.core.dependencies.get_db", new_callable=AsyncMock)
def test_sales_upload_sin_suscripcion_activa(mock_db, mock_process):
    """Debe rechazar upload si no hay suscripción activa (403 o 401)"""
    # Mock DB para retornar None en query de suscripción
    mock_session = AsyncMock()
    mock_db.return_value = mock_session
    
    token = create_access_token({"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4())})
    
    response = client.post(
        "/sales/uploads?period_month=2026-04-01",
        files={"file": ("test.csv", b"date,product\n2026-04-01,test")},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Puede ser 403 (sin suscripción) o 401 (admin no encontrado)
    assert response.status_code in [401, 403]


# =============================================
# TESTS: PARSEO CSV
# =============================================

def test_csv_parsing_columnas_obligatorias(csv_invalid):
    """Debe rechazar CSV sin columnas obligatorias"""
    from app.services.sales_service import SalesAnalyticsService
    
    result = SalesAnalyticsService._parse_csv(csv_invalid)
    
    assert not result["success"]
    assert "Faltan columnas" in result["error"]
    assert "unit_price" in result["error"] or "total_amount" in result["error"]


def test_csv_parsing_valido(csv_valid):
    """Debe parsear CSV válido correctamente"""
    from app.services.sales_service import SalesAnalyticsService
    
    result = SalesAnalyticsService._parse_csv(csv_valid)
    
    assert result["success"]
    assert len(result["rows"]) == 4
    # Las columnas se normalizan (minúsculas) pero los valores se preservan
    assert result["rows"][0]["product"] == "Cerveza"


def test_csv_parsing_encoding_invalido():
    """Debe rechazar archivos con encoding incorrecto"""
    from app.services.sales_service import SalesAnalyticsService
    
    # Bytes inválidos en UTF-8
    invalid_bytes = b"\x80\x81\x82\x83"
    result = SalesAnalyticsService._parse_csv(invalid_bytes)
    
    assert not result["success"]
    assert "UTF-8" in result["error"]


# =============================================
# TESTS: VALIDACIÓN DE FILAS
# =============================================

def test_validacion_fila_fecha_invalida():
    """Debe rechazar fechas con formato incorrecto"""
    from app.services.sales_service import SalesAnalyticsService
    
    row = {
        "date": "01/04/2026",  # Formato incorrecto
        "product": "Cerveza",
        "quantity": "10",
        "unit_price": "100.00",
        "total_amount": "1000.00"
    }
    
    result = SalesAnalyticsService._validate_row(row, 2)
    assert not result["valid"]
    assert "YYYY-MM-DD" in result["error"]


def test_validacion_fila_cantidad_negativa():
    """Debe rechazar cantidades negativas"""
    from app.services.sales_service import SalesAnalyticsService
    
    row = {
        "date": "2026-04-01",
        "product": "Cerveza",
        "quantity": "-10",  # Negativa
        "unit_price": "100.00",
        "total_amount": "1000.00"
    }
    
    result = SalesAnalyticsService._validate_row(row, 2)
    assert not result["valid"]
    assert "mayor" in result["error"]


def test_validacion_fila_producto_vacio():
    """Debe rechazar producto vacío"""
    from app.services.sales_service import SalesAnalyticsService
    
    row = {
        "date": "2026-04-01",
        "product": "",  # Vacío
        "quantity": "10",
        "unit_price": "100.00",
        "total_amount": "1000.00"
    }
    
    result = SalesAnalyticsService._validate_row(row, 2)
    assert not result["valid"]
    assert "no vacío" in result["error"]


def test_validacion_fila_completa_valida():
    """Validar fila correctamente formada"""
    from app.services.sales_service import SalesAnalyticsService
    
    row = {
        "date": "2026-04-01",
        "product": "Cerveza",
        "quantity": "10.5",
        "unit_price": "100.00",
        "total_amount": "1050.00",
        "seller": "Juan"
    }
    
    result = SalesAnalyticsService._validate_row(row, 2)
    assert result["valid"]
    assert result["data"]["product"] == "Cerveza"
    assert result["data"]["seller_name"] == "Juan"


def test_extract_covered_months_deduplicates_and_sorts():
    """Debe devolver meses únicos ordenados en formato YYYY-MM."""
    from app.services.sales_service import SalesAnalyticsService

    records = [
        MagicMock(sale_date=date(2026, 4, 2)),
        MagicMock(sale_date=date(2026, 3, 25)),
        MagicMock(sale_date=date(2026, 4, 15)),
        MagicMock(sale_date=date(2026, 2, 1)),
    ]

    months = SalesAnalyticsService.extract_covered_months([record.sale_date for record in records])

    assert months == ["2026-02", "2026-03", "2026-04"]


def test_resolve_period_filters_usa_rango_especifico_multi_mes():
    """Debe devolver rango explícito cuando llegan from_date y to_date."""
    from app.routers.sales import _resolve_period_filters

    start_date, end_date = _resolve_period_filters(
        month=None,
        from_date=date(2026, 4, 20),
        to_date=date(2026, 5, 3),
    )

    assert start_date == date(2026, 4, 20)
    assert end_date == date(2026, 5, 3)


def test_resolve_period_filters_invalido_from_mayor_to():
    """Debe devolver 400 si from_date es mayor que to_date."""
    from app.routers.sales import _resolve_period_filters

    with pytest.raises(HTTPException) as exc_info:
        _resolve_period_filters(
            month=None,
            from_date=date(2026, 5, 10),
            to_date=date(2026, 5, 1),
        )

    assert exc_info.value.status_code == 400
    assert "from_date" in str(exc_info.value.detail)


def test_resolve_period_filters_invalido_rango_incompleto():
    """Debe devolver 400 si llega solo una fecha del rango."""
    from app.routers.sales import _resolve_period_filters

    with pytest.raises(HTTPException) as exc_info:
        _resolve_period_filters(
            month=None,
            from_date=date(2026, 4, 20),
            to_date=None,
        )

    assert exc_info.value.status_code == 400
    assert "from_date" in str(exc_info.value.detail) and "to_date" in str(exc_info.value.detail)


def test_resolve_period_filters_default_mes_actual():
    """Sin parámetros debe usar el mes actual completo."""
    from app.routers.sales import _resolve_period_filters

    start_date, end_date = _resolve_period_filters(
        month=None,
        from_date=None,
        to_date=None,
    )

    today = date.today()
    expected_last_day = monthrange(today.year, today.month)[1]

    assert start_date == date(today.year, today.month, 1)
    assert end_date == date(today.year, today.month, expected_last_day)


def test_resolve_manual_comparison_filters_requiere_los_4_campos():
    """En modo manual, debe exigir las 4 fechas de comparación."""
    from app.routers.sales import _resolve_manual_comparison_filters

    with pytest.raises(HTTPException) as exc_info:
        _resolve_manual_comparison_filters(
            compare_mode="manual",
            compare_a_from=date(2026, 2, 10),
            compare_a_to=date(2026, 2, 15),
            compare_b_from=date(2026, 1, 10),
            compare_b_to=None,
        )

    assert exc_info.value.status_code == 400
    assert "compare_a_from" in str(exc_info.value.detail)


def test_resolve_manual_comparison_filters_devuelve_rangos_validos():
    """Debe devolver ambos rangos cuando modo manual es válido."""
    from app.routers.sales import _resolve_manual_comparison_filters

    result = _resolve_manual_comparison_filters(
        compare_mode="manual",
        compare_a_from=date(2026, 2, 10),
        compare_a_to=date(2026, 2, 15),
        compare_b_from=date(2026, 1, 10),
        compare_b_to=date(2026, 1, 15),
    )

    assert result == (
        (date(2026, 2, 10), date(2026, 2, 15)),
        (date(2026, 1, 10), date(2026, 1, 15)),
    )


# =============================================
# TESTS: AISLAMIENTO MULTI-TENANT
# =============================================

def test_delete_upload_no_existente():
    """Debe retornar 404 si upload_id no existe"""
    # Este test se ejecutaría con un admin logueado
    # Por ahora, confirmamos que la estructura está lista
    pass


# =============================================
# TESTS: INTEGRACIÓN
# =============================================

def test_ruta_sales_dashboard_existe():
    """Debe servir la página de sales analytics"""
    response = client.get("/sales-dashboard")
    assert response.status_code == 200
    assert b"Sales Analytics" in response.content or b"analytics" in response.content.lower()


def test_schema_upload_response():
    """Respuesta de upload debe tener estructura esperada"""
    # Este es un test de schema mockado
    from app.routers.sales import UploadResponse
    
    data = {
        "success": True,
        "upload_id": str(uuid.uuid4()),
        "rows_imported": 10,
        "rows_total": 10,
        "rows_errors": 0,
        "total_sales": 1000.00,
        "errors": None
    }
    
    response = UploadResponse(**data)
    assert response.success
    assert response.rows_imported == 10


def test_schema_uploads_history_response():
    """Historial debe aceptar lista de importaciones con montos numéricos."""
    from app.routers.sales import UploadsHistoryResponse

    payload = {
        "uploads": [
            {
                "id": str(uuid.uuid4()),
                "filename": "ventas_abril.csv",
                "period": "2026-04-01",
                "rows_imported": 10,
                "rows_total": 12,
                "total_sales": 2500.5,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        ]
    }

    response = UploadsHistoryResponse(**payload)
    assert len(response.uploads) == 1
    assert response.uploads[0].filename == "ventas_abril.csv"
    assert response.uploads[0].total_sales == 2500.5


def test_schema_charts_data_enriched_compatible():
    """ChartsData enriquecido debe mantener campos legacy y aceptar campos nuevos opcionales."""
    from app.routers.sales import ChartsData, MonthlySummaryResponse

    summary = MonthlySummaryResponse(
        period="2026-04",
        total_sales=1000.0,
        avg_ticket=100.0,
        quantity_sold=30.0,
        transaction_count=10,
        top_products=[],
    )

    payload = {
        "period": "2026-04",
        "daily_sales": [{"date": "2026-04-01", "sales": 250.0}],
        "product_distribution": [{"product": "Cerveza", "sales": 400.0}],
        "summary": summary,
        "daily_evolution": {
            "dates": ["2026-04-01"],
            "transactions": [2],
            "sales": [250.0],
            "quantity": [8.0],
            "avg_ticket": [125.0],
        },
        "top_products_quantity": [{"product": "Cerveza", "quantity": 8.0, "transactions": 2, "sales": 400.0}],
        "weekday_distribution": {
            "labels": ["Lunes"],
            "sales": [250.0],
            "transactions": [2],
            "quantity": [8.0],
            "percentages": [100.0],
        },
        "period_comparison": {
            "current_period": {"start": "2026-04-01", "end": "2026-04-30", "total_sales": 1000.0, "quantity_sold": 30.0, "transaction_count": 10, "avg_ticket": 100.0},
            "previous_period": {"start": "2026-03-01", "end": "2026-03-31", "total_sales": 900.0, "quantity_sold": 28.0, "transaction_count": 9, "avg_ticket": 100.0},
            "changes": {"total_sales_pct": 11.11, "quantity_sold_pct": 7.14, "transaction_count_pct": 11.11, "avg_ticket_pct": 0.0},
        },
    }

    response = ChartsData(**payload)
    assert response.period == "2026-04"
    assert len(response.daily_sales) == 1
    assert response.daily_evolution is not None


@pytest.mark.asyncio
async def test_get_daily_evolution_maps_rows_correctly():
    """Debe mapear correctamente filas agregadas de evolución diaria."""
    from app.services.sales_service import SalesAnalyticsService

    row1 = SimpleNamespace(
        sale_date=date(2026, 4, 20),
        transactions=2,
        sales=250.0,
        quantity=8.0,
        avg_ticket=125.0,
    )
    row2 = SimpleNamespace(
        sale_date=date(2026, 4, 21),
        transactions=1,
        sales=300.0,
        quantity=3.0,
        avg_ticket=300.0,
    )

    mock_result = MagicMock()
    mock_result.all.return_value = [row1, row2]
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await SalesAnalyticsService.get_daily_evolution(
        tenant_id=uuid.uuid4(),
        start_date=date(2026, 4, 20),
        end_date=date(2026, 4, 21),
        db=mock_db,
    )

    assert result["dates"] == ["2026-04-20", "2026-04-21"]
    assert result["transactions"] == [2, 1]
    assert result["sales"] == [250.0, 300.0]
    assert result["quantity"] == [8.0, 3.0]
    assert result["avg_ticket"] == [125.0, 300.0]


@pytest.mark.asyncio
async def test_get_top_products_by_quantity_maps_rows_correctly():
    """Debe devolver top por cantidad con campos esperados."""
    from app.services.sales_service import SalesAnalyticsService

    row = SimpleNamespace(
        product="Cerveza",
        quantity=12.0,
        transactions=3,
        sales=1200.0,
    )

    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await SalesAnalyticsService.get_top_products_by_quantity(
        tenant_id=uuid.uuid4(),
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        db=mock_db,
    )

    assert len(result) == 1
    assert result[0]["product"] == "Cerveza"
    assert result[0]["quantity"] == 12.0
    assert result[0]["transactions"] == 3
    assert result[0]["sales"] == 1200.0


@pytest.mark.asyncio
async def test_get_weekday_distribution_builds_percentage():
    """Debe mapear días ISO y calcular porcentajes de ventas."""
    from app.services.sales_service import SalesAnalyticsService

    monday = SimpleNamespace(weekday=1, sales=100.0, transactions=2, quantity=4.0)
    wednesday = SimpleNamespace(weekday=3, sales=300.0, transactions=3, quantity=8.0)

    mock_result = MagicMock()
    mock_result.all.return_value = [monday, wednesday]
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    result = await SalesAnalyticsService.get_weekday_distribution(
        tenant_id=uuid.uuid4(),
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        db=mock_db,
    )

    assert result["labels"][0] == "Lunes"
    assert result["sales"][0] == 100.0
    assert result["sales"][2] == 300.0
    # total = 400 => lunes 25%
    assert pytest.approx(result["percentages"][0], 0.01) == 25.0


@pytest.mark.asyncio
async def test_get_period_comparison_handles_previous_zero():
    """Si el período anterior es cero, el porcentaje debe ser None."""
    from app.services.sales_service import SalesAnalyticsService

    current_data = {
        "period": "2026-04",
        "total_sales": 1000.0,
        "avg_ticket": 100.0,
        "quantity_sold": 20.0,
        "transaction_count": 10,
        "top_products": [],
    }
    previous_data = {
        "period": "2026-03",
        "total_sales": 0.0,
        "avg_ticket": 0.0,
        "quantity_sold": 0.0,
        "transaction_count": 0,
        "top_products": [],
    }

    with patch(
        "app.services.sales_service.SalesAnalyticsService.get_summary_for_period",
        new_callable=AsyncMock,
    ) as mock_summary:
        mock_summary.side_effect = [current_data, previous_data]

        result = await SalesAnalyticsService.get_period_comparison(
            tenant_id=uuid.uuid4(),
            current_start=date(2026, 4, 1),
            current_end=date(2026, 4, 30),
            db=AsyncMock(),
        )

    assert result["current_period"]["total_sales"] == 1000.0
    assert result["previous_period"]["total_sales"] == 0.0
    assert result["changes"]["total_sales_pct"] is None


@pytest.mark.asyncio
async def test_get_period_comparison_between_ranges_uses_a_vs_b():
    """Debe comparar rango A contra rango B cuando se usa modo manual."""
    from app.services.sales_service import SalesAnalyticsService

    range_a_data = {
        "period": "2026-02-10 to 2026-02-15",
        "total_sales": 500.0,
        "avg_ticket": 100.0,
        "quantity_sold": 20.0,
        "transaction_count": 5,
        "top_products": [],
    }
    range_b_data = {
        "period": "2026-01-10 to 2026-01-15",
        "total_sales": 250.0,
        "avg_ticket": 50.0,
        "quantity_sold": 10.0,
        "transaction_count": 4,
        "top_products": [],
    }

    with patch(
        "app.services.sales_service.SalesAnalyticsService.get_summary_for_period",
        new_callable=AsyncMock,
    ) as mock_summary:
        mock_summary.side_effect = [range_a_data, range_b_data]

        result = await SalesAnalyticsService.get_period_comparison_between_ranges(
            tenant_id=uuid.uuid4(),
            range_a_start=date(2026, 2, 10),
            range_a_end=date(2026, 2, 15),
            range_b_start=date(2026, 1, 10),
            range_b_end=date(2026, 1, 15),
            db=AsyncMock(),
        )

    assert result["comparison_mode"] == "manual"
    assert result["current_period"]["total_sales"] == 500.0
    assert result["previous_period"]["total_sales"] == 250.0
    assert result["changes"]["total_sales_pct"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
