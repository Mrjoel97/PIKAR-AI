# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""MCP Tools Module.

This module provides individual MCP tools for agents:
- web_search: Privacy-safe web search using Tavily
- web_scrape: Web scraping using Firecrawl
- landing_page: Landing page generation and storage
- form_handler: Form submission handling
"""

from app.mcp.tools.form_handler import (
    FormHandlerTool,
    get_form_submissions,
    handle_form_submission,
)
from app.mcp.tools.google_seo import (
    GoogleSEOTool,
    ga4_traffic_report,
    search_console_performance,
)
from app.mcp.tools.landing_page import (
    LandingPageTool,
    generate_landing_page,
    get_landing_page,
    save_landing_page,
)
from app.mcp.tools.sitemap_crawler import (
    SitemapCrawlerTool,
    crawl_website,
    map_website,
)
from app.mcp.tools.social_listening import (
    SocialListeningTool,
    compare_brand_share_of_voice,
    monitor_brand_mentions,
)
from app.mcp.tools.web_scrape import (
    FirecrawlScrapeTool,
    web_scrape,
    web_scrape_multiple,
)
from app.mcp.tools.web_search import (
    TavilySearchTool,
    web_search,
    web_search_with_context,
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
