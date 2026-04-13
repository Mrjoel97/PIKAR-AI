"""Unit tests for CustomerSuccess new tools: draft_customer_response and suggest_faq_from_tickets.

Tests SUPP-02 (communication drafting) and SUPP-03 (FAQ suggestion from resolved tickets).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDraftCustomerResponse:
    """Tests for draft_customer_response tool."""

    @pytest.mark.asyncio
    async def test_refund_scenario_returns_success(self):
        """Test that refund scenario returns a structured draft."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="refund",
            context="Customer wants refund for order #123",
            customer_name="John",
        )
        assert result["success"] is True
        draft = result["draft"]
        assert "subject" in draft
        assert "body" in draft
        assert "tone" in draft
        assert "scenario" in draft
        assert draft["scenario"] == "refund"
        assert "John" in draft["body"]

    @pytest.mark.asyncio
    async def test_shipping_delay_returns_empathetic_language(self):
        """Test that shipping_delay scenario includes empathetic language."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="shipping_delay",
            context="Package delayed 5 days",
            customer_name="Jane",
        )
        assert result["success"] is True
        draft = result["draft"]
        assert draft["scenario"] == "shipping_delay"
        assert "Jane" in draft["body"]
        # Must contain some empathetic marker
        body_lower = draft["body"].lower()
        assert any(
            word in body_lower
            for word in ["apologize", "sorry", "understand", "sincerely", "delay"]
        )

    @pytest.mark.asyncio
    async def test_complaint_scenario_returns_success(self):
        """Test that complaint scenario returns a valid draft."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="complaint",
            context="Product quality issue",
            customer_name="Bob",
        )
        assert result["success"] is True
        draft = result["draft"]
        assert draft["scenario"] == "complaint"
        assert "Bob" in draft["body"]

    @pytest.mark.asyncio
    async def test_unknown_scenario_returns_generic_template(self):
        """Test that unknown scenario falls back to a generic professional template."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="unknown_xyz",
            context="Some context",
            customer_name="Alex",
        )
        assert result["success"] is True
        draft = result["draft"]
        assert "subject" in draft
        assert "body" in draft
        assert "Alex" in draft["body"]

    @pytest.mark.asyncio
    async def test_follow_up_scenario(self):
        """Test that follow_up scenario returns a draft."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="follow_up",
            context="Checking in on open ticket",
            customer_name="Sarah",
        )
        assert result["success"] is True
        assert result["draft"]["scenario"] == "follow_up"

    @pytest.mark.asyncio
    async def test_apology_scenario(self):
        """Test that apology scenario returns a draft."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="apology",
            context="Service outage impacted the customer",
            customer_name="Mike",
        )
        assert result["success"] is True
        assert result["draft"]["scenario"] == "apology"

    @pytest.mark.asyncio
    async def test_general_scenario(self):
        """Test that general scenario returns a draft."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="general",
            context="General inquiry",
            customer_name="Customer",
        )
        assert result["success"] is True
        assert result["draft"]["scenario"] == "general"

    @pytest.mark.asyncio
    async def test_default_customer_name(self):
        """Test that customer_name defaults gracefully."""
        from app.agents.customer_support.tools import draft_customer_response

        result = await draft_customer_response(
            scenario="refund",
            context="Refund request",
        )
        assert result["success"] is True
        assert "subject" in result["draft"]

    @pytest.mark.asyncio
    async def test_draft_contains_tone_field(self):
        """Test that tone field is included and non-empty."""
        from app.agents.customer_support.tools import draft_customer_response

        for scenario in ["refund", "shipping_delay", "complaint", "follow_up", "apology", "general"]:
            result = await draft_customer_response(
                scenario=scenario,
                context="Some context",
                customer_name="TestUser",
            )
            assert result["draft"]["tone"], f"Tone missing for scenario: {scenario}"


class TestSuggestFaqFromTickets:
    """Tests for suggest_faq_from_tickets tool."""

    @pytest.mark.asyncio
    async def test_with_enough_similar_tickets_returns_suggestions(self):
        """Test that 3+ similar resolved tickets produce FAQ suggestions."""
        mock_groups = [
            {
                "subject_pattern": "password reset not working",
                "count": 4,
                "tickets": [
                    {"id": "t1", "subject": "Password reset not working", "resolution": "Send reset email again", "resolved_at": "2024-01-01"},
                    {"id": "t2", "subject": "Password reset not working", "resolution": "Check spam folder", "resolved_at": "2024-01-02"},
                    {"id": "t3", "subject": "Password reset not working", "resolution": "Reset via mobile app", "resolved_at": "2024-01-03"},
                    {"id": "t4", "subject": "Password reset not working", "resolution": "Send reset email again", "resolved_at": "2024-01-04"},
                ],
            }
        ]
        with patch(
            "app.services.support_ticket_service.SupportTicketService",
        ) as MockService:
            instance = AsyncMock()
            instance.find_similar_resolved_tickets = AsyncMock(return_value=mock_groups)
            MockService.return_value = instance

            from app.agents.customer_support.tools import suggest_faq_from_tickets

            result = await suggest_faq_from_tickets(min_similar=3)

        assert result["success"] is True
        assert "faq_suggestions" in result
        assert len(result["faq_suggestions"]) == 1
        suggestion = result["faq_suggestions"][0]
        assert "title" in suggestion
        assert "content" in suggestion
        assert "source_ticket_count" in suggestion
        assert suggestion["source_ticket_count"] == 4
        assert "source_ticket_ids" in suggestion
        assert len(suggestion["source_ticket_ids"]) == 4

    @pytest.mark.asyncio
    async def test_with_not_enough_tickets_returns_empty_message(self):
        """Test that fewer than min_similar similar tickets returns a no-suggestion message."""
        with patch(
            "app.services.support_ticket_service.SupportTicketService",
        ) as MockService:
            instance = AsyncMock()
            instance.find_similar_resolved_tickets = AsyncMock(return_value=[])
            MockService.return_value = instance

            from app.agents.customer_support.tools import suggest_faq_from_tickets

            result = await suggest_faq_from_tickets(min_similar=3)

        assert result["success"] is True
        assert result["faq_suggestions"] == []
        assert "message" in result
        assert "3" in result["message"]

    @pytest.mark.asyncio
    async def test_multiple_groups_produce_multiple_suggestions(self):
        """Test that multiple groups produce multiple FAQ entries."""
        mock_groups = [
            {
                "subject_pattern": "billing issue",
                "count": 3,
                "tickets": [
                    {"id": "t1", "subject": "Billing issue", "resolution": "Refund issued", "resolved_at": "2024-01-01"},
                    {"id": "t2", "subject": "Billing issue", "resolution": "Credit applied", "resolved_at": "2024-01-02"},
                    {"id": "t3", "subject": "Billing issue", "resolution": "Invoice corrected", "resolved_at": "2024-01-03"},
                ],
            },
            {
                "subject_pattern": "login failed",
                "count": 5,
                "tickets": [
                    {"id": "t4", "subject": "Login failed", "resolution": "Reset password", "resolved_at": "2024-01-01"},
                    {"id": "t5", "subject": "Login failed", "resolution": "Clear cookies", "resolved_at": "2024-01-02"},
                    {"id": "t6", "subject": "Login failed", "resolution": "Check caps lock", "resolved_at": "2024-01-03"},
                    {"id": "t7", "subject": "Login failed", "resolution": "Account unlocked", "resolved_at": "2024-01-04"},
                    {"id": "t8", "subject": "Login failed", "resolution": "Browser issue", "resolved_at": "2024-01-05"},
                ],
            },
        ]
        with patch(
            "app.services.support_ticket_service.SupportTicketService",
        ) as MockService:
            instance = AsyncMock()
            instance.find_similar_resolved_tickets = AsyncMock(return_value=mock_groups)
            MockService.return_value = instance

            from app.agents.customer_support.tools import suggest_faq_from_tickets

            result = await suggest_faq_from_tickets()

        assert result["success"] is True
        assert len(result["faq_suggestions"]) == 2


class TestFindSimilarResolvedTickets:
    """Tests for SupportTicketService.find_similar_resolved_tickets."""

    @pytest.fixture(autouse=True)
    def mock_user_id(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch(
            "app.services.support_ticket_service.get_current_user_id",
            return_value="test-user",
        ):
            yield

    @pytest.fixture
    def service(self):
        """Create SupportTicketService with mocked dependencies."""
        with patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"},
        ):
            from app.services.support_ticket_service import SupportTicketService

            svc = SupportTicketService(user_token="test-token")
            svc._client = MagicMock()
            return svc

    @pytest.mark.asyncio
    async def test_groups_tickets_by_subject_prefix(self, service):
        """Test that tickets with identical subject prefixes are grouped together."""
        # All three "Password Reset Issue" tickets share the exact same subject
        # so their normalized 50-char prefix is identical ("password reset issue")
        resolved_tickets = [
            {"id": "t1", "subject": "Password Reset Issue", "status": "resolved", "resolution": "Email sent", "resolved_at": "2024-01-01", "user_id": "test-user"},
            {"id": "t2", "subject": "Password Reset Issue", "status": "resolved", "resolution": "App used", "resolved_at": "2024-01-02", "user_id": "test-user"},
            {"id": "t3", "subject": "Password Reset Issue", "status": "resolved", "resolution": "Confirmed", "resolved_at": "2024-01-03", "user_id": "test-user"},
            {"id": "t4", "subject": "Billing problem", "status": "resolved", "resolution": "Refunded", "resolved_at": "2024-01-04", "user_id": "test-user"},
        ]

        mock_response = MagicMock()
        mock_response.data = resolved_tickets

        # Chain: .table().select().in_().order().limit().eq().execute()
        # The service also calls .eq("user_id", ...) when user_id is set
        service._client.table.return_value.select.return_value.in_.return_value.order.return_value.limit.return_value.eq.return_value.execute.return_value = mock_response

        from app.services.support_ticket_service import SupportTicketService

        with patch.object(type(service), "client", new_callable=lambda: property(lambda self: self._client)):
            groups = await service.find_similar_resolved_tickets(min_count=3)

        # Password reset should form a group of 3
        assert isinstance(groups, list)
        # At least one group should have count >= 3
        counts = [g["count"] for g in groups]
        assert any(c >= 3 for c in counts)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_resolved_tickets(self, service):
        """Test that empty ticket list returns no groups."""
        mock_response = MagicMock()
        mock_response.data = []

        # Chain: .table().select().in_().order().limit().eq().execute()
        service._client.table.return_value.select.return_value.in_.return_value.order.return_value.limit.return_value.eq.return_value.execute.return_value = mock_response

        from app.services.support_ticket_service import SupportTicketService

        with patch.object(type(service), "client", new_callable=lambda: property(lambda self: self._client)):
            groups = await service.find_similar_resolved_tickets(min_count=3)

        assert groups == []

    @pytest.mark.asyncio
    async def test_method_exists_on_service(self):
        """Test that find_similar_resolved_tickets method exists on SupportTicketService."""
        from app.services.support_ticket_service import SupportTicketService

        assert hasattr(SupportTicketService, "find_similar_resolved_tickets")
        assert callable(getattr(SupportTicketService, "find_similar_resolved_tickets"))
