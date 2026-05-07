# app/middleware/auth_middleware.py

"""Middleware for extracting request context (IP, user agent) for auth operations."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    """Extracts IP address and user agent from requests and stores in request.state."""

    async def dispatch(self, request: Request, call_next):
        """Extract IP address and user agent from request."""
        
        # Extract client IP address, handling proxy headers
        ip_address = self._get_client_ip(request)
        
        # Extract user agent
        user_agent = request.headers.get("user-agent", "")
        
        # Store in request.state for use in auth handlers
        request.state.ip_address = ip_address
        request.state.user_agent = user_agent
        
        response = await call_next(request)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extract client IP from request, handling proxy headers.

        Priority:
        1. X-Forwarded-For (rightmost valid IP in chain)
        2. X-Real-IP
        3. request.client.host
        """
        # Check X-Forwarded-For header (most common in proxied setups)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the rightmost IP address (original client IP)
            ips = [ip.strip() for ip in x_forwarded_for.split(",")]
            for ip in reversed(ips):
                if ip and AuthMiddleware._is_valid_ip(ip):
                    return ip

        # Check X-Real-IP header
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip and AuthMiddleware._is_valid_ip(x_real_ip):
            return x_real_ip

        # Fall back to direct connection IP
        if request.client:
            return request.client.host

        return "unknown"

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Check if string is a valid IP address."""
        # Simple validation: not empty and not localhost proxy marker
        return bool(ip) and ip not in ("127.0.0.1", "::1", "localhost")
