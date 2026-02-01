"""Unit tests for ContentService."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.content_service import ContentService


def test_content_service_initialization():
    obj = ContentService()
    assert obj is not None


@patch("app.services.content_service.ingest_document_content")
@pytest.mark.asyncio
async def test_save_content(mock_ingest):
    # Setup
    mock_ingest.return_value = {"success": True, "ids": ["123"]}
    service = ContentService()
    
    # Act
    result = await service.save_content("My Title", "My Content", "agent-1")
    
    # Assert
    assert result["success"] is True
    mock_ingest.assert_called_once()
    call_args = mock_ingest.call_args[1]
    assert call_args["content"] == "My Content"
    assert call_args["title"] == "My Title"
    assert call_args["agent_id"] == "agent-1"


@patch("app.services.content_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_get_content(mock_create_client):
    """Test retrieving content by ID."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_single = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.single.return_value = mock_single
    mock_single.execute.return_value = mock_execute
    
    mock_execute.data = {"id": "123", "title": "Test", "content": "Hello"}
    
    service = ContentService()
    result = await service.get_content("123")
    
    assert result["id"] == "123"
    assert result["title"] == "Test"


@patch("app.services.content_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_update_content(mock_create_client):
    """Test updating content."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute.return_value = mock_execute
    
    mock_execute.data = [{"id": "123", "title": "Updated Title"}]
    
    service = ContentService()
    result = await service.update_content("123", title="Updated Title")
    
    assert result["title"] == "Updated Title"


@patch("app.services.content_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_delete_content(mock_create_client):
    """Test deleting content."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_eq = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.eq.return_value = mock_eq
    mock_eq.execute.return_value = mock_execute
    
    mock_execute.data = [{"id": "123"}]
    
    service = ContentService()
    result = await service.delete_content("123")
    
    assert result is True


@patch("app.services.content_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_list_content(mock_create_client):
    """Test listing content with filters."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit
    mock_limit.execute.return_value = mock_execute
    
    mock_execute.data = [
        {"id": "1", "title": "Post 1"},
        {"id": "2", "title": "Post 2"}
    ]
    
    service = ContentService()
    result = await service.list_content(content_type="blog")
    
    assert len(result) == 2
    assert result[0]["title"] == "Post 1"
