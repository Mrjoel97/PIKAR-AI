# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Slack notification service.

Sends rich Block Kit messages to Slack channels on behalf of a user using
their stored OAuth bot token.  Supports generic event notifications, approval
request buttons, daily briefings, and channel listing.

Usage::

    svc = SlackNotificationService()
    ok = await svc.send_notification(user_id, channel_id, "task.created", {...})
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_APPROVAL_URL_BASE = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

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


class SlackNotificationService:
    """Slack notification service with Block Kit rich formatting.

    Attributes:
        None — all state is resolved lazily per-call via IntegrationManager.

    """

    def __init__(self) -> None:
        """Initialise the service.

        No Slack SDK client is created at init time; the bot token and client
        are resolved lazily inside each async method to avoid blocking import.
        """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        user_id: str,
        channel_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Send a Block Kit notification to a Slack channel.

        Resolves the user's bot token via IntegrationManager, builds Block Kit
        blocks appropriate for ``event_type``, and calls ``chat.postMessage``.
        Returns ``False`` (and logs the error) on any Slack API failure.

        Args:
            user_id: Pikar user ID used to look up the Slack bot token.
            channel_id: Slack channel ID (e.g. ``C0123456789``).
            event_type: Dotted event name (e.g. ``"task.created"``).
            payload: Event-specific data dict for building the message body.

        Returns:
            ``True`` if the message was delivered, ``False`` otherwise.

        """
        token = await self._resolve_token(user_id)
        if not token:
            logger.warning(
                "No Slack token for user %s — cannot send %s notification",
                user_id,
                event_type,
            )
            return False

        try:
            from slack_sdk.web.async_client import (
                AsyncWebClient,  # type: ignore[import]
            )

            client = AsyncWebClient(token=token)
            blocks = self._build_event_blocks(event_type, payload)
            fallback_text = _EVENT_TYPE_TITLES.get(event_type, event_type)

            await client.chat_postMessage(
                channel=channel_id,
                text=fallback_text,
                blocks=blocks,
            )
            logger.info(
                "Sent Slack notification event=%s user=%s channel=%s",
                event_type,
                user_id,
                channel_id,
            )
            return True
        except Exception:
            logger.exception(
                "Failed to send Slack notification event=%s user=%s channel=%s",
                event_type,
                user_id,
                channel_id,
            )
            return False

    async def send_approval_request(
        self,
        user_id: str,
        channel_id: str,
        description: str,
        approval_token: str,
        details: str = "",
    ) -> dict[str, Any]:
        """Send an approval request message with Approve / Reject buttons.

        The button values encode the decision and token so the interactive
        handler can process them without a round-trip to the database to look
        up the token:
        - Approve button: ``value="APPROVED:{token}"`` action_id ``approval_approve``
        - Reject button: ``value="REJECTED:{token}"`` action_id ``approval_reject``

        Args:
            user_id: Pikar user ID for token resolution.
            channel_id: Target Slack channel ID.
            description: Human-readable description of the action requiring approval.
            approval_token: Raw approval token (first 16 chars used as block_id).
            details: Optional extra context displayed below the description.

        Returns:
            The Slack API response dict, or an empty dict on failure.

        """
        token = await self._resolve_token(user_id)
        if not token:
            logger.warning(
                "No Slack token for user %s — cannot send approval request",
                user_id,
            )
            return {}

        try:
            from slack_sdk.web.async_client import (
                AsyncWebClient,  # type: ignore[import]
            )

            client = AsyncWebClient(token=token)
            block_id = f"approval_{approval_token[:16]}"

            blocks: list[dict[str, Any]] = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Approval Required",
                        "emoji": False,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{description}*",
                    },
                },
            ]

            if details:
                blocks.append(
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": details},
                    }
                )

            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "actions",
                    "block_id": block_id,
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Approve",
                                "emoji": False,
                            },
                            "style": "primary",
                            "action_id": "approval_approve",
                            "value": f"APPROVED:{approval_token}",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Reject",
                                "emoji": False,
                            },
                            "style": "danger",
                            "action_id": "approval_reject",
                            "value": f"REJECTED:{approval_token}",
                        },
                    ],
                }
            )

            response = await client.chat_postMessage(
                channel=channel_id,
                text="Approval Required",
                blocks=blocks,
            )
            logger.info(
                "Sent Slack approval request user=%s channel=%s",
                user_id,
                channel_id,
            )
            return dict(response.data) if response.data else {}
        except Exception:
            logger.exception(
                "Failed to send Slack approval request user=%s channel=%s",
                user_id,
                channel_id,
            )
            return {}

    async def send_daily_briefing(
        self,
        user_id: str,
        channel_id: str,
        briefing_data: dict[str, Any],
    ) -> bool:
        """Send a daily briefing as a structured Block Kit message.

        The briefing covers pending approvals, upcoming tasks, and key metrics.

        Args:
            user_id: Pikar user ID for token resolution.
            channel_id: Target Slack channel ID.
            briefing_data: Dict with keys ``pending_approvals``, ``upcoming_tasks``,
                and ``key_metrics``.

        Returns:
            ``True`` if delivered, ``False`` on failure.

        """
        token = await self._resolve_token(user_id)
        if not token:
            logger.warning(
                "No Slack token for user %s — cannot send daily briefing",
                user_id,
            )
            return False

        try:
            from slack_sdk.web.async_client import (
                AsyncWebClient,  # type: ignore[import]
            )

            client = AsyncWebClient(token=token)
            blocks = self._build_briefing_blocks(briefing_data)

            await client.chat_postMessage(
                channel=channel_id,
                text="Daily Briefing",
                blocks=blocks,
            )
            logger.info(
                "Sent Slack daily briefing user=%s channel=%s",
                user_id,
                channel_id,
            )
            return True
        except Exception:
            logger.exception(
                "Failed to send Slack daily briefing user=%s channel=%s",
                user_id,
                channel_id,
            )
            return False

    async def list_channels(self, user_id: str) -> list[dict[str, Any]]:
        """List Slack channels accessible by the bot token.

        Args:
            user_id: Pikar user ID for token resolution.

        Returns:
            List of dicts with ``id``, ``name``, and ``is_private`` keys.
            Returns an empty list if the token is missing or the call fails.

        """
        token = await self._resolve_token(user_id)
        if not token:
            logger.warning(
                "No Slack token for user %s — cannot list channels",
                user_id,
            )
            return []

        try:
            from slack_sdk.web.async_client import (
                AsyncWebClient,  # type: ignore[import]
            )

            client = AsyncWebClient(token=token)
            response = await client.conversations_list(
                exclude_archived=True,
                types="public_channel,private_channel",
                limit=200,
            )
            channels = response.get("channels", [])
            return [
                {
                    "id": ch["id"],
                    "name": ch["name"],
                    "is_private": ch.get("is_private", False),
                }
                for ch in channels
            ]
        except Exception:
            logger.exception(
                "Failed to list Slack channels user=%s",
                user_id,
            )
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_token(self, user_id: str) -> str | None:
        """Resolve the Slack bot token via IntegrationManager.

        Args:
            user_id: Pikar user ID.

        Returns:
            Decrypted bot token, or ``None`` if not connected.

        """
        from app.services.integration_manager import IntegrationManager

        return await IntegrationManager().get_valid_token(user_id, "slack")

    def _build_event_blocks(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build Block Kit blocks for a generic event notification.

        Produces a header block with the event title, a section block with
        mrkdwn details extracted from ``payload``, and a trailing divider.

        Args:
            event_type: Dotted event name (e.g. ``"task.created"``).
            payload: Event data; uses ``title``, ``description``, and
                ``message`` keys if present.

        Returns:
            List of Block Kit block dicts.

        """
        title = _EVENT_TYPE_TITLES.get(event_type, event_type.replace(".", " ").title())

        detail_parts: list[str] = []
        if payload.get("title"):
            detail_parts.append(f"*{payload['title']}*")
        if payload.get("description"):
            detail_parts.append(payload["description"])
        if payload.get("message"):
            detail_parts.append(payload["message"])
        detail_text = "\n".join(detail_parts) if detail_parts else title

        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title, "emoji": False},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": detail_text},
            },
            {"type": "divider"},
        ]

    def _build_briefing_blocks(
        self,
        briefing_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build Block Kit blocks for the daily briefing message.

        Sections cover pending approvals, upcoming tasks, and key metrics.
        Each section is separated by a divider for readability.

        Args:
            briefing_data: Dict with optional keys:
                - ``pending_approvals`` (int): Number of pending approvals.
                - ``upcoming_tasks`` (list[str]): Task title strings.
                - ``key_metrics`` (dict): Metric name -> value mapping.

        Returns:
            List of Block Kit block dicts.

        """
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Daily Briefing",
                    "emoji": False,
                },
            },
            {"type": "divider"},
        ]

        # Pending approvals
        pending = briefing_data.get("pending_approvals", 0)
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Pending Approvals:* {pending}",
                },
            }
        )
        blocks.append({"type": "divider"})

        # Upcoming tasks
        tasks: list[str] = briefing_data.get("upcoming_tasks", [])
        if tasks:
            task_lines = "\n".join(f"• {t}" for t in tasks[:10])
        else:
            task_lines = "_No upcoming tasks_"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Upcoming Tasks:*\n{task_lines}",
                },
            }
        )
        blocks.append({"type": "divider"})

        # Key metrics
        metrics: dict[str, Any] = briefing_data.get("key_metrics", {})
        if metrics:
            metric_lines = "\n".join(f"• *{k}:* {v}" for k, v in metrics.items())
        else:
            metric_lines = "_No metrics available_"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Metrics:*\n{metric_lines}",
                },
            }
        )

        return blocks
