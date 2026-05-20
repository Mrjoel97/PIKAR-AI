# Shared Intelligence Infrastructure — Plan 112-02: Confidence Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first two pieces of the shared intelligence layer: a generic weighted confidence scorer with band classifier (`confidence.py`) and a research-domain preset that is bit-identical to the existing `app/agents/research/tools/synthesizer.py:calculate_confidence` (`presets/research.py`). No agent migrates onto these in this plan — that's Plan 112-05.

**Architecture:** Library-first (no new ADK tools). New package at `app/services/intelligence/` exposes `score_confidence`, `to_band`, and `presets` module via re-exports from `__init__.py`. `ConfidenceBand` Literal lives in a minimal `schemas.py` so Plan 112-03 can add `Claim` / `ClaimSource` / `ClaimPayload` to the same file without restructure. The research preset replicates the existing formula exactly — including the `freshness_clamped = max(0.0, freshness)` step the spec missed — and is locked in by a Hypothesis property test running 10k random inputs.

**Tech Stack:** Python 3.10+, Pydantic v2 (already a project dep), Hypothesis (new dev dependency), pytest, ruff, ty.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Module specifications, § Phase 112 acceptance criteria

**Out of scope for this plan:** Claims module (Plan 112-03), cache module (Plan 112-04), Research Agent refactor (Plan 112-05), Data Agent preset (Phase 113).

---

## File structure

**Create:**
- `app/services/intelligence/__init__.py` — public re-exports
- `app/services/intelligence/confidence.py` — `score_confidence` + `to_band`
- `app/services/intelligence/schemas.py` — `ConfidenceBand` Literal (Plan 112-03 will extend)
- `app/services/intelligence/presets/__init__.py` — re-exports `research_confidence` (and later `data_confidence`)
- `app/services/intelligence/presets/research.py` — `research_confidence`
- `tests/unit/services/intelligence/__init__.py` — empty marker
- `tests/unit/services/intelligence/test_confidence.py` — unit tests for generic scorer + band
- `tests/unit/services/intelligence/test_presets_research.py` — unit + property-based regression tests

**Reference (read-only, do not modify):**
- `app/agents/research/tools/synthesizer.py:120-151` — existing `calculate_confidence` (the reference implementation we must match)

**Modify (one file, only if Hypothesis isn't already a dev dependency):**
- `pyproject.toml` + `uv.lock` — add `hypothesis` via `uv add --dev hypothesis`

---

## Pre-flight context

The function we are lifting (from `app/agents/research/tools/synthesizer.py:120-151`):

```python
def calculate_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Calculate confidence using the multi-track formula from spec."""
    contradiction_penalty = min(1.0, contradictions_found * 0.05)
    freshness_clamped = max(0.0, freshness)

    confidence = (
        track_agreement * 0.35
        + source_quality * 0.30
        + freshness_clamped * 0.20
        + (1.0 - contradiction_penalty) * 0.15
    )

    return max(0.0, min(1.0, confidence))
```

Three subtle behaviors to preserve:
1. **`freshness_clamped = max(0.0, freshness)`** — freshness is floor-clamped at 0 before the weighted sum. The other inputs (track_agreement, source_quality) are NOT clamped at the input layer.
2. **`contradiction_penalty = min(1.0, contradictions_found * 0.05)`** — penalty saturates at 1.0 (i.e., 20 or more contradictions all yield penalty=1.0).
3. **Final clamp to `[0.0, 1.0]`** — applied to the weighted sum.

Environment quirks captured from Plan 112-01:
- `uv` only works via PowerShell (the `uv.cmd` shim at `C:\Users\expert\.local\bin\uv.cmd`)
- Use the `PowerShell` tool for `uv add`, `uv run` invocations
- No psql installed; not needed for this plan (no DB interaction)

Test commands:
```powershell
uv run pytest tests/unit/services/intelligence/ -v
uv run ruff check app/services/intelligence/ tests/unit/services/intelligence/
uv run ruff format app/services/intelligence/ tests/unit/services/intelligence/
uv run ty check app/services/intelligence/
```

---

## Tasks

### Task 1: Pre-flight — confirm package location is clear and Hypothesis available

**Files:** none modified — verification only.

- [ ] **Step 1: Confirm the target directory doesn't exist yet**

```bash
ls app/services/intelligence 2>&1 | head -3
```

Expected: `ls: cannot access 'app/services/intelligence': No such file or directory`. If the directory exists already with prior content, STOP and report BLOCKED — Plan 112-02 is the first time this package should appear.

- [ ] **Step 2: Confirm Hypothesis is or is not installed**

From PowerShell:
```powershell
uv run python -c "import hypothesis; print('hypothesis', hypothesis.__version__)" 2>&1
```

Two acceptable outcomes:
- Already installed: prints version, no action needed
- Not installed: ImportError — Task 2 will install it

Capture which one for the report.

- [ ] **Step 3: Confirm existing `calculate_confidence` is at the expected location**

```bash
grep -n "def calculate_confidence" app/agents/research/tools/synthesizer.py
```

Expected: `120:def calculate_confidence(`. If different line, note for the test imports.

No commit in this task — verification only.

---

### Task 2: Create the package skeleton

**Files:**
- Create: `app/services/intelligence/__init__.py` (placeholder)
- Create: `app/services/intelligence/schemas.py` (ConfidenceBand)
- Create: `app/services/intelligence/confidence.py` (stub)
- Create: `app/services/intelligence/presets/__init__.py` (placeholder)
- Create: `app/services/intelligence/presets/research.py` (stub)
- Create: `tests/unit/services/intelligence/__init__.py` (empty)

- [ ] **Step 1: Create `app/services/intelligence/__init__.py`**

```python
"""Shared intelligence infrastructure used by agents.

This package exposes:
- score_confidence / to_band — generic weighted scorer and band classifier
- presets — named confidence formulas per agent domain
- ConfidenceBand — Literal["low", "medium", "high"]

Plan 112-03 will add claims (kg_findings writer/reader) to this surface.
Plan 112-04 will add adaptive cache. See the design at
docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md.
"""

from app.services.intelligence import presets
from app.services.intelligence.confidence import score_confidence, to_band
from app.services.intelligence.schemas import ConfidenceBand

__all__ = [
    "ConfidenceBand",
    "presets",
    "score_confidence",
    "to_band",
]
```

- [ ] **Step 2: Create `app/services/intelligence/schemas.py`**

```python
"""Shared Pydantic models and type aliases for the intelligence package.

Plan 112-02 ships only ConfidenceBand. Plan 112-03 extends this module
with ClaimSource, Claim, ClaimPayload.
"""

from __future__ import annotations

from typing import Literal

ConfidenceBand = Literal["low", "medium", "high"]
```

- [ ] **Step 3: Create `app/services/intelligence/confidence.py` (stub for now)**

The full implementation lands in Task 4 after the tests are red. For Task 2 we ship the import-resolvable stub.

```python
"""Generic weighted confidence scorer and band classifier.

Used by per-agent presets (presets/research.py, presets/data.py, ...).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.services.intelligence.schemas import ConfidenceBand


def score_confidence(
    inputs: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 112-02 Task 4")


def to_band(
    score: float,
    *,
    low_threshold: float = 0.50,
    high_threshold: float = 0.75,
) -> ConfidenceBand:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 112-02 Task 4")
```

- [ ] **Step 4: Create `app/services/intelligence/presets/__init__.py`**

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Add a new preset when a new agent class needs
its own formula — Phase 113 adds data_confidence.
"""

from app.services.intelligence.presets.research import research_confidence

__all__ = ["research_confidence"]
```

- [ ] **Step 5: Create `app/services/intelligence/presets/research.py` (stub)**

```python
"""Research-domain confidence preset.

Bit-identical replacement for app/agents/research/tools/synthesizer.py:
calculate_confidence. Will be wired up in Plan 112-05 (Research refactor).
"""

from __future__ import annotations


def research_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Stub — implemented in Task 4. Do not call yet."""
    raise NotImplementedError("Implemented in Plan 112-02 Task 4")
```

- [ ] **Step 6: Create `tests/unit/services/intelligence/__init__.py` (empty)**

```python
```

(Zero-byte file. Required for pytest to discover the test directory.)

- [ ] **Step 7: Verify the package imports**

From PowerShell:
```powershell
uv run python -c "from app.services.intelligence import score_confidence, to_band, presets, ConfidenceBand; print('imports OK')"
```

Expected: `imports OK`. Any ImportError means a typo in module structure — fix before committing.

- [ ] **Step 8: Commit the skeleton**

```bash
git add app/services/intelligence/ tests/unit/services/intelligence/__init__.py
git commit -m "feat(112-02): scaffold app/services/intelligence package with stubs"
```

---

### Task 3: Write failing unit tests

**Files:**
- Create: `tests/unit/services/intelligence/test_confidence.py`
- Create: `tests/unit/services/intelligence/test_presets_research.py`

- [ ] **Step 1: Create `tests/unit/services/intelligence/test_confidence.py`**

```python
"""Unit tests for app.services.intelligence.confidence."""

from __future__ import annotations

import math

import pytest

from app.services.intelligence.confidence import score_confidence, to_band


# ---------------------------------------------------------------------------
# score_confidence
# ---------------------------------------------------------------------------


def test_score_confidence_basic_weighted_sum():
    """A simple two-input case computes (0.8 * 0.5) + (0.6 * 0.5) = 0.7."""
    result = score_confidence(
        inputs={"a": 0.8, "b": 0.6},
        weights={"a": 0.5, "b": 0.5},
    )
    assert math.isclose(result, 0.7, abs_tol=1e-9)


def test_score_confidence_clamps_to_max_one():
    """Weighted sum exceeding 1.0 is clamped to 1.0."""
    result = score_confidence(
        inputs={"a": 2.0},
        weights={"a": 1.0},
    )
    assert result == 1.0


def test_score_confidence_clamps_to_min_zero():
    """Negative weighted sum is clamped to 0.0."""
    result = score_confidence(
        inputs={"a": -2.0},
        weights={"a": 0.5},
    )
    assert result == 0.0


def test_score_confidence_rejects_key_mismatch():
    """Input keys and weight keys must match exactly."""
    with pytest.raises(ValueError, match="key mismatch|keys"):
        score_confidence(
            inputs={"a": 0.5, "b": 0.5},
            weights={"a": 0.5, "c": 0.5},
        )


def test_score_confidence_rejects_weights_over_one():
    """Weights summing above 1.0 (with epsilon) are rejected."""
    with pytest.raises(ValueError, match="weights sum"):
        score_confidence(
            inputs={"a": 0.5, "b": 0.5},
            weights={"a": 0.7, "b": 0.7},  # sums to 1.4
        )


def test_score_confidence_accepts_weights_summing_to_one():
    """Weights summing to exactly 1.0 are accepted."""
    result = score_confidence(
        inputs={"a": 0.8, "b": 0.4},
        weights={"a": 0.5, "b": 0.5},
    )
    assert math.isclose(result, 0.6, abs_tol=1e-9)


def test_score_confidence_accepts_weights_summing_under_one():
    """Weights summing below 1.0 are accepted (caller's choice)."""
    result = score_confidence(
        inputs={"a": 1.0, "b": 1.0},
        weights={"a": 0.3, "b": 0.3},
    )
    assert math.isclose(result, 0.6, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# to_band
# ---------------------------------------------------------------------------


def test_to_band_low():
    """Below 0.50 default threshold is 'low'."""
    assert to_band(0.0) == "low"
    assert to_band(0.49) == "low"
    assert to_band(0.499999) == "low"


def test_to_band_medium():
    """Inclusive [0.50, 0.75) is 'medium'."""
    assert to_band(0.50) == "medium"
    assert to_band(0.60) == "medium"
    assert to_band(0.749999) == "medium"


def test_to_band_high():
    """Inclusive [0.75, 1.0] is 'high'."""
    assert to_band(0.75) == "high"
    assert to_band(0.90) == "high"
    assert to_band(1.0) == "high"


def test_to_band_custom_thresholds():
    """Caller can override band thresholds."""
    # Tighter: only > 0.90 is high
    assert to_band(0.85, low_threshold=0.30, high_threshold=0.90) == "medium"
    assert to_band(0.91, low_threshold=0.30, high_threshold=0.90) == "high"


def test_to_band_monotonic():
    """Higher score never returns a lower band."""
    bands_order = {"low": 0, "medium": 1, "high": 2}
    prev_band_rank = -1
    for score in [0.0, 0.1, 0.3, 0.49, 0.50, 0.65, 0.749, 0.75, 0.85, 1.0]:
        band = to_band(score)
        rank = bands_order[band]
        assert rank >= prev_band_rank, f"non-monotonic at score={score}"
        prev_band_rank = rank
```

- [ ] **Step 2: Create `tests/unit/services/intelligence/test_presets_research.py`**

```python
"""Unit tests for app.services.intelligence.presets.research.

Includes a Hypothesis-driven property test asserting bit-identity with
the existing app/agents/research/tools/synthesizer.py:calculate_confidence.
The property test runs in Task 5 — this file gets it now as part of TDD red.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.research.tools.synthesizer import (
    calculate_confidence as legacy_calculate_confidence,
)
from app.services.intelligence.presets.research import research_confidence


# ---------------------------------------------------------------------------
# Known-good outputs (sanity)
# ---------------------------------------------------------------------------


def test_research_confidence_max_inputs_returns_one():
    """All inputs at 1.0 and zero contradictions saturates to 1.0."""
    # 1.0 * 0.35 + 1.0 * 0.30 + 1.0 * 0.20 + 1.0 * 0.15 = 1.00
    result = research_confidence(
        track_agreement=1.0,
        source_quality=1.0,
        freshness=1.0,
        contradictions_found=0,
    )
    assert math.isclose(result, 1.0, abs_tol=1e-9)


def test_research_confidence_zero_inputs_returns_fifteen_hundredths():
    """All evidence inputs at 0 with zero contradictions returns 0.15.

    Why: contradiction_penalty = 0, so (1 - penalty) = 1.0, times 0.15 weight.
    """
    result = research_confidence(
        track_agreement=0.0,
        source_quality=0.0,
        freshness=0.0,
        contradictions_found=0,
    )
    assert math.isclose(result, 0.15, abs_tol=1e-9)


def test_research_confidence_negative_freshness_clamped_at_zero():
    """Negative freshness is floor-clamped at 0 (matching legacy behavior).

    This is the subtle behavior the spec almost missed — freshness has
    an input-side max(0.0, freshness) step before being multiplied by 0.20.
    """
    result_neg = research_confidence(
        track_agreement=0.5,
        source_quality=0.5,
        freshness=-1.0,
        contradictions_found=0,
    )
    result_zero = research_confidence(
        track_agreement=0.5,
        source_quality=0.5,
        freshness=0.0,
        contradictions_found=0,
    )
    assert math.isclose(result_neg, result_zero, abs_tol=1e-9)


def test_research_confidence_many_contradictions_saturate_penalty():
    """20+ contradictions all produce the same minimum-confidence floor."""
    # contradiction_penalty = min(1.0, n * 0.05). At n=20, penalty=1.0;
    # at n=100, penalty still capped at 1.0. So (1 - penalty) = 0 for both.
    result_20 = research_confidence(
        track_agreement=1.0,
        source_quality=1.0,
        freshness=1.0,
        contradictions_found=20,
    )
    result_100 = research_confidence(
        track_agreement=1.0,
        source_quality=1.0,
        freshness=1.0,
        contradictions_found=100,
    )
    assert math.isclose(result_20, result_100, abs_tol=1e-9)
    # Expected: 1.0*0.35 + 1.0*0.30 + 1.0*0.20 + (1-1.0)*0.15 = 0.85
    assert math.isclose(result_20, 0.85, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Property-based regression: bit-identity with legacy calculate_confidence
# ---------------------------------------------------------------------------


@given(
    track_agreement=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    source_quality=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    freshness=st.floats(min_value=-0.5, max_value=1.0, allow_nan=False),
    contradictions_found=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=10000, deadline=None)
def test_research_confidence_matches_legacy(
    track_agreement, source_quality, freshness, contradictions_found,
):
    """research_confidence must be bit-identical to legacy calculate_confidence.

    This is the load-bearing test for Plan 112-02. If it fails, Plan 112-05
    (Research refactor) cannot proceed without behavioral drift. We run
    10,000 random inputs to catch any subtle formula difference.
    """
    new = research_confidence(
        track_agreement=track_agreement,
        source_quality=source_quality,
        freshness=freshness,
        contradictions_found=contradictions_found,
    )
    legacy = legacy_calculate_confidence(
        track_agreement=track_agreement,
        source_quality=source_quality,
        freshness=freshness,
        contradictions_found=contradictions_found,
    )
    assert math.isclose(new, legacy, abs_tol=1e-12), (
        f"Drift at inputs=({track_agreement}, {source_quality}, {freshness}, "
        f"{contradictions_found}): new={new}, legacy={legacy}"
    )
```

- [ ] **Step 3: Install Hypothesis if not already** (from PowerShell):

If Task 1 Step 2 showed Hypothesis missing:
```powershell
uv run uv add --dev hypothesis
```

(Note: `uv run uv add` — the workstation's `uv.cmd` doesn't expose `uv add` directly; same workaround used in Plan 112-01 Task 2.)

If Hypothesis was already installed, skip this step.

- [ ] **Step 4: Run the tests — they should all FAIL with NotImplementedError**

From PowerShell:
```powershell
uv run pytest tests/unit/services/intelligence/ -v --tb=short
```

Expected: every test in both files errors with `NotImplementedError: Implemented in Plan 112-02 Task 4`. The Hypothesis test will fail on the first generated input. This proves the tests have signal.

- [ ] **Step 5: Commit the failing tests**

```bash
git add tests/unit/services/intelligence/test_confidence.py \
        tests/unit/services/intelligence/test_presets_research.py \
        pyproject.toml uv.lock
git commit -m "test(112-02): add failing unit + property tests for confidence module"
```

NOTE: include `pyproject.toml` and `uv.lock` ONLY if Hypothesis was newly installed. Otherwise skip them.

---

### Task 4: Implement `score_confidence`, `to_band`, `research_confidence` (GREEN)

**Files:**
- Modify: `app/services/intelligence/confidence.py`
- Modify: `app/services/intelligence/presets/research.py`

- [ ] **Step 1: Replace `app/services/intelligence/confidence.py` with the real implementation**

```python
"""Generic weighted confidence scorer and band classifier.

Used by per-agent presets (presets/research.py, presets/data.py, ...).
"""

from __future__ import annotations

from collections.abc import Mapping

from app.services.intelligence.schemas import ConfidenceBand

_WEIGHTS_SUM_EPSILON = 1e-4


def score_confidence(
    inputs: Mapping[str, float],
    weights: Mapping[str, float],
) -> float:
    """Compute a clamped weighted-sum confidence score.

    Args:
        inputs: Named signals (e.g., {"track_agreement": 0.8, "freshness": 0.6}).
                Each value should be normalized to [0.0, 1.0] by the caller,
                but the function does not enforce that (presets may apply
                domain-specific normalization first).
        weights: Same keys as inputs. Must sum to <= 1.0 (with small epsilon).

    Returns:
        Confidence score clamped to [0.0, 1.0].

    Raises:
        ValueError: if input/weight keys mismatch or weights sum exceeds 1.0.
    """
    if set(inputs) != set(weights):
        raise ValueError(
            f"input/weight key mismatch: {set(inputs) ^ set(weights)}"
        )
    weights_sum = sum(weights.values())
    if weights_sum > 1.0 + _WEIGHTS_SUM_EPSILON:
        raise ValueError(f"weights sum > 1.0: {weights_sum}")

    raw = sum(inputs[k] * weights[k] for k in inputs)
    return max(0.0, min(1.0, raw))


def to_band(
    score: float,
    *,
    low_threshold: float = 0.50,
    high_threshold: float = 0.75,
) -> ConfidenceBand:
    """Classify a raw confidence float into a band.

    Defaults match Research Agent's existing convention:
    < 0.50 = low, 0.50 - 0.75 (exclusive) = medium, >= 0.75 = high.

    Args:
        score: Confidence in [0.0, 1.0].
        low_threshold: Scores below this are "low".
        high_threshold: Scores at or above this are "high".

    Returns:
        One of "low", "medium", "high".
    """
    if score < low_threshold:
        return "low"
    if score < high_threshold:
        return "medium"
    return "high"
```

- [ ] **Step 2: Replace `app/services/intelligence/presets/research.py` with the real implementation**

```python
"""Research-domain confidence preset.

Bit-identical replacement for app/agents/research/tools/synthesizer.py:
calculate_confidence. Plan 112-05 wires Research onto this implementation.
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

RESEARCH_WEIGHTS = {
    "track_agreement": 0.35,
    "source_quality": 0.30,
    "freshness": 0.20,
    "contradiction_adjusted": 0.15,
}


def research_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Compute research-domain confidence from multi-track signals.

    Preserves the legacy formula exactly:
        contradiction_penalty = min(1.0, contradictions_found * 0.05)
        freshness_clamped     = max(0.0, freshness)
        confidence = (track_agreement * 0.35)
                   + (source_quality   * 0.30)
                   + (freshness_clamped * 0.20)
                   + ((1.0 - contradiction_penalty) * 0.15)
        return max(0.0, min(1.0, confidence))

    Args:
        track_agreement: Cross-validated finding ratio in [0.0, 1.0].
        source_quality: Average source relevance in [0.0, 1.0].
        freshness: Recency score; values < 0 are floor-clamped at 0 (legacy).
        contradictions_found: Count of contradictions; penalty saturates at 20.

    Returns:
        Confidence in [0.0, 1.0].
    """
    contradiction_penalty = min(1.0, contradictions_found * 0.05)
    freshness_clamped = max(0.0, freshness)

    return score_confidence(
        inputs={
            "track_agreement": track_agreement,
            "source_quality": source_quality,
            "freshness": freshness_clamped,
            "contradiction_adjusted": 1.0 - contradiction_penalty,
        },
        weights=RESEARCH_WEIGHTS,
    )
```

- [ ] **Step 3: Run the tests — they should now PASS** (from PowerShell):

```powershell
uv run pytest tests/unit/services/intelligence/ -v --tb=short
```

Expected: all unit tests PASS. The Hypothesis property test (`test_research_confidence_matches_legacy`) runs 10,000 generated inputs and must pass on every one. The full run may take 15-60 seconds depending on Hypothesis's pacing.

If the Hypothesis test fails: it will print the minimal counterexample (e.g., `track_agreement=0.5, source_quality=0.3, freshness=-0.1, contradictions_found=2`). Compare `new` and `legacy` outputs at that input — the discrepancy is the bug. Common causes:
- Forgot the `freshness_clamped = max(0.0, freshness)` step (check Step 2)
- Weight values off by 0.05 (check `RESEARCH_WEIGHTS`)
- Failed to use `score_confidence`'s clamping (check return path)

Fix the preset, NOT the test. The legacy function is the ground truth.

- [ ] **Step 4: Commit the implementation**

```bash
git add app/services/intelligence/confidence.py \
        app/services/intelligence/presets/research.py
git commit -m "feat(112-02): implement score_confidence, to_band, research_confidence (GREEN)"
```

---

### Task 5: Verify package public surface

**Files:** none modified — verification only.

The public surface was defined in Task 2's `__init__.py`. Verify it imports cleanly and exposes exactly what the spec promised.

- [ ] **Step 1: Import test** (from PowerShell):

```powershell
uv run python -c "
from app.services.intelligence import (
    score_confidence,
    to_band,
    presets,
    ConfidenceBand,
)
from app.services.intelligence.presets import research_confidence
# Sanity call
score = research_confidence(0.8, 0.7, 0.6, 1)
band = to_band(score)
print(f'score={score:.3f} band={band}')
assert isinstance(score, float)
assert band in ('low', 'medium', 'high')
print('public surface OK')
"
```

Expected: prints `score=<some_float> band=<low|medium|high>` and `public surface OK`. If any ImportError, fix `__init__.py` or the offending submodule.

- [ ] **Step 2: Confirm no orphan names in `__init__.py`**

```bash
grep -E "^__all__|^from " app/services/intelligence/__init__.py
```

Expected: `from app.services.intelligence import presets`, `from app.services.intelligence.confidence import score_confidence, to_band`, `from app.services.intelligence.schemas import ConfidenceBand`, and `__all__ = ["ConfidenceBand", "presets", "score_confidence", "to_band"]`. Anything else means the public surface drifted from the spec — fix.

No commit in this task — verification only.

---

### Task 6: Lint pass

**Files:** modify only if lint flags issues.

- [ ] **Step 1: Ruff check** (from PowerShell):

```powershell
uv run ruff check app/services/intelligence/ tests/unit/services/intelligence/
```

Expected: `All checks passed!`. If errors, fix them in-place — common issues: missing trailing commas, import ordering, line length.

- [ ] **Step 2: Ruff format check**

```powershell
uv run ruff format app/services/intelligence/ tests/unit/services/intelligence/ --check
```

Expected: clean (no "Would reformat" output). If reformat needed, run without `--check`:

```powershell
uv run ruff format app/services/intelligence/ tests/unit/services/intelligence/
```

- [ ] **Step 3: Type check**

```powershell
uv run ty check app/services/intelligence/
```

Expected: no errors. If type errors appear, common fixes:
- Missing return type annotations
- `Mapping[str, float]` instead of `dict[str, float]` for parameters (we already use Mapping)
- Forward references in `from __future__ import annotations` files

- [ ] **Step 4: Re-run tests to confirm lint/format changes didn't break anything**

```powershell
uv run pytest tests/unit/services/intelligence/ --tb=no -q
```

Expected: same pass count as Task 4 Step 3.

- [ ] **Step 5: If any fixes were committed in Steps 1-3, commit them**

```bash
git add app/services/intelligence/ tests/unit/services/intelligence/
git commit -m "style(112-02): apply ruff and ty fixes to intelligence package"
```

If no fixes were needed, no commit.

---

### Task 7: Plan 112-02 acceptance sign-off

**Files:** none modified — verification only.

Cross-check against the spec acceptance criteria covered by this plan:

- [ ] **Spec line: `from app.services.intelligence import score_confidence, to_band, presets, ConfidenceBand` succeeds** — verified Task 5 Step 1.

- [ ] **Spec line: `to_band` returns `Literal["low", "medium", "high"]` with default thresholds 0.50 / 0.75** — verified by `test_to_band_*` in `test_confidence.py`.

- [ ] **Spec line: `research_confidence(...) == old calculate_confidence(...)` over 10k Hypothesis-generated inputs** — verified by `test_research_confidence_matches_legacy`.

- [ ] **Spec line: No new ADK tools registered** — purely library work; nothing in this plan touches tool registries. Verify with:

```bash
git diff --name-only spec-b-clean..HEAD | grep -E "tool_id|tools_manifest|registry" || echo "no tool surface changes"
```

Expected: `no tool surface changes`.

- [ ] **Step 1: Final test run**

From PowerShell:
```powershell
uv run pytest tests/unit/services/intelligence/ -v --tb=short
```

Expected: all unit tests PASS, Hypothesis property test PASS (10,000 examples).

- [ ] **Step 2: Confirm commit history is the expected TDD cycle**

```bash
git log --oneline phase-112-01-kg-findings-broaden | head -10
```

Expected (most recent first, atop the 4 Plan 112-01 commits):
- `style(112-02): apply ruff and ty fixes` (optional, only if lint fixes happened)
- `feat(112-02): implement score_confidence, to_band, research_confidence (GREEN)`
- `test(112-02): add failing unit + property tests for confidence module`
- `feat(112-02): scaffold app/services/intelligence package with stubs`
- (then the Plan 112-01 commits)

- [ ] **Step 3: Plan 112-02 complete. Plan 112-03 (claims module) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| New package at `app/services/intelligence/` | Task 2 |
| `confidence.py` with `score_confidence` (generic weighted scorer) | Task 2 (stub), Task 4 (impl) |
| `confidence.py` with `to_band` (band classifier, configurable thresholds) | Task 2 (stub), Task 4 (impl) |
| `schemas.py` with `ConfidenceBand` Literal | Task 2 |
| `presets/research.py` with `research_confidence` bit-identical to legacy | Task 2 (stub), Task 4 (impl) |
| `presets/__init__.py` re-exports | Task 2 |
| `__init__.py` public surface | Task 2, Task 5 |
| Property-based regression test (10k Hypothesis inputs) | Task 3, Task 4 |
| `freshness_clamped = max(0.0, freshness)` legacy behavior preserved | Task 4 (impl), `test_research_confidence_negative_freshness_clamped_at_zero` |
| `contradiction_penalty = min(1.0, n * 0.05)` saturation preserved | Task 4 (impl), `test_research_confidence_many_contradictions_saturate_penalty` |
| Final `max(0.0, min(1.0, score))` clamp | Task 4 (impl) — via `score_confidence`'s clamping |
| No new ADK tools | Task 7 verification |
| Lint clean (ruff + ty) | Task 6 |

All spec lines covered. No placeholders. No unmapped requirements.
