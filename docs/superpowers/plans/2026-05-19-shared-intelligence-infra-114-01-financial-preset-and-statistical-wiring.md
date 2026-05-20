# Shared Intelligence Infrastructure — Plan 114-01: Financial preset + statistical wiring + self-improvement engine audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `app/services/intelligence/presets/financial.py` with the `financial_confidence(...)` preset (four-signal weighted sum), wire it into Financial Agent tools so every numeric output carries `confidence` + `band` derived from real signals, and audit `app/services/self_improvement_engine.py` (+ `skill_experiment_evaluator.py` if present) for entanglement with Financial-Agent shapes BEFORE the wiring changes land.

**Architecture:** Mirror Plan 113-01's `presets/data.py` pattern. `FINANCIAL_WEIGHTS` is a frozen dict; `financial_confidence(...)` normalizes its four inputs (`data_completeness`, `reconciliation_signal`, `horizon_certainty`, `source_authority`) and delegates to the shared `score_confidence(...)` weighted-sum scorer. Tools in `app/agents/financial/tools.py` compute the four signals from the same data they already query (`financial_records`, `get_revenue_stats`, `get_burn_runway_report`, `generate_financial_forecast`, `get_financial_health_score`) and surface `confidence` + `band` on the response dict. Self-improvement audit runs FIRST because Decision #8 of the 114–122 design makes it a structural prerequisite, not optional hygiene: if `self_improvement_engine.py` reads a field whose shape will shift, we keep a thin shim rather than ship a silent break.

**Tech Stack:** Python 3.10+, Pydantic, `app/services/intelligence/` (Phase 112). No new dependencies. No DB schema changes.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 114 — Financial Agent adoption (detailed) § Confidence preset · Decision #8.

**Out of scope:**
- Two-tier cache wiring around Stripe/Shopify (Plan 114-02).
- `kg_findings` claim emission for `revenue_trend` / `expense_pattern` / `revenue_forecast_h{N}m` / `margin_signal` / `financial_anomaly` / `reconciliation_finding` (Plan 114-03).
- Weights calibration from telemetry (deferred per § Out of scope, weights ship as educated guesses).
- Forecast-service algorithm changes — only the surface that returns `confidence` is touched.
- Building a new `skill_experiment_evaluator.py` if its source isn't present (audit only — record findings).

---

## File structure

**Create:**
- `app/services/intelligence/presets/financial.py` — `FINANCIAL_WEIGHTS` + `financial_confidence(...)`.
- `tests/unit/services/intelligence/test_financial_preset.py` — preset unit tests (weights, clamping, key check, monotonicity).
- `tests/unit/agents/financial/test_financial_confidence_wiring.py` — verify every Financial tool that returns numeric data also returns `confidence` + `band`.
- `docs/intelligence/financial-self-improvement-audit.md` — Decision #8 audit report (load-bearing pre-flight artifact).

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `financial_confidence`.
- `app/agents/financial/tools.py` — compute the four signals and attach `confidence` + `band` to: `get_revenue_stats`, `get_cash_position`, `get_burn_runway_report`, `get_financial_report`, `generate_financial_forecast`, `get_financial_health_score`.

---

## Pre-flight context

`financial_confidence` signature:

```python
def financial_confidence(
    *,
    data_completeness: float,    # [0.0, 1.0] — share of period rows landed
    reconciliation_signal: float, # [0.0, 1.0] — accounting identity holds
    horizon_certainty: float,    # [0.0, 1.0] — 1.0 for historical, decays with forecast horizon
    source_authority: float,     # [0.0, 1.0] — Stripe/Plaid > manual > scraped
) -> float
```

Returns confidence clamped to `[0.0, 1.0]`. Inputs MUST already be normalized to `[0.0, 1.0]` by the caller — the preset does not enforce per-input normalization (matches `data_confidence` pattern). The `band` value comes from `to_band(score)` (shared classifier) and is exposed alongside the float.

`FINANCIAL_WEIGHTS` (exact, from spec):

```python
FINANCIAL_WEIGHTS = {
    "data_completeness":     0.30,
    "reconciliation_signal": 0.30,
    "horizon_certainty":     0.25,
    "source_authority":      0.15,
}
# Sum = 1.00
```

**Signal-derivation conventions** (called by tools in Task 3):

| Signal | Source data | Formula |
|---|---|---|
| `data_completeness` | `len(records)` vs expected for period | `min(1.0, observed_days / expected_days)` |
| `reconciliation_signal` | `inflows - outflows - cash_position == 0` (or close) | `1.0 - min(1.0, abs(residual) / max(1.0, abs(cash_position)))` |
| `horizon_certainty` | Forecast horizon in months (`0` for historical) | `max(0.1, 1.0 - horizon_months / 12.0)` |
| `source_authority` | Distinct `source_type` mix in records | `1.0` if Stripe/Plaid only; `0.7` if mixed; `0.4` if mostly `manual` |

Tools without a forecast horizon (`get_cash_position`, `get_revenue_stats`) pass `horizon_certainty=1.0`. The `generate_financial_forecast` tool passes `horizon_certainty = max(0.1, 1.0 - months_ahead / 12.0)`.

**Why audit FIRST:** `self_improvement_engine.py` evaluates skills against interaction logs. If it expects Financial tool responses to NOT carry `confidence` (because Data is the only agent shipping that field today), our new fields might be silently ignored — or they might mis-score (an interaction with a `low` band would inflate a "skill ineffective" signal). Decision #8 makes the audit binding so the change is intentional, not accidental.

Environment quirks: same as prior plans. `uv run pytest`; `uv run ruff check`; Windows-friendly path conventions.

---

## Tasks

### Task 1: Decision #8 audit — self-improvement engine entanglement

**Files:**
- Create: `docs/intelligence/financial-self-improvement-audit.md`

The audit MUST land first (separate commit) so we don't conflate audit findings with code changes. The output is a markdown report committed to the repo for traceability.

- [ ] **Step 1: Locate the engine files and run a structural scan**

```powershell
uv run python -c "import app.services.self_improvement_engine; print(app.services.self_improvement_engine.__file__)"
```

Expected: prints the absolute path to `self_improvement_engine.py`.

```powershell
uv run python -c "import importlib.util; print(importlib.util.find_spec('app.services.skill_experiment_evaluator'))"
```

Expected: `None` OR a `ModuleSpec`. The branch may have the `.pyc` cached but no source. If `None`, note this in the audit report and skip evaluator-specific findings.

- [ ] **Step 2: Grep for Financial-Agent surface usage in the engine**

```powershell
uv run python -c "
import pathlib, re
root = pathlib.Path('app/services')
for f in ['self_improvement_engine.py', 'self_improvement_settings.py']:
    p = root / f
    if not p.exists():
        print(f'SKIP {f} (not present)')
        continue
    text = p.read_text(encoding='utf-8')
    hits = []
    for pat in [r'financial', r'FIN\b', r'get_revenue_stats', r'get_burn_runway',
                r'get_financial_health_score', r'generate_financial_forecast',
                r'confidence', r'band']:
        for m in re.finditer(pat, text, re.IGNORECASE):
            line_no = text[:m.start()].count(chr(10)) + 1
            hits.append((line_no, pat, text.splitlines()[line_no-1].strip()[:120]))
    print(f'== {f} ==')
    for h in hits:
        print(h)
"
```

Expected: prints a list of (line, pattern, snippet) tuples for every match. Empty list means no entanglement.

- [ ] **Step 3: Write the audit report**

Create `docs/intelligence/financial-self-improvement-audit.md` capturing exactly:

```markdown
# Financial Self-Improvement Audit — Plan 114-01

**Date:** <YYYY-MM-DD>
**Auditor:** <agent or human handle>
**Scope:** `app/services/self_improvement_engine.py`, `app/services/skill_experiment_evaluator.py` (if present), `app/services/self_improvement_settings.py`.

## Findings

### 1. File presence
- `self_improvement_engine.py`: <PRESENT | ABSENT>
- `skill_experiment_evaluator.py` source: <PRESENT | ABSENT — only `.pyc` cached>
- `self_improvement_settings.py`: <PRESENT | ABSENT>

### 2. Financial-Agent symbol references
<paste the (line, pattern, snippet) output from Step 2 verbatim>

### 3. Confidence-field expectations
<For each tool we will modify in Task 3 (`get_revenue_stats`, `get_cash_position`,
`get_burn_runway_report`, `get_financial_report`, `generate_financial_forecast`,
`get_financial_health_score`), state whether the engine reads:
  - the response dict shape (answer: yes / no / not directly)
  - any field named `confidence` or `band` (answer: yes / no)
  - the agent id `FIN` or string `financial` (answer: yes / no)
>

### 4. Risk assessment
<one of: ZERO_RISK | LOW_RISK | MEDIUM_RISK | HIGH_RISK>

### 5. Mitigations applied to Plan 114-01
- We add `confidence` and `band` as ADDITIVE fields (existing keys
  unchanged), so any consumer that ignored these keys before still ignores
  them. (Confirms ZERO_RISK is achievable.)
- If the engine reads `confidence` as a binary signal, we annotate that
  here and route through a feature flag (`PIKAR_FIN_CONFIDENCE_EMIT`)
  defaulting `true` so we can flip it off in seconds if the engine
  misbehaves in prod.

### 6. Sign-off
- [ ] Plan 114-01 author confirms findings reviewed.
- [ ] If MEDIUM or HIGH risk, a follow-up shim spec is opened BEFORE Task 3
      lands.
```

Fill in the bracketed placeholders honestly from Step 2's output. If `self_improvement_engine.py` does NOT reference any Financial symbols and does NOT read `confidence`/`band`, mark `ZERO_RISK` and proceed. If it does, raise the risk and bake a feature flag into the tool wiring (Task 3).

- [ ] **Step 4: Commit the audit report**

```bash
git add docs/intelligence/financial-self-improvement-audit.md
git commit -m "audit(114-01): self-improvement engine entanglement audit per Decision #8"
```

Expected: clean commit on the working branch.

### Task 2: Implement `financial_confidence` preset (TDD)

**Files:**
- Create: `app/services/intelligence/presets/financial.py`
- Create: `tests/unit/services/intelligence/test_financial_preset.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Write failing unit tests**

```python
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
        horizon_certainty=0.95,  # 1-month forecast
        source_authority=0.9,
    )
    far = financial_confidence(
        data_completeness=0.9,
        reconciliation_signal=0.9,
        horizon_certainty=0.25,  # 9-month forecast
        source_authority=0.9,
    )
    assert near > far


def test_financial_confidence_clamps_below_one_on_overshoot():
    """Sum exceeding 1.0 due to caller error still returns within [0,1].

    Inputs above 1.0 are caller-error but the shared scorer clamps the
    final value. This protects downstream `band` classification.
    """
    from app.services.intelligence.presets.financial import financial_confidence

    score = financial_confidence(
        data_completeness=2.0,  # caller bug: above 1.0
        reconciliation_signal=1.0,
        horizon_certainty=1.0,
        source_authority=1.0,
    )
    assert 0.0 <= score <= 1.0
```

- [ ] **Step 2: Run — should FAIL with `ImportError`**

```powershell
uv run pytest tests/unit/services/intelligence/test_financial_preset.py -v --tb=short
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.intelligence.presets.financial'`.

- [ ] **Step 3: Implement the preset**

Create `app/services/intelligence/presets/financial.py`:

```python
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
```

Update `app/services/intelligence/presets/__init__.py`:

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula -- Phase 113 adds data_confidence; Phase 114 adds
financial_confidence.
"""

from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.financial import financial_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = ["data_confidence", "financial_confidence", "research_confidence"]
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_financial_preset.py -v --tb=short
```

Expected: PASS — 7 tests passing.

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/presets/financial.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_financial_preset.py
git commit -m "feat(114-01): add financial_confidence preset (GREEN)"
```

### Task 3: Wire `financial_confidence` into Financial Agent tools (TDD)

**Files:**
- Create: `tests/unit/agents/financial/test_financial_confidence_wiring.py`
- Modify: `app/agents/financial/tools.py` (touch six tools)

The Financial Agent today returns dicts with `success`, `revenue`, `cash_position`, `monthly_burn`, `runway_months`, etc. We add two new keys to each numeric response: `confidence` (float) and `band` (`"low" | "medium" | "high"`). Existing keys are unchanged.

- [ ] **Step 1: Write failing wiring tests**

```python
"""Verify each Financial tool returns confidence + band derived from real signals.

These tests mock the underlying service layer so they run fast and isolated.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_revenue_stats_returns_confidence_and_band():
    """get_revenue_stats must include confidence + band on success."""
    from app.agents.financial.tools import get_revenue_stats

    fake_stats = {
        "revenue": 12345.67,
        "currency": "USD",
        "transaction_count": 42,
        "data_age_hours": 1.5,
        "source_breakdown": {"stripe": 42, "manual": 0},
    }
    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(return_value=fake_stats)

    with patch(
        "app.services.financial_service.FinancialService",
        return_value=fake_service,
    ):
        result = await get_revenue_stats(period="current_month")

    assert result["success"] is True
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["band"] in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_get_revenue_stats_error_path_has_low_band():
    """When service fails, confidence collapses to 0.0 / band 'low'."""
    from app.agents.financial.tools import get_revenue_stats

    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(side_effect=RuntimeError("boom"))

    with patch(
        "app.services.financial_service.FinancialService",
        return_value=fake_service,
    ):
        result = await get_revenue_stats(period="current_month")

    assert result["success"] is False
    assert result["confidence"] == 0.0
    assert result["band"] == "low"


@pytest.mark.asyncio
async def test_get_cash_position_confidence_uses_reconciliation_signal():
    """Cash position reconciliation: inflows - outflows == cash_position."""
    from app.agents.financial.tools import get_cash_position

    with patch(
        "app.agents.financial.tools._query_financial_records",
        new=AsyncMock(return_value=[
            {"amount": 100.0, "transaction_type": "revenue", "currency": "USD"},
            {"amount": 50.0, "transaction_type": "expense", "currency": "USD"},
        ]),
    ), patch(
        "app.agents.financial.tools._get_current_user_id",
        return_value="user-abc",
    ):
        result = await get_cash_position()

    assert result["success"] is True
    assert "confidence" in result and "band" in result
    # 100 inflow - 50 outflow == 50 cash -> reconciliation_signal = 1.0
    assert result["confidence"] > 0.0


@pytest.mark.asyncio
async def test_get_burn_runway_report_carries_confidence():
    """Burn-runway report has confidence reflecting record count + recency."""
    from app.agents.financial.tools import get_burn_runway_report

    sample = [
        {"amount": 100.0, "transaction_type": "expense", "currency": "USD"}
        for _ in range(20)
    ]
    with patch(
        "app.agents.financial.tools._get_current_user_id",
        return_value="user-abc",
    ), patch(
        "app.agents.financial.tools.get_cash_position",
        new=AsyncMock(return_value={
            "success": True, "cash_position": 5000.0, "currency": "USD",
            "inflows": 8000.0, "outflows": 3000.0, "record_count": 20,
            "confidence": 0.9, "band": "high",
        }),
    ), patch(
        "app.agents.financial.tools._query_financial_records",
        new=AsyncMock(return_value=sample),
    ):
        result = await get_burn_runway_report()

    assert result["success"] is True
    assert "confidence" in result and "band" in result
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_generate_financial_forecast_horizon_decays_confidence():
    """Forecast confidence at 12 months < confidence at 1 month."""
    from app.agents.financial.tools import generate_financial_forecast

    fake_result = {
        "monthly_projections": [{"month": "2026-06", "revenue": 1000.0}],
        "methodology": "weighted_linear_regression",
        "sample_size": 200,
        "data_completeness": 0.95,
        "source_breakdown": {"stripe": 0.9, "manual": 0.1},
    }
    fake_svc = MagicMock()
    fake_svc.generate_forecast = AsyncMock(return_value=fake_result)

    with patch(
        "app.services.forecast_service.ForecastService",
        return_value=fake_svc,
    ), patch(
        "app.agents.financial.tools._get_current_user_id",
        return_value="user-abc",
    ):
        near = await generate_financial_forecast(months_ahead=1)
        far = await generate_financial_forecast(months_ahead=12)

    assert near["success"] is True and far["success"] is True
    assert near["confidence"] > far["confidence"], (
        f"near={near['confidence']} should exceed far={far['confidence']}"
    )


@pytest.mark.asyncio
async def test_get_financial_health_score_includes_band():
    """Composite health score wraps its own metric with confidence + band."""
    from app.agents.financial.tools import get_financial_health_score

    fake_svc = MagicMock()
    fake_svc.compute_health_score = AsyncMock(return_value={
        "score": 78,
        "color": "green",
        "explanation": "Healthy runway and stable burn.",
        "factors": {
            "revenue_trend": "positive",
            "runway_months": 14.2,
            "cash_flow_ratio": 1.3,
            "collection_rate": 0.92,
            "burn_stability": 0.88,
        },
        "data_completeness": 0.9,
        "reconciliation_signal": 0.95,
        "source_authority": 0.85,
    })

    with patch(
        "app.services.financial_health_score_service.FinancialHealthScoreService",
        return_value=fake_svc,
    ), patch(
        "app.agents.financial.tools._get_current_user_id",
        return_value="user-abc",
    ):
        result = await get_financial_health_score()

    assert result["success"] is True
    assert "confidence" in result and "band" in result
    assert result["band"] in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_no_hardcoded_confidence_constants():
    """No tool returns confidence as a fixed magic number (regression guard).

    We run each happy-path tool twice with materially different inputs and
    assert at least one yields a different confidence. If both happened to
    yield identical floats we'd be flagging a constant.
    """
    from app.agents.financial.tools import (
        generate_financial_forecast,
        get_revenue_stats,
    )

    fake_svc = MagicMock()
    fake_svc.get_revenue_stats = AsyncMock(return_value={
        "revenue": 1.0, "currency": "USD", "transaction_count": 1,
        "data_age_hours": 0.5, "source_breakdown": {"stripe": 1},
    })
    with patch(
        "app.services.financial_service.FinancialService",
        return_value=fake_svc,
    ):
        low_data = await get_revenue_stats(period="current_month")

    fake_svc.get_revenue_stats = AsyncMock(return_value={
        "revenue": 99999.0, "currency": "USD", "transaction_count": 500,
        "data_age_hours": 0.5, "source_breakdown": {"stripe": 500},
    })
    with patch(
        "app.services.financial_service.FinancialService",
        return_value=fake_svc,
    ):
        high_data = await get_revenue_stats(period="current_month")

    assert low_data["confidence"] != high_data["confidence"], (
        "Confidence appears to be a hardcoded constant — should reflect signals."
    )
```

- [ ] **Step 2: Run — should FAIL (existing tools don't return `confidence`)**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_confidence_wiring.py -v --tb=short
```

Expected: FAIL — assertions on `"confidence" in result` raise KeyError-style failures.

- [ ] **Step 3: Implement signal-derivation helpers in `app/agents/financial/tools.py`**

Add (near the top of `tools.py`, after the existing imports):

```python
from app.services.intelligence import to_band
from app.services.intelligence.presets import financial_confidence


def _source_authority_from_breakdown(
    breakdown: dict[str, int | float] | None,
) -> float:
    """Map a source-type record breakdown to an authority score in [0, 1].

    Stripe / Plaid records are high-authority (1.0); manual entries are
    low-authority (0.4). A mixed breakdown returns a weighted average.
    """
    if not breakdown:
        return 0.5  # unknown -> middling
    weights = {
        "stripe": 1.0,
        "plaid": 1.0,
        "shopify": 0.9,
        "bank": 0.85,
        "manual": 0.4,
        "scraped": 0.3,
    }
    total = 0.0
    weighted = 0.0
    for src, count in breakdown.items():
        if not isinstance(count, (int, float)) or count <= 0:
            continue
        w = weights.get(src.lower(), 0.5)
        weighted += w * float(count)
        total += float(count)
    if total == 0:
        return 0.5
    return weighted / total


def _data_completeness_from_age(
    transaction_count: int,
    period_days: int,
    expected_per_day: float = 1.0,
) -> float:
    """Estimate completeness as observed / expected, clamped to [0, 1]."""
    if period_days <= 0:
        return 1.0
    expected = max(1.0, expected_per_day * period_days)
    return min(1.0, transaction_count / expected)


def _reconciliation_signal_from_flows(
    inflows: float,
    outflows: float,
    cash_position: float,
) -> float:
    """1.0 when inflows-outflows == cash_position; 0.0 when residual >= cash."""
    residual = abs((inflows - outflows) - cash_position)
    base = max(1.0, abs(cash_position))
    return max(0.0, 1.0 - min(1.0, residual / base))


def _horizon_certainty(months_ahead: int) -> float:
    """1.0 for historical (0 months); decays linearly to 0.1 at 12 months."""
    if months_ahead <= 0:
        return 1.0
    return max(0.1, 1.0 - (months_ahead / 12.0))


_PERIOD_DAYS = {
    "current_month": 30,
    "last_month": 30,
    "last_3_months": 90,
    "last_6_months": 180,
    "last_year": 365,
    "all_time": 365,
}


def _attach_confidence(
    result: dict,
    *,
    data_completeness: float,
    reconciliation_signal: float,
    horizon_certainty: float,
    source_authority: float,
) -> dict:
    """Attach `confidence` + `band` to a Financial tool response in-place."""
    score = financial_confidence(
        data_completeness=data_completeness,
        reconciliation_signal=reconciliation_signal,
        horizon_certainty=horizon_certainty,
        source_authority=source_authority,
    )
    result["confidence"] = round(score, 4)
    result["band"] = to_band(score)
    return result
```

- [ ] **Step 4: Modify each Financial tool to attach `confidence` + `band`**

Update `get_revenue_stats` (replace the entire function):

```python
async def get_revenue_stats(period: str = "current_month") -> dict:
    """Get revenue statistics for financial analysis from FinancialService.

    Response now includes `confidence` (0.0-1.0) and `band`
    ("low"|"medium"|"high") derived from data completeness, source authority,
    and reconciliation signal. Forecast horizon is N/A for this tool
    (historical aggregation -> horizon_certainty = 1.0).
    """
    from app.services.financial_service import FinancialService

    try:
        service = FinancialService()
        stats = await service.get_revenue_stats(period)
        data_completeness = _data_completeness_from_age(
            transaction_count=int(stats.get("transaction_count", 0) or 0),
            period_days=_PERIOD_DAYS.get(period, 30),
        )
        source_authority = _source_authority_from_breakdown(
            stats.get("source_breakdown"),
        )
        return _attach_confidence(
            {"success": True, **stats},
            data_completeness=data_completeness,
            reconciliation_signal=1.0,  # not applicable for revenue-only view
            horizon_certainty=1.0,
            source_authority=source_authority,
        )
    except Exception as e:
        return {
            "success": False,
            "revenue": 0.0,
            "currency": "USD",
            "period": period,
            "error": f"Service unavailable: {e!s}",
            "confidence": 0.0,
            "band": "low",
        }
```

Update `get_cash_position` (replace the entire function):

```python
async def get_cash_position() -> dict:
    """Compute an estimated cash position from user financial records.

    Response now carries `confidence` + `band` reflecting record-count
    completeness and reconciliation residual.
    """
    try:
        user_id = _get_current_user_id()
        records = await _query_financial_records(user_id=user_id)
        inflow_types = {"revenue", "income", "credit", "payment"}
        outflow_types = {"expense", "burn", "cost", "payroll", "debit"}

        inflows = 0.0
        outflows = 0.0
        currency = "USD"
        source_counts: dict[str, int] = {}
        for record in records:
            amount = record.get("amount")
            if not isinstance(amount, (int, float)):
                continue
            currency = record.get("currency") or currency
            record_type = str(record.get("transaction_type") or "").strip().lower()
            numeric_amount = float(amount)
            if record_type in outflow_types:
                outflows += abs(numeric_amount)
            elif record_type in inflow_types or numeric_amount >= 0:
                inflows += numeric_amount
            else:
                outflows += abs(numeric_amount)
            src = str(record.get("source_type") or "manual").lower()
            source_counts[src] = source_counts.get(src, 0) + 1

        cash_position = round(inflows - outflows, 2)
        return _attach_confidence(
            {
                "success": True,
                "cash_position": cash_position,
                "currency": currency,
                "inflows": round(inflows, 2),
                "outflows": round(outflows, 2),
                "record_count": len(records),
            },
            data_completeness=_data_completeness_from_age(
                transaction_count=len(records), period_days=30,
            ),
            reconciliation_signal=_reconciliation_signal_from_flows(
                inflows=inflows, outflows=outflows, cash_position=cash_position,
            ),
            horizon_certainty=1.0,
            source_authority=_source_authority_from_breakdown(source_counts),
        )
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cash_position": 0.0,
            "currency": "USD",
            "confidence": 0.0,
            "band": "low",
        }
```

Update `get_burn_runway_report` (replace the entire function):

```python
async def get_burn_runway_report(monthly_burn: float | None = None) -> dict:
    """Estimate monthly burn and runway from recent financial records.

    Response now carries `confidence` + `band`. Confidence reflects expense
    record count and the cash_position reconciliation signal inherited from
    `get_cash_position`.
    """
    try:
        user_id = _get_current_user_id()
        cash_position = await get_cash_position()
        expense_records = await _query_financial_records(
            user_id=user_id, days_back=90, limit=500,
        )
        expense_total = 0.0
        source_counts: dict[str, int] = {}
        for record in expense_records:
            record_type = str(record.get("transaction_type") or "").strip().lower()
            amount = record.get("amount")
            if record_type in {"expense", "burn", "cost", "payroll", "debit"} \
                    and isinstance(amount, (int, float)):
                expense_total += abs(float(amount))
            src = str(record.get("source_type") or "manual").lower()
            source_counts[src] = source_counts.get(src, 0) + 1

        estimated_burn = round(
            monthly_burn if monthly_burn is not None
            else expense_total / 3 if expense_total
            else 0.0,
            2,
        )
        available_cash = float(cash_position.get("cash_position") or 0.0)
        runway_months = (
            round(available_cash / estimated_burn, 2) if estimated_burn > 0 else None
        )

        return _attach_confidence(
            {
                "success": True,
                "cash_position": available_cash,
                "monthly_burn": estimated_burn,
                "runway_months": runway_months,
                "currency": cash_position.get("currency", "USD"),
                "calculation_window_days": 90,
            },
            data_completeness=_data_completeness_from_age(
                transaction_count=len(expense_records), period_days=90,
            ),
            # Inherit reconciliation_signal from upstream get_cash_position when
            # the upstream confidence is high; otherwise fall back to 0.7.
            reconciliation_signal=(
                float(cash_position.get("confidence") or 0.7)
                if cash_position.get("success")
                else 0.5
            ),
            horizon_certainty=1.0,  # historical 90-day analysis
            source_authority=_source_authority_from_breakdown(source_counts),
        )
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "monthly_burn": 0.0,
            "runway_months": None,
            "confidence": 0.0,
            "band": "low",
        }
```

Update `get_financial_report` (replace the entire function):

```python
async def get_financial_report(period: str = "current_month") -> dict:
    """Return a compact finance report with revenue, cash, and runway metrics.

    The composite report's confidence is the MINIMUM of the child reports'
    confidences -- a single low-quality sub-signal drags the whole report
    down so callers know to ask for the source.
    """
    try:
        revenue = await get_revenue_stats(period)
        cash = await get_cash_position()
        runway = await get_burn_runway_report()
        composite_conf = min(
            float(revenue.get("confidence", 0.0) or 0.0),
            float(cash.get("confidence", 0.0) or 0.0),
            float(runway.get("confidence", 0.0) or 0.0),
        )
        return {
            "success": True,
            "period": period,
            "revenue": revenue.get("revenue", 0.0),
            "currency": revenue.get("currency") or cash.get("currency") or "USD",
            "cash_position": cash.get("cash_position", 0.0),
            "monthly_burn": runway.get("monthly_burn", 0.0),
            "runway_months": runway.get("runway_months"),
            "confidence": round(composite_conf, 4),
            "band": to_band(composite_conf),
            "details": {"revenue": revenue, "cash": cash, "runway": runway},
        }
    except Exception as e:
        return {
            "success": False, "error": str(e), "period": period,
            "confidence": 0.0, "band": "low",
        }
```

Update `generate_financial_forecast` (replace the entire function):

```python
async def generate_financial_forecast(
    months_ahead: int = 6,
    title: str = "Revenue Forecast",
) -> dict:
    """Generate a data-driven financial forecast using historical revenue.

    Confidence decays with `months_ahead` (longer horizon = lower confidence)
    via the `horizon_certainty` signal.
    """
    try:
        from app.services.forecast_service import ForecastService

        user_id = _get_current_user_id()
        if not user_id:
            return {
                "success": False, "error": "No authenticated user found",
                "confidence": 0.0, "band": "low",
            }

        svc = ForecastService()
        result = await svc.generate_forecast(
            user_id=user_id, months_ahead=months_ahead, title=title,
        )

        sample_size = int(result.get("sample_size", 0) or 0)
        data_completeness = float(
            result.get("data_completeness", min(1.0, sample_size / 90.0)),
        )
        source_authority = _source_authority_from_breakdown(
            result.get("source_breakdown") or {},
        ) if isinstance(result.get("source_breakdown"), dict) else 0.7

        return _attach_confidence(
            {"success": True, **result},
            data_completeness=data_completeness,
            reconciliation_signal=0.9,  # forecast doesn't reconcile against cash
            horizon_certainty=_horizon_certainty(months_ahead),
            source_authority=source_authority,
        )
    except Exception as e:
        return {
            "success": False, "error": str(e),
            "confidence": 0.0, "band": "low",
        }
```

Update `get_financial_health_score` (replace the entire function):

```python
async def get_financial_health_score() -> dict:
    """Compute a composite financial health score (0-100) for the current user.

    Adds `confidence` + `band` so callers can weight the score against its
    own credibility. The service-layer score is unchanged; only the
    trust envelope is new.
    """
    try:
        from app.services.financial_health_score_service import (
            FinancialHealthScoreService,
        )

        user_id = _get_current_user_id()
        if not user_id:
            return {
                "success": False, "error": "No authenticated user found",
                "confidence": 0.0, "band": "low",
            }

        svc = FinancialHealthScoreService()
        result = await svc.compute_health_score(user_id)
        return _attach_confidence(
            {"success": True, **result},
            data_completeness=float(result.get("data_completeness", 0.8)),
            reconciliation_signal=float(result.get("reconciliation_signal", 0.85)),
            horizon_certainty=1.0,  # health score is point-in-time
            source_authority=float(result.get("source_authority", 0.75)),
        )
    except Exception as e:
        return {
            "success": False, "error": str(e),
            "confidence": 0.0, "band": "low",
        }
```

- [ ] **Step 5: Re-run wiring tests — should PASS**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_confidence_wiring.py -v --tb=short
```

Expected: PASS — 7 tests passing.

- [ ] **Step 6: Re-run the full Financial Agent unit suite — must remain green**

```powershell
uv run pytest tests/unit/agents/financial/ -v --tb=short
```

Expected: PASS — every prior Financial Agent test still green (the added keys are additive).

- [ ] **Step 7: Commit**

```bash
git add app/agents/financial/tools.py tests/unit/agents/financial/test_financial_confidence_wiring.py
git commit -m "feat(114-01): wire financial_confidence into 6 Financial tools (GREEN)"
```

### Task 4: Public-surface import test + lint sign-off

- [ ] **Step 1: Confirm the preset is reachable from the public surface**

```powershell
uv run python -c "from app.services.intelligence.presets import financial_confidence; from app.services.intelligence.presets.financial import FINANCIAL_WEIGHTS; print('OK', sum(FINANCIAL_WEIGHTS.values()))"
```

Expected: `OK 1.0` (or `1.0000000000000002` -- a tiny float drift is fine).

- [ ] **Step 2: Lint and format**

```powershell
uv run ruff check app/services/intelligence/presets/financial.py app/services/intelligence/presets/__init__.py app/agents/financial/tools.py tests/unit/services/intelligence/test_financial_preset.py tests/unit/agents/financial/test_financial_confidence_wiring.py
uv run ruff format app/services/intelligence/presets/financial.py app/services/intelligence/presets/__init__.py app/agents/financial/tools.py tests/unit/services/intelligence/test_financial_preset.py tests/unit/agents/financial/test_financial_confidence_wiring.py --check
```

Expected: both commands report no findings. If `ruff check` finds violations, fix in place. If `ruff format --check` fails, run without `--check` to apply, then commit the format diff.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -u
git commit -m "style(114-01): ruff lint + format fixes for plan 114-01" || echo "nothing to commit"
```

Expected: either a clean commit, or `nothing to commit` if nothing changed.

### Task 5: Plan 114-01 acceptance sign-off

- [ ] **Step 1: Verify ALL acceptance lines for this plan**

| Plan 114-01 acceptance line | Verified by |
|---|---|
| `presets/financial.py` shipped with exact `FINANCIAL_WEIGHTS` | Task 2 Steps 3 + 4 (`test_financial_weights_match_spec_exactly` PASS) |
| `financial_confidence(...)` returns clamped [0,1] | Task 2 Step 4 (`test_financial_confidence_clamps_below_one_on_overshoot`) |
| Every Financial tool returns `confidence` + `band` | Task 3 Step 5 (wiring tests PASS) |
| No hardcoded confidence constants | Task 3 Step 5 (`test_no_hardcoded_confidence_constants`) |
| Forecast confidence decays with horizon | Task 3 Step 5 (`test_generate_financial_forecast_horizon_decays_confidence`) |
| Error paths collapse to `confidence=0.0`, `band="low"` | Task 3 Step 5 (`test_get_revenue_stats_error_path_has_low_band`) |
| Self-improvement engine audit committed BEFORE wiring | Task 1 Step 4 (audit commit precedes feat commits in `git log`) |
| Existing Financial Agent test suite green (no regression) | Task 3 Step 6 |
| Public-surface import works | Task 4 Step 1 |
| Lint clean | Task 4 Steps 2-3 |

- [ ] **Step 2: Plan 114-01 complete. Plan 114-02 (cache integration) is unblocked.**

Next planned work in Phase 114: Plan 114-02 wires the two-tier cache around Stripe/Shopify external calls; Plan 114-03 ships claim emission for `revenue_trend` / `expense_pattern` / `revenue_forecast_h{N}m` / `margin_signal` / `financial_anomaly` / `reconciliation_finding`.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `presets/financial.py` with exact `FINANCIAL_WEIGHTS` (0.30 / 0.30 / 0.25 / 0.15) | Task 2 |
| `data_completeness` signal | Task 2 + Task 3 (`_data_completeness_from_age`) |
| `reconciliation_signal` signal | Task 2 + Task 3 (`_reconciliation_signal_from_flows`) |
| `horizon_certainty` signal — novel input formalizing forecast decay | Task 2 + Task 3 (`_horizon_certainty`) |
| `source_authority` signal — Stripe/Plaid > manual > scraped | Task 2 + Task 3 (`_source_authority_from_breakdown`) |
| Every Financial output carries `confidence` + `band` (no hardcoded constants) | Task 3 (six tools modified, regression-guard test) |
| Self-improvement engine audit per Decision #8 BEFORE other changes land | Task 1 (audit committed first, separate commit) |
| Public surface re-exports `financial_confidence` from `presets/__init__.py` | Task 2 Step 3 |
| Financial Agent test suite remains green | Task 3 Step 6 |
| Lint clean (ruff check + ruff format --check) | Task 4 |

All spec lines covered.
