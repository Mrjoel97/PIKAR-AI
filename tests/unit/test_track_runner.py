"""Tests for the research track runner."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_run_track_returns_findings():
    """Track runner returns structured findings from search + scrape."""
    from app.agents.research.tools.track_runner import run_track

    mock_search_result = {
        "success": True,
        "results": [
            {
                "title": "SARB Rate Cut",
                "url": "https://example.com/1",
                "content": "SARB cut rates to 7.75%",
                "score": 0.92,
            },
            {
                "title": "SA Economy",
                "url": "https://example.com/2",
                "content": "Inflation at 4.2%",
                "score": 0.85,
            },
        ],
        "answer": "SARB recently cut the repo rate.",
    }
    mock_scrape_result = {
        "success": True,
        "url": "https://example.com/1",
        "markdown": "# SARB cuts repo rate to 7.75%\n\nThe South African Reserve Bank cut rates by 25bps.",
        "metadata": {"title": "SARB Rate Cut"},
    }

    with patch(
        "app.agents.research.tools.track_runner._search",
        new_callable=AsyncMock,
        return_value=mock_search_result,
    ):
        with patch(
            "app.agents.research.tools.track_runner._scrape_urls",
            new_callable=AsyncMock,
            return_value=[mock_scrape_result],
        ):
            result = _run(
                run_track(
                    query="SARB interest rate 2026",
                    track_type="primary",
                    scrape_top_n=2,
                )
            )

    assert result["success"] is True
    assert result["track_type"] == "primary"
    assert len(result["sources"]) >= 1
    assert len(result["scraped_content"]) >= 1
    assert result["sources"][0]["url"] == "https://example.com/1"


def test_run_track_handles_search_failure():
    """Track runner returns graceful error when search fails."""
    from app.agents.research.tools.track_runner import run_track

    mock_search_fail = {"success": False, "error": "Rate limit", "results": []}

    with patch(
        "app.agents.research.tools.track_runner._search",
        new_callable=AsyncMock,
        return_value=mock_search_fail,
    ):
        result = _run(
            run_track(
                query="anything",
                track_type="primary",
            )
        )

    assert result["success"] is False
    assert "error" in result


def test_run_track_deduplicates_urls():
    """Track runner removes duplicate URLs from results."""
    from app.agents.research.tools.track_runner import _deduplicate_sources

    sources = [
        {"url": "https://example.com/1", "score": 0.9},
        {"url": "https://example.com/1", "score": 0.8},
        {"url": "https://example.com/2", "score": 0.7},
    ]
    result = _deduplicate_sources(sources)
    assert len(result) == 2
    assert result[0]["score"] == 0.9  # keeps highest score


def test_run_track_truncates_large_scraped_markdown():
    """Per-page markdown is capped to MAX_SCRAPED_MARKDOWN_CHARS to bound LLM context."""
    from app.agents.research.tools.track_runner import (
        MAX_SCRAPED_MARKDOWN_CHARS,
        run_track,
    )

    big_markdown = "x" * (MAX_SCRAPED_MARKDOWN_CHARS * 4)
    mock_search = {
        "success": True,
        "results": [
            {
                "title": "Big page",
                "url": "https://example.com/big",
                "content": "snippet",
                "score": 0.9,
            }
        ],
        "answer": None,
    }
    mock_scrape = [
        {
            "success": True,
            "url": "https://example.com/big",
            "markdown": big_markdown,
            "metadata": {"title": "Big page"},
        }
    ]

    with patch(
        "app.agents.research.tools.track_runner._search",
        new_callable=AsyncMock,
        return_value=mock_search,
    ):
        with patch(
            "app.agents.research.tools.track_runner._scrape_urls",
            new_callable=AsyncMock,
            return_value=mock_scrape,
        ):
            result = _run(
                run_track(query="big", track_type="primary", scrape_top_n=1)
            )

    scraped = result["scraped_content"]
    assert len(scraped) == 1
    assert len(scraped[0]["markdown"]) <= MAX_SCRAPED_MARKDOWN_CHARS + 50
    assert scraped[0]["truncated"] is True
    assert scraped[0]["original_length"] == len(big_markdown)


def test_run_tracks_parallel_is_exported_as_tool():
    """run_tracks_parallel must be in TRACK_RUNNER_TOOLS so the agent can call it."""
    from app.agents.research.tools.track_runner import TRACK_RUNNER_TOOLS

    tool_names = {t.__name__ for t in TRACK_RUNNER_TOOLS}
    assert "run_track" in tool_names
    assert "run_tracks_parallel" in tool_names


def test_run_track_limits_scrape_count():
    """Track runner only scrapes top N URLs."""
    from app.agents.research.tools.track_runner import run_track

    mock_search = {
        "success": True,
        "results": [
            {
                "title": f"Result {i}",
                "url": f"https://example.com/{i}",
                "content": f"Content {i}",
                "score": 0.9 - i * 0.1,
            }
            for i in range(10)
        ],
        "answer": None,
    }

    scrape_call_count = 0

    async def mock_scrape(urls, **kwargs):
        nonlocal scrape_call_count
        scrape_call_count = len(urls)
        return [
            {"success": True, "url": u, "markdown": "content", "metadata": {}}
            for u in urls
        ]

    with patch(
        "app.agents.research.tools.track_runner._search",
        new_callable=AsyncMock,
        return_value=mock_search,
    ):
        with patch(
            "app.agents.research.tools.track_runner._scrape_urls",
            new_callable=AsyncMock,
            side_effect=mock_scrape,
        ):
            _run(run_track(query="test", track_type="primary", scrape_top_n=3))

    assert scrape_call_count <= 3
