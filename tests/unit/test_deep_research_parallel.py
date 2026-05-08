# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Verify deep research search queries run in parallel via asyncio.gather."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools.deep_research import DeepResearchTool


@pytest.mark.asyncio
async def test_search_queries_run_in_parallel():
    """All 3 search queries should run concurrently, not serially.

    Each mocked _search_with_retry sleeps for SLOW_SECONDS. If executed
    serially the loop would take ~3x SLOW_SECONDS; in parallel it should
    complete close to SLOW_SECONDS. We assert <1.5x the slowest call.
    """
    tool = DeepResearchTool()

    slow_seconds = 0.3
    call_starts: list[float] = []

    async def fake_search_with_retry(**kwargs):
        call_starts.append(time.perf_counter())
        await asyncio.sleep(slow_seconds)
        return {
            "success": True,
            "results": [
                {
                    "url": f"https://example.com/{kwargs['query']}",
                    "title": kwargs["query"],
                    "content": "snippet",
                    "score": 0.5,
                }
            ],
            "answer": None,
        }

    # Bypass scrape and vault save to keep the test focused on search timing.
    with patch.object(
        tool, "_search_with_retry", side_effect=fake_search_with_retry
    ) as mock_search, patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ):
        start = time.perf_counter()
        result = await tool.research(
            topic="quantum computing",
            research_type="comprehensive",
            num_sources=3,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )
        elapsed = time.perf_counter() - start

    assert mock_search.call_count == 3, "expected 3 search queries"
    assert result["success"] is True
    # Parallel: should be close to slow_seconds, not 3 * slow_seconds.
    assert elapsed < slow_seconds * 1.5, (
        f"searches did not run in parallel: elapsed={elapsed:.3f}s "
        f"vs slowest_call={slow_seconds}s (1.5x threshold = {slow_seconds * 1.5:.3f}s)"
    )
    # All calls should start within a small window of each other.
    assert call_starts, "no calls recorded"
    spread = max(call_starts) - min(call_starts)
    assert spread < slow_seconds * 0.5, (
        f"calls did not start concurrently: spread={spread:.3f}s"
    )


@pytest.mark.asyncio
async def test_search_query_exception_logged_and_skipped():
    """Exceptions from individual searches should be filtered and logged."""
    tool = DeepResearchTool()

    async def flaky_search(**kwargs):
        if "overview" in kwargs["query"]:
            raise RuntimeError("tavily down")
        return {
            "success": True,
            "results": [
                {
                    "url": f"https://example.com/{kwargs['query']}",
                    "title": kwargs["query"],
                    "content": "ok",
                    "score": 0.5,
                }
            ],
        }

    with patch.object(
        tool, "_search_with_retry", side_effect=flaky_search
    ), patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ), patch(
        "app.agents.tools.deep_research.logger"
    ) as mock_logger:
        result = await tool.research(
            topic="widgets",
            research_type="comprehensive",
            num_sources=3,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )

    # The failing query should be logged via logger.warning with extras.
    warning_calls = [c for c in mock_logger.warning.call_args_list
                     if c.args and c.args[0] == "search query failed"]
    assert warning_calls, "expected logger.warning('search query failed', ...) call"
    extras = warning_calls[0].kwargs.get("extra", {})
    assert "query" in extras and "error" in extras
    assert extras["error"] == "tavily down"

    # Other queries still produced sources.
    assert result["success"] is True
    assert result["provider_status"]["search"]["failed_queries"] >= 1
    assert result["provider_status"]["search"]["successful_queries"] >= 1
