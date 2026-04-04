# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""HubSpot CRM agent tools -- contacts, deals, and deal context.

Provides five agent-callable functions that wire into the HubSpotService
created in Phase 42 Plan 01.  Tools extract the current user from request
context and return structured dicts for the agent.

The ``get_hubspot_deal_context`` tool is especially important: agents
should call it **before** answering any sales question about a specific
contact or company so their response includes real pipeline data.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


# ---------------------------------------------------------------------------
# Tool: search_hubspot_contacts
# ---------------------------------------------------------------------------


async def search_hubspot_contacts(query: str) -> dict[str, Any]:
    """Search HubSpot contacts by name, email, or company.

    Args:
        query: Search string matched against name, email, and company.

    Returns:
        Dict with contacts list and count.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.hubspot_service import HubSpotService

    svc = HubSpotService()

    try:
        contacts = await svc.search_contacts(user_id, query)
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as exc:
        logger.exception("search_hubspot_contacts failed for user=%s", user_id)
        return {"error": f"Failed to search HubSpot contacts: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_hubspot_deal_context
# ---------------------------------------------------------------------------


async def get_hubspot_deal_context(
    contact_name_or_id: str,
) -> dict[str, Any]:
    """Get HubSpot deal pipeline context for a contact.

    Use this BEFORE answering any sales query about a specific contact
    or company to provide CRM-aware responses.  Returns the contact
    record, associated deals with stage/amount/pipeline, and a
    human-readable summary.

    Args:
        contact_name_or_id: Contact name, email, or UUID to look up.

    Returns:
        Dict with contact, deals, and summary keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.hubspot_service import HubSpotService

    svc = HubSpotService()

    try:
        return await svc.get_deal_context(user_id, contact_name_or_id)
    except Exception as exc:
        logger.exception("get_hubspot_deal_context failed for user=%s", user_id)
        return {"error": f"Failed to get deal context: {exc}"}


# ---------------------------------------------------------------------------
# Tool: create_hubspot_contact
# ---------------------------------------------------------------------------


async def create_hubspot_contact(
    email: str,
    name: str,
    company: str | None = None,
    phone: str | None = None,
) -> dict[str, Any]:
    """Create a new contact in HubSpot CRM.

    Creates the contact in the Pikar contacts table first, then pushes
    to HubSpot so it gets a ``hubspot_contact_id`` back.

    Args:
        email: Contact email address.
        name: Contact full name.
        company: Optional company name.
        phone: Optional phone number.

    Returns:
        Dict with contact data and hubspot_id, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.base_service import AdminService
    from app.services.hubspot_service import HubSpotService
    from app.services.supabase_async import execute_async

    admin = AdminService()

    try:
        # Create in Pikar contacts table
        row: dict[str, Any] = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "source": "manual",
        }
        if company:
            row["company"] = company
        if phone:
            row["phone"] = phone

        result = await execute_async(
            admin.client.table("contacts").insert(row),
            op_name="hubspot_tools.create_contact",
        )
        contact = result.data[0]

        # Push to HubSpot (creates in HubSpot and stores hubspot_contact_id)
        svc = HubSpotService()
        push_result = await svc.push_contact_to_hubspot(user_id, contact["id"])

        return {
            "contact": contact,
            "hubspot_id": push_result.get("hubspot_contact_id"),
            "action": push_result.get("action", "created"),
        }
    except Exception as exc:
        logger.exception("create_hubspot_contact failed for user=%s", user_id)
        return {"error": f"Failed to create HubSpot contact: {exc}"}


# ---------------------------------------------------------------------------
# Tool: update_hubspot_deal
# ---------------------------------------------------------------------------


async def update_hubspot_deal(
    deal_id: str,
    stage: str | None = None,
    amount: float | None = None,
    close_date: str | None = None,
) -> dict[str, Any]:
    """Update a HubSpot deal's stage, amount, or close date.

    Args:
        deal_id: Pikar hubspot_deals row UUID.
        stage: New deal stage (e.g. 'qualifiedtobuy', 'closedwon').
        amount: New deal amount in dollars.
        close_date: New close date as ISO-8601 string.

    Returns:
        Dict with updated deal info, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.hubspot_service import HubSpotService

    svc = HubSpotService()

    try:
        # Build properties dict from non-None params
        properties: dict[str, Any] = {}
        if stage is not None:
            properties["dealstage"] = stage
        if amount is not None:
            properties["amount"] = str(amount)
        if close_date is not None:
            properties["closedate"] = close_date

        if not properties:
            return {
                "error": "No properties to update. "
                "Provide at least one of: stage, amount, close_date.",
            }

        result = await svc.push_deal_to_hubspot(user_id, deal_id, properties)
        return {
            "deal_id": deal_id,
            "hubspot_deal_id": result.get("hubspot_deal_id"),
            "status": result.get("status", "updated"),
            "updated_properties": list(properties.keys()),
        }
    except Exception as exc:
        logger.exception("update_hubspot_deal failed for user=%s", user_id)
        return {"error": f"Failed to update HubSpot deal: {exc}"}


# ---------------------------------------------------------------------------
# Tool: list_hubspot_deals
# ---------------------------------------------------------------------------


async def list_hubspot_deals(
    pipeline: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    """List HubSpot deals with optional pipeline and stage filters.

    Args:
        pipeline: Optional pipeline name filter.
        stage: Optional deal stage filter.

    Returns:
        Dict with deals list, count, and total_value.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.base_service import AdminService
    from app.services.supabase_async import execute_async

    admin = AdminService()

    try:
        query = (
            admin.client.table("hubspot_deals")
            .select("*")
            .eq("user_id", user_id)
        )
        if pipeline:
            query = query.eq("pipeline", pipeline)
        if stage:
            query = query.eq("stage", stage)

        result = await execute_async(
            query.order("created_at", desc=True),
            op_name="hubspot_tools.list_deals",
        )
        deals = result.data or []

        total_value = sum(
            float(d.get("amount") or 0) for d in deals
        )
        return {
            "deals": deals,
            "count": len(deals),
            "total_value": round(total_value, 2),
        }
    except Exception as exc:
        logger.exception("list_hubspot_deals failed for user=%s", user_id)
        return {"error": f"Failed to list HubSpot deals: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

HUBSPOT_TOOLS = [
    search_hubspot_contacts,
    get_hubspot_deal_context,
    create_hubspot_contact,
    update_hubspot_deal,
    list_hubspot_deals,
]
