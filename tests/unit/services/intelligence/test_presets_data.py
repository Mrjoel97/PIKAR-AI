"""Unit tests for app.services.intelligence.presets.data.data_confidence.

15 boundary tests covering:
- Zero / tiny / full / oversized-clamped sample_size
- missing_pct variants (0, 0.5, 1.0)
- sigma_distance at 0, 1.5, 3.0, > 3 (saturation / clamping)
- recency horizon boundary (exactly at horizon, past horizon)
- Custom sample_threshold and recency_horizon_hours
- All-best (expected near 1.0) and all-worst (expected near 0.0) inputs
"""

from __future__ import annotations

import math

import pytest

from app.services.intelligence.presets.data import DATA_WEIGHTS, data_confidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _expected(
    sample_size: int,
    missing_pct: float,
    sigma_distance: float,
    data_age_hours: float,
    *,
    sample_threshold: int = 100,
    recency_horizon_hours: float = 720,
) -> float:
    """Reference implementation that mirrors the plan formula exactly."""
    w = DATA_WEIGHTS
    sample_adequacy = min(1.0, sample_size / sample_threshold)
    completeness = max(0.0, 1.0 - missing_pct)
    statistical_strength = max(0.0, 1.0 - min(1.0, sigma_distance / 3.0))
    recency = max(0.0, 1.0 - min(1.0, data_age_hours / recency_horizon_hours))
    raw = (
        sample_adequacy * w["sample_adequacy"]
        + completeness * w["completeness"]
        + statistical_strength * w["statistical_strength"]
        + recency * w["recency"]
    )
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------


def test_zero_sample_size():
    """sample_size=0 drives sample_adequacy to 0 — score is still positive via other signals."""
    result = data_confidence(0, 0.0, 0.0, 1.0)
    expected = _expected(0, 0.0, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)
    assert result >= 0.0


def test_sample_size_exactly_at_threshold():
    """sample_size == sample_threshold gives sample_adequacy == 1.0."""
    result = data_confidence(100, 0.0, 0.0, 1.0)
    expected = _expected(100, 0.0, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)


def test_sample_size_oversized_clamped():
    """sample_size >> sample_threshold is clamped to 1.0, not > 1.0."""
    result = data_confidence(9999, 0.0, 0.0, 1.0)
    expected = _expected(9999, 0.0, 0.0, 1.0)
    # Both should give same result as sample_size=100
    result_at_threshold = data_confidence(100, 0.0, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)
    assert math.isclose(result, result_at_threshold, abs_tol=1e-9)


def test_missing_pct_zero():
    """missing_pct=0 → completeness=1.0 (all data present)."""
    result = data_confidence(100, 0.0, 0.0, 1.0)
    expected = _expected(100, 0.0, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)


def test_missing_pct_half():
    """missing_pct=0.5 → completeness=0.5."""
    result = data_confidence(100, 0.5, 0.0, 1.0)
    expected = _expected(100, 0.5, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)


def test_missing_pct_full():
    """missing_pct=1.0 → completeness=0.0 (all fields missing)."""
    result = data_confidence(100, 1.0, 0.0, 1.0)
    expected = _expected(100, 1.0, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)


def test_sigma_zero_gives_full_statistical_strength():
    """sigma_distance=0 → statistical_strength=1.0 (no deviation from baseline)."""
    result = data_confidence(100, 0.0, 0.0, 1.0)
    expected = _expected(100, 0.0, 0.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)


def test_sigma_at_three_gives_zero_statistical_strength():
    """sigma_distance=3.0 → statistical_strength=0.0 (saturates at 3σ)."""
    result = data_confidence(100, 0.0, 3.0, 1.0)
    expected = _expected(100, 0.0, 3.0, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)
    # Without the statistical_strength signal, score should be < all-zeros-sigma score
    result_sigma_zero = data_confidence(100, 0.0, 0.0, 1.0)
    assert result < result_sigma_zero


def test_sigma_greater_than_three_clamped():
    """sigma_distance > 3 is clamped — same as sigma=3 (no negative contribution)."""
    result_3 = data_confidence(100, 0.0, 3.0, 1.0)
    result_10 = data_confidence(100, 0.0, 10.0, 1.0)
    assert math.isclose(result_3, result_10, abs_tol=1e-9)


def test_sigma_at_one_point_five():
    """sigma_distance=1.5 → statistical_strength=0.5 (halfway)."""
    result = data_confidence(100, 0.0, 1.5, 1.0)
    expected = _expected(100, 0.0, 1.5, 1.0)
    assert math.isclose(result, expected, abs_tol=1e-9)


def test_data_age_at_recency_horizon():
    """data_age_hours == recency_horizon_hours → recency=0.0."""
    result = data_confidence(100, 0.0, 0.0, 720.0)
    expected = _expected(100, 0.0, 0.0, 720.0)
    assert math.isclose(result, expected, abs_tol=1e-9)
    # recency=0 means the 0.15 weight is zeroed out
    result_fresh = data_confidence(100, 0.0, 0.0, 1.0)
    assert result < result_fresh


def test_data_age_past_recency_horizon_clamped():
    """data_age_hours >> horizon is clamped to recency=0.0 (no negative)."""
    result_at = data_confidence(100, 0.0, 0.0, 720.0)
    result_past = data_confidence(100, 0.0, 0.0, 9999.0)
    assert math.isclose(result_at, result_past, abs_tol=1e-9)


def test_custom_sample_threshold():
    """Custom sample_threshold=50 means sample_size=50 is fully adequate."""
    result_custom = data_confidence(50, 0.0, 0.0, 1.0, sample_threshold=50)
    result_default = data_confidence(100, 0.0, 0.0, 1.0, sample_threshold=100)
    assert math.isclose(result_custom, result_default, abs_tol=1e-9)


def test_custom_recency_horizon():
    """Custom recency_horizon_hours=48 ages out at 2 days."""
    result = data_confidence(100, 0.0, 0.0, 48.0, recency_horizon_hours=48)
    expected = _expected(100, 0.0, 0.0, 48.0, recency_horizon_hours=48)
    assert math.isclose(result, expected, abs_tol=1e-9)
    # recency=0 at exactly the horizon
    result_fresh = data_confidence(100, 0.0, 0.0, 1.0, recency_horizon_hours=48)
    assert result < result_fresh


def test_all_best_inputs_returns_one():
    """All signals at best possible values → confidence == 1.0.

    sample_size >> threshold, missing=0, sigma=0, age=0h.
    """
    result = data_confidence(10000, 0.0, 0.0, 0.0)
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_all_worst_inputs_returns_zero():
    """All signals at worst possible values → confidence == 0.0.

    sample_size=0, missing=1.0, sigma>=3, age>=horizon.
    """
    result = data_confidence(0, 1.0, 3.0, 720.0)
    assert math.isclose(result, 0.0, abs_tol=1e-9)
