"""Unit tests for TaskService."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.task_service import TaskService


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
def test_task_service_initialization(mock_create_client):
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    service = TaskService()
    assert service is not None
    assert service.client == mock_client


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_create_task(mock_create_client):
    # Setup
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    # Mock the chain: table('ai_jobs').insert().execute()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute
    
    # Mock response
    mock_execute.data = [{"id": "123", "status": "pending"}]
    
    service = TaskService()
    
    # Act
    result = await service.create_task("Test Task", "agent-123", "user-abc")
    
    # Assert
    mock_client.table.assert_called_with("ai_jobs")
    mock_table.insert.assert_called()
    assert result["id"] == "123"
    assert result["status"] == "pending"


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_get_task(mock_create_client):
    """Test retrieving a single task by ID."""
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
    
    mock_execute.data = {"id": "123", "status": "pending", "input_data": {"description": "Test"}}
    
    service = TaskService()
    result = await service.get_task("123")
    
    mock_client.table.assert_called_with("ai_jobs")
    mock_table.select.assert_called_with("*")
    mock_select.eq.assert_called_with("id", "123")
    assert result["id"] == "123"


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_update_task(mock_create_client):
    """Test updating a task's status."""
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
    
    mock_execute.data = [{"id": "123", "status": "completed"}]
    
    service = TaskService()
    result = await service.update_task("123", status="completed")
    
    mock_client.table.assert_called_with("ai_jobs")
    mock_table.update.assert_called()
    assert result["status"] == "completed"


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_delete_task(mock_create_client):
    """Test deleting a task."""
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
    
    service = TaskService()
    result = await service.delete_task("123")
    
    mock_client.table.assert_called_with("ai_jobs")
    mock_table.delete.assert_called()
    assert result is True


@patch("app.services.task_service.create_client")
@patch.dict("os.environ", {"SUPABASE_URL": "http://test", "SUPABASE_SERVICE_ROLE_KEY": "test"})
@pytest.mark.asyncio
async def test_list_tasks(mock_create_client):
    """Test listing tasks with optional filters."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_order = MagicMock()
    mock_execute = MagicMock()
    
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.order.return_value = mock_order
    mock_order.execute.return_value = mock_execute
    
    mock_execute.data = [
        {"id": "1", "status": "pending"},
        {"id": "2", "status": "pending"}
    ]
    
    service = TaskService()
    result = await service.list_tasks(status="pending")
    
    mock_client.table.assert_called_with("ai_jobs")
    assert len(result) == 2
    assert result[0]["id"] == "1"
