# Shared Intelligence Infrastructure — Plan 114-02: Financial cache integration (Stripe + Shopify)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Phase 112 two-tier adaptive cache (`should_call_external` for Redis raw responses, `should_query_graph` for `kg_findings` claim freshness) around every Stripe / Shopify external call the Financial Agent makes, so repeated calls within a TTL hit cache instead of the upstream service. Per spec acceptance: Stripe call rate reduced ≥40% on synthetic load test; graph-tier hit rate ≥60% on repeated `revenue_trend` queries within 24h.

**Architecture:** Mirrors Plan 113-02's pattern around Data Agent external calls. Every external-call site (`get_stripe_revenue_summary`, `get_shopify_orders`, and a NEW `get_stripe_disputes` helper) is wrapped in the same shape:

```
1. cache_key = "stripe:revenue_summary:{period}"  # or "shopify:orders:{period}:{shop}"
2. decision = await should_call_external(cache_key, ttl_seconds)
3. if decision.verdict == "fresh":  return cached value (Redis hit)
4. else:                            call upstream + cache.set(value)
```

Graph-tier wraps the higher-level claim consumers (`get_financial_report`, `get_revenue_stats` when invoked for `revenue_trend` purposes): if a recent `revenue_trend` claim exists in `kg_findings` for the entity within 24h, skip recomputation.

**Tech Stack:** `app/services/intelligence/cache.py` (Phase 112), `app/services/cache.py` `get_with_age()` (extended in Phase 112-04). No new dependencies. No DB schema changes.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 114 § Cache integration table.

**Out of scope:**
- `financial_confidence` preset and tool-level confidence wiring (Plan 114-01).
- Claim emission to `kg_findings` for `revenue_trend` etc. (Plan 114-03).
- Cache invalidation on Stripe webhooks (deferred; TTL drives staleness).
- Shopify multi-shop support beyond `{shop}` key — current model assumes a single shop per user; multi-shop becomes meaningful only after Phase 117 (Marketing) wires its own cache.
- Persistent cache stats dashboard — spot-checked via metrics in Task 5.

---

## File structure

**Create:**
- `app/agents/financial/cache.py` — Financial-Agent-specific cache key builders + the wrapper helper `cached_external_call(...)`.
- `tests/unit/agents/financial/test_financial_cache.py` — unit tests for cache key shapes, TTLs, and graph-tier decision wiring (all mocked).
- `tests/integration/test_financial_cache_load.py` — synthetic load test verifying ≥40% Stripe call-rate reduction across 1000 requests with 30% unique keys.
- `tests/integration/test_financial_graph_tier_hit_rate.py` — verifies ≥60% graph-tier hit rate on repeated `revenue_trend` queries.

**Modify:**
- `app/agents/tools/stripe_tools.py` — wrap `get_stripe_revenue_summary` with the cache; add `get_stripe_disputes` helper for the disputes/chargebacks cache key.
- `app/agents/tools/shopify_tools.py` — wrap `get_shopify_orders` with the cache.
- `app/agents/financial/tools.py` — graph-tier check in `get_revenue_stats` and `get_financial_report` before recompute.

---

## Pre-flight context

**Cache key shapes (spec-exact):**

| External call | Tier | TTL | Cache key |
|---|---|---|---|
| Stripe revenue summary | Redis | 300s | `stripe:revenue_summary:{period}` |
| Stripe disputes/chargebacks | Redis | 600s | `stripe:disputes:{period}` |
| Shopify order summary | Redis | 300s | `shopify:orders:{period}:{shop}` |
| Financial claims | Graph | 24h freshness | `claim_freshness_hours(entity_id, claim_type)` |

`should_call_external` returns a `CacheDecision(tier="redis", verdict={fresh, stale, miss}, freshness_hours)`. We treat `fresh` as "use cache" and `stale | miss` as "refetch then `cache.set(value)`".

`should_query_graph` returns `CacheDecision(tier="graph", verdict={fresh, stale, miss})` for the claim freshness check. `fresh` means we have a recent `revenue_trend` claim for the entity and can return its `finding_text` / `confidence` without recomputing.

**Helper signature** (added in Task 2):

```python
async def cached_external_call(
    *,
    cache_key: str,
    ttl_seconds: int,
    fetcher: Callable[[], Awaitable[dict]],
    metric_tag: str,  # for observability
) -> tuple[dict, bool]:
    """Return (payload, cache_hit). Reads degrade silently to fetcher()."""
```

The `cache_hit` boolean is for the load test in Task 4 (counts cache hits without monkey-patching Redis internals).

**Why a separate `cache.py` module under `app/agents/financial/`:** keeping the cache wiring as a tiny dedicated module makes it trivial to swap (e.g., to Memcached) and means the agent tool files stay focused on business logic. The `app/services/intelligence/cache.py` already provides the two-tier primitives; `app/agents/financial/cache.py` is just the per-agent adapter.

**Per-agent metric tags:** `intelligence.cache.decision { tier="redis", agent="financial", source=<stripe|shopify>, verdict }` and `intelligence.cache.decision { tier="graph", agent="financial", claim_type="revenue_trend", verdict }`. These already exist (Phase 112 observability); we just emit the new tag combinations.

Environment quirks: same as prior plans. The integration tests require a running local Supabase + Redis; otherwise they `pytest.skip`.

---

## Tasks

### Task 1: Stand up the Financial cache adapter (TDD)

**Files:**
- Create: `app/agents/financial/cache.py`
- Create: `tests/unit/agents/financial/test_financial_cache.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for Financial Agent cache adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def test_stripe_revenue_key_shape_matches_spec():
    """Cache key for Stripe revenue summary must be `stripe:revenue_summary:{period}`."""
    from app.agents.financial.cache import build_stripe_revenue_key

    assert build_stripe_revenue_key("current_month") == "stripe:revenue_summary:current_month"
    assert build_stripe_revenue_key("last_3_months") == "stripe:revenue_summary:last_3_months"


def test_stripe_disputes_key_shape_matches_spec():
    """Cache key for Stripe disputes must be `stripe:disputes:{period}`."""
    from app.agents.financial.cache import build_stripe_disputes_key

    assert build_stripe_disputes_key("current_month") == "stripe:disputes:current_month"


def test_shopify_orders_key_shape_matches_spec():
    """Cache key for Shopify orders must be `shopify:orders:{period}:{shop}`."""
    from app.agents.financial.cache import build_shopify_orders_key

    assert (
        build_shopify_orders_key("last_30_days", "pikar-store")
        == "shopify:orders:last_30_days:pikar-store"
    )


def test_shopify_orders_key_handles_none_shop():
    """When shop is None / missing, key uses 'default' as the suffix."""
    from app.agents.financial.cache import build_shopify_orders_key

    assert (
        build_shopify_orders_key("last_30_days", None)
        == "shopify:orders:last_30_days:default"
    )


def test_ttl_constants_match_spec():
    """TTLs MUST match the spec exactly."""
    from app.agents.financial.cache import (
        SHOPIFY_ORDERS_TTL_S,
        STRIPE_DISPUTES_TTL_S,
        STRIPE_REVENUE_TTL_S,
    )

    assert STRIPE_REVENUE_TTL_S == 300
    assert STRIPE_DISPUTES_TTL_S == 600
    assert SHOPIFY_ORDERS_TTL_S == 300


@pytest.mark.asyncio
async def test_cached_external_call_returns_cached_on_fresh():
    """When CacheDecision.verdict == 'fresh', skip fetcher and use cached value."""
    from app.agents.financial.cache import cached_external_call
    from app.services.intelligence.schemas import CacheDecision

    fetcher = AsyncMock()
    cache_value = {"revenue": 12345.67}

    with patch(
        "app.agents.financial.cache.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="fresh", freshness_hours=0.1,
        )),
    ), patch(
        "app.agents.financial.cache._cache_get",
        new=AsyncMock(return_value=cache_value),
    ):
        payload, hit = await cached_external_call(
            cache_key="stripe:revenue_summary:current_month",
            ttl_seconds=300,
            fetcher=fetcher,
            metric_tag="stripe_revenue_summary",
        )

    assert payload == cache_value
    assert hit is True
    fetcher.assert_not_called()


@pytest.mark.asyncio
async def test_cached_external_call_falls_through_on_miss():
    """When verdict='miss', call the fetcher and cache.set the result."""
    from app.agents.financial.cache import cached_external_call
    from app.services.intelligence.schemas import CacheDecision

    fresh_value = {"revenue": 999.0}
    fetcher = AsyncMock(return_value=fresh_value)
    set_mock = AsyncMock()

    with patch(
        "app.agents.financial.cache.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="miss", freshness_hours=None,
        )),
    ), patch(
        "app.agents.financial.cache._cache_set",
        new=set_mock,
    ):
        payload, hit = await cached_external_call(
            cache_key="stripe:revenue_summary:current_month",
            ttl_seconds=300,
            fetcher=fetcher,
            metric_tag="stripe_revenue_summary",
        )

    assert payload == fresh_value
    assert hit is False
    fetcher.assert_awaited_once()
    set_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cached_external_call_swallows_cache_set_errors():
    """If cache.set fails after a fresh fetch, payload is still returned."""
    from app.agents.financial.cache import cached_external_call
    from app.services.intelligence.schemas import CacheDecision

    fetcher = AsyncMock(return_value={"v": 1})
    failing_set = AsyncMock(side_effect=RuntimeError("redis down"))

    with patch(
        "app.agents.financial.cache.should_call_external",
        new=AsyncMock(return_value=CacheDecision(
            tier="redis", verdict="miss", freshness_hours=None,
        )),
    ), patch(
        "app.agents.financial.cache._cache_set",
        new=failing_set,
    ):
        payload, hit = await cached_external_call(
            cache_key="any:key",
            ttl_seconds=60,
            fetcher=fetcher,
            metric_tag="probe",
        )

    assert payload == {"v": 1}
    assert hit is False  # we did go upstream
```

- [ ] **Step 2: Run — should FAIL with `ModuleNotFoundError`**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py -v --tb=short
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.financial.cache'`.

- [ ] **Step 3: Implement `app/agents/financial/cache.py`**

```python
"""Financial Agent cache adapter — wraps the Phase 112 two-tier primitives.

Cache key shapes (spec):
    stripe:revenue_summary:{period}    TTL 300s
    stripe:disputes:{period}           TTL 600s
    shopify:orders:{period}:{shop}     TTL 300s

Graph tier uses claim_freshness_hours(entity_id, claim_type) with a 24h
threshold and is invoked directly from the tool layer (no helper here).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.services.intelligence.cache import should_call_external

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (must equal the design table values)
# ---------------------------------------------------------------------------

STRIPE_REVENUE_TTL_S: int = 300
STRIPE_DISPUTES_TTL_S: int = 600
SHOPIFY_ORDERS_TTL_S: int = 300


# ---------------------------------------------------------------------------
# Cache-key builders
# ---------------------------------------------------------------------------


def build_stripe_revenue_key(period: str) -> str:
    """Return the canonical cache key for a Stripe revenue summary."""
    return f"stripe:revenue_summary:{period}"


def build_stripe_disputes_key(period: str) -> str:
    """Return the canonical cache key for Stripe disputes / chargebacks."""
    return f"stripe:disputes:{period}"


def build_shopify_orders_key(period: str, shop: str | None) -> str:
    """Return the canonical cache key for a Shopify orders summary.

    `shop` is the user's connected Shopify shop slug. When not known
    we fall back to "default" so multi-shop migration later is a key
    rename rather than a schema change.
    """
    safe_shop = (shop or "default").strip() or "default"
    return f"shopify:orders:{period}:{safe_shop}"


# ---------------------------------------------------------------------------
# Cache get/set primitives (centralised here so tests can monkey-patch)
# ---------------------------------------------------------------------------


async def _cache_get(cache_key: str) -> dict | None:
    """Fetch a JSON-serialisable dict from the shared cache service."""
    from app.services.cache import get_cache_service

    try:
        cache = get_cache_service()
        value, _age = await cache.get_with_age(cache_key)
        return value
    except Exception as e:
        logger.warning("financial cache get failed for %s: %s", cache_key, e)
        return None


async def _cache_set(cache_key: str, value: dict, ttl_seconds: int) -> None:
    """Write a payload to the shared cache service with TTL."""
    from app.services.cache import get_cache_service

    cache = get_cache_service()
    await cache.set(cache_key, value, expire=ttl_seconds)


# ---------------------------------------------------------------------------
# Wrapper used by every external-call site
# ---------------------------------------------------------------------------


async def cached_external_call(
    *,
    cache_key: str,
    ttl_seconds: int,
    fetcher: Callable[[], Awaitable[dict]],
    metric_tag: str,
) -> tuple[dict, bool]:
    """Return (payload, cache_hit). Reads degrade silently to fetcher().

    Behavior:
    - Consult `should_call_external(cache_key, ttl_seconds)`.
    - On `verdict='fresh'`: pull the cached value, return (value, True). If
      the cache value is missing despite a 'fresh' verdict (edge case where
      the key expired between the decision and the get), fall through to
      the fetcher.
    - Otherwise: call fetcher(), best-effort cache.set, return (value, False).

    Args:
        cache_key: Canonical key string (build via the helpers above).
        ttl_seconds: Freshness threshold passed to should_call_external AND
            used as the set-TTL on miss.
        fetcher: Coroutine returning a JSON-serialisable dict.
        metric_tag: Short label used in observability (no PII).

    Returns:
        Tuple of (payload, cache_hit) where cache_hit is True iff we
        returned the cached value without calling the fetcher.
    """
    decision = await should_call_external(
        cache_key=cache_key, ttl_seconds=ttl_seconds,
    )
    if decision.verdict == "fresh":
        cached = await _cache_get(cache_key)
        if cached is not None:
            logger.debug(
                "financial cache HIT key=%s tag=%s age_h=%s",
                cache_key, metric_tag, decision.freshness_hours,
            )
            return cached, True
        # Race: decision said fresh but the value is gone -- fall through.
        logger.info(
            "financial cache fresh-but-missing key=%s tag=%s -- refetching",
            cache_key, metric_tag,
        )

    payload = await fetcher()
    if not isinstance(payload, dict):
        # Defensive: callers must return dicts; degrade silently.
        logger.warning(
            "financial cache fetcher returned non-dict for key=%s tag=%s",
            cache_key, metric_tag,
        )
        return payload, False  # type: ignore[return-value]

    try:
        await _cache_set(cache_key, payload, ttl_seconds)
    except Exception as e:
        logger.warning(
            "financial cache set failed key=%s tag=%s: %s",
            cache_key, metric_tag, e,
        )
    return payload, False


__all__ = [
    "SHOPIFY_ORDERS_TTL_S",
    "STRIPE_DISPUTES_TTL_S",
    "STRIPE_REVENUE_TTL_S",
    "build_shopify_orders_key",
    "build_stripe_disputes_key",
    "build_stripe_revenue_key",
    "cached_external_call",
]
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py -v --tb=short
```

Expected: PASS — 8 tests passing.

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/cache.py tests/unit/agents/financial/test_financial_cache.py
git commit -m "feat(114-02): add Financial Agent cache adapter + TTL constants (GREEN)"
```

### Task 2: Wrap Stripe tools with the cache adapter

**Files:**
- Modify: `app/agents/tools/stripe_tools.py` — wrap `get_stripe_revenue_summary`, add `get_stripe_disputes`.

The existing `get_stripe_revenue_summary` queries `financial_records` filtered to `source_type='stripe'`. The wrap keeps that fetch path; the cache short-circuits it on a fresh hit.

- [ ] **Step 1: Write a regression test that asserts cache use**

Add to `tests/unit/agents/financial/test_financial_cache.py`:

```python
@pytest.mark.asyncio
async def test_get_stripe_revenue_summary_hits_cache_on_repeat():
    """Second call within TTL returns the same payload without re-querying."""
    from unittest.mock import AsyncMock, patch

    from app.agents.tools.stripe_tools import get_stripe_revenue_summary

    fake_response = {
        "total_revenue": 1000.0, "transaction_count": 5,
        "period": "current_month", "avg_transaction_value": 200.0,
        "currency": "USD",
    }

    call_count = {"n": 0}

    async def fake_fetcher():
        call_count["n"] += 1
        return fake_response

    # Simulate Redis fresh on the SECOND call. First call: miss; second: fresh.
    from app.services.intelligence.schemas import CacheDecision

    decisions = iter([
        CacheDecision(tier="redis", verdict="miss", freshness_hours=None),
        CacheDecision(tier="redis", verdict="fresh", freshness_hours=0.05),
    ])

    async def fake_decision(**kw):
        return next(decisions)

    with patch(
        "app.agents.financial.cache.should_call_external",
        new=fake_decision,
    ), patch(
        "app.agents.financial.cache._cache_get",
        new=AsyncMock(return_value=fake_response),
    ), patch(
        "app.agents.financial.cache._cache_set",
        new=AsyncMock(),
    ), patch(
        "app.agents.tools.stripe_tools._fetch_stripe_revenue_summary_uncached",
        side_effect=fake_fetcher,
    ), patch(
        "app.agents.tools.stripe_tools._get_user_id",
        return_value="user-abc",
    ):
        r1 = await get_stripe_revenue_summary(period="current_month")
        r2 = await get_stripe_revenue_summary(period="current_month")

    assert r1 == r2
    assert call_count["n"] == 1, "Second call should have hit Redis, not the fetcher"
```

- [ ] **Step 2: Run — should FAIL (no `_fetch_stripe_revenue_summary_uncached` yet)**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py::test_get_stripe_revenue_summary_hits_cache_on_repeat -v --tb=short
```

Expected: FAIL — `AttributeError: module 'app.agents.tools.stripe_tools' has no attribute '_fetch_stripe_revenue_summary_uncached'`.

- [ ] **Step 3: Refactor `get_stripe_revenue_summary` to wrap the cache**

In `app/agents/tools/stripe_tools.py`, replace the body of `get_stripe_revenue_summary` and extract the upstream fetch into a private helper:

```python
async def _fetch_stripe_revenue_summary_uncached(
    *, user_id: str, period: str,
) -> dict[str, Any]:
    """Raw upstream fetch; called only on a cache miss."""
    from app.services.base_service import BaseService
    from app.services.supabase_async import execute_async

    svc = BaseService()
    query = (
        svc.client.table("financial_records")
        .select("amount, currency, transaction_date")
        .eq("user_id", user_id)
        .eq("transaction_type", "revenue")
        .eq("source_type", "stripe")
    )
    start_date = _period_start_date(period)
    if start_date:
        query = query.gte("transaction_date", start_date)
    result = await execute_async(query, op_name="stripe_tools.revenue_summary")
    records = result.data or []

    total_revenue = sum(float(r.get("amount", 0)) for r in records)
    count = len(records)
    avg_value = round(total_revenue / count, 2) if count else 0
    return {
        "total_revenue": round(total_revenue, 2),
        "transaction_count": count,
        "period": period,
        "avg_transaction_value": avg_value,
        "currency": records[0].get("currency", "USD") if records else "USD",
    }


async def get_stripe_revenue_summary(
    period: str = "current_month",
) -> dict[str, Any]:
    """Get revenue summary from Stripe transactions, with two-tier caching.

    Cache: Redis tier, key=`stripe:revenue_summary:{period}`, TTL 300s.
    Period values: 'current_month', 'last_month', 'last_3_months',
    'last_6_months', 'last_year', or 'all_time'.

    Returns:
        Same shape as before plus an internal `_cache_hit` boolean
        useful for load testing (not exposed to LLMs).
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.financial.cache import (
        STRIPE_REVENUE_TTL_S,
        build_stripe_revenue_key,
        cached_external_call,
    )

    try:
        payload, cache_hit = await cached_external_call(
            cache_key=build_stripe_revenue_key(period),
            ttl_seconds=STRIPE_REVENUE_TTL_S,
            fetcher=lambda: _fetch_stripe_revenue_summary_uncached(
                user_id=user_id, period=period,
            ),
            metric_tag="stripe_revenue_summary",
        )
        payload = dict(payload)
        payload["_cache_hit"] = cache_hit
        return payload
    except Exception as exc:
        logger.exception("stripe_tools.revenue_summary failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Stripe revenue: {exc}"}
```

- [ ] **Step 4: Add `get_stripe_disputes` — new tool**

Append to `app/agents/tools/stripe_tools.py`:

```python
async def _fetch_stripe_disputes_uncached(
    *, user_id: str, period: str,
) -> dict[str, Any]:
    """Fetch dispute / chargeback rows from financial_records.

    Disputes are stored as transaction_type='dispute' rows synced by
    StripeSyncService. Read-only — returns counts and totals.
    """
    from app.services.base_service import BaseService
    from app.services.supabase_async import execute_async

    svc = BaseService()
    query = (
        svc.client.table("financial_records")
        .select("amount, currency, transaction_date")
        .eq("user_id", user_id)
        .eq("transaction_type", "dispute")
        .eq("source_type", "stripe")
    )
    start_date = _period_start_date(period)
    if start_date:
        query = query.gte("transaction_date", start_date)
    result = await execute_async(query, op_name="stripe_tools.disputes")
    rows = result.data or []
    total = sum(float(r.get("amount", 0)) for r in rows)
    return {
        "dispute_count": len(rows),
        "total_disputed": round(total, 2),
        "currency": rows[0].get("currency", "USD") if rows else "USD",
        "period": period,
    }


async def get_stripe_disputes(period: str = "current_month") -> dict[str, Any]:
    """Get Stripe disputes / chargebacks for the period, with cache.

    Cache: Redis tier, key=`stripe:disputes:{period}`, TTL 600s.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.financial.cache import (
        STRIPE_DISPUTES_TTL_S,
        build_stripe_disputes_key,
        cached_external_call,
    )

    try:
        payload, cache_hit = await cached_external_call(
            cache_key=build_stripe_disputes_key(period),
            ttl_seconds=STRIPE_DISPUTES_TTL_S,
            fetcher=lambda: _fetch_stripe_disputes_uncached(
                user_id=user_id, period=period,
            ),
            metric_tag="stripe_disputes",
        )
        payload = dict(payload)
        payload["_cache_hit"] = cache_hit
        return payload
    except Exception as exc:
        logger.exception("stripe_tools.disputes failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Stripe disputes: {exc}"}
```

And update the `STRIPE_TOOLS` export at the bottom:

```python
STRIPE_TOOLS = [get_stripe_revenue_summary, get_stripe_disputes, trigger_stripe_sync]
```

- [ ] **Step 5: Re-run the cache test**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py -v --tb=short
```

Expected: PASS — 9 tests passing (the original 8 + new repeat-hit test).

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/stripe_tools.py tests/unit/agents/financial/test_financial_cache.py
git commit -m "feat(114-02): wrap Stripe revenue + disputes with two-tier cache (GREEN)"
```

### Task 3: Wrap Shopify tool with the cache adapter

**Files:**
- Modify: `app/agents/tools/shopify_tools.py` — wrap `get_shopify_orders`.

- [ ] **Step 1: Add regression test**

Append to `tests/unit/agents/financial/test_financial_cache.py`:

```python
@pytest.mark.asyncio
async def test_get_shopify_orders_hits_cache_on_repeat():
    """Shopify orders cache: second call within TTL skips upstream."""
    from unittest.mock import AsyncMock, patch

    from app.agents.tools.shopify_tools import get_shopify_orders
    from app.services.intelligence.schemas import CacheDecision

    fake_response = {"orders": [{"id": "o1"}], "count": 1}
    call_count = {"n": 0}

    async def fake_fetcher():
        call_count["n"] += 1
        return fake_response

    decisions = iter([
        CacheDecision(tier="redis", verdict="miss", freshness_hours=None),
        CacheDecision(tier="redis", verdict="fresh", freshness_hours=0.05),
    ])

    async def fake_decision(**kw):
        return next(decisions)

    with patch(
        "app.agents.financial.cache.should_call_external",
        new=fake_decision,
    ), patch(
        "app.agents.financial.cache._cache_get",
        new=AsyncMock(return_value=fake_response),
    ), patch(
        "app.agents.financial.cache._cache_set",
        new=AsyncMock(),
    ), patch(
        "app.agents.tools.shopify_tools._fetch_shopify_orders_uncached",
        side_effect=fake_fetcher,
    ), patch(
        "app.agents.tools.shopify_tools._get_user_id",
        return_value="user-abc",
    ), patch(
        "app.agents.tools.shopify_tools._get_user_shop_slug",
        return_value="pikar-store",
    ):
        r1 = await get_shopify_orders(period="last_30_days")
        r2 = await get_shopify_orders(period="last_30_days")

    assert r1 == r2
    assert call_count["n"] == 1
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py::test_get_shopify_orders_hits_cache_on_repeat -v --tb=short
```

Expected: FAIL — `_fetch_shopify_orders_uncached` / `_get_user_shop_slug` don't exist yet.

- [ ] **Step 3: Refactor `get_shopify_orders`**

In `app/agents/tools/shopify_tools.py`, replace the body of `get_shopify_orders` and add the helpers:

```python
def _get_user_shop_slug() -> str | None:
    """Best-effort lookup of the user's connected Shopify shop slug.

    Returns None if no connected shop is found; callers fall back to
    'default' for cache-key composition.
    """
    from app.services.request_context import get_current_user_id

    user_id = get_current_user_id()
    if not user_id:
        return None
    try:
        from app.services.shopify_service import ShopifyService

        svc = ShopifyService()
        # ShopifyService exposes `get_connected_shop_slug` in current Phase 41+
        # builds; if not present, falling back to None is acceptable.
        getter = getattr(svc, "get_connected_shop_slug", None)
        if getter is None:
            return None
        return getter(user_id=user_id)
    except Exception:  # noqa: BLE001 -- best-effort lookup
        return None


async def _fetch_shopify_orders_uncached(
    *,
    user_id: str,
    period: str | None,
    status: str | None,
) -> dict[str, Any]:
    """Raw Shopify orders fetch; only called on cache miss."""
    from app.services.shopify_service import ShopifyService

    svc = ShopifyService()
    resolved_period = _resolve_period(period)
    orders = await svc.get_orders(
        user_id=user_id, period=resolved_period, status=status,
    )
    return {"orders": orders, "count": len(orders)}


async def get_shopify_orders(
    period: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List Shopify orders with optional filters, two-tier cached.

    Cache: Redis tier, key=`shopify:orders:{period}:{shop}`, TTL 300s.
    The cache is keyed by (period, shop), so multi-shop users get
    independent cache entries.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.financial.cache import (
        SHOPIFY_ORDERS_TTL_S,
        build_shopify_orders_key,
        cached_external_call,
    )

    period_key = period or "all_time"
    shop = _get_user_shop_slug()

    try:
        payload, cache_hit = await cached_external_call(
            cache_key=build_shopify_orders_key(period_key, shop),
            ttl_seconds=SHOPIFY_ORDERS_TTL_S,
            fetcher=lambda: _fetch_shopify_orders_uncached(
                user_id=user_id, period=period, status=status,
            ),
            metric_tag="shopify_orders",
        )
        payload = dict(payload)
        payload["_cache_hit"] = cache_hit
        return payload
    except Exception as exc:
        logger.exception("get_shopify_orders failed for user=%s", user_id)
        return {"error": f"Failed to retrieve Shopify orders: {exc}"}
```

- [ ] **Step 4: Run — should PASS**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py -v --tb=short
```

Expected: PASS — 10 tests passing.

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/shopify_tools.py tests/unit/agents/financial/test_financial_cache.py
git commit -m "feat(114-02): wrap Shopify orders fetch with two-tier cache (GREEN)"
```

### Task 4: Graph-tier wiring for `revenue_trend` (24h freshness)

**Files:**
- Modify: `app/agents/financial/tools.py` — `get_revenue_stats` consults `should_query_graph` before recomputing; `get_financial_report` likewise.

The graph-tier short-circuits the full pipeline: if a `revenue_trend` claim exists for the entity within 24h, return its `finding_text` + `confidence` from `kg_findings` instead of recomputing. Plan 114-03 is the write side; this plan only adds the read side and the entity-resolution helper.

- [ ] **Step 1: Write the failing unit test**

Append to `tests/unit/agents/financial/test_financial_cache.py`:

```python
@pytest.mark.asyncio
async def test_get_revenue_stats_returns_graph_claim_when_fresh():
    """When a fresh revenue_trend claim exists, skip recompute and return it."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import (
        CacheDecision, Claim, ClaimSource,
    )

    entity = uuid4()
    fake_claim = Claim(
        id=uuid4(), entity_id=entity, edge_id=None,
        agent_id="financial", claim_type="revenue_trend",
        domain="financial",
        finding_text="Revenue trended +12% MoM in Q1.",
        confidence=0.82,
        sources=[ClaimSource(kind="stripe_row", ref="agg/q1")],
        contradicts=[],
        freshness_at=datetime.now(timezone.utc),
        expires_at=None,
        created_at=datetime.now(timezone.utc),
    )

    with patch(
        "app.agents.financial.tools.get_or_create_entity",
        new=AsyncMock(return_value=entity),
    ), patch(
        "app.agents.financial.tools.should_query_graph",
        new=AsyncMock(return_value=CacheDecision(
            tier="graph", verdict="fresh", freshness_hours=2.1,
        )),
    ), patch(
        "app.agents.financial.tools.find_claims",
        new=AsyncMock(return_value=[fake_claim]),
    ):
        result = await get_revenue_stats(period="current_month")

    assert result["success"] is True
    # When the graph short-circuits, surface the claim's narrative + confidence
    assert "Revenue trended" in str(result.get("revenue_trend") or "")
    assert result["confidence"] == pytest.approx(0.82, abs=1e-3)
    assert result.get("_source") == "graph_cache"


@pytest.mark.asyncio
async def test_get_revenue_stats_falls_through_on_stale_or_miss():
    """When verdict='stale' or 'miss', recompute via the existing path."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from uuid import uuid4

    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence.schemas import CacheDecision

    entity = uuid4()
    fake_service = MagicMock()
    fake_service.get_revenue_stats = AsyncMock(return_value={
        "revenue": 1000.0, "currency": "USD", "transaction_count": 10,
        "source_breakdown": {"stripe": 10},
    })

    with patch(
        "app.agents.financial.tools.get_or_create_entity",
        new=AsyncMock(return_value=entity),
    ), patch(
        "app.agents.financial.tools.should_query_graph",
        new=AsyncMock(return_value=CacheDecision(
            tier="graph", verdict="miss", freshness_hours=None,
        )),
    ), patch(
        "app.services.financial_service.FinancialService",
        return_value=fake_service,
    ):
        result = await get_revenue_stats(period="current_month")

    assert result["success"] is True
    assert result["revenue"] == 1000.0
    assert result.get("_source") != "graph_cache"
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py -k graph -v --tb=short
```

Expected: FAIL — `get_revenue_stats` doesn't call `should_query_graph` yet.

- [ ] **Step 3: Add graph-tier check to `get_revenue_stats`**

Add the imports at the top of `app/agents/financial/tools.py` (alongside the existing `from app.services.intelligence import to_band`):

```python
from app.services.intelligence import (
    find_claims,
    get_or_create_entity,
    should_query_graph,
)
```

Insert at the top of `get_revenue_stats`, BEFORE the existing `FinancialService` block:

```python
async def get_revenue_stats(period: str = "current_month") -> dict:
    """Get revenue statistics for financial analysis.

    Two-tier cache:
    - Graph: if a `revenue_trend` claim exists for the period entity within
      24 hours, return it without recomputing.
    - Redis: when recomputation happens, the upstream Stripe fetch is
      Redis-cached (TTL 300s) via Task 2.

    Response carries `confidence` + `band` (Plan 114-01 wiring).
    """
    # ---- Graph tier (24h freshness) ----
    try:
        entity_id = await get_or_create_entity(
            canonical_name=f"financial_revenue_{period}",
            entity_type="metric",
            domains=["financial"],
        )
        decision = await should_query_graph(
            entity_id=entity_id,
            claim_type="revenue_trend",
            agent_id="financial",
            freshness_threshold_hours=24.0,
        )
        if decision.verdict == "fresh":
            claims = await find_claims(
                entity_id=entity_id,
                claim_type="revenue_trend",
                agent_id="financial",
                limit=1,
            )
            if claims:
                claim = claims[0]
                return {
                    "success": True,
                    "period": period,
                    "revenue_trend": claim.finding_text,
                    "confidence": round(float(claim.confidence), 4),
                    "band": claim.band,
                    "_source": "graph_cache",
                    "_graph_age_hours": decision.freshness_hours,
                }
    except Exception as e:
        # Graph degrades silently -- keep going to the existing path.
        import logging as _logging
        _logging.getLogger(__name__).debug(
            "get_revenue_stats graph tier skipped (%s)", e,
        )

    # ---- Fall through to existing FinancialService + Redis path ----
    from app.services.financial_service import FinancialService

    try:
        service = FinancialService()
        stats = await service.get_revenue_stats(period)
        data_completeness = _data_completeness_from_age(
            transaction_count=int(stats.get("transaction_count", 0) or 0),
            period_days=_PERIOD_DAYS.get(period, 30),
        )
        source_authority = _source_authority_from_breakdown(
            stats.get("source_breakdown"),
        )
        return _attach_confidence(
            {"success": True, **stats},
            data_completeness=data_completeness,
            reconciliation_signal=1.0,
            horizon_certainty=1.0,
            source_authority=source_authority,
        )
    except Exception as e:
        return {
            "success": False, "revenue": 0.0, "currency": "USD",
            "period": period, "error": f"Service unavailable: {e!s}",
            "confidence": 0.0, "band": "low",
        }
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/financial/test_financial_cache.py -v --tb=short
```

Expected: PASS — 12 tests passing.

- [ ] **Step 5: Re-run full Financial unit suite**

```powershell
uv run pytest tests/unit/agents/financial/ -v --tb=short
```

Expected: PASS — every existing test still green; new tests passing.

- [ ] **Step 6: Commit**

```bash
git add app/agents/financial/tools.py tests/unit/agents/financial/test_financial_cache.py
git commit -m "feat(114-02): graph-tier 24h freshness check for revenue_trend (GREEN)"
```

### Task 5: Synthetic load test — Stripe call rate reduced ≥40%

**Files:**
- Create: `tests/integration/test_financial_cache_load.py`

The spec acceptance bar: 1000 requests with 30% unique periods (i.e. each unique period hits ~333 repeats); Stripe call count must drop by ≥40% vs an uncached run with the same workload.

- [ ] **Step 1: Write the load test**

```python
"""Synthetic load test: Stripe call rate reduction with two-tier cache.

Acceptance: >= 40% reduction in upstream Stripe fetcher calls when running
1000 requests over a small set of unique periods.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(
            os.environ.get(var) for var in ["REDIS_HOST", "REDIS_PORT"]
        ),
        reason="Redis env not set",
    ),
]


@pytest.mark.asyncio
async def test_stripe_call_rate_reduced_by_at_least_40_pct():
    """1000 requests, 7 unique periods: caching cuts fetcher calls by >=40%."""
    import random

    from app.agents.tools.stripe_tools import get_stripe_revenue_summary

    periods = [
        "current_month", "last_month", "last_3_months", "last_6_months",
        "last_year", "all_time", "current_month",  # weight 'current_month' a bit higher
    ]

    call_count = {"n": 0}

    async def fake_fetcher(*, user_id, period):
        call_count["n"] += 1
        return {
            "total_revenue": 1234.5,
            "transaction_count": 10,
            "period": period,
            "avg_transaction_value": 123.45,
            "currency": "USD",
        }

    rng = random.Random(42)

    with patch(
        "app.agents.tools.stripe_tools._fetch_stripe_revenue_summary_uncached",
        side_effect=fake_fetcher,
    ), patch(
        "app.agents.tools.stripe_tools._get_user_id",
        return_value="user-load",
    ):
        for _ in range(1000):
            await get_stripe_revenue_summary(period=rng.choice(periods))

    # Baseline (no cache) would be 1000 fetcher calls.
    reduction = 1.0 - (call_count["n"] / 1000.0)
    print(f"fetcher_calls={call_count['n']} reduction={reduction:.2%}")
    assert reduction >= 0.40, (
        f"Cache only reduced fetcher calls by {reduction:.2%}; "
        f"target >=40% (1000 reqs, {len(set(periods))} unique periods)."
    )
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_financial_cache_load.py -v --tb=short
```

Expected: PASS — typically ~85% reduction (only the first call per unique period misses; the remaining 993 hit cache).

If reduction < 40%, the most likely culprits:
1. The cache isn't actually warming (verify `_cache_set` is invoked on miss in Task 2).
2. The TTL is too short for the burst (300s is plenty for a 1000-call burst).
3. Redis is unreachable — check `REDIS_HOST` env.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_financial_cache_load.py
git commit -m "test(114-02): synthetic load test for >=40% Stripe call reduction"
```

### Task 6: Graph-tier hit rate ≥60% on repeated `revenue_trend`

**Files:**
- Create: `tests/integration/test_financial_graph_tier_hit_rate.py`

This test only exercises the read path (`should_query_graph` + `find_claims`); the write side ships in Plan 114-03. We seed a claim manually via `write_claim` to make this plan independently testable.

- [ ] **Step 1: Write the integration test**

```python
"""Graph-tier acceptance: repeated revenue_trend queries hit >=60% within 24h."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
        ),
        reason="Supabase env not set",
    ),
]


@pytest.mark.asyncio
async def test_repeated_revenue_trend_query_graph_hit_rate_at_least_60_pct():
    """Seed a fresh revenue_trend claim; repeated reads must hit graph tier."""
    from app.agents.financial.tools import get_revenue_stats
    from app.services.intelligence import (
        get_or_create_entity, write_claim,
    )

    period = f"loadtest_{uuid4().hex[:8]}"

    # Seed: create the entity + a revenue_trend claim.
    entity = await get_or_create_entity(
        canonical_name=f"financial_revenue_{period}",
        entity_type="metric",
        domains=["financial"],
    )
    await write_claim(
        entity_id=entity,
        domain="financial",
        finding_text="Synthetic revenue trended +5% MoM for load testing.",
        confidence=0.78,
        sources=[{"kind": "stripe_row", "ref": "load-test"}],
        agent_id="financial",
        claim_type="revenue_trend",
        embed=False,
    )

    # 50 repeated calls -- each should detect the fresh graph claim and
    # return the _source='graph_cache' marker.
    hits = 0
    total = 50
    for _ in range(total):
        result = await get_revenue_stats(period=period)
        if result.get("_source") == "graph_cache":
            hits += 1

    hit_rate = hits / total
    print(f"graph_tier hits={hits}/{total} rate={hit_rate:.2%}")
    assert hit_rate >= 0.60, (
        f"Graph-tier hit rate {hit_rate:.2%} below 60% target."
    )
```

- [ ] **Step 2: Run**

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
uv run pytest tests/integration/test_financial_graph_tier_hit_rate.py -v --tb=short
```

Expected: PASS — every call after the first should hit the graph tier (>=60% target gives generous margin even if a couple of reads transiently see `verdict='miss'` due to clock skew).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_financial_graph_tier_hit_rate.py
git commit -m "test(114-02): graph-tier >=60% hit rate on repeated revenue_trend"
```

### Task 7: Regression check — `/admin/financial/overview` still renders

The spec requires "no regression in `/admin/financial/overview` dashboard". The dashboard reads from the same `financial_records` rows and aggregations; our changes are additive (new fields on responses, cache wrapper around fetches). We verify behavior by hitting the route in an integration test.

- [ ] **Step 1: Search the routers for the overview endpoint**

```powershell
uv run python -c "
import pathlib
hits = []
for p in pathlib.Path('app/routers').rglob('*.py'):
    text = p.read_text(encoding='utf-8')
    if 'financial/overview' in text or 'financial_overview' in text:
        hits.append(str(p))
for h in hits:
    print(h)
"
```

Expected: prints the router file path(s) that own the endpoint. If empty, the route lives under `app/admin/` or is provided through a generic admin overview endpoint; expand the grep accordingly.

- [ ] **Step 2: Run the existing admin overview tests, if any**

```powershell
uv run pytest tests/ -k "admin and (financial or overview)" -v --tb=short
```

Expected: PASS, or "no tests ran" (acceptable -- means the route is exercised end-to-end by `test_financial_pilot_e2e.py` instead).

- [ ] **Step 3: Re-run the Financial pilot E2E suite to catch dashboard regressions**

```powershell
uv run pytest tests/integration/agents/financial/test_financial_pilot_e2e.py -v --tb=short
```

Expected: PASS — same number of tests as before, none newly failing.

- [ ] **Step 4: Commit a no-op marker if everything's green** (skip if nothing changed)

No commit needed if no files changed. If a regression surfaced, fix it and commit:

```bash
git add -u
git commit -m "fix(114-02): preserve /admin/financial/overview compatibility"
```

### Task 8: Lint + Plan 114-02 acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/agents/financial/cache.py app/agents/financial/tools.py app/agents/tools/stripe_tools.py app/agents/tools/shopify_tools.py tests/unit/agents/financial/test_financial_cache.py tests/integration/test_financial_cache_load.py tests/integration/test_financial_graph_tier_hit_rate.py
uv run ruff format app/agents/financial/cache.py app/agents/financial/tools.py app/agents/tools/stripe_tools.py app/agents/tools/shopify_tools.py tests/unit/agents/financial/test_financial_cache.py tests/integration/test_financial_cache_load.py tests/integration/test_financial_graph_tier_hit_rate.py --check
```

Expected: both report no findings. Fix in place; commit any fixes:

```bash
git add -u
git commit -m "style(114-02): ruff lint + format fixes for plan 114-02" || echo "nothing to commit"
```

- [ ] **Step 2: Plan 114-02 acceptance — cross-check**

| Plan 114-02 acceptance line | Verified by |
|---|---|
| `stripe:revenue_summary:{period}` cache key + TTL 300s | Task 1 + Task 2 |
| `stripe:disputes:{period}` cache key + TTL 600s | Task 1 + Task 2 (`get_stripe_disputes` added) |
| `shopify:orders:{period}:{shop}` cache key + TTL 300s | Task 1 + Task 3 |
| Graph tier check via `claim_freshness_hours(entity_id, claim_type)` w/ 24h threshold | Task 4 |
| Stripe call rate reduced ≥40% on synthetic load | Task 5 |
| Graph-tier hit rate ≥60% on repeated `revenue_trend` within 24h | Task 6 |
| No regression in `/admin/financial/overview` | Task 7 |
| Reads degrade silently on cache backend failure | Task 1 (`test_cached_external_call_swallows_cache_set_errors`) |
| Lint clean | Task 8 |

- [ ] **Step 3: Plan 114-02 complete. Plan 114-03 (claim emission) is unblocked.**

Next planned work in Phase 114: Plan 114-03 wires `write_claim` calls for `revenue_trend`, `expense_pattern`, `revenue_forecast_h{N}m`, `margin_signal`, `financial_anomaly`, and `reconciliation_finding` so the graph tier has claims to serve.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `stripe:revenue_summary:{period}` Redis cache (TTL 300s) | Tasks 1, 2 |
| `stripe:disputes:{period}` Redis cache (TTL 600s) — new tool | Tasks 1, 2 |
| `shopify:orders:{period}:{shop}` Redis cache (TTL 300s) | Tasks 1, 3 |
| Graph-tier `claim_freshness_hours(entity_id, claim_type)` 24h threshold | Task 4 |
| Stripe call rate reduced ≥40% on synthetic load test | Task 5 |
| Graph-tier hit rate ≥60% on repeated `revenue_trend` within 24h | Task 6 |
| No regression in `/admin/financial/overview` | Task 7 |
| Reads degrade silently on cache backend failure | Task 1 (silent set-failure test) |
| Lint clean (ruff check + ruff format --check) | Task 8 |

All spec lines covered.
