"""
Authentication middleware for API key-based authentication.
Protects write operations (POST, PATCH, DELETE, PUT) and documentation endpoints.
"""
import os
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import APIKeyHeader
from typing import Optional

# API key header name
API_KEY_HEADER = "X-API-Key"

# Get API key from environment
API_KEY = os.getenv("API_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Create API key header dependency
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def require_api_key(request: Request, api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    Dependency function to require API key authentication.
    
    Args:
        request: FastAPI request object
        api_key: API key from header (injected by FastAPI)
    
    Returns:
        API key string if authentication successful
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Skip authentication in development if API_KEY is not set
    if ENVIRONMENT != "production" and not API_KEY:
        return "dev-bypass"
    
    # In production, API_KEY must be set
    if ENVIRONMENT == "production" and not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY not configured. Server misconfiguration."
        )
    
    # Get API key from header
    provided_key = api_key or request.headers.get(API_KEY_HEADER)
    
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Compare API keys (use constant-time comparison to prevent timing attacks)
    if not _constant_time_compare(provided_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return provided_key


def _constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
    
    Returns:
        True if strings are equal, False otherwise
    """
    if len(a) != len(b):
        return False
    
    result = 0
    for x, y in zip(a.encode(), b.encode()):
        result |= x ^ y
    
    return result == 0


def verify_api_key(provided_key: str) -> bool:
    """
    Verify an API key against the configured API_KEY.
    
    Args:
        provided_key: API key to verify
    
    Returns:
        True if valid, False otherwise
    """
    # Skip authentication in development if API_KEY is not set
    if ENVIRONMENT != "production" and not API_KEY:
        return True
    
    # In production, API_KEY must be set
    if ENVIRONMENT == "production" and not API_KEY:
        return False
    
    if not provided_key:
        return False
    
    return _constant_time_compare(provided_key, API_KEY)


def check_api_key_for_docs(request: Request) -> bool:
    """
    Check API key for documentation endpoints.
    Allows API key via header or query parameter.
    
    Args:
        request: FastAPI request object
    
    Returns:
        True if authentication successful, False otherwise
    """
    # Get API key from header or query parameter
    provided_key = (
        request.headers.get(API_KEY_HEADER) or
        request.query_params.get("api_key")
    )
    
    return verify_api_key(provided_key) if provided_key else False
