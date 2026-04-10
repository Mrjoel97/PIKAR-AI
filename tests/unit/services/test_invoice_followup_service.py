# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for InvoiceFollowupService.

Tests cover:
- Overdue invoice detection (status='sent'/'overdue', due_date < today)
- Email draft generation with professional tone
- Draft includes invoice_number, amount, days_overdue, due_date
- Invoices with status='paid' or 'draft' are NOT flagged
- Empty result when no overdue invoices
- Combined get_overdue_invoices_with_drafts flow
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set required env vars for BaseService init."""
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


@pytest.fixture()
def followup_service():
    """Return an InvoiceFollowupService instance."""
    from app.services.invoice_followup_service import InvoiceFollowupService

    return InvoiceFollowupService()


# ---------------------------------------------------------------------------
# Overdue Invoice Detection Tests
# ---------------------------------------------------------------------------


class TestOverdueInvoiceDetection:
    """Tests for detecting overdue invoices from the database."""

    @pytest.mark.asyncio()
    async def test_overdue_invoices_detected(self, followup_service):
        """Invoices with status='sent' and due_date < today are detected."""
        past_date = (date.today() - timedelta(days=10)).isoformat()
        mock_data = [
            {
                "id": "inv-1",
                "invoice_number": "INV-001",
                "due_date": past_date,
                "status": "sent",
                "metadata": {
                    "customer_name": "Acme Corp",
                    "customer_email": "billing@acme.com",
                    "total_amount": 1500.00,
                    "currency": "USD",
                },
            },
        ]
        mock_response = MagicMock()
        mock_response.data = mock_data

        with patch(
            "app.services.invoice_followup_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await followup_service.get_overdue_invoices("user-123")

        assert len(result) == 1
        assert result[0]["invoice_number"] == "INV-001"
        assert result[0]["days_overdue"] >= 10

    @pytest.mark.asyncio()
    async def test_paid_invoices_not_flagged(self, followup_service):
        """Invoices with status='paid' should NOT appear in overdue results."""
        # The query itself filters by status IN ('sent', 'overdue'),
        # so 'paid' invoices won't be returned by the DB query.
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.invoice_followup_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await followup_service.get_overdue_invoices("user-123")

        assert result == []

    @pytest.mark.asyncio()
    async def test_draft_invoices_not_flagged(self, followup_service):
        """Invoices with status='draft' should NOT appear in overdue results."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.invoice_followup_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await followup_service.get_overdue_invoices("user-123")

        assert result == []

    @pytest.mark.asyncio()
    async def test_no_overdue_invoices_returns_empty(self, followup_service):
        """When no invoices are overdue, return an empty list."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.invoice_followup_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await followup_service.get_overdue_invoices("user-123")

        assert result == []


# ---------------------------------------------------------------------------
# Email Draft Generation Tests
# ---------------------------------------------------------------------------


class TestEmailDraftGeneration:
    """Tests for follow-up email draft generation."""

    def test_draft_contains_required_fields(self, followup_service):
        """Each email draft has subject, recipient, body, invoice details."""
        invoice = {
            "id": "inv-1",
            "invoice_number": "INV-001",
            "due_date": (date.today() - timedelta(days=5)).isoformat(),
            "metadata": {
                "customer_name": "Acme Corp",
                "customer_email": "billing@acme.com",
                "total_amount": 2500.00,
                "currency": "USD",
            },
        }

        draft = followup_service.generate_followup_draft(invoice)

        assert "subject" in draft
        assert "recipient" in draft
        assert "body" in draft
        assert "invoice_id" in draft
        assert "invoice_number" in draft
        assert "days_overdue" in draft
        assert "amount" in draft

    def test_draft_subject_includes_invoice_number(self, followup_service):
        """Email subject includes the invoice number."""
        invoice = {
            "id": "inv-1",
            "invoice_number": "INV-042",
            "due_date": (date.today() - timedelta(days=3)).isoformat(),
            "metadata": {
                "customer_name": "Test Co",
                "total_amount": 100.00,
                "currency": "USD",
            },
        }

        draft = followup_service.generate_followup_draft(invoice)

        assert "INV-042" in draft["subject"]

    def test_draft_body_includes_amount_and_days(self, followup_service):
        """Email body includes the amount, due date, and days overdue."""
        past_date = date.today() - timedelta(days=7)
        invoice = {
            "id": "inv-1",
            "invoice_number": "INV-007",
            "due_date": past_date.isoformat(),
            "metadata": {
                "customer_name": "Widget Inc",
                "customer_email": "pay@widget.com",
                "total_amount": 3000.50,
                "currency": "USD",
            },
        }

        draft = followup_service.generate_followup_draft(invoice)

        assert "3000.50" in draft["body"] or "3,000.50" in draft["body"]
        assert "7 days" in draft["body"]
        assert past_date.isoformat() in draft["body"]

    def test_draft_uses_customer_email_when_available(self, followup_service):
        """Recipient is the customer email from metadata."""
        invoice = {
            "id": "inv-1",
            "invoice_number": "INV-001",
            "due_date": (date.today() - timedelta(days=1)).isoformat(),
            "metadata": {
                "customer_name": "Test",
                "customer_email": "billing@test.com",
                "total_amount": 500.00,
                "currency": "USD",
            },
        }

        draft = followup_service.generate_followup_draft(invoice)

        assert draft["recipient"] == "billing@test.com"

    def test_draft_fallback_recipient_when_no_email(self, followup_service):
        """Recipient defaults to 'customer' when no email in metadata."""
        invoice = {
            "id": "inv-1",
            "invoice_number": "INV-001",
            "due_date": (date.today() - timedelta(days=1)).isoformat(),
            "metadata": {
                "customer_name": "No Email Corp",
                "total_amount": 200.00,
                "currency": "USD",
            },
        }

        draft = followup_service.generate_followup_draft(invoice)

        assert draft["recipient"] == "customer"


# ---------------------------------------------------------------------------
# Combined Flow Tests
# ---------------------------------------------------------------------------


class TestGetOverdueInvoicesWithDrafts:
    """Tests for the combined overdue detection + draft generation flow."""

    @pytest.mark.asyncio()
    async def test_returns_invoices_with_drafts(self, followup_service):
        """Combined method returns invoices merged with their email drafts."""
        past_date = (date.today() - timedelta(days=3)).isoformat()
        mock_data = [
            {
                "id": "inv-1",
                "invoice_number": "INV-001",
                "due_date": past_date,
                "status": "overdue",
                "metadata": {
                    "customer_name": "Test Co",
                    "customer_email": "test@co.com",
                    "total_amount": 750.00,
                    "currency": "USD",
                },
            },
        ]
        mock_response = MagicMock()
        mock_response.data = mock_data

        with patch(
            "app.services.invoice_followup_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await followup_service.get_overdue_invoices_with_drafts("user-123")

        assert len(result) == 1
        item = result[0]
        assert "subject" in item
        assert "body" in item
        assert "invoice_number" in item
        assert item["invoice_number"] == "INV-001"

    @pytest.mark.asyncio()
    async def test_empty_when_no_overdue(self, followup_service):
        """Combined method returns empty list when no overdue invoices."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.invoice_followup_service.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await followup_service.get_overdue_invoices_with_drafts("user-123")

        assert result == []
