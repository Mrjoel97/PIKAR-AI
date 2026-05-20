# Shared Intelligence Infrastructure — Plan 115-02: Sales HubSpot Cache Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Phase 112 two-tier adaptive cache (`should_call_external` → Redis-tier; `should_query_graph` → graph-tier) around the HubSpot read paths the Sales Agent uses (`search_hubspot_contacts`, `get_hubspot_deal_context`, `list_hubspot_deals`, `query_hubspot_crm`). Reduce HubSpot API call rate ≥40% on synthetic repeat load. Graph-tier (`kg_findings` freshness) becomes the long-lived cache for `pipeline_health` / `deal_stage_signal` claims after Plan 115-03 lands; this plan ships only the Redis tier and the graph-tier scaffolding (the claims themselves arrive in 115-03).

**Architecture:** Per spec Phase 115 cache table:

| HubSpot resource | Tier | TTL | Cache key |
|---|---|---|---|
| Contact | Redis | 300s (5 min) | `hubspot:contact:{contact_id}` |
| Deal | Redis | 300s | `hubspot:deal:{deal_id}` |
| Pipeline (set of stages) | Redis | 600s (10 min) | `hubspot:pipeline:{pipeline_id}` |
| Deal context (contact + associated deals) | Redis | 300s | `hubspot:deal_context:{contact_key}` |
| `pipeline_health` claim (set after 115-03) | Graph | 24h freshness | `claim_freshness_hours(entity_id, claim_type="pipeline_health")` |
| `deal_stage_signal` claim | Graph | 24h freshness | same shape |

Cache integration is a *wrapper* pattern: existing `HubSpotService` calls stay intact; we add a thin caching layer in the agent tools (`app/agents/tools/hubspot_tools.py`) that consults Redis first, falls through to the existing call on miss, then writes the result back with TTL. On Redis failure, the wrapper short-circuits to the live call (matches existing circuit-breaker behavior in `app/services/cache.py`).

**Tech Stack:** `app/services/intelligence/cache.py` (existing `should_call_external` / `should_query_graph`), `app/services/cache.py` (`get_cache_service` for the underlying Redis client with `get_generic` / `set_generic`), `app/agents/tools/hubspot_tools.py` (read-path wrappers).

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 115 — Cache (HubSpot resource TTLs).

**Out of scope:** Write-path cache invalidation for `update_hubspot_deal` / `create_hubspot_contact` / `sync_deal_notes` (those are write-through to HubSpot — we don't pre-cache writes). Claim emission of `lead_score` / `deal_stage_signal` / `pipeline_health` claims (Plan 115-03). Graph-tier population — that's a side effect of 115-03 once claims start landing in `kg_findings`. This plan ships the Redis tier + a thin graph-tier consult that returns "miss" until claims exist.

---

## File structure

**Create:**
- `app/agents/tools/hubspot_cache.py` — wrapper helpers `get_cached_contact`, `get_cached_deal`, `get_cached_pipeline`, `get_cached_deal_context`
- `tests/unit/agents/tools/test_hubspot_cache.py` — unit tests with Redis mocked
- `tests/integration/test_hubspot_cache_load.py` — synthetic load test (≥40% API reduction)

**Modify:**
- `app/agents/tools/hubspot_tools.py` — route `search_hubspot_contacts` / `get_hubspot_deal_context` / `list_hubspot_deals` reads through the cache layer

---

## Pre-flight context

`should_call_external` (existing) signature:

```python
async def should_call_external(
    *,
    cache_key: str,
    ttl_seconds: int,
) -> CacheDecision
```

Returns `CacheDecision(tier="redis", verdict="fresh" | "stale" | "miss", freshness_hours: float | None)`.

This *only checks* — it doesn't fetch or populate. The caller is responsible for:
1. Calling `should_call_external` with the chosen key + TTL.
2. If `verdict == "fresh"`, call `get_cache_service().get_generic(key)` and use the value.
3. If `verdict == "miss"` or `verdict == "stale"`, do the live HubSpot call, then `get_cache_service().set_generic(key, value, ttl=ttl_seconds)`.

We codify this dance once in `hubspot_cache.py` so the tool functions stay clean.

**Why a separate wrapper module (not extending `hubspot_tools.py` directly):**

`hubspot_tools.py` already imports `HubSpotService` at module level. Adding inline caching would tangle the cache decision with the call. A standalone `hubspot_cache.py` module:
- Keeps `hubspot_tools.py` thin (it just calls the wrapper).
- Makes the cache surface independently testable.
- Aligns with Phase 113's pattern (`app/agents/data/cache.py` for the Data Agent's Stripe/Shopify wrappers).

**Cache key design — collision avoidance:**

`hubspot:contact:{contact_id}` — `contact_id` is the Pikar `contacts.id` UUID, NOT the HubSpot ID. Reason: callers identify contacts by Pikar ID after the first sync; HubSpot IDs aren't always known upfront.

`hubspot:deal_context:{contact_key}` — `contact_key = sha1(f"{user_id}:{lead_name}:{company}")` because `get_hubspot_deal_context` accepts a free-text lookup (name, email, OR UUID). The hashed key avoids leaking PII to Redis keys and stays bounded.

`hubspot:deal:{deal_id}` — Pikar `hubspot_deals.id` UUID.

`hubspot:pipeline:{pipeline_id}` — HubSpot pipeline name (e.g., `default`, `enterprise`). Pipelines are rarely user-specific; OK to share across users.

**TTL rationale:**

| Resource | TTL | Rationale |
|---|---|---|
| Contact | 300s | Contacts change daily — 5-min cache balances freshness vs. burst load. |
| Deal | 300s | Stage transitions matter; 5 min is short enough to catch same-session updates. |
| Pipeline | 600s | Pipeline structure is stable for hours/days; 10 min is conservative. |
| Deal context | 300s | Aggregates contact + deals — short to track recent context. |

**Circuit-breaker degradation:**

The existing `CacheService.get_generic` / `set_generic` already wraps Redis in a circuit breaker (`app/services/cache.py`). When Redis is unhealthy, both return `None` / `False` silently. Our wrapper treats `None` as a miss and proceeds to live fetch — no extra code needed.

**Decision-relevant memory:**

Per memory `reference_local_dev_env_quirks`: local Redis is at `redis://default:pikar_dev_redis@localhost:6379/0`. Tests that mock Redis don't need that, but the synthetic load test in Task 4 does.

Acceptance bar (from spec):
- ≥40% HubSpot API call reduction on synthetic load test (Task 4)
- Unit tests cover hit / miss / Redis-down paths
- No regression in existing `hubspot_tools.py` test suite

Environment quirks: Windows + uv + PowerShell. Tests via `uv run pytest`.

---

## Tasks

### Task 1: Pre-flight + scaffolding

**Files:**
- Create: `app/agents/tools/hubspot_cache.py` (empty scaffolding for now — populated in Task 2)

- [ ] **Step 1: Confirm prerequisites**

```powershell
uv run python -c "from app.services.intelligence import should_call_external, should_query_graph; print('cache OK')"
uv run python -c "from app.services.cache import get_cache_service; svc = get_cache_service(); print('redis OK', type(svc).__name__)"
uv run python -c "from app.agents.tools.hubspot_tools import HUBSPOT_TOOLS; print('hubspot tools count:', len(HUBSPOT_TOOLS))"
```

Expected: `cache OK`, `redis OK CacheService`, `hubspot tools count: 8`.

If `get_cache_service` raises about Redis connection, that's expected without the local Redis stack — unit tests in Task 2 mock the service. The integration test in Task 4 needs Redis running.

- [ ] **Step 2: Create the scaffold**

```python
# app/agents/tools/hubspot_cache.py
"""Cache wrappers for HubSpot read paths used by the Sales Agent.

Phase 115-02 — adds the Redis tier of the two-tier adaptive cache around
HubSpotService read methods so repeated reads inside a session don't hit
the HubSpot API every time. The graph tier (kg_findings) auto-populates
once Plan 115-03 ships claim emission.

Public surface:
- get_cached_contact     — cached contact lookup by Pikar contact_id
- get_cached_deal        — cached deal lookup by Pikar deal_id
- get_cached_pipeline    — cached pipeline structure by pipeline_id
- get_cached_deal_context — cached deal-context summary by free-text key
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Commit the scaffold**

```bash
git add app/agents/tools/hubspot_cache.py
git commit -m "feat(115-02): scaffold hubspot_cache module"
```

### Task 2: Implement the cache wrappers (TDD)

**Files:**
- Modify: `app/agents/tools/hubspot_cache.py`
- Create: `tests/unit/agents/tools/test_hubspot_cache.py`

- [ ] **Step 1: Failing unit tests**

```python
"""Unit tests for hubspot_cache wrappers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.intelligence.schemas import CacheDecision


def _make_decision(verdict: str, age_hours: float | None = None) -> CacheDecision:
    return CacheDecision(tier="redis", verdict=verdict, freshness_hours=age_hours)


@pytest.mark.asyncio
async def test_get_cached_contact_hit_returns_cached_value():
    """Fresh Redis hit returns cached value without calling the loader."""
    from app.agents.tools.hubspot_cache import get_cached_contact

    loader = AsyncMock(return_value={"id": "c1", "name": "Fresh Live Value"})
    cached_payload = {"id": "c1", "name": "Cached Value"}

    cache_svc = MagicMock()
    cache_svc.get_generic = AsyncMock(return_value=MagicMock(value=cached_payload))
    cache_svc.set_generic = AsyncMock(return_value=True)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_make_decision("fresh", 0.01)),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ):
        result = await get_cached_contact(contact_id="c1", loader=loader)

    assert result == cached_payload
    loader.assert_not_called()
    cache_svc.set_generic.assert_not_called()


@pytest.mark.asyncio
async def test_get_cached_contact_miss_calls_loader_and_sets():
    """Cache miss calls the loader and writes the result back."""
    from app.agents.tools.hubspot_cache import get_cached_contact

    live_value = {"id": "c1", "name": "Live Value"}
    loader = AsyncMock(return_value=live_value)

    cache_svc = MagicMock()
    cache_svc.get_generic = AsyncMock(return_value=MagicMock(value=None))
    cache_svc.set_generic = AsyncMock(return_value=True)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_make_decision("miss")),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ):
        result = await get_cached_contact(contact_id="c1", loader=loader)

    assert result == live_value
    loader.assert_awaited_once()
    cache_svc.set_generic.assert_awaited_once()
    # Verify TTL passed to set is the 300s default
    args, kwargs = cache_svc.set_generic.call_args
    assert kwargs.get("ttl") == 300 or (len(args) >= 3 and args[2] == 300)


@pytest.mark.asyncio
async def test_get_cached_contact_stale_refreshes():
    """Stale verdict triggers a refresh — same flow as miss."""
    from app.agents.tools.hubspot_cache import get_cached_contact

    loader = AsyncMock(return_value={"id": "c1", "name": "Refreshed"})

    cache_svc = MagicMock()
    cache_svc.get_generic = AsyncMock(return_value=MagicMock(value={"stale": True}))
    cache_svc.set_generic = AsyncMock(return_value=True)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_make_decision("stale", 0.5)),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ):
        result = await get_cached_contact(contact_id="c1", loader=loader)

    assert result == {"id": "c1", "name": "Refreshed"}
    loader.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cached_contact_redis_down_degrades_to_live():
    """Redis error → fall through to loader, don't crash."""
    from app.agents.tools.hubspot_cache import get_cached_contact

    loader = AsyncMock(return_value={"id": "c1", "name": "Live"})

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_make_decision("miss")),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        side_effect=RuntimeError("redis down"),
    ):
        result = await get_cached_contact(contact_id="c1", loader=loader)

    assert result == {"id": "c1", "name": "Live"}
    loader.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cached_deal_uses_deal_key():
    """Deal wrapper uses the hubspot:deal:{id} key shape."""
    from app.agents.tools.hubspot_cache import get_cached_deal

    captured_key = {}

    async def fake_should(*, cache_key, ttl_seconds):
        captured_key["key"] = cache_key
        captured_key["ttl"] = ttl_seconds
        return _make_decision("miss")

    loader = AsyncMock(return_value={"id": "d1"})

    cache_svc = MagicMock()
    cache_svc.set_generic = AsyncMock(return_value=True)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        side_effect=fake_should,
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ):
        await get_cached_deal(deal_id="d1", loader=loader)

    assert captured_key["key"] == "hubspot:deal:d1"
    assert captured_key["ttl"] == 300


@pytest.mark.asyncio
async def test_get_cached_pipeline_uses_pipeline_key_and_longer_ttl():
    """Pipeline wrapper uses 600s TTL and pipeline-id key shape."""
    from app.agents.tools.hubspot_cache import get_cached_pipeline

    captured = {}

    async def fake_should(*, cache_key, ttl_seconds):
        captured["key"] = cache_key
        captured["ttl"] = ttl_seconds
        return _make_decision("miss")

    cache_svc = MagicMock()
    cache_svc.set_generic = AsyncMock(return_value=True)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        side_effect=fake_should,
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ):
        await get_cached_pipeline(
            pipeline_id="default", loader=AsyncMock(return_value={"stages": []})
        )

    assert captured["key"] == "hubspot:pipeline:default"
    assert captured["ttl"] == 600


@pytest.mark.asyncio
async def test_get_cached_deal_context_hashes_freetext_key():
    """Deal context key is sha1(user_id + lead + company) — bounded length."""
    from app.agents.tools.hubspot_cache import get_cached_deal_context

    captured = {}

    async def fake_should(*, cache_key, ttl_seconds):
        captured["key"] = cache_key
        return _make_decision("miss")

    cache_svc = MagicMock()
    cache_svc.set_generic = AsyncMock(return_value=True)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        side_effect=fake_should,
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ):
        await get_cached_deal_context(
            user_id="u1",
            lookup_query="John Smith @ Acme",
            loader=AsyncMock(return_value={"contact": {}, "deals": []}),
        )

    assert captured["key"].startswith("hubspot:deal_context:")
    # SHA1 hex (40 chars) appended
    assert len(captured["key"]) == len("hubspot:deal_context:") + 40
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/tools/test_hubspot_cache.py -v --tb=short
```

- [ ] **Step 3: Implement `hubspot_cache.py`**

```python
"""Cache wrappers for HubSpot read paths used by the Sales Agent.

Phase 115-02 — adds the Redis tier of the two-tier adaptive cache around
HubSpotService read methods so repeated reads inside a session don't hit
the HubSpot API every time. The graph tier (kg_findings) auto-populates
once Plan 115-03 ships claim emission.

Public surface:
- get_cached_contact     — cached contact lookup by Pikar contact_id
- get_cached_deal        — cached deal lookup by Pikar deal_id
- get_cached_pipeline    — cached pipeline structure by pipeline_id
- get_cached_deal_context — cached deal-context summary by free-text key

Each wrapper takes an async ``loader`` callable that performs the live
HubSpot fetch on cache miss. The wrapper consults ``should_call_external``,
returns the cached value on fresh, or calls the loader + writes back on
miss/stale.

Redis or circuit-breaker failure: silently degrades to the live loader.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Awaitable, Callable

from app.services.cache import get_cache_service
from app.services.intelligence import should_call_external

logger = logging.getLogger(__name__)


_TTL_CONTACT = 300
_TTL_DEAL = 300
_TTL_PIPELINE = 600
_TTL_DEAL_CONTEXT = 300


async def _cached_or_fetch(
    *,
    cache_key: str,
    ttl_seconds: int,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Generic cache-aside helper.

    Consults should_call_external for tier-decision-and-age, returns cached
    value on fresh, otherwise calls the loader and writes back with TTL.
    Failures in the cache layer fall through to the live loader.
    """
    decision = await should_call_external(
        cache_key=cache_key, ttl_seconds=ttl_seconds,
    )

    if decision.verdict == "fresh":
        try:
            svc = get_cache_service()
            cached = await svc.get_generic(cache_key)
            value = getattr(cached, "value", None) if cached is not None else None
            if value is not None:
                logger.debug("hubspot_cache HIT key=%s age=%s", cache_key, decision.freshness_hours)
                return value
            # Decision said fresh but value gone — race, fall through
        except Exception as exc:
            logger.warning("hubspot_cache get failed key=%s: %s", cache_key, exc)

    # miss / stale / fresh-but-gone — call live loader
    value = await loader()

    # Write back, best-effort
    try:
        svc = get_cache_service()
        await svc.set_generic(cache_key, value, ttl=ttl_seconds)
        logger.debug("hubspot_cache MISS->SET key=%s ttl=%s", cache_key, ttl_seconds)
    except Exception as exc:
        logger.warning("hubspot_cache set failed key=%s: %s", cache_key, exc)

    return value


async def get_cached_contact(
    *,
    contact_id: str,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Return a HubSpot contact dict, cached for 5 min by Pikar contact_id."""
    return await _cached_or_fetch(
        cache_key=f"hubspot:contact:{contact_id}",
        ttl_seconds=_TTL_CONTACT,
        loader=loader,
    )


async def get_cached_deal(
    *,
    deal_id: str,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Return a HubSpot deal dict, cached for 5 min by Pikar deal_id."""
    return await _cached_or_fetch(
        cache_key=f"hubspot:deal:{deal_id}",
        ttl_seconds=_TTL_DEAL,
        loader=loader,
    )


async def get_cached_pipeline(
    *,
    pipeline_id: str,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Return a HubSpot pipeline structure, cached for 10 min."""
    return await _cached_or_fetch(
        cache_key=f"hubspot:pipeline:{pipeline_id}",
        ttl_seconds=_TTL_PIPELINE,
        loader=loader,
    )


async def get_cached_deal_context(
    *,
    user_id: str,
    lookup_query: str,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Return a deal-context summary, cached for 5 min by hashed query.

    The lookup_query is free-text (name, email, or UUID), so we hash it
    along with user_id to produce a bounded, PII-safe Redis key.
    """
    key_material = f"{user_id}:{lookup_query}".encode("utf-8")
    digest = hashlib.sha1(key_material, usedforsecurity=False).hexdigest()
    return await _cached_or_fetch(
        cache_key=f"hubspot:deal_context:{digest}",
        ttl_seconds=_TTL_DEAL_CONTEXT,
        loader=loader,
    )
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/tools/test_hubspot_cache.py -v --tb=short
```

Expected output snippet:

```
test_get_cached_contact_hit_returns_cached_value PASSED
test_get_cached_contact_miss_calls_loader_and_sets PASSED
test_get_cached_contact_stale_refreshes PASSED
test_get_cached_contact_redis_down_degrades_to_live PASSED
test_get_cached_deal_uses_deal_key PASSED
test_get_cached_pipeline_uses_pipeline_key_and_longer_ttl PASSED
test_get_cached_deal_context_hashes_freetext_key PASSED
======== 7 passed in 0.XXs ========
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/hubspot_cache.py tests/unit/agents/tools/test_hubspot_cache.py
git commit -m "feat(115-02): hubspot_cache wrappers with Redis-tier should_call_external (GREEN)"
```

### Task 3: Route `hubspot_tools` read paths through the cache

**Files:**
- Modify: `app/agents/tools/hubspot_tools.py`
- Create: `tests/unit/agents/tools/test_hubspot_tools_cached.py`

The read paths we wrap:
1. `get_hubspot_deal_context` → cached by `get_cached_deal_context`
2. `list_hubspot_deals` (no filters) → cached by `get_cached_deal` per-deal-id is not a fit; instead cache the *list* under a per-user key. We use `hubspot:deals_list:{user_id}:{pipeline_or_all}:{stage_or_all}`.
3. `search_hubspot_contacts` → cached by `hubspot:contacts_search:{user_id}:{sha1(query)}` (300s).
4. `query_hubspot_crm` → similar key shape.

For the list endpoints, the key includes the filter args so different filters get distinct cache entries.

- [ ] **Step 1: Failing tests for cached read paths**

```python
"""Tests that hubspot_tools read paths consult the cache layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.intelligence.schemas import CacheDecision


def _fresh() -> CacheDecision:
    return CacheDecision(tier="redis", verdict="fresh", freshness_hours=0.01)


def _miss() -> CacheDecision:
    return CacheDecision(tier="redis", verdict="miss", freshness_hours=None)


@pytest.mark.asyncio
async def test_get_hubspot_deal_context_cache_hit_skips_live():
    """On Redis hit, the live HubSpotService.get_deal_context is NOT called."""
    from app.agents.tools import hubspot_tools

    cached = {
        "contact": {"id": "c1", "name": "Cached"},
        "deals": [{"id": "d1", "stage": "qualified"}],
        "summary": "from cache",
    }
    cache_svc = MagicMock()
    cache_svc.get_generic = AsyncMock(return_value=MagicMock(value=cached))
    cache_svc.set_generic = AsyncMock(return_value=True)

    live_svc = MagicMock()
    live_svc.get_deal_context = AsyncMock(return_value={"summary": "from LIVE"})

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_fresh()),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ), patch(
        "app.agents.tools.hubspot_tools.HubSpotService",
        return_value=live_svc,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ):
        result = await hubspot_tools.get_hubspot_deal_context("Jane @ Acme")

    assert result == cached
    live_svc.get_deal_context.assert_not_called()


@pytest.mark.asyncio
async def test_get_hubspot_deal_context_cache_miss_calls_live_and_sets():
    """On Redis miss, the live call happens and the result is cached."""
    from app.agents.tools import hubspot_tools

    live_value = {"contact": {"id": "c1"}, "deals": [], "summary": "fresh"}
    cache_svc = MagicMock()
    cache_svc.get_generic = AsyncMock(return_value=None)
    cache_svc.set_generic = AsyncMock(return_value=True)

    live_svc = MagicMock()
    live_svc.get_deal_context = AsyncMock(return_value=live_value)

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_miss()),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ), patch(
        "app.agents.tools.hubspot_tools.HubSpotService",
        return_value=live_svc,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ):
        result = await hubspot_tools.get_hubspot_deal_context("Jane @ Acme")

    assert result == live_value
    live_svc.get_deal_context.assert_awaited_once_with("user-1", "Jane @ Acme")
    cache_svc.set_generic.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_hubspot_deal_context_error_response_not_cached():
    """If the live call returns an {error: ...} dict, do NOT cache."""
    from app.agents.tools import hubspot_tools

    cache_svc = MagicMock()
    cache_svc.get_generic = AsyncMock(return_value=None)
    cache_svc.set_generic = AsyncMock(return_value=True)

    live_svc = MagicMock()
    live_svc.get_deal_context = AsyncMock(side_effect=RuntimeError("HS down"))

    with patch(
        "app.agents.tools.hubspot_cache.should_call_external",
        new=AsyncMock(return_value=_miss()),
    ), patch(
        "app.agents.tools.hubspot_cache.get_cache_service",
        return_value=cache_svc,
    ), patch(
        "app.agents.tools.hubspot_tools.HubSpotService",
        return_value=live_svc,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="user-1",
    ):
        result = await hubspot_tools.get_hubspot_deal_context("Jane @ Acme")

    assert "error" in result
    # The wrapper should NOT pre-cache an error response — otherwise transient
    # failures pin to the cache for 5 minutes.
    cache_svc.set_generic.assert_not_called()
```

- [ ] **Step 2: Run — should FAIL until the integration lands**

```powershell
uv run pytest tests/unit/agents/tools/test_hubspot_tools_cached.py -v --tb=short
```

- [ ] **Step 3: Modify `get_hubspot_deal_context` to route through the cache**

Replace the existing function body with the cached version. The change:
1. Pull `user_id` upfront (unchanged).
2. Build a loader that calls the live `HubSpotService.get_deal_context`.
3. Hand off to `get_cached_deal_context`.
4. Don't cache responses that contain an `error` key.

```python
async def get_hubspot_deal_context(
    contact_name_or_id: str,
) -> dict[str, Any]:
    """Get HubSpot deal pipeline context for a contact (cache-aware).

    Phase 115-02: results are cached in Redis (5-min TTL) keyed by
    sha1(user_id + lookup) so repeated lookups inside a session don't
    re-hit HubSpot.

    Use this BEFORE answering any sales query about a specific contact
    or company to provide CRM-aware responses. Returns the contact
    record, associated deals with stage/amount/pipeline, and a
    human-readable summary.

    Args:
        contact_name_or_id: Contact name, email, or UUID to look up.

    Returns:
        Dict with contact, deals, and summary keys.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.tools.hubspot_cache import get_cached_deal_context
    from app.services.hubspot_service import HubSpotService

    async def _live_loader() -> dict[str, Any]:
        try:
            svc = HubSpotService()
            return await svc.get_deal_context(user_id, contact_name_or_id)
        except Exception as exc:
            logger.exception("get_hubspot_deal_context failed for user=%s", user_id)
            return {"error": f"Failed to get deal context: {exc}"}

    result = await get_cached_deal_context(
        user_id=user_id,
        lookup_query=contact_name_or_id,
        loader=_live_loader,
    )

    # Negative-cache prevention: if the loader returned an error response,
    # invalidate so a retry next call doesn't get the cached error.
    if isinstance(result, dict) and "error" in result:
        try:
            from app.services.cache import get_cache_service

            import hashlib as _h

            key_material = f"{user_id}:{contact_name_or_id}".encode("utf-8")
            digest = _h.sha1(key_material, usedforsecurity=False).hexdigest()
            await get_cache_service().delete(f"hubspot:deal_context:{digest}")
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass

    return result
```

The error-purge path needs `CacheService.delete` — if that doesn't exist (it does as of Phase 112), wrap the `await get_cache_service().delete(...)` call in `getattr(..., 'delete', None)` and skip if absent. Refer to `app/services/cache.py` for the actual method name (often `forget` or `invalidate`). The unit test only asserts `set_generic` is NOT called for the error case, not that delete IS called — so the negative-cache cleanup is best-effort.

- [ ] **Step 4: Re-run the cached-path tests**

```powershell
uv run pytest tests/unit/agents/tools/test_hubspot_tools_cached.py -v --tb=short
```

Expected: 3 passed.

- [ ] **Step 5: Run the original hubspot_tools test suite for regression**

```powershell
uv run pytest tests/unit/agents/tools/ -v -k hubspot --tb=short
```

Expected: all existing tests + new cached-path tests pass. If any existing test that mocks `HubSpotService.get_deal_context` now fails because the patch is short-circuited by the cache, fix it by also patching `app.agents.tools.hubspot_cache.should_call_external` to return `miss`. The fix is mechanical — add the second patch alongside the existing one.

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/hubspot_tools.py tests/unit/agents/tools/test_hubspot_tools_cached.py
git commit -m "feat(115-02): route get_hubspot_deal_context through Redis cache (GREEN)"
```

### Task 4: Synthetic load test — verify ≥40% API call reduction

**Files:**
- Create: `tests/integration/test_hubspot_cache_load.py`

The spec's hard acceptance: HubSpot API call rate reduced ≥40% on synthetic load. Test design: simulate 100 lookups against 20 distinct contacts (each contact looked up 5 times). With a 300s TTL, the second through fifth lookup of each contact should hit the cache. Naive expected reduction: 80 of 100 calls become cache hits = 80% reduction.

We mock the `HubSpotService.get_deal_context` so the test doesn't actually call HubSpot; we just count invocations.

- [ ] **Step 1: Write the load test**

```python
"""Synthetic load test for Phase 115-02 HubSpot cache.

Simulates 100 lookups across 20 distinct contacts with repeat probability
80% (each contact looked up 5 times). Asserts ≥40% reduction in live
HubSpotService.get_deal_context invocations vs. baseline (no cache).
"""

from __future__ import annotations

import os
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("REDIS_HOST"),
        reason="REDIS_HOST not set — load test requires live Redis",
    ),
]


@pytest.mark.asyncio
async def test_get_hubspot_deal_context_load_reduces_calls_by_at_least_40_pct():
    """100 lookups, 20 distinct contacts, ≥40% reduction in live calls."""
    from app.agents.tools import hubspot_tools

    # Distinct contacts; ~80% repeats by random choice
    contacts = [f"contact-{i}" for i in range(20)]
    random.seed(115)
    lookup_seq = [random.choice(contacts) for _ in range(100)]

    call_counter = {"count": 0}

    async def fake_get_deal_context(user_id, query):
        call_counter["count"] += 1
        return {
            "contact": {"id": f"hs-{query}", "name": query},
            "deals": [],
            "summary": "fake live",
        }

    live_svc = MagicMock()
    live_svc.get_deal_context = AsyncMock(side_effect=fake_get_deal_context)

    with patch(
        "app.agents.tools.hubspot_tools.HubSpotService",
        return_value=live_svc,
    ), patch(
        "app.agents.tools.hubspot_tools._get_user_id",
        return_value="load-test-user",
    ):
        for lookup in lookup_seq:
            await hubspot_tools.get_hubspot_deal_context(lookup)

    distinct = len(set(lookup_seq))
    live_calls = call_counter["count"]
    total_calls = len(lookup_seq)
    reduction_pct = (total_calls - live_calls) / total_calls

    print(
        f"distinct={distinct} live_calls={live_calls} total={total_calls} "
        f"reduction={reduction_pct:.0%}"
    )

    # The acceptance bar is ≥40%. With 20 distinct of 100 lookups, the
    # *theoretical* minimum live calls = 20 → 80% reduction. We assert ≥40%
    # to leave headroom for Redis hiccups / TTL boundary effects.
    assert reduction_pct >= 0.40, (
        f"Cache reduced only {reduction_pct:.0%} of calls (<40% threshold)"
    )
```

- [ ] **Step 2: Ensure Redis is running and run**

```powershell
docker ps --filter "name=redis"  # confirm pikar redis container is up
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:REDIS_PASSWORD = "pikar_dev_redis"
uv run pytest tests/integration/test_hubspot_cache_load.py -v -s
```

Expected output snippet:

```
distinct=20 live_calls=20 reduction=80%
test_get_hubspot_deal_context_load_reduces_calls_by_at_least_40_pct PASSED
```

If reduction is below 40%, investigate:
1. Is Redis actually being written to? Run `redis-cli -a pikar_dev_redis KEYS "hubspot:*"` after the test — should show ~20 keys.
2. Are the cache keys sensitive to a hidden var? Add `print(captured_key)` in a debug variant.
3. Is `should_call_external` returning `miss` always due to a Redis-side circuit-breaker trip? Check `/health/cache` — circuit-breaker state should be `closed`.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_hubspot_cache_load.py
git commit -m "test(115-02): synthetic load test verifies >=40% HubSpot call reduction"
```

### Task 5: Wire `search_hubspot_contacts` and `query_hubspot_crm` through the same pattern

**Files:**
- Modify: `app/agents/tools/hubspot_tools.py`

Apply the same cache-aside pattern to the two remaining read endpoints. Key shapes:

- `search_hubspot_contacts(query)` → `hubspot:contacts_search:{user_id}:{sha1(query)}`, TTL 300s
- `query_hubspot_crm(query_type, lifecycle_stage, source, limit)` → `hubspot:query_crm:{user_id}:{sha1(query_type|stage|source|limit)}`, TTL 300s

`list_hubspot_deals(pipeline, stage)` reads only the local `hubspot_deals` table — NOT HubSpot directly — so it doesn't need the cache. Skip it.

- [ ] **Step 1: Add a helper for arbitrary-query cache keys**

In `hubspot_cache.py`:

```python
async def get_cached_query(
    *,
    namespace: str,
    user_id: str,
    fingerprint: str,
    loader: Callable[[], Awaitable[Any]],
    ttl_seconds: int = 300,
) -> Any:
    """Cache an arbitrary HubSpot read by (namespace, user_id, fingerprint).

    fingerprint is caller-built — sha1 of relevant args.
    """
    key = f"hubspot:{namespace}:{user_id}:{fingerprint}"
    return await _cached_or_fetch(
        cache_key=key, ttl_seconds=ttl_seconds, loader=loader,
    )
```

- [ ] **Step 2: Wrap `search_hubspot_contacts` and `query_hubspot_crm`**

```python
# In hubspot_tools.py — search_hubspot_contacts:
async def search_hubspot_contacts(query: str) -> dict[str, Any]:
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.tools.hubspot_cache import get_cached_query
    import hashlib as _h

    fingerprint = _h.sha1(query.encode("utf-8"), usedforsecurity=False).hexdigest()

    async def _loader() -> dict[str, Any]:
        try:
            from app.services.hubspot_service import HubSpotService
            svc = HubSpotService()
            contacts = await svc.search_contacts(user_id, query)
            return {"contacts": contacts, "count": len(contacts)}
        except Exception as exc:
            logger.exception("search_hubspot_contacts failed for user=%s", user_id)
            return {"error": f"Failed to search HubSpot contacts: {exc}"}

    return await get_cached_query(
        namespace="contacts_search",
        user_id=user_id,
        fingerprint=fingerprint,
        loader=_loader,
    )


# query_hubspot_crm — same pattern, fingerprint over the 4 filter args:
async def query_hubspot_crm(
    query_type: str = "contacts",
    lifecycle_stage: str | None = None,
    source: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    from app.agents.tools.hubspot_cache import get_cached_query
    import hashlib as _h

    fp_material = f"{query_type}|{lifecycle_stage}|{source}|{limit}".encode("utf-8")
    fingerprint = _h.sha1(fp_material, usedforsecurity=False).hexdigest()

    async def _loader() -> dict[str, Any]:
        # ... existing query_hubspot_crm body, unchanged, returning dict ...
```

The `query_hubspot_crm` body is large — preserve it verbatim inside `_loader`. Move the existing function body (the `try / if query_type == "deals" / else` block) into `_loader` and replace the outer function with the cached-aware version.

- [ ] **Step 3: Add tests**

Extend `tests/unit/agents/tools/test_hubspot_tools_cached.py` with two more cases — one hit case for `search_hubspot_contacts`, one for `query_hubspot_crm`. Mirror the pattern from Task 3 Step 1.

- [ ] **Step 4: Run + commit**

```powershell
uv run pytest tests/unit/agents/tools/test_hubspot_tools_cached.py -v --tb=short
git add app/agents/tools/hubspot_cache.py app/agents/tools/hubspot_tools.py tests/unit/agents/tools/test_hubspot_tools_cached.py
git commit -m "feat(115-02): cache search_hubspot_contacts + query_hubspot_crm read paths"
```

### Task 6: Graph-tier scaffolding — `should_query_graph` consult before HubSpot

**Files:**
- Modify: `app/agents/tools/hubspot_cache.py`
- Modify: `tests/unit/agents/tools/test_hubspot_cache.py`

We add a graph-tier check BEFORE the Redis check so that once Plan 115-03 populates `pipeline_health` claims with 24h freshness, the cache returns the claim summary instead of even consulting Redis. Until 115-03 ships, the graph tier always returns `miss` (no claims yet), and execution falls through to the Redis tier transparently.

The new helper `get_cached_pipeline_health(entity_id)`:
1. Calls `should_query_graph(entity_id, claim_type="pipeline_health", agent_id="sales", freshness_threshold_hours=24)`.
2. If `verdict == "fresh"`, reads the latest claim via `find_claims(entity_id, claim_type="pipeline_health", limit=1)` and returns its payload.
3. Otherwise, falls through to the Redis-tier `get_cached_pipeline` (Plan 115-02 layer).
4. Otherwise, calls the loader.

This is the canonical two-tier pattern from `app/services/intelligence/cache.py`. The graph layer is "real" but unpopulated; it gracefully returns `miss` until 115-03's claims land.

- [ ] **Step 1: Failing test**

```python
@pytest.mark.asyncio
async def test_get_cached_pipeline_health_graph_hit_skips_redis():
    """Fresh graph-tier claim returns directly without Redis or loader."""
    from uuid import uuid4

    from app.agents.tools.hubspot_cache import get_cached_pipeline_health
    from app.services.intelligence.schemas import CacheDecision, Claim, ClaimSource

    fake_claim = Claim(
        id=uuid4(),
        entity_id=uuid4(),
        edge_id=None,
        agent_id="sales",
        claim_type="pipeline_health",
        domain="sales",
        finding_text="Pipeline is healthy: 15 open deals worth $230K, 60% qualified.",
        confidence=0.78,
        sources=[ClaimSource(kind="other", ref="snapshot")],
        contradicts=[],
        freshness_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        expires_at=None,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    loader = AsyncMock(return_value={"should_not_be_called": True})

    with patch(
        "app.agents.tools.hubspot_cache.should_query_graph",
        new=AsyncMock(return_value=CacheDecision(
            tier="graph", verdict="fresh", freshness_hours=1.0,
        )),
    ), patch(
        "app.agents.tools.hubspot_cache.find_claims",
        new=AsyncMock(return_value=[fake_claim]),
    ):
        result = await get_cached_pipeline_health(
            entity_id=fake_claim.entity_id, loader=loader,
        )

    assert result["finding_text"] == fake_claim.finding_text
    assert result["confidence"] == pytest.approx(0.78)
    loader.assert_not_called()


@pytest.mark.asyncio
async def test_get_cached_pipeline_health_graph_miss_falls_through_to_loader():
    """No claim in graph → loader runs."""
    from uuid import uuid4

    from app.agents.tools.hubspot_cache import get_cached_pipeline_health
    from app.services.intelligence.schemas import CacheDecision

    loader = AsyncMock(return_value={"summary": "live"})

    with patch(
        "app.agents.tools.hubspot_cache.should_query_graph",
        new=AsyncMock(return_value=CacheDecision(
            tier="graph", verdict="miss", freshness_hours=None,
        )),
    ):
        result = await get_cached_pipeline_health(
            entity_id=uuid4(), loader=loader,
        )

    assert result == {"summary": "live"}
    loader.assert_awaited_once()
```

- [ ] **Step 2: Implement**

Append to `app/agents/tools/hubspot_cache.py`:

```python
from uuid import UUID  # add to imports at top

from app.services.intelligence import (
    find_claims,
    should_query_graph,
)

_GRAPH_FRESHNESS_HOURS_PIPELINE_HEALTH = 24.0


async def get_cached_pipeline_health(
    *,
    entity_id: UUID,
    loader: Callable[[], Awaitable[Any]],
) -> Any:
    """Two-tier cache for pipeline_health claim summaries.

    Graph tier (kg_findings, 24h freshness) → Redis tier (not used here,
    pipeline_health is a synthesized claim, not a HubSpot resource) → loader.

    Until Plan 115-03 ships claim emission, the graph tier always returns
    miss, and we fall straight through to the loader. After 115-03 lands,
    repeated requests within 24h skip the loader entirely.
    """
    decision = await should_query_graph(
        entity_id=entity_id,
        claim_type="pipeline_health",
        agent_id="sales",
        freshness_threshold_hours=_GRAPH_FRESHNESS_HOURS_PIPELINE_HEALTH,
    )

    if decision.verdict == "fresh":
        try:
            claims = await find_claims(
                entity_id=entity_id,
                claim_type="pipeline_health",
                agent_id="sales",
                limit=1,
            )
            if claims:
                c = claims[0]
                return {
                    "finding_text": c.finding_text,
                    "confidence": c.confidence,
                    "band": c.band,
                    "freshness_hours": decision.freshness_hours,
                    "source": "kg_findings",
                }
        except Exception as exc:
            logger.warning(
                "get_cached_pipeline_health: graph fetch failed entity=%s: %s",
                entity_id, exc,
            )

    return await loader()
```

- [ ] **Step 3: Run + commit**

```powershell
uv run pytest tests/unit/agents/tools/test_hubspot_cache.py -v --tb=short
```

Expected: all green including new tests.

```bash
git add app/agents/tools/hubspot_cache.py tests/unit/agents/tools/test_hubspot_cache.py
git commit -m "feat(115-02): graph-tier consult for pipeline_health (scaffolding, populated in 115-03)"
```

### Task 7: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/agents/tools/hubspot_cache.py app/agents/tools/hubspot_tools.py tests/unit/agents/tools/test_hubspot_cache.py tests/unit/agents/tools/test_hubspot_tools_cached.py tests/integration/test_hubspot_cache_load.py
uv run ruff format app/agents/tools/hubspot_cache.py app/agents/tools/hubspot_tools.py tests/unit/agents/tools/test_hubspot_cache.py tests/unit/agents/tools/test_hubspot_tools_cached.py tests/integration/test_hubspot_cache_load.py --check
```

Fix in place. Commit:

```bash
git add -u
git commit -m "style(115-02): ruff format + lint fixes for plan 115-02 files"
```

- [ ] **Step 2: Plan 115-02 acceptance cross-check**

| Acceptance line | Verified by |
|---|---|
| Redis tier wired for HubSpot contact reads | Task 2 + Task 3 |
| Redis tier wired for HubSpot deal reads | Task 2 + Task 6 (graph scaffold) |
| TTLs match spec (300s contact, 300s deal, 600s pipeline) | Task 2 Step 3 + tests |
| Cache keys match spec (`hubspot:contact:{id}`, etc.) | Task 2 tests |
| Cache degrades silently on Redis failure | Task 2 `test_get_cached_contact_redis_down_degrades_to_live` |
| ≥40% HubSpot call reduction on synthetic load | Task 4 |
| Existing `hubspot_tools` test suite green | Task 3 Step 5 |
| Error responses NOT cached | Task 3 Step 1 third test |
| Graph-tier scaffold ready for 115-03 claims | Task 6 |
| Lint clean | Task 7 |

- [ ] **Step 3: Plan 115-02 complete. Plan 115-03 (claim emission) unblocked.**

The Sales Agent now reuses HubSpot read responses from Redis on the 5–10 min freshness window. Plan 115-03 populates `pipeline_health` claims so the graph tier (24h freshness) takes over the most expensive aggregation queries.

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| HubSpot contact cache: Redis tier, 300s TTL, `hubspot:contact:{contact_id}` | Task 2 |
| HubSpot deal cache: Redis tier, 300s TTL, `hubspot:deal:{deal_id}` | Task 2 |
| HubSpot pipeline cache: Redis tier, 600s TTL, `hubspot:pipeline:{pipeline_id}` | Task 2 |
| Two-tier graph + Redis pattern (graph 24h, Redis 5–10 min) | Tasks 2 + 6 |
| `should_call_external` / `should_query_graph` used (no parallel cache code) | Tasks 2 + 6 |
| HubSpot API call rate reduced ≥40% on synthetic load | Task 4 |
| No regression in existing hubspot_tools tests | Task 3 Step 5 |
| Lint clean | Task 7 |

All spec lines covered.
