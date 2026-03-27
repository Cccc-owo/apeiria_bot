"""API router — aggregates all route modules."""

from fastapi import APIRouter

from .auth_routes import router as auth_router
from .chat_routes import router as chat_router
from .dashboard_routes import router as dashboard_router
from .data_routes import router as data_router
from .group_routes import router as group_router
from .log_routes import router as log_router
from .permission_routes import router as permission_router
from .plugin_routes import router as plugin_router
from .plugin_store_routes import router as plugin_store_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
router.include_router(
    plugin_store_router,
    prefix="/plugins/store",
    tags=["plugin-store"],
)
router.include_router(plugin_router, prefix="/plugins", tags=["plugins"])
router.include_router(permission_router, prefix="/permissions", tags=["permissions"])
router.include_router(group_router, prefix="/groups", tags=["groups"])
router.include_router(data_router, prefix="/data", tags=["data"])
router.include_router(log_router, prefix="/logs", tags=["logs"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
