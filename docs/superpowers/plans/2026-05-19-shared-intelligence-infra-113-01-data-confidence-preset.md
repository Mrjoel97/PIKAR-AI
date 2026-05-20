# Shared Intelligence Infrastructure — Plan 113-01: Data Confidence Preset + Pilot Wiring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `app/services/intelligence/presets/data.py` with `data_confidence(sample_size, missing_pct, sigma_distance, data_age_hours)` and wire it into Data Agent's `cohort_analysis` as the pilot adoption. Other Data Agent tools (`query_analytics`, `query_usage`, `generate_weekly_report`) adopt in Plans 113-02 / 113-03 alongside the cache and claim-emission work.

**Architecture:** Pure-function preset using the existing generic `score_confidence` from Plan 112-02. The formula codifies Data Agent's statistical rigor (already documented in `app/agents/data/agent.py:166-176` — sample_size ≥ 30 trends, ≥ 100 anomalies, missing >20% flagged, outliers >3σ). The pilot wiring computes the four signals from real cohort data and adds `confidence` + `band` fields to the `cohort_analysis` response payload.

**Tech Stack:** Python 3.10+ (already configured), Pydantic v2 (for `to_band`), the shared `app/services/intelligence/` package.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Module specifications § presets/data.py + § Phase 113

**Out of scope for this plan:** Two-tier cache wiring around Stripe calls (Plan 113-02), claim emission to `kg_findings` from cohort results (Plan 113-03), pgvector-backed semantic search (Plan 113-04), contradiction detection (Plan 113-05), other Data Agent functions beyond `cohort_analysis`.

---

## File structure

**Create:**
- `app/services/intelligence/presets/data.py` — `data_confidence` and `DATA_WEIGHTS`
- `tests/unit/services/intelligence/test_presets_data.py` — preset unit tests

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `data_confidence`
- `app/services/intelligence/__init__.py` — no change needed (presets is already in `__all__`)
- `app/agents/data/tools.py:220-265` — `cohort_analysis` adds confidence + band to response
- Existing cohort-analysis tests if any (find via grep before modifying)

**Reference (read-only):**
- `app/services/intelligence/confidence.py` — `score_confidence` and `to_band`
- `app/services/intelligence/presets/research.py` — pattern to mirror
- `app/services/cohort_analysis_service.py` — `CohortAnalysisService` returns the raw data shape that `cohort_analysis` uses
- `app/agents/data/agent.py:166-176` — statistical rigor expectations baked into agent instructions

---

## Pre-flight context

Existing Data Agent statistical rigor (from `app/agents/data/agent.py:166-176`):
- Minimum sample sizes: **30 for trends, 100 for anomalies**
- Flag missing values **>20%**, don't analyze if **>50% missing**
- Flag outliers **>3 std dev**
- Always report confidence intervals on forecasts
- Distinguish correlation from causation explicitly

`data_confidence` formula (from the spec):
```python
DATA_WEIGHTS = {
    "sample_adequacy": 0.35,
    "completeness": 0.25,
    "statistical_strength": 0.25,
    "recency": 0.15,
}

sample_adequacy      = min(1.0, sample_size / sample_threshold)       # threshold=100 default
completeness         = max(0.0, 1.0 - missing_pct)
statistical_strength = max(0.0, 1.0 - min(1.0, sigma_distance / 3.0)) # inversion: high sigma = anomalous, low confidence in stability
recency              = max(0.0, 1.0 - min(1.0, data_age_hours / recency_horizon_hours))  # horizon=720h=30d default
```

**`statistical_strength` inverts sigma deliberately** — high sigma means *anomalous*, not *certain*. An anomaly detection has high signal but low confidence in trend stability.

`cohort_analysis(months: int = 6)` is at `app/agents/data/tools.py:220`. It delegates to `app/services/cohort_analysis_service.py:CohortAnalysisService`. The pilot needs to:
1. Extract signals from the service's result
2. Compute `data_confidence(...)`
3. Add `confidence` and `band` to the response dict

Environment quirks (carried from Phase 112):
- `uv` only via PowerShell
- Test env vars for tests that hit external services: `SUPABASE_*`, `REDIS_*`
- `pytest-asyncio` is installed and `asyncio_mode = "strict"` is set

---

## Tasks

### Task 1: Pre-flight — confirm Phase 112 is integrated and locate cohort_analysis

**Files:** none modified — verification only.

- [ ] **Step 1: Confirm Phase 112 is integrated**

```bash
ls app/services/intelligence/{__init__,confidence,claims,cache,schemas}.py app/services/intelligence/presets/{__init__,research}.py
grep -E "^def (score_confidence|to_band)" app/services/intelligence/confidence.py
grep -E "^def research_confidence" app/services/intelligence/presets/research.py
```

Expected: all files exist, all three functions present (not stubs). If any missing, Phase 112 isn't integrated locally — `git log --oneline | grep 112` should show ~32 commits.

- [ ] **Step 2: Confirm `cohort_analysis` and `CohortAnalysisService` shapes**

```bash
grep -n "def cohort_analysis\|class CohortAnalysisService\|def analyze" app/agents/data/tools.py app/services/cohort_analysis_service.py | head -10
```

Read the service's `analyze` method (or equivalent) to understand the result dict shape — specifically, what fields are available to compute `sample_size`, `missing_pct`, `sigma_distance`, `data_age_hours`. Most likely:
- `sample_size` = total customers / orders / records in the analysis window
- `missing_pct` = rows with NULL key fields / total rows (often near 0 for Stripe-derived data)
- `sigma_distance` = how far retention is from the historical mean (may need to compute, or default to 0 if no historical baseline)
- `data_age_hours` = time since the latest record in the cohort

Capture the result shape for the implementation in Task 4.

No commit in this task.

### Task 2: Scaffold `presets/data.py` with stub

**Files:**
- Create: `app/services/intelligence/presets/data.py`

- [ ] **Step 1: Create the file with stub**

```python
"""Data-domain confidence preset.

Used by Data Agent tools (cohort_analysis, query_analytics, ...) to
attach a calibrated confidence band to numerical / statistical outputs.

Formula reflects the statistical rigor already documented in
app/agents/data/agent.py:166-176 (sample_size >= 30 trends / >= 100
anomalies, missing >20% flagged, outliers >3 sigma).
"""

from __future__ import annotations


def data_confidence(
    sample_size: int,
    missing_pct: float,
    sigma_distance: float,
    data_age_hours: float,
    *,
    sample_threshold: int = 100,
    recency_horizon_hours: float = 720,  # 30 days
) -> float:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 113-01 Task 4")
```

- [ ] **Step 2: Update `presets/__init__.py` to re-export the stub**

Edit `app/services/intelligence/presets/__init__.py`. Add the import alongside `research_confidence`:

```python
"""Per-agent confidence presets."""

from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = ["data_confidence", "research_confidence"]
```

- [ ] **Step 3: Verify imports**

```powershell
uv run python -c "from app.services.intelligence.presets import data_confidence, research_confidence; print('preset imports OK')"
```

Expected: `preset imports OK`.

- [ ] **Step 4: Commit**

```bash
git add app/services/intelligence/presets/data.py app/services/intelligence/presets/__init__.py
git commit -m "feat(113-01): scaffold data_confidence preset (stub)"
```

### Task 3: Write failing unit tests for `data_confidence`

**Files:**
- Create: `tests/unit/services/intelligence/test_presets_data.py`

- [ ] **Step 1: Create the test file**

```python
"""Unit tests for app.services.intelligence.presets.data."""

from __future__ import annotations

import math

import pytest

from app.services.intelligence.presets.data import data_confidence


# ---------------------------------------------------------------------------
# Boundary cases — sample size dominates at low N
# ---------------------------------------------------------------------------


def test_zero_sample_returns_low_confidence():
    """sample_size=0 nukes sample_adequacy (weight 0.35); result <= 0.65."""
    result = data_confidence(
        sample_size=0, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    # Other inputs perfect: completeness=1.0 (0.25), strength=1.0 (0.25),
    # recency=1.0 (0.15). Sample at 0 contributes 0. Total = 0.65.
    assert math.isclose(result, 0.65, abs_tol=1e-9)


def test_full_sample_high_confidence():
    """sample_size=100, missing=0, sigma=0, age=0 -> 1.0."""
    result = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_oversized_sample_clamped_at_threshold():
    """sample_size > sample_threshold (default 100) doesn't help beyond 1.0."""
    result_100 = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    result_10000 = data_confidence(
        sample_size=10000, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    assert math.isclose(result_100, result_10000, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# missing_pct
# ---------------------------------------------------------------------------


def test_missing_data_reduces_confidence():
    """50% missing data reduces completeness contribution by half."""
    full = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    half_missing = data_confidence(
        sample_size=100, missing_pct=0.5, sigma_distance=0.0, data_age_hours=0.0,
    )
    # completeness contribution drops from 0.25 to 0.125, total drops by 0.125
    assert math.isclose(full - half_missing, 0.125, abs_tol=1e-9)


def test_complete_data_missing():
    """missing_pct=1.0 zeros out the completeness contribution (-0.25)."""
    result = data_confidence(
        sample_size=100, missing_pct=1.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    # sample=1.0*0.35 + completeness=0.0*0.25 + strength=1.0*0.25 + recency=1.0*0.15 = 0.75
    assert math.isclose(result, 0.75, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# sigma_distance — high sigma INVERTS to LOW confidence in stability
# ---------------------------------------------------------------------------


def test_zero_sigma_full_statistical_strength():
    """sigma=0 means data is at the mean — full statistical strength."""
    result = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_three_sigma_zeros_statistical_strength():
    """sigma >= 3.0 saturates the inversion — strength contribution drops to 0."""
    result = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=3.0, data_age_hours=0.0,
    )
    # sample=0.35 + completeness=0.25 + strength=0 + recency=0.15 = 0.75
    assert math.isclose(result, 0.75, abs_tol=1e-9)


def test_high_sigma_floored_at_zero_strength():
    """sigma >> 3.0 doesn't make confidence negative — strength floored at 0."""
    result_3 = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=3.0, data_age_hours=0.0,
    )
    result_10 = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=10.0, data_age_hours=0.0,
    )
    assert math.isclose(result_3, result_10, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# data_age_hours — older data discounts recency
# ---------------------------------------------------------------------------


def test_fresh_data_full_recency():
    """age=0 contributes full recency weight."""
    result = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_30_day_old_data_zeros_recency():
    """age >= default horizon (720h) saturates the decay."""
    result = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=720.0,
    )
    # sample=0.35 + completeness=0.25 + strength=0.25 + recency=0 = 0.85
    assert math.isclose(result, 0.85, abs_tol=1e-9)


def test_ancient_data_floored_at_zero_recency():
    """age >> horizon doesn't make confidence negative."""
    result_720 = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=720.0,
    )
    result_1y = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=8760.0,
    )
    assert math.isclose(result_720, result_1y, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------


def test_custom_sample_threshold():
    """sample_threshold override changes what counts as 'fully sampled'."""
    # With threshold=30 (trends spec), sample=30 hits adequacy=1.0
    result = data_confidence(
        sample_size=30, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
        sample_threshold=30,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_custom_recency_horizon():
    """recency_horizon override changes what counts as 'old'."""
    # With horizon=24h, age=24h saturates the decay
    result = data_confidence(
        sample_size=100, missing_pct=0.0, sigma_distance=0.0, data_age_hours=24.0,
        recency_horizon_hours=24.0,
    )
    assert math.isclose(result, 0.85, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Result is always in [0.0, 1.0]
# ---------------------------------------------------------------------------


def test_all_worst_case_returns_zero():
    """All inputs at their worst saturate to floor (still non-negative)."""
    result = data_confidence(
        sample_size=0, missing_pct=1.0, sigma_distance=10.0, data_age_hours=10000.0,
    )
    assert result == 0.0


def test_all_best_case_returns_one():
    """All inputs at their best -> 1.0."""
    result = data_confidence(
        sample_size=1000, missing_pct=0.0, sigma_distance=0.0, data_age_hours=0.0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)
```

- [ ] **Step 2: Run — should FAIL with NotImplementedError**

```powershell
uv run pytest tests/unit/services/intelligence/test_presets_data.py -v --tb=short
```

Expected: 15 FAILED with NotImplementedError.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/services/intelligence/test_presets_data.py
git commit -m "test(113-01): failing unit tests for data_confidence preset"
```

### Task 4: Implement `data_confidence` (GREEN)

**Files:**
- Modify: `app/services/intelligence/presets/data.py`

- [ ] **Step 1: Replace the stub with the implementation**

```python
"""Data-domain confidence preset.

Used by Data Agent tools (cohort_analysis, query_analytics, ...) to
attach a calibrated confidence band to numerical / statistical outputs.

Formula reflects the statistical rigor already documented in
app/agents/data/agent.py:166-176 (sample_size >= 30 trends / >= 100
anomalies, missing >20% flagged, outliers >3 sigma).
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

DATA_WEIGHTS = {
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
    recency_horizon_hours: float = 720,  # 30 days
) -> float:
    """Compute confidence from internal-data statistical signals.

    Args:
        sample_size: Number of records in the analysis. Saturates at
            sample_threshold (default 100, matching the anomaly bar).
        missing_pct: Fraction of records with missing key fields,
            in [0.0, 1.0]. Higher means worse completeness.
        sigma_distance: Distance from baseline mean in standard
            deviations. **High sigma = anomalous = LOWER confidence in
            trend stability.** Saturates at 3.0.
        data_age_hours: Age of the underlying data in hours. Saturates
            at recency_horizon_hours (default 720h = 30 days).
        sample_threshold: Custom sample-size threshold. Set to 30 for
            trend confidence (matching the trends spec).
        recency_horizon_hours: Custom recency decay horizon.

    Returns:
        Confidence in [0.0, 1.0].
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
```

- [ ] **Step 2: Run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_presets_data.py -v --tb=short
```

Expected: 15 PASSED. If any fail, the formula has a typo or the test expectations are wrong — investigate the specific failure.

- [ ] **Step 3: Commit**

```bash
git add app/services/intelligence/presets/data.py
git commit -m "feat(113-01): implement data_confidence preset (GREEN)"
```

### Task 5: Wire `data_confidence` into `cohort_analysis`

**Files:**
- Modify: `app/agents/data/tools.py:220-265` — `cohort_analysis` function

- [ ] **Step 1: Read the current implementation** of `cohort_analysis` end-to-end

```bash
grep -n "def cohort_analysis" app/agents/data/tools.py
```

Then read ~50 lines from there. Note:
- What `CohortAnalysisService.analyze(...)` returns (the result dict shape)
- Which fields naturally map to `sample_size`, `missing_pct`, `sigma_distance`, `data_age_hours`

If `sigma_distance` isn't available from the service (the historical baseline may not exist yet), default it to `0.0` and add a TODO comment. Phase 113-03 (claim emission) will refine this.

- [ ] **Step 2: Modify `cohort_analysis` to compute the four signals and call `data_confidence`**

After the existing service call, before the return:

```python
# Compute confidence signals from the analysis result.
from app.services.intelligence import to_band
from app.services.intelligence.presets import data_confidence

retention_data = result.get("retention_data", {})
ltv_breakdown = result.get("ltv_breakdown", {})

# sample_size: total customers across all cohorts (proxy for analysis robustness)
sample_size = sum(
    int(cohort.get("cohort_size", 0))
    for cohort in retention_data.get("cohorts", [])
) if isinstance(retention_data, dict) else 0

# missing_pct: not directly available from CohortAnalysisService; assume
# 0 unless the service surfaces it later. Stripe-derived data is usually
# complete on the fields we need (signup_date, payment_count).
missing_pct = float(result.get("missing_data_pct", 0.0))

# sigma_distance: historical baseline not yet implemented in CohortAnalysisService.
# Default to 0 (trend stability is unknown, treated as "in line with baseline").
# Plan 113-03+ can introduce a baseline service and feed real sigma here.
sigma_distance = float(result.get("sigma_distance", 0.0))

# data_age_hours: time since the latest record. Use 1h as a conservative
# default if the service doesn't surface a freshness timestamp.
data_age_hours = float(result.get("data_age_hours", 1.0))

confidence = data_confidence(
    sample_size=sample_size,
    missing_pct=missing_pct,
    sigma_distance=sigma_distance,
    data_age_hours=data_age_hours,
)

result["confidence"] = confidence
result["band"] = to_band(confidence)
```

The exact field extractions depend on what `CohortAnalysisService` returns — adjust the keys based on Task 1 findings. If the service does NOT surface `missing_data_pct`, `sigma_distance`, or `data_age_hours`, the conservative defaults (0.0 missing, 0.0 sigma, 1.0h age) keep the confidence high for well-formed Stripe data and don't break existing callers.

- [ ] **Step 3: Update or add a test for `cohort_analysis` confidence output**

Find existing tests:
```bash
grep -rn "cohort_analysis\|CohortAnalysisService" tests/ | head
```

If a test for `cohort_analysis` exists, add an assertion for the new `confidence` and `band` fields. If no test exists, add a minimal one:

`tests/unit/agents/data/test_cohort_analysis_confidence.py`:

```python
"""Confirm cohort_analysis attaches confidence + band fields (Plan 113-01)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_cohort_analysis_attaches_confidence_and_band():
    """cohort_analysis result includes confidence (float) and band (literal)."""
    from app.agents.data.tools import cohort_analysis

    fake_result = {
        "retention_data": {
            "cohorts": [
                {"cohort_month": "2026-01", "cohort_size": 150},
                {"cohort_month": "2026-02", "cohort_size": 120},
            ],
        },
        "ltv_breakdown": {},
        "executive_summary": "Stable retention.",
        "chart_data": {},
    }

    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
    ) as fake_service_class:
        fake_service = fake_service_class.return_value
        fake_service.analyze = AsyncMock(return_value=fake_result)
        result = await cohort_analysis(months=6)

    assert "confidence" in result
    assert "band" in result
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["band"] in ("low", "medium", "high")
    # 270 customers, default missing/sigma/age — should be high
    assert result["band"] == "high"
```

If `CohortAnalysisService` is instantiated differently (singleton, factory), adapt the mocking — the goal is to control the return shape so the confidence wiring is the only thing under test.

- [ ] **Step 4: Run the new test**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
uv run pytest tests/unit/agents/data/test_cohort_analysis_confidence.py -v --tb=short
```

Expected: PASS. If the mock's patch path doesn't intercept (e.g., the actual import path differs), update the patch target.

- [ ] **Step 5: Confirm no Data Agent regressions**

```powershell
uv run pytest tests/unit/agents/data/ tests/unit/test_data_*.py -v --tb=short 2>&1 | Select-Object -Last 15
```

Expected: existing tests pass; the new test passes.

- [ ] **Step 6: Commit**

```bash
git add app/agents/data/tools.py tests/unit/agents/data/test_cohort_analysis_confidence.py
git commit -m "feat(113-01): wire data_confidence into cohort_analysis pilot (GREEN)"
```

### Task 6: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/presets/data.py app/agents/data/tools.py tests/unit/services/intelligence/test_presets_data.py tests/unit/agents/data/test_cohort_analysis_confidence.py
uv run ruff format app/services/intelligence/presets/data.py app/agents/data/tools.py tests/unit/services/intelligence/test_presets_data.py tests/unit/agents/data/test_cohort_analysis_confidence.py --check
```

Expected: all clean. Fix in-place if any errors.

- [ ] **Step 2: Final test run**

```powershell
uv run pytest tests/unit/services/intelligence/ tests/unit/agents/data/test_cohort_analysis_confidence.py -v --tb=short
```

Expected: all PASS — 17 from confidence module (pre-existing) + 15 from data preset + the cohort_analysis confidence test.

- [ ] **Step 3: Acceptance check against spec**

| Spec line | Status |
|---|---|
| `data_confidence(sample_size, missing_pct, sigma_distance, data_age_hours) -> float` | ✓ Task 4 |
| Weights match spec (0.35 sample, 0.25 completeness, 0.25 strength, 0.15 recency) | ✓ Task 4 + tests |
| `statistical_strength = 1 - sigma/3` inversion preserved | ✓ Task 4 + `test_three_sigma_zeros_statistical_strength` |
| `sample_threshold` / `recency_horizon_hours` configurable | ✓ Task 4 + custom-threshold tests |
| Output clamped to `[0, 1]` | ✓ via `score_confidence` |
| Pilot integration: `cohort_analysis` carries confidence + band | ✓ Task 5 |
| Existing Data Agent test suite green | ✓ Task 5 Step 5 |
| No new ADK tools | ✓ Library only |

- [ ] **Step 4: Commit any lint fixes**

```bash
git add app/services/intelligence/presets/data.py app/agents/data/tools.py tests/unit/services/intelligence/test_presets_data.py tests/unit/agents/data/test_cohort_analysis_confidence.py
git commit -m "style(113-01): lint and format fixes for data preset and cohort wiring"
```

Skip if no fixes needed.

- [ ] **Step 5: Plan 113-01 complete. Plan 113-02 (Data Agent cache integration) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `data_confidence` preset with 4-signal formula | Tasks 2, 3, 4 |
| Configurable `sample_threshold` and `recency_horizon_hours` | Task 4 + custom-threshold tests |
| `statistical_strength` inverts sigma (anomalous = uncertain) | Task 4 + `test_three_sigma_zeros_statistical_strength` |
| Wired into Data Agent's `cohort_analysis` | Task 5 |
| Response payload carries `confidence` + `band` | Task 5 + `test_cohort_analysis_attaches_confidence_and_band` |
| Existing Data Agent tests stay green | Task 5 Step 5 |
| Public surface importable from `app.services.intelligence.presets` | Task 2 |
| Lint clean | Task 6 |

All spec lines covered. No placeholders. No unmapped requirements.
