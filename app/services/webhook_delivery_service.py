# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Outbound webhook delivery service.

Handles enqueuing, delivering, retrying, and dead-lettering outbound
webhook events.  Includes a per-endpoint circuit breaker that
auto-disables endpoints after sustained failures.

Delivery flow:
1. ``enqueue_webhook_event`` finds all active endpoints subscribed to an
   event type and creates ``webhook_deliveries`` rows.
2. ``run_webhook_delivery_tick`` (called by the worker loop) picks up
   pending/failed deliveries whose ``next_retry_at`` has elapsed.
3. ``_deliver_single`` POSTs the payload with an HMAC-SHA256 signature,
   handles success/failure, and applies backoff + circuit breaker logic.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.services.encryption import decrypt_secret
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RETRY_BACKOFF_SECONDS: list[int] = [1, 5, 30, 300, 1800]
"""Backoff schedule in seconds: 1s, 5s, 30s, 5min, 30min."""

MAX_ATTEMPTS: int = 5
"""Maximum delivery attempts before moving to dead letter."""

CIRCUIT_BREAKER_THRESHOLD: int = 10
"""Consecutive failures before an endpoint is auto-disabled."""

_DELIVERY_TIMEOUT_SECONDS: float = 10.0
"""HTTP timeout for outbound webhook POST requests."""

_DELIVERY_BATCH_SIZE: int = 50
"""Maximum deliveries to process per tick."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def enqueue_webhook_event(event_type: str, payload: dict) -> int:
    """Create delivery rows for all active endpoints subscribed to *event_type*.

    Args:
        event_type: Dotted event name (e.g. ``"task.created"``).
        payload: The event payload dict to deliver.

    Returns:
        Number of deliveries enqueued.
    """
    client = get_service_client()

    # Fetch active endpoints that include this event_type in their events array.
    # Supabase ``cs`` (contains) filter checks if the column array contains
    # the given value.
    result = await execute_async(
        client.table("webhook_endpoints")
        .select("id")
        .eq("active", True)
        .contains("events", [event_type]),
        op_name="webhook.delivery.find_endpoints",
    )

    endpoints = result.data or []
    if not endpoints:
        return 0

    # Build delivery rows
    rows = [
        {
            "endpoint_id": ep["id"],
            "event_type": event_type,
            "payload": payload,
            "status": "pending",
        }
        for ep in endpoints
    ]

    await execute_async(
        client.table("webhook_deliveries").insert(rows),
        op_name="webhook.delivery.enqueue",
    )

    logger.info(
        "Enqueued %d webhook deliveries for event %s", len(rows), event_type
    )
    return len(rows)


async def run_webhook_delivery_tick() -> list[dict]:
    """Process pending webhook deliveries that are due for (re)delivery.

    Fetches up to ``_DELIVERY_BATCH_SIZE`` rows where:
    - ``status`` is ``"pending"`` or ``"failed"``
    - ``next_retry_at <= now()``
    - ``attempts < MAX_ATTEMPTS``

    Returns:
        List of delivery result dicts.
    """
    client = get_service_client()

    now_iso = datetime.now(tz=timezone.utc).isoformat()

    result = await execute_async(
        client.table("webhook_deliveries")
        .select("*, webhook_endpoints(*)")
        .in_("status", ["pending", "failed"])
        .lte("next_retry_at", now_iso)
        .lt("attempts", MAX_ATTEMPTS)
        .order("created_at")
        .limit(_DELIVERY_BATCH_SIZE),
        op_name="webhook.delivery.fetch_pending",
    )

    deliveries = result.data or []
    if not deliveries:
        return []

    results: list[dict] = []
    for delivery in deliveries:
        try:
            res = await _deliver_single(client, delivery)
            results.append(res)
        except Exception:
            logger.exception(
                "Unexpected error delivering webhook %s", delivery.get("id")
            )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _deliver_single(client: Any, delivery: dict) -> dict:
    """Attempt to deliver a single webhook payload to the endpoint.

    On success (2xx):
    - Updates delivery status to ``"delivered"``
    - Resets endpoint ``consecutive_failures`` to 0

    On failure (non-2xx or exception):
    - Increments ``attempts``
    - If ``attempts >= MAX_ATTEMPTS``: status becomes ``"dead"``
    - Otherwise: status becomes ``"failed"`` with exponential backoff
    - Increments endpoint ``consecutive_failures``
    - If ``consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD``: disables endpoint

    Args:
        client: Supabase service client.
        delivery: Delivery row dict with joined ``webhook_endpoints``.

    Returns:
        Dict with ``delivery_id``, ``status``, ``attempts``, ``response_code``.
    """
    delivery_id = delivery["id"]
    event_type = delivery["event_type"]
    payload = delivery["payload"]
    attempts = delivery["attempts"]
    endpoint = delivery["webhook_endpoints"]

    endpoint_id = endpoint["id"]
    url = endpoint["url"]
    encrypted_secret = endpoint["secret"]
    consecutive_failures = endpoint.get("consecutive_failures", 0)

    # Decrypt the endpoint signing secret
    secret = decrypt_secret(encrypted_secret)

    # Compute HMAC-SHA256 signature
    payload_bytes = json.dumps(payload, separators=(",", ":"), default=str).encode()
    signature = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Pikar-Signature": f"sha256={signature}",
        "X-Pikar-Event": event_type,
        "X-Pikar-Delivery": str(delivery_id),
    }

    response_code: int | None = None
    response_body: str = ""
    new_attempts = attempts + 1

    try:
        async with httpx.AsyncClient(timeout=_DELIVERY_TIMEOUT_SECONDS) as http:
            response = await http.post(url, content=payload_bytes, headers=headers)

        response_code = response.status_code
        response_body = response.text[:1000]

        if 200 <= response_code < 300:
            # -- SUCCESS --
            await execute_async(
                client.table("webhook_deliveries")
                .update({
                    "status": "delivered",
                    "attempts": new_attempts,
                    "response_code": response_code,
                    "response_body": response_body,
                })
                .eq("id", delivery_id),
                op_name="webhook.delivery.mark_delivered",
            )

            # Reset endpoint consecutive failures
            await execute_async(
                client.table("webhook_endpoints")
                .update({
                    "consecutive_failures": 0,
                    "updated_at": datetime.now(tz=timezone.utc).isoformat(),
                })
                .eq("id", endpoint_id),
                op_name="webhook.delivery.reset_failures",
            )

            return {
                "delivery_id": delivery_id,
                "status": "delivered",
                "attempts": new_attempts,
                "response_code": response_code,
            }

        # -- FAILURE (non-2xx) --
        # Fall through to failure handling below

    except Exception as exc:
        response_body = str(exc)[:1000]
        logger.warning(
            "Webhook delivery %s to %s failed: %s", delivery_id, url, exc
        )

    # -- Handle failure --
    return await _handle_delivery_failure(
        client=client,
        delivery_id=delivery_id,
        endpoint_id=endpoint_id,
        new_attempts=new_attempts,
        consecutive_failures=consecutive_failures,
        response_code=response_code,
        response_body=response_body,
    )


async def _handle_delivery_failure(
    *,
    client: Any,
    delivery_id: str,
    endpoint_id: str,
    new_attempts: int,
    consecutive_failures: int,
    response_code: int | None,
    response_body: str,
) -> dict:
    """Update delivery and endpoint state after a failed delivery attempt.

    Args:
        client: Supabase service client.
        delivery_id: ID of the webhook_deliveries row.
        endpoint_id: ID of the webhook_endpoints row.
        new_attempts: Updated attempt count (already incremented).
        consecutive_failures: Current consecutive failures on the endpoint.
        response_code: HTTP response code (None if connection failed).
        response_body: Truncated response body or error message.

    Returns:
        Dict with delivery result.
    """
    new_consecutive = consecutive_failures + 1

    if new_attempts >= MAX_ATTEMPTS:
        # Dead letter
        status = "dead"
        delivery_update: dict[str, Any] = {
            "status": "dead",
            "attempts": new_attempts,
            "response_code": response_code,
            "response_body": response_body,
        }
    else:
        # Schedule retry with exponential backoff
        status = "failed"
        backoff_idx = min(new_attempts - 1, len(RETRY_BACKOFF_SECONDS) - 1)
        backoff = RETRY_BACKOFF_SECONDS[backoff_idx]
        next_retry = datetime.now(tz=timezone.utc) + timedelta(seconds=backoff)

        delivery_update = {
            "status": "failed",
            "attempts": new_attempts,
            "next_retry_at": next_retry.isoformat(),
            "response_code": response_code,
            "response_body": response_body,
        }

    await execute_async(
        client.table("webhook_deliveries")
        .update(delivery_update)
        .eq("id", delivery_id),
        op_name="webhook.delivery.mark_failed",
    )

    # Increment endpoint consecutive failures
    endpoint_update: dict[str, Any] = {
        "consecutive_failures": new_consecutive,
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Circuit breaker: disable endpoint after threshold
    if new_consecutive >= CIRCUIT_BREAKER_THRESHOLD:
        endpoint_update["active"] = False
        endpoint_update["disabled_at"] = datetime.now(tz=timezone.utc).isoformat()
        logger.warning(
            "Circuit breaker tripped: endpoint %s disabled after %d consecutive failures",
            endpoint_id,
            new_consecutive,
        )

        await execute_async(
            client.table("webhook_endpoints")
            .update(endpoint_update)
            .eq("id", endpoint_id),
            op_name="webhook.delivery.disable_endpoint",
        )
    else:
        await execute_async(
            client.table("webhook_endpoints")
            .update(endpoint_update)
            .eq("id", endpoint_id),
            op_name="webhook.delivery.increment_failures",
        )

    return {
        "delivery_id": delivery_id,
        "status": status,
        "attempts": new_attempts,
        "response_code": response_code,
    }
