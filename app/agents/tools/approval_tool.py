# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Approval tool.

Generates human approval requests with Magic Links and dispatches
``approval.pending`` notifications to connected Slack / Teams channels.
"""

import asyncio
import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


async def _notify_approval(
    user_id: str,
    action_type: str,
    description: str,
    token: str,
) -> None:
    """Dispatch an approval.pending notification to all connected channels.

    Called as a fire-and-forget ``asyncio.create_task`` so it never
    blocks or breaks the approval creation flow.

    Args:
        user_id: Pikar user ID who owns the approval request.
        action_type: Short action type identifier (e.g. ``"POST_TWEET"``).
        description: Human-readable action description.
        token: Plain (unhashed) approval token used to build button values.

    """
    try:
        from app.services.notification_dispatcher import dispatch_notification

        await dispatch_notification(
            user_id,
            "approval.pending",
            {
                "action_type": action_type,
                "description": description,
                "approval_token": token,
            },
        )
    except Exception:
        logger.warning(
            "Failed to dispatch approval.pending notification for user=%s",
            user_id,
            exc_info=True,
        )


async def request_human_approval(
    action_type: str,
    action_description: str,
    payload: dict[str, Any],
    requires_response_by: str | None = None,
) -> dict[str, Any]:
    """Pause execution and request human approval via a generated Magic Link.

    Creates an ``approval_requests`` row with a hashed token and dispatches
    an ``approval.pending`` notification to any connected notification
    channels (Slack, Teams) so the user can approve from chat.

    Args:
        action_type: Short identifier like ``'POST_TWEET'`` or ``'SEND_EMAIL'``.
        action_description: Human readable text for the user,
            e.g. ``"Post a tweet about the launch"``.
        payload: The exact data to be acted upon.
        requires_response_by: Optional ISO-8601 deadline displayed on the card.

    Returns:
        A widget envelope dict with ``type='approval'``, structured ``data``
        for the frontend ApprovalCard, plus a back-compat ``message`` key
        carrying the legacy magic-link text. Errors return a ``type='text'``
        envelope so callers can degrade gracefully without unwrapping.

    """
    try:
        supabase = get_service_client()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        payload = dict(payload or {})
        requester_user_id = payload.get("requester_user_id") or payload.get("user_id")
        if requester_user_id:
            payload.setdefault("requester_user_id", requester_user_id)
            payload.setdefault("user_id", requester_user_id)

        data = {
            "token": token_hash,
            "action_type": action_type,
            "payload": payload,
            "user_id": requester_user_id,
            "expires_at": expires_at.isoformat(),
            "status": "PENDING",
        }

        await execute_async(
            supabase.table("approval_requests").insert(data),
            op_name="approvals.create",
        )

        # Dispatch notification to connected channels (fire-and-forget)
        if requester_user_id:
            asyncio.create_task(
                _notify_approval(
                    requester_user_id,
                    action_type,
                    action_description,
                    token,
                )
            )

        base_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
        magic_link = f"{base_url}/approval/{token}"
        decision_endpoint = f"{base_url.rstrip('/')}/approvals/{token}/decision"
        legacy_message = (
            f"I have generated an approval request for "
            f"'{action_description}'.\n"
            f"Please approve it here: {magic_link}"
        )

        return {
            "type": "approval",
            "title": action_description,
            "data": {
                "token": token,
                "action_type": action_type,
                "requires_response_by": requires_response_by
                or expires_at.isoformat(),
                "base_url": base_url,
                "decision_endpoint": decision_endpoint,
                "magic_link": magic_link,
            },
            "widget_id": str(uuid.uuid4()),
            "dismissible": True,
            "message": legacy_message,
        }

    except Exception as e:
        return {
            "type": "text",
            "message": f"Failed to generate approval link: {e!s}",
        }
