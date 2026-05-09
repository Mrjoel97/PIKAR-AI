# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Administrative cache operations."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from app.app_utils.auth import verify_token

router = APIRouter(tags=["Admin"])
CURRENT_USER_DEPENDENCY = Depends(verify_token)


def _csv_env(name: str) -> set[str]:
    return {v.strip().lower() for v in os.getenv(name, "").split(",") if v.strip()}


def _is_cache_admin(user: dict) -> bool:
    """Authorize access to cache invalidation."""
    if os.getenv("ALLOW_ANY_AUTH_ADMIN_ENDPOINT") == "1":
        return True

    user_id = str(user.get("id", "")).lower()
    email = str(user.get("email", "")).lower()
    allow_ids = _csv_env("ADMIN_USER_IDS")
    allow_emails = _csv_env("ADMIN_USER_EMAILS")
    allowed_roles = _csv_env("ADMIN_ROLES") or {"admin", "service_role"}

    if user_id and user_id in allow_ids:
        return True
    if email and email in allow_emails:
        return True

    role_candidates = {str(user.get("role", "")).lower()}
    metadata = user.get("metadata") or {}
    if isinstance(metadata, dict):
        app_meta = metadata.get("app_metadata") or {}
        if isinstance(app_meta, dict):
            app_role = app_meta.get("role")
            if isinstance(app_role, str):
                role_candidates.add(app_role.lower())
            app_roles = app_meta.get("roles")
            if isinstance(app_roles, list):
                role_candidates.update(
                    str(role).lower() for role in app_roles if isinstance(role, str)
                )

    return any(role in allowed_roles for role in role_candidates if role)


@router.post("/admin/cache/invalidate")
async def invalidate_cache(
    user_id: str | None = None,
    confirm_flush_all: bool = False,
    current_user: dict = CURRENT_USER_DEPENDENCY,
):
    """Invalidate cache for a specific user or all users."""
    if not _is_cache_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    from app.services.cache import get_cache_service

    cache = get_cache_service()

    if user_id:
        await cache.invalidate_user_all(user_id)
        return {"status": "success", "message": f"Cache invalidated for user {user_id}"}

    if not confirm_flush_all:
        raise HTTPException(
            status_code=400,
            detail="confirm_flush_all=true is required for global cache invalidation",
        )
    await cache.flush_all()
    return {"status": "success", "message": "All caches invalidated"}
