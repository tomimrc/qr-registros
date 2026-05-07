# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import hmac
import hashlib
import time
import bcrypt
from app.core.config import settings

def _normalize_password(password: str) -> str:
    """Convierte cualquier password en una huella ASCII fija para evitar el límite de bcrypt."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Convierte una contraseña en un hash bcrypt usando una huella SHA-256 previa."""
    normalized_password = _normalize_password(password).encode("utf-8")
    hashed_password = bcrypt.hashpw(normalized_password, bcrypt.gensalt())
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara password ingresado contra el hash guardado en DB"""
    try:
        normalized_password = _normalize_password(plain_password).encode("utf-8")
        stored_hash = hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password
        if bcrypt.checkpw(normalized_password, stored_hash):
            return True

        # Compatibilidad con hashes existentes generados antes del prehash.
        legacy_password = plain_password.encode("utf-8")
        return bcrypt.checkpw(legacy_password, stored_hash)
    except Exception:
        return False

# =========================================================
# TOKENS JWT (Para el Login del Dashboard de Administrador)
# =========================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a JWT token.
    data = {"sub": str(admin_id), "tenant_id": str(tenant_id)}
    El token expira en ACCESS_TOKEN_EXPIRE_MINUTES minutos.
    
    This is maintained for backward compatibility.
    For new code, use TokenManager.create_access_token()
    """
    from app.core.token_manager import TokenManager
    
    # Extract admin_id and tenant_id from data
    sub = data.get("sub")
    tenant_id = data.get("tenant_id")
    
    if not sub or not tenant_id:
        # Fall back to old behavior for legacy code
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Use new TokenManager
    return TokenManager.create_access_token(sub, tenant_id, expires_delta)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT token.
    Devuelve el payload o None si es inválido/expirado.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

# =========================================================
# TOKENS HMAC (Para el Escaneo del QR Dinámico de Empleados)
# =========================================================

def create_qr_token(tenant_id: str) -> str:
    """Genera un token firmado con el timestamp actual para el QR"""
    timestamp = int(time.time())
    message = f"{tenant_id}:{timestamp}"
    # Achicamos la firma a 32 caracteres para no exceder límite del QR
    signature = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{timestamp}:{signature}"

def verify_qr_token(tenant_id: str, token: str, max_age_seconds: int = 60) -> bool:
    """Verifica la firma y que el token del QR no esté vencido"""
    try:
        parts = token.split(":")
        if len(parts) != 2:
            return False
        
        ts_str, signature = parts
        timestamp = int(ts_str)
        
        if int(time.time()) - timestamp > max_age_seconds:
            return False 
        
        expected_message = f"{tenant_id}:{timestamp}"
        expected_signature = hmac.new(settings.SECRET_KEY.encode(), expected_message.encode(), hashlib.sha256).hexdigest()[:32]
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False