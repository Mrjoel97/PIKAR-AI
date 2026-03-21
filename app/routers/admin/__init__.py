"""Admin router package for Pikar-AI admin panel.

Registers all admin sub-routers under the ``/admin`` prefix.

Usage in fast_api_app.py::

    from app.routers.admin import admin_router
    app.include_router(admin_router)
"""

from fastapi import APIRouter

from app.routers.admin import audit, auth, chat, monitoring, users

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# Phase 7 Plan 1: authentication / access-check endpoint
admin_router.include_router(auth.router)

# Phase 7 Plan 3: SSE chat endpoint with session persistence
admin_router.include_router(chat.router)

# Phase 7 Plan 5: audit log endpoint
admin_router.include_router(audit.router)

# Phase 8: monitoring status + run-check endpoints
admin_router.include_router(monitoring.router)

# Phase 9: user management endpoints
admin_router.include_router(users.router)

__all__ = ["admin_router"]
