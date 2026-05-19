"""Perf test: write_claim with embed=True + auto-contradiction stays under budget.

20 measured writes after 5 warm-up writes; asserts p95 latency <= 750ms
end-to-end (embedding + contradiction query + row insert).

Requires a running local Supabase stack WITH real embedding credentials.
In zero-vector fallback mode the test is skipped — executor overhead for
the fallback path is not representative of production latency.
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


def _embeddings_available() -> bool:
    """Return True only when the embedding service returns real (non-zero) vectors."""
    from app.rag.embedding_service import generate_embedding

    emb = generate_embedding("test")
    return any(v != 0.0 for v in emb[:10])


@pytest.mark.asyncio
async def test_write_claim_embed_true_p95_under_budget():
    """20 writes of embed=True claims; p95 latency <= 750ms (rough end-to-end).

    The 750ms budget encompasses:
    - Embedding generation (~50-150ms with real Vertex AI / Google API creds)
    - Contradiction detection pgvector query (~20-50ms on local Supabase)
    - Supabase row insert (~50-100ms)
    - JSON serialisation and network overhead

    Skipped when embeddings are in zero-vector fallback mode; the fallback
    path incurs abnormal executor cold-start overhead that is not representative
    of production latency with real embedding calls.
    """
    loop = asyncio.get_event_loop()
    real_embeddings = await loop.run_in_executor(None, _embeddings_available)
    if not real_embeddings:
        pytest.skip(
            "Embedding service in zero-vector fallback mode (no Google credentials). "
            "Performance test requires real embeddings to measure meaningful latency. "
            "Set GOOGLE_API_KEY or Vertex AI env vars and re-run."
        )

    from uuid import uuid4

    from app.services.intelligence import get_or_create_entity, write_claim

    entity = await get_or_create_entity(
        canonical_name=f"perf_test_{uuid4()}",
        entity_type="topic",
        domains=["test"],
    )

    # Seed 5 existing claims so contradiction-detect has rows to compare against
    for i in range(5):
        await write_claim(
            entity_id=entity,
            domain="test",
            finding_text=(
                f"Baseline observation {i}: stable behavior across cohorts "
                "in the measurement window"
            ),
            confidence=0.5,
            sources=[],
            agent_id="test",
            claim_type="probe",
            embed=True,
        )

    latencies_ms: list[float] = []
    for i in range(20):
        start = time.perf_counter()
        await write_claim(
            entity_id=entity,
            domain="test",
            finding_text=(
                f"New observation {i}: behavior changed in recent measurement window"
            ),
            confidence=0.6,
            sources=[],
            agent_id="test",
            claim_type="probe",
            embed=True,
        )
        latencies_ms.append((time.perf_counter() - start) * 1000)

    latencies_ms.sort()
    p50_idx = len(latencies_ms) // 2
    p95_idx = int(len(latencies_ms) * 0.95)
    p50 = latencies_ms[p50_idx]
    p95 = latencies_ms[p95_idx]
    print(f"\np50={p50:.1f}ms p95={p95:.1f}ms (n={len(latencies_ms)})")
    print(f"min={latencies_ms[0]:.1f}ms max={latencies_ms[-1]:.1f}ms")

    assert p95 <= 750, (
        f"p95={p95:.0f}ms exceeds 750ms budget. "
        "The contradiction detection query or embedding generation is too slow. "
        "Consider reducing _contradiction_query_rows LIMIT from 20 to 10, "
        "or adding a covering index on (entity_id, embedding IS NOT NULL)."
    )
