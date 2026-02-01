"""MCP Agent Tools - ADK-compatible tool wrappers for MCP functionality.

This module provides synchronous and async tool functions that can be
directly used in Google ADK Agent definitions.

These tools are designed to be added to the `tools` list of any Agent.
"""

from typing import Any, Dict, List, Optional
import asyncio

from app.mcp.security.pii_filter import sanitize_query
from app.mcp.security.audit_logger import log_mcp_call


def mcp_web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> Dict[str, Any]:
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
    
    # Run the async function synchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new task if already in async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    web_search(query, max_results, search_depth)
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                web_search(query, max_results, search_depth)
            )
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


def mcp_web_scrape(
    url: str,
    extract_content: bool = True,
) -> Dict[str, Any]:
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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    web_scrape(url, extract_content)
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(web_scrape(url, extract_content))
    except Exception as e:
        return {"success": False, "error": str(e), "content": None}


def mcp_generate_landing_page(
    title: str,
    description: str,
    headline: Optional[str] = None,
    subheadline: Optional[str] = None,
    style: str = "modern",
    include_form: bool = True,
    cta_text: str = "Get Started",
) -> Dict[str, Any]:
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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    generate_landing_page(
                        title=title,
                        description=description,
                        headline=headline,
                        subheadline=subheadline,
                        style=style,
                        include_form=include_form,
                        cta_text=cta_text,
                    )
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                generate_landing_page(
                    title=title,
                    description=description,
                    headline=headline,
                    subheadline=subheadline,
                    style=style,
                    include_form=include_form,
                    cta_text=cta_text,
                )
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


# List of all MCP tools for easy import
MCP_TOOLS = [
    mcp_web_search,
    mcp_web_scrape,
    mcp_generate_landing_page,
]

# Tool names to function mapping
MCP_TOOLS_MAP = {
    "web_search": mcp_web_search,
    "web_scrape": mcp_web_scrape,
    "landing_page": mcp_generate_landing_page,
}


def get_mcp_agent_tools(tool_names: Optional[List[str]] = None) -> List:
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

