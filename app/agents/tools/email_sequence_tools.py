# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Email sequence agent tools -- drip campaign management.

Provides six agent-callable functions that wire into the
EmailSequenceService created in Phase 42 Plan 02.  Tools extract the
current user from request context and return structured dicts for the
agent.

The ``generate_sequence_content`` tool produces default email templates
programmatically (welcome, value-prop, CTA pattern) that the agent can
then refine with its own LLM capability.
"""

from __future__ import annotations

import json
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
# Tool: create_email_sequence
# ---------------------------------------------------------------------------


async def create_email_sequence(
    name: str,
    steps: str,
) -> dict[str, Any]:
    """Create a multi-step email sequence (drip campaign).

    Steps should be a JSON string array of objects, each with:
    ``subject_template``, ``body_template``, ``delay_hours`` (default 24),
    and ``delay_type`` ('after_previous' or 'at_time').

    Args:
        name: Sequence name (e.g. 'Welcome Series').
        steps: JSON string array of step objects.

    Returns:
        Created sequence dict with nested steps, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_sequence_service import EmailSequenceService

    svc = EmailSequenceService()

    try:
        parsed_steps = json.loads(steps)
        if not isinstance(parsed_steps, list):
            return {"error": "Steps must be a JSON array of objects."}

        result = await svc.create_sequence(
            user_id=user_id,
            name=name,
            steps=parsed_steps,
        )
        return result
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON in steps: {exc}"}
    except Exception as exc:
        logger.exception(
            "create_email_sequence failed for user=%s", user_id
        )
        return {"error": f"Failed to create email sequence: {exc}"}


# ---------------------------------------------------------------------------
# Tool: enroll_contacts_in_sequence
# ---------------------------------------------------------------------------


async def enroll_contacts_in_sequence(
    sequence_id: str,
    contact_ids: str,
    timezone: str = "UTC",
) -> dict[str, Any]:
    """Enroll contacts into an email sequence.

    Contacts begin receiving the sequence emails according to the
    configured step delays and their timezone.

    Args:
        sequence_id: UUID of the email sequence.
        contact_ids: Comma-separated string of contact UUIDs.
        timezone: IANA timezone (e.g. 'America/New_York').

    Returns:
        Dict with enrolled and skipped counts, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_sequence_service import EmailSequenceService

    svc = EmailSequenceService()

    try:
        parsed_ids = [
            cid.strip() for cid in contact_ids.split(",") if cid.strip()
        ]
        if not parsed_ids:
            return {"error": "No contact IDs provided."}

        result = await svc.enroll_contacts(
            user_id=user_id,
            sequence_id=sequence_id,
            contact_ids=parsed_ids,
            timezone_str=timezone,
        )
        return result
    except Exception as exc:
        logger.exception(
            "enroll_contacts_in_sequence failed for user=%s", user_id
        )
        return {
            "error": f"Failed to enroll contacts: {exc}",
        }


# ---------------------------------------------------------------------------
# Tool: get_sequence_performance
# ---------------------------------------------------------------------------


async def get_sequence_performance(
    sequence_id: str,
) -> dict[str, Any]:
    """Get email sequence performance metrics.

    Returns open rate, click rate, bounce rate, and completion rate
    for the specified sequence.

    Args:
        sequence_id: UUID of the email sequence.

    Returns:
        Dict with performance metrics, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_sequence_service import EmailSequenceService

    svc = EmailSequenceService()

    try:
        return await svc.get_sequence_performance(
            user_id=user_id, sequence_id=sequence_id
        )
    except Exception as exc:
        logger.exception(
            "get_sequence_performance failed for user=%s", user_id
        )
        return {
            "error": f"Failed to get sequence performance: {exc}",
        }


# ---------------------------------------------------------------------------
# Tool: generate_sequence_content
# ---------------------------------------------------------------------------


def _build_default_steps(
    campaign_context: str,
    contact_segment: str,
    num_steps: int,
) -> list[dict[str, Any]]:
    """Build programmatic default email sequence templates.

    Follows a welcome -> value-prop -> CTA pattern that the agent
    can refine using its own LLM capability.
    """
    templates: list[dict[str, Any]] = []

    # Step 1: Introductory
    templates.append({
        "subject_template": (
            "Hi {{first_name}}, quick intro from {{company}}"
        ),
        "body_template": (
            "<p>Hi {{first_name}},</p>"
            "<p>I noticed {{company}} might benefit from "
            f"{campaign_context}. I wanted to reach out and "
            "introduce myself.</p>"
            "<p>Would you be open to a quick chat?</p>"
        ),
        "delay_hours": 0,
        "delay_type": "after_previous",
    })

    # Middle steps: Value proposition
    for i in range(1, num_steps - 1):
        templates.append({
            "subject_template": (
                f"{{{{first_name}}}}, resource #{i} "
                f"for {contact_segment}"
            ),
            "body_template": (
                "<p>Hi {{first_name}},</p>"
                "<p>Following up with something useful "
                f"for {contact_segment} teams like yours "
                f"at {{{{company}}}}.</p>"
                f"<p>[Value content #{i} related to "
                f"{campaign_context}]</p>"
            ),
            "delay_hours": 24 * (i + 1),
            "delay_type": "after_previous",
        })

    # Final step: CTA
    if num_steps > 1:
        templates.append({
            "subject_template": (
                "{{first_name}}, let's schedule a call"
            ),
            "body_template": (
                "<p>Hi {{first_name}},</p>"
                "<p>I've shared a few resources about "
                f"{campaign_context}. I'd love to discuss "
                "how this could help {{company}}.</p>"
                "<p><strong>Can we find 15 minutes this week?"
                "</strong></p>"
            ),
            "delay_hours": 72,
            "delay_type": "after_previous",
        })

    return templates


async def generate_sequence_content(
    campaign_context: str,
    contact_segment: str,
    num_steps: int = 3,
) -> dict[str, Any]:
    """Generate email sequence content based on campaign context.

    Produces default email templates using a welcome, value-prop,
    CTA pattern with Jinja2 variables (``{{first_name}}``,
    ``{{company}}``, ``{{deal_name}}``).  The agent can then refine
    the generated content with its own LLM capability.

    Args:
        campaign_context: Description of the campaign or product.
        contact_segment: Target audience description.
        num_steps: Number of email steps to generate (default 3).

    Returns:
        Dict with generated steps and campaign context.
    """
    try:
        num_steps = max(1, min(num_steps, 10))
        steps = _build_default_steps(
            campaign_context, contact_segment, num_steps
        )
        return {
            "steps": steps,
            "num_steps": len(steps),
            "campaign_context": campaign_context,
            "contact_segment": contact_segment,
            "note": (
                "These are default templates. "
                "Customise subject lines and body content "
                "before creating the sequence."
            ),
        }
    except Exception as exc:
        logger.exception("generate_sequence_content failed")
        return {
            "error": f"Failed to generate sequence content: {exc}",
        }


# ---------------------------------------------------------------------------
# Tool: pause_email_sequence
# ---------------------------------------------------------------------------


async def pause_email_sequence(
    sequence_id: str,
) -> dict[str, Any]:
    """Pause an active email sequence.

    All pending sends will be held until the sequence is resumed.

    Args:
        sequence_id: UUID of the email sequence.

    Returns:
        Updated sequence dict, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_sequence_service import EmailSequenceService

    svc = EmailSequenceService()

    try:
        return await svc.update_sequence_status(
            user_id=user_id,
            sequence_id=sequence_id,
            status="paused",
        )
    except Exception as exc:
        logger.exception(
            "pause_email_sequence failed for user=%s", user_id
        )
        return {"error": f"Failed to pause sequence: {exc}"}


# ---------------------------------------------------------------------------
# Tool: resume_email_sequence
# ---------------------------------------------------------------------------


async def resume_email_sequence(
    sequence_id: str,
) -> dict[str, Any]:
    """Resume a paused email sequence.

    Pending sends will resume from where they stopped.

    Args:
        sequence_id: UUID of the email sequence.

    Returns:
        Updated sequence dict, or an error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.services.email_sequence_service import EmailSequenceService

    svc = EmailSequenceService()

    try:
        return await svc.update_sequence_status(
            user_id=user_id,
            sequence_id=sequence_id,
            status="active",
        )
    except Exception as exc:
        logger.exception(
            "resume_email_sequence failed for user=%s", user_id
        )
        return {"error": f"Failed to resume sequence: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

EMAIL_SEQUENCE_TOOLS = [
    create_email_sequence,
    enroll_contacts_in_sequence,
    get_sequence_performance,
    generate_sequence_content,
    pause_email_sequence,
    resume_email_sequence,
]
