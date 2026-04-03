# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workspace service for team RBAC operations.

Manages workspaces, membership, role lookups, and invite tokens.
Application-layer workspace isolation: the workspace_members table
records which users share a workspace; the service filters shared data
by looking up co-members rather than by adding workspace_id columns to
existing tables.
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

_VALID_ROLES = frozenset({"admin", "editor", "viewer"})
_INVITE_ROLES = frozenset({"editor", "viewer"})


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug.

    Args:
        text: The input string to slugify.

    Returns:
        A lowercase alphanumeric slug with hyphens replacing spaces/special chars.
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].strip("-")


class WorkspaceService:
    """Service for workspace CRUD, membership management, and invite tokens.

    All database operations use the service-role client for full access,
    with business-logic permission checks enforced in application code.
    """

    def __init__(self) -> None:
        """Initialise the service with the Supabase service client."""
        self.client = get_service_client()

    # ------------------------------------------------------------------
    # Workspace resolution
    # ------------------------------------------------------------------

    async def get_or_create_workspace(self, user_id: str) -> dict[str, Any]:
        """Return the user's workspace, creating one automatically if none exists.

        The first call for a new user creates a workspace, assigns the user as
        the owner, and inserts an ``admin`` membership row.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            A workspace dict with ``id``, ``name``, ``slug``, ``owner_id``,
            ``created_at``, and ``updated_at``.
        """
        existing = await self.get_workspace_for_user(user_id)
        if existing:
            return existing

        # Create workspace
        slug_base = _slugify(f"workspace-{user_id[:8]}")
        slug = f"{slug_base}-{secrets.token_urlsafe(4)}"

        ws_result = await execute_async(
            self.client.table("workspaces")
            .insert({"owner_id": user_id, "name": "My Workspace", "slug": slug})
            .select("id, name, slug, owner_id, created_at, updated_at"),
            op_name="workspace_service.create_workspace",
        )
        workspace = (ws_result.data or [{}])[0]
        workspace_id = workspace["id"]

        # Insert admin membership
        await execute_async(
            self.client.table("workspace_members").insert(
                {"workspace_id": workspace_id, "user_id": user_id, "role": "admin"}
            ),
            op_name="workspace_service.create_owner_member",
        )

        logger.info(
            "Created workspace=%s for user=%s", workspace_id, user_id
        )
        return workspace

    async def get_workspace_for_user(
        self, user_id: str
    ) -> dict[str, Any] | None:
        """Look up the workspace a user belongs to.

        Args:
            user_id: The authenticated user's UUID.

        Returns:
            The workspace record dict, or ``None`` if the user has no workspace.
        """
        result = await execute_async(
            self.client.table("workspace_members")
            .select("workspace_id, workspaces(id, name, slug, owner_id, created_at, updated_at)")
            .eq("user_id", user_id)
            .limit(1),
            op_name="workspace_service.get_workspace_for_user",
        )
        rows = result.data or []
        if not rows:
            return None

        workspace_data = rows[0].get("workspaces")
        if isinstance(workspace_data, list):
            return workspace_data[0] if workspace_data else None
        return workspace_data if workspace_data else None

    # ------------------------------------------------------------------
    # Role lookup
    # ------------------------------------------------------------------

    async def get_member_role(
        self, user_id: str, workspace_id: str
    ) -> str | None:
        """Return the user's role in the given workspace.

        Args:
            user_id: The authenticated user's UUID.
            workspace_id: The workspace UUID.

        Returns:
            The role string (``'admin'``, ``'editor'``, or ``'viewer'``),
            or ``None`` if the user is not a member.
        """
        result = await execute_async(
            self.client.table("workspace_members")
            .select("role")
            .eq("workspace_id", workspace_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="workspace_service.get_member_role",
        )
        rows = result.data or []
        return rows[0]["role"] if rows else None

    # ------------------------------------------------------------------
    # Member listing
    # ------------------------------------------------------------------

    async def get_workspace_members(
        self, workspace_id: str
    ) -> list[dict[str, Any]]:
        """Return all members of a workspace with profile info.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            A list of member dicts, each containing ``user_id``, ``role``,
            ``joined_at``, and any available profile fields (``email``,
            ``full_name``) from ``user_profiles``.
        """
        members_result = await execute_async(
            self.client.table("workspace_members")
            .select("id, user_id, role, joined_at")
            .eq("workspace_id", workspace_id)
            .order("joined_at"),
            op_name="workspace_service.get_workspace_members",
        )
        members = members_result.data or []

        if not members:
            return []

        user_ids = [m["user_id"] for m in members]

        # Fetch profiles (best-effort; ignore if table missing or no rows)
        profiles: dict[str, dict[str, Any]] = {}
        try:
            profiles_result = await execute_async(
                self.client.table("user_profiles")
                .select("user_id, full_name, email")
                .in_("user_id", user_ids),
                op_name="workspace_service.get_member_profiles",
            )
            for p in profiles_result.data or []:
                profiles[p["user_id"]] = p
        except Exception:
            logger.debug("user_profiles lookup failed — returning members without profile data")

        enriched: list[dict[str, Any]] = []
        for m in members:
            profile = profiles.get(m["user_id"], {})
            enriched.append(
                {
                    "id": m["id"],
                    "user_id": m["user_id"],
                    "role": m["role"],
                    "joined_at": m["joined_at"],
                    "email": profile.get("email"),
                    "full_name": profile.get("full_name"),
                }
            )
        return enriched

    # ------------------------------------------------------------------
    # Invite management
    # ------------------------------------------------------------------

    async def create_invite_link(
        self,
        workspace_id: str,
        created_by: str,
        role: str = "viewer",
        expires_hours: int = 168,
    ) -> dict[str, Any]:
        """Create a shareable invite token for the workspace.

        Args:
            workspace_id: The workspace UUID.
            created_by: UUID of the user creating the invite (must be admin).
            role: Role to assign on acceptance — ``'editor'`` or ``'viewer'``.
            expires_hours: Hours until the invite expires (default 168 = 7 days).

        Returns:
            The created invite record including the ``token``.

        Raises:
            PermissionError: If ``created_by`` is not an admin of the workspace.
            ValueError: If ``role`` is not ``'editor'`` or ``'viewer'``.
        """
        if role not in _INVITE_ROLES:
            raise ValueError(
                f"Invalid invite role '{role}'. Must be 'editor' or 'viewer'. "
                "Admin cannot be assigned via invite — the workspace owner is always admin."
            )

        actor_role = await self.get_member_role(created_by, workspace_id)
        if actor_role != "admin":
            raise PermissionError(
                f"Only workspace admins can create invite links. "
                f"User {created_by} has role '{actor_role}'."
            )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)

        result = await execute_async(
            self.client.table("workspace_invites")
            .insert(
                {
                    "workspace_id": workspace_id,
                    "token": token,
                    "role": role,
                    "created_by": created_by,
                    "expires_at": expires_at.isoformat(),
                    "is_active": True,
                }
            )
            .select("id, workspace_id, token, role, created_by, expires_at, is_active, created_at"),
            op_name="workspace_service.create_invite_link",
        )
        invite = (result.data or [{}])[0]
        logger.info(
            "Created invite token for workspace=%s by user=%s role=%s",
            workspace_id,
            created_by,
            role,
        )
        return invite

    async def accept_invite(
        self, token: str, user_id: str
    ) -> dict[str, Any]:
        """Accept a workspace invite and add the user as a member.

        Args:
            token: The invite token from the share link.
            user_id: The UUID of the user accepting the invite.

        Returns:
            The new ``workspace_members`` record.

        Raises:
            ValueError: If the token is invalid, expired, already used,
                revoked, or the user is already a member.
        """
        invite_result = await execute_async(
            self.client.table("workspace_invites")
            .select("id, workspace_id, role, expires_at, accepted_by, is_active")
            .eq("token", token)
            .limit(1),
            op_name="workspace_service.lookup_invite",
        )
        invites = invite_result.data or []
        if not invites:
            raise ValueError("Invite token not found or has already been used.")

        invite = invites[0]

        if not invite.get("is_active"):
            raise ValueError("This invite link has been revoked.")

        if invite.get("accepted_by"):
            raise ValueError("This invite link has already been accepted.")

        expires_at_str = invite.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if datetime.now(UTC) > expires_at:
                raise ValueError("This invite link has expired.")

        workspace_id = invite["workspace_id"]

        # Check not already a member
        existing_role = await self.get_member_role(user_id, workspace_id)
        if existing_role:
            raise ValueError(
                f"User is already a member of this workspace with role '{existing_role}'."
            )

        # Insert membership
        member_result = await execute_async(
            self.client.table("workspace_members")
            .insert(
                {
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "role": invite["role"],
                }
            )
            .select("id, workspace_id, user_id, role, joined_at"),
            op_name="workspace_service.accept_invite_insert_member",
        )
        member = (member_result.data or [{}])[0]

        # Mark invite accepted
        now_iso = datetime.now(UTC).isoformat()
        await execute_async(
            self.client.table("workspace_invites")
            .update({"accepted_by": user_id, "accepted_at": now_iso, "is_active": False})
            .eq("id", invite["id"]),
            op_name="workspace_service.mark_invite_accepted",
        )

        logger.info(
            "User=%s accepted invite for workspace=%s with role=%s",
            user_id,
            workspace_id,
            invite["role"],
        )
        return member

    # ------------------------------------------------------------------
    # Member role management
    # ------------------------------------------------------------------

    async def update_member_role(
        self,
        workspace_id: str,
        target_user_id: str,
        new_role: str,
        actor_user_id: str,
    ) -> dict[str, Any]:
        """Change a workspace member's role.

        Args:
            workspace_id: The workspace UUID.
            target_user_id: UUID of the member whose role is being changed.
            new_role: The new role (``'admin'``, ``'editor'``, or ``'viewer'``).
            actor_user_id: UUID of the user performing the update (must be admin).

        Returns:
            The updated ``workspace_members`` record.

        Raises:
            PermissionError: If the actor is not an admin.
            ValueError: If ``new_role`` is invalid, the target is not a member,
                or attempting to change the workspace owner's role.
        """
        if new_role not in _VALID_ROLES:
            raise ValueError(
                f"Invalid role '{new_role}'. Must be one of: admin, editor, viewer."
            )

        actor_role = await self.get_member_role(actor_user_id, workspace_id)
        if actor_role != "admin":
            raise PermissionError(
                f"Only workspace admins can change member roles. "
                f"User {actor_user_id} has role '{actor_role}'."
            )

        # Prevent changing the workspace owner's role
        ws_result = await execute_async(
            self.client.table("workspaces")
            .select("owner_id")
            .eq("id", workspace_id)
            .limit(1),
            op_name="workspace_service.get_workspace_owner",
        )
        ws_rows = ws_result.data or []
        if ws_rows and ws_rows[0]["owner_id"] == target_user_id:
            raise ValueError(
                "Cannot change the workspace owner's role. "
                "The owner is always an admin."
            )

        result = await execute_async(
            self.client.table("workspace_members")
            .update({"role": new_role})
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id)
            .select("id, workspace_id, user_id, role, joined_at"),
            op_name="workspace_service.update_member_role",
        )
        updated = result.data or []
        if not updated:
            raise ValueError(
                f"User {target_user_id} is not a member of workspace {workspace_id}."
            )

        logger.info(
            "Updated member=%s in workspace=%s to role=%s by actor=%s",
            target_user_id,
            workspace_id,
            new_role,
            actor_user_id,
        )
        return updated[0]

    async def remove_member(
        self,
        workspace_id: str,
        target_user_id: str,
        actor_user_id: str,
    ) -> bool:
        """Remove a member from a workspace.

        Args:
            workspace_id: The workspace UUID.
            target_user_id: UUID of the member to remove.
            actor_user_id: UUID of the user performing the removal (must be admin).

        Returns:
            ``True`` on successful removal.

        Raises:
            PermissionError: If the actor is not an admin.
            ValueError: If attempting to remove the workspace owner.
        """
        actor_role = await self.get_member_role(actor_user_id, workspace_id)
        if actor_role != "admin":
            raise PermissionError(
                f"Only workspace admins can remove members. "
                f"User {actor_user_id} has role '{actor_role}'."
            )

        # Prevent removing the workspace owner
        ws_result = await execute_async(
            self.client.table("workspaces")
            .select("owner_id")
            .eq("id", workspace_id)
            .limit(1),
            op_name="workspace_service.get_workspace_owner_for_remove",
        )
        ws_rows = ws_result.data or []
        if ws_rows and ws_rows[0]["owner_id"] == target_user_id:
            raise ValueError(
                "Cannot remove the workspace owner. "
                "Transfer ownership first before removing this member."
            )

        await execute_async(
            self.client.table("workspace_members")
            .delete()
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id),
            op_name="workspace_service.remove_member",
        )

        logger.info(
            "Removed member=%s from workspace=%s by actor=%s",
            target_user_id,
            workspace_id,
            actor_user_id,
        )
        return True
