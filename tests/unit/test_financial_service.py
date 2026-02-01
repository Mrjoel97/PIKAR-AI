"""Unit tests for FinancialService."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.financial_service import FinancialService


@patch("app.services.financial_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
def test_financial_service_initialization(mock_create_client):
    # Setup mock
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Act
    service = FinancialService()
    
    # Assert
    assert service is not None
    assert service.client == mock_client

@patch("app.services.financial_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_get_revenue_stats(mock_create_client):
    # Setup mock
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    service = FinancialService()
    
    # Act
    stats = await service.get_revenue_stats()
    
    # Assert
    assert stats["revenue"] == 0.0
    assert stats["currency"] == "USD"
