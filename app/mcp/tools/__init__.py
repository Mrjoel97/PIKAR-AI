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
from app.mcp.tools.sitemap_crawler import (
    crawl_website,
    map_website,
    SitemapCrawlerTool,
)
from app.mcp.tools.google_seo import (
    search_console_performance,
    ga4_traffic_report,
    GoogleSEOTool,
)
from app.mcp.tools.social_listening import (
    monitor_brand_mentions,
    compare_brand_share_of_voice,
    SocialListeningTool,
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
    # Sitemap Crawler
    "crawl_website",
    "map_website",
    "SitemapCrawlerTool",
    # Landing Pages
    "generate_landing_page",
    "save_landing_page",
    "get_landing_page",
    "LandingPageTool",
    # Form Handling
    "handle_form_submission",
    "get_form_submissions",
    "FormHandlerTool",
    # Google SEO (Search Console + GA4)
    "search_console_performance",
    "ga4_traffic_report",
    "GoogleSEOTool",
    # Social Listening
    "monitor_brand_mentions",
    "compare_brand_share_of_voice",
    "SocialListeningTool",
]

