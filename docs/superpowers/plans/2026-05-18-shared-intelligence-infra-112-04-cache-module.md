# Shared Intelligence Infrastructure — Plan 112-04: Adaptive Cache Module

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the two-tier adaptive cache module — `should_query_graph` (consults kg_findings freshness) and `should_call_external` (consults Redis with age tracking). Both return a `CacheDecision` immutable dataclass with verdict `fresh` / `stale` / `miss`. Extends the existing `app/services/cache.py` with `get_with_age` / `set_with_age` helpers to support the raw-tier age check.

**Architecture:** Two pure-async functions and one frozen dataclass. `should_query_graph` calls `claims.claim_freshness_hours` (Plan 112-03) and applies a threshold. `should_call_external` wraps the existing Redis CacheService with a metadata envelope `{__value__, __stored_at__}` so the consumer can know how old a cached entry is. Reads degrade silently — backend failure returns `verdict="miss"` so callers force a fresh fetch. No new ADK tools.

**Tech Stack:** Python 3.10+, asyncio, existing `app/services/cache.py` (Redis with circuit breaker).

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Module specifications § cache.py

**Out of scope for this plan:** Research Agent refactor (Plan 112-05), per-agent budget tracking (Phase 113+).

---

## File structure

**Create:**
- `app/services/intelligence/cache.py` — `should_query_graph`, `should_call_external`
- `tests/unit/services/intelligence/test_cache.py` — unit tests with mocked freshness/Redis backends
- `tests/integration/test_intelligence_cache.py` — integration tests against real Redis + DB

**Modify:**
- `app/services/intelligence/schemas.py` — add `CacheDecision` frozen dataclass
- `app/services/intelligence/__init__.py` — re-export
- `app/services/cache.py` — add `get_with_age` + `set_with_age` methods on `CacheService`

**Reference (read-only):**
- `app/services/cache.py:97-130` — existing `CacheResult` dataclass and helpers
- `app/services/cache.py:670-727` — existing `get_generic` / `set_generic` (we mirror their pattern)
- `app/services/intelligence/claims.py` — `claim_freshness_hours` (called by `should_query_graph`)

---

## Pre-flight context

The cache substrate decision (from the spec): two-tier — graph for claims (kg_findings freshness), Redis for raw external calls. They serve different cache shapes:

- **Graph tier:** semantic value, long-lived (hours to days), already structured in kg_findings. Age is computed from `freshness_at` column.
- **Redis tier:** raw API responses, transient (minutes), value can be any JSON-serializable thing. Age requires us to wrap the stored value with a timestamp.

Environment quirks (carried from earlier plans):
- `uv` only works via PowerShell
- Redis runs locally via `docker compose up` (per CLAUDE.md)
- For tests, env vars: `REDIS_HOST=localhost`, `REDIS_PORT=6379` (defaults usually work)

Test commands:
```powershell
uv run pytest tests/unit/services/intelligence/test_cache.py -v
uv run pytest tests/integration/test_intelligence_cache.py -v -m integration
```

---

## Tasks

### Task 1: Pre-flight + add `CacheDecision` to schemas.py

**Files:**
- Modify: `app/services/intelligence/schemas.py`

- [ ] **Step 1: Confirm Plan 112-03 complete**

```bash
grep -E "^async def (write_claim|find_claims|claim_freshness_hours|get_or_create_entity)" app/services/intelligence/claims.py
```

Expected: all four function signatures present (NOT stubs raising NotImplementedError). If still stubs, STOP — 112-04 depends on 112-03 being implemented.

- [ ] **Step 2: Confirm Redis is reachable** (from PowerShell):

```powershell
docker ps --filter "name=redis" --format "{{.Names}}: {{.Status}}"
```

Expected: a redis container listed as Up. If not, `docker compose up -d redis` from PowerShell.

- [ ] **Step 3: Append `CacheDecision` to `app/services/intelligence/schemas.py`**

Edit the existing file. Add at the bottom:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheDecision:
    """Decision returned by should_query_graph / should_call_external.

    Frozen so callers can rely on the value being unchanged after return.
    """

    tier: Literal["graph", "redis"]
    verdict: Literal["fresh", "stale", "miss"]
    freshness_hours: float | None  # None on miss
```

Also add `CacheDecision` to the file's intended public exports (the `__init__.py` import will be updated in Task 8).

- [ ] **Step 4: Verify imports**

```powershell
uv run python -c "from app.services.intelligence.schemas import CacheDecision; print(CacheDecision)"
```

Expected: `<class 'app.services.intelligence.schemas.CacheDecision'>`.

- [ ] **Step 5: Commit**

```bash
git add app/services/intelligence/schemas.py
git commit -m "feat(112-04): add CacheDecision frozen dataclass to intelligence.schemas"
```

---

### Task 2: Extend `CacheService` with `get_with_age` / `set_with_age` (TDD)

**Files:**
- Modify: `app/services/cache.py`
- Create: `tests/unit/services/test_cache_with_age.py`

The existing `get_generic` / `set_generic` don't return age. We add a sibling pair that wraps the stored value in a metadata envelope `{"__value__": ..., "__stored_at__": iso_timestamp}` and returns `(value, age_seconds)` on read.

- [ ] **Step 1: Write the failing test file**

```python
"""Unit tests for CacheService.get_with_age / set_with_age (Plan 112-04)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_set_with_age_then_get_with_age_returns_value_and_age():
    """Roundtrip: stored value comes back, age is small (<1s) immediately after."""
    from app.services.cache import CacheService

    svc = CacheService()
    key = "test:plan-112-04:roundtrip"
    await svc.set_with_age(key, {"hello": "world"}, ttl=10)
    value, age = await svc.get_with_age(key)
    assert value == {"hello": "world"}
    assert age is not None
    assert 0.0 <= age < 1.0


@pytest.mark.asyncio
async def test_get_with_age_miss_returns_none_none():
    """Missing key returns (None, None)."""
    from app.services.cache import CacheService

    svc = CacheService()
    value, age = await svc.get_with_age("test:plan-112-04:nonexistent-key-zzzzzz")
    assert value is None
    assert age is None


@pytest.mark.asyncio
async def test_get_with_age_aged_value():
    """After artificial sleep, age increases monotonically."""
    from app.services.cache import CacheService

    svc = CacheService()
    key = "test:plan-112-04:aged"
    await svc.set_with_age(key, "value", ttl=10)
    await asyncio.sleep(0.6)
    _, age = await svc.get_with_age(key)
    assert age is not None
    assert age >= 0.5
```

The first two tests require a running Redis. If your dev machine doesn't have Redis, these will skip (the cache service degrades gracefully when Redis is unavailable). Confirm Redis is running before proceeding.

- [ ] **Step 2: Run tests — should FAIL** (AttributeError, no such methods)

```powershell
uv run pytest tests/unit/services/test_cache_with_age.py -v --tb=short
```

Expected: AttributeError for missing `set_with_age` / `get_with_age` methods.

- [ ] **Step 3: Implement the methods on `CacheService`**

In `app/services/cache.py`, find the existing `set_generic` / `get_generic` methods (around lines 670-727). Add these two methods immediately after them (still inside the `CacheService` class):

```python
async def set_with_age(self, key: str, value: Any, ttl: int = 3600) -> bool:
    """Store a value with a metadata envelope so get_with_age can report age.

    Args:
        key: Redis key (caller should namespace).
        value: Any JSON-serializable value.
        ttl: Time-to-live in seconds.

    Returns:
        True on success, False on failure or circuit-breaker-open.
    """
    from datetime import datetime, timezone

    envelope = {
        "__value__": value,
        "__stored_at__": datetime.now(timezone.utc).isoformat(),
    }
    return await self.set_generic(key, envelope, ttl)


async def get_with_age(self, key: str) -> tuple[Any | None, float | None]:
    """Fetch a value stored via set_with_age along with its age in seconds.

    Returns:
        (value, age_seconds) on hit. (None, None) on miss or error.
        If the value was stored via the legacy set_generic (no envelope),
        returns (value, None) — caller treats unknown-age as "no age info".
    """
    from datetime import datetime, timezone

    result = await self.get_generic(key)
    if not result.found or result.value is None:
        return None, None
    raw = result.value
    if not isinstance(raw, dict) or "__stored_at__" not in raw:
        # Legacy key without metadata — return value, no age.
        return raw, None
    try:
        stored_at = datetime.fromisoformat(raw["__stored_at__"])
        if stored_at.tzinfo is None:
            stored_at = stored_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age_seconds = (now - stored_at).total_seconds()
        return raw.get("__value__"), max(0.0, age_seconds)
    except (ValueError, KeyError):
        return raw.get("__value__"), None
```

- [ ] **Step 4: Re-run tests — should PASS**

```powershell
uv run pytest tests/unit/services/test_cache_with_age.py -v
```

Expected: all 3 PASS. If Redis isn't reachable they'll fail with connection errors — the CacheService prints those at the WARNING level. Start Redis or skip with `-m "not integration"` (the tests aren't marked integration here because we want unit-level tests of the new methods, but they DO need a Redis backend; consider marking as integration in a follow-up if this causes CI grief).

- [ ] **Step 5: Commit**

```bash
git add app/services/cache.py tests/unit/services/test_cache_with_age.py
git commit -m "feat(112-04): add get_with_age/set_with_age to CacheService (GREEN)"
```

---

### Task 3: Scaffold `cache.py` with stubs

**Files:**
- Create: `app/services/intelligence/cache.py`

- [ ] **Step 1: Create the file with stubs**

```python
"""Two-tier adaptive cache: graph for claims, Redis for raw external calls.

Public surface:
- should_query_graph   — consult kg_findings freshness
- should_call_external — consult Redis with age tracking

Both return CacheDecision(tier, verdict, freshness_hours). Reads degrade
silently — backend failure returns verdict='miss' forcing a fresh fetch.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.services.intelligence.schemas import CacheDecision

logger = logging.getLogger(__name__)


async def should_query_graph(
    *,
    entity_id: UUID,
    claim_type: str | None,
    agent_id: str | None,
    freshness_threshold_hours: float,
) -> CacheDecision:
    """Stub — implemented in Task 4."""
    raise NotImplementedError("Implemented in Plan 112-04 Task 4")


async def should_call_external(
    *,
    cache_key: str,
    ttl_seconds: int,
) -> CacheDecision:
    """Stub — implemented in Task 6."""
    raise NotImplementedError("Implemented in Plan 112-04 Task 6")
```

- [ ] **Step 2: Verify import**

```powershell
uv run python -c "
from app.services.intelligence.cache import should_query_graph, should_call_external
print('cache stub imports OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/intelligence/cache.py
git commit -m "feat(112-04): scaffold intelligence.cache with stubs"
```

---

### Task 4: Implement `should_query_graph` (TDD)

**Files:**
- Create: `tests/unit/services/intelligence/test_cache.py`
- Modify: `app/services/intelligence/cache.py`

- [ ] **Step 1: Create the unit test file**

```python
"""Unit tests for app.services.intelligence.cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# should_query_graph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_query_graph_fresh():
    """When a fresh claim exists within threshold, verdict='fresh'."""
    from app.services.intelligence.cache import should_query_graph

    entity_id = uuid4()
    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(return_value=2.0),
    ):
        decision = await should_query_graph(
            entity_id=entity_id,
            claim_type="cohort_retention",
            agent_id="data",
            freshness_threshold_hours=24.0,
        )
    assert decision.tier == "graph"
    assert decision.verdict == "fresh"
    assert decision.freshness_hours == 2.0


@pytest.mark.asyncio
async def test_should_query_graph_stale():
    """When claim exists but exceeds threshold, verdict='stale'."""
    from app.services.intelligence.cache import should_query_graph

    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(return_value=48.0),
    ):
        decision = await should_query_graph(
            entity_id=uuid4(),
            claim_type="cohort_retention",
            agent_id="data",
            freshness_threshold_hours=24.0,
        )
    assert decision.verdict == "stale"
    assert decision.freshness_hours == 48.0


@pytest.mark.asyncio
async def test_should_query_graph_miss():
    """When no matching claim exists, verdict='miss'."""
    from app.services.intelligence.cache import should_query_graph

    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(return_value=None),
    ):
        decision = await should_query_graph(
            entity_id=uuid4(),
            claim_type="x",
            agent_id="y",
            freshness_threshold_hours=12.0,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None


@pytest.mark.asyncio
async def test_should_query_graph_db_failure_returns_miss():
    """When claim_freshness_hours raises, verdict='miss' (degrades silently)."""
    from app.services.intelligence.cache import should_query_graph

    with patch(
        "app.services.intelligence.cache.claim_freshness_hours",
        new=AsyncMock(side_effect=Exception("DB down")),
    ):
        decision = await should_query_graph(
            entity_id=uuid4(),
            claim_type="x",
            agent_id="y",
            freshness_threshold_hours=12.0,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None
```

- [ ] **Step 2: Run — should FAIL** with NotImplementedError

```powershell
uv run pytest tests/unit/services/intelligence/test_cache.py -k "should_query_graph" -v
```

- [ ] **Step 3: Implement `should_query_graph`**

Replace the stub in `app/services/intelligence/cache.py`:

```python
async def should_query_graph(
    *,
    entity_id: UUID,
    claim_type: str | None,
    agent_id: str | None,
    freshness_threshold_hours: float,
) -> CacheDecision:
    """Graph-tier cache decision: is there a fresh-enough claim in kg_findings?

    Args:
        entity_id: kg_entities row to check.
        claim_type: Restrict to this claim_type, or None for any.
        agent_id: Restrict to claims from this agent, or None for any.
        freshness_threshold_hours: Maximum age in hours for "fresh".

    Returns:
        CacheDecision with tier='graph'. On DB failure, returns
        verdict='miss' so caller forces fresh fetch.
    """
    from app.services.intelligence.claims import claim_freshness_hours

    try:
        age = await claim_freshness_hours(
            entity_id=entity_id,
            claim_type=claim_type,
            agent_id=agent_id,
        )
    except Exception as e:
        logger.warning("should_query_graph: freshness lookup failed: %s", e)
        return CacheDecision(tier="graph", verdict="miss", freshness_hours=None)

    if age is None:
        return CacheDecision(tier="graph", verdict="miss", freshness_hours=None)
    if age <= freshness_threshold_hours:
        return CacheDecision(tier="graph", verdict="fresh", freshness_hours=age)
    return CacheDecision(tier="graph", verdict="stale", freshness_hours=age)
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_cache.py -k "should_query_graph" -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/unit/services/intelligence/test_cache.py \
        app/services/intelligence/cache.py
git commit -m "feat(112-04): implement should_query_graph with degrade-silently semantics (GREEN)"
```

---

### Task 5: Implement `should_call_external` (TDD)

**Files:**
- Modify: `tests/unit/services/intelligence/test_cache.py`
- Modify: `app/services/intelligence/cache.py`

- [ ] **Step 1: Append `should_call_external` tests** to `test_cache.py`:

```python
# ---------------------------------------------------------------------------
# should_call_external
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_call_external_fresh():
    """Fresh Redis entry (age <= ttl) returns verdict='fresh'."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(return_value=("cached value", 60.0))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key", ttl_seconds=300,
        )
    assert decision.tier == "redis"
    assert decision.verdict == "fresh"
    assert decision.freshness_hours == pytest.approx(60.0 / 3600.0, rel=1e-6)


@pytest.mark.asyncio
async def test_should_call_external_stale():
    """Stale Redis entry (age > ttl, but present) returns verdict='stale'."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(return_value=("cached value", 600.0))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key", ttl_seconds=300,
        )
    assert decision.verdict == "stale"


@pytest.mark.asyncio
async def test_should_call_external_miss():
    """No Redis entry returns verdict='miss'."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(return_value=(None, None))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key", ttl_seconds=300,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None


@pytest.mark.asyncio
async def test_should_call_external_redis_down_returns_miss():
    """Redis backend exception returns verdict='miss' (degrades silently)."""
    from app.services.intelligence.cache import should_call_external

    fake_cache = AsyncMock()
    fake_cache.get_with_age = AsyncMock(side_effect=Exception("Redis down"))

    with patch(
        "app.services.intelligence.cache.get_cache_service",
        return_value=fake_cache,
    ):
        decision = await should_call_external(
            cache_key="test:key", ttl_seconds=300,
        )
    assert decision.verdict == "miss"
    assert decision.freshness_hours is None
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/services/intelligence/test_cache.py -k "should_call_external" -v
```

- [ ] **Step 3: Implement `should_call_external`**

Replace the stub:

```python
async def should_call_external(
    *,
    cache_key: str,
    ttl_seconds: int,
) -> CacheDecision:
    """Redis-tier cache decision: is there a fresh-enough cached value?

    Wraps the existing CacheService.get_with_age. Age is converted to hours
    in the returned CacheDecision so consumers always have a uniform unit
    across graph-tier and redis-tier decisions.

    Args:
        cache_key: Redis key — caller is responsible for namespacing.
        ttl_seconds: Freshness threshold in seconds.

    Returns:
        CacheDecision with tier='redis'. On Redis failure, returns
        verdict='miss' so caller forces fresh fetch.
    """
    from app.services.cache import get_cache_service

    try:
        cache = get_cache_service()
        value, age_seconds = await cache.get_with_age(cache_key)
    except Exception as e:
        logger.warning("should_call_external: Redis lookup failed: %s", e)
        return CacheDecision(tier="redis", verdict="miss", freshness_hours=None)

    if value is None or age_seconds is None:
        return CacheDecision(tier="redis", verdict="miss", freshness_hours=None)

    age_hours = age_seconds / 3600.0
    if age_seconds <= ttl_seconds:
        return CacheDecision(tier="redis", verdict="fresh", freshness_hours=age_hours)
    return CacheDecision(tier="redis", verdict="stale", freshness_hours=age_hours)
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/services/intelligence/test_cache.py -v
```

Expected: 8 tests PASS (4 for should_query_graph, 4 for should_call_external).

- [ ] **Step 5: Commit**

```bash
git add tests/unit/services/intelligence/test_cache.py \
        app/services/intelligence/cache.py
git commit -m "feat(112-04): implement should_call_external with redis age tracking (GREEN)"
```

---

### Task 6: Update `__init__.py` public surface

**Files:**
- Modify: `app/services/intelligence/__init__.py`

- [ ] **Step 1: Add cache exports to `__init__.py`**

Update the existing `__init__.py` to add the cache module's public names:

```python
"""Shared intelligence infrastructure used by agents.

Public surface:
- score_confidence / to_band — generic weighted scorer and band classifier
- presets — named confidence formulas per agent domain
- write_claim / write_claims / find_claims — kg_findings writers and reader
- claim_freshness_hours — graph-tier freshness check
- get_or_create_entity — entity resolution with idempotent upsert
- should_query_graph / should_call_external — two-tier adaptive cache
- Claim / ClaimPayload / ClaimSource / ConfidenceBand / CacheDecision — schemas
"""

from app.services.intelligence import presets
from app.services.intelligence.cache import should_call_external, should_query_graph
from app.services.intelligence.claims import (
    claim_freshness_hours,
    find_claims,
    get_or_create_entity,
    write_claim,
    write_claims,
)
from app.services.intelligence.confidence import score_confidence, to_band
from app.services.intelligence.schemas import (
    CacheDecision,
    Claim,
    ClaimPayload,
    ClaimSource,
    ConfidenceBand,
)

__all__ = [
    "CacheDecision",
    "Claim",
    "ClaimPayload",
    "ClaimSource",
    "ConfidenceBand",
    "claim_freshness_hours",
    "find_claims",
    "get_or_create_entity",
    "presets",
    "score_confidence",
    "should_call_external",
    "should_query_graph",
    "to_band",
    "write_claim",
    "write_claims",
]
```

- [ ] **Step 2: Import test**

```powershell
uv run python -c "
from app.services.intelligence import (
    score_confidence, to_band, presets,
    write_claim, write_claims, find_claims, claim_freshness_hours,
    get_or_create_entity,
    should_query_graph, should_call_external,
    Claim, ClaimPayload, ClaimSource, ConfidenceBand, CacheDecision,
)
print('full public surface OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add app/services/intelligence/__init__.py
git commit -m "feat(112-04): expose cache module in intelligence public surface"
```

---

### Task 7: Integration test against real Redis + DB

**Files:**
- Create: `tests/integration/test_intelligence_cache.py`

A small smoke test that exercises both tiers end-to-end against real backends. Catches any wiring issue the mock-based unit tests missed.

- [ ] **Step 1: Create the integration test**

```python
"""Integration smoke tests for the two-tier adaptive cache."""

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
        reason="Supabase credentials not provided in environment variables.",
    ),
]


@pytest.mark.asyncio
async def test_graph_tier_miss_then_fresh():
    """Write a claim, then should_query_graph reports it as fresh."""
    from app.services.intelligence import (
        get_or_create_entity, should_query_graph, write_claim,
    )

    entity_id = await get_or_create_entity(
        canonical_name=f"Cache Integ {uuid4()}",
        entity_type="topic", domains=["test"],
    )

    # Miss before any claim
    decision = await should_query_graph(
        entity_id=entity_id, claim_type="probe",
        agent_id="test", freshness_threshold_hours=24.0,
    )
    assert decision.verdict == "miss"

    await write_claim(
        entity_id=entity_id, domain="test",
        finding_text="cache probe claim", confidence=0.7,
        sources=[], agent_id="test", claim_type="probe",
    )

    decision = await should_query_graph(
        entity_id=entity_id, claim_type="probe",
        agent_id="test", freshness_threshold_hours=24.0,
    )
    assert decision.verdict == "fresh"
    assert decision.freshness_hours is not None and decision.freshness_hours < 0.01


@pytest.mark.asyncio
async def test_redis_tier_miss_then_fresh_then_stale():
    """Lifecycle of a Redis-tier cached entry: miss -> fresh -> stale."""
    import asyncio

    from app.services.cache import get_cache_service
    from app.services.intelligence import should_call_external

    cache = get_cache_service()
    key = f"test:plan-112-04:integ:{uuid4()}"

    # Miss
    decision = await should_call_external(cache_key=key, ttl_seconds=300)
    assert decision.verdict == "miss"

    # Fresh after set_with_age
    await cache.set_with_age(key, {"data": "payload"}, ttl=600)
    decision = await should_call_external(cache_key=key, ttl_seconds=300)
    assert decision.verdict == "fresh"

    # Stale after waiting longer than ttl_seconds
    # (ttl_seconds=1 forces stale after a brief sleep)
    await asyncio.sleep(1.2)
    decision = await should_call_external(cache_key=key, ttl_seconds=1)
    assert decision.verdict == "stale"
```

- [ ] **Step 2: Run** (from PowerShell):

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
uv run pytest tests/integration/test_intelligence_cache.py -v -m integration
```

Expected: 2 PASS. If `test_redis_tier_*` skips, Redis isn't reachable — start it.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_intelligence_cache.py
git commit -m "test(112-04): integration smoke tests for two-tier adaptive cache"
```

---

### Task 8: Lint + acceptance sign-off

- [ ] **Step 1: Lint** (from PowerShell):

```powershell
uv run ruff check app/services/intelligence/ tests/unit/services/intelligence/test_cache.py tests/integration/test_intelligence_cache.py tests/unit/services/test_cache_with_age.py
uv run ruff format app/services/intelligence/ tests/unit/services/intelligence/test_cache.py tests/integration/test_intelligence_cache.py tests/unit/services/test_cache_with_age.py --check
uv run ty check app/services/intelligence/
```

Fix any issues in place. Re-run.

- [ ] **Step 2: Run full intelligence test suite to confirm no regression**

```powershell
uv run pytest tests/unit/services/intelligence/ -v
uv run pytest tests/integration/test_intelligence_cache.py -v -m integration
```

Expected: all PASS.

- [ ] **Step 3: Acceptance check** against spec lines:

| Spec line | Where verified |
|---|---|
| `CacheDecision` is frozen dataclass | Task 1 — `@dataclass(frozen=True)` |
| `CacheDecision.verdict ∈ {fresh, stale, miss}` only (no suggested_action) | Task 1 schema |
| `should_query_graph` reads `claim_freshness_hours`, applies threshold | Task 4 impl |
| `should_call_external` wraps `CacheService.get_with_age` | Task 5 impl |
| Reads degrade silently on backend failure | `test_should_query_graph_db_failure_returns_miss`, `test_should_call_external_redis_down_returns_miss` |
| `get_with_age` returns `(value, age_seconds)` | Task 2 impl + tests |
| Public surface importable from `app.services.intelligence` | Task 6 |
| No new ADK tools | `git diff` check |

- [ ] **Step 4: Commit lint fixes if any, then close out**

```bash
git add app/services/intelligence/ tests/unit/services/intelligence/ tests/integration/test_intelligence_cache.py tests/unit/services/test_cache_with_age.py
git commit -m "style(112-04): lint and format fixes for cache module"
```

(Skip if no fixes.)

- [ ] **Step 5: Plan 112-04 complete. Plan 112-05 (Research refactor) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `should_query_graph` async, returns `CacheDecision` | Task 4 |
| `should_call_external` async, returns `CacheDecision` | Task 5 |
| `CacheDecision` frozen dataclass with tier, verdict, freshness_hours | Task 1 |
| No `suggested_action` field on `CacheDecision` | Task 1 schema |
| Verdict ∈ {fresh, stale, miss} | Task 1 + tests |
| Reads degrade silently | Task 4 + Task 5 implementations + tests |
| `CacheService.get_with_age` extension | Task 2 |
| Public surface in `__init__.py` | Task 6 |
| Integration smoke against real Redis + DB | Task 7 |
| No new ADK tools | Task 8 verification |

All spec lines covered. No placeholders. No unmapped requirements.
