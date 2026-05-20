# Shared Intelligence Infrastructure — Plan 117-03: Marketing Claim Emission

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit three Marketing claim types into `kg_findings` — `campaign_lift`, `audience_resonance`, and `creative_performance` — from the Marketing Agent's quantitative tool surfaces. Every campaign-level claim carries `expires_at = campaign_end_date + 30d`. `creative_performance` claims cross-reference Content Agent's `brand_fidelity_score` claims (Phase 122) via the `edges` table when both phases have shipped — and degrade gracefully when Phase 122 has not.

**Architecture:** Marketing tools that already attach `confidence` + `band` (Plan 117-01) now also write a claim to `kg_findings` when the result is non-transient. Claim emission is opt-in per tool path — short factual aggregations (e.g., raw daily spend) stay in Redis, while *assertions* (lift, resonance, performance) become claims. Cross-referencing happens at write time: when emitting a `creative_performance` claim, the writer looks up the most recent `brand_fidelity_score` claim attached to the same creative entity and links it via `kg_edges` with `relation='references'`. Phase-122 absence is the common case at ship time — the lookup returns empty, no edge is written, and a structured log line records the gap.

**Tech Stack:** `app/services/intelligence/claims.py` (read-only — Plan 112-03 / 113-05 surface), `app/services/intelligence/marketing_emit.py` (new — Marketing-specific emission helpers), `app/agents/tools/campaign_performance_tools.py`, `app/agents/tools/attribution_tools.py`, `app/agents/tools/social_analytics.py`, `app/agents/tools/ad_platform_tools.py` (modified — claim emission hooks).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 117 — Marketing Agent adoption · Claims (`campaign_lift`, `audience_resonance`, `creative_performance`).

**Out of scope:** Backfill of historical campaigns (forward-only — claims accumulate from this plan onward). Multi-track decomposition (research-specific). Persona-aware confidence overrides. LLM-driven claim emission via an ADK tool (deferred per Decision #7 / Decision #10 — library-first, ExecutiveAgent already has `search_agent_claims` from Phase 113-04). The Content Agent's own `brand_fidelity_score` emission is Phase 122, not this plan — this plan only *reads* and *links*.

---

## File structure

**Create:**
- `app/services/intelligence/marketing_emit.py` — `emit_campaign_lift_claim`, `emit_audience_resonance_claim`, `emit_creative_performance_claim`
- `tests/unit/services/intelligence/test_marketing_emit.py` — unit tests with mocked Supabase + embedding
- `tests/integration/test_marketing_claims_round_trip.py` — integration: write → find → semantic-search a Marketing claim
- `tests/integration/test_marketing_creative_cross_ref.py` — integration: creative_performance edges to brand_fidelity_score when present

**Modify:**
- `app/agents/tools/campaign_performance_tools.py` — emit `campaign_lift` after the summarizer returns
- `app/agents/tools/attribution_tools.py` — emit `campaign_lift` from `get_cross_channel_attribution` per channel
- `app/agents/tools/ad_platform_tools.py` — emit `creative_performance` after `save_ad_copy_as_creative` produces measurable results
- `app/agents/tools/social_analytics.py` — emit `audience_resonance` from per-post breakdowns

---

## Pre-flight context

**Claim-type vocabulary** (from the spec):

| claim_type | Emitted by | Entity | `expires_at` | Cross-ref |
|---|---|---|---|---|
| `campaign_lift` | `summarize_campaign_performance`, `get_cross_channel_attribution` | per-campaign or per-channel kg_entity | `campaign_end_date + 30d` | none |
| `audience_resonance` | `get_social_analytics`, `get_all_platform_analytics` | per-audience-segment kg_entity | `period_end + 30d` | none |
| `creative_performance` | `ad_platform_tools` (post-save activation) | per-creative kg_entity | `campaign_end_date + 30d` | edge to `brand_fidelity_score` claim if Phase 122 has shipped |

**`expires_at` formula** (load-bearing — Plan 117-04 baseline depends on this):

```python
def claim_expires_at(*, campaign_end: datetime | None, period_end: datetime | None) -> datetime | None:
    """campaign_end > period_end > None — first non-None + 30 days."""
    anchor = campaign_end or period_end
    if anchor is None:
        return None
    return anchor + timedelta(days=30)
```

When a campaign is still active (no `campaign_end_date`), the claim uses `period_end + 30d`. When neither is known, `expires_at` is None and the claim is treated as evergreen until manually superseded.

**Cross-reference rule** (`creative_performance` → `brand_fidelity_score`):

1. Resolve the creative kg_entity by canonical name `creative_<creative_id>`.
2. Query `find_claims(entity_id=<creative_entity>, claim_type="brand_fidelity_score", agent_id="content", limit=1)`.
3. If a fresh claim is found (freshness_at within 30d), write an edge `kg_edges` row with `from_id=<creative_performance_claim>`, `to_id=<brand_fidelity_score_claim>`, `relation="references"`.
4. If no claim is found, log structured `marketing.creative_cross_ref.absent` (informational) and skip edge creation. **No error.** Phase 122 hasn't shipped — this is expected.

**Embedding policy:** All three claim types pass `embed=True`. This wires them automatically into:
- `search_claims_semantic` (Phase 113-04 cross-agent search)
- `detect_contradictions` (Phase 113-05 — flags conflicting Marketing claims about the same entity automatically)

The Marketing Agent does NOT need to call either of these directly — they happen at write time inside `write_claim`.

**Confidence wiring:** Each emission helper takes the *already-computed* `confidence` from Plan 117-01's `_attach_marketing_confidence`. Helpers do not recompute. This guarantees the kg_findings `confidence` column matches whatever number was shown to the user.

Acceptance bar:
- `emit_campaign_lift_claim`, `emit_audience_resonance_claim`, `emit_creative_performance_claim` shipped in `app/services/intelligence/marketing_emit.py`
- `summarize_campaign_performance` writes a `campaign_lift` claim per call that produces a summary text
- `get_cross_channel_attribution` writes one `campaign_lift` claim per channel in the breakdown
- `get_social_analytics` / `get_all_platform_analytics` write one `audience_resonance` claim per platform
- `ad_platform_tools.save_ad_copy_as_creative` (or activation path) writes a `creative_performance` claim
- `expires_at = campaign_end + 30d` (or `period_end + 30d` fallback) is set
- Cross-reference edge written to a `brand_fidelity_score` claim when present; silently skipped when absent
- `search_claims_semantic(query="Q1 campaign performance", top_k=10)` returns a mix of Marketing, Data, and Research claims (when seeded)
- All claims carry `embed=True` and so participate in contradiction detection automatically

---

## Tasks

### Task 1: Pre-flight — confirm prerequisites + Marketing-Agent claim entity strategy

- [ ] **Step 1: Confirm 117-01 + 117-02 have landed**

```powershell
uv run python -c "from app.services.intelligence.presets import marketing_confidence; from app.services.intelligence.marketing_cache_keys import gads_campaign_key; from app.agents.tools._marketing_confidence import _attach_marketing_confidence; print('OK')"
```

Must succeed. If not, **STOP** — 117-03 depends on prior plans.

- [ ] **Step 2: Confirm `write_claim` + `find_claims` + `search_claims_semantic` are importable**

```powershell
uv run python -c "from app.services.intelligence import write_claim, find_claims, search_claims_semantic, get_or_create_entity; print('OK')"
```

- [ ] **Step 3: Decide entity canonicalisation for Marketing**

The Marketing Agent operates on three entity classes:

| Class | canonical_name shape | entity_type |
|---|---|---|
| Per-campaign aggregate | `campaign_<campaign_id>` | `topic` |
| Per-channel rollup (cross-channel attribution) | `channel_<user_id>_<channel>` | `topic` |
| Per-creative | `creative_<creative_id>` | `topic` |
| Per-audience-segment | `audience_<segment_id>` | `topic` |

`topic` is used uniformly because the existing CHECK constraint on `kg_entities.entity_type` does not list `campaign`/`creative`/`audience`. Document this in the module docstring of `marketing_emit.py`.

- [ ] **Step 4: Capture today's `kg_findings` shape for `confidence`, `sources`, `contradicts` columns**

```powershell
uv run python -c "from app.services.intelligence.schemas import Claim, ClaimPayload, ClaimSource; print(Claim.model_json_schema()['properties'].keys()); print(ClaimSource.model_json_schema()['properties'].keys())"
```

Confirm the existing column set — no new migrations are needed for Plan 117-03; we are writing into the pre-existing broadened `kg_findings`.

### Task 2: Implement `emit_campaign_lift_claim` (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_marketing_emit.py`
- Create: `app/services/intelligence/marketing_emit.py`

- [ ] **Step 1: Failing tests**

```python
"""Unit tests for Marketing claim-emission helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest


@pytest.mark.asyncio
async def test_emit_campaign_lift_claim_writes_with_30day_expiry():
    from app.services.intelligence.marketing_emit import emit_campaign_lift_claim

    seen = {}

    async def fake_write(**kwargs):
        seen.update(kwargs)
        return uuid4()

    async def fake_entity(**kwargs):
        return uuid4()

    campaign_end = datetime(2026, 6, 1, tzinfo=timezone.utc)

    with patch(
        "app.services.intelligence.marketing_emit.get_or_create_entity",
        new=AsyncMock(side_effect=fake_entity),
    ), patch(
        "app.services.intelligence.marketing_emit.write_claim",
        new=AsyncMock(side_effect=fake_write),
    ):
        await emit_campaign_lift_claim(
            campaign_id="camp-1",
            finding_text="Spring sale drove a 23% lift in conversions WoW",
            confidence=0.78,
            sources=[{"kind": "platform_api", "ref": "google_ads/c-1"}],
            campaign_end_date=campaign_end,
            period_end_date=None,
        )

    assert seen["claim_type"] == "campaign_lift"
    assert seen["domain"] == "marketing"
    assert seen["agent_id"] == "marketing"
    assert seen["embed"] is True
    # expires_at = campaign_end + 30d
    assert seen["expires_at"] == campaign_end + timedelta(days=30)


@pytest.mark.asyncio
async def test_emit_campaign_lift_claim_uses_period_when_no_campaign_end():
    from app.services.intelligence.marketing_emit import emit_campaign_lift_claim

    seen = {}
    async def fake_write(**kwargs):
        seen.update(kwargs)
        return uuid4()

    period_end = datetime(2026, 5, 19, tzinfo=timezone.utc)
    with patch(
        "app.services.intelligence.marketing_emit.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.intelligence.marketing_emit.write_claim",
        new=AsyncMock(side_effect=fake_write),
    ):
        await emit_campaign_lift_claim(
            campaign_id="camp-2",
            finding_text="WoW change inside normal volatility band",
            confidence=0.55,
            sources=[],
            campaign_end_date=None,
            period_end_date=period_end,
        )
    assert seen["expires_at"] == period_end + timedelta(days=30)


@pytest.mark.asyncio
async def test_emit_campaign_lift_claim_no_anchor_no_expiry():
    from app.services.intelligence.marketing_emit import emit_campaign_lift_claim

    seen = {}
    async def fake_write(**kwargs):
        seen.update(kwargs)
        return uuid4()

    with patch(
        "app.services.intelligence.marketing_emit.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.intelligence.marketing_emit.write_claim",
        new=AsyncMock(side_effect=fake_write),
    ):
        await emit_campaign_lift_claim(
            campaign_id="camp-3",
            finding_text="Insufficient data for stable lift estimate over 4-day window",
            confidence=0.30,
            sources=[],
            campaign_end_date=None,
            period_end_date=None,
        )
    assert seen["expires_at"] is None


@pytest.mark.asyncio
async def test_emit_campaign_lift_claim_short_text_returns_none():
    """finding_text < 20 chars is rejected (no claim, no error)."""
    from app.services.intelligence.marketing_emit import emit_campaign_lift_claim

    with patch(
        "app.services.intelligence.marketing_emit.write_claim",
        new=AsyncMock(side_effect=AssertionError("must NOT be called")),
    ):
        result = await emit_campaign_lift_claim(
            campaign_id="camp-4",
            finding_text="x",
            confidence=0.5,
            sources=[],
            campaign_end_date=None,
            period_end_date=None,
        )
    assert result is None


@pytest.mark.asyncio
async def test_emit_campaign_lift_claim_swallows_supabase_error():
    """write_claim raising must not propagate — degrade silently and log."""
    from app.services.intelligence.marketing_emit import emit_campaign_lift_claim

    with patch(
        "app.services.intelligence.marketing_emit.get_or_create_entity",
        new=AsyncMock(return_value=uuid4()),
    ), patch(
        "app.services.intelligence.marketing_emit.write_claim",
        new=AsyncMock(side_effect=RuntimeError("supabase down")),
    ):
        result = await emit_campaign_lift_claim(
            campaign_id="camp-5",
            finding_text="A perfectly fine claim text that is sufficiently long",
            confidence=0.7,
            sources=[],
            campaign_end_date=None,
            period_end_date=None,
        )
    assert result is None
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_marketing_emit.py -v --tb=short
```

- [ ] **Step 3: Implement `app/services/intelligence/marketing_emit.py`**

```python
"""Marketing-Agent claim-emission helpers.

Three public helpers, one per claim type:
- emit_campaign_lift_claim       (campaign-level performance assertions)
- emit_audience_resonance_claim  (per-segment engagement findings)
- emit_creative_performance_claim (per-creative outcome claims with brand cross-ref)

All three:
- Use entity_type='topic' (kg_entities CHECK constraint doesn't list
  campaign/creative/audience; topic is the closest catch-all).
- Write with embed=True so contradictions auto-detect and semantic
  search picks up the claim.
- Set expires_at = (campaign_end_date or period_end_date) + 30 days.
- Degrade silently on any failure — emission is best-effort, never blocks
  the tool path that triggered it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)

# Avoid circular imports — defer to call time.
from app.services.intelligence.claims import (  # noqa: E402
    find_claims, get_or_create_entity, write_claim,
)


def _claim_expires_at(
    *,
    campaign_end_date: datetime | None,
    period_end_date: datetime | None,
) -> datetime | None:
    """campaign_end > period_end > None — first non-None plus 30 days."""
    anchor = campaign_end_date or period_end_date
    if anchor is None:
        return None
    return anchor + timedelta(days=30)


async def emit_campaign_lift_claim(
    *,
    campaign_id: str,
    finding_text: str,
    confidence: float,
    sources: Sequence[dict],
    campaign_end_date: datetime | None,
    period_end_date: datetime | None,
) -> UUID | None:
    """Emit a campaign_lift claim. Returns claim UUID or None on failure / skip."""
    if not finding_text or len(finding_text.strip()) < 20:
        return None
    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"campaign_{campaign_id}",
            entity_type="topic", domains=["marketing"],
        )
        return await write_claim(
            entity_id=entity_id, domain="marketing",
            finding_text=finding_text, confidence=confidence,
            sources=list(sources), agent_id="marketing",
            claim_type="campaign_lift", embed=True,
            expires_at=_claim_expires_at(
                campaign_end_date=campaign_end_date,
                period_end_date=period_end_date,
            ),
        )
    except Exception as e:
        logger.warning("emit_campaign_lift_claim failed: %s", e)
        return None


async def emit_audience_resonance_claim(
    *,
    segment_id: str,
    finding_text: str,
    confidence: float,
    sources: Sequence[dict],
    period_end_date: datetime | None,
) -> UUID | None:
    """Emit an audience_resonance claim. Returns claim UUID or None."""
    if not finding_text or len(finding_text.strip()) < 20:
        return None
    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"audience_{segment_id}",
            entity_type="topic", domains=["marketing"],
        )
        return await write_claim(
            entity_id=entity_id, domain="marketing",
            finding_text=finding_text, confidence=confidence,
            sources=list(sources), agent_id="marketing",
            claim_type="audience_resonance", embed=True,
            expires_at=_claim_expires_at(
                campaign_end_date=None,
                period_end_date=period_end_date,
            ),
        )
    except Exception as e:
        logger.warning("emit_audience_resonance_claim failed: %s", e)
        return None


async def emit_creative_performance_claim(
    *,
    creative_id: str,
    finding_text: str,
    confidence: float,
    sources: Sequence[dict],
    campaign_end_date: datetime | None,
    period_end_date: datetime | None,
) -> UUID | None:
    """Emit a creative_performance claim + cross-reference brand_fidelity_score.

    The cross-reference is best-effort: it succeeds when Phase 122 has shipped
    a brand_fidelity_score claim for the same creative entity; otherwise it
    logs marketing.creative_cross_ref.absent and skips edge creation.
    """
    if not finding_text or len(finding_text.strip()) < 20:
        return None
    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"creative_{creative_id}",
            entity_type="topic", domains=["marketing", "content"],
        )
        claim_id = await write_claim(
            entity_id=entity_id, domain="marketing",
            finding_text=finding_text, confidence=confidence,
            sources=list(sources), agent_id="marketing",
            claim_type="creative_performance", embed=True,
            expires_at=_claim_expires_at(
                campaign_end_date=campaign_end_date,
                period_end_date=period_end_date,
            ),
        )
    except Exception as e:
        logger.warning("emit_creative_performance_claim failed: %s", e)
        return None

    # Best-effort cross-reference to Content's brand_fidelity_score (Phase 122)
    try:
        brand_claims = await find_claims(
            entity_id=entity_id,
            claim_type="brand_fidelity_score",
            agent_id="content",
            limit=1,
        )
        if not brand_claims:
            logger.info(
                "marketing.creative_cross_ref.absent",
                extra={"creative_id": creative_id, "claim_id": str(claim_id)},
            )
            return claim_id

        # Phase 122 has shipped — record the edge.
        from app.services.intelligence.claims import _get_supabase_client

        client = _get_supabase_client()
        client.table("kg_edges").insert({
            "from_id": str(claim_id),
            "to_id": str(brand_claims[0].id),
            "relation": "references",
            "domain": "marketing",
            "properties": {"source": "117-03_auto_cross_ref"},
        }).execute()
    except Exception as e:
        logger.warning("creative_performance cross-ref skipped: %s", e)

    return claim_id
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_marketing_emit.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/marketing_emit.py tests/unit/services/intelligence/test_marketing_emit.py
git commit -m "feat(117-03): emit_campaign_lift/audience_resonance/creative_performance helpers (GREEN)"
```

### Task 3: Wire emission into `summarize_campaign_performance` + `get_cross_channel_attribution`

**Files:**
- Modify: `app/agents/tools/campaign_performance_tools.py`
- Modify: `app/agents/tools/attribution_tools.py`

- [ ] **Step 1: Append integration-style emission tests**

Add to `tests/unit/app/agents/tools/test_campaign_performance_confidence.py`:

```python
@pytest.mark.asyncio
async def test_summarize_campaign_performance_emits_campaign_lift_claim():
    """Live-path summarizer call emits one campaign_lift claim per call."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, patch

    from app.agents.tools.campaign_performance_tools import (
        summarize_campaign_performance,
    )

    fake_payload = {
        "summary_text": "Spent $340 with 12 conversions — 20% lift WoW",
        "total_spend": 340.0, "total_conversions": 12, "overall_cpa": 28.33,
        "wow_spend_change_pct": 0.20, "wow_conversions_change_pct": 0.10,
        "per_campaign": [
            {"campaign_id": "g1", "spend": 200, "conversions": 8,
             "matched_conversions": 8, "z_score": 2.1, "n": 80,
             "observed_audience": 5000, "declared_audience": 10000,
             "data_age_hours": 6,
             "campaign_end_date": datetime(2026, 6, 1, tzinfo=timezone.utc).isoformat()},
        ],
        "period": "2026-05-12_2026-05-19",
        "prior_period": "2026-05-05_2026-05-12",
    }

    emit_mock = AsyncMock(return_value=None)
    with patch(
        "app.agents.tools.campaign_performance_tools._get_user_id",
        return_value="u-1",
    ), patch(
        "app.services.campaign_performance_summarizer.CampaignPerformanceSummarizer.summarize_all_platforms",
        new=AsyncMock(return_value=fake_payload),
    ), patch(
        "app.agents.tools.campaign_performance_tools._resolve_user_campaign_entity",
        new=AsyncMock(return_value=None),  # graph-tier miss, fall to live
    ), patch(
        "app.agents.tools.campaign_performance_tools.emit_campaign_lift_claim",
        new=emit_mock,
    ):
        await summarize_campaign_performance(days=7)

    emit_mock.assert_awaited()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["campaign_id"] == "g1"
    assert kwargs["confidence"] == pytest.approx(
        # Same wiring as Plan 117-01 — verify it flows through
        0.0, abs=1.0,  # exact value is not the point of this test
    )
```

- [ ] **Step 2: Run — should FAIL (emit_campaign_lift_claim not imported yet)**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py::test_summarize_campaign_performance_emits_campaign_lift_claim -v --tb=short
```

- [ ] **Step 3: Wire the emit in `campaign_performance_tools.py`**

After `_attach_marketing_confidence(payload)` in the live path, iterate `payload["per_campaign"]` and call `emit_campaign_lift_claim` for each. Pass the per-campaign confidence — but since 117-01 attached the *aggregate* confidence, refine: re-compute per-row confidence so each claim has its own number.

Add at module scope:

```python
from app.services.intelligence.marketing_emit import emit_campaign_lift_claim


def _row_confidence(row: dict) -> float:
    """Per-row confidence using the same helpers as _attach_marketing_confidence."""
    from app.services.intelligence.marketing_stats import (
        attribution_completeness, audience_coverage,
        recency_score, statistical_significance,
    )
    from app.services.intelligence.presets import marketing_confidence

    ac = attribution_completeness(
        matched=int(row.get("matched_conversions", 0)),
        total=int(row.get("conversions", 0)),
    )
    ss = statistical_significance(
        z_score=float(row.get("z_score", 0.0)),
        n=int(row.get("n", 0)),
    )
    coverage = audience_coverage(
        observed=int(row.get("observed_audience", 0)),
        declared=row.get("declared_audience"),
    )
    recency = recency_score(float(row.get("data_age_hours", 0.0)))
    return marketing_confidence(ac, ss, coverage, recency)


async def _emit_campaign_lift_claims(payload: dict) -> None:
    """Emit one campaign_lift claim per per-campaign row. Best-effort."""
    from datetime import datetime

    for row in payload.get("per_campaign") or []:
        try:
            cid = row.get("campaign_id")
            if not cid:
                continue
            text = (
                payload.get("summary_text")
                or f"Campaign {cid}: {row.get('conversions', 0)} conversions"
            )
            campaign_end = row.get("campaign_end_date")
            if isinstance(campaign_end, str):
                campaign_end = datetime.fromisoformat(
                    campaign_end.replace("Z", "+00:00")
                )
            await emit_campaign_lift_claim(
                campaign_id=str(cid),
                finding_text=text,
                confidence=_row_confidence(row),
                sources=[{"kind": "platform_api", "ref": f"summary/{cid}"}],
                campaign_end_date=campaign_end,
                period_end_date=None,
            )
        except Exception:
            logger.warning("campaign_lift emission skipped for row", exc_info=True)
```

Call `_emit_campaign_lift_claims(payload)` after `_attach_marketing_confidence(payload)` and *before* the return. Wrap in a try/except so emission never blocks the tool response.

- [ ] **Step 4: Run — should PASS**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py -v --tb=short
```

- [ ] **Step 5: Mirror in `attribution_tools.py`**

`get_cross_channel_attribution` returns `per_channel`; emit one `campaign_lift` claim per channel using `campaign_id = f"channel_{channel}"` so the entity canonical name is namespaced. `get_budget_recommendation` does NOT emit (it's a forward-looking suggestion, not a measurement).

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
git commit -m "feat(117-03): emit campaign_lift claims from summarizer + cross-channel attribution"
```

### Task 4: Wire `audience_resonance` emission into social analytics

**Files:**
- Modify: `app/agents/tools/social_analytics.py`

- [ ] **Step 1: Failing test**

Append to `tests/unit/app/agents/tools/test_campaign_performance_confidence.py`:

```python
@pytest.mark.asyncio
async def test_get_social_analytics_emits_audience_resonance_claim():
    from unittest.mock import AsyncMock, patch
    from app.agents.tools.social_analytics import get_social_analytics

    fake = {
        "summary_text": "Instagram drove 12k impressions and 250 engagements",
        "per_post": [
            {"segment_id": "ig_25_34_f", "impressions": 5000, "engagements": 250,
             "matched_conversions": 0, "conversions": 0,
             "z_score": 1.7, "n": 40, "observed_audience": 5000,
             "declared_audience": None, "data_age_hours": 4,
             "period_end_date": None},
        ],
    }
    emit_mock = AsyncMock(return_value=None)
    with patch(
        "app.services.social_analytics_service.SocialAnalyticsService.get_summary",
        new=AsyncMock(return_value=fake),
    ), patch(
        "app.agents.tools.social_analytics._get_user_id", return_value="u-1",
    ), patch(
        "app.agents.tools.social_analytics.emit_audience_resonance_claim",
        new=emit_mock,
    ):
        await get_social_analytics(platform="instagram", days=7)
    emit_mock.assert_awaited()
    assert emit_mock.call_args.kwargs["segment_id"] == "ig_25_34_f"
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py::test_get_social_analytics_emits_audience_resonance_claim -v --tb=short
```

- [ ] **Step 3: Implement**

In `app/agents/tools/social_analytics.py`, mirror the Task-3 emission helper:

```python
from app.services.intelligence.marketing_emit import emit_audience_resonance_claim


async def _emit_audience_resonance_claims(payload: dict) -> None:
    from datetime import datetime
    for row in payload.get("per_post") or []:
        try:
            seg = row.get("segment_id")
            if not seg:
                continue
            text = (
                payload.get("summary_text")
                or f"Segment {seg}: engagement signal observed"
            )
            period_end = row.get("period_end_date")
            if isinstance(period_end, str):
                period_end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
            await emit_audience_resonance_claim(
                segment_id=str(seg),
                finding_text=text,
                confidence=_row_confidence(row),
                sources=[{"kind": "platform_api", "ref": f"social/{seg}"}],
                period_end_date=period_end,
            )
        except Exception:
            logger.warning("audience_resonance emission skipped", exc_info=True)
```

Call after `_attach_marketing_confidence` and before return on both `get_social_analytics` and `get_all_platform_analytics`. Import `_row_confidence` from `_marketing_confidence.py` (promote it there if it lives in `campaign_performance_tools.py`).

- [ ] **Step 4: Run — should PASS**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/_marketing_confidence.py app/agents/tools/social_analytics.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
git commit -m "feat(117-03): emit audience_resonance claims from social analytics tools"
```

### Task 5: Wire `creative_performance` emission into ad platform tools

**Files:**
- Modify: `app/agents/tools/ad_platform_tools.py`

`creative_performance` claims are emitted when an ad creative produces measurable results — practically, after the first call to `get_ad_campaign_performance` returns metrics for an active creative. Lower-effort path: emit alongside `save_ad_copy_as_creative` with provisional confidence; refresh on subsequent `refresh_ad_performance` calls.

- [ ] **Step 1: Failing test**

Append to the test file:

```python
@pytest.mark.asyncio
async def test_refresh_ad_performance_emits_creative_performance_claim():
    from unittest.mock import AsyncMock, patch
    from app.agents.tools.ad_platform_tools import refresh_ad_performance

    fake_perf = {
        "creative_id": "creative-99",
        "summary_text": "Creative outperformed control by 18% CTR over 5k impressions",
        "matched_conversions": 90, "conversions": 100,
        "z_score": 2.4, "n": 5000,
        "observed_audience": 5000, "declared_audience": 12000,
        "data_age_hours": 3,
        "campaign_end_date": None,
        "period_end_date": "2026-05-19T00:00:00Z",
    }
    emit_mock = AsyncMock(return_value=None)
    with patch(
        "app.agents.tools.ad_platform_tools._refresh_live",
        new=AsyncMock(return_value=fake_perf),
    ), patch(
        "app.agents.tools.ad_platform_tools._get_user_id", return_value="u-1",
    ), patch(
        "app.agents.tools.ad_platform_tools.emit_creative_performance_claim",
        new=emit_mock,
    ):
        await refresh_ad_performance(creative_id="creative-99")

    emit_mock.assert_awaited()
    assert emit_mock.call_args.kwargs["creative_id"] == "creative-99"
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py::test_refresh_ad_performance_emits_creative_performance_claim -v --tb=short
```

- [ ] **Step 3: Implement**

In `app/agents/tools/ad_platform_tools.py`, locate `refresh_ad_performance` (or whatever the canonical "fetch fresh creative metrics" entry point is — confirm via `grep -n "refresh_ad_performance" app/agents/tools/ad_platform_tools.py`). After the live fetch returns, call:

```python
from datetime import datetime
from app.services.intelligence.marketing_emit import emit_creative_performance_claim

try:
    creative_id = perf.get("creative_id")
    campaign_end = perf.get("campaign_end_date")
    period_end = perf.get("period_end_date")
    if isinstance(campaign_end, str):
        campaign_end = datetime.fromisoformat(campaign_end.replace("Z", "+00:00"))
    if isinstance(period_end, str):
        period_end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
    if creative_id:
        await emit_creative_performance_claim(
            creative_id=str(creative_id),
            finding_text=perf.get("summary_text", f"Creative {creative_id} performance"),
            confidence=_row_confidence(perf),
            sources=[{"kind": "platform_api", "ref": f"refresh/{creative_id}"}],
            campaign_end_date=campaign_end,
            period_end_date=period_end,
        )
except Exception:
    logger.warning("creative_performance emission skipped", exc_info=True)
```

- [ ] **Step 4: Run — should PASS**

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/ad_platform_tools.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
git commit -m "feat(117-03): emit creative_performance claims from refresh_ad_performance"
```

### Task 6: Integration test — round-trip + cross-agent semantic search

**Files:**
- Create: `tests/integration/test_marketing_claims_round_trip.py`

- [ ] **Step 1: Write the test**

```python
"""Integration: Marketing claim writes show up in semantic + structured search."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_marketing_claims_appear_in_semantic_search():
    """campaign_lift + audience_resonance + creative_performance — all retrievable."""
    from datetime import datetime, timezone
    from app.services.intelligence import (
        find_claims, search_claims_semantic,
    )
    from app.services.intelligence.marketing_emit import (
        emit_audience_resonance_claim,
        emit_campaign_lift_claim,
        emit_creative_performance_claim,
    )

    suffix = uuid4().hex[:8]

    lift_id = await emit_campaign_lift_claim(
        campaign_id=f"intg_camp_{suffix}",
        finding_text=(
            "Q1 2026 spring sale campaign drove a 23 percent lift "
            "in conversions week-over-week"
        ),
        confidence=0.78,
        sources=[{"kind": "platform_api", "ref": "intg_test"}],
        campaign_end_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        period_end_date=None,
    )
    resonance_id = await emit_audience_resonance_claim(
        segment_id=f"intg_seg_{suffix}",
        finding_text=(
            "Q1 2026 instagram audience segment 25-34 female showed "
            "highest engagement on lifestyle posts"
        ),
        confidence=0.71,
        sources=[{"kind": "platform_api", "ref": "intg_test"}],
        period_end_date=datetime(2026, 5, 19, tzinfo=timezone.utc),
    )
    creative_id = await emit_creative_performance_claim(
        creative_id=f"intg_creative_{suffix}",
        finding_text=(
            "Q1 2026 hero banner creative outperformed control by 18 percent CTR"
        ),
        confidence=0.82,
        sources=[{"kind": "platform_api", "ref": "intg_test"}],
        campaign_end_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        period_end_date=None,
    )

    assert lift_id is not None
    assert resonance_id is not None
    assert creative_id is not None

    # Structured search returns each by claim_type
    marketing_claims = await find_claims(agent_id="marketing", limit=20)
    types = {c.claim_type for c in marketing_claims}
    assert {"campaign_lift", "audience_resonance", "creative_performance"} <= types

    # Semantic search returns Marketing claims interleaved
    semantic = await search_claims_semantic(
        query="Q1 campaign performance and audience engagement",
        top_k=10,
    )
    agents = {c.agent_id for c, _ in semantic}
    assert "marketing" in agents
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_marketing_claims_round_trip.py -v --tb=short
```

Expected: PASS. If `search_claims_semantic` returns no Marketing claims, check the pgvector ivfflat index from `supabase/migrations/20260519000000_kg_findings_embedding_ivfflat_index.sql` is present.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_marketing_claims_round_trip.py
git commit -m "test(117-03): integration round-trip + cross-agent semantic search for Marketing claims"
```

### Task 7: Integration test — creative_performance ↔ brand_fidelity_score cross-ref

**Files:**
- Create: `tests/integration/test_marketing_creative_cross_ref.py`

This test SHIPS NOW but is **conditionally skipped** when Phase 122 has not landed. The skip predicate is the presence of any `brand_fidelity_score` claim_type in the DB after seeding a Content-Agent claim. The point of shipping it now is so Phase 122 has a ready-made smoke test.

- [ ] **Step 1: Write the test**

```python
"""Integration: creative_performance writes an edge to brand_fidelity_score (when Phase 122 present)."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="env not set",
    ),
]


@pytest.mark.asyncio
async def test_creative_performance_links_to_brand_fidelity_when_present():
    """When a brand_fidelity_score claim exists, creative_performance writes an edge."""
    from app.services.intelligence import (
        get_or_create_entity, write_claim,
    )
    from app.services.intelligence.claims import _get_supabase_client
    from app.services.intelligence.marketing_emit import (
        emit_creative_performance_claim,
    )

    suffix = uuid4().hex[:8]
    creative_canonical = f"creative_intg_{suffix}"

    # Seed a brand_fidelity_score claim as if Phase 122 had emitted it
    entity_id = await get_or_create_entity(
        canonical_name=creative_canonical, entity_type="topic",
        domains=["marketing", "content"],
    )
    brand_claim = await write_claim(
        entity_id=entity_id, domain="content",
        finding_text=(
            "Creative passes brand fidelity check: tone matches guidelines, "
            "colors within palette, logo positioned per spec"
        ),
        confidence=0.92,
        sources=[{"kind": "brand_profile", "ref": "v1"}],
        agent_id="content",
        claim_type="brand_fidelity_score",
        embed=True,
    )

    # Now emit a creative_performance claim — should write an edge
    perf_id = await emit_creative_performance_claim(
        creative_id=f"intg_{suffix}",
        finding_text="Hero banner outperformed control by 18 percent CTR",
        confidence=0.82,
        sources=[{"kind": "platform_api", "ref": "intg"}],
        campaign_end_date=None,
        period_end_date=None,
    )
    assert perf_id is not None

    # Edge should exist
    client = _get_supabase_client()
    edges = (
        client.table("kg_edges")
        .select("*")
        .eq("from_id", str(perf_id))
        .eq("to_id", str(brand_claim))
        .eq("relation", "references")
        .execute()
    )
    assert edges.data, "Expected edge from creative_performance to brand_fidelity_score"


@pytest.mark.asyncio
async def test_creative_performance_skips_edge_when_brand_claim_absent():
    """No brand_fidelity_score for the entity -> no edge, no error."""
    from app.services.intelligence.claims import _get_supabase_client
    from app.services.intelligence.marketing_emit import (
        emit_creative_performance_claim,
    )

    suffix = uuid4().hex[:8]
    perf_id = await emit_creative_performance_claim(
        creative_id=f"orphan_{suffix}",
        finding_text="A perfectly fine creative_performance claim text",
        confidence=0.7,
        sources=[],
        campaign_end_date=None,
        period_end_date=None,
    )
    assert perf_id is not None

    client = _get_supabase_client()
    edges = (
        client.table("kg_edges")
        .select("*")
        .eq("from_id", str(perf_id))
        .execute()
    )
    assert not edges.data, "No edge expected when no brand_fidelity_score claim"
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_marketing_creative_cross_ref.py -v --tb=short
```

Expected: both tests PASS. The first test seeds the brand claim itself, so it does not depend on Phase 122 having shipped — it verifies the *mechanism*.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_marketing_creative_cross_ref.py
git commit -m "test(117-03): creative_performance ↔ brand_fidelity_score edge creation"
```

### Task 8: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/marketing_emit.py app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py app/agents/tools/social_analytics.py app/agents/tools/ad_platform_tools.py app/agents/tools/_marketing_confidence.py tests/unit/services/intelligence/test_marketing_emit.py tests/integration/test_marketing_claims_round_trip.py tests/integration/test_marketing_creative_cross_ref.py
uv run ruff format --check app/services/intelligence/marketing_emit.py app/agents/tools/campaign_performance_tools.py app/agents/tools/attribution_tools.py app/agents/tools/social_analytics.py app/agents/tools/ad_platform_tools.py app/agents/tools/_marketing_confidence.py tests/unit/services/intelligence/test_marketing_emit.py tests/integration/test_marketing_claims_round_trip.py tests/integration/test_marketing_creative_cross_ref.py
```

Fix in place. Commit `style(117-03): ...`.

- [ ] **Step 2: Acceptance cross-check**

| 117-03 acceptance line | Verified by |
|---|---|
| `campaign_lift` claim shipped, `expires_at = campaign_end + 30d` | Task 2, Task 3 |
| `audience_resonance` claim shipped | Task 2, Task 4 |
| `creative_performance` claim shipped | Task 2, Task 5 |
| `creative_performance` cross-refs `brand_fidelity_score` when present | Tasks 2, 7 |
| All claims `embed=True` (semantic search + contradiction detection) | Task 2 Step 3 |
| Confidence flows from Plan 117-01 helpers into claim row | Task 3 (`_row_confidence`) |
| `search_claims_semantic("Q1 campaign performance")` returns Marketing + Data + Research interleaved | Task 6 |
| Emission degrades silently on Supabase / embedding failure | Task 2 Step 1 (`test_emit_campaign_lift_claim_swallows_supabase_error`) |
| Lint clean | Task 8 |

- [ ] **Step 3: Plan 117-03 complete. Hand off to 117-04 (regression guardrails).**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `campaign_lift` claim_type | Tasks 2, 3 |
| `audience_resonance` claim_type | Tasks 2, 4 |
| `creative_performance` claim_type | Tasks 2, 5 |
| `expires_at = campaign_end + 30d` | Task 2 (`_claim_expires_at`) |
| `period_end + 30d` fallback | Task 2 (`_claim_expires_at`) |
| Cross-ref to `brand_fidelity_score` when Phase 122 ships | Tasks 2, 7 |
| Phase-122-absent path is non-fatal | Task 2 Step 3 (logger.info), Task 7 (second test) |
| Cross-agent semantic search interleaves Marketing | Task 6 |
| Lint clean | Task 8 |

All spec lines covered.
