# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for app.agents.tools.quick_research.

The tool is a lightweight, single-query specialist-level research helper.
We mock both the Tavily search wrapper and the Firecrawl scrape wrapper to
keep the test fast and offline.
"""

from unittest.mock import AsyncMock

import pytest

from app.agents.tools import quick_research as quick_research_module
from app.agents.tools.quick_research import (
    QUICK_RESEARCH_TOOLS,
    quick_research,
)


def _search_payload(num_results: int) -> dict:
    return {
        "success": True,
        "answer": "Tavily summary paragraph.",
        "results": [
            {
                "title": f"Source {i}",
                "url": f"https://example.com/{i}",
                "content": f"Tavily snippet {i}. Continues here.",
                "score": 0.9 - i * 0.1,
            }
            for i in range(num_results)
        ],
    }


def _scrape_payload(url: str) -> dict:
    return {
        "success": True,
        "url": url,
        "markdown": f"Scraped markdown body for {url}. Has plenty of words. "
        * 10,
        "metadata": {"title": f"Title {url}"},
    }


@pytest.mark.asyncio
async def test_quick_research_returns_expected_shape(monkeypatch):
    """Tool returns {query, sources: [{url,title,excerpt}], summary}."""
    search_mock = AsyncMock(return_value=_search_payload(num_results=3))
    scrape_mock = AsyncMock(side_effect=lambda url, **kwargs: _scrape_payload(url))

    monkeypatch.setattr(
        quick_research_module, "web_search_with_context", search_mock
    )
    monkeypatch.setattr(quick_research_module, "web_scrape", scrape_mock)

    result = await quick_research("AI copilots for SMB", max_sources=3)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"query", "sources", "summary"}
    assert result["query"] == "AI copilots for SMB"
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) == 3

    for source in result["sources"]:
        assert set(source.keys()) == {"url", "title", "excerpt"}
        assert source["url"].startswith("https://example.com/")
        assert source["excerpt"]  # non-empty

    assert isinstance(result["summary"], str)
    assert result["summary"]  # non-empty
    # Tavily-provided answer is preferred when present.
    assert result["summary"] == "Tavily summary paragraph."

    # The search was called once (single-query) and scrape was called per URL.
    assert search_mock.await_count == 1
    assert scrape_mock.await_count == 3


@pytest.mark.asyncio
async def test_quick_research_caps_max_sources_at_5(monkeypatch):
    """max_sources is capped to 5 even if a larger value is requested."""
    search_mock = AsyncMock(return_value=_search_payload(num_results=10))
    scrape_mock = AsyncMock(side_effect=lambda url, **kwargs: _scrape_payload(url))

    monkeypatch.setattr(
        quick_research_module, "web_search_with_context", search_mock
    )
    monkeypatch.setattr(quick_research_module, "web_scrape", scrape_mock)

    result = await quick_research("anything", max_sources=20)

    # The Tavily call should request <=5 results, not 20.
    call_kwargs = search_mock.await_args.kwargs
    assert call_kwargs["max_results"] == 5
    # Final source list is capped to 5.
    assert len(result["sources"]) == 5
    # Scrape was called at most 5 times.
    assert scrape_mock.await_count == 5


@pytest.mark.asyncio
async def test_quick_research_respects_smaller_max_sources(monkeypatch):
    """A smaller max_sources value is honored as-is."""
    search_mock = AsyncMock(return_value=_search_payload(num_results=5))
    scrape_mock = AsyncMock(side_effect=lambda url, **kwargs: _scrape_payload(url))

    monkeypatch.setattr(
        quick_research_module, "web_search_with_context", search_mock
    )
    monkeypatch.setattr(quick_research_module, "web_scrape", scrape_mock)

    result = await quick_research("topic", max_sources=2)

    call_kwargs = search_mock.await_args.kwargs
    assert call_kwargs["max_results"] == 2
    assert len(result["sources"]) == 2
    assert scrape_mock.await_count == 2


@pytest.mark.asyncio
async def test_quick_research_falls_back_to_tavily_snippet_when_scrape_fails(
    monkeypatch,
):
    """If a scrape errors out, the excerpt falls back to Tavily's content."""
    search_mock = AsyncMock(return_value=_search_payload(num_results=2))
    # Each scrape "fails" (success=False, no markdown).
    scrape_mock = AsyncMock(
        side_effect=lambda url, **kwargs: {
            "success": False,
            "url": url,
            "error": "boom",
        }
    )

    monkeypatch.setattr(
        quick_research_module, "web_search_with_context", search_mock
    )
    monkeypatch.setattr(quick_research_module, "web_scrape", scrape_mock)

    result = await quick_research("topic", max_sources=2)

    assert len(result["sources"]) == 2
    # Excerpts are populated from Tavily's content even though scrape failed.
    for source in result["sources"]:
        assert source["excerpt"].startswith("Tavily snippet")


@pytest.mark.asyncio
async def test_quick_research_handles_search_failure(monkeypatch):
    """When Tavily search fails, sources is empty and summary explains why."""
    search_mock = AsyncMock(
        return_value={"success": False, "error": "Tavily API not configured"}
    )
    scrape_mock = AsyncMock()

    monkeypatch.setattr(
        quick_research_module, "web_search_with_context", search_mock
    )
    monkeypatch.setattr(quick_research_module, "web_scrape", scrape_mock)

    result = await quick_research("topic", max_sources=3)

    assert result["query"] == "topic"
    assert result["sources"] == []
    assert "Search failed" in result["summary"]
    # Scrape must NOT be called if search failed.
    assert scrape_mock.await_count == 0


@pytest.mark.asyncio
async def test_quick_research_rejects_empty_query(monkeypatch):
    """Empty/whitespace query short-circuits without hitting the network."""
    search_mock = AsyncMock()
    scrape_mock = AsyncMock()
    monkeypatch.setattr(
        quick_research_module, "web_search_with_context", search_mock
    )
    monkeypatch.setattr(quick_research_module, "web_scrape", scrape_mock)

    result = await quick_research("   ", max_sources=3)

    assert result["sources"] == []
    assert "non-empty query" in result["summary"]
    assert search_mock.await_count == 0
    assert scrape_mock.await_count == 0


def test_quick_research_tools_list_exports_function():
    """QUICK_RESEARCH_TOOLS is the wiring expected by specialist agents."""
    assert quick_research in QUICK_RESEARCH_TOOLS
    assert len(QUICK_RESEARCH_TOOLS) == 1
