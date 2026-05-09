# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""quick_research: Single-query, lightweight research for specialist agents.

Used inside a specialist's turn (~30s). For deep multi-hop research,
delegate to Executive's deep_research.

This is intentionally light:
- ONE Tavily query (no multi-query expansion)
- Up to 5 parallel Firecrawl scrapes (capped)
- Deterministic excerpt-based summary (no extra LLM round-trip)

If you need multi-query / multi-hop / vault-saving research, use
``deep_research`` (Executive-only) or one of the workflow research tools
in ``app.agents.tools.deep_research``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.mcp.tools.web_scrape import web_scrape
from app.mcp.tools.web_search import web_search_with_context

logger = logging.getLogger(__name__)

_MAX_SOURCES_CAP = 5
_EXCERPT_CHARS = 600
_SUMMARY_SOURCE_CHARS = 240


async def quick_research(query: str, max_sources: int = 3) -> dict[str, Any]:
    """Run a single-query Tavily search + scrape top N URLs.

    Args:
        query: Single research question. Be specific.
        max_sources: How many URLs to scrape (default 3, max 5).

    Returns:
        ``{"query", "sources": [{"url", "title", "excerpt"}], "summary"}``.
        Always returns the same shape; on failure ``sources`` may be empty
        and ``summary`` will explain the failure.
    """
    if not isinstance(query, str) or not query.strip():
        return {
            "query": query or "",
            "sources": [],
            "summary": "quick_research requires a non-empty query string.",
        }

    # Cap max_sources defensively (model could pass anything).
    try:
        capped = int(max_sources)
    except (TypeError, ValueError):
        capped = 3
    capped = max(1, min(capped, _MAX_SOURCES_CAP))

    search_result = await web_search_with_context(
        query=query,
        max_results=capped,
        search_depth="basic",
        include_answer=True,
        agent_name="quick_research",
    )

    if not search_result.get("success"):
        error = search_result.get("error") or "unknown search error"
        logger.info("quick_research search failed: %s", error)
        return {
            "query": query,
            "sources": [],
            "summary": f"Search failed: {error}",
        }

    raw_results = search_result.get("results") or []
    top_results = raw_results[:capped]

    urls_to_scrape = [
        r["url"] for r in top_results if isinstance(r, dict) and r.get("url")
    ]

    scrape_results: list[Any] = []
    if urls_to_scrape:
        scrape_results = await asyncio.gather(
            *(
                web_scrape(
                    url=url,
                    extract_content=True,
                    formats=["markdown"],
                    agent_name="quick_research",
                )
                for url in urls_to_scrape
            ),
            return_exceptions=True,
        )

    scrape_by_url: dict[str, dict[str, Any]] = {}
    for url, scrape in zip(urls_to_scrape, scrape_results):
        if isinstance(scrape, Exception):
            logger.info("quick_research scrape failed for %s: %s", url, scrape)
            continue
        if isinstance(scrape, dict) and scrape.get("success"):
            scrape_by_url[url] = scrape

    sources: list[dict[str, str]] = []
    for r in top_results:
        if not isinstance(r, dict):
            continue
        url = r.get("url") or ""
        title = r.get("title") or ""
        excerpt = ""
        scrape = scrape_by_url.get(url) if url else None
        if scrape:
            markdown = scrape.get("markdown") or ""
            if markdown:
                excerpt = markdown[:_EXCERPT_CHARS].strip()
            metadata = scrape.get("metadata") or {}
            if not title and metadata.get("title"):
                title = metadata["title"]
        if not excerpt:
            # Fall back to Tavily's content snippet when scrape failed/empty.
            excerpt = (r.get("content") or "")[:_EXCERPT_CHARS].strip()
        sources.append({"url": url, "title": title, "excerpt": excerpt})

    summary = _build_summary(
        query=query,
        tavily_answer=search_result.get("answer"),
        sources=sources,
    )

    return {
        "query": query,
        "sources": sources,
        "summary": summary,
    }


def _build_summary(
    query: str,
    tavily_answer: str | None,
    sources: list[dict[str, str]],
) -> str:
    """Build a deterministic one-paragraph summary.

    Prefers Tavily's built-in ``answer`` when available, otherwise stitches
    together the first sentence of each source excerpt. No extra LLM call.
    """
    if tavily_answer and isinstance(tavily_answer, str) and tavily_answer.strip():
        return tavily_answer.strip()

    if not sources:
        return f"No sources found for: {query}"

    fragments: list[str] = []
    for src in sources:
        excerpt = (src.get("excerpt") or "").strip()
        if not excerpt:
            continue
        # First sentence-ish: split on period+space, keep up to ~240 chars.
        first = excerpt.split(". ", 1)[0]
        fragments.append(first[:_SUMMARY_SOURCE_CHARS].strip())

    if not fragments:
        return f"Found {len(sources)} sources for '{query}' but no readable content."

    body = " ".join(fragments)
    return body[: _SUMMARY_SOURCE_CHARS * 3]


QUICK_RESEARCH_TOOLS = [quick_research]
