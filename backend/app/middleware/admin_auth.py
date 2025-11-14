"""
Admin authentication middleware for sensitive operations.
Implements role-based access control (RBAC) for delete and admin operations.
"""
import os
import secrets
from typing import Optional
from fastapi import HTTPException, Header
from datetime import datetime, timedelta
import jwt

# Admin credentials (in production, use environment variables or database)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")  # bcrypt hash
ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", secrets.token_urlsafe(32))
ADMIN_JWT_ALGORITHM = "HS256"
ADMIN_JWT_EXPIRY_HOURS = 24


def verify_admin_password(username: str, password: str) -> bool:
    """
    Verify admin credentials against environment variables or database.

    In production:
    1. Store hashed passwords in database with bcrypt
    2. Implement proper user roles (admin, agent, viewer)
    3. Use OAuth2/OIDC for enterprise deployments
    """
    import bcrypt

    if username != ADMIN_USERNAME:
        return False

    if not ADMIN_PASSWORD_HASH:
        # Development mode: allow any password if hash not set
        # WARNING: Never use in production!
        return os.getenv("ENVIRONMENT", "development") == "development"

    # Verify password against bcrypt hash
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            ADMIN_PASSWORD_HASH.encode('utf-8')
        )
    except Exception:
        return False


def create_admin_token(username: str) -> str:
    """
    Create JWT token for authenticated admin user.
    Token expires after ADMIN_JWT_EXPIRY_HOURS.
    """
    payload = {
        "sub": username,
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=ADMIN_JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, ADMIN_JWT_SECRET, algorithm=ADMIN_JWT_ALGORITHM)


def verify_admin_token(token: str) -> Optional[dict]:
    """
    Verify JWT token and return payload if valid.
    Returns None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            ADMIN_JWT_SECRET,
            algorithms=[ADMIN_JWT_ALGORITHM]
        )

        # Check if user has admin role
        if payload.get("role") != "admin":
            return None

        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_admin_auth(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
) -> dict:
    """
    FastAPI dependency for requiring admin authentication.

    Usage:
        @router.delete("/messages/{message_id}")
        async def delete_message(
            message_id: int,
            admin: dict = Depends(require_admin_auth)
        ):
            # Only admins can reach this code
            pass

    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 403: If user is not an admin
    """
    if not x_admin_token:
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required. Please provide X-Admin-Token header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = verify_admin_token(x_admin_token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload


# Alternative: Use HTTP Basic Auth for simpler deployments
def require_admin_basic_auth(
    authorization: Optional[str] = Header(None)
) -> str:
    """
    FastAPI dependency for HTTP Basic Auth.
    Simpler than JWT but less secure (credentials sent with every request).

    Usage:
        @router.delete("/messages/{message_id}")
        async def delete_message(
            message_id: int,
            username: str = Depends(require_admin_basic_auth)
        ):
            pass
    """
    import base64

    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Basic realm=\"Admin Access\""}
        )

    try:
        # Decode Base64 credentials
        credentials = base64.b64decode(
            authorization.replace("Basic ", "")
        ).decode("utf-8")

        username, password = credentials.split(":", 1)

        if not verify_admin_password(username, password):
            raise HTTPException(
                status_code=401,
                detail="Invalid admin credentials",
                headers={"WWW-Authenticate": "Basic realm=\"Admin Access\""}
            )

        return username

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Basic realm=\"Admin Access\""}
        )
