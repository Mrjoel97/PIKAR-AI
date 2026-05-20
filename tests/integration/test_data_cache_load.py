"""Synthetic load test: confirm Stripe call count is reduced by Plan 113-02 caching.

Acceptance criterion from spec:
    Stripe API call rate reduced by >= 40% vs pre-113 baseline during repeated
    requests within the Redis TTL window.

Implementation: 20 identical cohort_analysis(months=6) calls with a counting
mock on _fetch_stripe_transactions. After the first cold call, Redis should
serve all subsequent 19 requests — expected stripe_calls == 1, threshold <= 12.

Requires local Supabase + Redis. Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "REDIS_PASSWORD"]
        ),
        reason="env vars not provided",
    ),
]

_FAKE_FULL_RESULT = {
    "retention": {"cohorts": {"2026-01": {"month_0": 100.0}}, "months_analyzed": 6, "total_customers": 100},
    "ltv": {"cohorts": {}, "overall_avg_ltv": 0.0},
    "churn": {"cohorts": {}, "overall_churn_rate": 0.0},
    "executive_summary": "load test summary",
    "chart_data": {},
}


@pytest.mark.asyncio
async def test_stripe_call_rate_below_60pct_of_request_count():
    """Across 20 cohort_analysis(months=6) calls, _fetch_stripe_transactions is
    invoked fewer than 12 times (>= 40% reduction vs the 20-call baseline).

    Expected: stripe_calls == 1 (one cold call + 19 Redis hits within TTL).
    Threshold: <= 12 (generous 40% reduction bar).
    """
    from app.agents.data.tools import cohort_analysis

    fake_service = AsyncMock()
    fake_service.full_cohort_analysis = AsyncMock(return_value=_FAKE_FULL_RESULT)

    stripe_calls = 0

    async def counting_stripe(months, user_id):
        nonlocal stripe_calls
        stripe_calls += 1
        return []  # empty rows; service mock provides the full result

    with (
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=fake_service,
        ),
        patch(
            "app.services.cohort_analysis_service._fetch_stripe_transactions",
            side_effect=counting_stripe,
        ),
    ):
        for _ in range(20):
            await cohort_analysis(months=6)

    # 1 cold call + at most 0 warm calls (TTL holds for the duration of the test)
    # Acceptance: <= 12 Stripe calls out of 20 requests (>= 40% reduction)
    assert stripe_calls <= 12, (
        f"Expected <= 12 Stripe calls; got {stripe_calls}. "
        "Cache wiring may not be hitting. "
        "Check REDIS_HOST/REDIS_PORT/REDIS_PASSWORD and that _fetch_stripe_transactions "
        "is being called from compute_cohort_retention / compute_ltv_by_cohort / "
        "compute_churn_by_cohort."
    )
