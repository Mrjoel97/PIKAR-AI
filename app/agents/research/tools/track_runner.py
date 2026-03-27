# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Track runner for parallel research execution.

Executes a single research track: Tavily search -> rank results ->
Firecrawl scrape top URLs -> extract key findings. Multiple track
runners execute concurrently via asyncio.gather.

Reuses existing Tavily and Firecrawl infrastructure from app/mcp/tools/.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


async def run_track(
    query: str,
    track_type: str,
    max_search_results: int = 5,
    scrape_top_n: int = 3,
    search_depth: str = "advanced",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Execute one research track: search, rank, scrape, extract.

    Args:
        query: Search query for this track.
        track_type: Track type (primary, context, contrarian, impact, risk).
        max_search_results: Max results from Tavily search.
        scrape_top_n: Number of top URLs to scrape via Firecrawl.
        search_depth: Tavily search depth ('basic' or 'advanced').
        user_id: Optional user ID for audit logging.

    Returns:
        Dict with track_type, sources, scraped_content, quick_answer,
        duration_ms, and success flag.
    """
    start = time.monotonic()

    try:
        # Step 1: Search
        search_result = await _search(
            query=query,
            max_results=max_search_results,
            search_depth=search_depth,
            user_id=user_id,
        )

        if not search_result.get("success"):
            return {
                "success": False,
                "track_type": track_type,
                "query": query,
                "error": search_result.get("error", "Search failed"),
                "sources": [],
                "scraped_content": [],
                "duration_ms": int((time.monotonic() - start) * 1000),
            }

        # Step 2: Deduplicate and rank sources
        sources = _deduplicate_sources(search_result.get("results", []))
        sources.sort(key=lambda s: s.get("score", 0), reverse=True)

        # Step 3: Scrape top URLs
        urls_to_scrape = [s["url"] for s in sources[:scrape_top_n] if s.get("url")]
        scraped_content: list[dict[str, Any]] = []
        if urls_to_scrape:
            scraped_content = await _scrape_urls(
                urls=urls_to_scrape,
                user_id=user_id,
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        return {
            "success": True,
            "track_type": track_type,
            "query": query,
            "sources": sources,
            "scraped_content": [s for s in scraped_content if s.get("success")],
            "quick_answer": search_result.get("answer"),
            "search_count": 1,
            "scrape_count": len(urls_to_scrape),
            "duration_ms": duration_ms,
        }

    except Exception as e:
        logger.error("Track runner error for '%s' (%s): %s", query, track_type, e)
        return {
            "success": False,
            "track_type": track_type,
            "query": query,
            "error": str(e),
            "sources": [],
            "scraped_content": [],
            "duration_ms": int((time.monotonic() - start) * 1000),
        }


async def run_tracks_parallel(
    tracks: list[dict[str, Any]],
    scrape_top_n: int = 3,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Run multiple research tracks in parallel.

    Args:
        tracks: List of track dicts from query planner, each with 'query' and 'track_type'.
        scrape_top_n: URLs to scrape per track.
        user_id: Optional user ID.

    Returns:
        List of track results (same order as input).
    """
    tasks = [
        run_track(
            query=track["query"],
            track_type=track["track_type"],
            scrape_top_n=scrape_top_n,
            user_id=user_id,
        )
        for track in tracks
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: list[dict[str, Any]] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append(
                {
                    "success": False,
                    "track_type": tracks[i]["track_type"],
                    "query": tracks[i]["query"],
                    "error": str(result),
                    "sources": [],
                    "scraped_content": [],
                }
            )
        else:
            processed.append(result)

    return processed


def _deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate URLs, keeping highest-scored version.

    Args:
        sources: List of source dicts with 'url' and 'score' keys.

    Returns:
        Deduplicated list sorted by score descending.
    """
    seen: dict[str, dict[str, Any]] = {}
    for source in sources:
        url = source.get("url", "")
        if not url:
            continue
        if url not in seen or source.get("score", 0) > seen[url].get("score", 0):
            seen[url] = source
    return sorted(seen.values(), key=lambda s: s.get("score", 0), reverse=True)


async def _search(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Execute Tavily search using existing MCP infrastructure.

    Args:
        query: Search query string.
        max_results: Max results to return.
        search_depth: 'basic' or 'advanced'.
        user_id: Optional user ID for audit.

    Returns:
        Search result dict with success, results, answer keys.
    """
    from app.mcp.tools.web_search import web_search_with_context

    return await web_search_with_context(
        query=query,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=True,
        agent_name="ResearchAgent",
        user_id=user_id,
    )


async def _scrape_urls(
    urls: list[str],
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Scrape multiple URLs in parallel using existing Firecrawl infrastructure.

    Args:
        urls: List of URLs to scrape.
        user_id: Optional user ID for audit.

    Returns:
        List of scrape result dicts.
    """
    from app.mcp.tools.web_scrape import web_scrape

    tasks = [
        web_scrape(
            url=url,
            extract_content=True,
            agent_name="ResearchAgent",
            user_id=user_id,
        )
        for url in urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: list[dict[str, Any]] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append(
                {
                    "success": False,
                    "url": urls[i],
                    "error": str(result),
                }
            )
        else:
            processed.append(result)

    return processed


# ADK tool export
TRACK_RUNNER_TOOLS = [run_track]
