# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Team analytics service for workspace-scoped KPIs and activity feed.

Provides aggregate KPI counts across all workspace members, per-member
breakdowns, shared resource browsing, and a resource-grouped activity
feed built from the governance_audit_log table.

Role enforcement is intentionally absent here — it belongs in the router
layer. Any caller with a valid workspace_id may retrieve analytics.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


class TeamAnalyticsService:
    """Service for team-scoped analytics, shared resources, and activity feed.

    All queries use member_ids extracted from workspace_members so data is
    always scoped to the correct workspace without requiring workspace_id
    columns on every table.
    """

    def __init__(self) -> None:
        """Initialise with the Supabase service client and a WorkspaceService."""
        self.client = get_service_client()
        self.ws_service = WorkspaceService()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _safe_rows(self, query: Any) -> list[dict[str, Any]]:
        """Execute a query and return rows, swallowing any error.

        Args:
            query: A Supabase query builder instance.

        Returns:
            List of row dicts, or an empty list on error.
        """
        try:
            response = await execute_async(query, op_name="team_analytics.query")
            return response.data or []
        except Exception:
            logger.debug("team_analytics: query failed, returning []")
            return []

    def _extract_count(self, response: Any) -> int:
        """Pull an integer count from a Supabase count-query response.

        Args:
            response: Raw response object from execute_async.

        Returns:
            Integer count value, defaulting to 0 on any format mismatch.
        """
        rows = response.data or []
        if rows and isinstance(rows[0], dict) and "count" in rows[0]:
            return int(rows[0]["count"])
        return len(rows)

    # ------------------------------------------------------------------
    # Aggregate KPIs
    # ------------------------------------------------------------------

    async def get_team_kpis(self, workspace_id: str) -> dict[str, Any]:
        """Return aggregate KPI counts across all workspace members.

        Queries are run sequentially against four tables (initiatives,
        workflow_executions, tasks, approval_requests) filtered by the
        workspace member ID list.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            Dict with keys: total_initiatives, total_workflows, total_tasks,
            total_approvals, active_workflows, member_count.
        """
        members = await self.ws_service.get_workspace_members(workspace_id)
        member_ids = [m["user_id"] for m in members]

        if not member_ids:
            return {
                "total_initiatives": 0,
                "total_workflows": 0,
                "total_tasks": 0,
                "total_approvals": 0,
                "active_workflows": 0,
                "member_count": 0,
            }

        initiatives_resp = await execute_async(
            self.client.table("initiatives")
            .select("id", count="exact")
            .in_("user_id", member_ids),
            op_name="team_analytics.count_initiatives",
        )
        workflows_resp = await execute_async(
            self.client.table("workflow_executions")
            .select("id", count="exact")
            .in_("user_id", member_ids),
            op_name="team_analytics.count_workflows",
        )
        tasks_resp = await execute_async(
            self.client.table("tasks")
            .select("id", count="exact")
            .in_("user_id", member_ids),
            op_name="team_analytics.count_tasks",
        )
        approvals_resp = await execute_async(
            self.client.table("approval_requests")
            .select("id", count="exact")
            .in_("user_id", member_ids)
            .eq("status", "PENDING"),
            op_name="team_analytics.count_approvals",
        )
        active_wf_resp = await execute_async(
            self.client.table("workflow_executions")
            .select("id", count="exact")
            .in_("user_id", member_ids)
            .in_("status", ["pending", "running", "waiting_approval"]),
            op_name="team_analytics.count_active_workflows",
        )

        return {
            "total_initiatives": self._extract_count(initiatives_resp),
            "total_workflows": self._extract_count(workflows_resp),
            "total_tasks": self._extract_count(tasks_resp),
            "total_approvals": self._extract_count(approvals_resp),
            "active_workflows": self._extract_count(active_wf_resp),
            "member_count": len(member_ids),
        }

    # ------------------------------------------------------------------
    # Per-member KPI breakdown
    # ------------------------------------------------------------------

    async def get_per_member_kpis(self, workspace_id: str) -> list[dict[str, Any]]:
        """Return per-member KPI counts for all workspace members.

        Runs 4 count queries per member (initiatives, workflow_executions,
        tasks, approval_requests). Acceptable for workspaces <20 members.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            List of dicts with keys: user_id, display_name, email,
            initiatives, workflows, tasks, approvals.
        """
        members = await self.ws_service.get_workspace_members(workspace_id)
        if not members:
            return []

        result: list[dict[str, Any]] = []
        for m in members:
            uid = m["user_id"]

            init_resp = await execute_async(
                self.client.table("initiatives")
                .select("id", count="exact")
                .in_("user_id", [uid]),
                op_name="team_analytics.member_initiatives",
            )
            wf_resp = await execute_async(
                self.client.table("workflow_executions")
                .select("id", count="exact")
                .in_("user_id", [uid]),
                op_name="team_analytics.member_workflows",
            )
            task_resp = await execute_async(
                self.client.table("tasks")
                .select("id", count="exact")
                .in_("user_id", [uid]),
                op_name="team_analytics.member_tasks",
            )
            approval_resp = await execute_async(
                self.client.table("approval_requests")
                .select("id", count="exact")
                .in_("user_id", [uid])
                .eq("status", "PENDING"),
                op_name="team_analytics.member_approvals",
            )

            result.append(
                {
                    "user_id": uid,
                    "display_name": m.get("full_name"),
                    "email": m.get("email"),
                    "initiatives": self._extract_count(init_resp),
                    "workflows": self._extract_count(wf_resp),
                    "tasks": self._extract_count(task_resp),
                    "approvals": self._extract_count(approval_resp),
                }
            )

        return result

    # ------------------------------------------------------------------
    # Shared resources
    # ------------------------------------------------------------------

    async def get_shared_initiatives(
        self, workspace_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return initiatives created by any workspace member.

        Args:
            workspace_id: The workspace UUID.
            limit: Maximum number of rows to return.

        Returns:
            List of initiative row dicts ordered by updated_at descending.
        """
        members = await self.ws_service.get_workspace_members(workspace_id)
        member_ids = [m["user_id"] for m in members]
        if not member_ids:
            return []

        return await self._safe_rows(
            self.client.table("initiatives")
            .select("*")
            .in_("user_id", member_ids)
            .order("updated_at", desc=True)
            .limit(limit)
        )

    async def get_shared_workflows(
        self, workspace_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return workflow executions created by any workspace member.

        Args:
            workspace_id: The workspace UUID.
            limit: Maximum number of rows to return.

        Returns:
            List of workflow_executions row dicts ordered by created_at descending.
        """
        members = await self.ws_service.get_workspace_members(workspace_id)
        member_ids = [m["user_id"] for m in members]
        if not member_ids:
            return []

        return await self._safe_rows(
            self.client.table("workflow_executions")
            .select("*")
            .in_("user_id", member_ids)
            .order("created_at", desc=True)
            .limit(limit)
        )

    # ------------------------------------------------------------------
    # Activity feed
    # ------------------------------------------------------------------

    async def get_activity_feed(
        self, workspace_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return audit log events grouped by resource.

        Uses a single query against governance_audit_log filtered by
        workspace member IDs. Python-level grouping avoids N+1 queries.
        Clusters are sorted by the most recent event timestamp per group,
        descending.

        Args:
            workspace_id: The workspace UUID.
            limit: Maximum number of audit rows to pull.

        Returns:
            List of cluster dicts: {resource_type, resource_id,
            resource_name, events: [...]}, sorted most-recently-active
            first.
        """
        members = await self.ws_service.get_workspace_members(workspace_id)
        member_ids = [m["user_id"] for m in members]
        if not member_ids:
            return []

        audit_resp = await execute_async(
            self.client.table("governance_audit_log")
            .select("*")
            .in_("user_id", member_ids)
            .order("created_at", desc=True)
            .limit(limit),
            op_name="team_analytics.activity_feed",
        )
        rows = audit_resp.data or []

        # Group by (resource_type, resource_id)
        groups: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = (row.get("resource_type", ""), row.get("resource_id"))
            groups[key].append(row)

        # Build clusters
        clusters: list[dict[str, Any]] = []
        for (resource_type, resource_id), events in groups.items():
            # Extract resource_name from the first event's details if present
            first_details = events[0].get("details") or {}
            resource_name = (
                first_details.get("resource_name")
                if isinstance(first_details, dict)
                else None
            )

            # Most recent event timestamp for sorting clusters
            latest_ts = events[0].get("created_at", "")

            clusters.append(
                {
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "latest_at": latest_ts,
                    "events": events,
                }
            )

        # Sort clusters by most recently active (events already sorted desc by DB)
        clusters.sort(key=lambda c: c.get("latest_at") or "", reverse=True)

        # Remove internal latest_at from output
        for c in clusters:
            c.pop("latest_at", None)

        return clusters
