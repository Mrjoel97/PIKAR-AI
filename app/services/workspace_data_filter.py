# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workspace-scoped data filter for shared content visibility.

When a user belongs to a workspace with multiple members, content queries
should include data from all workspace members — not just the requesting user.
This avoids adding workspace_id columns to every existing table.

Usage::

    from app.services.workspace_data_filter import get_workspace_user_ids

    scoped_user_ids = await get_workspace_user_ids(user_id)
    # For solo users: returns [user_id]
    # For team users: returns [user_id, teammate1_id, teammate2_id, ...]

    # Always safe to use .in_() — works identically to .eq() for solo users:
    query = table.select("*").in_("user_id", scoped_user_ids)
"""

from __future__ import annotations

import logging

from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


async def get_workspace_user_ids(user_id: str) -> list[str]:
    """Return all user_ids sharing a workspace with the given user.

    If the user has no workspace or is the only member, returns ``[user_id]``
    (single-element list). This means callers can always use ``.in_()``
    instead of ``.eq()`` and get correct behaviour for both solo and team users.

    Args:
        user_id: The requesting user's ID.

    Returns:
        List of user_id strings. Always contains at least the input user_id
        and is never empty.
    """
    try:
        service = WorkspaceService()
        workspace = await service.get_workspace_for_user(user_id)
        if workspace is None:
            return [user_id]

        workspace_id = workspace["id"]
        members = await service.get_workspace_members(workspace_id)
        if not members:
            return [user_id]

        member_ids = [m["user_id"] for m in members]
        # Safety: ensure the requesting user is always included even if the
        # membership list is stale or the join query missed a row.
        if user_id not in member_ids:
            member_ids.append(user_id)
        return member_ids
    except Exception:
        logger.warning(
            "workspace_data_filter: falling back to solo user_id for user=%s",
            user_id,
            exc_info=True,
        )
        return [user_id]
