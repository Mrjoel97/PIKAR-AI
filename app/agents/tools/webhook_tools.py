# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Agent tools for outbound webhook management.

Provides thin, agent-callable wrappers around the webhook_endpoints and
webhook_deliveries tables so that OperationsAgent can manage webhooks via
natural-language chat commands.

Exported list::

    WEBHOOK_TOOLS = [
        list_webhook_endpoints,
        create_webhook_endpoint,
        delete_webhook_endpoint,
        list_webhook_events,
        get_webhook_delivery_log,
    ]

Pattern matches COMMUNICATION_TOOLS and PM_TASK_TOOLS — raw function exports,
not FunctionTool wrappers. ``sanitize_tools`` in the agent module handles
wrapping.
"""

from __future__ import annotations

import logging
import secrets

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def list_webhook_endpoints(tool_context) -> dict:
    """List all outbound webhook endpoints registered by the user.

    Queries the ``webhook_endpoints`` table for endpoints owned by the caller.
    Secrets are never returned.

    Args:
        tool_context: ADK tool context — ``tool_context.state["user_id"]`` must
            be set.

    Returns:
        Dict with ``endpoints`` list, each item containing id, url, events,
        active, description, and consecutive_failures.

    """
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    user_id: str = tool_context.state.get("user_id", "")
    client = get_service_client()
    result = await execute_async(
        client.table("webhook_endpoints")
        .select("id, url, events, active, description, consecutive_failures, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True),
        op_name="webhook_tools.list_endpoints",
    )
    # Explicitly drop secret field — never expose it via agent tools
    rows = [{k: v for k, v in row.items() if k != "secret"} for row in (result.data or [])]
    return {"endpoints": rows, "count": len(rows)}


async def create_webhook_endpoint(
    tool_context,
    url: str,
    events: list[str],
    description: str = "",
) -> dict:
    """Create a new outbound webhook endpoint.

    Validates events against the EVENT_CATALOG, generates a signing secret,
    encrypts it for storage, and inserts the row.

    Args:
        tool_context: ADK tool context — ``tool_context.state["user_id"]``
            must be set.
        url: Destination URL that will receive webhook POST requests.
        events: List of event type strings to subscribe to (e.g.
            ``["task.created"]``).  All events must appear in EVENT_CATALOG.
        description: Optional human-readable label for this endpoint.

    Returns:
        Dict with ``endpoint_id``, ``secret`` (plaintext — shown once only),
        and ``message``.  Returns ``{"error": "..."}`` on validation failure.

    """
    from app.models.webhook_events import EVENT_CATALOG
    from app.services.encryption import encrypt_secret
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    # Validate events
    unknown = [e for e in events if e not in EVENT_CATALOG]
    if unknown:
        return {
            "error": (
                f"Unknown event type(s): {', '.join(unknown)}. "
                f"Valid events: {', '.join(EVENT_CATALOG.keys())}"
            )
        }

    user_id: str = tool_context.state.get("user_id", "")
    plaintext_secret = "whsec_" + secrets.token_urlsafe(32)
    encrypted = encrypt_secret(plaintext_secret)

    client = get_service_client()
    result = await execute_async(
        client.table("webhook_endpoints").insert(
            {
                "user_id": user_id,
                "url": url,
                "events": events,
                "secret": encrypted,
                "active": True,
                "description": description,
            }
        ),
        op_name="webhook_tools.create_endpoint",
    )
    rows = result.data or []
    endpoint_id = rows[0]["id"] if rows else None
    return {
        "endpoint_id": endpoint_id,
        "secret": plaintext_secret,
        "message": (
            "Webhook endpoint created. "
            "Store this secret securely — it will not be shown again."
        ),
    }


async def delete_webhook_endpoint(tool_context, endpoint_id: str) -> dict:
    """Delete an outbound webhook endpoint owned by the user.

    Verifies ownership before deleting. Returns an error dict if the endpoint
    does not exist or does not belong to the caller.

    Args:
        tool_context: ADK tool context — ``tool_context.state["user_id"]``
            must be set.
        endpoint_id: UUID of the endpoint to delete.

    Returns:
        Dict with ``deleted=True`` and ``message`` on success, or
        ``{"error": "..."}`` if the endpoint is not found.

    """
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    user_id: str = tool_context.state.get("user_id", "")
    client = get_service_client()

    # Ownership check
    fetch_result = await execute_async(
        client.table("webhook_endpoints")
        .select("id")
        .eq("id", endpoint_id)
        .eq("user_id", user_id)
        .limit(1),
        op_name="webhook_tools.delete_check_ownership",
    )
    if not (fetch_result.data or []):
        return {"error": f"Webhook endpoint '{endpoint_id}' not found or not owned by you."}

    await execute_async(
        client.table("webhook_endpoints")
        .delete()
        .eq("id", endpoint_id)
        .eq("user_id", user_id),
        op_name="webhook_tools.delete_endpoint",
    )
    return {"deleted": True, "message": f"Webhook endpoint {endpoint_id} deleted."}


async def list_webhook_events(tool_context) -> dict:  # noqa: ARG001
    """List available webhook event types with descriptions.

    Returns the EVENT_CATALOG summary suitable for chat display — event_type
    and description only (no full JSON schema).

    Args:
        tool_context: ADK tool context (unused — catalog is static).

    Returns:
        Dict with ``events`` list of ``{event_type, description}`` dicts.

    """
    from app.models.webhook_events import EVENT_CATALOG

    events = [
        {"event_type": k, "description": v["description"]}
        for k, v in EVENT_CATALOG.items()
    ]
    return {"events": events, "count": len(events)}


async def get_webhook_delivery_log(
    tool_context,
    endpoint_id: str,
    limit: int = 20,
) -> dict:
    """Retrieve recent delivery attempts for a webhook endpoint.

    Verifies that the caller owns the endpoint before returning delivery data.

    Args:
        tool_context: ADK tool context — ``tool_context.state["user_id"]``
            must be set.
        endpoint_id: UUID of the endpoint whose deliveries to retrieve.
        limit: Maximum number of rows to return (default 20).

    Returns:
        Dict with ``deliveries`` list, each item containing event_type, status,
        attempts, response_code, and created_at.  Returns ``{"error": "..."}``
        if the endpoint is not found or not owned.

    """
    from app.services.supabase import get_service_client
    from app.services.supabase_async import execute_async

    user_id: str = tool_context.state.get("user_id", "")
    client = get_service_client()

    # Ownership check
    fetch_ep = await execute_async(
        client.table("webhook_endpoints")
        .select("id")
        .eq("id", endpoint_id)
        .eq("user_id", user_id)
        .limit(1),
        op_name="webhook_tools.delivery_log_check_ownership",
    )
    if not (fetch_ep.data or []):
        return {"error": f"Webhook endpoint '{endpoint_id}' not found or not owned by you."}

    fetch_del = await execute_async(
        client.table("webhook_deliveries")
        .select("event_type, status, attempts, response_code, created_at")
        .eq("endpoint_id", endpoint_id)
        .order("created_at", desc=True)
        .limit(limit),
        op_name="webhook_tools.delivery_log_fetch",
    )
    rows = fetch_del.data or []
    return {"deliveries": rows, "count": len(rows), "endpoint_id": endpoint_id}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

WEBHOOK_TOOLS = [
    list_webhook_endpoints,
    create_webhook_endpoint,
    delete_webhook_endpoint,
    list_webhook_events,
    get_webhook_delivery_log,
]
