"""Integration tests for semantic search across agents (Plan 113-04).

Requires local Supabase running with Phase 112 + 113-04 migrations applied.
Requires SUPABASE_DB_URL for psycopg direct access.

Skip with: pytest -m "not integration"

Design note: _embed_text is patched to return deterministic vectors so the
test does not depend on Vertex AI credentials. The two embeddings are
purposefully distant in semantic space (cohort vector vs GDPR vector) to
ensure cosine distance ordering is meaningful.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_DB_URL"]
        ),
        reason="SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_DB_URL must be set.",
    ),
]

# ---------------------------------------------------------------------------
# Deterministic embeddings (768-dim, unit-normalised)
# ---------------------------------------------------------------------------
# COHORT_EMBED: first half 1s, second half 0s (normalised)
# GDPR_EMBED:   first half 0s, second half 1s (normalised)
# These are maximally distant in cosine space (distance ≈ 1.0 apart)
# so "query_near_cohort" (≈ COHORT_EMBED) will be much closer to the cohort
# claim than to the GDPR claim.

import math

_DIM = 768
_HALF = _DIM // 2

_COHORT_EMBED = [1.0 / math.sqrt(_HALF)] * _HALF + [0.0] * (_DIM - _HALF)
_GDPR_EMBED = [0.0] * _HALF + [1.0 / math.sqrt(_DIM - _HALF)] * (_DIM - _HALF)
# Query embedding — almost identical to cohort (slight noise in last position)
_QUERY_EMBED = _COHORT_EMBED[:]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cleanup_entities():
    """Track entity IDs created during the test and delete them after."""
    created: list = []
    yield created
    if created:
        try:
            from supabase import create_client

            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            client = create_client(url, key)  # type: ignore[arg-type]
            for entity_id in created:
                try:
                    client.table("kg_entities").delete().eq(
                        "id", str(entity_id)
                    ).execute()
                except Exception:
                    pass
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_search_returns_relevant_claims(cleanup_entities):
    """Semantic search returns the cohort claim ranked above the GDPR claim.

    Flow:
    1. Seed two entities (cohort metric, GDPR regulation).
    2. Write cohort claim with a "cohort-like" embedding.
    3. Write GDPR claim with a "GDPR-like" embedding (orthogonal to cohort).
    4. Search with a query near the cohort embedding.
    5. Assert cohort claim appears before GDPR claim in results.
    """
    from app.services.intelligence.claims import (
        get_or_create_entity,
        search_claims_semantic,
        write_claim,
    )

    # --- seed entities ---
    cohort_entity_id = await get_or_create_entity(
        canonical_name=f"cohort_search_test_{uuid4()}",
        entity_type="metric",
        domains=["data"],
    )
    cleanup_entities.append(cohort_entity_id)

    gdpr_entity_id = await get_or_create_entity(
        canonical_name=f"gdpr_search_test_{uuid4()}",
        entity_type="regulation",
        domains=["compliance"],
    )
    cleanup_entities.append(gdpr_entity_id)

    # --- write cohort claim with cohort-like embedding ---
    cohort_embed_mock = AsyncMock(return_value=_COHORT_EMBED)
    with patch("app.services.intelligence.claims._embed_text", cohort_embed_mock):
        await write_claim(
            entity_id=cohort_entity_id,
            domain="data",
            finding_text=(
                "SaaS cohort analysis: month-3 retention dropped 18% for Q1 2026 "
                "cohort, indicating early churn pressure"
            ),
            confidence=0.88,
            sources=[{"kind": "stripe_row", "ref": "cohort:2026-01"}],
            agent_id="data",
            claim_type="cohort_summary",
            embed=True,
        )

    # --- write GDPR claim with GDPR-like embedding (orthogonal) ---
    gdpr_embed_mock = AsyncMock(return_value=_GDPR_EMBED)
    with patch("app.services.intelligence.claims._embed_text", gdpr_embed_mock):
        await write_claim(
            entity_id=gdpr_entity_id,
            domain="compliance",
            finding_text=(
                "GDPR Article 17 right-to-erasure compliance review: data retention "
                "policies require update for EU customer records"
            ),
            confidence=0.91,
            sources=[{"kind": "regulation", "ref": "GDPR:Art17"}],
            agent_id="compliance",
            claim_type="compliance_finding",
            embed=True,
        )

    # --- search with query near cohort ---
    query_embed_mock = AsyncMock(return_value=_QUERY_EMBED)
    with patch("app.services.intelligence.claims._embed_text", query_embed_mock):
        results = await search_claims_semantic(
            query="cohort retention drop", top_k=5
        )

    # --- assertions ---
    assert len(results) >= 2, (
        f"Expected at least 2 results; got {len(results)}. "
        "Check that both claims have embeddings stored."
    )

    texts = [claim.finding_text for claim, _ in results]
    sims = [sim for _, sim in results]

    cohort_idx = next(
        (i for i, (c, _) in enumerate(results) if c.agent_id == "data"), None
    )
    gdpr_idx = next(
        (i for i, (c, _) in enumerate(results) if c.agent_id == "compliance"), None
    )

    assert cohort_idx is not None, f"Cohort claim not found in results: {texts}"
    assert gdpr_idx is not None, f"GDPR claim not found in results: {texts}"

    assert cohort_idx < gdpr_idx, (
        f"Expected cohort claim (idx={cohort_idx}, sim={sims[cohort_idx]:.4f}) "
        f"to rank above GDPR claim (idx={gdpr_idx}, sim={sims[gdpr_idx]:.4f}). "
        "This may indicate the ivfflat index is not being used or the embeddings "
        "were not stored."
    )

    # Results must be sorted ascending by distance
    assert all(sims[i] <= sims[i + 1] for i in range(len(sims) - 1)), (
        f"Results not sorted by ascending similarity distance: {sims}"
    )

    # Log EXPLAIN ANALYZE output for pgvector index verification (informational only)
    try:
        import psycopg
        db_url = os.environ.get("SUPABASE_DB_URL")
        if db_url:
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "EXPLAIN ANALYZE SELECT id, (embedding <=> %s::vector) AS sim "
                        "FROM kg_findings ORDER BY embedding <=> %s::vector ASC LIMIT 5",
                        [_QUERY_EMBED, _QUERY_EMBED],
                    )
                    plan_rows = cur.fetchall()
                    plan_text = "\n".join(r[0] for r in plan_rows)
                    print(f"\n[EXPLAIN ANALYZE]\n{plan_text}\n")
    except Exception as e:
        print(f"[EXPLAIN ANALYZE skipped: {e}]")
