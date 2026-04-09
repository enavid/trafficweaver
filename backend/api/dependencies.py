"""
    dependencies.py — Dependency injection container for the API layer.

    Provides singleton instances of all application services and
    infrastructure implementations, wired together at application startup.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.api.auth import verify_token
from backend.application.auth_service import AuthService
from backend.application.config_service import ConfigService
from backend.application.engine_service import EngineService
from backend.application.log_service import LogService
from backend.application.network_service import NetworkService
from backend.application.site_service import SiteService
from backend.application.stats_service import StatsService
from backend.infrastructure.config.toml_config import TomlConfigService, get_config_service
from backend.infrastructure.network.psutil_network import PsutilNetworkService
from backend.infrastructure.persistence.sqlite_repository import SqliteRepository


# ── Singleton instances ───────────────────────────────────────────────────────

_repository: Optional[SqliteRepository] = None
_config_svc: Optional[TomlConfigService] = None
_auth_svc: Optional[AuthService] = None
_site_svc: Optional[SiteService] = None
_engine_svc: Optional[EngineService] = None
_stats_svc: Optional[StatsService] = None
_log_svc: Optional[LogService] = None
_network_svc: Optional[NetworkService] = None


async def init_dependencies() -> None:
    """Initialize all dependencies at application startup."""
    global _repository, _config_svc, _auth_svc, _site_svc
    global _engine_svc, _stats_svc, _log_svc, _network_svc

    # Infrastructure
    _repository = SqliteRepository()
    await _repository.initialize()

    _config_svc = get_config_service()

    # Application services
    _auth_svc = AuthService(_config_svc)
    _site_svc = SiteService(_repository)
    _engine_svc = EngineService()
    _stats_svc = StatsService(_repository)
    _log_svc = LogService(_repository)
    _network_svc = NetworkService(PsutilNetworkService())


async def shutdown_dependencies() -> None:
    """Clean up resources on application shutdown."""
    if _repository:
        await _repository.close()


# ── Dependency providers ──────────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """FastAPI dependency: extract and validate the current user from JWT."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


def get_repository() -> SqliteRepository:
    assert _repository is not None
    return _repository


def get_config() -> ConfigService:
    assert _config_svc is not None
    return ConfigService(_config_svc)


def get_auth() -> AuthService:
    assert _auth_svc is not None
    return _auth_svc


def get_sites() -> SiteService:
    assert _site_svc is not None
    return _site_svc


def get_engine() -> EngineService:
    assert _engine_svc is not None
    return _engine_svc


def get_stats() -> StatsService:
    assert _stats_svc is not None
    return _stats_svc


def get_logs() -> LogService:
    assert _log_svc is not None
    return _log_svc


def get_network() -> NetworkService:
    assert _network_svc is not None
    return _network_svc
