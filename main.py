"""
    main.py — TrafficWeaver entry point.

    Starts the FastAPI server which serves both the REST API
    and the static frontend SPA.
"""

from __future__ import annotations

import uvicorn
from backend.api.app import create_app
from backend.infrastructure.config.toml_config import get_config_service


def main() -> None:
    app = create_app()
    cfg = get_config_service().get_config()
    uvicorn.run(
        app,
        host=cfg.server_host,
        port=cfg.server_port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
