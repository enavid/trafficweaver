"""
    auth_routes.py — Authentication endpoints.

    Provides login, password change, and token refresh.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.api.auth import create_token, refresh_token
from backend.api.dependencies import get_auth, get_current_user
from backend.api.middleware import limiter
from backend.application.auth_service import AuthService

router = APIRouter(tags=["Authentication"])


# ── Request / Response models ─────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Credentials for authentication."""

    username: str = Field(..., min_length=1, max_length=64, description="Account username")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")


class LoginResponse(BaseModel):
    """Successful login response."""

    token: str
    username: str


class ChangePasswordRequest(BaseModel):
    """Request to change the current password."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128, description="New password (min 6 characters)")


class MessageResponse(BaseModel):
    """Generic success message."""

    message: str


class TokenRefreshResponse(BaseModel):
    """New token issued after refresh."""

    token: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Authenticate user",
    description="Validate credentials and return a JWT token. Rate limited to 30 requests per minute.",
)
async def login(
    req: LoginRequest,
    auth_svc: AuthService = Depends(get_auth),
) -> Dict[str, Any]:
    success, error = await auth_svc.verify_password(req.username, req.password)
    if not success:
        raise HTTPException(status_code=401, detail=error or "Invalid credentials")
    token = create_token(req.username)
    return {"token": token, "username": req.username}


@router.post(
    "/auth/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change the authenticated user's password.",
)
async def change_password(
    req: ChangePasswordRequest,
    user: str = Depends(get_current_user),
    auth_svc: AuthService = Depends(get_auth),
) -> Dict[str, str]:
    success, error = await auth_svc.verify_password(user, req.current_password)
    if not success:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await auth_svc.set_password(req.new_password)
    return {"message": "Password changed successfully"}


@router.post(
    "/auth/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh token",
    description="Issue a new JWT token using a valid existing token.",
)
async def token_refresh(
    user: str = Depends(get_current_user),
) -> Dict[str, str]:
    new_token = create_token(user)
    return {"token": new_token}
