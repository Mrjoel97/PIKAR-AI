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
from typing import Any, Dict, List, Optional
import httpx

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call


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
        formats: Optional[List[str]] = None,
        only_main_content: bool = True,
        wait_for: int = 0,
    ) -> Dict[str, Any]:
        """Scrape content from a URL using Firecrawl API.
        
        Args:
            url: URL to scrape.
            formats: Output formats ("markdown", "html", "text"). Default: ["markdown"]
            only_main_content: Extract only main content, skip nav/footer.
            wait_for: Milliseconds to wait for JavaScript rendering.
            
        Returns:
            Scraped content dictionary.
        """
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
                    }
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
                        "description": data.get("data", {}).get("metadata", {}).get("description"),
                        "language": data.get("data", {}).get("metadata", {}).get("language"),
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


# Singleton instance
_scrape_tool: Optional[FirecrawlScrapeTool] = None


def _get_scrape_tool() -> FirecrawlScrapeTool:
    """Get the singleton scrape tool instance."""
    global _scrape_tool
    if _scrape_tool is None:
        _scrape_tool = FirecrawlScrapeTool()
    return _scrape_tool


async def web_scrape(
    url: str,
    extract_content: bool = True,
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Scrape content from a web page using Firecrawl.
    
    This tool extracts content from web pages, converting them to
    clean markdown format for easy processing by agents.
    
    Args:
        url: The URL to scrape.
        extract_content: If True, extract only main content (default: True).
        
    Returns:
        Dictionary with scraped content including:
        - markdown: Page content in markdown format
        - metadata: Page title, description, etc.
    """
    tool = _get_scrape_tool()
    result = await tool.scrape(url=url, only_main_content=extract_content)
    
    log_mcp_call(
        tool_name="web_scrape",
        query_sanitized=url,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
    )
    
    return result


async def web_scrape_multiple(
    urls: List[str],
    extract_content: bool = True,
) -> List[Dict[str, Any]]:
    """Scrape content from multiple URLs.
    
    Args:
        urls: List of URLs to scrape.
        extract_content: If True, extract only main content.
        
    Returns:
        List of scraped content dictionaries.
    """
    results = []
    for url in urls:
        result = await web_scrape(url=url, extract_content=extract_content)
        results.append(result)
    return results

