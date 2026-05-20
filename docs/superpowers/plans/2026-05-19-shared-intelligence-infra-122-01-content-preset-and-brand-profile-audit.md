# Shared Intelligence Infrastructure — Plan 122-01: Content Preset + Brand-Profile Embedding Audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `presets/content.py` (Content-domain confidence preset with the **per-claim-type override layer** that distinguishes Content from every prior agent), wire it through the Content director + 3 sub-agents (VideoDirector, GraphicDesigner, Copywriter) so every output begins to carry `confidence + band`, and **audit two pre-requisite surfaces before the rest of Phase 122 lands**:

1. **Brand-profile embedding infrastructure** — Plan 122-02's idempotent render cache key depends on `brand_profile_version`, and `brand_fidelity_score` (Plan 122-03) needs a `visual_style` embedding to compare against. If either is missing the plan must escalate to Phase 121.5 *before* 122-02 starts.
2. **Self-improvement engine entanglement** — per Decision #8 of the rollout spec and `docs/self-improvement-policy.md`, each phase's first sub-plan audits `app/services/self_improvement_engine.py` for hard-coded references to current Content sub-agent shapes that our preset/claim changes might silently break.

**Architecture:** Mirror of `presets/data.py` and `presets/research.py` with **one structural addition**: Content is the first agent whose preset has *per-claim-type overrides* (e.g., `asset_origin_claim → 1.0`, `seo_performance_cohort → recency dominates`). The override layer composes with — does not replace — the generic weights. Implementation strategy is settled below to remove ambiguity.

**Tech Stack:** `app/services/intelligence/presets/content.py` (new), `app/services/intelligence/presets/__init__.py` (extended), `app/agents/content/agent.py` + `app/agents/content/tools.py` (wired call sites), `tests/unit/services/intelligence/presets/test_content.py` (new).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 122 — Content Agent adoption.

**Out of scope:** Idempotent Canva/Veo render cache (Plan 122-02), claim emission per sub-agent (Plan 122-03), MILESTONES.md edit (already done in design commit), Phase 121.5 itself (this plan only decides whether 121.5 is required).

---

## File structure

**Create:**
- `app/services/intelligence/presets/content.py` — `content_confidence(...)` + per-claim-type override resolver
- `tests/unit/services/intelligence/presets/test_content.py` — preset unit tests (generic + per-claim overrides)
- `docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md` — written audit report; the source-of-truth artifact for the 121.5 escalation decision
- `docs/superpowers/audits/2026-05-19-content-self-improvement-audit.md` — written audit report on engine entanglement

**Modify:**
- `app/services/intelligence/presets/__init__.py` — re-export `content_confidence` and `CLAIM_TYPE_OVERRIDES`
- `app/agents/content/tools.py` — wire `content_confidence` into the `simple_create_content` return payload (lightweight first call site; sub-agents wire in Plan 122-03)

---

## Pre-flight context

### The preset signature

```python
async def content_confidence(
    brand_alignment_score: float,
    performance_sample_size: int,
    recency_hours: float,
    statistical_significance: float,
    engagement_lift_magnitude: float,
    *,
    claim_type: str | None = None,
    sample_size_threshold: int = 50,
    recency_horizon_hours: float = 720,
) -> float:
    ...
```

`claim_type` is **optional**. When `None`, the function applies the generic weighted-sum formula (the same shape as `data_confidence`). When provided, the function consults `CLAIM_TYPE_OVERRIDES[claim_type]` and applies the override rule on top of (or *instead of*) the generic formula.

### Generic weights — the baseline formula

```python
CONTENT_WEIGHTS: dict[str, float] = {
    "brand_alignment_score":     0.30,
    "performance_sample_size":   0.25,
    "recency":                   0.20,
    "statistical_significance":  0.15,
    "engagement_lift_magnitude": 0.10,
}
```

Normalization (inside `content_confidence` before calling `score_confidence`):
- `brand_alignment_score` — caller passes a float in [0, 1]; pass through.
- `performance_sample_size` — normalize via `min(1.0, n / sample_size_threshold)`.
- `recency` — `max(0.0, 1.0 - min(1.0, recency_hours / recency_horizon_hours))`.
- `statistical_significance` — caller passes a p-value-derived signal already in [0, 1] (e.g., `1 - p`).
- `engagement_lift_magnitude` — caller passes lift expressed as a [0, 1] saturated ratio.

### Per-claim-type override layer — settled implementation

The override layer is **the single source of ambiguity flagged by the spec**. We resolve it here, in this plan, as a **module-level config table** (not a separate branch in code, not a runtime hook). The table lives next to `CONTENT_WEIGHTS` in `presets/content.py`:

```python
# Per-claim-type override rules.
#
# Each entry is one of three shapes:
#   1. {"constant": float}                          → return this value, bypass weights entirely
#   2. {"weights": dict[str, float]}                → use these weights instead of CONTENT_WEIGHTS
#   3. {"weights": dict, "min_sample_size": int,    → use weights, but cap if sample size below threshold
#       "low_sample_cap": float}
#
# Composition rule (settled): the override REPLACES the generic weights for
# the named claim_type. It does NOT compose multiplicatively — that would
# couple two formulas implicitly and make calibration hard. If a claim type
# is absent from this table, the generic CONTENT_WEIGHTS apply unchanged.
CLAIM_TYPE_OVERRIDES: dict[str, dict] = {
    # Provenance is deterministic — we KNOW the asset came from our pipeline.
    "asset_origin_claim": {"constant": 1.0},

    # brand_fidelity_score is driven solely by brand_alignment_score.
    "brand_fidelity_score": {
        "weights": {"brand_alignment_score": 1.0},
    },

    # SEO claims are time-sensitive; recency dominates.
    "seo_performance_cohort": {
        "weights": {
            "brand_alignment_score":     0.10,
            "performance_sample_size":   0.20,
            "recency":                   0.40,
            "statistical_significance":  0.20,
            "engagement_lift_magnitude": 0.10,
        },
    },

    # Hook comparison claims need adequate sample to be trustworthy.
    "hook_performance_comparative": {
        "weights": CONTENT_WEIGHTS,
        "min_sample_size": 15,    # per variant
        "low_sample_cap": 0.65,
    },
}
```

**Composition decision:** override REPLACES, does not multiply. Rationale: composing two weight vectors implicitly makes weights non-interpretable. A reviewer reading `CLAIM_TYPE_OVERRIDES["seo_performance_cohort"]` should see the *full* effective weights, not have to multiply them against the generic table mentally.

**`asset_origin_claim` constant=1.0 rationale:** when the Video Director writes a claim like *"this asset was rendered by execute_content_pipeline run_id=…"*, we have ground-truth provenance — no statistical inference is involved. Returning 1.0 communicates this honestly downstream (it will surface as `band="high"` always).

**`hook_performance_comparative` low-sample cap rationale:** A/B style hooks routinely report wins on n=3 per variant. The spec sets the floor at n>=15/variant. Below that, even a "high" score gets capped at 0.65 (i.e., `band="medium"`) so the executive layer doesn't overweight an underpowered comparison.

### Audit deliverables — separate files, both required

The brand-profile and self-improvement audits each produce a markdown report. We file them under `docs/superpowers/audits/` so they remain discoverable after the plan ships. Their conclusions feed the Phase 122 acceptance check. Without these audits, the Phase 122 rollout has no shared truth on whether 121.5 is needed.

Environment quirks: same as prior plans (Windows-PowerShell-first, `uv` is the only Python entry, integration tests need `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`).

---

## Tasks

### Task 1: Pre-flight — confirm shared intelligence package is healthy

**Files:** no edits in this task.

- [ ] **Step 1: Confirm prior phases shipped the symbols we depend on**

```bash
grep -E "^async def (write_claim|search_claims_semantic|detect_contradictions)" app/services/intelligence/claims.py
grep -E "^def score_confidence" app/services/intelligence/confidence.py
grep -E "^def to_band" app/services/intelligence/confidence.py
grep -E "^def (data_confidence|research_confidence)" app/services/intelligence/presets/*.py
ls supabase/migrations/20260518000000_broaden_kg_findings_for_shared_claims.sql
ls supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql
```

Expected: every line returns a match. If any is missing, the Phase 113 lineage isn't merged into this branch — stop and resolve the missing dependency before continuing.

- [ ] **Step 2: Confirm the Content director and sub-agent shapes match the spec**

```bash
grep -E "_create_(video_director|graphic_designer|copywriter)" app/agents/content/agent.py
grep -E "create_content_agent" app/agents/content/agent.py
```

Expected: 3 sub-agent factories + 1 director factory. If the agent has been refactored mid-roadmap, the claim-emission plan (122-03) will need to be rewritten — surface that early.

No commit in this task; it is read-only verification.

### Task 2: Brand-profile embedding infrastructure audit

**Files:**
- Create: `docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md`

This audit answers two yes/no questions and records the evidence:

1. Does `brand_profiles` have a `version` column (or equivalent monotonically-increasing token) suitable for embedding into the Canva/Veo render cache key?
2. Does `brand_profiles` have an `embedding` column populated from `visual_style + voice_tone + voice_examples`, suitable for comparison against generated-asset embeddings to derive `brand_fidelity_score`?

If **either** is missing, the audit concludes with: **"Phase 121.5 required — schema + backfill + write-trigger for brand_profile embedding."** This is the load-bearing escalation gate.

- [ ] **Step 1: Inspect the brand_profiles schema**

```bash
ls supabase/migrations/*brand_profile*
grep -E "(embedding|version|profile_version)" supabase/migrations/20260321000000_brand_profiles.sql
grep -rE "brand_profile_version|brand_profiles.version|brand_profiles.embedding" app/ supabase/migrations/ 2>/dev/null
```

Expected (based on snapshot at planning time): the migration defines `id`, `user_id`, `voice_tone`, `voice_personality`, `voice_examples`, `visual_style` (JSONB), `audience_*`, `platform_rules`, `content_rules`, `forbidden_terms`, `created_at`, `updated_at` — **no `version` and no `embedding`**.

- [ ] **Step 2: Inspect the brand_profile read path for any computed-on-read version surrogate**

```bash
grep -nE "updated_at|version" app/agents/tools/brand_profile.py
grep -nE "updated_at|version" app/services/brand_voice_service.py
```

`updated_at` *could* in principle serve as a poor-man's version, but the render cache key needs a stable, monotonically-increasing token that the user can reason about (so they can identify when their cache invalidated). `updated_at` is a timestamp — close, but its precision and timezone behaviour make it a brittle key. **The audit must record `updated_at` as not sufficient and recommend an explicit integer/text `version`.**

- [ ] **Step 3: Write the audit report**

Path: `docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md`

Contents (full markdown body, ~80 lines, structured as below):

```markdown
# Brand-Profile Embedding Infrastructure Audit (Phase 122 prerequisite)

**Date:** 2026-05-19
**Author:** Phase 122-01 audit task
**Decision required by:** Phase 122-02 kickoff
**Outcome:** ESCALATE_TO_121_5 / PROCEED  (fill in based on evidence below)

## Question 1 — Versioning

**Required by:** Plan 122-02 cache key
  `render_cache_key = sha256(template_id + brand_profile_version + prompt_text + style_preset + dimensions)`

**Evidence:**
- `supabase/migrations/20260321000000_brand_profiles.sql` columns: <list>
- Presence of `version` column: <yes/no>
- Surrogate available (`updated_at`): <yes/no — but not adequate>

**Conclusion:** <explicit>

## Question 2 — Embedding column + backfill

**Required by:** Plan 122-03 `brand_fidelity_score`
  Score is derived from `cosine_similarity(asset_embedding, brand_profile.embedding)`.

**Evidence:**
- `embedding` column in `brand_profiles`: <yes/no>
- Population strategy if column exists: <trigger / app-write / backfill job / none>
- pgvector extension enabled (required for column type): <yes/no>

**Conclusion:** <explicit>

## Overall decision

- If both questions answered "yes" → audit conclusion = PROCEED. Phase 122-02 + 122-03 may begin.
- If either answered "no" → audit conclusion = ESCALATE_TO_121_5.
  - Phase 121.5 ships:
    1. `ALTER TABLE brand_profiles ADD COLUMN version INTEGER NOT NULL DEFAULT 1;`
       plus `BEFORE UPDATE` trigger to bump `version` on any field change.
    2. `ALTER TABLE brand_profiles ADD COLUMN embedding vector(768);`
       (matches `kg_findings.embedding` dimension).
    3. Backfill job: for each existing row, generate embedding from concatenated
       `voice_tone + voice_personality + voice_examples + visual_style` and write.
    4. Write-path hook in `update_brand_profile` to refresh `embedding` on field change.
    5. RLS unchanged; service-role bypass policy already covers the new columns.

## Recommendation (filled at audit time)

<one paragraph: e.g., "Evidence shows no `version` and no `embedding` columns;
escalate to Phase 121.5. Block Phase 122-02 until 121.5 ships.">
```

- [ ] **Step 4: Fill in the audit based on actual evidence found in Step 1+2**

Based on snapshot taken at planning time (May 2026), the expected outcome is **ESCALATE_TO_121_5**: neither `version` nor `embedding` exists on `brand_profiles`. The audit report must capture this with the exact column list pulled from the migration file as evidence.

- [ ] **Step 5: Commit the audit**

```bash
git add docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md
git commit -m "audit(122-01): brand-profile embedding infrastructure audit (escalation decision)"
```

If the audit conclusion is ESCALATE_TO_121_5, **stop the Phase 122 rollout here** and open Phase 121.5 planning. Document the stop in `MILESTONES.md`:

```markdown
- Phase 121.5: Brand-profile embedding infrastructure (unblocks Phase 122) — 1 week
```

Tasks 3 onwards in this plan still ship — the *preset* itself doesn't depend on the embedding column, only the render cache and claim emission do.

### Task 3: Self-improvement engine entanglement audit

**Files:**
- Create: `docs/superpowers/audits/2026-05-19-content-self-improvement-audit.md`

Per Decision #8 of the rollout spec and `docs/self-improvement-policy.md`, the engine may auto-modify some agent shapes. We must record which Content surfaces it touches before the preset and claim changes land, so a future regression can be traced.

- [ ] **Step 1: Grep the engine for Content references**

```bash
grep -nE "content|cont_agent|ContentAgent|CONT|VideoDirector|GraphicDesigner|Copywriter" app/services/self_improvement_engine.py
grep -nE "content|cont_agent|ContentAgent|CONT|VideoDirector|GraphicDesigner|Copywriter" app/services/self_improvement_settings.py
```

Expected (per spec snapshot): the engine has a `_agent_id_to_domain` mapping with `"CON": "content"`. That mapping is brittle to any agent_id rename, but does not bind to specific tool names or sub-agent shapes — so the Phase 122 changes are unlikely to break it. Verify in the audit.

- [ ] **Step 2: Check `skill_experiment_evaluator.py` (if present)**

```bash
ls app/services/skill_experiment_evaluator.py 2>/dev/null || echo "NOT_PRESENT_AT_AUDIT_TIME"
```

At planning-snapshot time, no such file exists in this codebase. The audit must record that as the state of evidence — the spec mentions it explicitly because the predecessor Phase 112 spec referenced it; if it has since been renamed, removed, or never landed, the audit captures that fact rather than silently skipping.

- [ ] **Step 3: Write the audit report**

Path: `docs/superpowers/audits/2026-05-19-content-self-improvement-audit.md`

Sections:

```markdown
# Self-Improvement Engine Entanglement Audit (Phase 122 prerequisite)

**Date:** 2026-05-19
**Author:** Phase 122-01 audit task
**Scope:** `app/services/self_improvement_engine.py`,
          `app/services/self_improvement_settings.py`,
          `app/services/skill_experiment_evaluator.py` (if present).

## Findings

### 1. Direct references to Content surfaces

| Symbol/string | Location | Risk | Mitigation |
|---|---|---|---|
| `"CON"` agent_id mapping | `self_improvement_engine.py:_agent_id_to_domain` | Low — string constant | Preserve "CON" agent_id throughout Phase 122. |
| `"content"` domain | `self_improvement_engine.py:_agent_id_to_domain` | Low — string constant | Preserve "content" domain string in all claim writes. |
| (anything else found) | | | |

### 2. References to Content sub-agent factories

If the engine binds to `_create_video_director` / `_create_graphic_designer` / `_create_copywriter` by name, claim emission changes that wrap those factories would be risky. As of audit, no such references — confirm in the report.

### 3. Skill experiment evaluator

If the file exists, list which Content skills it owns and whether their telemetry shape changes after Phase 122-03 (claim emission). If the file does not exist at audit time, record that fact; the design doc references it as a *potential* surface, not a guaranteed one.

## Conclusion

<PASS / NEEDS_SHIM>: <one paragraph>
- PASS = Phase 122 may modify Content code freely without engine adjustments.
- NEEDS_SHIM = wrap renamed/moved symbols so engine continues to resolve them.
```

- [ ] **Step 4: Commit the audit**

```bash
git add docs/superpowers/audits/2026-05-19-content-self-improvement-audit.md
git commit -m "audit(122-01): self-improvement engine entanglement audit (Decision #8)"
```

### Task 4: Implement the Content preset (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/presets/test_content.py`
- Create: `app/services/intelligence/presets/content.py`
- Modify: `app/services/intelligence/presets/__init__.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for content_confidence + per-claim-type override layer."""

from __future__ import annotations

import math

import pytest


def test_content_confidence_generic_no_claim_type():
    """Without claim_type, generic CONTENT_WEIGHTS produce the expected score."""
    from app.services.intelligence.presets.content import content_confidence

    # All signals at 1.0 except recency at 0 → expected weighted sum
    # = 0.30 + 0.25 + 0.0 + 0.15 + 0.10 = 0.80
    score = content_confidence(
        brand_alignment_score=1.0,
        performance_sample_size=100,        # >= threshold 50 → 1.0
        recency_hours=10_000,               # >> horizon 720 → 0.0
        statistical_significance=1.0,
        engagement_lift_magnitude=1.0,
    )
    assert math.isclose(score, 0.80, abs_tol=1e-4)


def test_content_confidence_clamps_to_unit_interval():
    """Out-of-range inputs do not explode the output."""
    from app.services.intelligence.presets.content import content_confidence

    score_zero = content_confidence(
        brand_alignment_score=0.0,
        performance_sample_size=0,
        recency_hours=0.0,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
    )
    # recency_hours=0 → recency signal = 1.0, so result is 0.20 not 0
    assert 0.0 <= score_zero <= 1.0
    assert math.isclose(score_zero, 0.20, abs_tol=1e-4)


def test_asset_origin_claim_returns_constant_one():
    """Deterministic-provenance override returns 1.0 regardless of inputs."""
    from app.services.intelligence.presets.content import content_confidence

    score = content_confidence(
        brand_alignment_score=0.0,
        performance_sample_size=0,
        recency_hours=10_000,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
        claim_type="asset_origin_claim",
    )
    assert score == 1.0


def test_brand_fidelity_score_uses_brand_alignment_only():
    """brand_fidelity_score weight vector ignores all signals except alignment."""
    from app.services.intelligence.presets.content import content_confidence

    score = content_confidence(
        brand_alignment_score=0.7,
        performance_sample_size=0,
        recency_hours=10_000,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
        claim_type="brand_fidelity_score",
    )
    assert math.isclose(score, 0.7, abs_tol=1e-4)


def test_seo_performance_cohort_recency_dominates():
    """At equal signals = 1.0, recency now weights 0.40 not 0.20."""
    from app.services.intelligence.presets.content import content_confidence

    # All signals = 1.0, weights sum to 1.0 → score = 1.0
    score = content_confidence(
        brand_alignment_score=1.0,
        performance_sample_size=100,
        recency_hours=0.0,                  # recency=1.0
        statistical_significance=1.0,
        engagement_lift_magnitude=1.0,
        claim_type="seo_performance_cohort",
    )
    assert math.isclose(score, 1.0, abs_tol=1e-4)

    # Now drop recency: penalty should be 0.40, not 0.20
    score_no_recency = content_confidence(
        brand_alignment_score=1.0,
        performance_sample_size=100,
        recency_hours=10_000,               # recency=0.0
        statistical_significance=1.0,
        engagement_lift_magnitude=1.0,
        claim_type="seo_performance_cohort",
    )
    # Expected: 0.10 + 0.20 + 0.0 + 0.20 + 0.10 = 0.60
    assert math.isclose(score_no_recency, 0.60, abs_tol=1e-4)


def test_hook_performance_low_sample_caps_at_0_65():
    """Under-powered hook comparison caps to 0.65 even when raw score is high."""
    from app.services.intelligence.presets.content import content_confidence

    # All signals = 1.0 → raw score 1.0; but sample_size 5 < 15 floor
    score = content_confidence(
        brand_alignment_score=1.0,
        performance_sample_size=5,
        recency_hours=0.0,
        statistical_significance=1.0,
        engagement_lift_magnitude=1.0,
        claim_type="hook_performance_comparative",
    )
    assert math.isclose(score, 0.65, abs_tol=1e-4)


def test_hook_performance_adequate_sample_no_cap():
    """With sample_size >= 15, no cap applies — generic formula runs."""
    from app.services.intelligence.presets.content import content_confidence

    score = content_confidence(
        brand_alignment_score=1.0,
        performance_sample_size=30,         # >= 15 per variant
        recency_hours=0.0,
        statistical_significance=1.0,
        engagement_lift_magnitude=1.0,
        claim_type="hook_performance_comparative",
    )
    # Generic CONTENT_WEIGHTS at all 1.0 = 1.0
    assert math.isclose(score, 1.0, abs_tol=1e-4)


def test_unknown_claim_type_falls_through_to_generic():
    """Claim types not in CLAIM_TYPE_OVERRIDES use generic CONTENT_WEIGHTS."""
    from app.services.intelligence.presets.content import content_confidence

    score = content_confidence(
        brand_alignment_score=1.0,
        performance_sample_size=100,
        recency_hours=0.0,
        statistical_significance=1.0,
        engagement_lift_magnitude=1.0,
        claim_type="some_brand_new_claim_type",
    )
    assert math.isclose(score, 1.0, abs_tol=1e-4)


def test_content_weights_sum_to_one():
    """Generic weights invariant: sum to 1.0 within float epsilon."""
    from app.services.intelligence.presets.content import CONTENT_WEIGHTS

    assert math.isclose(sum(CONTENT_WEIGHTS.values()), 1.0, abs_tol=1e-4)


@pytest.mark.parametrize(
    "claim_type",
    ["brand_fidelity_score", "seo_performance_cohort", "hook_performance_comparative"],
)
def test_override_weights_sum_to_at_most_one(claim_type: str):
    """Per-claim weight vectors must satisfy the score_confidence invariant."""
    from app.services.intelligence.presets.content import CLAIM_TYPE_OVERRIDES

    override = CLAIM_TYPE_OVERRIDES[claim_type]
    if "weights" in override:
        assert sum(override["weights"].values()) <= 1.0 + 1e-4
```

- [ ] **Step 2: Run — should FAIL (module not yet created)**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_content.py -v --tb=short
```

- [ ] **Step 3: Implement `presets/content.py`**

```python
"""Content-domain confidence preset.

Phase 122-01 — pilots on the Content director + 3 sub-agents
(VideoDirector, GraphicDesigner, Copywriter).

The Content preset is the FIRST agent preset with per-claim-type overrides.
The generic CONTENT_WEIGHTS apply when no claim_type is supplied; when one
IS supplied AND is present in CLAIM_TYPE_OVERRIDES, the override REPLACES
the generic weights (does not compose multiplicatively — see plan 122-01
§ "Composition decision" for rationale).
"""

from __future__ import annotations

from app.services.intelligence.confidence import score_confidence

CONTENT_WEIGHTS: dict[str, float] = {
    "brand_alignment_score":     0.30,
    "performance_sample_size":   0.25,
    "recency":                   0.20,
    "statistical_significance":  0.15,
    "engagement_lift_magnitude": 0.10,
}


# Per-claim-type override rules.
#
# Each entry is one of three shapes:
#   1. {"constant": float}                    → return this value, bypass weights entirely
#   2. {"weights": dict[str, float]}          → use these weights instead of CONTENT_WEIGHTS
#   3. {"weights": dict, "min_sample_size": int, "low_sample_cap": float}
#                                             → use weights; cap if sample below floor
#
# Composition: the override REPLACES the generic weights for the named claim_type.
# A claim type NOT in this table uses CONTENT_WEIGHTS unchanged.
CLAIM_TYPE_OVERRIDES: dict[str, dict] = {
    "asset_origin_claim": {"constant": 1.0},
    "brand_fidelity_score": {"weights": {"brand_alignment_score": 1.0}},
    "seo_performance_cohort": {
        "weights": {
            "brand_alignment_score":     0.10,
            "performance_sample_size":   0.20,
            "recency":                   0.40,
            "statistical_significance":  0.20,
            "engagement_lift_magnitude": 0.10,
        },
    },
    "hook_performance_comparative": {
        "weights": CONTENT_WEIGHTS,
        "min_sample_size": 15,
        "low_sample_cap": 0.65,
    },
}


def _normalize_signals(
    brand_alignment_score: float,
    performance_sample_size: int,
    recency_hours: float,
    statistical_significance: float,
    engagement_lift_magnitude: float,
    *,
    sample_size_threshold: int,
    recency_horizon_hours: float,
) -> dict[str, float]:
    """Project raw signals into the [0, 1] basis used by score_confidence."""
    sample_score = min(1.0, performance_sample_size / max(1, sample_size_threshold))
    recency_score = max(0.0, 1.0 - min(1.0, recency_hours / recency_horizon_hours))
    return {
        "brand_alignment_score":     max(0.0, min(1.0, brand_alignment_score)),
        "performance_sample_size":   sample_score,
        "recency":                   recency_score,
        "statistical_significance":  max(0.0, min(1.0, statistical_significance)),
        "engagement_lift_magnitude": max(0.0, min(1.0, engagement_lift_magnitude)),
    }


def content_confidence(
    brand_alignment_score: float,
    performance_sample_size: int,
    recency_hours: float,
    statistical_significance: float,
    engagement_lift_magnitude: float,
    *,
    claim_type: str | None = None,
    sample_size_threshold: int = 50,
    recency_horizon_hours: float = 720,
) -> float:
    """Compute content-domain confidence with optional per-claim-type override.

    Args:
        brand_alignment_score: Float in [0, 1] — derived from cosine similarity
            against the user's brand_profile embedding (Plan 122-03 wires this).
        performance_sample_size: Number of impressions / views / interactions.
        recency_hours: Age in hours of the latest signal contributing to the claim.
        statistical_significance: A 1 - p_value -derived signal in [0, 1].
        engagement_lift_magnitude: Lift expressed as a saturated [0, 1] ratio.
        claim_type: Optional — when present and known, applies an override rule
            from CLAIM_TYPE_OVERRIDES instead of (not in addition to) the generic
            CONTENT_WEIGHTS.
        sample_size_threshold: Sample size at which performance signal saturates
            to 1.0. Default 50.
        recency_horizon_hours: Hour age at which recency saturates to 0.0.
            Default 720 (= 30 days).

    Returns:
        Confidence score clamped to [0.0, 1.0].
    """
    signals = _normalize_signals(
        brand_alignment_score=brand_alignment_score,
        performance_sample_size=performance_sample_size,
        recency_hours=recency_hours,
        statistical_significance=statistical_significance,
        engagement_lift_magnitude=engagement_lift_magnitude,
        sample_size_threshold=sample_size_threshold,
        recency_horizon_hours=recency_horizon_hours,
    )

    override = CLAIM_TYPE_OVERRIDES.get(claim_type) if claim_type else None

    if override is None:
        return score_confidence(inputs=signals, weights=CONTENT_WEIGHTS)

    if "constant" in override:
        return float(override["constant"])

    weights = override["weights"]
    # Filter signals to only those weights reference, so score_confidence's
    # key-mismatch check accepts the inputs.
    filtered_signals = {k: signals[k] for k in weights}
    raw = score_confidence(inputs=filtered_signals, weights=weights)

    # Low-sample cap (only for overrides that declare it).
    min_sample = override.get("min_sample_size")
    cap = override.get("low_sample_cap")
    if min_sample is not None and cap is not None and performance_sample_size < min_sample:
        return min(raw, float(cap))

    return raw
```

- [ ] **Step 4: Update `presets/__init__.py`**

```python
"""Per-agent confidence presets.

Each preset is a thin wrapper over score_confidence with domain-specific
input mapping and weights. Phase 122 adds content_confidence — the first
preset with per-claim-type overrides.
"""

from app.services.intelligence.presets.content import (
    CLAIM_TYPE_OVERRIDES,
    CONTENT_WEIGHTS,
    content_confidence,
)
from app.services.intelligence.presets.data import data_confidence
from app.services.intelligence.presets.research import research_confidence

__all__ = [
    "CLAIM_TYPE_OVERRIDES",
    "CONTENT_WEIGHTS",
    "content_confidence",
    "data_confidence",
    "research_confidence",
]
```

- [ ] **Step 5: Re-run tests — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_content.py -v --tb=short
```

Expected: all 11 tests green.

- [ ] **Step 6: Commit**

```bash
git add app/services/intelligence/presets/content.py app/services/intelligence/presets/__init__.py tests/unit/services/intelligence/presets/test_content.py
git commit -m "feat(122-01): content_confidence preset with per-claim-type overrides (GREEN)"
```

### Task 5: Property-based clamp invariants

**Files:**
- Modify: `tests/unit/services/intelligence/presets/test_content.py` — append property-based test

The generic Phase 112 testing pattern includes property-based clamping. Add the same coverage for Content.

- [ ] **Step 1: Append property test**

```python
import random


def test_content_confidence_always_clamped():
    """Random inputs always produce a score in [0.0, 1.0]."""
    from app.services.intelligence.presets.content import (
        CLAIM_TYPE_OVERRIDES,
        content_confidence,
    )

    rng = random.Random(42)
    types_to_probe = [None, *CLAIM_TYPE_OVERRIDES.keys(), "unknown_type_42"]

    for _ in range(500):
        ct = rng.choice(types_to_probe)
        score = content_confidence(
            brand_alignment_score=rng.uniform(-0.5, 1.5),
            performance_sample_size=rng.randint(-5, 1000),
            recency_hours=rng.uniform(-100.0, 1_000_000.0),
            statistical_significance=rng.uniform(-0.5, 1.5),
            engagement_lift_magnitude=rng.uniform(-0.5, 1.5),
            claim_type=ct,
        )
        assert 0.0 <= score <= 1.0, (
            f"clamp violated: score={score}, claim_type={ct}"
        )
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_content.py::test_content_confidence_always_clamped -v
```

Expected: PASS. If it fails, the normalizer or the override resolver isn't clamping correctly — fix in place before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/services/intelligence/presets/test_content.py
git commit -m "test(122-01): property-based clamp invariant for content_confidence"
```

### Task 6: Wire `content_confidence` into the first call site (`simple_create_content`)

**Files:**
- Modify: `app/agents/content/tools.py` — augment `simple_create_content` return payload

The full sub-agent wiring lands in Plan 122-03. Here we wire a single, simple call site so the preset is exercised end-to-end in this plan's CI.

- [ ] **Step 1: Add a failing test**

Append to `tests/unit/services/intelligence/presets/test_content.py`:

```python
@pytest.mark.asyncio
async def test_simple_create_content_attaches_confidence_band(monkeypatch):
    """simple_create_content's return payload now carries confidence + band."""
    from app.agents.content import tools as content_tools

    # Stub out brand profile and ContentService side effects
    async def _no_brand(*_a, **_kw):
        return {"success": True, "brand_name": "", "voice_tone": ""}

    class _StubService:
        async def save_content(self, **kw):
            return {"success": True, "ids": ["00000000-0000-0000-0000-000000000000"]}

    monkeypatch.setattr(content_tools, "get_brand_profile", _no_brand)
    monkeypatch.setattr(content_tools, "ContentService", lambda: _StubService())
    monkeypatch.setattr(content_tools, "get_current_user_id", lambda: "u1")

    result = await content_tools.simple_create_content(
        topic="Launching our new feature",
        content_type="social_post",
        platform="linkedin",
    )

    assert "confidence" in result
    assert "band" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["band"] in {"low", "medium", "high"}
```

- [ ] **Step 2: Implement minimal addition in `simple_create_content`**

In `app/agents/content/tools.py`, after building `prompt_context` and before returning, add:

```python
# --- 4.5 Confidence + band (Phase 122-01) ---
from app.services.intelligence import to_band
from app.services.intelligence.presets import content_confidence

# At fast-path call time we have no performance telemetry yet — emit a
# baseline confidence using the generic preset. Claim emission (Plan 122-03)
# refines this with real signals after publish.
_brand_alignment = 1.0 if brand_context.get("brand_name") else 0.5
_confidence = content_confidence(
    brand_alignment_score=_brand_alignment,
    performance_sample_size=0,
    recency_hours=0.0,
    statistical_significance=0.0,
    engagement_lift_magnitude=0.0,
)
_band = to_band(_confidence)
```

And include `confidence` + `band` in the final return dict.

- [ ] **Step 3: Run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/presets/test_content.py -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add app/agents/content/tools.py tests/unit/services/intelligence/presets/test_content.py
git commit -m "feat(122-01): wire content_confidence + band into simple_create_content (first call site)"
```

### Task 7: Lint, type-check, and acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/presets/ app/agents/content/tools.py tests/unit/services/intelligence/presets/test_content.py
uv run ruff format app/services/intelligence/presets/ app/agents/content/tools.py tests/unit/services/intelligence/presets/test_content.py --check
```

Fix any issues in place. Commit fixes with `style(122-01): ...`.

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/services/intelligence/presets/content.py app/agents/content/tools.py
```

Fix any complaints. The new module is small; type errors here are almost always missing-import or wrong-keyword-arg, which the test suite would have caught — but the type-checker catches them faster.

- [ ] **Step 3: Plan 122-01 acceptance cross-check**

| Acceptance criterion (from Phase 122 spec) | Verified by |
|---|---|
| `content_confidence` preset shipped | Task 4 |
| Per-claim-type overrides apply correctly | Task 4 (test cases for all 4 override types) |
| `asset_origin_claim → 1.0` | `test_asset_origin_claim_returns_constant_one` |
| `brand_fidelity_score → brand_alignment only` | `test_brand_fidelity_score_uses_brand_alignment_only` |
| `seo_performance_cohort → recency 0.40` | `test_seo_performance_cohort_recency_dominates` |
| `hook_performance_comparative → cap at 0.65 below n=15` | `test_hook_performance_low_sample_caps_at_0_65` |
| Brand-profile audit recorded; escalation decision in writing | Task 2 |
| Self-improvement engine audit recorded | Task 3 |
| One Content call site carries `confidence + band` | Task 6 |
| Lint + type-check clean | Task 7 |

- [ ] **Step 4: Decide whether Phase 122-02 can start**

If Task 2's audit concluded ESCALATE_TO_121_5: open Phase 121.5 immediately; do not start 122-02. The preset (122-01) and its first call site can ship before 121.5 — but the *render cache* depends on `brand_profile_version`, which is precisely what 121.5 unblocks.

If audit concluded PROCEED: Plan 122-02 may begin.

- [ ] **Step 5: Plan 122-01 complete.**

Next planned work in Phase 122: 122-02 (idempotent Canva/Veo render cache; depends on Phase 121.5 if escalation occurred) and 122-03 (per-sub-agent claim emission; depends on this plan's preset module).

---

## Spec coverage check

| Spec requirement (Phase 122 § design doc) | Task(s) |
|---|---|
| Ship `presets/content.py` with generic CONTENT_WEIGHTS | Task 4 |
| Per-claim-type overrides table | Task 4 (`CLAIM_TYPE_OVERRIDES`) |
| `asset_origin_claim` → 1.0 deterministic | Task 4 |
| `brand_fidelity_score` → brand_alignment only | Task 4 |
| `seo_performance_cohort` → recency dominates (0.40) | Task 4 |
| `hook_performance_comparative` → cap at 0.65 below n=15/variant | Task 4 |
| Override layer composition decision documented | Pre-flight context + module docstring |
| Brand-profile embedding infrastructure audit | Task 2 |
| Escalate to Phase 121.5 if missing | Task 2 Step 4 + acceptance Step 4 |
| Self-improvement engine entanglement audit | Task 3 |
| Lint + type-check clean | Task 7 |
| At least one call site exercises preset end-to-end | Task 6 |

All Phase 122-01 spec lines covered.
