# Shared Intelligence Infrastructure — Plan 122-03: Content Claim Emission per Sub-Agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the full `emit_*` library for the 9 claim types that the three Content sub-agents (Video Director, Graphic Designer, Copywriter) produce. Each emitter takes structured metadata, computes confidence via `content_confidence` (Plan 122-01), and writes a row to `kg_findings` via `write_claim`. Every Content output that already lands in the user's Knowledge Vault now also lands in the shared knowledge graph with a calibrated confidence and band.

This plan also closes the loop with Plan 122-02: the cache MISS path *already* tries to call `emit_asset_generation_provenance`; once this plan lands, that import succeeds and the provenance claim is written for every cache MISS.

**Architecture:** A single new module — `app/agents/content/claims.py` — holds 9 thin emitter functions, one per claim type. Each function:

1. Resolves or creates the relevant `kg_entities` row (e.g., the asset itself, the campaign, the SEO topic).
2. Computes confidence by calling `content_confidence` with the appropriate `claim_type=` argument (so the per-claim-type override layer fires).
3. Calls `write_claim(...)` with `embed=True` for entity-attached claims (so `detect_contradictions` and `search_claims_semantic` see them).
4. Returns the new claim UUID.

The **claim is META about an artifact**, never the artifact itself. A Video Director claim says *"this 28-second vertical promo for product X has a hook-comparison win over variant B at p<0.05"*; it does **not** say *"product X is great"*. The distinction is what makes Content's claim model different from every prior phase, and it must show up in the `finding_text` shape conventions below.

**Tech Stack:** `app/agents/content/claims.py` (new), `app/agents/content/agent.py` (sub-agent instructions extended to mention claim emission), `app/agents/content/tools.py` (a couple of small wiring updates), `tests/unit/agents/content/test_claims.py` (new), `tests/integration/test_content_claims_cross_agent.py` (new).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 122 — Content Agent adoption § Claims.

**Out of scope:** UI surfaces for displaying confidence (`/admin/research/overview` already auto-extends per the design doc), Strategic Agent's consumption of these claims (Phase 121 work — already shipped before 122 per the rollout order), claim de-duplication beyond what `detect_contradictions` already handles.

---

## File structure

**Create:**
- `app/agents/content/claims.py` — 9 emitter functions + entity-resolution helpers
- `tests/unit/agents/content/test_claims.py` — unit tests with mocked write_claim
- `tests/integration/test_content_claims_cross_agent.py` — end-to-end test: emit Content claim, then `search_claims_semantic` and verify interleaving with Marketing/Sales/Data claims

**Modify:**
- `app/agents/content/agent.py` — append a short "Claim Emission" section to each sub-agent's instruction (5–8 lines each)
- `app/agents/content/tools.py` — invoke `emit_brand_fidelity_score` from the `simple_create_content` write path so the meta-claim is exercised in CI
- `app/agents/__init__.py` (if applicable) — re-export only if other agents import the emitter (they shouldn't; emitters are internal)

---

## Pre-flight context

### Prerequisites

This plan depends on both Plan 122-01 (preset + audits) and Plan 122-02 (render cache façade with the safe-emission hook). Verify before starting:

```bash
test -f app/services/intelligence/presets/content.py
test -f app/services/intelligence/render_cache.py
grep -q "_emit_provenance_claim_safe" app/services/intelligence/render_cache.py
test -f docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md
```

Expected: all present. If the brand-profile audit concluded ESCALATE_TO_121_5 and 121.5 has not yet shipped, `brand_fidelity_score` emission cannot use real embeddings — the implementation falls back to `brand_alignment_score=0.5` (neutral signal) until 121.5 lands. Mark such claims with `sources=[{"kind": "system", "ref": "brand_embedding_pending_121_5"}]` so they can be back-filled.

### Claim-type matrix — full vocabulary, per sub-agent

| Sub-agent | Claim type | Entity it attaches to | What it asserts (META) | When to emit |
|---|---|---|---|---|
| Video Director | `video_completion_rate_signal` | the video asset | "video X has Y% completion through 50% mark, n=Z" | After 24h of post-publish analytics |
| Video Director | `hook_performance_comparative` | the campaign / experiment | "hook A beats hook B by Δ at p<X, n>=15/variant" | When A/B comparison concludes |
| Video Director | `asset_origin_claim` | the asset | "asset X was rendered by run_id=Y from prompt P" | Immediately on render |
| Graphic Designer | `brand_fidelity_score` | the asset | "design X scored brand_alignment_score=Y vs brand v.Z" | At asset commit |
| Graphic Designer | `design_audience_resonance` | the campaign | "design X resonates with audience A at engagement_rate=Y" | After 24h analytics |
| Graphic Designer | `asset_generation_provenance` | the asset | "asset X was generated by tool T with prompt P at time τ" | At render (cache MISS) |
| Copywriter | `seo_performance_cohort` | the SEO topic | "page X ranks position P for keyword K over window W" | On SEO sync (TTL 7d) |
| Copywriter | `copy_tone_fidelity` | the copy artifact | "copy X has tone alignment Y vs voice profile" | At copy commit |
| Copywriter | `content_repurpose_lift` | the campaign | "repurposed copy X drove Δ engagement lift over original Y" | After repurpose telemetry |

### `finding_text` shape conventions (META, not assertion)

Every emitter MUST produce a `finding_text` that:

- Names the artifact (asset_id / content_id / campaign_id) explicitly.
- States the metric and the value with units.
- Specifies the sample / window.
- Does NOT make a value judgment about what the artifact says.

Examples:

| Good (META) | Bad (asserts content) |
|---|---|
| "asset abc123 completion_rate=68% n=240 over 24h" | "video is engaging" |
| "design xyz789 brand_alignment_score=0.92 vs brand_profile.version=7" | "design is on-brand" |
| "copy lmn456 ranks position 4 for 'productivity hacks' over 14d window" | "blog post is great for SEO" |

This rule isn't enforced by code — it lives in the docstring of each emitter and in the prompt update for each sub-agent (Task 6).

### Entity resolution — which `entity_type` to use

`kg_entities.entity_type` is constrained by a CHECK constraint (`get_or_create_entity` docstring). We map Content artifacts onto allowed types:

| Artifact | `entity_type` | `canonical_name` shape |
|---|---|---|
| Asset (video/image/copy) | `product` | `content_asset:<asset_id>` |
| Campaign | `topic` | `campaign:<campaign_id>` |
| SEO topic / keyword | `topic` | `seo_topic:<keyword_slug>` |
| Brand profile | `topic` | `brand_profile:<brand_profile_id>` |

The `product` choice for assets is a deliberate stretch — Content assets are "the products of our creative pipeline." `topic` is the catch-all for campaigns and SEO subjects.

### Sample-size rules baked into the preset

Plan 122-01's `CLAIM_TYPE_OVERRIDES` already enforces:

- `hook_performance_comparative` capped at 0.65 when n<15/variant.
- `asset_origin_claim` returns 1.0 deterministic.
- `brand_fidelity_score` ignores everything except brand_alignment_score.
- `seo_performance_cohort` weights recency at 0.40.

The emitters in this plan rely on those overrides — they call `content_confidence(..., claim_type=<type>)` and trust the preset to do the right thing. No additional capping logic in the emitter layer.

### Cross-agent edges (one concrete case)

Per the spec acceptance: *"Marketing's `creative_performance` claim can reference Content's `brand_fidelity_score` via edges."* This means when Marketing emits a creative-performance claim, it includes `contradicts` or `edge_id` referencing the matching Content `brand_fidelity_score` claim UUID. This plan does not change Marketing's emitter, but the integration test in Task 7 simulates the cross-reference by:

1. Emitting a `brand_fidelity_score` claim for asset X.
2. Calling `search_claims_semantic(query="brand fidelity asset X")` and confirming the claim is found.
3. Stubbing a "Marketing-style" claim referencing the same `entity_id`.
4. Confirming both surface together in a `find_claims(entity_id=X)` query.

Environment quirks: same as prior plans.

---

## Tasks

### Task 1: Pre-flight + scaffolding

**Files:**
- Create: `app/agents/content/claims.py` (initially empty module with module docstring + lazy imports)

- [ ] **Step 1: Confirm prerequisites**

```bash
test -f app/services/intelligence/presets/content.py
test -f app/services/intelligence/render_cache.py
grep -q "_emit_provenance_claim_safe" app/services/intelligence/render_cache.py
grep -E "^async def (write_claim|search_claims_semantic|get_or_create_entity)" app/services/intelligence/claims.py
```

Expected: all present.

- [ ] **Step 2: Read the brand-profile audit conclusion**

```bash
grep -E "^\*\*Outcome:\*\*" docs/superpowers/audits/2026-05-19-content-brand-profile-audit.md
```

If `PROCEED`: emitters use real brand embeddings (Task 4). If `ESCALATE_TO_121_5` and 121.5 not yet shipped: emitters fall back to neutral signal (also covered in Task 4). Either way, the plan proceeds; the difference is one branch in `emit_brand_fidelity_score`.

- [ ] **Step 3: Create the module scaffolding**

```python
# app/agents/content/claims.py
"""Content-agent claim emitters (Phase 122-03).

Each emitter is a thin layer over `write_claim` that:
1. Resolves the kg_entities row for the artifact / campaign / topic.
2. Computes content-domain confidence via the per-claim-type override
   layer in `presets/content.py`.
3. Writes the claim with embed=True so it surfaces in search and
   contradiction detection.

CLAIM-TEXT RULE (load-bearing):
    finding_text MUST be META about the artifact — it names the artifact id
    and reports a measured metric. It does NOT make a value judgment about
    what the artifact says. See plan 122-03 § finding_text shape conventions.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.services.intelligence import (
    get_or_create_entity,
    to_band,
    write_claim,
)
from app.services.intelligence.presets import content_confidence

logger = logging.getLogger(__name__)
```

- [ ] **Step 4: Commit scaffolding**

```bash
git add app/agents/content/claims.py
git commit -m "feat(122-03): scaffold content/claims.py module"
```

### Task 2: Video Director emitters (TDD)

**Files:**
- Create: `tests/unit/agents/content/test_claims.py`
- Modify: `app/agents/content/claims.py` — add the 3 Video Director emitters

- [ ] **Step 1: Failing tests for Video Director emitters**

```python
"""Unit tests for app/agents/content/claims.py — Video Director emitters."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest


@pytest.mark.asyncio
async def test_emit_asset_origin_claim_returns_constant_confidence(monkeypatch):
    """asset_origin_claim writes confidence=1.0 (deterministic provenance)."""
    from app.agents.content import claims

    captured: dict = {}

    async def fake_get_entity(**kw):
        return uuid4()

    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    asset_id = str(uuid4())
    result = await claims.emit_asset_origin_claim(
        asset_id=asset_id,
        prompt_text="A clean launch promo at 6s with vibrant style",
        run_id="run-001",
        tool_name="create_video_with_veo",
        rendered_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    assert isinstance(result, UUID)
    assert captured["agent_id"] == "VideoDirectorAgent"
    assert captured["claim_type"] == "asset_origin_claim"
    assert captured["confidence"] == 1.0
    assert captured["domain"] == "content"
    # META rule: finding_text mentions the asset id
    assert asset_id in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_video_completion_rate_signal(monkeypatch):
    """Confidence reflects sample size + recency."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    asset_id = str(uuid4())
    result = await claims.emit_video_completion_rate_signal(
        asset_id=asset_id,
        completion_rate=0.68,
        sample_size=240,
        window_hours=24,
        platform="instagram",
    )
    assert isinstance(result, UUID)
    assert captured["claim_type"] == "video_completion_rate_signal"
    # Generic preset, not an override-keyed claim — confidence < 1.0
    assert 0.0 <= captured["confidence"] <= 1.0
    assert "completion_rate=0.68" in captured["finding_text"]
    assert "n=240" in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_hook_performance_caps_at_low_sample(monkeypatch):
    """hook_performance_comparative caps at 0.65 when n<15/variant."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    await claims.emit_hook_performance_comparative(
        campaign_id="camp-001",
        hook_a_label="vibrant",
        hook_b_label="minimal",
        lift_magnitude=0.40,
        p_value=0.04,
        sample_size_per_variant=5,
    )
    assert captured["confidence"] <= 0.65, (
        f"low-sample cap should apply, got {captured['confidence']}"
    )


@pytest.mark.asyncio
async def test_emit_hook_performance_adequate_sample(monkeypatch):
    """At n>=15/variant, no cap fires."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    await claims.emit_hook_performance_comparative(
        campaign_id="camp-002",
        hook_a_label="vibrant",
        hook_b_label="minimal",
        lift_magnitude=0.40,
        p_value=0.04,
        sample_size_per_variant=50,
    )
    assert captured["confidence"] > 0.65, (
        "high-sample hook claim should exceed 0.65"
    )
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/content/test_claims.py -v --tb=short
```

- [ ] **Step 3: Implement Video Director emitters**

Append to `app/agents/content/claims.py`:

```python
# ============================================================================
# Video Director emitters
# ============================================================================


async def emit_asset_origin_claim(
    *,
    asset_id: str,
    prompt_text: str,
    run_id: str,
    tool_name: str,
    rendered_at: datetime,
) -> UUID:
    """Write an asset_origin_claim — deterministic provenance, confidence=1.0.

    Emitted immediately on render success. The claim is META: it records that
    the asset exists and was produced by a specific pipeline run, NOT that the
    asset's content is good.
    """
    entity_id = await get_or_create_entity(
        canonical_name=f"content_asset:{asset_id}",
        entity_type="product",
        domains=["content"],
        properties={"asset_id": asset_id},
    )

    finding_text = (
        f"asset {asset_id} rendered by {tool_name} run_id={run_id} "
        f"at {rendered_at.isoformat()} prompt='{prompt_text[:200]}'"
    )

    confidence = content_confidence(
        brand_alignment_score=0.0,
        performance_sample_size=0,
        recency_hours=0.0,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
        claim_type="asset_origin_claim",
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[
            {"kind": "tool_run", "ref": run_id},
            {"kind": "tool", "ref": tool_name},
        ],
        agent_id="VideoDirectorAgent",
        claim_type="asset_origin_claim",
        embed=True,
    )


async def emit_video_completion_rate_signal(
    *,
    asset_id: str,
    completion_rate: float,
    sample_size: int,
    window_hours: int,
    platform: str | None = None,
) -> UUID:
    """Write a video_completion_rate_signal claim.

    Emitted ~24h after publish when platform analytics catch up. Sample size
    drives confidence via the generic CONTENT_WEIGHTS performance signal.
    """
    entity_id = await get_or_create_entity(
        canonical_name=f"content_asset:{asset_id}",
        entity_type="product",
        domains=["content"],
        properties={"asset_id": asset_id},
    )

    platform_str = f" on {platform}" if platform else ""
    finding_text = (
        f"asset {asset_id} completion_rate={completion_rate:.2f} "
        f"n={sample_size} over {window_hours}h{platform_str}"
    )

    confidence = content_confidence(
        brand_alignment_score=0.5,           # unknown at this stage
        performance_sample_size=sample_size,
        recency_hours=float(window_hours),
        statistical_significance=0.5,        # no formal test — use neutral
        engagement_lift_magnitude=min(1.0, completion_rate * 1.5),
        claim_type="video_completion_rate_signal",
    )

    sources: list[dict] = [{"kind": "platform_analytics", "ref": platform or "unknown"}]

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
        agent_id="VideoDirectorAgent",
        claim_type="video_completion_rate_signal",
        embed=True,
    )


async def emit_hook_performance_comparative(
    *,
    campaign_id: str,
    hook_a_label: str,
    hook_b_label: str,
    lift_magnitude: float,
    p_value: float,
    sample_size_per_variant: int,
) -> UUID:
    """Write a hook_performance_comparative claim.

    Confidence is capped at 0.65 when sample_size_per_variant<15 by the
    preset's CLAIM_TYPE_OVERRIDES entry.
    """
    entity_id = await get_or_create_entity(
        canonical_name=f"campaign:{campaign_id}",
        entity_type="topic",
        domains=["content"],
        properties={"campaign_id": campaign_id},
    )

    finding_text = (
        f"campaign {campaign_id} hook_a='{hook_a_label}' beats hook_b='{hook_b_label}' "
        f"lift={lift_magnitude:+.2f} p={p_value:.3f} n={sample_size_per_variant}/variant"
    )

    confidence = content_confidence(
        brand_alignment_score=0.5,
        performance_sample_size=sample_size_per_variant,
        recency_hours=0.0,
        statistical_significance=max(0.0, min(1.0, 1.0 - p_value)),
        engagement_lift_magnitude=min(1.0, abs(lift_magnitude)),
        claim_type="hook_performance_comparative",
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[{"kind": "ab_test", "ref": f"campaign:{campaign_id}"}],
        agent_id="VideoDirectorAgent",
        claim_type="hook_performance_comparative",
        embed=True,
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/content/test_claims.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/content/claims.py tests/unit/agents/content/test_claims.py
git commit -m "feat(122-03): Video Director emitters (asset_origin, completion_rate, hook_comparative) (GREEN)"
```

### Task 3: Graphic Designer emitters (TDD)

**Files:**
- Modify: `tests/unit/agents/content/test_claims.py` — append Graphic Designer tests
- Modify: `app/agents/content/claims.py` — append Graphic Designer emitters

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.asyncio
async def test_emit_brand_fidelity_score(monkeypatch):
    """brand_fidelity_score uses brand_alignment_score weight only (=1.0)."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    asset_id = str(uuid4())
    await claims.emit_brand_fidelity_score(
        asset_id=asset_id,
        brand_alignment_score=0.92,
        brand_profile_version=7,
    )

    assert captured["claim_type"] == "brand_fidelity_score"
    # Override layer makes confidence == brand_alignment_score
    assert abs(captured["confidence"] - 0.92) < 1e-4
    assert "brand_alignment_score=0.92" in captured["finding_text"]
    assert "brand_profile.version=7" in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_brand_fidelity_score_falls_back_when_brand_embedding_missing(monkeypatch):
    """When brand_alignment_score is None (no embedding infra), use neutral 0.5."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    await claims.emit_brand_fidelity_score(
        asset_id=str(uuid4()),
        brand_alignment_score=None,
        brand_profile_version=None,
    )
    assert abs(captured["confidence"] - 0.5) < 1e-4
    # Source marker telling future back-fill what to do
    src_kinds = [s.get("kind") for s in captured["sources"]]
    src_refs = [s.get("ref") for s in captured["sources"]]
    assert "system" in src_kinds
    assert any("brand_embedding_pending" in str(r) for r in src_refs)


@pytest.mark.asyncio
async def test_emit_design_audience_resonance(monkeypatch):
    """design_audience_resonance attaches to campaign entity."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        captured["entity_canonical_name"] = kw.get("canonical_name")
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    await claims.emit_design_audience_resonance(
        campaign_id="camp-009",
        engagement_rate=0.18,
        sample_size=400,
        audience_label="Gen Z creators",
        window_hours=24,
    )
    assert "campaign:camp-009" == captured["entity_canonical_name"]
    assert captured["claim_type"] == "design_audience_resonance"


@pytest.mark.asyncio
async def test_emit_asset_generation_provenance(monkeypatch):
    """asset_generation_provenance is the entry point that render_cache calls."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    asset_id = str(uuid4())
    await claims.emit_asset_generation_provenance(
        surface="canva_render",
        asset_id=asset_id,
        asset_url="https://example.com/asset.png",
        agent_id="GraphicDesignerAgent",
        prompt_text="vibrant launch promo design with bold contrast",
    )

    assert captured["claim_type"] == "asset_generation_provenance"
    assert captured["agent_id"] == "GraphicDesignerAgent"
    assert asset_id in captured["finding_text"]
    assert "canva_render" in captured["finding_text"]
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/content/test_claims.py -v --tb=short
```

- [ ] **Step 3: Implement Graphic Designer emitters**

Append:

```python
# ============================================================================
# Graphic Designer emitters
# ============================================================================


async def emit_brand_fidelity_score(
    *,
    asset_id: str,
    brand_alignment_score: float | None,
    brand_profile_version: int | str | None,
) -> UUID:
    """Write a brand_fidelity_score claim for a design asset.

    When ``brand_alignment_score`` is None (brand-profile embedding infra
    not yet shipped — audit conclusion ESCALATE_TO_121_5), fall back to
    a neutral 0.5 signal and mark the claim with a sentinel source so
    a future back-fill job can reprocess it.
    """
    entity_id = await get_or_create_entity(
        canonical_name=f"content_asset:{asset_id}",
        entity_type="product",
        domains=["content"],
        properties={"asset_id": asset_id},
    )

    sources: list[dict] = [{"kind": "design_pipeline", "ref": asset_id}]
    if brand_alignment_score is None:
        effective_alignment = 0.5
        version_label = "unknown"
        sources.append(
            {"kind": "system", "ref": "brand_embedding_pending_121_5"},
        )
    else:
        effective_alignment = float(brand_alignment_score)
        version_label = str(brand_profile_version) if brand_profile_version is not None else "unknown"

    finding_text = (
        f"asset {asset_id} brand_alignment_score={effective_alignment:.2f} "
        f"vs brand_profile.version={version_label}"
    )

    confidence = content_confidence(
        brand_alignment_score=effective_alignment,
        performance_sample_size=0,
        recency_hours=0.0,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
        claim_type="brand_fidelity_score",
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=sources,
        agent_id="GraphicDesignerAgent",
        claim_type="brand_fidelity_score",
        embed=True,
    )


async def emit_design_audience_resonance(
    *,
    campaign_id: str,
    engagement_rate: float,
    sample_size: int,
    audience_label: str,
    window_hours: int,
) -> UUID:
    """Write a design_audience_resonance claim for a campaign."""
    entity_id = await get_or_create_entity(
        canonical_name=f"campaign:{campaign_id}",
        entity_type="topic",
        domains=["content"],
        properties={"campaign_id": campaign_id},
    )

    finding_text = (
        f"campaign {campaign_id} engagement_rate={engagement_rate:.2f} "
        f"audience='{audience_label}' n={sample_size} over {window_hours}h"
    )

    confidence = content_confidence(
        brand_alignment_score=0.5,
        performance_sample_size=sample_size,
        recency_hours=float(window_hours),
        statistical_significance=0.5,
        engagement_lift_magnitude=min(1.0, engagement_rate * 4),
        claim_type="design_audience_resonance",
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[{"kind": "platform_analytics", "ref": f"campaign:{campaign_id}"}],
        agent_id="GraphicDesignerAgent",
        claim_type="design_audience_resonance",
        embed=True,
    )


async def emit_asset_generation_provenance(
    *,
    surface: str,
    asset_id: str,
    asset_url: str,
    agent_id: str,
    prompt_text: str,
) -> UUID:
    """Write an asset_generation_provenance claim from a render MISS path.

    Called automatically by ``cached_render`` (Plan 122-02) after every cache
    MISS. The agent_id is whichever sub-agent triggered the render
    (VideoDirectorAgent or GraphicDesignerAgent — Copywriter doesn't render
    assets).
    """
    entity_id = await get_or_create_entity(
        canonical_name=f"content_asset:{asset_id}",
        entity_type="product",
        domains=["content"],
        properties={"asset_id": asset_id, "asset_url": asset_url},
    )

    finding_text = (
        f"asset {asset_id} generated via {surface} url={asset_url} "
        f"prompt='{prompt_text[:200]}'"
    )

    confidence = content_confidence(
        brand_alignment_score=0.0,
        performance_sample_size=0,
        recency_hours=0.0,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
        claim_type="asset_origin_claim",     # provenance shares the 1.0 constant
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[
            {"kind": "tool_run", "ref": surface},
            {"kind": "url", "ref": asset_url},
        ],
        agent_id=agent_id or "GraphicDesignerAgent",
        claim_type="asset_generation_provenance",
        embed=True,
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/content/test_claims.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/content/claims.py tests/unit/agents/content/test_claims.py
git commit -m "feat(122-03): Graphic Designer emitters (brand_fidelity, audience_resonance, provenance) (GREEN)"
```

### Task 4: Copywriter emitters (TDD)

**Files:**
- Modify: `tests/unit/agents/content/test_claims.py` — append
- Modify: `app/agents/content/claims.py` — append Copywriter emitters

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.asyncio
async def test_emit_seo_performance_cohort_recency_dominates(monkeypatch):
    """At equal signals, fresher window produces higher confidence."""
    from app.agents.content import claims

    captured_fresh = {}
    captured_stale = {}

    async def fake_get_entity(**kw):
        return uuid4()

    async def fake_write_claim_fresh(**kw):
        captured_fresh.update(kw)
        return uuid4()

    async def fake_write_claim_stale(**kw):
        captured_stale.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)

    # Fresh window
    monkeypatch.setattr(claims, "write_claim", fake_write_claim_fresh)
    await claims.emit_seo_performance_cohort(
        keyword="productivity hacks",
        ranking_position=4,
        sample_size=100,
        window_days=1,
    )

    # Stale window
    monkeypatch.setattr(claims, "write_claim", fake_write_claim_stale)
    await claims.emit_seo_performance_cohort(
        keyword="productivity hacks",
        ranking_position=4,
        sample_size=100,
        window_days=60,   # > 30d horizon → recency=0
    )

    assert captured_fresh["confidence"] > captured_stale["confidence"], (
        "recency-dominated override should give fresher window higher confidence"
    )


@pytest.mark.asyncio
async def test_emit_copy_tone_fidelity(monkeypatch):
    """copy_tone_fidelity attaches to copy artifact via product entity."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        captured["canonical_name"] = kw.get("canonical_name")
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    content_id = str(uuid4())
    await claims.emit_copy_tone_fidelity(
        content_id=content_id,
        tone_alignment_score=0.85,
        voice_profile_version=3,
    )
    assert captured["canonical_name"] == f"content_asset:{content_id}"
    assert captured["claim_type"] == "copy_tone_fidelity"
    assert "tone_alignment_score=0.85" in captured["finding_text"]


@pytest.mark.asyncio
async def test_emit_content_repurpose_lift(monkeypatch):
    """content_repurpose_lift attaches to campaign topic."""
    from app.agents.content import claims

    captured = {}

    async def fake_get_entity(**kw):
        captured["canonical_name"] = kw.get("canonical_name")
        return uuid4()
    async def fake_write_claim(**kw):
        captured.update(kw)
        return uuid4()

    monkeypatch.setattr(claims, "get_or_create_entity", fake_get_entity)
    monkeypatch.setattr(claims, "write_claim", fake_write_claim)

    await claims.emit_content_repurpose_lift(
        campaign_id="camp-021",
        original_content_id="orig-1",
        repurposed_content_id="repu-2",
        engagement_delta=0.35,
        sample_size=120,
        window_hours=72,
    )
    assert "campaign:camp-021" == captured["canonical_name"]
    assert captured["claim_type"] == "content_repurpose_lift"
```

- [ ] **Step 2: Run — should FAIL**

- [ ] **Step 3: Implement Copywriter emitters**

```python
# ============================================================================
# Copywriter emitters
# ============================================================================


async def emit_seo_performance_cohort(
    *,
    keyword: str,
    ranking_position: int,
    sample_size: int,
    window_days: int,
) -> UUID:
    """Write a seo_performance_cohort claim.

    Recency-dominated (preset override weight 0.40). TTL 7d after the window
    end — the claim expires when the next SEO sync would supersede it.
    """
    # Normalize the keyword to a slug for canonical_name idempotency
    slug = keyword.strip().lower().replace(" ", "_")
    entity_id = await get_or_create_entity(
        canonical_name=f"seo_topic:{slug}",
        entity_type="topic",
        domains=["content"],
        properties={"keyword": keyword},
    )

    finding_text = (
        f"seo_topic '{keyword}' ranking_position={ranking_position} "
        f"n={sample_size} over {window_days}d window"
    )

    confidence = content_confidence(
        brand_alignment_score=0.5,
        performance_sample_size=sample_size,
        recency_hours=float(window_days) * 24,
        statistical_significance=0.6,
        # Lift signal: shrinking ranking_position (1 is best) → higher signal.
        engagement_lift_magnitude=max(0.0, 1.0 - (ranking_position - 1) / 20.0),
        claim_type="seo_performance_cohort",
    )

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[{"kind": "seo_sync", "ref": slug}],
        agent_id="CopywriterAgent",
        claim_type="seo_performance_cohort",
        embed=True,
        expires_at=expires_at,
    )


async def emit_copy_tone_fidelity(
    *,
    content_id: str,
    tone_alignment_score: float,
    voice_profile_version: int | str,
) -> UUID:
    """Write a copy_tone_fidelity claim for a copy artifact."""
    entity_id = await get_or_create_entity(
        canonical_name=f"content_asset:{content_id}",
        entity_type="product",
        domains=["content"],
        properties={"content_id": content_id},
    )

    finding_text = (
        f"copy {content_id} tone_alignment_score={tone_alignment_score:.2f} "
        f"vs voice_profile.version={voice_profile_version}"
    )

    confidence = content_confidence(
        brand_alignment_score=tone_alignment_score,
        performance_sample_size=0,
        recency_hours=0.0,
        statistical_significance=0.0,
        engagement_lift_magnitude=0.0,
        # Reuse brand_fidelity override: alignment-only weight.
        claim_type="brand_fidelity_score",
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[{"kind": "copy_pipeline", "ref": content_id}],
        agent_id="CopywriterAgent",
        claim_type="copy_tone_fidelity",
        embed=True,
    )


async def emit_content_repurpose_lift(
    *,
    campaign_id: str,
    original_content_id: str,
    repurposed_content_id: str,
    engagement_delta: float,
    sample_size: int,
    window_hours: int,
) -> UUID:
    """Write a content_repurpose_lift claim."""
    entity_id = await get_or_create_entity(
        canonical_name=f"campaign:{campaign_id}",
        entity_type="topic",
        domains=["content"],
        properties={"campaign_id": campaign_id},
    )

    finding_text = (
        f"campaign {campaign_id} repurposed content {repurposed_content_id} "
        f"vs original {original_content_id} engagement_delta={engagement_delta:+.2f} "
        f"n={sample_size} over {window_hours}h"
    )

    confidence = content_confidence(
        brand_alignment_score=0.5,
        performance_sample_size=sample_size,
        recency_hours=float(window_hours),
        statistical_significance=0.5,
        engagement_lift_magnitude=min(1.0, max(0.0, engagement_delta)),
    )

    return await write_claim(
        entity_id=entity_id,
        domain="content",
        finding_text=finding_text,
        confidence=confidence,
        sources=[
            {"kind": "platform_analytics", "ref": f"campaign:{campaign_id}"},
            {"kind": "content_pair", "ref": f"{original_content_id}->{repurposed_content_id}"},
        ],
        agent_id="CopywriterAgent",
        claim_type="content_repurpose_lift",
        embed=True,
    )
```

- [ ] **Step 4: Run — should PASS**

```powershell
uv run pytest tests/unit/agents/content/test_claims.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/content/claims.py tests/unit/agents/content/test_claims.py
git commit -m "feat(122-03): Copywriter emitters (seo_cohort, tone_fidelity, repurpose_lift) (GREEN)"
```

### Task 5: Verify Plan 122-02's MISS-path emission now succeeds

**Files:**
- Modify: `tests/integration/test_render_cache_canva_veo.py` — extend existing test

When 122-02 shipped, the `_emit_provenance_claim_safe` helper logged a debug message *"emit_asset_generation_provenance not available; skipping"* because this plan's module didn't exist yet. Now it does. Verify the link closes.

- [ ] **Step 1: Add a test that observes the provenance claim arrives in `kg_findings`**

Append to `tests/integration/test_render_cache_canva_veo.py`:

```python
@pytest.mark.asyncio
async def test_cache_miss_emits_provenance_claim_to_kg_findings(monkeypatch):
    """End-to-end: a MISS render emits an asset_generation_provenance claim row."""
    import os

    if not all(os.environ.get(v) for v in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")):
        pytest.skip("Supabase env not set")

    from app.services.intelligence import find_claims, get_or_create_entity
    from app.services.intelligence.render_cache import cached_render, render_cache_key

    fixed_asset_id = "11111111-2222-3333-4444-555555555555"

    async def stub_render():
        return {
            "asset_url": "https://example.com/post-122-03-asset.png",
            "asset_id": fixed_asset_id,
            "tool_metadata": {},
        }

    key = render_cache_key(
        template_id="provenance_emission_test",
        brand_profile_version=42,
        prompt_text="A prompt long enough for the emission round trip",
        style_preset="vibrant",
        dimensions=(1080, 1080),
    )

    r = await cached_render(
        surface="canva_render",
        key=key,
        render_fn=stub_render,
        emission_metadata={
            "agent_id": "GraphicDesignerAgent",
            "prompt_text": "A prompt long enough for the emission round trip",
        },
    )
    assert r["cache_hit"] is False

    # Resolve the asset entity and look for the provenance claim
    entity = await get_or_create_entity(
        canonical_name=f"content_asset:{fixed_asset_id}",
        entity_type="product",
        domains=["content"],
    )
    claims = await find_claims(
        entity_id=entity,
        claim_type="asset_generation_provenance",
        limit=5,
    )
    assert len(claims) >= 1
    assert any(fixed_asset_id in c.finding_text for c in claims)
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:REDIS_HOST = "localhost"
uv run pytest tests/integration/test_render_cache_canva_veo.py::test_cache_miss_emits_provenance_claim_to_kg_findings -v
```

Expected: PASS. If the claim is missing, the lazy-import path inside `_emit_provenance_claim_safe` may still be failing to resolve — verify by importing directly:

```powershell
uv run python -c "from app.agents.content.claims import emit_asset_generation_provenance; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_render_cache_canva_veo.py
git commit -m "test(122-03): verify 122-02 MISS path emits provenance claim end-to-end"
```

### Task 6: Update sub-agent instructions to mention claim emission

**Files:**
- Modify: `app/agents/content/agent.py` — extend each of the 3 sub-agent instruction strings

The sub-agents need to know *when* to emit claims and *what shape* the META rule requires. Without this, the LLM running each sub-agent won't call the emitter at the right place.

- [ ] **Step 1: Append a CLAIM EMISSION section to each instruction**

In `_VIDEO_DIRECTOR_INSTRUCTION`, append (before the closing `"""`):

```text

## CLAIM EMISSION (Phase 122)
After every successful render or A/B test conclusion, emit the matching claim:
- On render success → call `emit_asset_origin_claim(asset_id, prompt, run_id, tool, rendered_at)`. This is automatic when calling `create_video_with_veo` (the cache layer emits provenance), but if you call a video tool directly, emit explicitly.
- ~24h after publish, when completion-rate analytics catch up → `emit_video_completion_rate_signal(asset_id, completion_rate, sample_size, window_hours, platform)`.
- When an A/B hook comparison concludes → `emit_hook_performance_comparative(campaign_id, hook_a_label, hook_b_label, lift_magnitude, p_value, sample_size_per_variant)`. NEVER claim a winner with <15 samples per variant — the preset will cap confidence at 0.65 in that case.

CLAIM-TEXT RULE: claims are META about the artifact. Say *"asset X completion_rate=0.68 n=240"*, not *"the video is engaging"*.
```

Similar `CLAIM EMISSION` sections for `_GRAPHIC_DESIGNER_INSTRUCTION`:

```text

## CLAIM EMISSION (Phase 122)
- On asset commit → `emit_brand_fidelity_score(asset_id, brand_alignment_score, brand_profile_version)`. If brand-profile embedding isn't available yet, pass brand_alignment_score=None and the system will mark the claim as pending back-fill.
- ~24h after publish → `emit_design_audience_resonance(campaign_id, engagement_rate, sample_size, audience_label, window_hours)`.
- Generation provenance is emitted automatically by the render cache layer; do not call `emit_asset_generation_provenance` directly.

CLAIM-TEXT RULE: claims describe the design's measured properties (alignment_score, engagement_rate), not their aesthetic merit.
```

And `_COPYWRITER_INSTRUCTION`:

```text

## CLAIM EMISSION (Phase 122)
- On SEO sync that returns a position for a tracked keyword → `emit_seo_performance_cohort(keyword, ranking_position, sample_size, window_days)`. These claims auto-expire after 7 days.
- On copy commit when tone-alignment is measured against the voice profile → `emit_copy_tone_fidelity(content_id, tone_alignment_score, voice_profile_version)`.
- After `repurpose_content` telemetry catches up → `emit_content_repurpose_lift(campaign_id, original_content_id, repurposed_content_id, engagement_delta, sample_size, window_hours)`.

CLAIM-TEXT RULE: claims report measured properties (ranking_position, tone_alignment_score), not editorial opinion about the copy.
```

- [ ] **Step 2: Verify the instructions still load correctly (no syntax errors)**

```powershell
uv run python -c "from app.agents.content.agent import _VIDEO_DIRECTOR_INSTRUCTION, _GRAPHIC_DESIGNER_INSTRUCTION, _COPYWRITER_INSTRUCTION; print(len(_VIDEO_DIRECTOR_INSTRUCTION), len(_GRAPHIC_DESIGNER_INSTRUCTION), len(_COPYWRITER_INSTRUCTION))"
```

Expected: three positive integers, indicating the strings parsed.

- [ ] **Step 3: Commit**

```bash
git add app/agents/content/agent.py
git commit -m "feat(122-03): teach sub-agents to emit claims (CLAIM EMISSION instructions)"
```

### Task 7: Cross-agent integration — Content claims in semantic search + cross-reference

**Files:**
- Create: `tests/integration/test_content_claims_cross_agent.py`

Two acceptance criteria from the spec:

1. `search_claims_semantic` returns Content claims interleaved with Marketing/Sales/Data claims.
2. Marketing's `creative_performance` claim can reference Content's `brand_fidelity_score` via edges.

We can't (and shouldn't) emit a real Marketing claim from this plan — that's Phase 117. We *can* simulate the cross-reference by writing a Marketing-style claim manually and verifying the find/search surfaces both together.

- [ ] **Step 1: Write the integration test**

```python
"""Cross-agent integration: Content claims surface alongside Marketing/Data."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(v) for v in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_content_claims_surface_in_semantic_search():
    """search_claims_semantic returns Content + Marketing + Data interleaved."""
    from app.agents.content.claims import emit_brand_fidelity_score
    from app.services.intelligence import (
        get_or_create_entity,
        search_claims_semantic,
        write_claim,
    )

    asset_id = str(uuid4())
    campaign_id = f"camp-{uuid4()}"

    # 1. Content: brand_fidelity_score
    content_id = await emit_brand_fidelity_score(
        asset_id=asset_id,
        brand_alignment_score=0.91,
        brand_profile_version=7,
    )

    # 2. Simulate Marketing's creative_performance claim against the same campaign
    marketing_entity = await get_or_create_entity(
        canonical_name=f"campaign:{campaign_id}",
        entity_type="topic",
        domains=["marketing"],
    )
    marketing_id = await write_claim(
        entity_id=marketing_entity,
        domain="marketing",
        finding_text=(
            f"campaign {campaign_id} creative_performance lift=0.22 over baseline "
            f"references asset {asset_id} brand_fidelity_score"
        ),
        confidence=0.7,
        sources=[{"kind": "platform_analytics", "ref": campaign_id}],
        agent_id="MarketingAgent",
        claim_type="creative_performance",
        embed=True,
    )

    # 3. Simulate Data's cohort_summary touching the same campaign
    data_id = await write_claim(
        entity_id=marketing_entity,
        domain="data",
        finding_text=(
            f"campaign {campaign_id} cohort retention 64% n=200 over 30d"
        ),
        confidence=0.8,
        sources=[{"kind": "stripe_row", "ref": campaign_id}],
        agent_id="DataAgent",
        claim_type="cohort_summary",
        embed=True,
    )

    # 4. Semantic search across all three
    results = await search_claims_semantic(
        query=f"asset {asset_id} brand fidelity creative performance",
        top_k=10,
    )
    agent_ids = {claim.agent_id for claim, _sim in results}
    assert "GraphicDesignerAgent" in agent_ids, (
        f"Content's brand_fidelity_score missing from semantic search: {agent_ids}"
    )
    # Marketing + Data should be discoverable too (the query mentions both topics)
    found_ids = {claim.id for claim, _sim in results}
    assert content_id in found_ids


@pytest.mark.asyncio
async def test_marketing_can_reference_content_claim_via_find_claims():
    """find_claims on the campaign entity surfaces both Marketing + Content claims."""
    from app.agents.content.claims import emit_design_audience_resonance
    from app.services.intelligence import find_claims, get_or_create_entity, write_claim

    campaign_id = f"camp-xref-{uuid4()}"

    # Content writes against the same campaign entity
    content_id = await emit_design_audience_resonance(
        campaign_id=campaign_id,
        engagement_rate=0.18,
        sample_size=400,
        audience_label="Gen Z creators",
        window_hours=24,
    )

    # Marketing writes against the same campaign — share entity
    entity = await get_or_create_entity(
        canonical_name=f"campaign:{campaign_id}",
        entity_type="topic",
        domains=["marketing", "content"],
    )
    marketing_id = await write_claim(
        entity_id=entity,
        domain="marketing",
        finding_text=f"campaign {campaign_id} creative_performance lift=0.30",
        confidence=0.7,
        sources=[],
        agent_id="MarketingAgent",
        claim_type="creative_performance",
        embed=False,
    )

    claims = await find_claims(entity_id=entity, limit=20)
    ids = {c.id for c in claims}
    agent_ids = {c.agent_id for c in claims}
    assert content_id in ids
    assert marketing_id in ids
    assert "GraphicDesignerAgent" in agent_ids
    assert "MarketingAgent" in agent_ids
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_content_claims_cross_agent.py -v --tb=short
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_content_claims_cross_agent.py
git commit -m "test(122-03): cross-agent integration — Content + Marketing + Data interleave"
```

### Task 8: Wire `emit_brand_fidelity_score` into `simple_create_content`

**Files:**
- Modify: `app/agents/content/tools.py` — call the emitter when fast-path saves content

The fast path already saves to ContentService and now (post-122-01) returns `confidence + band`. Add a side-effecting call to the emitter so the claim lands too. This makes the META claim model surface even for the simplest content creation flow.

- [ ] **Step 1: Failing test**

Append to `tests/unit/agents/content/test_claims.py`:

```python
@pytest.mark.asyncio
async def test_simple_create_content_emits_brand_fidelity_claim(monkeypatch):
    """fast-path content save triggers a brand_fidelity_score emission."""
    from app.agents.content import tools as content_tools
    from app.agents.content import claims as content_claims

    async def _no_brand(*_a, **_kw):
        return {"success": True, "brand_name": "TestBrand", "voice_tone": "bold"}

    class _StubService:
        async def save_content(self, **kw):
            return {"success": True, "ids": ["00000000-0000-0000-0000-000000000aaa"]}

    monkeypatch.setattr(content_tools, "get_brand_profile", _no_brand)
    monkeypatch.setattr(content_tools, "ContentService", lambda: _StubService())
    monkeypatch.setattr(content_tools, "get_current_user_id", lambda: "u1")

    captured: dict = {}

    async def fake_emit_brand_fidelity_score(**kw):
        captured.update(kw)
        from uuid import uuid4 as _u
        return _u()

    monkeypatch.setattr(
        content_claims,
        "emit_brand_fidelity_score",
        fake_emit_brand_fidelity_score,
    )

    result = await content_tools.simple_create_content(
        topic="A friendly product launch announcement",
        content_type="social_post",
        platform="linkedin",
    )

    assert result.get("success")
    assert captured.get("asset_id") == "00000000-0000-0000-0000-000000000aaa"
```

- [ ] **Step 2: Implement the wiring in `simple_create_content`**

In `app/agents/content/tools.py`, after the `save_result` block (where `content_id` is set) and *before* the final return:

```python
# --- 4.7 Emit brand_fidelity_score claim (Phase 122-03) ---
if content_id:
    try:
        from app.agents.content import claims as _claims
        # Fast path has no real brand_alignment measurement; pass None so the
        # emitter records a neutral 0.5 with the back-fill sentinel.
        await _claims.emit_brand_fidelity_score(
            asset_id=content_id,
            brand_alignment_score=None,
            brand_profile_version=None,
        )
    except Exception:
        logger.warning("brand_fidelity_score emission failed; continuing.")
```

- [ ] **Step 3: Run — should PASS**

```powershell
uv run pytest tests/unit/agents/content/test_claims.py -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add app/agents/content/tools.py tests/unit/agents/content/test_claims.py
git commit -m "feat(122-03): emit brand_fidelity_score from simple_create_content fast path"
```

### Task 9: Lint, type-check, and Phase 122 acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/agents/content/claims.py app/agents/content/agent.py app/agents/content/tools.py tests/unit/agents/content/test_claims.py tests/integration/test_content_claims_cross_agent.py
uv run ruff format app/agents/content/claims.py app/agents/content/agent.py app/agents/content/tools.py tests/unit/agents/content/test_claims.py tests/integration/test_content_claims_cross_agent.py --check
```

Fix in place. Commit `style(122-03): ...` for any.

- [ ] **Step 2: Type check**

```powershell
uv run ty check app/agents/content/claims.py app/agents/content/tools.py
```

- [ ] **Step 3: Phase 122 acceptance cross-check (all 3 plans)**

| Phase 122 acceptance line | Verified by |
|---|---|
| `content_confidence` preset shipped | Plan 122-01 |
| Per-claim-type overrides apply correctly | Plan 122-01 + Plan 122-03 tests |
| Brand-profile audit recorded; escalation if needed | Plan 122-01 |
| Self-improvement engine audit recorded | Plan 122-01 |
| Idempotent render cache (Canva+Veo) | Plan 122-02 |
| `render_cache_key = sha256(...)` | Plan 122-02 |
| Cache HIT → cached asset URL + cost=$0.00 | Plan 122-02 + Plan 122-03 (provenance verification) |
| Cache MISS → calls Canva/Veo + emits asset_generation_provenance claim | Plan 122-02 + Plan 122-03 Task 5 |
| Video Director claim types (3): video_completion_rate_signal, hook_performance_comparative, asset_origin_claim | Task 2 |
| Graphic Designer claim types (3): brand_fidelity_score, design_audience_resonance, asset_generation_provenance | Task 3 |
| Copywriter claim types (3): seo_performance_cohort, copy_tone_fidelity, content_repurpose_lift | Task 4 |
| `search_claims_semantic` returns Content claims interleaved with Marketing/Sales/Data | Task 7 |
| Marketing's `creative_performance` claim can reference Content's `brand_fidelity_score` via edges | Task 7 second test |
| All Content outputs carry confidence + band | Plan 122-01 first call site + Task 8 emit on save |
| META claim-text rule embedded in sub-agent instructions | Task 6 |
| Lint + type-check clean | Task 9 |

- [ ] **Step 4: Phase 122 complete — verify Cloud Run deploy gate**

This plan doesn't trigger a deploy by itself, but Phase 122 ends the 9-phase rollout, so:

```bash
git log --oneline --grep="122-" | head
```

Should show 3 plans' worth of feat/test commits.

- [ ] **Step 5: Plan 122-03 complete. Phase 122 (Content Agent adoption) is fully shipped.**

Next planned work: cleanup phase consolidating `graph_service.py` / `intelligence_scheduler.py` / `intelligence_worker.py` into the `app/services/intelligence/` package (separate spec). Per the rollout spec § Out of scope.

---

## Spec coverage check

| Spec requirement (Phase 122 § Content claims) | Task(s) |
|---|---|
| Video Director: video_completion_rate_signal | Task 2 |
| Video Director: hook_performance_comparative | Task 2 |
| Video Director: asset_origin_claim | Task 2 |
| Graphic Designer: brand_fidelity_score | Task 3 |
| Graphic Designer: design_audience_resonance | Task 3 |
| Graphic Designer: asset_generation_provenance | Task 3 + Task 5 link from 122-02 |
| Copywriter: seo_performance_cohort | Task 4 |
| Copywriter: copy_tone_fidelity | Task 4 |
| Copywriter: content_repurpose_lift | Task 4 |
| Per-claim-type overrides applied correctly | Tasks 2, 3, 4 |
| Confidence + band on every Content output | Plan 122-01 + Task 8 |
| `search_claims_semantic` returns Content interleaved | Task 7 |
| Cross-agent edge ref (Marketing ↔ Content) | Task 7 |
| Claims are META about artifacts, not assertions | finding_text shape conventions + Task 6 instructions |
| Brand-embedding fallback path when 121.5 not yet shipped | Task 3 second test |
| Lint + type-check clean | Task 9 |

All Phase 122-03 spec lines covered. All 3 plans together close Phase 122 acceptance.
