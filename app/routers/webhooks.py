"""Webhook API Router.

Receives inbound webhooks from third-party platforms (LinkedIn, Resend, etc.).
Each platform has its own verification mechanism.
"""

import base64
import hashlib
import hmac
import html
import json
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from app.mcp.config import get_mcp_config
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
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

    logger.info(
        "LinkedIn webhook verification request received — responding with signed challenge"
    )
    return Response(
        content=json.dumps(
            {
                "challengeCode": challengeCode,
                "challengeResponse": challenge_response,
            }
        ),
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
# Resend Webhooks (Inbound Email)
# ============================================================================

# Tolerance window for Svix timestamp verification (5 minutes)
_SVIX_TIMESTAMP_TOLERANCE_SECONDS = 300

# Resend API base for fetching received email content
_RESEND_API_BASE = "https://api.resend.com"


def _verify_svix_signature(
    body: bytes, headers: dict[str, str], secret: str
) -> bool:
    """Verify a Resend/Svix webhook signature.

    Resend uses Svix for webhook delivery. The signature is HMAC-SHA256 over
    ``{svix_id}.{svix_timestamp}.{body}`` using the base64-decoded portion
    of the ``whsec_...`` signing secret.
    """
    svix_id = headers.get("svix-id", "")
    svix_timestamp = headers.get("svix-timestamp", "")
    svix_signature = headers.get("svix-signature", "")

    if not svix_id or not svix_timestamp or not svix_signature:
        return False

    # Reject stale timestamps to prevent replay attacks
    try:
        ts = int(svix_timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > _SVIX_TIMESTAMP_TOLERANCE_SECONDS:
        return False

    # Decode the secret — strip the "whsec_" prefix first
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))

    # Build the signed content: "{svix_id}.{svix_timestamp}.{raw_body}"
    signed_content = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode()

    # Svix may send multiple signatures separated by spaces, each prefixed "v1,"
    for sig in svix_signature.split(" "):
        sig_value = sig.removeprefix("v1,")
        if hmac.compare_digest(expected, sig_value):
            return True

    return False


async def _fetch_received_email(email_id: str, api_key: str) -> dict[str, Any]:
    """Fetch full email content from Resend Received Emails API.

    The webhook only includes metadata — the body, headers, and attachments
    must be fetched separately.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{_RESEND_API_BASE}/emails/{email_id}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
    if response.status_code == 200:
        return response.json()
    logger.error(
        "Failed to fetch received email %s: %s %s",
        email_id,
        response.status_code,
        response.text,
    )
    return {}


async def _forward_email(
    *,
    from_addr: str,
    to_addr: str,
    subject: str,
    body_html: str | None,
    body_text: str | None,
    original_from: str,
    api_key: str,
) -> bool:
    """Forward an inbound email to the configured personal inbox."""
    forward_subject = f"[Fwd] {subject} (from {original_from})"

    # Build forwarding content with original sender attribution
    if body_html:
        html_content = (
            f'<div style="padding:12px;margin-bottom:16px;border-left:4px solid #6366f1;'
            f'background:#f8fafc;border-radius:4px;">'
            f"<strong>Forwarded email</strong><br>"
            f"From: {html.escape(original_from)}<br>"
            f"Subject: {html.escape(subject)}</div>"
            f"<hr style='border:none;border-top:1px solid #e2e8f0;margin:16px 0;'>"
            f"{body_html}"
        )
    else:
        html_content = (
            f"<pre>--- Forwarded email ---\n"
            f"From: {html.escape(original_from)}\nSubject: {html.escape(subject)}\n---\n\n"
            f"{html.escape(body_text or '(empty body)')}</pre>"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_RESEND_API_BASE}/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [to_addr],
                "subject": forward_subject,
                "html": html_content,
                "reply_to": original_from,
            },
        )

    if response.status_code == 200:
        logger.info("Forwarded email to %s (resend_id=%s)", to_addr, response.json().get("id"))
        return True

    logger.error("Failed to forward email: %s %s", response.status_code, response.text)
    return False


@router.post("/resend")
async def resend_webhook(request: Request) -> JSONResponse:
    """Receive Resend webhook events (email.received).

    Flow:
    1. Verify Svix signature (if webhook secret configured)
    2. Parse the email.received event metadata
    3. Fetch full email body from Resend API
    4. Store in ``inbound_emails`` table
    5. Forward to personal inbox
    """
    config = get_mcp_config()

    # Read raw body — must happen before any JSON parsing for signature verification
    body = await request.body()

    # Verify Svix signature if webhook secret is configured
    if config.resend_webhook_secret:
        svix_headers = {
            "svix-id": request.headers.get("svix-id", ""),
            "svix-timestamp": request.headers.get("svix-timestamp", ""),
            "svix-signature": request.headers.get("svix-signature", ""),
        }
        if not _verify_svix_signature(body, svix_headers, config.resend_webhook_secret):
            logger.warning("Resend webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type", "")

    # We only process email.received events
    if event_type != "email.received":
        logger.info("Resend webhook event ignored: %s", event_type)
        return JSONResponse({"status": "ignored", "event_type": event_type})

    data = payload.get("data", {})
    email_id = data.get("email_id", "")

    if not email_id:
        logger.warning("Resend email.received event missing email_id")
        raise HTTPException(status_code=400, detail="Missing email_id in event data")

    logger.info(
        "Resend inbound email received: id=%s from=%s to=%s subject=%s",
        email_id,
        data.get("from"),
        data.get("to"),
        data.get("subject"),
    )

    # Fetch full email content (webhook only has metadata)
    full_email: dict[str, Any] = {}
    if config.resend_api_key:
        full_email = await _fetch_received_email(email_id, config.resend_api_key)

    from_address = data.get("from", full_email.get("from", "unknown"))
    to_addresses = data.get("to", full_email.get("to", []))
    if isinstance(to_addresses, str):
        to_addresses = [to_addresses]
    cc_addresses = data.get("cc", full_email.get("cc", []))
    if isinstance(cc_addresses, str):
        cc_addresses = [cc_addresses]
    bcc_addresses = data.get("bcc", full_email.get("bcc", []))
    if isinstance(bcc_addresses, str):
        bcc_addresses = [bcc_addresses]

    subject = data.get("subject", full_email.get("subject", "(no subject)"))
    body_html = full_email.get("html")
    body_text = full_email.get("text")
    headers = full_email.get("headers", {})
    attachments = data.get("attachments", full_email.get("attachments", []))
    message_id = data.get("message_id", full_email.get("message_id"))

    # Store in Supabase
    client = get_service_client()
    insert_data = {
        "resend_email_id": email_id,
        "from_address": from_address,
        "to_addresses": to_addresses,
        "cc_addresses": cc_addresses,
        "bcc_addresses": bcc_addresses,
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text,
        "headers": headers if isinstance(headers, dict) else {},
        "attachments": attachments if isinstance(attachments, list) else [],
        "message_id": message_id,
        "status": "received",
    }

    try:
        result = await execute_async(
            client.table("inbound_emails").insert(insert_data),
            op_name="webhooks.resend.store_inbound",
        )
        record_id = result.data[0]["id"] if result.data else None
        logger.info("Stored inbound email: db_id=%s resend_id=%s", record_id, email_id)
    except Exception:
        logger.exception("Failed to store inbound email %s", email_id)
        record_id = None

    # Forward to personal inbox
    forwarded = False
    if config.resend_api_key and config.resend_forward_to:
        try:
            forwarded = await _forward_email(
                from_addr=f"Pikar AI Mail <{config.resend_from_email}>",
                to_addr=config.resend_forward_to,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                original_from=from_address,
                api_key=config.resend_api_key,
            )
        except Exception:
            logger.exception("Failed to forward email %s", email_id)

    # Update status in DB
    if record_id:
        new_status = "forwarded" if forwarded else "received"
        update_data: dict[str, Any] = {"status": new_status}
        if forwarded:
            update_data["forwarded_to"] = config.resend_forward_to
            update_data["forwarded_at"] = "now()"
        try:
            await execute_async(
                client.table("inbound_emails")
                .update(update_data)
                .eq("id", record_id),
                op_name="webhooks.resend.update_status",
            )
        except Exception:
            logger.exception("Failed to update inbound email status %s", record_id)

    return JSONResponse({
        "status": "processed",
        "email_id": email_id,
        "forwarded": forwarded,
    })


# ============================================================================
# Stripe Webhooks (Dedicated — Phase 41)
# ============================================================================


async def _resolve_stripe_user_id() -> str | None:
    """Resolve user_id for Stripe platform-key mode.

    Looks up the single user who has a Stripe integration credential.
    In platform API key mode there is typically one connected account.

    Returns:
        The user_id string, or ``None`` if no Stripe credential found.
    """
    client = get_service_client()
    result = await execute_async(
        client.table("integration_credentials")
        .select("user_id")
        .eq("provider", "stripe")
        .limit(1),
        op_name="webhooks.stripe.resolve_user",
    )
    if result.data:
        return result.data[0]["user_id"]
    return None


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    """Receive and process Stripe webhook events.

    Uses Stripe's native ``construct_event`` for signature verification
    (timestamp-based format: ``t=TIMESTAMP,v1=SIGNATURE``).

    This is a DEDICATED endpoint — does NOT use the generic
    ``_verify_inbound_signature`` which expects ``sha256=<hex>`` format.

    Supported events:
    - ``payment_intent.succeeded`` — creates a revenue record
    - ``charge.refunded`` — creates a refund record
    - ``payout.paid`` — creates a payout record

    Returns:
        ``{"status": "processed"}`` on success.

    Raises:
        HTTPException: 400 for invalid payload, 403 for invalid signature.
    """
    try:
        import stripe as stripe_sdk  # type: ignore[import]
    except ImportError as exc:
        logger.error("Stripe SDK not installed — cannot process webhook")
        raise HTTPException(
            status_code=500, detail="Stripe SDK not available"
        ) from exc

    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not endpoint_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=500, detail="Stripe webhook secret not configured"
        )

    # Read raw body for signature verification
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    # Verify using Stripe's native construct_event
    try:
        event = stripe_sdk.Webhook.construct_event(
            body, sig_header, endpoint_secret
        )
    except ValueError as exc:
        logger.warning("Stripe webhook: invalid payload")
        raise HTTPException(
            status_code=400, detail="Invalid payload"
        ) from exc
    except stripe_sdk.error.SignatureVerificationError as exc:
        logger.warning("Stripe webhook: invalid signature")
        raise HTTPException(
            status_code=403, detail="Invalid signature"
        ) from exc

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})

    logger.info("Stripe webhook received: type=%s", event_type)

    # Resolve user_id — in platform key mode, look up the Stripe user
    user_id = await _resolve_stripe_user_id()
    if not user_id:
        logger.warning(
            "Stripe webhook: no user with Stripe credential found, "
            "acknowledging but skipping event %s",
            event_type,
        )
        return {"status": "skipped", "reason": "no_stripe_user"}

    # Route to appropriate handler
    from app.services.stripe_sync_service import StripeSyncService

    svc = StripeSyncService()

    if event_type == "payment_intent.succeeded":
        await svc.handle_payment_intent_succeeded(event_data, user_id)
    elif event_type == "charge.refunded":
        await svc.handle_charge_refunded(event_data, user_id)
    elif event_type == "payout.paid":
        await svc.handle_payout_paid(event_data, user_id)
    else:
        logger.info("Stripe webhook: unhandled event type %s", event_type)
        return {"status": "ignored", "event_type": event_type}

    return {"status": "processed", "event_type": event_type}


# ============================================================================
# Generalized Inbound Webhooks (Phase 39)
# ============================================================================

# Provider-specific webhook secret env var names for HMAC verification.
# When Plan 01 delivers app.config.integration_providers.PROVIDER_REGISTRY,
# this map should be replaced with registry lookups.
_INBOUND_PROVIDER_SECRETS: dict[str, str] = {
    "stripe": "STRIPE_WEBHOOK_SECRET",
    "hubspot": "HUBSPOT_WEBHOOK_SECRET",
    "resend": "RESEND_WEBHOOK_SECRET",
    "github": "GITHUB_WEBHOOK_SECRET",
    "slack": "SLACK_WEBHOOK_SECRET",
    "shopify": "SHOPIFY_WEBHOOK_SECRET",
}


def _verify_inbound_signature(
    *,
    body: bytes,
    secret: str,
    signature_header: str,
) -> bool:
    """Verify an inbound webhook payload using HMAC-SHA256.

    The expected header format is ``sha256=<hex_digest>``.  Uses
    ``hmac.compare_digest`` for timing-safe comparison.

    Args:
        body: Raw request body bytes.
        secret: The shared HMAC signing secret.
        signature_header: Value of the provider's signature header.

    Returns:
        ``True`` if the signature is valid.
    """
    if not signature_header:
        return False

    # Strip the "sha256=" prefix if present
    hex_sig = signature_header
    if hex_sig.startswith("sha256="):
        hex_sig = hex_sig[7:]

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, hex_sig)


def _extract_event_id(provider: str, payload: dict[str, Any]) -> str:
    """Extract a unique event ID from the webhook payload.

    Falls back to hashing the entire payload when no ``id`` field is present.

    Args:
        provider: Provider slug (e.g. ``"stripe"``).
        payload: Parsed JSON payload.

    Returns:
        A string suitable for deduplication.
    """
    # Most providers include an "id" at the top level
    event_id = payload.get("id")
    if event_id:
        return str(event_id)

    # Fallback: deterministic hash of the serialised payload
    serialised = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()[:32]


def _extract_event_type(provider: str, payload: dict[str, Any]) -> str:
    """Extract the event type string from a provider's webhook payload.

    Args:
        provider: Provider slug.
        payload: Parsed JSON payload.

    Returns:
        A string describing the event type, or ``"unknown"`` if absent.
    """
    return str(payload.get("type", payload.get("event", "unknown")))


async def _handle_inbound_insert(
    *,
    client: Any,
    provider: str,
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Insert into webhook_events with ON CONFLICT DO NOTHING.

    If the insert returns empty data (duplicate), returns
    ``{status: "duplicate"}``.  Otherwise queues a job in ``ai_jobs``
    and returns ``{status: "received"}``.

    This function is split out from the endpoint handler so it can be
    unit-tested without triggering the full ASGI import chain.
    """
    # Insert with idempotency guard
    insert_data = {
        "provider": provider,
        "event_id": event_id,
        "event_type": event_type,
        "payload": payload,
        "status": "pending",
    }

    result = await execute_async(
        client.table("webhook_events").upsert(
            insert_data,
            on_conflict="provider,event_id",
            ignore_duplicates=True,
        ),
        op_name="webhooks.inbound.insert",
    )

    # Supabase upsert with ignore_duplicates returns empty data for conflicts
    if not result.data:
        return {"status": "duplicate", "event_id": event_id}

    # Queue for async processing
    row_id = result.data[0]["id"]
    await execute_async(
        client.table("ai_jobs").insert({
            "job_type": "webhook_inbound_process",
            "priority": 8,
            "input_data": {
                "webhook_event_id": row_id,
                "provider": provider,
                "event_type": event_type,
            },
        }),
        op_name="webhooks.inbound.queue_job",
    )

    return {"status": "received", "event_id": event_id}


@router.post("/inbound/{provider}")
async def inbound_webhook(provider: str, request: Request) -> dict[str, Any]:
    """Receive and verify a generic inbound webhook from any provider.

    Uses HMAC-SHA256 verification with a per-provider shared secret.

    Args:
        provider: Provider slug from URL path (e.g. ``stripe``).
        request: FastAPI request object.

    Returns:
        ``{status: "received", event_id}`` or ``{status: "duplicate", event_id}``.

    Raises:
        HTTPException: 404 if provider is unknown, 403 if signature is invalid.
    """
    # Look up provider secret env var
    env_var = _INBOUND_PROVIDER_SECRETS.get(provider)
    if not env_var:
        # Try loading from PROVIDER_REGISTRY (Plan 01) at runtime
        try:
            from app.config.integration_providers import PROVIDER_REGISTRY

            provider_cfg = PROVIDER_REGISTRY.get(provider)
            if provider_cfg and hasattr(provider_cfg, "webhook_secret_header"):
                env_var = f"{provider.upper()}_WEBHOOK_SECRET"
        except ImportError:
            pass

    if not env_var:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    secret = os.environ.get(env_var, "")
    if not secret:
        logger.error(
            "Webhook secret not configured for provider %s (env: %s)", provider, env_var
        )
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Read raw body for signature verification
    body = await request.body()

    # Determine provider-specific signature header
    sig_header_names = {
        "stripe": "Stripe-Signature",
        "hubspot": "X-HubSpot-Signature-v3",
        "github": "X-Hub-Signature-256",
        "slack": "X-Slack-Signature",
        "shopify": "X-Shopify-Hmac-SHA256",
    }
    header_name = sig_header_names.get(provider, f"X-{provider.title()}-Signature")
    signature = request.headers.get(header_name, "")

    if not _verify_inbound_signature(
        body=body,
        secret=secret,
        signature_header=signature,
    ):
        logger.warning("Inbound webhook signature verification failed for %s", provider)
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_id = _extract_event_id(provider, payload)
    event_type = _extract_event_type(provider, payload)

    logger.info(
        "Inbound webhook received: provider=%s event_type=%s event_id=%s",
        provider,
        event_type,
        event_id,
    )

    client = get_service_client()
    return await _handle_inbound_insert(
        client=client,
        provider=provider,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
    )


@router.get("/events")
@limiter.limit(get_user_persona_limit)
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

    result = await execute_async(query, op_name="webhooks.events.list")
    return {"events": result.data}
