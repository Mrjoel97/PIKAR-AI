"""Threshold-tuning test against the hand-curated contradiction fixture.

Reports false-positive rate at threshold 0.85. Acceptance: <= 10%.

Requires a running local Supabase stack with real embedding credentials.
When the embedding service is in zero-vector fallback mode, all cosine
distances are NaN so no pairs are detected — the test skips automatically.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

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
async def test_threshold_tuning_at_default_0_85():
    """At threshold 0.85: false-positive rate <= 10% on the 50-pair fixture.

    For each pair: seeds claim_a under a unique entity, then runs
    detect_contradictions(claim_b, entity_id, threshold=0.85) and tallies
    TP/FP/FN/TN. Skips when embeddings are in zero-vector fallback mode.
    """
    loop = asyncio.get_event_loop()
    real_embeddings = await loop.run_in_executor(None, _embeddings_available)
    if not real_embeddings:
        pytest.skip(
            "Embedding service in zero-vector fallback mode (no Google credentials). "
            "Threshold tuning requires real embeddings. "
            "Set GOOGLE_API_KEY or Vertex AI env vars and re-run."
        )

    from app.services.intelligence import get_or_create_entity, write_claim
    from app.services.intelligence.claims import detect_contradictions

    fixture_path = Path("tests/fixtures/contradiction_pairs.json")
    pairs = json.loads(fixture_path.read_text())

    false_positives = 0
    false_negatives = 0
    true_positives = 0
    true_negatives = 0
    should_flag_count = sum(1 for p in pairs if p["should_flag"])
    should_not_flag_count = len(pairs) - should_flag_count

    for pair in pairs:
        entity = await get_or_create_entity(
            canonical_name=f"tune_{pair['id']}_{uuid4()}",
            entity_type="topic",
            domains=["test"],
        )
        # Write claim_a as the seed
        await write_claim(
            entity_id=entity,
            domain="test",
            finding_text=pair["claim_a"],
            confidence=0.5,
            sources=[],
            agent_id="test",
            claim_type="probe",
            embed=True,
        )
        # Run detection against claim_b text
        detected = await detect_contradictions(
            pair["claim_b"],
            entity_id=entity,
            threshold=0.85,
        )
        flagged = len(detected) > 0

        if pair["should_flag"] and flagged:
            true_positives += 1
        elif pair["should_flag"] and not flagged:
            false_negatives += 1
            print(f"FALSE NEGATIVE on {pair['id']}: {pair['reason']}")
        elif not pair["should_flag"] and flagged:
            false_positives += 1
            print(f"FALSE POSITIVE on {pair['id']}: {pair['reason']}")
        else:
            true_negatives += 1

    fp_rate = false_positives / max(1, should_not_flag_count)
    fn_rate = false_negatives / max(1, should_flag_count)

    print(
        f"\nTP={true_positives} FP={false_positives} "
        f"FN={false_negatives} TN={true_negatives}"
    )
    print(f"FP rate (target <= 0.10): {fp_rate:.2%}")
    print(f"FN rate (informational, no target): {fn_rate:.2%}")

    assert fp_rate <= 0.10, (
        f"False-positive rate {fp_rate:.2%} exceeds 10% target. "
        f"Increase threshold above 0.85 to be more conservative."
    )
