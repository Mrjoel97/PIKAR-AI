"""Integration tests for MCP (Model Context Protocol) tools.

Tests the MCP tool suite including setup wizard, user configuration,
and integration management functionality.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock


@pytest.fixture
def mock_user_config_service():
    """Create a mock user config service."""
    service = Mock()
    service.get_templates.return_value = [
        Mock(
            id="supabase",
            name="Supabase",
            description="PostgreSQL database",
            category="database",
            docs_url="https://supabase.com/docs",
        ),
        Mock(
            id="resend",
            name="Resend",
            description="Email service",
            category="email",
            docs_url="https://resend.com/docs",
        ),
    ]
    service.save_integration.return_value = {
        "success": True,
        "integration_id": "test-int-123",
        "message": "Integration saved",
    }
    service.activate_integration.return_value = True
    service.get_user_integrations.return_value = []
    return service


class TestMCPListAvailableIntegrations:
    """Test mcp_list_available_integrations tool."""

    def test_returns_all_integrations(self, mock_user_config_service):
        """Should return all available integrations."""
        from app.mcp.tools.setup_wizard import mcp_list_available_integrations
        
        with patch('app.mcp.tools.setup_wizard.get_user_config_service', return_value=mock_user_config_service):
            result = mcp_list_available_integrations()
        
        assert result["success"] is True
        assert len(result["integrations"]) == 2
        assert result["integrations"][0]["id"] == "supabase"
        assert result["integrations"][1]["id"] == "resend"
        assert "categories" in result

    def test_filters_by_category(self, mock_user_config_service):
        """Should filter integrations by category."""
        from app.mcp.tools.setup_wizard import mcp_list_available_integrations
        
        with patch('app.mcp.tools.setup_wizard.get_user_config_service', return_value=mock_user_config_service):
            result = mcp_list_available_integrations(category="database")
        
        assert result["success"] is True
        assert len(result["integrations"]) == 1
        assert result["integrations"][0]["category"] == "database"


class TestMCPGetIntegrationRequirements:
    """Test mcp_get_integration_requirements tool."""

    def test_returns_requirements_for_valid_integration(self):
        """Should return requirements for a valid integration type."""
        from app.mcp.tools.setup_wizard import mcp_get_integration_requirements
        
        result = mcp_get_integration_requirements("supabase")
        
        assert result["success"] is True
        assert result["integration_type"] == "supabase"
        assert "required_fields" in result
        assert "optional_fields" in result
        assert "setup_instructions" in result
        assert result["docs_url"] == "https://supabase.com/docs"

    def test_returns_error_for_invalid_integration(self):
        """Should return error for invalid integration type."""
        from app.mcp.tools.setup_wizard import mcp_get_integration_requirements
        
        result = mcp_get_integration_requirements("invalid_integration")
        
        assert result["success"] is False
        assert "error" in result
        assert "available_types" in result


class TestMCPValidateAPIKey:
    """Test mcp_validate_api_key tool."""

    @pytest.mark.parametrize("integration,field,value,expected_valid", [
        ("supabase", "url", "https://test.supabase.co", True),
        ("supabase", "url", "invalid-url", False),
        ("resend", "api_key", "re_test123", True),
        ("resend", "api_key", "invalid_key", False),
        ("slack", "webhook_url", "https://hooks.slack.com/services/test", True),
        ("slack", "webhook_url", "https://invalid.com", False),
    ])
    def test_validates_api_key_format(self, integration, field, value, expected_valid):
        """Should validate API key format correctly."""
        from app.mcp.tools.setup_wizard import mcp_validate_api_key
        
        result = mcp_validate_api_key(integration, field, value)
        
        assert result["success"] is True
        assert result["valid"] is expected_valid

    def test_accepts_any_value_for_unknown_fields(self):
        """Should accept any non-empty value for unknown fields."""
        from app.mcp.tools.setup_wizard import mcp_validate_api_key
        
        result = mcp_validate_api_key("custom", "unknown_field", "some_value")
        
        assert result["success"] is True
        assert result["valid"] is True

    def test_rejects_empty_values(self):
        """Should reject empty values."""
        from app.mcp.tools.setup_wizard import mcp_validate_api_key
        
        result = mcp_validate_api_key("supabase", "url", "")
        
        assert result["success"] is True
        assert result["valid"] is False


class TestMCPTestIntegration:
    """Test mcp_test_integration tool."""

    @pytest_asyncio.fixture
    async def test_supabase_connection(self):
        """Test Supabase connection validation."""
        from app.mcp.tools.setup_wizard import _test_supabase
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await _test_supabase({
                "url": "https://test.supabase.co",
                "anon_key": "test_key"
            })
            
            assert result["success"] is True
            assert "Connected to Supabase" in result["message"]

    @pytest_asyncio.fixture
    async def test_resend_connection(self):
        """Test Resend connection validation."""
        from app.mcp.tools.setup_wizard import _test_resend
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await _test_resend({"api_key": "re_test123"})
            
            assert result["success"] is True
            assert "Connected to Resend" in result["message"]


class TestMCPSaveIntegration:
    """Test mcp_save_integration tool."""

    def test_saves_integration_successfully(self, mock_user_config_service):
        """Should save integration configuration."""
        from app.mcp.tools.setup_wizard import mcp_save_integration
        
        with patch('app.mcp.tools.setup_wizard.get_user_config_service', return_value=mock_user_config_service):
            result = mcp_save_integration(
                user_id="user-123",
                integration_type="supabase",
                config={"url": "https://test.supabase.co", "anon_key": "test"},
                display_name="My Supabase"
            )
        
        assert result["success"] is True
        assert "integration_id" in result
        mock_user_config_service.save_integration.assert_called_once()


class TestMCPActivateIntegration:
    """Test mcp_activate_integration tool."""

    def test_activates_integration_successfully(self, mock_user_config_service):
        """Should activate integration successfully."""
        from app.mcp.tools.setup_wizard import mcp_activate_integration
        
        with patch('app.mcp.tools.setup_wizard.get_user_config_service', return_value=mock_user_config_service):
            result = mcp_activate_integration("user-123", "int-123")
        
        assert result["success"] is True
        assert "activated" in result["message"].lower()

    def test_fails_when_activation_fails(self, mock_user_config_service):
        """Should return failure when activation fails."""
        from app.mcp.tools.setup_wizard import mcp_activate_integration
        
        mock_user_config_service.activate_integration.return_value = False
        
        with patch('app.mcp.tools.setup_wizard.get_user_config_service', return_value=mock_user_config_service):
            result = mcp_activate_integration("user-123", "int-123")
        
        assert result["success"] is False
        assert "Could not activate" in result["message"]


class TestMCPGetUserIntegrations:
    """Test mcp_get_user_integrations tool."""

    def test_returns_user_integrations(self, mock_user_config_service):
        """Should return user's integrations."""
        from app.mcp.tools.setup_wizard import mcp_get_user_integrations
        
        mock_user_config_service.get_user_integrations.return_value = [
            Mock(
                id="int-1",
                integration_type="supabase",
                display_name="My Supabase",
                is_active=True,
                test_status="passed",
                last_tested_at=None,
            ),
            Mock(
                id="int-2",
                integration_type="resend",
                display_name="My Resend",
                is_active=False,
                test_status="pending",
                last_tested_at=None,
            ),
        ]
        
        with patch('app.mcp.tools.setup_wizard.get_user_config_service', return_value=mock_user_config_service):
            result = mcp_get_user_integrations("user-123")
        
        assert result["success"] is True
        assert len(result["integrations"]) == 2
        assert result["active_count"] == 1
        assert result["total_count"] == 2


class TestMCPSetupToolsExport:
    """Test MCP_SETUP_TOOLS export."""

    def test_all_tools_exported(self):
        """Should export all MCP setup tools."""
        from app.mcp.tools.setup_wizard import MCP_SETUP_TOOLS
        
        assert len(MCP_SETUP_TOOLS) == 7
        tool_names = [t.__name__ for t in MCP_SETUP_TOOLS]
        
        expected_tools = [
            "mcp_list_available_integrations",
            "mcp_get_integration_requirements",
            "mcp_validate_api_key",
            "mcp_test_integration",
            "mcp_save_integration",
            "mcp_activate_integration",
            "mcp_get_user_integrations",
        ]
        
        for tool in expected_tools:
            assert tool in tool_names, f"Missing tool: {tool}"
