# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin router package for Pikar-AI admin panel.

Registers all admin sub-routers under the ``/admin`` prefix.

Usage in fast_api_app.py::

    from app.routers.admin import admin_router
    app.include_router(admin_router)
"""

from fastapi import APIRouter

from app.routers.admin import (
    analytics,
    audit,
    auth,
    billing,
    chat,
    config,
    integrations,
    knowledge,
    monitoring,
    research,
    users,
)

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

# Phase 10: analytics endpoints
admin_router.include_router(analytics.router)

# Phase 11: external integrations
admin_router.include_router(integrations.router)

# Phase 12: agent config, feature flags, autonomy permissions, MCP endpoints
admin_router.include_router(config.router, tags=["admin-config"])

# Phase 12.1: agent knowledge base upload and management
admin_router.include_router(knowledge.router, tags=["admin-knowledge"])

# Research Intelligence: monitoring and management endpoints
admin_router.include_router(research.router)

# Phase 14: billing dashboard
admin_router.include_router(billing.router)

__all__ = ["admin_router"]
