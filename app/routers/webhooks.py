"""Webhook API Router.

Receives inbound webhooks from third-party platforms (LinkedIn, etc.).
Each platform has its own verification mechanism.
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.social.linkedin_webhook import (
    extract_event_type,
    extract_organization_id,
    resolve_user_from_event,
    store_webhook_event,
    verify_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ============================================================================
# LinkedIn Webhooks
# ============================================================================


@router.get("/linkedin")
async def linkedin_webhook_verification(
    challengeCode: str = Query(..., description="LinkedIn challenge code to echo back"),
) -> Response:
    """Handle LinkedIn webhook URL verification.

    LinkedIn sends a GET request with a ``challengeCode`` query param.
    We must respond with:
    - ``challengeCode``: echo the value back
    - ``challengeResponse``: HMAC-SHA256 of challengeCode signed with the
      app's client secret (LINKEDIN_CLIENT_SECRET)

    Docs: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/webhooks
    """
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
    if not client_secret:
        logger.error("LINKEDIN_CLIENT_SECRET not configured — cannot verify webhook")
        raise HTTPException(
            status_code=500,
            detail="LinkedIn client secret not configured",
        )

    # LinkedIn requires HMAC-SHA256 of the challengeCode using the client secret
    challenge_response = hmac.new(
        client_secret.encode("utf-8"),
        challengeCode.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    logger.info("LinkedIn webhook verification request received — responding with signed challenge")
    return Response(
        content=json.dumps({
            "challengeCode": challengeCode,
            "challengeResponse": challenge_response,
        }),
        media_type="application/json",
        status_code=200,
    )


@router.post("/linkedin")
async def linkedin_webhook_event(request: Request) -> dict[str, Any]:
    """Receive and process LinkedIn webhook event notifications.

    LinkedIn signs every payload with HMAC-SHA256 via the
    ``X-LinkedIn-Signature`` header. We verify the signature before
    processing.

    Events are stored in ``social_webhook_events`` for async processing
    by the agent system.
    """
    # Read raw body for signature verification
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-LinkedIn-Signature", "")
    if not signature or not verify_signature(body, signature):
        logger.warning("LinkedIn webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = extract_event_type(payload)
    organization_id = extract_organization_id(payload)
    user_id = resolve_user_from_event(payload)

    logger.info(
        "LinkedIn webhook event received: type=%s org=%s user=%s",
        event_type,
        organization_id,
        user_id,
    )

    # Store for async processing
    stored = await store_webhook_event(
        event_type=event_type,
        payload=payload,
        user_id=user_id,
        organization_id=organization_id,
    )

    return {"status": "received", "event_id": stored.get("id")}


# ============================================================================
# Webhook Events API (authenticated, for dashboard)
# ============================================================================


@router.get("/events")
async def list_webhook_events(
    request: Request,
    platform: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    current_user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    """List webhook events for the current user.

    Used by the frontend dashboard to display incoming social events.
    """
    client = get_service_client()
    query = (
        client.table("social_webhook_events")
        .select("id, platform, event_type, status, received_at, processed_at")
        .eq("user_id", current_user_id)
        .order("received_at", desc=True)
        .limit(limit)
    )

    if platform:
        query = query.eq("platform", platform)
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return {"events": result.data}
