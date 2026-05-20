# Shared Intelligence Infrastructure — Plan 121-01: Strategic preset + edges architecture + self-improvement audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `presets/strategic.py` with the `strategic_confidence` weighted scorer, wire the four Strategic sub-agents (BraindumpPipeline, ResearchSuite, KnowledgeVaultAgent, InitiativeOpsAgent) so their consensus drives the preset's `sub_agent_consensus` signal, decide how Strategic claims reference prior-agent claims via the existing `kg_findings` columns (the "edges-heavy architecture" question), and audit `app/services/self_improvement_engine.py` + `skill_experiment_evaluator.py` per Decision #8 before any claim-emission code lands in Plan 121-02.

**Architecture:** Strategic is unique among the 114-122 cohort because it is an **orchestrator over four sub-agents**, not a domain expert that produces novel facts. Its valuable claims (`cross_domain_risk_consolidation`, `priority_assessment`, `strategic_decision`) are *synthesis* over prior-agent claims emitted by Financial, Sales, Compliance, Marketing, HR, Customer Support, Operations, Data, Research, and Content. This plan settles two coupled architectural questions:

1. **Confidence preset shape** — weights bound to sub-agent consensus rather than direct evidence, because Strategic rarely touches raw evidence itself.
2. **Edges representation** — how a Strategic claim "points at" the ≥3 prior-agent claims it consolidates, without inventing a new column on `kg_findings`.

After investigation (see `spec-112-113-predecessor.md` § Module specifications), the cleanest answer to (2) is to **reuse the existing `sources` JSONB column** with a new `ClaimSource.kind="claim_ref"` literal value. The `contradicts` JSONB column carries opposition semantics (named for and used by `detect_contradictions`) — repurposing it for "references" would corrupt the existing contradiction-detection signal. The `edge_id` foreign key on `kg_findings` points at `kg_edges` (entity-to-entity relationships), not at sibling findings. `sources` is already a JSONB array of arbitrary-kind references with optional `score` — extending its `kind` Literal is a one-line schema-free change.

**Tech Stack:** `app/services/intelligence/presets/strategic.py` (new), `app/services/intelligence/presets/__init__.py` (extend), `app/services/intelligence/schemas.py` (extend `ClaimSource.kind` Literal), `app/agents/strategic/agent.py` (instructions tighten only; no factory change), property-based tests via `hypothesis`.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 121 — Strategic Agent adoption · Decisions #5 (Strategic order-dependency), #8 (per-phase self-improvement audit) · Risk register row "Self-improvement engine entanglement"

**Out of scope:**
- Strategic claim emission code (lives in Plan 121-02)
- `cross_domain_risk_consolidation` synthesis logic (Plan 121-02)
- New ADK tools (none added in Phase 121; Strategic claims emit from library-internal callers per Decision #7 of the predecessor spec)
- Calibration of `STRATEGIC_WEIGHTS` against telemetry (deferred; weights ship as educated guesses)
- Cache integration (Strategic doesn't call external APIs directly — sub-agents do that)
- Migration of `kg_findings` schema (we are deliberately avoiding a new column; the audit step verifies that `sources` + new `kind` literal is sufficient)

---

## File structure

**Create:**
- `app/services/intelligence/presets/strategic.py` — `STRATEGIC_WEIGHTS` constant + `strategic_confidence(...)` callable
- `tests/unit/services/intelligence/test_strategic_preset.py` — property + unit tests for the preset
- `docs/intelligence/strategic-edges-architecture-decision.md` — short ADR documenting why we chose `sources[].kind="claim_ref"` over a new column, a new edges relation, or repurposing `contradicts`
- `docs/intelligence/self-improvement-audit-121.md` — audit report listing every symbol in `self_improvement_engine.py` + `skill_experiment_evaluator.py` that the Strategic adoption touches, with a verdict per symbol (no-op / shim required / refactor required)

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `strategic_confidence`
- `app/services/intelligence/schemas.py` — extend `ClaimSource.kind` Literal to include `"claim_ref"`
- `app/agents/strategic/agent.py` — no code change, but `instructions.md` adds a paragraph telling the director that any output worth recalling (decisions, priorities, milestones, consolidations, journey-readiness) must be persisted as a Claim via the Plan 121-02 callable, and that those Claims carry `sources=[ClaimSource(kind="claim_ref", ref=str(prior_claim_uuid))]` when synthesizing prior-agent findings

---

## Pre-flight context

`strategic_confidence` signature:
```python
def strategic_confidence(
    sub_agent_consensus: float,
    evidence_breadth: float,
    recency_of_input: float,
    stakeholder_validation_signal: float,
) -> float
```

All four arguments must be in `[0.0, 1.0]` and are blended via the shared `score_confidence(...)` machinery (predecessor spec § `confidence.py`). Weights:

```python
STRATEGIC_WEIGHTS = {
    "sub_agent_consensus":           0.40,
    "evidence_breadth":              0.30,
    "recency_of_input":              0.20,
    "stakeholder_validation_signal": 0.10,
}
```

Signal interpretations (load-bearing — these are the contract the call sites in Plan 121-02 implement against):

| Signal | What it measures | How a caller computes it |
|---|---|---|
| `sub_agent_consensus` | Fraction of the four sub-agents that produced a coherent, non-conflicting output for the synthesis question | `agreeing_sub_agents / 4.0`, where "agreeing" means the sub-agent emitted a claim/finding pointing in the same direction as the strategic synthesis. If only Research and InitiativeOps weighed in and they agreed → `2/4 = 0.5`. Solo orchestrations (e.g. `advance_initiative_phase` called directly) report `1.0` because there is no consensus question. |
| `evidence_breadth` | Diversity of prior-agent claims referenced by the synthesis | `min(1.0, distinct_agent_ids_in_sources / 3.0)`. The acceptance criterion `cross_domain_risk_consolidation` ≥3 distinct agent_ids saturates this signal at exactly the threshold. Below 3 → `<1.0`. |
| `recency_of_input` | Freshness of the prior-agent claims being synthesized | `max(0.0, 1.0 - mean_input_age_days / 30.0)`. Inputs averaging 0 days old → `1.0`; averaging 30 days → `0.0`. Identical decay shape to `data_confidence.recency` for consistency. |
| `stakeholder_validation_signal` | Whether a human reviewed/approved the synthesis before storage | `1.0` if the synthesis comes from an `approve_workflow_step`-gated path or an InitiativeOps phase advance the user explicitly accepted; `0.5` if the boardroom debate (`convene_board_meeting`) produced a majority verdict without explicit user sign-off; `0.0` for unsupervised director output. |

Strategic's adoption is **edges-heavy, not text-heavy**. The director rarely writes new prose into `finding_text` that is not already present in a prior claim. Two patterns dominate:

1. **Pure pointer claim** (`cross_domain_risk_consolidation`): `finding_text` is a one-line synthesis ("Pricing change increases churn risk per CS + Sales + Compliance signals"); `sources` is the load-bearing payload — 3+ entries with `kind="claim_ref"` pointing at the prior claims.
2. **Decision claim** (`strategic_decision`): `finding_text` carries the go/no-go verbatim; `sources` lists the prior claims that informed it.

Acceptance bar (from the design spec):
- `strategic_confidence(...)` clamped to `[0.0, 1.0]` on all inputs
- Weights sum to exactly `1.0` (validated by the property test)
- Public re-export from `app.services.intelligence.presets`
- `ClaimSource.kind` accepts `"claim_ref"` (verified by Pydantic round-trip test)
- Audit doc exists and is referenced by 121-02
- No regression in existing Strategic agent test suite

Environment quirks: same as Plan 113-05. Property tests use `hypothesis` (already in dev deps per `pyproject.toml`).

---

## Tasks

### Task 1: Pre-flight + self-improvement engine audit (Decision #8)

**Files:**
- Create: `docs/intelligence/self-improvement-audit-121.md`

The predecessor spec's Decision #8 ("Each phase's *first* sub-plan audits self-improvement engine entanglement") is structural — we audit *before* touching code, because the engine's bindings to current Strategic shapes determine whether we can ship Plan 121-02 freely or whether we need shims.

- [ ] **Step 1: Confirm prerequisites**

```powershell
uv run python -c "from app.services.intelligence import score_confidence, write_claim, find_claims; print('ok')"
uv run python -c "from app.services.intelligence.presets import data_confidence, research_confidence; print('ok')"
uv run python -c "from app.services.intelligence.schemas import ClaimSource; print(ClaimSource.model_fields['kind'].annotation)"
```

Expected: all three commands print `ok` / the `kind` Literal type. If any fails, Phase 113 has not landed on this branch and Plan 121-01 cannot start — abort and rebase onto a branch with Plan 113-05 merged.

- [ ] **Step 2: Grep self-improvement engine for Strategic bindings**

```powershell
uv run python -c "import inspect; from app.services import self_improvement_engine as s; print(inspect.getsourcefile(s))"
```

Then use the Grep tool (NOT raw rg/grep) to enumerate every symbol the engine pins to Strategic:

```
pattern: "STR|strategic|StrategicPlanning|create_strategic"
path: app/services/self_improvement_engine.py
output_mode: content
-n: true
```

Expected hits include (per `app/services/self_improvement_engine.py:1577-1593`):
- The `_agent_id_to_domain` mapping `{"STR": "strategic", "EXEC": "strategic"}`
- Any call site that dispatches per-agent skill refinement keyed on `agent_id == "STR"`

Repeat for `app/services/skill_experiment_evaluator.py`.

- [ ] **Step 3: Classify each hit**

For each matched symbol, classify it as one of:

| Class | Meaning | Action in Plan 121-02 |
|---|---|---|
| **Stable** | Binds to `agent_id="STR"` or the `strategic` domain string; not affected by claim-shape changes | No action. Strategic claim emission preserves both. |
| **Shape-coupled** | Reads from a per-agent skill manifest, instructions file, or tool list whose layout this plan changes | Coordinate change in 121-02 or add a shim. |
| **Refactor-required** | Hard-codes Strategic tool names or sub-agent class names that will be renamed | Stop. Rename plan first, then proceed. |

The expectation, based on a read of the file at HEAD: every hit is **Stable**. `_agent_id_to_domain` is a one-way string map and Plan 121-02 preserves the `STR → strategic` mapping; nothing in this plan or 121-02 renames sub-agent classes or removes tools from the manifest. Document the verdict.

- [ ] **Step 4: Write `docs/intelligence/self-improvement-audit-121.md`**

Use the structure from the predecessor audit (which the 112-05 plan produced) verbatim — one section per file, one row per symbol, columns `Symbol | Line | Class | Notes`. Close with an explicit verdict line:

```markdown
## Verdict

All entanglement points in `self_improvement_engine.py` and `skill_experiment_evaluator.py`
are **Stable** against the Plan 121-02 Strategic adoption. No shims required. No
refactor required. Plan 121-02 may proceed.
```

If any row is **Shape-coupled** or **Refactor-required**, the verdict must enumerate the mitigation before 121-02 starts.

- [ ] **Step 5: Commit**

```bash
git add docs/intelligence/self-improvement-audit-121.md
git commit -m "docs(121-01): self-improvement engine audit for Strategic adoption"
```

### Task 2: Edges architecture decision record

**Files:**
- Create: `docs/intelligence/strategic-edges-architecture-decision.md`

This is the **edges-heavy architecture design** decision called out in the user request: how does `write_claim` reference prior-agent claims via the `edges` relation? The ADR settles it on paper before the preset (Task 3) ships, so that Task 4 (extending `ClaimSource.kind`) does not feel arbitrary.

- [ ] **Step 1: Enumerate the candidate mechanisms**

For the ADR's "Considered alternatives" section, write out exactly four options and the trade-off table:

| Option | Mechanism | Pros | Cons |
|---|---|---|---|
| **A. New `references` JSONB column** | `ALTER TABLE kg_findings ADD COLUMN references JSONB NOT NULL DEFAULT '[]'` plus `Claim.references: list[UUID]` | Explicit semantics; symmetric to `contradicts`; queryable | Requires a migration; touches the public schema for one agent's needs; predecessor spec said "no migration of existing data" was a design goal |
| **B. Repurpose `contradicts`** | Store Strategic's `sources_claim_ids` in `contradicts` and document the dual meaning | Zero schema change | Poisons `detect_contradictions` — it treats `contradicts` as opposition, and a Strategic claim referencing a Sales lead-score would auto-flag the lead-score as contradictory to itself; semantics break |
| **C. New `kg_edges` rows finding-to-finding** | Insert `kg_edges` rows pointing from Strategic's owning entity to each prior claim's owning entity, then walk edges at read time | Honours the graph model | `kg_edges` are entity↔entity; finding↔finding is not modelled and the unique constraint `(source_id, target_id, relationship, domain)` would collide on repeated synthesis; adds two writes per claim |
| **D. Reuse `sources` with new `kind="claim_ref"`** | Extend `ClaimSource.kind` Literal; store `{"kind": "claim_ref", "ref": str(uuid)}` per prior claim | Zero schema change; `sources` is already JSONB array semantics; symmetric to URL/Stripe-row/Supabase-row patterns; read-time parse is a one-line UUID conversion | Slight overload of `sources` — historically a "provenance" field, now also "synthesis input" — but the conceptual stretch is small (a referenced prior claim *is* a source for the synthesis) |

- [ ] **Step 2: Choose Option D and justify**

Write the "Decision" section: chosen mechanism is **Option D**. Rationale:

1. Phase 112's predecessor spec explicitly chose `kg_findings` extension only via `agent_id` + `claim_type` and called out "no migration of existing data" — a new column conflicts with that.
2. `ClaimSource` already models references with `kind` + `ref` + optional `score`. Adding `"claim_ref"` to the Literal is a one-line backward-compatible change (existing rows continue to parse).
3. Reading is mechanical: `[UUID(s.ref) for s in claim.sources if s.kind == "claim_ref"]`.
4. The integration test in Plan 121-02 verifies the ≥3-distinct-agent_ids acceptance criterion by joining `claim.sources` UUIDs against `find_claims(entity_id=..., agent_id=...)` per reference — no SQL changes needed.

- [ ] **Step 3: Document the read path**

Add a "Read path" section showing exactly how a Strategic claim consumer reconstructs the consolidated graph:

```python
async def expand_strategic_claim(claim: Claim) -> dict[str, list[Claim]]:
    """Resolve a Strategic claim's sources[].kind=='claim_ref' UUIDs into Claim objects.

    Returns a dict keyed by referenced agent_id (e.g. 'sales', 'cs', 'compliance')
    containing the prior-agent claims that informed this synthesis.
    """
    from app.services.intelligence import find_claims
    from collections import defaultdict

    prior_ids = [
        UUID(s.ref) for s in claim.sources
        if s.kind == "claim_ref"
    ]
    by_agent: dict[str, list[Claim]] = defaultdict(list)
    for pid in prior_ids:
        # find_claims has no by-id filter; the cheapest route is one query
        # per UUID using entity_id+min_confidence=0 and filter the result.
        # For production we'd add a get_claim_by_id helper; out of scope
        # for this ADR (Plan 121-02 will inline that helper if needed).
        ...
    return dict(by_agent)
```

The ADR notes that **`find_claims` does not currently accept an `id` filter** — Plan 121-02 may add `get_claim_by_id(claim_id: UUID)` to `claims.py` if the integration test needs it, but it is not a 121-01 deliverable. The ADR makes the read-path concrete enough that the absence is obvious.

- [ ] **Step 4: Document the degrade-gracefully contract**

Add a "Missing prior claim" section: when a `claim_ref` UUID resolves to no row (because the prior claim was deleted or never written), the Strategic claim must not raise. The consumer treats the missing reference as a zero-confidence input, which lowers `evidence_breadth` (fewer than 3 distinct agents resolved) and therefore lowers the Strategic claim's own confidence on the next refresh. This matches the design spec acceptance line: "Strategic claims that depend on prior-agent claims fail gracefully if those claims are missing (degrade to lower confidence, not exception)."

- [ ] **Step 5: Commit**

```bash
git add docs/intelligence/strategic-edges-architecture-decision.md
git commit -m "docs(121-01): ADR for Strategic edges via sources[].kind=claim_ref"
```

### Task 3: Implement `strategic_confidence` preset (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_strategic_preset.py`
- Create: `app/services/intelligence/presets/strategic.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Failing unit + property tests**

```python
"""Unit + property tests for the Strategic confidence preset."""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st


def test_strategic_preset_imports_from_public_surface():
    """strategic_confidence is reachable from app.services.intelligence.presets."""
    from app.services.intelligence.presets import strategic_confidence

    assert callable(strategic_confidence)


def test_strategic_weights_sum_to_one():
    """STRATEGIC_WEIGHTS sums to exactly 1.0 — the score_confidence contract."""
    from app.services.intelligence.presets.strategic import STRATEGIC_WEIGHTS

    assert abs(sum(STRATEGIC_WEIGHTS.values()) - 1.0) < 1e-9


def test_strategic_weights_match_spec():
    """Weights match the design-spec values exactly."""
    from app.services.intelligence.presets.strategic import STRATEGIC_WEIGHTS

    assert STRATEGIC_WEIGHTS == {
        "sub_agent_consensus": 0.40,
        "evidence_breadth": 0.30,
        "recency_of_input": 0.20,
        "stakeholder_validation_signal": 0.10,
    }


def test_all_perfect_inputs_returns_one():
    """All signals at 1.0 → confidence 1.0."""
    from app.services.intelligence.presets import strategic_confidence

    assert strategic_confidence(
        sub_agent_consensus=1.0,
        evidence_breadth=1.0,
        recency_of_input=1.0,
        stakeholder_validation_signal=1.0,
    ) == pytest.approx(1.0)


def test_all_zero_inputs_returns_zero():
    """All signals at 0.0 → confidence 0.0."""
    from app.services.intelligence.presets import strategic_confidence

    assert strategic_confidence(
        sub_agent_consensus=0.0,
        evidence_breadth=0.0,
        recency_of_input=0.0,
        stakeholder_validation_signal=0.0,
    ) == pytest.approx(0.0)


def test_consensus_dominates():
    """sub_agent_consensus carries the largest weight (0.40)."""
    from app.services.intelligence.presets import strategic_confidence

    only_consensus = strategic_confidence(
        sub_agent_consensus=1.0,
        evidence_breadth=0.0,
        recency_of_input=0.0,
        stakeholder_validation_signal=0.0,
    )
    only_breadth = strategic_confidence(
        sub_agent_consensus=0.0,
        evidence_breadth=1.0,
        recency_of_input=0.0,
        stakeholder_validation_signal=0.0,
    )
    assert only_consensus > only_breadth  # 0.40 > 0.30


def test_breadth_threshold_at_three_agents():
    """Evidence breadth saturates at exactly 3 distinct agents per spec.

    The breadth signal is computed at the call site, not inside the preset;
    this test documents the saturation contract so call-site formulae line up.
    Caller is expected to pass: min(1.0, distinct_agent_ids / 3.0).
    """
    from app.services.intelligence.presets import strategic_confidence

    breadth_2 = min(1.0, 2 / 3.0)
    breadth_3 = min(1.0, 3 / 3.0)
    breadth_5 = min(1.0, 5 / 3.0)

    c2 = strategic_confidence(1.0, breadth_2, 1.0, 1.0)
    c3 = strategic_confidence(1.0, breadth_3, 1.0, 1.0)
    c5 = strategic_confidence(1.0, breadth_5, 1.0, 1.0)

    # 3 agents should give max breadth contribution; 5 agents same as 3.
    assert c3 == pytest.approx(c5)
    assert c3 > c2


@given(
    consensus=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    breadth=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    recency=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    stakeholder=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_output_in_unit_interval(consensus, breadth, recency, stakeholder):
    """Output is always clamped to [0.0, 1.0] for any valid input."""
    from app.services.intelligence.presets import strategic_confidence

    result = strategic_confidence(
        sub_agent_consensus=consensus,
        evidence_breadth=breadth,
        recency_of_input=recency,
        stakeholder_validation_signal=stakeholder,
    )
    assert 0.0 <= result <= 1.0


@given(
    consensus_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    consensus_b=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    breadth=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_monotonic_in_consensus(consensus_a, consensus_b, breadth):
    """Holding other signals fixed, higher consensus → higher confidence."""
    from app.services.intelligence.presets import strategic_confidence

    if consensus_a == consensus_b:
        return  # trivially equal

    lo, hi = sorted([consensus_a, consensus_b])
    c_lo = strategic_confidence(lo, breadth, 0.5, 0.5)
    c_hi = strategic_confidence(hi, breadth, 0.5, 0.5)
    assert c_hi >= c_lo


def test_negative_input_rejected():
    """Out-of-range inputs raise ValueError (programming error)."""
    from app.services.intelligence.presets import strategic_confidence

    with pytest.raises(ValueError):
        strategic_confidence(
            sub_agent_consensus=-0.1,
            evidence_breadth=0.5,
            recency_of_input=0.5,
            stakeholder_validation_signal=0.5,
        )


def test_above_one_input_rejected():
    """Out-of-range inputs raise ValueError."""
    from app.services.intelligence.presets import strategic_confidence

    with pytest.raises(ValueError):
        strategic_confidence(
            sub_agent_consensus=0.5,
            evidence_breadth=1.01,
            recency_of_input=0.5,
            stakeholder_validation_signal=0.5,
        )
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_strategic_preset.py -v --tb=short
```

Expected: every test fails with `ModuleNotFoundError` / `ImportError` for `strategic_confidence`. Capture the failure output.

- [ ] **Step 3: Implement `presets/strategic.py`**

Create `app/services/intelligence/presets/strategic.py`:

```python
"""Strategic-domain confidence preset.

Phase 121-01 — adopted by `app/agents/strategic/agent.py` for synthesis claims
(``initiative_milestone``, ``strategic_decision``, ``priority_assessment``,
``cross_domain_risk_consolidation``, ``journey_workflow_readiness``).

The formula weights four signals:
- sub_agent_consensus       (0.40): fraction of the four sub-agents agreeing
                                    on the synthesis direction (0.0 to 1.0)
- evidence_breadth          (0.30): caller passes ``min(1.0, distinct_agent_ids / 3.0)``
                                    where distinct_agent_ids counts unique
                                    prior-agent ids referenced via
                                    ``sources[].kind == "claim_ref"``. Saturates
                                    at the cross-domain threshold (3).
- recency_of_input          (0.20): ``max(0.0, 1.0 - mean_input_age_days / 30.0)``;
                                    30-day horizon matches data_confidence
- stakeholder_validation_signal (0.10): 1.0 if a human approved the synthesis;
                                        0.5 if boardroom-debate majority; 0.0 if
                                        unsupervised director output

Strategic rarely produces novel evidence — its claims point at prior-agent
claims via the existing ``sources`` JSONB column with the new
``claim_ref`` kind (see docs/intelligence/strategic-edges-architecture-decision.md).
The preset is therefore weighted toward *synthesis quality* (consensus +
breadth) rather than primary-evidence quality (the Financial / Data shape).

Out-of-range inputs raise ValueError — they indicate a programming error at
the caller and must surface immediately rather than be silently clamped.
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

STRATEGIC_WEIGHTS: dict[str, float] = {
    "sub_agent_consensus": 0.40,
    "evidence_breadth": 0.30,
    "recency_of_input": 0.20,
    "stakeholder_validation_signal": 0.10,
}


def strategic_confidence(
    sub_agent_consensus: float,
    evidence_breadth: float,
    recency_of_input: float,
    stakeholder_validation_signal: float,
) -> float:
    """Compute Strategic-domain confidence from synthesis-quality signals.

    Args:
        sub_agent_consensus: Fraction in [0.0, 1.0] of sub-agents (out of 4)
            that produced a coherent, non-conflicting output for the
            synthesis question. Solo orchestrations report 1.0.
        evidence_breadth: Saturating breadth signal in [0.0, 1.0]. Callers
            compute ``min(1.0, distinct_agent_ids / 3.0)`` so that 3+
            distinct prior-agent claims yield the maximum contribution.
        recency_of_input: Freshness signal in [0.0, 1.0] computed as
            ``max(0.0, 1.0 - mean_input_age_days / 30.0)``.
        stakeholder_validation_signal: Human-validation signal in
            [0.0, 1.0]. 1.0 if a human approved; 0.5 if boardroom-debate
            majority; 0.0 if unsupervised director output.

    Returns:
        Confidence score in [0.0, 1.0].

    Raises:
        ValueError: If any input is outside [0.0, 1.0] (programming error).
    """
    for name, value in (
        ("sub_agent_consensus", sub_agent_consensus),
        ("evidence_breadth", evidence_breadth),
        ("recency_of_input", recency_of_input),
        ("stakeholder_validation_signal", stakeholder_validation_signal),
    ):
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"strategic_confidence: {name}={value!r} outside [0.0, 1.0]"
            )

    return score_confidence(
        inputs={
            "sub_agent_consensus": sub_agent_consensus,
            "evidence_breadth": evidence_breadth,
            "recency_of_input": recency_of_input,
            "stakeholder_validation_signal": stakeholder_validation_signal,
        },
        weights=STRATEGIC_WEIGHTS,
    )
```

- [ ] **Step 4: Re-export from `presets/__init__.py`**

Open `app/services/intelligence/presets/__init__.py` and append `strategic_confidence` to both the import block and `__all__`:

```python
from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.research import research_confidence
from app.services.intelligence.presets.strategic import strategic_confidence

__all__ = ["data_confidence", "research_confidence", "strategic_confidence"]
```

- [ ] **Step 5: Run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_strategic_preset.py -v --tb=short
```

Expected: all 10 tests pass (8 named + 2 Hypothesis property tests, the latter shrinking to no counterexample within Hypothesis's default budget). If `test_monotonic_in_consensus` flakes on equal inputs, the `if consensus_a == consensus_b: return` guard already covers it — re-run to confirm not a real bug.

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/presets/strategic.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_strategic_preset.py
git commit -m "feat(121-01): strategic_confidence preset + property tests (GREEN)"
```

### Task 4: Extend `ClaimSource.kind` to accept `"claim_ref"`

**Files:**
- Modify: `app/services/intelligence/schemas.py`
- Modify: `tests/unit/services/intelligence/test_schemas.py` (create if absent; otherwise extend)

This is the **schema-free edges representation** — extending the existing `ClaimSource.kind` Literal so Strategic claims can record `{"kind": "claim_ref", "ref": str(uuid)}` entries in their `sources` JSONB column without any DB migration.

- [ ] **Step 1: Failing test**

Create or extend `tests/unit/services/intelligence/test_schemas.py`:

```python
"""Tests for the intelligence package schemas."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_claim_source_accepts_claim_ref():
    """ClaimSource.kind accepts the new 'claim_ref' literal."""
    from app.services.intelligence.schemas import ClaimSource

    s = ClaimSource(kind="claim_ref", ref=str(uuid4()))
    assert s.kind == "claim_ref"


def test_claim_source_rejects_unknown_kind():
    """Unknown kinds still raise — the Literal is exhaustive."""
    from app.services.intelligence.schemas import ClaimSource

    with pytest.raises(ValidationError):
        ClaimSource(kind="not_a_real_kind", ref="x")  # type: ignore[arg-type]


def test_claim_source_existing_kinds_still_work():
    """Existing literals (url, stripe_row, etc.) continue to validate."""
    from app.services.intelligence.schemas import ClaimSource

    for kind in (
        "url", "supabase_row", "stripe_row", "shopify_row",
        "regulation", "user", "other",
    ):
        s = ClaimSource(kind=kind, ref="x")
        assert s.kind == kind


def test_claim_source_claim_ref_roundtrip_via_dict():
    """JSONB round-trip preserves the claim_ref kind."""
    from app.services.intelligence.schemas import ClaimSource

    src_uuid = str(uuid4())
    original = ClaimSource(kind="claim_ref", ref=src_uuid, score=0.85)
    as_dict = original.model_dump(exclude_none=True)
    restored = ClaimSource(**as_dict)
    assert restored.kind == "claim_ref"
    assert restored.ref == src_uuid
    assert restored.score == 0.85
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_schemas.py::test_claim_source_accepts_claim_ref -v --tb=short
```

Expected: `ValidationError: ... Input should be 'url', 'supabase_row', ..., 'other'` (claim_ref not in the Literal yet).

- [ ] **Step 3: Extend the Literal in `schemas.py`**

Locate the `ClaimSource` class and extend its `kind` field:

```python
class ClaimSource(BaseModel):
    """A source backing a claim. Domain-agnostic.

    The ``claim_ref`` kind is used by Strategic synthesis claims (Phase 121)
    to point at prior-agent claims via UUID. See
    docs/intelligence/strategic-edges-architecture-decision.md for the
    edges-architecture rationale.
    """

    kind: Literal[
        "url",
        "supabase_row",
        "stripe_row",
        "shopify_row",
        "regulation",
        "user",
        "claim_ref",   # NEW: reference to another kg_findings row by UUID
        "other",
    ]
    ref: str
    score: float | None = None
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_schemas.py -v --tb=short
```

Expected: all 4 tests pass. Run the broader intelligence test suite to confirm no regression on existing kinds:

```powershell
uv run pytest tests/unit/services/intelligence/ -v --tb=short
```

Expected: every existing test still passes (claim_ref is additive, not breaking).

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/schemas.py tests/unit/services/intelligence/test_schemas.py
git commit -m "feat(121-01): extend ClaimSource.kind with claim_ref for Strategic edges"
```

### Task 5: Tighten `instructions.md` for the Strategic director

**Files:**
- Modify: `app/agents/strategic/instructions.md`

The director needs to know that synthesis outputs worth recalling must persist as claims, and that synthesis claims carry `claim_ref` sources. This is a documentation-only update — the actual claim-emission tool wiring lives in Plan 121-02.

- [ ] **Step 1: Read the current instructions**

Use the Read tool to read `app/agents/strategic/instructions.md`.

- [ ] **Step 2: Append the persistence guidance section**

Add a new section near the end, BEFORE any "Output format" / "Examples" tail, titled `## Persisting synthesis as claims`. Content (paraphrase, do not copy verbatim if the surrounding style differs — match the file's voice):

```markdown
## Persisting synthesis as claims

When your synthesis is worth recalling across future conversations — an
initiative milestone, a go/no-go decision, a priority ranking, a
cross-domain risk consolidation, or a journey-workflow readiness verdict —
it must be persisted as a Claim in the knowledge graph. Sub-agents handle
their own domain claims; you do not duplicate theirs. Your claims are
*synthesis over their claims*.

Two patterns:

1. **Pure pointer claim** (e.g. `cross_domain_risk_consolidation`): a
   one-line synthesis text plus 3+ prior-agent claims as sources, each with
   `kind="claim_ref"` and `ref=str(<prior_claim_uuid>)`. The integration
   test gate requires ≥3 distinct agent_ids across those references.
2. **Decision claim** (e.g. `strategic_decision`): the go/no-go verbatim in
   the text, plus the prior claims that informed it as `claim_ref` sources.

Confidence is computed via the `strategic_confidence` preset:
sub_agent_consensus (0.40), evidence_breadth (0.30), recency_of_input
(0.20), stakeholder_validation_signal (0.10). The signals are derived from
your sub-agent orchestration trace, not asserted directly.

If the prior-agent claims you would reference do not exist yet, persist a
lower-confidence claim or defer the synthesis — never invent references.
```

- [ ] **Step 3: Quick sanity check**

```powershell
uv run python -c "from pathlib import Path; s = Path('app/agents/strategic/instructions.md').read_text(encoding='utf-8'); assert 'Persisting synthesis as claims' in s and 'claim_ref' in s; print('ok')"
```

Expected: `ok`. If the assertion fails, the section was not inserted — re-edit.

- [ ] **Step 4: Confirm no Strategic test regression**

The existing Strategic test suite must remain green — instructions are loaded but the integration tests do not currently key off this section.

```powershell
uv run pytest tests/unit/agents/strategic/ tests/integration/ -k "strategic" -v --tb=short
```

Expected: every selected test passes. If any test inspects the instructions content directly (likely none), update its expectation.

- [ ] **Step 5: Commit**

```bash
git add app/agents/strategic/instructions.md
git commit -m "docs(121-01): instruct Strategic director to persist synthesis as claim_ref claims"
```

### Task 6: Cross-cutting lint + Plan 121-01 acceptance sign-off

- [ ] **Step 1: Lint everything 121-01 touched**

```powershell
uv run ruff check app/services/intelligence/presets/strategic.py app/services/intelligence/presets/__init__.py app/services/intelligence/schemas.py tests/unit/services/intelligence/test_strategic_preset.py tests/unit/services/intelligence/test_schemas.py
uv run ruff format app/services/intelligence/presets/strategic.py app/services/intelligence/presets/__init__.py app/services/intelligence/schemas.py tests/unit/services/intelligence/test_strategic_preset.py tests/unit/services/intelligence/test_schemas.py --check
```

Fix in place. Commit any fixes:

```bash
git add -u
git commit -m "style(121-01): ruff lint + format for 121-01 modules"
```

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/services/intelligence/
```

Expected: no errors. The Literal extension is type-safe; the preset uses only typed arithmetic.

- [ ] **Step 3: Plan 121-01 acceptance — cross-check**

| Plan 121-01 acceptance line | Verified by |
|---|---|
| `strategic_confidence` preset shipped | Task 3 |
| Weights match spec values exactly | Task 3 `test_strategic_weights_match_spec` |
| Public re-export from `presets/__init__.py` | Task 3 `test_strategic_preset_imports_from_public_surface` |
| Output clamped to [0.0, 1.0] for all valid inputs | Task 3 Hypothesis test |
| `ClaimSource.kind` accepts `"claim_ref"` | Task 4 |
| `ClaimSource` round-trip preserves `claim_ref` | Task 4 `test_claim_source_claim_ref_roundtrip_via_dict` |
| Existing `ClaimSource` kinds still validate | Task 4 `test_claim_source_existing_kinds_still_work` |
| Self-improvement audit verdict documented | Task 1 audit doc |
| Edges architecture ADR documented | Task 2 ADR |
| Strategic instructions document the persistence pattern | Task 5 |
| No regression in Strategic agent test suite | Task 5 Step 4 |

- [ ] **Step 4: Plan 121-01 complete. Plan 121-02 unblocked.**

Plan 121-02 builds on the preset + `claim_ref` kind + edges ADR. The audit verdict in Task 1 is the gate — if it surfaces any **Shape-coupled** or **Refactor-required** entanglement, Plan 121-02 must address it before claim emission lands.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `presets/strategic.py` exists | Task 3 |
| Strategic weights: 0.40 / 0.30 / 0.20 / 0.10 | Task 3 |
| Public surface re-export | Task 3 |
| Edges-heavy architecture decided | Task 2 |
| `kg_findings.contradicts` NOT repurposed (semantics preserved) | Task 2 ADR Option B rejected |
| Self-improvement audit per Decision #8 | Task 1 |
| Strategic claims reference prior-agent claims via `sources[].kind="claim_ref"` | Tasks 2, 4, 5 |
| Degrade-gracefully contract for missing prior claims | Task 2 ADR § Missing prior claim |
| Strategic instructions tightened for claim emission | Task 5 |
| Lint + type clean | Task 6 |

All spec lines covered.

---

## Risk register (delta for 121-01)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `ClaimSource.kind` Literal extension breaks serialisation of existing rows | Low | Medium | Task 4 round-trip test covers existing kinds; Pydantic Literal additions are forward-compatible |
| Audit finds shape-coupled entanglement we did not expect | Low | High | Task 1 Step 3 verdict gate; if hit, halt and route to a 121.5 shim plan rather than press into 121-02 |
| ADR Option D criticised in review for overloading `sources` | Low | Low | ADR documents the four options; reviewer can choose Option A (new column) if Option D rejected — but Option D's zero-migration property is decisive |
| Hypothesis property test flakes on edge values | Low | Low | Property test has explicit equal-input guard; Hypothesis default budget is sufficient for a 4-dim unit-cube search |
| Existing intelligence tests fail after Literal extension | Low | Medium | Task 4 Step 4 runs the full `tests/unit/services/intelligence/` suite |
