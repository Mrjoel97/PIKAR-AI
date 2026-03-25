# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin authentication middleware for Pikar-AI admin panel.

Provides the ``require_admin`` FastAPI dependency that gates all admin
endpoints.  Access is granted when EITHER of these conditions holds:

1. The user's email is in the ``ADMIN_EMAILS`` env var (comma-separated,
   case-insensitive).  This is the bootstrap path — always fast, no DB
   round-trip.  Bootstrap admins always receive ``admin_role='super_admin'``.

2. The user has an admin-level role in the ``user_roles`` table, determined
   via the ``is_admin()`` SECURITY DEFINER function.

OR logic: satisfying either condition grants access.  The returned dict
includes an ``admin_source`` field ('env_allowlist' | 'db_role') and an
``admin_role`` field ('junior_admin' | 'senior_admin' | 'admin' |
'super_admin') for use by ``require_admin_role`` and audit logging.

Also provides ``require_admin_role(min_role)`` — a dependency factory that
builds on ``require_admin`` and enforces a minimum role level.  Endpoints
gated by ``require_admin_role('senior_admin')`` will return HTTP 403 for
any caller whose ``admin_role`` has a lower ROLE_HIERARCHY level.
"""

import logging
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.app_utils.auth import verify_token
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)
_security = HTTPBearer()

# ---------------------------------------------------------------------------
# Role hierarchy: higher number = more privilege.
# Used by require_admin_role() to enforce minimum access levels.
# ---------------------------------------------------------------------------
ROLE_HIERARCHY: dict[str, int] = {
    "junior_admin": 1,
    "senior_admin": 2,
    "admin": 3,
    "super_admin": 4,
}


async def _get_admin_role(user_id: str) -> str | None:
    """Query the user_roles table and return the user's role string.

    Args:
        user_id: UUID of the authenticated user.

    Returns:
        Role string (e.g. 'senior_admin') or None if no row found.
    """
    try:
        client = get_service_client()
        result = (
            client.table("user_roles").select("role").eq("user_id", user_id).execute()
        )
        rows = result.data or []
        if rows:
            return rows[0]["role"]
    except Exception as exc:
        logger.warning("_get_admin_role query failed for user %s: %s", user_id, exc)
    return None


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_security),  # noqa: B008
) -> dict:
    """FastAPI dependency: validates JWT and checks admin access.

    Checks ADMIN_EMAILS env var first (fast path), then falls back to the
    ``is_admin()`` DB function.  Logs which path granted access for audit
    coverage.

    The returned dict always contains an ``admin_role`` field:
    - ``'super_admin'`` for env-allowlist admins (bootstrap path).
    - The role string from ``user_roles`` for DB-role admins.

    Args:
        credentials: Bearer token extracted from the Authorization header.

    Returns:
        User dict with ``id``, ``email``, ``role``, ``metadata``,
        ``admin_source`` ('env_allowlist' | 'db_role'), and
        ``admin_role`` ('junior_admin' | 'senior_admin' | 'admin' | 'super_admin').

    Raises:
        HTTPException 403: User is authenticated but not an admin.
        HTTPException 503: The DB admin check is unavailable.
    """
    user = await verify_token(credentials)
    email = (user.get("email") or "").lower()

    # --- Path 1: env allowlist (bootstrap path — always active while set) ---
    admin_emails_raw = os.environ.get("ADMIN_EMAILS", "")
    admin_emails = [e.strip().lower() for e in admin_emails_raw.split(",") if e.strip()]
    if email in admin_emails:
        logger.info("Admin access granted via env_allowlist for %s", email)
        return {**user, "admin_source": "env_allowlist", "admin_role": "super_admin"}

    # --- Path 2: user_roles table via is_admin() SECURITY DEFINER RPC -------
    try:
        client = get_service_client()
        result = client.rpc("is_admin", {"user_id_param": user["id"]}).execute()
        if result.data is True:
            admin_role = await _get_admin_role(user["id"]) or "junior_admin"
            logger.info(
                "Admin access granted via db_role for %s (role=%s)", email, admin_role
            )
            return {**user, "admin_source": "db_role", "admin_role": admin_role}
    except Exception as exc:
        logger.error("is_admin() DB check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Admin access check unavailable",
        ) from exc

    logger.warning("Admin access denied for %s", email)
    raise HTTPException(status_code=403, detail="Admin access required")


def require_admin_role(min_role: str):
    """Dependency factory: gates an endpoint to admins with at least *min_role*.

    Builds on ``require_admin`` — the caller must first pass the base admin
    check, then additionally have a role at or above *min_role* in the
    ROLE_HIERARCHY.

    Usage::

        @router.post("/roles")
        async def create_role(admin: dict = Depends(require_admin_role("super_admin"))):
            ...

    Args:
        min_role: Minimum role required (one of 'junior_admin', 'senior_admin',
            'admin', 'super_admin').

    Returns:
        A FastAPI-compatible async dependency function.

    Raises:
        HTTPException 403: Admin's role level is below the required level.
    """

    async def _check(
        credentials: HTTPAuthorizationCredentials = Depends(_security),  # noqa: B008
    ) -> dict:
        """Inner dependency: verify role level after base admin check."""
        admin = await require_admin(credentials)
        admin_level = ROLE_HIERARCHY.get(admin.get("admin_role", ""), 0)
        required_level = ROLE_HIERARCHY.get(min_role, 99)
        if admin_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Requires {min_role} or higher",
            )
        return admin

    return _check
