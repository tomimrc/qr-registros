# app/utils/password_validator.py

import re
from typing import Optional, List
from app.models.auth_exceptions import PasswordValidationError


class PasswordValidator:
    """Validates passwords against security requirements."""

    # Password requirements
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_NUMBER = True
    REQUIRE_SPECIAL_CHAR = True
    SPECIAL_CHARS = "!@#$%^&*"

    @classmethod
    def validate(
        cls,
        password: str,
        email: Optional[str] = None,
        previous_passwords: Optional[List[str]] = None,
    ) -> None:
        """
        Validate password against security requirements.

        Args:
            password: The password to validate
            email: Email to check similarity against
            previous_passwords: List of hashed previous passwords to check for reuse

        Raises:
            PasswordValidationError: If validation fails with specific error code

        Returns:
            None (raises exception on failure)
        """
        errors = []

        # Check minimum length
        if len(password) < cls.MIN_LENGTH:
            errors.append(
                PasswordValidationError(
                    "PASSWORD_TOO_SHORT",
                    f"La contraseña debe tener al menos {cls.MIN_LENGTH} caracteres",
                )
            )

        # Check for uppercase letter
        if cls.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append(
                PasswordValidationError(
                    "MISSING_UPPERCASE",
                    "La contraseña debe contener al menos 1 letra mayúscula",
                )
            )

        # Check for number
        if cls.REQUIRE_NUMBER and not re.search(r"\d", password):
            errors.append(
                PasswordValidationError(
                    "MISSING_NUMBER",
                    "La contraseña debe contener al menos 1 número",
                )
            )

        # Check for special character
        if cls.REQUIRE_SPECIAL_CHAR:
            if not re.search(rf"[{re.escape(cls.SPECIAL_CHARS)}]", password):
                errors.append(
                    PasswordValidationError(
                        "MISSING_SPECIAL_CHAR",
                        f"La contraseña debe contener al menos 1 carácter especial ({cls.SPECIAL_CHARS})",
                    )
                )

        # Check similarity to email
        if email and cls._is_password_similar_to_email(password, email):
            errors.append(
                PasswordValidationError(
                    "PASSWORD_TOO_SIMILAR_TO_EMAIL",
                    "La contraseña debe diferir de tu correo electrónico",
                )
            )

        # If we have any errors, raise the first one
        if errors:
            raise errors[0]

    @classmethod
    def _is_password_similar_to_email(cls, password: str, email: str) -> bool:
        """
        Check if password is too similar to email.

        Simple heuristic: if email domain or username appears in password (case-insensitive).
        """
        email_lower = email.lower()
        password_lower = password.lower()

        # Check if email domain or username appears in password
        email_parts = email_lower.split("@")
        for part in email_parts:
            if part and len(part) > 3 and part in password_lower:
                return True

        return False
