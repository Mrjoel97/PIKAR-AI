# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for skill embedding cache: build_index, search_similar, async wrappers."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


def _make_skill(name: str, description: str) -> MagicMock:
    """Create a fake Skill object with name and description."""
    skill = MagicMock()
    skill.name = name
    skill.description = description
    return skill


# ---------------------------------------------------------------------------
# Deterministic embedding vectors for testing
# ---------------------------------------------------------------------------
_VEC_A = [1.0, 0.0, 0.0]
_VEC_B = [0.0, 1.0, 0.0]
_VEC_C = [0.7, 0.7, 0.0]  # similar to A and B


def _fake_batch(texts: list[str], batch_size: int = 5) -> list[list[float]]:
    """Return deterministic vectors for each text in the batch."""
    vecs = [_VEC_A, _VEC_B, _VEC_C]
    return vecs[: len(texts)]


def _fake_embedding(text: str) -> list[float]:
    """Return a query vector similar to _VEC_A."""
    return [0.9, 0.1, 0.0]


FAKE_SKILLS = [
    _make_skill("seo_checklist", "Search engine optimization checklist"),
    _make_skill("budget_analysis", "Financial budget analysis techniques"),
    _make_skill("social_media", "Social media content strategy"),
]


# ---------------------------------------------------------------------------
# Test 1: build_index populates cache and is_warmed returns True
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.skills.skill_embeddings.warmup_skill_embeddings")
@patch("app.skills.registry.skills_registry")
async def test_build_index_populates_cache(mock_registry, mock_warmup):
    """build_index calls warmup via to_thread and populates cache."""
    from app.skills import skill_embeddings

    # Reset cache
    skill_embeddings._embedding_cache.clear()

    mock_registry.list_all.return_value = FAKE_SKILLS
    mock_warmup.return_value = 3

    # Simulate warmup side-effect: populate the cache
    def warmup_side_effect(skills):
        for i, s in enumerate(skills):
            skill_embeddings._embedding_cache[s.name] = [_VEC_A, _VEC_B, _VEC_C][i]
        return len(skills)

    mock_warmup.side_effect = warmup_side_effect

    result = await skill_embeddings.build_index()

    assert result == 3
    assert skill_embeddings.is_warmed() is True
    assert skill_embeddings.get_skill_embedding("seo_checklist") is not None


# ---------------------------------------------------------------------------
# Test 2: build_index uses asyncio.to_thread (non-blocking)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.skills.skill_embeddings.warmup_skill_embeddings")
@patch("app.skills.registry.skills_registry")
@patch("app.skills.skill_embeddings.asyncio")
async def test_build_index_uses_to_thread(mock_asyncio, mock_registry, mock_warmup):
    """build_index wraps warmup_skill_embeddings in asyncio.to_thread."""
    from app.skills import skill_embeddings

    skill_embeddings._embedding_cache.clear()

    mock_registry.list_all.return_value = FAKE_SKILLS

    # Make to_thread return a coroutine that resolves to 3
    async def fake_to_thread(fn, *args):
        return fn(*args)

    mock_asyncio.to_thread = MagicMock(side_effect=fake_to_thread)
    mock_warmup.return_value = 3

    result = await skill_embeddings.build_index()

    mock_asyncio.to_thread.assert_called_once_with(
        mock_warmup, FAKE_SKILLS
    )
    assert result == 3


# ---------------------------------------------------------------------------
# Test 3: search_similar returns sorted results
# ---------------------------------------------------------------------------
@patch("app.skills.skill_embeddings.generate_embedding", side_effect=_fake_embedding)
def test_search_similar_returns_sorted(mock_embed):
    """search_similar returns (name, score) tuples sorted by descending similarity."""
    from app.skills import skill_embeddings

    # Populate cache
    skill_embeddings._embedding_cache.clear()
    skill_embeddings._embedding_cache["seo_checklist"] = _VEC_A
    skill_embeddings._embedding_cache["budget_analysis"] = _VEC_B
    skill_embeddings._embedding_cache["social_media"] = _VEC_C

    results = skill_embeddings.search_similar("test query", limit=3)

    assert len(results) == 3
    # All results are (name, score) tuples
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    # Sorted descending by score
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True)
    # seo_checklist (VEC_A=[1,0,0]) should be most similar to query [0.9,0.1,0]
    assert results[0][0] == "seo_checklist"


# ---------------------------------------------------------------------------
# Test 4: search_similar returns empty list when cache is empty
# ---------------------------------------------------------------------------
def test_search_similar_empty_cache():
    """search_similar returns [] when embedding cache is cold."""
    from app.skills import skill_embeddings

    skill_embeddings._embedding_cache.clear()

    results = skill_embeddings.search_similar("anything")
    assert results == []


# ---------------------------------------------------------------------------
# Test 5: add_skill_embedding_async wraps sync add in to_thread
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.skills.skill_embeddings.add_skill_embedding", return_value=True)
async def test_add_skill_embedding_async(mock_add):
    """add_skill_embedding_async delegates to sync version via to_thread."""
    from app.skills import skill_embeddings

    result = await skill_embeddings.add_skill_embedding_async("new_skill", "A new skill")

    assert result is True
    mock_add.assert_called_once_with("new_skill", "A new skill")


# ---------------------------------------------------------------------------
# Test 6: build_index returns 0 when no skills registered
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("app.skills.registry.skills_registry")
async def test_build_index_no_skills(mock_registry):
    """build_index returns 0 and does not error when no skills registered."""
    from app.skills import skill_embeddings

    skill_embeddings._embedding_cache.clear()
    mock_registry.list_all.return_value = []

    result = await skill_embeddings.build_index()

    assert result == 0
    assert skill_embeddings.is_warmed() is False
