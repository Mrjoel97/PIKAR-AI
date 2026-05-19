"""Integration test: cross-agent claims auto-populate contradicts.

Requires a running local Supabase stack with SUPABASE_URL,
SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL set, AND a working embedding
service (real Vertex AI / Google API key). When embeddings fall back to zeros
(no credentials), cosine distance becomes NaN and no contradictions are flagged
— the test is skipped in that case.
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


def _embeddings_available() -> bool:
    """Return True only when the embedding service will return real (non-zero) vectors."""
    from app.rag.embedding_service import generate_embedding

    emb = generate_embedding("test")
    return any(v != 0.0 for v in emb[:10])


@pytest.mark.asyncio
async def test_conflicting_claims_auto_flag():
    """Data's Q1 retention claim should flag Research's contradicting claim.

    Writes a Research claim first (industry baseline 71%), then a Data claim
    (company-specific 62%). Both are about the same entity and period, so
    their embeddings should be close enough for detect_contradictions to flag
    them. The Data claim's ``contradicts`` field should contain the Research
    claim's UUID.

    Skipped when the embedding service is in zero-vector fallback mode (no
    Google credentials configured) — zero vectors produce NaN cosine distance
    which cannot satisfy the similarity threshold.
    """
    loop = asyncio.get_event_loop()
    real_embeddings = await loop.run_in_executor(None, _embeddings_available)
    if not real_embeddings:
        pytest.skip(
            "Embedding service in zero-vector fallback mode (no Google credentials). "
            "Contradiction detection requires real embeddings to compute cosine similarity. "
            "Set GOOGLE_API_KEY or Vertex AI env vars and re-run."
        )

    from app.services.intelligence import (
        find_claims,
        get_or_create_entity,
        write_claim,
    )

    e = await get_or_create_entity(
        canonical_name=f"contradiction_q1_{uuid4()}",
        entity_type="metric",
        domains=["data", "research"],
    )

    # Research writes the industry baseline first
    research_id = await write_claim(
        entity_id=e,
        domain="research",
        finding_text=(
            "Industry Q1 2026 customer retention averaged 71 percent across benchmarks"
        ),
        confidence=0.8,
        sources=[{"kind": "url", "ref": "https://example.com/industry-report"}],
        agent_id="research",
        claim_type="research_finding",
        embed=True,
    )

    # Data writes the company-specific claim — should auto-detect the research
    # claim as a contradicting candidate
    data_id = await write_claim(
        entity_id=e,
        domain="data",
        finding_text=(
            "Q1 2026 customer retention dropped to 62 percent at our company"
        ),
        confidence=0.85,
        sources=[{"kind": "stripe_row", "ref": "test"}],
        agent_id="data",
        claim_type="cohort_summary",
        embed=True,
    )

    # Inspect the data claim's contradicts field
    all_claims = await find_claims(entity_id=e, limit=10)
    target = next((c for c in all_claims if c.id == data_id), None)
    assert target is not None, f"Data claim {data_id} not found in find_claims result"

    # The research claim should be in contradicts
    assert research_id in target.contradicts, (
        f"Expected research claim {research_id} in contradicts, "
        f"got {target.contradicts}. "
        "Cosine similarity between the two claims may be below threshold. "
        "Check actual distance and consider adjusting claim phrasings or threshold."
    )
