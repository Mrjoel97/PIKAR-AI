"""Unit tests for AnalyticsService.

Tests event tracking and reporting operations used by DataAnalysisAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAnalyticsService:
    """Test suite for AnalyticsService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create AnalyticsService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }):
            with patch('app.services.analytics_service.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                from app.services.analytics_service import AnalyticsService
                return AnalyticsService()

    def test_initialization_success(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service._events_table == "analytics_events"
        assert service._reports_table == "analytics_reports"

    @pytest.mark.asyncio
    async def test_track_event(self, service, mock_supabase_client):
        """Test tracking an event."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "evt-1",
            "event_name": "login",
            "category": "auth"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.track_event(
            event_name="login",
            category="auth",
            properties={"method": "email"}
        )
        assert result["id"] == "evt-1"
        assert result["event_name"] == "login"

    @pytest.mark.asyncio
    async def test_query_events(self, service, mock_supabase_client):
        """Test querying events."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "evt-1"}, {"id": "evt-2"}]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        # Note: We are mocking the chain, so filters won't actually filter the mock response
        # We just check if the method returns the data
        result = await service.query_events(category="auth")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create_report(self, service, mock_supabase_client):
        """Test creating a report."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "rpt-1",
            "title": "Monthly Growth",
            "report_type": "growth"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_report(
            title="Monthly Growth",
            report_type="growth",
            data={"users": 100}
        )
        assert result["id"] == "rpt-1"

    @pytest.mark.asyncio
    async def test_get_report(self, service, mock_supabase_client):
        """Test retrieving a report."""
        mock_response = MagicMock()
        mock_response.data = {"id": "rpt-1", "title": "Report"}
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = await service.get_report("rpt-1")
        assert result["id"] == "rpt-1"

    @pytest.mark.asyncio
    async def test_list_reports(self, service, mock_supabase_client):
        """Test listing reports."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "rpt-1"}, {"id": "rpt-2"}]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        result = await service.list_reports(report_type="growth")
        assert len(result) == 2
