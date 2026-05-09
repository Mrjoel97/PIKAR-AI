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


def _row_to_result(token: str, row: dict[str, Any]) -> dict[str, Any]:
    """Normalise a decided ``approval_requests`` row into the public result.

    Shared by both the polling arm and the realtime arm so the result shape
    is byte-for-byte identical regardless of which side wins the race.
    """
    payload = row.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    status = row.get("status")
    decision = _TERMINAL_STATUSES.get(status or "", "error")
    return {
        "decision": decision,
        "token": token,
        "decided_at": row.get("responded_at"),
        "decided_by": payload.get("decided_by"),
        "status": status,
    }


async def _wait_via_realtime(
    token_hash: str, timeout_s: float
) -> dict[str, Any] | None:
    """Push-based wait: subscribe to ``approval_requests`` UPDATEs.

    Returns the decided row dict (``{status, responded_at, payload, ...}``)
    as soon as a non-PENDING UPDATE event fires for ``token=eq.<token_hash>``.
    Returns ``None`` on timeout or any subscription/transport error so the
    caller can fall back to polling cleanly.

    All Realtime imports are lazy — if the pinned Supabase SDK ever drops
    realtime support, this helper degrades to a no-op (``None``) and the
    polling arm keeps the wait correct.
    """
    try:
        # Lazy imports — keep realtime optional so missing SDK support
        # degrades to polling-only without breaking the module import.
        from app.services.supabase_client import get_async_service
    except Exception:  # pragma: no cover - import error path
        return None

    decided_event = asyncio.Event()
    decided_row: dict[str, Any] = {}
    channel = None

    def _on_update(payload: dict[str, Any]) -> None:
        # postgres_changes payload shape: {"data": {"record": {...}, ...}, ...}
        # but newer realtime SDKs flatten it. Be permissive.
        try:
            data = payload.get("data") if isinstance(payload, dict) else None
            record: dict[str, Any] | None = None
            if isinstance(data, dict):
                record = data.get("record") or data.get("new") or data
            if record is None and isinstance(payload, dict):
                record = payload.get("record") or payload.get("new")
            if not isinstance(record, dict):
                return
            status = record.get("status")
            if status and status != "PENDING":
                decided_row.update(record)
                decided_event.set()
        except Exception:
            logger.debug("realtime payload parse failed", exc_info=True)

    try:
        service = await get_async_service()
        async_client = service.client
        channel = async_client.channel(f"approvals:{token_hash[:16]}")
        channel.on_postgres_changes(
            "UPDATE",
            callback=_on_update,
            schema="public",
            table="approval_requests",
            filter=f"token=eq.{token_hash}",
        )
        await channel.subscribe()
    except Exception as exc:
        logger.debug(
            "wait_for_approval realtime subscribe failed for token_hash=%s: %s",
            token_hash[:8],
            exc,
        )
        # Best-effort cleanup of a partially-set-up channel.
        if channel is not None:
            try:
                await channel.unsubscribe()
            except Exception:
                pass
        return None

    try:
        try:
            await asyncio.wait_for(decided_event.wait(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None
        return dict(decided_row) if decided_row else None
    finally:
        try:
            await channel.unsubscribe()
        except Exception:
            logger.debug("realtime unsubscribe failed", exc_info=True)


async def _wait_via_polling(
    token: str,
    token_hash: str,
    timeout_s: float,
    poll_interval_s: float,
) -> dict[str, Any]:
    """Polling arm — preserves Wave 4 behaviour byte-for-byte.

    Returns the public result dict (same shape as ``wait_for_approval``).
    Kept as a standalone helper so it can be raced against the realtime arm.
    """
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
            return _row_to_result(token, row)

        if time.monotonic() >= deadline:
            return {
                "decision": "timeout",
                "token": token,
                "decided_at": None,
                "decided_by": None,
                "status": status,
            }

        await asyncio.sleep(poll_interval_s)


async def wait_for_approval(
    token: str,
    timeout_s: int | float = 600,
    poll_interval_s: int | float = 3,
) -> dict[str, Any]:
    """Block until an approval token reaches a terminal status, or timeout.

    Hybrid wait: races a Supabase Realtime subscription against a DB-polling
    fallback. Whichever resolves first wins; the loser is cancelled cleanly.
    This drops decision-propagation latency from the polling floor (3s) to
    ~tens of milliseconds when Realtime is reachable, while keeping polling
    as the safety net so transient WebSocket failures never break the wait.

    The token is SHA-256 hashed before querying — matching the storage
    scheme used by ``request_human_approval`` and the decision endpoint at
    ``POST /approvals/{token}/decision``.

    Args:
        token: The plain (unhashed) approval token returned by
            ``request_human_approval`` in ``data.token``.
        timeout_s: Maximum seconds to wait before returning a ``timeout``
            decision. Defaults to 600 (10 minutes).
        poll_interval_s: Seconds to sleep between polls on the fallback arm.
            Defaults to 3.

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
    timeout_f = float(timeout_s)
    poll_f = float(poll_interval_s)

    # Pre-check: handle "already decided before subscribe" race so we never
    # miss a terminal status that landed before the realtime channel joined.
    try:
        supabase = get_service_client()
        pre = await execute_async(
            supabase.table("approval_requests")
            .select("status, responded_at, payload")
            .eq("token", token_hash)
            .single(),
            op_name="approvals.wait_for_approval.precheck",
        )
        pre_row = getattr(pre, "data", None) or {}
        pre_status = pre_row.get("status")
        if pre_status and pre_status != "PENDING":
            return _row_to_result(token, pre_row)
    except Exception:
        # Pre-check is best-effort — if it fails, the polling arm will
        # surface the real error after its own retry budget.
        logger.debug(
            "wait_for_approval precheck failed for token_hash=%s",
            token_hash[:8],
            exc_info=True,
        )

    # Race: realtime push vs. polling fallback. First to resolve wins.
    realtime_task = asyncio.create_task(
        _wait_via_realtime(token_hash, timeout_f),
        name="wait_for_approval.realtime",
    )
    polling_task = asyncio.create_task(
        _wait_via_polling(token, token_hash, timeout_f, poll_f),
        name="wait_for_approval.polling",
    )

    try:
        while True:
            done, _pending = await asyncio.wait(
                {realtime_task, polling_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                if task is realtime_task:
                    try:
                        rt_row = task.result()
                    except Exception:
                        logger.debug("realtime arm raised", exc_info=True)
                        rt_row = None
                    if rt_row:
                        # Realtime delivered a decided row — return immediately.
                        return _row_to_result(token, rt_row)
                    # Realtime arm ended (timeout/error) without a decision.
                    # Fall through and let polling continue.
                else:
                    # Polling arm produced the canonical result dict already.
                    try:
                        return task.result()
                    except Exception as exc:
                        return {
                            "decision": "error",
                            "token": token,
                            "decided_at": None,
                            "decided_by": None,
                            "status": None,
                            "error": str(exc),
                        }

            # If only realtime finished (with None) but polling is still
            # running, loop and wait for polling to resolve.
            if polling_task.done():
                try:
                    return polling_task.result()
                except Exception as exc:
                    return {
                        "decision": "error",
                        "token": token,
                        "decided_at": None,
                        "decided_by": None,
                        "status": None,
                        "error": str(exc),
                    }
    finally:
        # Ensure the loser is cancelled cleanly — no orphaned tasks.
        for task in (realtime_task, polling_task):
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass


# Tool list (mirrors MAGIC_LINK_TOOLS / NOTIFICATION_TOOLS export pattern)
# so the Executive Agent can be wired up via `*APPROVAL_TOOLS`.
APPROVAL_TOOLS = [request_human_approval, wait_for_approval]
