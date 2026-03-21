"""Web Scrape Tool - Web scraping using Firecrawl API.

This module provides web scraping capabilities using Firecrawl's API
for extracting content from web pages during research tasks.

Firecrawl Features:
- Full page content extraction
- Markdown conversion
- JavaScript rendering
- Clean content extraction
"""

import time
from typing import Any

import httpx

from app.mcp.config import get_mcp_config
from app.mcp.rate_limiter import check_rate_limit
from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import protect_url_payload


class FirecrawlScrapeTool:
    """Web scraping tool using Firecrawl API.

    Firecrawl provides robust web scraping with JavaScript rendering
    and clean content extraction.
    """

    def __init__(self):
        self.config = get_mcp_config()
        self.base_url = self.config.firecrawl_base_url

    async def scrape(
        self,
        url: str,
        formats: list[str] | None = None,
        only_main_content: bool = True,
        wait_for: int = 0,
    ) -> dict[str, Any]:
        """Scrape content from a URL using Firecrawl API."""
        if not self.config.is_firecrawl_configured():
            return {
                "success": False,
                "error": "Firecrawl API not configured",
                "url": url,
                "content": None,
            }

        if formats is None:
            formats = ["markdown"]

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/scrape",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.config.firecrawl_api_key}",
                    },
                    json={
                        "url": url,
                        "formats": formats,
                        "onlyMainContent": only_main_content,
                        "waitFor": wait_for,
                    },
                )
                response.raise_for_status()

                duration_ms = int((time.time() - start_time) * 1000)
                data = response.json()

                return {
                    "success": data.get("success", True),
                    "url": url,
                    "markdown": data.get("data", {}).get("markdown"),
                    "html": data.get("data", {}).get("html"),
                    "metadata": {
                        "title": data.get("data", {}).get("metadata", {}).get("title"),
                        "description": data.get("data", {})
                        .get("metadata", {})
                        .get("description"),
                        "language": data.get("data", {})
                        .get("metadata", {})
                        .get("language"),
                    },
                    "duration_ms": duration_ms,
                }

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "url": url,
                "content": None,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "content": None,
                "duration_ms": duration_ms,
            }


_scrape_tool: FirecrawlScrapeTool | None = None


def _get_scrape_tool() -> FirecrawlScrapeTool:
    """Get the singleton scrape tool instance."""
    global _scrape_tool
    if _scrape_tool is None:
        _scrape_tool = FirecrawlScrapeTool()
    return _scrape_tool


async def web_scrape(
    url: str,
    extract_content: bool = True,
    formats: list[str] | None = None,
    wait_for: int = 0,
    agent_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Scrape content from a web page using Firecrawl."""
    config = get_mcp_config()
    if not await check_rate_limit("scrape", config.scrape_rate_limit_per_minute):
        return {"success": False, "error": "Rate limit exceeded for web scraping", "url": url, "content": None}

    guard = protect_url_payload(url, field_name="url")
    tool = _get_scrape_tool()
    result = await tool.scrape(
        url=guard.outbound_value,
        formats=formats,
        only_main_content=extract_content,
        wait_for=wait_for,
    )

    log_mcp_call(
        tool_name="web_scrape",
        query_sanitized=guard.audit_value,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
        metadata=guard.metadata,
    )

    return result


async def web_scrape_multiple(
    urls: list[str],
    extract_content: bool = True,
) -> list[dict[str, Any]]:
    """Scrape content from multiple URLs."""
    results = []
    for url in urls:
        result = await web_scrape(url=url, extract_content=extract_content)
        results.append(result)
    return results
