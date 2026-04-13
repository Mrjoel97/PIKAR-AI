# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""RegulatoryMonitorService -- regulatory change monitoring and deadline reminders.

Provides two capabilities for the Compliance & Risk Agent:

1. **check_updates** -- Uses web search to find recent regulatory changes
   affecting a user's industry and jurisdiction.  Returns structured results
   with relevance scoring.

2. **dispatch_deadline_reminders** -- Scans compliance_deadlines for entries
   within the reminder window and dispatches proactive alerts via
   ``ProactiveAlertService``.

Used by the ``check_regulatory_updates`` agent tool and scheduled background
tasks.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from app.mcp.agent_tools import mcp_web_search
from app.services.proactive_alert_service import dispatch_proactive_alert
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class RegulatoryMonitorService:
    """Service for monitoring regulatory changes and dispatching deadline reminders.

    Uses a service-role Supabase client for cross-user scheduled queries
    (dispatch_deadline_reminders) and web search for regulatory scanning
    (check_updates).
    """

    _deadlines_table = "compliance_deadlines"

    def __init__(self) -> None:
        """Initialize the regulatory monitor service."""
        self._client = get_service_client()

    # ------------------------------------------------------------------
    # Regulatory change scanning
    # ------------------------------------------------------------------

    async def check_updates(
        self,
        industry: str,
        jurisdiction: str,
        topics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Check for recent regulatory changes via web search.

        Builds a search query from the user's industry, jurisdiction, and
        optional topics, then parses results into a structured format with
        relevance scoring.

        Args:
            industry: User's industry (e.g. 'healthcare', 'fintech').
            jurisdiction: Jurisdiction (e.g. 'United States', 'European Union').
            topics: Optional specific topics to monitor (e.g. ['data privacy']).

        Returns:
            Dictionary with success flag, updates list, metadata.
        """
        from datetime import datetime

        topics_str = " ".join(topics or [])
        search_query = (
            f"new {industry} regulations {jurisdiction} {topics_str} 2026"
        ).strip()

        try:
            raw = await mcp_web_search(search_query)
            results = raw.get("results", [])

            updates = []
            for item in results:
                title = item.get("title", "")
                content = item.get("content", "")
                source_url = item.get("url", "")

                relevance = self._score_relevance(
                    title, content, industry, jurisdiction
                )

                updates.append(
                    {
                        "title": title,
                        "summary": content[:500] if content else "",
                        "source_url": source_url,
                        "relevance": relevance,
                        "date_published": item.get(
                            "published_date",
                            datetime.now().strftime("%Y-%m-%d"),
                        ),
                    }
                )

            return {
                "success": True,
                "industry": industry,
                "jurisdiction": jurisdiction,
                "updates": updates,
                "checked_at": datetime.now().isoformat(),
                "query": search_query,
            }
        except Exception as e:
            logger.exception("check_updates failed: %s", e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Deadline reminder dispatch
    # ------------------------------------------------------------------

    async def dispatch_deadline_reminders(
        self, user_id: str
    ) -> dict[str, Any]:
        """Find deadlines within reminder window and dispatch proactive alerts.

        Queries compliance_deadlines WHERE user_id AND status='upcoming'
        AND due_date is between today and today + reminder_days_before.
        For each match, dispatches a proactive alert via
        ``dispatch_proactive_alert``.

        Args:
            user_id: The user whose deadlines to check.

        Returns:
            Dictionary with reminders_sent and deadlines_checked counts.
        """
        today = date.today()

        # Fetch upcoming deadlines for this user that are within any
        # reasonable reminder window (max 90 days out).
        max_window = today + timedelta(days=90)
        query = (
            self._client.table(self._deadlines_table)
            .select("id,title,due_date,category,reminder_days_before")
            .eq("user_id", user_id)
            .eq("status", "upcoming")
            .gte("due_date", today.isoformat())
            .lte("due_date", max_window.isoformat())
        )
        response = await execute_async(query, op_name="regulatory.deadline_reminders")
        deadlines = response.data or []

        reminders_sent = 0
        for dl in deadlines:
            due = date.fromisoformat(dl["due_date"])
            reminder_days = dl.get("reminder_days_before", 14)
            days_until = (due - today).days

            # Only dispatch if within the reminder window
            if days_until > reminder_days:
                continue

            alert_key = f"{dl['id']}_{dl['due_date']}"
            category = dl.get("category", "custom")

            try:
                await dispatch_proactive_alert(
                    user_id=user_id,
                    alert_type="compliance_deadline_reminder",
                    alert_key=alert_key,
                    title=f"Compliance Deadline: {dl['title']}",
                    message=(
                        f"{dl['title']} is due in {days_until} days "
                        f"({dl['due_date']}). Category: {category}."
                    ),
                )
                reminders_sent += 1
            except Exception:
                logger.exception(
                    "Failed to dispatch reminder for deadline %s", dl["id"]
                )

        return {
            "reminders_sent": reminders_sent,
            "deadlines_checked": len(
                [
                    dl
                    for dl in deadlines
                    if (date.fromisoformat(dl["due_date"]) - today).days
                    <= dl.get("reminder_days_before", 14)
                ]
            ),
        }

    # ------------------------------------------------------------------
    # Relevance scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _score_relevance(
        title: str, content: str, industry: str, jurisdiction: str
    ) -> str:
        """Score relevance of a search result based on keyword matching.

        Args:
            title: Result title.
            content: Result content/snippet.
            industry: Target industry.
            jurisdiction: Target jurisdiction.

        Returns:
            One of 'high', 'medium', or 'low'.
        """
        text = f"{title} {content}".lower()
        industry_lower = industry.lower()
        jurisdiction_lower = jurisdiction.lower()

        industry_match = industry_lower in text
        jurisdiction_match = jurisdiction_lower in text

        if industry_match and jurisdiction_match:
            return "high"
        if industry_match or jurisdiction_match:
            return "medium"
        return "low"
