"""Financial-domain confidence preset.

Phase 114-01 — used by Financial Agent tools in app/agents/financial/tools.py
to compute confidence + band on every numeric output.

Four signals (weights sum to 1.0):
- data_completeness     (0.30): share of expected period rows that landed
- reconciliation_signal (0.30): accounting identity residual (closer to 0 = better)
- horizon_certainty     (0.25): historical (1.0) -> long-range forecast (~0.1)
- source_authority      (0.15): Stripe/Plaid > mixed > manual
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

FINANCIAL_WEIGHTS: dict[str, float] = {
    "data_completeness": 0.30,
    "reconciliation_signal": 0.30,
    "horizon_certainty": 0.25,
    "source_authority": 0.15,
}


def financial_confidence(
    *,
    data_completeness: float,
    reconciliation_signal: float,
    horizon_certainty: float,
    source_authority: float,
) -> float:
    """Compute financial-domain confidence from four signals.

    All inputs MUST be normalized to [0.0, 1.0] by the caller. The shared
    score_confidence scorer clamps the final value, so caller-side bugs
    (e.g. a stray > 1.0) do not produce out-of-range output, but they will
    skew the score; presets are not the right place to enforce caller hygiene.

    Args:
        data_completeness: Fraction of expected period rows landed [0, 1].
        reconciliation_signal: Accounting-identity residual normalized [0, 1]
            where 1.0 means residual == 0 and 0.0 means residual is as large
            as the cash position.
        horizon_certainty: 1.0 for historical analysis; decays toward 0.0 as
            forecast horizon (months) grows. Conventional formula in callers:
            ``max(0.1, 1.0 - months_ahead / 12.0)``.
        source_authority: 1.0 when all rows come from Stripe/Plaid; lower
            when mixed with manual or scraped entries.

    Returns:
        Confidence in [0.0, 1.0].
    """
    return score_confidence(
        inputs={
            "data_completeness": data_completeness,
            "reconciliation_signal": reconciliation_signal,
            "horizon_certainty": horizon_certainty,
            "source_authority": source_authority,
        },
        weights=FINANCIAL_WEIGHTS,
    )
