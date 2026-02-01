"""Pytest configuration for unit tests.

This file sets up mocks for google.adk and other heavy dependencies
BEFORE any test modules are imported, allowing isolated unit testing.
"""
import sys
from unittest.mock import MagicMock


class MockAgent:
    """Mock Agent class that captures constructor kwargs as attributes."""
    
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "MockAgent")
        self.model = kwargs.get("model", "mock-model")
        self.description = kwargs.get("description", "")
        self.instruction = kwargs.get("instruction", "")
        self.tools = kwargs.get("tools", [])
        # Structured output attributes
        self.output_schema = kwargs.get("output_schema", None)
        self.output_key = kwargs.get("output_key", None)
        self.sub_agents = kwargs.get("sub_agents", [])
        self.include_contents = kwargs.get("include_contents", "all")
        self._kwargs = kwargs


class MockApp:
    """Mock App class that captures constructor kwargs as attributes."""
    
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "MockApp")
        self.root_agent = kwargs.get("root_agent", None)
        self._kwargs = kwargs


def pytest_configure(config):
    """Called before test collection. Set up mocks for external dependencies."""
    # Create mock modules
    mock_google = MagicMock()
    mock_genai = MagicMock()
    mock_genai_types = MagicMock()
    mock_adk = MagicMock()
    mock_adk_agents = MagicMock()
    mock_adk_apps = MagicMock()
    mock_adk_app = MagicMock()
    mock_adk_models = MagicMock()
    
    # Configure Agent to use our MockAgent class
    mock_adk_agents.Agent = MockAgent
    mock_adk_apps.App = MockApp
    
    # Wire up the module hierarchy
    mock_google.genai = mock_genai
    mock_google.adk = mock_adk
    mock_genai.types = mock_genai_types
    mock_adk.agents = mock_adk_agents
    mock_adk.apps = mock_adk_apps
    
    # Set up modules
    sys.modules["google"] = mock_google
    sys.modules["google.genai"] = mock_genai
    sys.modules["google.genai.types"] = mock_genai_types
    sys.modules["google.adk"] = mock_adk
    sys.modules["google.adk.agents"] = mock_adk_agents
    sys.modules["google.adk.apps"] = mock_adk_apps
    sys.modules["google.adk.apps.app"] = mock_adk_app
    sys.modules["google.adk.models"] = mock_adk_models
    sys.modules["google.adk.agents.context_cache_config"] = MagicMock()
    sys.modules["google.adk.apps.events_compaction_config"] = MagicMock()
    
    # OpenTelemetry
    sys.modules["opentelemetry"] = MagicMock()
    sys.modules["opentelemetry.instrumentation"] = MagicMock()
    sys.modules["opentelemetry.instrumentation.google_genai"] = MagicMock()
    
    # Vertex AI for embedding service
    sys.modules["vertexai"] = MagicMock()
    sys.modules["vertexai.language_models"] = MagicMock()

