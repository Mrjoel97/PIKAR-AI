# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Notification dispatcher.

Fans out Pikar events to all connected notification providers (Slack, Teams)
by querying the ``notification_rules`` table for matching enabled rules.

Redis deduplication (60-second TTL) prevents duplicate deliveries caused by
rapid-fire event triggers for the same user / event / payload combination.

Usage::

    result = await dispatch_notification(user_id, "task.created", {...})
    # {"slack": True, "teams": False}
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.services.cache import get_cache_service
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEDUP_TTL_SECONDS = 60
"""TTL for the Redis dedup key — events within this window are deduplicated."""


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class NotificationDispatcher:
    """Fan-out dispatcher routing events to all provider services.

    Queries ``notification_rules`` for enabled rules matching the given
    ``user_id`` and ``event_type``, then calls the appropriate provider
    service for each matching rule.  Individual provider failures are caught
    and logged without aborting the rest of the fan-out.
    """

    async def dispatch(
        self,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, bool]:
        """Fan out an event to all matching notification rules.

        Performs Redis-based deduplication before querying the database.  Uses
        a 60-second TTL keyed on ``(user_id, event_type, payload_hash)`` to
        prevent duplicate deliveries when the same event fires multiple times
        in quick succession.

        Args:
            user_id: Pikar user ID whose notification rules are queried.
            event_type: Dotted event name (e.g. ``"task.created"``).
            payload: Event-specific data dict forwarded to provider services.

        Returns:
            Dict mapping provider name to delivery success flag, e.g.
            ``{"slack": True, "teams": False}``.

        """
        # Deduplication check
        dedup_key = self._dedup_key(user_id, event_type, payload)
        cache = get_cache_service()
        cached = await cache.get_generic(dedup_key)
        if cached.hit:
            logger.debug(
                "Skipping duplicate notification user=%s event=%s",
                user_id,
                event_type,
            )
            return {}

        # Fetch matching enabled rules
        client = get_service_client()
        result = await execute_async(
            client.table("notification_rules")
            .select("*")
            .eq("user_id", user_id)
            .eq("event_type", event_type)
            .eq("enabled", True),
            op_name="notification.dispatcher.fetch_rules",
        )
        rules: list[dict[str, Any]] = result.data or []

        if not rules:
            logger.debug(
                "No notification rules for user=%s event=%s",
                user_id,
                event_type,
            )
            return {}

        # Mark dedup key before delivery attempts
        await cache.set_generic(dedup_key, True, ttl=_DEDUP_TTL_SECONDS)

        # Fan out to each provider
        results: dict[str, bool] = {}
        for rule in rules:
            provider = rule.get("provider", "")
            channel_id = rule.get("channel_id", "")
            try:
                if provider == "slack":
                    ok = await self._deliver_slack(
                        user_id, channel_id, event_type, payload
                    )
                elif provider == "teams":
                    ok = await self._deliver_teams(
                        user_id, channel_id, event_type, payload
                    )
                else:
                    logger.warning(
                        "Unknown provider '%s' in notification rule %s",
                        provider,
                        rule.get("id"),
                    )
                    ok = False

                # Last-write-wins: True beats False for same provider
                if provider not in results or ok:
                    results[provider] = ok
            except Exception:
                logger.exception(
                    "Unhandled error dispatching to provider=%s rule=%s",
                    provider,
                    rule.get("id"),
                )
                if provider not in results:
                    results[provider] = False

        logger.info(
            "Dispatched notification user=%s event=%s results=%s",
            user_id,
            event_type,
            results,
        )
        return results

    # ------------------------------------------------------------------
    # Provider delivery helpers (lazy imports to avoid circular deps)
    # ------------------------------------------------------------------

    async def _deliver_slack(
        self,
        user_id: str,
        channel_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Deliver a notification via SlackNotificationService.

        Lazy-imported inside the method to avoid circular import issues.

        Args:
            user_id: Pikar user ID.
            channel_id: Slack channel ID.
            event_type: Dotted event name.
            payload: Event data dict.

        Returns:
            ``True`` if delivered successfully.

        """
        from app.services.slack_notification_service import (
            SlackNotificationService,
        )

        return await SlackNotificationService().send_notification(
            user_id, channel_id, event_type, payload
        )

    async def _deliver_teams(
        self,
        user_id: str,
        webhook_url: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Deliver a notification via TeamsNotificationService.

        Lazy-imported inside the method to avoid circular import issues.

        Args:
            user_id: Pikar user ID.
            webhook_url: Teams incoming webhook URL (stored as channel_id in rules).
            event_type: Dotted event name.
            payload: Event data dict.

        Returns:
            ``True`` if delivered successfully.

        """
        from app.services.teams_notification_service import (
            TeamsNotificationService,
        )

        return await TeamsNotificationService().send_notification(
            user_id, webhook_url, event_type, payload
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup_key(
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Build the Redis deduplication key for an event.

        Args:
            user_id: Pikar user ID.
            event_type: Dotted event name.
            payload: Event payload dict.

        Returns:
            Redis key string following the ``pikar:notif:sent:`` namespace.

        """
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        return f"pikar:notif:sent:{user_id}:{event_type}:{payload_hash}"


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


async def dispatch_notification(
    user_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, bool]:
    """Dispatch an event to all matching providers via ``NotificationDispatcher``.

    Args:
        user_id: Pikar user ID.
        event_type: Dotted event name (e.g. ``"approval.pending"``).
        payload: Event-specific data dict.

    Returns:
        Dict mapping provider name to delivery success flag.

    """
    return await NotificationDispatcher().dispatch(user_id, event_type, payload)
