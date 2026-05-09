# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Verify deep research uses LLM for synthesis, follow-up hops, and confidence.

These tests mock the underlying Gemini ``_call_research_llm`` helper to return
canned JSON so the test exercises the parsing, hop-orchestration, and
confidence-surfacing logic without hitting the network.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools.deep_research import DeepResearchTool


def _fake_search_factory(query_to_results: dict[str, list[dict]]):
    """Return an async fake for ``_search_with_retry`` driven by query keyword."""

    async def fake_search(**kwargs):
        query = kwargs["query"]
        # Find the first registered key contained in the query.
        for keyword, rows in query_to_results.items():
            if keyword in query:
                return {"success": True, "results": rows, "answer": None}
        return {"success": True, "results": [], "answer": None}

    return fake_search


@pytest.mark.asyncio
async def test_synthesis_returns_structured_findings():
    """LLM synthesis output should be parsed and surface as ``key_findings``."""
    tool = DeepResearchTool()

    fake_findings = [
        {
            "claim": "AI agents are reshaping enterprise workflows.",
            "evidence": "Reports cite 40% productivity gains.",
            "source_id": 1,
            "contradicts": [],
        },
        {
            "claim": "Adoption costs remain a barrier.",
            "evidence": "Source 2 disagrees with source 1 on ROI.",
            "source_id": 2,
            "contradicts": [1],
        },
    ]

    async def fake_llm(prompt: str):
        # First call (synthesis): return findings JSON.
        # Second call (follow-up): return empty list (no follow-up).
        # Third call (confidence): return scoring JSON.
        if "STRUCTURED findings" in prompt:
            return json.dumps(fake_findings)
        if "follow-up search queries" in prompt:
            return "[]"
        if "Rate the overall confidence" in prompt:
            return json.dumps(
                {"authority": 0.8, "recency": 0.7, "agreement": 0.5, "overall": 0.7}
            )
        return "[]"

    search_rows = [
        {
            "url": "https://example.com/a",
            "title": "AI in the Enterprise",
            "content": "AI agents are reshaping enterprise workflows.",
            "score": 0.9,
        },
        {
            "url": "https://example.com/b",
            "title": "Adoption Costs",
            "content": "Adoption costs remain a barrier.",
            "score": 0.8,
        },
    ]

    with patch.object(
        tool,
        "_search_with_retry",
        side_effect=_fake_search_factory({"": search_rows}),
    ), patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ), patch(
        "app.agents.tools.deep_research._call_research_llm", side_effect=fake_llm
    ):
        result = await tool.research(
            topic="AI agents",
            research_type="comprehensive",
            num_sources=3,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )

    assert result["success"] is True
    # Structured findings preserved in key_findings.
    assert isinstance(result["key_findings"], list)
    assert all(isinstance(f, dict) for f in result["key_findings"])
    claims = {f["claim"] for f in result["key_findings"]}
    assert "AI agents are reshaping enterprise workflows." in claims
    # Contradictions surfaced into limitations.
    assert any("contradicted" in lim.lower() for lim in result["limitations"])
    # Confidence is the LLM-graded overall, not the mechanical formula.
    assert result["confidence_score"] == 0.7
    assert result["confidence_breakdown"]["authority"] == 0.8


@pytest.mark.asyncio
async def test_followup_queries_fire_when_model_requests_them():
    """If the follow-up prompt returns >0 queries, those searches must fire."""
    tool = DeepResearchTool()

    initial_findings = [
        {"claim": "Initial claim.", "evidence": "ev", "source_id": 1, "contradicts": []}
    ]

    async def fake_llm(prompt: str):
        if "STRUCTURED findings" in prompt:
            return json.dumps(initial_findings)
        if "follow-up search queries" in prompt:
            return json.dumps(["deeper question A", "deeper question B"])
        if "Rate the overall confidence" in prompt:
            return json.dumps(
                {"authority": 0.6, "recency": 0.6, "agreement": 0.6, "overall": 0.6}
            )
        return "[]"

    initial_rows = [
        {
            "url": "https://example.com/initial",
            "title": "Initial",
            "content": "Initial content",
            "score": 0.9,
        }
    ]
    followup_rows = [
        {
            "url": "https://example.com/followup",
            "title": "Followup",
            "content": "More detail",
            "score": 0.85,
        }
    ]

    fake_search = _fake_search_factory(
        {"deeper": followup_rows, "": initial_rows}
    )
    search_mock = AsyncMock(side_effect=fake_search)

    with patch.object(tool, "_search_with_retry", new=search_mock), patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ), patch(
        "app.agents.tools.deep_research._call_research_llm", side_effect=fake_llm
    ):
        result = await tool.research(
            topic="topic X",
            research_type="comprehensive",
            num_sources=5,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )

    # Expect 3 initial searches + 2 follow-up = 5 total.
    assert search_mock.await_count == 5
    # Both follow-up queries should be recorded.
    assert result.get("followup_queries") == ["deeper question A", "deeper question B"]
    assert result["hop_count"] == 2
    # The follow-up source url should be merged into the final source pool.
    urls = {s.get("url") for s in result["sources"]}
    assert "https://example.com/followup" in urls


@pytest.mark.asyncio
async def test_confidence_is_llm_graded_not_mechanical():
    """``confidence_score`` should equal the LLM ``overall``, not the count-based calc."""
    tool = DeepResearchTool()

    async def fake_llm(prompt: str):
        if "STRUCTURED findings" in prompt:
            return json.dumps(
                [
                    {
                        "claim": "c",
                        "evidence": "e",
                        "source_id": 1,
                        "contradicts": [],
                    }
                ]
            )
        if "follow-up search queries" in prompt:
            return "[]"
        if "Rate the overall confidence" in prompt:
            return json.dumps(
                {
                    "authority": 0.95,
                    "recency": 0.90,
                    "agreement": 0.85,
                    "overall": 0.90,
                }
            )
        return "[]"

    search_rows = [
        {
            "url": "https://example.com/x",
            "title": "X",
            "content": "x content",
            "score": 0.9,
        }
    ]

    # Patch _calculate_confidence to a sentinel value to prove it's NOT used
    # when LLM grading succeeds.
    with patch.object(
        tool,
        "_search_with_retry",
        side_effect=_fake_search_factory({"": search_rows}),
    ), patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ), patch.object(
        tool, "_calculate_confidence", return_value=0.123
    ) as mech_mock, patch(
        "app.agents.tools.deep_research._call_research_llm", side_effect=fake_llm
    ):
        result = await tool.research(
            topic="confidence test",
            research_type="comprehensive",
            num_sources=3,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )

    assert result["confidence_score"] == 0.90
    assert result["confidence_breakdown"]["authority"] == 0.95
    mech_mock.assert_not_called()


@pytest.mark.asyncio
async def test_falls_back_to_string_concat_when_llm_unavailable():
    """If the LLM returns None, the legacy string-concat path runs and a warning is logged."""
    tool = DeepResearchTool()

    async def fake_llm_returns_none(prompt: str):
        return None

    search_rows = [
        {
            "url": "https://example.com/a",
            "title": "Title A",
            "content": (
                "This is a long enough first sentence to be picked up. "
                "Second sentence here."
            ),
            "score": 0.9,
        }
    ]

    with patch.object(
        tool,
        "_search_with_retry",
        side_effect=_fake_search_factory({"": search_rows}),
    ), patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ), patch(
        "app.agents.tools.deep_research._call_research_llm",
        side_effect=fake_llm_returns_none,
    ):
        result = await tool.research(
            topic="fallback topic",
            research_type="comprehensive",
            num_sources=3,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )

    # Legacy fallback yields list[str], not list[dict].
    assert result["success"] is True
    assert isinstance(result["key_findings"], list)
    assert all(isinstance(f, str) for f in result["key_findings"])
    assert any("fallback" in lim.lower() for lim in result["limitations"])
    # Mechanical confidence is used when LLM grading also fails.
    assert isinstance(result["confidence_score"], float)
    assert "confidence_breakdown" not in result
