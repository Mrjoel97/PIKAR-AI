# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Decision Journal Service -- log and query past business decisions.

Provides a persistent record of significant business decisions with topic,
rationale, outcome tracking, and text search. Decisions are scoped per user
and ordered by recency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase_async import execute_async
from app.services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

# Module-level singleton
_service_instance: DecisionJournalService | None = None


class DecisionJournalService:
    """Central service for logging and querying business decisions.

    Singleton -- use :func:`get_decision_journal_service` to obtain the instance.
    """

    def __init__(self) -> None:
        self._client = get_service_client()
        self._table = "decision_journal"

    async def log_decision(
        self,
        user_id: str,
        topic: str,
        decision_text: str,
        *,
        rationale: str | None = None,
        agent_name: str | None = None,
        outcome: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Insert a decision journal entry and return the inserted row.

        Args:
            user_id: The user who made the decision.
            topic: Short topic label (e.g. "Pricing", "Hiring plan").
            decision_text: The actual decision that was made.
            rationale: Why this decision was made.
            agent_name: Which agent facilitated the decision.
            outcome: Expected or recorded outcome.
            tags: Optional list of tags for categorization.
            metadata: Optional JSON metadata.

        Returns:
            The inserted row as a dict, or None on failure.
        """
        try:
            data: dict[str, Any] = {
                "user_id": user_id,
                "topic": topic,
                "decision_text": decision_text,
            }
            if rationale is not None:
                data["rationale"] = rationale
            if agent_name is not None:
                data["agent_name"] = agent_name
            if outcome is not None:
                data["outcome"] = outcome
            if tags is not None:
                data["tags"] = tags
            if metadata is not None:
                data["metadata"] = metadata

            response = await execute_async(
                self._client.table(self._table).insert(data).select("*"),
                op_name="decision_journal.log_decision",
            )
            if response.data:
                return response.data[0]
            return None
        except Exception:
            logger.warning(
                "Failed to log decision topic=%s for user=%s",
                topic,
                user_id,
                exc_info=True,
            )
            return None

    async def query_decisions(
        self,
        user_id: str,
        *,
        topic: str | None = None,
        days: int = 90,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query decisions for a user, optionally filtered by topic keyword.

        Args:
            user_id: Filter to this user's decisions.
            topic: Optional keyword to match against the topic column (ilike).
            days: Look-back period in days (default 90).
            limit: Maximum rows to return (default 10).

        Returns:
            List of decision rows, newest first.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = (
            self._client.table(self._table)
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
        )

        if topic:
            query = query.ilike("topic", f"%{topic}%")

        query = query.order("created_at", desc=True).limit(limit)

        response = await execute_async(
            query,
            op_name="decision_journal.query_decisions",
        )
        return response.data or []

    async def update_outcome(self, decision_id: str, outcome: str) -> bool:
        """Update the outcome field for a decision.

        Args:
            decision_id: The UUID of the decision to update.
            outcome: The new outcome text.

        Returns:
            True if the update succeeded, False otherwise.
        """
        try:
            response = await execute_async(
                self._client.table(self._table)
                .update({
                    "outcome": outcome,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", decision_id),
                op_name="decision_journal.update_outcome",
            )
            return bool(response.data)
        except Exception:
            logger.warning(
                "Failed to update outcome for decision=%s",
                decision_id,
                exc_info=True,
            )
            return False


def get_decision_journal_service() -> DecisionJournalService:
    """Return the singleton DecisionJournalService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DecisionJournalService()
    return _service_instance
