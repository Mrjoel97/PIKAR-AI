# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Sales follow-up email drafting tool -- post-meeting email generation.

Provides a single agent-callable function that combines meeting context
(attendees, agenda, notes, next steps) with optional HubSpot CRM deal data
to produce a ready-to-send follow-up email draft.

The generated email includes a meeting recap, deal context (when HubSpot is
connected), a numbered next-steps list, and a clear call-to-action.  If
HubSpot is unavailable or the contact is not found, the tool degrades
gracefully and produces a meeting-only email.
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


def _format_amount(amount_str: str | None) -> str:
    """Format a numeric string as a dollar amount.

    Args:
        amount_str: Numeric string value, e.g. '50000'.

    Returns:
        Formatted string, e.g. '$50,000', or empty string when None.
    """
    if not amount_str:
        return ""
    try:
        return f"${float(amount_str):,.0f}"
    except (ValueError, TypeError):
        return amount_str


def _build_email_body(
    contact_name: str,
    meeting_subject: str,
    meeting_notes: str,
    next_steps: list[str],
    meeting_date: str | None,
    deal_context: dict[str, Any] | None,
) -> str:
    """Compose the multi-section plain-text email body.

    Args:
        contact_name: Display name of the contact.
        meeting_subject: Subject / title of the meeting.
        meeting_notes: Raw notes or recap from the meeting.
        next_steps: Ordered list of agreed follow-up actions.
        meeting_date: Optional ISO date string for the meeting.
        deal_context: Optional HubSpot deal context dict.

    Returns:
        Formatted plain-text email body string.
    """
    first_name = contact_name.split()[0] if contact_name else "there"

    date_fragment = f" on {meeting_date}" if meeting_date else ""
    lines: list[str] = [
        f"Hi {first_name},",
        "",
        f"Thank you for taking the time to meet{date_fragment} to discuss {meeting_subject}. "
        f"I wanted to follow up with a quick recap of what we covered.",
        "",
        "Meeting Recap",
        "-------------",
        meeting_notes,
        "",
    ]

    # Deal context section (only when HubSpot data is available)
    if deal_context:
        deals: list[dict[str, Any]] = deal_context.get("deals") or []
        if deals:
            deal = deals[0]
            stage = deal.get("stage") or deal.get("dealstage") or "In Progress"
            amount_formatted = _format_amount(deal.get("amount"))
            pipeline = deal.get("pipeline") or "default"
            deal_line = f"Deal Status: {stage}"
            if amount_formatted:
                deal_line += f" — {amount_formatted}"
            if pipeline and pipeline != "default":
                deal_line += f" ({pipeline} pipeline)"
            lines += [
                "Deal Context",
                "------------",
                deal_line,
                "",
            ]

    # Next steps section
    if next_steps:
        lines += ["Next Steps", "----------"]
        for idx, step in enumerate(next_steps, start=1):
            lines.append(f"{idx}. {step}")
        lines.append("")

    # CTA and sign-off
    lines += [
        "Please feel free to reach out if you have any questions or would like to schedule "
        "a follow-up call. I look forward to continuing our conversation.",
        "",
        "Best regards,",
    ]

    return "\n".join(lines)


def _pick_suggested_cta(
    next_steps: list[str],
    deal_context: dict[str, Any] | None,
) -> str:
    """Choose a one-line call-to-action recommendation.

    Args:
        next_steps: Agreed follow-up actions from the meeting.
        deal_context: Optional HubSpot deal context.

    Returns:
        A short CTA string.
    """
    if next_steps:
        return f"Schedule a call to review: {next_steps[0]}"

    if deal_context:
        deals = deal_context.get("deals") or []
        if deals:
            stage = deals[0].get("stage") or deals[0].get("dealstage") or ""
            if "proposal" in stage.lower():
                return "Schedule a call to review the proposal and answer any questions."
            if "demo" in stage.lower():
                return "Schedule a product demo to showcase key capabilities."

    return "Schedule a follow-up call to discuss next steps."


# ---------------------------------------------------------------------------
# Tool: generate_followup_email
# ---------------------------------------------------------------------------


async def generate_followup_email(
    contact_name: str,
    meeting_subject: str,
    meeting_notes: str,
    next_steps: list[str] | None = None,
    meeting_date: str | None = None,
    attendees: list[str] | None = None,
) -> dict[str, Any]:
    """Draft a personalized post-meeting follow-up email.

    Combines meeting context with optional HubSpot CRM deal data to
    produce a ready-to-send email with recap, next steps, and CTA.
    Degrades gracefully when HubSpot is unavailable.

    Args:
        contact_name: Full name of the primary contact (e.g. 'Jane Smith').
        meeting_subject: Subject or title of the meeting.
        meeting_notes: Raw notes or recap text from the meeting.
        next_steps: Optional ordered list of agreed follow-up actions.
        meeting_date: Optional ISO-8601 date string for the meeting.
        attendees: Optional list of attendee email addresses; the first
            email is used as the primary ``to`` address.

    Returns:
        On success: ``{"success": True, "email": {subject, to, body,
        suggested_cta}, "deal_context": <dict|None>}``.
        On auth failure: ``{"success": False, "error": "Authentication required"}``.
        On unexpected error: ``{"success": False, "error": <message>}``.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"success": False, "error": "Authentication required"}

    steps = list(next_steps) if next_steps else []

    # Attempt CRM enrichment -- non-fatal if HubSpot is not connected
    deal_context: dict[str, Any] | None = None
    try:
        from app.services.hubspot_service import HubSpotService

        svc = HubSpotService()
        deal_context = await svc.get_deal_context(user_id, contact_name)
    except Exception:
        logger.debug(
            "HubSpot enrichment unavailable for contact=%r; proceeding without CRM data",
            contact_name,
        )

    try:
        # Determine primary recipient
        to_address: str = ""
        if attendees:
            to_address = attendees[0]
        elif deal_context:
            contact = deal_context.get("contact") or {}
            to_address = contact.get("email") or ""

        body = _build_email_body(
            contact_name=contact_name,
            meeting_subject=meeting_subject,
            meeting_notes=meeting_notes,
            next_steps=steps,
            meeting_date=meeting_date,
            deal_context=deal_context,
        )

        suggested_cta = _pick_suggested_cta(steps, deal_context)

        return {
            "success": True,
            "email": {
                "subject": f"Following up: {meeting_subject}",
                "to": to_address,
                "body": body,
                "suggested_cta": suggested_cta,
            },
            "deal_context": deal_context,
        }
    except Exception as exc:
        logger.exception(
            "generate_followup_email failed for user=%s contact=%r",
            user_id,
            contact_name,
        )
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

SALES_FOLLOWUP_TOOLS = [generate_followup_email]
