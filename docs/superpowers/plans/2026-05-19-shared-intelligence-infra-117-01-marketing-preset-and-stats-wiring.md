# Shared Intelligence Infrastructure — Plan 117-01: Marketing Preset + Stats Wiring + Self-Improvement Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `app/services/intelligence/presets/marketing.py` exposing `marketing_confidence(...)`, wire it into the Marketing Agent's quantitative tool surfaces (campaign-performance summarizer, cross-channel attribution, ROAS budget recommender, social analytics) so every Marketing output carries a calibrated `confidence` + `band`, and audit `app/services/self_improvement_engine.py` for Marketing-Agent entanglement *before* any code changes land.

**Architecture:** The preset is a thin wrapper over the generic `score_confidence(...)` scorer (Plan 112-01) with Marketing-specific input mapping. Per Decision #8 in the rolling-adoption design, the **first** sub-plan of every adoption phase must audit the self-improvement engine. The audit ships as a markdown report committed alongside the preset so subsequent plans (117-02, 117-03, 117-04) execute against a known engine surface. Marketing has the highest regression risk of any agent in the rollout (active downstream workflows, paid-spend gates, multi-platform integrations), so this plan also publishes the **statistical-significance helper** that downstream claim emission (117-03) and the regression baseline (117-04) both depend on.

**Tech Stack:** `app/services/intelligence/presets/marketing.py` (new), `app/services/intelligence/presets/__init__.py` (modified), `app/services/intelligence/marketing_stats.py` (new helper), `app/agents/tools/campaign_performance_tools.py` (modified — confidence wiring), `app/agents/tools/attribution_tools.py` (modified — confidence wiring), `app/agents/tools/social_analytics.py` (modified — confidence wiring).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 117 — Marketing Agent adoption · Decision #8 (self-improvement audit gate).

**Out of scope:** Claim emission to `kg_findings` (Plan 117-03). Multi-platform cache wiring (Plan 117-02). Regression-baseline capture and replay (Plan 117-04). Persona-aware confidence weighting. Calibration of weights from telemetry — the values shipped here are educated-guess.

---

## File structure

**Create:**
- `app/services/intelligence/presets/marketing.py` — `marketing_confidence(...)` + `MARKETING_WEIGHTS` constant
- `app/services/intelligence/marketing_stats.py` — `attribution_completeness(...)`, `statistical_significance(...)`, `audience_coverage(...)`, `recency_score(...)` helpers
- `docs/superpowers/audits/2026-05-19-self-improvement-engine-marketing-audit.md` — Marketing-Agent entanglement audit (markdown report)
- `tests/unit/services/intelligence/test_presets_marketing.py` — preset property tests + golden values
- `tests/unit/services/intelligence/test_marketing_stats.py` — helper unit tests
- `tests/unit/app/agents/tools/test_campaign_performance_confidence.py` — confidence wiring on the summarizer tool

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `marketing_confidence`
- `app/agents/tools/campaign_performance_tools.py` — call `marketing_confidence` + attach `confidence` / `band` to the tool's returned dict
- `app/agents/tools/attribution_tools.py` — same wiring on `get_cross_channel_attribution` and `get_budget_recommendation`
- `app/agents/tools/social_analytics.py` — same wiring on `get_social_analytics` and `get_all_platform_analytics`

---

## Pre-flight context

`marketing_confidence` signature:

```python
def marketing_confidence(
    attribution_completeness: float,
    statistical_significance: float,
    audience_coverage: float,
    recency: float,
) -> float:
```

Weights (per the spec):

```python
MARKETING_WEIGHTS: dict[str, float] = {
    "attribution_completeness": 0.35,
    "statistical_significance": 0.30,
    "audience_coverage":        0.20,
    "recency":                  0.15,
}
```

All four inputs are normalised to `[0.0, 1.0]` before the call. `score_confidence` validates key match + sum-≤-1.0 and clamps to `[0.0, 1.0]`.

**Input definitions** (load-bearing — Plans 117-03 and 117-04 both reference these):

- `attribution_completeness` — fraction of conversions matched to a campaign by UTM / CRM linkage. `matched_conversions / total_conversions`. When 0 conversions: pass 0.0. Floor at 0.0, ceiling at 1.0.
- `statistical_significance` — binomial / chi-square confidence proxy for the observed lift vs. baseline. Mapped to `[0.0, 1.0]` via `min(1.0, max(0.0, (z_score - 1.0) / 2.29))` (z=1.0 → 0.0, z=1.96 → ~0.42, z=2.58 → ~0.69, z=3.29+ → 1.0). When sample size < 30 or zero variance: pass 0.0.
- `audience_coverage` — fraction of the targeted persona/segment population observed in the measurement window. `observed_segment_size / declared_segment_size` clamped to `[0.0, 1.0]`. When the declared segment size is unknown: pass 0.5 (neutral).
- `recency` — `max(0.0, 1.0 - data_age_hours / 720.0)` — 30-day horizon, identical to `data_confidence`'s recency formula.

**Statistical-significance helper rationale:** Marketing's biggest credibility problem today is that "campaign X is winning" claims rest on tiny samples. Phase 113's `cohort_analysis` already learned this lesson — Plan 117-01 makes the *test* (binomial z-score + sample-size floor) explicit so 117-03 doesn't have to reinvent it.

**Self-improvement audit rationale:** `app/services/self_improvement_engine.py` reads agent-specific signal shapes and can mutate prompts/tool selection if the contract drifts. Per the spec's Risk #6 ("Self-improvement engine entangles with old per-agent code paths"), we must capture *what* the engine reads about the Marketing Agent today, so 117-02/03/04 can verify they have not accidentally broken that surface. The audit also confirms whether `skill_experiment_evaluator.py` exists yet in this repo — if not (it currently does not; see `Grep` for `skill_experiment_evaluator` returning zero hits on 2026-05-19), the audit records that gap and marks engine entanglement as "engine-only, no evaluator".

Environment quirks: identical to the Phase 113 plans. Windows + uv + PowerShell for runs; `tests/integration/conftest.py:63-98` mocks the Supabase client (irrelevant to this plan — Plan 117-01 is pure-unit).

Acceptance bar (from spec § Phase 117):
- `marketing_confidence` shipped; clamped to `[0.0, 1.0]`; weights sum ≤ 1.0
- Every Marketing tool that emits a quantitative result attaches `confidence` + `band` (no hardcoded `confidence: 0.9`)
- Self-improvement audit committed to `docs/superpowers/audits/`
- Lint clean (`uv run ruff check app/services/intelligence/presets/marketing.py app/services/intelligence/marketing_stats.py app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py app/agents/tools/social_analytics.py`)
- No regression in `tests/unit/services/test_campaign_performance_summarizer.py` or `tests/unit/app/agents/test_marketing_campaign_wizard.py`

---

## Tasks

### Task 1: Pre-flight — confirm prerequisites + dependency inventory

**Files:**
- Read-only: `app/services/intelligence/__init__.py`, `app/services/intelligence/confidence.py`, `app/services/intelligence/presets/__init__.py`, `app/services/intelligence/presets/data.py`, `app/services/self_improvement_engine.py`

- [ ] **Step 1: Confirm Phase 112/113 infrastructure is importable**

```powershell
uv run python -c "from app.services.intelligence import score_confidence, to_band; from app.services.intelligence.presets import data_confidence, research_confidence; print('OK')"
```

Expected stdout: `OK`. If this fails the Phase 112 modules are missing and **STOP** — Plan 117-01 cannot proceed without the generic scorer.

- [ ] **Step 2: Confirm Marketing Agent code shape matches the spec assumption**

```powershell
uv run python -c "from app.agents.marketing.agent import marketing_agent; print(marketing_agent.name)"
uv run python -c "from app.agents.tools.campaign_performance_tools import summarize_campaign_performance; from app.agents.tools.attribution_tools import ATTRIBUTION_TOOLS; from app.agents.tools.social_analytics import get_social_analytics, get_all_platform_analytics; print('OK')"
```

Expected: `MarketingAutomationAgent` on the first line and `OK` on the second. If imports fail, the Marketing-Agent surface has drifted — fix imports before proceeding.

- [ ] **Step 3: Capture the self-improvement-engine read shape for Marketing**

```powershell
uv run python -c "import ast, pathlib; src = pathlib.Path('app/services/self_improvement_engine.py').read_text(); [print(line) for line in src.splitlines() if 'marketing' in line.lower() or 'MarketingAutomation' in line]"
```

Note every line that mentions the Marketing Agent, marketing tools, or `marketing_*` skill IDs. The audit deliverable in Task 2 enumerates these.

- [ ] **Step 4: Confirm `skill_experiment_evaluator.py` status**

```powershell
uv run python -c "import importlib; m = importlib.util.find_spec('app.services.skill_experiment_evaluator'); print('present' if m else 'absent')"
```

If `absent`, the audit records "no skill_experiment_evaluator on this branch; engine-only entanglement". This is the expected state on `spec-b-clean` as of 2026-05-19.

### Task 2: Write the self-improvement audit (Decision #8 gate)

**Files:**
- Create: `docs/superpowers/audits/2026-05-19-self-improvement-engine-marketing-audit.md`

- [ ] **Step 1: Draft the audit**

The audit document MUST cover:

1. **Read surface** — every attribute/method the engine reads from Marketing Agent / Marketing tools (use Task 1 Step 3 output).
2. **Write surface** — what (if anything) the engine mutates (prompt fragments, tool ordering, persona-policy blocks). If nothing, say "no write surface".
3. **Skill IDs** — every `marketing_*` skill ID registered today (`app/agents/tools/agent_skills.py:MKT_SKILL_TOOLS`).
4. **Evaluator status** — whether `skill_experiment_evaluator.py` exists. If absent, state explicitly and note that any future evaluator must consume the new `confidence` / `band` fields shipped by this phase.
5. **Risk verdict** — green / yellow / red on whether Plans 117-02/03/04 can change Marketing tool return shapes without breaking the engine.
6. **Pinning commitments** — list the fields Plan 117-03 will ADD (`confidence`, `band`) and confirm they are additive, not mutating.

Use this skeleton:

```markdown
# Self-Improvement Engine — Marketing Agent Entanglement Audit

**Date:** 2026-05-19
**Phase:** 117 (Marketing Agent adoption)
**Owner:** <handle of plan executor>
**Decision reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Decision #8

## Read surface

| Engine file:line | Reads | Notes |
|---|---|---|
| `app/services/self_improvement_engine.py:<line>` | `<attr>` | <observed pattern> |

## Write surface

<bullets, or "no write surface against Marketing">

## Skill IDs registered

<table from `MKT_SKILL_TOOLS`>

## skill_experiment_evaluator status

<present | absent>; if absent, what the next phase requires.

## Risk verdict

<green | yellow | red> — <one-paragraph justification>

## Additive-field commitments (Plans 117-03, 117-04)

- New top-level keys on Marketing tool responses: `confidence: float`, `band: Literal["low", "medium", "high"]`.
- No existing key is removed, renamed, or has its type changed.
- Engine code that grep's for `confidence`/`band` MUST be inspected separately before 117-03 lands.
```

- [ ] **Step 2: Commit the audit BEFORE any code changes**

```bash
git add docs/superpowers/audits/2026-05-19-self-improvement-engine-marketing-audit.md
git commit -m "docs(117-01): self-improvement engine audit for Marketing entanglement (Decision #8)"
```

Per the policy, the audit lands first so reviewers can object before any signal-shape change.

### Task 3: Implement `marketing_stats.py` helpers (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_marketing_stats.py`
- Create: `app/services/intelligence/marketing_stats.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for Marketing input-normalisation helpers."""

from __future__ import annotations

import math

import pytest


def test_attribution_completeness_zero_conversions_returns_zero():
    from app.services.intelligence.marketing_stats import attribution_completeness

    assert attribution_completeness(matched=0, total=0) == 0.0


def test_attribution_completeness_clamps_to_unit_interval():
    from app.services.intelligence.marketing_stats import attribution_completeness

    assert attribution_completeness(matched=42, total=100) == pytest.approx(0.42)
    # Defensive: matched > total should clamp to 1.0, never raise
    assert attribution_completeness(matched=120, total=100) == 1.0
    # Defensive: negative inputs are floored at 0
    assert attribution_completeness(matched=-5, total=100) == 0.0


def test_statistical_significance_small_sample_returns_zero():
    from app.services.intelligence.marketing_stats import statistical_significance

    assert statistical_significance(z_score=2.5, n=20) == 0.0  # below floor
    assert statistical_significance(z_score=2.5, n=30) > 0.0


def test_statistical_significance_maps_z_score_to_unit_interval():
    from app.services.intelligence.marketing_stats import statistical_significance

    # z=1.0 -> 0.0, z=1.96 -> ~0.42, z=3.29 -> 1.0
    assert statistical_significance(z_score=1.0, n=100) == 0.0
    assert statistical_significance(z_score=1.96, n=100) == pytest.approx(0.419, abs=0.01)
    assert statistical_significance(z_score=4.0, n=100) == 1.0
    # NaN / inf must degrade to 0.0, not propagate
    assert statistical_significance(z_score=math.nan, n=100) == 0.0
    assert statistical_significance(z_score=math.inf, n=100) == 1.0


def test_audience_coverage_unknown_segment_returns_neutral():
    from app.services.intelligence.marketing_stats import audience_coverage

    assert audience_coverage(observed=0, declared=None) == 0.5
    assert audience_coverage(observed=500, declared=None) == 0.5


def test_audience_coverage_clamps():
    from app.services.intelligence.marketing_stats import audience_coverage

    assert audience_coverage(observed=300, declared=1000) == 0.3
    assert audience_coverage(observed=1200, declared=1000) == 1.0
    assert audience_coverage(observed=-5, declared=1000) == 0.0


def test_recency_score_30_day_horizon():
    from app.services.intelligence.marketing_stats import recency_score

    assert recency_score(data_age_hours=0) == 1.0
    assert recency_score(data_age_hours=360) == pytest.approx(0.5, abs=0.001)
    assert recency_score(data_age_hours=720) == 0.0
    assert recency_score(data_age_hours=10_000) == 0.0
```

- [ ] **Step 2: Run — should FAIL (module missing)**

```powershell
uv run pytest tests/unit/services/intelligence/test_marketing_stats.py -v --tb=short
```

Expected: `ModuleNotFoundError: No module named 'app.services.intelligence.marketing_stats'`.

- [ ] **Step 3: Implement `app/services/intelligence/marketing_stats.py`**

```python
"""Input normalisation helpers for marketing_confidence.

Each helper maps a raw observation to the [0.0, 1.0] band that
marketing_confidence expects. Helpers degrade silently on bad
inputs (NaN, negative, missing) rather than raising, because
Marketing tool surfaces routinely return partial data and we
do not want one missing field to crash the whole tool.
"""

from __future__ import annotations

import math


_MIN_SAMPLE = 30  # below this, statistical_significance returns 0.0
_RECENCY_HORIZON_HOURS = 720.0  # 30 days, identical to data_confidence


def attribution_completeness(*, matched: int, total: int) -> float:
    """Fraction of conversions matched to a campaign by UTM / CRM linkage.

    Args:
        matched: Number of conversions with a campaign attribution.
        total:   Total observed conversions in the window.

    Returns:
        ``matched / total`` clamped to ``[0.0, 1.0]``. Returns 0.0 when
        ``total <= 0`` (no signal, treat as worst-case for confidence).
    """
    if total <= 0:
        return 0.0
    matched = max(0, matched)
    raw = matched / total
    return min(1.0, max(0.0, raw))


def statistical_significance(*, z_score: float, n: int) -> float:
    """Map a z-score to [0.0, 1.0] under a 30-sample floor.

    Mapping: ``(z - 1.0) / 2.29`` clamped to ``[0.0, 1.0]`` (z=1.0 -> 0.0,
    z=1.96 -> ~0.419, z=3.29 -> 1.0). The 2.29 divisor is chosen so the
    ~95% one-sided cutoff lands near 0.42 and the ~99.9% cutoff saturates
    at 1.0.

    NaN inputs degrade to 0.0; +inf saturates to 1.0; below the
    sample floor (``n < 30``), always returns 0.0 regardless of z.

    Args:
        z_score: Observed z-statistic for the lift vs. baseline.
        n:       Sample size that produced the z-statistic.

    Returns:
        Float in ``[0.0, 1.0]``.
    """
    if n < _MIN_SAMPLE:
        return 0.0
    if math.isnan(z_score):
        return 0.0
    if math.isinf(z_score):
        return 1.0 if z_score > 0 else 0.0
    raw = (z_score - 1.0) / 2.29
    return min(1.0, max(0.0, raw))


def audience_coverage(*, observed: int, declared: int | None) -> float:
    """Fraction of declared segment size observed in the measurement window.

    Args:
        observed: Number of users / events observed for this segment.
        declared: Total segment size, or None when unknown.

    Returns:
        ``observed / declared`` clamped to ``[0.0, 1.0]``. Returns 0.5
        (neutral) when declared is None — we have no basis to score either
        way and 0.5 is intentionally non-committal so it neither inflates
        nor crushes the overall confidence.
    """
    if declared is None:
        return 0.5
    if declared <= 0:
        return 0.5
    observed = max(0, observed)
    raw = observed / declared
    return min(1.0, max(0.0, raw))


def recency_score(data_age_hours: float) -> float:
    """30-day recency curve identical to data_confidence's recency."""
    if data_age_hours <= 0:
        return 1.0
    raw = 1.0 - (data_age_hours / _RECENCY_HORIZON_HOURS)
    return max(0.0, min(1.0, raw))
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_marketing_stats.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/marketing_stats.py tests/unit/services/intelligence/test_marketing_stats.py
git commit -m "feat(117-01): marketing_stats helpers for confidence input normalisation (GREEN)"
```

### Task 4: Implement `marketing_confidence` preset (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_presets_marketing.py`
- Create: `app/services/intelligence/presets/marketing.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Failing tests**

```python
"""Property + golden tests for marketing_confidence."""

from __future__ import annotations

import pytest


def test_marketing_confidence_returns_clamped_value():
    from app.services.intelligence.presets import marketing_confidence

    # All-zero inputs -> 0.0
    assert marketing_confidence(0.0, 0.0, 0.0, 0.0) == 0.0
    # All-one inputs -> 1.0 (weights sum to 1.0)
    assert marketing_confidence(1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)


def test_marketing_confidence_weighted_average_holds():
    from app.services.intelligence.presets import marketing_confidence
    from app.services.intelligence.presets.marketing import MARKETING_WEIGHTS

    # Verify the weight allocation matches the spec
    assert MARKETING_WEIGHTS == {
        "attribution_completeness": 0.35,
        "statistical_significance": 0.30,
        "audience_coverage":        0.20,
        "recency":                  0.15,
    }
    # Targeted check: only attribution_completeness=1.0 -> 0.35
    result = marketing_confidence(1.0, 0.0, 0.0, 0.0)
    assert result == pytest.approx(0.35, abs=1e-6)
    # only statistical_significance=1.0 -> 0.30
    assert marketing_confidence(0.0, 1.0, 0.0, 0.0) == pytest.approx(0.30, abs=1e-6)


def test_marketing_confidence_clamps_out_of_range_inputs():
    """Defensive: inputs >1.0 or <0.0 do not push the score outside [0,1]."""
    from app.services.intelligence.presets import marketing_confidence

    # Out-of-range inputs are accepted but clamped via score_confidence
    high = marketing_confidence(2.0, 2.0, 2.0, 2.0)
    assert 0.0 <= high <= 1.0
    low = marketing_confidence(-1.0, -1.0, -1.0, -1.0)
    assert 0.0 <= low <= 1.0


@pytest.mark.parametrize(
    "ac, ss, coverage, recency, expected_band",
    [
        (0.95, 0.90, 0.80, 0.95, "high"),    # > 0.75 -> high
        (0.60, 0.60, 0.50, 0.60, "medium"),  # 0.50-0.75 -> medium
        (0.20, 0.10, 0.10, 0.10, "low"),     # < 0.50 -> low
    ],
)
def test_marketing_confidence_bands_align_with_research_thresholds(
    ac, ss, coverage, recency, expected_band,
):
    """Bands use the 0.50 / 0.75 split inherited from research_confidence."""
    from app.services.intelligence import to_band
    from app.services.intelligence.presets import marketing_confidence

    score = marketing_confidence(ac, ss, coverage, recency)
    assert to_band(score) == expected_band
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_presets_marketing.py -v --tb=short
```

- [ ] **Step 3: Implement `app/services/intelligence/presets/marketing.py`**

```python
"""Marketing-domain confidence preset.

Phase 117-01 — wires onto campaign performance, cross-channel attribution,
ROAS budget recommender, and social analytics tools.

Weights:
- attribution_completeness (0.35): fraction of conversions matched to a campaign
- statistical_significance (0.30): binomial / chi-square confidence proxy
- audience_coverage        (0.20): fraction of declared segment observed
- recency                  (0.15): how fresh the measurement window is
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

MARKETING_WEIGHTS: dict[str, float] = {
    "attribution_completeness": 0.35,
    "statistical_significance": 0.30,
    "audience_coverage": 0.20,
    "recency": 0.15,
}


def marketing_confidence(
    attribution_completeness: float,
    statistical_significance: float,
    audience_coverage: float,
    recency: float,
) -> float:
    """Compute marketing-domain confidence from four normalised inputs.

    Args:
        attribution_completeness: Fraction of conversions matched to a
            campaign (0.0-1.0). Use marketing_stats.attribution_completeness
            to compute from raw counts.
        statistical_significance: Significance proxy (0.0-1.0). Use
            marketing_stats.statistical_significance to compute from
            z-score + sample size.
        audience_coverage: Fraction of declared segment observed (0.0-1.0).
            Use marketing_stats.audience_coverage; pass 0.5 when declared
            segment size is unknown.
        recency: Recency score (0.0-1.0). Use marketing_stats.recency_score
            with the freshest record's data_age_hours.

    Returns:
        Confidence score clamped to ``[0.0, 1.0]``.
    """
    return score_confidence(
        inputs={
            "attribution_completeness": attribution_completeness,
            "statistical_significance": statistical_significance,
            "audience_coverage": audience_coverage,
            "recency": recency,
        },
        weights=MARKETING_WEIGHTS,
    )
```

- [ ] **Step 4: Re-export from `presets/__init__.py`**

```python
"""Per-agent confidence presets."""

from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.marketing import marketing_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = ["data_confidence", "marketing_confidence", "research_confidence"]
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_presets_marketing.py -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/presets/marketing.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_presets_marketing.py
git commit -m "feat(117-01): marketing_confidence preset with attribution/significance/coverage/recency weights"
```

### Task 5: Wire `marketing_confidence` into `summarize_campaign_performance` (TDD)

**Files:**
- Create: `tests/unit/app/agents/tools/test_campaign_performance_confidence.py`
- Modify: `app/agents/tools/campaign_performance_tools.py`

The summarizer is the single most-used Marketing surface ("how are my ads doing?"). Confidence-wiring it first proves the pattern; remaining tools repeat it identically.

- [ ] **Step 1: Failing test**

```python
"""Confidence wiring on summarize_campaign_performance."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_summarize_campaign_performance_attaches_confidence_and_band():
    """Tool response must include `confidence` (float in [0,1]) and `band`."""
    from app.agents.tools.campaign_performance_tools import (
        summarize_campaign_performance,
    )

    fake_payload = {
        "summary_text": "Spent $340 this week, 12 conversions",
        "total_spend": 340.0,
        "total_conversions": 12,
        "overall_cpa": 28.33,
        "wow_spend_change_pct": 0.20,
        "wow_conversions_change_pct": 0.10,
        "per_campaign": [
            {"campaign_id": "g1", "spend": 200.0, "conversions": 8,
             "matched_conversions": 8, "z_score": 2.1, "n": 80,
             "observed_audience": 5000, "declared_audience": 10000,
             "data_age_hours": 6},
        ],
        "period": "2026-05-12_2026-05-19",
        "prior_period": "2026-05-05_2026-05-12",
    }

    with patch(
        "app.agents.tools.campaign_performance_tools._get_user_id",
        return_value="u-1",
    ), patch(
        "app.services.campaign_performance_summarizer.CampaignPerformanceSummarizer.summarize_all_platforms",
        new=AsyncMock(return_value=fake_payload),
    ):
        result = await summarize_campaign_performance(days=7)

    assert "confidence" in result, "tool must attach confidence"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["band"] in {"low", "medium", "high"}
    # Existing keys MUST still be present (additive change, not mutating)
    for k in fake_payload:
        assert k in result


@pytest.mark.asyncio
async def test_summarize_campaign_performance_zero_conversions_low_band():
    """Zero attribution -> attribution_completeness=0 -> low band."""
    from app.agents.tools.campaign_performance_tools import (
        summarize_campaign_performance,
    )

    fake_payload = {
        "summary_text": "No activity this week",
        "total_spend": 0.0,
        "total_conversions": 0,
        "overall_cpa": 0.0,
        "wow_spend_change_pct": 0.0,
        "wow_conversions_change_pct": 0.0,
        "per_campaign": [],
        "period": "x",
        "prior_period": "y",
    }

    with patch(
        "app.agents.tools.campaign_performance_tools._get_user_id",
        return_value="u-1",
    ), patch(
        "app.services.campaign_performance_summarizer.CampaignPerformanceSummarizer.summarize_all_platforms",
        new=AsyncMock(return_value=fake_payload),
    ):
        result = await summarize_campaign_performance(days=7)

    assert result["band"] == "low"
    assert result["confidence"] < 0.5


@pytest.mark.asyncio
async def test_summarize_campaign_performance_error_path_omits_confidence():
    """Authentication-failure path returns the error untouched (no confidence)."""
    from app.agents.tools.campaign_performance_tools import (
        summarize_campaign_performance,
    )

    with patch(
        "app.agents.tools.campaign_performance_tools._get_user_id",
        return_value=None,
    ):
        result = await summarize_campaign_performance(days=7)
    assert result == {"error": "Authentication required"}
    assert "confidence" not in result
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py -v --tb=short
```

- [ ] **Step 3: Implement the wiring**

Edit `app/agents/tools/campaign_performance_tools.py` — after the existing `summarize_campaign_performance` body returns the summarizer payload, decorate the dict with `confidence` + `band`. The change is additive only.

Add a private helper at module scope:

```python
def _attach_marketing_confidence(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach confidence + band to a marketing tool response.

    Reads aggregate signals from the payload's per-campaign rows and
    applies the marketing_confidence preset. Never raises — on any
    error returns the payload unchanged (read-degrade pattern).
    """
    from app.services.intelligence import to_band
    from app.services.intelligence.marketing_stats import (
        attribution_completeness,
        audience_coverage,
        recency_score,
        statistical_significance,
    )
    from app.services.intelligence.presets import marketing_confidence

    try:
        rows = payload.get("per_campaign") or []
        matched = sum(int(r.get("matched_conversions", 0)) for r in rows)
        total = sum(int(r.get("conversions", 0)) for r in rows)
        # Average z and n across campaigns; treat absent fields as zeros
        zs = [float(r.get("z_score", 0.0)) for r in rows if r.get("z_score") is not None]
        ns = [int(r.get("n", 0)) for r in rows if r.get("n") is not None]
        avg_z = sum(zs) / len(zs) if zs else 0.0
        total_n = sum(ns)
        observed = sum(int(r.get("observed_audience", 0)) for r in rows)
        declared_vals = [r.get("declared_audience") for r in rows if r.get("declared_audience") is not None]
        declared = sum(int(d) for d in declared_vals) if declared_vals else None
        ages = [float(r.get("data_age_hours", 0.0)) for r in rows]
        min_age = min(ages) if ages else 0.0

        ac = attribution_completeness(matched=matched, total=total)
        ss = statistical_significance(z_score=avg_z, n=total_n)
        coverage = audience_coverage(observed=observed, declared=declared)
        recency = recency_score(min_age)

        score = marketing_confidence(ac, ss, coverage, recency)
        payload["confidence"] = round(score, 4)
        payload["band"] = to_band(score)
    except Exception:
        # Never crash a Marketing tool on a confidence-attachment failure.
        logger.warning(
            "summarize_campaign_performance: confidence attachment failed",
            exc_info=True,
        )
    return payload
```

Then modify the existing function to call the helper before returning:

```python
async def summarize_campaign_performance(days: int = 7) -> dict[str, Any]:
    # ... existing docstring + early-return / validation ...
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}
    if days <= 0:
        return {"error": "days must be a positive integer."}

    try:
        from app.services.campaign_performance_summarizer import (
            CampaignPerformanceSummarizer,
        )

        summarizer = CampaignPerformanceSummarizer()
        payload = await summarizer.summarize_all_platforms(user_id=user_id, days=days)
        return _attach_marketing_confidence(payload)
    except Exception as exc:
        logger.exception(
            "summarize_campaign_performance failed for user=%s days=%s",
            user_id, days,
        )
        return {"error": f"Failed to summarize campaign performance: {exc}"}
```

Update the function docstring's `Returns` block to document the new `confidence` and `band` keys.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/campaign_performance_tools.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
git commit -m "feat(117-01): attach marketing_confidence to summarize_campaign_performance"
```

### Task 6: Wire `marketing_confidence` into attribution + social-analytics tools

**Files:**
- Modify: `app/agents/tools/attribution_tools.py`
- Modify: `app/agents/tools/social_analytics.py`

The pattern is identical to Task 5: import `_attach_marketing_confidence`, call it on the returned dict, document the additive keys. Both tools accept a `per_*` breakdown that supplies the same input signals.

- [ ] **Step 1: Promote `_attach_marketing_confidence` to a shared helper**

Move the helper from `campaign_performance_tools.py` to a new module `app/agents/tools/_marketing_confidence.py` so all three tool files can import it without circular references. Update the Task 5 import accordingly.

- [ ] **Step 2: Add a parameterised unit test that covers attribution + social analytics**

Append to `tests/unit/app/agents/tools/test_campaign_performance_confidence.py`:

```python
@pytest.mark.asyncio
async def test_get_cross_channel_attribution_attaches_confidence():
    from app.agents.tools.attribution_tools import get_cross_channel_attribution

    fake = {
        "summary_text": "Top channel: Google Ads",
        "per_channel": [
            {"channel": "google_ads", "conversions": 50, "matched_conversions": 48,
             "z_score": 2.2, "n": 80, "observed_audience": 4000,
             "declared_audience": 8000, "data_age_hours": 2},
        ],
    }
    with patch(
        "app.services.cross_channel_attribution_service.CrossChannelAttributionService.compute",
        new=AsyncMock(return_value=fake),
    ), patch(
        "app.agents.tools.attribution_tools._get_user_id", return_value="u-1",
    ):
        result = await get_cross_channel_attribution(days=14)

    assert "confidence" in result
    assert result["band"] in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_get_social_analytics_attaches_confidence():
    from app.agents.tools.social_analytics import get_social_analytics

    fake = {
        "summary_text": "Posts gained 12k impressions",
        "per_post": [
            {"impressions": 5000, "engagements": 250, "matched_conversions": 0,
             "conversions": 0, "z_score": 1.5, "n": 40,
             "observed_audience": 5000, "declared_audience": None,
             "data_age_hours": 4},
        ],
    }
    with patch(
        "app.services.social_analytics_service.SocialAnalyticsService.get_summary",
        new=AsyncMock(return_value=fake),
    ), patch(
        "app.agents.tools.social_analytics._get_user_id", return_value="u-1",
    ):
        result = await get_social_analytics(platform="instagram", days=7)

    assert "confidence" in result
    assert result["band"] in {"low", "medium", "high"}
```

Note: the attribution and social-analytics services may expose different aggregator keys (`per_channel`, `per_post`). The shared helper must accept either by reading whichever `per_*` key exists.

- [ ] **Step 3: Generalise the helper to accept any `per_*` rollup**

In `app/agents/tools/_marketing_confidence.py`:

```python
def _find_breakdown_rows(payload: dict) -> list[dict]:
    """Pick the first per_* list-of-dicts in the payload."""
    for key in ("per_campaign", "per_channel", "per_post", "per_platform"):
        rows = payload.get(key)
        if isinstance(rows, list) and rows:
            return rows
    return []
```

Replace the direct `payload.get("per_campaign") or []` lookup with `_find_breakdown_rows(payload)`.

- [ ] **Step 4: Wire the attribution + social-analytics tools**

In `app/agents/tools/attribution_tools.py`, locate the two functions `get_cross_channel_attribution` and `get_budget_recommendation`. After each one's existing return-payload step, call `_attach_marketing_confidence(payload)` and document the added keys.

In `app/agents/tools/social_analytics.py`, do the same for `get_social_analytics` and `get_all_platform_analytics`.

- [ ] **Step 5: Run the parameterised tests + the existing Marketing tests for no-regression**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py -v --tb=short
uv run pytest tests/unit/services/test_campaign_performance_summarizer.py -v --tb=short
uv run pytest tests/unit/app/agents/test_marketing_campaign_wizard.py -v --tb=short
```

Expected: all PASS. If `test_campaign_performance_summarizer.py` or `test_marketing_campaign_wizard.py` fail, the wiring is non-additive — revert and tighten.

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/_marketing_confidence.py app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py app/agents/tools/social_analytics.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
git commit -m "feat(117-01): attach marketing_confidence to attribution + social analytics tools"
```

### Task 7: Lint + final acceptance sign-off

- [ ] **Step 1: Lint + format the modified surface**

```powershell
uv run ruff check app/services/intelligence/presets/marketing.py app/services/intelligence/marketing_stats.py app/services/intelligence/presets/__init__.py app/agents/tools/_marketing_confidence.py app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py app/agents/tools/social_analytics.py tests/unit/services/intelligence/test_presets_marketing.py tests/unit/services/intelligence/test_marketing_stats.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
uv run ruff format app/services/intelligence/presets/marketing.py app/services/intelligence/marketing_stats.py app/services/intelligence/presets/__init__.py app/agents/tools/_marketing_confidence.py app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py app/agents/tools/social_analytics.py tests/unit/services/intelligence/test_presets_marketing.py tests/unit/services/intelligence/test_marketing_stats.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py --check
```

Fix in place. Commit any style-only fixes as:

```bash
git add -u
git commit -m "style(117-01): ruff lint + format for plan 117-01 surface"
```

- [ ] **Step 2: Type check the new modules**

```powershell
uv run ty check app/services/intelligence/presets/marketing.py app/services/intelligence/marketing_stats.py app/agents/tools/_marketing_confidence.py
```

Resolve any `ty` errors; commit fixes.

- [ ] **Step 3: Phase 117-01 acceptance — cross-check**

| 117-01 acceptance line | Verified by |
|---|---|
| `marketing_confidence` preset shipped | Task 4 |
| Weights match spec (0.35 / 0.30 / 0.20 / 0.15) | Task 4 Step 1 (`test_marketing_confidence_weighted_average_holds`) |
| Helper module shipped (significance + completeness + coverage + recency) | Task 3 |
| Self-improvement engine audit committed BEFORE code change | Task 2 |
| `summarize_campaign_performance` carries `confidence` + `band` | Task 5 |
| `get_cross_channel_attribution`, `get_budget_recommendation`, `get_social_analytics`, `get_all_platform_analytics` carry `confidence` + `band` | Task 6 |
| Additive-only — existing tests pass | Task 6 Step 5 |
| Lint + format + types clean | Task 7 Steps 1-2 |

- [ ] **Step 4: Plan 117-01 complete. Hand off to 117-02 (multi-platform cache).**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `presets/marketing.py` + `MARKETING_WEIGHTS` | Task 4 |
| Marketing Agent statistical wiring | Tasks 3, 5, 6 |
| Self-improvement engine audit (Decision #8) | Tasks 1, 2 |
| `attribution_completeness` (0.35) input definition | Task 3 |
| `statistical_significance` (0.30) input definition | Task 3 |
| `audience_coverage` (0.20) input definition | Task 3 |
| `recency` (0.15) input definition | Task 3 |
| Every Marketing output carries confidence + band | Tasks 5, 6 |
| No regression in existing Marketing tests | Task 6 Step 5 |
| Lint clean | Task 7 |

All spec lines covered.
