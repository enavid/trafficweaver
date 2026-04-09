"""
    config_routes.py — Configuration management endpoints.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.dependencies import get_config, get_current_user
from backend.application.config_service import ConfigService
from backend.infrastructure.config.toml_config import ALLOWED_CONFIG_KEYS

router = APIRouter(tags=["Configuration"])


# ── Request / Response models ─────────────────────────────────────────────────


class ConfigUpdate(BaseModel):
    """Partial configuration update using dot-notation keys."""

    updates: Dict[str, Any]


class ConfigResponse(BaseModel):
    """Full configuration as nested dict."""

    class Config:
        extra = "allow"


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/config",
    summary="Get configuration",
    description="Return the full application configuration as a nested dictionary.",
)
async def get_configuration(
    user: str = Depends(get_current_user),
    config_svc: ConfigService = Depends(get_config),
) -> Dict[str, Any]:
    return config_svc.to_dict()


@router.patch(
    "/config",
    summary="Update configuration",
    description="Apply partial configuration updates. Keys use dot notation matching TOML paths.",
)
async def update_configuration(
    req: ConfigUpdate,
    user: str = Depends(get_current_user),
    config_svc: ConfigService = Depends(get_config),
) -> Dict[str, Any]:
    # Validate that all keys are whitelisted
    invalid_keys = [k for k in req.updates if k not in ALLOWED_CONFIG_KEYS]
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration keys: {invalid_keys}",
        )
    return await config_svc.update_config(req.updates)
