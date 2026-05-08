# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Approval tool.

Generates human approval requests with Magic Links and dispatches
``approval.pending`` notifications to connected Slack / Teams channels.

Also exposes ``wait_for_approval`` so an agent that called
``request_human_approval`` can asynchronously block on the user's decision
(approve / reject / timeout) and resume its workflow without re-prompting.
"""

import asyncio
import hashlib
import logging
import os
import secrets
import time
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
    action_type: str, action_description: str, payload: dict[str, Any]
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

    Returns:
        A widget envelope dict with ``type='approval'`` so the frontend can
        render an inline Approve/Reject card. Shape::

            {
                "type": "approval",
                "title": <action_description>,
                "data": {
                    "token": <plain token>,
                    "action_type": <action_type>,
                    "requires_response_by": <iso8601>,
                    "base_url": <app base url>,
                    "decision_endpoint": "/approvals/{token}/decision",
                    "magic_link": "<base_url>/approval/{token}",
                },
                "widget_id": <uuid4>,
                "dismissible": True,
                "message": <legacy human-readable text + magic link>,
            }

        On error, returns a back-compat ``{"type": "text", "message": ..., ...}``
        dict so callers that only read ``message`` keep working.

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
        link = f"{base_url}/approval/{token}"
        legacy_message = (
            f"I have generated an approval request for "
            f"'{action_description}'.\n"
            f"Please approve it here: {link}"
        )

        return {
            "type": "approval",
            "title": action_description,
            "data": {
                "token": token,
                "action_type": action_type,
                "requires_response_by": expires_at.isoformat(),
                "base_url": base_url,
                "decision_endpoint": f"/approvals/{token}/decision",
                "magic_link": link,
            },
            "widget_id": str(uuid.uuid4()),
            "dismissible": True,
            "message": legacy_message,
        }

    except Exception as e:
        err_msg = f"Failed to generate approval link: {e!s}"
        return {
            "type": "text",
            "message": err_msg,
            "success": False,
            "error": err_msg,
        }


# Terminal statuses written by the approvals decision endpoint. Anything else
# (PENDING) means the row hasn't been decided yet and we keep polling.
_TERMINAL_STATUSES: dict[str, str] = {
    "APPROVED": "approve",
    "REJECTED": "reject",
    "EXPIRED": "timeout",
}


async def wait_for_approval(
    token: str,
    timeout_s: int | float = 600,
    poll_interval_s: int | float = 3,
) -> dict[str, Any]:
    """Block until an approval token reaches a terminal status, or timeout.

    Polls the ``approval_requests`` row for the supplied (plain) token by
    SHA-256-hashing it and querying the ``token`` column — matching the
    storage scheme used by ``request_human_approval`` and the decision
    endpoint at ``POST /approvals/{token}/decision``.

    The loop exits as soon as the row's ``status`` is no longer ``"PENDING"``
    or ``timeout_s`` seconds have elapsed (whichever comes first). DB-polling
    is intentional: no Realtime / pubsub infra to stand up.

    Args:
        token: The plain (unhashed) approval token returned by
            ``request_human_approval`` in ``data.token``.
        timeout_s: Maximum seconds to wait before returning a ``timeout``
            decision. Defaults to 600 (10 minutes).
        poll_interval_s: Seconds to sleep between polls. Defaults to 3.

    Returns:
        A dict the caller can branch on::

            {
                "decision": "approve" | "reject" | "timeout" | "error",
                "token": <plain token>,
                "decided_at": <iso8601 str | None>,
                "decided_by": <user_id str | None>,
                "status": <raw db status | None>,
                "error": <str>,    # only on decision=="error"
            }

        ``decision`` is normalised to lowercase verbs so the agent can use
        a simple branch (``if result["decision"] == "approve": ...``).

    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    deadline = time.monotonic() + float(timeout_s)
    supabase = get_service_client()

    while True:
        try:
            response = await execute_async(
                supabase.table("approval_requests")
                .select("status, responded_at, payload")
                .eq("token", token_hash)
                .single(),
                op_name="approvals.wait_for_approval.poll",
            )
        except Exception as exc:
            # Transient DB error — log and treat as still-waiting unless the
            # deadline has already passed; that gives the helper resilience
            # against momentary Supabase blips without busy-looping forever.
            logger.warning(
                "wait_for_approval poll failed for token_hash=%s: %s",
                token_hash[:8],
                exc,
                exc_info=True,
            )
            if time.monotonic() >= deadline:
                return {
                    "decision": "error",
                    "token": token,
                    "decided_at": None,
                    "decided_by": None,
                    "status": None,
                    "error": str(exc),
                }
            await asyncio.sleep(poll_interval_s)
            continue

        row = getattr(response, "data", None) or {}
        status = row.get("status")

        if status and status != "PENDING":
            payload = row.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}
            decision = _TERMINAL_STATUSES.get(status, "error")
            return {
                "decision": decision,
                "token": token,
                "decided_at": row.get("responded_at"),
                "decided_by": payload.get("decided_by"),
                "status": status,
            }

        if time.monotonic() >= deadline:
            return {
                "decision": "timeout",
                "token": token,
                "decided_at": None,
                "decided_by": None,
                "status": status,
            }

        await asyncio.sleep(poll_interval_s)


# Tool list (mirrors MAGIC_LINK_TOOLS / NOTIFICATION_TOOLS export pattern)
# so the Executive Agent can be wired up via `*APPROVAL_TOOLS`.
APPROVAL_TOOLS = [request_human_approval, wait_for_approval]
