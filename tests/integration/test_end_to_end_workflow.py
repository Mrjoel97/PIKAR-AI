import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from google.adk.agents import InvocationContext, BaseAgent
from google.adk.sessions import Session, InMemorySessionService
from google.adk.events import Event, EventActions
from google.genai import types as genai_types

from app.workflows.dynamic import DynamicWorkflowGenerator

@pytest.fixture
def mock_supabase():
    with patch('app.workflows.user_workflow_service.create_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_agent_factories():
    with patch('app.workflows.dynamic.AGENT_FACTORY_REGISTRY') as mock_registry:
        # Create mock agents that are instances of BaseAgent (or similar) to pass validation
        strategic_mock = MagicMock(spec=BaseAgent)
        strategic_mock.name = "StrategicPlanningAgent_dynamic"
        strategic_mock.parent_agent = None  # Essential for ADK validation
        strategic_mock.run_async = MagicMock()
        
        data_mock = MagicMock(spec=BaseAgent)
        data_mock.name = "DataAnalysisAgent_dynamic"
        data_mock.parent_agent = None  # Essential for ADK validation
        data_mock.run_async = MagicMock()
        
        registry = {
            "strategic": MagicMock(return_value=strategic_mock),
            "data": MagicMock(return_value=data_mock)
        }
        mock_registry.get.side_effect = registry.get
        mock_registry.keys.return_value = registry.keys()
        mock_registry.__contains__.side_effect = lambda x: x in registry
        yield registry

@pytest.mark.asyncio
async def test_dynamic_workflow_e2e_flow(mock_supabase, mock_agent_factories, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    
    generator = DynamicWorkflowGenerator()
    generator._analyze_intent = MagicMock(return_value=["strategic", "data"])
    generator._determine_pattern = MagicMock(return_value="sequential")
    
    # Setup context
    session = Session(
        id="test-session", 
        app_name="pikar-ai",
        user_id="user-123",
        state={"user_id": "user-123", "user_request": "analyze finances and strategy"}
    )
    
    session_service = InMemorySessionService()
    ctx = InvocationContext(
        session=session,
        session_service=session_service,
        invocation_id="test-inv-123",
        agent=generator
    )
    
    # Mock specialized agents' run_async to yield some events
    strategic_agent = mock_agent_factories["strategic"].return_value
    async def strategic_events(context):
        yield Event(author="StrategicPlanningAgent_dynamic", content=genai_types.Content(parts=[genai_types.Part(text="Strategy analyzed")]))
    strategic_agent.run_async.side_effect = strategic_events
    
    data_agent = mock_agent_factories["data"].return_value
    async def data_events(context):
        yield Event(author="DataAnalysisAgent_dynamic", content=genai_types.Content(parts=[genai_types.Part(text="Data analyzed")]))
    data_agent.run_async.side_effect = data_events

    # Mock workflow service save
    with patch('app.workflows.user_workflow_service.UserWorkflowService.save_workflow', new_callable=AsyncMock) as mock_save:
        events = []
        async for event in generator.run_async(ctx):
            print(f"Captured event from {event.author}")
            events.append(event)
            
        # Verify events
        print(f"Total events captured: {len(events)}")
        assert len(events) >= 2
        authors = [e.author for e in events]
        assert "StrategicPlanningAgent_dynamic" in authors
        assert "DataAnalysisAgent_dynamic" in authors
        
        # Verify workflow info in state
        assert "dynamic_workflow" in ctx.session.state
        assert "strategic" in ctx.session.state["dynamic_workflow"]["agents"]
        
        # Verify save_workflow was called
        mock_save.assert_called()
