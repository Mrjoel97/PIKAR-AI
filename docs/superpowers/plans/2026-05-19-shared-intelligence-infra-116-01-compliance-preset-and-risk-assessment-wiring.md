# Shared Intelligence Infrastructure — Plan 116-01: Compliance preset, RiskAssessment wiring & self-improvement audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `app/services/intelligence/presets/compliance.py` with a `compliance_confidence(...)` formula, wire it through the Compliance Agent's `RiskReportAgent` sub-agent and `create_risk` / `update_risk` paths so every risk assessment carries `confidence` + `band` derived from the four named signals — and, as the **first** task of the Phase 116 rollout, audit `app/services/self_improvement_engine.py` + `app/services/skill_experiment_evaluator.py` per `docs/self-improvement-policy.md` so we know what Compliance-shaped state the engine binds to *before* we change Compliance.

**Architecture:** Per Decision #8 of the rolling-adoption design, the first sub-plan of every phase audits the self-improvement engine. Compliance is the third phase, so the abstraction has settled — the audit here is targeted (find Compliance-shaped state, confirm no entanglement broken by the preset/claims work) rather than open-ended. The preset itself is a thin wrapper around `score_confidence` matching the shape of `presets/data.py` and `presets/research.py`. Wiring touches three call sites: the `RiskReportAgent` JSON output (post-process to attach confidence + band before serialization), and the two service-layer mutations `ComplianceService.create_risk` / `update_risk` (compute confidence from the `severity` / `mitigation_plan` inputs).

**Tech Stack:** `app/services/intelligence/confidence.py` (existing — used as-is), `app/services/intelligence/presets/__init__.py` (extended re-export), `app/agents/schemas.py` (`RiskAssessment` Pydantic model extended with two optional fields), `app/agents/compliance/agent.py` + `app/services/compliance_service.py` (call sites), `app/services/self_improvement_engine.py` + `app/services/skill_experiment_evaluator.py` (read-only audit).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 116 — Compliance Agent adoption

**Out of scope:** Claim emission to `kg_findings` (covered in Plan 116-02). External-system cache integration (Compliance is internal-only — Decision #3, adaptive sub-plan template; no cache plan exists for Phase 116). Calibrating the four weights from telemetry (each preset ships with educated-guess weights; calibration is a separate phase per the spec's "Out of scope"). Editing the Compliance Agent's `instructions.md` voice (preserved verbatim — wiring is mechanical).

---

## File structure

**Create:**
- `app/services/intelligence/presets/compliance.py` — `compliance_confidence` + `COMPLIANCE_WEIGHTS`
- `tests/unit/services/intelligence/presets/test_compliance.py` — unit tests for the preset
- `tests/unit/services/intelligence/presets/__init__.py` — empty package marker if missing
- `tests/unit/agents/compliance/test_risk_assessment_confidence.py` — RiskAssessment wiring tests
- `.planning/phase-116/audit-self-improvement-2026-05-19.md` — audit report (Task 1 output)

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `compliance_confidence`
- `app/services/intelligence/__init__.py` — no changes required (presets surfaced via `presets` namespace)
- `app/agents/schemas.py` — add `confidence: float | None` + `band: Literal["low","medium","high"] | None` to `RiskAssessment`
- `app/agents/compliance/agent.py` — post-process RiskReportAgent JSON to attach confidence + band
- `app/services/compliance_service.py` — `create_risk` + `update_risk` compute and persist confidence + band

---

## Pre-flight context

### What "Compliance confidence" means

Per the spec, the four signals are:

```python
COMPLIANCE_WEIGHTS = {
    "regulation_authority":            0.40,
    "evidence_traceability":           0.30,
    "recency_vs_regulation_version":   0.20,
    "peer_review_signal":              0.10,
}
```

Signal definitions used throughout this plan:

| Signal | Range | Source in Compliance flow |
|---|---|---|
| `regulation_authority` | 0.0–1.0 | Statute/regulation > industry guidance > peer commentary > anecdote. Maps `RiskAssessment.category` and the presence of explicit regulation citations in `description` / `mitigation`. |
| `evidence_traceability` | 0.0–1.0 | Fraction of claims with explicit citations (audit logs, regulator URLs, internal policies). Maps to count and quality of `sources` later in Plan 116-02; for this plan we approximate from `mitigation_plan` length + presence of citation keywords. |
| `recency_vs_regulation_version` | 0.0–1.0 | How recent the underlying regulation version is vs. the assessment date. For 116-01 we use `data_age_days` (days since the underlying source was last refreshed). |
| `peer_review_signal` | 0.0–1.0 | Whether a second auditor / reviewer has validated. 0.0 = single-author, 1.0 = reviewed by ≥2 parties. |

These are intentionally normalized to [0, 1] *before* the weighted sum, mirroring `data_confidence`'s `sample_adequacy` / `completeness` pattern.

### Why a Pydantic field, not a sidecar dict

`RiskAssessment` is the structured-output schema for `RiskReportAgent` (an ADK sub-agent with `output_schema=RiskAssessment` set, which forbids callbacks). The cleanest way to surface confidence to downstream consumers (`/admin/compliance/*`, risk dashboards, future claim emission in Plan 116-02) is to extend the schema with two optional fields and back-fill them in the parent ComplianceRiskAgent's flow.

Why *optional*: historical risk rows in Supabase pre-date this plan and have no confidence column populated. Marking the new fields optional means we don't need a backfill migration — the post-processing path simply skips rows that have no confidence yet, and new writes populate them going forward.

### Self-improvement audit scope

`app/services/self_improvement_engine.py` runs daily via `POST /scheduled/self-improvement-cycle` (per `docs/runbooks/self-improvement-scheduler.md`). It evaluates skill effectiveness from `interaction_logs` and writes to `skill_scores`, `improvement_actions`, `coverage_gaps`. Per the rolling-adoption design Decision #8 and the risk register, it *may* bind to per-agent code paths that we're about to change. The audit's job is to:

1. Enumerate every reference to `compliance`, `legal`, `risk_assessment`, `RiskAssessment`, `RiskReportAgent`, `ComplianceService` (and aliases) in the two files.
2. Classify each reference: harmless string tag / structural assumption / behavioral coupling.
3. For any *behavioral* coupling (e.g., "engine expects RiskAssessment to be the canonical compliance output shape"), record what would break if we extended the schema.
4. Confirm the proposed changes (add two optional fields, attach confidence in agent post-processing, compute confidence in `create_risk` / `update_risk`) are compatible.

The audit is read-only; if entanglement is found, this plan PAUSES and the discovery is added as a new task before continuing.

Acceptance bar (per spec § Phase 116 ACCEPTANCE CRITERIA, addressed by this plan):
- Compliance Agent test suite green (verified Task 6)
- All Compliance outputs carry confidence + band — *risk-assessment outputs* covered here; claim-bearing outputs covered in Plan 116-02
- Self-improvement engine entanglement audit completed and recorded (Task 1)

Environment quirks: same as prior plans — `uv run` for everything, `psql` via docker exec for direct DB inspection, frontend env may point at prod (irrelevant for this plan since it's backend-only). RLS is on `compliance_risks`; service-role bypass is already in place via `AdminService` in `compliance_service.py`.

---

## Tasks

### Task 1: Pre-flight + self-improvement engine entanglement audit (BLOCKING)

**Files:**
- Create: `.planning/phase-116/audit-self-improvement-2026-05-19.md`

Per Decision #8 of the rolling-adoption design and the project's `docs/self-improvement-policy.md`, this audit MUST run before any other Phase 116 change. The audit is read-only.

- [ ] **Step 1: Confirm prerequisites are in place**

```powershell
uv run python -c "from app.services.intelligence import presets; print(dir(presets))"
uv run python -c "from app.services.intelligence.presets.data import data_confidence; print(data_confidence(100, 0.0, 0.0, 0.0))"
uv run python -c "from app.agents.schemas import RiskAssessment; print(RiskAssessment.model_fields.keys())"
```

Expected: the first prints `[..., 'data_confidence', 'research_confidence', ...]`. The second prints a float in `[0.0, 1.0]`. The third prints `dict_keys([..., 'risk_id', 'title', ..., 'status'])` without `confidence` or `band` (those are what this plan adds).

- [ ] **Step 2: Enumerate Compliance-shaped references in the engine**

```powershell
uv run python -m ruff check --quiet app/services/self_improvement_engine.py app/services/skill_experiment_evaluator.py
```

Then capture references with grep:

```powershell
Select-String -Path "app/services/self_improvement_engine.py","app/services/skill_experiment_evaluator.py" -Pattern "compliance|legal|risk_assessment|RiskAssessment|RiskReportAgent|ComplianceService" -SimpleMatch | Format-Table LineNumber,Filename,Line -AutoSize | Out-File -Encoding utf8 .planning/phase-116/_audit_grep.txt
Get-Content .planning/phase-116/_audit_grep.txt
```

Expected output: a small handful of references (Compliance is a downstream consumer of the skills registry, not an emitter of `interaction_logs` shapes the engine cares about). Document each. If the count is unexpectedly high (>10), pause and inspect — this likely indicates structural coupling that needs its own plan.

- [ ] **Step 3: Write the audit report**

Create `.planning/phase-116/audit-self-improvement-2026-05-19.md` with this structure:

```markdown
# Self-Improvement Engine — Compliance Adoption Audit
Date: 2026-05-19
Auditor: <git user>
Phase: 116 (Compliance Agent adoption)
Files audited:
- app/services/self_improvement_engine.py
- app/services/skill_experiment_evaluator.py

## References

| File:Line | Reference | Classification | Impact of Phase 116 changes |
|---|---|---|---|
| `self_improvement_engine.py:1587` | `"CMP": "compliance"` (AgentID alias mapping) | harmless string tag | None — we don't change AgentID. |
| ... | ... | ... | ... |

## Behavioral couplings
(None expected, but list any.)

## Conclusion
[ ] Phase 116 changes are SAFE to proceed.
[ ] Phase 116 needs additional plan task: ______
```

Fill the table from the grep output of Step 2. Each row gets a classification and an impact assessment. The known starting point: the AgentID alias `"CMP": "compliance"` at `self_improvement_engine.py:1587` is a string tag, harmless.

- [ ] **Step 4: Decide go/no-go**

If the conclusion is "SAFE to proceed", continue. If new entanglement was found (e.g., the engine reads `RiskAssessment` fields directly), pause and add the discovered work as a Task between Task 1 and Task 2.

- [ ] **Step 5: Commit the audit**

```bash
git add .planning/phase-116/audit-self-improvement-2026-05-19.md
git commit -m "docs(116-01): self-improvement engine audit — Compliance Phase 116 adoption"
```

### Task 2: Implement the `compliance_confidence` preset (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/presets/__init__.py` (if missing)
- Create: `tests/unit/services/intelligence/presets/test_compliance.py`
- Create: `app/services/intelligence/presets/compliance.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Confirm the test directory exists and is a package**

```powershell
if (-not (Test-Path "tests/unit/services/intelligence/presets")) {
    New-Item -ItemType Directory tests/unit/services/intelligence/presets
}
if (-not (Test-Path "tests/unit/services/intelligence/presets/__init__.py")) {
    New-Item -ItemType File tests/unit/services/intelligence/presets/__init__.py
}
```

- [ ] **Step 2: Write the failing unit test**

Create `tests/unit/services/intelligence/presets/test_compliance.py`:

```python
"""Unit tests for the compliance_confidence preset.

Validates:
- Returns a float clamped to [0.0, 1.0]
- Weights sum to 1.0 (regulation 0.40 + evidence 0.30 + recency 0.20 + peer 0.10)
- Each named signal contributes its weighted share
- Inverted recency: 0 days = 1.0, ≥ horizon = 0.0
- Property: monotonic in regulation_authority when other signals are fixed
"""

from __future__ import annotations

import pytest


def test_compliance_confidence_all_max_returns_one():
    """Maxed inputs → 1.0 (weighted sum saturates at clamp)."""
    from app.services.intelligence.presets.compliance import compliance_confidence

    score = compliance_confidence(
        regulation_authority=1.0,
        evidence_traceability=1.0,
        regulation_age_days=0.0,
        peer_review_signal=1.0,
    )
    assert score == pytest.approx(1.0)


def test_compliance_confidence_all_min_returns_zero():
    """Minimum inputs → 0.0."""
    from app.services.intelligence.presets.compliance import compliance_confidence

    score = compliance_confidence(
        regulation_authority=0.0,
        evidence_traceability=0.0,
        regulation_age_days=10_000.0,  # very old
        peer_review_signal=0.0,
    )
    assert score == pytest.approx(0.0)


def test_compliance_weights_sum_to_one():
    """The preset weights must sum to exactly 1.0."""
    from app.services.intelligence.presets.compliance import COMPLIANCE_WEIGHTS

    assert sum(COMPLIANCE_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(COMPLIANCE_WEIGHTS.keys()) == {
        "regulation_authority",
        "evidence_traceability",
        "recency_vs_regulation_version",
        "peer_review_signal",
    }


def test_compliance_confidence_monotonic_in_regulation_authority():
    """Holding other signals fixed, confidence rises with regulation_authority."""
    from app.services.intelligence.presets.compliance import compliance_confidence

    fixed = {
        "evidence_traceability": 0.5,
        "regulation_age_days": 90.0,
        "peer_review_signal": 0.5,
    }
    low = compliance_confidence(regulation_authority=0.2, **fixed)
    mid = compliance_confidence(regulation_authority=0.5, **fixed)
    high = compliance_confidence(regulation_authority=0.9, **fixed)
    assert low < mid < high


def test_compliance_confidence_recency_inversion():
    """0 days old → recency = 1.0; default horizon (365 days) → recency = 0.0."""
    from app.services.intelligence.presets.compliance import compliance_confidence

    # Only recency varies; other signals constant at 0.5.
    fixed = {
        "regulation_authority": 0.5,
        "evidence_traceability": 0.5,
        "peer_review_signal": 0.5,
    }
    fresh = compliance_confidence(regulation_age_days=0.0, **fixed)
    stale = compliance_confidence(regulation_age_days=365.0, **fixed)
    assert fresh > stale
    # Recency contributes weight 0.20: max delta between fresh and stale = 0.20.
    assert fresh - stale == pytest.approx(0.20)


def test_compliance_confidence_returns_band_classifiable():
    """Output is consumable by to_band — float in [0.0, 1.0]."""
    from app.services.intelligence.confidence import to_band
    from app.services.intelligence.presets.compliance import compliance_confidence

    s = compliance_confidence(
        regulation_authority=0.8,
        evidence_traceability=0.7,
        regulation_age_days=30.0,
        peer_review_signal=0.6,
    )
    assert 0.0 <= s <= 1.0
    assert to_band(s) in {"low", "medium", "high"}


def test_compliance_confidence_horizon_param_extends_freshness():
    """Caller-supplied horizon shifts where recency reaches 0.0."""
    from app.services.intelligence.presets.compliance import compliance_confidence

    fixed = {
        "regulation_authority": 0.5,
        "evidence_traceability": 0.5,
        "peer_review_signal": 0.5,
    }
    # With default horizon of 365 days, 730 days is well past stale.
    default_horizon = compliance_confidence(regulation_age_days=730.0, **fixed)
    # With horizon of 1825 days (5y), 730 days still has some recency credit.
    long_horizon = compliance_confidence(
        regulation_age_days=730.0, recency_horizon_days=1825.0, **fixed
    )
    assert long_horizon > default_horizon


def test_compliance_confidence_clamps_below_zero():
    """Negative inputs are clamped — never returns negative."""
    from app.services.intelligence.presets.compliance import compliance_confidence

    # Pass a contrived negative — implementation should clamp.
    score = compliance_confidence(
        regulation_authority=-0.5,
        evidence_traceability=0.0,
        regulation_age_days=10_000.0,
        peer_review_signal=-0.5,
    )
    assert score >= 0.0
```

- [ ] **Step 3: Run — should FAIL with `ModuleNotFoundError`**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_compliance.py -v --tb=short
```

Expected: `ModuleNotFoundError: No module named 'app.services.intelligence.presets.compliance'`.

- [ ] **Step 4: Implement the preset**

Create `app/services/intelligence/presets/compliance.py`:

```python
"""Compliance-domain confidence preset.

Phase 116-01 — wires the Compliance Agent's RiskReportAgent + create_risk /
update_risk service paths onto a standard confidence formula.

The formula weights four signals:
- regulation_authority           (0.40): statute > guidance > peer commentary > anecdote
- evidence_traceability          (0.30): fraction of claims with explicit citations
- recency_vs_regulation_version  (0.20): how fresh the underlying regulation is
- peer_review_signal             (0.10): single-author vs reviewed by ≥2 parties

Recency is inverted from a days-old input the same way data.py inverts
data_age_hours into a recency score: 0 days = 1.0, ≥ horizon = 0.0.
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

COMPLIANCE_WEIGHTS: dict[str, float] = {
    "regulation_authority": 0.40,
    "evidence_traceability": 0.30,
    "recency_vs_regulation_version": 0.20,
    "peer_review_signal": 0.10,
}


def compliance_confidence(
    regulation_authority: float,
    evidence_traceability: float,
    regulation_age_days: float,
    peer_review_signal: float,
    *,
    recency_horizon_days: float = 365.0,
) -> float:
    """Compute compliance-domain confidence from regulation + evidence signals.

    Args:
        regulation_authority: [0.0, 1.0] — quality of the underlying regulatory
            source. Statute/regulation = 1.0, industry guidance ≈ 0.7,
            peer commentary ≈ 0.4, anecdote ≈ 0.1.
        evidence_traceability: [0.0, 1.0] — fraction of assertions in the
            assessment with explicit citations (URLs, audit log refs, policy
            section numbers).
        regulation_age_days: How old the regulation version cited in the
            assessment is, in days. Inverted: 0 days = max recency,
            ``recency_horizon_days`` or older = 0 recency.
        peer_review_signal: [0.0, 1.0] — single-author = 0.0, second-reviewer
            sign-off = 1.0. Intermediate values for partial review
            (e.g., 0.5 for an automated linter pass).
        recency_horizon_days: Days at which recency reaches zero. Default 365
            (one year — most regulations are amended on an annual cycle).

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Notes:
        Inputs outside [0.0, 1.0] are clamped at the boundary BEFORE the
        weighted sum, so callers can pass raw counts or fractions without
        manual clamping. Recency is derived inside the function — callers
        pass days-old, not a normalized score.
    """
    # Clamp the directly-normalized signals to [0.0, 1.0]
    reg = max(0.0, min(1.0, regulation_authority))
    evidence = max(0.0, min(1.0, evidence_traceability))
    peer = max(0.0, min(1.0, peer_review_signal))

    # Invert age-in-days into a recency score in [0.0, 1.0].
    age = max(0.0, regulation_age_days)
    horizon = max(1.0, recency_horizon_days)  # avoid div-by-zero on bad input
    recency = max(0.0, 1.0 - min(1.0, age / horizon))

    return score_confidence(
        inputs={
            "regulation_authority": reg,
            "evidence_traceability": evidence,
            "recency_vs_regulation_version": recency,
            "peer_review_signal": peer,
        },
        weights=COMPLIANCE_WEIGHTS,
    )
```

- [ ] **Step 5: Wire it into the presets package**

Modify `app/services/intelligence/presets/__init__.py`:

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula — Phase 113 added data_confidence; Phase 116 adds
compliance_confidence.
"""

from app.services.intelligence.presets.compliance import compliance_confidence
from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = ["compliance_confidence", "data_confidence", "research_confidence"]
```

- [ ] **Step 6: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_compliance.py -v --tb=short
```

Expected: 8 passed.

- [ ] **Step 7: Commit (GREEN)**

```bash
git add app/services/intelligence/presets/compliance.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/presets/__init__.py tests/unit/services/intelligence/presets/test_compliance.py
git commit -m "feat(116-01): compliance_confidence preset with 40/30/20/10 weights (GREEN)"
```

### Task 3: Extend `RiskAssessment` schema with confidence + band (TDD)

**Files:**
- Modify: `app/agents/schemas.py`
- Create: `tests/unit/agents/compliance/__init__.py` (if missing — empty package marker)
- Create: `tests/unit/agents/compliance/test_risk_assessment_confidence.py`

- [ ] **Step 1: Ensure the test directory is a package**

```powershell
if (-not (Test-Path "tests/unit/agents/compliance")) {
    New-Item -ItemType Directory tests/unit/agents/compliance
}
if (-not (Test-Path "tests/unit/agents/compliance/__init__.py")) {
    New-Item -ItemType File tests/unit/agents/compliance/__init__.py
}
```

- [ ] **Step 2: Write the failing schema test**

Create `tests/unit/agents/compliance/test_risk_assessment_confidence.py`:

```python
"""Schema test: RiskAssessment accepts optional confidence + band."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _minimal_risk_assessment_kwargs() -> dict:
    """Return the smallest valid RiskAssessment kwarg dict."""
    return dict(
        risk_id="RISK-2026-001",
        title="GDPR Data Processing",
        description="No DPA on file with vendor X.",
        category="legal",
        severity="high",
        probability="likely",
        impact_score=16,
        mitigation="Sign DPA within 30 days.",
        owner="DPO",
    )


def test_risk_assessment_accepts_confidence_and_band():
    """Optional confidence + band populate correctly."""
    from app.agents.schemas import RiskAssessment

    ra = RiskAssessment(
        **_minimal_risk_assessment_kwargs(),
        confidence=0.83,
        band="high",
    )
    assert ra.confidence == pytest.approx(0.83)
    assert ra.band == "high"


def test_risk_assessment_omits_confidence_and_band_when_unset():
    """Backward-compat — historical risk rows have no confidence; both default None."""
    from app.agents.schemas import RiskAssessment

    ra = RiskAssessment(**_minimal_risk_assessment_kwargs())
    assert ra.confidence is None
    assert ra.band is None


def test_risk_assessment_confidence_bounds_enforced():
    """confidence must be in [0.0, 1.0]."""
    from app.agents.schemas import RiskAssessment

    with pytest.raises(ValidationError):
        RiskAssessment(
            **_minimal_risk_assessment_kwargs(),
            confidence=1.5,
            band="high",
        )
    with pytest.raises(ValidationError):
        RiskAssessment(
            **_minimal_risk_assessment_kwargs(),
            confidence=-0.1,
            band="low",
        )


def test_risk_assessment_band_must_be_literal():
    """band only accepts 'low', 'medium', 'high'."""
    from app.agents.schemas import RiskAssessment

    with pytest.raises(ValidationError):
        RiskAssessment(
            **_minimal_risk_assessment_kwargs(),
            confidence=0.5,
            band="critical",  # not a valid band
        )
```

- [ ] **Step 3: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/compliance/test_risk_assessment_confidence.py -v --tb=short
```

Expected: at least 2 failures — the existing `RiskAssessment` rejects unknown fields (`confidence`, `band`) under Pydantic's `model_config` defaults.

- [ ] **Step 4: Extend the schema**

Open `app/agents/schemas.py`, locate `class RiskAssessment(BaseModel)` (around line 103), and add the two optional fields immediately after `status`:

```python
class RiskAssessment(BaseModel):
    """Structured output for compliance risk evaluation.

    Used by RiskReportAgent to produce JSON that the parent
    ComplianceRiskAgent narrates for users.
    """

    risk_id: str
    title: str
    description: str
    category: Literal["legal", "financial", "operational", "reputational"]
    severity: Literal["low", "medium", "high", "critical"]
    probability: Literal["unlikely", "possible", "likely", "certain"]
    impact_score: int = Field(
        ge=1, le=25, description="Risk matrix score (severity * probability)"
    )
    mitigation: str = Field(description="Recommended mitigation strategy")
    owner: str = Field(description="Responsible party for addressing this risk")
    due_date: date | None = None
    status: Literal["identified", "in_progress", "mitigated", "accepted"] = "identified"
    # Phase 116-01: shared-intelligence calibration. Optional so historical
    # rows that pre-date the wiring continue to validate.
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Compliance-domain confidence in [0.0, 1.0] from compliance_confidence preset.",
    )
    band: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Confidence band classification — derived from `confidence` via to_band().",
    )
```

- [ ] **Step 5: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/compliance/test_risk_assessment_confidence.py -v --tb=short
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/agents/schemas.py tests/unit/agents/compliance/__init__.py tests/unit/agents/compliance/test_risk_assessment_confidence.py
git commit -m "feat(116-01): extend RiskAssessment schema with optional confidence + band"
```

### Task 4: Wire `compliance_confidence` into ComplianceService.create_risk / update_risk (TDD)

**Files:**
- Create: `tests/unit/services/test_compliance_service_confidence.py`
- Modify: `app/services/compliance_service.py`

The service-layer mutation is the canonical write path for `compliance_risks` rows. Compute confidence here so every row inserted via `create_risk` / `update_risk` gets a populated `confidence` + `band` column, regardless of caller (agent tool, admin UI, future workflow).

- [ ] **Step 1: Confirm the `compliance_risks` table has nullable confidence + band columns**

```powershell
docker exec -i supabase_db_pikar-ai psql -U postgres -d postgres -c "\d compliance_risks"
```

Expected: if `confidence` / `band` columns are absent, a one-line schema migration is needed. Add `supabase/migrations/20260519_phase116_compliance_risks_confidence.sql`:

```sql
-- Phase 116-01: persist confidence + band on compliance_risks for analytics.
ALTER TABLE compliance_risks
    ADD COLUMN IF NOT EXISTS confidence numeric(5, 4),
    ADD COLUMN IF NOT EXISTS confidence_band text
        CHECK (confidence_band IN ('low', 'medium', 'high'));

-- Lightweight index for "show me low-confidence risks for human review."
CREATE INDEX IF NOT EXISTS idx_compliance_risks_confidence_band
    ON compliance_risks(confidence_band)
    WHERE confidence_band IS NOT NULL;
```

Apply it:

```powershell
supabase db push --local
```

If the local push errors with "drift", fall back to `docker exec -i supabase_db_pikar-ai psql -U postgres -d postgres -f supabase/migrations/20260519_phase116_compliance_risks_confidence.sql` (per `reference_local_dev_env_quirks.md`).

- [ ] **Step 2: Write the failing service test**

Create `tests/unit/services/test_compliance_service_confidence.py`:

```python
"""Unit test: ComplianceService.create_risk / update_risk compute + persist confidence.

We mock the Supabase async client to capture the insert payload — the test
asserts that `confidence` and `confidence_band` are in the payload and are
derived from the documented signal mapping.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_create_risk_attaches_confidence_and_band():
    """create_risk computes confidence from severity + mitigation_plan signals."""
    from app.services.compliance_service import ComplianceService

    captured: dict = {}

    class _FakeQuery:
        def insert(self, data):
            captured["insert"] = data
            return self

    fake_client = MagicMock()
    fake_client.table.return_value = _FakeQuery()

    async def _fake_execute(query):
        return MagicMock(data=[dict(captured["insert"], id="r-1")])

    with patch(
        "app.services.compliance_service.execute_async",
        new=AsyncMock(side_effect=_fake_execute),
    ), patch(
        "app.services.compliance_service.AdminService",
    ) as fake_admin:
        fake_admin.return_value.client = fake_client
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False  # force admin path
        await svc.create_risk(
            title="SOC2 evidence gap",
            description="Annual penetration test report missing from auditor portal. See https://example.com/policy.",
            severity="high",
            mitigation_plan="Engage Qualys to schedule pen test within 14 days. See SOC2 CC7.2.",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    insert = captured["insert"]
    assert "confidence" in insert
    assert 0.0 <= insert["confidence"] <= 1.0
    assert insert.get("confidence_band") in {"low", "medium", "high"}


@pytest.mark.asyncio
async def test_create_risk_low_evidence_low_confidence():
    """An assessment with no citations and short mitigation gets a 'low' band."""
    from app.services.compliance_service import ComplianceService

    captured: dict = {}

    class _FakeQuery:
        def insert(self, data):
            captured["insert"] = data
            return self

    fake_client = MagicMock()
    fake_client.table.return_value = _FakeQuery()

    async def _fake_execute(query):
        return MagicMock(data=[dict(captured["insert"], id="r-2")])

    with patch(
        "app.services.compliance_service.execute_async",
        new=AsyncMock(side_effect=_fake_execute),
    ), patch(
        "app.services.compliance_service.AdminService",
    ) as fake_admin:
        fake_admin.return_value.client = fake_client
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.create_risk(
            title="vague concern",
            description="something feels off",
            severity="low",
            mitigation_plan="tbd",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    insert = captured["insert"]
    # Low evidence + no citations + short mitigation = low band.
    assert insert["confidence_band"] == "low"
    assert insert["confidence"] < 0.50


@pytest.mark.asyncio
async def test_update_risk_recomputes_confidence_on_mitigation_change():
    """update_risk recomputes confidence when mitigation_plan changes."""
    from app.services.compliance_service import ComplianceService

    captured: dict = {}

    class _FakeQuery:
        def update(self, data):
            captured["update"] = data
            return self

        def eq(self, *_a, **_k):
            return self

    fake_client = MagicMock()
    fake_client.table.return_value = _FakeQuery()

    async def _fake_execute(query):
        return MagicMock(data=[dict(captured["update"], id="r-3")])

    with patch(
        "app.services.compliance_service.execute_async",
        new=AsyncMock(side_effect=_fake_execute),
    ), patch(
        "app.services.compliance_service.AdminService",
    ) as fake_admin:
        fake_admin.return_value.client = fake_client
        svc = ComplianceService(user_token=None)
        svc._is_authenticated = False
        await svc.update_risk(
            risk_id="r-3",
            mitigation_plan="Implemented controls per SOC2 CC7.2 with second-reviewer sign-off. Evidence in https://corp.example.com/audit/2026.",
            user_id="00000000-0000-0000-0000-000000000001",
        )

    update = captured["update"]
    assert "confidence" in update
    assert update["confidence_band"] in {"low", "medium", "high"}
```

- [ ] **Step 3: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/test_compliance_service_confidence.py -v --tb=short
```

Expected: 3 failures — the existing `create_risk` / `update_risk` don't compute confidence.

- [ ] **Step 4: Add the confidence helper to compliance_service.py**

In `app/services/compliance_service.py`, add a private helper near the top of the class (after `__init__`):

```python
    # ==========================
    # Confidence Computation (Phase 116-01)
    # ==========================

    @staticmethod
    def _compute_risk_confidence(
        *,
        description: str,
        mitigation_plan: str,
        severity: str,
    ) -> tuple[float, str]:
        """Compute compliance_confidence from risk-row inputs.

        Maps raw text + severity to the four signals the preset expects:

        - regulation_authority: 1.0 if description cites a known regulation
          keyword (gdpr, hipaa, sox, ccpa, pci-dss, soc2, iso 27001,
          article \\d+, § \\d+), else 0.5 if it cites a policy, else 0.2.
        - evidence_traceability: fraction of mitigation_plan tokens that look
          like citations (urls, policy refs, audit-log markers), bounded
          by len(plan) >= 40 chars for a floor.
        - regulation_age_days: 0.0 (assume current at write time — Plan 116-02
          surfaces real version dates via `sources`).
        - peer_review_signal: 0.5 (single-author default; UI can pass an
          override later).

        Severity acts as a meta-multiplier: 'critical' severity scales the
        result up by 1.0 (no penalty), 'low' scales by 0.9 (rough confidence
        attenuation — low-severity risks are typically less thoroughly
        documented).

        Returns:
            (confidence_float, confidence_band_str)
        """
        import re

        from app.services.intelligence.confidence import to_band
        from app.services.intelligence.presets.compliance import compliance_confidence

        text = f"{description}\n{mitigation_plan}".lower()
        # Regulation signal
        if re.search(r"\b(gdpr|hipaa|sox|ccpa|cpra|pci[- ]?dss|soc\s*2|iso\s*27001|article\s+\d+|§\s*\d+|cc7\.\d|cc8\.\d)\b", text):
            reg_signal = 1.0
        elif re.search(r"\b(policy|procedure|standard)\b", text):
            reg_signal = 0.5
        else:
            reg_signal = 0.2

        # Evidence signal: tokens that smell like citations.
        plan_lower = mitigation_plan.lower()
        citation_hits = len(re.findall(r"https?://|\bref:?\s*[a-z0-9-]+|\baudit log\b|\bdocument id\b", plan_lower))
        plan_len_signal = min(1.0, len(mitigation_plan) / 200.0)
        evidence_signal = max(plan_len_signal, min(1.0, citation_hits * 0.25))

        # Recency: assume the risk is being recorded against current regulation.
        regulation_age_days = 0.0

        # Peer review: default to single-author. Real signal comes from
        # PR reviewers / dual-control checkboxes in a follow-up.
        peer_signal = 0.5

        raw = compliance_confidence(
            regulation_authority=reg_signal,
            evidence_traceability=evidence_signal,
            regulation_age_days=regulation_age_days,
            peer_review_signal=peer_signal,
        )

        # Severity attenuation: low-severity risks slightly attenuated.
        severity_multiplier = {
            "critical": 1.0,
            "high": 1.0,
            "medium": 0.95,
            "low": 0.90,
        }.get(severity, 1.0)
        confidence = max(0.0, min(1.0, raw * severity_multiplier))
        return confidence, to_band(confidence)
```

- [ ] **Step 5: Use the helper in `create_risk` and `update_risk`**

Locate `create_risk` (around line ~118 of the file in its current form). Add confidence computation just before building `data`:

```python
    async def create_risk(
        self,
        title: str,
        description: str,
        severity: str,
        mitigation_plan: str,
        user_id: str | None = None,
    ) -> dict:
        """Create a new risk item with computed confidence + band (Phase 116-01)."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for risk creation")

        confidence, band = self._compute_risk_confidence(
            description=description,
            mitigation_plan=mitigation_plan,
            severity=severity,
        )

        data = {
            "title": title,
            "description": description,
            "severity": severity,
            "mitigation_plan": mitigation_plan,
            "user_id": effective_user_id,
            "confidence": confidence,
            "confidence_band": band,
        }
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._risks_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert risk")
```

For `update_risk`, only recompute when either `mitigation_plan` or `severity` is being changed:

```python
    async def update_risk(
        self,
        risk_id: str,
        status: str | None = None,
        severity: str | None = None,
        mitigation_plan: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a risk row; recompute confidence when severity or mitigation_plan change."""
        update_data: dict = {}
        if status is not None:
            update_data["status"] = status
        if severity is not None:
            update_data["severity"] = severity
        if mitigation_plan is not None:
            update_data["mitigation_plan"] = mitigation_plan

        if severity is not None or mitigation_plan is not None:
            # Fetch the row to combine new+old fields for recompute.
            existing = await self.get_risk(risk_id, user_id=user_id)
            confidence, band = self._compute_risk_confidence(
                description=existing.get("description", ""),
                mitigation_plan=mitigation_plan or existing.get("mitigation_plan", ""),
                severity=severity or existing.get("severity", "medium"),
            )
            update_data["confidence"] = confidence
            update_data["confidence_band"] = band

        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._risks_table).update(update_data).eq("id", risk_id)
        if not self.is_authenticated and user_id:
            query = query.eq("user_id", user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update risk")
```

Note the test for `update_risk` mocks `get_risk` via the captured client — if the test fails on the `existing = await self.get_risk(...)` line, mock `get_risk` directly in the test (add `with patch.object(ComplianceService, "get_risk", new=AsyncMock(return_value={"description": "...", "mitigation_plan": "...", "severity": "high"})):`).

- [ ] **Step 6: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/test_compliance_service_confidence.py -v --tb=short
```

Expected: 3 passed. If the `update_risk` test fails because `get_risk` was called on the mock client, add a `get_risk` patch inside the test:

```python
with patch.object(ComplianceService, "get_risk", new=AsyncMock(return_value={"description": "old desc", "mitigation_plan": "old plan", "severity": "high"})):
    ...
```

- [ ] **Step 7: Commit**

```bash
git add app/services/compliance_service.py supabase/migrations/20260519_phase116_compliance_risks_confidence.sql tests/unit/services/test_compliance_service_confidence.py
git commit -m "feat(116-01): wire compliance_confidence into create_risk + update_risk"
```

### Task 5: Wire confidence post-processing into RiskReportAgent flow (TDD)

**Files:**
- Create: `tests/unit/agents/compliance/test_risk_report_agent_post_processing.py`
- Modify: `app/agents/compliance/agent.py`

The `RiskReportAgent` ADK sub-agent uses `output_schema=RiskAssessment` + `include_contents="none"`, which forbids before/after_model_callback (per the file's docstring). We attach confidence in the *parent* `ComplianceRiskAgent`'s flow — specifically by adding an `after_tool_callback` that intercepts when a tool returns a `RiskAssessment`-shaped dict and back-fills `confidence` + `band` before the dict reaches the LLM's narration step.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/agents/compliance/test_risk_report_agent_post_processing.py`:

```python
"""Unit tests for the Compliance Agent's risk-assessment post-processing.

We don't spin up the full ADK runtime; we test the pure post-processor
function (`_attach_risk_confidence`) that the after_tool_callback delegates
to.
"""

from __future__ import annotations

import pytest


def test_attach_risk_confidence_populates_fields():
    """A RiskAssessment-shaped dict is enriched with confidence + band."""
    from app.agents.compliance.agent import _attach_risk_confidence

    raw = {
        "risk_id": "RISK-2026-005",
        "title": "GDPR Article 28 processor obligations",
        "description": "Vendor X under GDPR Article 28 has no signed DPA.",
        "category": "legal",
        "severity": "high",
        "probability": "likely",
        "impact_score": 16,
        "mitigation": "Sign DPA per GDPR Article 28. See https://gdpr.eu/article-28.",
        "owner": "DPO",
        "status": "identified",
    }
    enriched = _attach_risk_confidence(raw)

    assert "confidence" in enriched
    assert 0.0 <= enriched["confidence"] <= 1.0
    assert enriched["band"] in {"low", "medium", "high"}


def test_attach_risk_confidence_is_idempotent():
    """If the dict already has confidence + band, the values are preserved."""
    from app.agents.compliance.agent import _attach_risk_confidence

    raw = {
        "risk_id": "RISK-2026-006",
        "title": "x",
        "description": "y",
        "category": "operational",
        "severity": "medium",
        "probability": "possible",
        "impact_score": 6,
        "mitigation": "z",
        "owner": "ops",
        "status": "identified",
        "confidence": 0.42,
        "band": "low",
    }
    enriched = _attach_risk_confidence(raw)
    assert enriched["confidence"] == pytest.approx(0.42)
    assert enriched["band"] == "low"


def test_attach_risk_confidence_non_assessment_passthrough():
    """Non-RiskAssessment shaped dicts are passed through unchanged."""
    from app.agents.compliance.agent import _attach_risk_confidence

    raw = {"unrelated": "payload", "value": 42}
    result = _attach_risk_confidence(raw)
    assert result == raw


def test_attach_risk_confidence_high_authority_high_evidence():
    """A risk that cites a regulation by name + URL + ref is at least 'medium' band."""
    from app.agents.compliance.agent import _attach_risk_confidence

    raw = {
        "risk_id": "RISK-2026-007",
        "title": "SOC2 CC7.2 monitoring gap",
        "description": "Per SOC2 CC7.2 we lack continuous monitoring evidence.",
        "category": "operational",
        "severity": "high",
        "probability": "likely",
        "impact_score": 16,
        "mitigation": (
            "Onboard Datadog APM by 2026-06-01. See https://corp.example.com/runbook "
            "and audit log ref: AUD-2026-Q2-CC72."
        ),
        "owner": "CISO",
        "status": "identified",
    }
    enriched = _attach_risk_confidence(raw)
    assert enriched["band"] in {"medium", "high"}, enriched
```

- [ ] **Step 2: Run — should FAIL with ImportError**

```powershell
uv run pytest tests/unit/agents/compliance/test_risk_report_agent_post_processing.py -v --tb=short
```

Expected: `ImportError: cannot import name '_attach_risk_confidence'`.

- [ ] **Step 3: Add `_attach_risk_confidence` to `app/agents/compliance/agent.py`**

Add a module-level helper above `_create_risk_report_agent`:

```python
# ---------------------------------------------------------------------------
# Phase 116-01: confidence post-processing for RiskAssessment dicts.
# ---------------------------------------------------------------------------

_REQUIRED_RISK_FIELDS = (
    "risk_id",
    "title",
    "category",
    "severity",
    "probability",
    "impact_score",
    "mitigation",
)


def _attach_risk_confidence(payload: dict) -> dict:
    """Enrich a RiskAssessment-shaped dict with `confidence` + `band`.

    Returns a NEW dict (does not mutate `payload`). Idempotent — if both
    fields are already present, returns the payload unchanged.

    A dict is "RiskAssessment-shaped" when it contains every key in
    ``_REQUIRED_RISK_FIELDS``. Non-shaped payloads pass through.
    """
    if not isinstance(payload, dict):
        return payload
    if not all(k in payload for k in _REQUIRED_RISK_FIELDS):
        return payload
    if (
        payload.get("confidence") is not None
        and payload.get("band") is not None
    ):
        return payload

    # Local imports to avoid the agent module incurring intelligence
    # dependencies at import time.
    from app.services.compliance_service import ComplianceService

    confidence, band = ComplianceService._compute_risk_confidence(
        description=payload.get("description", ""),
        mitigation_plan=payload.get("mitigation", ""),
        severity=payload.get("severity", "medium"),
    )
    return {**payload, "confidence": confidence, "band": band}
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/compliance/test_risk_report_agent_post_processing.py -v --tb=short
```

Expected: 4 passed.

- [ ] **Step 5: Wire the post-processor into the ADK callback (parent agent only)**

The parent `ComplianceRiskAgent` is built via `PikarBaseAgent` and supports `after_tool_callback`. Locate the `create_compliance_agent` factory and add the callback through `**extra` plumbing — but we want it always-on, not opt-in.

Add a module-level callback wrapper:

```python
def _after_risk_tool_callback(tool_context, tool_name, tool_result):
    """ADK after_tool_callback: enrich RiskAssessment-shaped tool results.

    Runs after each tool invocation in the ComplianceRiskAgent. If the tool
    returned a dict that looks like a RiskAssessment, attaches confidence + band.

    No-op for other tools (the helper passes through non-shaped payloads).
    """
    _ = tool_context, tool_name  # ADK signature compliance
    if isinstance(tool_result, dict) and tool_result.get("success") is True:
        # Some tools wrap the assessment inside {"success": True, "risk": {...}}.
        if "risk" in tool_result and isinstance(tool_result["risk"], dict):
            tool_result = {**tool_result, "risk": _attach_risk_confidence(tool_result["risk"])}
            return tool_result
    return _attach_risk_confidence(tool_result) if isinstance(tool_result, dict) else tool_result
```

Modify the `PikarBaseAgent` construction in `create_compliance_agent` to pass this callback. Inspect `PikarBaseAgent`'s signature for the right kwarg name:

```powershell
Select-String -Path app/agents/base_agent.py -Pattern "after_tool_callback|callback" | Format-Table LineNumber,Line -AutoSize | Out-File -Encoding utf8 .planning/phase-116/_callback_probe.txt
Get-Content .planning/phase-116/_callback_probe.txt
```

If `PikarBaseAgent` accepts `after_tool_callback` (or aliases like `tool_callback`), pass `_after_risk_tool_callback` via that kwarg. If `PikarBaseAgent` doesn't expose a callback hook, fall back: pass the callback as one of the `**extra` kwargs forwarded to the underlying ADK Agent and document why.

For the minimal-risk version, add the parameter to `create_compliance_agent` and let callers opt out (default on):

```python
def create_compliance_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    attach_confidence: bool = True,
    **extra: Any,
) -> PikarBaseAgent:
    _ = name_suffix
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()

    if attach_confidence:
        extra.setdefault("after_tool_callback", _after_risk_tool_callback)

    return PikarBaseAgent(
        agent_id=AgentID.LEGAL,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description="Legal Counsel - Compliance, risk assessment, and legal guidance",
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        sub_agents=[_create_risk_report_agent()],
        **extra,
    )
```

If `PikarBaseAgent` rejects `after_tool_callback`, remove the setdefault and document in the agent's docstring that the post-processing is applied at the ComplianceService write boundary (which is already covered by Task 4); Task 5 then becomes a pure unit-test-of-helper task and the integration check moves to Plan 116-02's claim emission.

- [ ] **Step 6: Run the compliance agent smoke test to confirm nothing crashes**

```powershell
uv run pytest tests/unit/agents/compliance/ -v --tb=short
```

Expected: all green. If `tests/unit/agents/compliance/` already has other tests, they continue to pass — the factory's new kwarg has a default that preserves prior behavior.

- [ ] **Step 7: Commit**

```bash
git add app/agents/compliance/agent.py tests/unit/agents/compliance/test_risk_report_agent_post_processing.py
git commit -m "feat(116-01): post-process RiskAssessment dicts with confidence + band"
```

### Task 6: Run the full Compliance Agent test suite + lint

**Files:** none (verification only).

- [ ] **Step 1: Run every test in or near the Compliance Agent**

```powershell
uv run pytest tests/unit/agents/compliance/ tests/unit/services/test_compliance_service_confidence.py tests/unit/services/intelligence/presets/test_compliance.py -v --tb=short
```

Expected: all green. If any pre-existing Compliance test fails, investigate — Plan 116-01 should be schema-additive only.

- [ ] **Step 2: Run any broader test bucket that touches compliance**

```powershell
uv run pytest -k "compliance" --tb=short
```

Expected: green or skipped (with skip reasons documented — usually "env not set" for integration tests).

- [ ] **Step 3: Lint**

```powershell
uv run ruff check app/services/intelligence/presets/compliance.py app/services/compliance_service.py app/agents/compliance/agent.py app/agents/schemas.py tests/unit/services/intelligence/presets/test_compliance.py tests/unit/agents/compliance/ tests/unit/services/test_compliance_service_confidence.py
uv run ruff format --check app/services/intelligence/presets/compliance.py app/services/compliance_service.py app/agents/compliance/agent.py app/agents/schemas.py tests/unit/services/intelligence/presets/test_compliance.py tests/unit/agents/compliance/ tests/unit/services/test_compliance_service_confidence.py
```

If formatter complains, run `uv run ruff format <files>` and re-stage. Commit any pure-formatting fix-ups as:

```bash
git add -u
git commit -m "style(116-01): ruff format fixes for Compliance preset + wiring"
```

- [ ] **Step 4: Type check**

```powershell
uv run ty check app/services/intelligence/presets/compliance.py app/services/compliance_service.py app/agents/compliance/agent.py
```

Expected: clean. If `ty` complains about `_compute_risk_confidence` not returning the right tuple shape, add explicit return-type annotation (already done in Task 4).

- [ ] **Step 5: Plan 116-01 acceptance — cross-check**

| Spec requirement (Phase 116 § Acceptance) | Verified by |
|---|---|
| `compliance_confidence` preset shipped with 40/30/20/10 weights | Task 2 |
| Optional `confidence` + `band` on RiskAssessment | Task 3 |
| Risk-assessment writes carry confidence + band | Tasks 4, 5 |
| Self-improvement engine entanglement audit completed BEFORE changes | Task 1 |
| Compliance Agent test suite green | Task 6 |

- [ ] **Step 6: Push branch**

```bash
git status   # confirm clean
git log --oneline -10   # confirm 5 commits this plan
```

Expected: 5 commits with subjects starting `feat(116-01):` / `docs(116-01):` / `style(116-01):`.

Plan 116-01 complete. Plan 116-02 takes over for claim emission to `kg_findings`.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `presets/compliance.py` with documented weights | Task 2 |
| Wire preset into RiskAssessment outputs (confidence + band) | Tasks 3, 5 |
| Wire preset into create_risk / update_risk write path | Task 4 |
| Self-improvement engine audit BEFORE other changes (Decision #8) | Task 1 |
| Backward-compat: historical rows still validate | Task 3 (optional field) |
| Test suite green | Task 6 |
| Lint + types clean | Task 6 |

All Phase 116 § Acceptance criteria addressed *by this plan* are covered. The remaining criterion ("`search_claims_semantic` returns Compliance claims" and the immutability invariant) is delivered by Plan 116-02.
