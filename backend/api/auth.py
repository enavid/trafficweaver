"""
    auth.py — JWT-based authentication for the TrafficWeaver API.

    Uses HMAC-SHA256 for token signing with timing-safe comparisons.
    Token expiry is set to 8 hours.
"""

from __future__ import annotations

import time
import hashlib
import hmac
import json
import base64
import secrets
from typing import Optional

from backend.infrastructure.config.toml_config import get_config_service

_TOKEN_EXPIRY = 8 * 3600  # 8 hours


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(payload: str, secret: str) -> str:
    return _b64url_encode(
        hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    )


def create_token(username: str) -> str:
    """Create a simple HMAC-signed JWT-like token with 8-hour expiry."""
    cfg = get_config_service().get_config()
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(
        json.dumps(
            {
                "sub": username,
                "iat": int(time.time()),
                "exp": int(time.time()) + _TOKEN_EXPIRY,
            }
        ).encode()
    )
    signature = _sign(f"{header}.{payload}", cfg.secret_key)
    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> Optional[str]:
    """Verify token and return the username, or None if invalid."""
    try:
        cfg = get_config_service().get_config()
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header, payload, signature = parts
        expected_sig = _sign(f"{header}.{payload}", cfg.secret_key)

        # Timing-safe comparison to prevent timing attacks
        if not secrets.compare_digest(signature, expected_sig):
            return None

        data = json.loads(_b64url_decode(payload))
        if data.get("exp", 0) < time.time():
            return None

        return data.get("sub")
    except Exception:
        return None


def refresh_token(token: str) -> Optional[str]:
    """
    Issue a new token if the current token is still valid.

    Returns None if the token is invalid or expired.
    """
    username = verify_token(token)
    if username is None:
        return None
    return create_token(username)
