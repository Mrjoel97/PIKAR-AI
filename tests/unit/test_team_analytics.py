# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for team analytics service and router endpoints.

Tests cover:
- TeamAnalyticsService: workspace-scoped KPI aggregation, per-member KPI breakdown
- TeamAnalyticsService: resource-grouped activity feed from governance_audit_log
- TeamAnalyticsService: shared initiatives and workflow queries scoped to member IDs
- Router: GET /teams/analytics with role-gated per-member breakdown
- Router: GET /teams/shared/initiatives, GET /teams/shared/workflows
- Router: GET /teams/activity resource-grouped feed
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_members(count: int = 3) -> list[dict]:
    """Return a list of workspace member dicts."""
    return [
        {
            "id": f"mem-{i}",
            "user_id": f"user-{i}",
            "role": "admin" if i == 0 else "editor",
            "joined_at": "2026-01-01T00:00:00Z",
            "email": f"user{i}@example.com",
            "full_name": f"User {i}",
        }
        for i in range(count)
    ]


def _make_audit_rows() -> list[dict]:
    """Return audit log rows spanning multiple resources."""
    return [
        {
            "id": "a1",
            "user_id": "user-0",
            "action_type": "initiative.created",
            "resource_type": "initiative",
            "resource_id": "init-1",
            "details": {"resource_name": "Project Alpha"},
            "created_at": "2026-03-10T12:00:00Z",
        },
        {
            "id": "a2",
            "user_id": "user-1",
            "action_type": "initiative.updated",
            "resource_type": "initiative",
            "resource_id": "init-1",
            "details": {},
            "created_at": "2026-03-10T13:00:00Z",
        },
        {
            "id": "a3",
            "user_id": "user-2",
            "action_type": "workflow.started",
            "resource_type": "workflow",
            "resource_id": "wf-1",
            "details": {"resource_name": "Weekly Report"},
            "created_at": "2026-03-09T09:00:00Z",
        },
    ]


# ---------------------------------------------------------------------------
# Service: TestTeamKpis
# ---------------------------------------------------------------------------


class TestTeamKpis:
    """get_team_kpis returns aggregate KPIs across all workspace members."""

    @pytest.mark.asyncio
    async def test_get_team_kpis_returns_aggregate_counts(self):
        """Aggregate KPIs include all expected keys and correct values."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(3)
        member_ids = [m["user_id"] for m in members]

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        def make_count_response(count: int):
            resp = MagicMock()
            resp.data = [{"count": count}]
            return resp

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_exec.side_effect = [
                make_count_response(5),   # initiatives
                make_count_response(10),  # workflow_executions
                make_count_response(7),   # tasks
                make_count_response(3),   # pending approvals
                make_count_response(4),   # active workflows
            ]
            mock_client.return_value = MagicMock()

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_team_kpis("ws-1")

        assert result["total_initiatives"] == 5
        assert result["total_workflows"] == 10
        assert result["total_tasks"] == 7
        assert result["total_approvals"] == 3
        assert result["active_workflows"] == 4
        assert result["member_count"] == 3

    @pytest.mark.asyncio
    async def test_get_team_kpis_empty_workspace(self):
        """Returns zeros when workspace has no members."""
        from app.services.team_analytics_service import TeamAnalyticsService

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = []

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch("app.services.team_analytics_service.get_service_client"),
        ):
            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_team_kpis("ws-empty")

        assert result["member_count"] == 0
        assert result["total_initiatives"] == 0
        assert result["total_workflows"] == 0

    @pytest.mark.asyncio
    async def test_get_per_member_kpis_returns_per_member_list(self):
        """Per-member KPIs list contains one dict per workspace member."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(2)

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        def make_count_resp(count: int):
            r = MagicMock()
            r.data = [{"count": count}]
            return r

        # 4 queries per member: initiatives, workflows, tasks, approvals
        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.side_effect = [
                make_count_resp(2),  # user-0 initiatives
                make_count_resp(3),  # user-0 workflows
                make_count_resp(1),  # user-0 tasks
                make_count_resp(0),  # user-0 approvals
                make_count_resp(1),  # user-1 initiatives
                make_count_resp(4),  # user-1 workflows
                make_count_resp(2),  # user-1 tasks
                make_count_resp(1),  # user-1 approvals
            ]

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_per_member_kpis("ws-1")

        assert len(result) == 2
        assert result[0]["user_id"] == "user-0"
        assert result[0]["initiatives"] == 2
        assert result[0]["workflows"] == 3
        assert result[1]["user_id"] == "user-1"
        assert result[1]["approvals"] == 1

    @pytest.mark.asyncio
    async def test_per_member_kpis_includes_display_name(self):
        """Per-member KPI dict includes display_name and email from member profile."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = [
            {
                "id": "mem-0",
                "user_id": "user-0",
                "role": "admin",
                "joined_at": "2026-01-01T00:00:00Z",
                "email": "alice@example.com",
                "full_name": "Alice",
            }
        ]

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        def zero_count():
            r = MagicMock()
            r.data = [{"count": 0}]
            return r

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.side_effect = [zero_count() for _ in range(4)]

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_per_member_kpis("ws-1")

        assert result[0]["display_name"] == "Alice"
        assert result[0]["email"] == "alice@example.com"


# ---------------------------------------------------------------------------
# Service: TestRoleVisibility
# ---------------------------------------------------------------------------


class TestRoleVisibility:
    """Service does NOT enforce roles — that is the router layer's job."""

    @pytest.mark.asyncio
    async def test_get_team_kpis_has_no_role_check(self):
        """get_team_kpis accepts any workspace_id without checking caller role."""
        from app.services.team_analytics_service import TeamAnalyticsService

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = []

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch("app.services.team_analytics_service.get_service_client"),
        ):
            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            # Should not raise any PermissionError
            result = await svc.get_team_kpis("any-workspace-id")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_per_member_kpis_has_no_role_check(self):
        """get_per_member_kpis accepts any workspace_id without checking caller role."""
        from app.services.team_analytics_service import TeamAnalyticsService

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = []

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch("app.services.team_analytics_service.get_service_client"),
        ):
            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            # Should not raise
            result = await svc.get_per_member_kpis("any-workspace-id")
            assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Service: TestTeamSharing
# ---------------------------------------------------------------------------


class TestTeamSharing:
    """Shared initiatives and workflows scoped to workspace member IDs."""

    @pytest.mark.asyncio
    async def test_get_shared_initiatives_scoped_to_members(self):
        """get_shared_initiatives uses member_ids for .in_ filter."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(2)
        initiatives = [
            {"id": "i-1", "title": "Alpha", "user_id": "user-0"},
            {"id": "i-2", "title": "Beta", "user_id": "user-1"},
        ]

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        mock_resp = MagicMock()
        mock_resp.data = initiatives

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.return_value = mock_resp

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_shared_initiatives("ws-1", limit=50)

        assert len(result) == 2
        assert result[0]["id"] == "i-1"

    @pytest.mark.asyncio
    async def test_get_shared_initiatives_empty_when_no_members(self):
        """Returns empty list when workspace has no members."""
        from app.services.team_analytics_service import TeamAnalyticsService

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = []

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch("app.services.team_analytics_service.get_service_client"),
        ):
            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_shared_initiatives("ws-empty")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_shared_workflows_scoped_to_members(self):
        """get_shared_workflows returns workflow_executions filtered to member IDs."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(2)
        workflows = [
            {"id": "w-1", "workflow_id": "wf-1", "user_id": "user-0"},
        ]

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        mock_resp = MagicMock()
        mock_resp.data = workflows

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.return_value = mock_resp

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_shared_workflows("ws-1")

        assert len(result) == 1
        assert result[0]["id"] == "w-1"


# ---------------------------------------------------------------------------
# Service: TestActivityFeed
# ---------------------------------------------------------------------------


class TestActivityFeed:
    """Activity feed groups audit_log rows by (resource_type, resource_id)."""

    @pytest.mark.asyncio
    async def test_get_activity_feed_groups_by_resource(self):
        """Audit rows with same resource are combined into one cluster."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(3)
        audit_rows = _make_audit_rows()

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        mock_resp = MagicMock()
        mock_resp.data = audit_rows

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.return_value = mock_resp

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_activity_feed("ws-1")

        # Two distinct resources: initiative/init-1 and workflow/wf-1
        assert len(result) == 2

        # Find the initiative cluster
        init_cluster = next(
            (r for r in result if r["resource_type"] == "initiative"), None
        )
        assert init_cluster is not None
        assert init_cluster["resource_id"] == "init-1"
        assert len(init_cluster["events"]) == 2

        wf_cluster = next(
            (r for r in result if r["resource_type"] == "workflow"), None
        )
        assert wf_cluster is not None
        assert len(wf_cluster["events"]) == 1

    @pytest.mark.asyncio
    async def test_get_activity_feed_sorted_most_recent_first(self):
        """Clusters are sorted by the most recent event timestamp (descending)."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(2)
        # initiative has events at 12:00 and 13:00, workflow at 09:00
        # So initiative cluster (latest at 13:00) should appear before workflow (09:00)
        audit_rows = _make_audit_rows()

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        mock_resp = MagicMock()
        mock_resp.data = audit_rows

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.return_value = mock_resp

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_activity_feed("ws-1")

        # Most recently active cluster first
        assert result[0]["resource_type"] == "initiative"
        assert result[1]["resource_type"] == "workflow"

    @pytest.mark.asyncio
    async def test_get_activity_feed_uses_single_query(self):
        """Activity feed executes exactly one DB query (single .in_ on member_ids)."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(2)

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        mock_resp = MagicMock()
        mock_resp.data = []

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.return_value = mock_resp

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            await svc.get_activity_feed("ws-1")

        # Only 1 execute_async call for the audit_log query
        assert mock_exec.call_count == 1

    @pytest.mark.asyncio
    async def test_get_activity_feed_resource_name_from_details(self):
        """resource_name is extracted from the first event's details dict if present."""
        from app.services.team_analytics_service import TeamAnalyticsService

        members = _make_members(1)
        audit_rows = [
            {
                "id": "a1",
                "user_id": "user-0",
                "action_type": "initiative.created",
                "resource_type": "initiative",
                "resource_id": "init-1",
                "details": {"resource_name": "Project Alpha"},
                "created_at": "2026-03-10T12:00:00Z",
            }
        ]

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = members

        mock_resp = MagicMock()
        mock_resp.data = audit_rows

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch(
                "app.services.team_analytics_service.get_service_client"
            ) as mock_client,
            patch(
                "app.services.team_analytics_service.execute_async",
                new_callable=AsyncMock,
            ) as mock_exec,
        ):
            mock_client.return_value = MagicMock()
            mock_exec.return_value = mock_resp

            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_activity_feed("ws-1")

        assert result[0]["resource_name"] == "Project Alpha"

    @pytest.mark.asyncio
    async def test_get_activity_feed_empty_when_no_members(self):
        """Returns empty list when workspace has no members."""
        from app.services.team_analytics_service import TeamAnalyticsService

        ws_service_mock = AsyncMock()
        ws_service_mock.get_workspace_members.return_value = []

        with (
            patch(
                "app.services.team_analytics_service.WorkspaceService",
                return_value=ws_service_mock,
            ),
            patch("app.services.team_analytics_service.get_service_client"),
        ):
            svc = TeamAnalyticsService()
            svc.ws_service = ws_service_mock

            result = await svc.get_activity_feed("ws-1")

        assert result == []


# ---------------------------------------------------------------------------
# Router: TestTeamAnalyticsEndpoint
# ---------------------------------------------------------------------------


class TestTeamAnalyticsEndpoint:
    """GET /teams/analytics endpoint tests."""

    @pytest.mark.asyncio
    async def test_admin_gets_member_breakdown(self):
        """Admin role includes per_member_breakdown in response."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        kpis = {
            "total_initiatives": 10,
            "total_workflows": 20,
            "total_tasks": 5,
            "total_approvals": 2,
            "active_workflows": 3,
            "member_count": 2,
        }
        member_breakdown = [
            {
                "user_id": "user-0",
                "display_name": "User 0",
                "email": "user0@example.com",
                "initiatives": 6,
                "workflows": 12,
                "tasks": 3,
                "approvals": 1,
            }
        ]
        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-0",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws.get_member_role.return_value = "admin"
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_team_kpis.return_value = kpis
            mock_svc.get_per_member_kpis.return_value = member_breakdown
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            resp = client.get(
                "/teams/analytics",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["kpis"]["total_initiatives"] == 10
        assert data["member_breakdown"] is not None
        assert len(data["member_breakdown"]) == 1

    @pytest.mark.asyncio
    async def test_non_admin_gets_null_breakdown(self):
        """Non-admin role returns member_breakdown as null."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        kpis = {
            "total_initiatives": 5,
            "total_workflows": 8,
            "total_tasks": 2,
            "total_approvals": 1,
            "active_workflows": 1,
            "member_count": 3,
        }
        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-1",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws.get_member_role.return_value = "viewer"
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_team_kpis.return_value = kpis
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            resp = client.get(
                "/teams/analytics",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["kpis"]["total_workflows"] == 8
        assert data["member_breakdown"] is None

    @pytest.mark.asyncio
    async def test_analytics_returns_404_when_no_workspace(self):
        """Returns 404 when user has no workspace."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-no-ws",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService"),
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = None
            mock_ws_cls.return_value = mock_ws

            client = TestClient(app)
            resp = client.get(
                "/teams/analytics",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Router: TestSharedResourcesEndpoint
# ---------------------------------------------------------------------------


class TestSharedResourcesEndpoint:
    """GET /teams/shared/initiatives and GET /teams/shared/workflows endpoints."""

    @pytest.mark.asyncio
    async def test_shared_initiatives_returns_list(self):
        """GET /teams/shared/initiatives returns a list of initiative dicts."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}
        initiatives = [
            {"id": "i-1", "title": "Alpha", "user_id": "user-0"},
            {"id": "i-2", "title": "Beta", "user_id": "user-1"},
        ]

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-0",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_shared_initiatives.return_value = initiatives
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            resp = client.get(
                "/teams/shared/initiatives?limit=50",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_shared_initiatives_limit_passed_through(self):
        """limit query param is forwarded to get_shared_initiatives."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-0",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_shared_initiatives.return_value = []
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            client.get(
                "/teams/shared/initiatives?limit=10",
                headers={"Authorization": "Bearer test-token"},
            )

            mock_svc.get_shared_initiatives.assert_called_once_with("ws-1", limit=10)

    @pytest.mark.asyncio
    async def test_shared_workflows_returns_list(self):
        """GET /teams/shared/workflows returns workflow execution dicts."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}
        workflows = [{"id": "w-1", "workflow_id": "wf-1", "user_id": "user-0"}]

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-0",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_shared_workflows.return_value = workflows
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            resp = client.get(
                "/teams/shared/workflows",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


# ---------------------------------------------------------------------------
# Router: TestActivityFeedEndpoint
# ---------------------------------------------------------------------------


class TestActivityFeedEndpoint:
    """GET /teams/activity endpoint returns resource-grouped clusters."""

    @pytest.mark.asyncio
    async def test_activity_feed_returns_grouped_clusters(self):
        """GET /teams/activity returns a list of resource cluster dicts."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}
        clusters = [
            {
                "resource_type": "initiative",
                "resource_id": "init-1",
                "resource_name": "Project Alpha",
                "events": [
                    {"id": "a1", "action_type": "initiative.created"},
                    {"id": "a2", "action_type": "initiative.updated"},
                ],
            }
        ]

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-0",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_activity_feed.return_value = clusters
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            resp = client.get(
                "/teams/activity",
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["resource_type"] == "initiative"
        assert len(data[0]["events"]) == 2

    @pytest.mark.asyncio
    async def test_activity_feed_limit_param_passed_through(self):
        """limit query param forwarded to get_activity_feed."""
        from fastapi.testclient import TestClient

        from app.fast_api_app import app

        workspace = {"id": "ws-1", "name": "Acme", "owner_id": "user-0"}

        with (
            patch(
                "app.routers.teams.get_current_user_id",
                return_value="user-0",
            ),
            patch("app.routers.teams.require_feature", return_value=lambda: None),
            patch("app.routers.teams.TeamAnalyticsService") as mock_svc_cls,
            patch("app.routers.teams.WorkspaceService") as mock_ws_cls,
        ):
            mock_ws = AsyncMock()
            mock_ws.get_workspace_for_user.return_value = workspace
            mock_ws_cls.return_value = mock_ws

            mock_svc = AsyncMock()
            mock_svc.get_activity_feed.return_value = []
            mock_svc_cls.return_value = mock_svc

            client = TestClient(app)
            client.get(
                "/teams/activity?limit=25",
                headers={"Authorization": "Bearer test-token"},
            )

            mock_svc.get_activity_feed.assert_called_once_with("ws-1", limit=25)
