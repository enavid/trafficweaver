"""
    log_handler.py — Backward-compatible shim.

    Delegates to the infrastructure logging module.
    Existing code that imports from ``backend.utils.log_handler``
    will continue to work without changes.
"""

from backend.infrastructure.logging.log_handler import (  # noqa: F401
    DatabaseLogHandler,
    get_logger,
    register_ws_callback,
    setup_logger,
    update_log_level,
)
