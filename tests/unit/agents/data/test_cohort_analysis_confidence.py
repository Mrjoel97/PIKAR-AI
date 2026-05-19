"""Unit tests for cohort_analysis tool — confidence / band fields (Phase 113-01).

Verifies that after wiring data_confidence into the cohort_analysis tool
(app/agents/data/tools.py) the returned dict contains:
  - "confidence": a float in [0.0, 1.0]
  - "band": one of "low" | "medium" | "high"

Uses the sys.modules stub pattern from Phase 49-05 to avoid the
slowapi/starlette .env UnicodeDecodeError on Windows before importing.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs to sidestep expensive / env-dependent imports
# ---------------------------------------------------------------------------

_FAKE_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-test-key",
    "SUPABASE_ANON_KEY": "anon-test-key",
    "GOOGLE_API_KEY": "fake-api-key",
}


def _stub_modules() -> None:
    """Inject minimal stubs so tools.py can be imported without side-effects.

    Note: starlette is a real installed package so we must NOT stub it.
    Only stub slowapi (which tries to import starlette internals at import-time
    in some configurations) and google.adk / google.genai (heavyweight SDKs).
    """
    for mod_name in [
        "slowapi",
        "slowapi.util",
        "slowapi.errors",
        "slowapi.middleware",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    # google is a namespace package; only stub the sub-packages if absent
    for mod_name in ["google.adk", "google.genai"]:
        if mod_name not in sys.modules:
            parent, _, child = mod_name.rpartition(".")
            stub = types.ModuleType(mod_name)
            sys.modules[mod_name] = stub
            if parent in sys.modules:
                setattr(sys.modules[parent], child, stub)


# ---------------------------------------------------------------------------
# Fake cohort result returned by CohortAnalysisService.full_cohort_analysis
# ---------------------------------------------------------------------------

_FAKE_COHORT_RESULT = {
    "retention": {
        "cohorts": {"2026-01": {"month_0": 100.0, "month_1": 75.0}},
        "months_analyzed": 6,
        "total_customers": 42,
    },
    "ltv": {
        "cohorts": {
            "2026-01": {"avg_ltv": 150.0, "total_revenue": 6300.0, "customer_count": 42}
        },
        "overall_avg_ltv": 150.0,
    },
    "churn": {
        "cohorts": {"2026-01": {"churn_rate": 0.05, "churned": 2, "total": 42}},
        "overall_churn_rate": 0.05,
    },
    "executive_summary": "42 customers, good retention.",
    "chart_data": {},
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_cohort_service() -> MagicMock:
    """Return a MagicMock CohortAnalysisService with full_cohort_analysis stubbed."""
    svc = MagicMock()
    svc.full_cohort_analysis = AsyncMock(return_value=_FAKE_COHORT_RESULT)
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cohort_analysis_confidence_field_present(
    mock_cohort_service: MagicMock,
) -> None:
    """cohort_analysis result includes a float 'confidence' field."""
    _stub_modules()
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=mock_cohort_service,
        ),
        patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user",
        ),
    ):
        from app.agents.data.tools import cohort_analysis

        result = await cohort_analysis(months=6)

    assert result["success"] is True
    assert "confidence" in result, "expected 'confidence' key in result"
    assert isinstance(result["confidence"], float), "confidence must be a float"
    assert 0.0 <= result["confidence"] <= 1.0, "confidence must be in [0.0, 1.0]"


@pytest.mark.asyncio
async def test_cohort_analysis_band_field_present(
    mock_cohort_service: MagicMock,
) -> None:
    """cohort_analysis result includes a 'band' literal string."""
    _stub_modules()
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=mock_cohort_service,
        ),
        patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user",
        ),
    ):
        from app.agents.data.tools import cohort_analysis

        result = await cohort_analysis(months=6)

    assert "band" in result, "expected 'band' key in result"
    assert result["band"] in {"low", "medium", "high"}, (
        f"band must be low/medium/high, got {result['band']!r}"
    )


@pytest.mark.asyncio
async def test_cohort_analysis_confidence_high_for_good_data(
    mock_cohort_service: MagicMock,
) -> None:
    """42 customers, 0 missing, 0 sigma, 1h age → confidence in 'high' band (>= 0.75)."""
    _stub_modules()
    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=mock_cohort_service,
        ),
        patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user",
        ),
    ):
        from app.agents.data.tools import cohort_analysis

        result = await cohort_analysis(months=6)

    # With defaults: missing=0, sigma=0, age=1h and 42 customers (< 100 threshold)
    # sample_adequacy = 0.42, completeness=1.0, strength=1.0, recency≈0.9986
    # score ≈ 0.42*0.35 + 1.0*0.25 + 1.0*0.25 + 0.9986*0.15 ≈ 0.797 → "high"
    assert result["band"] == "high"


@pytest.mark.asyncio
async def test_cohort_analysis_no_customers_no_confidence_key() -> None:
    """When total_customers == 0 the early-return path omits confidence/band fields."""
    _stub_modules()
    empty_result = {
        "retention": {"cohorts": {}, "months_analyzed": 6, "total_customers": 0},
        "ltv": {},
        "churn": {},
        "executive_summary": "",
        "chart_data": {},
    }
    svc = MagicMock()
    svc.full_cohort_analysis = AsyncMock(return_value=empty_result)

    with (
        patch.dict("os.environ", _FAKE_ENV, clear=False),
        patch(
            "app.services.cohort_analysis_service.CohortAnalysisService",
            return_value=svc,
        ),
        patch(
            "app.services.request_context.get_current_user_id",
            return_value="test-user",
        ),
    ):
        from app.agents.data.tools import cohort_analysis

        result = await cohort_analysis(months=6)

    assert result["success"] is True
    assert "message" in result  # early-return message path
    # confidence/band not present on the empty-data early-exit path
    assert "confidence" not in result
    assert "band" not in result
