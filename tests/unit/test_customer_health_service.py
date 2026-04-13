"""Unit tests for CustomerHealthService and SupportTicketService.get_ticket_stats.

Tests SUPP-04: customer health dashboard with real computed metrics.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ticket(
    status: str = "new",
    priority: str = "normal",
    sentiment: str = "neutral",
    created_at: str = "2024-01-01T00:00:00Z",
    resolved_at: str | None = None,
) -> dict:
    """Build a minimal ticket dict for testing."""
    return {
        "id": "t-test",
        "status": status,
        "priority": priority,
        "sentiment": sentiment,
        "created_at": created_at,
        "resolved_at": resolved_at,
    }


# ---------------------------------------------------------------------------
# SupportTicketService.get_ticket_stats
# ---------------------------------------------------------------------------


class TestGetTicketStats:
    """Tests for SupportTicketService.get_ticket_stats."""

    @pytest.fixture(autouse=True)
    def mock_env(self):
        """Patch environment variables so BaseService init succeeds."""
        with patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"},
        ):
            yield

    @pytest.fixture(autouse=True)
    def mock_user_id(self):
        """Ensure get_current_user_id returns a test user."""
        with patch(
            "app.services.support_ticket_service.get_current_user_id",
            return_value="user-123",
        ):
            yield

    def _make_svc_with_mock_client(self):
        """Create SupportTicketService with a fully mocked _client (no real Supabase auth)."""
        from app.services.support_ticket_service import SupportTicketService

        svc = SupportTicketService()  # no user_token → is_authenticated=False
        svc._client = MagicMock()  # never called: is_authenticated is False
        return svc

    @pytest.mark.asyncio
    async def test_get_ticket_stats_basic(self):
        """Test get_ticket_stats computes correct counts from ticket rows."""
        tickets = [
            _make_ticket(status="new", sentiment="negative"),
            _make_ticket(
                status="resolved",
                sentiment="positive",
                created_at="2024-01-01T00:00:00Z",
                resolved_at="2024-01-01T04:00:00Z",
            ),
            _make_ticket(
                status="closed",
                sentiment="neutral",
                created_at="2024-01-02T00:00:00Z",
                resolved_at="2024-01-02T02:00:00Z",
            ),
        ]

        mock_response = MagicMock()
        mock_response.data = tickets

        with patch(
            "app.services.support_ticket_service.execute_async",
            AsyncMock(return_value=mock_response),
        ), patch(
            "app.services.support_ticket_service.AdminService"
        ) as MockAdmin:
            MockAdmin.return_value.client = MagicMock()
            svc = self._make_svc_with_mock_client()
            stats = await svc.get_ticket_stats(user_id="user-123")

        assert stats["open_count"] == 1
        assert stats["resolved_count"] == 2
        assert stats["total_count"] == 3
        # avg of 4h and 2h = 3h
        assert stats["avg_resolution_hours"] == pytest.approx(3.0)
        assert stats["sentiment_breakdown"]["negative"] == 1
        assert stats["sentiment_breakdown"]["positive"] == 1
        assert stats["sentiment_breakdown"]["neutral"] == 1

    @pytest.mark.asyncio
    async def test_get_ticket_stats_no_resolved_gives_none_avg(self):
        """Test that avg_resolution_hours is None when no tickets have resolved_at."""
        tickets = [_make_ticket(status="new"), _make_ticket(status="in_progress")]
        mock_response = MagicMock()
        mock_response.data = tickets

        with patch(
            "app.services.support_ticket_service.execute_async",
            AsyncMock(return_value=mock_response),
        ), patch(
            "app.services.support_ticket_service.AdminService"
        ) as MockAdmin:
            MockAdmin.return_value.client = MagicMock()
            svc = self._make_svc_with_mock_client()
            stats = await svc.get_ticket_stats(user_id="user-123")

        assert stats["avg_resolution_hours"] is None
        assert stats["open_count"] == 2
        assert stats["resolved_count"] == 0

    @pytest.mark.asyncio
    async def test_get_ticket_stats_empty(self):
        """Test that empty ticket list returns all zeros."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch(
            "app.services.support_ticket_service.execute_async",
            AsyncMock(return_value=mock_response),
        ), patch(
            "app.services.support_ticket_service.AdminService"
        ) as MockAdmin:
            MockAdmin.return_value.client = MagicMock()
            svc = self._make_svc_with_mock_client()
            stats = await svc.get_ticket_stats(user_id="user-123")

        assert stats["open_count"] == 0
        assert stats["resolved_count"] == 0
        assert stats["total_count"] == 0
        assert stats["avg_resolution_hours"] is None


# ---------------------------------------------------------------------------
# CustomerHealthService.get_health_dashboard
# ---------------------------------------------------------------------------


class TestCustomerHealthDashboard:
    """Tests for CustomerHealthService.get_health_dashboard."""

    def _make_stats(
        self,
        open_count: int = 0,
        resolved_count: int = 0,
        total_count: int = 0,
        avg_resolution_hours: float | None = None,
        positive: int = 0,
        neutral: int = 0,
        negative: int = 0,
    ) -> dict:
        """Build a ticket stats dict for mocking."""
        return {
            "open_count": open_count,
            "resolved_count": resolved_count,
            "total_count": total_count,
            "avg_resolution_hours": avg_resolution_hours,
            "sentiment_breakdown": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
            },
            "priority_breakdown": {"low": 0, "normal": total_count, "high": 0, "urgent": 0},
        }

    @pytest.mark.asyncio
    async def test_health_dashboard_with_tickets(self):
        """Test dashboard computes correct metrics from mixed ticket data."""
        stats = self._make_stats(
            open_count=3,
            resolved_count=7,
            total_count=10,
            avg_resolution_hours=12.0,
            positive=4,
            neutral=4,
            negative=2,
        )

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["open_tickets"] == 3
        assert dashboard["total_tickets"] == 10
        assert dashboard["resolution_rate"] == pytest.approx(70.0)
        assert dashboard["avg_resolution_time_hours"] == pytest.approx(12.0)
        assert dashboard["sentiment_summary"]["positive"] == 4
        assert dashboard["sentiment_summary"]["negative"] == 2
        assert "churn_risk_level" in dashboard
        assert "churn_risk_factors" in dashboard

    @pytest.mark.asyncio
    async def test_health_dashboard_empty(self):
        """Test that empty ticket data returns zeros and low churn risk."""
        stats = self._make_stats()

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["open_tickets"] == 0
        assert dashboard["total_tickets"] == 0
        assert dashboard["resolution_rate"] == 0.0
        assert dashboard["avg_resolution_time_hours"] is None
        assert dashboard["churn_risk_level"] == "low"
        assert dashboard["churn_risk_factors"] == []

    @pytest.mark.asyncio
    async def test_churn_risk_high_many_open_tickets(self):
        """Test high churn risk when there are 6+ open tickets."""
        stats = self._make_stats(
            open_count=6,
            resolved_count=2,
            total_count=8,
            avg_resolution_hours=10.0,
            negative=1,
            neutral=7,
        )

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["churn_risk_level"] == "high"
        assert len(dashboard["churn_risk_factors"]) >= 1

    @pytest.mark.asyncio
    async def test_churn_risk_high_majority_negative_sentiment(self):
        """Test high churn risk when >50% tickets have negative sentiment."""
        stats = self._make_stats(
            open_count=2,
            resolved_count=8,
            total_count=10,
            avg_resolution_hours=5.0,
            positive=1,
            neutral=3,
            negative=6,  # 60% negative
        )

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["churn_risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_churn_risk_medium(self):
        """Test medium churn risk when there are 3+ open tickets."""
        stats = self._make_stats(
            open_count=3,
            resolved_count=5,
            total_count=8,
            avg_resolution_hours=10.0,
            positive=4,
            neutral=4,
            negative=0,
        )

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["churn_risk_level"] == "medium"

    @pytest.mark.asyncio
    async def test_churn_risk_low(self):
        """Test low churn risk when 1 open ticket with positive sentiment."""
        stats = self._make_stats(
            open_count=1,
            resolved_count=9,
            total_count=10,
            avg_resolution_hours=8.0,
            positive=8,
            neutral=2,
            negative=0,
        )

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["churn_risk_level"] == "low"
        assert dashboard["churn_risk_factors"] == []

    @pytest.mark.asyncio
    async def test_churn_risk_high_slow_resolution(self):
        """Test high churn risk when avg resolution exceeds 48 hours."""
        stats = self._make_stats(
            open_count=1,
            resolved_count=5,
            total_count=6,
            avg_resolution_hours=72.0,
            positive=3,
            neutral=3,
            negative=0,
        )

        with patch(
            "app.services.customer_health_service.SupportTicketService"
        ) as MockService:
            instance = AsyncMock()
            instance.get_ticket_stats = AsyncMock(return_value=stats)
            MockService.return_value = instance

            from app.services.customer_health_service import CustomerHealthService

            svc = CustomerHealthService()
            dashboard = await svc.get_health_dashboard(user_id="u1")

        assert dashboard["churn_risk_level"] == "high"
        assert any("72.0h" in f for f in dashboard["churn_risk_factors"])
