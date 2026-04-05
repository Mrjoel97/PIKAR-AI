# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Agent tools for notification management.

Provides thin, agent-callable wrappers around the notification services so
that OperationsAgent can send messages to Slack/Teams and manage notification
routing rules via natural-language chat.

Exported list::

    COMMUNICATION_TOOLS = [
        send_notification_to_channel,
        list_notification_rules,
        configure_notification_rule,
    ]

Pattern matches PM_TASK_TOOLS and AD_PLATFORM_TOOLS — raw function exports, not
FunctionTool wrappers.  ``sanitize_tools`` in the agent module handles wrapping.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _detect_provider(user_id: str) -> list[str]:
    """Return notification provider keys connected for the user.

    Queries ``integration_credentials`` for Slack and Teams credentials.

    Args:
        user_id: Pikar user ID.

    Returns:
        List of connected provider keys (e.g. ``["slack"]``).

    """
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    client = get_service_client()
    result = await execute_async(
        client.table("integration_credentials")
        .select("provider")
        .eq("user_id", user_id)
        .in_("provider", ["slack", "teams"]),
        op_name="communication_tools.detect_provider",
    )
    return [row["provider"] for row in (result.data or [])]


async def _get_teams_webhook(user_id: str) -> str | None:
    """Retrieve the Teams webhook URL from integration_credentials.

    Teams uses ``api_key`` auth — the webhook URL is stored as ``account_name``.

    Args:
        user_id: Pikar user ID.

    Returns:
        Webhook URL string, or ``None`` if not found.

    """
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    client = get_service_client()
    result = await execute_async(
        client.table("integration_credentials")
        .select("account_name")
        .eq("user_id", user_id)
        .eq("provider", "teams")
        .limit(1),
        op_name="communication_tools.get_teams_webhook",
    )
    rows = result.data or []
    return rows[0]["account_name"] if rows else None


async def _get_slack_default_channel(user_id: str) -> str | None:
    """Return the configured briefing channel ID for Slack, or None.

    Args:
        user_id: Pikar user ID.

    Returns:
        Slack channel ID or ``None`` if not configured.

    """
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    client = get_service_client()
    result = await execute_async(
        client.table("notification_channel_config")
        .select("briefing_channel_id")
        .eq("user_id", user_id)
        .eq("provider", "slack")
        .limit(1),
        op_name="communication_tools.get_default_channel",
    )
    rows = result.data or []
    return rows[0].get("briefing_channel_id") if rows else None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def send_notification_to_channel(
    user_id: str,
    message: str,
    channel: str = "",
    provider: str = "",
) -> str:
    """Send a message to a connected Slack or Teams channel.

    Auto-detects the notification provider when not specified.  For Slack,
    falls back to the configured briefing channel when ``channel`` is empty.

    Args:
        user_id: Pikar user ID.
        message: Text to send to the channel.
        channel: Slack channel ID (optional — auto-detects from config).
        provider: Notification provider key ``"slack"`` or ``"teams"``.
            When empty the first connected provider is used; if both are
            connected the user is asked to specify.

    Returns:
        Human-readable success or error message.

    """
    resolved_provider = provider.lower().strip() if provider else ""

    if not resolved_provider:
        connected = await _detect_provider(user_id)
        if not connected:
            return (
                "No notification provider connected. "
                "Please connect Slack or Teams from the Configuration page."
            )
        if len(connected) > 1:
            return (
                f"Multiple providers connected: {', '.join(connected)}. "
                "Please specify provider='slack' or provider='teams'."
            )
        resolved_provider = connected[0]

    try:
        if resolved_provider == "slack":
            from app.services.slack_notification_service import (
                SlackNotificationService,
            )

            channel_id = (
                channel.strip() or await _get_slack_default_channel(user_id) or ""
            )
            if not channel_id:
                return (
                    "No Slack channel specified and no default briefing channel"
                    " configured. Please specify a channel or set one up in"
                    " Configuration."
                )
            ok = await SlackNotificationService().send_notification(
                user_id,
                channel_id,
                "agent.message",
                {"text": message, "message": message},
            )
        elif resolved_provider == "teams":
            from app.services.teams_notification_service import (
                TeamsNotificationService,
            )

            webhook_url = await _get_teams_webhook(user_id)
            if not webhook_url:
                return (
                    "Teams webhook URL not found. "
                    "Please reconnect Teams from the Configuration page."
                )
            ok = await TeamsNotificationService().send_notification(
                user_id,
                webhook_url,
                "agent.message",
                {"text": message, "message": message},
            )
        else:
            return f"Unknown provider '{resolved_provider}'. Use 'slack' or 'teams'."

        if ok:
            return f"Message sent successfully via {resolved_provider}."
        return (
            f"Failed to deliver message via {resolved_provider}."
            " Check your connection settings."
        )

    except Exception:
        logger.exception(
            "send_notification_to_channel failed user=%s provider=%s",
            user_id,
            resolved_provider,
        )
        return f"Error sending message via {resolved_provider}. Please try again."


async def list_notification_rules(user_id: str) -> str:
    """List all notification rules configured for the user.

    Args:
        user_id: Pikar user ID.

    Returns:
        Human-readable list of rules showing event type, channel, provider,
        and enabled status.  Returns a brief message if no rules are found.

    """
    from app.services.notification_rule_service import NotificationRuleService

    rules = await NotificationRuleService().list_rules(user_id)
    if not rules:
        return (
            "No notification rules configured yet. "
            "Use 'configure_notification_rule' or visit Configuration to set them up."
        )

    lines: list[str] = ["Notification rules:"]
    for rule in rules:
        event = rule.get("event_type", "unknown")
        channel = rule.get("channel_name") or rule.get("channel_id", "unknown")
        prov = rule.get("provider", "unknown")
        status = "enabled" if rule.get("enabled", True) else "disabled"
        lines.append(f"  • {event} -> {channel} ({prov}, {status})")

    return "\n".join(lines)


async def configure_notification_rule(
    user_id: str,
    event_type: str,
    channel_name: str,
    provider: str = "",
    enabled: bool = True,
) -> str:
    """Create or update a notification rule routing an event to a channel.

    For Slack, resolves ``channel_name`` to a channel ID via the Slack API.
    For Teams, the webhook URL from credentials is used as the channel.

    Args:
        user_id: Pikar user ID.
        event_type: Dotted event name (e.g. ``"approval.pending"``).
        channel_name: Human-readable channel name.  For Teams, pass any
            descriptive label — the webhook URL is looked up automatically.
        provider: Notification provider key.  Auto-detected when empty.
        enabled: Whether the rule is active (default ``True``).

    Returns:
        Confirmation message or error description.

    """
    resolved_provider = provider.lower().strip() if provider else ""

    if not resolved_provider:
        connected = await _detect_provider(user_id)
        if not connected:
            return (
                "No notification provider connected. "
                "Please connect Slack or Teams from the Configuration page."
            )
        if len(connected) > 1:
            return (
                f"Multiple providers connected: {', '.join(connected)}. "
                "Please specify provider='slack' or provider='teams'."
            )
        resolved_provider = connected[0]

    try:
        channel_id: str = ""

        if resolved_provider == "slack":
            from app.services.slack_notification_service import (
                SlackNotificationService,
            )

            channels = await SlackNotificationService().list_channels(user_id)
            # Case-insensitive name match (strip leading '#')
            clean_name = channel_name.lstrip("#").lower()
            for ch in channels:
                if ch.get("name", "").lower() == clean_name:
                    channel_id = ch["id"]
                    channel_name = ch["name"]
                    break
            if not channel_id:
                available = [ch.get("name", "") for ch in channels[:10]]
                return (
                    f"Slack channel '{channel_name}' not found. "
                    f"Available channels: {', '.join(available)}"
                )

        elif resolved_provider == "teams":
            webhook_url = await _get_teams_webhook(user_id)
            if not webhook_url:
                return (
                    "Teams webhook URL not found. "
                    "Please reconnect Teams from the Configuration page."
                )
            channel_id = webhook_url
            if not channel_name:
                channel_name = "Teams Webhook"

        else:
            return f"Unknown provider '{resolved_provider}'. Use 'slack' or 'teams'."

        from app.services.notification_rule_service import NotificationRuleService

        await NotificationRuleService().create_rule(
            user_id, resolved_provider, event_type, channel_id, channel_name
        )
        return (
            f"Notification rule configured: {event_type} events will be sent to "
            f"'{channel_name}' via {resolved_provider}."
        )

    except Exception:
        logger.exception(
            "configure_notification_rule failed user=%s provider=%s event=%s",
            user_id,
            resolved_provider,
            event_type,
        )
        return "Error configuring notification rule. Please try again."


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

COMMUNICATION_TOOLS = [
    send_notification_to_channel,
    list_notification_rules,
    configure_notification_rule,
]
