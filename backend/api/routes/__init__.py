"""
    routes — All API route modules.

    Each module registers its endpoints on a shared APIRouter.
"""

from fastapi import APIRouter

from backend.api.routes.auth_routes import router as auth_router
from backend.api.routes.config_routes import router as config_router
from backend.api.routes.engine_routes import router as engine_router
from backend.api.routes.site_routes import router as site_router
from backend.api.routes.stats_routes import router as stats_router
from backend.api.routes.log_routes import router as log_router
from backend.api.routes.preset_routes import router as preset_router
from backend.api.routes.network_routes import router as network_router
from backend.api.routes.ws_routes import router as ws_router

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(config_router)
router.include_router(engine_router)
router.include_router(site_router)
router.include_router(stats_router)
router.include_router(log_router)
router.include_router(preset_router)
router.include_router(network_router)
router.include_router(ws_router)
