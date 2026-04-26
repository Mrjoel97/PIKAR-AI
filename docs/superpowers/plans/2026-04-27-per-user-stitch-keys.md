# Per-User Stitch Keys + Always-Active Tavily/Firecrawl — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global Stitch MCP singleton with a per-user pool, treat Tavily/Firecrawl as always-active platform-managed integrations.

**Architecture:** A `StitchPool` keyed by `user:{user_id}` (or `__env_default__` fallback) lazily spawns `StitchMCPService` subprocesses. Each user's saved `STITCH_API_KEY` lives in `user_configurations`. Per-request key resolution is user-saved → env → mock → error. Tavily/Firecrawl are always rendered as active in the Configuration UI; their backend logic is unchanged.

**Tech Stack:** FastAPI + asyncio, MCP Python SDK (stdio), Supabase Python client (sync), pytest + `pytest-asyncio`, Next.js 16 / React 19 frontend.

**Spec:** `docs/superpowers/specs/2026-04-27-per-user-stitch-keys-design.md`

## File map

**Created:**
- `app/services/user_config.py` — read/write helpers for `user_configurations` API keys
- `tests/unit/services/test_user_config.py` — unit tests for the helpers
- `tests/unit/app_builder/test_stitch_pool.py` — unit tests for `StitchPool`
- `tests/unit/test_configuration_save_api_key.py` — endpoint tests for `POST /configuration/save-api-key`

**Modified:**
- `app/services/stitch_mcp.py` — add `api_key` param to `StitchMCPService`, add `StitchPool`, make `get_stitch_service` async
- `app/fast_api_app.py` — lifespan replaces singleton init with pool init + evict-loop
- `app/agents/tools/app_builder.py` — `await get_stitch_service(user_id)`
- `app/routers/app_builder.py` — `await get_stitch_service(user_id)`
- `app/services/multi_page_service.py` — `await get_stitch_service(user_id)`
- `app/services/iteration_service.py` — `await get_stitch_service(user_id)`
- `app/services/screen_generation_service.py` — `await get_stitch_service(user_id)`
- `app/routers/configuration.py` — new `POST /configuration/save-api-key`, status logic for Stitch + Tavily/Firecrawl
- `frontend/src/app/api/configuration/save-api-key/route.ts` — repoint at the new dedicated backend endpoint
- `frontend/src/app/dashboard/configuration/page.tsx` — always-active rendering for Tavily/Firecrawl
- `tests/unit/app_builder/test_stitch_mcp_service.py` — update existing tests for the new `api_key` constructor argument

---

## Task 1: `user_config` helpers

**Files:**
- Create: `app/services/user_config.py`
- Test: `tests/unit/services/test_user_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/services/test_user_config.py
"""Unit tests for user_config helpers — Supabase client mocked."""
from unittest.mock import MagicMock, patch


def _mock_table(rows: list[dict]) -> MagicMock:
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.limit.return_value = table
    table.execute.return_value = MagicMock(data=rows)
    table.upsert.return_value = table
    return table


def test_get_user_api_key_returns_value_when_row_exists():
    from app.services import user_config

    table = _mock_table([{"config_value": "tvly-secret"}])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        assert user_config.get_user_api_key("u1", "STITCH_API_KEY") == "tvly-secret"

    client.table.assert_called_with("user_configurations")
    table.eq.assert_any_call("user_id", "u1")
    table.eq.assert_any_call("config_key", "STITCH_API_KEY")


def test_get_user_api_key_returns_none_when_no_row():
    from app.services import user_config

    table = _mock_table([])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        assert user_config.get_user_api_key("u1", "STITCH_API_KEY") is None


def test_get_user_api_key_returns_none_for_blank_value():
    from app.services import user_config

    table = _mock_table([{"config_value": "   "}])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        assert user_config.get_user_api_key("u1", "STITCH_API_KEY") is None


def test_set_user_api_key_upserts_with_is_sensitive_true():
    from app.services import user_config

    table = _mock_table([])
    client = MagicMock()
    client.table.return_value = table

    with patch.object(user_config, "get_service_client", return_value=client):
        user_config.set_user_api_key("u1", "STITCH_API_KEY", "tvly-secret")

    table.upsert.assert_called_once()
    payload = table.upsert.call_args.args[0]
    assert payload["user_id"] == "u1"
    assert payload["config_key"] == "STITCH_API_KEY"
    assert payload["config_value"] == "tvly-secret"
    assert payload["is_sensitive"] is True
    assert table.upsert.call_args.kwargs.get("on_conflict") == "user_id,config_key"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/services/test_user_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.user_config'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/user_config.py
"""Per-user API key storage helpers backed by `user_configurations`.

Keys are stored with `is_sensitive=true`. Reads bypass RLS via the service-role
client. Both helpers are synchronous because the Supabase Python client is sync.
"""

from app.services.supabase import get_service_client


def get_user_api_key(user_id: str, key_name: str) -> str | None:
    """Return the user's stored API key, or None if unset/blank."""
    client = get_service_client()
    result = (
        client.table("user_configurations")
        .select("config_value")
        .eq("user_id", user_id)
        .eq("config_key", key_name)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    raw = result.data[0].get("config_value")
    if not raw:
        return None
    stripped = raw.strip()
    return stripped or None


def set_user_api_key(user_id: str, key_name: str, api_key: str) -> None:
    """Upsert a user's API key with `is_sensitive=true`."""
    client = get_service_client()
    client.table("user_configurations").upsert(
        {
            "user_id": user_id,
            "config_key": key_name,
            "config_value": api_key,
            "is_sensitive": True,
        },
        on_conflict="user_id,config_key",
    ).execute()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/services/test_user_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/user_config.py tests/unit/services/test_user_config.py
git commit -m "feat(user_config): add per-user API key read/write helpers"
```

---

## Task 2: `StitchMCPService.__init__(api_key)`

**Files:**
- Modify: `app/services/stitch_mcp.py:43-79`
- Modify: `tests/unit/app_builder/test_stitch_mcp_service.py:8-13`

- [ ] **Step 1: Update existing test to pass an explicit key**

In `tests/unit/app_builder/test_stitch_mcp_service.py`, replace the body of `test_is_ready_false_before_run` to verify the new constructor:

```python
def test_is_ready_false_before_run():
    """Service starts not-ready before _run() initializes the session."""
    from app.services.stitch_mcp import StitchMCPService

    s = StitchMCPService(api_key="tvly-test")
    assert s.is_ready() is False
    assert s._api_key == "tvly-test"
```

- [ ] **Step 2: Add new test for default key=None backwards-compat**

Append at the end of `tests/unit/app_builder/test_stitch_mcp_service.py`:

```python
def test_service_falls_back_to_env_when_no_explicit_key(monkeypatch):
    """When constructor api_key is None, _run reads STITCH_API_KEY from env."""
    from app.services.stitch_mcp import StitchMCPService

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    s = StitchMCPService()  # api_key=None
    assert s._api_key is None  # not captured at init
```

- [ ] **Step 3: Run tests to verify the first one fails**

Run: `uv run pytest tests/unit/app_builder/test_stitch_mcp_service.py::test_is_ready_false_before_run -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'api_key'`

- [ ] **Step 4: Update `StitchMCPService` to accept an explicit api_key**

In `app/services/stitch_mcp.py`, modify the `__init__` and `_run` methods:

```python
class StitchMCPService:
    """Singleton owning the Stitch MCP subprocess for the FastAPI process lifetime."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialise the service. If api_key is None, _run() falls back to env."""
        self._api_key = api_key
        self._session = None
        self._lock = asyncio.Lock()
        self._ready = anyio.Event()
        self._healthy = True

    async def _run(self) -> None:
        """Background coroutine — holds stdio_client + ClientSession open until cancelled."""
        from mcp import ClientSession, StdioServerParameters, stdio_client

        stitch_key = self._api_key or os.environ.get("STITCH_API_KEY", "")
        params = StdioServerParameters(
            command="npx",
            args=["@_davideast/stitch-mcp", "proxy"],
            env={**os.environ, "STITCH_API_KEY": stitch_key},
            cwd=None,
        )
        # ... (rest of the method unchanged)
```

Also update `MockStitchMCPService.__init__` to call `super().__init__(api_key=None)`:

```python
class MockStitchMCPService(StitchMCPService):
    """Testing-only Stitch replacement that returns local data-URL previews."""

    def __init__(self) -> None:
        super().__init__(api_key=None)
        self._projects: dict[str, dict[str, Any]] = {}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_stitch_mcp_service.py -v`
Expected: 6 passed (4 existing + 1 updated + 1 new)

- [ ] **Step 6: Commit**

```bash
git add app/services/stitch_mcp.py tests/unit/app_builder/test_stitch_mcp_service.py
git commit -m "refactor(stitch): accept explicit api_key in StitchMCPService"
```

---

## Task 3: `StitchPool.get_or_spawn` — first-call spawn

**Files:**
- Modify: `app/services/stitch_mcp.py` (append `StitchPool` class)
- Create: `tests/unit/app_builder/test_stitch_pool.py`

- [ ] **Step 1: Write failing test for resolve-key precedence**

```python
# tests/unit/app_builder/test_stitch_pool.py
"""Unit tests for StitchPool — covers key resolution and spawn behavior."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_resolve_key_user_saved_takes_precedence(monkeypatch):
    """If user has a saved key, pool key is user:{user_id} and api_key is theirs."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    pool = StitchPool()

    with patch(
        "app.services.user_config.get_user_api_key", return_value="user-key"
    ):
        pool_key, api_key, fp = pool._resolve_key("u1")

    assert pool_key == "user:u1"
    assert api_key == "user-key"
    assert fp == pool._fingerprint("user-key")


def test_resolve_key_falls_back_to_env(monkeypatch):
    """If no user key, env key wins; pool key is __env_default__."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    pool = StitchPool()

    with patch(
        "app.services.user_config.get_user_api_key", return_value=None
    ):
        pool_key, api_key, fp = pool._resolve_key("u1")

    assert pool_key == StitchPool.POOL_KEY_ENV
    assert api_key == "env-key"


def test_resolve_key_falls_back_to_mock(monkeypatch):
    """If no user/env key but mock enabled, pool key is __mock__."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.setenv("APP_BUILDER_USE_MOCK_STITCH", "1")
    pool = StitchPool()

    pool_key, api_key, _ = pool._resolve_key(None)
    assert pool_key == StitchPool.POOL_KEY_MOCK
    assert api_key is None


def test_resolve_key_raises_when_nothing_configured(monkeypatch):
    """No user key, no env key, no mock — raise RuntimeError."""
    from app.services.stitch_mcp import StitchPool

    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.delenv("APP_BUILDER_USE_MOCK_STITCH", raising=False)
    pool = StitchPool()

    with pytest.raises(RuntimeError, match="No Stitch API key configured"):
        pool._resolve_key(None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_stitch_pool.py -v`
Expected: FAIL — `cannot import name 'StitchPool' from 'app.services.stitch_mcp'`

- [ ] **Step 3: Append `StitchPool` skeleton + `_resolve_key` to `stitch_mcp.py`**

Add at the bottom of `app/services/stitch_mcp.py` (above `get_stitch_service`):

```python
import hashlib
import time


class StitchPool:
    """Per-user pool of StitchMCPService subprocesses.

    Resolution order: user-saved key → env key → mock → error.
    Lazy spawn under a single lock; idle eviction at 10-min TTL.
    """

    POOL_KEY_ENV = "__env_default__"
    POOL_KEY_MOCK = "__mock__"

    def __init__(self, evict_ttl_seconds: int = 600) -> None:
        self._services: dict[str, StitchMCPService] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._fingerprints: dict[str, str] = {}
        self._last_used: dict[str, float] = {}
        self._spawn_lock = asyncio.Lock()
        self._evict_ttl = evict_ttl_seconds
        self._evict_task: asyncio.Task[None] | None = None

    @staticmethod
    def _fingerprint(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]

    def _resolve_key(
        self, user_id: str | None
    ) -> tuple[str, str | None, str]:
        """Return (pool_key, api_key, fingerprint). Raises if nothing configured."""
        if user_id:
            from app.services.user_config import get_user_api_key

            user_key = get_user_api_key(user_id, "STITCH_API_KEY")
            if user_key:
                return f"user:{user_id}", user_key, self._fingerprint(user_key)
        env_key = (os.environ.get("STITCH_API_KEY") or "").strip()
        if env_key:
            return self.POOL_KEY_ENV, env_key, self._fingerprint(env_key)
        if should_use_mock_stitch_service():
            return self.POOL_KEY_MOCK, None, "mock"
        raise RuntimeError(
            "No Stitch API key configured. Connect your Stitch key in Configuration."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_stitch_pool.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/stitch_mcp.py tests/unit/app_builder/test_stitch_pool.py
git commit -m "feat(stitch): add StitchPool with key resolution"
```

---

## Task 4: `StitchPool.get_or_spawn` body

**Files:**
- Modify: `app/services/stitch_mcp.py` (extend `StitchPool`)
- Modify: `tests/unit/app_builder/test_stitch_pool.py` (add tests)

- [ ] **Step 1: Add tests for spawn / reuse / fingerprint mismatch**

Append to `tests/unit/app_builder/test_stitch_pool.py`:

```python
class _FakeService:
    """Test double that mimics StitchMCPService without a subprocess."""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self._healthy = True
        self._ready_set = False

    async def _run(self):
        self._ready_set = True
        await asyncio.sleep(3600)  # block forever; cancelled at shutdown

    def is_ready(self):
        return self._ready_set and self._healthy


def _patch_service_classes(monkeypatch):
    """Replace real service classes with fakes that don't spawn subprocesses."""
    from app.services import stitch_mcp

    # Wire StitchPool.get_or_spawn to a synthetic ready event
    async def _fake_run(self):
        self._session = MagicMock()
        self._healthy = True
        self._ready.set()
        await asyncio.sleep(3600)

    monkeypatch.setattr(stitch_mcp.StitchMCPService, "_run", _fake_run)


@pytest.mark.asyncio
async def test_get_or_spawn_spawns_once_and_reuses(monkeypatch):
    """First call spawns; second call returns the same service."""
    _patch_service_classes(monkeypatch)
    monkeypatch.setenv("STITCH_API_KEY", "env-key")

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool()
    with patch(
        "app.services.user_config.get_user_api_key", return_value=None
    ):
        s1 = await pool.get_or_spawn("u1")
        s2 = await pool.get_or_spawn("u1")

    assert s1 is s2
    assert StitchPool.POOL_KEY_ENV in pool._services
    await pool.shutdown()


@pytest.mark.asyncio
async def test_get_or_spawn_two_users_two_pools(monkeypatch):
    """Different users with different saved keys get different pool entries."""
    _patch_service_classes(monkeypatch)
    monkeypatch.delenv("STITCH_API_KEY", raising=False)

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool()

    def _per_user_key(user_id, key_name):
        return f"key-for-{user_id}"

    with patch(
        "app.services.user_config.get_user_api_key", side_effect=_per_user_key
    ):
        s1 = await pool.get_or_spawn("u1")
        s2 = await pool.get_or_spawn("u2")

    assert s1 is not s2
    assert "user:u1" in pool._services
    assert "user:u2" in pool._services
    await pool.shutdown()


@pytest.mark.asyncio
async def test_get_or_spawn_respawns_on_fingerprint_change(monkeypatch):
    """When the user's saved key changes, the pool respawns the service."""
    _patch_service_classes(monkeypatch)
    monkeypatch.delenv("STITCH_API_KEY", raising=False)

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool()

    keys = iter(["old-key", "new-key"])
    with patch(
        "app.services.user_config.get_user_api_key",
        side_effect=lambda u, k: next(keys),
    ):
        s1 = await pool.get_or_spawn("u1")
        s2 = await pool.get_or_spawn("u1")

    assert s1 is not s2
    await pool.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_stitch_pool.py -v`
Expected: FAIL — `AttributeError: 'StitchPool' object has no attribute 'get_or_spawn'`

- [ ] **Step 3: Implement `get_or_spawn` and `shutdown`**

In `app/services/stitch_mcp.py`, add to the `StitchPool` class:

```python
    async def get_or_spawn(
        self, user_id: str | None = None
    ) -> "StitchMCPService":
        """Return a ready service for this user, spawning if necessary."""
        pool_key, api_key, fingerprint = self._resolve_key(user_id)

        existing = self._services.get(pool_key)
        if (
            existing is not None
            and existing.is_ready()
            and self._fingerprints.get(pool_key) == fingerprint
        ):
            self._last_used[pool_key] = time.monotonic()
            return existing

        async with self._spawn_lock:
            existing = self._services.get(pool_key)
            if (
                existing is not None
                and existing.is_ready()
                and self._fingerprints.get(pool_key) == fingerprint
            ):
                self._last_used[pool_key] = time.monotonic()
                return existing

            old_task = self._tasks.pop(pool_key, None)
            self._services.pop(pool_key, None)
            self._fingerprints.pop(pool_key, None)
            if old_task and not old_task.done():
                old_task.cancel()

            if pool_key == self.POOL_KEY_MOCK:
                service = MockStitchMCPService()
            else:
                service = StitchMCPService(api_key=api_key)

            task = asyncio.create_task(
                service._run(), name=f"stitch-{pool_key}"
            )
            try:
                await asyncio.wait_for(
                    asyncio.shield(service._ready.wait()),
                    timeout=30.0,
                )
            except asyncio.TimeoutError as exc:
                task.cancel()
                raise RuntimeError(
                    f"StitchMCPService for {pool_key} did not become ready in 30s"
                ) from exc

            self._services[pool_key] = service
            self._tasks[pool_key] = task
            self._fingerprints[pool_key] = fingerprint
            self._last_used[pool_key] = time.monotonic()
            return service

    async def shutdown(self) -> None:
        """Cancel every running task and clear pool state."""
        if self._evict_task and not self._evict_task.done():
            self._evict_task.cancel()
        for task in list(self._tasks.values()):
            if not task.done():
                task.cancel()
        self._services.clear()
        self._tasks.clear()
        self._fingerprints.clear()
        self._last_used.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_stitch_pool.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/stitch_mcp.py tests/unit/app_builder/test_stitch_pool.py
git commit -m "feat(stitch): implement StitchPool.get_or_spawn + shutdown"
```

---

## Task 5: `StitchPool.evict_idle` + background loop

**Files:**
- Modify: `app/services/stitch_mcp.py` (extend `StitchPool`)
- Modify: `tests/unit/app_builder/test_stitch_pool.py` (add tests)

- [ ] **Step 1: Add eviction tests**

Append to `tests/unit/app_builder/test_stitch_pool.py`:

```python
@pytest.mark.asyncio
async def test_evict_idle_drops_old_user_entries_keeps_env(monkeypatch):
    """Entries past TTL are evicted; __env_default__ is never evicted."""
    _patch_service_classes(monkeypatch)
    monkeypatch.delenv("STITCH_API_KEY", raising=False)

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool(evict_ttl_seconds=1)

    with patch(
        "app.services.user_config.get_user_api_key",
        side_effect=lambda u, k: f"key-{u}",
    ):
        await pool.get_or_spawn("u1")

    # Mark the env-default as fresh (simulate it would never be evicted anyway)
    pool._last_used[StitchPool.POOL_KEY_ENV] = time.monotonic()

    # Make u1 stale
    pool._last_used["user:u1"] = time.monotonic() - 5

    evicted = await pool.evict_idle()
    assert evicted == 1
    assert "user:u1" not in pool._services
    await pool.shutdown()


@pytest.mark.asyncio
async def test_evict_idle_keeps_fresh_entries(monkeypatch):
    """Entries within TTL are not evicted."""
    _patch_service_classes(monkeypatch)
    monkeypatch.delenv("STITCH_API_KEY", raising=False)

    from app.services.stitch_mcp import StitchPool

    pool = StitchPool(evict_ttl_seconds=600)

    with patch(
        "app.services.user_config.get_user_api_key",
        side_effect=lambda u, k: f"key-{u}",
    ):
        await pool.get_or_spawn("u1")

    evicted = await pool.evict_idle()
    assert evicted == 0
    assert "user:u1" in pool._services
    await pool.shutdown()
```

(Add `import time` at the top of the test file if not already present.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/app_builder/test_stitch_pool.py::test_evict_idle_drops_old_user_entries_keeps_env -v`
Expected: FAIL — `AttributeError: 'StitchPool' object has no attribute 'evict_idle'`

- [ ] **Step 3: Implement `evict_idle` and the background loop**

Add to `StitchPool` in `app/services/stitch_mcp.py`:

```python
    async def evict_idle(self) -> int:
        """Cancel and remove pool entries idle longer than TTL.

        Never evicts ``__env_default__`` — that's the hot platform path.
        Returns the number of evicted entries.
        """
        now = time.monotonic()
        async with self._spawn_lock:
            to_evict = [
                k
                for k, ts in self._last_used.items()
                if k != self.POOL_KEY_ENV and (now - ts) > self._evict_ttl
            ]
            for k in to_evict:
                task = self._tasks.pop(k, None)
                self._services.pop(k, None)
                self._fingerprints.pop(k, None)
                self._last_used.pop(k, None)
                if task and not task.done():
                    task.cancel()
        return len(to_evict)

    async def _evict_loop(self) -> None:
        """Background task: run evict_idle every 60s for the process lifetime."""
        while True:
            try:
                await asyncio.sleep(60)
                await self.evict_idle()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # pragma: no cover — defensive
                logger.warning("Stitch pool evict loop error: %s", e)

    def start_evict_loop(self) -> None:
        """Start the background eviction task. Idempotent."""
        if self._evict_task is None or self._evict_task.done():
            self._evict_task = asyncio.create_task(
                self._evict_loop(), name="stitch-pool-evict"
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_stitch_pool.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/stitch_mcp.py tests/unit/app_builder/test_stitch_pool.py
git commit -m "feat(stitch): add StitchPool idle eviction"
```

---

## Task 6: Async `get_stitch_service(user_id)`

**Files:**
- Modify: `app/services/stitch_mcp.py:381-391`
- Modify: `tests/unit/app_builder/test_stitch_mcp_service.py:16-26`

- [ ] **Step 1: Update legacy `get_stitch_service` test for the async pool path**

Replace the existing `test_get_stitch_service_raises_when_not_initialized` body with:

```python
@pytest.mark.asyncio
async def test_get_stitch_service_raises_when_no_keys(monkeypatch):
    """Async get_stitch_service raises when no key is anywhere configured."""
    import app.services.stitch_mcp as mod

    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.delenv("APP_BUILDER_USE_MOCK_STITCH", raising=False)

    # Reset module-level pool
    mod._pool = None

    with pytest.raises(RuntimeError, match="No Stitch API key configured"):
        await mod.get_stitch_service(user_id=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/app_builder/test_stitch_mcp_service.py::test_get_stitch_service_raises_when_no_keys -v`
Expected: FAIL — current `get_stitch_service` is sync and raises about `_stitch_service` not initialized

- [ ] **Step 3: Replace `get_stitch_service` with the async pool variant**

In `app/services/stitch_mcp.py`, replace lines 381-391 (`def get_stitch_service(...)`) with:

```python
# Module-level pool instance — initialised on first use or by lifespan
_pool: StitchPool | None = None
# Kept for backwards compat / inspection by existing tests
_stitch_service: "StitchMCPService | None" = None
_stitch_task: "asyncio.Task[None] | None" = None


def get_pool() -> StitchPool:
    """Return the module-level StitchPool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = StitchPool()
    return _pool


async def get_stitch_service(
    user_id: str | None = None,
) -> "StitchMCPService":
    """Return a ready StitchMCPService for the given user.

    Resolution order: user-saved STITCH_API_KEY → env STITCH_API_KEY → mock
    (if ``APP_BUILDER_USE_MOCK_STITCH=1``) → RuntimeError.
    """
    return await get_pool().get_or_spawn(user_id)
```

- [ ] **Step 4: Run all stitch tests to verify they pass**

Run: `uv run pytest tests/unit/app_builder/test_stitch_mcp_service.py tests/unit/app_builder/test_stitch_pool.py -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add app/services/stitch_mcp.py tests/unit/app_builder/test_stitch_mcp_service.py
git commit -m "refactor(stitch): make get_stitch_service async + pool-backed"
```

---

## Task 7: Wire pool into FastAPI lifespan

**Files:**
- Modify: `app/fast_api_app.py:545-578` (startup) and `app/fast_api_app.py:597-600` (shutdown)

- [ ] **Step 1: Replace singleton init with pool init**

In `app/fast_api_app.py`, replace the block at lines 545-578 with:

```python
    # --- Stitch MCP pool startup ---
    import asyncio as _asyncio_lifespan

    import app.services.stitch_mcp as _stitch_module

    if not BYPASS_IMPORT:
        pool = _stitch_module.get_pool()
        # Pre-warm __env_default__ if env key (or mock) is configured.
        env_key_present = bool((os.environ.get("STITCH_API_KEY") or "").strip())
        mock_enabled = _stitch_module.should_use_mock_stitch_service()
        if env_key_present or mock_enabled:
            try:
                await _asyncio_lifespan.wait_for(
                    pool.get_or_spawn(user_id=None),
                    timeout=30.0,
                )
                logger.info("Stitch pool pre-warmed (__env_default__ or __mock__)")
            except Exception as e:
                logger.warning(
                    "Stitch pool pre-warm failed (non-fatal): %s — per-user spawns "
                    "will still work on first call",
                    e,
                )
        else:
            logger.info(
                "STITCH_API_KEY not set and mock disabled — skipping pre-warm; "
                "per-user spawns happen on first call"
            )
        pool.start_evict_loop()
```

- [ ] **Step 2: Replace singleton shutdown with pool shutdown**

In `app/fast_api_app.py`, replace lines 597-600 (the `_stitch_task` cancellation block) with:

```python
    # --- Stitch MCP pool shutdown ---
    try:
        await _stitch_module.get_pool().shutdown()
        logger.info("Stitch pool shut down")
    except Exception as e:
        logger.warning("Stitch pool shutdown failed (non-fatal): %s", e)
```

- [ ] **Step 3: Verify imports + linter still happy**

Run: `uv run ruff check app/fast_api_app.py`
Expected: No errors

Run: `uv run ty check app/fast_api_app.py`
Expected: No new errors (pre-existing errors are tolerated)

- [ ] **Step 4: Commit**

```bash
git add app/fast_api_app.py
git commit -m "feat(stitch): replace singleton lifespan with StitchPool"
```

---

## Task 8: Update call sites — agent tool

**Files:**
- Modify: `app/agents/tools/app_builder.py:45-47`, `:121-126`

- [ ] **Step 1: Update `_generate_screen_async`**

In `app/agents/tools/app_builder.py`, replace the import + service line:

```python
async def _generate_screen_async(
    prompt: str,
    project_id: str,
    device_type: str = "DESKTOP",
    enhance: bool = True,
    user_id: str | None = None,
    project_uuid: str | None = None,
    screen_id: str | None = None,
    variant_index: int = 0,
) -> dict[str, Any]:
    """Async inner for generate_app_screen."""
    from app.services.stitch_mcp import get_stitch_service

    service = await get_stitch_service(user_id)

    # ... rest unchanged
```

- [ ] **Step 2: Update `_list_stitch_tools_async`**

```python
async def _list_stitch_tools_async(user_id: str | None = None) -> dict[str, Any]:
    """List tools exposed by the running Stitch MCP server."""
    from app.services.stitch_mcp import get_stitch_service

    service = await get_stitch_service(user_id)
    async with service._lock:
        tools_result = await service._session.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description} for t in tools_result.tools
        ]
    }
```

The sync wrapper `list_stitch_tools` already exists; update it to forward `user_id`:

```python
def list_stitch_tools(user_id: str | None = None) -> dict[str, Any]:
    """List all tools available from the connected Stitch MCP server."""
    try:
        return _run_async(_list_stitch_tools_async(user_id=user_id))
    except RuntimeError as e:
        logger.error("list_stitch_tools failed: %s", e)
        return {"success": False, "error": str(e)}
```

- [ ] **Step 3: Lint check**

Run: `uv run ruff check app/agents/tools/app_builder.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add app/agents/tools/app_builder.py
git commit -m "refactor(stitch): thread user_id through agent app_builder tools"
```

---

## Task 9: Update call sites — services + router

**Files:**
- Modify: `app/routers/app_builder.py:338-343`
- Modify: `app/services/screen_generation_service.py:67-68`, `:185-186`
- Modify: `app/services/iteration_service.py:103`, `:138`
- Modify: `app/services/multi_page_service.py:80`

- [ ] **Step 1: Update `screen_generation_service.py`**

At line 67 inside `generate_screen_variants(project_id, user_id, ...)`, replace:

```python
    supabase = get_service_client()
    service = await get_stitch_service(user_id)
    screen_id = str(uuid4())
```

At line 185 inside `generate_device_variant(screen_id, user_id, ...)`, the same change:

```python
    service = await get_stitch_service(user_id)
```

- [ ] **Step 2: Update `iteration_service.py`**

Lines 103 and 138 are inside `edit_screen_variant(..., user_id, ...)`. Replace each `service = get_stitch_service()` with `service = await get_stitch_service(user_id)`.

- [ ] **Step 3: Update `multi_page_service.py`**

Line 80 is inside `build_all_pages(project_id, user_id, ...)`. Replace `service = get_stitch_service()` with `service = await get_stitch_service(user_id)`.

- [ ] **Step 4: Update `routers/app_builder.py`**

Line 340 is inside an async route handler that already binds `user_id`. Replace:

```python
        service = await get_stitch_service(user_id)
        stitch_proj = await service.call_tool(
            "create_project", {"name": project.get("title", "App")}
        )
```

- [ ] **Step 5: Run the existing app-builder service tests**

Run: `uv run pytest tests/unit/app_builder/ -v -k "iteration or screen or multi"`
Expected: All existing tests still pass (they should mock `get_stitch_service` directly).

If any test patches the module path of `get_stitch_service`, it now needs `AsyncMock` instead of `MagicMock` for the return value. Update those mocks accordingly.

- [ ] **Step 6: Commit**

```bash
git add app/routers/app_builder.py app/services/screen_generation_service.py app/services/iteration_service.py app/services/multi_page_service.py
git commit -m "refactor(stitch): thread user_id through service + router call sites"
```

---

## Task 10: `POST /configuration/save-api-key` endpoint

**Files:**
- Modify: `app/routers/configuration.py` (append new endpoint + model)
- Create: `tests/unit/test_configuration_save_api_key.py`

- [ ] **Step 1: Write failing endpoint tests**

```python
# tests/unit/test_configuration_save_api_key.py
"""Tests for POST /configuration/save-api-key."""
from unittest.mock import patch

from fastapi.testclient import TestClient


def _client_with_user(user_id: str = "u1"):
    """Build a TestClient with auth dependency overridden."""
    from app.fast_api_app import app
    from app.routers.onboarding import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app)


def test_save_api_key_writes_stitch_key():
    client = _client_with_user("u1")
    with patch("app.routers.configuration.set_user_api_key") as mock_set:
        resp = client.post(
            "/configuration/save-api-key",
            json={"tool_id": "stitch", "api_key": "tvly-abc"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    mock_set.assert_called_once_with("u1", "STITCH_API_KEY", "tvly-abc")


def test_save_api_key_rejects_unknown_tool():
    client = _client_with_user("u1")
    resp = client.post(
        "/configuration/save-api-key",
        json={"tool_id": "stripe", "api_key": "sk_test"},
    )
    assert resp.status_code == 400
    assert "tool_id" in resp.json()["detail"].lower()


def test_save_api_key_rejects_empty_key():
    client = _client_with_user("u1")
    resp = client.post(
        "/configuration/save-api-key",
        json={"tool_id": "stitch", "api_key": "   "},
    )
    assert resp.status_code == 400
    assert "api_key" in resp.json()["detail"].lower()


def test_save_api_key_rejects_oversize_key():
    client = _client_with_user("u1")
    resp = client.post(
        "/configuration/save-api-key",
        json={"tool_id": "stitch", "api_key": "x" * 1024},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_configuration_save_api_key.py -v`
Expected: FAIL — `404 Not Found` for the route.

- [ ] **Step 3: Add the endpoint**

Append to `app/routers/configuration.py` (above the trailing OAuth callback handler is fine):

```python
ALLOWED_API_KEY_TOOLS = {
    "stitch": "STITCH_API_KEY",
}


class SaveApiKeyRequest(BaseModel):
    tool_id: str
    api_key: str


@router.post("/save-api-key", response_model=SaveConfigResponse)
@limiter.limit(get_user_persona_limit)
async def save_api_key(
    request: Request,
    body: SaveApiKeyRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """Persist a per-user API key into user_configurations.

    Restricted to a small allowlist of integrations (currently: Stitch).
    """
    from app.services.user_config import set_user_api_key

    env_var = ALLOWED_API_KEY_TOOLS.get(body.tool_id)
    if env_var is None:
        raise HTTPException(status_code=400, detail=f"Unknown tool_id '{body.tool_id}'")

    api_key = (body.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key must not be empty")
    if len(api_key) > 512:
        raise HTTPException(status_code=400, detail="api_key exceeds 512-character limit")

    try:
        set_user_api_key(current_user_id, env_var, api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to save API key: {exc!s}"
        ) from exc

    return SaveConfigResponse(
        success=True, message=f"{body.tool_id.capitalize()} API key saved."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_configuration_save_api_key.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add app/routers/configuration.py tests/unit/test_configuration_save_api_key.py
git commit -m "feat(configuration): add POST /save-api-key for Stitch BYO-key"
```

---

## Task 11: `mcp-status` reflects user-saved Stitch key + always-active Tavily/Firecrawl

**Files:**
- Modify: `app/routers/configuration.py` (`get_mcp_status` + `_built_in_status` + `_is_built_in_tool_configured`)
- Add tests in: `tests/unit/test_configuration_save_api_key.py`

- [ ] **Step 1: Write failing tests for the new behavior**

Append to `tests/unit/test_configuration_save_api_key.py`:

```python
def test_mcp_status_tavily_firecrawl_always_active(monkeypatch):
    """Tavily and Firecrawl render as configured regardless of env."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    # Important: clear the lru_cache so the env change takes effect
    from app.mcp.config import clear_config_cache

    clear_config_cache()

    client = _client_with_user("u1")
    resp = client.get("/configuration/mcp-status")
    assert resp.status_code == 200
    body = resp.json()
    by_id = {t["id"]: t for t in body["built_in_tools"]}
    assert by_id["tavily"]["configured"] is True
    assert "Active" in by_id["tavily"]["status"]
    assert by_id["firecrawl"]["configured"] is True


def test_mcp_status_stitch_uses_user_saved_key(monkeypatch):
    """Stitch shows configured when user has a saved key, even if env is empty."""
    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    from app.mcp.config import clear_config_cache

    clear_config_cache()

    client = _client_with_user("u1")
    with patch(
        "app.routers.configuration.get_user_api_key", return_value="user-key"
    ):
        resp = client.get("/configuration/mcp-status")
    assert resp.status_code == 200
    body = resp.json()
    stitch = next(t for t in body["configurable_tools"] if t["id"] == "stitch")
    assert stitch["configured"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_configuration_save_api_key.py::test_mcp_status_tavily_firecrawl_always_active tests/unit/test_configuration_save_api_key.py::test_mcp_status_stitch_uses_user_saved_key -v`
Expected: FAIL — the current logic returns `configured: False` when env keys are unset.

- [ ] **Step 3: Update `_is_built_in_tool_configured` and `_built_in_status`**

In `app/routers/configuration.py`, replace lines 190-202 with:

```python
# Tavily and Firecrawl are platform-managed. From the end-user's perspective
# they are always active; backend admins still verify via /health/connections.
_ALWAYS_ACTIVE_BUILT_INS = {"tavily", "firecrawl"}


def _is_built_in_tool_configured(tool_id: str, config) -> bool:
    if tool_id in _ALWAYS_ACTIVE_BUILT_INS:
        return True
    return False  # no other built-ins today


def _built_in_status(tool_id: str, config) -> str:
    if tool_id in _ALWAYS_ACTIVE_BUILT_INS:
        return "Active for all users"
    return "Bundled in the app"
```

- [ ] **Step 4: Update `get_mcp_status` to honor user-saved Stitch key**

In `app/routers/configuration.py`, change the configurable-tools loop to use the new helper. Replace lines 343-357 with:

```python
        from app.services.user_config import get_user_api_key

        tools = []
        for tool_info in MCP_TOOLS_INFO:
            env_value = os.environ.get(tool_info["env_var"])
            user_value = None
            # Currently only Stitch supports per-user keys via /save-api-key
            if tool_info["id"] == "stitch":
                try:
                    user_value = get_user_api_key(_user_id, tool_info["env_var"])
                except Exception:
                    user_value = None
            is_configured = bool(env_value) or bool(user_value)

            tools.append(
                MCPToolStatus(
                    id=tool_info["id"],
                    name=tool_info["name"],
                    description=tool_info["description"],
                    configured=is_configured,
                    env_var=tool_info["env_var"],
                    docs_url=tool_info.get("docs_url"),
                    is_built_in=False,
                )
            )
```

- [ ] **Step 5: Run all configuration tests**

Run: `uv run pytest tests/unit/test_configuration_save_api_key.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add app/routers/configuration.py tests/unit/test_configuration_save_api_key.py
git commit -m "feat(configuration): mcp-status reflects user-saved Stitch + always-active Tavily/Firecrawl"
```

---

## Task 12: Frontend — repoint save endpoint + always-active rendering

**Files:**
- Modify: `frontend/src/app/api/configuration/save-api-key/route.ts:57-69`
- Modify: `frontend/src/app/dashboard/configuration/page.tsx:3520-3548`

- [ ] **Step 1: Repoint the Next.js save route at the new backend endpoint**

In `frontend/src/app/api/configuration/save-api-key/route.ts`, replace the body of the POST handler from `// Save to user_configurations via backend` through the response check (lines ~57-74) with:

```ts
    // POST to the dedicated backend endpoint that handles API-key persistence.
    const response = await fetch(`${API_BASE_URL}/configuration/save-api-key`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({
        tool_id,
        api_key,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || 'Failed to save API key');
    }

    const data = await response.json();

    return NextResponse.json({
      success: data.success,
      message: data.message,
    });
```

The unused `TOOL_ENV_VARS` map can be removed — the backend now owns the mapping. Delete lines 11-19.

- [ ] **Step 2: Render Tavily/Firecrawl as always active in the configuration page**

In `frontend/src/app/dashboard/configuration/page.tsx`, find the built-in tool render block at line ~3530-3548 and update the conditional styling. Replace:

```tsx
                                    {builtInTools.map((tool) => (
                                        <div
                                            key={tool.id}
                                            className={`flex items-center gap-4 rounded-xl border p-4 backdrop-blur ${tool.configured ? 'border-emerald-100 bg-white/85' : 'border-amber-200 bg-white/75'}`}
                                        >
                                            <div className={`rounded-lg p-2.5 ${tool.configured ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-700'}`}>
                                                {mcpToolIcons[tool.id] || <Zap className="w-5 h-5" />}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <h3 className="font-medium text-slate-800">{tool.name}</h3>
                                                    <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${tool.configured ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
                                                        {tool.configured ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                                                        {tool.status}
                                                    </span>
                                                </div>
                                                <p className="mt-0.5 text-sm text-slate-500">{tool.description}</p>
                                            </div>
                                        </div>
                                    ))}
```

With (forces the active variant for `tavily` and `firecrawl`):

```tsx
                                    {builtInTools.map((tool) => {
                                        const alwaysActive = tool.id === 'tavily' || tool.id === 'firecrawl';
                                        const showActive = alwaysActive || tool.configured;
                                        return (
                                            <div
                                                key={tool.id}
                                                className={`flex items-center gap-4 rounded-xl border p-4 backdrop-blur ${showActive ? 'border-emerald-100 bg-white/85' : 'border-amber-200 bg-white/75'}`}
                                            >
                                                <div className={`rounded-lg p-2.5 ${showActive ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-700'}`}>
                                                    {mcpToolIcons[tool.id] || <Zap className="w-5 h-5" />}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <h3 className="font-medium text-slate-800">{tool.name}</h3>
                                                        <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${showActive ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
                                                            {showActive ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                                                            {alwaysActive ? 'Active for all users' : tool.status}
                                                        </span>
                                                    </div>
                                                    <p className="mt-0.5 text-sm text-slate-500">{tool.description}</p>
                                                </div>
                                            </div>
                                        );
                                    })}
```

- [ ] **Step 3: Type check the frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors

- [ ] **Step 4: Visual smoke test**

Run: `cd frontend && npm run dev`

In a browser, sign in, visit `/dashboard/configuration`. Verify:
- "Built-in Research Providers" section shows Tavily and Firecrawl with the green "Active for all users" badge.
- Stitch row in the configurable section shows "Setup" if no key is saved.
- Clicking Setup, pasting a fake key, and saving returns success (the backend writes the row; lookups in the next request will reflect the saved key).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/api/configuration/save-api-key/route.ts frontend/src/app/dashboard/configuration/page.tsx
git commit -m "feat(frontend): repoint save-api-key + always-active Tavily/Firecrawl"
```

---

## Task 13: Backend lint + full test pass

**Files:** none (validation only)

- [ ] **Step 1: Run backend linter**

Run: `make lint`
Expected: ruff check, ruff format, ty all pass.

- [ ] **Step 2: Run the targeted unit suites for everything we touched**

Run: `uv run pytest tests/unit/services/test_user_config.py tests/unit/app_builder/test_stitch_pool.py tests/unit/app_builder/test_stitch_mcp_service.py tests/unit/test_configuration_save_api_key.py tests/unit/app_builder/test_iteration_service.py tests/unit/app_builder/test_screen_generation_service.py tests/unit/app_builder/test_multi_page_service.py tests/unit/app_builder/test_app_builder_router.py -v`
Expected: all pass.

- [ ] **Step 3: Run the broader app_builder test suite**

Run: `uv run pytest tests/unit/app_builder/ -v`
Expected: all pass.

- [ ] **Step 4: If anything fails, fix the call site or test mock**

The most common failure: a test that does `from unittest.mock import MagicMock; service = MagicMock()` and patches `get_stitch_service` returning that — now the call is `await get_stitch_service(user_id)`, so patches need to return an `AsyncMock` whose return value is the original `MagicMock`. Adjust those mocks file by file.

- [ ] **Step 5: Commit (only if Step 4 made changes)**

```bash
git add tests/
git commit -m "test(stitch): adjust mocks for async get_stitch_service"
```

---

## Self-review checklist

Run through this once before handing off:

- **Spec coverage** — every requirement in `docs/superpowers/specs/2026-04-27-per-user-stitch-keys-design.md` maps to a task above:
  - Tavily/Firecrawl always-active → Task 11 + Task 12
  - Stitch save endpoint with allowlist + `is_sensitive` → Task 1 + Task 10
  - User-config helper module → Task 1
  - Pool with key resolution → Task 3
  - Pool spawn / reuse / fingerprint rotation → Task 4
  - Pool eviction + background loop + shutdown → Task 4 + Task 5
  - Async `get_stitch_service(user_id)` → Task 6
  - Lifespan integration → Task 7
  - Six call-site updates → Task 8 + Task 9
  - `mcp-status` for Stitch + Tavily/Firecrawl → Task 11
  - Frontend repoint + UI → Task 12

- **No placeholders** — every step has either a concrete code block, an exact command, or an exact file path. No "TBD", "etc.", or "similar to above".

- **Type / signature consistency** — `get_stitch_service(user_id: str | None = None)` is the signature used by every caller. `set_user_api_key(user_id, key_name, api_key)` and `get_user_api_key(user_id, key_name)` are both sync. `StitchPool` constants are `POOL_KEY_ENV` and `POOL_KEY_MOCK`.
