# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Verify Phase 99 conflict surfacing in deep_research output.

Wave 2 (RESEARCH-05) produces structured findings with optional ``contradicts``
arrays of source ids. Phase 99 promotes those into a dedicated top-level
``conflicts`` list of ``{claim, source_a_*, source_b_*}`` records so the chat
UI can render them as a distinct "Conflicting sources" section instead of
burying them in the ``limitations`` flavor text.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools.deep_research import DeepResearchTool


def _fake_search_factory(rows: list[dict]):
    """Return an async fake for ``_search_with_retry`` returning fixed rows."""

    async def fake_search(**_kwargs):
        return {"success": True, "results": rows, "answer": None}

    return fake_search


@pytest.mark.asyncio
async def test_research_emits_conflicts_when_findings_have_contradicts():
    """Findings with non-empty ``contradicts`` should surface as ``conflicts``."""
    tool = DeepResearchTool()

    # Two findings; the second contradicts the first.
    fake_findings = [
        {
            "claim": "AI agents are reshaping enterprise workflows.",
            "evidence": "40% productivity gains reported.",
            "source_id": 1,
            "contradicts": [],
        },
        {
            "claim": "Adoption costs remain a major barrier.",
            "evidence": "Source 2 disagrees on ROI vs source 1.",
            "source_id": 2,
            "contradicts": [1],
        },
    ]

    async def fake_llm(prompt: str):
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
            "content": "AI agents are reshaping enterprise workflows. Big productivity gains.",
            "score": 0.9,
        },
        {
            "url": "https://example.com/b",
            "title": "Adoption Costs",
            "content": "Adoption costs remain a barrier in mid-market firms.",
            "score": 0.8,
        },
    ]

    with patch.object(
        tool,
        "_search_with_retry",
        side_effect=_fake_search_factory(search_rows),
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

    # Conflicts list is present and non-empty.
    assert "conflicts" in result, "conflicts field must always be present"
    conflicts = result["conflicts"]
    assert isinstance(conflicts, list)
    assert len(conflicts) == 1, "exactly one conflict (finding 2 vs source 1)"

    conflict = conflicts[0]
    assert conflict["claim"].startswith("Adoption costs")
    assert conflict["source_a_id"] == 2  # primary source from the finding
    assert conflict["source_b_id"] == 1  # contradicting source
    # Source resolution should fill title/url for known indices.
    assert conflict["source_a_title"] == "Adoption Costs"
    assert conflict["source_a_url"] == "https://example.com/b"
    assert conflict["source_b_title"] == "AI in the Enterprise"
    assert conflict["source_b_url"] == "https://example.com/a"
    # Excerpts pulled from source content.
    assert "Adoption costs" in conflict["source_a_excerpt"]
    assert "enterprise workflows" in conflict["source_b_excerpt"]

    # The legacy limitations text is still populated for back-compat.
    assert any("contradicted" in lim.lower() for lim in result["limitations"])


@pytest.mark.asyncio
async def test_research_conflicts_empty_when_no_contradictions():
    """When no finding flags ``contradicts``, ``conflicts`` is an empty list."""
    tool = DeepResearchTool()

    fake_findings = [
        {
            "claim": "Stable claim 1.",
            "evidence": "ev",
            "source_id": 1,
            "contradicts": [],
        },
        {
            "claim": "Stable claim 2.",
            "evidence": "ev",
            "source_id": 2,
            "contradicts": [],
        },
    ]

    async def fake_llm(prompt: str):
        if "STRUCTURED findings" in prompt:
            return json.dumps(fake_findings)
        if "follow-up search queries" in prompt:
            return "[]"
        if "Rate the overall confidence" in prompt:
            return json.dumps(
                {"authority": 0.8, "recency": 0.8, "agreement": 0.9, "overall": 0.85}
            )
        return "[]"

    search_rows = [
        {
            "url": "https://example.com/x",
            "title": "X",
            "content": "x content",
            "score": 0.9,
        },
        {
            "url": "https://example.com/y",
            "title": "Y",
            "content": "y content",
            "score": 0.8,
        },
    ]

    with patch.object(
        tool,
        "_search_with_retry",
        side_effect=_fake_search_factory(search_rows),
    ), patch.object(
        tool, "_scrape_with_retry", new=AsyncMock(return_value={"success": False})
    ), patch(
        "app.agents.tools.deep_research._call_research_llm", side_effect=fake_llm
    ):
        result = await tool.research(
            topic="no conflicts",
            research_type="comprehensive",
            num_sources=3,
            scrape_top_n=0,
            user_id=None,
            save_to_vault=False,
        )

    assert "conflicts" in result
    assert result["conflicts"] == []
    # No "contradicted" message added to limitations.
    assert not any("contradicted" in lim.lower() for lim in result["limitations"])


@pytest.mark.asyncio
async def test_research_conflicts_empty_when_llm_fallback_used():
    """When LLM synthesis fails, conflicts stays empty (graceful degradation)."""
    tool = DeepResearchTool()

    async def fake_llm_returns_none(_prompt: str):
        return None

    search_rows = [
        {
            "url": "https://example.com/a",
            "title": "Title A",
            "content": "First sentence is long enough to be picked up. Second sentence.",
            "score": 0.9,
        }
    ]

    with patch.object(
        tool,
        "_search_with_retry",
        side_effect=_fake_search_factory(search_rows),
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

    # conflicts remains an empty list (the field is initialized in results dict
    # before the LLM path runs, so it must always be present).
    assert "conflicts" in result
    assert result["conflicts"] == []


@pytest.mark.asyncio
async def test_build_conflicts_handles_unknown_source_ids():
    """Defensively: contradicts pointing at out-of-range source ids should not crash."""
    tool = DeepResearchTool()
    tool._ensure_runtime_state()

    sources = [
        {"url": "u1", "title": "T1", "content": "c1"},
        {"url": "u2", "title": "T2", "content": "c2"},
    ]
    findings = [
        {
            "claim": "weird claim",
            "evidence": "e",
            "source_id": 99,  # out of range
            "contradicts": [42],  # out of range
        }
    ]
    conflicts = tool._build_conflicts(findings, sources)
    assert len(conflicts) == 1
    # Out-of-range ids resolve to empty strings, but no exception is raised.
    assert conflicts[0]["source_a_title"] == ""
    assert conflicts[0]["source_b_title"] == ""
    assert conflicts[0]["source_a_excerpt"] == ""
    assert conflicts[0]["source_b_excerpt"] == ""
    assert conflicts[0]["claim"] == "weird claim"
