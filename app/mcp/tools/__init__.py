"""MCP Tools Module.

This module provides individual MCP tools for agents:
- web_search: Privacy-safe web search using Tavily
- web_scrape: Web scraping using Firecrawl
- landing_page: Landing page generation and storage
- form_handler: Form submission handling
"""

from app.mcp.tools.web_search import (
    web_search,
    web_search_with_context,
    TavilySearchTool,
)
from app.mcp.tools.web_scrape import (
    web_scrape,
    web_scrape_multiple,
    FirecrawlScrapeTool,
)
from app.mcp.tools.landing_page import (
    generate_landing_page,
    save_landing_page,
    get_landing_page,
    LandingPageTool,
)
from app.mcp.tools.form_handler import (
    handle_form_submission,
    get_form_submissions,
    FormHandlerTool,
)

__all__ = [
    # Web Search
    "web_search",
    "web_search_with_context",
    "TavilySearchTool",
    # Web Scraping
    "web_scrape",
    "web_scrape_multiple",
    "FirecrawlScrapeTool",
    # Landing Pages
    "generate_landing_page",
    "save_landing_page",
    "get_landing_page",
    "LandingPageTool",
    # Form Handling
    "handle_form_submission",
    "get_form_submissions",
    "FormHandlerTool",
]

