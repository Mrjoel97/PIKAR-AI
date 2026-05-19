"""Research-domain confidence preset.

Bit-identical replacement for app/agents/research/tools/synthesizer.py:
calculate_confidence. Plan 112-05 wires Research onto this implementation.
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

RESEARCH_WEIGHTS = {
    "track_agreement": 0.35,
    "source_quality": 0.30,
    "freshness": 0.20,
    "contradiction_adjusted": 0.15,
}


def research_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Compute research-domain confidence from multi-track signals.

    Preserves the legacy formula exactly, including freshness floor clamp.

    Args:
        track_agreement: Cross-validated finding ratio in [0.0, 1.0].
        source_quality: Average source relevance in [0.0, 1.0].
        freshness: Recency score; values < 0 are floor-clamped at 0 (legacy).
        contradictions_found: Count of contradictions; penalty saturates at 20.

    Returns:
        Confidence in [0.0, 1.0].
    """
    contradiction_penalty = min(1.0, contradictions_found * 0.05)
    freshness_clamped = max(0.0, freshness)

    return score_confidence(
        inputs={
            "track_agreement": track_agreement,
            "source_quality": source_quality,
            "freshness": freshness_clamped,
            "contradiction_adjusted": 1.0 - contradiction_penalty,
        },
        weights=RESEARCH_WEIGHTS,
    )
