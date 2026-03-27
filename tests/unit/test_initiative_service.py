"""Unit tests for InitiativeService.

Tests CRUD operations for initiatives used by StrategicPlanningAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestInitiativeService:
    """Test suite for InitiativeService."""

    @pytest.fixture(autouse=True)
    def mock_user_id(self):
        """Ensure get_current_user_id returns a test user for all tests."""
        with patch('app.services.initiative_service.get_current_user_id', return_value='test-user'):
            yield

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create InitiativeService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-key'
        }):
            from app.services.initiative_service import InitiativeService
            svc = InitiativeService(user_token="test-token")
            svc._client = mock_supabase_client
            return svc

    def test_initialization_success(self, service):
        """Test that service initializes correctly with credentials."""
        assert service is not None
        assert service._table_name == "initiatives"

    def test_initialization_fails_without_credentials(self):
        """Test that service raises error without Supabase credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL environment variable is required"):
                from app.services.initiative_service import InitiativeService
                InitiativeService()

    @pytest.mark.asyncio
    async def test_create_initiative(self, service, mock_supabase_client):
        """Test creating a new initiative."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "init-123",
            "title": "Q1 Growth Strategy",
            "description": "Focus on user acquisition",
            "priority": "high",
            "status": "draft",
            "progress": 0
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        result = await service.create_initiative(
            title="Q1 Growth Strategy",
            description="Focus on user acquisition",
            priority="high"
        )

        assert result["id"] == "init-123"
        assert result["title"] == "Q1 Growth Strategy"
        assert result["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_initiative(self, service, mock_supabase_client):
        """Test retrieving an initiative by ID."""
        mock_response = MagicMock()
        mock_response.data = {
            "id": "init-123",
            "title": "Test Initiative",
            "status": "active"
        }
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = await service.get_initiative("init-123")

        assert result["id"] == "init-123"

    @pytest.mark.asyncio
    async def test_update_initiative(self, service, mock_supabase_client):
        """Test updating an initiative."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "init-123",
            "status": "active",
            "progress": 50
        }]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.update_initiative("init-123", status="active", progress=50)

        assert result["status"] == "active"
        assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_delete_initiative(self, service, mock_supabase_client):
        """Test deleting an initiative."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "init-123"}]
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

        result = await service.delete_initiative("init-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_list_initiatives(self, service, mock_supabase_client):
        """Test listing initiatives with filters."""
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "init-1", "title": "Initiative 1", "status": "active"},
            {"id": "init-2", "title": "Initiative 2", "status": "active"}
        ]
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = await service.list_initiatives(status="active")

        assert len(result) == 2
        assert result[0]["id"] == "init-1"
