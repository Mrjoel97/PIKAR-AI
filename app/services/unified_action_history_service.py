# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unified Action History Service -- cross-agent action logging and querying.

Provides a single chronological feed of every AI-performed action across all
agents. Actions are logged fire-and-forget (failures never propagate to callers)
and can be queried with filtering by agent, action type, date range, and
pagination.

Standard action_type values:
    - campaign_created
    - report_generated
    - lead_scored
    - workflow_started
    - content_drafted
    - analysis_completed
    - email_sent
    - initiative_updated
    - research_completed
    - decision_logged
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Module-level singleton
_service_instance: UnifiedActionHistoryService | None = None


class UnifiedActionHistoryService:
    """Central service for logging and querying cross-agent actions.

    Singleton -- use :func:`get_action_history_service` to obtain the instance.
    """

    def __init__(self) -> None:
        self._client = get_service_client()
        self._table = "unified_action_history"

    async def log_agent_action(
        self,
        user_id: str,
        agent_name: str,
        action_type: str,
        description: str,
        *,
        metadata: dict[str, Any] | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
    ) -> None:
        """Log a single agent action to the unified history.

        This is fire-and-forget: all exceptions are caught and logged as
        warnings so callers are never affected by logging failures.

        Args:
            user_id: The user who owns this action.
            agent_name: Which agent performed the action (e.g. "marketing").
            action_type: Standardized action type (e.g. "campaign_created").
            description: Human-readable description of the action.
            metadata: Optional JSON metadata for the action.
            source_id: Optional link to a source record (workflow ID, etc.).
            source_type: Optional source type ('interaction', 'workflow', etc.).
        """
        try:
            data: dict[str, Any] = {
                "user_id": user_id,
                "agent_name": agent_name,
                "action_type": action_type,
                "description": description,
                "metadata": metadata or {},
            }
            if source_id is not None:
                data["source_id"] = source_id
            if source_type is not None:
                data["source_type"] = source_type

            await execute_async(
                self._client.table(self._table).insert(data),
                op_name="action_history.log_action",
            )
        except Exception:
            logger.warning(
                "Failed to log action for agent=%s type=%s",
                agent_name,
                action_type,
                exc_info=True,
            )

    async def get_action_history(
        self,
        user_id: str,
        *,
        agent_name: str | None = None,
        action_type: str | None = None,
        days: int = 30,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query the unified action history for a user.

        Returns actions in reverse chronological order (newest first).

        Args:
            user_id: Filter to this user's actions.
            agent_name: Optional filter by agent name.
            action_type: Optional filter by action type.
            days: Look-back period in days (default 30).
            limit: Maximum rows to return (default 50).
            offset: Pagination offset (default 0).

        Returns:
            List of action history rows, newest first.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = (
            self._client.table(self._table)
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
        )

        if agent_name:
            query = query.eq("agent_name", agent_name)
        if action_type:
            query = query.eq("action_type", action_type)

        query = query.order("created_at", desc=True).limit(limit).offset(offset)

        response = await execute_async(
            query,
            op_name="action_history.get_history",
        )
        return response.data or []


def get_action_history_service() -> UnifiedActionHistoryService:
    """Return the singleton UnifiedActionHistoryService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = UnifiedActionHistoryService()
    return _service_instance


async def log_agent_action(
    user_id: str,
    agent_name: str,
    action_type: str,
    description: str,
    *,
    metadata: dict[str, Any] | None = None,
    source_id: str | None = None,
    source_type: str | None = None,
) -> None:
    """Module-level convenience function for logging agent actions.

    Delegates to the singleton :class:`UnifiedActionHistoryService`. This is
    the primary API for other services and tools to call.

    Args:
        user_id: The user who owns this action.
        agent_name: Which agent performed the action.
        action_type: Standardized action type.
        description: Human-readable description.
        metadata: Optional JSON metadata.
        source_id: Optional link to a source record.
        source_type: Optional source type.
    """
    svc = get_action_history_service()
    await svc.log_agent_action(
        user_id=user_id,
        agent_name=agent_name,
        action_type=action_type,
        description=description,
        metadata=metadata,
        source_id=source_id,
        source_type=source_type,
    )
