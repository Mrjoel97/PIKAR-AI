# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Notification rule CRUD service.

Manages ``notification_rules`` and ``notification_channel_config`` rows for
all connected notification providers (Slack, Teams).

Usage::

    svc = NotificationRuleService()
    rules = await svc.list_rules(user_id, provider="slack")
    rule  = await svc.create_rule(user_id, "slack", "approval.pending", "C12345")
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class NotificationRuleService:
    """CRUD service for notification rules and channel configuration.

    Uses the service-role client (AdminService pattern) so that background
    tasks such as the dispatcher can call this service without a user JWT.

    Attributes:
        SUPPORTED_EVENTS: Class-level list of event types that Pikar can route
            through notification rules.  Returned by the ``/notification-events``
            endpoint so frontends can build rule-configuration UIs without
            hard-coding event names.

    """

    SUPPORTED_EVENTS: list[dict[str, str]] = [
        {"type": "approval.pending", "label": "Approval Required"},
        {"type": "task.created", "label": "Task Created"},
        {"type": "task.completed", "label": "Task Completed"},
        {"type": "workflow.completed", "label": "Workflow Completed"},
        {"type": "workflow.failed", "label": "Workflow Failed"},
        {"type": "campaign.milestone", "label": "Campaign Milestone"},
        {"type": "report.ready", "label": "Report Ready"},
        {"type": "monitoring.alert", "label": "Monitoring Alert"},
        {"type": "agent.message", "label": "Agent Message"},
    ]

    def __init__(self) -> None:
        """Initialise the service with a service-role Supabase client."""
        self._client = get_service_client()

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    async def list_rules(
        self,
        user_id: str,
        provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """List notification rules for a user, optionally filtered by provider.

        Args:
            user_id: Pikar user ID.
            provider: Optional provider key (``"slack"`` or ``"teams"``).
                When ``None``, returns rules for all providers.

        Returns:
            List of rule dicts ordered by ``created_at`` descending.

        """
        query = (
            self._client.table("notification_rules")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if provider is not None:
            query = query.eq("provider", provider)

        result = await execute_async(
            query,
            op_name="notification_rules.list",
        )
        return result.data or []

    async def create_rule(
        self,
        user_id: str,
        provider: str,
        event_type: str,
        channel_id: str,
        channel_name: str = "",
    ) -> dict[str, Any]:
        """Create or update a notification rule.

        Uses ``upsert`` on the ``(user_id, provider, event_type, channel_id)``
        unique constraint, so calling this method twice with the same args is
        idempotent.

        Args:
            user_id: Pikar user ID.
            provider: Notification provider key (``"slack"`` or ``"teams"``).
            event_type: Dotted event name (e.g. ``"approval.pending"``).
            channel_id: Slack channel ID or Teams webhook URL.
            channel_name: Human-readable label for the channel (optional).

        Returns:
            The upserted rule row dict.

        """
        row = {
            "user_id": user_id,
            "provider": provider,
            "event_type": event_type,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "enabled": True,
        }
        result = await execute_async(
            self._client.table("notification_rules").upsert(
                row,
                on_conflict="user_id,provider,event_type,channel_id",
            ),
            op_name="notification_rules.create",
        )
        rows: list[dict[str, Any]] = result.data or []
        return rows[0] if rows else row

    async def update_rule(
        self,
        user_id: str,
        rule_id: str,
        enabled: bool,
    ) -> dict[str, Any]:
        """Toggle the ``enabled`` flag on a notification rule.

        Args:
            user_id: Pikar user ID (used as ownership guard).
            rule_id: UUID of the rule to update.
            enabled: New value for the ``enabled`` flag.

        Returns:
            The updated rule row dict.

        """
        result = await execute_async(
            self._client.table("notification_rules")
            .update({"enabled": enabled})
            .eq("id", rule_id)
            .eq("user_id", user_id),
            op_name="notification_rules.update",
        )
        rows: list[dict[str, Any]] = result.data or []
        return rows[0] if rows else {}

    async def delete_rule(
        self,
        user_id: str,
        rule_id: str,
    ) -> bool:
        """Delete a notification rule.

        Args:
            user_id: Pikar user ID (used as ownership guard).
            rule_id: UUID of the rule to delete.

        Returns:
            ``True`` if the row was found and deleted.

        """
        result = await execute_async(
            self._client.table("notification_rules")
            .delete()
            .eq("id", rule_id)
            .eq("user_id", user_id),
            op_name="notification_rules.delete",
        )
        return bool(result.data)

    async def get_matching_rules(
        self,
        user_id: str,
        event_type: str,
    ) -> list[dict[str, Any]]:
        """Return all enabled rules that match a given user ID and event type.

        Args:
            user_id: Pikar user ID.
            event_type: Dotted event name (e.g. ``"task.created"``).

        Returns:
            List of matching enabled rule dicts.

        """
        result = await execute_async(
            self._client.table("notification_rules")
            .select("*")
            .eq("user_id", user_id)
            .eq("event_type", event_type)
            .eq("enabled", True),
            op_name="notification_rules.get_matching",
        )
        return result.data or []

    # ------------------------------------------------------------------
    # Channel config
    # ------------------------------------------------------------------

    async def get_channel_config(
        self,
        user_id: str,
        provider: str,
    ) -> dict[str, Any] | None:
        """Return the channel config row for a provider, or ``None``.

        Args:
            user_id: Pikar user ID.
            provider: Notification provider key.

        Returns:
            Config dict or ``None`` if not yet configured.

        """
        result = await execute_async(
            self._client.table("notification_channel_config")
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .limit(1),
            op_name="notification_channel_config.get",
        )
        rows: list[dict[str, Any]] = result.data or []
        return rows[0] if rows else None

    async def upsert_channel_config(
        self,
        user_id: str,
        provider: str,
        daily_briefing: bool,
        briefing_channel_id: str | None,
        briefing_channel_name: str = "",
        briefing_time_utc: str = "08:00",
    ) -> dict[str, Any]:
        """Upsert the channel configuration for a notification provider.

        Args:
            user_id: Pikar user ID.
            provider: Notification provider key (``"slack"`` or ``"teams"``).
            daily_briefing: Whether to enable daily briefing messages.
            briefing_channel_id: Slack channel ID / Teams URL to send briefings to.
            briefing_channel_name: Human-readable label for the briefing channel.
            briefing_time_utc: ``HH:MM`` time string for the daily briefing (UTC).

        Returns:
            The upserted config row dict.

        """
        row = {
            "user_id": user_id,
            "provider": provider,
            "daily_briefing": daily_briefing,
            "briefing_channel_id": briefing_channel_id,
            "briefing_channel_name": briefing_channel_name,
            "briefing_time_utc": briefing_time_utc,
        }
        result = await execute_async(
            self._client.table("notification_channel_config").upsert(
                row,
                on_conflict="user_id,provider",
            ),
            op_name="notification_channel_config.upsert",
        )
        rows: list[dict[str, Any]] = result.data or []
        return rows[0] if rows else row
