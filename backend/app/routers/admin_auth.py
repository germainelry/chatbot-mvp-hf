"""
Admin authentication endpoints.
Provides login/logout functionality for admin users.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.middleware.admin_auth import (
    verify_admin_password,
    create_admin_token,
    require_admin_auth
)

router = APIRouter()


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int  # seconds
    username: str


class AdminProfileResponse(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(credentials: AdminLoginRequest):
    """
    Authenticate admin user and return JWT token.

    Usage:
        POST /api/admin/login
        {
            "username": "admin",
            "password": "your_secure_password"
        }

    Returns:
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "bearer",
            "expires_in": 86400,
            "username": "admin"
        }

    Then use the token in subsequent requests:
        X-Admin-Token: eyJ0eXAiOiJKV1QiLCJhbGc...
    """
    # Verify credentials
    if not verify_admin_password(credentials.username, credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT token
    token = create_admin_token(credentials.username)

    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=86400,  # 24 hours
        username=credentials.username
    )


@router.post("/logout")
async def admin_logout(
    admin: dict = Depends(require_admin_auth)
):
    """
    Logout admin user (client should discard token).

    Note: JWT tokens cannot be invalidated server-side.
    For true logout, implement token blacklist in Redis or database.
    """
    return {
        "message": "Logged out successfully",
        "username": admin.get("sub")
    }


@router.get("/profile", response_model=AdminProfileResponse)
async def get_admin_profile(
    admin: dict = Depends(require_admin_auth)
):
    """
    Get current admin user profile.
    Used to verify token validity.
    """
    return AdminProfileResponse(
        username=admin.get("sub"),
        role=admin.get("role", "admin")
    )


@router.post("/verify")
async def verify_admin_token(
    admin: dict = Depends(require_admin_auth)
):
    """
    Verify admin token validity.
    Returns 200 if valid, 401 if invalid.
    """
    return {
        "valid": True,
        "username": admin.get("sub"),
        "role": admin.get("role")
    }
