"""Generic weighted confidence scorer and band classifier.

Used by per-agent presets (presets/research.py, presets/data.py, ...).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.services.intelligence.schemas import ConfidenceBand

_WEIGHTS_SUM_EPSILON = 1e-4


def score_confidence(
    inputs: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Compute a clamped weighted-sum confidence score.

    Args:
        inputs: Named signals (e.g., {"track_agreement": 0.8, "freshness": 0.6}).
                Each value should be normalized to [0.0, 1.0] by the caller,
                but the function does not enforce that (presets may apply
                domain-specific normalization first).
        weights: Same keys as inputs. Must sum to <= 1.0 (with small epsilon).

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Raises:
        ValueError: if input/weight keys mismatch or weights sum exceeds 1.0.
    """
    if set(inputs) != set(weights):
        raise ValueError(
            f"input/weight key mismatch: {set(inputs) ^ set(weights)}"
        )
    weights_sum = sum(weights.values())
    if weights_sum > 1.0 + _WEIGHTS_SUM_EPSILON:
        raise ValueError(f"weights sum > 1.0: {weights_sum}")

    raw = sum(inputs[k] * weights[k] for k in inputs)
    return max(0.0, min(1.0, raw))


def to_band(
    score: float,
    *,
    low_threshold: float = 0.50,
    high_threshold: float = 0.75,
) -> ConfidenceBand:
    """Classify a raw confidence float into a band.

    Defaults match Research Agent's existing convention:
    < 0.50 = low, 0.50 - 0.75 (exclusive) = medium, >= 0.75 = high.
    """
    if score < low_threshold:
        return "low"
    if score < high_threshold:
        return "medium"
    return "high"
