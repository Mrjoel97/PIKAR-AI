# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tool Registry for Workflow Automation.

Maps string identifiers (used in workflow definitions) to executable Python functions.
"""

import logging

# Import actual tools
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape
# from app.agents.tools.invoicing import generate_invoice # Example
# from app.agents.tools.notifications import send_notification

logger = logging.getLogger(__name__)

async def placeholder_tool(context: dict = {}) -> dict:
    """Fallback tool for unimplemented functions."""
    logger.warning("Executing placeholder tool.")
    return {
        "status": "simulated_success",
        "message": "This tool is not yet implemented. Step auto-completed."
    }

# Registry Dictionary
# format: "tool_name": function_reference
TOOL_REGISTRY = {
    # MCP Tools
    "mcp_web_search": mcp_web_search,
    "mcp_web_scrape": mcp_web_scrape,
    
    # We will map other tools here as they are implemented.
    # For now, we rely on the .get() method returning the placeholder.
}

def get_tool(tool_name: str):
    """Get a tool function by name."""
    if tool_name in TOOL_REGISTRY:
        return TOOL_REGISTRY[tool_name]
    
    # Return placeholder for missing tools to allow workflow testing
    # In production, we might want to raise an error or pause the workflow.
    logger.info(f"Tool '{tool_name}' not found in registry. Using placeholder.")
    
    # We return a wrapper to inject the tool name into the result for clarity
    async def wrapper(**kwargs):
        logger.warning(f"Executing placeholder for: {tool_name}")
        return {
            "status": "simulated_success",
            "message": f"Tool '{tool_name}' implementation missing. Auto-completed step.",
            "mock_data": kwargs
        }
    return wrapper
