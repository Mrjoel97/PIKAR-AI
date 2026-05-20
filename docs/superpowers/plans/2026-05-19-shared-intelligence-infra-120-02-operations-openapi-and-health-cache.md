# Shared Intelligence Infrastructure — Plan 120-02: Operations Two-Tier Cache (OpenAPI Spec + Integration Health + Endpoint Metadata)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Phase 112 two-tier adaptive cache (Redis-tier via `should_call_external`, graph-tier via `should_query_graph`) around three Operations-Agent external-call hot paths: OpenAPI spec parses (`connect_api`), integration health checks (`check_integration_status` / `validate_api_connection`), and endpoint metadata reads (`list_api_connections` lookups). End state: OpenAPI spec re-fetches drop ≥50% on synthetic load, integration health checks bunch into 5-min windows with ≥40% rate reduction, and endpoint metadata stays cached 7 days. No new ADK tools — the cache is library-first.

**Architecture:** Redis tier for raw external responses (spec body, probe results, endpoint metadata). Graph tier for the `integration_health_verified` claim freshness (24h threshold) — note that the *claim emission* itself ships in Plan 120-03; this plan only sets up the cache *consultation* against existing claims so repeated reads can short-circuit. Three distinct cache keys, three distinct TTLs, three distinct cache-miss behaviours.

**Tech Stack:** `app/services/intelligence/cache.py` (Phase 112 module), `app/services/cache.py` (Redis client with circuit breaker). `app/agents/tools/api_connector.py` and `app/agents/tools/integration_setup.py` get the wiring. pytest + mocked Redis for unit tests; live Redis (docker compose) for integration tests.

**Spec reference:** `docs/superpowers/specs/2026-05-19-shared-intelligence-infra-114-122-rolling-adoption-design.md` § Phase 120 — Operations Agent adoption § "Cache".

**Out of scope:** Claim emission (Plan 120-03). New ADK tools. Persona-aware cache namespacing. Cache invalidation on user-initiated reconnect (a follow-up — for now, reconnect simply writes a new entry and the next read sees it). Replacing the existing `cache_service` interface — we use `get_with_age` as shipped in Phase 112. Multi-tenant key isolation beyond what `cache_service` already provides via prefix. Calibration of TTL values beyond the spec-pinned numbers.

---

## File structure

**Create:**
- `tests/unit/agents/operations/test_openapi_spec_cache.py` — OpenAPI cache unit tests
- `tests/unit/agents/operations/test_integration_health_cache.py` — health-check cache unit tests
- `tests/unit/agents/operations/test_endpoint_metadata_cache.py` — endpoint metadata cache unit tests
- `tests/integration/test_operations_cache_load.py` — synthetic load test against live Redis
- `app/agents/operations/_cache_keys.py` — single source of truth for cache key shapes

**Modify:**
- `app/agents/tools/api_connector.py` — `connect_api` consults the spec cache before parse; `validate_api_connection` consults the health cache
- `app/agents/tools/integration_setup.py` — `check_integration_status` consults the health cache per service
- `app/agents/operations/agent.py` — no change (library-first; the wiring lives in the tools)

---

## Pre-flight context

Cache keys + TTLs (final, from spec):

| Key shape | TTL | Tier | Triggering call |
|---|---|---|---|
| `openapi_spec:{source_url_hash}` | 86400s (24h) | Redis | `connect_api` (spec re-fetches) |
| `integration_health:{service_id}` | 300s (5min) | Redis | `check_integration_status`, `validate_api_connection` |
| `endpoint_metadata:{connector_id}` | 604800s (7d) | Redis | post-`connect_api` codegen lookups, `list_api_connections` enrichment |
| (graph tier) `integration_health_verified` per `entity_id` | 24h freshness | Graph | consulted before re-running an integration probe |

`source_url_hash` = SHA-256 of the normalized spec URL (lowercased, trailing slash stripped) — keeps the key bounded even when the source URL is very long, and decouples logical identity from URL quirks (query-string ordering).

`service_id` for `integration_health:` = the canonical service short name (`hubspot`, `stripe`, `slack`, …) when it's a platform-managed integration, OR `api:{api_name}` for user-connected OpenAPI APIs.

`connector_id` for `endpoint_metadata:` = the `api_name` slug used by `connect_api` (lowercased, regex-cleaned per the existing code path).

**Cache-miss vs cache-hit behaviour by call type:**

| Call | Cache-hit behaviour | Cache-miss behaviour |
|---|---|---|
| `connect_api` spec parse | Skip HTTP fetch + `OpenAPIParser.parse_from_url`; reuse cached `(api_spec, endpoint_count)` | Fetch + parse + `cache_service.set(...)` with TTL 86400 |
| `check_integration_status` per service | Reuse cached `(configured: bool, last_checked: ts)` | Run live `config.is_*_configured` probe + cache write TTL 300 |
| `validate_api_connection` spec re-check | Reuse cached endpoint count from `endpoint_metadata:...` if `<7d` AND health cache says `<5min` | Re-fetch spec, write both caches |
| Graph-tier `integration_health_verified` check | If `should_query_graph(...).verdict='fresh'`, treat the integration as verified without re-probing | If `verdict in ('stale','miss')`, run live probe |

**Cache invalidation policy (open question, defaulted in this plan, see "Ambiguities" report at the bottom):**

- **OpenAPI spec cache:** pure TTL. The 24h TTL is the only invalidation signal. A new commit to the upstream spec causes a 0–24h staleness window on average. *Alternative considered:* event-driven invalidation via webhook from the upstream provider — not done because (a) most upstream specs are public URLs without callback infrastructure, (b) the spec change rate in practice is well below 1/day, (c) `validate_api_connection` already detects drift and emits a status when endpoint counts change.

- **Integration health cache:** pure TTL (5min). User-initiated reconnect implicitly invalidates by overwriting the key (the new `check_integration_status` after reconnect writes a fresh entry).

- **Endpoint metadata cache:** pure TTL (7d). `disconnect_api` does NOT explicitly evict — the TTL aging-out is sufficient because subsequent `connect_api` for the same name overwrites the entry.

If a future plan needs event-driven invalidation (e.g., admin "reconnect now" UI), it can add explicit `cache_service.delete(...)` calls without changing the cache surface itself.

Acceptance bar for this plan:
- OpenAPI spec re-fetches reduced ≥50% on synthetic load (the spec's primary load criterion).
- Integration health checks bunched into 5-min windows (≥40% rate reduction).
- Endpoint metadata cache hit on the second `list_api_connections` call within 7d.
- Cache miss path still works (live fetch + cache write).
- Cache backend failure degrades silently (verdict='miss' → live fetch).
- Zero behaviour change to the public tool surfaces (response shapes are byte-identical modulo timestamps and the cached field).

Environment quirks: Windows local-dev. Redis password is `pikar_dev_redis` (per `reference_local_dev_env_quirks` memory). Use `docker compose up redis` for the live-Redis integration tests; the unit tests mock `get_cache_service()` so they don't need Redis at all.

---

## Tasks

### Task 1: Pre-flight + cache key constants

**Files:**
- Create: `app/agents/operations/_cache_keys.py`

- [ ] **Step 1: Confirm Phase 112 cache module is intact**

```powershell
uv run python -c "from app.services.intelligence import should_call_external, should_query_graph, CacheDecision; print('ok')"
```

Expected output: `ok`. If this fails, Phase 112's `cache.py` regressed — STOP and surface.

- [ ] **Step 2: Confirm Redis cache service exposes `get_with_age`**

```powershell
uv run python -c "from app.services.cache import get_cache_service; svc = get_cache_service(); print(hasattr(svc, 'get_with_age'))"
```

Expected output: `True`. The Phase 112 Plan 112-04 extension is the load-bearing dependency.

- [ ] **Step 3: Create the cache keys module**

Create `app/agents/operations/_cache_keys.py`:

```python
"""Cache-key constants for Operations Agent caches (Plan 120-02).

Centralises the key shapes and TTL constants so the two tool modules
(api_connector.py, integration_setup.py) stay in sync. The leading
underscore in the module name marks it as private — external callers
should NOT import these directly; they belong to the cache wiring in
the operations tools layer.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

# TTL constants — pinned by the Phase 120 design spec.
OPENAPI_SPEC_TTL_SECONDS: Final[int] = 86_400  # 24h
INTEGRATION_HEALTH_TTL_SECONDS: Final[int] = 300  # 5min
ENDPOINT_METADATA_TTL_SECONDS: Final[int] = 604_800  # 7d

# Graph-tier freshness threshold for integration_health_verified claims (Plan 120-03).
INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS: Final[float] = 24.0

_SERVICE_SLUG_RE = re.compile(r"[^a-z0-9_-]")


def _normalise_spec_url(spec_url: str) -> str:
    """Normalise a spec URL for stable hashing: lowercase, strip trailing slash."""
    return spec_url.strip().lower().rstrip("/")


def openapi_spec_key(spec_url: str) -> str:
    """Build the Redis key for an OpenAPI spec cache entry.

    Uses SHA-256 of the normalised URL so the key is bounded even when the
    source URL is very long.
    """
    normalised = _normalise_spec_url(spec_url)
    digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return f"openapi_spec:{digest}"


def integration_health_key(service_id: str) -> str:
    """Build the Redis key for an integration health-check cache entry.

    service_id is lowercased and stripped of non-slug chars. Empty/None
    values raise — callers must provide a valid id.
    """
    if not service_id:
        raise ValueError("service_id must be non-empty")
    slug = _SERVICE_SLUG_RE.sub("", service_id.strip().lower())
    if not slug:
        raise ValueError(f"service_id {service_id!r} produces empty slug")
    return f"integration_health:{slug}"


def endpoint_metadata_key(connector_id: str) -> str:
    """Build the Redis key for an endpoint metadata cache entry.

    connector_id mirrors the api_name slug used by connect_api.
    """
    if not connector_id:
        raise ValueError("connector_id must be non-empty")
    slug = _SERVICE_SLUG_RE.sub("", connector_id.strip().lower())
    if not slug:
        raise ValueError(f"connector_id {connector_id!r} produces empty slug")
    return f"endpoint_metadata:{slug}"


__all__ = [
    "ENDPOINT_METADATA_TTL_SECONDS",
    "INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS",
    "INTEGRATION_HEALTH_TTL_SECONDS",
    "OPENAPI_SPEC_TTL_SECONDS",
    "endpoint_metadata_key",
    "integration_health_key",
    "openapi_spec_key",
]
```

- [ ] **Step 4: Sanity-check the key module**

```powershell
uv run python -c "from app.agents.operations._cache_keys import openapi_spec_key, integration_health_key, endpoint_metadata_key; print(openapi_spec_key('https://api.example.com/openapi.json/')); print(integration_health_key('HubSpot')); print(endpoint_metadata_key('Stripe-Live'))"
```

Expected output (one line each):
```
openapi_spec:<64-hex-char-hash>
integration_health:hubspot
endpoint_metadata:stripe-live
```

- [ ] **Step 5: Commit**

```bash
git add app/agents/operations/_cache_keys.py
git commit -m "feat(120-02): cache key constants + helpers for Operations cache surfaces"
```

### Task 2: OpenAPI spec cache (TDD)

**Files:**
- Create: `tests/unit/agents/operations/test_openapi_spec_cache.py`
- Modify: `app/agents/tools/api_connector.py`

The Redis-tier cache wraps `OpenAPIParser.parse_from_url`. The cached
value is the *parsed* `(api_spec_dict, endpoint_count)` tuple — not the
raw JSON — because the parser is the expensive step. JSON re-parse is
cheap; what we save is the network fetch + the parser walk.

- [ ] **Step 1: Failing unit tests**

Create `tests/unit/agents/operations/test_openapi_spec_cache.py`:

```python
"""Unit tests for the OpenAPI spec cache around connect_api."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _fake_api_spec(title: str = "FakeAPI", n_endpoints: int = 3) -> SimpleNamespace:
    """Build a minimal OpenAPIParser.parse_from_url return shape."""
    endpoints = [
        SimpleNamespace(
            operation_id=f"op{i}",
            method="GET",
            path=f"/x/{i}",
        )
        for i in range(n_endpoints)
    ]
    return SimpleNamespace(title=title, endpoints=endpoints)


@pytest.mark.asyncio
async def test_connect_api_uses_cached_spec_on_hit():
    """Cache hit: parse_from_url MUST NOT be called."""
    from app.agents.tools import api_connector

    cached_spec = _fake_api_spec()
    fake_decision = MagicMock(verdict="fresh", freshness_hours=0.5)

    with (
        patch(
            "app.agents.tools.api_connector.should_call_external",
            new=AsyncMock(return_value=fake_decision),
        ) as mock_decide,
        patch(
            "app.agents.tools.api_connector._load_cached_spec",
            new=AsyncMock(return_value=cached_spec),
        ),
        patch(
            "app.skills.api_parser.OpenAPIParser.parse_from_url",
        ) as mock_parse,
        patch(
            "app.skills.api_parser.validate_url",
            return_value=True,
        ),
    ):
        # connect_api is sync; the async cache lookups are bridged via the
        # adapter we add in Step 3 below.
        api_connector.connect_api(
            spec_url="https://example.com/openapi.json",
            api_name="example",
        )

        mock_decide.assert_called_once()
        mock_parse.assert_not_called()


@pytest.mark.asyncio
async def test_connect_api_cache_miss_parses_and_writes():
    """Cache miss: parse + cache_service.set with TTL 86400."""
    from app.agents.tools import api_connector

    fake_decision = MagicMock(verdict="miss", freshness_hours=None)
    parsed = _fake_api_spec()
    set_mock = AsyncMock()

    with (
        patch(
            "app.agents.tools.api_connector.should_call_external",
            new=AsyncMock(return_value=fake_decision),
        ),
        patch(
            "app.agents.tools.api_connector._load_cached_spec",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.agents.tools.api_connector._store_cached_spec",
            new=set_mock,
        ),
        patch(
            "app.skills.api_parser.OpenAPIParser.parse_from_url",
            return_value=parsed,
        ),
        patch(
            "app.skills.api_parser.validate_url",
            return_value=True,
        ),
    ):
        api_connector.connect_api(
            spec_url="https://example.com/openapi.json",
            api_name="example",
        )

        set_mock.assert_called_once()
        args, kwargs = set_mock.call_args
        # TTL must be the spec-pinned value (24h).
        assert kwargs.get("ttl_seconds") == 86400 or (
            len(args) >= 3 and args[2] == 86400
        )


def test_openapi_spec_key_stable_for_url_normalisation():
    """openapi_spec_key normalises trailing slash + case."""
    from app.agents.operations._cache_keys import openapi_spec_key

    a = openapi_spec_key("https://example.com/openapi.json/")
    b = openapi_spec_key("HTTPS://EXAMPLE.COM/openapi.json")
    assert a == b


def test_connect_api_redis_failure_falls_back_to_live_fetch():
    """Redis-down → verdict='miss' → live parse still works."""
    from app.agents.tools import api_connector

    miss = MagicMock(verdict="miss", freshness_hours=None)
    parsed = _fake_api_spec()

    with (
        patch(
            "app.agents.tools.api_connector.should_call_external",
            new=AsyncMock(return_value=miss),
        ),
        patch(
            "app.agents.tools.api_connector._load_cached_spec",
            new=AsyncMock(side_effect=RuntimeError("redis is down")),
        ),
        patch(
            "app.agents.tools.api_connector._store_cached_spec",
            new=AsyncMock(side_effect=RuntimeError("redis still down")),
        ),
        patch(
            "app.skills.api_parser.OpenAPIParser.parse_from_url",
            return_value=parsed,
        ),
        patch(
            "app.skills.api_parser.validate_url",
            return_value=True,
        ),
    ):
        result = api_connector.connect_api(
            spec_url="https://example.com/openapi.json",
            api_name="example",
        )
        # Cache failure must NOT propagate — degrade silently to live fetch.
        assert result.get("success") in (True, False)  # tool ran to completion
```

- [ ] **Step 2: Run — should FAIL (no wiring yet)**

```powershell
uv run pytest tests/unit/agents/operations/test_openapi_spec_cache.py -v --tb=short
```

Expected: collection errors or AttributeError on the patched symbols.

- [ ] **Step 3: Wire the cache into `connect_api`**

Modify `app/agents/tools/api_connector.py`. Add helper functions near the top of the file (after the existing imports):

```python
import asyncio
import json
from app.agents.operations._cache_keys import (
    OPENAPI_SPEC_TTL_SECONDS,
    openapi_spec_key,
)
from app.services.intelligence import should_call_external


async def _load_cached_spec(spec_url: str):
    """Fetch the cached parsed spec from Redis. Returns None on miss/error."""
    try:
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        key = openapi_spec_key(spec_url)
        value, _age = await cache.get_with_age(key)
        if value is None:
            return None
        # Stored as JSON-serialisable dict; reconstruct the SimpleNamespace shape
        # the rest of connect_api expects (.title, .endpoints).
        from types import SimpleNamespace
        data = value if isinstance(value, dict) else json.loads(value)
        return SimpleNamespace(
            title=data.get("title", ""),
            endpoints=[SimpleNamespace(**e) for e in data.get("endpoints", [])],
        )
    except Exception as e:
        logger.warning("OpenAPI spec cache read failed: %s", e)
        return None


async def _store_cached_spec(spec_url: str, api_spec, *, ttl_seconds: int) -> None:
    """Persist the parsed spec to Redis with TTL."""
    try:
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        key = openapi_spec_key(spec_url)
        payload = {
            "title": api_spec.title,
            "endpoints": [
                {
                    "operation_id": e.operation_id,
                    "method": getattr(e, "method", ""),
                    "path": getattr(e, "path", ""),
                }
                for e in api_spec.endpoints
            ],
        }
        await cache.set(key, payload, ttl_seconds=ttl_seconds)
    except Exception as e:
        logger.warning("OpenAPI spec cache write failed: %s", e)


def _run_async(coro):
    """Bridge: ADK tools run sync; helper executes a coroutine on a fresh loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already inside an event loop — schedule and wait via to_thread bridge
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)
```

Then modify the `connect_api` body — right after the SSRF check and before `parser = OpenAPIParser()`, insert:

```python
    # Cache-first: consult Redis before live spec parse.
    cached_decision = _run_async(
        should_call_external(
            cache_key=openapi_spec_key(spec_url),
            ttl_seconds=OPENAPI_SPEC_TTL_SECONDS,
        )
    )
    api_spec = None
    if cached_decision.verdict == "fresh":
        api_spec = _run_async(_load_cached_spec(spec_url))
    if api_spec is None:
        try:
            parser = OpenAPIParser()
            api_spec = parser.parse_from_url(spec_url)
        except Exception as e:
            logger.error(
                "Failed to parse OpenAPI spec from %s: %s",
                spec_url, e, exc_info=True,
            )
            return {"success": False, "error": f"Failed to parse API spec: {e!s}"}
        # Write-through cache the parsed spec.
        _run_async(
            _store_cached_spec(
                spec_url, api_spec, ttl_seconds=OPENAPI_SPEC_TTL_SECONDS
            )
        )
```

Delete the existing `parser = OpenAPIParser()` block that used to live where the new cache-first block now goes.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_openapi_spec_cache.py -v --tb=short
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/api_connector.py tests/unit/agents/operations/test_openapi_spec_cache.py
git commit -m "feat(120-02): cache OpenAPI spec parses with 24h TTL around connect_api (GREEN)"
```

### Task 3: Integration health-check cache (TDD)

**Files:**
- Create: `tests/unit/agents/operations/test_integration_health_cache.py`
- Modify: `app/agents/tools/integration_setup.py`

`check_integration_status` currently re-runs `config.is_*_configured` on
every call. Cache the per-service `(configured, last_checked, details)`
tuple for 5 minutes to bunch repeated calls into 5-min windows.

- [ ] **Step 1: Failing unit tests**

Create `tests/unit/agents/operations/test_integration_health_cache.py`:

```python
"""Unit tests for the integration health-check cache around check_integration_status."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_check_cache_hit_skips_probe():
    """Cache hit: live config.is_*_configured probes are NOT called."""
    from app.agents.tools import integration_setup

    fresh = MagicMock(verdict="fresh", freshness_hours=0.05)  # 3min old
    cached_status = {
        "hubspot": {"configured": True, "details": "ok"},
    }

    with (
        patch(
            "app.agents.tools.integration_setup.should_call_external",
            new=AsyncMock(return_value=fresh),
        ),
        patch(
            "app.agents.tools.integration_setup._load_cached_health",
            new=AsyncMock(return_value=cached_status),
        ),
        patch(
            "app.agents.tools.integration_setup._probe_integration_health",
        ) as mock_probe,
    ):
        result = integration_setup.check_integration_status(user_id="u123")
        # Probe MUST NOT have been called when cache is fresh.
        mock_probe.assert_not_called()
        assert "hubspot" in result.get("integrations", result)


@pytest.mark.asyncio
async def test_health_check_cache_miss_writes_with_300s_ttl():
    """Cache miss: live probe + cache write with TTL 300."""
    from app.agents.tools import integration_setup

    miss = MagicMock(verdict="miss", freshness_hours=None)
    probed = {"hubspot": {"configured": True, "details": "probed"}}
    store_mock = AsyncMock()

    with (
        patch(
            "app.agents.tools.integration_setup.should_call_external",
            new=AsyncMock(return_value=miss),
        ),
        patch(
            "app.agents.tools.integration_setup._load_cached_health",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.agents.tools.integration_setup._store_cached_health",
            new=store_mock,
        ),
        patch(
            "app.agents.tools.integration_setup._probe_integration_health",
            return_value=probed,
        ),
    ):
        integration_setup.check_integration_status(user_id="u123")
        store_mock.assert_called_once()
        args, kwargs = store_mock.call_args
        assert kwargs.get("ttl_seconds") == 300 or (
            len(args) >= 2 and args[-1] == 300
        )


def test_integration_health_key_normalises_service_id():
    """Service ids with mixed case / non-slug chars normalise consistently."""
    from app.agents.operations._cache_keys import integration_health_key

    a = integration_health_key("HubSpot")
    b = integration_health_key("hubspot")
    assert a == b
    with pytest.raises(ValueError):
        integration_health_key("")
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/operations/test_integration_health_cache.py -v --tb=short
```

- [ ] **Step 3: Wire the cache into `check_integration_status`**

Modify `app/agents/tools/integration_setup.py`. Add helpers near the top
imports:

```python
import asyncio
import json
from app.agents.operations._cache_keys import (
    INTEGRATION_HEALTH_TTL_SECONDS,
    integration_health_key,
)
from app.services.intelligence import should_call_external


# Single shared key for the all-integrations snapshot used by check_integration_status.
# Per-service entries (used by validate_api_connection in Task 4) use a different
# key shape — this one is the "snapshot" view.
_ALL_INTEGRATIONS_SNAPSHOT_KEY = "integration_health:_snapshot"


async def _load_cached_health(user_id: str | None):
    """Return the cached snapshot dict or None on miss/error."""
    try:
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        key = (
            f"{_ALL_INTEGRATIONS_SNAPSHOT_KEY}:{user_id}"
            if user_id
            else _ALL_INTEGRATIONS_SNAPSHOT_KEY
        )
        value, _age = await cache.get_with_age(key)
        if value is None:
            return None
        return value if isinstance(value, dict) else json.loads(value)
    except Exception:
        return None


async def _store_cached_health(user_id: str | None, payload: dict, *, ttl_seconds: int) -> None:
    """Persist the snapshot dict with TTL."""
    try:
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        key = (
            f"{_ALL_INTEGRATIONS_SNAPSHOT_KEY}:{user_id}"
            if user_id
            else _ALL_INTEGRATIONS_SNAPSHOT_KEY
        )
        await cache.set(key, payload, ttl_seconds=ttl_seconds)
    except Exception:
        pass


def _probe_integration_health(user_id: str | None) -> dict:
    """Run the live probe path — the existing check_integration_status body
    minus the return statement. Extracted for testability."""
    # NOTE during implementation: lift lines that currently sit inside
    # check_integration_status (the build of `statuses`) into this helper
    # verbatim. Return the statuses dict.
    from app.mcp.built_in_research import is_provider_available_to_all_users  # noqa: F401
    from app.mcp.config import get_mcp_config
    from app.workflows.contract_defaults import INTEGRATION_SETUP_GUIDE
    config = get_mcp_config()
    statuses = {
        # ... preserve the exact build from the original function ...
    }
    return statuses


def _run_async(coro):
    """Same bridge pattern as api_connector — sync ADK tool, async cache."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)
```

Replace the body of `check_integration_status` so that:

```python
def check_integration_status(user_id: str | None = None) -> dict[str, Any]:
    """[... existing docstring ...]"""
    decision = _run_async(
        should_call_external(
            cache_key=(
                f"{_ALL_INTEGRATIONS_SNAPSHOT_KEY}:{user_id}"
                if user_id
                else _ALL_INTEGRATIONS_SNAPSHOT_KEY
            ),
            ttl_seconds=INTEGRATION_HEALTH_TTL_SECONDS,
        )
    )
    statuses = None
    if decision.verdict == "fresh":
        statuses = _run_async(_load_cached_health(user_id))
    if statuses is None:
        statuses = _probe_integration_health(user_id)
        _run_async(
            _store_cached_health(
                user_id, statuses, ttl_seconds=INTEGRATION_HEALTH_TTL_SECONDS
            )
        )
    # Build and return the summary exactly as the original function did,
    # but using `statuses` from cache-or-probe.
    return _build_status_response(statuses)
```

Move the existing summary-build code path into a private `_build_status_response(statuses)` helper for clarity. Preserve the response shape (`integrations`, `summary`, etc.) byte-for-byte modulo timestamps.

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_integration_health_cache.py -v --tb=short
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/integration_setup.py tests/unit/agents/operations/test_integration_health_cache.py
git commit -m "feat(120-02): cache integration health snapshot with 5min TTL (GREEN)"
```

### Task 4: Endpoint metadata cache (TDD)

**Files:**
- Create: `tests/unit/agents/operations/test_endpoint_metadata_cache.py`
- Modify: `app/agents/tools/api_connector.py` (extend `validate_api_connection` and `list_api_connections` to consult the cache)

`endpoint_metadata:{connector_id}` caches the post-codegen view of an
API connector: list of `(name, description, endpoint)` tuples + the
spec URL + the endpoint count at registration time. TTL is 7 days
because connector metadata changes only on `connect_api` or
`disconnect_api`. Reading `list_api_connections` should hit Redis,
not Supabase, for connectors whose entries are <7d old.

- [ ] **Step 1: Failing unit tests**

Create `tests/unit/agents/operations/test_endpoint_metadata_cache.py`:

```python
"""Unit tests for endpoint_metadata Redis cache around api_connector tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_endpoint_metadata_key_shape():
    """endpoint_metadata_key produces the expected prefix and slug."""
    from app.agents.operations._cache_keys import endpoint_metadata_key

    assert endpoint_metadata_key("Stripe").startswith("endpoint_metadata:")
    assert endpoint_metadata_key("Stripe") == endpoint_metadata_key("stripe")
    with pytest.raises(ValueError):
        endpoint_metadata_key("")


@pytest.mark.asyncio
async def test_validate_api_connection_uses_cached_metadata():
    """validate_api_connection skips Supabase read when metadata is cached."""
    from app.agents.tools import api_connector

    fresh = MagicMock(verdict="fresh", freshness_hours=12.0)  # 12h old, < 7d
    cached_metadata = {
        "api_name": "stripe",
        "spec_url": "https://stripe.example/openapi.json",
        "endpoint_count": 7,
    }

    with (
        patch(
            "app.agents.tools.api_connector.should_call_external",
            new=AsyncMock(return_value=fresh),
        ),
        patch(
            "app.agents.tools.api_connector._load_cached_endpoint_metadata",
            new=AsyncMock(return_value=cached_metadata),
        ),
        patch(
            "app.services.supabase_client.get_service_client"
        ) as mock_supabase,
    ):
        result = api_connector.validate_api_connection("stripe")
        # On a fresh cache hit, Supabase MUST NOT be consulted.
        mock_supabase.assert_not_called()
        assert result.get("success") is True
        assert result.get("api_name") == "stripe"


@pytest.mark.asyncio
async def test_connect_api_writes_endpoint_metadata_on_success():
    """A successful connect_api writes endpoint_metadata with TTL 604800."""
    from app.agents.tools import api_connector

    store_mock = AsyncMock()
    with (
        patch(
            "app.agents.tools.api_connector._store_cached_endpoint_metadata",
            new=store_mock,
        ),
        # Stub out the rest of the connect_api dependencies — we're checking
        # only the cache-write side-effect.
        patch("app.skills.api_parser.validate_url", return_value=True),
        patch(
            "app.skills.api_parser.OpenAPIParser.parse_from_url",
            return_value=MagicMock(
                title="X",
                endpoints=[MagicMock(operation_id="op1", method="GET", path="/a")],
            ),
        ),
        patch(
            "app.skills.api_codegen.APIToolGenerator.generate_batch",
            return_value=[],
        ),
        patch(
            "app.agents.tools.api_connector.should_call_external",
            new=AsyncMock(return_value=MagicMock(verdict="miss")),
        ),
        patch(
            "app.agents.tools.api_connector._load_cached_spec",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.agents.tools.api_connector._store_cached_spec",
            new=AsyncMock(),
        ),
    ):
        api_connector.connect_api(spec_url="https://x.example/spec", api_name="x")
        store_mock.assert_called_once()
        args, kwargs = store_mock.call_args
        assert kwargs.get("ttl_seconds") == 604800 or (
            args and args[-1] == 604800
        )
```

- [ ] **Step 2: Run — should FAIL**

```powershell
uv run pytest tests/unit/agents/operations/test_endpoint_metadata_cache.py -v --tb=short
```

- [ ] **Step 3: Implement**

Add to `app/agents/tools/api_connector.py`:

```python
from app.agents.operations._cache_keys import (
    ENDPOINT_METADATA_TTL_SECONDS,
    endpoint_metadata_key,
)


async def _load_cached_endpoint_metadata(connector_id: str):
    try:
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        value, _age = await cache.get_with_age(endpoint_metadata_key(connector_id))
        if value is None:
            return None
        return value if isinstance(value, dict) else json.loads(value)
    except Exception:
        return None


async def _store_cached_endpoint_metadata(
    connector_id: str, payload: dict, *, ttl_seconds: int
) -> None:
    try:
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        await cache.set(
            endpoint_metadata_key(connector_id), payload, ttl_seconds=ttl_seconds
        )
    except Exception:
        pass
```

In `connect_api`, after the successful tool-registration loop and just before the return, add:

```python
    _run_async(
        _store_cached_endpoint_metadata(
            api_name,
            {
                "api_name": api_name,
                "api_title": api_spec.title,
                "spec_url": spec_url,
                "endpoint_count": len(created),
                "tools": [t["name"] for t in created],
            },
            ttl_seconds=ENDPOINT_METADATA_TTL_SECONDS,
        )
    )
```

In `validate_api_connection`, replace the opening Supabase fetch with a cache-first lookup:

```python
def validate_api_connection(api_name: str) -> dict[str, Any]:
    """[... existing docstring ...]"""
    if not api_name:
        return {"success": False, "error": "api_name is required"}

    decision = _run_async(
        should_call_external(
            cache_key=endpoint_metadata_key(api_name),
            ttl_seconds=ENDPOINT_METADATA_TTL_SECONDS,
        )
    )
    cached = None
    if decision.verdict == "fresh":
        cached = _run_async(_load_cached_endpoint_metadata(api_name))
    if cached:
        return {
            "success": True,
            "api_name": cached["api_name"],
            "status": "healthy",
            "spec_url": cached.get("spec_url", ""),
            "connected_tools": cached.get("endpoint_count", 0),
            "message": (
                f"Connection metadata cached "
                f"({cached.get('endpoint_count', 0)} tool(s) — re-verify via "
                "explicit refresh if needed)."
            ),
        }
    # ... existing Supabase + spec-fetch path unchanged ...
```

- [ ] **Step 4: Re-run — should PASS**

```powershell
uv run pytest tests/unit/agents/operations/test_endpoint_metadata_cache.py -v --tb=short
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/api_connector.py tests/unit/agents/operations/test_endpoint_metadata_cache.py
git commit -m "feat(120-02): cache endpoint metadata with 7d TTL on connect_api/validate (GREEN)"
```

### Task 5: Integration test — live Redis, real load reduction

**Files:**
- Create: `tests/integration/test_operations_cache_load.py`

The spec acceptance bar is "OpenAPI spec re-fetches reduced ≥50% on
synthetic load" and "integration health checks bunched into 5-min
windows (≥40% rate reduction)." This integration test proves both.

- [ ] **Step 1: Write the load test**

Create `tests/integration/test_operations_cache_load.py`:

```python
"""Integration test: cache load reduction against live Redis.

Acceptance:
- OpenAPI spec re-fetches reduced >=50% on a 20-call synthetic burst
- Integration health checks reduced >=40% on a 20-call burst
"""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("REDIS_HOST"),
        reason="REDIS_HOST not set; skipping live-Redis load test",
    ),
]


def test_openapi_spec_cache_reduces_parse_calls_by_50pct():
    """20 connect_api calls to the same spec URL → 1 parse + 19 cache hits."""
    from app.agents.tools import api_connector

    parse_calls = {"n": 0}

    def _counting_parse(url):
        parse_calls["n"] += 1
        return MagicMock(
            title="X",
            endpoints=[MagicMock(operation_id="op1", method="GET", path="/a")],
        )

    with (
        patch("app.skills.api_parser.validate_url", return_value=True),
        patch(
            "app.skills.api_parser.OpenAPIParser.parse_from_url",
            side_effect=_counting_parse,
        ),
        patch(
            "app.skills.api_codegen.APIToolGenerator.generate_batch",
            return_value=[],
        ),
    ):
        # Use a deterministic URL so the cache key is stable across iterations.
        url = "https://load-test.example.invalid/openapi.json"
        for _ in range(20):
            api_connector.connect_api(spec_url=url, api_name="loadtest")

    # Acceptance: at MOST 10 actual parses out of 20 calls (>=50% reduction).
    # Realistically we expect 1 (perfect cache); we allow up to 10 to absorb
    # any first-call seeding and cache eviction surprises.
    assert parse_calls["n"] <= 10, (
        f"OpenAPI parse calls = {parse_calls['n']} / 20 — "
        "spec cache failed to achieve >=50% reduction"
    )


def test_integration_health_cache_reduces_probe_calls_by_40pct():
    """20 check_integration_status calls in <5min → cache absorbs >=8 probes."""
    from app.agents.tools import integration_setup

    probe_calls = {"n": 0}

    def _counting_probe(user_id):
        probe_calls["n"] += 1
        return {"hubspot": {"configured": True, "details": "ok"}}

    with patch(
        "app.agents.tools.integration_setup._probe_integration_health",
        side_effect=_counting_probe,
    ):
        for _ in range(20):
            integration_setup.check_integration_status(user_id="loadtest_user")

    # Acceptance: at MOST 12 actual probes out of 20 calls (>=40% reduction).
    assert probe_calls["n"] <= 12, (
        f"Integration probe calls = {probe_calls['n']} / 20 — "
        "health cache failed to achieve >=40% reduction"
    )
```

- [ ] **Step 2: Run with live Redis**

```powershell
docker compose up -d redis
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:REDIS_PASSWORD = "pikar_dev_redis"
uv run pytest tests/integration/test_operations_cache_load.py -v --tb=short
```

Expected: both tests PASS. Parse calls ≤10/20, probe calls ≤12/20.

If a test fails, the likely cause is the `_run_async` bridge not actually
hitting Redis in some scenarios. Add `print(decision.verdict)` inside
the `connect_api` / `check_integration_status` body to confirm the
verdicts seen across the 20 iterations.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_operations_cache_load.py
git commit -m "test(120-02): synthetic load test — OpenAPI >=50% + health >=40% reduction"
```

### Task 6: Smoke test — agent still loads, manifest unchanged

**Files:** none (verification only)

- [ ] **Step 1: Confirm Operations Agent assembly**

```powershell
uv run python -c "from app.agents.operations.agent import create_operations_agent; a = create_operations_agent(); print(len(a.tools) if hasattr(a, 'tools') else 'no-tools-attr'); print(type(a).__name__)"
```

Expected: `PikarBaseAgent` and the tool count is the same as
pre-120-02 (the manifest in `app/agents/operations/tools.py` did NOT
change). If the count drifted, something in Task 2-4 accidentally
removed a tool — STOP and reverse the unintended edit.

- [ ] **Step 2: Confirm ADK tool registry is unchanged**

```powershell
uv run python -c "from app.agents.tools.api_connector import API_CONNECTOR_TOOLS; print([t.__name__ for t in API_CONNECTOR_TOOLS])"
```

Expected: `['connect_api', 'list_api_connections', 'disconnect_api', 'validate_api_connection']`. No new tool names. Plan 120-02 is library-first.

- [ ] **Step 3: No commit (smoke only).**

### Task 7: Lint + acceptance sign-off

- [ ] **Step 1: Ruff check + format**

```powershell
uv run ruff check app/agents/operations/_cache_keys.py app/agents/tools/api_connector.py app/agents/tools/integration_setup.py tests/unit/agents/operations/test_openapi_spec_cache.py tests/unit/agents/operations/test_integration_health_cache.py tests/unit/agents/operations/test_endpoint_metadata_cache.py tests/integration/test_operations_cache_load.py
uv run ruff format app/agents/operations/_cache_keys.py app/agents/tools/api_connector.py app/agents/tools/integration_setup.py tests/unit/agents/operations/test_openapi_spec_cache.py tests/unit/agents/operations/test_integration_health_cache.py tests/unit/agents/operations/test_endpoint_metadata_cache.py tests/integration/test_operations_cache_load.py --check
```

Fix in place. If format produced changes:

```bash
git add app/agents/tools/api_connector.py app/agents/tools/integration_setup.py app/agents/operations/_cache_keys.py tests/unit/agents/operations/ tests/integration/test_operations_cache_load.py
git commit -m "style(120-02): ruff format pass over cache wiring + tests"
```

- [ ] **Step 2: Run the full operations test suite**

```powershell
uv run pytest tests/unit/agents/operations/ -v --tb=short
```

Expected: existing operations tests (`test_create_operations_agent`, etc.) still green + 10 new cache tests pass.

- [ ] **Step 3: Plan 120-02 acceptance**

| Acceptance line | Verified by |
|---|---|
| `openapi_spec:{hash}` Redis key + 24h TTL | Task 1 + Task 2 |
| `integration_health:{service_id}` + 5min TTL | Task 1 + Task 3 |
| `endpoint_metadata:{connector_id}` + 7d TTL | Task 1 + Task 4 |
| Graph-tier freshness threshold = 24h documented | `INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS` constant (used in 120-03) |
| OpenAPI spec re-fetches reduced ≥50% on synthetic load | Task 5 `test_openapi_spec_cache_reduces_parse_calls_by_50pct` |
| Integration health checks reduced ≥40% on synthetic load | Task 5 `test_integration_health_cache_reduces_probe_calls_by_40pct` |
| Redis-failure path degrades silently | Task 2 `test_connect_api_redis_failure_falls_back_to_live_fetch` |
| No new ADK tools | Task 6 Step 2 |
| Operations Agent still loads | Task 6 Step 1 |
| Lint clean | Task 7 Step 1 |

- [ ] **Step 4: Plan 120-02 complete. Hand off cache surface to Plan 120-03 — claim emission will consult `INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS` and the per-claim `expires_at` policy from the vocabulary doc.**

---

## Spec coverage check

| Spec requirement (from Phase 120 design) | Task |
|---|---|
| OpenAPI spec parse cache (TTL 24h) | Tasks 1, 2 |
| Integration health-check cache (TTL 5min) | Tasks 1, 3 |
| Endpoint metadata cache (TTL 7d) | Tasks 1, 4 |
| Graph tier: 24h freshness threshold | Task 1 (`INTEGRATION_HEALTH_GRAPH_FRESHNESS_HOURS` constant) |
| OpenAPI re-fetches reduced ≥50% on synthetic load | Task 5 |
| Integration health checks bunched into 5-min windows (≥40% rate reduction) | Task 5 |
| No new ADK tools | Task 6 |
| Lint clean | Task 7 |

All spec lines for 120-02 covered.

---

## Ambiguities (for caller / reviewer)

1. **OpenAPI cache invalidation — pure TTL vs event-driven on spec changes?**
   This plan defaults to **pure TTL** (24h). The spec doesn't explicitly say.
   Rationale documented under "Cache invalidation policy" at the top of the
   plan: (a) most upstream specs are public URLs without webhook
   infrastructure, (b) spec change rate in practice is well below 1/day, (c)
   `validate_api_connection` already detects drift via endpoint-count diff.
   If a Plan 120-03 reviewer or a future stakeholder wants event-driven
   invalidation (e.g., admin "reconnect now" UI), that adds explicit
   `cache_service.delete(openapi_spec_key(url))` calls without changing the
   cache surface itself — additive, no rework of Plan 120-02.

2. **Snapshot key vs per-service health key.**
   `check_integration_status` returns a *snapshot* of every integration at
   once, so this plan caches the whole snapshot under a single key
   (`integration_health:_snapshot[:user_id]`). `validate_api_connection`
   targets one connector at a time and uses `endpoint_metadata:{connector_id}`.
   A future plan could refactor health caching to per-service keys for finer
   invalidation; left out here to minimise scope drift.

3. **`_run_async` bridge.** ADK tools run synchronously but the Phase 112
   cache surface is async. This plan ships a pragmatic
   `concurrent.futures.ThreadPoolExecutor + asyncio.run` bridge inside each
   sync tool. A future cleanup could move the cache surface to a sync
   client, or push the tools to async — out of scope here.
