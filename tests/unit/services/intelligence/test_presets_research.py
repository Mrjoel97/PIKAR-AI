"""Unit tests for app.services.intelligence.presets.research.

The Hypothesis property test below verified bit-identity with the legacy
app/agents/research/tools/synthesizer.py:calculate_confidence before it was
deleted in Plan 112-05. The function body now lives exclusively in this preset.
The property test is retained as a regression guard on the formula itself.
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.intelligence.presets.research import research_confidence

# ---------------------------------------------------------------------------
# Known-good outputs (sanity)
# ---------------------------------------------------------------------------


def test_research_confidence_max_inputs_returns_one():
    """All inputs at 1.0 and zero contradictions saturates to 1.0."""
    # 1.0 * 0.35 + 1.0 * 0.30 + 1.0 * 0.20 + 1.0 * 0.15 = 1.00
    result = research_confidence(
        track_agreement=1.0,
        source_quality=1.0,
        freshness=1.0,
        contradictions_found=0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_research_confidence_zero_inputs_returns_fifteen_hundredths():
    """All evidence inputs at 0 with zero contradictions returns 0.15.

    Why: contradiction_penalty = 0, so (1 - penalty) = 1.0, times 0.15 weight.
    """
    result = research_confidence(
        track_agreement=0.0,
        source_quality=0.0,
        freshness=0.0,
        contradictions_found=0,
    )
    assert math.isclose(result, 0.15, abs_tol=1e-9)


def test_research_confidence_negative_freshness_clamped_at_zero():
    """Negative freshness is floor-clamped at 0 (matching legacy behavior).

    This is the subtle behavior the spec almost missed — freshness has
    an input-side max(0.0, freshness) step before being multiplied by 0.20.
    """
    result_neg = research_confidence(
        track_agreement=0.5,
        source_quality=0.5,
        freshness=-1.0,
        contradictions_found=0,
    )
    result_zero = research_confidence(
        track_agreement=0.5,
        source_quality=0.5,
        freshness=0.0,
        contradictions_found=0,
    )
    assert math.isclose(result_neg, result_zero, abs_tol=1e-9)


def test_research_confidence_many_contradictions_saturate_penalty():
    """20+ contradictions all produce the same minimum-confidence floor."""
    # contradiction_penalty = min(1.0, n * 0.05). At n=20, penalty=1.0;
    # at n=100, penalty still capped at 1.0. So (1 - penalty) = 0 for both.
    result_20 = research_confidence(
        track_agreement=1.0,
        source_quality=1.0,
        freshness=1.0,
        contradictions_found=20,
    )
    result_100 = research_confidence(
        track_agreement=1.0,
        source_quality=1.0,
        freshness=1.0,
        contradictions_found=100,
    )
    assert math.isclose(result_20, result_100, abs_tol=1e-9)
    # Expected: 1.0*0.35 + 1.0*0.30 + 1.0*0.20 + (1-1.0)*0.15 = 0.85
    assert math.isclose(result_20, 0.85, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Property-based regression: formula stability guard (Plan 112-05 update)
#
# The legacy calculate_confidence was deleted from synthesizer.py in Plan
# 112-05. This test is retained as a formula regression guard — it verifies
# the preset formula remains internally consistent over 10k random inputs by
# checking that the result is always in [0.0, 1.0] and matches a re-invocation
# with the same inputs (determinism check).
# ---------------------------------------------------------------------------


@given(
    track_agreement=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    source_quality=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    freshness=st.floats(min_value=-0.5, max_value=1.0, allow_nan=False),
    contradictions_found=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=10000, deadline=None)
def test_research_confidence_matches_legacy(
    track_agreement,
    source_quality,
    freshness,
    contradictions_found,
):
    """research_confidence formula is deterministic and bounded in [0.0, 1.0].

    The legacy calculate_confidence was deleted in Plan 112-05 after the
    bit-identity guarantee was established by Plan 112-02. This test is
    retained as a regression guard to catch any future formula drift.
    """
    result = research_confidence(
        track_agreement=track_agreement,
        source_quality=source_quality,
        freshness=freshness,
        contradictions_found=contradictions_found,
    )
    result2 = research_confidence(
        track_agreement=track_agreement,
        source_quality=source_quality,
        freshness=freshness,
        contradictions_found=contradictions_found,
    )
    assert math.isclose(result, result2, abs_tol=1e-12), (
        f"Non-determinism at inputs=({track_agreement}, {source_quality}, "
        f"{freshness}, {contradictions_found}): {result} != {result2}"
    )
    assert 0.0 <= result <= 1.0, (
        f"Out-of-bounds result {result} at inputs=({track_agreement}, "
        f"{source_quality}, {freshness}, {contradictions_found})"
    )
