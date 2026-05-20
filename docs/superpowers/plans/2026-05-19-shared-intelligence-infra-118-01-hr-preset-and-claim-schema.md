# Shared Intelligence Infrastructure — Plan 118-01: HR Preset, Claim Schema, and Self-Improvement Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `presets/hr.py` (`hr_confidence`) wired into the four HR-domain signals; design the HR claim-type vocabulary from scratch (HR has *no* existing claim schema, unlike Sales/Financial/Compliance which already had `LeadQualification` / `RiskAssessment` shapes to formalize); and audit the self-improvement engine's entanglement with HR-agent code paths before any claim emission begins (Decision #8 in the rolling adoption design).

**Architecture:** Thin preset over `score_confidence`, mirroring `presets/data.py`. The novel work is **schema design** — HR's outputs (resume screenings, interview rubrics, hiring funnel snapshots, candidate progression) have never been written as claims, so the claim_type vocabulary, entity_type mapping, and `expires_at` lifecycle semantics are designed in this plan. The audit step is **information-gathering only** (no code changes to `self_improvement_engine.py`) — it captures the existing entanglement contract so Plan 118-02 doesn't accidentally break it when emitting claims from `update_candidate_status` paths.

**Tech Stack:** `app/services/intelligence/` (shared package from Phase 112), `app/services/intelligence/presets/hr.py` (new), Pydantic v2 schemas, pytest.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 118 — HR Agent adoption.

**Out of scope:** Claim *emission* from HR tools (Plan 118-02). External cache integration — HR is internal CRUD over `recruitment_jobs` / `recruitment_candidates`, no external API calls to amortize (this is why Phase 118 only has two sub-plans, not three). Persona-aware formatting of confidence in HR responses (deferred from Phase 112). Bias-guardrail integration (the HR agent's existing fairness rules remain enforced via the instructions file; confidence scoring does not gate or replace them).

---

## File structure

**Create:**
- `app/services/intelligence/presets/hr.py` — the `hr_confidence` preset
- `tests/unit/services/intelligence/test_hr_preset.py` — boundary tests for the preset
- `docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md` — audit findings (no code; reference doc consumed by Plan 118-02)

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `hr_confidence`
- `app/services/intelligence/__init__.py` — re-export `hr_confidence` (mirroring `data_confidence`)

**Read-only (reference):**
- `app/services/self_improvement_engine.py` — audit input
- `app/services/skill_experiment_evaluator.py` — audit input
- `docs/self-improvement-policy.md` — audit reference (the autonomy boundary contract)
- `app/agents/hr/agent.py`, `app/agents/hr/tools.py`, `app/agents/hr/instructions.md` — agent surface the audit must walk over

---

## Pre-flight context

### The four HR signals

The preset weights `HR_WEIGHTS`:

```python
HR_WEIGHTS = {
    "candidate_data_completeness": 0.35,  # how many resume / app fields landed
    "interviewer_consensus":       0.30,  # cross-interviewer score agreement
    "recency":                     0.20,  # how fresh the latest interaction is
    "assessment_battery_coverage": 0.15,  # fraction of planned assessments done
}
```

Why these signals and these weights:

- **`candidate_data_completeness` (0.35)** — HR's analogue to Data's "sample adequacy". A candidate evaluated on only a name + email is much weaker evidence than one with resume + 3 interviewer rubrics + reference checks. Computed as `non_null_fields / expected_fields_for_stage`. Highest weight because incomplete data is the single biggest noise source in HR signals.
- **`interviewer_consensus` (0.30)** — Standard deviation of interviewer scores (1–5 rubric), inverted: `1 - min(1, sigma / 2)`. A single interviewer's strong "yes" with no peer corroboration scores lower than 4 interviewers averaging 4.2. This is *similar in spirit* to Research's `track_agreement` but applied to humans not retrieval tracks.
- **`recency` (0.20)** — Hours since the latest candidate touchpoint (interview, application update, reference check). Decays linearly to zero at 30 days (720 h). Matches the data preset's `recency` shape so the formulas compose consistently.
- **`assessment_battery_coverage` (0.15)** — For roles that have a planned assessment battery (coding test + behavioral interview + reference check + work sample), the fraction completed. Default 1.0 if no battery is defined for the role.

All four signals are normalized to `[0.0, 1.0]` by the preset before passing to `score_confidence`. The preset itself does the normalization (so callers pass raw counts / sigma / hours and the preset clamps).

### The HR claim-type vocabulary (designed in this plan)

This is the **novel** half of 118-01: HR has never written to `kg_findings`, so every claim_type, entity_type, source kind, and lifecycle rule is new.

| Claim type | Entity type | Lifecycle | `expires_at` | Emitted from |
|---|---|---|---|---|
| `candidate_signal` | `person` (candidate) | **One claim per candidate-job pair**, `freshness_at` updates on each interaction. Expires at offer-accept (status='hired') or rejection (status='rejected'). | NULL on creation; set to `now()` at terminal transition | `add_candidate`, `update_candidate_status`, `generate_interview_questions` (rubric finalized) — Plan 118-02 |
| `hiring_pipeline_state` | `topic` (requisition) | **Periodic snapshot per requisition**, written every time `get_hiring_funnel(job_id=X)` runs OR every 24 h, whichever is sooner. New claim_id per snapshot (append-only). | `now() + 7d` (snapshot becomes stale after a week) | `get_hiring_funnel` — Plan 118-02 |

Two claim types. Deliberately small surface — HR is operational, not analytical, and we want to validate the spine of the abstraction before adding `compensation_band_signal` / `onboarding_completion_state` claim types in a future iteration.

#### Source `kind` extension

The `ClaimSource.kind` Literal currently includes `'url' | 'supabase_row' | 'stripe_row' | 'shopify_row' | 'regulation' | 'user' | 'other'`. **HR claims do not introduce a new `kind`** — they reuse `supabase_row` (for recruitment table rows) and `user` (for interviewer rubric inputs). This keeps the schema migration cost at zero. If a future plan needs a dedicated `ats_row` kind (e.g., when external ATS ingestion lands), it adds it then.

#### `entity_id` resolution rules

- `candidate_signal` claims attach to a **candidate-as-`person`-entity**. Canonical name = `f"candidate:{candidate_uuid}"`. This namespaces candidates from real people the agent already knows about (e.g., investors, board members), preventing collision in semantic search.
- `hiring_pipeline_state` claims attach to a **requisition-as-`topic`-entity**. Canonical name = `f"hiring_requisition:{job_uuid}"`. We use `topic` (not `event` or `product`) because the requisition is a long-running thing the agent reasons about over time, not a one-shot event.

#### `agent_id` and `domain`

- `agent_id = "hr"` (matches `AgentID.HR` in `app/skills/registry.py`).
- `domain = "hr"` (lower-case string tag — Phase 112 schema constraint is just `domain TEXT NOT NULL`, no enum).

#### `embed` policy

- `candidate_signal` → `embed=True`. We want semantic search to surface candidate evaluations alongside cross-agent claims (e.g., Sales asking "who did we interview for the sales engineer role" should be able to find the HR claim).
- `hiring_pipeline_state` → `embed=False`. Snapshots are mostly numerical breakdowns; the value is the structured payload, not the text. Save the embedding budget for `candidate_signal`.

### Self-improvement engine audit (Decision #8 — STRUCTURAL REQUIREMENT)

Per the spec table row 8 and the risk register row "Self-improvement engine entangles with old per-agent code paths", **every** Phase 114–122 phase's first sub-plan must audit `app/services/self_improvement_engine.py` and `app/services/skill_experiment_evaluator.py` *before* the agent's code paths change.

The audit answers four questions:

1. **Does the engine bind to any HR-specific table / row shape?** If `interaction_logs` rows tagged `agent_id='hr'` are consumed differently from generic rows, surface the binding so Plan 118-02 doesn't break it.
2. **Does the engine read HR tool names from `app.agents.hr.tools` by string?** If yes, renaming or wrapping a tool in Plan 118-02 silently breaks the engine's effectiveness scoring.
3. **Does `skill_experiment_evaluator` reference any HR-domain skill names from `app/skills/registry.py`?** The HR agent calls `use_skill("resume_screening")`, `use_skill("interview_question_generator")`, etc. — if the evaluator pattern-matches on these names, Plan 118-02 must preserve them.
4. **Does the engine assume HR outputs are *not* claims?** If the engine treats `agent_id='hr'` interactions as inherently non-claim-producing (e.g., excludes them from a "claim coverage" metric), Plan 118-02 will violate that assumption and must either update the engine or stay outside its loop.

The audit deliverable is a **read-only Markdown notes file** under `docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md`. No code is touched in `self_improvement_engine.py` during 118-01. If the audit surfaces a load-bearing entanglement, it surfaces as a **new** task in Plan 118-02, not a retroactive edit here.

### Environment quirks

Same as prior Phase 112/113 plans:
- `uv run` only — never raw `pip`/`python`.
- Local Supabase via `supabase start`; `SUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres` for psycopg.
- On Windows PowerShell, embedded JSON in `.execute()` payloads goes through normally; no `--%` parser stop token needed for ordinary pytest commands.
- The integration-test conftest stubs `app.services.supabase_client` — direct `supabase.create_client(url, key)` calls bypass it (already the pattern in `app/services/intelligence/claims.py`).

---

## Tasks

### Task 1: Pre-flight — confirm the shared infrastructure is in place

**Files:**
- Read-only: `app/services/intelligence/__init__.py`, `app/services/intelligence/presets/__init__.py`, `app/services/intelligence/presets/data.py`

- [ ] **Step 1: Confirm Phase 112/113 modules are importable**

```powershell
uv run python -c "from app.services.intelligence import score_confidence, to_band, write_claim, find_claims, detect_contradictions, search_claims_semantic; print('intelligence package OK')"
uv run python -c "from app.services.intelligence.presets import data_confidence, research_confidence; print('presets OK')"
```

Expected: both lines print `... OK`. If either fails, this plan is blocked — Phase 113 has not landed on this branch.

- [ ] **Step 2: Confirm the HR agent surface is at the expected version**

```powershell
uv run python -c "from app.agents.hr.agent import create_hr_agent; from app.agents.hr.tools import build_tools_manifest; print('HR agent module OK')"
```

Expected: prints `HR agent module OK`. Absence here means the W4 base-agent migration hasn't propagated; fix that first.

- [ ] **Step 3: Confirm the `kg_findings` schema accepts new claim_types without migration**

```bash
git grep -n "claim_type" supabase/migrations/20260321500000_knowledge_graph.sql
git grep -n "claim_type" supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql
```

Expected: the migration files show `claim_type TEXT NOT NULL` with no CHECK constraint enumerating allowed values (the Phase 112 broadening migration removed the enum constraint specifically so new agents can introduce new types without DDL). If a CHECK constraint exists, a follow-up migration to extend it is required before Plan 118-02 can write claims.

- [ ] **Step 4: No commit — this is preflight only.**

### Task 2: Failing unit tests for `hr_confidence` (RED)

**Files:**
- Create: `tests/unit/services/intelligence/test_hr_preset.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for hr_confidence preset.

Mirrors the boundary-test pattern from tests/unit/services/intelligence/test_data_preset.py
(Plan 113-01): all-min, all-max, weighted-sum sanity, recency decay, sigma
inversion for interviewer_consensus, completeness normalization, and an
out-of-band sample (negative count, > 1.0 fraction) clamp check.
"""

from __future__ import annotations

import pytest


def test_hr_confidence_all_max_returns_one():
    """All four signals at their max produce confidence = 1.0."""
    from app.services.intelligence.presets import hr_confidence

    score = hr_confidence(
        non_null_fields=10,
        expected_fields=10,
        interviewer_score_sigma=0.0,
        latest_touchpoint_age_hours=0.0,
        assessments_completed=4,
        assessments_planned=4,
    )
    assert score == pytest.approx(1.0)


def test_hr_confidence_all_min_returns_zero():
    """All four signals at their floor produce confidence = 0.0."""
    from app.services.intelligence.presets import hr_confidence

    score = hr_confidence(
        non_null_fields=0,
        expected_fields=10,
        interviewer_score_sigma=2.0,  # saturates the inversion
        latest_touchpoint_age_hours=720.0,  # 30 d horizon
        assessments_completed=0,
        assessments_planned=4,
    )
    assert score == pytest.approx(0.0, abs=1e-3)


def test_hr_confidence_weights_balance():
    """At each signal individually maxed (others at 0), the score equals that
    signal's weight. This is the load-bearing invariant of score_confidence."""
    from app.services.intelligence.presets import hr_confidence
    from app.services.intelligence.presets.hr import HR_WEIGHTS

    # Maximize completeness only
    score = hr_confidence(
        non_null_fields=10,
        expected_fields=10,
        interviewer_score_sigma=2.0,  # saturates inversion -> 0
        latest_touchpoint_age_hours=720.0,  # -> 0
        assessments_completed=0,
        assessments_planned=4,
    )
    assert score == pytest.approx(HR_WEIGHTS["candidate_data_completeness"])


def test_hr_confidence_interviewer_consensus_is_inverted():
    """High score sigma (disagreement) lowers confidence; low sigma raises it."""
    from app.services.intelligence.presets import hr_confidence

    # Baseline: everything else at 1.0
    high_consensus = hr_confidence(
        non_null_fields=10, expected_fields=10,
        interviewer_score_sigma=0.0,  # full consensus
        latest_touchpoint_age_hours=0.0,
        assessments_completed=4, assessments_planned=4,
    )
    low_consensus = hr_confidence(
        non_null_fields=10, expected_fields=10,
        interviewer_score_sigma=1.5,  # mid-range disagreement
        latest_touchpoint_age_hours=0.0,
        assessments_completed=4, assessments_planned=4,
    )
    assert high_consensus > low_consensus


def test_hr_confidence_recency_decays_linearly():
    """Latest touchpoint age 0 -> recency 1.0; age 720 h -> 0.0; 360 h -> 0.5."""
    from app.services.intelligence.presets import hr_confidence

    # Use weights that make recency dominant by zeroing the others
    fresh = hr_confidence(
        non_null_fields=0, expected_fields=10,
        interviewer_score_sigma=2.0,
        latest_touchpoint_age_hours=0.0,
        assessments_completed=0, assessments_planned=4,
    )
    mid = hr_confidence(
        non_null_fields=0, expected_fields=10,
        interviewer_score_sigma=2.0,
        latest_touchpoint_age_hours=360.0,
        assessments_completed=0, assessments_planned=4,
    )
    stale = hr_confidence(
        non_null_fields=0, expected_fields=10,
        interviewer_score_sigma=2.0,
        latest_touchpoint_age_hours=720.0,
        assessments_completed=0, assessments_planned=4,
    )
    assert fresh > mid > stale
    # mid should be ~ 0.5 * recency_weight
    from app.services.intelligence.presets.hr import HR_WEIGHTS
    assert mid == pytest.approx(0.5 * HR_WEIGHTS["recency"], abs=1e-3)


def test_hr_confidence_assessment_coverage_defaults_to_1_when_planned_is_zero():
    """A role with no planned battery should not be penalized."""
    from app.services.intelligence.presets import hr_confidence
    from app.services.intelligence.presets.hr import HR_WEIGHTS

    # Zero everything else; only assessment_battery_coverage should contribute
    score = hr_confidence(
        non_null_fields=0, expected_fields=10,
        interviewer_score_sigma=2.0,
        latest_touchpoint_age_hours=720.0,
        assessments_completed=0,
        assessments_planned=0,  # no battery defined -> coverage = 1.0
    )
    assert score == pytest.approx(HR_WEIGHTS["assessment_battery_coverage"])


def test_hr_confidence_clamps_out_of_band_inputs():
    """Negative counts and fractions > 1 must not break the formula."""
    from app.services.intelligence.presets import hr_confidence

    score = hr_confidence(
        non_null_fields=15,  # > expected -> clamp to 1.0
        expected_fields=10,
        interviewer_score_sigma=-0.5,  # clamp to 0
        latest_touchpoint_age_hours=-100,  # clamp to 0 (fresh)
        assessments_completed=10,  # > planned -> clamp to 1.0
        assessments_planned=4,
    )
    assert 0.0 <= score <= 1.0
    # With all inputs effectively saturating to max, score should be 1.0
    assert score == pytest.approx(1.0)


def test_hr_confidence_returns_float_in_unit_interval():
    """Property: any reasonable input produces a value in [0.0, 1.0]."""
    from app.services.intelligence.presets import hr_confidence

    for non_null, sigma, age, done, planned in [
        (3, 0.5, 100.0, 2, 4),
        (7, 1.2, 480.0, 3, 4),
        (10, 0.1, 1.0, 4, 4),
    ]:
        s = hr_confidence(
            non_null_fields=non_null,
            expected_fields=10,
            interviewer_score_sigma=sigma,
            latest_touchpoint_age_hours=age,
            assessments_completed=done,
            assessments_planned=planned,
        )
        assert 0.0 <= s <= 1.0, f"out of band: {s}"
```

- [ ] **Step 2: Run — should FAIL with ImportError**

```powershell
uv run pytest tests/unit/services/intelligence/test_hr_preset.py -v --tb=short
```

Expected: every test fails on `ImportError: cannot import name 'hr_confidence' from 'app.services.intelligence.presets'`. This is the RED state.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/unit/services/intelligence/test_hr_preset.py
git commit -m "test(118-01): failing unit tests for hr_confidence preset (RED)"
```

### Task 3: Scaffold `hr_confidence` to make tests resolve imports

**Files:**
- Create: `app/services/intelligence/presets/hr.py`
- Modify: `app/services/intelligence/presets/__init__.py`
- Modify: `app/services/intelligence/__init__.py`

- [ ] **Step 1: Create the stub**

```python
"""HR-domain confidence preset.

Phase 118-01 — first agent in the rolling adoption (114–122) to design a
claim schema from scratch (no pre-existing structured output shape like
Sales's LeadQualification or Compliance's RiskAssessment).

The formula weights four signals:
- candidate_data_completeness  (0.35): fraction of expected fields present.
- interviewer_consensus        (0.30): inverted rubric-score sigma across
                                       interviewers (low sigma = high agreement).
- recency                      (0.20): freshness of the latest touchpoint.
- assessment_battery_coverage  (0.15): fraction of planned assessments done;
                                       defaults to 1.0 when no battery is
                                       defined for the role (i.e., zero
                                       planned items is not a penalty).
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

HR_WEIGHTS: dict[str, float] = {
    "candidate_data_completeness": 0.35,
    "interviewer_consensus": 0.30,
    "recency": 0.20,
    "assessment_battery_coverage": 0.15,
}


def hr_confidence(
    non_null_fields: int,
    expected_fields: int,
    interviewer_score_sigma: float,
    latest_touchpoint_age_hours: float,
    assessments_completed: int,
    assessments_planned: int,
    *,
    sigma_saturation: float = 2.0,
    recency_horizon_hours: float = 720.0,
) -> float:
    """Stub — to be implemented in the next step."""
    raise NotImplementedError("scaffold only; see Task 4")
```

- [ ] **Step 2: Update `presets/__init__.py` re-exports**

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula. Phase 118 adds hr_confidence.
"""

from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.hr import hr_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = ["data_confidence", "hr_confidence", "research_confidence"]
```

- [ ] **Step 3: Update top-level `app/services/intelligence/__init__.py`**

```python
# Append to the existing imports and __all__:
from app.services.intelligence.presets import (
    data_confidence,
    hr_confidence,
    research_confidence,
)
```

Add `hr_confidence` to `__all__`.

- [ ] **Step 4: Re-run — tests now fail on NotImplementedError, not ImportError**

```powershell
uv run pytest tests/unit/services/intelligence/test_hr_preset.py -v --tb=short
```

Expected: every test fails with `NotImplementedError: scaffold only`. Imports resolve, signatures match. Good RED state.

- [ ] **Step 5: Commit the scaffold**

```bash
git add app/services/intelligence/presets/hr.py app/services/intelligence/presets/__init__.py app/services/intelligence/__init__.py
git commit -m "feat(118-01): scaffold hr_confidence preset (stub)"
```

### Task 4: Implement `hr_confidence` (GREEN)

**Files:**
- Modify: `app/services/intelligence/presets/hr.py`

- [ ] **Step 1: Replace the stub with the real implementation**

```python
def hr_confidence(
    non_null_fields: int,
    expected_fields: int,
    interviewer_score_sigma: float,
    latest_touchpoint_age_hours: float,
    assessments_completed: int,
    assessments_planned: int,
    *,
    sigma_saturation: float = 2.0,
    recency_horizon_hours: float = 720.0,
) -> float:
    """Compute HR-domain confidence from four candidate-quality signals.

    Args:
        non_null_fields: Count of populated candidate-record fields
            (name, email, resume_url, status, current_stage, source,
            referral_id, ...). The HR table schema's expected-fields set
            is computed by the caller and passed in via expected_fields.
        expected_fields: Total fields the caller expected to see for this
            stage. Used as the denominator for completeness.
        interviewer_score_sigma: Standard deviation of interviewer rubric
            scores (1-5 scale) across all interviewers who have submitted
            for this candidate. Saturates at sigma_saturation (default 2.0)
            -- a sigma of 2.0 on a 1-5 scale means the panel is essentially
            split, which we treat as zero consensus.
        latest_touchpoint_age_hours: Hours since the freshest
            candidate-related event (interview, status update, reference
            check). Linear decay to zero at recency_horizon_hours.
        assessments_completed: Number of planned assessments the candidate
            has finished.
        assessments_planned: Total planned assessments for the role.
            If 0, coverage is treated as 1.0 (no battery is not a penalty).
        sigma_saturation: Sigma value at which consensus drops to zero
            (default 2.0 on a 1-5 rubric).
        recency_horizon_hours: Age at which recency decays to zero
            (default 720 h = 30 days, matching the data preset).

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Notes:
        - All signals are clamped before weighting; out-of-band inputs
          (negative counts, sigma > saturation, age > horizon, completed
          > planned) saturate rather than raise.
        - This mirrors data_confidence's clamp-don't-raise convention so
          callers can pass raw inputs without pre-validation.
    """
    # Signal 1: completeness fraction in [0, 1]
    if expected_fields <= 0:
        completeness = 1.0
    else:
        completeness = max(0.0, min(1.0, non_null_fields / expected_fields))

    # Signal 2: interviewer consensus = 1 - clamped(sigma / saturation)
    clamped_sigma = max(0.0, min(sigma_saturation, interviewer_score_sigma))
    interviewer_consensus = 1.0 - (clamped_sigma / sigma_saturation)

    # Signal 3: recency = 1 - clamped(age / horizon)
    clamped_age = max(0.0, min(recency_horizon_hours, latest_touchpoint_age_hours))
    recency = 1.0 - (clamped_age / recency_horizon_hours)

    # Signal 4: assessment coverage; no-battery -> 1.0
    if assessments_planned <= 0:
        assessment_coverage = 1.0
    else:
        assessment_coverage = max(
            0.0, min(1.0, assessments_completed / assessments_planned)
        )

    return score_confidence(
        inputs={
            "candidate_data_completeness": completeness,
            "interviewer_consensus": interviewer_consensus,
            "recency": recency,
            "assessment_battery_coverage": assessment_coverage,
        },
        weights=HR_WEIGHTS,
    )
```

- [ ] **Step 2: Re-run unit tests — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_hr_preset.py -v --tb=short
```

Expected: 8/8 pass. If `test_hr_confidence_weights_balance` fails by < 1e-4, it's a floating-point artifact — bump `pytest.approx`'s `abs` to 1e-4. If it fails by more, the weights re-export is broken.

- [ ] **Step 3: Run the full intelligence test suite for regression**

```powershell
uv run pytest tests/unit/services/intelligence/ -v --tb=short
```

Expected: all prior tests (data preset, research preset, score_confidence, to_band) still pass alongside the new HR ones.

- [ ] **Step 4: Commit GREEN**

```bash
git add app/services/intelligence/presets/hr.py
git commit -m "feat(118-01): implement hr_confidence preset (GREEN)"
```

### Task 5: Schema design — claim-type vocabulary spec table in the agent module

**Files:**
- Create: `app/services/intelligence/presets/hr_claim_schema.py` — pure-data constants module (no runtime logic)

The claim_type vocabulary lives in code, not in markdown alone, so that Plan 118-02 has importable constants for `claim_type` strings and `entity_type` mappings rather than free-form string literals that could drift.

- [ ] **Step 1: Failing test for the schema constants**

```python
# Append to tests/unit/services/intelligence/test_hr_preset.py:

def test_hr_claim_schema_constants_exist():
    """The claim-type vocabulary is importable as constants."""
    from app.services.intelligence.presets.hr_claim_schema import (
        CANDIDATE_SIGNAL,
        HIRING_PIPELINE_STATE,
        HR_AGENT_ID,
        HR_DOMAIN,
        candidate_entity_canonical_name,
        requisition_entity_canonical_name,
    )

    assert CANDIDATE_SIGNAL == "candidate_signal"
    assert HIRING_PIPELINE_STATE == "hiring_pipeline_state"
    assert HR_AGENT_ID == "hr"
    assert HR_DOMAIN == "hr"


def test_candidate_entity_canonical_name_namespaces_uuids():
    """Candidate entities use a `candidate:<uuid>` namespace prefix."""
    from app.services.intelligence.presets.hr_claim_schema import (
        candidate_entity_canonical_name,
    )

    name = candidate_entity_canonical_name("11111111-1111-1111-1111-111111111111")
    assert name == "candidate:11111111-1111-1111-1111-111111111111"


def test_requisition_entity_canonical_name_namespaces_uuids():
    """Requisitions (jobs) use a `hiring_requisition:<uuid>` prefix."""
    from app.services.intelligence.presets.hr_claim_schema import (
        requisition_entity_canonical_name,
    )

    name = requisition_entity_canonical_name(
        "22222222-2222-2222-2222-222222222222"
    )
    assert name == "hiring_requisition:22222222-2222-2222-2222-222222222222"


def test_terminal_candidate_statuses_set_is_load_bearing():
    """The terminal-status set drives the expires_at lifecycle (Plan 118-02)."""
    from app.services.intelligence.presets.hr_claim_schema import (
        TERMINAL_CANDIDATE_STATUSES,
    )

    assert "hired" in TERMINAL_CANDIDATE_STATUSES
    assert "rejected" in TERMINAL_CANDIDATE_STATUSES
    # offer-extended is NOT terminal -- the lifecycle stops at offer-accept
    # (==hired) or rejection, per spec.
    assert "offer" not in TERMINAL_CANDIDATE_STATUSES
```

- [ ] **Step 2: Run — should FAIL with ImportError**

```powershell
uv run pytest tests/unit/services/intelligence/test_hr_preset.py::test_hr_claim_schema_constants_exist -v
```

Expected: `ImportError`. RED state confirmed.

- [ ] **Step 3: Implement the schema module**

```python
# app/services/intelligence/presets/hr_claim_schema.py

"""HR claim-type vocabulary (Phase 118-01 design).

Centralizes the constants used by Plan 118-02's claim-emission code paths
so claim_type / entity_type / canonical-name shapes don't drift via
string-literal copies across recruitment_service callers.

Two claim types are introduced in Phase 118 -- intentionally small to
validate the abstraction spine on a CRUD-shaped agent before extending:

candidate_signal
    One claim per (candidate, job) pair. freshness_at updates on every
    interaction (application update, interview submission, status change)
    UNTIL the candidate hits a terminal status (hired or rejected), at
    which point expires_at is set to now() and no further updates are
    written.

hiring_pipeline_state
    Periodic snapshot per requisition. Append-only -- each call creates a
    new claim_id. expires_at = now() + 7 days so semantic search prefers
    fresh snapshots over historical ones.
"""

from __future__ import annotations

# Claim-type tags (use these constants, not string literals)
CANDIDATE_SIGNAL = "candidate_signal"
HIRING_PIPELINE_STATE = "hiring_pipeline_state"

# Agent + domain tags
HR_AGENT_ID = "hr"
HR_DOMAIN = "hr"

# Entity-type tags consumed by get_or_create_entity
CANDIDATE_ENTITY_TYPE = "person"
REQUISITION_ENTITY_TYPE = "topic"

# Source kinds (subset of ClaimSource.kind Literal -- no schema extension needed)
SOURCE_KIND_SUPABASE_ROW = "supabase_row"
SOURCE_KIND_USER = "user"

# Terminal candidate statuses that set expires_at on the candidate_signal claim.
# Drives the Plan 118-02 update_candidate_status emission path.
TERMINAL_CANDIDATE_STATUSES: frozenset[str] = frozenset({"hired", "rejected"})

# Hiring pipeline snapshot retention
HIRING_PIPELINE_STATE_TTL_DAYS = 7

# Embedding policy per claim_type
EMBED_CANDIDATE_SIGNAL = True
EMBED_HIRING_PIPELINE_STATE = False


def candidate_entity_canonical_name(candidate_uuid: str) -> str:
    """Build the canonical_name for a candidate's kg_entities row.

    Namespaces candidate UUIDs under ``candidate:`` so they cannot collide
    with real-people entities the agent already knows (investors, board
    members, etc.) in semantic search.
    """
    return f"candidate:{candidate_uuid}"


def requisition_entity_canonical_name(job_uuid: str) -> str:
    """Build the canonical_name for a hiring requisition's kg_entities row."""
    return f"hiring_requisition:{job_uuid}"
```

- [ ] **Step 4: Re-run schema tests — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_hr_preset.py -v --tb=short
```

Expected: all 12 tests pass (8 preset + 4 schema).

- [ ] **Step 5: Commit the schema**

```bash
git add app/services/intelligence/presets/hr_claim_schema.py tests/unit/services/intelligence/test_hr_preset.py
git commit -m "feat(118-01): HR claim-type vocabulary constants + entity-name helpers"
```

### Task 6: Self-improvement engine audit (Decision #8)

**Files:**
- Create: `docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md`

This task produces NO code. It walks `self_improvement_engine.py` + `skill_experiment_evaluator.py` + `docs/self-improvement-policy.md` against the HR agent surface and answers the four audit questions from the pre-flight context above. The output is a notes file that Plan 118-02 reads before emitting any claim.

- [ ] **Step 1: Open the three reference files**

```bash
git grep -n "agent_id\|'hr'\|\"hr\"\|AgentID.HR" app/services/self_improvement_engine.py
git grep -n "agent_id\|'hr'\|\"hr\"\|AgentID.HR" app/services/skill_experiment_evaluator.py
git grep -n "agent_id\|'hr'\|\"hr\"\|AgentID.HR" app/services/self_improvement_settings.py 2>/dev/null
```

If `skill_experiment_evaluator.py` does not exist (Phase 112's spec referenced it; if it was renamed), substitute the actual file. The spec calls out both files by name -- if the rename happened, the audit notes file documents it.

- [ ] **Step 2: Walk the four audit questions and write findings**

The notes file template:

````markdown
# Phase 118-01 — Self-Improvement Engine Audit Notes

**Date:** 2026-05-19
**Scope:** HR Agent (`app/agents/hr/`) entanglement with the
self-improvement engine before Plan 118-02 introduces claim emission.

**Read inputs:**
- `app/services/self_improvement_engine.py`
- `app/services/skill_experiment_evaluator.py` (or its rename, if any)
- `app/services/self_improvement_settings.py`
- `docs/self-improvement-policy.md`

## Q1 — Does the engine bind to HR-specific table / row shape?

[Write findings: e.g., "interaction_logs rows tagged agent_id='hr' are
consumed by `_score_skills_for_period` without any HR-specific branching.
Claim emission in 118-02 will add new `interaction_logs` rows tagged
`agent_id='hr'` that should be benign."]

**Risk:** [low/medium/high] -- justify.
**Mitigation:** [None needed / Plan 118-02 must do X].

## Q2 — Does the engine read HR tool names from `app.agents.hr.tools` by string?

[Write findings: enumerate any string-literal references to HR tool names.
The tool list per `_TOOL_IDS` in tools.py is: create_job, get_job,
update_job, list_jobs, add_candidate, update_candidate_status,
list_candidates, generate_job_description, generate_interview_questions,
get_hiring_funnel, assign_training, post_job_board,
auto_generate_onboarding, get_team_org_chart.]

**Risk:** [low/medium/high]
**Mitigation:** [Plan 118-02 must not rename / remove these tools].

## Q3 — Does `skill_experiment_evaluator` reference HR skill names?

The HR agent's instructions.md uses these skills:
- resume_screening
- interview_question_generator
- employee_turnover_analysis
- onboarding_checklist
- performance_review_framework
- compensation_benchmarking

[Write findings: which of these the experiment evaluator hard-codes, if any.]

**Risk:** [low/medium/high]
**Mitigation:** [None needed / explicit].

## Q4 — Does the engine assume HR outputs are NOT claims?

[Write findings: e.g., "No `claim_coverage` metric exists yet in the
engine; the engine scores skills on positive/completion/escalation/retry
weights only. Claim emission adds no new column the engine reads."]

**Risk:** [low/medium/high]
**Mitigation:** [None needed].

## Summary

| Question | Risk | Plan 118-02 must... |
|---|---|---|
| Q1 (table binding) | ... | ... |
| Q2 (tool names) | ... | ... |
| Q3 (skill names) | ... | ... |
| Q4 (claim assumption) | ... | ... |

## Policy compliance check (docs/self-improvement-policy.md)

- [ ] Plan 118-02 stays within the **autonomy boundary** (engine may
      adjust skill weights but not modify HR tool implementations).
- [ ] The **A/B eval harness invariants** are not changed -- no new
      experiment row shapes introduced.
- [ ] The **rollback contract** holds: if Plan 118-02 must be reverted,
      the `kg_findings` rows it wrote are flagged stale, not deleted
      retroactively (the engine has no claim-deletion path).

End of audit.
````

Fill in the bracketed findings with the actual code observations. Be honest -- if the engine has zero HR entanglement, document "zero entanglement" rather than padding.

- [ ] **Step 3: Commit the audit notes**

```bash
git add docs/superpowers/plans/2026-05-19-shared-intelligence-infra-118-01-self-improvement-audit-notes.md
git commit -m "docs(118-01): self-improvement engine audit for HR adoption (Decision #8)"
```

### Task 7: Lint + final formatting

- [ ] **Step 1: Ruff check + format**

```powershell
uv run ruff check app/services/intelligence/presets/hr.py app/services/intelligence/presets/hr_claim_schema.py app/services/intelligence/presets/__init__.py app/services/intelligence/__init__.py tests/unit/services/intelligence/test_hr_preset.py
uv run ruff format app/services/intelligence/presets/hr.py app/services/intelligence/presets/hr_claim_schema.py app/services/intelligence/presets/__init__.py app/services/intelligence/__init__.py tests/unit/services/intelligence/test_hr_preset.py --check
```

Fix any issues in place. Common gotchas observed in earlier Phase 113 plans:
- D-rule docstring formatting (first line summary)
- Unicode dashes/quotes in docstrings -- replace with ASCII (`--` not `—`)
- Sorted `__all__` entries

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/services/intelligence/presets/hr.py app/services/intelligence/presets/hr_claim_schema.py
```

Expected: clean. If `ty` complains about untyped return, add explicit `-> float`.

- [ ] **Step 3: Run the broader intelligence suite one more time as a regression gate**

```powershell
uv run pytest tests/unit/services/intelligence/ -v
```

Expected: all green. If a prior plan's test fails, that's pre-existing -- surface it but do not fix in this plan.

- [ ] **Step 4: Commit any lint fixes**

```bash
git add -u app/services/intelligence/ tests/unit/services/intelligence/
git diff --cached --quiet || git commit -m "style(118-01): ruff lint + format for HR preset and schema"
```

(The `git diff --cached --quiet || git commit` idiom skips the commit silently if nothing changed.)

### Task 8: Plan 118-01 acceptance sign-off

- [ ] **Step 1: Cross-check spec acceptance**

| Spec acceptance line (Phase 118) | Verified by |
|---|---|
| HR Agent test suite green | Task 4 Step 3 + existing `tests/unit/agents/hr/` (unchanged) |
| `hr_confidence` preset shipped with documented weights | Tasks 3-4 |
| `presets/hr.py` re-exported from `app.services.intelligence.presets` | Task 3 Step 2 |
| Claim-type vocabulary designed: `candidate_signal`, `hiring_pipeline_state` | Task 5 (constants module) |
| `freshness_at` update pattern designed (not implemented -- Plan 118-02) | Task 5 (`TERMINAL_CANDIDATE_STATUSES` constant + docstring) |
| Self-improvement engine audit (Decision #8) complete | Task 6 |
| All HR outputs carry confidence + band | Deferred to Plan 118-02 (this plan only ships the preset; emission is 118-02) |
| `search_claims_semantic` returns HR claims | Deferred to Plan 118-02 |

- [ ] **Step 2: Plan 118-01 complete.** Next: Plan 118-02 -- claim emission, lifecycle wiring, integration tests.

The schema constants module (`hr_claim_schema.py`) and the audit notes file are the load-bearing handoffs to Plan 118-02. If either is missing or hand-waves the answers, Plan 118-02 lacks the design surface to do its job correctly.

---

## Spec coverage check

| Spec requirement (Phase 118 § HR Agent adoption) | Task(s) |
|---|---|
| `presets/hr.py` with documented weights | Tasks 3, 4 |
| `HR_WEIGHTS` = {0.35, 0.30, 0.20, 0.15} matching the spec | Task 4 + test `test_hr_confidence_weights_balance` |
| Claim schema designed FROM SCRATCH (no pre-existing structured shape) | Task 5 (constants module + canonical-name helpers) |
| `candidate_signal` claim_type defined | Task 5 (`CANDIDATE_SIGNAL` constant) |
| `hiring_pipeline_state` claim_type defined | Task 5 (`HIRING_PIPELINE_STATE` constant) |
| candidate_signal terminal lifecycle (hired/rejected) | Task 5 (`TERMINAL_CANDIDATE_STATUSES` set) |
| Self-improvement engine audit (Decision #8) | Task 6 |
| Audit covers `self_improvement_engine.py` + `skill_experiment_evaluator.py` | Task 6 Step 1-2 |
| Per `docs/self-improvement-policy.md` invariants | Task 6 (policy compliance check) |
| Two sub-plans only (no external cache) | This plan + 118-02; no 118-03 |
| Lint clean | Task 7 |

All Phase 118 design lines covered. Emission, lifecycle wiring, and integration tests land in Plan 118-02.

---

## Handoff to Plan 118-02

Plan 118-02 imports the following from this plan's deliverables:

```python
from app.services.intelligence.presets import hr_confidence
from app.services.intelligence.presets.hr_claim_schema import (
    CANDIDATE_SIGNAL,
    HIRING_PIPELINE_STATE,
    HR_AGENT_ID,
    HR_DOMAIN,
    CANDIDATE_ENTITY_TYPE,
    REQUISITION_ENTITY_TYPE,
    SOURCE_KIND_SUPABASE_ROW,
    SOURCE_KIND_USER,
    TERMINAL_CANDIDATE_STATUSES,
    HIRING_PIPELINE_STATE_TTL_DAYS,
    EMBED_CANDIDATE_SIGNAL,
    EMBED_HIRING_PIPELINE_STATE,
    candidate_entity_canonical_name,
    requisition_entity_canonical_name,
)
```

Plan 118-02 reads the audit notes file (Task 6) before deciding where in the HR tool callstack to insert claim writes -- the audit answers determine whether 118-02 emits *inside* the existing tool functions or wraps them externally.

If the audit found a load-bearing entanglement (e.g., `self_improvement_engine` enumerates HR tools by string), Plan 118-02's first task is to thread that constraint through the emission design rather than discover it mid-implementation.
