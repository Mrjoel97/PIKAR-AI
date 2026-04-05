# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Teams notification service.

Sends Adaptive Card messages to Microsoft Teams channels via incoming webhook
URLs.  Supports generic event notifications and daily briefings.

Teams incoming webhooks do not support interactive responses, so approval
events include an ``Action.OpenUrl`` button pointing to the Pikar approval
page rather than an in-Teams response form.

Usage::

    svc = TeamsNotificationService()
    ok = await svc.send_notification(user_id, webhook_url, "task.created", {...})
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ADAPTIVE_CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
_ADAPTIVE_CARD_VERSION = "1.2"
_APP_URL = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
_REQUEST_TIMEOUT = 10.0

_EVENT_TYPE_TITLES: dict[str, str] = {
    "approval.pending": "Approval Required",
    "task.created": "Task Created",
    "task.completed": "Task Completed",
    "workflow.completed": "Workflow Completed",
    "workflow.failed": "Workflow Failed",
    "campaign.milestone": "Campaign Milestone",
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TeamsNotificationService:
    """Teams notification service using Adaptive Cards over incoming webhooks.

    Teams incoming webhooks do not require OAuth — the webhook URL is stored
    as the ``account_name`` field in the ``integration_credentials`` table.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        user_id: str,
        webhook_url: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Post an Adaptive Card notification to a Teams channel.

        Args:
            user_id: Pikar user ID (used for logging only in this service).
            webhook_url: Teams incoming webhook URL.
            event_type: Dotted event name (e.g. ``"task.created"``).
            payload: Event-specific data dict for building the card body.

        Returns:
            ``True`` if the webhook returned 200, ``False`` otherwise.

        """
        card = self._build_adaptive_card(event_type, payload)
        return await self._post_card(webhook_url, card, user_id=user_id)

    async def send_daily_briefing(
        self,
        user_id: str,
        webhook_url: str,
        briefing_data: dict[str, Any],
    ) -> bool:
        """Post a daily briefing Adaptive Card to a Teams channel.

        Args:
            user_id: Pikar user ID (used for logging only).
            webhook_url: Teams incoming webhook URL.
            briefing_data: Dict with ``pending_approvals``, ``upcoming_tasks``,
                and ``key_metrics`` keys.

        Returns:
            ``True`` if the webhook returned 200, ``False`` otherwise.

        """
        card = self._build_briefing_card(briefing_data)
        return await self._post_card(webhook_url, card, user_id=user_id)

    # ------------------------------------------------------------------
    # Card builders
    # ------------------------------------------------------------------

    def _build_adaptive_card(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an Adaptive Card body for a generic event.

        Uses schema version 1.2.  For ``approval.pending`` events, appends an
        ``Action.OpenUrl`` button linking to the Pikar approval page (incoming
        webhooks cannot handle ``Action.Submit`` responses).

        Args:
            event_type: Dotted event name.
            payload: Event data; uses ``title``, ``description``, ``message``,
                and ``approval_token`` keys if present.

        Returns:
            Dict representing the full Adaptive Card body ready for POST.

        """
        title = _EVENT_TYPE_TITLES.get(event_type, event_type.replace(".", " ").title())

        detail_parts: list[str] = []
        if payload.get("title"):
            detail_parts.append(payload["title"])
        if payload.get("description"):
            detail_parts.append(payload["description"])
        if payload.get("message"):
            detail_parts.append(payload["message"])
        detail_text = " ".join(detail_parts) if detail_parts else title

        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": title,
                "size": "Medium",
                "weight": "Bolder",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": detail_text,
                "wrap": True,
            },
        ]

        actions: list[dict[str, Any]] = []
        if event_type == "approval.pending":
            approval_token = payload.get("approval_token", "")
            approval_url = f"{_APP_URL}/approval/{approval_token}"
            actions.append(
                {
                    "type": "Action.OpenUrl",
                    "title": "View in Pikar",
                    "url": approval_url,
                }
            )

        card: dict[str, Any] = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": _ADAPTIVE_CARD_SCHEMA,
                        "type": "AdaptiveCard",
                        "version": _ADAPTIVE_CARD_VERSION,
                        "body": body,
                    },
                }
            ],
        }

        if actions:
            card["attachments"][0]["content"]["actions"] = actions

        return card

    def _build_briefing_card(
        self,
        briefing_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an Adaptive Card for the daily briefing.

        Uses a ColumnSet for the metrics section for a two-column layout.

        Args:
            briefing_data: Dict with optional keys:
                - ``pending_approvals`` (int): Count of pending approvals.
                - ``upcoming_tasks`` (list[str]): Task title strings.
                - ``key_metrics`` (dict): Metric name -> value mapping.

        Returns:
            Dict representing the full Adaptive Card body ready for POST.

        """
        pending = briefing_data.get("pending_approvals", 0)
        tasks: list[str] = briefing_data.get("upcoming_tasks", [])
        metrics: dict[str, Any] = briefing_data.get("key_metrics", {})

        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": "Daily Briefing",
                "size": "Medium",
                "weight": "Bolder",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": f"Pending Approvals: {pending}",
                "wrap": True,
            },
        ]

        # Upcoming tasks as a bulleted text block
        if tasks:
            task_text = "\n".join(f"- {t}" for t in tasks[:10])
        else:
            task_text = "No upcoming tasks"
        body.append(
            {
                "type": "TextBlock",
                "text": f"Upcoming Tasks:\n{task_text}",
                "wrap": True,
            }
        )

        # Key metrics as ColumnSet (two columns: name | value)
        if metrics:
            columns: list[dict[str, Any]] = [
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "\n".join(str(k) for k in metrics),
                            "wrap": True,
                            "weight": "Bolder",
                        }
                    ],
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "\n".join(str(v) for v in metrics.values()),
                            "wrap": True,
                        }
                    ],
                },
            ]
            body.append(
                {
                    "type": "ColumnSet",
                    "columns": columns,
                }
            )

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": _ADAPTIVE_CARD_SCHEMA,
                        "type": "AdaptiveCard",
                        "version": _ADAPTIVE_CARD_VERSION,
                        "body": body,
                    },
                }
            ],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _post_card(
        self,
        webhook_url: str,
        card: dict[str, Any],
        *,
        user_id: str = "",
    ) -> bool:
        """POST an Adaptive Card payload to a Teams webhook URL.

        Handles HTTP 429 (rate limit) with a logged warning without raising.

        Args:
            webhook_url: Teams incoming webhook URL.
            card: Adaptive Card body dict.
            user_id: Pikar user ID for log context.

        Returns:
            ``True`` if the response status is 200, ``False`` otherwise.

        """
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as http:
                response = await http.post(webhook_url, json=card)

            if response.status_code == 429:
                logger.warning(
                    "Teams webhook rate-limited (429) user=%s url=%s",
                    user_id,
                    webhook_url,
                )
                return False

            if response.status_code != 200:
                logger.error(
                    "Teams webhook returned %d user=%s body=%s",
                    response.status_code,
                    user_id,
                    response.text[:500],
                )
                return False

            logger.info(
                "Teams webhook delivered user=%s url=%.40s...",
                user_id,
                webhook_url,
            )
            return True
        except Exception:
            logger.exception(
                "Failed to POST Teams webhook user=%s",
                user_id,
            )
            return False
