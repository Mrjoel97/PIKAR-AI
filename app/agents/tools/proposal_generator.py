# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Sales proposal generation tool -- one-request PDF proposal from deal context.

Provides ``generate_sales_proposal``, an agent-callable function that:
- Auto-populates client and deal data from HubSpot when a ``deal_id`` is given.
- Accepts explicit client info and line items for non-CRM proposals.
- Calculates line-item totals, applies discounts, and derives a final amount.
- Renders a branded ``sales_proposal`` PDF via :class:`DocumentService` and
  returns a downloadable widget to the chat UI.

Phase 62 Plan 03 -- SALES-03 requirement.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers (lazy to avoid import chain in tests)
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Return the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


def _get_session_id() -> str | None:
    """Return the current session ID from the request-scoped context."""
    from app.services.request_context import get_current_session_id

    return get_current_session_id()


# ---------------------------------------------------------------------------
# Line-item calculation helpers
# ---------------------------------------------------------------------------


def _calculate_line_items(
    line_items: list[dict[str, Any]],
    discount_percent: float,
) -> tuple[list[dict[str, Any]], float, float]:
    """Compute per-item totals, subtotal, and post-discount total.

    Args:
        line_items: Raw line item dicts (name, quantity, unit_price, …).
        discount_percent: Percentage discount to apply (0-100).

    Returns:
        Tuple of (enriched_items, subtotal, total_amount).
    """
    enriched: list[dict[str, Any]] = []
    subtotal = 0.0

    for item in line_items:
        qty = float(item.get("quantity", 1))
        unit_price = float(item.get("unit_price", 0.0))
        total = qty * unit_price
        subtotal += total
        enriched.append(
            {
                **item,
                "quantity": qty,
                "unit_price": unit_price,
                "total": total,
            }
        )

    discount_amount = subtotal * (discount_percent / 100.0) if discount_percent else 0.0
    total_amount = subtotal - discount_amount
    return enriched, subtotal, total_amount


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------


async def generate_sales_proposal(
    client_name: str | None = None,
    client_company: str | None = None,
    client_email: str | None = None,
    deal_id: str | None = None,
    executive_summary: str = "",
    line_items: list[dict[str, Any]] | None = None,
    total_amount: float | None = None,
    timeline: str = "",
    terms: str = "",
    validity_days: int = 30,
    discount_percent: float = 0,
) -> dict[str, Any]:
    """Generate a professional branded PDF sales proposal.

    Creates a downloadable PDF proposal from deal context or manual input.
    When ``deal_id`` is provided, client info and deal amount are automatically
    enriched from HubSpot CRM.  Line item totals are calculated automatically.

    Args:
        client_name: Prospect full name (auto-populated from HubSpot if deal_id given).
        client_company: Prospect company name.
        client_email: Prospect email address.
        deal_id: HubSpot deal UUID to auto-populate client and pricing data.
        executive_summary: Opening summary paragraph for the proposal.
        line_items: List of dicts with ``name``, ``quantity``, ``unit_price``,
            and optional ``description``.  Totals are calculated automatically.
        total_amount: Override final total (used when no line_items provided).
        timeline: Plain-text project timeline or delivery schedule.
        terms: Terms and conditions text (falls back to standard boilerplate).
        validity_days: Days the proposal remains valid (default 30).
        discount_percent: Percentage discount applied to line-item subtotal.

    Returns:
        Dict with ``success``, ``widget`` (downloadable PDF card), and
        ``proposal_data`` summary on success; ``success`` + ``error`` on failure.
    """
    # ------------------------------------------------------------------
    # 1. Resolve user identity
    # ------------------------------------------------------------------
    user_id = _get_user_id()
    if not user_id:
        return {
            "success": False,
            "error": "User not authenticated. Cannot generate proposal without a valid user session.",
        }

    # ------------------------------------------------------------------
    # 2. Enrich from HubSpot when deal_id is provided
    # ------------------------------------------------------------------
    if deal_id:
        try:
            from app.services.hubspot_service import HubSpotService

            hs = HubSpotService()
            deal_context = await hs.get_deal_context(
                user_id=user_id,
                contact_name_or_id=deal_id,
            )
            contact = deal_context.get("contact") or {}
            deals = deal_context.get("deals") or []

            # Auto-populate client fields when not explicitly overridden
            if not client_name:
                client_name = contact.get("name")
            if not client_company:
                client_company = contact.get("company")
            if not client_email:
                client_email = contact.get("email")

            # Auto-populate total from deal amount when not set
            if total_amount is None and deals:
                deal_amount = deals[0].get("amount")
                if deal_amount is not None:
                    total_amount = float(deal_amount)

        except Exception as exc:
            logger.warning(
                "HubSpot enrichment failed for deal_id=%s: %s. Proceeding with provided data.",
                deal_id,
                exc,
            )

    # ------------------------------------------------------------------
    # 3. Validate required fields after enrichment
    # ------------------------------------------------------------------
    if not client_name:
        return {
            "success": False,
            "error": (
                "client_name is required. Provide it explicitly or pass a deal_id "
                "to auto-populate from HubSpot."
            ),
        }

    # ------------------------------------------------------------------
    # 4. Calculate line-item totals
    # ------------------------------------------------------------------
    computed_line_items: list[dict[str, Any]] = []
    subtotal: float | None = None

    if line_items:
        computed_line_items, subtotal, computed_total = _calculate_line_items(
            line_items, discount_percent
        )
        # Only override total_amount when computed from line items (not overridden by caller)
        if total_amount is None:
            total_amount = computed_total
        elif not deal_id:
            # When caller provides both line_items and total_amount explicitly, respect total_amount
            pass
    elif total_amount is not None:
        # No line items — synthesise a single "As quoted" entry
        computed_line_items = [
            {
                "name": "As Quoted",
                "description": "See proposal details",
                "quantity": 1,
                "unit_price": total_amount,
                "total": total_amount,
            }
        ]
        subtotal = total_amount

    # ------------------------------------------------------------------
    # 5. Build template data dict
    # ------------------------------------------------------------------
    proposal_number = f"PROP-{uuid.uuid4().hex[:6].upper()}"
    proposal_date = date.today().isoformat()

    template_data: dict[str, Any] = {
        "client_name": client_name,
        "client_company": client_company or "",
        "client_email": client_email or "",
        "proposal_number": proposal_number,
        "proposal_date": proposal_date,
        "executive_summary": executive_summary,
        "line_items": computed_line_items,
        "subtotal": subtotal,
        "discount_percent": discount_percent if discount_percent else None,
        "total_amount": total_amount,
        "timeline": timeline,
        "terms": terms,
        "validity_days": validity_days,
        "milestones": [],
    }

    # ------------------------------------------------------------------
    # 6. Generate PDF via DocumentService
    # ------------------------------------------------------------------
    doc_title = f"Proposal - {client_company or client_name}"
    session_id = _get_session_id()

    try:
        from app.services.document_service import DocumentService

        svc = DocumentService()
        widget = await svc.generate_pdf(
            template_name="sales_proposal",
            data=template_data,
            user_id=user_id,
            session_id=session_id,
            title=doc_title,
        )
    except Exception as exc:
        logger.exception("Failed to generate sales proposal PDF: %s", exc)
        return {
            "success": False,
            "error": f"PDF generation failed: {exc}",
        }

    # ------------------------------------------------------------------
    # 7. Return result
    # ------------------------------------------------------------------
    return {
        "success": True,
        "widget": widget,
        "proposal_data": {
            "client": client_company or client_name,
            "amount": total_amount,
            "items_count": len(computed_line_items),
            "proposal_number": proposal_number,
            "valid_until": f"{validity_days} days from {proposal_date}",
        },
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

PROPOSAL_TOOLS = [generate_sales_proposal]
