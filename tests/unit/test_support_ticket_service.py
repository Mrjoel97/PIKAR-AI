"""Unit tests for SupportTicketService.

Tests CRUD operations for tickets used by CustomerSupportAgent.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestSupportTicketService:
    """Test suite for SupportTicketService."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def service(self, mock_supabase_client):
        """Create SupportTicketService with mocked dependencies."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key',
            'SUPABASE_ANON_KEY': 'anon-key'
        }):
            with patch('supabase.create_client') as mock_create:
                mock_create.return_value = mock_supabase_client
                # Import here to ensure patch is active during usage if it does import time stuff (it doesn't, but safe)
                from app.services.support_ticket_service import SupportTicketService
                return SupportTicketService()

    def test_initialization_success(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service._table_name == "support_tickets"

    @pytest.mark.asyncio
    async def test_create_ticket(self, service, mock_supabase_client):
        """Test creating a ticket."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "tkt-1",
            "subject": "Login Issue",
            "status": "new"
        }]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response

        try:
            result = await service.create_ticket(
                subject="Login Issue",
                description="Can't login",
                customer_email="user@example.com"
            )
            print(f"DEBUG: create_ticket result: {result}")
            assert result["id"] == "tkt-1"
            assert result["status"] == "new"
        except Exception as e:
            print(f"DEBUG: create_ticket FAILED with: {e}")
            raise e

    @pytest.mark.asyncio
    async def test_get_ticket(self, service, mock_supabase_client):
        """Test retrieving a ticket."""
        mock_response = MagicMock()
        mock_response.data = {"id": "tkt-1", "subject": "Issue"}
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        try:
            result = await service.get_ticket("tkt-1")
            print(f"DEBUG: get_ticket result: {result}")
            assert result["id"] == "tkt-1"
        except Exception as e:
            print(f"DEBUG: get_ticket FAILED with: {e}")
            raise e

    @pytest.mark.asyncio
    async def test_delete_ticket(self, service, mock_supabase_client):
        """Test deleting a ticket."""
        mock_response = MagicMock()
        mock_response.data = [{"id": "tkt-1"}]
        # Debug: Print what we are setting
        print(f"DEBUG TEST: Setting mock_response.data = {mock_response.data}")
        
        # Setup chain
        mock_execute = MagicMock(return_value=mock_response)
        mock_eq = MagicMock()
        mock_eq.execute = mock_execute
        mock_delete = MagicMock()
        mock_delete.eq = MagicMock(return_value=mock_eq)
        mock_table = MagicMock()
        mock_table.delete = MagicMock(return_value=mock_delete)
        mock_supabase_client.table.return_value = mock_table
        
        # Verify chain locally
        print(f"DEBUG TEST: Verification chain: {mock_supabase_client.table('t').delete().eq('id', '1').execute().data}")

        try:
            result = await service.delete_ticket("tkt-1")
            print(f"DEBUG: delete_ticket result: {result}")
            assert result is True
        except Exception as e:
            print(f"DEBUG: delete_ticket FAILED with: {e}")
            raise e
