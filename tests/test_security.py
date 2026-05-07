import pytest
import time
from unittest.mock import patch
from app.core.security import create_qr_token, verify_qr_token
import uuid

# Un Tenant ID de prueba simulando el UUID de un restaurante
MOCK_TENANT_ID = str(uuid.uuid4())

def test_create_qr_token_format():
    """Prueba que el token generado tenga exactamente 2 partes separadas por ':'"""
    token = create_qr_token(MOCK_TENANT_ID)
    partes = token.split(":")
    
    assert len(partes) == 2
    assert partes[0].isdigit() # La primera parte debe ser el timestamp (números)
    assert len(partes[1]) == 32 # La segunda parte debe ser la firma truncada a 32 caracteres

def test_verify_qr_token_success():
    """Prueba que un token recién generado sea aceptado como válido"""
    token = create_qr_token(MOCK_TENANT_ID)
    
    es_valido = verify_qr_token(MOCK_TENANT_ID, token)
    assert es_valido is True

def test_verify_qr_token_wrong_tenant():
    """Prueba que un empleado NO pueda usar el QR de la Sucursal A en la Sucursal B"""
    token_sucursal_a = create_qr_token(MOCK_TENANT_ID)
    
    otro_tenant_id = str(uuid.uuid4())
    es_valido = verify_qr_token(otro_tenant_id, token_sucursal_a)
    
    assert es_valido is False # El sistema debe rechazarlo

def test_verify_qr_token_altered_signature():
    """Prueba que si un hacker modifica un número del token, sea rechazado"""
    token = create_qr_token(MOCK_TENANT_ID)
    
    # Cambiamos el último caracter de la firma para simular un ataque
    token_hackeado = token[:-1] + "X"
    
    es_valido = verify_qr_token(MOCK_TENANT_ID, token_hackeado)
    assert es_valido is False

@patch('app.core.security.time.time')
def test_verify_qr_token_expired(mock_time):
    """Prueba que el token caduque exactamente después de los 60 segundos (Antifraude WhatsApp)"""
    
    # 1. Congelamos el tiempo simulando que son las 12:00:00
    mock_time.return_value = 1600000000.0
    token = create_qr_token(MOCK_TENANT_ID)
    
    # 2. El empleado escanea a las 12:00:45 (45 segundos después) -> DEBE FUNCIONAR
    mock_time.return_value = 1600000045.0
    assert verify_qr_token(MOCK_TENANT_ID, token, max_age_seconds=60) is True
    
    # 3. Alguien escanea una foto del QR a las 12:01:05 (65 segundos después) -> DEBE FALLAR
    mock_time.return_value = 1600000065.0
    assert verify_qr_token(MOCK_TENANT_ID, token, max_age_seconds=60) is False