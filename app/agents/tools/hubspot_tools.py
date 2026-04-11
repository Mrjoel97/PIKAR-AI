# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""HubSpot CRM agent tools -- contacts, deals, and deal context.

Provides eight agent-callable functions that wire into the HubSpotService
created in Phase 42 Plan 01.  Tools extract the current user from request
context and return structured dicts for the agent.

The ``get_hubspot_deal_context`` tool is especially important: agents
should call it **before** answering any sales question about a specific
contact or company so their response includes real pipeline data.

Phase 62 Plan 04 adds three real tools:
- ``score_hubspot_lead``: pushes lead scores to HubSpot (replaces degraded score_lead)
- ``query_hubspot_crm``: real CRM queries with filters (replaces degraded query_crm)
- ``sync_deal_notes``: auto-syncs deal notes/stage to HubSpot after conversations
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Module-level imports so tests can patch them via
# ``patch("app.agents.tools.hubspot_tools.HubSpotService")``,
# ``patch("app.agents.tools.hubspot_tools.AdminService")``, and
# ``patch("app.agents.tools.hubspot_tools._execute_async_query")``.
try:
    from app.services.hubspot_service import HubSpotService
except ImportError:  # pragma: no cover — SDK not installed in test env
    HubSpotService = None  # type: ignore[assignment,misc]

try:
    from app.services.base_service import AdminService
except ImportError:  # pragma: no cover
    AdminService = None  # type: ignore[assignment,misc]

try:
    from app.services.supabase_async import execute_async as _execute_async_query
except ImportError:  # pragma: no cover
    _execute_async_query = None  # type: ignore[assignment]


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
        query = admin.client.table("hubspot_deals").select("*").eq("user_id", user_id)
        if pipeline:
            query = query.eq("pipeline", pipeline)
        if stage:
            query = query.eq("stage", stage)

        result = await execute_async(
            query.order("created_at", desc=True),
            op_name="hubspot_tools.list_deals",
        )
        deals = result.data or []

        total_value = sum(float(d.get("amount") or 0) for d in deals)
        return {
            "deals": deals,
            "count": len(deals),
            "total_value": round(total_value, 2),
        }
    except Exception as exc:
        logger.exception("list_hubspot_deals failed for user=%s", user_id)
        return {"error": f"Failed to list HubSpot deals: {exc}"}


# ---------------------------------------------------------------------------
# Tool: score_hubspot_lead  (Phase 62: replaces degraded score_lead)
# ---------------------------------------------------------------------------


async def score_hubspot_lead(
    contact_name_or_email: str,
    score: int,
    framework: str = "BANT",
    qualification_notes: str = "",
) -> dict[str, Any]:
    """Score a lead and push the score to HubSpot CRM.

    Looks up the contact locally by name or email.  If HubSpot is
    connected and the contact has a ``hubspot_contact_id``, the score is
    pushed to HubSpot contact properties (``hs_lead_status`` and
    ``pikar_lead_score``).  Falls back to local-only scoring when HubSpot
    is not connected.

    The score is always logged as a ``lead_scored`` activity in the
    ``contact_activities`` table.

    Args:
        contact_name_or_email: Contact name or email address to look up.
        score: Lead score 0-100.
        framework: Scoring framework used (BANT, MEDDIC, CHAMP).
        qualification_notes: Optional notes from the qualification session.

    Returns:
        Dict with ``success``, ``contact``, ``score``, and
        ``synced_to_hubspot`` keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    admin = AdminService()

    # Look up contact by name or email
    try:
        contact_result = await _execute_async_query(
            admin.client.table("contacts")
            .select(
                "id, name, email, company, lifecycle_stage, hubspot_contact_id, metadata"
            )
            .eq("user_id", user_id)
            .or_(
                f"name.ilike.%{contact_name_or_email}%,"
                f"email.ilike.%{contact_name_or_email}%"
            )
            .limit(1),
            op_name="hubspot_tools.score_lead.find_contact",
        )
    except Exception as exc:
        logger.exception("score_hubspot_lead: contact lookup failed")
        return {"error": f"Failed to find contact: {exc}"}

    if not contact_result.data:
        return {
            "error": f"No contact found matching '{contact_name_or_email}'",
        }

    contact = contact_result.data[0]
    contact_id = contact["id"]

    synced_to_hubspot = False
    hubspot_contact_id = contact.get("hubspot_contact_id")

    if hubspot_contact_id:
        try:
            svc = HubSpotService()
            await svc.update_contact_score(
                user_id=user_id,
                contact_id=contact_id,
                score=score,
                qualification_data={
                    "framework": framework,
                    "notes": qualification_notes,
                },
            )
            synced_to_hubspot = True
        except Exception as exc:
            logger.warning(
                "score_hubspot_lead: HubSpot push failed for contact=%s, "
                "falling back to local-only: %s",
                contact_id,
                exc,
            )

    # Log activity in contact_activities table
    try:
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        await _execute_async_query(
            admin.client.table("contact_activities").insert(
                {
                    "contact_id": contact_id,
                    "user_id": user_id,
                    "activity_type": "lead_scored",
                    "notes": (
                        f"Score: {score}/100 | Framework: {framework}"
                        + (f" | {qualification_notes}" if qualification_notes else "")
                    ),
                    "activity_date": now_iso,
                    "metadata": {
                        "score": score,
                        "framework": framework,
                        "synced_to_hubspot": synced_to_hubspot,
                    },
                }
            ),
            op_name="hubspot_tools.score_lead.log_activity",
        )
    except Exception:
        logger.warning(
            "score_hubspot_lead: failed to log activity for contact=%s", contact_id
        )

    return {
        "success": True,
        "contact": {
            "id": contact_id,
            "name": contact.get("name"),
            "email": contact.get("email"),
            "company": contact.get("company"),
            "lifecycle_stage": contact.get("lifecycle_stage"),
        },
        "score": score,
        "framework": framework,
        "synced_to_hubspot": synced_to_hubspot,
    }


# ---------------------------------------------------------------------------
# Tool: query_hubspot_crm  (Phase 62: replaces degraded query_crm)
# ---------------------------------------------------------------------------


async def query_hubspot_crm(
    query_type: str = "contacts",
    lifecycle_stage: str | None = None,
    source: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Query real CRM data from the local contacts or deals tables.

    Returns contacts or deals with optional filtering by lifecycle stage,
    source, pipeline, and stage.  Includes aggregations: total count and
    per-stage breakdown.  For deals, total value is also calculated.

    Args:
        query_type: Either ``"contacts"`` or ``"deals"``.
        lifecycle_stage: Optional lifecycle stage filter for contacts
            (e.g. ``"lead"``, ``"qualified"``, ``"customer"``).
        source: Optional source filter for contacts
            (e.g. ``"inbound"``, ``"referral"``).
        limit: Maximum number of records to return (default 50).

    Returns:
        Dict with ``success``, ``results``, ``count``, and
        ``aggregations`` keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    admin = AdminService()

    try:
        if query_type == "deals":
            query = (
                admin.client.table("hubspot_deals").select("*").eq("user_id", user_id)
            )
            if source:
                query = query.eq("pipeline", source)

            result = await _execute_async_query(
                query.order("created_at", desc=True).limit(limit),
                op_name="hubspot_tools.query_crm.deals",
            )
            records = result.data or []

            # Aggregations for deals
            total_value = sum(float(d.get("amount") or 0) for d in records)
            stage_breakdown: dict[str, int] = {}
            for d in records:
                stage = d.get("stage") or "unknown"
                stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

            return {
                "success": True,
                "results": records,
                "count": len(records),
                "aggregations": {
                    "total_value": round(total_value, 2),
                    "by_stage": stage_breakdown,
                },
            }

        else:
            # Default: contacts
            query = (
                admin.client.table("contacts")
                .select(
                    "id, name, email, company, phone, lifecycle_stage, "
                    "source, hubspot_contact_id, created_at"
                )
                .eq("user_id", user_id)
            )
            if lifecycle_stage:
                query = query.eq("lifecycle_stage", lifecycle_stage)
            if source:
                query = query.eq("source", source)

            result = await _execute_async_query(
                query.order("created_at", desc=True).limit(limit),
                op_name="hubspot_tools.query_crm.contacts",
            )
            records = result.data or []

            # Aggregations for contacts
            stage_breakdown = {}
            for c in records:
                stage = c.get("lifecycle_stage") or "unknown"
                stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

            return {
                "success": True,
                "results": records,
                "count": len(records),
                "aggregations": {
                    "by_lifecycle_stage": stage_breakdown,
                },
            }

    except Exception as exc:
        logger.exception("query_hubspot_crm failed for user=%s", user_id)
        return {"error": f"Failed to query CRM: {exc}"}


# ---------------------------------------------------------------------------
# Tool: sync_deal_notes  (Phase 62: auto-sync deal notes after conversations)
# ---------------------------------------------------------------------------


async def sync_deal_notes(
    deal_name_or_id: str,
    notes: str,
    next_steps: list[str] | None = None,
    stage_change: str | None = None,
) -> dict[str, Any]:
    """Push conversation notes and optional stage change to a HubSpot deal.

    After any sales conversation about a deal, call this tool to log the
    discussion notes and next steps.  If HubSpot is connected, a note
    engagement is created and any stage change is pushed to HubSpot.
    If HubSpot is not connected, the notes are stored in the local
    ``hubspot_deals`` properties JSONB column.

    Args:
        deal_name_or_id: Deal name (matched with ilike) or Pikar UUID.
        notes: Conversation notes to attach to the deal.
        next_steps: Optional list of next-step bullet points.
        stage_change: Optional new deal stage (e.g. ``"negotiation"``).

    Returns:
        Dict with ``success``, ``deal``, ``synced_to_hubspot``, and
        ``stage_changed`` keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    admin = AdminService()

    # Look up deal by name (ilike) or UUID
    try:
        deal_result = await _execute_async_query(
            admin.client.table("hubspot_deals")
            .select("id, deal_name, stage, hubspot_deal_id, user_id, properties")
            .eq("user_id", user_id)
            .or_(f"deal_name.ilike.%{deal_name_or_id}%,id.eq.{deal_name_or_id}")
            .limit(1),
            op_name="hubspot_tools.sync_deal_notes.find_deal",
        )
    except Exception as exc:
        logger.exception("sync_deal_notes: deal lookup failed")
        return {"error": f"Failed to find deal: {exc}"}

    if not deal_result.data:
        return {
            "error": f"No deal found matching '{deal_name_or_id}'",
        }

    deal = deal_result.data[0]
    deal_id = deal["id"]
    hubspot_deal_id = deal.get("hubspot_deal_id")

    # Format full note text with next steps
    formatted_notes = notes
    if next_steps:
        steps_str = "\n".join(f"• {step}" for step in next_steps)
        formatted_notes = f"{notes}\n\nNext Steps:\n{steps_str}"

    synced_to_hubspot = False
    stage_changed = False

    if hubspot_deal_id:
        try:
            svc = HubSpotService()
            result_note = await svc.add_deal_note(
                user_id=user_id,
                deal_id=deal_id,
                note_text=formatted_notes,
                stage_change=stage_change,
            )
            synced_to_hubspot = True
            stage_changed = result_note.get("stage_changed", False)
        except Exception as exc:
            logger.warning(
                "sync_deal_notes: HubSpot push failed for deal=%s, "
                "falling back to local-only: %s",
                deal_id,
                exc,
            )

    # Always update local properties with notes and last_activity_at
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    try:
        existing_props = deal.get("properties") or {}
        existing_props["last_meeting_notes"] = formatted_notes
        existing_props["last_notes_updated_at"] = now_iso
        if stage_change and stage_changed:
            existing_props["stage_after_sync"] = stage_change

        await _execute_async_query(
            admin.client.table("hubspot_deals")
            .update(
                {
                    "properties": existing_props,
                    "last_activity_at": now_iso,
                }
            )
            .eq("id", deal_id),
            op_name="hubspot_tools.sync_deal_notes.update_local",
        )
    except Exception:
        logger.warning(
            "sync_deal_notes: failed to update local deal properties for %s",
            deal_id,
        )

    return {
        "success": True,
        "deal": {
            "id": deal_id,
            "deal_name": deal.get("deal_name"),
            "stage": stage_change if stage_changed else deal.get("stage"),
            "hubspot_deal_id": hubspot_deal_id,
        },
        "synced_to_hubspot": synced_to_hubspot,
        "stage_changed": stage_changed,
    }


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

HUBSPOT_TOOLS = [
    search_hubspot_contacts,
    get_hubspot_deal_context,
    create_hubspot_contact,
    update_hubspot_deal,
    list_hubspot_deals,
    score_hubspot_lead,  # Phase 62: replaces degraded score_lead
    query_hubspot_crm,  # Phase 62: replaces degraded query_crm
    sync_deal_notes,  # Phase 62: auto-sync deal notes to HubSpot
]
