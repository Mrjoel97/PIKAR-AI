"""MCP Connector Module for Pikar AI.

This module provides MCP (Model Context Protocol) connectors that enable
agents to access external services securely.

Features:
- Privacy-safe web search (Tavily) with PII filtering
- Web scraping (Firecrawl) for research and content extraction
- Landing page generation with HTML/React components
- Form submission handling with Supabase storage
- Email notifications for form submissions
- CRM integration (HubSpot) for lead management
- Audit logging for all external service calls
- **User-configurable integrations** (Supabase, Resend, Slack, etc.)
- **AI-assisted setup wizard** for non-technical users

Usage:
    from app.mcp import get_mcp_tools, MCPConnector

    # Get MCP tools for an agent
    tools = get_mcp_tools(["web_search", "web_scrape", "landing_page"])

    # Or use the connector directly
    connector = MCPConnector()
    results = await connector.web_search("market research AI trends")

    # For ADK Agent integration, use get_mcp_agent_tools
    from app.mcp import get_mcp_agent_tools

    agent = Agent(
        name="MyAgent",
        tools=[*existing_tools, *get_mcp_agent_tools()],
    )

    # For integration setup wizard (AI-assisted)
    from app.mcp import get_mcp_setup_tools

    setup_agent = Agent(
        name="IntegrationWizard",
        tools=get_mcp_setup_tools(),
    )
"""

from app.mcp.connector import MCPConnector, get_mcp_tools
from app.mcp.agent_tools import (
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
    get_mcp_agent_tools,
    MCP_TOOLS,
)
from app.mcp.user_config import (
    get_user_config_service,
    UserMCPConfigService,
    INTEGRATION_TEMPLATES,
)
from app.mcp.tools.setup_wizard import (
    mcp_list_available_integrations,
    mcp_get_integration_requirements,
    mcp_validate_api_key,
    mcp_test_integration,
    mcp_save_integration,
    mcp_activate_integration,
    mcp_get_user_integrations,
    MCP_SETUP_TOOLS,
)


def get_mcp_setup_tools():
    """Get MCP setup wizard tools for agent integration."""
    return MCP_SETUP_TOOLS.copy()


__all__ = [
    # Connector
    "MCPConnector",
    "get_mcp_tools",
    # ADK Agent Tools
    "mcp_web_search",
    "mcp_web_scrape",
    "mcp_generate_landing_page",
    "get_mcp_agent_tools",
    "MCP_TOOLS",
    # User Config Service
    "get_user_config_service",
    "UserMCPConfigService",
    "INTEGRATION_TEMPLATES",
    # Setup Wizard Tools
    "mcp_list_available_integrations",
    "mcp_get_integration_requirements",
    "mcp_validate_api_key",
    "mcp_test_integration",
    "mcp_save_integration",
    "mcp_activate_integration",
    "mcp_get_user_integrations",
    "get_mcp_setup_tools",
    "MCP_SETUP_TOOLS",
]

