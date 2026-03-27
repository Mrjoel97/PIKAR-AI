# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""LinkedIn Webhook Handler.

Handles LinkedIn webhook verification and event processing.
LinkedIn uses HMAC-SHA256 signature verification on incoming webhooks.

Supported event types:
- MEMBER_SOCIAL_ACTION: Likes, comments, shares on member posts
- ORGANIZATION_SOCIAL_ACTION: Activity on organization pages
- SHARE: New posts by connected members/organizations
- COMMENT: Comments on tracked posts
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

# LinkedIn signs webhook payloads with this secret
LINKEDIN_WEBHOOK_SECRET_ENV = "LINKEDIN_WEBHOOK_SECRET"


def _get_webhook_secret() -> str | None:
    """Get the LinkedIn webhook verification secret."""
    return os.environ.get(LINKEDIN_WEBHOOK_SECRET_ENV)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify LinkedIn webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-LinkedIn-Signature header.

    Returns:
        True if signature is valid.
    """
    secret = _get_webhook_secret()
    if not secret:
        logger.warning("LINKEDIN_WEBHOOK_SECRET not configured — rejecting webhook")
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def store_webhook_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    """Persist a LinkedIn webhook event for later processing.

    Args:
        event_type: LinkedIn event type string.
        payload: Full JSON payload from LinkedIn.
        user_id: Pikar-AI user id if resolvable from the event.
        organization_id: LinkedIn organization URN if applicable.

    Returns:
        Inserted row data.
    """
    client = get_service_client()

    row = {
        "platform": "linkedin",
        "event_type": event_type,
        "payload": json.dumps(payload),
        "linkedin_org_id": organization_id,
        "user_id": user_id,
        "status": "pending",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    result = client.table("social_webhook_events").insert(row).execute()
    logger.info("Stored LinkedIn webhook event: type=%s", event_type)
    return result.data[0] if result.data else {}


def resolve_user_from_event(payload: dict[str, Any]) -> str | None:
    """Try to map a LinkedIn webhook event back to a Pikar-AI user.

    Looks up the LinkedIn member URN in connected_accounts.
    """
    # LinkedIn events include the actor as a URN like "urn:li:person:ABC123"
    actor_urn = None
    if "data" in payload and "actor" in payload["data"]:
        actor_urn = payload["data"]["actor"]
    elif "actor" in payload:
        actor_urn = payload["actor"]

    if not actor_urn:
        return None

    client = get_service_client()
    result = (
        client.table("connected_accounts")
        .select("user_id")
        .eq("platform", "linkedin")
        .eq("platform_user_id", actor_urn)
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]["user_id"]
    return None


def extract_event_type(payload: dict[str, Any]) -> str:
    """Extract the event type string from a LinkedIn webhook payload."""
    return payload.get("eventType", payload.get("type", "unknown"))


def extract_organization_id(payload: dict[str, Any]) -> str | None:
    """Extract the LinkedIn organization URN if present."""
    if "data" in payload and "organization" in payload["data"]:
        return payload["data"]["organization"]
    return payload.get("organizationId")
