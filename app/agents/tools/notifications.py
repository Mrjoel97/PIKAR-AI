# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Notification Tools for Agents.

Allow agents to send notifications to users via the Supabase NotificationService.
All tools are async because ADK runs inside an async event loop.
"""

from app.notifications.notification_service import (
    NotificationType,
    get_notification_service,
)


async def send_notification(
    user_id: str, title: str, message: str, type: str = "info", link: str | None = None
) -> dict:
    """Send a notification to the user.

    Use this when you need to alert the user about important events,
    task completions, or required actions.

    Args:
        user_id: The ID of the user to notify.
        title: Short title for the notification.
        message: The full message content.
        type: One of 'info', 'success', 'warning', 'error', 'task_update'.
        link: Optional URL to redirect the user to.

    Returns:
        Status dictionary.
    """
    service = get_notification_service()

    # Map string type to Enum
    try:
        notif_type = NotificationType(type)
    except ValueError:
        notif_type = NotificationType.INFO

    result = await service.create_notification(
        user_id=user_id, title=title, message=message, type=notif_type, link=link
    )

    if result:
        return {"success": True, "notification_id": result["id"]}
    else:
        return {"success": False, "error": "Failed to create notification"}


# Export tools
NOTIFICATION_TOOLS = [send_notification]
