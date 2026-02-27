"""Pytest configuration for unit tests.

This file sets up mocks for google.adk and other heavy dependencies
BEFORE any test modules are imported, allowing isolated unit testing.
"""
import sys
import types
from typing import Any
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


def _as_package(module: object) -> object:
    """Ensure a module-like object looks like a package to importlib."""
    if not hasattr(module, "__path__"):
        setattr(module, "__path__", [])
    return module


def pytest_configure(config):
    """Called before test collection. Set up mocks for external dependencies."""
    # Keep the top-level `google` package importable so mixed test runs
    # (e.g., app/tests + tests/unit) can still resolve real modules like
    # `google.cloud`. Only mock the specific ADK/GenAI submodules needed by
    # unit tests.
    google_pkg = sys.modules.get("google")
    if google_pkg is None:
        google_pkg = types.ModuleType("google")
        # Mark as package to support submodule imports (google.cloud, etc.)
        google_pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["google"] = google_pkg

    # Create mock modules
    mock_genai = _as_package(types.ModuleType("google.genai"))
    mock_genai_types = MagicMock()
    mock_genai_types.Content = Any
    mock_adk = _as_package(types.ModuleType("google.adk"))
    mock_adk_agents = MagicMock()
    mock_adk_apps = MagicMock()
    mock_adk_app = MagicMock()
    mock_adk_models = MagicMock()
    mock_adk_events = _as_package(types.ModuleType("google.adk.events"))
    mock_adk_events.Event = Any
    mock_adk_events_event = types.ModuleType("google.adk.events.event")
    mock_adk_events_event.Event = Any
    mock_adk_artifacts = MagicMock()
    mock_adk_runners = MagicMock()
    mock_adk_sessions = MagicMock()
    mock_adk_sessions.InMemorySessionService = MagicMock()
    mock_adk_runners.Runner = MagicMock()
    mock_adk_artifacts.GcsArtifactService = MagicMock()
    mock_adk_artifacts.InMemoryArtifactService = MagicMock()

    # Configure Agent to use our MockAgent class
    mock_adk_agents.Agent = MockAgent
    mock_adk_apps.App = MockApp
    
    # Wire up the module hierarchy
    setattr(google_pkg, "genai", mock_genai)
    setattr(google_pkg, "adk", mock_adk)
    mock_genai.types = mock_genai_types
    mock_adk.agents = mock_adk_agents
    mock_adk.apps = mock_adk_apps
    
    # Set up modules
    sys.modules["google.genai"] = mock_genai
    sys.modules["google.genai.types"] = mock_genai_types
    sys.modules["google.adk"] = mock_adk
    sys.modules["google.adk.agents"] = mock_adk_agents
    sys.modules["google.adk.apps"] = mock_adk_apps
    sys.modules["google.adk.apps.app"] = mock_adk_app
    sys.modules["google.adk.models"] = mock_adk_models
    sys.modules["google.adk.events"] = mock_adk_events
    sys.modules["google.adk.events.event"] = mock_adk_events_event
    sys.modules["google.adk.artifacts"] = mock_adk_artifacts
    sys.modules["google.adk.runners"] = mock_adk_runners
    sys.modules["google.adk.sessions"] = mock_adk_sessions
    sys.modules["google.adk.agents.context_cache_config"] = MagicMock()
    sys.modules["google.adk.apps.events_compaction_config"] = MagicMock()
    
    # OpenTelemetry
    sys.modules["opentelemetry"] = MagicMock()
    sys.modules["opentelemetry.instrumentation"] = MagicMock()
    sys.modules["opentelemetry.instrumentation.google_genai"] = MagicMock()
    
    # Vertex AI for embedding service
    sys.modules["vertexai"] = MagicMock()
    sys.modules["vertexai.language_models"] = MagicMock()

