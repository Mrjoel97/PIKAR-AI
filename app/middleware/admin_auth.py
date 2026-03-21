"""Admin authentication middleware for Pikar-AI admin panel.

Provides the ``require_admin`` FastAPI dependency that gates all admin
endpoints.  Access is granted when EITHER of these conditions holds:

1. The user's email is in the ``ADMIN_EMAILS`` env var (comma-separated,
   case-insensitive).  This is the bootstrap path — always fast, no DB
   round-trip.

2. The user has an admin-level role in the ``user_roles`` table, determined
   via the ``is_admin()`` SECURITY DEFINER function.

OR logic: satisfying either condition grants access.  The returned dict
includes an ``admin_source`` field ('env_allowlist' | 'db_role') for audit
logging.
"""

import logging
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.app_utils.auth import verify_token
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)
_security = HTTPBearer()


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    """FastAPI dependency: validates JWT and checks admin access.

    Checks ADMIN_EMAILS env var first (fast path), then falls back to the
    ``is_admin()`` DB function.  Logs which path granted access for audit
    coverage.

    Args:
        credentials: Bearer token extracted from the Authorization header.

    Returns:
        User dict with ``id``, ``email``, ``role``, ``metadata``, and
        ``admin_source`` ('env_allowlist' | 'db_role').

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
        return {**user, "admin_source": "env_allowlist"}

    # --- Path 2: user_roles table via is_admin() SECURITY DEFINER RPC -------
    try:
        client = get_service_client()
        result = client.rpc("is_admin", {"user_id_param": user["id"]}).execute()
        if result.data is True:
            logger.info("Admin access granted via db_role for %s", email)
            return {**user, "admin_source": "db_role"}
    except Exception as exc:
        logger.error("is_admin() DB check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Admin access check unavailable",
        ) from exc

    logger.warning("Admin access denied for %s", email)
    raise HTTPException(status_code=403, detail="Admin access required")
