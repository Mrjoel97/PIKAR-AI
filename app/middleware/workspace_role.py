# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workspace role middleware for RBAC endpoint gating.

Provides two FastAPI dependency factories:

- ``require_role(*allowed_roles)`` — gates an endpoint by workspace role.
  Solo users (no workspace) pass through without restriction; team members
  are checked against the allowed roles.

- ``get_workspace_context`` — resolves and returns the caller's workspace_id
  and role without gating, useful for endpoints that need workspace context.

Usage::

    from app.middleware.workspace_role import get_workspace_context, require_role

    # Router-level (all endpoints require editor or admin)
    router = APIRouter(
        dependencies=[Depends(require_role("admin", "editor"))],
    )

    # Per-endpoint (admin only)
    @router.delete("/{id}")
    async def delete_item(
        _role: None = Depends(require_role("admin")),
    ):
        ...

    # Context injection (no gating)
    @router.get("/items")
    async def list_items(
        ctx: dict | None = Depends(get_workspace_context),
    ):
        workspace_id = ctx["workspace_id"] if ctx else None
        ...
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException

from app.routers.onboarding import get_current_user_id
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


def require_role(*allowed_roles: str) -> Callable[..., Any]:
    """Create a FastAPI dependency that gates an endpoint by workspace role.

    Solo users without a workspace always pass (team RBAC only applies once
    a workspace exists). Team members whose role is not in ``allowed_roles``
    receive HTTP 403 with a structured JSON error.

    Args:
        *allowed_roles: One or more role strings that are permitted
            (e.g. ``"admin"``, ``"editor"``, ``"viewer"``).

    Returns:
        An async FastAPI dependency callable suitable for use in
        ``Depends(require_role(...))`` or router-level ``dependencies=[...]``.

    Example::

        @router.post("/invite")
        async def create_invite(
            _: None = Depends(require_role("admin")),
        ):
            ...
    """

    async def _check_workspace_role(
        user_id: str = Depends(get_current_user_id),
    ) -> None:
        """Inner dependency: resolve workspace role and enforce gate.

        Args:
            user_id: The authenticated user ID from the JWT (injected by FastAPI).

        Raises:
            HTTPException: HTTP 403 with structured JSON when the user's
                workspace role is not in ``allowed_roles``.
        """
        service = WorkspaceService()
        workspace = await service.get_workspace_for_user(user_id)

        if not workspace:
            # No workspace = solo user — team RBAC does not apply yet
            return

        workspace_id = workspace.get("id")
        role = await service.get_member_role(user_id, workspace_id)

        if role not in allowed_roles:
            required_display = " or ".join(allowed_roles)
            logger.info(
                "Role gate blocked: user=%s workspace=%s role=%s required=%s",
                user_id,
                workspace_id,
                role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_role",
                    "message": (
                        f"This action requires {required_display} role. "
                        f"Your role is {role}. "
                        "Contact your workspace admin."
                    ),
                    "current_role": role,
                    "required_roles": list(allowed_roles),
                },
            )

    return _check_workspace_role


async def get_workspace_context(
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any] | None:
    """Resolve and return the caller's workspace context without gating.

    Returns the user's ``workspace_id`` and ``role`` so endpoints can use
    workspace context without enforcing a minimum role.

    Args:
        user_id: The authenticated user ID from the JWT (injected by FastAPI).

    Returns:
        A dict with ``workspace_id`` and ``role`` keys, or ``None`` if the
        user has no workspace.

    Example::

        @router.get("/members")
        async def list_members(
            ctx: dict | None = Depends(get_workspace_context),
        ):
            if ctx:
                members = await service.get_workspace_members(ctx["workspace_id"])
            ...
    """
    service = WorkspaceService()
    workspace = await service.get_workspace_for_user(user_id)
    if not workspace:
        return None

    workspace_id = workspace.get("id")
    role = await service.get_member_role(user_id, workspace_id)

    return {"workspace_id": workspace_id, "role": role}
