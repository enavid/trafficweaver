"""
    middleware.py — Security middleware for the TrafficWeaver API.

    Provides:
      - Rate limiting (30/min for login, 200/min for general API)
      - Security headers (nosniff, X-Frame-Options, HSTS, CSP, etc.)
      - Request body size limit (10 MB)
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Maximum request body size: 10 MB
_MAX_BODY_SIZE = 10 * 1024 * 1024


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return a 429 response when rate limits are exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


# ── Security headers middleware ───────────────────────────────────────────────


# CSP for Swagger UI (needs CDN resources)
_SWAGGER_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net"
)

# Strict CSP for the main application
_APP_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self' ws: wss:"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add recommended security headers to every HTTP response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Use relaxed CSP for Swagger UI, strict CSP for the app
        path = request.url.path
        if path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            response.headers["Content-Security-Policy"] = _SWAGGER_CSP
        else:
            response.headers["Content-Security-Policy"] = _APP_CSP

        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# ── Body size limiter middleware ──────────────────────────────────────────────


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies exceeding the configured maximum size."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large. Maximum size is 10 MB."},
            )
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Attach all security middleware to the FastAPI application."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
