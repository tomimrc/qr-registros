import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import uuid

# Importamos tu aplicación FastAPI principal y el generador de tokens
from app.main import app 
from app.core.security import create_qr_token

# TestClient es un navegador virtual que FastAPI nos da para testear
client = TestClient(app)

# Usamos @patch para poner "dobles de riesgo" en los servicios de Base de Datos
@patch("app.routers.attendance.ValidationService.validate_request", new_callable=AsyncMock)
@patch("app.routers.attendance.AttendanceService.register_event", new_callable=AsyncMock)
def test_fichaje_exitoso_entrada(mock_register_event, mock_validate_request):
    """Prueba que el endpoint de fichaje funcione correctamente cuando los datos son válidos"""
    
    # 1. Preparar datos falsos simulando un celular
    tenant_id = str(uuid.uuid4())
    qr_token = create_qr_token(tenant_id)
    device_token = "dev-celular-prueba-123"
    fake_employee_id = uuid.uuid4()

    # 2. Configurar los "dobles de riesgo" (Qué devolverían los servicios si la DB estuviera perfecta)
    mock_validate_request.return_value = ("127.0.0.1", fake_employee_id)
    mock_register_event.return_value = {"tipo": "entrada", "timestamp": "2026-04-07T08:00:00"}

    # 3. Armar el paquete de datos (El payload JSON que viaja desde el HTML)
    payload = {
        "tenant_id": tenant_id,
        "device_token": device_token,
        "qr_token": qr_token
    }

    # 4. Disparar el Request a nuestra propia API
    response = client.post("/attendance/register", json=payload)

    # 5. Afirmaciones (Asserts) - Verificamos que la API hizo su trabajo
    assert response.status_code == 200
    
    data = response.json()
    assert "Registro de entrada exitoso" in data["message"]
    assert data["data"]["tipo"] == "entrada"
    
    # Verificamos que la API haya llamado a nuestros servicios de DB exactamente 1 vez
    mock_validate_request.assert_called_once()
    mock_register_event.assert_called_once()


@patch("app.routers.attendance.ValidationService.validate_request", new_callable=AsyncMock)
def test_fichaje_rechazado_qr_falso(mock_validate_request):
    """Prueba que la API tire error si el frontend manda un QR falso o vacío"""
    
    payload = {
        "tenant_id": str(uuid.uuid4()),
        "device_token": "dev-celular-prueba-123",
        "qr_token": "token_inventado_por_un_hacker"
    }

    # Acá NO mockeamos nada más, porque el token va a fallar apenas FastAPI lo reciba
    # y la función del QR (que no está mockeada) va a lanzar una excepción o error.
    
    # (Nota: En este caso, hacemos que nuestro mock tire una excepción que simule 
    # la que tiraría ValidationService si el QR falla)
    from fastapi import HTTPException
    mock_validate_request.side_effect = HTTPException(status_code=400, detail="QR inválido o expirado")

    response = client.post("/attendance/register", json=payload)

    # Verificamos que la API lo rebotó con un error 400 Bad Request
    assert response.status_code == 400
    assert response.json()["detail"] == "QR inválido o expirado"