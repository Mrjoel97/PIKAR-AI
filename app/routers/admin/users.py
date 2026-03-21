"""Admin user management API endpoints.

Provides:
- GET /admin/users       — paginated, filterable user list
- GET /admin/users/{id}  — full user profile with activity stats
- PATCH /admin/users/{id}/suspend   — ban user via Supabase Auth Admin API
- PATCH /admin/users/{id}/unsuspend — unban user via Supabase Auth Admin API
- PATCH /admin/users/{id}/persona   — update persona tier in user_executive_agents

All endpoints require admin authentication via ``require_admin`` middleware.
Mutating endpoints are audit-logged with ``source="manual"``.

Note: Supabase auth.admin methods are synchronous — always wrapped in
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter
from app.services.admin_audit import log_admin_action
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid persona values — must match user_executive_agents.persona CHECK constraint
_VALID_PERSONAS = frozenset({"solopreneur", "startup", "sme", "enterprise"})


class PersonaBody(BaseModel):
    """Request body for the change_persona endpoint."""

    persona: str


# Activity lookback window in days
_ACTIVITY_DAYS = 90


@router.get("/users")
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    search: str | None = Query(default=None, description="Filter by email/name (case-insensitive)"),
    persona: Literal["solopreneur", "startup", "sme", "enterprise"] | None = Query(default=None),
    status: Literal["active", "suspended"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict:
    """Return a paginated list of users with auth and profile data.

    Queries ``user_executive_agents`` for profile rows, then enriches each
    with auth data from ``auth.admin.get_user_by_id``. Status and search
    filters are applied Python-side after auth enrichment because Supabase
    Auth Admin API does not support server-side filtering on those fields.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        search: Optional case-insensitive substring match on email.
        persona: Optional filter on ``user_executive_agents.persona``.
        status: Optional filter — "active" (no ban) or "suspended" (ban set).
        page: 1-indexed page number.
        page_size: Rows per page (max 100).

    Returns:
        JSON with ``users`` list, ``total``, ``page``, ``page_size``.

    Raises:
        HTTPException 500: If a Supabase query fails.
    """
    client = get_service_client()
    offset = (page - 1) * page_size

    try:
        # Build profile query with optional persona filter
        query = (
            client.table("user_executive_agents")
            .select("user_id, agent_name, persona, onboarding_completed, created_at", count="exact")
            .order("created_at", desc=True)
        )
        if persona is not None:
            query = query.eq("persona", persona)
        query = query.range(offset, offset + page_size - 1)

        result = await execute_async(query, op_name="users.list")
        uea_rows: list[dict] = result.data or []
        db_total: int = result.count or 0

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query user_executive_agents: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve user list") from exc

    if not uea_rows:
        return {"users": [], "total": db_total, "page": page, "page_size": page_size}

    # Enrich with auth data concurrently (auth.admin is synchronous)
    auth_responses = await asyncio.gather(
        *[
            asyncio.to_thread(
                client.auth.admin.get_user_by_id,
                row["user_id"],
            )
            for row in uea_rows
        ],
        return_exceptions=True,
    )

    users: list[dict] = []
    for row, auth_resp in zip(uea_rows, auth_responses, strict=False):
        if isinstance(auth_resp, Exception):
            logger.warning("Failed to fetch auth user %s: %s", row["user_id"], auth_resp)
            continue

        auth_user_obj = auth_resp.user if hasattr(auth_resp, "user") else None
        if auth_user_obj is None:
            continue

        email: str = getattr(auth_user_obj, "email", "") or ""
        banned_until = getattr(auth_user_obj, "banned_until", None)

        # Apply status filter Python-side
        if status == "suspended" and banned_until is None:
            continue
        if status == "active" and banned_until is not None:
            continue

        # Apply search filter Python-side (case-insensitive email match)
        if search is not None and search.lower() not in email.lower():
            continue

        users.append(
            {
                "id": row["user_id"],
                "email": email,
                "persona": row.get("persona"),
                "agent_name": row.get("agent_name"),
                "created_at": row.get("created_at"),
                "banned_until": banned_until,
                "onboarding_completed": row.get("onboarding_completed"),
            }
        )

    return {
        "users": users,
        "total": db_total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}")
@limiter.limit("120/minute")
async def get_user_detail(
    user_id: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Return a full user profile with approximate activity stats.

    Combines ``user_executive_agents`` profile data with Supabase Auth user
    details and counts of recent activity from ``admin_audit_log``.

    Args:
        user_id: UUID of the target user.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        JSON with ``user`` object containing id, email, persona, agent_name,
        created_at, banned_until, and ``activity`` dict with chat_count and
        workflow_count.

    Raises:
        HTTPException 404: If user not found in user_executive_agents.
        HTTPException 500: If Supabase query fails.
    """
    client = get_service_client()

    try:
        # Fetch profile + auth concurrently
        profile_query = (
            client.table("user_executive_agents")
            .select("user_id, agent_name, persona, onboarding_completed, created_at")
            .eq("user_id", user_id)
            .single()
        )
        profile_result, auth_resp = await asyncio.gather(
            execute_async(profile_query, op_name="users.detail.profile"),
            asyncio.to_thread(client.auth.admin.get_user_by_id, user_id),
            return_exceptions=True,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch user detail for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve user detail") from exc

    if isinstance(profile_result, Exception):
        raise HTTPException(status_code=404, detail="User not found")

    uea_row: dict = profile_result.data or {}
    if not uea_row:
        raise HTTPException(status_code=404, detail="User not found")

    auth_user_obj = None
    if not isinstance(auth_resp, Exception) and hasattr(auth_resp, "user"):
        auth_user_obj = auth_resp.user

    email = getattr(auth_user_obj, "email", "") or "" if auth_user_obj else ""
    banned_until = getattr(auth_user_obj, "banned_until", None) if auth_user_obj else None

    # Approximate activity: recent admin_audit_log entries targeting this user
    try:
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(days=_ACTIVITY_DAYS)).isoformat()

        activity_query = (
            client.table("admin_audit_log")
            .select("id", count="exact")
            .eq("target_id", user_id)
            .gte("created_at", cutoff)
        )
        activity_result = await execute_async(activity_query, op_name="users.detail.activity")
        activity_count: int = activity_result.count or 0
    except Exception as exc:
        logger.warning("Could not fetch activity stats for %s: %s", user_id, exc)
        activity_count = 0

    return {
        "user": {
            "id": user_id,
            "email": email,
            "persona": uea_row.get("persona"),
            "agent_name": uea_row.get("agent_name"),
            "created_at": uea_row.get("created_at"),
            "banned_until": banned_until,
            "onboarding_completed": uea_row.get("onboarding_completed"),
            "activity": {
                "action_count": activity_count,
            },
        }
    }


@router.patch("/users/{user_id}/suspend")
@limiter.limit("30/minute")
async def suspend_user(
    user_id: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Suspend a user account by setting a long ban duration.

    Calls Supabase Auth Admin API with ``ban_duration="876000h"`` (~100 years).
    Wraps the synchronous auth call in ``asyncio.to_thread()``.

    Args:
        user_id: UUID of the target user.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        JSON ``{"success": True}``.

    Raises:
        HTTPException 500: If the Supabase Auth call fails.
    """
    client = get_service_client()

    try:
        await asyncio.to_thread(
            client.auth.admin.update_user_by_id,
            user_id,
            {"ban_duration": "876000h"},
        )
    except Exception as exc:
        logger.error("Failed to suspend user %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to suspend user") from exc

    await log_admin_action(
        admin_user["id"],
        "suspend_user",
        "user",
        user_id,
        None,
        "manual",
    )

    return {"success": True}


@router.patch("/users/{user_id}/unsuspend")
@limiter.limit("30/minute")
async def unsuspend_user(
    user_id: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Re-enable a suspended user account by clearing the ban.

    Calls Supabase Auth Admin API with ``ban_duration="none"`` to lift the ban.
    Wraps the synchronous auth call in ``asyncio.to_thread()``.

    Args:
        user_id: UUID of the target user.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.

    Returns:
        JSON ``{"success": True}``.

    Raises:
        HTTPException 500: If the Supabase Auth call fails.
    """
    client = get_service_client()

    try:
        await asyncio.to_thread(
            client.auth.admin.update_user_by_id,
            user_id,
            {"ban_duration": "none"},
        )
    except Exception as exc:
        logger.error("Failed to unsuspend user %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to unsuspend user") from exc

    await log_admin_action(
        admin_user["id"],
        "unsuspend_user",
        "user",
        user_id,
        None,
        "manual",
    )

    return {"success": True}


@router.patch("/users/{user_id}/persona")
@limiter.limit("30/minute")
async def change_persona(
    user_id: str,
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
    body: PersonaBody = Body(...),  # noqa: B008
) -> dict:
    """Change a user's persona tier in user_executive_agents.

    Validates the persona value against allowed tiers before updating.

    Args:
        user_id: UUID of the target user.
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; confirms caller is an admin.
        body: Request body containing ``persona`` field — must be one of
            solopreneur, startup, sme, enterprise.

    Returns:
        JSON ``{"success": True}``.

    Raises:
        HTTPException 422: If persona is not a valid tier.
        HTTPException 500: If the Supabase update fails.
    """
    persona = body.persona
    if persona not in _VALID_PERSONAS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid persona '{persona}'. Must be one of: {', '.join(sorted(_VALID_PERSONAS))}",
        )

    client = get_service_client()

    try:
        update_query = (
            client.table("user_executive_agents")
            .update({"persona": persona})
            .eq("user_id", user_id)
        )
        await execute_async(update_query, op_name="users.change_persona")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to change persona for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to change persona") from exc

    await log_admin_action(
        admin_user["id"],
        "change_user_persona",
        "user",
        user_id,
        {"new_persona": persona},
        "manual",
    )

    return {"success": True}
