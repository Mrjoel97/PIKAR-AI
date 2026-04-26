# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""MCP Agent Tools - ADK-compatible async tool wrappers for MCP functionality.

This module provides async tool functions that can be
directly used in Google ADK Agent definitions.

These tools are designed to be added to the `tools` list of any Agent.
"""

from typing import Any


async def mcp_web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> dict[str, Any]:
    """Search the web for information using Tavily AI search.

    This tool performs privacy-safe web searches by automatically
    filtering PII from queries before sending to external services.
    Use this for research, fact-checking, and finding up-to-date information.

    Args:
        query: The search query to execute.
        max_results: Maximum number of results to return (default: 5).
        search_depth: Search depth - "basic" or "advanced" (default: basic).

    Returns:
        Dictionary with search results including:
        - answer: AI-generated answer summary
        - results: List of search results with title, url, content, score
    """
    from app.mcp.tools.web_search import web_search

    try:
        return await web_search(query, max_results, search_depth)
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


async def mcp_web_scrape(
    url: str,
    extract_content: bool = True,
) -> dict[str, Any]:
    """Scrape content from a web page using Firecrawl.

    This tool extracts content from web pages, converting them to
    clean markdown format for easy processing. Use this for extracting
    detailed information from specific web pages.

    Args:
        url: The URL to scrape.
        extract_content: If True, extract only main content (default: True).

    Returns:
        Dictionary with scraped content including:
        - markdown: Page content in markdown format
        - metadata: Page title, description, etc.
    """
    from app.mcp.tools.web_scrape import web_scrape

    try:
        return await web_scrape(url, extract_content)
    except Exception as e:
        return {"success": False, "error": str(e), "content": None}


async def mcp_generate_landing_page(
    title: str,
    description: str,
    headline: str | None = None,
    subheadline: str | None = None,
    style: str = "modern",
    include_form: bool = True,
    cta_text: str = "Get Started",
) -> dict[str, Any]:
    """Generate a landing page with HTML and React components.

    Creates both HTML and React versions of a landing page based on
    the provided configuration. The page includes responsive design
    and optional lead capture form.

    Args:
        title: Page title for SEO and browser tab.
        description: Brief description of the page purpose.
        headline: Main headline (defaults to title if not provided).
        subheadline: Supporting text (defaults to description).
        style: Visual style - "modern", "minimal", or "bold".
        include_form: Whether to include a lead capture form.
        cta_text: Call-to-action button text.

    Returns:
        Dictionary with:
        - html: Generated HTML landing page
        - react: Generated React component
        - config: Page configuration for later editing
    """
    from app.mcp.tools.landing_page import generate_landing_page

    try:
        return await generate_landing_page(
            title=title,
            description=description,
            headline=headline,
            subheadline=subheadline,
            style=style,
            include_form=include_form,
            cta_text=cta_text,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


async def mcp_stitch_landing_page(
    title: str,
    description: str,
    headline: str | None = None,
    subheadline: str | None = None,
    style: str = "modern",
    include_form: bool = True,
    cta_text: str = "Get Started",
    sections: list[str] | None = None,
    user_id: str | None = None,
    save_to_workspace: bool = True,
) -> dict[str, Any]:
    """Generate a landing page using Stitch MCP and save to workspace.

    Creates a complete landing page with HTML and React versions using
    Google Stitch AI. The page is automatically saved to the user's
    workspace for later access and editing.

    Args:
        title: Page title for SEO and browser tab.
        description: Brief description of the page purpose.
        headline: Main headline (defaults to title if not provided).
        subheadline: Supporting text (defaults to description).
        style: Visual style - "modern", "minimal", "bold", "tech", or "startup".
        include_form: Whether to include a lead capture form.
        cta_text: Call-to-action button text.
        sections: List of sections to include (default: hero, features, cta).
        user_id: User ID for workspace storage.
        save_to_workspace: Whether to save to workspace (default: True).

    Returns:
        Dictionary with:
        - html: Generated HTML landing page
        - react: Generated React component
        - page_id: Unique page identifier
        - workspace_saved: Whether saved to workspace
    """
    # Check if Stitch is configured
    from app.mcp.config import get_mcp_config

    config = get_mcp_config()
    if not config.is_stitch_configured():
        return {
            "status": "not_configured",
            "success": False,
            "message": (
                "Stitch API is not configured. To generate professional landing pages, "
                "you need a Stitch API key from stitch.withgoogle.com. "
                "You can paste your key here and I'll configure it for you, "
                "or I can create a simpler landing page using built-in templates."
            ),
        }

    from app.mcp.tools.stitch import stitch_generate_landing_page

    try:
        return await stitch_generate_landing_page(
            title=title,
            description=description,
            headline=headline,
            subheadline=subheadline,
            style=style,
            include_form=include_form,
            cta_text=cta_text,
            sections=sections,
            user_id=user_id,
            save_to_workspace=save_to_workspace,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


# List of all MCP tools for easy import
MCP_TOOLS = [
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
    mcp_stitch_landing_page,
]

# Tool names to function mapping
MCP_TOOLS_MAP = {
    "web_search": mcp_web_search,
    "web_scrape": mcp_web_scrape,
    "landing_page": mcp_generate_landing_page,
    "stitch_landing_page": mcp_stitch_landing_page,
}


def get_mcp_agent_tools(tool_names: list[str] | None = None) -> list:
    """Get MCP tools for agent integration.

    Args:
        tool_names: List of tool names to include. If None, returns all.
                   Options: "web_search", "web_scrape", "landing_page"

    Returns:
        List of tool functions compatible with Google ADK Agent.
    """
    if tool_names is None:
        return MCP_TOOLS.copy()

    return [MCP_TOOLS_MAP[name] for name in tool_names if name in MCP_TOOLS_MAP]
