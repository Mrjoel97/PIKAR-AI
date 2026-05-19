"""Unit tests for detect_contradictions with mocked embedding + DB."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.mark.asyncio
async def test_detect_contradictions_returns_high_similarity_uuids():
    """Rows above threshold are returned as contradicting candidates."""
    from app.services.intelligence.claims import detect_contradictions

    entity = uuid4()
    similar_id = uuid4()
    dissimilar_id = uuid4()
    fake_rows = [
        {"id": str(similar_id), "similarity": 0.05},  # very close (0.05 distance)
        {"id": str(dissimilar_id), "similarity": 0.50},  # far
    ]

    with patch(
        "app.services.intelligence.claims._embed_text",
        new=AsyncMock(return_value=[0.1] * 768),
    ), patch(
        "app.services.intelligence.claims._contradiction_query_rows",
        new=AsyncMock(return_value=fake_rows),
    ):
        # threshold 0.85 means: similarity (= 1 - distance) >= 0.85,
        # so distance <= 0.15. Only similar_id qualifies (distance=0.05).
        result = await detect_contradictions(
            "Q1 2026 retention dropped to 62 percent", entity_id=entity, threshold=0.85,
        )

    assert similar_id in result
    assert dissimilar_id not in result


@pytest.mark.asyncio
async def test_detect_contradictions_no_embedding_returns_empty():
    """If embedding generation fails, return [] (degrade silently)."""
    from app.services.intelligence.claims import detect_contradictions

    with patch(
        "app.services.intelligence.claims._embed_text",
        new=AsyncMock(return_value=None),
    ):
        result = await detect_contradictions(
            "anything longer than twenty chars", entity_id=uuid4(),
        )
    assert result == []


@pytest.mark.asyncio
async def test_detect_contradictions_filters_by_entity():
    """Only rows attached to the entity are considered."""
    from app.services.intelligence.claims import detect_contradictions

    captured = {}

    async def capture_query(*, embedding, entity_id):
        captured["entity_id"] = entity_id
        return []

    entity = uuid4()
    with patch(
        "app.services.intelligence.claims._embed_text",
        new=AsyncMock(return_value=[0.1] * 768),
    ), patch(
        "app.services.intelligence.claims._contradiction_query_rows",
        side_effect=capture_query,
    ):
        await detect_contradictions(
            "this text is longer than twenty chars", entity_id=entity,
        )

    assert captured["entity_id"] == entity
