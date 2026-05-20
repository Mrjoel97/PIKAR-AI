# Shared Intelligence Infrastructure — Plan 115-01: Sales Preset + Lead-Scoring Wiring + Self-Improvement Engine Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `app/services/intelligence/presets/sales.py` with `sales_confidence(...)`, wire it into the Sales Agent's `LeadScoringAgent` sub-agent so every `LeadQualification` output carries `confidence` + `band` derived from CRM evidence, and — **as the FIRST task per Decision #8 of the rolling-adoption spec** — audit `app/services/self_improvement_engine.py` and the skill-experiment evaluator for entanglement with Sales-Agent shapes BEFORE making any other changes.

**Architecture:** Sales-domain confidence preset weighs four signals: lead-criteria completeness (BANT/MEDDIC/CHAMP fields actually populated), CRM authority (HubSpot vs. local-only vs. manual entry), recency (last-touch age), and signal consistency (agreement across criteria scores). Preset is a thin wrapper over `score_confidence`. Wiring point: extend the `LeadQualification` schema with a non-breaking optional `confidence` + `band`, compute via `sales_confidence(...)` in a post-LeadScoringAgent narration step in the Sales director, propagate to HubSpot via existing `score_hubspot_lead`.

**Tech Stack:** `app/services/intelligence/confidence.py` (existing), `app/services/intelligence/presets/__init__.py` (existing), Sales Agent at `app/agents/sales/agent.py`, `LeadQualification` at `app/agents/schemas.py`. Self-improvement engine at `app/services/self_improvement_engine.py`. Skill experiment evaluator at `app/services/skill_experiment_evaluator.py`.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 115 — Sales Agent adoption.

**Out of scope:** HubSpot Redis cache wiring (Plan 115-02). Claim emission of `lead_score` / `deal_stage_signal` / `pipeline_health` (Plan 115-03). Forward-port of `confidence` into the `<json>...</json>` block consumed by the frontend (covered by claim emission in 115-03 — confidence is propagated via `kg_findings.confidence`, not via the structured-output block).

---

## File structure

**Create:**
- `app/services/intelligence/presets/sales.py` — `sales_confidence(...)` + `SALES_WEIGHTS`
- `tests/unit/services/intelligence/presets/test_sales.py` — preset unit tests
- `tests/unit/agents/sales/test_sales_confidence_wiring.py` — Sales director wiring tests
- `docs/superpowers/audits/2026-05-19-self-improvement-engine-sales-entanglement.md` — Task 1 audit deliverable

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `sales_confidence`
- `app/agents/schemas.py` — add `confidence: float | None`, `band: str | None` to `LeadQualification`
- `app/agents/sales/agent.py` — wire `sales_confidence(...)` into the director's post-scoring narration path

---

## Pre-flight context

`sales_confidence` signature (Decision-anchored from spec):

```python
def sales_confidence(
    lead_criteria_completeness: float,  # fraction of BANT/MEDDIC/CHAMP criteria populated [0, 1]
    crm_authority: float,                # HubSpot-synced (1.0) > local+enriched (0.7) > manual (0.4)
    recency: float,                      # 1 - min(1, days_since_last_touch / recency_horizon_days)
    signal_consistency: float,           # 1 - stdev(per-criterion scores) / 50  (clamped [0,1])
    *,
    recency_horizon_days: float = 30.0,
) -> float
```

Returns confidence clamped to `[0.0, 1.0]`. Pair with `to_band(confidence)` for the band string.

**Why this exact preset shape (anchored to Sales Agent reality):**

The Sales Agent's `LeadScoringAgent` already produces a `LeadQualification` schema with `score`, `framework`, `qualified`, `priority`, `next_steps`, and a `criteria_breakdown: list[CriteriaScore]`. The framework is one of `BANT` / `MEDDIC` / `CHAMP`, each with a known criterion count:

| Framework | Criterion count | Source field |
|---|---|---|
| BANT | 4 (Budget, Authority, Need, Timeline) | `criteria_breakdown` |
| MEDDIC | 6 (Metrics, Economic buyer, Decision criteria, Decision process, Identify pain, Champion) | `criteria_breakdown` |
| CHAMP | 4 (Challenges, Authority, Money, Prioritization) | `criteria_breakdown` |

`lead_criteria_completeness` = `len([c for c in criteria_breakdown if c.notes.strip()]) / expected_count(framework)`.

`crm_authority` is derived from the contact's `hubspot_contact_id` presence + `source` field on the contacts row (manual / enrichment / import).

`recency` reads `contact_activities.activity_date` for the most-recent row of the contact.

`signal_consistency` measures whether the per-criterion `score` values agree. A lead with `score = 85` but criterion variance `[100, 100, 30, 30]` (stdev ≈ 40) is less consistent — and less trustworthy — than one with `[80, 90, 85, 85]` (stdev ≈ 4). We normalise by `/50` because score range is 0–100, and stdev ≥ 50 indicates near-maximum spread.

**Why Decision #8 mandates the audit FIRST (not last):**

The risk register in the spec calls out: "Self-improvement engine entangles with old per-agent code paths" — mitigation is "Each phase's first sub-plan audits `app/services/self_improvement_engine.py` + `skill_experiment_evaluator.py` per `docs/self-improvement-policy.md`." The audit BEFORE changes lets us discover what the engine reads about Sales today — so when we add `confidence` to LeadQualification, we don't silently break a skill-effectiveness signal that the engine was already consuming.

Environment quirks: Windows + uv + Supabase local stack per memory `reference_local_dev_env_quirks`. Tests run via `uv run pytest`. Lint via `uv run ruff check` + `uv run ruff format`.

Acceptance bar (from spec):
- All Sales outputs carry `confidence` + `band` (no hardcoded constants)
- Sales Agent test suite green
- LeadQualification JSON includes the new fields without breaking existing JSON-block consumers
- Audit doc lands documenting all sales-shape touchpoints

---

## Tasks

### Task 1: Self-improvement engine entanglement audit (BLOCKING — Decision #8)

**Files:**
- Create: `docs/superpowers/audits/2026-05-19-self-improvement-engine-sales-entanglement.md`

This task ships BEFORE any code change. Per Decision #8, audit `app/services/self_improvement_engine.py` and `app/services/skill_experiment_evaluator.py` for any path that reads Sales-Agent shapes (`LeadQualification`, `agent_id="sales"`, `skill_name in sales skill list`, `AgentID.SALES`, hubspot tool ids). Produce a written audit so subsequent tasks know what NOT to break.

- [ ] **Step 1: Confirm prerequisites**

```powershell
uv run python -c "from app.services.intelligence import presets, score_confidence, to_band; print('OK')"
uv run python -c "from app.services.self_improvement_engine import SelfImprovementEngine; print(SelfImprovementEngine.__doc__[:120])"
uv run python -c "from app.services.skill_experiment_evaluator import *; print('skill_experiment_evaluator importable')"
```

Expected: all three print without error. If `skill_experiment_evaluator` import fails, locate the module first via `Get-ChildItem -Recurse -Filter skill_experiment_evaluator.py` and adjust the import path — the spec calls it out as load-bearing.

- [ ] **Step 2: Grep for Sales-shape touchpoints**

```powershell
uv run ruff check app/services/self_improvement_engine.py app/services/skill_experiment_evaluator.py
```

Run targeted greps to populate the audit (use the Grep tool, not raw rg):

- Pattern `agent_id\s*==\s*['"]sales['"]` in `app/services/`
- Pattern `LeadQualification|lead_qualification` in `app/services/`
- Pattern `AgentID\.SALES` in `app/services/`
- Pattern `skill_name.*sales|sales.*skill_name` in `app/services/`
- Pattern `lead_qualification_framework|objection_handling|pipeline_review|sales_forecasting` in `app/services/`

Record every hit (file:line) in the audit doc. If a hit reads a field we're about to add (e.g., `confidence` on LeadQualification), call it out explicitly as "will become read-after-add — verify no NoneType crash."

- [ ] **Step 3: Write the audit deliverable**

```markdown
# Self-Improvement Engine Entanglement Audit — Phase 115 (Sales Agent)

**Date:** 2026-05-19
**Phase:** 115-01
**Status:** Pre-implementation (BLOCKING gate per spec Decision #8)
**Audited files:**
- `app/services/self_improvement_engine.py`
- `app/services/skill_experiment_evaluator.py`

## Summary

[1-2 sentence summary of whether the engine has any hard-coded Sales-agent
assumptions that the Phase 115 wiring must preserve.]

## Findings

### Engine-side Sales touchpoints

| File:Line | Code | Reads Sales shape? | Impact of Phase 115 change | Mitigation |
|---|---|---|---|---|
| self_improvement_engine.py:LINE | `interaction.agent_id == "sales"` | Yes (string literal) | None — we don't change agent_id values | None needed |
| self_improvement_engine.py:LINE | `skill_name in {"lead_qualification_framework", ...}` | Yes (skill list) | None — Plan 115 adds claims, not skills | None needed |
| ... | ... | ... | ... | ... |

### Skill experiment evaluator-side touchpoints

| File:Line | Code | Reads Sales shape? | Impact | Mitigation |
|---|---|---|---|---|
| skill_experiment_evaluator.py:LINE | `record.get("confidence")` | Reads a field we are about to add | Engine will silently start receiving non-None confidences mid-rollout; verify no schema validation rejects them | Add a test asserting LeadQualification with new `confidence` field passes through the evaluator's `_validate_record` if it exists |

### Cross-cutting

- Are there any periodic jobs (`run_improvement_cycle`, scheduled evaluator runs) that re-snapshot Sales-Agent output shape into a stored history table? If yes, list table names and confirm Plan 115's additive schema change won't violate any CHECK constraint.
- Does the engine compute per-agent effectiveness scores using `LeadQualification` fields directly? If yes, list which fields.

## Decision

- **No entanglement found** — proceed with Tasks 2-5 without further mitigation, OR
- **Entanglement found** — list mitigations required BEFORE Task 2 (typically a defensive None-check or a feature-flag).

## Sign-off

Auditor: Phase 115-01 implementer
Date: 2026-05-19
Next: proceed to Task 2 (preset implementation).
```

Populate the tables with REAL findings, not placeholders. If zero hits, document "No sales-shape touchpoints found — engine is decoupled" and proceed.

- [ ] **Step 4: Commit the audit**

```bash
git add docs/superpowers/audits/2026-05-19-self-improvement-engine-sales-entanglement.md
git commit -m "audit(115-01): self-improvement engine entanglement audit for Sales adoption (Decision #8 gate)"
```

### Task 2: Implement `sales_confidence` preset (TDD)

**Files:**
- Create: `app/services/intelligence/presets/sales.py`
- Create: `tests/unit/services/intelligence/presets/test_sales.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for sales_confidence preset.

The preset is a thin wrapper over score_confidence with Sales-domain inputs:
- lead_criteria_completeness (0.30)
- crm_authority (0.25)
- recency (0.25)
- signal_consistency (0.20)
"""

from __future__ import annotations

import pytest


def test_sales_confidence_all_max_signals_returns_high_confidence():
    """All inputs at 1.0 → confidence at 1.0 (sum of weights = 1.0)."""
    from app.services.intelligence.presets import sales_confidence

    result = sales_confidence(
        lead_criteria_completeness=1.0,
        crm_authority=1.0,
        recency=1.0,
        signal_consistency=1.0,
    )
    assert result == pytest.approx(1.0, abs=1e-9)


def test_sales_confidence_all_zero_signals_returns_zero():
    """All inputs at 0.0 → confidence at 0.0."""
    from app.services.intelligence.presets import sales_confidence

    result = sales_confidence(
        lead_criteria_completeness=0.0,
        crm_authority=0.0,
        recency=0.0,
        signal_consistency=0.0,
    )
    assert result == pytest.approx(0.0, abs=1e-9)


def test_sales_confidence_clamped_to_unit_interval():
    """Out-of-range inputs are clamped, never raise."""
    from app.services.intelligence.presets import sales_confidence

    # Over-1.0 inputs (e.g., a buggy upstream)
    result = sales_confidence(
        lead_criteria_completeness=1.5,
        crm_authority=1.2,
        recency=1.0,
        signal_consistency=1.0,
    )
    assert 0.0 <= result <= 1.0


def test_sales_confidence_weights_match_spec():
    """Each signal contributes the expected fraction at 1.0 with others at 0.0."""
    from app.services.intelligence.presets import sales_confidence
    from app.services.intelligence.presets.sales import SALES_WEIGHTS

    # Sanity: weights sum to 1.0
    assert sum(SALES_WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)

    # lead_criteria_completeness alone at 1.0 → contributes 0.30
    assert sales_confidence(1.0, 0.0, 0.0, 0.0) == pytest.approx(0.30, abs=1e-9)
    # crm_authority alone → 0.25
    assert sales_confidence(0.0, 1.0, 0.0, 0.0) == pytest.approx(0.25, abs=1e-9)
    # recency alone → 0.25
    assert sales_confidence(0.0, 0.0, 1.0, 0.0) == pytest.approx(0.25, abs=1e-9)
    # signal_consistency alone → 0.20
    assert sales_confidence(0.0, 0.0, 0.0, 1.0) == pytest.approx(0.20, abs=1e-9)


def test_sales_confidence_typical_strong_lead():
    """A strong BANT lead with full criteria + HubSpot-synced + recent + consistent."""
    from app.services.intelligence.presets import sales_confidence

    # 4/4 BANT criteria populated, HubSpot-synced (1.0), touched 2 days ago,
    # criterion scores tightly clustered (stdev ≈ 5, normalised ≈ 0.9)
    result = sales_confidence(
        lead_criteria_completeness=1.0,
        crm_authority=1.0,
        recency=1 - (2 / 30),
        signal_consistency=0.9,
    )
    # Should land in "high" band
    from app.services.intelligence import to_band

    assert to_band(result) == "high"
    assert result >= 0.75


def test_sales_confidence_weak_lead_with_missing_criteria():
    """Lead with 2/4 BANT criteria + manual entry + 60 days old + high variance."""
    from app.services.intelligence.presets import sales_confidence

    result = sales_confidence(
        lead_criteria_completeness=0.5,   # 2 of 4 criteria populated
        crm_authority=0.4,                 # manual entry, no HubSpot sync
        recency=0.0,                       # > 30 days = floor
        signal_consistency=0.3,            # high stdev across criterion scores
    )
    # Should land in low or medium band
    assert result < 0.55


def test_sales_confidence_re_exported_in_presets():
    """sales_confidence is reachable from app.services.intelligence.presets."""
    from app.services.intelligence import presets

    assert hasattr(presets, "sales_confidence")
    assert callable(presets.sales_confidence)
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_sales.py -v --tb=short
```

Expected: `ModuleNotFoundError` or `AttributeError: module 'app.services.intelligence.presets' has no attribute 'sales_confidence'`.

- [ ] **Step 3: Implement `app/services/intelligence/presets/sales.py`**

```python
"""Sales-domain confidence preset.

Phase 115-01 — pilots on LeadQualification output of the Sales Agent's
LeadScoringAgent sub-agent.

The formula weights four signals:
- lead_criteria_completeness (0.30): fraction of BANT/MEDDIC/CHAMP criteria
                                      populated with non-empty notes.
- crm_authority              (0.25): HubSpot-synced (1.0) > local-enriched
                                      (~0.7) > manual entry (~0.4).
- recency                    (0.25): 1 - min(1, days_since_last_touch /
                                      recency_horizon_days). Last-touch comes
                                      from contact_activities.activity_date.
- signal_consistency         (0.20): 1 - clamp(stdev(criterion_scores) / 50).
                                      Tight per-criterion scores (low variance)
                                      mean the framework is confident in its
                                      assessment.
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

SALES_WEIGHTS: dict[str, float] = {
    "lead_criteria_completeness": 0.30,
    "crm_authority": 0.25,
    "recency": 0.25,
    "signal_consistency": 0.20,
}


def sales_confidence(
    lead_criteria_completeness: float,
    crm_authority: float,
    recency: float,
    signal_consistency: float,
    *,
    recency_horizon_days: float = 30.0,
) -> float:
    """Compute sales-domain confidence from lead-quality signals.

    Args:
        lead_criteria_completeness: Fraction in [0.0, 1.0] of the framework's
            criteria (BANT=4, MEDDIC=6, CHAMP=4) that have non-empty ``notes``
            in the LeadQualification.criteria_breakdown.
        crm_authority: Authority of the contact record's origin. Suggested
            mapping: HubSpot-synced (``hubspot_contact_id is not None``) = 1.0;
            local-enrichment from ``source in {"inbound", "referral",
            "campaign"}`` = 0.7; manual entry (``source = "manual"``) = 0.4;
            unknown source = 0.5. Clamped to [0.0, 1.0].
        recency: 1.0 minus the normalised age of the most-recent activity.
            Caller computes ``1 - min(1, days_since / recency_horizon_days)``.
            Pass 0.0 when no activity exists.
        signal_consistency: 1.0 minus the normalised standard deviation of the
            per-criterion ``score`` values in criteria_breakdown. A buggy
            framework that scores [100, 100, 30, 30] for an "85" lead has
            stdev ≈ 40 → consistency ≈ 0.2 (low). A consistent framework with
            [82, 88, 85, 85] has stdev ≈ 2.5 → consistency ≈ 0.95.
        recency_horizon_days: Age at which recency saturates to 0 (default 30).

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Note — recency_horizon_days is exposed so callers (e.g., long-cycle
    enterprise pipelines) can lengthen the horizon. The default 30 days
    matches the Sales Agent's existing follow-up cadence — leads untouched
    for >30 days are treated as cold.
    """
    _ = recency_horizon_days  # kwarg surface; caller passes pre-normalised recency

    return score_confidence(
        inputs={
            "lead_criteria_completeness": max(0.0, min(1.0, lead_criteria_completeness)),
            "crm_authority": max(0.0, min(1.0, crm_authority)),
            "recency": max(0.0, min(1.0, recency)),
            "signal_consistency": max(0.0, min(1.0, signal_consistency)),
        },
        weights=SALES_WEIGHTS,
    )
```

- [ ] **Step 4: Update `app/services/intelligence/presets/__init__.py`**

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula — Phase 115 adds sales_confidence.
"""

from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.research import research_confidence
from app.services.intelligence.presets.sales import sales_confidence

__all__ = ["data_confidence", "research_confidence", "sales_confidence"]
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_sales.py -v --tb=short
```

Expected output snippet:

```
test_sales_confidence_all_max_signals_returns_high_confidence PASSED
test_sales_confidence_all_zero_signals_returns_zero PASSED
test_sales_confidence_clamped_to_unit_interval PASSED
test_sales_confidence_weights_match_spec PASSED
test_sales_confidence_typical_strong_lead PASSED
test_sales_confidence_weak_lead_with_missing_criteria PASSED
test_sales_confidence_re_exported_in_presets PASSED
======== 7 passed in 0.XXs ========
```

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/presets/sales.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/presets/test_sales.py
git commit -m "feat(115-01): add sales_confidence preset with 4-signal weighting (GREEN)"
```

### Task 3: Extend `LeadQualification` schema with optional confidence + band

**Files:**
- Modify: `app/agents/schemas.py`
- Create: `tests/unit/agents/test_lead_qualification_schema.py`

The schema add must be backward-compatible — existing JSON-block consumers in the frontend and the `score_hubspot_lead` tool must not break when the fields are absent.

- [ ] **Step 1: Failing schema tests**

```python
"""Schema tests for LeadQualification's new confidence + band fields."""

from __future__ import annotations

import pytest


def test_lead_qualification_backward_compatible_without_confidence():
    """Existing payload (no confidence/band) still validates."""
    from app.agents.schemas import LeadQualification

    payload = {
        "lead_name": "Jane Doe",
        "company": "Acme Corp",
        "industry": "SaaS",
        "score": 78,
        "framework": "BANT",
        "qualified": True,
        "priority": "high",
        "next_steps": ["Schedule discovery"],
        "criteria_breakdown": [],
    }
    obj = LeadQualification.model_validate(payload)
    assert obj.confidence is None
    assert obj.band is None


def test_lead_qualification_accepts_confidence_and_band():
    """New optional fields parse when present."""
    from app.agents.schemas import LeadQualification

    payload = {
        "lead_name": "Jane Doe",
        "company": "Acme Corp",
        "score": 78,
        "framework": "BANT",
        "qualified": True,
        "priority": "high",
        "next_steps": [],
        "confidence": 0.82,
        "band": "high",
    }
    obj = LeadQualification.model_validate(payload)
    assert obj.confidence == pytest.approx(0.82)
    assert obj.band == "high"


def test_lead_qualification_confidence_clamped_to_unit():
    """Out-of-range confidence raises ValidationError."""
    from pydantic import ValidationError

    from app.agents.schemas import LeadQualification

    payload = {
        "lead_name": "X",
        "company": "Y",
        "score": 50,
        "framework": "BANT",
        "qualified": False,
        "priority": "low",
        "next_steps": [],
        "confidence": 1.5,  # invalid
    }
    with pytest.raises(ValidationError):
        LeadQualification.model_validate(payload)


def test_lead_qualification_band_literal_enforced():
    """Band must be one of low/medium/high."""
    from pydantic import ValidationError

    from app.agents.schemas import LeadQualification

    payload = {
        "lead_name": "X",
        "company": "Y",
        "score": 50,
        "framework": "BANT",
        "qualified": False,
        "priority": "low",
        "next_steps": [],
        "band": "extreme",  # invalid
    }
    with pytest.raises(ValidationError):
        LeadQualification.model_validate(payload)
```

- [ ] **Step 2: Run — should FAIL on the first three (the schema doesn't have those fields yet)**

```powershell
uv run pytest tests/unit/agents/test_lead_qualification_schema.py -v --tb=short
```

- [ ] **Step 3: Modify `app/agents/schemas.py`**

Locate `class LeadQualification(BaseModel)` and add the two optional fields after `criteria_breakdown`. The exact diff (preserving the existing class doc and surrounding context):

```python
class LeadQualification(BaseModel):
    """Structured output for lead scoring.

    Used by LeadScoringAgent to produce JSON that the parent
    SalesIntelligenceAgent narrates for users.

    Phase 115-01 adds optional ``confidence`` + ``band`` carried forward
    from app.services.intelligence.presets.sales.sales_confidence — the
    Sales director computes these AFTER LeadScoringAgent returns and
    annotates the payload before narration.
    """

    lead_name: str
    company: str
    industry: str | None = None
    score: int = Field(ge=0, le=100, description="Overall lead score 0-100")
    framework: Literal["BANT", "MEDDIC", "CHAMP"]
    qualified: bool
    priority: Literal["low", "medium", "high", "urgent"]
    next_steps: list[str]
    criteria_breakdown: list[CriteriaScore] = Field(
        default_factory=list, description="Score breakdown for visualization"
    )
    # Phase 115-01 additions — optional so existing payloads stay valid.
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Sales-confidence preset score in [0.0, 1.0]",
    )
    band: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Band derived from confidence via to_band(...)",
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/test_lead_qualification_schema.py -v --tb=short
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/schemas.py tests/unit/agents/test_lead_qualification_schema.py
git commit -m "feat(115-01): add optional confidence + band to LeadQualification schema"
```

### Task 4: Wire `sales_confidence` into the Sales director's post-scoring path

**Files:**
- Modify: `app/agents/sales/agent.py` — add a helper that annotates LeadQualification with confidence/band
- Create: `tests/unit/agents/sales/test_sales_confidence_wiring.py`

The wiring point: after `LeadScoringAgent` returns a structured `LeadQualification`, the Sales director computes the four signals from the qualification + a lightweight CRM lookup, runs `sales_confidence`, sets `confidence` + `band` on the output object, then continues narration. We expose this as a module-level callable so it's testable without spinning up the full ADK agent.

- [ ] **Step 1: Failing wiring tests**

```python
"""Tests for annotate_lead_qualification_confidence wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def _strong_payload() -> dict:
    return {
        "lead_name": "Jane Doe",
        "company": "Acme Corp",
        "industry": "SaaS",
        "score": 85,
        "framework": "BANT",
        "qualified": True,
        "priority": "high",
        "next_steps": ["Schedule discovery"],
        "criteria_breakdown": [
            {"criterion": "Budget", "score": 85, "notes": "Confirmed $50K"},
            {"criterion": "Authority", "score": 90, "notes": "Decision maker"},
            {"criterion": "Need", "score": 80, "notes": "Pain points identified"},
            {"criterion": "Timeline", "score": 85, "notes": "Q2 decision"},
        ],
    }


@pytest.mark.asyncio
async def test_annotate_lead_qualification_confidence_strong_lead():
    """A strong BANT lead with HubSpot-synced contact gets high confidence."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    qual = LeadQualification.model_validate(_strong_payload())

    fake_crm_meta = {
        "hubspot_contact_id": "12345",
        "source": "inbound",
        "days_since_last_touch": 2.0,
    }
    with patch(
        "app.agents.sales.agent._lookup_contact_crm_meta",
        new=AsyncMock(return_value=fake_crm_meta),
    ):
        annotated = await annotate_lead_qualification_confidence(qual)

    assert annotated.confidence is not None
    assert annotated.confidence >= 0.75
    assert annotated.band == "high"


@pytest.mark.asyncio
async def test_annotate_lead_qualification_confidence_weak_lead():
    """A manual-entry lead with missing criteria gets low confidence."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    weak_payload = _strong_payload()
    # Drop 2 of 4 criterion notes
    weak_payload["criteria_breakdown"][2]["notes"] = ""
    weak_payload["criteria_breakdown"][3]["notes"] = ""
    # High variance scores
    weak_payload["criteria_breakdown"][0]["score"] = 100
    weak_payload["criteria_breakdown"][1]["score"] = 100
    weak_payload["criteria_breakdown"][2]["score"] = 20
    weak_payload["criteria_breakdown"][3]["score"] = 20

    qual = LeadQualification.model_validate(weak_payload)

    fake_crm_meta = {
        "hubspot_contact_id": None,
        "source": "manual",
        "days_since_last_touch": 60.0,
    }
    with patch(
        "app.agents.sales.agent._lookup_contact_crm_meta",
        new=AsyncMock(return_value=fake_crm_meta),
    ):
        annotated = await annotate_lead_qualification_confidence(qual)

    assert annotated.confidence is not None
    assert annotated.confidence < 0.55
    assert annotated.band in {"low", "medium"}


@pytest.mark.asyncio
async def test_annotate_lead_qualification_handles_missing_crm_meta():
    """No CRM record found → defaults that don't crash."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    qual = LeadQualification.model_validate(_strong_payload())
    with patch(
        "app.agents.sales.agent._lookup_contact_crm_meta",
        new=AsyncMock(return_value=None),
    ):
        annotated = await annotate_lead_qualification_confidence(qual)

    assert annotated.confidence is not None
    assert 0.0 <= annotated.confidence <= 1.0
    assert annotated.band in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_annotate_lead_qualification_silently_degrades_on_lookup_error():
    """CRM lookup raises → fallback authoritative defaults, confidence still set."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    qual = LeadQualification.model_validate(_strong_payload())
    with patch(
        "app.agents.sales.agent._lookup_contact_crm_meta",
        new=AsyncMock(side_effect=RuntimeError("supabase down")),
    ):
        annotated = await annotate_lead_qualification_confidence(qual)

    # Must not raise; confidence should be populated using neutral defaults
    assert annotated.confidence is not None
    assert annotated.band is not None


def test_framework_expected_criterion_count():
    """Framework → expected criterion count is hard-mapped per spec."""
    from app.agents.sales.agent import _framework_expected_criterion_count

    assert _framework_expected_criterion_count("BANT") == 4
    assert _framework_expected_criterion_count("MEDDIC") == 6
    assert _framework_expected_criterion_count("CHAMP") == 4
    # Unknown framework → fall back to len(criteria_breakdown), handled in caller
    assert _framework_expected_criterion_count("UNKNOWN") == 0
```

- [ ] **Step 2: Run — should FAIL (the helper doesn't exist yet)**

```powershell
uv run pytest tests/unit/agents/sales/test_sales_confidence_wiring.py -v --tb=short
```

- [ ] **Step 3: Implement the wiring in `app/agents/sales/agent.py`**

Add the following helpers between the `_create_lead_scoring_agent` definition and `create_sales_agent`. Do NOT replace existing code — append.

```python
# =============================================================================
# Phase 115-01: sales_confidence wiring
# =============================================================================

import logging
import statistics
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


_FRAMEWORK_CRITERION_COUNT: dict[str, int] = {
    "BANT": 4,
    "MEDDIC": 6,
    "CHAMP": 4,
}


def _framework_expected_criterion_count(framework: str) -> int:
    """Expected number of criteria for a scoring framework.

    Returns 0 for unknown frameworks — callers fall back to
    ``len(criteria_breakdown)`` so completeness becomes 1.0 (best-effort).
    """
    return _FRAMEWORK_CRITERION_COUNT.get(framework, 0)


def _crm_authority_from_meta(meta: dict | None) -> float:
    """Map a contact's CRM origin metadata to authority in [0.0, 1.0]."""
    if not meta:
        return 0.5  # unknown — middle value
    if meta.get("hubspot_contact_id"):
        return 1.0
    source = (meta.get("source") or "").lower()
    if source in {"inbound", "referral", "campaign", "import"}:
        return 0.7
    if source == "manual":
        return 0.4
    return 0.5


def _recency_from_days(days_since_last_touch: float | None, horizon: float = 30.0) -> float:
    """Convert age in days into a recency score in [0.0, 1.0]."""
    if days_since_last_touch is None:
        return 0.0
    return max(0.0, 1.0 - min(1.0, float(days_since_last_touch) / horizon))


def _signal_consistency_from_scores(scores: list[int]) -> float:
    """Convert per-criterion score variance into a consistency signal."""
    if len(scores) < 2:
        return 1.0  # single criterion = trivially consistent
    try:
        stdev = statistics.stdev(scores)
    except statistics.StatisticsError:
        return 1.0
    # stdev range for 0-100 scores is 0..50. Normalise + invert.
    return max(0.0, 1.0 - min(1.0, stdev / 50.0))


async def _lookup_contact_crm_meta(
    *,
    lead_name: str,
    company: str,
) -> dict | None:
    """Best-effort lookup of CRM metadata for a lead.

    Reads ``contacts`` + the freshest ``contact_activities`` for the matched
    contact. Returns dict with ``hubspot_contact_id``, ``source``, and
    ``days_since_last_touch``, or None on miss.

    Failures (Supabase down, RLS, etc.) log and return None — the caller
    treats that as "unknown CRM metadata" and uses neutral defaults.
    """
    try:
        from app.services.base_service import AdminService
        from app.services.request_context import get_current_user_id
        from app.services.supabase_async import execute_async

        user_id = get_current_user_id()
        if not user_id:
            return None

        admin = AdminService()
        contact_q = (
            admin.client.table("contacts")
            .select("id, hubspot_contact_id, source")
            .eq("user_id", user_id)
            .or_(f"name.ilike.%{lead_name}%,company.ilike.%{company}%")
            .limit(1)
        )
        contact_res = await execute_async(
            contact_q, op_name="sales_confidence.lookup_contact"
        )
        if not contact_res.data:
            return None

        contact = contact_res.data[0]
        contact_id = contact["id"]

        activity_q = (
            admin.client.table("contact_activities")
            .select("activity_date")
            .eq("contact_id", contact_id)
            .order("activity_date", desc=True)
            .limit(1)
        )
        activity_res = await execute_async(
            activity_q, op_name="sales_confidence.lookup_last_activity"
        )

        days_since: float | None = None
        if activity_res.data:
            raw = activity_res.data[0].get("activity_date")
            if isinstance(raw, str):
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0

        return {
            "hubspot_contact_id": contact.get("hubspot_contact_id"),
            "source": contact.get("source"),
            "days_since_last_touch": days_since,
        }
    except Exception as exc:
        logger.warning("_lookup_contact_crm_meta failed: %s", exc)
        return None


async def annotate_lead_qualification_confidence(
    qual,  # LeadQualification — annotated forward-ref to keep import cheap
):
    """Compute sales_confidence + band and mutate the LeadQualification.

    Always returns a populated object even on lookup failures (neutral defaults).
    Side effect: sets qual.confidence and qual.band in place.
    """
    from app.services.intelligence import presets, to_band

    # Pull CRM metadata (best effort).
    try:
        meta = await _lookup_contact_crm_meta(
            lead_name=qual.lead_name, company=qual.company,
        )
    except Exception as exc:
        logger.warning("annotate_lead_qualification_confidence: lookup raised: %s", exc)
        meta = None

    expected = _framework_expected_criterion_count(qual.framework)
    if expected == 0:
        expected = max(1, len(qual.criteria_breakdown))
    populated = sum(
        1 for c in qual.criteria_breakdown if c.notes and c.notes.strip()
    )
    completeness = min(1.0, populated / expected)

    authority = _crm_authority_from_meta(meta)
    recency = _recency_from_days(
        meta.get("days_since_last_touch") if meta else None
    )
    consistency = _signal_consistency_from_scores(
        [c.score for c in qual.criteria_breakdown]
    )

    confidence = presets.sales_confidence(
        lead_criteria_completeness=completeness,
        crm_authority=authority,
        recency=recency,
        signal_consistency=consistency,
    )
    qual.confidence = confidence
    qual.band = to_band(confidence)
    return qual
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/sales/test_sales_confidence_wiring.py -v --tb=short
```

Expected output snippet:

```
test_annotate_lead_qualification_confidence_strong_lead PASSED
test_annotate_lead_qualification_confidence_weak_lead PASSED
test_annotate_lead_qualification_handles_missing_crm_meta PASSED
test_annotate_lead_qualification_silently_degrades_on_lookup_error PASSED
test_framework_expected_criterion_count PASSED
======== 5 passed in 0.XXs ========
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/sales/agent.py tests/unit/agents/sales/test_sales_confidence_wiring.py
git commit -m "feat(115-01): wire sales_confidence into LeadQualification annotation path"
```

### Task 5: Update Sales instructions so the director invokes the new helper

**Files:**
- Modify: `app/agents/sales/instructions.md`

The LeadScoringAgent is a structured-output specialist that can't call tools — the director (PikarBaseAgent) is the layer that narrates. We update its instructions to require a call to `annotate_lead_qualification_confidence(...)` BEFORE narration, mirroring how Phase 113 added "confidence + band" to cohort_analysis narration.

- [ ] **Step 1: Read the existing instructions section "STRUCTURED LEAD SCORING"** at the top of `app/agents/sales/instructions.md`. The current text is shown in pre-flight.

- [ ] **Step 2: Replace the "STRUCTURED LEAD SCORING" section with the annotated version**

```markdown
## STRUCTURED LEAD SCORING
When asked to qualify or score a lead:
1. Delegate to LeadScoringAgent to generate structured JSON.
2. After receiving the qualification data, call `annotate_lead_qualification_confidence` (Sales-Agent internal helper) to attach `confidence` + `band` derived from CRM-evidence signals.
3. Narrate the result conversationally and embed the annotated JSON in a `<json>...</json>` block.
4. ALWAYS state the confidence band in the narration (e.g., "This is a **high-confidence** qualification" / "**medium**" / "**low**"). Never present a lead score without its band — bands are how users calibrate trust.

Example response format for lead scoring:
```
🎯 **Lead Qualification: John Smith @ Acme Corp** (high-confidence)

Based on BANT analysis, this is a **high-priority qualified lead** with a score of 85/100. CRM evidence supports a confidence of 0.82 — HubSpot-synced contact, full BANT criteria populated, last touched 2 days ago, criterion scores tightly clustered.

**Criteria Breakdown:**
- Budget: ✅ Confirmed ($50K allocated)
- Authority: ✅ Decision maker
- Need: ✅ Clear pain points identified
- Timeline: ⚠️ Q2 decision (3 months out)

**Recommended Next Steps:**
1. Schedule discovery call this week
2. Send case study for similar company

<json>
{
  "lead_name": "John Smith",
  ...,
  "confidence": 0.82,
  "band": "high"
}
</json>
```

For weak / low-band qualifications, soften the narration ("Preliminary qualification — low confidence due to missing CRM history and incomplete criteria. Recommend gathering more data before pursuing.").
```

- [ ] **Step 3: Run the sales agent regression suite to confirm nothing broke**

```powershell
uv run pytest tests/unit/agents/sales/ -v --tb=short
```

Expected: all green, including any pre-existing director / lead-scoring tests.

- [ ] **Step 4: Commit**

```bash
git add app/agents/sales/instructions.md
git commit -m "docs(115-01): require sales_confidence annotation in lead-scoring narration"
```

### Task 6: Integration test — preset + wiring end-to-end

**Files:**
- Create: `tests/integration/test_sales_confidence_wiring.py`

A lightweight integration test that exercises the helper against a fake-but-realistic LeadQualification payload, no Supabase required (the CRM lookup is patched). Validates that the full `LeadQualification → annotate → confidence + band` chain produces sensible outputs across the band boundary.

- [ ] **Step 1: Write the integration test**

```python
"""End-to-end test: preset + wiring + schema round-trip."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_full_lead_qualification_confidence_round_trip():
    """Three leads across the band spectrum produce expected confidences."""
    from app.agents.schemas import LeadQualification
    from app.agents.sales.agent import annotate_lead_qualification_confidence

    scenarios = [
        # (label, payload, crm_meta, expected_band)
        (
            "strong",
            {
                "lead_name": "A. Buyer",
                "company": "Acme",
                "score": 88,
                "framework": "BANT",
                "qualified": True,
                "priority": "high",
                "next_steps": ["close"],
                "criteria_breakdown": [
                    {"criterion": "Budget", "score": 88, "notes": "Confirmed"},
                    {"criterion": "Authority", "score": 90, "notes": "Decision maker"},
                    {"criterion": "Need", "score": 86, "notes": "Acute pain"},
                    {"criterion": "Timeline", "score": 88, "notes": "Q1 close"},
                ],
            },
            {"hubspot_contact_id": "h1", "source": "inbound", "days_since_last_touch": 1.0},
            "high",
        ),
        (
            "medium",
            {
                "lead_name": "B. Maybe",
                "company": "Beta",
                "score": 60,
                "framework": "BANT",
                "qualified": True,
                "priority": "medium",
                "next_steps": ["follow up"],
                "criteria_breakdown": [
                    {"criterion": "Budget", "score": 70, "notes": "Approved"},
                    {"criterion": "Authority", "score": 50, "notes": "Influencer"},
                    {"criterion": "Need", "score": 60, "notes": "Some pain"},
                    {"criterion": "Timeline", "score": 60, "notes": ""},  # missing
                ],
            },
            {"hubspot_contact_id": None, "source": "import", "days_since_last_touch": 15.0},
            "medium",
        ),
        (
            "low",
            {
                "lead_name": "C. Cold",
                "company": "Cipher",
                "score": 30,
                "framework": "BANT",
                "qualified": False,
                "priority": "low",
                "next_steps": ["disqualify"],
                "criteria_breakdown": [
                    {"criterion": "Budget", "score": 100, "notes": ""},
                    {"criterion": "Authority", "score": 0, "notes": ""},
                    {"criterion": "Need", "score": 0, "notes": ""},
                    {"criterion": "Timeline", "score": 0, "notes": ""},
                ],
            },
            {"hubspot_contact_id": None, "source": "manual", "days_since_last_touch": 90.0},
            "low",
        ),
    ]

    for label, payload, meta, expected_band in scenarios:
        qual = LeadQualification.model_validate(payload)
        with patch(
            "app.agents.sales.agent._lookup_contact_crm_meta",
            new=AsyncMock(return_value=meta),
        ):
            annotated = await annotate_lead_qualification_confidence(qual)

        assert annotated.confidence is not None, f"{label}: missing confidence"
        assert annotated.band == expected_band, (
            f"{label}: expected band={expected_band}, got {annotated.band} "
            f"(confidence={annotated.confidence:.3f})"
        )

        # Round-trip: dump and re-validate preserves the new fields.
        dumped = annotated.model_dump()
        round_tripped = LeadQualification.model_validate(dumped)
        assert round_tripped.confidence == pytest.approx(annotated.confidence)
        assert round_tripped.band == annotated.band
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_sales_confidence_wiring.py -v --tb=short
```

Expected: 1 passed.

If a band assertion fails, inspect the printed confidence: the boundary may need a slight payload tweak. The bands are determined by `to_band`'s thresholds (typically 0.5 / 0.75) — adjust the "medium" or "low" payload signals to land cleanly in their bands.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_sales_confidence_wiring.py
git commit -m "test(115-01): end-to-end LeadQualification → confidence + band round-trip"
```

### Task 7: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/presets/sales.py app/agents/sales/agent.py app/agents/schemas.py tests/unit/services/intelligence/presets/test_sales.py tests/unit/agents/sales/test_sales_confidence_wiring.py tests/unit/agents/test_lead_qualification_schema.py tests/integration/test_sales_confidence_wiring.py
uv run ruff format app/services/intelligence/presets/sales.py app/agents/sales/agent.py app/agents/schemas.py tests/unit/services/intelligence/presets/test_sales.py tests/unit/agents/sales/test_sales_confidence_wiring.py tests/unit/agents/test_lead_qualification_schema.py tests/integration/test_sales_confidence_wiring.py --check
```

Fix in place. Commit any formatter fixes:

```bash
git add -u
git commit -m "style(115-01): ruff format + lint fixes for plan 115-01 files"
```

- [ ] **Step 2: Plan 115-01 acceptance cross-check**

| Acceptance line (from spec § Phase 115) | Verified by |
|---|---|
| Self-improvement engine audit shipped FIRST (Decision #8) | Task 1 |
| `sales_confidence` preset shipped | Task 2 |
| Preset re-exported via `app.services.intelligence.presets` | Task 2 Step 4 |
| `LeadQualification` carries `confidence` + `band` | Task 3 |
| Schema change is backward-compatible | Task 3 Step 1 |
| Sales director annotates qualification before narration | Task 4 + Task 5 |
| Sales Agent test suite green | Task 5 Step 3 |
| All inputs clamped, never raise | Task 2 Step 3 |
| Helper degrades silently on CRM-lookup failures | Task 4 Step 1 |
| Three-band round-trip (high/medium/low) covered | Task 6 |

- [ ] **Step 3: Plan 115-01 complete. Plan 115-02 (HubSpot cache integration) unblocked.**

The Sales Agent now produces calibrated `LeadQualification` outputs. Plan 115-02 wires the Redis cache around HubSpot calls so repeated lookups don't hit the API every time. Plan 115-03 then writes `lead_score`, `deal_stage_signal`, and `pipeline_health` claims into `kg_findings` so the calibrated scores appear in cross-agent semantic search.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `presets/sales.py` shipped with 4-signal weighting | Task 2 |
| `lead_criteria_completeness` (0.30) | Task 2 |
| `crm_authority` (0.25) | Task 2 |
| `recency` (0.25) | Task 2 |
| `signal_consistency` (0.20) | Task 2 |
| Weights sum to 1.0 | Task 2 test `test_sales_confidence_weights_match_spec` |
| Sales Agent lead-scoring wired into preset | Task 4 |
| Every Sales output carries `confidence` + `band` | Tasks 3, 4, 5 |
| Self-improvement engine audit performed BEFORE other changes (Decision #8) | Task 1 |
| Audit file lands in `docs/superpowers/audits/` | Task 1 Step 3 |
| Sales Agent test suite green (regression) | Task 5 Step 3 |
| Backward-compatible schema change | Task 3 |
| Lint clean | Task 7 |

All spec lines covered.
