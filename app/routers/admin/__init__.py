"""Admin router package for Pikar-AI admin panel.

Registers all admin sub-routers under the ``/admin`` prefix.  Sub-routers
for chat and audit will be added in subsequent plans (07-02, 07-03).

Usage in fast_api_app.py::

    from app.routers.admin import admin_router
    app.include_router(admin_router)
"""

from fastapi import APIRouter

from app.routers.admin import auth

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# Phase 7 Plan 1: authentication / access-check endpoint
admin_router.include_router(auth.router)

# Future plans will add:
#   admin_router.include_router(chat.router)   # 07-02
#   admin_router.include_router(audit.router)  # 07-03

__all__ = ["admin_router"]
