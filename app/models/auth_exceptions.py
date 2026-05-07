# app/models/auth_exceptions.py

class AuthError(Exception):
    """Base exception for authentication errors."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PasswordValidationError(AuthError):
    """Exception raised when password validation fails."""
    def __init__(self, code: str, message: str):
        super().__init__(code, message, 400)


class DuplicateEmailError(AuthError):
    """Exception raised when email already exists."""
    def __init__(self):
        super().__init__("DUPLICATE_EMAIL", "El email ya está registrado", 409)


class AdminInactiveError(AuthError):
    """Exception raised when admin is inactive."""
    def __init__(self):
        super().__init__("ADMIN_INACTIVE", "Cuenta desactivada", 403)


class InvalidCredentialsError(AuthError):
    """Exception raised when credentials are invalid."""
    def __init__(self):
        super().__init__("INVALID_CREDENTIALS", "Email o contraseña incorrectos", 401)


class TenantNotFoundError(AuthError):
    """Exception raised when tenant is not found."""
    def __init__(self):
        super().__init__("TENANT_NOT_FOUND", "Empresa no encontrada", 404)


class InvalidOldPasswordError(AuthError):
    """Exception raised when old password is incorrect."""
    def __init__(self):
        super().__init__("INVALID_OLD_PASSWORD", "La contraseña actual es incorrecta", 400)


class AccountLockedError(AuthError):
    """Exception raised when account is locked due to failed login attempts."""
    def __init__(self, locked_until: str = None):
        message = "Cuenta bloqueada debido a demasiados intentos fallidos"
        if locked_until:
            message += f". Intenta de nuevo después de {locked_until}"
        super().__init__("ACCOUNT_LOCKED", message, 429)
        self.locked_until = locked_until


class TokenExpiredError(AuthError):
    """Exception raised when token has expired."""
    def __init__(self, token_type: str = "access"):
        super().__init__(f"{token_type.upper()}_TOKEN_EXPIRED", f"{token_type.capitalize()} token ha expirado", 401)


class TokenRevokedError(AuthError):
    """Exception raised when token has been revoked."""
    def __init__(self):
        super().__init__("TOKEN_REVOKED", "Token ha sido revocado", 401)


class InvalidTokenTypeError(AuthError):
    """Exception raised when token type is invalid."""
    def __init__(self):
        super().__init__("INVALID_TOKEN_TYPE", "Tipo de token inválido", 400)
