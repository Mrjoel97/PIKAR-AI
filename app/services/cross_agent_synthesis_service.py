# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Cross-Agent Business Synthesis Service.

Fans out queries to multiple domain data sources (Financial, Sales,
Marketing, Data) in parallel using asyncio.gather, merges results into
a unified business health snapshot with graceful degradation when
individual sources fail.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class CrossAgentSynthesisService:
    """Gathers business health data from multiple domain sources.

    Singleton pattern -- use ``get_cross_agent_synthesis_service()``.
    """

    _instance: CrossAgentSynthesisService | None = None

    def __new__(cls) -> CrossAgentSynthesisService:
        """Singleton pattern to ensure one global service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._client = get_service_client()
            self._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def gather_business_health(
        self,
        user_id: str,
        time_range_days: int = 7,
    ) -> dict[str, Any]:
        """Gather business health data from all domain sources.

        Uses ``asyncio.gather`` with ``return_exceptions=True`` to fan
        out to Financial, Sales, Marketing, and Data sources in parallel.
        Individual failures degrade gracefully -- the response still
        includes data from the sources that succeeded.

        Args:
            user_id: The user whose business data to query.
            time_range_days: Look-back window in days (default 7).

        Returns:
            Dictionary with keys ``financial``, ``sales``, ``marketing``,
            ``data``, and ``gathered_at`` (ISO timestamp).
        """
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=time_range_days)
        ).isoformat()

        results = await asyncio.gather(
            self._gather_financial(user_id, cutoff),
            self._gather_sales(user_id, cutoff),
            self._gather_marketing(user_id, cutoff),
            self._gather_data(user_id, cutoff),
            return_exceptions=True,
        )

        domain_keys = ["financial", "sales", "marketing", "data"]
        snapshot: dict[str, Any] = {}

        for key, result in zip(domain_keys, results, strict=True):
            if isinstance(result, BaseException):
                snapshot[key] = {
                    "status": "unavailable",
                    "error": str(result),
                    "highlights": [],
                    "metrics": {},
                }
            else:
                snapshot[key] = result

        snapshot["gathered_at"] = datetime.now(timezone.utc).isoformat()
        return snapshot

    # ------------------------------------------------------------------
    # Private domain gatherers
    # ------------------------------------------------------------------

    async def _gather_financial(
        self, user_id: str, cutoff: str
    ) -> dict[str, Any]:
        """Gather financial domain data.

        Queries workflow_executions for recent financial-related workflows
        and interaction_logs for FinancialAnalysisAgent recent summaries.
        """
        try:
            # Recent financial workflow executions
            workflows_resp = await execute_async(
                self._client.table("workflow_executions")
                .select("id, workflow_name, status, created_at")
                .eq("user_id", user_id)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(10),
                op_name="synthesis.financial.workflows",
            )

            # Recent FinancialAnalysisAgent interaction summaries
            interactions_resp = await execute_async(
                self._client.table("interaction_logs")
                .select("agent_response_summary, skill_used, created_at")
                .eq("user_id", user_id)
                .eq("agent_id", "FIN")
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(10),
                op_name="synthesis.financial.interactions",
            )

            workflows = workflows_resp.data or []
            interactions = interactions_resp.data or []

            highlights = []
            if workflows:
                completed = sum(1 for w in workflows if w.get("status") == "completed")
                highlights.append(
                    f"{len(workflows)} financial workflows in the last period "
                    f"({completed} completed)"
                )
            if interactions:
                highlights.append(
                    f"{len(interactions)} financial agent interactions recorded"
                )
            if not highlights:
                highlights.append("No recent financial activity found")

            return {
                "status": "ok",
                "highlights": highlights,
                "metrics": {
                    "workflow_count": len(workflows),
                    "interaction_count": len(interactions),
                },
            }
        except Exception as exc:
            logger.warning("Financial synthesis failed: %s", exc)
            return {
                "status": "unavailable",
                "error": str(exc),
                "highlights": [],
                "metrics": {},
            }

    async def _gather_sales(
        self, user_id: str, cutoff: str
    ) -> dict[str, Any]:
        """Gather sales domain data.

        Queries interaction_logs for SalesIntelligenceAgent recent
        summaries and the initiatives table for sales-tagged initiatives.
        """
        try:
            # Recent SalesIntelligenceAgent interactions
            interactions_resp = await execute_async(
                self._client.table("interaction_logs")
                .select("agent_response_summary, skill_used, created_at")
                .eq("user_id", user_id)
                .eq("agent_id", "SALES")
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(10),
                op_name="synthesis.sales.interactions",
            )

            # Sales-related initiatives
            initiatives_resp = await execute_async(
                self._client.table("initiatives")
                .select("id, title, status, created_at")
                .eq("user_id", user_id)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(10),
                op_name="synthesis.sales.initiatives",
            )

            interactions = interactions_resp.data or []
            initiatives = initiatives_resp.data or []

            highlights = []
            if interactions:
                highlights.append(
                    f"{len(interactions)} sales agent interactions recorded"
                )
            if initiatives:
                active = sum(
                    1
                    for i in initiatives
                    if i.get("status") in ("active", "in_progress")
                )
                highlights.append(
                    f"{len(initiatives)} initiatives tracked ({active} active)"
                )
            if not highlights:
                highlights.append("No recent sales activity found")

            return {
                "status": "ok",
                "highlights": highlights,
                "metrics": {
                    "interaction_count": len(interactions),
                    "initiative_count": len(initiatives),
                },
            }
        except Exception as exc:
            logger.warning("Sales synthesis failed: %s", exc)
            return {
                "status": "unavailable",
                "error": str(exc),
                "highlights": [],
                "metrics": {},
            }

    async def _gather_marketing(
        self, user_id: str, cutoff: str
    ) -> dict[str, Any]:
        """Gather marketing domain data.

        Queries interaction_logs for MarketingAutomationAgent activity
        and analytics_events for campaign-related events.
        """
        try:
            # Recent MarketingAutomationAgent interactions
            interactions_resp = await execute_async(
                self._client.table("interaction_logs")
                .select("agent_response_summary, skill_used, created_at")
                .eq("user_id", user_id)
                .eq("agent_id", "MKT")
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(10),
                op_name="synthesis.marketing.interactions",
            )

            # Campaign-related analytics events
            events_resp = await execute_async(
                self._client.table("analytics_events")
                .select("event_type, event_data, created_at")
                .eq("user_id", user_id)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(20),
                op_name="synthesis.marketing.events",
            )

            interactions = interactions_resp.data or []
            events = events_resp.data or []

            highlights = []
            if interactions:
                highlights.append(
                    f"{len(interactions)} marketing agent interactions recorded"
                )
            if events:
                highlights.append(
                    f"{len(events)} analytics events in the last period"
                )
            if not highlights:
                highlights.append("No recent marketing activity found")

            return {
                "status": "ok",
                "highlights": highlights,
                "metrics": {
                    "interaction_count": len(interactions),
                    "event_count": len(events),
                },
            }
        except Exception as exc:
            logger.warning("Marketing synthesis failed: %s", exc)
            return {
                "status": "unavailable",
                "error": str(exc),
                "highlights": [],
                "metrics": {},
            }

    async def _gather_data(
        self, user_id: str, cutoff: str
    ) -> dict[str, Any]:
        """Gather data/analytics domain data.

        Queries analytics_events for recent trends and anomalies.
        """
        try:
            # Recent analytics events for trends/anomalies
            events_resp = await execute_async(
                self._client.table("analytics_events")
                .select("event_type, event_data, created_at")
                .eq("user_id", user_id)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(20),
                op_name="synthesis.data.events",
            )

            events = events_resp.data or []

            highlights = []
            if events:
                # Group by event type for summary
                event_types: dict[str, int] = {}
                for evt in events:
                    et = evt.get("event_type", "unknown")
                    event_types[et] = event_types.get(et, 0) + 1
                type_summary = ", ".join(
                    f"{count} {etype}" for etype, count in event_types.items()
                )
                highlights.append(
                    f"{len(events)} analytics events: {type_summary}"
                )
            else:
                highlights.append("No recent analytics events found")

            return {
                "status": "ok",
                "highlights": highlights,
                "metrics": {
                    "event_count": len(events),
                },
            }
        except Exception as exc:
            logger.warning("Data synthesis failed: %s", exc)
            return {
                "status": "unavailable",
                "error": str(exc),
                "highlights": [],
                "metrics": {},
            }


def get_cross_agent_synthesis_service() -> CrossAgentSynthesisService:
    """Get the singleton CrossAgentSynthesisService instance.

    Returns:
        The global CrossAgentSynthesisService singleton.
    """
    return CrossAgentSynthesisService()
