"""Sitemap Crawler Agent Tools.

ADK-compatible tools for crawling websites — discovering all pages
via sitemap.xml and batch-scraping their content. Wraps the async
MCP sitemap_crawler module into sync functions for agent use.
"""

import asyncio
from typing import Any, Dict, List, Optional


def crawl_website(
    url: str,
    max_pages: int = 50,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Crawl a website to discover and scrape all its pages.

    Maps the domain's sitemap to find all page URLs, then batch-scrapes
    their content into clean markdown. Use this to analyze a competitor's
    entire site, audit a client's blog, or extract content for repurposing.

    Args:
        url: The domain or base URL to crawl (e.g. "https://example.com").
        max_pages: Maximum number of pages to scrape (default: 50, max: 1000).
        search: Optional search term to filter pages (e.g. "blog" to only
                crawl blog pages, "pricing" to find pricing pages).

    Returns:
        Dictionary with:
        - pages_discovered: Total URLs found on the domain
        - pages_scraped: Number of pages with extracted content
        - results: List of page dicts with url, title, description,
          markdown content, and word_count
        - site_structure: All discovered URLs and which were scraped
        - total_word_count: Combined word count across all pages
    """
    from app.mcp.tools.sitemap_crawler import crawl_website as _crawl

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    _crawl(url=url, max_pages=max_pages, search=search),
                )
                return future.result(timeout=300)
        else:
            return loop.run_until_complete(
                _crawl(url=url, max_pages=max_pages, search=search)
            )
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


def map_website(
    url: str,
    search: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Discover all URLs on a website without scraping their content.

    Lightweight alternative to crawl_website — returns just the URL
    list from the domain's sitemap and internal links. Use this to
    understand a site's structure before deciding what to scrape.

    Args:
        url: The domain or base URL to map (e.g. "https://example.com").
        search: Optional search term to filter URLs (e.g. "blog", "product").
        limit: Maximum number of URLs to return (default: 100, max: 5000).

    Returns:
        Dictionary with:
        - total_links: Number of URLs discovered
        - links: List of discovered page URLs
    """
    from app.mcp.tools.sitemap_crawler import map_website as _map

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    _map(url=url, search=search, limit=limit),
                )
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(
                _map(url=url, search=search, limit=limit)
            )
    except Exception as e:
        return {"success": False, "error": str(e), "links": []}


SITEMAP_CRAWLER_TOOLS = [
    crawl_website,
    map_website,
]
