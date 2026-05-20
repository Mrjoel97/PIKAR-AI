# Shared Intelligence Infrastructure — Plan 117-02: Marketing Multi-Platform Cache

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the two-tier adaptive cache (Phase 112-04) around Marketing's four external-API surfaces — Google Ads, Meta Ads, Shopify, and social analytics — using platform-specific TTLs. Reduce repeat external-API call rate by ≥40% on a synthetic load test, with a graph-tier check that returns a fresh Marketing claim instead of round-tripping the platform API when one exists.

**Architecture:** Marketing's external surface is wider than Data's (which had only Stripe/Shopify): four platforms, each with its own quota and freshness profile. The cache lives entirely in `should_call_external(...)` (Redis) for raw payloads and `should_query_graph(...)` for derived claims. Cache keys are namespaced per platform so Phase 114-02's `shopify:orders:*` keys are *reused* not duplicated. Each external-API call gains a thin wrapper that consults the cache first, falls back to live fetch on miss, and writes the response back to Redis with the platform-specific TTL. Graph-tier hits are explicitly tagged `tier=external` so observability can distinguish them from intra-graph reads.

**Tech Stack:** `app/services/intelligence/cache.py` (read-only — Plan 112-04 surface), `app/services/google_ads_service.py`, `app/services/meta_ads_service.py`, `app/services/shopify_service.py`, `app/services/social_analytics_service.py` (modified), `app/services/intelligence/marketing_cache_keys.py` (new — central key-shape registry).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 117 — Marketing Agent adoption · Cache integration table.

**Out of scope:** Claim emission (Plan 117-03). Confidence preset (Plan 117-01, complete). Regression baseline capture (Plan 117-04). Per-user-tier cache TTL overrides (deferred — uniform TTLs per the spec). Cross-platform deduplication of identical campaign IDs across Google + Meta (theoretical only — no real ID collision today). Pre-warming the cache from background jobs (the cache fills from live queries; no warmer needed).

---

## File structure

**Create:**
- `app/services/intelligence/marketing_cache_keys.py` — central key-shape registry + TTL table
- `tests/unit/services/intelligence/test_marketing_cache_keys.py` — key-shape contract tests
- `tests/unit/services/test_google_ads_cache.py` — Google Ads cache wrapper tests
- `tests/unit/services/test_meta_ads_cache.py` — Meta Ads cache wrapper tests
- `tests/unit/services/test_social_analytics_cache.py` — Social analytics cache wrapper tests
- `tests/integration/test_marketing_cache_perf.py` — synthetic-load perf test (≥40% reduction target)

**Modify:**
- `app/services/google_ads_service.py` — wrap `get_campaign_performance` in `should_call_external` / `set_cached`
- `app/services/meta_ads_service.py` — wrap `get_campaign_insights` similarly
- `app/services/shopify_service.py` — wrap `get_orders` / `get_analytics` (114-02 may have done this — REUSE if so)
- `app/services/social_analytics_service.py` — wrap the public read surface (`get_summary` / `get_all_platforms`)
- `app/agents/tools/campaign_performance_tools.py` — graph-tier short-circuit before the summarizer call

---

## Pre-flight context

**Cache keys** (from the spec):

| Cache key shape | Tier | TTL | Source |
|---|---|---|---|
| `gads:campaign:{campaign_id}` | Redis | 600s | Google Ads `get_campaign_performance` |
| `meta:campaign:{campaign_id}` | Redis | 600s | Meta Ads `get_campaign_insights` |
| `shopify:orders:{period}:{shop}` | Redis | 300s | Shopify `get_orders` — **may already exist from 114-02** |
| `social_analytics:{platform}:{period}` | Redis | 1800s | Social analytics services |
| Marketing claims | Graph | 24h freshness | `claim_freshness_hours(entity_id, claim_type=campaign_lift\|audience_resonance\|creative_performance)` |

**Why these TTLs:**
- Google/Meta campaigns refresh on ~5-15min platform cadence; 600s sits inside that window without showing stale numbers
- Shopify orders refresh within minutes during business hours; 300s mirrors the Data-Agent pilot's choice
- Social analytics platforms (Instagram, Twitter, LinkedIn) refresh aggregates on 30-60min cadence; 1800s is comfortably inside that
- Graph tier 24h matches the Phase 113 Data-pilot pattern — campaign claims older than a day are stale enough to require re-derivation

**Reuse rule:** Before defining `shopify:orders:*`, **grep** for the key in `app/services/`. If Phase 114-02 shipped it, this plan must import the same key-builder, not duplicate it. The grep is part of Task 1.

**Cache-decision semantics:**

```python
decision = await should_call_external(
    cache_key="gads:campaign:abc123",
    ttl_seconds=600,
)
if decision.verdict == "fresh":
    # decision.freshness_hours has the age; cache hit
    cached = await cache_service.get(cache_key)
    return cached
# else: live fetch + cache write
```

`should_query_graph` for the graph tier:

```python
decision = await should_query_graph(
    entity_id=campaign_entity_id,
    claim_type="campaign_lift",
    agent_id="marketing",
    freshness_threshold_hours=24.0,
)
if decision.verdict == "fresh":
    claims = await find_claims(entity_id=campaign_entity_id, claim_type="campaign_lift", limit=1)
    return claims[0] if claims else None
# else: derive new claim from platform data
```

Environment quirks: same as prior plans. Redis dev password `pikar_dev_redis`; `app/services/cache.py` provides the singleton with circuit breaker. The breaker can be **open** during tests — wrappers MUST degrade gracefully (verdict='miss' → live fetch).

Acceptance bar:
- All four cache keys defined in `marketing_cache_keys.py` with documented TTLs
- Each external-API call goes through a cache wrapper that returns cached data on `verdict='fresh'`
- ≥40% call-rate reduction on the synthetic load test (Task 6)
- No regression in live-fetch correctness when the cache is empty (the existing service tests still pass)
- Graph-tier short-circuit triggers in `summarize_campaign_performance` when a fresh `campaign_lift` claim exists
- Lint + format clean

---

## Tasks

### Task 1: Pre-flight — confirm reuse opportunities + cache surface

- [ ] **Step 1: Confirm Plan 117-01 has landed**

```powershell
uv run python -c "from app.services.intelligence.presets import marketing_confidence; print('OK')"
ls app/services/intelligence/marketing_stats.py
```

Both must succeed. If 117-01 is incomplete, **STOP** — confidence wiring is a hard prerequisite because cache writes will eventually carry the confidence numbers.

- [ ] **Step 2: Detect prior Shopify cache keys (Phase 114-02 reuse check)**

```powershell
uv run python -c "import pathlib, re; src = pathlib.Path('app/services'); hits = [(p.name, line) for p in src.rglob('*.py') for line in p.read_text(errors='ignore').splitlines() if 'shopify:orders' in line.lower()]; [print(*h) for h in hits]"
```

If hits are found, copy the exact key-builder signature into Step-3's plan. **Reuse it**, do not redefine. If no hits, this plan is the first to define the key.

- [ ] **Step 3: Confirm cache service availability**

```powershell
uv run python -c "from app.services.cache import get_cache_service; c = get_cache_service(); print(type(c).__name__)"
uv run python -c "from app.services.intelligence.cache import should_call_external, should_query_graph; print('OK')"
```

Both must succeed.

- [ ] **Step 4: Capture the baseline external-call count under load (informational, no commit)**

```powershell
uv run python -c "import asyncio; from app.services.google_ads_service import GoogleAdsService; svc = GoogleAdsService(); print('service constructible: OK')"
```

Record this in the commit message of Task 6's perf test ("Pre-cache baseline = N calls / 100 requests").

### Task 2: Build the cache-key registry (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_marketing_cache_keys.py`
- Create: `app/services/intelligence/marketing_cache_keys.py`

- [ ] **Step 1: Failing tests**

```python
"""Cache-key shape + TTL registry tests."""

from __future__ import annotations

import pytest


def test_google_ads_campaign_key_shape():
    from app.services.intelligence.marketing_cache_keys import gads_campaign_key

    assert gads_campaign_key("abc-123") == "gads:campaign:abc-123"


def test_meta_ads_campaign_key_shape():
    from app.services.intelligence.marketing_cache_keys import meta_campaign_key

    assert meta_campaign_key("act_1/c_55") == "meta:campaign:act_1/c_55"


def test_shopify_orders_key_includes_period_and_shop():
    from app.services.intelligence.marketing_cache_keys import shopify_orders_key

    assert (
        shopify_orders_key(period="2026-05-12_2026-05-19", shop="acme.myshopify.com")
        == "shopify:orders:2026-05-12_2026-05-19:acme.myshopify.com"
    )


def test_social_analytics_key_includes_platform_and_period():
    from app.services.intelligence.marketing_cache_keys import social_analytics_key

    assert (
        social_analytics_key(platform="instagram", period="2026-05-12_2026-05-19")
        == "social_analytics:instagram:2026-05-12_2026-05-19"
    )


def test_ttl_table_matches_spec():
    from app.services.intelligence.marketing_cache_keys import MARKETING_TTL

    assert MARKETING_TTL["gads:campaign"] == 600
    assert MARKETING_TTL["meta:campaign"] == 600
    assert MARKETING_TTL["shopify:orders"] == 300
    assert MARKETING_TTL["social_analytics"] == 1800
    assert MARKETING_TTL["graph_freshness_hours"] == 24.0


@pytest.mark.parametrize("bad", ["", "  ", None])
def test_keys_reject_empty_components(bad):
    """Empty / whitespace-only / None components must raise ValueError."""
    from app.services.intelligence.marketing_cache_keys import gads_campaign_key

    with pytest.raises(ValueError):
        gads_campaign_key(bad)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_marketing_cache_keys.py -v --tb=short
```

- [ ] **Step 3: Implement `app/services/intelligence/marketing_cache_keys.py`**

```python
"""Central registry of Marketing-Agent cache keys + TTLs.

Phase 117-02. All platform wrappers MUST consume these helpers to
guarantee a single source of truth for key shape. Adding a new key
here is a deliberate, reviewable act.
"""

from __future__ import annotations

MARKETING_TTL: dict[str, float | int] = {
    "gads:campaign": 600,        # 10 minutes — Google Ads platform refresh cadence
    "meta:campaign": 600,        # 10 minutes — Meta Ads platform refresh cadence
    "shopify:orders": 300,       # 5 minutes — matches Phase 114-02 / Data pilot
    "social_analytics": 1800,    # 30 minutes — Instagram/LinkedIn/Twitter aggregate cadence
    "graph_freshness_hours": 24.0,  # graph tier — campaign_lift / audience_resonance / creative_performance
}


def _require(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def gads_campaign_key(campaign_id: str) -> str:
    """Google Ads per-campaign performance cache key."""
    return f"gads:campaign:{_require(campaign_id, name='campaign_id')}"


def meta_campaign_key(campaign_id: str) -> str:
    """Meta Ads per-campaign insights cache key."""
    return f"meta:campaign:{_require(campaign_id, name='campaign_id')}"


def shopify_orders_key(*, period: str, shop: str) -> str:
    """Shopify orders cache key.

    Phase 114-02 may already define this — if so, that definition is
    canonical and this module re-exports the same shape.
    """
    return (
        f"shopify:orders:"
        f"{_require(period, name='period')}:"
        f"{_require(shop, name='shop')}"
    )


def social_analytics_key(*, platform: str, period: str) -> str:
    """Per-platform social analytics summary cache key."""
    return (
        f"social_analytics:"
        f"{_require(platform, name='platform')}:"
        f"{_require(period, name='period')}"
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_marketing_cache_keys.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/marketing_cache_keys.py tests/unit/services/intelligence/test_marketing_cache_keys.py
git commit -m "feat(117-02): central registry for Marketing cache keys + TTLs"
```

### Task 3: Wrap Google Ads `get_campaign_performance` in the cache (TDD)

**Files:**
- Create: `tests/unit/services/test_google_ads_cache.py`
- Modify: `app/services/google_ads_service.py`

- [ ] **Step 1: Failing test**

```python
"""Google Ads cache-wrapper tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_campaign_performance_returns_cached_on_fresh():
    """When should_call_external says 'fresh', the live API is NOT called."""
    from app.services.google_ads_service import GoogleAdsService
    from app.services.intelligence.schemas import CacheDecision

    cached_payload = {"campaign_id": "c-1", "spend": 100.0, "cached": True}

    with patch(
        "app.services.google_ads_service.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="fresh", freshness_hours=0.05,
        )),
    ), patch(
        "app.services.google_ads_service.get_cache_service",
        return_value=MagicMock(get=AsyncMock(return_value=cached_payload)),
    ), patch.object(
        GoogleAdsService, "_fetch_campaign_performance_live",
        new=AsyncMock(side_effect=AssertionError("live API must NOT be called")),
    ):
        svc = GoogleAdsService()
        result = await svc.get_campaign_performance(
            user_id="u-1", campaign_id="c-1",
        )

    assert result == cached_payload


@pytest.mark.asyncio
async def test_get_campaign_performance_falls_back_to_live_on_miss():
    """When verdict='miss', live API is called AND result is cached."""
    from app.services.google_ads_service import GoogleAdsService
    from app.services.intelligence.schemas import CacheDecision

    live_payload = {"campaign_id": "c-1", "spend": 200.0, "cached": False}
    cache_mock = MagicMock(
        get=AsyncMock(return_value=None),
        set=AsyncMock(return_value=None),
    )

    with patch(
        "app.services.google_ads_service.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="miss", freshness_hours=None,
        )),
    ), patch(
        "app.services.google_ads_service.get_cache_service",
        return_value=cache_mock,
    ), patch.object(
        GoogleAdsService, "_fetch_campaign_performance_live",
        new=AsyncMock(return_value=live_payload),
    ):
        svc = GoogleAdsService()
        result = await svc.get_campaign_performance(
            user_id="u-1", campaign_id="c-1",
        )

    assert result == live_payload
    cache_mock.set.assert_awaited_once()
    args, kwargs = cache_mock.set.call_args
    # key shape is exact
    assert args[0] == "gads:campaign:c-1"
    assert kwargs.get("ttl") == 600


@pytest.mark.asyncio
async def test_get_campaign_performance_degrades_when_cache_breaker_open():
    """Cache service raising must NOT block the live fetch."""
    from app.services.google_ads_service import GoogleAdsService

    live_payload = {"campaign_id": "c-1", "spend": 200.0}
    with patch(
        "app.services.google_ads_service.should_call_external",
        new=AsyncMock(side_effect=RuntimeError("circuit breaker open")),
    ), patch.object(
        GoogleAdsService, "_fetch_campaign_performance_live",
        new=AsyncMock(return_value=live_payload),
    ):
        svc = GoogleAdsService()
        result = await svc.get_campaign_performance(
            user_id="u-1", campaign_id="c-1",
        )
    assert result == live_payload
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/test_google_ads_cache.py -v --tb=short
```

- [ ] **Step 3: Implement the wrapper**

In `app/services/google_ads_service.py`:

1. Rename the existing `get_campaign_performance` body to `_fetch_campaign_performance_live` (preserving the entire HTTP/auth path verbatim).
2. Write a new `get_campaign_performance` that consults the cache, falls back, and writes back.

```python
from app.services.cache import get_cache_service
from app.services.intelligence.cache import should_call_external
from app.services.intelligence.marketing_cache_keys import (
    MARKETING_TTL, gads_campaign_key,
)

class GoogleAdsService:
    # ... existing __init__, get_accessible_customers, etc. ...

    async def get_campaign_performance(
        self,
        *,
        user_id: str,
        campaign_id: str,
        # ... preserve all existing keyword args ...
    ) -> dict:
        """Cache-aware wrapper around _fetch_campaign_performance_live."""
        key = gads_campaign_key(campaign_id)
        ttl = int(MARKETING_TTL["gads:campaign"])

        try:
            decision = await should_call_external(cache_key=key, ttl_seconds=ttl)
        except Exception:
            decision = None

        if decision is not None and decision.verdict == "fresh":
            try:
                cached = await get_cache_service().get(key)
                if cached is not None:
                    return cached
            except Exception:
                # Cache read failed — fall through to live fetch
                pass

        live = await self._fetch_campaign_performance_live(
            user_id=user_id, campaign_id=campaign_id,
            # ... pass through remaining kwargs ...
        )

        # Best-effort cache write — never let a write failure raise
        try:
            await get_cache_service().set(key, live, ttl=ttl)
        except Exception:
            pass

        return live

    async def _fetch_campaign_performance_live(
        self,
        *,
        user_id: str,
        campaign_id: str,
        # ... preserve original signature ...
    ) -> dict:
        # ... original body of get_campaign_performance, unchanged ...
```

- [ ] **Step 4: Run — should PASS**

```powershell
uv run pytest tests/unit/services/test_google_ads_cache.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/google_ads_service.py tests/unit/services/test_google_ads_cache.py
git commit -m "feat(117-02): cache wrapper around GoogleAdsService.get_campaign_performance (600s TTL)"
```

### Task 4: Wrap Meta Ads `get_campaign_insights` in the cache

**Files:**
- Create: `tests/unit/services/test_meta_ads_cache.py`
- Modify: `app/services/meta_ads_service.py`

Identical pattern to Task 3. Substitute `meta_campaign_key`, TTL `MARKETING_TTL["meta:campaign"]` (600s), function name `get_campaign_insights` → `_fetch_campaign_insights_live`.

- [ ] **Step 1: Failing test** — copy the three Task-3 tests, change all references from Google → Meta, `gads:campaign:c-1` → `meta:campaign:c-1`, `get_campaign_performance` → `get_campaign_insights`.

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/test_meta_ads_cache.py -v --tb=short
```

- [ ] **Step 3: Implement the wrapper** (mirror Task 3 Step 3 verbatim with the Meta substitutions).

- [ ] **Step 4: Run — should PASS**

```powershell
uv run pytest tests/unit/services/test_meta_ads_cache.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/meta_ads_service.py tests/unit/services/test_meta_ads_cache.py
git commit -m "feat(117-02): cache wrapper around MetaAdsService.get_campaign_insights (600s TTL)"
```

### Task 5: Wrap Shopify + Social Analytics services

**Files:**
- Create: `tests/unit/services/test_social_analytics_cache.py`
- Modify: `app/services/social_analytics_service.py`
- Modify (only if Phase 114-02 didn't): `app/services/shopify_service.py`

- [ ] **Step 1: Shopify reuse check**

Re-run the Task 1 Step 2 grep. If `shopify_orders_key` is *already* called from `app/services/shopify_service.py`, **skip the Shopify wrapping in this task** — only confirm via a tiny smoke test in Task 6's perf script that the existing wrapper still hits the right Redis key. Otherwise, repeat the Task 3 pattern with `shopify_orders_key(period=..., shop=...)` and TTL 300s.

- [ ] **Step 2: Failing social-analytics test**

```python
"""Social analytics cache-wrapper tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_summary_returns_cached_on_fresh():
    from app.services.intelligence.schemas import CacheDecision
    from app.services.social_analytics_service import SocialAnalyticsService

    cached = {"platform": "instagram", "impressions": 12_000, "cached": True}
    with patch(
        "app.services.social_analytics_service.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="fresh", freshness_hours=0.2,
        )),
    ), patch(
        "app.services.social_analytics_service.get_cache_service",
        return_value=MagicMock(get=AsyncMock(return_value=cached)),
    ), patch.object(
        SocialAnalyticsService, "_fetch_summary_live",
        new=AsyncMock(side_effect=AssertionError("live API must NOT be called")),
    ):
        svc = SocialAnalyticsService()
        result = await svc.get_summary(
            user_id="u-1", platform="instagram",
            period="2026-05-12_2026-05-19",
        )
    assert result == cached


@pytest.mark.asyncio
async def test_get_summary_caches_live_response_for_1800s():
    from app.services.intelligence.schemas import CacheDecision
    from app.services.social_analytics_service import SocialAnalyticsService

    live = {"platform": "instagram", "impressions": 15_000}
    cache_mock = MagicMock(
        get=AsyncMock(return_value=None),
        set=AsyncMock(return_value=None),
    )
    with patch(
        "app.services.social_analytics_service.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="miss", freshness_hours=None,
        )),
    ), patch(
        "app.services.social_analytics_service.get_cache_service",
        return_value=cache_mock,
    ), patch.object(
        SocialAnalyticsService, "_fetch_summary_live",
        new=AsyncMock(return_value=live),
    ):
        svc = SocialAnalyticsService()
        result = await svc.get_summary(
            user_id="u-1", platform="instagram",
            period="2026-05-12_2026-05-19",
        )
    assert result == live
    args, kwargs = cache_mock.set.call_args
    assert args[0] == "social_analytics:instagram:2026-05-12_2026-05-19"
    assert kwargs.get("ttl") == 1800
```

- [ ] **Step 3: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/test_social_analytics_cache.py -v --tb=short
```

- [ ] **Step 4: Implement**

If `app/services/social_analytics_service.py` does not exist (the grep in Task 1 Step 1 hits only `app/agents/tools/social_analytics.py`), then promote a thin service module:

```python
# app/services/social_analytics_service.py
from __future__ import annotations

from app.services.cache import get_cache_service
from app.services.intelligence.cache import should_call_external
from app.services.intelligence.marketing_cache_keys import (
    MARKETING_TTL, social_analytics_key,
)


class SocialAnalyticsService:
    async def get_summary(
        self, *, user_id: str, platform: str, period: str,
    ) -> dict:
        key = social_analytics_key(platform=platform, period=period)
        ttl = int(MARKETING_TTL["social_analytics"])

        try:
            decision = await should_call_external(cache_key=key, ttl_seconds=ttl)
        except Exception:
            decision = None

        if decision is not None and decision.verdict == "fresh":
            try:
                cached = await get_cache_service().get(key)
                if cached is not None:
                    return cached
            except Exception:
                pass

        live = await self._fetch_summary_live(
            user_id=user_id, platform=platform, period=period,
        )
        try:
            await get_cache_service().set(key, live, ttl=ttl)
        except Exception:
            pass
        return live

    async def _fetch_summary_live(
        self, *, user_id: str, platform: str, period: str,
    ) -> dict:
        # Delegate to the existing per-platform fetchers in
        # app/agents/tools/social_analytics.py or services/social_*.py.
        from app.agents.tools.social_analytics import get_social_analytics
        return await get_social_analytics(platform=platform, days=7)
```

If the service file already exists, mirror the Task 3 pattern in-place.

- [ ] **Step 5: Run — should PASS**

```powershell
uv run pytest tests/unit/services/test_social_analytics_cache.py -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add app/services/social_analytics_service.py app/services/shopify_service.py tests/unit/services/test_social_analytics_cache.py
git commit -m "feat(117-02): cache wrappers around social_analytics + shopify (1800s / 300s TTLs)"
```

### Task 6: Graph-tier short-circuit in `summarize_campaign_performance`

**Files:**
- Modify: `app/agents/tools/campaign_performance_tools.py`

The Redis tier saves a network round-trip; the **graph tier** saves derivation cost. When a `campaign_lift` claim fresher than 24h exists for the campaign entity, return it without ever calling the platform APIs.

- [ ] **Step 1: Add a graph-tier short-circuit test**

Append to `tests/unit/app/agents/tools/test_campaign_performance_confidence.py`:

```python
@pytest.mark.asyncio
async def test_summarize_short_circuits_on_fresh_graph_claim():
    """If a fresh campaign_lift claim exists, the summarizer is not called."""
    from datetime import datetime, timezone
    from uuid import uuid4
    from unittest.mock import AsyncMock, patch

    from app.agents.tools.campaign_performance_tools import (
        summarize_campaign_performance,
    )
    from app.services.intelligence.schemas import (
        CacheDecision, Claim, ClaimSource,
    )

    entity_id = uuid4()
    fresh_claim = Claim(
        id=uuid4(), entity_id=entity_id, edge_id=None,
        agent_id="marketing", claim_type="campaign_lift",
        domain="marketing",
        finding_text="Spring sale drove a 23% lift WoW",
        confidence=0.78, sources=[ClaimSource(kind="other", ref="t")],
        contradicts=[], freshness_at=datetime.now(timezone.utc),
        expires_at=None, created_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.agents.tools.campaign_performance_tools._resolve_user_campaign_entity",
        new=AsyncMock(return_value=entity_id),
    ), patch(
        "app.agents.tools.campaign_performance_tools.should_query_graph",
        new=AsyncMock(return_value=CacheDecision(
            tier="graph", verdict="fresh", freshness_hours=2.0,
        )),
    ), patch(
        "app.agents.tools.campaign_performance_tools.find_claims",
        new=AsyncMock(return_value=[fresh_claim]),
    ), patch(
        "app.services.campaign_performance_summarizer.CampaignPerformanceSummarizer.summarize_all_platforms",
        new=AsyncMock(side_effect=AssertionError("summarizer must not run")),
    ), patch(
        "app.agents.tools.campaign_performance_tools._get_user_id",
        return_value="u-1",
    ):
        result = await summarize_campaign_performance(days=7)

    assert result["summary_text"] == fresh_claim.finding_text
    assert result["confidence"] == fresh_claim.confidence
    assert result["band"] in {"low", "medium", "high"}
    assert result.get("source") == "graph_cache"
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py::test_summarize_short_circuits_on_fresh_graph_claim -v --tb=short
```

- [ ] **Step 3: Implement the short-circuit**

In `app/agents/tools/campaign_performance_tools.py`, before the existing `CampaignPerformanceSummarizer` call:

```python
async def _resolve_user_campaign_entity(user_id: str) -> "UUID | None":
    """Look up the per-user campaign aggregate entity, or None if absent.

    Used by the graph-tier short-circuit. Returns None when the entity has
    not been created yet — the live path runs and (per Plan 117-03) emits
    the first campaign_lift claim, which populates the entity going forward.
    """
    try:
        from app.services.intelligence import get_or_create_entity
        return await get_or_create_entity(
            canonical_name=f"user_campaign_aggregate_{user_id}",
            entity_type="topic", domains=["marketing"],
        )
    except Exception:
        return None


async def summarize_campaign_performance(days: int = 7) -> dict[str, Any]:
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}
    if days <= 0:
        return {"error": "days must be a positive integer."}

    # Graph-tier short-circuit
    try:
        from app.services.intelligence import (
            find_claims, to_band,
        )
        from app.services.intelligence.cache import should_query_graph
        from app.services.intelligence.marketing_cache_keys import MARKETING_TTL

        entity_id = await _resolve_user_campaign_entity(user_id)
        if entity_id is not None:
            decision = await should_query_graph(
                entity_id=entity_id,
                claim_type="campaign_lift",
                agent_id="marketing",
                freshness_threshold_hours=float(
                    MARKETING_TTL["graph_freshness_hours"]
                ),
            )
            if decision.verdict == "fresh":
                claims = await find_claims(
                    entity_id=entity_id,
                    claim_type="campaign_lift",
                    agent_id="marketing",
                    limit=1,
                )
                if claims:
                    c = claims[0]
                    return {
                        "summary_text": c.finding_text,
                        "confidence": c.confidence,
                        "band": to_band(c.confidence),
                        "source": "graph_cache",
                        "freshness_hours": decision.freshness_hours,
                    }
    except Exception:
        logger.warning(
            "summarize_campaign_performance: graph-tier short-circuit failed",
            exc_info=True,
        )

    # Live path (Plan 117-01 already added confidence attachment)
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

- [ ] **Step 4: Run — should PASS, no other test should regress**

```powershell
uv run pytest tests/unit/app/agents/tools/test_campaign_performance_confidence.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/campaign_performance_tools.py tests/unit/app/agents/tools/test_campaign_performance_confidence.py
git commit -m "feat(117-02): graph-tier short-circuit on summarize_campaign_performance (24h freshness)"
```

### Task 7: Synthetic-load perf test — ≥40% call-rate reduction

**Files:**
- Create: `tests/integration/test_marketing_cache_perf.py`

- [ ] **Step 1: Write the perf test**

```python
"""Cache-reduction perf test: ≥40% fewer external calls on 100-burst load."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


@pytest.mark.asyncio
async def test_burst_load_reduces_external_call_rate_by_at_least_40_pct():
    """100 calls across 5 campaigns; live API call rate should drop ≥40%."""
    from app.services.google_ads_service import GoogleAdsService

    live_calls = {"n": 0}

    async def fake_live(*, user_id, campaign_id, **_):
        live_calls["n"] += 1
        return {"campaign_id": campaign_id, "spend": 100.0}

    # Real Redis if available; fall back to in-memory dict if not.
    inmem: dict = {}

    async def fake_get(key):
        return inmem.get(key)

    async def fake_set(key, value, *, ttl=None):
        inmem[key] = value

    cache_mock = MagicMock(get=AsyncMock(side_effect=fake_get),
                          set=AsyncMock(side_effect=fake_set))

    # Use the real should_call_external against the fake cache so freshness
    # tracking actually fires.
    with patch.object(
        GoogleAdsService, "_fetch_campaign_performance_live",
        new=AsyncMock(side_effect=fake_live),
    ), patch(
        "app.services.google_ads_service.get_cache_service",
        return_value=cache_mock,
    ), patch(
        "app.services.cache.get_cache_service",
        return_value=cache_mock,
    ):
        svc = GoogleAdsService()
        # 100 calls; only 5 unique campaign IDs -> 95 cache hits expected
        campaign_ids = [f"c-{i % 5}" for i in range(100)]
        await asyncio.gather(*[
            svc.get_campaign_performance(user_id="u-1", campaign_id=cid)
            for cid in campaign_ids
        ])

    # First-call-per-campaign always misses; 5 unique cids -> exactly 5 live calls
    # at the lower bound. ≥40% reduction = ≤60 live calls / 100.
    assert live_calls["n"] <= 60, (
        f"Live calls = {live_calls['n']} / 100; expected ≤60 (40% reduction). "
        f"Cache wrapper is not deduplicating concurrent first-call races, "
        f"or cache writes are dropping."
    )
    # Aspiration: at most 10 live calls (we'll print, not fail, the better number)
    print(f"Live calls = {live_calls['n']} / 100 — saving = "
          f"{(100 - live_calls['n']) / 100:.0%}")
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_marketing_cache_perf.py -v --tb=short
```

Expected: PASS with `live_calls ≤ 60`. The print line should show savings ≥40%.

If it fails: the wrapper is *racing* on the first call (multiple concurrent first calls all see verdict='miss', all do live fetches before any writes back). The acceptable mitigations:

1. Add a per-key asyncio lock around the live fetch in `GoogleAdsService.get_campaign_performance` (single-flight).
2. Document the racing-window as known behaviour and only count post-cache-warm calls.

Prefer mitigation 1 — single-flight matches the Phase 113 Data cache pattern.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_marketing_cache_perf.py
git commit -m "test(117-02): synthetic-load perf test for ≥40% cache-reduction on Google Ads"
```

### Task 8: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/services/intelligence/marketing_cache_keys.py app/services/google_ads_service.py app/services/meta_ads_service.py app/services/social_analytics_service.py app/services/shopify_service.py app/agents/tools/campaign_performance_tools.py tests/unit/services/intelligence/test_marketing_cache_keys.py tests/unit/services/test_google_ads_cache.py tests/unit/services/test_meta_ads_cache.py tests/unit/services/test_social_analytics_cache.py tests/integration/test_marketing_cache_perf.py
uv run ruff format --check app/services/intelligence/marketing_cache_keys.py app/services/google_ads_service.py app/services/meta_ads_service.py app/services/social_analytics_service.py app/services/shopify_service.py app/agents/tools/campaign_performance_tools.py tests/unit/services/intelligence/test_marketing_cache_keys.py tests/unit/services/test_google_ads_cache.py tests/unit/services/test_meta_ads_cache.py tests/unit/services/test_social_analytics_cache.py tests/integration/test_marketing_cache_perf.py
```

Fix in place; commit fixes as `style(117-02): ...`.

- [ ] **Step 2: Acceptance cross-check**

| 117-02 acceptance line | Verified by |
|---|---|
| `gads:campaign:{campaign_id}` key + 600s TTL | Task 2, Task 3 |
| `meta:campaign:{campaign_id}` key + 600s TTL | Task 2, Task 4 |
| `shopify:orders:{period}:{shop}` reused or shipped | Task 1 (reuse check), Task 5 |
| `social_analytics:{platform}:{period}` + 1800s TTL | Task 2, Task 5 |
| Graph-tier short-circuit on 24h freshness | Task 6 |
| ≥40% reduction on synthetic burst | Task 7 |
| No regression in existing service tests | Tasks 3-5 |

- [ ] **Step 3: Plan 117-02 complete. Hand off to 117-03 (claim emission).**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| Google Ads cache (Redis 600s) | Tasks 2, 3 |
| Meta Ads cache (Redis 600s) | Tasks 2, 4 |
| Shopify orders cache (Redis 300s, reuse 114-02 if extant) | Tasks 1, 5 |
| Social analytics cache (Redis 1800s) | Tasks 2, 5 |
| Marketing claims graph tier (24h) | Task 6 |
| ≥40% reduction on synthetic load | Task 7 |
| Reads degrade silently on cache failure | Tasks 3-5 (breaker-open paths) |
| Lint clean | Task 8 |

All spec lines covered.
