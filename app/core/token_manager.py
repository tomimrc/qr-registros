# app/core/token_manager.py

"""JWT token management with support for access and refresh tokens."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.core.config import settings
from app.models.auth_exceptions import TokenExpiredError, InvalidTokenTypeError


class TokenManager:
    """Manages JWT token creation, validation, and differentiation."""

    ALGORITHM = settings.ALGORITHM
    SECRET_KEY = settings.SECRET_KEY

    # Token expiration times (in minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES  # 60 minutes
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    @classmethod
    def create_access_token(
        cls,
        sub: str,  # admin_id
        tenant_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a short-lived access token (15 minutes by default).

        Args:
            sub: Subject (admin_id)
            tenant_id: Tenant ID
            expires_delta: Custom expiration (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)

        Returns:
            str: JWT token
        """
        return cls._create_token(
            token_type="access",
            sub=sub,
            tenant_id=tenant_id,
            expires_delta=expires_delta
            or timedelta(minutes=15),  # Access tokens expire in 15 minutes
        )

    @classmethod
    def create_refresh_token(
        cls,
        sub: str,  # admin_id
        tenant_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a long-lived refresh token (7 days by default).

        Args:
            sub: Subject (admin_id)
            tenant_id: Tenant ID
            expires_delta: Custom expiration (defaults to 7 days)

        Returns:
            str: JWT token
        """
        return cls._create_token(
            token_type="refresh",
            sub=sub,
            tenant_id=tenant_id,
            expires_delta=expires_delta
            or timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    @classmethod
    def _create_token(
        cls,
        token_type: str,
        sub: str,
        tenant_id: str,
        expires_delta: timedelta,
    ) -> str:
        """
        Internal method to create a JWT token with type.

        Args:
            token_type: Type of token ("access" or "refresh")
            sub: Subject (admin_id)
            tenant_id: Tenant ID
            expires_delta: Expiration delta

        Returns:
            str: JWT token
        """
        to_encode = {
            "sub": sub,
            "tenant_id": tenant_id,
            "type": token_type,
            "jti": str(uuid.uuid4()),  # Unique token identifier for blacklisting
            "iat": datetime.now(timezone.utc),
        }

        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            cls.SECRET_KEY,
            algorithm=cls.ALGORITHM,
        )
        return encoded_jwt

    @classmethod
    def verify_access_token(cls, token: str) -> Dict[str, Any]:
        """
        Verify and decode an access token.

        Args:
            token: JWT token to verify

        Returns:
            Dict: Token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenTypeError: If token is not an access token
        """
        return cls.decode_token_with_type_check(token, expected_type="access")

    @classmethod
    def verify_refresh_token(cls, token: str) -> Dict[str, Any]:
        """
        Verify and decode a refresh token.

        Args:
            token: JWT token to verify

        Returns:
            Dict: Token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenTypeError: If token is not a refresh token
        """
        return cls.decode_token_with_type_check(token, expected_type="refresh")

    @classmethod
    def decode_token_with_type_check(
        cls,
        token: str,
        expected_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decode a token and optionally verify its type.

        Args:
            token: JWT token to decode
            expected_type: Expected token type (None = no check)

        Returns:
            Dict: Token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenTypeError: If token type doesn't match expected
        """
        try:
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM],
            )
        except JWTError as e:
            if "exp" in str(e).lower():
                raise TokenExpiredError()
            raise

        # Verify token type if expected_type is specified
        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type:
                raise InvalidTokenTypeError()

        return payload

    @classmethod
    def decode_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without type checking (backward compatibility).

        Args:
            token: JWT token

        Returns:
            Dict: Token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM],
            )
            return payload
        except JWTError:
            return None

    @classmethod
    def get_token_expiration(cls, token: str) -> Optional[datetime]:
        """
        Get token expiration time without verifying signature.

        Args:
            token: JWT token

        Returns:
            datetime: Expiration time or None
        """
        try:
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM],
                options={"verify_exp": False},
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        except JWTError:
            pass
        return None
