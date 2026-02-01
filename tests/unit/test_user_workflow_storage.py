import pytest
from unittest.mock import MagicMock, patch
from app.workflows.user_workflow_service import UserWorkflowService

@pytest.fixture
def mock_supabase():
    with patch('app.workflows.user_workflow_service.create_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def service(mock_supabase, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    return UserWorkflowService()

@pytest.mark.asyncio
async def test_save_workflow(service, mock_supabase):
    user_id = "test-user"
    workflow_name = "test-workflow"
    
    # Mock response
    mock_supabase.table().upsert().execute.return_value.data = [{"workflow_name": workflow_name}]
    
    result = await service.save_workflow(
        user_id=user_id,
        workflow_name=workflow_name,
        workflow_pattern="sequential",
        agent_ids=["strategic", "data"],
        request_pattern="test request",
        workflow_config={"agents": ["strategic", "data"]}
    )
    
    assert result["workflow_name"] == workflow_name
    mock_supabase.table.assert_called_with("user_workflows")

@pytest.mark.asyncio
async def test_get_workflow(service, mock_supabase):
    user_id = "test-user"
    workflow_name = "test-workflow"
    
    mock_supabase.table().select().eq().eq().single().execute.return_value.data = {"workflow_name": workflow_name}
    
    result = await service.get_workflow(user_id, workflow_name)
    assert result["workflow_name"] == workflow_name

@pytest.mark.asyncio
async def test_list_workflows(service, mock_supabase):
    user_id = "test-user"
    mock_supabase.table().select().eq().order().limit().execute.return_value.data = [{"workflow_name": "w1"}]
    
    result = await service.list_workflows(user_id)
    assert len(result) == 1
    assert result[0]["workflow_name"] == "w1"

@pytest.mark.asyncio
async def test_find_matching_workflow(service, mock_supabase):
    user_id = "test-user"
    # Mock list_workflows response
    mock_supabase.table().select().eq().order().limit().execute.return_value.data = [
        {
            "workflow_name": "w1",
            "request_pattern": "financial analysis report",
            "usage_count": 5
        },
        {
            "workflow_name": "w2",
            "request_pattern": "marketing social media",
            "usage_count": 1
        }
    ]
    
    # Match against "analyze finances"
    result = await service.find_matching_workflow(user_id, "analyze finances and create report", threshold=0.1)
    assert result is not None
    assert result["workflow_name"] == "w1"

@pytest.mark.asyncio
async def test_update_workflow_usage(service, mock_supabase):
    user_id = "test-user"
    workflow_name = "w1"
    
    # Mock get_workflow
    mock_supabase.table().select().eq().eq().single().execute.return_value.data = {"usage_count": 5}
    # Mock update
    mock_supabase.table().update().eq().eq().execute.return_value.data = [{"usage_count": 6}]
    
    result = await service.update_workflow_usage(user_id, workflow_name)
    assert result["usage_count"] == 6

def test_normalize_request(service):
    request = "I want a Financial Analysis for my project!"
    normalized = service.normalize_request(request)
    # financial, analysis, project should remain
    # i, want, a, for, my should be removed as stopwords
    assert "financial" in normalized
    assert "analysis" in normalized
    assert "project" in normalized
    assert "want" not in normalized

def test_generate_workflow_name(service):
    agents = ["data", "strategic"]
    name = service.generate_workflow_name(agents, "sequential")
    assert name.startswith("sequential_data_strategic_")
