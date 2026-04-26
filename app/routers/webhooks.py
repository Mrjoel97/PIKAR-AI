"""Webhook API Router.

Receives inbound webhooks from third-party platforms (LinkedIn, Resend,
Shopify, etc.).  Each platform has its own verification mechanism.
"""

import asyncio
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


def _verify_svix_signature(body: bytes, headers: dict[str, str], secret: str) -> bool:
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
        logger.info(
            "Forwarded email to %s (resend_id=%s)", to_addr, response.json().get("id")
        )
        return True

    logger.error("Failed to forward email: %s %s", response.status_code, response.text)
    return False


async def _handle_resend_sequence_event(
    event_type: str, payload: dict[str, Any]
) -> None:
    """Handle Resend webhook events that relate to email sequences.

    Checks for ``X-Pikar-Enrollment-Id`` and ``X-Pikar-Step`` headers
    in the email metadata to identify sequence emails.  Routes to the
    appropriate ``EmailSequenceService`` handler.

    Args:
        event_type: Resend event type string.
        payload: Parsed webhook JSON payload.
    """
    data = payload.get("data", {})

    # Extract sequence metadata from email headers/tags
    headers = data.get("headers", {})
    tags = data.get("tags", {})

    enrollment_id = headers.get("X-Pikar-Enrollment-Id") or tags.get(
        "pikar_enrollment_id"
    )
    step_str = headers.get("X-Pikar-Step") or tags.get("pikar_step")

    if not enrollment_id:
        # Not a sequence email, nothing to do
        return

    try:
        step_number = int(step_str) if step_str else 0
    except (ValueError, TypeError):
        step_number = 0

    logger.info(
        "Resend sequence event: type=%s enrollment=%s step=%s",
        event_type,
        enrollment_id,
        step_number,
    )

    try:
        from app.services.email_sequence_service import (
            EmailSequenceService,
        )

        svc = EmailSequenceService()

        if event_type == "email.bounced":
            await svc.handle_bounce_event(enrollment_id, step_number)
        elif event_type in ("email.opened", "email.clicked"):
            # Record server-side tracking event
            from app.services.supabase_async import execute_async

            evt = "open" if event_type == "email.opened" else "click"
            client = svc._admin.client
            await execute_async(
                client.table("email_tracking_events").insert(
                    {
                        "enrollment_id": enrollment_id,
                        "step_number": step_number,
                        "event_type": evt,
                        "metadata": {
                            "source": "resend_webhook",
                            "resend_event": event_type,
                        },
                    }
                ),
                op_name=f"webhooks.resend.sequence_{evt}",
            )
    except Exception:
        logger.exception(
            "Failed to handle Resend sequence event %s for %s",
            event_type,
            enrollment_id,
        )


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

    # Handle sequence-related events (bounce, open, click)
    _SEQUENCE_EVENT_TYPES = {
        "email.bounced",
        "email.opened",
        "email.clicked",
    }
    if event_type in _SEQUENCE_EVENT_TYPES:
        await _handle_resend_sequence_event(event_type, payload)
        return JSONResponse({"status": "processed", "event_type": event_type})

    # We only process email.received events below
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
                client.table("inbound_emails").update(update_data).eq("id", record_id),
                op_name="webhooks.resend.update_status",
            )
        except Exception:
            logger.exception("Failed to update inbound email status %s", record_id)

    return JSONResponse(
        {
            "status": "processed",
            "email_id": email_id,
            "forwarded": forwarded,
        }
    )


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
        raise HTTPException(status_code=500, detail="Stripe SDK not available") from exc

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
        event = stripe_sdk.Webhook.construct_event(body, sig_header, endpoint_secret)
    except ValueError as exc:
        logger.warning("Stripe webhook: invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload") from exc
    except stripe_sdk.error.SignatureVerificationError as exc:
        logger.warning("Stripe webhook: invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature") from exc

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
# Shopify Webhooks
# ============================================================================


def _verify_shopify_hmac(body: bytes, secret: str, header_value: str) -> bool:
    """Verify a Shopify webhook using base64-encoded HMAC-SHA256.

    Shopify signs payloads with HMAC-SHA256 and base64-encodes the
    digest (unlike most providers that use hex encoding).

    Args:
        body: Raw request body bytes.
        secret: The Shopify webhook signing secret.
        header_value: Value of the ``X-Shopify-Hmac-Sha256`` header.

    Returns:
        ``True`` if the signature is valid.
    """
    if not header_value:
        return False
    expected = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(expected, header_value)


async def _resolve_shopify_user(shop_domain: str) -> str | None:
    """Look up user_id from integration_credentials for a Shopify shop.

    The shop domain is stored in credential metadata during the OAuth
    callback.

    Args:
        shop_domain: Shopify shop domain (e.g. ``mystore.myshopify.com``).

    Returns:
        User UUID string, or ``None`` if no matching credential found.
    """
    client = get_service_client()
    # Search credentials where provider=shopify and metadata contains shop
    result = await execute_async(
        client.table("integration_credentials")
        .select("user_id, account_name")
        .eq("provider", "shopify"),
        op_name="shopify.webhook.resolve_user",
    )
    if not result.data:
        return None

    # Match by shop domain in account_name
    # account_name stores the shop slug (e.g. "mystore")
    shop_slug = shop_domain.replace(".myshopify.com", "")
    for row in result.data:
        acct = row.get("account_name", "")
        if acct == shop_slug or acct == shop_domain:
            return row["user_id"]
    return None


@router.post("/shopify")
async def shopify_webhook(request: Request) -> dict[str, Any]:
    """Receive and process Shopify webhook events.

    Shopify signs payloads with base64-encoded HMAC-SHA256 via the
    ``X-Shopify-Hmac-Sha256`` header.  The event topic is in the
    ``X-Shopify-Topic`` header.

    Routes events to the appropriate ``ShopifyService`` handler.

    Returns:
        ``{"status": "processed"}`` on success,
        ``{"status": "skipped"}`` if no user found for the shop.

    Raises:
        HTTPException: 403 if signature is invalid, 500 if secret missing.
    """
    secret = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")
    if not secret:
        logger.error("SHOPIFY_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=500,
            detail="Shopify webhook secret not configured",
        )

    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not _verify_shopify_hmac(body, secret, hmac_header):
        logger.warning("Shopify webhook HMAC verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    topic = request.headers.get("X-Shopify-Topic", "unknown")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    logger.info(
        "Shopify webhook received: topic=%s shop=%s",
        topic,
        shop_domain,
    )

    # Resolve user from shop domain
    user_id = await _resolve_shopify_user(shop_domain)
    if not user_id:
        logger.warning("No user found for Shopify shop: %s", shop_domain)
        return {"status": "skipped"}

    # Route to appropriate handler
    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()

    topic_handlers = {
        "orders/create": svc.handle_order_create,
        "orders/updated": svc.handle_order_update,
        "products/update": svc.handle_product_update,
        "inventory_levels/update": svc.handle_inventory_update,
    }

    handler = topic_handlers.get(topic)
    if handler:
        await handler(data=payload, user_id=user_id)
        return {"status": "processed"}

    logger.info("Shopify webhook topic not handled: %s", topic)
    return {"status": "skipped"}


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
        client.table("ai_jobs").insert(
            {
                "job_type": "webhook_inbound_process",
                "priority": 8,
                "input_data": {
                    "webhook_event_id": row_id,
                    "provider": provider,
                    "event_type": event_type,
                },
            }
        ),
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


# ============================================================================
# HubSpot Webhooks (Dedicated — Phase 42)
# ============================================================================


def _verify_hubspot_signature_v3(
    *,
    body: bytes,
    method: str,
    url: str,
    timestamp: str,
    secret: str,
    signature: str,
) -> bool:
    """Verify a HubSpot v3 webhook signature.

    HubSpot v3 signatures are computed as::

        HMAC-SHA256(client_secret, method + url + body + timestamp)

    then base64-encoded.  The timestamp must be within 300 seconds of
    the current time to prevent replay attacks.

    Args:
        body: Raw request body bytes.
        method: HTTP method (e.g. ``"POST"``).
        url: Full request URL as received by HubSpot.
        timestamp: Value of ``X-HubSpot-Request-Timestamp`` header.
        secret: HubSpot app's client secret.
        signature: Value of ``X-HubSpot-Signature-v3`` header.

    Returns:
        ``True`` if signature is valid and timestamp is fresh.
    """
    # Reject stale timestamps (300 second window)
    try:
        ts_ms = int(timestamp)
        now_ms = int(time.time() * 1000)
        if abs(now_ms - ts_ms) > 300_000:
            logger.warning(
                "HubSpot webhook timestamp too old: %s (now: %s)",
                timestamp,
                now_ms,
            )
            return False
    except (ValueError, TypeError):
        return False

    # Build source string: METHOD + URL + body + timestamp
    source = f"{method}{url}{body.decode('utf-8')}{timestamp}"
    expected = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            source.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    return hmac.compare_digest(expected, signature)


async def _resolve_hubspot_user(portal_id: str) -> str | None:
    """Resolve user_id from integration_credentials for a HubSpot portal.

    Looks for a HubSpot credential whose ``account_name`` or
    ``metadata`` contains the portal ID.

    Args:
        portal_id: HubSpot portal (account) ID string.

    Returns:
        User UUID string, or ``None`` if no matching credential found.
    """
    client = get_service_client()
    result = await execute_async(
        client.table("integration_credentials")
        .select("user_id, account_name")
        .eq("provider", "hubspot"),
        op_name="webhooks.hubspot.resolve_user",
    )
    if not result.data:
        return None

    for row in result.data:
        acct = row.get("account_name", "")
        if acct == portal_id or portal_id in acct:
            return row["user_id"]

    # Fallback: return the first HubSpot credential (single-user mode)
    return result.data[0]["user_id"]


# ============================================================================
# Linear Webhooks (PM sync — Phase 44)
# ============================================================================


async def _resolve_linear_user(organization_id: str) -> str | None:
    """Resolve user_id from integration_credentials for a Linear organisation.

    Linear credentials store the organisation ID in ``account_name`` during
    the OAuth callback.

    Args:
        organization_id: Linear organisation UUID from the webhook payload.

    Returns:
        User UUID string, or ``None`` if no matching credential found.
    """
    client = get_service_client()
    result = await execute_async(
        client.table("integration_credentials")
        .select("user_id, account_name")
        .eq("provider", "linear"),
        op_name="webhooks.linear.resolve_user",
    )
    if not result.data:
        return None

    for row in result.data:
        acct = row.get("account_name", "")
        if acct == organization_id:
            return row["user_id"]

    # Fallback: single-user mode — return the first Linear credential
    return result.data[0]["user_id"]


async def _resolve_linear_synced_projects(user_id: str) -> list[str]:
    """Return the team IDs the user has enabled sync for.

    Args:
        user_id: The owning user's UUID.

    Returns:
        List of Linear team ID strings, or empty list.
    """
    from app.services.pm_sync_service import PMSyncService

    svc = PMSyncService()
    config = await svc.get_sync_config(user_id, "linear")
    return config.get("project_ids", [])


@router.post("/linear")
async def linear_webhook(request: Request) -> dict[str, Any]:
    """Receive and process Linear webhook events for PM sync.

    Verifies the ``Linear-Signature`` HMAC-SHA256 header then processes
    ``Issue`` create/update/remove events by delegating to
    ``PMSyncService.sync_from_external``.

    Returns:
        ``{"ok": True}`` on success (Linear expects a fast 200 response).

    Raises:
        HTTPException: 403 if signature is invalid, 500 if secret missing.
    """
    signing_secret = os.environ.get("LINEAR_WEBHOOK_SECRET", "")
    if not signing_secret:
        logger.error("LINEAR_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=500, detail="Webhook secret not configured"
        )

    # Read raw body first (must happen before any streaming reads)
    body = await request.body()

    # Verify HMAC-SHA256 signature (signing_secret is guaranteed non-empty here)
    received_sig = request.headers.get("Linear-Signature", "")
    expected_sig = hmac.new(
        signing_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    if not received_sig or not hmac.compare_digest(expected_sig, received_sig):
        logger.warning("Linear webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_type = payload.get("type", "")
    action = payload.get("action", "")
    organization_id = payload.get("organizationId", "")

    logger.info(
        "Linear webhook received: type=%s action=%s org=%s",
        event_type,
        action,
        organization_id,
    )

    # Only process Issue events
    if event_type != "Issue":
        return {"ok": True}

    if action not in ("create", "update", "remove"):
        return {"ok": True}

    issue_data: dict[str, Any] = payload.get("data", {})
    if not issue_data:
        return {"ok": True}

    # Resolve the user from organisation ID
    user_id = await _resolve_linear_user(organization_id)
    if not user_id:
        logger.warning("Linear webhook: no user found for org=%s", organization_id)
        return {"ok": True}

    # Check if the issue's team is in synced projects
    team_obj = issue_data.get("team") or {}
    team_id = team_obj.get("id", "")
    synced_projects = await _resolve_linear_synced_projects(user_id)
    if synced_projects and team_id and team_id not in synced_projects:
        logger.info(
            "Linear webhook: team %s not in synced projects for user %s — skipping",
            team_id,
            user_id,
        )
        return {"ok": True}

    from app.services.pm_sync_service import PMSyncService

    svc = PMSyncService()

    if action == "remove":
        # Mark the task as cancelled rather than deleting it
        external_id = issue_data.get("id", "")
        if external_id:
            cancelled_issue = dict(issue_data)
            cancelled_issue["state"] = {
                "id": "cancelled",
                "name": "Cancelled",
                "type": "cancelled",
            }
            try:
                await svc.sync_from_external(user_id, "linear", cancelled_issue)
            except Exception:
                logger.exception(
                    "Linear webhook: failed to cancel issue %s", external_id
                )
        return {"ok": True}

    # For create/update, delegate to service
    try:
        await svc.sync_from_external(user_id, "linear", issue_data)
    except Exception:
        logger.exception(
            "Linear webhook: sync_from_external failed for issue %s",
            issue_data.get("id"),
        )

    return {"ok": True}


# ============================================================================
# Asana Webhooks (PM sync — Phase 44)
# ============================================================================

# Redis key prefix for storing Asana hook secrets (per webhook GID).
_ASANA_HOOK_SECRET_PREFIX = "pikar:asana:hook_secret:"
# Fallback: env-based Asana hook secret when Redis is unavailable.
_ASANA_HOOK_SECRET_ENV = "ASANA_WEBHOOK_SECRET"


async def _store_asana_hook_secret(hook_gid: str, secret: str) -> None:
    """Persist an Asana hook secret in Redis for future verification.

    The secret is set with a 90-day TTL (Asana webhooks expire).

    Args:
        hook_gid: Asana webhook GID (used as part of the key).
        secret: The X-Hook-Secret value to store.
    """
    try:
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        redis_client = await cache._get_redis()
        if redis_client is not None:
            key = f"{_ASANA_HOOK_SECRET_PREFIX}{hook_gid}"
            await redis_client.setex(key, 90 * 24 * 3600, secret)
    except Exception:
        logger.warning("Failed to store Asana hook secret for %s", hook_gid)


async def _get_asana_hook_secret(hook_gid: str) -> str:
    """Retrieve an Asana hook secret from Redis.

    Falls back to the ``ASANA_WEBHOOK_SECRET`` env var when Redis is
    unavailable or the key is missing.

    Args:
        hook_gid: Asana webhook GID.

    Returns:
        The hook secret string, or empty string if not found.
    """
    try:
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        redis_client = await cache._get_redis()
        if redis_client is not None:
            key = f"{_ASANA_HOOK_SECRET_PREFIX}{hook_gid}"
            val = await redis_client.get(key)
            if val is not None:
                return val.decode("utf-8") if isinstance(val, bytes) else str(val)
    except Exception:
        logger.warning("Failed to read Asana hook secret for %s", hook_gid)

    # Fallback to env var
    return os.environ.get(_ASANA_HOOK_SECRET_ENV, "")


async def _resolve_asana_user(webhook_gid: str) -> str | None:
    """Resolve user_id from integration_sync_state for an Asana webhook GID.

    During webhook registration, the GID is stored in sync_cursor metadata.
    We scan all Asana sync states to find the matching GID.

    Args:
        webhook_gid: Asana webhook GID from the request.

    Returns:
        User UUID string, or ``None`` if no match found.
    """
    client = get_service_client()
    result = await execute_async(
        client.table("integration_sync_state")
        .select("user_id, sync_cursor")
        .eq("provider", "asana"),
        op_name="webhooks.asana.resolve_user",
    )
    if not result.data:
        return None

    for row in result.data:
        cursor = row.get("sync_cursor") or {}
        webhook_gids: list[str] = cursor.get("webhook_gids", [])
        if webhook_gid in webhook_gids:
            return row["user_id"]

    # Fallback: single-user mode
    return result.data[0]["user_id"]


@router.post("/asana")
async def asana_webhook(request: Request) -> Response:
    """Receive and process Asana webhook events for PM sync.

    **Handshake:** When Asana first registers a webhook it sends a POST
    with an ``X-Hook-Secret`` header.  We echo it back in the response
    header and store it in Redis for future HMAC verification.

    **Events:** Subsequent POSTs carry a JSON body with an ``events``
    array.  We verify the ``X-Hook-Signature`` header, then process
    task change events via ``PMSyncService.sync_from_external``.

    Returns:
        200 response (with ``X-Hook-Secret`` echo during handshake).

    Raises:
        HTTPException: 403 if signature is invalid on events payload.
    """
    body = await request.body()

    # Asana webhook handshake — echo back X-Hook-Secret
    hook_secret_header = request.headers.get("X-Hook-Secret", "")
    if hook_secret_header:
        # Derive a pseudo GID from the request URL query or use a fixed key
        hook_gid = request.query_params.get("gid", "default")
        await _store_asana_hook_secret(hook_gid, hook_secret_header)
        logger.info(
            "Asana webhook handshake received — echoing X-Hook-Secret (gid=%s)",
            hook_gid,
        )
        return Response(
            content=json.dumps({"ok": True}),
            media_type="application/json",
            status_code=200,
            headers={"X-Hook-Secret": hook_secret_header},
        )

    # Events request — verify signature
    hook_gid = request.query_params.get("gid", "default")
    hook_secret = await _get_asana_hook_secret(hook_gid)

    if not hook_secret:
        logger.error(
            "Asana webhook secret not configured for hook GID %s", hook_gid
        )
        raise HTTPException(
            status_code=500, detail="Webhook secret not configured"
        )

    # Verify HMAC-SHA256 signature (hook_secret is guaranteed non-empty here)
    received_sig = request.headers.get("X-Hook-Signature", "")
    expected_sig = hmac.new(
        hook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    if not received_sig or not hmac.compare_digest(expected_sig, received_sig):
        logger.warning("Asana webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    events: list[dict[str, Any]] = payload.get("events", [])
    if not events:
        return Response(
            content=json.dumps({"ok": True}),
            media_type="application/json",
            status_code=200,
        )

    logger.info("Asana webhook: %d events received", len(events))

    from app.services.pm_sync_service import PMSyncService

    svc = PMSyncService()

    for event in events:
        action = event.get("action", "")
        resource = event.get("resource", {})
        resource_type = resource.get("resource_type", "")
        task_gid = resource.get("gid", "")

        if resource_type != "task" or action not in ("changed", "added"):
            continue

        if not task_gid:
            continue

        # Resolve the user from webhook GID
        user_id = await _resolve_asana_user(hook_gid)
        if not user_id:
            logger.warning("Asana webhook: no user found for hook_gid=%s", hook_gid)
            continue

        # Delegate full task fetch + sync to the service
        try:
            await svc.handle_webhook_event(
                provider="asana",
                event_data={"task_gid": task_gid, "user_id": user_id},
            )
        except Exception:
            logger.exception(
                "Asana webhook: handle_webhook_event failed for task %s", task_gid
            )

    return Response(
        content=json.dumps({"ok": True}),
        media_type="application/json",
        status_code=200,
    )


# ============================================================================
# HubSpot Webhooks (Dedicated — Phase 42)
# ============================================================================


@router.post("/hubspot")
async def hubspot_webhook(request: Request) -> dict[str, Any]:
    """Receive and process HubSpot webhook events.

    HubSpot sends batched events as a JSON array.  Each event is
    routed to the appropriate ``HubSpotService`` handler based on
    the ``subscriptionType`` field.

    Signature verification uses HubSpot's v3 scheme
    (HMAC-SHA256 of method + URL + body + timestamp).

    Returns:
        ``{"status": "processed"}`` on success.

    Raises:
        HTTPException: 403 if signature is invalid, 500 if secret
            is not configured.
    """
    hubspot_secret = os.environ.get("HUBSPOT_CLIENT_SECRET", "")
    if not hubspot_secret:
        logger.error("HUBSPOT_CLIENT_SECRET not configured")
        raise HTTPException(
            status_code=500,
            detail="HubSpot webhook secret not configured",
        )

    # Read raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-HubSpot-Signature-v3", "")
    timestamp = request.headers.get("X-HubSpot-Request-Timestamp", "")

    # Reconstruct the URL as HubSpot sees it
    request_url = str(request.url)

    if not _verify_hubspot_signature_v3(
        body=body,
        method=request.method,
        url=request_url,
        timestamp=timestamp,
        secret=hubspot_secret,
        signature=signature,
    ):
        logger.warning("HubSpot webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload — HubSpot sends a JSON array of events
    try:
        events = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(events, list):
        events = [events]

    processed = 0
    for event in events:
        subscription_type = event.get("subscriptionType", "")
        portal_id = str(event.get("portalId", ""))

        # Resolve user from portal ID
        user_id = await _resolve_hubspot_user(portal_id)
        if not user_id:
            logger.warning(
                "HubSpot webhook: no user for portal %s, skipping",
                portal_id,
            )
            continue

        # Route to appropriate handler
        from app.services.hubspot_service import HubSpotService

        svc = HubSpotService()

        if subscription_type.startswith("contact."):
            await svc.handle_contact_webhook(user_id, event)
            processed += 1
        elif subscription_type.startswith("deal."):
            await svc.handle_deal_webhook(user_id, event)
            processed += 1
        else:
            logger.info("HubSpot webhook: unhandled type %s", subscription_type)

    return {"status": "processed", "events_processed": processed}


# ============================================================================
# Slack Interactive Components (Phase 45 — Approval Buttons)
# ============================================================================

_SLACK_RESPONSE_URL_ALLOWLIST = frozenset({
    "hooks.slack.com",
    "api.slack.com",
})


def _is_valid_slack_response_url(url: str) -> bool:
    """Validate that a Slack response_url points to a known Slack domain.

    Prevents SSRF by ensuring outbound POSTs only reach Slack infrastructure.
    Requires HTTPS and exact domain match (no subdomain spoofing).

    Args:
        url: The response_url value from the Slack interaction payload.

    Returns:
        True if the URL is safe to POST to, False otherwise.

    """
    if not url:
        return False
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        hostname = parsed.hostname or ""
        # Check exact domain match or *.slack.com subdomain
        return hostname in _SLACK_RESPONSE_URL_ALLOWLIST or (
            hostname.endswith(".slack.com") and not hostname.endswith("..slack.com")
        )
    except Exception:
        return False


async def _process_slack_block_action(payload: dict[str, Any]) -> None:
    """Process a Slack block_actions payload asynchronously.

    Extracts the approval action from the button value, updates the
    ``approval_requests`` row, then posts a confirmation message back to
    Slack via the ``response_url``.

    Args:
        payload: Parsed Slack interaction payload (type ``block_actions``).

    """
    try:
        action = payload["actions"][0]
        value: str = action.get("value", "")
        # Value format: "APPROVED:<plain_token>" or "REJECTED:<plain_token>"
        parts = value.split(":", 1)
        if len(parts) != 2:  # noqa: PLR2004
            logger.warning("Slack interact: unexpected action value format: %s", value)
            return

        status_str, token = parts[0], parts[1]
        # Map button value prefix to DB status
        status = "APPROVED" if status_str.upper() == "APPROVED" else "REJECTED"

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user_info = payload.get("user", {})
        user_name = user_info.get("name") or user_info.get("username", "someone")
        response_url: str = payload.get("response_url", "")

        # Update approval_requests via service-role client
        client = get_service_client()
        result = await execute_async(
            client.table("approval_requests")
            .update({"status": status, "resolved_at": "now()"})
            .eq("token", token_hash)
            .eq("status", "PENDING"),
            op_name="approvals.slack_interact.resolve",
        )
        rows: list[dict[str, Any]] = result.data or []
        row_updated = bool(rows)

        if not response_url:
            logger.debug("Slack interact: no response_url, skipping confirmation post")
            return

        if not _is_valid_slack_response_url(response_url):
            logger.warning(
                "Slack interact: rejected response_url with non-Slack domain: %s",
                response_url[:200],
            )
            return

        # Build confirmation message
        if row_updated:
            verb = "Approved" if status == "APPROVED" else "Rejected"
            confirmation_text = f"{verb} by {user_name}"
            color = "#36a64f" if status == "APPROVED" else "#cc0000"
        else:
            confirmation_text = (
                "This approval has already been processed or has expired"
            )
            color = "#888888"

        message = {
            "replace_original": True,
            "attachments": [
                {
                    "color": color,
                    "text": confirmation_text,
                }
            ],
        }

        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.post(
                response_url,
                json=message,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:  # noqa: PLR2004
                logger.warning(
                    "Slack response_url returned %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )

    except Exception:
        logger.exception("Error processing Slack block_actions payload")


@router.post("/slack/interact")
async def slack_interact(request: Request) -> JSONResponse:
    """Receive and process Slack interactive component payloads.

    Verifies the Slack request signature using ``SLACK_SIGNING_SECRET``
    before processing any payload.  For ``block_actions`` payloads, the
    approval is resolved and a confirmation message posted back to Slack
    via the ``response_url``.

    The endpoint returns ``{"ok": True}`` immediately; the DB update and
    Slack confirmation are performed in a background ``asyncio.Task`` so
    the response is always delivered within Slack's 3-second window.

    Returns:
        ``{"ok": True}`` on successful signature verification.

    Raises:
        HTTPException: 403 if the signature is invalid or
            ``SLACK_SIGNING_SECRET`` is not configured.

    """
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        logger.error("SLACK_SIGNING_SECRET not configured — rejecting interact request")
        raise HTTPException(
            status_code=403,
            detail="Slack signing secret not configured",
        )

    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Verify signature using slack_sdk
    try:
        from slack_sdk.signature import SignatureVerifier

        verifier = SignatureVerifier(signing_secret)
        if not verifier.is_valid(body.decode(), timestamp, signature):
            logger.warning("Slack interact: signature verification failed")
            raise HTTPException(status_code=403, detail="Invalid Slack signature")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Slack interact: error during signature verification")
        raise HTTPException(
            status_code=403,
            detail="Signature verification error",
        ) from exc

    # Parse form-encoded payload
    try:
        form = await request.form()
        payload = json.loads(form["payload"])
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid payload format",
        ) from exc

    # Dispatch processing in background — respond immediately to beat 3s timeout
    if payload.get("type") == "block_actions":
        asyncio.create_task(_process_slack_block_action(payload))

    return JSONResponse(content={"ok": True})
