# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for generate_followup_email tool.

Covers structured output, body section validation, HubSpot enrichment,
graceful degradation when CRM is unavailable, and missing auth guard.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_DEAL_CONTEXT = {
    "contact": {"name": "Jane Smith", "email": "jane@acme.com", "company": "Acme Corp"},
    "deals": [
        {
            "id": "deal-123",
            "name": "Acme Corp - Enterprise",
            "stage": "Proposal Sent",
            "amount": "50000",
            "pipeline": "default",
        }
    ],
    "summary": "1 active deal in Proposal Sent stage worth $50,000.",
}


# ---------------------------------------------------------------------------
# Test 1: generate_followup_email returns structured dict with required keys
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_followup_email_returns_structured_dict():
    """Tool returns success=True with subject, body, to, and suggested_cta."""
    with (
        patch(
            "app.agents.tools.sales_followup._get_user_id",
            return_value="user-abc-123",
        ),
        patch(
            "app.services.hubspot_service.HubSpotService",
        ) as mock_svc_cls,
    ):
        mock_svc = AsyncMock()
        mock_svc.get_deal_context = AsyncMock(return_value=_SAMPLE_DEAL_CONTEXT)
        mock_svc_cls.return_value = mock_svc

        from app.agents.tools.sales_followup import generate_followup_email

        result = await generate_followup_email(
            contact_name="Jane Smith",
            meeting_subject="Q2 Growth Strategy",
            meeting_notes="Discussed expansion into EMEA market and pricing model.",
            next_steps=["Send proposal", "Schedule demo"],
            meeting_date="2026-04-10",
            attendees=["jane@acme.com"],
        )

    assert result["success"] is True
    email = result["email"]
    assert "subject" in email
    assert "body" in email
    assert "to" in email
    assert "suggested_cta" in email
    assert "Q2 Growth Strategy" in email["subject"]


# ---------------------------------------------------------------------------
# Test 2: Email body contains recap, next steps, and CTA sections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_body_contains_required_sections():
    """Body includes greeting, meeting recap, next steps, and CTA paragraphs."""
    with (
        patch(
            "app.agents.tools.sales_followup._get_user_id",
            return_value="user-abc-123",
        ),
        patch(
            "app.services.hubspot_service.HubSpotService",
        ) as mock_svc_cls,
    ):
        mock_svc = AsyncMock()
        mock_svc.get_deal_context = AsyncMock(return_value=_SAMPLE_DEAL_CONTEXT)
        mock_svc_cls.return_value = mock_svc

        from app.agents.tools.sales_followup import generate_followup_email

        result = await generate_followup_email(
            contact_name="Jane Smith",
            meeting_subject="Product Demo",
            meeting_notes="Covered core platform features and integration points.",
            next_steps=["Review integration docs", "Book technical call"],
        )

    body = result["email"]["body"]
    body_lower = body.lower()

    # Greeting section
    assert "jane" in body_lower

    # Recap section
    assert any(kw in body_lower for kw in ("recap", "discussed", "meeting", "covered"))

    # Next steps section -- numbered list or header
    assert any(kw in body_lower for kw in ("next step", "action", "review integration", "book technical"))

    # CTA paragraph or sign-off
    assert any(kw in body_lower for kw in ("reach out", "schedule", "look forward", "feel free", "questions"))


# ---------------------------------------------------------------------------
# Test 3: Email includes deal stage and amount when HubSpot is connected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_includes_deal_context_when_hubspot_connected():
    """When HubSpot returns deal data, the result includes deal_context."""
    with (
        patch(
            "app.agents.tools.sales_followup._get_user_id",
            return_value="user-abc-123",
        ),
        patch(
            "app.services.hubspot_service.HubSpotService",
        ) as mock_svc_cls,
    ):
        mock_svc = AsyncMock()
        mock_svc.get_deal_context = AsyncMock(return_value=_SAMPLE_DEAL_CONTEXT)
        mock_svc_cls.return_value = mock_svc

        from app.agents.tools.sales_followup import generate_followup_email

        result = await generate_followup_email(
            contact_name="Jane Smith",
            meeting_subject="Pipeline Review",
            meeting_notes="Reviewed deal status and procurement timeline.",
        )

    assert result["success"] is True
    assert result["deal_context"] is not None
    assert result["deal_context"]["deals"][0]["stage"] == "Proposal Sent"
    assert result["deal_context"]["deals"][0]["amount"] == "50000"

    # Deal info should appear in email body
    body_lower = result["email"]["body"].lower()
    assert any(kw in body_lower for kw in ("proposal sent", "50,000", "$50", "enterprise"))


# ---------------------------------------------------------------------------
# Test 4: Generates successfully without HubSpot (graceful degradation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_generates_without_hubspot_connection():
    """When HubSpot raises, email still generates with meeting-only context."""
    with (
        patch(
            "app.agents.tools.sales_followup._get_user_id",
            return_value="user-abc-123",
        ),
        patch(
            "app.services.hubspot_service.HubSpotService",
        ) as mock_svc_cls,
    ):
        mock_svc = AsyncMock()
        mock_svc.get_deal_context = AsyncMock(
            side_effect=ValueError("HubSpot integration not connected")
        )
        mock_svc_cls.return_value = mock_svc

        from app.agents.tools.sales_followup import generate_followup_email

        result = await generate_followup_email(
            contact_name="Bob Jones",
            meeting_subject="Initial Discovery",
            meeting_notes="Learned about their current pain points and timeline.",
            next_steps=["Send intro deck"],
        )

    assert result["success"] is True
    assert result["deal_context"] is None
    email = result["email"]
    assert "subject" in email
    assert "body" in email
    assert "bob" in email["body"].lower()


# ---------------------------------------------------------------------------
# Test 5: Returns error dict when no user_id in request context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_error_when_no_user_id():
    """When user_id is missing from request context, returns error dict."""
    with patch(
        "app.agents.tools.sales_followup._get_user_id",
        return_value=None,
    ):
        from app.agents.tools.sales_followup import generate_followup_email

        result = await generate_followup_email(
            contact_name="Someone",
            meeting_subject="Some Meeting",
            meeting_notes="Some notes.",
        )

    assert result["success"] is False
    assert "error" in result
