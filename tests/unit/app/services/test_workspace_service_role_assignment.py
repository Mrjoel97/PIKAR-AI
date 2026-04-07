# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for WorkspaceService.update_member_role role assignment enforcement.

Covers AUTH-03: a workspace admin can assign admin, editor, or viewer roles via
WorkspaceService.update_member_role. Validates: role taxonomy (admin/editor/viewer),
actor permission (admin-only), owner immutability, and not-found semantics.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Prevent cp1252 encoding failure from slowapi reading .env on Windows.
# Stub the rate_limiter module before workspace_service / its dependents import.
# ---------------------------------------------------------------------------
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *a, **kw: (lambda fn: fn)
    _mock_rate_limiter.limiter = _mock_limiter
    _mock_rate_limiter.get_user_persona_limit = "100/minute"
    sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_member_row(role: str = "admin", user_id: str = "target-uid") -> dict:
    """Return a workspace_members row dict matching the service's select shape."""
    return {
        "id": "mem-1",
        "workspace_id": "ws-1",
        "user_id": user_id,
        "role": role,
        "joined_at": "2026-04-06T00:00:00Z",
    }


def _make_role_lookup_response(role: str | None) -> MagicMock:
    """Return a Supabase response for get_member_role lookups."""
    resp = MagicMock()
    resp.data = [{"role": role}] if role is not None else []
    return resp


def _make_workspace_owner_response(owner_id: str) -> MagicMock:
    """Return a Supabase response for the workspaces.owner_id lookup."""
    resp = MagicMock()
    resp.data = [{"owner_id": owner_id}]
    return resp


def _make_update_response(role: str, user_id: str = "target-uid") -> MagicMock:
    """Return a Supabase response for the workspace_members update."""
    resp = MagicMock()
    resp.data = [_make_member_row(role=role, user_id=user_id)]
    return resp


def _make_empty_update_response() -> MagicMock:
    """Return an empty Supabase response (target not a member)."""
    resp = MagicMock()
    resp.data = []
    return resp


@pytest.fixture
def service():
    """Provide a WorkspaceService with the supabase client mocked."""
    with patch(
        "app.services.workspace_service.get_service_client",
        return_value=MagicMock(),
    ):
        from app.services.workspace_service import WorkspaceService

        yield WorkspaceService()


# ---------------------------------------------------------------------------
# Successful role assignment cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_admin_promotes_viewer_to_admin(service):
    """Admin actor promoting a viewer to admin succeeds and returns updated row."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("admin"),  # actor role lookup
            _make_workspace_owner_response("owner-uid"),  # workspace owner check
            _make_update_response("admin", user_id="target-uid"),  # update result
        ]
        result = await service.update_member_role(
            workspace_id="ws-1",
            target_user_id="target-uid",
            new_role="admin",
            actor_user_id="actor-admin-uid",
        )
    assert result["role"] == "admin"
    assert result["user_id"] == "target-uid"


@pytest.mark.asyncio
async def test_update_role_admin_demotes_admin_to_editor(service):
    """Admin actor demoting an admin to editor (Member) succeeds."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("admin"),
            _make_workspace_owner_response("owner-uid"),
            _make_update_response("editor", user_id="target-uid"),
        ]
        result = await service.update_member_role(
            workspace_id="ws-1",
            target_user_id="target-uid",
            new_role="editor",
            actor_user_id="actor-admin-uid",
        )
    assert result["role"] == "editor"


@pytest.mark.asyncio
async def test_update_role_admin_assigns_viewer_role(service):
    """Admin actor assigning the viewer role succeeds."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("admin"),
            _make_workspace_owner_response("owner-uid"),
            _make_update_response("viewer", user_id="target-uid"),
        ]
        result = await service.update_member_role(
            workspace_id="ws-1",
            target_user_id="target-uid",
            new_role="viewer",
            actor_user_id="actor-admin-uid",
        )
    assert result["role"] == "viewer"


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_invalid_role_raises_value_error(service):
    """Unknown role string raises ValueError before any DB call."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        with pytest.raises(ValueError, match="Invalid role"):
            await service.update_member_role(
                workspace_id="ws-1",
                target_user_id="target-uid",
                new_role="invalid_role",
                actor_user_id="actor-admin-uid",
            )
        # Validation rejects before any DB roundtrip
        assert mock_exec.call_count == 0


# ---------------------------------------------------------------------------
# Permission failures (non-admin actors)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_non_admin_actor_raises_permission_error(service):
    """An editor actor cannot change member roles — PermissionError raised."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("editor"),  # actor is editor, not admin
        ]
        with pytest.raises(PermissionError, match="Only workspace admins"):
            await service.update_member_role(
                workspace_id="ws-1",
                target_user_id="target-uid",
                new_role="admin",
                actor_user_id="actor-editor-uid",
            )


@pytest.mark.asyncio
async def test_update_role_viewer_actor_raises_permission_error(service):
    """A viewer actor cannot change member roles — PermissionError raised."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("viewer"),
        ]
        with pytest.raises(PermissionError, match="Only workspace admins"):
            await service.update_member_role(
                workspace_id="ws-1",
                target_user_id="target-uid",
                new_role="viewer",
                actor_user_id="actor-viewer-uid",
            )


# ---------------------------------------------------------------------------
# Owner immutability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_targeting_owner_raises_value_error(service):
    """Attempting to change the workspace owner's role raises ValueError."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("admin"),  # actor is admin
            _make_workspace_owner_response("owner-uid"),  # target IS the owner
        ]
        with pytest.raises(
            ValueError, match="Cannot change the workspace owner's role"
        ):
            await service.update_member_role(
                workspace_id="ws-1",
                target_user_id="owner-uid",  # same as workspace owner
                new_role="viewer",
                actor_user_id="actor-admin-uid",
            )


# ---------------------------------------------------------------------------
# Target not a member
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_role_target_not_member_raises_value_error(service):
    """Updating a non-member target raises ValueError after empty update result."""
    with patch(
        "app.services.workspace_service.execute_async", new_callable=AsyncMock
    ) as mock_exec:
        mock_exec.side_effect = [
            _make_role_lookup_response("admin"),
            _make_workspace_owner_response("owner-uid"),
            _make_empty_update_response(),  # update returned 0 rows
        ]
        with pytest.raises(ValueError, match="is not a member"):
            await service.update_member_role(
                workspace_id="ws-1",
                target_user_id="ghost-uid",
                new_role="editor",
                actor_user_id="actor-admin-uid",
            )
