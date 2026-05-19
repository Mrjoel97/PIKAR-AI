"""Unit tests for app.services.intelligence.confidence."""

from __future__ import annotations

import math

import pytest

from app.services.intelligence.confidence import score_confidence, to_band


# ---------------------------------------------------------------------------
# score_confidence
# ---------------------------------------------------------------------------


def test_score_confidence_basic_weighted_sum():
    """A simple two-input case computes (0.8 * 0.5) + (0.6 * 0.5) = 0.7."""
    result = score_confidence(
        inputs={"a": 0.8, "b": 0.6},
        weights={"a": 0.5, "b": 0.5},
    )
    assert math.isclose(result, 0.7, abs_tol=1e-9)


def test_score_confidence_clamps_to_max_one():
    """Weighted sum exceeding 1.0 is clamped to 1.0."""
    result = score_confidence(
        inputs={"a": 2.0},
        weights={"a": 1.0},
    )
    assert result == 1.0


def test_score_confidence_clamps_to_min_zero():
    """Negative weighted sum is clamped to 0.0."""
    result = score_confidence(
        inputs={"a": -2.0},
        weights={"a": 0.5},
    )
    assert result == 0.0


def test_score_confidence_rejects_key_mismatch():
    """Input keys and weight keys must match exactly."""
    with pytest.raises(ValueError, match="key mismatch|keys"):
        score_confidence(
            inputs={"a": 0.5, "b": 0.5},
            weights={"a": 0.5, "c": 0.5},
        )


def test_score_confidence_rejects_weights_over_one():
    """Weights summing above 1.0 (with epsilon) are rejected."""
    with pytest.raises(ValueError, match="weights sum"):
        score_confidence(
            inputs={"a": 0.5, "b": 0.5},
            weights={"a": 0.7, "b": 0.7},  # sums to 1.4
        )


def test_score_confidence_accepts_weights_summing_to_one():
    """Weights summing to exactly 1.0 are accepted."""
    result = score_confidence(
        inputs={"a": 0.8, "b": 0.4},
        weights={"a": 0.5, "b": 0.5},
    )
    assert math.isclose(result, 0.6, abs_tol=1e-9)


def test_score_confidence_accepts_weights_summing_under_one():
    """Weights summing below 1.0 are accepted (caller's choice)."""
    result = score_confidence(
        inputs={"a": 1.0, "b": 1.0},
        weights={"a": 0.3, "b": 0.3},
    )
    assert math.isclose(result, 0.6, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# to_band
# ---------------------------------------------------------------------------


def test_to_band_low():
    """Below 0.50 default threshold is 'low'."""
    assert to_band(0.0) == "low"
    assert to_band(0.49) == "low"
    assert to_band(0.499999) == "low"


def test_to_band_medium():
    """Inclusive [0.50, 0.75) is 'medium'."""
    assert to_band(0.50) == "medium"
    assert to_band(0.60) == "medium"
    assert to_band(0.749999) == "medium"


def test_to_band_high():
    """Inclusive [0.75, 1.0] is 'high'."""
    assert to_band(0.75) == "high"
    assert to_band(0.90) == "high"
    assert to_band(1.0) == "high"


def test_to_band_custom_thresholds():
    """Caller can override band thresholds."""
    # Tighter: only > 0.90 is high
    assert to_band(0.85, low_threshold=0.30, high_threshold=0.90) == "medium"
    assert to_band(0.91, low_threshold=0.30, high_threshold=0.90) == "high"


def test_to_band_monotonic():
    """Higher score never returns a lower band."""
    bands_order = {"low": 0, "medium": 1, "high": 2}
    prev_band_rank = -1
    for score in [0.0, 0.1, 0.3, 0.49, 0.50, 0.65, 0.749, 0.75, 0.85, 1.0]:
        band = to_band(score)
        rank = bands_order[band]
        assert rank >= prev_band_rank, f"non-monotonic at score={score}"
        prev_band_rank = rank
