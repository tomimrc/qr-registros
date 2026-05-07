# app/core/token_blacklist.py

"""In-memory token blacklist for token revocation/logout functionality."""

from datetime import datetime, timezone
from typing import Dict, Optional
import asyncio


class TokenBlacklist:
    """In-memory blacklist for revoked tokens (e.g., after logout)."""

    # Storage: {token_jti: expiration_timestamp}
    _blacklist: Dict[str, float] = {}
    _lock = asyncio.Lock()

    # Cleanup task handle
    _cleanup_task: Optional[asyncio.Task] = None

    @classmethod
    async def add(cls, token_jti: str, expiration_timestamp: float) -> None:
        """
        Add token to blacklist.

        Args:
            token_jti: Unique token identifier (usually from 'jti' claim)
            expiration_timestamp: Unix timestamp when token expires
        """
        async with cls._lock:
            cls._blacklist[token_jti] = expiration_timestamp

    @classmethod
    async def is_blacklisted(cls, token_jti: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            token_jti: Unique token identifier

        Returns:
            bool: True if token is blacklisted and not expired
        """
        async with cls._lock:
            if token_jti not in cls._blacklist:
                return False

            expiration = cls._blacklist[token_jti]
            current_time = datetime.now(timezone.utc).timestamp()

            # If token has naturally expired, remove from blacklist
            if current_time > expiration:
                del cls._blacklist[token_jti]
                return False

            return True

    @classmethod
    async def cleanup(cls) -> None:
        """
        Clean up expired entries from blacklist.

        This is a background task that periodically removes expired tokens.
        """
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                async with cls._lock:
                    current_time = datetime.now(timezone.utc).timestamp()
                    expired_tokens = [
                        token_jti
                        for token_jti, expiration in cls._blacklist.items()
                        if current_time > expiration
                    ]

                    for token_jti in expired_tokens:
                        del cls._blacklist[token_jti]

                    if expired_tokens:
                        print(f"🧹 Cleaned up {len(expired_tokens)} expired tokens from blacklist")

            except Exception as e:
                print(f"❌ Error in token blacklist cleanup: {e}")

    @classmethod
    async def clear(cls) -> None:
        """Clear all entries from blacklist (useful for testing)."""
        async with cls._lock:
            cls._blacklist.clear()

    @classmethod
    def get_stats(cls) -> Dict[str, int]:
        """Get statistics about the blacklist."""
        return {
            "total_entries": len(cls._blacklist),
        }
