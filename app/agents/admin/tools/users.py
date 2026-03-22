"""User management tools for the AdminAgent.

Provides 6 tools for managing platform users via the AI chat interface.
Each tool enforces the autonomy tier by querying admin_agent_permissions
before executing, using the same ``_check_autonomy()`` pattern established
in ``monitoring.py``.

Auto-tier tools (list_users, get_user_detail) return data directly.
Confirm-tier tools (suspend_user, unsuspend_user, change_user_persona,
impersonate_user) return a confirmation request dict when the tier is
'confirm', or execute immediately when the tier is 'auto'.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.services.admin_audit import log_admin_action
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Valid persona values for user accounts
_VALID_PERSONAS = frozenset(
    {
        "solopreneur",
        "startup",
        "sme",
        "enterprise",
    }
)


# ---------------------------------------------------------------------------
# Autonomy enforcement helper (copied from monitoring.py — same pattern)
# ---------------------------------------------------------------------------


from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy


# ---------------------------------------------------------------------------
# Tool 1: list_users
# ---------------------------------------------------------------------------


async def list_users(
    search: str = "",
    persona: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """Return a paginated list of platform users.

    Queries ``user_executive_agents`` with optional persona filter and
    enriches results with auth data. Applies search/status filters
    Python-side.

    Autonomy tier: auto (read-only).

    Args:
        search: Optional search string matched against email or user_id.
        persona: Optional persona filter (e.g. 'executive', 'manager').
        status: Optional status filter — 'active' or 'suspended'.
        page: Page number (1-indexed, default 1).
        page_size: Results per page (default 25).

    Returns:
        Dict with ``users`` list, ``total`` count, and ``page`` number.
        On confirm tier: returns confirmation request dict.
        On blocked tier: returns error dict.
    """
    gate = await _check_autonomy("list_users")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        query = client.table("user_executive_agents").select("user_id, persona, created_at")
        if persona:
            query = query.eq("persona", persona)

        result = await execute_async(query, op_name="list_users")
        rows: list[dict] = result.data or []

        # Enrich with auth data in parallel (not N+1 sequential calls)
        async def _fetch_auth(uid: str):
            try:
                auth_resp = await asyncio.to_thread(
                    client.auth.admin.get_user_by_id, uid
                )
                auth_user = getattr(auth_resp, "user", auth_resp)
                email = getattr(auth_user, "email", "") or ""
                ban_duration = getattr(auth_user, "ban_duration", None)
                last_sign_in = getattr(auth_user, "last_sign_in_at", None)
                is_suspended = bool(ban_duration and ban_duration != "none")
                return uid, email, "suspended" if is_suspended else "active", last_sign_in
            except Exception:
                return uid, "", "unknown", None

        auth_results = await asyncio.gather(*[
            _fetch_auth(row.get("user_id", "")) for row in rows
        ])
        auth_map = {uid: (email, status, last_sign) for uid, email, status, last_sign in auth_results}

        enriched: list[dict] = []
        for row in rows:
            uid = row.get("user_id", "")
            email, user_status, last_sign_in = auth_map.get(uid, ("", "unknown", None))

            # Apply search filter
            if search and search.lower() not in email.lower() and search.lower() not in uid.lower():
                continue

            # Apply status filter
            if status and user_status != status:
                continue

            enriched.append(
                {
                    "user_id": uid,
                    "email": email,
                    "persona": row.get("persona"),
                    "status": user_status,
                    "last_sign_in_at": last_sign_in,
                    "created_at": row.get("created_at"),
                }
            )

        # Paginate Python-side
        total = len(enriched)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = enriched[start:end]

        return {
            "users": paginated,
            "total": total,
            "page": page,
        }
    except Exception as exc:
        logger.error("list_users failed: %s", exc)
        return {"error": f"Failed to list users: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: get_user_detail
# ---------------------------------------------------------------------------


async def get_user_detail(user_id: str) -> dict[str, Any]:
    """Return full user profile with activity stats for a specific user.

    Fetches the user from ``user_executive_agents`` and ``auth.admin``,
    plus approximate activity counts for the last 90 days.

    Autonomy tier: auto (read-only).

    Args:
        user_id: UUID of the user to retrieve.

    Returns:
        Dict with ``user_id``, ``email``, ``persona``, ``status``,
        ``created_at``, ``last_sign_in_at``, and ``activity`` sub-dict.
        On error: error dict.
    """
    gate = await _check_autonomy("get_user_detail")
    if gate is not None:
        return gate

    client = get_service_client()

    try:
        # Fetch profile row
        query = (
            client.table("user_executive_agents")
            .select("user_id, persona, created_at")
            .eq("user_id", user_id)
            .limit(1)
        )
        result = await execute_async(query, op_name="get_user_detail.profile")
        rows: list[dict] = result.data or []

        profile_row = rows[0] if rows else {}

        # Fetch auth data
        try:
            auth_resp = await asyncio.to_thread(
                client.auth.admin.get_user_by_id, user_id
            )
            auth_user = getattr(auth_resp, "user", auth_resp)
            email = getattr(auth_user, "email", "") or ""
            ban_duration = getattr(auth_user, "ban_duration", None)
            last_sign_in = getattr(auth_user, "last_sign_in_at", None)
            auth_created_at = getattr(auth_user, "created_at", None)
            is_suspended = bool(ban_duration and ban_duration != "none")
            user_status = "suspended" if is_suspended else "active"
        except Exception as exc:
            logger.warning("Could not fetch auth user for %s: %s", user_id, exc)
            email = ""
            user_status = "unknown"
            last_sign_in = None
            auth_created_at = None

        return {
            "user_id": user_id,
            "email": email,
            "persona": profile_row.get("persona"),
            "status": user_status,
            "created_at": profile_row.get("created_at") or auth_created_at,
            "last_sign_in_at": last_sign_in,
            "activity": {
                "note": "Activity counts require analytics integration (Phase 10)."
            },
        }
    except Exception as exc:
        logger.error("get_user_detail failed for %s: %s", user_id, exc)
        return {"error": f"Failed to retrieve user detail for {user_id}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: suspend_user
# ---------------------------------------------------------------------------


async def suspend_user(user_id: str) -> dict[str, Any]:
    """Suspend a user account (ban from logging in).

    Sets ``ban_duration`` to ``876000h`` (effectively permanent) via the
    Supabase Auth Admin API. Requires confirmation tier by default.

    Autonomy tier: confirm (mutates user account).

    Args:
        user_id: UUID of the user to suspend.

    Returns:
        Confirmation request dict if confirm tier, or ``{"status": "suspended",
        "user_id": user_id}`` on success. On blocked tier: error dict.
    """
    gate = await _check_autonomy("suspend_user")
    if gate is not None:
        # Override risk level for suspension (medium risk)
        if gate.get("requires_confirmation"):
            gate["action_details"]["risk_level"] = "medium"
            gate["action_details"]["description"] = (
                f"Suspend user account: {user_id}. "
                "This will block the user from logging in."
            )
        return gate

    client = get_service_client()

    try:
        await asyncio.to_thread(
            client.auth.admin.update_user_by_id,
            user_id,
            {"ban_duration": "876000h"},
        )
        await log_admin_action(
            admin_user_id=None,
            action="suspend_user",
            target_type="user",
            target_id=user_id,
            details={"ban_duration": "876000h"},
            source="ai_agent",
        )
        return {"status": "suspended", "user_id": user_id}
    except Exception as exc:
        logger.error("suspend_user failed for %s: %s", user_id, exc)
        return {"error": f"Failed to suspend user {user_id}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: unsuspend_user
# ---------------------------------------------------------------------------


async def unsuspend_user(user_id: str) -> dict[str, Any]:
    """Re-enable a suspended user account.

    Clears ``ban_duration`` by setting it to ``none`` via the Supabase
    Auth Admin API. Requires confirmation tier by default.

    Autonomy tier: confirm (mutates user account).

    Args:
        user_id: UUID of the user to re-enable.

    Returns:
        Confirmation request dict if confirm tier, or ``{"status": "active",
        "user_id": user_id}`` on success. On blocked tier: error dict.
    """
    gate = await _check_autonomy("unsuspend_user")
    if gate is not None:
        if gate.get("requires_confirmation"):
            gate["action_details"]["description"] = (
                f"Re-enable user account: {user_id}. "
                "This will restore the user's ability to log in."
            )
        return gate

    client = get_service_client()

    try:
        await asyncio.to_thread(
            client.auth.admin.update_user_by_id,
            user_id,
            {"ban_duration": "none"},
        )
        await log_admin_action(
            admin_user_id=None,
            action="unsuspend_user",
            target_type="user",
            target_id=user_id,
            details={"ban_duration": "none"},
            source="ai_agent",
        )
        return {"status": "active", "user_id": user_id}
    except Exception as exc:
        logger.error("unsuspend_user failed for %s: %s", user_id, exc)
        return {"error": f"Failed to unsuspend user {user_id}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 5: change_user_persona
# ---------------------------------------------------------------------------


async def change_user_persona(user_id: str, new_persona: str) -> dict[str, Any]:
    """Change a user's persona in user_executive_agents.

    Updates the ``persona`` column for the given user. Requires confirmation
    tier by default.

    Autonomy tier: confirm (mutates user profile).

    Args:
        user_id: UUID of the user.
        new_persona: New persona identifier. Must be one of the valid personas:
            executive, manager, analyst, sales, marketing, operations,
            finance, hr, compliance, support.

    Returns:
        Confirmation request dict if confirm tier, or ``{"status": "updated",
        "user_id": user_id, "new_persona": new_persona}`` on success.
        On blocked tier: error dict. On invalid persona: error dict.
    """
    if new_persona not in _VALID_PERSONAS:
        return {
            "error": (
                f"Invalid persona '{new_persona}'. "
                f"Valid personas: {', '.join(sorted(_VALID_PERSONAS))}"
            )
        }

    gate = await _check_autonomy("change_user_persona")
    if gate is not None:
        if gate.get("requires_confirmation"):
            gate["action_details"]["description"] = (
                f"Change persona for user {user_id} to '{new_persona}'."
            )
            gate["action_details"]["new_persona"] = new_persona
        return gate

    client = get_service_client()

    try:
        query = (
            client.table("user_executive_agents")
            .update({"persona": new_persona})
            .eq("user_id", user_id)
        )
        await execute_async(query, op_name="change_user_persona")
        await log_admin_action(
            admin_user_id=None,
            action="change_user_persona",
            target_type="user",
            target_id=user_id,
            details={"new_persona": new_persona},
            source="ai_agent",
        )
        return {"status": "updated", "user_id": user_id, "new_persona": new_persona}
    except Exception as exc:
        logger.error("change_user_persona failed for %s: %s", user_id, exc)
        return {"error": f"Failed to change persona for user {user_id}: {exc}"}


# ---------------------------------------------------------------------------
# Tool 6: impersonate_user
# ---------------------------------------------------------------------------


async def impersonate_user(user_id: str) -> dict[str, Any]:
    """Open a read-only impersonation view for a specific user.

    Requires confirmation tier by default. When executed (auto tier),
    returns the impersonation URL for the admin UI to open.

    Autonomy tier: confirm (accesses user data in user context).

    Args:
        user_id: UUID of the user to impersonate.

    Returns:
        Confirmation request dict if confirm tier (includes impersonation URL
        in action_details), or ``{"impersonation_url": "...", "mode": "read_only"}``
        on success. On blocked tier: error dict.
    """
    gate = await _check_autonomy("impersonate_user")
    if gate is not None:
        if gate.get("requires_confirmation"):
            gate["action_details"]["description"] = (
                f"Open read-only impersonation view for user {user_id}."
            )
            gate["action_details"]["impersonation_url"] = (
                f"/admin/impersonate/{user_id}"
            )
        return gate

    await log_admin_action(
        admin_user_id=None,
        action="impersonate_user",
        target_type="user",
        target_id=user_id,
        details={"mode": "read_only"},
        source="ai_agent",
    )
    return {
        "impersonation_url": f"/admin/impersonate/{user_id}",
        "mode": "read_only",
    }
