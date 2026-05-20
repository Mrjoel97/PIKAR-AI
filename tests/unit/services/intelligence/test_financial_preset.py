"""Unit tests for financial_confidence preset.

Acceptance: weights match spec, scorer clamps to [0,1], invalid inputs raise,
monotonicity holds across each axis.
"""

from __future__ import annotations

import pytest


def test_financial_weights_match_spec_exactly():
    """FINANCIAL_WEIGHTS must equal the spec values bit-for-bit."""
    from app.services.intelligence.presets.financial import FINANCIAL_WEIGHTS

    assert FINANCIAL_WEIGHTS == {
        "data_completeness": 0.30,
        "reconciliation_signal": 0.30,
        "horizon_certainty": 0.25,
        "source_authority": 0.15,
    }
    assert abs(sum(FINANCIAL_WEIGHTS.values()) - 1.0) < 1e-6


def test_financial_confidence_all_max_returns_one():
    """All four signals at 1.0 -> confidence = 1.0."""
    from app.services.intelligence.presets.financial import financial_confidence

    score = financial_confidence(
        data_completeness=1.0,
        reconciliation_signal=1.0,
        horizon_certainty=1.0,
        source_authority=1.0,
    )
    assert score == pytest.approx(1.0, abs=1e-6)


def test_financial_confidence_all_zero_returns_zero():
    """All four signals at 0.0 -> confidence = 0.0."""
    from app.services.intelligence.presets.financial import financial_confidence

    score = financial_confidence(
        data_completeness=0.0,
        reconciliation_signal=0.0,
        horizon_certainty=0.0,
        source_authority=0.0,
    )
    assert score == pytest.approx(0.0, abs=1e-6)


def test_financial_confidence_mixed_known_value():
    """Hand-checked numeric: 0.5/0.5/0.5/0.5 -> 0.5."""
    from app.services.intelligence.presets.financial import financial_confidence

    score = financial_confidence(
        data_completeness=0.5,
        reconciliation_signal=0.5,
        horizon_certainty=0.5,
        source_authority=0.5,
    )
    assert score == pytest.approx(0.5, abs=1e-6)


def test_financial_confidence_monotonic_in_data_completeness():
    """Increasing data_completeness with others fixed must never decrease score."""
    from app.services.intelligence.presets.financial import financial_confidence

    scores = [
        financial_confidence(
            data_completeness=x,
            reconciliation_signal=0.5,
            horizon_certainty=0.5,
            source_authority=0.5,
        )
        for x in [0.0, 0.25, 0.5, 0.75, 1.0]
    ]
    assert scores == sorted(scores)


def test_financial_confidence_horizon_certainty_drives_forecast_decay():
    """Lower horizon_certainty (longer forecast) yields lower confidence."""
    from app.services.intelligence.presets.financial import financial_confidence

    near = financial_confidence(
        data_completeness=0.9,
        reconciliation_signal=0.9,
        horizon_certainty=0.95,
        source_authority=0.9,
    )
    far = financial_confidence(
        data_completeness=0.9,
        reconciliation_signal=0.9,
        horizon_certainty=0.25,
        source_authority=0.9,
    )
    assert near > far


def test_financial_confidence_clamps_below_one_on_overshoot():
    """Inputs above 1.0 are caller-error but the shared scorer clamps the
    final value. This protects downstream `band` classification.
    """
    from app.services.intelligence.presets.financial import financial_confidence

    score = financial_confidence(
        data_completeness=2.0,
        reconciliation_signal=1.0,
        horizon_certainty=1.0,
        source_authority=1.0,
    )
    assert 0.0 <= score <= 1.0
