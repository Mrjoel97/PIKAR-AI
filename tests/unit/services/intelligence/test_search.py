"""Unit tests for app.services.intelligence.claims.search_claims_semantic (Plan 113-04).

These tests mock all I/O — no real DB or Vertex AI calls are made.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Helper: build a minimal raw DB row (as psycopg would return)
# ---------------------------------------------------------------------------


def _make_row(
    *,
    finding_text: str = "test finding",
    confidence: float = 0.85,
    agent_id: str = "data",
    claim_type: str = "cohort_summary",
    domain: str = "data",
    similarity: float = 0.12,
) -> dict:
    """Build a dict mimicking what _semantic_query_rows returns."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid4()),
        "entity_id": str(uuid4()),
        "edge_id": None,
        "agent_id": agent_id,
        "claim_type": claim_type,
        "domain": domain,
        "finding_text": finding_text,
        "confidence": confidence,
        "sources": [],
        "contradicts": [],
        "freshness_at": now_iso,
        "expires_at": None,
        "created_at": now_iso,
        "similarity": similarity,
    }


# ---------------------------------------------------------------------------
# test_search_claims_semantic_returns_claims_ordered_by_similarity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_claims_semantic_returns_claims_ordered_by_similarity():
    """Mocked DB rows come back as Claim objects, distances preserved as similarity floats."""
    from app.services.intelligence.claims import search_claims_semantic
    from app.services.intelligence.schemas import Claim

    row_near = _make_row(
        finding_text="cohort retention dropped 12% in Q1",
        similarity=0.05,  # closer (lower cosine distance)
    )
    row_far = _make_row(
        finding_text="GDPR compliance regulation review",
        claim_type="compliance_finding",
        agent_id="compliance",
        similarity=0.80,
    )

    mock_embed = AsyncMock(return_value=[0.1] * 768)
    mock_query = AsyncMock(return_value=[row_near, row_far])

    with (
        patch(
            "app.services.intelligence.claims._embed_text",
            mock_embed,
        ),
        patch(
            "app.services.intelligence.claims._semantic_query_rows",
            mock_query,
        ),
    ):
        results = await search_claims_semantic(query="cohort retention drop", top_k=10)

    assert len(results) == 2
    # Each element is (Claim, float)
    claim0, sim0 = results[0]
    claim1, sim1 = results[1]
    assert isinstance(claim0, Claim)
    assert isinstance(claim1, Claim)
    assert sim0 == pytest.approx(0.05)
    assert sim1 == pytest.approx(0.80)
    assert claim0.finding_text == "cohort retention dropped 12% in Q1"
    assert claim1.finding_text == "GDPR compliance regulation review"


# ---------------------------------------------------------------------------
# test_search_claims_semantic_skips_when_embedding_fails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_claims_semantic_skips_when_embedding_fails():
    """If embedding generation returns None, function returns empty list immediately."""
    from app.services.intelligence.claims import search_claims_semantic

    mock_embed = AsyncMock(return_value=None)
    mock_query = AsyncMock()  # should NOT be called

    with (
        patch(
            "app.services.intelligence.claims._embed_text",
            mock_embed,
        ),
        patch(
            "app.services.intelligence.claims._semantic_query_rows",
            mock_query,
        ),
    ):
        results = await search_claims_semantic(query="any query", top_k=5)

    assert results == []
    mock_query.assert_not_called()


# ---------------------------------------------------------------------------
# test_search_claims_semantic_top_k_respected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_claims_semantic_top_k_respected():
    """top_k argument is forwarded to _semantic_query_rows."""
    from app.services.intelligence.claims import search_claims_semantic

    mock_embed = AsyncMock(return_value=[0.0] * 768)
    mock_query = AsyncMock(return_value=[])

    with (
        patch(
            "app.services.intelligence.claims._embed_text",
            mock_embed,
        ),
        patch(
            "app.services.intelligence.claims._semantic_query_rows",
            mock_query,
        ),
    ):
        await search_claims_semantic(query="test", top_k=3)

    mock_query.assert_called_once()
    call_kwargs = mock_query.call_args
    # _semantic_query_rows is called with keyword args
    assert call_kwargs.kwargs.get("top_k") == 3 or (
        # fallback: positional call — check keyword or args
        len(call_kwargs.args) == 0 and call_kwargs.kwargs.get("top_k") == 3
    )
