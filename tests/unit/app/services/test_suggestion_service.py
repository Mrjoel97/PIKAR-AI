# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the suggestion chip service.

Covers persona-awareness, time-of-day buckets, activity follow-ups,
and result-count guarantees.
"""

from __future__ import annotations

import pytest

from app.services.suggestion_service import SuggestionItem, get_suggestions


@pytest.mark.asyncio
async def test_solopreneur_morning_returns_4_to_6_items_with_text_and_category() -> None:
    """get_suggestions(persona='solopreneur', hour=9) returns 4-6 items with text + category."""
    results = await get_suggestions(persona="solopreneur", hour=9)
    assert 4 <= len(results) <= 6
    for item in results:
        assert isinstance(item, SuggestionItem)
        assert item.text
        assert item.category in (
            "quick_start",
            "persona_specific",
            "time_aware",
            "activity_followup",
        )


@pytest.mark.asyncio
async def test_enterprise_returns_different_suggestions_than_solopreneur() -> None:
    """Enterprise suggestions differ from solopreneur suggestions."""
    solo = await get_suggestions(persona="solopreneur", hour=9)
    enterprise = await get_suggestions(persona="enterprise", hour=9)
    solo_texts = {s.text for s in solo}
    enterprise_texts = {s.text for s in enterprise}
    # At least some suggestions should be different (persona-specific pool differs)
    assert solo_texts != enterprise_texts


@pytest.mark.asyncio
async def test_time_of_day_buckets() -> None:
    """Morning, afternoon, and evening produce time-appropriate suggestions."""
    morning = await get_suggestions(persona="solopreneur", hour=9)
    afternoon = await get_suggestions(persona="solopreneur", hour=14)
    evening = await get_suggestions(persona="solopreneur", hour=20)

    morning_texts = {s.text for s in morning}
    afternoon_texts = {s.text for s in afternoon}
    evening_texts = {s.text for s in evening}

    # Each time bucket draws from a different pool, so the union of all three
    # should contain more unique items than any single bucket.
    all_texts = morning_texts | afternoon_texts | evening_texts
    assert len(all_texts) > max(len(morning_texts), len(afternoon_texts), len(evening_texts))


@pytest.mark.asyncio
async def test_activity_followup_includes_related_suggestion() -> None:
    """Passing recent_activity with content_creation includes a follow-up."""
    results = await get_suggestions(
        persona="solopreneur",
        hour=10,
        recent_activity=["workflow:content_creation"],
    )
    texts = [s.text for s in results]
    categories = [s.category for s in results]
    # At least one activity_followup should appear
    assert "activity_followup" in categories


@pytest.mark.asyncio
async def test_always_returns_between_4_and_6() -> None:
    """Regardless of params, result count is always 4-6."""
    for persona in ("solopreneur", "startup", "sme", "enterprise"):
        for hour in (7, 14, 21):
            results = await get_suggestions(persona=persona, hour=hour)
            assert 4 <= len(results) <= 6, (
                f"Expected 4-6 for {persona} at hour {hour}, got {len(results)}"
            )
