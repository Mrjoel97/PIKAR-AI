# Shared Intelligence Infrastructure — Plan 120-01: Operations Preset + Claim Schema Design + Self-Improvement Engine Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `app/services/intelligence/presets/operations.py` exposing `operations_confidence(...)`, design the Operations claim-type vocabulary (5 claim types), wire it through `presets/__init__.py`, and complete the **Decision #8 self-improvement engine entanglement audit** that every Phase 114–122 phase opens with. End state: every existing Operations Agent code path that produces an operational outcome (`integration_health_verified`, `workflow_execution_completed`, `api_connector_setup_validated`, `configuration_audit_passed`, `sop_generation_completed`) has a known confidence signal and a known claim emission target — even if emission itself ships in Plan 120-03.

**Architecture:** Operations is heavily *orchestration-driven*. Unlike Data (statistical) or Financial (numerical), Operations claims describe operational *outcomes* — did the integration work, did the workflow finish, was the API connector setup valid, did the audit pass, did the SOP get generated. The preset reflects this: `integration_verification_signal` is the dominant weight (0.40) because the most common claim is "this integration is verified healthy"; `audit_trail_completeness` (0.35) reflects "we have evidence the operation happened"; `execution_idempotency` (0.20) reflects "we can re-run safely"; `test_coverage_signal` (0.05) is the small "do we have automated tests behind this" tail. Weights sum to exactly 1.00.

**Tech Stack:** Python 3.10+, `app/services/intelligence/` package shipped in Phase 112. Mirrors `presets/data.py` and `presets/research.py`. Hypothesis for property-based testing. ty for type-checking.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 120 — Operations Agent adoption.

**Out of scope:** Cache integration (Plan 120-02). Live claim emission from Operations tools (Plan 120-03). Persona-aware formatting. ADK tool registration — the preset is library-first, no new ADK tools. Calibration of preset weights from telemetry (deferred per Phase 112 decision; the educated-guess weights ship as-is until labeled outcome data exists). Migrating `app/services/self_improvement_engine.py` itself — audit only; remediation belongs in whichever plan owns the surface that broke.

---

## File structure

**Create:**
- `app/services/intelligence/presets/operations.py` — `operations_confidence()` + `OPERATIONS_WEIGHTS` + module docstring
- `tests/unit/services/intelligence/test_operations_preset.py` — preset unit + property tests
- `docs/intelligence/operations-claim-vocabulary.md` — Operations claim-type taxonomy reference (load-bearing for 120-03)
- `docs/intelligence/self-improvement-audit-120.md` — Decision #8 audit findings (read-only artifact for review)

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `operations_confidence`
- `app/services/intelligence/__init__.py` — no change (presets re-exported via `presets` namespace)

---

## Pre-flight context

`operations_confidence` signature (final):
```python
def operations_confidence(
    integration_verification_signal: float,
    audit_trail_completeness: float,
    execution_idempotency: float,
    test_coverage_signal: float,
) -> float:
    """Compute Operations-domain confidence from operational outcome signals.

    All inputs are pre-normalised to [0.0, 1.0] by the caller — the preset is
    a thin wrapper over score_confidence with the OPERATIONS_WEIGHTS map.
    """
```

Returns a confidence float clamped to `[0.0, 1.0]` via `score_confidence`. The caller is responsible for normalising raw signals (e.g., compressing an OpenAPI 200-response check + auth round-trip into a single `integration_verification_signal` in `[0, 1]`). Plan 120-03 specifies the normalisation rules per claim type; this plan only ships the preset.

**Why no `recency` term in the Operations preset:**

Every other preset shipped so far (`research_confidence`, `data_confidence`) has a `recency` term. Operations explicitly does NOT — recency is handled at the claim layer instead via per-claim `expires_at`. `integration_health_verified` claims expire after 24h (a hard freshness contract, not a smooth decay); `workflow_execution_completed` is immutable on completion (recency is meaningless — the workflow either finished at T or it didn't); `api_connector_setup_validated` expires only when the underlying spec changes (event-driven, not time-driven); `configuration_audit_passed` expires at the next audit cycle; `sop_generation_completed` is immutable (an SOP is generated at T0 and never "ages"). Encoding recency as a preset weight would either be redundant or actively wrong. The cache layer (Plan 120-02) and `expires_at` columns enforce time semantics; the preset stays purely about *outcome quality*.

This is consistent with Decision #3 in the design spec ("adaptive sub-plan template — each phase carries only the plans the agent needs"). The same principle applies inside a preset: Operations doesn't need a recency term — don't shoehorn one in.

**Operations claim-type vocabulary (target — emitted in Plan 120-03):**

| Claim type | Becomes a claim? | `expires_at` policy | Notes |
|---|---|---|---|
| `integration_health_verified` | Yes | `now + 24h` (hard contract) | Must re-verify daily; spec acceptance criterion |
| `workflow_execution_completed` | Yes | `NULL` (immutable on completion) | Append-only audit row, never updates |
| `api_connector_setup_validated` | Yes | `NULL` (or until spec hash changes) | Bound to OpenAPI spec hash; see Plan 120-02 cache |
| `configuration_audit_passed` | Yes | Until next audit cycle (typically 7d) | Reflects `audit_user_setup_tool` result |
| `sop_generation_completed` | Yes | `NULL` (immutable) | One per SOP; updates create new claim with `contradicts=[old_id]` only on superseding revisions |

**Operational outcomes that explicitly stay OFF the claim layer:**

| Output | Why no claim |
|---|---|
| Raw `analyze_workflow_bottlenecks` step stats | Transient analytical; goes to Redis (5-min TTL) per Plan 120-02 |
| Vendor cost line items (`track_vendor_subscription`) | Storage rows already in dedicated table; not epistemic content |
| Webhook delivery log entries | Domain has its own log table; not graph-worthy |
| Notification rule changes | Configuration state, not assertion content |
| Skill creation events (`create_operational_skill`) | Self-improvement engine owns this surface — see audit in Task 4 |
| One-off "list tasks" responses | Pure read-through, no assertion |

Acceptance bar for this plan:
- `operations_confidence(...)` matches the contract shape from `data_confidence`/`research_confidence`
- Weights sum to exactly 1.00 (no epsilon overshoot allowed; we own this preset)
- 10k-input Hypothesis sweep stays in `[0.0, 1.0]` and never raises on valid inputs
- `from app.services.intelligence import presets; presets.operations_confidence` resolves
- Claim-type vocabulary doc lists exactly the 5 claim types above (audit caught: don't drift)
- Decision #8 audit produces a written file with findings + remediation plan IDs

Environment quirks: Windows-only repo. Use `uv run pytest`, `uv run ruff check`. Never raw pip. No `find` / `grep` shell — use Grep/Glob tools.

---

## Tasks

### Task 1: Pre-flight — confirm Phase 113 spine still holds

**Files:** none (read-only verification)

- [ ] **Step 1: Confirm `presets` package + `score_confidence` are present**

```powershell
uv run python -c "from app.services.intelligence import presets, score_confidence, to_band; print(presets.__all__); print(score_confidence({'a': 0.5}, {'a': 1.0}))"
```

Expected output:
```
['data_confidence', 'research_confidence']
0.5
```

If the import fails, Phase 112 / 113 has regressed — STOP and surface the regression. Do not proceed with 120-01 on a broken spine.

- [ ] **Step 2: Confirm Operations Agent still loads with current tools manifest**

```powershell
uv run python -c "from app.agents.operations.agent import create_operations_agent; a = create_operations_agent(); print(type(a).__name__)"
```

Expected output: `PikarBaseAgent`.

This is the canary — if it fails, the W4-migration shape has shifted under us and the preset wiring later in this phase has nothing to bind to.

- [ ] **Step 3: Snapshot the public surface BEFORE we touch it**

```powershell
uv run python -c "import app.services.intelligence as si; print(sorted(si.__all__))" | Set-Content C:\Users\expert\Documents\PKA\Pikar-Ai\tests\unit\services\intelligence\_pre_120_surface.txt
```

Plan 120-01 must not change the top-level `__all__`. The `presets` namespace gains an entry (re-export), but `from app.services.intelligence import operations_confidence` is NOT a public surface we're adding — callers go through `presets.operations_confidence` like they do for `presets.data_confidence`. This snapshot is the no-regression diff for Task 5.

- [ ] **Step 4: Pre-flight done. No commit (read-only).**

### Task 2: Implement `presets/operations.py` (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_operations_preset.py`
- Create: `app/services/intelligence/presets/operations.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/services/intelligence/test_operations_preset.py`:

```python
"""Unit tests for the operations_confidence preset.

These tests pin the shape of the preset:
- four named inputs matching OPERATIONS_WEIGHTS
- weights sum to 1.0
- clamped output in [0.0, 1.0]
- ValueError on key mismatch
"""

from __future__ import annotations

import math

import pytest


def test_operations_confidence_importable_from_presets():
    """The preset must be re-exported from app.services.intelligence.presets."""
    from app.services.intelligence import presets

    assert hasattr(presets, "operations_confidence")
    assert callable(presets.operations_confidence)


def test_operations_weights_sum_to_one_exactly():
    """Decision #8 audit baseline: weights are owned, no float drift allowed."""
    from app.services.intelligence.presets.operations import OPERATIONS_WEIGHTS

    total = sum(OPERATIONS_WEIGHTS.values())
    # We *own* this preset and ship it with deliberate 0.40+0.35+0.20+0.05.
    # Use math.isclose with a tight tolerance — any drift is a typo.
    assert math.isclose(total, 1.0, abs_tol=1e-9), (
        f"OPERATIONS_WEIGHTS must sum to exactly 1.0, got {total!r}"
    )


def test_operations_weights_match_spec():
    """Pin the exact weights per the Phase 120 design spec."""
    from app.services.intelligence.presets.operations import OPERATIONS_WEIGHTS

    assert OPERATIONS_WEIGHTS == {
        "integration_verification_signal": 0.40,
        "audit_trail_completeness": 0.35,
        "execution_idempotency": 0.20,
        "test_coverage_signal": 0.05,
    }


def test_operations_confidence_all_perfect_returns_one():
    """All signals at 1.0 → confidence = 1.0."""
    from app.services.intelligence.presets.operations import operations_confidence

    result = operations_confidence(
        integration_verification_signal=1.0,
        audit_trail_completeness=1.0,
        execution_idempotency=1.0,
        test_coverage_signal=1.0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_operations_confidence_all_zero_returns_zero():
    """All signals at 0.0 → confidence = 0.0."""
    from app.services.intelligence.presets.operations import operations_confidence

    result = operations_confidence(
        integration_verification_signal=0.0,
        audit_trail_completeness=0.0,
        execution_idempotency=0.0,
        test_coverage_signal=0.0,
    )
    assert math.isclose(result, 0.0, abs_tol=1e-9)


def test_operations_confidence_dominant_signal_is_integration_verification():
    """Sanity: the 0.40-weighted input moves the needle furthest."""
    from app.services.intelligence.presets.operations import operations_confidence

    only_integration = operations_confidence(
        integration_verification_signal=1.0,
        audit_trail_completeness=0.0,
        execution_idempotency=0.0,
        test_coverage_signal=0.0,
    )
    only_audit = operations_confidence(
        integration_verification_signal=0.0,
        audit_trail_completeness=1.0,
        execution_idempotency=0.0,
        test_coverage_signal=0.0,
    )
    only_idempotency = operations_confidence(
        integration_verification_signal=0.0,
        audit_trail_completeness=0.0,
        execution_idempotency=1.0,
        test_coverage_signal=0.0,
    )
    only_tests = operations_confidence(
        integration_verification_signal=0.0,
        audit_trail_completeness=0.0,
        execution_idempotency=0.0,
        test_coverage_signal=1.0,
    )

    assert only_integration > only_audit > only_idempotency > only_tests
    assert math.isclose(only_integration, 0.40, abs_tol=1e-9)
    assert math.isclose(only_audit, 0.35, abs_tol=1e-9)
    assert math.isclose(only_idempotency, 0.20, abs_tol=1e-9)
    assert math.isclose(only_tests, 0.05, abs_tol=1e-9)


@pytest.mark.parametrize(
    "verification,audit,idemp,tests,expected",
    [
        (0.8, 0.9, 0.7, 0.5, 0.40 * 0.8 + 0.35 * 0.9 + 0.20 * 0.7 + 0.05 * 0.5),
        (0.5, 0.5, 0.5, 0.5, 0.5),
        (1.0, 0.0, 0.0, 1.0, 0.40 + 0.05),
    ],
)
def test_operations_confidence_known_combinations(
    verification, audit, idemp, tests, expected
):
    """Hand-computed checks against the formula."""
    from app.services.intelligence.presets.operations import operations_confidence

    result = operations_confidence(
        integration_verification_signal=verification,
        audit_trail_completeness=audit,
        execution_idempotency=idemp,
        test_coverage_signal=tests,
    )
    assert math.isclose(result, expected, abs_tol=1e-9)
```

- [ ] **Step 2: Run — should FAIL (module not created yet)**

```powershell
uv run pytest tests/unit/services/intelligence/test_operations_preset.py -v --tb=short
```

Expected: collection error or `ImportError: cannot import name 'operations_confidence'`.

- [ ] **Step 3: Create `app/services/intelligence/presets/operations.py`**

```python
"""Operations-domain confidence preset.

Phase 120-01 — used by Operations Agent claim emission (Plan 120-03).

Operations is heavily orchestration-driven. Unlike Data (statistical) or
Financial (numerical), Operations claims describe operational *outcomes*:
- integration_health_verified (did the integration work?)
- workflow_execution_completed (did the workflow finish?)
- api_connector_setup_validated (was the connector setup correct?)
- configuration_audit_passed (did the audit pass?)
- sop_generation_completed (did SOP generation succeed?)

Weight rationale:
- integration_verification_signal (0.40): the dominant claim type is health-
  verified; weight reflects that we trust evidence the integration actually
  responded over indirect signals.
- audit_trail_completeness (0.35): "we have evidence the operation happened" —
  did we capture inputs, outputs, and side-effects? Operations without a trail
  is unverifiable.
- execution_idempotency (0.20): "can we re-run safely?" — workflows that
  produced the same output deterministically score higher.
- test_coverage_signal (0.05): "do we have automated tests behind this path?"
  — small tail signal; most Operations outcomes are runtime-verified, not
  test-verified.

No recency term in the preset — recency is handled at the claim layer via
per-claim expires_at (integration_health_verified TTL=24h, immutable claims
have expires_at=NULL). See plan 120-01 § "Why no recency term".
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

OPERATIONS_WEIGHTS: dict[str, float] = {
    "integration_verification_signal": 0.40,
    "audit_trail_completeness": 0.35,
    "execution_idempotency": 0.20,
    "test_coverage_signal": 0.05,
}


def operations_confidence(
    integration_verification_signal: float,
    audit_trail_completeness: float,
    execution_idempotency: float,
    test_coverage_signal: float,
) -> float:
    """Compute Operations-domain confidence from operational outcome signals.

    All inputs must be pre-normalised to [0.0, 1.0] by the caller. Per-claim
    normalisation rules live in plan 120-03; this preset is the thin wrapper
    over score_confidence with OPERATIONS_WEIGHTS.

    Args:
        integration_verification_signal: Did the integration actually respond
            and behave correctly? E.g., OpenAPI 200-response check passed +
            auth round-trip succeeded → 1.0; partial pass → 0.5; no probe
            performed → 0.0.
        audit_trail_completeness: Fraction of expected audit-trail fields
            captured. E.g., for workflow_execution_completed: inputs, outputs,
            step transitions, side-effects all logged → 1.0.
        execution_idempotency: 1.0 if the operation is provably idempotent
            (e.g., upsert with deterministic key), 0.5 if probably idempotent
            but unproven, 0.0 if not idempotent.
        test_coverage_signal: 1.0 if there's an automated test covering this
            exact code path, 0.0 if not.

    Returns:
        Confidence score clamped to [0.0, 1.0].
    """
    return score_confidence(
        inputs={
            "integration_verification_signal": integration_verification_signal,
            "audit_trail_completeness": audit_trail_completeness,
            "execution_idempotency": execution_idempotency,
            "test_coverage_signal": test_coverage_signal,
        },
        weights=OPERATIONS_WEIGHTS,
    )
```

- [ ] **Step 4: Re-export from `presets/__init__.py`**

Modify `app/services/intelligence/presets/__init__.py`:

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Phase 120 adds operations_confidence.
"""

from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.operations import operations_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = ["data_confidence", "operations_confidence", "research_confidence"]
```

- [ ] **Step 5: Re-run unit tests — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_operations_preset.py -v --tb=short
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/presets/operations.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_operations_preset.py
git commit -m "feat(120-01): operations_confidence preset (GREEN)"
```

### Task 3: Hypothesis property tests (range + monotonicity invariants)

**Files:**
- Modify: `tests/unit/services/intelligence/test_operations_preset.py`

The hand-rolled tests in Task 2 cover specific points. Hypothesis sweeps the function over 10k random inputs to catch range violations and monotonicity bugs that point tests would miss.

- [ ] **Step 1: Append the property tests**

Append to `tests/unit/services/intelligence/test_operations_preset.py`:

```python
from hypothesis import given, settings, strategies as st


_FLOAT_01 = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@settings(max_examples=10_000, deadline=None)
@given(
    verification=_FLOAT_01,
    audit=_FLOAT_01,
    idemp=_FLOAT_01,
    tests=_FLOAT_01,
)
def test_operations_confidence_always_in_unit_interval(
    verification, audit, idemp, tests
):
    """For any valid input combo, output ∈ [0.0, 1.0]."""
    from app.services.intelligence.presets.operations import operations_confidence

    result = operations_confidence(
        integration_verification_signal=verification,
        audit_trail_completeness=audit,
        execution_idempotency=idemp,
        test_coverage_signal=tests,
    )
    assert 0.0 <= result <= 1.0, f"Out-of-range result: {result}"


@settings(max_examples=2_000, deadline=None)
@given(
    base_v=_FLOAT_01,
    base_a=_FLOAT_01,
    base_i=_FLOAT_01,
    base_t=_FLOAT_01,
    bump=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
)
def test_operations_confidence_monotonic_in_verification(
    base_v, base_a, base_i, base_t, bump
):
    """Raising the verification signal never lowers the output."""
    from app.services.intelligence.presets.operations import operations_confidence

    bumped_v = min(1.0, base_v + bump)
    low = operations_confidence(
        integration_verification_signal=base_v,
        audit_trail_completeness=base_a,
        execution_idempotency=base_i,
        test_coverage_signal=base_t,
    )
    high = operations_confidence(
        integration_verification_signal=bumped_v,
        audit_trail_completeness=base_a,
        execution_idempotency=base_i,
        test_coverage_signal=base_t,
    )
    # Floating-point slack — should be monotonically non-decreasing.
    assert high >= low - 1e-9, (
        f"Monotonicity violated: verification {base_v} -> {bumped_v} "
        f"gave {low} -> {high}"
    )


@settings(max_examples=2_000, deadline=None)
@given(
    base_v=_FLOAT_01,
    base_a=_FLOAT_01,
    base_i=_FLOAT_01,
    base_t=_FLOAT_01,
    bump=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
)
def test_operations_confidence_monotonic_in_audit_trail(
    base_v, base_a, base_i, base_t, bump
):
    """Raising audit_trail_completeness never lowers the output."""
    from app.services.intelligence.presets.operations import operations_confidence

    bumped_a = min(1.0, base_a + bump)
    low = operations_confidence(
        integration_verification_signal=base_v,
        audit_trail_completeness=base_a,
        execution_idempotency=base_i,
        test_coverage_signal=base_t,
    )
    high = operations_confidence(
        integration_verification_signal=base_v,
        audit_trail_completeness=bumped_a,
        execution_idempotency=base_i,
        test_coverage_signal=base_t,
    )
    assert high >= low - 1e-9
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/unit/services/intelligence/test_operations_preset.py -v --tb=short
```

Expected: all 10 tests pass (7 from Task 2 + 3 Hypothesis). The 10k sweep takes ~3-6s; the 2k sweeps ~1-2s each.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/services/intelligence/test_operations_preset.py
git commit -m "test(120-01): Hypothesis property tests for operations_confidence (range + monotonicity)"
```

### Task 4: Self-improvement engine entanglement audit (Decision #8)

**Files:**
- Create: `docs/intelligence/self-improvement-audit-120.md`

Per spec Decision #8: each phase's first sub-plan audits `app/services/self_improvement_engine.py` and `app/services/skill_experiment_evaluator.py` (or notes its absence). The audit happens *before* changes so we know what shapes the engine depends on — not after, when entanglement is already broken.

- [ ] **Step 1: Inventory the entanglement surface**

Run these probes (capture output as you go — the audit doc cites specific line numbers and import names):

```powershell
# 1. Direct imports from the Operations Agent into self-improvement
uv run python -c "import ast, pathlib; tree = ast.parse(pathlib.Path('app/services/self_improvement_engine.py').read_text()); print([n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and 'operations' in n.module])"

# 2. Direct imports from skill_experiment_evaluator into operations
# (skill_experiment_evaluator may not exist yet — capture that)
uv run python -c "import pathlib; p = pathlib.Path('app/services/skill_experiment_evaluator.py'); print('exists' if p.exists() else 'missing'); print(p.read_text()[:2000] if p.exists() else '')"

# 3. Any reference to ops_tools / api_connector / integration_setup from the engine
```

Use Grep tool for the rest:

```
Grep pattern: "operations|ops_tools|api_connector|integration_setup|generate_sop_document|analyze_workflow_bottlenecks"
Path: app/services/self_improvement_engine.py
Output mode: content with line numbers
```

```
Grep pattern: "create_operational_skill|workflow_bottleneck|integration_health"
Path: app/services/
Output mode: content with line numbers
```

- [ ] **Step 2: Inventory the *reverse* direction**

Does anything in `app/agents/operations/*` import from the self-improvement engine?

```
Grep pattern: "self_improvement_engine|skill_experiment_evaluator"
Path: app/agents/operations/
Output mode: content with line numbers
```

Also check the broader `app/agents/tools/skill_builder.py` since `create_operational_skill` is the Operations-owned skill-creation surface and it likely talks to the engine.

```
Grep pattern: "self_improvement|experiment_evaluator|skill_eval"
Path: app/agents/tools/skill_builder.py
Output mode: content with line numbers
```

- [ ] **Step 3: Inventory references to Operations claim shapes from anywhere**

Plan 120-03 will introduce 5 new claim_type values. If any existing code already grep-matches strings like `"integration_health_verified"`, `"sop_generation_completed"`, etc., we'd have a collision.

```
Grep pattern: "integration_health_verified|workflow_execution_completed|api_connector_setup_validated|configuration_audit_passed|sop_generation_completed"
Path: app/
Output mode: content with line numbers
```

Expected: no matches (these are NEW claim types). Any match means Plan 120-03 will collide and the vocabulary must change.

- [ ] **Step 4: Inventory `record_outcome` / `evaluate_skill_*` shapes**

The self-improvement engine evaluates skills based on outcomes. If those outcomes share a vocabulary with our planned claim_types, Plan 120-03 has more wiring to do.

```
Grep pattern: "def (record_outcome|evaluate_skill|score_skill_run|skill_outcome)"
Path: app/services/
Output mode: content with line numbers
```

Cross-reference with `docs/self-improvement-policy.md` (load-bearing per CLAUDE.md).

- [ ] **Step 5: Write the audit doc**

Create `docs/intelligence/self-improvement-audit-120.md`:

```markdown
# Phase 120 — Self-Improvement Engine Entanglement Audit

**Status:** Decision #8 compliance artifact for Phase 120 (Operations Agent adoption).
**Date:** 2026-05-19
**Owner:** Plan 120-01 author
**Policy reference:** `docs/self-improvement-policy.md`

## Scope

Audit `app/services/self_improvement_engine.py` and any sibling
`skill_experiment_evaluator.py` for code paths that bind to:

1. Operations Agent module shape (tools manifest, sub-agent registration)
2. Operations claim types (planned for Plan 120-03)
3. Operations-owned `create_operational_skill` surface

Audit happens BEFORE Plan 120-03 code changes so we know what shapes the
engine depends on. Per the policy doc this is load-bearing for any change
that touches `self_improvement_engine.py` or `skill_experiment_evaluator.py`.

## Findings

### F1 — Direct Operations module imports

[Paste output from Step 1, probes 1-3 here. Record file:line for each hit
or the literal string "no hits" if Grep returns empty.]

### F2 — Reverse direction: Operations → engine imports

[Paste output from Step 2 here.]

Notable: `app/agents/tools/skill_builder.py::create_operational_skill` is
the user-facing entry to skill generation. Its interaction with the
self-improvement engine determines whether Plan 120-03 can safely add
new claim emission inside skill creation without disturbing the engine's
A/B harness invariants.

### F3 — Claim-type vocabulary collisions

[Paste output from Step 3 here. Expected: empty. Any hit must be
documented with the call-site and proposed remediation.]

### F4 — Outcome / evaluator API shapes

[Paste output from Step 4 here. Cross-reference each match with
docs/self-improvement-policy.md § "What the engine may auto-modify".]

## Remediation plan

Map each finding to the plan that owns its remediation. The audit doc
itself never changes engine code — it allocates work to downstream plans.

| Finding ID | Severity | Owner plan | Action |
|---|---|---|---|
| F1 | (low/med/high based on hit count) | 120-03 if claim-emission collides; else N/A | (describe) |
| F2 | (low/med/high) | 120-03 if skill-creation surface adopts claims | (describe) |
| F3 | (low/med/high) | 120-01 (re-vocabulary in this plan) if any hit | (describe) |
| F4 | (low/med/high) | 120-03 if Operations adopts engine outcome API | (describe) |

## Decision

(Pick exactly one)

- [ ] **GO** — no engine entanglement found. Phase 120 may proceed without
  engine changes. Plan 120-03 may emit claims freely.

- [ ] **GO WITH FENCES** — entanglement found but isolated. Phase 120 may
  proceed; Plan 120-03 owners must respect the fences below.

- [ ] **HOLD** — entanglement requires engine remediation BEFORE Plan
  120-03. Block Plan 120-03 on completion of (plan ID).

## Fences (only if "GO WITH FENCES")

(List each constraint. Example: "Plan 120-03 must NOT use claim_type
values matching the existing engine outcome vocabulary listed in F3.")

## Sign-off

This audit is itself a planning artifact, not a code change. Commit it
alongside the Plan 120-01 preset commit.
```

Fill out every `[Paste output…]` section with the actual results from Steps 1-4. The literal placeholders must not survive into the committed file.

- [ ] **Step 6: Commit the audit**

```bash
git add docs/intelligence/self-improvement-audit-120.md
git commit -m "docs(120-01): self-improvement engine entanglement audit (Decision #8)"
```

### Task 5: Claim-type vocabulary documentation

**Files:**
- Create: `docs/intelligence/operations-claim-vocabulary.md`

Plan 120-03 consumes this doc to wire claim emission. Writing it here forces the vocabulary design to happen now, not when Plan 120-03 author is mid-implementation.

- [ ] **Step 1: Create `docs/intelligence/operations-claim-vocabulary.md`**

```markdown
# Operations Agent — Claim-Type Vocabulary

**Status:** Reference doc for Phase 120 (Operations Agent adoption).
**Owner:** Plan 120-01 design; consumed by Plan 120-03 emission.
**Last reviewed:** 2026-05-19.

## Principle

Operations claims describe operational *outcomes* — assertions about
whether something the agent orchestrated actually happened, completed
correctly, and remains verifiable. They are NOT transient analytical
outputs.

A finding becomes a claim iff:

1. It is an assertion about a real-world operational state worth recalling
2. Re-deriving the assertion would require external work (an integration
   probe, a workflow execution, an audit pass)
3. Other agents or future Operations runs may consult it

If a finding is purely transient (a one-off list, raw telemetry, a
configuration view), it stays in Redis or in the response payload — NOT
in `kg_findings`.

## Vocabulary (exactly 5 claim types)

### `integration_health_verified`

**Meaning:** A named integration (e.g., `hubspot`, `stripe`, a connected
OpenAPI service) was probed and confirmed healthy within the last 24h.

**Emitter:** Operations Agent during integration health-check flows
(`check_integration_status`, `validate_api_connection`, post-`connect_api`
verification).

**`entity_id`:** kg_entities row for the integration, `entity_type='technology'`
or `'product'`, `canonical_name=<service_id>`.

**`finding_text` shape:** `"<service_name> integration verified healthy at <timestamp>: <evidence summary>"`.

**`expires_at`:** `now + timedelta(hours=24)`. **Hard contract** —
the spec acceptance criterion is "all integration_health_verified
claims expire within 24h of write." Plan 120-03 must respect this.

**`embed`:** True (claims will be discoverable via
`search_claims_semantic` so other agents can answer "is integration X
healthy?").

**Confidence inputs:**

- `integration_verification_signal`: 1.0 if all probe checks passed
  (auth + sample endpoint 200 + expected schema); 0.5 if partial; 0.0
  if no probe.
- `audit_trail_completeness`: fraction of probe artifacts captured
  (request, response status, headers, latency).
- `execution_idempotency`: 1.0 (probe is read-only).
- `test_coverage_signal`: 1.0 if there's a regression test pinning the
  probe path; else 0.0.

### `workflow_execution_completed`

**Meaning:** A user-defined workflow ran to completion with all steps
finishing (success or terminal failure). Immutable record of the run.

**Emitter:** Operations Agent via workflow engine integrations
(`workflow_ops.py`, `adaptive_workflows.py`). Plan 120-03 wires this at
the engine's `on_workflow_complete` hook, NOT inside each step.

**`entity_id`:** kg_entities row for the workflow definition,
`entity_type='topic'`, `canonical_name='workflow:' + workflow_id`.

**`finding_text` shape:** `"Workflow '<workflow_name>' completed at <timestamp>: <N> steps, <duration>, terminal_status=<success|failure>"`.

**`expires_at`:** `NULL` — immutable on completion. Workflow runs are
audit-grade history; they never expire.

**`embed`:** True — completion records are searchable ("did the X
workflow run yesterday?").

**Confidence inputs:**

- `integration_verification_signal`: 1.0 if no integration step failed;
  scaled by integration-step success rate otherwise.
- `audit_trail_completeness`: fraction of step events captured (inputs,
  outputs, transitions, side-effects).
- `execution_idempotency`: 1.0 if all steps are idempotent; degrade per
  step.
- `test_coverage_signal`: 1.0 if the workflow definition has an
  end-to-end test fixture; else 0.0.

### `api_connector_setup_validated`

**Meaning:** A newly-connected external API (via OpenAPI spec parse +
codegen, `connect_api`) was validated end-to-end: spec parsed, generated
tools registered, sample call succeeded.

**Emitter:** `connect_api` / `validate_api_connection` post-success
path.

**`entity_id`:** kg_entities row for the API,
`entity_type='product'`, `canonical_name='api:' + api_name`.

**`finding_text` shape:** `"API connector '<api_name>' setup validated at <timestamp>: <N> endpoints generated, spec_hash=<hash>"`.

**`expires_at`:** `NULL` (or until spec_hash changes — Plan 120-02
caches the spec; new hash means a new validation must produce a new
claim with `contradicts=[old_validation_id]`).

**`embed`:** True.

**Confidence inputs:**

- `integration_verification_signal`: 1.0 if sample endpoint call
  succeeded; 0.0 if not validated post-codegen.
- `audit_trail_completeness`: 1.0 if spec hash, endpoint list, and
  registration metadata are all captured.
- `execution_idempotency`: 0.5 (connect_api itself is not perfectly
  idempotent — re-runs may register duplicate tools; this is a known
  surface that Plan 120-03 may document).
- `test_coverage_signal`: 1.0 if the generated tools have at least one
  smoke test; else 0.0.

### `configuration_audit_passed`

**Meaning:** A user-setup audit (`audit_user_setup_tool`) ran and
reported no blocking gaps.

**Emitter:** Configuration & Integration sub-agent inside
`create_operations_agent` (the `_create_config_agent` factory).

**`entity_id`:** kg_entities row for the user,
`entity_type='person'`, `canonical_name='user:' + user_id`.

**`finding_text` shape:** `"User <user_id> configuration audit passed at <timestamp>: <N> integrations checked, <M> non-blocking notes"`.

**`expires_at`:** `now + timedelta(days=7)` (audits are valid for a
week; weekly re-audit refreshes).

**`embed`:** False — `configuration_audit_passed` claims are
per-user, not semantically searchable across agents. Embedding cost
without payoff.

**Confidence inputs:**

- `integration_verification_signal`: fraction of integrations the audit
  actively probed (vs. cache-trusted).
- `audit_trail_completeness`: fraction of audit-checklist items
  executed.
- `execution_idempotency`: 1.0 (audit is read-only).
- `test_coverage_signal`: 1.0 if the audit tool has unit-test coverage
  per check; else 0.0.

### `sop_generation_completed`

**Meaning:** A Standard Operating Procedure document was generated and
emitted to the user (`generate_sop_document` success path).

**Emitter:** `generate_sop_document` post-success.

**`entity_id`:** kg_entities row for the SOP process name,
`entity_type='topic'`, `canonical_name='sop:' + process_name_slug`.

**`finding_text` shape:** `"SOP '<process_name>' v<version> generated at <timestamp>: <N> procedure steps, document_id=<id>"`.

**`expires_at`:** `NULL` (immutable). SOP revisions create a NEW claim
with `contradicts=[old_sop_claim_id]` to express supersession.

**`embed`:** True (SOPs are highly searchable across agents:
"what's our SOP for X?").

**Confidence inputs:**

- `integration_verification_signal`: not strictly applicable; pass
  through as 1.0 (the operation is local).
- `audit_trail_completeness`: 1.0 if document_id, version, all
  procedure steps, and roles are captured.
- `execution_idempotency`: 1.0 (deterministic from inputs).
- `test_coverage_signal`: 1.0 if `_format_sop_as_text` has a snapshot
  test; else 0.0.

## Outputs that explicitly stay OFF the claim layer

| Operations output | Why no claim | Where it lives |
|---|---|---|
| `analyze_workflow_bottlenecks` per-step stats | Transient analytical | Redis (Plan 120-02) |
| `track_vendor_subscription` line items | Owned by dedicated table | `vendor_subscriptions` table |
| Webhook delivery log entries | Domain-owned log | `webhook_delivery_log` table |
| Notification rule changes | Config state, not assertion | `notification_rules` table |
| `create_operational_skill` events | Owned by self-improvement engine | `custom_skills` + engine outcome tables |
| One-off task list responses | Pure read-through | Response payload only |

## Cross-agent overlap check

Per spec risk register: "Cross-agent claim collisions (semantic-equivalent
claim_types)." None of the 5 Operations claim types overlap by name with
existing Phase 113 (Data) or planned Phase 114-119 vocabularies. Document
any future overlap discovered during Plan 120-03 implementation here.

## Storage notes

- `kg_findings` table — broadened in Phase 112 migration
  `20260518000000_broaden_kg_findings_for_shared_claims.sql`.
- pgvector ivfflat index — `20260519000000_kg_findings_embedding_ivfflat_index.sql`.
- Plan 120-03 must verify the `(agent_id, claim_type)` composite index
  is hit by EXPLAIN ANALYZE on a representative `find_claims` call.
```

- [ ] **Step 2: Commit the vocabulary doc**

```bash
git add docs/intelligence/operations-claim-vocabulary.md
git commit -m "docs(120-01): Operations claim-type vocabulary (5 types) for Plan 120-03"
```

### Task 6: Public-surface no-regression check

**Files:** none new — verification of Tasks 2-4 deliverables

- [ ] **Step 1: Snapshot the public surface AFTER changes**

```powershell
uv run python -c "import app.services.intelligence as si; print(sorted(si.__all__))" | Set-Content tests/unit/services/intelligence/_post_120_surface.txt
```

- [ ] **Step 2: Diff against the pre-flight snapshot**

```powershell
Compare-Object -ReferenceObject (Get-Content tests/unit/services/intelligence/_pre_120_surface.txt) -DifferenceObject (Get-Content tests/unit/services/intelligence/_post_120_surface.txt)
```

Expected: zero differences. The top-level `__all__` did NOT change — only
`presets.__all__` grew by one (`operations_confidence`).

- [ ] **Step 3: Confirm the new preset is reachable through the expected path**

```powershell
uv run python -c "from app.services.intelligence import presets; print(presets.operations_confidence(1.0, 1.0, 1.0, 1.0))"
```

Expected output: `1.0`.

- [ ] **Step 4: Confirm Operations Agent still loads (canary re-run)**

```powershell
uv run python -c "from app.agents.operations.agent import create_operations_agent; a = create_operations_agent(); print(type(a).__name__)"
```

Expected: `PikarBaseAgent`. Plan 120-01 must not break agent assembly.

- [ ] **Step 5: Delete the surface snapshot files (they're scratch)**

```powershell
Remove-Item tests/unit/services/intelligence/_pre_120_surface.txt, tests/unit/services/intelligence/_post_120_surface.txt
```

- [ ] **Step 6: No commit (verification only)**

### Task 7: Lint + final acceptance

- [ ] **Step 1: Ruff check + format**

```powershell
uv run ruff check app/services/intelligence/presets/operations.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_operations_preset.py
uv run ruff format app/services/intelligence/presets/operations.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_operations_preset.py --check
```

Fix in place. If format produced changes:

```bash
git add app/services/intelligence/presets/operations.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/test_operations_preset.py
git commit -m "style(120-01): ruff format pass over operations preset + tests"
```

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/services/intelligence/presets/operations.py
```

Expected: no errors. The preset is intentionally a thin wrapper — no
complex types should appear.

- [ ] **Step 3: Plan 120-01 acceptance**

| Acceptance line | Verified by |
|---|---|
| `operations_confidence` preset shipped | Task 2 Step 5 |
| `OPERATIONS_WEIGHTS` sums to exactly 1.00 | Task 2 `test_operations_weights_sum_to_one_exactly` |
| Output ∈ [0.0, 1.0] over 10k Hypothesis inputs | Task 3 `test_operations_confidence_always_in_unit_interval` |
| Monotonic in dominant signals | Task 3 monotonicity tests |
| `presets.operations_confidence` importable | Task 6 Step 3 |
| Top-level `__all__` unchanged | Task 6 Step 2 |
| Operations Agent still loads | Task 6 Step 4 |
| Decision #8 audit document written | Task 4 Step 6 |
| Claim-type vocabulary document written | Task 5 Step 2 |
| Lint clean | Task 7 Step 1 |

- [ ] **Step 4: Plan 120-01 complete. Hand off claim-type vocabulary to Plan 120-03 author; hand off cache surface inventory to Plan 120-02 author.**

---

## Spec coverage check

| Spec requirement (from Phase 120 design) | Task |
|---|---|
| `presets/operations.py` shipped | Task 2 |
| `OPERATIONS_WEIGHTS` = {0.40, 0.35, 0.20, 0.05} | Task 2 |
| Self-improvement engine audit per Decision #8 | Task 4 |
| Claim-type vocabulary (5 types) documented | Task 5 |
| `integration_health_verified` TTL = 24h (documented; emitted in 120-03) | Task 5 |
| `workflow_execution_completed` immutable on completion | Task 5 |
| `api_connector_setup_validated` documented | Task 5 |
| `configuration_audit_passed` documented | Task 5 |
| `sop_generation_completed` documented | Task 5 |
| No new ADK tools registered | (verified by no edit to `app/agents/operations/tools.py` or ADK registry) |
| Lint clean | Task 7 |

All spec lines for 120-01 covered.

---

## Notes for Plan 120-02 (cache integration)

- Cache surfaces to address:
  - OpenAPI spec parse cache — keyed `openapi_spec:{source_url_hash}`, TTL 86400 (24h). Triggered by `app/agents/tools/api_connector.py::connect_api`.
  - Integration health check cache — keyed `integration_health:{service_id}`, TTL 300 (5min). Triggered by `app/agents/tools/integration_setup.py::check_integration_status`.
  - Endpoint metadata cache — keyed `endpoint_metadata:{connector_id}`, TTL 604800 (7d). Used by codegen path inside `connect_api`.
  - Graph-tier freshness threshold = 24h for `integration_health_verified` claims.

## Notes for Plan 120-03 (claim emission)

- Five new claim_type values, all defined in `docs/intelligence/operations-claim-vocabulary.md`.
- Emission sites:
  - `check_integration_status` / `validate_api_connection` → `integration_health_verified`.
  - Workflow engine's `on_workflow_complete` hook → `workflow_execution_completed`.
  - `connect_api` post-success → `api_connector_setup_validated`.
  - `audit_user_setup_tool` post-success → `configuration_audit_passed`.
  - `generate_sop_document` post-success → `sop_generation_completed`.
- `expires_at` policy is type-specific (see vocabulary doc); enforce in `write_claim` call-site, not in a shared helper.
- `embed=True` for the 4 cross-agent-discoverable types; `embed=False` for `configuration_audit_passed` (per-user, not searchable).
