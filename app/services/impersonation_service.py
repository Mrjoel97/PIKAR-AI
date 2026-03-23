"""Impersonation session service for interactive admin impersonation.

Provides session CRUD, allow-list path validation, and notification suppression
check for Phase 13 interactive impersonation.

All DB operations use the service-role Supabase client and execute_async
for non-blocking async execution.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESSION_DURATION_MINUTES: int = 30

# Paths that an impersonating admin is permitted to access on behalf of a user.
# validate_impersonation_path checks prefix membership — sub-paths are allowed.
IMPERSONATION_ALLOWED_PATHS: frozenset[str] = frozenset(
    {
        "/api/agents/chat",
        "/api/workflows",
        "/api/approvals",
        "/api/briefing",
        "/api/reports",
        "/admin/users",
    }
)


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


async def create_impersonation_session(
    admin_user_id: str,
    target_user_id: str,
) -> dict:
    """Create a new interactive impersonation session.

    Inserts a row into ``admin_impersonation_sessions`` with ``is_active=True``
    and an ``expires_at`` 30 minutes from now (UTC).

    Args:
        admin_user_id: UUID of the admin who is starting the session.
        target_user_id: UUID of the user being impersonated.

    Returns:
        The inserted session row as a dict (id, admin_user_id, target_user_id,
        is_active, expires_at, created_at, ended_at).

    Raises:
        Exception: Propagated from execute_async if the insert fails.
    """
    expires_at = datetime.now(UTC) + timedelta(minutes=SESSION_DURATION_MINUTES)

    row: dict = {
        "admin_user_id": admin_user_id,
        "target_user_id": target_user_id,
        "is_active": True,
        "expires_at": expires_at.isoformat(),
    }

    client = get_service_client()
    response = await execute_async(
        client.table("admin_impersonation_sessions").insert(row),
        op_name="impersonation.create_session",
    )

    return response.data[0]


async def validate_impersonation_session(session_id: str) -> dict | None:
    """Return the session row if it is active and not expired, else None.

    Queries ``admin_impersonation_sessions`` filtering on:
    - ``id = session_id``
    - ``is_active = True``
    - ``expires_at > now(UTC)``

    Args:
        session_id: UUID of the impersonation session to validate.

    Returns:
        Session row dict if valid, or None if expired / inactive / not found.
    """
    now_iso = datetime.now(UTC).isoformat()
    client = get_service_client()

    response = await execute_async(
        client.table("admin_impersonation_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("is_active", True)
        .gte("expires_at", now_iso),
        op_name="impersonation.validate_session",
    )

    rows: list[dict] = response.data or []
    return rows[0] if rows else None


async def deactivate_impersonation_session(session_id: str) -> None:
    """Deactivate an impersonation session by setting is_active=False and ended_at.

    Args:
        session_id: UUID of the session to deactivate.
    """
    now_iso = datetime.now(UTC).isoformat()
    client = get_service_client()

    await execute_async(
        client.table("admin_impersonation_sessions")
        .update({"is_active": False, "ended_at": now_iso})
        .eq("id", session_id),
        op_name="impersonation.deactivate_session",
    )

    logger.debug("Impersonation session %s deactivated", session_id)


# ---------------------------------------------------------------------------
# Notification suppression check
# ---------------------------------------------------------------------------


async def is_impersonation_active(user_id: str) -> bool:
    """Return True if there is a current active impersonation session for user_id.

    Used by NotificationService to suppress notifications dispatched to a user
    while an admin is actively impersonating them.

    Args:
        user_id: UUID of the target user to check.

    Returns:
        True if an active, non-expired session exists; False otherwise.
    """
    now_iso = datetime.now(UTC).isoformat()
    client = get_service_client()

    response = await execute_async(
        client.table("admin_impersonation_sessions")
        .select("id")
        .eq("target_user_id", user_id)
        .eq("is_active", True)
        .gte("expires_at", now_iso),
        op_name="impersonation.is_active",
    )

    rows: list[dict] = response.data or []
    return len(rows) > 0


# ---------------------------------------------------------------------------
# Allow-list enforcement
# ---------------------------------------------------------------------------


def validate_impersonation_path(path: str) -> bool:
    """Return True if path is permitted during an impersonation session.

    Checks whether ``path`` starts with any entry in
    ``IMPERSONATION_ALLOWED_PATHS``. Sub-paths of allowed prefixes are permitted.

    Args:
        path: URL path to validate (e.g. ``/api/agents/chat/stream``).

    Returns:
        True if the path is within the allow-list, False otherwise.
    """
    return any(path.startswith(allowed) for allowed in IMPERSONATION_ALLOWED_PATHS)
