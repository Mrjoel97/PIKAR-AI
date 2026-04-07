# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the teams_rbac sibling router (un-gated workspace RBAC).

Covers AUTH-03: a workspace admin on ANY tier (including solopreneur, which has
no `teams` feature gate) MUST be able to call PATCH /teams/members/{uid}/role
and receive 200. The new sibling router `app/routers/teams_rbac.py` exposes the
role-management endpoint WITHOUT the `require_feature("teams")` dependency that
gates the rest of `app/routers/teams.py`.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router.
# ---------------------------------------------------------------------------
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *a, **kw: (lambda fn: fn)
    _mock_rate_limiter.limiter = _mock_limiter
    _mock_rate_limiter.get_user_persona_limit = "100/minute"
    sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter


# ---------------------------------------------------------------------------
# Test app builder + dependency overrides
# ---------------------------------------------------------------------------


def _build_app(actor_role: str = "admin"):
    """Build a minimal FastAPI app with teams_rbac_router and dependency overrides.

    Returns the app + the WorkspaceService mock so individual tests can tweak
    the service-layer behavior (success, raise PermissionError, raise ValueError).
    """
    from app.routers import teams_rbac
    from app.routers.onboarding import get_current_user_id

    app = FastAPI()

    ws_mock = MagicMock()
    ws_mock.get_workspace_for_user = AsyncMock(
        return_value={"id": "ws-1", "owner_id": "actor-uid"}
    )
    ws_mock.update_member_role = AsyncMock(
        return_value={
            "id": "mem-1",
            "user_id": "target-uid",
            "email": "target@example.com",
            "full_name": "Target User",
            "role": "viewer",
            "joined_at": "2026-04-06T00:00:00Z",
        }
    )

    # Patch WorkspaceService at the router module level so the handler picks up
    # our mock when it does `service = WorkspaceService()`.
    ws_patcher = patch(
        "app.routers.teams_rbac.WorkspaceService", return_value=ws_mock
    )
    ws_patcher.start()

    # Override get_current_user_id (no JWT in tests)
    async def _fake_user_id() -> str:
        return "actor-uid"

    app.dependency_overrides[get_current_user_id] = _fake_user_id

    # Override the require_role dependency. Because require_role("admin") is
    # called at IMPORT time of teams_rbac, the SAME inner-dependency function
    # object is bound to the route. We grab it from the router's dependency
    # tree and override it.
    inner_admin_dep = None
    for route in teams_rbac.router.routes:
        for dep in getattr(route, "dependant", None).dependencies if getattr(route, "dependant", None) else []:
            if dep.call.__name__ == "_check_workspace_role":
                inner_admin_dep = dep.call
                break

    async def _fake_admin_check() -> None:
        if actor_role != "admin":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_role",
                    "message": "admin role required",
                    "current_role": actor_role,
                    "required_roles": ["admin"],
                },
            )
        return None

    if inner_admin_dep is not None:
        app.dependency_overrides[inner_admin_dep] = _fake_admin_check

    app.include_router(teams_rbac.router)

    return app, ws_mock, ws_patcher


# ---------------------------------------------------------------------------
# Happy path: admin can assign all three roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_assigns_viewer_role_returns_200():
    """Admin actor PATCHes member role to viewer and gets 200 + updated row."""
    app, ws_mock, ws_patcher = _build_app(actor_role="admin")
    try:
        client = TestClient(app)
        resp = client.patch(
            "/teams/members/target-uid/role",
            json={"role": "viewer"},
            headers={"Authorization": "Bearer fake-admin-token"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["role"] == "viewer"
        assert body["user_id"] == "target-uid"
        ws_mock.update_member_role.assert_awaited_once()
    finally:
        ws_patcher.stop()


@pytest.mark.asyncio
async def test_admin_assigns_admin_role_returns_200():
    """Admin actor promotes member to admin and gets 200."""
    app, ws_mock, ws_patcher = _build_app(actor_role="admin")
    ws_mock.update_member_role.return_value = {
        "id": "mem-1",
        "user_id": "target-uid",
        "email": "target@example.com",
        "full_name": "Target",
        "role": "admin",
        "joined_at": "2026-04-06T00:00:00Z",
    }
    try:
        client = TestClient(app)
        resp = client.patch(
            "/teams/members/target-uid/role",
            json={"role": "admin"},
            headers={"Authorization": "Bearer fake-admin-token"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "admin"
    finally:
        ws_patcher.stop()


@pytest.mark.asyncio
async def test_admin_assigns_editor_role_returns_200():
    """Admin actor demotes member to editor (Member) and gets 200."""
    app, ws_mock, ws_patcher = _build_app(actor_role="admin")
    ws_mock.update_member_role.return_value = {
        "id": "mem-1",
        "user_id": "target-uid",
        "email": "target@example.com",
        "full_name": "Target",
        "role": "editor",
        "joined_at": "2026-04-06T00:00:00Z",
    }
    try:
        client = TestClient(app)
        resp = client.patch(
            "/teams/members/target-uid/role",
            json={"role": "editor"},
            headers={"Authorization": "Bearer fake-admin-token"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "editor"
    finally:
        ws_patcher.stop()


# ---------------------------------------------------------------------------
# Validation: invalid role string -> 422 from Pydantic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_role_value_returns_422():
    """Pydantic UpdateRoleRequest rejects roles outside (admin|editor|viewer)."""
    app, _ws_mock, ws_patcher = _build_app(actor_role="admin")
    try:
        client = TestClient(app)
        resp = client.patch(
            "/teams/members/target-uid/role",
            json={"role": "owner"},
            headers={"Authorization": "Bearer fake-admin-token"},
        )
        assert resp.status_code == 422, resp.text
    finally:
        ws_patcher.stop()


# ---------------------------------------------------------------------------
# Auth: missing token -> 401/403 from HTTPBearer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_auth_header_returns_401_or_403():
    """No Authorization header on PATCH should be rejected by the auth gate.

    NOTE: this test does NOT use _build_app's dependency override for
    get_current_user_id — we mount the router with the REAL HTTPBearer security
    dependency intact so we can verify the gate fires.
    """
    from app.routers import teams_rbac

    app = FastAPI()
    # Patch WorkspaceService so that even if the request slipped through, the
    # service call would not blow up. The point is the auth gate fires first.
    with patch("app.routers.teams_rbac.WorkspaceService"):
        app.include_router(teams_rbac.router)
        client = TestClient(app)
        resp = client.patch(
            "/teams/members/target-uid/role",
            json={"role": "viewer"},
        )
        assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# Permission: non-admin actor -> 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_admin_actor_returns_403():
    """A workspace editor cannot PATCH a member's role — require_role denies."""
    app, _ws_mock, ws_patcher = _build_app(actor_role="editor")
    try:
        client = TestClient(app)
        resp = client.patch(
            "/teams/members/target-uid/role",
            json={"role": "viewer"},
            headers={"Authorization": "Bearer fake-editor-token"},
        )
        assert resp.status_code == 403, resp.text
    finally:
        ws_patcher.stop()


# ---------------------------------------------------------------------------
# CRITICAL — feature-gate bypass test (AUTH-03 success criterion)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_on_non_teams_tier_can_call_role_endpoint():
    """Proves the new sibling router is NOT behind the `teams` feature gate.

    AUTH-03: a workspace admin on solopreneur (no `teams` feature gate) MUST
    be able to PATCH /teams/members/{id}/role and receive 200. We monkey-patch
    `app.middleware.feature_gate.require_feature` to RAISE 403 if anything in
    the call path tries to invoke it. The handler must still return 200 —
    proving the new router does NOT depend on require_feature.
    """
    from fastapi import HTTPException as _HTTPException

    def fake_require_feature(name: str):
        def _dep():
            raise _HTTPException(
                status_code=403, detail=f"feature {name} not enabled"
            )

        return _dep

    with patch(
        "app.middleware.feature_gate.require_feature",
        side_effect=fake_require_feature,
    ):
        app, _ws_mock, ws_patcher = _build_app(actor_role="admin")
        try:
            client = TestClient(app)
            resp = client.patch(
                "/teams/members/target-uid/role",
                json={"role": "viewer"},
                headers={"Authorization": "Bearer fake-admin-token"},
            )
            assert resp.status_code == 200, (
                f"Expected 200 (un-gated), got {resp.status_code}: {resp.text}"
            )
            assert resp.json()["role"] == "viewer"
        finally:
            ws_patcher.stop()
