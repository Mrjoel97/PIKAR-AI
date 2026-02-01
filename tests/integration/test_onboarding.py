import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.user_onboarding_service import (
    UserOnboardingService, 
    BusinessContextInput, 
    PreferencesInput
)

@pytest.fixture
def mock_supabase():
    with patch('app.services.user_onboarding_service.create_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_agent_factory():
    with patch('app.services.user_onboarding_service.get_user_agent_factory') as mock:
        factory = MagicMock()
        mock.return_value = factory
        yield factory

@pytest.fixture
def service(mock_supabase, mock_agent_factory, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    return UserOnboardingService()

@pytest.mark.asyncio
async def test_start_onboarding_new_user(service, mock_supabase):
    user_id = "new-user"
    
    # Mock status check - no record
    mock_supabase.table().select().eq().single().execute.side_effect = Exception("No record")
    
    # Mock upsert
    mock_supabase.table().upsert().execute.return_value = MagicMock()
    
    result = await service.start_onboarding(user_id)
    
    assert result.success is True
    assert result.step == "welcome"
    assert result.next_step == "business_context"
    mock_supabase.table.assert_any_call("user_executive_agents")

@pytest.mark.asyncio
async def test_submit_business_context(service, mock_supabase):
    user_id = "test-user"
    context = BusinessContextInput(
        company_name="Test Co",
        industry="Tech",
        goals=["Growth"]
    )
    
    # Mock update
    mock_supabase.table().update().eq().execute.return_value.data = [{"user_id": user_id}]
    # Mock progress check response
    mock_supabase.table().select().eq().single().execute.return_value.data = {
        "user_id": user_id,
        "business_context": context.model_dump(),
        "onboarding_completed": False
    }
    
    result = await service.submit_business_context(user_id, context)
    
    assert result.success is True
    assert result.step == "business_context"
    assert result.next_step == "preferences"

@pytest.mark.asyncio
async def test_complete_onboarding(service, mock_supabase, mock_agent_factory):
    user_id = "test-user"
    
    # Mock update
    mock_supabase.table().update().eq().execute.return_value = MagicMock()
    # Mock agent creation
    mock_agent = MagicMock()
    mock_agent.name = "Assistant"
    mock_agent_factory.create_executive_agent = AsyncMock(return_value=mock_agent)
    
    # Mock status check response
    mock_supabase.table().select().eq().single().execute.return_value.data = {
        "user_id": user_id,
        "onboarding_completed": True
    }
    
    result = await service.complete_onboarding(user_id, agent_name="My AI")
    
    assert result.success is True
    assert result.step == "complete"
    assert "Assistant" in result.message
    mock_agent_factory.invalidate_cache.assert_called_with(user_id)

@pytest.mark.asyncio
async def test_skip_onboarding(service, mock_supabase):
    user_id = "test-user"
    mock_supabase.table().upsert().execute.return_value = MagicMock()
    mock_supabase.table().select().eq().single().execute.return_value.data = {
        "user_id": user_id,
        "onboarding_completed": True
    }
    
    result = await service.skip_onboarding(user_id)
    assert result.success is True
    assert result.step == "complete"

@pytest.mark.asyncio
async def test_reset_onboarding(service, mock_supabase, mock_agent_factory):
    user_id = "test-user"
    mock_supabase.table().update().eq().execute.return_value = MagicMock()
    mock_supabase.table().select().eq().single().execute.return_value.data = {
        "user_id": user_id,
        "onboarding_completed": False
    }
    
    result = await service.reset_onboarding(user_id)
    assert result.success is True
    assert result.step == "welcome"
    mock_agent_factory.invalidate_cache.assert_called_with(user_id)
