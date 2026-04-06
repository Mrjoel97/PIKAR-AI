# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Outbound webhook management endpoints.

Provides REST endpoints for creating, listing, updating, and deleting
outbound webhook endpoint configurations. Also exposes the event catalog
and delivery log for each endpoint.

All tiers have access to outbound webhooks — no feature gate applied.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.webhook_events import EVENT_CATALOG
from app.routers.onboarding import get_current_user_id
from app.services.encryption import decrypt_secret, encrypt_secret
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outbound-webhooks", tags=["Outbound Webhooks"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateEndpointRequest(BaseModel):
    """Request body for creating a new webhook endpoint."""

    url: str
    events: list[str]
    description: str | None = None


class UpdateEndpointRequest(BaseModel):
    """Request body for updating a webhook endpoint. All fields optional."""

    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_secret(plaintext: str) -> str:
    """Return masked secret preview: whsec_...{last4}.

    Args:
        plaintext: Decrypted secret string.

    Returns:
        Masked preview string.
    """
    return f"whsec_...{plaintext[-4:]}"


def _build_endpoint_response(row: dict, *, include_secret: str | None = None) -> dict:
    """Build endpoint response dict from a DB row.

    Args:
        row: webhook_endpoints DB row.
        include_secret: If provided, mask from this plaintext (create only).

    Returns:
        Response dict with secret_preview, never full secret.
    """
    result: dict[str, Any] = {
        "id": row["id"],
        "url": row["url"],
        "events": row["events"],
        "active": row["active"],
        "description": row.get("description"),
        "consecutive_failures": row.get("consecutive_failures", 0),
        "created_at": row.get("created_at"),
    }
    if include_secret is not None:
        result["secret_preview"] = _mask_secret(include_secret)
    else:
        try:
            plaintext = decrypt_secret(row["secret"])
            result["secret_preview"] = _mask_secret(plaintext)
        except Exception:
            result["secret_preview"] = "whsec_...????"
    return result


# ---------------------------------------------------------------------------
# Endpoint functions (called directly in tests; registered as HTTP routes below)
# ---------------------------------------------------------------------------


async def create_endpoint(
    req: CreateEndpointRequest,
    user_id: str,
) -> dict:
    """Create a new webhook endpoint and return it with the plaintext secret.

    Args:
        req: Create request with url, events, optional description.
        user_id: Authenticated user ID from JWT.

    Returns:
        Dict with endpoint details and one-time plaintext secret.

    Raises:
        HTTPException: 422 if any event type is unknown.
    """
    unknown = [e for e in req.events if e not in EVENT_CATALOG]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown event types: {unknown}. Valid: {list(EVENT_CATALOG.keys())}",
        )

    plaintext_secret = "whsec_" + secrets.token_urlsafe(32)
    encrypted = encrypt_secret(plaintext_secret)

    client = get_service_client()
    row_data: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "url": req.url,
        "secret": encrypted,
        "events": req.events,
        "active": True,
        "consecutive_failures": 0,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    if req.description is not None:
        row_data["description"] = req.description

    result = await execute_async(
        client.table("webhook_endpoints").insert(row_data),
        op_name="webhook.endpoint.create",
    )

    created_row = (result.data or [row_data])[0]
    return {
        "secret": plaintext_secret,
        "endpoint": _build_endpoint_response(
            created_row, include_secret=plaintext_secret
        ),
    }


async def list_endpoints(user_id: str) -> list[dict]:
    """List all webhook endpoints for the authenticated user.

    Args:
        user_id: Authenticated user ID.

    Returns:
        List of endpoint response dicts with masked secrets.
    """
    client = get_service_client()
    result = await execute_async(
        client.table("webhook_endpoints").select("*").eq("user_id", user_id),
        op_name="webhook.endpoint.list",
    )
    rows = result.data or []
    return [_build_endpoint_response(row) for row in rows]


async def update_endpoint(
    endpoint_id: str,
    req: UpdateEndpointRequest,
    user_id: str,
) -> dict:
    """Update a webhook endpoint owned by the authenticated user.

    Args:
        endpoint_id: UUID of the endpoint to update.
        req: Update request with optional fields.
        user_id: Authenticated user ID.

    Returns:
        Updated endpoint response dict.

    Raises:
        HTTPException: 404 if endpoint not found or not owned by user.
        HTTPException: 422 if unknown event types provided.
    """
    client = get_service_client()

    fetch_result = await execute_async(
        client.table("webhook_endpoints")
        .select("*")
        .eq("id", endpoint_id)
        .eq("user_id", user_id),
        op_name="webhook.endpoint.fetch_for_update",
    )
    if not fetch_result.data:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    if req.events is not None:
        unknown = [e for e in req.events if e not in EVENT_CATALOG]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown event types: {unknown}",
            )

    updates: dict[str, Any] = {"updated_at": datetime.now(tz=timezone.utc).isoformat()}
    if req.url is not None:
        updates["url"] = req.url
    if req.events is not None:
        updates["events"] = req.events
    if req.active is not None:
        updates["active"] = req.active
    if req.description is not None:
        updates["description"] = req.description

    update_result = await execute_async(
        client.table("webhook_endpoints").update(updates).eq("id", endpoint_id),
        op_name="webhook.endpoint.update",
    )

    merged = {**fetch_result.data[0], **updates}
    if update_result.data:
        merged = update_result.data[0]
    return _build_endpoint_response(merged)


async def delete_endpoint(endpoint_id: str, user_id: str) -> dict:
    """Delete a webhook endpoint owned by the authenticated user.

    Args:
        endpoint_id: UUID of the endpoint to delete.
        user_id: Authenticated user ID.

    Returns:
        Dict with deleted=True.

    Raises:
        HTTPException: 404 if endpoint not found or not owned by user.
    """
    client = get_service_client()

    fetch_result = await execute_async(
        client.table("webhook_endpoints")
        .select("id")
        .eq("id", endpoint_id)
        .eq("user_id", user_id),
        op_name="webhook.endpoint.fetch_for_delete",
    )
    if not fetch_result.data:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    await execute_async(
        client.table("webhook_endpoints").delete().eq("id", endpoint_id),
        op_name="webhook.endpoint.delete",
    )

    return {"deleted": True, "id": endpoint_id}


def get_events() -> list[dict]:
    """Return the event catalog as a list of event type dicts.

    Returns:
        List of dicts with event_type, description, schema keys.
    """
    return [
        {
            "event_type": event_type,
            "description": meta["description"],
            "schema": meta["payload_schema"],
        }
        for event_type, meta in EVENT_CATALOG.items()
    ]


async def get_deliveries(
    endpoint_id: str,
    user_id: str,
    limit: int,
    offset: int,
) -> list[dict]:
    """Return delivery logs for an endpoint owned by the authenticated user.

    Args:
        endpoint_id: UUID of the endpoint.
        user_id: Authenticated user ID.
        limit: Maximum rows to return.
        offset: Row offset for pagination.

    Returns:
        List of delivery log dicts.

    Raises:
        HTTPException: 404 if endpoint not found or not owned by user.
    """
    client = get_service_client()

    fetch_result = await execute_async(
        client.table("webhook_endpoints")
        .select("id")
        .eq("id", endpoint_id)
        .eq("user_id", user_id),
        op_name="webhook.endpoint.fetch_for_deliveries",
    )
    if not fetch_result.data:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    deliveries_result = await execute_async(
        client.table("webhook_deliveries")
        .select(
            "id, endpoint_id, event_type, status, attempts, response_code, created_at"
        )
        .eq("endpoint_id", endpoint_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1),
        op_name="webhook.endpoint.list_deliveries",
    )

    return deliveries_result.data or []


async def test_send(endpoint_id: str, user_id: str) -> dict:
    """Enqueue a synthetic test delivery for the endpoint.

    Inserts a single webhook_deliveries row using the first event type
    in the endpoint's events list and a synthetic payload derived from
    the event schema.

    Args:
        endpoint_id: UUID of the endpoint to test.
        user_id: Authenticated user ID.

    Returns:
        Dict with queued=True and the delivery row ID.

    Raises:
        HTTPException: 404 if endpoint not found or not owned by user.
    """
    client = get_service_client()

    fetch_result = await execute_async(
        client.table("webhook_endpoints")
        .select("*")
        .eq("id", endpoint_id)
        .eq("user_id", user_id),
        op_name="webhook.endpoint.fetch_for_test",
    )
    if not fetch_result.data:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    endpoint = fetch_result.data[0]
    events = endpoint.get("events") or []
    event_type = events[0] if events else next(iter(EVENT_CATALOG))

    catalog_entry = EVENT_CATALOG.get(event_type, {})
    schema = catalog_entry.get("payload_schema", {})
    required_fields = schema.get("required", [])
    synthetic_payload: dict[str, Any] = {
        field: f"test-{field}" for field in required_fields
    }
    synthetic_payload["_test"] = True

    delivery_row: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "endpoint_id": endpoint_id,
        "event_type": event_type,
        "payload": synthetic_payload,
        "status": "pending",
        "attempts": 0,
        "next_retry_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    insert_result = await execute_async(
        client.table("webhook_deliveries").insert(delivery_row),
        op_name="webhook.endpoint.test_send",
    )

    inserted_id = delivery_row["id"]
    if insert_result.data:
        inserted_id = insert_result.data[0].get("id", inserted_id)

    logger.info(
        "Test webhook delivery %s enqueued for endpoint %s", inserted_id, endpoint_id
    )
    return {"queued": True, "delivery_id": inserted_id}


# ---------------------------------------------------------------------------
# HTTP route registration
# ---------------------------------------------------------------------------


@router.post("/endpoints", status_code=201)
async def _create_endpoint_route(
    req: CreateEndpointRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Create a new outbound webhook endpoint.

    Returns the endpoint details plus the plaintext signing secret exactly once.
    Store it securely — it will not be shown again.
    """
    return await create_endpoint(req, user_id=user_id)


@router.get("/endpoints")
async def _list_endpoints_route(
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list[dict]:
    """List all outbound webhook endpoints for the authenticated user."""
    return await list_endpoints(user_id=user_id)


@router.patch("/endpoints/{endpoint_id}")
async def _update_endpoint_route(
    endpoint_id: str,
    req: UpdateEndpointRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Update an outbound webhook endpoint."""
    return await update_endpoint(endpoint_id=endpoint_id, req=req, user_id=user_id)


@router.delete("/endpoints/{endpoint_id}")
async def _delete_endpoint_route(
    endpoint_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Delete an outbound webhook endpoint."""
    return await delete_endpoint(endpoint_id=endpoint_id, user_id=user_id)


@router.get("/events")
def _get_events_route() -> list[dict]:
    """Return the full event catalog with descriptions and payload schemas."""
    return get_events()


@router.get("/endpoints/{endpoint_id}/deliveries")
async def _get_deliveries_route(
    endpoint_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """Return paginated delivery logs for an endpoint."""
    return await get_deliveries(
        endpoint_id=endpoint_id, user_id=user_id, limit=limit, offset=offset
    )


@router.post("/endpoints/{endpoint_id}/test", status_code=202)
async def _test_send_route(
    endpoint_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Enqueue a synthetic test delivery for the endpoint."""
    return await test_send(endpoint_id=endpoint_id, user_id=user_id)
