"""Data-domain confidence preset.

Phase 113-01 — pilots on the cohort_analysis tool in app/agents/data/tools.py.

The formula weights four signals:
- sample_adequacy  (0.35): are we working with enough rows to trust statistics?
- completeness     (0.25): how many fields are present (1 − missing_pct)?
- statistical_strength (0.25): how close to expected baseline?
                              *Inverted* — high sigma_distance means an
                              anomalous / unstable trend, reducing confidence.
- recency          (0.15): how fresh is the dataset?
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

DATA_WEIGHTS: dict[str, float] = {
    "sample_adequacy": 0.35,
    "completeness": 0.25,
    "statistical_strength": 0.25,
    "recency": 0.15,
}


def data_confidence(
    sample_size: int,
    missing_pct: float,
    sigma_distance: float,
    data_age_hours: float,
    *,
    sample_threshold: int = 100,
    recency_horizon_hours: float = 720,
) -> float:
    """Compute data-domain confidence from dataset quality signals.

    Args:
        sample_size: Number of data points / rows in the analysis.
        missing_pct: Fraction of missing fields in [0.0, 1.0].
        sigma_distance: Standard-deviation distance from a baseline expectation.
            High values (> 3) indicate anomalous / outlier data, which *lowers*
            confidence in trend stability (inverted signal — see note below).
            Pass 0.0 when no baseline is available (known TODO: wire a real
            baseline from CohortAnalysisService once it surfaces one).
        data_age_hours: Age of the freshest record in the dataset in hours.
        sample_threshold: Minimum sample size considered adequate (default 100).
        recency_horizon_hours: Age at which recency score reaches zero (default
            720 h = 30 days).

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Note — sigma inversion:
        ``statistical_strength = 1 - sigma_distance / 3`` is intentionally
        *inverted*: a sigma_distance of 0 means the data is right at the
        expected baseline (high confidence), while a distance ≥ 3 saturates to
        0.  This models the idea that highly anomalous results are less
        trustworthy as stable trend indicators.
    """
    sample_adequacy = min(1.0, sample_size / sample_threshold)
    completeness = max(0.0, 1.0 - missing_pct)
    statistical_strength = max(0.0, 1.0 - min(1.0, sigma_distance / 3.0))
    recency = max(0.0, 1.0 - min(1.0, data_age_hours / recency_horizon_hours))

    return score_confidence(
        inputs={
            "sample_adequacy": sample_adequacy,
            "completeness": completeness,
            "statistical_strength": statistical_strength,
            "recency": recency,
        },
        weights=DATA_WEIGHTS,
    )
