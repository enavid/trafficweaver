"""
    app.py — FastAPI application factory.

    Creates and configures the FastAPI application with:
      - OpenAPI/Swagger documentation
      - CORS (restricted origins)
      - Security headers middleware
      - Rate limiting
      - Request body size limits
      - Static file serving for the SPA frontend
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.routes import router
from backend.api.dependencies import init_dependencies, shutdown_dependencies
from backend.api.middleware import (
    limiter,
    rate_limit_exceeded_handler,
    register_middleware,
)
from backend.infrastructure.config.toml_config import get_config_service
from backend.infrastructure.logging.log_handler import setup_logger, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    await init_dependencies()
    yield
    await shutdown_dependencies()


def create_app() -> FastAPI:
    """Build and return the fully configured FastAPI application."""

    # Initialize config (sync — needed before app creation)
    cfg_svc = get_config_service()
    cfg = cfg_svc.get_config()

    # Setup logging
    setup_logger(cfg.log_file, cfg.log_level)
    log = get_logger("app")

    # Listen for config changes to update log level dynamically
    def _on_config_change(new_cfg):
        from backend.infrastructure.logging.log_handler import update_log_level
        update_log_level(new_cfg.log_level)

    cfg_svc.on_change(_on_config_change)

    # Create FastAPI with OpenAPI metadata
    app = FastAPI(
        title="TrafficWeaver",
        description=(
            "Human-like traffic simulation engine with web UI. "
            "Generates realistic network traffic patterns across "
            "configurable site lists with schedule-aware distribution."
        ),
        version="2.2.0",
        contact={
            "name": "TrafficWeaver Team",
            "email": "support@trafficweaver.dev",
        },
        openapi_tags=[
            {"name": "Authentication", "description": "Login, password management, and token refresh"},
            {"name": "Configuration", "description": "Read and update application settings"},
            {"name": "Engine", "description": "Start, stop, and monitor the traffic simulation engine"},
            {"name": "Download Sites", "description": "Manage file download targets"},
            {"name": "Browsing Sites", "description": "Manage web browsing targets"},
            {"name": "Statistics", "description": "View daily traffic statistics and history"},
            {"name": "Logs", "description": "View and manage system logs"},
            {"name": "Presets", "description": "Load curated site presets and compute schedules"},
            {"name": "Network", "description": "Discover and select network interfaces"},
        ],
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # CORS — restricted origins (not wildcard)
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8099",
        f"http://{cfg.server_host}:{cfg.server_port}",
    ]
    # Include HTTPS variants
    allowed_origins.extend([
        "https://localhost:3000",
        "https://localhost:8099",
        f"https://{cfg.server_host}:{cfg.server_port}",
    ])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware (headers, body size limit)
    register_middleware(app)

    # API routes
    app.include_router(router)

    # Serve static frontend files (SPA — fallback to index.html)
    static_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    )
    if os.path.isdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount(
                "/assets",
                StaticFiles(directory=assets_dir),
                name="assets",
            )

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            file_path = os.path.join(static_dir, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(static_dir, "index.html"))

    log.info("TrafficWeaver API v1.1 initialized | port=%d", cfg.server_port)
    return app
