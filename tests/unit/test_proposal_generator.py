"""Unit tests for proposal_generator tool.

Tests generate_sales_proposal with mocked DocumentService and HubSpotService.
Covers success paths, auto-population from deal_id, manual client info,
line item calculations, and error cases.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_WIDGET = {
    "type": "document",
    "title": "Proposal - Acme Corp",
    "data": {
        "documentUrl": "https://example.com/proposal.pdf",
        "title": "Proposal - Acme Corp",
        "fileType": "pdf",
        "sizeBytes": 12345,
        "templateName": "sales_proposal",
    },
    "dismissible": True,
    "expandable": False,
}

SAMPLE_DEAL_CONTEXT = {
    "contact": {
        "id": "contact-uuid-123",
        "name": "Jane Smith",
        "email": "jane@acme.com",
        "company": "Acme Corp",
    },
    "deals": [
        {
            "id": "deal-uuid-456",
            "deal_name": "Acme Corp - Enterprise License",
            "amount": 25000.0,
            "deal_stage": "proposal",
            "close_date": "2026-05-31",
        }
    ],
    "summary": "1 active deal, total value $25,000",
}


# ---------------------------------------------------------------------------
# Test 1: Success with all required fields provided manually
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_sales_proposal_success_manual_fields():
    """generate_sales_proposal returns success with widget when all fields provided."""
    with (
        patch(
            "app.agents.tools.proposal_generator._get_user_id",
            return_value="user-123",
        ),
        patch(
            "app.services.document_service.DocumentService"
        ) as MockDocSvc,
    ):
        mock_svc = AsyncMock()
        mock_svc.generate_pdf.return_value = SAMPLE_WIDGET
        MockDocSvc.return_value = mock_svc

        from app.agents.tools.proposal_generator import generate_sales_proposal

        result = await generate_sales_proposal(
            client_name="Jane Smith",
            client_company="Acme Corp",
            client_email="jane@acme.com",
            executive_summary="We propose a best-in-class solution for Acme Corp.",
            line_items=[
                {"name": "Enterprise License", "description": "Annual SaaS license", "quantity": 1, "unit_price": 20000.0},
                {"name": "Implementation", "description": "Onboarding services", "quantity": 5, "unit_price": 1000.0},
            ],
            validity_days=30,
        )

    assert result["success"] is True
    assert "widget" in result
    assert result["widget"]["type"] == "document"
    assert result["proposal_data"]["client"] == "Acme Corp"
    mock_svc.generate_pdf.assert_called_once()
    call_kwargs = mock_svc.generate_pdf.call_args
    assert call_kwargs.kwargs["template_name"] == "sales_proposal"
    assert call_kwargs.kwargs["user_id"] == "user-123"


# ---------------------------------------------------------------------------
# Test 2: Auto-populate from HubSpot deal_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_sales_proposal_deal_id_auto_populate():
    """When deal_id provided, client data is auto-populated from HubSpot."""
    with (
        patch(
            "app.agents.tools.proposal_generator._get_user_id",
            return_value="user-123",
        ),
        patch(
            "app.services.document_service.DocumentService"
        ) as MockDocSvc,
        patch(
            "app.services.hubspot_service.HubSpotService"
        ) as MockHubSpot,
    ):
        mock_svc = AsyncMock()
        mock_svc.generate_pdf.return_value = SAMPLE_WIDGET
        MockDocSvc.return_value = mock_svc

        mock_hs = AsyncMock()
        mock_hs.get_deal_context.return_value = SAMPLE_DEAL_CONTEXT
        MockHubSpot.return_value = mock_hs

        from app.agents.tools.proposal_generator import generate_sales_proposal

        result = await generate_sales_proposal(
            deal_id="deal-uuid-456",
            executive_summary="Custom summary.",
        )

    assert result["success"] is True
    assert "widget" in result
    # Client data should have been drawn from deal context
    mock_hs.get_deal_context.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3: Manual client info used when no deal_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_sales_proposal_no_deal_id_uses_explicit_client():
    """When deal_id is not provided, tool uses explicitly passed client info."""
    with (
        patch(
            "app.agents.tools.proposal_generator._get_user_id",
            return_value="user-456",
        ),
        patch(
            "app.services.document_service.DocumentService"
        ) as MockDocSvc,
    ):
        mock_svc = AsyncMock()
        mock_svc.generate_pdf.return_value = SAMPLE_WIDGET
        MockDocSvc.return_value = mock_svc

        from app.agents.tools.proposal_generator import generate_sales_proposal

        result = await generate_sales_proposal(
            client_name="Bob Builder",
            client_company="Builder Co",
            total_amount=5000.0,
        )

    assert result["success"] is True
    assert result["proposal_data"]["client"] == "Builder Co"
    # HubSpot should NOT have been called
    mock_svc.generate_pdf.assert_called_once()
    call_data = mock_svc.generate_pdf.call_args.kwargs["data"]
    assert call_data["client_name"] == "Bob Builder"
    assert call_data["client_company"] == "Builder Co"


# ---------------------------------------------------------------------------
# Test 4: Line item totals are correctly calculated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_sales_proposal_line_item_calculation():
    """Line items are structured with calculated totals (quantity * unit_price)."""
    captured_data: dict = {}

    async def capture_pdf(template_name, data, user_id, title=None, session_id=None):
        captured_data.update(data)
        return SAMPLE_WIDGET

    with (
        patch(
            "app.agents.tools.proposal_generator._get_user_id",
            return_value="user-789",
        ),
        patch(
            "app.services.document_service.DocumentService"
        ) as MockDocSvc,
    ):
        mock_svc = AsyncMock()
        mock_svc.generate_pdf.side_effect = capture_pdf
        MockDocSvc.return_value = mock_svc

        from app.agents.tools.proposal_generator import generate_sales_proposal

        result = await generate_sales_proposal(
            client_name="Test Client",
            line_items=[
                {"name": "Widget A", "quantity": 3, "unit_price": 100.0},
                {"name": "Widget B", "quantity": 2, "unit_price": 250.0},
            ],
            discount_percent=10.0,
        )

    assert result["success"] is True
    items = captured_data.get("line_items", [])
    assert len(items) == 2
    assert items[0]["total"] == pytest.approx(300.0)
    assert items[1]["total"] == pytest.approx(500.0)
    # Subtotal = 800, discount 10% -> total 720
    assert captured_data.get("subtotal") == pytest.approx(800.0)
    assert captured_data.get("total_amount") == pytest.approx(720.0)
    assert result["proposal_data"]["items_count"] == 2


# ---------------------------------------------------------------------------
# Test 5: Error when neither deal_id nor client_name provided
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_sales_proposal_error_no_client_info():
    """Returns error dict when neither deal_id nor client_name is provided."""
    with patch(
        "app.agents.tools.proposal_generator._get_user_id",
        return_value="user-123",
    ):
        from app.agents.tools.proposal_generator import generate_sales_proposal

        result = await generate_sales_proposal()

    assert result["success"] is False
    assert "error" in result
    assert "client_name" in result["error"].lower() or "deal_id" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test 6: Error when no user_id in request context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_sales_proposal_error_no_user_id():
    """Returns error when user_id cannot be resolved from request context."""
    with patch(
        "app.agents.tools.proposal_generator._get_user_id",
        return_value=None,
    ):
        from app.agents.tools.proposal_generator import generate_sales_proposal

        result = await generate_sales_proposal(client_name="Some Client")

    assert result["success"] is False
    assert "error" in result
    assert "user" in result["error"].lower() or "authenticated" in result["error"].lower()
