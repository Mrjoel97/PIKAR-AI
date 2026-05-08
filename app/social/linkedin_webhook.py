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

# LinkedIn signs webhooks with the application's clientSecret (NOT a separate
# webhook secret).  See https://learn.microsoft.com/en-us/linkedin/marketing/integrations/webhooks
# The deprecated ``LINKEDIN_WEBHOOK_SECRET`` env var is no longer read at runtime;
# the deprecation note is kept in ``.env.example`` so existing deployments don't
# break on env-var validation.
LINKEDIN_CLIENT_SECRET_ENV = "LINKEDIN_CLIENT_SECRET"
_LINKEDIN_SIG_PREFIX = "hmacsha256="


def _get_client_secret() -> str | None:
    """Get the LinkedIn application client secret used for webhook HMAC."""
    return os.environ.get(LINKEDIN_CLIENT_SECRET_ENV)


def verify_signature(payload: bytes, signature_header: str) -> bool:
    """Verify LinkedIn webhook X-LI-Signature header.

    LinkedIn signs payloads with HMAC-SHA256 of the raw body, prefixed
    with ``hmacsha256=``, using the application's clientSecret
    (env var ``LINKEDIN_CLIENT_SECRET``).

    Args:
        payload: Raw request body bytes (must be the exact bytes LinkedIn signed).
        signature_header: Value of the ``X-LI-Signature`` header. Expected
            format: ``hmacsha256=<hex-digest>``.

    Returns:
        ``True`` if the signature is valid; ``False`` for missing secret,
        missing/malformed header, or HMAC mismatch.
    """
    secret = _get_client_secret()
    if not secret:
        logger.warning(
            "%s not configured -- rejecting LinkedIn webhook",
            LINKEDIN_CLIENT_SECRET_ENV,
        )
        return False
    if not signature_header or not signature_header.startswith(_LINKEDIN_SIG_PREFIX):
        return False
    received = signature_header[len(_LINKEDIN_SIG_PREFIX) :]
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received)


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


# TODO(post-Phase-103): platform_user_id is now the bare OIDC sub
# (Phase 103 POST-01) but actor_urn here is the full URN. Either strip
# the 'urn:li:person:' prefix here or denormalize. Track as follow-up.
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
