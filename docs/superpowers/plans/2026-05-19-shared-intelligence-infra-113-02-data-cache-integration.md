# Shared Intelligence Infrastructure — Plan 113-02: Data Agent Two-Tier Cache Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the two-tier adaptive cache (built in Plan 112-04) around Data Agent's external calls and aggregations. `should_query_graph` short-circuits `cohort_analysis` when a fresh claim exists; `should_call_external` caches Stripe API responses in Redis so a repeated query doesn't re-call Stripe. Acceptance includes a measurable Stripe-call-reduction target.

**Architecture:** Two surgical wirings in `app/agents/data/tools.py:cohort_analysis`:
1. **Graph tier (before computation):** call `should_query_graph` with the cohort entity + `claim_type="cohort_summary"`. If `verdict="fresh"`, fetch the stored Claim via `find_claims` and return immediately — no Stripe call, no recomputation.
2. **Redis tier (before Stripe call):** wrap the Stripe transaction fetch with `should_call_external` keyed on cohort + month range. If `verdict="fresh"`, use the cached raw response. Otherwise call Stripe and `set_with_age` the response.

Claim *writing* on the graph tier is deferred to Plan 113-03 (which decides the full claim-emission vocabulary). This plan only consumes existing claims; writes happen after 113-03 ships.

**Tech Stack:** Plan 112-04's `should_query_graph` / `should_call_external` / `CacheService.get_with_age` / `set_with_age`. No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-05-18-shared-intelligence-infra-design.md` § Phase 113 § Cache effectiveness

**Out of scope for this plan:** Writing new claims (Plan 113-03), `search_claims_semantic` (Plan 113-04), contradiction detection (Plan 113-05), wiring cache around other Data Agent functions besides `cohort_analysis` (deferred per the pilot scope locked in Plan 113-01).

---

## File structure

**Create:**
- `tests/integration/test_data_cache_integration.py` — round-trip tests against real Supabase + Redis

**Modify:**
- `app/agents/data/tools.py:cohort_analysis` — graph-cache short-circuit + Redis caching of Stripe payload
- Possibly `app/services/cohort_analysis_service.py` — if Stripe access is encapsulated there, wire the Redis cache at the lowest layer to minimize blast radius

**Reference (read-only):**
- `app/services/intelligence/cache.py` — `should_query_graph`, `should_call_external`, `CacheDecision`
- `app/services/intelligence/claims.py` — `find_claims`, `get_or_create_entity` (no `write_claim` calls in this plan)
- Plan 113-01's pilot wiring (already in `cohort_analysis`)

---

## Pre-flight context

The pilot wiring from Plan 113-01 added `confidence` and `band` fields to `cohort_analysis` output but did NOT cache anything yet. This plan adds the cache discipline.

Cache key conventions:
- **Graph tier:** entity = `cohort_<period>` (e.g., `cohort_2026-q1`), entity_type = `metric`, claim_type = `cohort_summary`, agent_id = `data`. Freshness threshold: **24 hours** (cohort data doesn't change frequently for past months).
- **Redis tier:** cache key = `stripe:cohort_raw:{months}:{user_id}`. TTL: **300 seconds** (5 minutes) — Stripe transaction data is append-only so short TTL is appropriate for the recent window.

Acceptance bar (from spec):
- Stripe API call rate during synthetic 1000-request load test reduced by **≥40%** vs pre-113 baseline
- Graph-tier hit rate for `cohort_analysis` repeated calls within 24h: **≥60%**

The 40% target is generous: a repeated identical call within 5 minutes should be a 100% Redis hit. A call within 24h on the same cohort should be a 100% graph hit (once Plan 113-03 ships claim writes). For Plan 113-02, the graph tier will mostly miss because we haven't started writing claims yet — the cache acceptance is mostly about the Redis tier and the *structure* being correct so 113-03's writes start delivering hits.

Environment quirks: same as 112-04 — env vars `SUPABASE_*` + `REDIS_*` (password `pikar_dev_redis`).

---

## Tasks

### Task 1: Pre-flight + locate Stripe access point

**Files:** none modified — verification only.

- [ ] **Step 1: Confirm Plan 112-04 and Plan 113-01 are integrated**

```bash
grep -E "^async def (should_query_graph|should_call_external)" app/services/intelligence/cache.py
grep -E "^def data_confidence" app/services/intelligence/presets/data.py
grep -nB 2 "data_confidence" app/agents/data/tools.py
```

Expected: all three present, `data_confidence` called somewhere inside `cohort_analysis`. If `cohort_analysis` doesn't reference `data_confidence`, Plan 113-01 isn't done — finish that first.

- [ ] **Step 2: Trace the Stripe call**

```bash
grep -n "stripe\|Stripe\|StripeService\|stripe_client" app/services/cohort_analysis_service.py app/agents/data/tools.py | head -20
```

Locate where `CohortAnalysisService.analyze` actually calls Stripe. Capture:
- The function name (e.g., `_fetch_stripe_transactions`)
- The arguments it takes (probably `start_date`, `end_date`, `user_id`)
- The shape of its return value (list of dicts? `StripeChargeList`?)

This is the function we'll wrap with `should_call_external` + `set_with_age` in Task 4. If the Stripe call is buried deep, prefer wrapping at the lowest sensible layer — the goal is to cache the raw response BEFORE any parsing.

- [ ] **Step 3: Capture pre-wiring behavior as a baseline**

```bash
grep -c "stripe" app/services/cohort_analysis_service.py
```

Record the answer. After Plan 113-02 ships, the same grep should show one *additional* line (the cache check) — a sanity hint that the wiring landed where expected.

No commit in this task.

### Task 2: Wire graph-tier short-circuit into `cohort_analysis` (TDD)

**Files:**
- Modify: `app/agents/data/tools.py:cohort_analysis`
- Create: `tests/integration/test_data_cache_integration.py` (first section)

- [ ] **Step 1: Create the integration test file with the graph-tier tests**

```python
"""Integration tests for Data Agent two-tier cache wiring (Plan 113-02)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch
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


# ---------------------------------------------------------------------------
# Graph-tier short-circuit: when a fresh claim exists, skip computation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cohort_analysis_short_circuits_on_fresh_graph_claim():
    """If a fresh kg_findings claim exists for the cohort, cohort_analysis
    returns from it without invoking CohortAnalysisService.
    """
    from app.agents.data.tools import cohort_analysis
    from app.services.intelligence import (
        get_or_create_entity, write_claim,
    )

    # Seed a fresh claim
    entity_id = await get_or_create_entity(
        canonical_name=f"cohort_test_{uuid4()}",
        entity_type="metric",
        domains=["data"],
    )
    await write_claim(
        entity_id=entity_id, domain="data",
        finding_text="seeded cohort summary for short-circuit test",
        confidence=0.85,
        sources=[{"kind": "stripe_row", "ref": "test"}],
        agent_id="data", claim_type="cohort_summary",
    )

    # Mock CohortAnalysisService to detect whether it was called
    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={})
    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ), patch(
        # The cohort_analysis function builds the entity name from `months`;
        # patch the entity-id derivation so it lands on our seeded entity.
        "app.agents.data.tools._cohort_entity_id",
        AsyncMock(return_value=entity_id),
    ):
        result = await cohort_analysis(months=6)

    # Service should NOT have been called — we returned from cache
    fake_service.analyze.assert_not_called()
    # Result includes the cached payload signals
    assert "from_cache" in result and result["from_cache"] is True
    assert result.get("band") == "high"


@pytest.mark.asyncio
async def test_cohort_analysis_misses_graph_then_computes():
    """Without a fresh claim, cohort_analysis calls the service normally."""
    from app.agents.data.tools import cohort_analysis

    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={
        "retention_data": {"cohorts": [{"cohort_size": 150}]},
        "ltv_breakdown": {}, "executive_summary": "ok", "chart_data": {},
    })
    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ):
        result = await cohort_analysis(months=6)

    fake_service.analyze.assert_called_once()
    assert "confidence" in result
    assert result.get("from_cache", False) is False
```

- [ ] **Step 2: Run — should FAIL** (the helper `_cohort_entity_id` and the `from_cache` field don't exist yet)

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_SERVICE_ROLE_KEY = (supabase status -o env | Select-String '^SERVICE_ROLE_KEY=').ToString().Split('=',2)[1].Trim('"')
$env:SUPABASE_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
$env:REDIS_HOST = "localhost"; $env:REDIS_PORT = "6379"; $env:REDIS_PASSWORD = "pikar_dev_redis"
uv run pytest tests/integration/test_data_cache_integration.py -k "graph" -v --tb=short
```

Expected: 2 FAILED.

- [ ] **Step 3: Modify `cohort_analysis` to short-circuit on a fresh graph claim**

Add a helper to `app/agents/data/tools.py` (near `cohort_analysis`):

```python
async def _cohort_entity_id(months: int) -> "UUID":
    """Build / fetch the kg_entities row representing this cohort window."""
    from app.services.intelligence import get_or_create_entity
    return await get_or_create_entity(
        canonical_name=f"cohort_window_{months}m",
        entity_type="metric",
        domains=["data"],
    )
```

Then at the top of `cohort_analysis`, before calling `CohortAnalysisService`:

```python
from app.services.intelligence import (
    find_claims, should_query_graph, to_band,
)
from app.services.intelligence.presets import data_confidence

entity_id = await _cohort_entity_id(months)
decision = await should_query_graph(
    entity_id=entity_id,
    claim_type="cohort_summary",
    agent_id="data",
    freshness_threshold_hours=24.0,
)
if decision.verdict == "fresh":
    # Pull the most recent matching claim and return it
    claims = await find_claims(
        entity_id=entity_id, claim_type="cohort_summary", agent_id="data", limit=1,
    )
    if claims:
        c = claims[0]
        return {
            "from_cache": True,
            "cache_tier": "graph",
            "finding_text": c.finding_text,
            "confidence": c.confidence,
            "band": c.band,
            "freshness_hours": decision.freshness_hours,
            "sources": [s.model_dump(exclude_none=True) for s in c.sources],
        }
    # else fall through to computation
```

Add `"from_cache": False, "cache_tier": None` to the response payload before returning from the normal path, so downstream callers can always tell.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py -k "graph" -v --tb=short
```

Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/agents/data/tools.py tests/integration/test_data_cache_integration.py
git commit -m "feat(113-02): graph-tier short-circuit in cohort_analysis (GREEN)"
```

### Task 3: Wire Redis-tier caching around the Stripe call (TDD)

**Files:**
- Modify: `app/services/cohort_analysis_service.py` (where Stripe is called) OR `app/agents/data/tools.py` (if the cache wraps at the tool layer)
- Modify: `tests/integration/test_data_cache_integration.py` (append)

The implementer chooses the wrap layer based on Task 1 Step 2's audit. If `CohortAnalysisService.analyze` itself calls Stripe internally, wrap there. If `cohort_analysis` in tools.py orchestrates the Stripe call directly, wrap there.

- [ ] **Step 1: Append Redis-tier tests** to `test_data_cache_integration.py`:

```python
# ---------------------------------------------------------------------------
# Redis-tier: Stripe payload is cached
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stripe_payload_cached_in_redis():
    """A repeated cohort_analysis call within the Redis TTL doesn't re-call Stripe."""
    from app.agents.data.tools import cohort_analysis

    fake_stripe_response = {"transactions": [{"id": "ch_test_1"}]}
    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={
        "retention_data": {"cohorts": [{"cohort_size": 100}]},
        "ltv_breakdown": {}, "executive_summary": "x", "chart_data": {},
    })

    call_count = {"n": 0}

    async def fake_stripe_call(*args, **kwargs):
        call_count["n"] += 1
        return fake_stripe_response

    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ), patch(
        # Replace with the actual Stripe-call path from Task 1's audit
        "app.services.cohort_analysis_service._fetch_stripe_transactions",
        side_effect=fake_stripe_call,
    ):
        # First call hits Stripe
        await cohort_analysis(months=6)
        first_count = call_count["n"]
        # Second call within 300s should hit Redis, not Stripe
        await cohort_analysis(months=6)
        second_count = call_count["n"]

    # The second call shouldn't increment Stripe call count
    assert second_count == first_count, "Repeated cohort_analysis within TTL should hit Redis cache"
```

If the actual Stripe call path isn't `_fetch_stripe_transactions`, adjust the patch target to whatever Task 1 found.

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py -k "stripe" -v --tb=short
```

- [ ] **Step 3: Wire the Redis cache around the Stripe call**

In the function identified by Task 1 (Stripe call site), wrap as:

```python
from app.services.intelligence import should_call_external
from app.services.cache import get_cache_service

async def _fetch_stripe_transactions(months: int, user_id: str) -> dict:
    """Fetch Stripe transactions for the cohort window.

    Cached in Redis via the shared adaptive cache (Plan 113-02). 5-minute TTL
    matches Stripe's append-only data model — recent transactions are stable.
    """
    cache_key = f"stripe:cohort_raw:{months}m:{user_id}"
    decision = await should_call_external(cache_key=cache_key, ttl_seconds=300)
    cache = get_cache_service()

    if decision.verdict == "fresh":
        value, _age = await cache.get_with_age(cache_key)
        if value is not None:
            return value

    # Cache miss or stale — call Stripe
    result = await _real_stripe_fetch(months=months, user_id=user_id)
    await cache.set_with_age(cache_key, result, ttl=300)
    return result
```

If the existing Stripe-fetch function has a different signature, adapt — the pattern is `decision → cache.get_with_age on fresh → fall through to real fetch → set_with_age`.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py -k "stripe" -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add app/services/cohort_analysis_service.py tests/integration/test_data_cache_integration.py
git commit -m "feat(113-02): redis-tier caching around Stripe call (GREEN)"
```

### Task 4: Synthetic load test for cache effectiveness

**Files:**
- Create: `tests/integration/test_data_cache_load.py`

The spec's acceptance criterion is "Stripe API call rate reduced by ≥40% during synthetic 1000-request burst." We don't actually need 1000 requests for the test — a smaller burst that demonstrates the same hit-rate property is sufficient and faster.

- [ ] **Step 1: Create the load test**

```python
"""Synthetic load test: confirm Stripe call count is reduced by Plan 113-02 caching."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "REDIS_PASSWORD"]
        ),
        reason="env vars not provided",
    ),
]


@pytest.mark.asyncio
async def test_stripe_call_rate_below_60pct_of_request_count():
    """Across 20 cohort_analysis calls, Stripe is hit fewer than 12 times (>=40% reduction)."""
    from app.agents.data.tools import cohort_analysis

    fake_service = AsyncMock()
    fake_service.analyze = AsyncMock(return_value={
        "retention_data": {"cohorts": [{"cohort_size": 100}]},
        "ltv_breakdown": {}, "executive_summary": "x", "chart_data": {},
    })

    stripe_calls = 0

    async def counting_stripe(*args, **kwargs):
        nonlocal stripe_calls
        stripe_calls += 1
        return {"transactions": []}

    with patch(
        "app.services.cohort_analysis_service.CohortAnalysisService",
        return_value=fake_service,
    ), patch(
        "app.services.cohort_analysis_service._fetch_stripe_transactions",
        side_effect=counting_stripe,
    ):
        for _ in range(20):
            await cohort_analysis(months=6)

    # 1 cold call + at most 0 warm calls (TTL holds for the duration of the test)
    # Acceptance: <=12 Stripe calls out of 20 requests (>= 40% reduction)
    assert stripe_calls <= 12, (
        f"Expected <=12 Stripe calls; got {stripe_calls}. "
        "Cache wiring may not be hitting."
    )
```

- [ ] **Step 2: Run**

```powershell
uv run pytest tests/integration/test_data_cache_load.py -v
```

Expected: PASS, `stripe_calls == 1` (one cold call, 19 warm Redis hits within TTL).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_data_cache_load.py
git commit -m "test(113-02): synthetic load test for cache effectiveness (>=40% Stripe reduction)"
```

### Task 5: Lint + acceptance sign-off

- [ ] **Step 1: Lint**

```powershell
uv run ruff check app/agents/data/tools.py app/services/cohort_analysis_service.py tests/integration/test_data_cache_integration.py tests/integration/test_data_cache_load.py
uv run ruff format app/agents/data/tools.py app/services/cohort_analysis_service.py tests/integration/test_data_cache_integration.py tests/integration/test_data_cache_load.py --check
```

Fix in-place; commit any fixes.

- [ ] **Step 2: Final test run**

```powershell
uv run pytest tests/integration/test_data_cache_integration.py tests/integration/test_data_cache_load.py tests/unit/services/intelligence/ -v --tb=short 2>&1 | Select-Object -Last 10
```

Expected: all PASS.

- [ ] **Step 3: Acceptance check against spec**

| Spec line | Where verified |
|---|---|
| Graph-tier short-circuit on fresh claims | Task 2 + `test_cohort_analysis_short_circuits_on_fresh_graph_claim` |
| Redis-tier caching around Stripe calls | Task 3 + `test_stripe_payload_cached_in_redis` |
| Stripe call rate reduced ≥40% on repeated load | Task 4 + `test_stripe_call_rate_below_60pct_of_request_count` |
| No cache-poisoning regression (graph-stale path) | Implicit — `verdict="stale"` falls through to computation |
| Two-tier substrate semantically distinct | Graph stores epistemic claims (cohort_summary); Redis stores raw Stripe payload — separate cache keys |
| No new ADK tools | This plan is library-only |

- [ ] **Step 4: Plan 113-02 complete. Plan 113-03 (claim emission rules) is unblocked.**

---

## Spec coverage check

| Spec requirement | Task(s) |
|---|---|
| `should_query_graph` wraps `cohort_analysis` head | Task 2 |
| `should_call_external` wraps Stripe call | Task 3 |
| `CacheService.set_with_age` used for Redis writes | Task 3 |
| ≥40% Stripe call reduction measurable | Task 4 |
| Integration tests against real Supabase + Redis | All tasks |
| No new ADK tools | Library only |

All spec lines covered.
