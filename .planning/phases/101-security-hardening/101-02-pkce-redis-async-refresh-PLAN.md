---
phase: 101-security-hardening
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/connector.py
  - app/agents/tools/social.py
  - app/social/publisher.py
  - app/social/analytics.py
  - app/mcp/tools/social_listening.py
  - app/mcp/tools/google_seo.py
  - app/routers/configuration.py
  - tests/unit/social/test_pkce_redis.py
  - tests/unit/social/test_async_refresh.py
  - tests/unit/test_social_connector_security.py
autonomous: true
requirements: [AUTH-03, AUTH-05]

must_haves:
  truths:
    - "OAuth authorize → callback succeeds when in-process state is wiped between the two calls (simulating a Cloud Run callback landing on a different instance), proving PKCE survives horizontal scaling — `_pkce_verifiers: dict[str, str]` is removed from `SocialConnector` and the `_store_pkce_verifier`/`_pop_pkce_verifier` Postgres-backed helpers are replaced with Redis writes/reads via `cache.set_generic`/`get_generic`/`delete` keyed by `pikar:integration:pkce:{state}` with `ttl=600`"
    - "When Redis is unavailable (circuit breaker OPEN, `get_generic` returns `is_error=True`, `set_generic` returns `False`), `get_authorization_url` returns `{\"error\": \"OAuth temporarily unavailable, please retry\"}` and `handle_callback` returns `{\"error\": \"PKCE verifier not found. Session may have expired.\"}` — fails closed; in-memory fallback is gone"
    - "`SocialConnector.get_access_token` and `SocialConnector._refresh_token` are `async def` and use `httpx.AsyncClient` (sync `httpx.Client` removed at connector.py:425); calling `get_access_token` from an async tool no longer blocks the event loop — proven by a load test that fires 5 concurrent calls against a mocked-1-second token endpoint, asserts a heartbeat counter advances ≥4 times during the wait, AND asserts exactly one `httpx.AsyncClient.post` call is made (per-key `asyncio.Lock` prevents thundering herd)"
    - "All four production callers of `connector.get_access_token` (`publisher.py:35`, `analytics.py:37`, `mcp/tools/social_listening.py:126`, `mcp/tools/google_seo.py:77`) and the one caller of `connector.get_authorization_url` (`routers/configuration.py:662`, `agents/tools/social.py:144`) are updated to `await` the now-async method calls; existing test suite passes"
  artifacts:
    - path: "app/social/connector.py"
      provides: "SocialConnector with Redis-backed PKCE persistence (drops `_pkce_verifiers` dict, drops `oauth_pkce_states` Postgres table reads/writes — those become legacy/unused), async `get_access_token`/`_refresh_token` using `httpx.AsyncClient`, per-`(user_id, platform)` `asyncio.Lock` registry mirroring `IntegrationManager._refresh_locks`. `get_authorization_url` becomes async."
      contains: "async def _refresh_token"
    - path: "app/agents/tools/social.py"
      provides: "`get_oauth_url` becomes async (or wraps the call via `asyncio.run` if ADK tool model requires sync); `disconnect_social_account` unchanged"
      contains: "async def get_oauth_url"
    - path: "app/social/publisher.py"
      provides: "`_get_token_or_error` becomes async; all call sites updated to await"
      contains: "async def _get_token_or_error"
    - path: "app/social/analytics.py"
      provides: "`_get_token` becomes async; existing async metric methods now `await self._get_token(...)`"
      contains: "async def _get_token"
    - path: "app/mcp/tools/social_listening.py"
      provides: "Adds `await` to the existing `connector.get_access_token(...)` call at line 126"
      contains: "await connector.get_access_token"
    - path: "app/mcp/tools/google_seo.py"
      provides: "Adds `await` to the existing `connector.get_access_token(...)` call at line 77"
      contains: "await connector.get_access_token"
    - path: "app/routers/configuration.py"
      provides: "`connect-social` route awaits `connector.get_authorization_url(...)`"
      contains: "await connector.get_authorization_url"
    - path: "tests/unit/social/test_pkce_redis.py"
      provides: "Unit tests covering: (a) get_authorization_url calls cache.set_generic with correct key/value/TTL; (b) handle_callback reads via cache.get_generic and deletes via cache.delete; (c) Redis miss returns the documented error; (d) Redis circuit-breaker error returns the temporary-unavailable error (fail-closed contract); (e) cross-instance simulation: state written via instance A's connector, instance B's connector reads it (shared cache fixture)"
      contains: "test_callback_reads_pkce_from_redis"
    - path: "tests/unit/social/test_async_refresh.py"
      provides: "Async test that asserts: (a) get_access_token is awaitable; (b) under 5 concurrent calls for an expired-token row, exactly 1 httpx.AsyncClient.post is made (Lock works); (c) a parallel asyncio task continues incrementing a counter while the refresh is in flight (event loop not blocked); (d) refresh updates the row with re-encrypted access_token + new expires_at"
      contains: "test_concurrent_refresh_uses_lock"
  key_links:
    - from: "app/social/connector.py:get_authorization_url"
      to: "app.services.cache.CacheService.set_generic"
      via: "await cache.set_generic(f\"pikar:integration:pkce:{state}\", {\"verifier\": ..., \"platform\": ...}, ttl=600)"
      pattern: "pikar:integration:pkce:"
    - from: "app/social/connector.py:handle_callback"
      to: "app.services.cache.CacheService.get_generic + delete"
      via: "cached = await cache.get_generic(...); if cached.is_miss or cached.is_error: error; verifier = cached.value['verifier']; await cache.delete(...)"
      pattern: "is_miss or cached.is_error"
    - from: "app/social/connector.py:get_access_token"
      to: "app/social/connector.py:_refresh_token"
      via: "per-(user_id, platform) asyncio.Lock with double-check pattern (mirror integration_manager.py:191-205)"
      pattern: "_get_refresh_lock"
    - from: "app/social/connector.py:_refresh_token"
      to: "httpx.AsyncClient"
      via: "async with httpx.AsyncClient(timeout=30.0) as http: resp = await http.post(...)"
      pattern: "httpx.AsyncClient"
---

<objective>
Replace the dual-source-of-truth PKCE state (in-memory dict + Postgres `oauth_pkce_states` table) with a single Redis-backed implementation, and convert the synchronous-on-async-path token refresh in `SocialConnector` to true async I/O with a per-key `asyncio.Lock` mirroring `IntegrationManager`'s pattern.

Purpose: Satisfy AUTH-03 success criterion #3 (OAuth callback succeeds across Cloud Run instances) and AUTH-05 success criterion #5 (event-loop heartbeats keep flowing during refresh). Per RESEARCH §AUTH-03 and §AUTH-05, the gap is twofold: (1) the current `oauth_pkce_states` Postgres approach works but adds a DB roundtrip and a fallback in-memory dict at `connector.py:175` that breaks across instances; the project's standard for short-lived OAuth state is Redis (`pikar:integration:` namespace, see `routers/integrations.py:148-153`); (2) `_refresh_token` uses `httpx.Client` (sync, blocking) inside a method called from `async def` tool functions in `mcp/tools/{social_listening,google_seo}.py` and `social/{publisher,analytics}.py` — every parallel publish or metric fetch on an expired token freezes the event loop for the refresh duration.

Output: `SocialConnector` rewritten so PKCE state lives only in Redis, `get_access_token`/`_refresh_token` are `async def` with per-key locks, and `get_authorization_url` is `async def`. Five caller files updated to `await` the new signatures. Two new test modules cover the Redis round-trip and the concurrent-refresh + heartbeat invariants. The Postgres-backed `_store_pkce_verifier`/`_pop_pkce_verifier` helpers and the `oauth_pkce_states` table remain in the codebase but are no longer called by `connector.py` — table cleanup is a Phase 108 hygiene item, not blocking 101.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/101-security-hardening/101-RESEARCH.md
@.planning/phases/101-security-hardening/101-CONTEXT.md
@app/social/connector.py
@app/services/cache.py
@app/services/integration_manager.py
@app/routers/integrations.py
@app/social/publisher.py
@app/social/analytics.py
@app/mcp/tools/social_listening.py
@app/mcp/tools/google_seo.py
@app/agents/tools/social.py
@app/routers/configuration.py
@tests/unit/test_social_connector_security.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->

From app/services/cache.py (NAMESPACE + API — use these directly):
```python
REDIS_KEY_PREFIXES = {
    ...
    "integration": "pikar:integration:",  # use this prefix
    ...
}

# CacheResult is a dataclass:
@dataclass
class CacheResult:
    found: bool
    value: Any
    error: str | None
    is_miss: bool
    is_error: bool
    @classmethod
    def hit(cls, value): ...
    @classmethod
    def miss(cls): ...
    @classmethod
    def from_error(cls, msg): ...

class CacheService:
    @with_circuit_breaker
    async def set_generic(self, key: str, value: Any, ttl: int = 3600) -> bool: ...
    @with_circuit_breaker
    async def get_generic(self, key: str) -> CacheResult: ...
    @with_circuit_breaker
    async def delete(self, key: str) -> bool: ...

def get_cache_service() -> CacheService:
    """Singleton accessor — do not instantiate directly."""
```

From app/routers/integrations.py:148-153, 228-242 (REFERENCE PATTERN — mirror exactly):
```python
# Write
await cache.set_generic(
    f"pikar:integration:oauth_state:{state}",
    state_data,
    ttl=600,
)
# Read + delete
cached_state = await cache.get_generic(f"pikar:integration:oauth_state:{state}")
if cached_state.is_miss or cached_state.is_error:
    raise HTTPException(...)
state_data = cached_state.value
await cache.delete(f"pikar:integration:oauth_state:{state}")
```

From app/services/integration_manager.py:70-88, 166-205 (REFERENCE PATTERN — mirror in connector.py):
```python
class IntegrationManager(BaseService):
    _refresh_locks: ClassVar[dict[tuple[str, str], asyncio.Lock]] = {}
    _locks_guard = asyncio.Lock()

    @classmethod
    async def _get_refresh_lock(cls, user_id, provider) -> asyncio.Lock:
        key = (user_id, provider)
        async with cls._locks_guard:
            if key not in cls._refresh_locks:
                cls._refresh_locks[key] = asyncio.Lock()
            return cls._refresh_locks[key]

    async def get_valid_token(self, user_id, provider) -> str | None:
        cred = await self.get_credentials(user_id, provider)
        if not cred:
            return None
        if not _is_expiring_soon(cred.get("expires_at")):
            return decrypt_secret(cred["access_token"])
        lock = await self._get_refresh_lock(user_id, provider)
        async with lock:
            cred = await self.get_credentials(user_id, provider)  # double-check
            if not cred:
                return None
            if not _is_expiring_soon(cred.get("expires_at")):
                return decrypt_secret(cred["access_token"])
            cred = await self._refresh_token(user_id, provider, cred)
            return decrypt_secret(cred["access_token"])

    async def _refresh_token(self, user_id, provider, cred) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(token_url, data={...})
            response.raise_for_status()
            token_data = response.json()
        # ... store via store_credentials (which encrypts)
```

From app/social/connector.py (CURRENT — what we're replacing):
```python
class SocialConnector:
    def __init__(self):
        self.client = self._get_supabase()
        self._pkce_verifiers: dict[str, str] = {}  # REMOVE

    def _store_pkce_verifier(self, state, user_id, platform, verifier) -> None:
        # Currently uses Postgres oauth_pkce_states table + in-memory fallback.
        # REPLACE entirely: write only to Redis via cache.set_generic.

    def _pop_pkce_verifier(self, state, platform) -> str | None:
        # Currently reads from Postgres + falls back to in-memory dict.
        # REPLACE entirely: read+delete via cache.get_generic + cache.delete.

    def get_authorization_url(self, platform, user_id, redirect_uri) -> dict:
        # Currently sync. Make async.

    async def handle_callback(self, platform, code, state, redirect_uri) -> dict:
        # Already async. Just update _pop_pkce_verifier call.

    def get_access_token(self, user_id, platform) -> str | None:
        # Currently sync. Make async.

    def _refresh_token(self, user_id, platform, account) -> str | None:
        # Currently sync (httpx.Client). Make async (httpx.AsyncClient).
```

Caller sites (verified via grep — all need `await` added):
- `app/social/publisher.py:35` — `token = self.connector.get_access_token(user_id, platform)` → `token = await self.connector.get_access_token(user_id, platform)` (and `_get_token_or_error` becomes `async def`)
- `app/social/analytics.py:37` — `return self.connector.get_access_token(user_id, platform)` → `return await self.connector.get_access_token(user_id, platform)` (and `_get_token` becomes `async def`)
- `app/mcp/tools/social_listening.py:126` — already in `async def`; just add `await`
- `app/mcp/tools/google_seo.py:77` — already in `async def`; just add `await`
- `app/routers/configuration.py:662` — already in `async def`; add `await`
- `app/agents/tools/social.py:144` — `def get_oauth_url(...) -> dict[str, Any]` is currently sync (ADK tool). The cleanest path: convert to `async def` (ADK supports async tools per `app/agents/data/agent.py` patterns). Alternatively wrap with `asyncio.run` — but the connector method also touches Redis (already async-aware) so async-tool is the natural fit. Verify ADK tool registration accepts coroutines (it does — `app/agents/marketing/agent.py` registers async `post_*_content` tools).

Tests already in place at tests/unit/test_social_connector_security.py:
- 3 tests use `_FakeClient` + `_FakeTable` patterns and Postgres-style PKCE rows.
- After this plan, the PKCE-row tests at lines 109-129 and 132-185 become OBSOLETE (Postgres path is gone). Either: (a) DELETE those two tests and rely on the new tests/unit/social/test_pkce_redis.py module; (b) UPDATE them to assert the Redis path. Recommendation: DELETE — they tested the now-removed Postgres path. Keep `test_get_access_token_decrypts_stored_token` (line 188) but make it `async def` and `await` the call.

Project test command:
```bash
uv run pytest tests/unit/social/ tests/unit/test_social_connector_security.py -x
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave-0 failing tests for Redis-backed PKCE</name>
  <files>tests/unit/social/test_pkce_redis.py</files>
  <behavior>
    Five tests, ALL FAILING initially because the production code still calls `_store_pkce_verifier`/`_pop_pkce_verifier` (Postgres path), not Redis.

    Use `unittest.mock.AsyncMock` for `cache.set_generic`/`get_generic`/`delete`, and `patch("app.social.connector.get_cache_service", return_value=mock_cache)` (Task 2 will add this import to connector.py).

    1. **test_get_authorization_url_writes_pkce_to_redis**: Build a fake Supabase client, fake `cache` mock with `set_generic = AsyncMock(return_value=True)`. Patch `os.environ["LINKEDIN_CLIENT_ID"] = "client-id"`. Call `await connector.get_authorization_url("linkedin", "user-1", "https://app.test/cb")`. Assert: `cache.set_generic.await_count == 1`. The single call's args: first positional arg is a string starting with `"pikar:integration:pkce:user-1:"`; second positional or `value=` kwarg is a dict with keys `{"verifier": <some_string>, "platform": "linkedin"}`; `ttl=600`. Assert the returned dict has `authorization_url`, `state`, `platform="linkedin"` keys (no error).

    2. **test_get_authorization_url_fails_closed_when_redis_set_fails**: Same setup but `set_generic = AsyncMock(return_value=False)` (circuit breaker open or Redis down). Assert returned dict is `{"error": "OAuth temporarily unavailable, please retry"}` (or substring match on `"temporarily unavailable"`). Assert `cache.set_generic` was awaited once (we tried).

    3. **test_handle_callback_reads_pkce_from_redis_and_deletes**: Build Redis mock: `get_generic = AsyncMock(return_value=CacheResult.hit({"verifier": "v123", "platform": "linkedin"}))`, `delete = AsyncMock(return_value=True)`. Mock `httpx.AsyncClient` to return a 200 with token JSON. Patch `encrypt_secret = lambda v: f"enc:{v}"`. Call `await connector.handle_callback("linkedin", "code", "user-1:abc", "https://app.test/cb")`. Assert: `cache.get_generic.await_count == 1` with key `"pikar:integration:pkce:user-1:abc"`; `cache.delete.await_count == 1` with the SAME key; result has `success=True`. Assert `httpx.AsyncClient.post` was called with `data={"code_verifier": "v123", ...}`.

    4. **test_handle_callback_fails_when_pkce_missing_or_expired_in_redis**: `get_generic = AsyncMock(return_value=CacheResult.miss())`. Call handle_callback. Assert returned dict is `{"error": "PKCE verifier not found. Session may have expired."}`. Assert `httpx.AsyncClient` was NOT called (no token exchange happens). Assert `cache.delete` was NOT awaited.

    5. **test_handle_callback_fails_closed_on_redis_circuit_breaker_error**: `get_generic = AsyncMock(return_value=CacheResult.from_error("Connection error: timeout"))`. Same callback call. Assert returned dict has `"error"` key with substring `"PKCE verifier not found"` OR `"OAuth temporarily unavailable"` (executor picks consistent message; test asserts the contract that **no token exchange happens** when Redis is unhealthy). Assert `httpx.AsyncClient.post` was NOT called.

    Run `uv run pytest tests/unit/social/test_pkce_redis.py -x -v 2>&1 | tail -30` — ALL 5 tests fail with `AssertionError` (e.g. `cache.set_generic.await_count == 0`) or `AttributeError` referencing the not-yet-added `get_cache_service` import patch target.

    Commit message: `test(101-02): add failing tests for Redis-backed PKCE state (AUTH-03)`.
  </behavior>
  <action>
    1. Create `tests/unit/social/test_pkce_redis.py`. Imports: `from __future__ import annotations`, `import pytest`, `from unittest.mock import AsyncMock, patch`, `from datetime import datetime, timedelta, timezone`, `from app.services.cache import CacheResult`, `from app.social.connector import SocialConnector`.
    2. Reproduce minimal `_FakeClient`/`_FakeTable` (copy from `tests/unit/test_social_connector_security.py:12-99` — strip the PKCE-row branches since we no longer use Postgres for PKCE; keep only the connected_accounts branches).
    3. Define a fixture `redis_mock(monkeypatch)` that patches `app.social.connector.get_cache_service` to return a `MagicMock` whose `set_generic`/`get_generic`/`delete` are `AsyncMock`s. Yields the mock cache so tests can configure return values per scenario.
    4. Use `pytest.mark.asyncio` on every test (the connector methods will all be async after Task 2).
    5. Verify FAIL: `uv run pytest tests/unit/social/test_pkce_redis.py -x -v 2>&1 | tail -30` — all 5 fail.
    6. Lint: `uv run ruff check tests/unit/social/test_pkce_redis.py --fix && uv run ruff format tests/unit/social/test_pkce_redis.py`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_pkce_redis.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    `tests/unit/social/test_pkce_redis.py` exists with 5 tests, ALL FAIL. Failure messages reference either the missing `get_cache_service` patch target, the wrong call count, or the missing `await`. `ruff check` clean. Commit `test(101-02): add failing tests for Redis-backed PKCE state (AUTH-03)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wave-0 failing tests for async refresh + per-key Lock</name>
  <files>tests/unit/social/test_async_refresh.py</files>
  <behavior>
    Three tests, ALL FAILING initially because `get_access_token` / `_refresh_token` are still sync.

    1. **test_get_access_token_is_awaitable_and_returns_decrypted_token**: Seed connected_accounts with one row containing `access_token="enc:tok"`, `token_expires_at=(now+5min).isoformat()` (NOT expired). Patch `app.social.connector.decrypt_secret` to return `"plain-tok"`. Call `result = await connector.get_access_token("user-1", "linkedin")`. Assert `result == "plain-tok"`. Assert `inspect.iscoroutinefunction(connector.get_access_token)` is `True`.

    2. **test_concurrent_refresh_uses_per_key_lock_single_http_post**: Seed an EXPIRED row (`token_expires_at = (now - 1min).isoformat()`). Patch `httpx.AsyncClient` so `.post(...)` records calls in a list AND `await asyncio.sleep(0.5)` before returning a 200 with new tokens. Patch `encrypt_secret = lambda v: f"enc:{v}"`, `decrypt_secret = lambda v: v.removeprefix("enc:")` for the round-trip. Spawn 5 concurrent `await connector.get_access_token("user-1", "linkedin")` via `asyncio.gather`. Assert: all 5 results are equal AND match `"plain-new-access"` (from the mocked response). Assert `len(post_calls) == 1` — only ONE refresh fired (lock works).

    3. **test_refresh_does_not_block_event_loop**: Same expired-row setup. Spawn TWO tasks: (a) `await connector.get_access_token(...)` (will trigger refresh that sleeps for 1 second); (b) a "heartbeat" task that increments a counter every 100ms and sleeps. Run both via `asyncio.gather` with a timeout of 2 seconds. Assert the heartbeat counter advanced ≥ 8 times during the 1 second refresh window (well above the ≥4 threshold from must_haves; tolerates jitter on slow CI). This proves `httpx.AsyncClient` is genuinely yielding to the event loop.

    Run `uv run pytest tests/unit/social/test_async_refresh.py -x -v 2>&1 | tail -25` — ALL 3 fail (TypeError: 'str' object is not awaitable / get_access_token is not a coroutine function / etc.).

    Commit message: `test(101-02): add failing tests for async refresh + per-key Lock (AUTH-05)`.
  </behavior>
  <action>
    1. Create `tests/unit/social/test_async_refresh.py`. Imports: `from __future__ import annotations`, `import asyncio`, `import inspect`, `import pytest`, `from datetime import datetime, timedelta, timezone`, `from unittest.mock import patch`, `from app.social.connector import SocialConnector`.
    2. Reuse the `_FakeClient` from Task 1's file (DRY — extract to `tests/unit/social/conftest.py` with a `fake_supabase_client` fixture if it grows past one usage).
    3. Build a mock `httpx.AsyncClient` class with an `__aenter__`/`__aexit__` and an async `.post(...)` that appends to a `post_calls` list and `await asyncio.sleep(0.5)` (or 1.0 for test 3).
    4. Verify FAIL: `uv run pytest tests/unit/social/test_async_refresh.py -x -v 2>&1 | tail -25` — all 3 fail.
    5. Lint: `uv run ruff check tests/unit/social/test_async_refresh.py --fix`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_async_refresh.py -x -v 2>&1 | tail -25</automated>
  </verify>
  <done>
    `tests/unit/social/test_async_refresh.py` exists with 3 tests, ALL FAIL. Commit `test(101-02): add failing tests for async refresh + per-key Lock (AUTH-05)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Rewrite connector for Redis PKCE + async refresh</name>
  <files>app/social/connector.py</files>
  <behavior>
    After this task: ALL 8 tests from Tasks 1+2 are GREEN. Existing test `tests/unit/test_social_connector_security.py::test_get_access_token_decrypts_stored_token` is updated to async (one-line patch — see Task 4). The two existing PKCE-Postgres tests in that file (lines 109-185) are removed in Task 4.

    Concrete edits to `app/social/connector.py`:

    1. **Imports**: Add `import asyncio`, `from typing import ClassVar`, `from app.services.cache import get_cache_service`. Keep `httpx` import — but move the inline imports inside `handle_callback` and `_refresh_token` to module scope.

    2. **Class state**:
       - DELETE `self._pkce_verifiers: dict[str, str] = {}` (line 114).
       - DELETE the `PKCE_STATE_TABLE` constant (line 29) — no longer needed.
       - DELETE `_store_pkce_verifier` and `_pop_pkce_verifier` methods (lines 152-211) entirely.
       - ADD class-level lock registry, mirroring `IntegrationManager._refresh_locks` (`integration_manager.py:70-88`):
         ```python
         _refresh_locks: ClassVar[dict[tuple[str, str], asyncio.Lock]] = {}
         _locks_guard: ClassVar[asyncio.Lock] = None  # lazy-init in _get_refresh_lock
         ```
         Note: `asyncio.Lock()` constructed at class-definition time can bind to the wrong loop. Defer by using `_locks_guard: ClassVar[asyncio.Lock | None] = None` and lazy-init inside `_get_refresh_lock` (which is `async`). See pattern below.

    3. **NEW helper `_get_refresh_lock`** (mirror `IntegrationManager` exactly):
       ```python
       @classmethod
       async def _get_refresh_lock(cls, user_id: str, platform: str) -> asyncio.Lock:
           if cls._locks_guard is None:
               cls._locks_guard = asyncio.Lock()
           key = (user_id, platform)
           async with cls._locks_guard:
               if key not in cls._refresh_locks:
                   cls._refresh_locks[key] = asyncio.Lock()
               return cls._refresh_locks[key]
       ```

    4. **`get_authorization_url` becomes async**:
       ```python
       async def get_authorization_url(
           self, platform: str, user_id: str, redirect_uri: str
       ) -> dict[str, Any]:
           # ... existing platform/client_id validation unchanged ...
           state = f"{user_id}:{secrets.token_urlsafe(16)}"
           verifier, challenge = self._generate_pkce()
           cache = get_cache_service()
           ok = await cache.set_generic(
               f"pikar:integration:pkce:{state}",
               {"verifier": verifier, "platform": platform},
               ttl=600,
           )
           if not ok:
               return {"error": "OAuth temporarily unavailable, please retry"}
           # ... rest of URL building unchanged ...
       ```

    5. **`handle_callback` PKCE read+delete (replace lines 285-287)**:
       ```python
       cache = get_cache_service()
       cached = await cache.get_generic(f"pikar:integration:pkce:{state}")
       if cached.is_miss or cached.is_error or not cached.value:
           return {"error": "PKCE verifier not found. Session may have expired."}
       cached_payload = cached.value
       if cached_payload.get("platform") != platform:
           return {"error": "PKCE verifier platform mismatch"}
       verifier = cached_payload.get("verifier")
       if not verifier:
           return {"error": "PKCE verifier not found. Session may have expired."}
       await cache.delete(f"pikar:integration:pkce:{state}")
       ```

    6. **`get_access_token` becomes async** with double-check + lock pattern (mirror `integration_manager.py:166-205`):
       ```python
       async def get_access_token(self, user_id: str, platform: str) -> str | None:
           account = await asyncio.to_thread(self._fetch_active_account, user_id, platform)
           if not account:
               return None
           if not _is_token_expiring(account.get("token_expires_at")):
               return self._decrypt_token(account.get("access_token"))
           lock = await self._get_refresh_lock(user_id, platform)
           async with lock:
               # double-check
               account = await asyncio.to_thread(self._fetch_active_account, user_id, platform)
               if not account:
                   return None
               if not _is_token_expiring(account.get("token_expires_at")):
                   return self._decrypt_token(account.get("access_token"))
               return await self._refresh_token(user_id, platform, account)
       ```
       Define `_fetch_active_account(self, user_id, platform) -> dict | None` as the sync helper that wraps the existing `.execute()` call (same code as current lines 368-380). Define module-level `_is_token_expiring(iso_string) -> bool` returning True when expires_at is None OR within 5 minutes. Both helpers are simple (~5-10 lines each).

    7. **`_refresh_token` becomes async** with `httpx.AsyncClient` (mirror `integration_manager.py:207-279`):
       ```python
       async def _refresh_token(
           self, user_id: str, platform: str, account: dict[str, Any]
       ) -> str | None:
           refresh_token = self._decrypt_token(account.get("refresh_token"))
           if not refresh_token or platform not in PLATFORM_CONFIGS:
               return None
           config = PLATFORM_CONFIGS[platform]
           client_id = os.environ.get(config["client_id_env"])
           client_secret = os.environ.get(config["client_secret_env"])
           if not client_id or not client_secret:
               return None
           try:
               async with httpx.AsyncClient(timeout=30.0) as http:
                   resp = await http.post(
                       config["token_url"],
                       data={
                           "grant_type": "refresh_token",
                           "refresh_token": refresh_token,
                           "client_id": client_id,
                           "client_secret": client_secret,
                       },
                   )
                   if resp.status_code != 200:
                       return None
                   tokens = resp.json()
               new_access = tokens.get("access_token")
               if not new_access:
                   return None
               expires_in = tokens.get("expires_in", 3600)
               new_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
               update_data: dict[str, Any] = {
                   "access_token": self._encrypt_token(new_access),
                   "token_expires_at": new_expires.isoformat(),
               }
               if tokens.get("refresh_token"):
                   update_data["refresh_token"] = self._encrypt_token(tokens["refresh_token"])
               await asyncio.to_thread(
                   self._update_account, user_id, platform, update_data
               )
               return new_access
           except Exception:
               logger.exception("Refresh token failed for user=%s platform=%s", user_id, platform)
               return None
       ```
       Helper `_update_account(self, user_id, platform, update_data)` wraps the existing `.update().eq().eq().execute()` chain (current lines 458-460).

    8. **DELETE leftover Postgres-PKCE code paths** so the module no longer references `oauth_pkce_states` or `PKCE_STATE_TABLE`. The Postgres table remains in the DB (defined at `20260508123000_social_oauth_security.sql:4-11`) but is now orphan; **DO NOT** drop it in this plan — Phase 108 hygiene will clean up. Note this in the summary.

    9. Run `uv run pytest tests/unit/social/ -x -v 2>&1 | tail -40`. ALL 8 new tests should pass. The two PKCE-Postgres tests in `tests/unit/test_social_connector_security.py:109-185` will FAIL — that is expected; Task 4 cleans them up.

    10. Lint + types: `uv run ruff check app/social/connector.py --fix && uv run ruff format app/social/connector.py && uv run ty check app/social/connector.py`.

    Commit message: `feat(101-02): Redis-backed PKCE + async refresh with per-key Lock in SocialConnector (AUTH-03, AUTH-05)`.
  </behavior>
  <action>
    1. Edit `app/social/connector.py` per the 9 numbered edits in the behavior section.
    2. After the rewrite, re-read the file end-to-end and confirm: no references to `_pkce_verifiers`, `_store_pkce_verifier`, `_pop_pkce_verifier`, `oauth_pkce_states`, or `PKCE_STATE_TABLE`; `httpx.Client` (sync) is gone.
    3. Module structure: `import asyncio` and `from typing import ClassVar` go in the alphabetical block at the top. `from app.services.cache import get_cache_service` joins the existing `from app.services.encryption import ...` line below.
    4. Run `uv run pytest tests/unit/social/ -x -v` — all 8 new tests pass.
    5. Lint + format + types as listed.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/ -x -v 2>&1 | tail -40 && uv run ruff check app/social/connector.py 2>&1 | tail -5</automated>
  </verify>
  <done>
    `app/social/connector.py` no longer references the in-memory dict, the Postgres PKCE table, or `httpx.Client`. `get_authorization_url`, `get_access_token`, `_refresh_token` are all `async def`. Per-key `asyncio.Lock` registry mirrors `IntegrationManager`. All 8 new tests in `tests/unit/social/test_pkce_redis.py` and `tests/unit/social/test_async_refresh.py` are GREEN. `ruff check` clean. `ty check` clean. Commit `feat(101-02): Redis-backed PKCE + async refresh with per-key Lock in SocialConnector (AUTH-03, AUTH-05)` lands.
  </done>
</task>

<task type="auto">
  <name>Task 4: Update callers + obsolete tests for async signatures</name>
  <files>app/social/publisher.py, app/social/analytics.py, app/mcp/tools/social_listening.py, app/mcp/tools/google_seo.py, app/routers/configuration.py, app/agents/tools/social.py, tests/unit/test_social_connector_security.py</files>
  <action>
    Mechanical updates to add `await` where the connector methods are now async, plus retire two now-obsolete tests.

    1. **`app/social/publisher.py`**:
       - Line 31: `def _get_token_or_error(self, user_id: str, platform: str) -> tuple[str | None, dict | None]:` → `async def _get_token_or_error(...)`.
       - Line 35: `token = self.connector.get_access_token(user_id, platform)` → `token = await self.connector.get_access_token(user_id, platform)`.
       - Find every caller of `_get_token_or_error` in this file (likely `post_with_media` and similar) — add `await` to each invocation. Use `grep -n "_get_token_or_error" app/social/publisher.py` to find all sites.

    2. **`app/social/analytics.py`**:
       - Line 35: `def _get_token(self, user_id: str, platform: str) -> str | None:` → `async def _get_token(...)`.
       - Line 37: `return self.connector.get_access_token(user_id, platform)` → `return await self.connector.get_access_token(user_id, platform)`.
       - All `self._get_token(...)` call sites in this file (already inside `async def get_*_metrics` methods) → `await self._get_token(...)`. Use grep to find all.

    3. **`app/mcp/tools/social_listening.py`** (line 126):
       `token = connector.get_access_token(user_id, "twitter")` → `token = await connector.get_access_token(user_id, "twitter")`. The enclosing function is already `async def`.

    4. **`app/mcp/tools/google_seo.py`** (line 77):
       `token = connector.get_access_token(user_id, "google_search_console")` → `token = await connector.get_access_token(user_id, "google_search_console")`. Already in `async def`.

    5. **`app/routers/configuration.py`** (line 662):
       `result = connector.get_authorization_url(...)` → `result = await connector.get_authorization_url(...)`. Already in `async def connect_social`.

    6. **`app/agents/tools/social.py`** (lines 124-145):
       Convert `def get_oauth_url(...)` → `async def get_oauth_url(...)`. Update line 145 to `return await connector.get_authorization_url(platform, user_id, redirect_uri)`. ADK supports async tools — verify by grepping for an existing async tool registered in `SOCIAL_TOOLS` (line 170 area). If `SOCIAL_TOOLS = [..., get_oauth_url, ...]` works for both sync and async, no further change needed. **Verify via grep**: `grep -n "async def" app/agents/tools/social.py` — if other tools in this file are already async (e.g. `post_*`), then async-tool registration is supported.

    7. **`tests/unit/test_social_connector_security.py`** — clean up obsolete tests:
       - **DELETE** `test_pkce_verifier_is_persisted_encrypted_and_consumed` (lines 109-129) — tested the now-removed Postgres path.
       - **DELETE** `test_callback_uses_persisted_pkce_and_stores_encrypted_tokens` (lines 132-185) — same reason; identical contract is now covered by `tests/unit/social/test_pkce_redis.py::test_handle_callback_reads_pkce_from_redis_and_deletes`.
       - **UPDATE** `test_get_access_token_decrypts_stored_token` (lines 188-202): make it `async def`, add `@pytest.mark.asyncio`, change the call to `assert await connector.get_access_token("user-id", "linkedin") == "access-token"`. KEEP this test — it's a useful smoke test for the encryption-on-read path.
       - The `_FakeClient`/`_FakeTable` helper classes can stay in this file (still used by the remaining test). Drop the `pkce_rows` dict and `_execute_pkce` branch since no test uses them anymore.

    8. Verify everything: `uv run pytest tests/unit/social/ tests/unit/test_social_connector_security.py -x -v 2>&1 | tail -20`. All tests GREEN. Then `uv run pytest tests/unit/ tests/integration/ -x 2>&1 | tail -30` — full unit + integration run. Any unrelated failures must be diagnosed separately (likely none if grep was thorough).

    9. Lint all modified files: `uv run ruff check app/ tests/ --fix && uv run ruff format app/ tests/`.

    Commit message: `refactor(101-02): await async connector methods at all caller sites; retire Postgres-PKCE tests`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/ tests/unit/test_social_connector_security.py -x -v 2>&1 | tail -25 && uv run ruff check app/social/ app/mcp/tools/social_listening.py app/mcp/tools/google_seo.py app/routers/configuration.py app/agents/tools/social.py 2>&1 | tail -5</automated>
  </verify>
  <done>
    All 5 caller files have `await` added at the right call sites. `get_oauth_url` in `agents/tools/social.py` is async. `tests/unit/test_social_connector_security.py` has the two obsolete PKCE-Postgres tests removed and the encryption test converted to async; all remaining tests in that file are GREEN. `tests/unit/social/` 8 tests still GREEN. Full unit-test run is GREEN. `ruff check` clean across all modified files. Commit `refactor(101-02): await async connector methods at all caller sites; retire Postgres-PKCE tests` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end:
1. `uv run pytest tests/unit/social/ tests/unit/test_social_connector_security.py -x -v` — 9 tests GREEN (8 new + 1 surviving original).
2. `uv run pytest tests/unit tests/integration -x` — full suite GREEN (modulo unrelated failures, which must be < the count before this plan started; record baseline before Task 1).
3. `grep -nR "_pkce_verifiers\|_store_pkce_verifier\|_pop_pkce_verifier\|PKCE_STATE_TABLE" app/social/ tests/` — returns zero matches (the legacy names are gone from app code).
4. `grep -nR "httpx.Client(" app/social/` — returns zero matches (only `httpx.AsyncClient` remains).
5. `grep -nR "get_access_token" app/` and ensure every call site has `await` in front.

Manual smoke (deferred to phase-level UAT):
- Run a real OAuth round-trip against a single LinkedIn dev app: `make local-backend`, navigate to /configuration, click Connect LinkedIn, complete the consent flow, observe the new `connected_accounts` row and a Redis `MONITOR | grep pkce` show the SET/GET/DEL sequence.
</verification>

<success_criteria>
- `app/social/connector.py` has `_pkce_verifiers` dict removed, `_store_pkce_verifier`/`_pop_pkce_verifier` deleted, `PKCE_STATE_TABLE` constant deleted; `oauth_pkce_states` table no longer referenced.
- `get_authorization_url`, `get_access_token`, `_refresh_token` are all `async def`. `httpx.AsyncClient` replaces `httpx.Client`. Per-`(user_id, platform)` `asyncio.Lock` registry exists at class scope and mirrors `IntegrationManager._refresh_locks`.
- PKCE Redis keys use `pikar:integration:pkce:{state}` namespace (matches RESEARCH §AUTH-03 §Redis-keyed short-TTL state pattern).
- Redis-unavailable behavior: `get_authorization_url` returns `{"error": "OAuth temporarily unavailable, please retry"}`; `handle_callback` returns `{"error": "PKCE verifier not found..."}` and never calls the token endpoint.
- All 4 production callers of `get_access_token` and the 2 callers of `get_authorization_url` are updated to `await`.
- 8 new tests + 1 updated original test are GREEN. Two obsolete PKCE-Postgres tests are deleted.
- `ruff check` and `ty check` clean for `app/social/connector.py`, `app/agents/tools/social.py`, and the 4 caller files.
- Concurrent-refresh test proves single HTTP refresh under 5-way contention; heartbeat test proves event loop is not blocked.
</success_criteria>

<output>
After completion, create `.planning/phases/101-security-hardening/101-02-pkce-redis-async-refresh-SUMMARY.md` documenting:
- The decision to delete (not preserve) the in-memory PKCE fallback (RESEARCH §Open Question 3 resolution: fail-closed)
- That `oauth_pkce_states` table remains in the DB orphaned (Phase 108 cleanup)
- Caller-site list with file:line for each `await` addition
- Test count delta (existing 3 → 1 surviving + 8 new = 9 in social/ scope)
</output>
