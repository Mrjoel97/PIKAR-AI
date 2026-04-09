# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Proactive Alert Service.

Centralized dispatcher for proactive alerts (daily briefings, anomaly alerts,
stalled-initiative nudges, etc.).  Creates an in-app notification via
``NotificationService`` **and** fans out to external channels (Slack, Teams,
email) via ``dispatch_notification``.

Deduplication is handled by the ``proactive_alert_log`` table with a unique
constraint on ``(user_id, alert_type, alert_key)`` -- if an identical row
already exists, the dispatch is skipped.

Usage::

    from app.services.proactive_alert_service import dispatch_proactive_alert

    result = await dispatch_proactive_alert(
        user_id=uid,
        alert_type="daily_briefing",
        alert_key="2026-04-09",
        title="Good morning!",
        message="Here is your daily snapshot.",
    )
"""

from __future__ import annotations

import logging
from typing import Any

from app.notifications.notification_service import (
    NotificationService,
    NotificationType,
)
from app.services.notification_dispatcher import dispatch_notification
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class ProactiveAlertService:
    """Dispatches proactive alerts with deduplication and multi-channel fan-out.

    Uses a service-role Supabase client (bypasses RLS) so it can query and
    insert into ``proactive_alert_log`` across all users.
    """

    def __init__(self) -> None:
        """Initialize the service with a service-role client."""
        self._client = get_service_client()

    async def dispatch_proactive_alert(
        self,
        user_id: str,
        alert_type: str,
        alert_key: str,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        link: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dispatch a proactive alert to a user.

        1. Check ``proactive_alert_log`` for an existing entry with the same
           ``(user_id, alert_type, alert_key)`` -- if found, skip (dedup).
        2. Create an in-app notification via ``NotificationService``.
        3. Fan out to external channels via ``dispatch_notification``.
        4. Insert a row into ``proactive_alert_log`` for audit/dedup.

        Args:
            user_id: Target user ID.
            alert_type: Category of the alert (e.g. ``"daily_briefing"``,
                ``"anomaly_alert"``).
            alert_key: Unique key within the type for dedup (e.g. today's
                ISO date ``"2026-04-09"``).
            title: Short notification title.
            message: Full notification message body.
            notification_type: In-app notification severity.
            link: Optional deep-link URL for the in-app notification.
            metadata: Optional extra data attached to the notification.

        Returns:
            Dict with ``dispatched`` (bool) and ``channels`` (dict of
            provider -> bool) keys.

        """
        # --- 1. Dedup check ---
        dedup_result = await execute_async(
            self._client.table("proactive_alert_log")
            .select("id")
            .eq("user_id", user_id)
            .eq("alert_type", alert_type)
            .eq("alert_key", alert_key),
            op_name="proactive_alert.dedup_check",
        )

        if dedup_result.data:
            logger.debug(
                "Proactive alert dedup hit: user=%s type=%s key=%s",
                user_id,
                alert_type,
                alert_key,
            )
            return {"dispatched": False, "channels": {}, "reason": "duplicate"}

        # --- 2. In-app notification ---
        try:
            notif_svc = NotificationService()
            await notif_svc.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                link=link,
                metadata=metadata or {},
            )
        except Exception:
            logger.exception(
                "Failed to create in-app notification for user=%s alert_type=%s",
                user_id,
                alert_type,
            )

        # --- 3. External channel fan-out ---
        channels: dict[str, bool] = {}
        try:
            channels = await dispatch_notification(
                user_id=user_id,
                event_type=alert_type,
                payload={
                    "title": title,
                    "message": message,
                    "alert_key": alert_key,
                    **(metadata or {}),
                },
            )
        except Exception:
            logger.exception(
                "Failed to dispatch external notification for user=%s alert_type=%s",
                user_id,
                alert_type,
            )

        # --- 4. Log to proactive_alert_log ---
        try:
            await execute_async(
                self._client.table("proactive_alert_log").insert(
                    {
                        "user_id": user_id,
                        "alert_type": alert_type,
                        "alert_key": alert_key,
                        "payload": metadata or {},
                        "dispatched_channels": channels,
                    }
                ),
                op_name="proactive_alert.insert_log",
            )
        except Exception:
            logger.exception(
                "Failed to insert proactive_alert_log for user=%s alert_type=%s",
                user_id,
                alert_type,
            )

        logger.info(
            "Proactive alert dispatched: user=%s type=%s key=%s channels=%s",
            user_id,
            alert_type,
            alert_key,
            channels,
        )
        return {"dispatched": True, "channels": channels}


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


async def dispatch_proactive_alert(
    user_id: str,
    alert_type: str,
    alert_key: str,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    link: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper around ``ProactiveAlertService.dispatch_proactive_alert``.

    Args:
        user_id: Target user ID.
        alert_type: Category of the alert.
        alert_key: Unique dedup key within the type.
        title: Short notification title.
        message: Full notification message body.
        notification_type: In-app notification severity.
        link: Optional deep-link URL.
        metadata: Optional extra data.

    Returns:
        Dict with ``dispatched`` and ``channels`` keys.

    """
    svc = ProactiveAlertService()
    return await svc.dispatch_proactive_alert(
        user_id=user_id,
        alert_type=alert_type,
        alert_key=alert_key,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        metadata=metadata,
    )
