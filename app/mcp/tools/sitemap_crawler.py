"""Sitemap Crawler Tool - Domain-wide URL discovery and batch scraping via Firecrawl.

Leverages Firecrawl's /v1/map endpoint to discover all URLs on a domain
(via sitemap.xml and link crawling), then /v1/batch/scrape for parallel
content extraction.

Use cases:
- Analyze a competitor's entire website structure
- Audit a client's blog content for repurposing
- Discover all landing pages on a domain for SEO analysis
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import protect_url_payload

logger = logging.getLogger(__name__)


class SitemapCrawlerTool:
    """Discovers URLs on a domain and batch-scrapes their content."""

    def __init__(self):
        self.config = get_mcp_config()
        self.base_url = self.config.firecrawl_base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.firecrawl_api_key}",
        }

    async def map_domain(
        self,
        url: str,
        search: str | None = None,
        limit: int = 100,
        ignore_subdomains: bool = True,
    ) -> dict[str, Any]:
        """Discover all URLs on a domain using Firecrawl's /v1/map endpoint.

        Args:
            url: The base URL or domain to map (e.g. "https://example.com").
            search: Optional search term to filter discovered URLs.
            limit: Maximum number of URLs to return (default: 100, max: 5000).
            ignore_subdomains: If True, only map the main domain.

        Returns:
            Dict with success, links (list of URLs), and metadata.
        """
        if not self.config.is_firecrawl_configured():
            return {
                "success": False,
                "error": "Firecrawl API not configured",
                "links": [],
            }

        start_time = time.time()
        payload: dict[str, Any] = {
            "url": url,
            "limit": min(limit, 5000),
            "ignoreSitemap": False,
            "includeSubdomains": not ignore_subdomains,
        }
        if search:
            payload["search"] = search

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/map",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                duration_ms = int((time.time() - start_time) * 1000)

                links = data.get("links", [])
                return {
                    "success": data.get("success", True),
                    "url": url,
                    "total_links": len(links),
                    "links": links,
                    "duration_ms": duration_ms,
                }

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "url": url,
                "links": [],
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "links": [],
                "duration_ms": duration_ms,
            }

    async def batch_scrape(
        self,
        urls: list[str],
        formats: list[str] | None = None,
        only_main_content: bool = True,
    ) -> dict[str, Any]:
        """Batch scrape multiple URLs using Firecrawl's /v1/batch/scrape endpoint.

        Args:
            urls: List of URLs to scrape (max 1000).
            formats: Output formats (default: ["markdown"]).
            only_main_content: Extract only main content, stripping nav/footer.

        Returns:
            Dict with success, batch_id, status, and results when complete.
        """
        if not self.config.is_firecrawl_configured():
            return {
                "success": False,
                "error": "Firecrawl API not configured",
                "results": [],
            }

        if formats is None:
            formats = ["markdown"]

        start_time = time.time()
        payload = {
            "urls": urls[:1000],
            "formats": formats,
            "onlyMainContent": only_main_content,
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Initiate batch scrape
                response = await client.post(
                    f"{self.base_url}/v1/batch/scrape",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                batch_id = data.get("id")
                if not batch_id:
                    return {
                        "success": data.get("success", False),
                        "error": "No batch ID returned",
                        "results": [],
                    }

                # Poll for completion
                results = await self._poll_batch(batch_id)
                duration_ms = int((time.time() - start_time) * 1000)

                return {
                    "success": True,
                    "batch_id": batch_id,
                    "total_urls": len(urls),
                    "results": results,
                    "duration_ms": duration_ms,
                }

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "results": [],
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "duration_ms": duration_ms,
            }

    async def _poll_batch(
        self,
        batch_id: str,
        max_polls: int = 60,
        poll_interval: float = 5.0,
    ) -> list[dict[str, Any]]:
        """Poll a batch scrape job until completion.

        Returns list of scraped page results.
        """
        async with httpx.AsyncClient(timeout=30.0) as poll_client:
            for _ in range(max_polls):
                resp = await poll_client.get(
                    f"{self.base_url}/v1/batch/scrape/{batch_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status", "")

                if status == "completed":
                    raw_data = data.get("data", [])
                    return [
                        {
                            "url": item.get("metadata", {}).get("sourceURL", ""),
                            "title": item.get("metadata", {}).get("title", ""),
                            "description": item.get("metadata", {}).get("description", ""),
                            "markdown": item.get("markdown", ""),
                            "word_count": len(item.get("markdown", "").split()),
                        }
                        for item in raw_data
                    ]

                if status == "failed":
                    logger.warning("Batch scrape %s failed", batch_id)
                    return []

                await asyncio.sleep(poll_interval)

        logger.warning("Batch scrape %s timed out after %d polls", batch_id, max_polls)
        return []

    async def crawl_and_scrape(
        self,
        url: str,
        max_pages: int = 50,
        search: str | None = None,
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Full pipeline: discover URLs on a domain, then batch-scrape them.

        This is the primary method agents should use. It:
        1. Maps the domain to discover all page URLs
        2. Batch-scrapes the discovered pages
        3. Returns structured results with content and metadata

        Args:
            url: The domain or base URL to crawl.
            max_pages: Maximum pages to scrape (default: 50).
            search: Optional search term to filter which pages to scrape.
            formats: Output formats for scraped content.

        Returns:
            Dict with site map, scraped content, and analysis summary.
        """
        start_time = time.time()

        # Step 1: Discover URLs
        map_result = await self.map_domain(url, search=search, limit=max_pages * 2)
        if not map_result.get("success"):
            return {
                "success": False,
                "error": f"Domain mapping failed: {map_result.get('error')}",
                "url": url,
                "pages_discovered": 0,
                "pages_scraped": 0,
                "results": [],
            }

        discovered_urls = map_result.get("links", [])[:max_pages]

        if not discovered_urls:
            return {
                "success": True,
                "url": url,
                "pages_discovered": 0,
                "pages_scraped": 0,
                "results": [],
                "note": "No pages discovered on this domain.",
            }

        # Step 2: Batch scrape
        scrape_result = await self.batch_scrape(
            urls=discovered_urls,
            formats=formats,
            only_main_content=True,
        )

        duration_ms = int((time.time() - start_time) * 1000)
        results = scrape_result.get("results", [])

        # Step 3: Build summary
        total_words = sum(r.get("word_count", 0) for r in results)
        pages_with_content = sum(1 for r in results if r.get("word_count", 0) > 50)

        return {
            "success": True,
            "url": url,
            "pages_discovered": len(map_result.get("links", [])),
            "pages_scraped": len(results),
            "pages_with_content": pages_with_content,
            "total_word_count": total_words,
            "results": results,
            "site_structure": {
                "all_urls": map_result.get("links", []),
                "scraped_urls": [r.get("url") for r in results],
            },
            "duration_ms": duration_ms,
        }


# Singleton
_crawler_tool: SitemapCrawlerTool | None = None


def _get_crawler_tool() -> SitemapCrawlerTool:
    """Get the singleton sitemap crawler tool instance."""
    global _crawler_tool
    if _crawler_tool is None:
        _crawler_tool = SitemapCrawlerTool()
    return _crawler_tool


async def crawl_website(
    url: str,
    max_pages: int = 50,
    search: str | None = None,
    agent_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Crawl a website: discover pages via sitemap, then batch-scrape content.

    This is the primary async entry point. Combines URL discovery and
    batch content extraction into a single call.

    Args:
        url: Domain or base URL to crawl.
        max_pages: Maximum number of pages to scrape.
        search: Optional filter term (e.g. "blog" to only scrape blog pages).
        agent_name: Name of the calling agent (for audit).
        user_id: User ID (for audit).
        session_id: Session ID (for audit).

    Returns:
        Comprehensive crawl results with page content and site structure.
    """
    guard = protect_url_payload(url, field_name="url")
    tool = _get_crawler_tool()
    result = await tool.crawl_and_scrape(
        url=guard.outbound_value,
        max_pages=max_pages,
        search=search,
    )

    log_mcp_call(
        tool_name="sitemap_crawler",
        query_sanitized=guard.audit_value,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
        metadata={
            **guard.metadata,
            "pages_discovered": result.get("pages_discovered", 0),
            "pages_scraped": result.get("pages_scraped", 0),
        },
    )

    return result


async def map_website(
    url: str,
    search: str | None = None,
    limit: int = 100,
    agent_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Discover all URLs on a domain without scraping content.

    Lighter-weight than crawl_website — just returns the URL list.

    Args:
        url: Domain or base URL to map.
        search: Optional filter for URL discovery.
        limit: Max URLs to return (up to 5000).

    Returns:
        Dict with discovered URLs and count.
    """
    guard = protect_url_payload(url, field_name="url")
    tool = _get_crawler_tool()
    result = await tool.map_domain(
        url=guard.outbound_value,
        search=search,
        limit=limit,
    )

    log_mcp_call(
        tool_name="sitemap_mapper",
        query_sanitized=guard.audit_value,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
        metadata={
            **guard.metadata,
            "total_links": result.get("total_links", 0),
        },
    )

    return result
