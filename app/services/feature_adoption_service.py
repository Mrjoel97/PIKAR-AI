# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Feature adoption service for the AdminAgent (Phase 69).

Provides ``FeatureAdoptionService`` which queries ``tool_telemetry`` to
compute per-agent, per-user tool usage metrics over a configurable time window.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.base_service import AdminService
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class FeatureAdoptionService(AdminService):
    """Service for computing feature adoption metrics from tool_telemetry.

    Inherits ``AdminService`` for service-role DB access (bypasses RLS),
    consistent with other admin analytics services.
    """

    async def compute_adoption(
        self,
        days: int = 30,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute per-agent tool adoption metrics.

        Queries ``tool_telemetry`` for the last ``days`` days, optionally
        filtered by ``user_id``, and groups results by agent and tool.

        Args:
            days: Number of days to look back (default 30).
            user_id: Optional UUID to restrict to a single user. When None,
                returns platform-wide metrics including unique_users counts.

        Returns:
            Dict with:
            - ``agent_adoption``: list of per-agent dicts:
              - ``agent_name``: which agent
              - ``unique_tools_used``: count of distinct tools
              - ``total_calls``: total tool invocations
              - ``top_tools``: list of {tool_name, call_count} top 5 by calls
              - ``unique_users``: count of distinct users (only when user_id is None)
            - ``total_agents_active``: number of distinct agents seen
            - ``total_unique_tools``: number of distinct tools across all agents
            - ``period_days``: the days parameter used
        """
        client = get_service_client()
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        try:
            query = (
                client.table("tool_telemetry")
                .select("tool_name, agent_name, user_id, status, created_at")
                .gte("created_at", since)
            )
            if user_id is not None:
                query = query.eq("user_id", user_id)

            result = await execute_async(query, op_name="feature_adoption.fetch")
            rows: list[dict] = result.data or []

        except Exception as exc:
            logger.error("FeatureAdoptionService.compute_adoption failed: %s", exc)
            return {
                "agent_adoption": [],
                "total_agents_active": 0,
                "total_unique_tools": 0,
                "period_days": days,
                "error": str(exc),
            }

        # Group rows by agent_name
        # per_agent[agent_name] = {tool_name: {count, users_set}}
        per_agent: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"tools": defaultdict(lambda: {"count": 0, "users": set()})}
        )

        for row in rows:
            agent = row.get("agent_name") or "unknown"
            tool = row.get("tool_name") or "unknown"
            uid = row.get("user_id")
            per_agent[agent]["tools"][tool]["count"] += 1
            if uid:
                per_agent[agent]["tools"][tool]["users"].add(uid)

        # Build adoption list
        agent_adoption: list[dict] = []
        all_tools: set[str] = set()

        for agent_name, data in per_agent.items():
            tools_data = data["tools"]
            all_tools.update(tools_data.keys())

            # Sort tools by call count descending, take top 5
            sorted_tools = sorted(
                tools_data.items(), key=lambda kv: kv[1]["count"], reverse=True
            )
            top_tools = [
                {"tool_name": tname, "call_count": tdata["count"]}
                for tname, tdata in sorted_tools[:5]
            ]

            total_calls = sum(t["count"] for t in tools_data.values())
            unique_tools = len(tools_data)

            entry: dict[str, Any] = {
                "agent_name": agent_name,
                "unique_tools_used": unique_tools,
                "total_calls": total_calls,
                "top_tools": top_tools,
            }

            # Only include unique_users in platform-wide mode
            if user_id is None:
                all_users: set[str] = set()
                for tdata in tools_data.values():
                    all_users.update(tdata["users"])
                entry["unique_users"] = len(all_users)

            agent_adoption.append(entry)

        # Sort by total_calls descending for readability
        agent_adoption.sort(key=lambda e: e["total_calls"], reverse=True)

        return {
            "agent_adoption": agent_adoption,
            "total_agents_active": len(agent_adoption),
            "total_unique_tools": len(all_tools),
            "period_days": days,
        }
