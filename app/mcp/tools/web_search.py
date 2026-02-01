"""Web Search Tool - Privacy-safe web search using Tavily API.

This module provides web search capabilities using Tavily's AI-powered
search API. All queries are sanitized for PII before being sent.

Tavily API Features:
- AI-powered search results with relevance scoring
- Source citations and URLs
- Content summaries
- Topic categorization
"""

import time
from typing import Any, Dict, List, Optional
import httpx

from app.mcp.config import get_mcp_config
from app.mcp.security.pii_filter import sanitize_query
from app.mcp.security.audit_logger import log_mcp_call


class TavilySearchTool:
    """Web search tool using Tavily API.
    
    Tavily provides AI-powered search results with citations,
    making it ideal for research tasks.
    """
    
    def __init__(self):
        self.config = get_mcp_config()
        self.base_url = self.config.tavily_base_url
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
    ) -> Dict[str, Any]:
        """Execute a search query using Tavily API.
        
        Args:
            query: Search query (should already be sanitized).
            max_results: Maximum number of results to return.
            search_depth: "basic" or "advanced" search depth.
            include_answer: Include AI-generated answer summary.
            include_raw_content: Include full page content.
            
        Returns:
            Search results dictionary with answer, sources, and results.
        """
        if not self.config.is_tavily_configured():
            return {
                "success": False,
                "error": "Tavily API not configured",
                "results": [],
            }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={
                        "Content-Type": "application/json",
                    },
                    json={
                        "api_key": self.config.tavily_api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": search_depth,
                        "include_answer": include_answer,
                        "include_raw_content": include_raw_content,
                    }
                )
                response.raise_for_status()
                
                duration_ms = int((time.time() - start_time) * 1000)
                data = response.json()
                
                return {
                    "success": True,
                    "query": query,
                    "answer": data.get("answer"),
                    "results": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "content": r.get("content"),
                            "score": r.get("score"),
                        }
                        for r in data.get("results", [])
                    ],
                    "duration_ms": duration_ms,
                }
                
        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "query": query,
                "results": [],
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": [],
                "duration_ms": duration_ms,
            }


# Singleton instance
_search_tool: Optional[TavilySearchTool] = None


def _get_search_tool() -> TavilySearchTool:
    """Get the singleton search tool instance."""
    global _search_tool
    if _search_tool is None:
        _search_tool = TavilySearchTool()
    return _search_tool


async def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> Dict[str, Any]:
    """Search the web for information using Tavily AI search.
    
    This tool performs privacy-safe web searches by automatically
    filtering PII from queries before sending to external services.
    
    Args:
        query: The search query to execute.
        max_results: Maximum number of results to return (default: 5).
        search_depth: Search depth - "basic" or "advanced" (default: basic).
        
    Returns:
        Dictionary with search results including:
        - answer: AI-generated answer summary
        - results: List of search results with title, url, content, score
    """
    # Sanitize query for PII
    safe_query = sanitize_query(query)
    
    # Execute search
    tool = _get_search_tool()
    result = await tool.search(
        query=safe_query,
        max_results=max_results,
        search_depth=search_depth,
    )
    
    # Log the call
    log_mcp_call(
        tool_name="web_search",
        query_sanitized=safe_query,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
    )
    
    return result


async def web_search_with_context(
    query: str,
    max_results: int = 5,
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Search with additional context for audit logging."""
    safe_query = sanitize_query(query)
    tool = _get_search_tool()
    result = await tool.search(query=safe_query, max_results=max_results)
    
    log_mcp_call(
        tool_name="web_search",
        query_sanitized=safe_query,
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        agent_name=agent_name,
        user_id=user_id,
        session_id=session_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
    )
    
    return result

