"""Integration tests for the Adaptive Ecosystem.

Verifies:
1. UserOnboardingService correctly classifies personas.
2. UserAgentFactory injects the correct context.
3. JourneyDiscoveryService proposes workflows.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure apps is in path to import backend
sys.path.append(os.path.join(os.getcwd(), "apps"))

# Mock google.adk dependencies BEFORE importing agent
# This allows agent module to load even if ADK is missing
sys.modules["google.adk"] = MagicMock()
sys.modules["google.adk.agents"] = MagicMock()
sys.modules["google.adk.models"] = MagicMock()
sys.modules["google.adk.types"] = MagicMock()
sys.modules["google.adk.events"] = MagicMock()
sys.modules["google.adk.runtime"] = MagicMock()
sys.modules["google.genai"] = MagicMock()
sys.modules["google.genai.types"] = MagicMock()

# Alias 'backend' as 'app' to satisfy project imports
try:
    import backend
    sys.modules["app"] = backend
    
    # Explicitly import agent to register it in backend namespace
    import apps.backend.agent
except ImportError as e:
    print(f"Test Setup Warning: Failed to import backend or agent: {e}") 
except Exception as e:
    print(f"Test Setup Error: {e}")

# Also ensure backend root is in path if needed for relative imports inside it
sys.path.append(os.path.join(os.getcwd(), "apps", "backend"))

from app.services.user_onboarding_service import (
    UserOnboardingService,
    UserPersona,
    BusinessContextInput,
    get_user_onboarding_service
)
from app.services.user_agent_factory import UserAgentFactory
from app.services.journey_discovery import JourneyDiscoveryService, DiscoveredPattern
# The following line was malformed in the user's request. Assuming it was intended to be a separate import.
# If 'Geminiv' was a typo for 'Gemini' and meant to be imported from 'google.generativeai',
# or if it was meant to be part of a fixture, please clarify.
# For now, I'm placing it as a standalone import, assuming 'google.adk.models' is a valid module.
# If this import is not needed or is incorrect, it should be removed or corrected in a subsequent instruction.
# from google.adk.models import Geminiv # This line is commented out as it causes a syntax error with the fixture.
                                      # If it's a valid import, it should be placed correctly.

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://mock.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "mock-key")

@pytest.fixture
def mock_supabase(mock_env):
    with patch("app.services.user_onboarding_service.create_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_supabase_factory(mock_env):
    with patch("app.services.user_agent_factory.create_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def onboarding_service(mock_supabase):
    return UserOnboardingService()

@pytest.fixture
def agent_factory(mock_supabase_factory):
    return UserAgentFactory()

@pytest.fixture
def discovery_service():
    return JourneyDiscoveryService()

class TestAdaptiveOnboarding:
    
    def test_persona_classification_solopreneur(self, onboarding_service):
        context = {"team_size": "1", "role": "Freelancer"}
        persona = onboarding_service._determine_persona(context)
        assert persona == UserPersona.SOLOPRENEUR

    def test_persona_classification_startup(self, onboarding_service):
        context = {"team_size": "11-50", "role": "Founder"}
        persona = onboarding_service._determine_persona(context)
        assert persona == UserPersona.STARTUP

    def test_persona_classification_sme(self, onboarding_service):
        context = {"team_size": "51-200", "role": "Director"}
        persona = onboarding_service._determine_persona(context)
        assert persona == UserPersona.SME

    def test_persona_classification_enterprise(self, onboarding_service):
        context = {"team_size": "200+", "role": "VP"}
        persona = onboarding_service._determine_persona(context)
        assert persona == UserPersona.ENTERPRISE

class TestRealTimeTracking:
    @pytest.mark.asyncio
    async def test_telemetry_callback_logs_activity(self):
        # Mock Context and Event
        mock_context = MagicMock()
        mock_context.session.state = {"user_id": "test_user_tracking"}
        
        mock_event = MagicMock()
        mock_event.tool_name = "test_tool"
        
        # Mock Service
        # Note: Unpatcher is not defined in the provided context, assuming it's a placeholder
        # or a custom utility. For a standard unittest.mock.patch, it's usually handled
        # by the 'with' statement itself.
        # If Unpatcher is a custom class, it would need to be imported or defined.
        # For this exercise, I will assume it's a conceptual placeholder for ensuring
        # proper patching/unpatching.
        # with Unpatcher(): # Ensure we patch where it is imported in agent.py
        # with Unpatcher(): # Ensure we patch where it is imported in agent.py
        with patch("app.agent.get_journey_discovery_service") as mock_get_service:
            mock_service_instance = AsyncMock()
            mock_get_service.return_value = mock_service_instance
            
            # Import the callback to test
            from app.agent import telemetry_callback
            
            await telemetry_callback(mock_event, mock_context)
            
            mock_service_instance.log_activity.assert_called_once_with(
                user_id="test_user_tracking",
                action="tool_use",
                details="Tool: test_tool"
            )


class TestPersonaContextInjection:
    
    def test_inject_persona_context(self, agent_factory):
        base_instruction = "## YOUR ROLE\nYou are a helpful assistant."
        
        # Test Solopreneur
        enhanced = agent_factory._inject_persona_context(base_instruction, "solopreneur")
        assert "## YOUR USER PERSONA: SOLOPRENEUR" in enhanced
        assert "Efficiency, Action" in enhanced

        # Test Enterprise
        enhanced = agent_factory._inject_persona_context(base_instruction, "enterprise")
        assert "## YOUR USER PERSONA: ENTERPRISE EXECUTIVE" in enhanced
        assert "Strategy, Security" in enhanced

@pytest.mark.asyncio
class TestJourneyDiscovery:
    
    async def test_analyze_activity_mock(self):
        # Create the service
        service = JourneyDiscoveryService()
        
        # Replace the .model attribute entirely with a MagicMock to bypass Pydantic checks
        # on the Gemini object itself.
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
            [
                {
                    "description": "Repeated email check",
                    "frequency": 5,
                    "confidence": 0.9,
                    "suggested_goal": "Automate email check",
                    "suggested_context": "User checks email manually 5 times"
                }
            ]
        """
        # Mock the async method
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Inject the mock model into the service
        service.model = mock_model
        
        patterns = await service.analyze_user_activity("user_123", [{"action": "test", "timestamp": "now", "details": "d"} for _ in range(6)])
        
        assert len(patterns) == 1
        assert patterns[0].description == "Repeated email check"
        assert patterns[0].suggested_goal == "Automate email check"

if __name__ == "__main__":
    # Manually run tests if executed as script
    # pytest.main([__file__])
    pass
