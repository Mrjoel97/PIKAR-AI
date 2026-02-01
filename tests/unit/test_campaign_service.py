"""Unit tests for CampaignService.

Tests CRUD operations for campaigns used by MarketingAutomationAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestCampaignService:
    """Test suite for CampaignService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create CampaignService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key'
        }):
            with patch('app.services.campaign_service.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                from app.services.campaign_service import CampaignService
                return CampaignService()

    def test_initialization_success(self, service):
        """Test that service initializes correctly with credentials."""
        assert service is not None
        assert service._table_name == "campaigns"

    def test_initialization_fails_without_credentials(self):
        """Test that service raises error without Supabase credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Supabase credentials missing"):
                from app.services.campaign_service import CampaignService
                CampaignService()

    @pytest.mark.asyncio
    async def test_create_campaign(self, service, mock_supabase_client):
        """Test creating a new campaign."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "camp-123",
            "name": "Q1 Email Campaign",
            "campaign_type": "email",
            "target_audience": "B2B decision makers",
            "status": "draft"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_campaign(
            name="Q1 Email Campaign",
            campaign_type="email",
            target_audience="B2B decision makers"
        )

        assert result["id"] == "camp-123"
        assert result["campaign_type"] == "email"
        assert result["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_campaign(self, service, mock_supabase_client):
        """Test retrieving a campaign by ID."""
        mock_response = MagicMock()
        mock_response.data = {
            "id": "camp-123",
            "name": "Test Campaign",
            "status": "active"
        }
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = await service.get_campaign("camp-123")

        assert result["id"] == "camp-123"

    @pytest.mark.asyncio
    async def test_update_campaign(self, service, mock_supabase_client):
        """Test updating a campaign."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "camp-123",
            "status": "active",
            "name": "Updated Campaign"
        }]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_campaign("camp-123", status="active", name="Updated Campaign")

        assert result["status"] == "active"
        assert result["name"] == "Updated Campaign"

    @pytest.mark.asyncio
    async def test_delete_campaign(self, service, mock_supabase_client):
        """Test deleting a campaign."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "camp-123"}]
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.delete_campaign("camp-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_list_campaigns(self, service, mock_supabase_client):
        """Test listing campaigns with filters."""
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "camp-1", "name": "Campaign 1", "status": "active"},
            {"id": "camp-2", "name": "Campaign 2", "status": "active"}
        ]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = await service.list_campaigns(status="active")

        assert len(result) == 2
        assert result[0]["id"] == "camp-1"

    @pytest.mark.asyncio
    async def test_record_metrics(self, service, mock_supabase_client):
        """Test recording campaign metrics."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "camp-123",
            "metrics": {"impressions": 1000, "clicks": 50, "conversions": 10, "ctr": 5.0}
        }]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.record_metrics("camp-123", impressions=1000, clicks=50, conversions=10)

        assert result["metrics"]["impressions"] == 1000
        assert result["metrics"]["ctr"] == 5.0
