# app/utils/rate_limiter.py

"""Rate limiting decorators for auth endpoints using slowapi."""

from functools import wraps
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Callable, Any


# Initialize limiter with custom key function
limiter = Limiter(key_func=get_remote_address)


def rate_limit_by_ip(limit: str) -> Callable:
    """
    Rate limit decorator by IP address.
    
    Args:
        limit: Rate limit string (e.g., "5/15 minutes", "3/hour")
    """
    def decorator(func: Callable) -> Callable:
        return limiter.limit(limit)(func)
    return decorator


def rate_limit_by_user(limit: str) -> Callable:
    """
    Rate limit decorator by authenticated user.
    
    Args:
        limit: Rate limit string (e.g., "10/hour")
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            if not request:
                # Find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request and hasattr(request, "state") and hasattr(request.state, "admin"):
                # Rate limit by admin_id for authenticated endpoints
                admin = request.state.admin
                key = f"user:{admin.id}"
            else:
                # Fall back to IP
                key = get_remote_address(request)

            return await func(*args, **kwargs)

        return wrapper
    return decorator


class RateLimitHelper:
    """Helper class for rate limiting operations."""

    # Rate limit configurations
    LOGIN_LIMIT = "5/15 minutes"  # 5 attempts per 15 minutes
    REGISTER_LIMIT = "3/1 hour"   # 3 attempts per hour
    PASSWORD_CHANGE_LIMIT = "10/1 hour"  # 10 attempts per hour

    @staticmethod
    def get_rate_limit_headers(limit_info: dict) -> dict:
        """
        Generate RateLimit headers for response.

        Args:
            limit_info: Dictionary with limit information

        Returns:
            dict: Headers to add to response
        """
        return {
            "RateLimit-Limit": str(limit_info.get("limit", 0)),
            "RateLimit-Remaining": str(limit_info.get("remaining", 0)),
            "RateLimit-Reset": str(limit_info.get("reset", 0)),
        }
