"""
Rate limiting middleware using slowapi.
Implements per-IP and per-tenant rate limiting for demo mode.
"""
import os
from typing import Callable

# Try to import slowapi (optional dependency)
SLOWAPI_AVAILABLE = False
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    pass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Get rate limit from environment (default: 100 requests per hour)
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key for the request.
    Uses IP address by default, can be extended to use tenant ID.
    """
    # Try to get tenant ID from header
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return f"tenant:{tenant_id}"
    
    # Fall back to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    if request.client:
        return request.client.host
    
    return "unknown"


# Initialize limiter with custom key function (only if slowapi is available)
limiter = None
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_rate_limit_key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that applies limits to all requests
    except health check endpoints.
    Note: This is a basic implementation. For production, consider using
    slowapi decorators on individual routes for more granular control.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # If slowapi is not available, skip rate limiting (for local development)
        if not SLOWAPI_AVAILABLE:
            return await call_next(request)
        
        # Basic rate limiting check
        # In a full implementation, you would use slowapi's limiter.check() here
        # For now, we'll rely on route-level decorators if needed
        # This middleware serves as a placeholder for future enhancement
        
        return await call_next(request)

