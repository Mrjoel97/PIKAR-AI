# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin authentication router.

Provides the ``GET /admin/check-access`` endpoint used by the frontend
``AdminGuard`` to verify admin status server-side (never client-side).

The endpoint:
- Returns 200 + admin info for valid admins
- Returns 403 for non-admins (raised by require_admin)
- Is rate-limited to 120 requests/minute (read endpoint tier)
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.middleware.admin_auth import require_admin
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/check-access")
@limiter.limit("120/minute")
async def check_admin_access(
    request: Request,
    admin_user: dict = Depends(require_admin),  # noqa: B008
) -> dict:
    """Verify the caller has admin access.

    Called by the frontend AdminGuard (server component) before rendering
    any admin UI.  The ADMIN_EMAILS env var is never exposed in the client
    bundle — this server-side check is the only admin gate the frontend uses.

    Args:
        request: FastAPI Request (required by slowapi rate limiter).
        admin_user: Injected by require_admin; contains id, email,
            admin_source, and role.

    Returns:
        JSON with ``access``, ``email``, and ``admin_source``.

    Raises:
        HTTPException 403: Raised upstream by require_admin for non-admins.
    """
    return {
        "access": True,
        "email": admin_user["email"],
        "admin_source": admin_user["admin_source"],
        "admin_role": admin_user.get("admin_role", "junior_admin"),
    }
