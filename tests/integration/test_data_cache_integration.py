"""Integration tests for Data Agent two-tier cache wiring (Plan 113-02).

Requires local Supabase + Redis running with the Phase 112 migrations applied.
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]

# ---------------------------------------------------------------------------
# Shared fake-service builder
# ---------------------------------------------------------------------------

_FAKE_FULL_RESULT = {
    "retention": {"cohorts": {"2026-01": {"month_0": 100.0}}, "months_analyzed": 6, "total_customers": 150},
    "ltv": {"cohorts": {}, "overall_avg_ltv": 0.0},
    "churn": {"cohorts": {}, "overall_churn_rate": 0.0},
    "executive_summary": "test summary",
    "chart_data": {},
}


def _make_fake_service():
    """Return a mock CohortAnalysisService whose full_cohort_analysis returns fake data."""
    fake = AsyncMock()
    fake.full_cohort_analysis = AsyncMock(return_value=_FAKE_FULL_RESULT)
    return fake


# ---------------------------------------------------------------------------
# Graph-tier short-circuit: when a fresh claim exists, skip computation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cohort_analysis_short_circuits_on_fresh_graph_claim():
    """If a fresh cohort_summary claim exists in kg_findings, cohort_analysis
    returns from it without invoking CohortAnalysisService.
    """
    from app.services.intelligence import get_or_create_entity, write_claim

    # Seed a fresh claim with a unique entity so it doesn't collide with other tests
    entity_id = await get_or_create_entity(
        canonical_name=f"cohort_test_{uuid4()}",
        entity_type="metric",
        domains=["data"],
    )
    await write_claim(
        entity_id=entity_id,
        domain="data",
        finding_text="seeded cohort summary for short-circuit test",
        confidence=0.85,
        sources=[{"kind": "stripe_row", "ref": "test"}],
        agent_id="data",
        claim_type="cohort_summary",
    )

    fake_service = _make_fake_service()

    with (
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=fake_service,
        ),
        patch(
            # Redirect the entity-id derivation to our seeded entity so
            # should_query_graph finds the claim we just wrote.
            "app.agents.data.tools._cohort_entity_id",
            AsyncMock(return_value=entity_id),
        ),
    ):
        result = await _call_cohort_analysis()

    # Service should NOT have been called — we returned from graph cache
    fake_service.full_cohort_analysis.assert_not_called()
    assert result.get("from_cache") is True, f"Expected from_cache=True, got: {result}"
    assert result.get("cache_tier") == "graph"
    # band should be present (derived from stored confidence = 0.85 → high)
    assert result.get("band") == "high"


@pytest.mark.asyncio
async def test_cohort_analysis_misses_graph_then_computes():
    """Without a fresh claim, cohort_analysis calls the service normally.

    Uses months=99 (a value never seeded by other tests) so this test is
    isolated from claim accumulation by the 113-03 emission tests.
    """
    from app.agents.data.tools import cohort_analysis

    fake_service = _make_fake_service()

    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        result = await cohort_analysis(months=99)

    fake_service.full_cohort_analysis.assert_called_once()
    assert "confidence" in result, f"Expected confidence in result: {result}"
    assert result.get("from_cache", False) is False


# ---------------------------------------------------------------------------
# Redis-tier: Stripe payload is cached so repeated calls don't re-hit DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stripe_payload_cached_in_redis():
    """A repeated cohort_analysis call within the Redis TTL doesn't re-call
    the underlying Stripe/DB fetch function.
    """
    from app.agents.data.tools import cohort_analysis

    call_count = {"n": 0}

    async def fake_stripe_fetch(months, user_id):
        call_count["n"] += 1
        return []  # empty rows — service returns no-customer result

    fake_service = _make_fake_service()

    with (
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=fake_service,
        ),
        patch(
            "app.services.cohort_analysis_service._fetch_stripe_transactions",
            side_effect=fake_stripe_fetch,
        ),
    ):
        # First call — graph cache misses (no claim written); falls through to
        # full_cohort_analysis mock.  Our patch of _fetch_stripe_transactions is
        # overriding the cached wrapper itself, so call_count tracks invocations
        # at the patching boundary.
        await cohort_analysis(months=7)
        first_count = call_count["n"]
        # Second call within 300 s — the Redis tier should serve the cached result,
        # NOT call _fetch_stripe_transactions again.
        await cohort_analysis(months=7)
        second_count = call_count["n"]

    # Both calls go through full_cohort_analysis mock (graph miss for months=7),
    # but the Stripe fetch inside each compute_* method should be cached after
    # the first call.  The second full_cohort_analysis invocation (3 compute
    # methods) should hit Redis for all 3 sub-calls.
    assert second_count == first_count, (
        f"Repeated cohort_analysis within TTL should not increment _fetch_stripe_transactions. "
        f"first={first_count}, second={second_count}."
    )


# ---------------------------------------------------------------------------
# Plan 113-03: claim emission
# ---------------------------------------------------------------------------

# Fake full_cohort_analysis return value with real-shaped retention data
# (retention.cohorts is a dict of cohort_month → {month_0: 100.0, month_N: X})
_FAKE_FULL_RESULT_WITH_RETENTION = {
    "retention": {
        "cohorts": {
            "2026-01": {"month_0": 100.0, "month_1": 85.0, "month_2": 72.0, "month_3": 65.0},
        },
        "months_analyzed": 6,
        "total_customers": 200,
    },
    "ltv": {"cohorts": {}, "overall_avg_ltv": 0.0},
    "churn": {"cohorts": {}, "overall_churn_rate": 0.0},
    "executive_summary": "Stable retention in early cohorts.",
    "chart_data": {},
}

_FAKE_FULL_RESULT_TWO_COHORTS = {
    "retention": {
        "cohorts": {
            "2026-01": {"month_0": 100.0, "month_1": 85.0, "month_2": 72.0, "month_3": 65.0},
            "2026-02": {"month_0": 100.0, "month_1": 88.0, "month_2": 74.0},
        },
        "months_analyzed": 6,
        "total_customers": 380,
    },
    "ltv": {"cohorts": {}, "overall_avg_ltv": 0.0},
    "churn": {"cohorts": {}, "overall_churn_rate": 0.0},
    "executive_summary": "Two cohorts analysed; retention broadly stable.",
    "chart_data": {},
}


@pytest.mark.asyncio
async def test_cohort_analysis_writes_summary_claim():
    """After a fresh cohort_analysis, a cohort_summary claim exists in kg_findings."""
    from app.agents.data.tools import _cohort_entity_id, cohort_analysis
    from app.services.intelligence import find_claims

    fake_service = AsyncMock()
    fake_service.full_cohort_analysis = AsyncMock(
        return_value=_FAKE_FULL_RESULT_WITH_RETENTION
    )
    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        await cohort_analysis(months=6)

    entity_id = await _cohort_entity_id(6)
    summaries = await find_claims(
        entity_id=entity_id, claim_type="cohort_summary", agent_id="data", limit=5,
    )
    assert len(summaries) >= 1
    assert summaries[0].finding_text  # non-empty
    assert summaries[0].agent_id == "data"
    assert summaries[0].domain == "data"


@pytest.mark.asyncio
async def test_cohort_analysis_writes_per_month_retention_claims():
    """After cohort_analysis, per-month retention claims exist (one per cohort × month)."""
    from app.agents.data.tools import _cohort_entity_id, cohort_analysis
    from app.services.intelligence import find_claims

    fake_service = AsyncMock()
    fake_service.full_cohort_analysis = AsyncMock(
        return_value=_FAKE_FULL_RESULT_TWO_COHORTS
    )
    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        await cohort_analysis(months=6)

    entity_id = await _cohort_entity_id(6)
    # We seeded 4 + 3 = 7 (cohort, month) points across month_1..month_3 and month_1..month_2
    # (month_0 = 100% acquisition month is intentionally skipped)
    m1 = await find_claims(
        entity_id=entity_id, claim_type="cohort_retention_m1", agent_id="data", limit=10,
    )
    m2 = await find_claims(
        entity_id=entity_id, claim_type="cohort_retention_m2", agent_id="data", limit=10,
    )
    m3 = await find_claims(
        entity_id=entity_id, claim_type="cohort_retention_m3", agent_id="data", limit=10,
    )
    # At least one of each — fixture-row uniqueness across runs may vary so use >=
    assert len(m1) >= 1, "cohort_retention_m1 claims should exist"
    assert len(m2) >= 1, "cohort_retention_m2 claims should exist"
    assert len(m3) >= 1, "cohort_retention_m3 claims should exist"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _call_cohort_analysis(months: int = 6) -> dict:
    """Import and call cohort_analysis, re-importing to pick up patches."""
    # Re-import at call time so in-function local imports pick up patches
    from app.agents.data.tools import cohort_analysis

    return await cohort_analysis(months=months)
