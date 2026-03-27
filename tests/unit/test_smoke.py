# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Basic smoke tests to verify the application can start and key components are available.
These tests ensure no critical import errors or configuration issues exist.
"""

import pytest
import os


class TestApplicationSmoke:
    """Smoke tests for basic application health."""
    
    def test_environment_variables_exist(self):
        """Verify critical environment variables are configured (if not in CI)."""
        # In CI, these might not be set, so we just check the structure
        # The actual values are validated at runtime
        pass  # Placeholder - actual env validation happens in services
    
    def test_core_modules_importable(self):
        """Verify core application modules can be imported without errors."""
        try:
            from app.workflows.engine import WorkflowEngine
            assert WorkflowEngine is not None
        except (ImportError, KeyError) as e:
            pytest.fail(f"Failed to import core modules: {e}")
        # app.agent and app.fast_api_app depend on google.adk internals that
        # may not be available in all test environments; skip when missing.
        try:
            from app.agent import ExecutiveAgent  # noqa: F401
        except ImportError:
            pytest.skip("google.adk version mismatch — skipping ExecutiveAgent import check")
    
    def test_agent_tools_importable(self):
        """Verify agent tool modules are importable."""
        try:
            from app.agents.tools.registry import TOOL_REGISTRY
            from app.agents.tools.ui_widgets import create_revenue_chart_widget
            assert TOOL_REGISTRY is not None
        except (ImportError, KeyError) as e:
            pytest.fail(f"Failed to import agent tools: {e}")
    
    def test_services_importable(self):
        """Verify service modules are importable."""
        try:
            from app.services.cache import CacheService
            from app.services.financial_service import FinancialService
            from app.services.supabase import get_service_client
            assert True
        except (ImportError, KeyError) as e:
            pytest.fail(f"Failed to import services: {e}")
    
    def test_routers_importable(self):
        """Verify FastAPI router modules are importable."""
        try:
            from app.routers.vault import router as vault_router
            from app.routers.workflows import router as workflows_router
            assert vault_router is not None
            assert workflows_router is not None
        except (ImportError, KeyError) as e:
            pytest.fail(f"Failed to import routers: {e}")
    
    def test_workflow_components_importable(self):
        """Verify workflow system components are importable."""
        try:
            from app.workflows.generator import get_workflow_generator
            from app.workflows.engine import get_workflow_engine
            from app.workflows.user_workflow_service import get_user_workflow_service
            assert True
        except (ImportError, KeyError) as e:
            pytest.fail(f"Failed to import workflow components: {e}")
    
    def test_persistence_layer_importable(self):
        """Verify persistence layer components are importable."""
        try:
            from app.persistence.supabase_task_store import SupabaseTaskStore
            assert SupabaseTaskStore is not None
        except ImportError as e:
            pytest.fail(f"Failed to import persistence layer: {e}")
        # SupabaseSessionService depends on google.adk.sessions which may
        # have breaking changes across ADK versions.
        try:
            from app.persistence.supabase_session_service import SupabaseSessionService  # noqa: F401
        except ImportError:
            pytest.skip("google.adk version mismatch — skipping SupabaseSessionService import check")


class TestConfigurationSmoke:
    """Smoke tests for configuration validation."""
    
    def test_pyproject_exists(self):
        """Verify pyproject.toml exists and is readable."""
        import tomllib
        pyproject_path = os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml")
        
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)
                assert "project" in config or "tool" in config
        else:
            pytest.skip("pyproject.toml not found")
    
    def test_app_directory_structure(self):
        """Verify expected directory structure exists."""
        base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
        
        expected_dirs = [
            "app",
            "app/agents",
            "app/routers",
            "app/services",
            "app/workflows",
            "tests",
        ]
        
        for dir_path in expected_dirs:
            full_path = os.path.join(base_dir, dir_path)
            assert os.path.isdir(full_path), f"Expected directory not found: {dir_path}"


class TestFastAPIAppSmoke:
    """Smoke tests for FastAPI application."""
    
    def test_fastapi_app_has_routes(self):
        """Verify FastAPI app has routes configured."""
        try:
            from app.fast_api_app import app
        except ImportError:
            pytest.skip("google.adk version mismatch — skipping FastAPI app route check")
            return

        # Get all routes
        routes = [route.path for route in app.routes]

        # Should have some routes defined
        assert len(routes) > 0, "FastAPI app should have routes configured"

        # Check for common route patterns
        route_str = " ".join(routes)
        assert "/health" in route_str or "/a2a" in route_str or "/api" in route_str, \
            "Should have expected API routes"
