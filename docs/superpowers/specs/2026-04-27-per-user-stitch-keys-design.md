# Per-User Stitch Keys + Always-Active Tavily/Firecrawl

**Date:** 2026-04-27
**Author:** Pikar AI eng
**Status:** Spec — pending review

## Problem

The Configuration page surfaces three integrations as "not active":

1. **Tavily** and **Firecrawl** — server-managed (admin sets `TAVILY_API_KEY` / `FIRECRAWL_API_KEY` in `.env`). End users should not need to configure them; they should always show as active.
2. **Google Stitch** — there is a setup wizard, but it does not work end-to-end. Three breakages:
   - The save endpoint at `app/routers/configuration.py:495` (`save-user-config`) rejects `STITCH_API_KEY` because of the `_ALLOWED_CONFIG_KEYS` allowlist (line 509-513). Saves silently return `success: false`.
   - Even if a key were saved, no runtime path reads from `user_configurations`.
   - The Stitch MCP runs as a single Node subprocess spawned at FastAPI lifespan startup with the env key baked in. There is no mechanism for any user other than the env-key owner to use Stitch.

## Goals

- Tavily and Firecrawl render as always-active server-managed integrations.
- Users can save their own Google Stitch API key in Configuration and have it work for **all** Stitch-backed flows, including the app-builder screen-generation pipeline.
- Existing single-tenant deployments (env-only `STITCH_API_KEY`) keep working with no behavior change.

## Non-goals

- Field-level encryption of saved API keys at rest. Out of scope; flagged for a future hardening pass.
- Validate-on-save (test ping to Stitch before storing). Skipped to avoid an extra Stitch invocation.
- Eager pre-warm of per-user MCP subprocesses on login. Lazy on first use only.
- An admin UI to list or revoke per-user keys.

## Architecture

### Tavily / Firecrawl — UI-only change

Treat Tavily and Firecrawl as platform-managed in `BUILT_IN_TOOLS_INFO` rendering. Their backend env-detection logic stays as-is (admin can still verify via `/health/connections` and `app/routers/admin/config.py`), but the per-user `/configuration/mcp-status` response presents them with `configured: True` and a fixed status string `"Active for all users"`. The frontend drops the amber/inactive variant for these two.

This is purely a presentation change. No backend integration logic is touched.

### Stitch — per-user MCP pool

Replace the singleton `StitchMCPService` instance with a `StitchPool` that owns a dict of `StitchMCPService` keyed by pool key.

```
class StitchPool:
    _services: dict[str, StitchMCPService]
    _tasks: dict[str, asyncio.Task]
    _key_fingerprints: dict[str, str]   # sha256 prefix of api key — detects rotation
    _last_used: dict[str, float]        # monotonic timestamp
    _spawn_lock: asyncio.Lock
    _evict_task: asyncio.Task | None

    async def get_or_spawn(user_id: str | None) -> StitchMCPService
    async def shutdown() -> None
    async def evict_idle(ttl_seconds: int = 600) -> int
```

#### Key resolution per request

1. If `user_id` is supplied and `user_configurations` row `(user_id, "STITCH_API_KEY")` exists → use that key, pool key = `f"user:{user_id}"`.
2. Otherwise if `os.environ["STITCH_API_KEY"]` is set → use env key, pool key = `"__env_default__"`.
3. Otherwise if `APP_BUILDER_USE_MOCK_STITCH=1` → use the existing `MockStitchMCPService`, pool key = `"__mock__"`.
4. Otherwise → raise `RuntimeError("No Stitch API key configured. Connect your Stitch key in Configuration.")`.

#### Pool semantics

- **Lazy spawn.** First call for a given `pool_key` acquires `_spawn_lock`, instantiates a `StitchMCPService` with the resolved key, starts its `_run()` background task, and waits for `_ready` (existing 30s timeout reused).
- **Key rotation detection.** Each entry stores a sha256 prefix of the resolved key. If the user updates their saved key, the next `get_or_spawn` sees a fingerprint mismatch, cancels the old task, and respawns.
- **Crash recovery.** If `_healthy` becomes false, the next `get_or_spawn` removes the entry and spawns fresh.
- **Idle eviction.** A background task started during lifespan iterates the pool every 60s and cancels entries whose `_last_used` is older than 600s (10 min).
- **Shutdown.** Lifespan calls `pool.shutdown()` which cancels every task and clears the pool.
- **Concurrency.** `_spawn_lock` is held only during pool dict mutation. Per-request `call_tool` invocations use the existing per-service `_lock` so different users do not block each other.

#### Subprocess key injection

Today, `StitchMCPService._run()` reads `os.environ["STITCH_API_KEY"]` at spawn time. The pool adds an `__init__(api_key: str)` parameter on `StitchMCPService` and passes it through `StdioServerParameters.env`. The parent process env is no longer mutated.

### Per-user storage

Keys are saved into the existing `user_configurations` table with `is_sensitive=true`. No schema change.

A new helper module `app/services/user_config.py` exposes:

```
def get_user_api_key(user_id: str, key_name: str) -> str | None
def set_user_api_key(user_id: str, key_name: str, api_key: str) -> None
```

Both are synchronous and go through `get_service_client()` (the Supabase Python client is sync; backend is the only writer, RLS bypass via service role). Callers in async context wrap them with `asyncio.to_thread` if the caller is performance-sensitive; otherwise direct sync calls are acceptable for a one-row lookup.

### Save endpoint

A new dedicated endpoint `POST /configuration/save-api-key` is added to `app/routers/configuration.py`:

```
class SaveApiKeyRequest(BaseModel):
    tool_id: str
    api_key: str

ALLOWED_API_KEY_TOOLS = {
    "stitch": "STITCH_API_KEY",
}
```

- Validates `tool_id` is in the allowlist.
- Validates `api_key` is non-empty and reasonably bounded (`len <= 512`).
- Writes via `set_user_api_key`.
- Does **not** test the key. Returns immediately.

The existing generic `save-user-config` allowlist stays untouched (no API keys mixed in with theme/language/etc.).

### Status endpoint

`GET /configuration/mcp-status` is updated:

- Tavily/Firecrawl built-ins return `configured: True` with status `"Active for all users"` regardless of env state.
- Stitch is treated as `configured = (user_has_saved_key) or (env_set)`. The check requires the authenticated user; the endpoint already injects `current_user_id` via `Depends(get_current_user_id)`.

### Call-site changes

Six files currently call `get_stitch_service()` synchronously:

| File | Function |
|------|----------|
| `app/agents/tools/app_builder.py` | `_generate_screen_async`, `_list_stitch_tools_async` |
| `app/routers/app_builder.py` | screen-generation route handler |
| `app/services/screen_generation_service.py` | `generate_screen_variants`, `generate_device_variant` |
| `app/services/iteration_service.py` | iteration generators |
| `app/services/multi_page_service.py` | multi-page generation |
| `app/fast_api_app.py` lifespan | singleton bootstrap |

All six already have `user_id` in scope. Mechanical change: `get_stitch_service()` → `await get_stitch_service(user_id)`. The function is now `async` (it may spawn a subprocess and wait).

The agent tool `generate_app_screen` (sync wrapper) already accepts `user_id: str | None`. The inner `_generate_screen_async` simply forwards it.

### Frontend changes

- `frontend/src/app/api/configuration/save-api-key/route.ts` — repoint at the new dedicated backend endpoint `/configuration/save-api-key` (not the generic `save-user-config`).
- `frontend/src/app/dashboard/configuration/page.tsx` — for built-in tools, drop the amber/inactive branch when `tool.id` is `tavily` or `firecrawl`. Always render them as the active variant.

## Risks

- **Memory.** Each per-user MCP subprocess is a Node process at ~50-80 MB. 50 active concurrent users ≈ 2.5-4 GB. Idle eviction at 10 min mitigates but does not eliminate. If scale grows beyond Cloud Run instance memory, switch to direct Stitch REST calls.
- **Cold-start latency.** First Stitch call per user pays the npx subprocess startup (~1-2s, currently 30s timeout). The user-visible impact is one extra second on the very first screen generation per user per 10-min window.
- **Key rotation gap.** Between a user updating their key and the next request, the in-flight subprocess may briefly continue with the old key. Acceptable; the next call respawns.
- **No encryption at rest.** RLS-protected only. Stripe/HubSpot keys via `save-user-config` would have the same shape. Worth a follow-up.

## Implementation order

1. `app/services/user_config.py` — read/write helpers.
2. `app/services/stitch_mcp.py` — extract `StitchPool`, give `StitchMCPService` an `api_key` param.
3. `app/fast_api_app.py` lifespan — instantiate pool, pre-warm `__env_default__`, register evict task, wire shutdown.
4. Update all 6 call sites to `await get_stitch_service(user_id)`.
5. `app/routers/configuration.py` — new `save-api-key` endpoint, status-endpoint Stitch + Tavily/Firecrawl logic.
6. Frontend route repoint + always-active rendering for Tavily/Firecrawl.
7. Tests: pool spawn/respawn/evict, key resolution order, save-api-key allowlist, status reflects user-saved key.

## Tests

Unit:
- `StitchPool.get_or_spawn` returns the same service for repeated calls (same key).
- `StitchPool.get_or_spawn` respawns when fingerprint changes (key rotated).
- `StitchPool.evict_idle` cancels entries past TTL, leaves fresh ones.
- `StitchPool.shutdown` cancels all tasks.
- `get_user_api_key` returns `None` for unset keys, value for set keys.
- `save-api-key` rejects unknown `tool_id`, empty/oversize key.
- `mcp-status` returns `configured: True` for Tavily/Firecrawl always.
- `mcp-status` returns `configured: True` for Stitch when user has saved a key but env is unset.

Integration (with `APP_BUILDER_USE_MOCK_STITCH=1`):
- Two users with different "saved keys" each get their own pool entry.
- A user with no saved key falls through to env / mock.

## Open questions

None at spec time. Three decisions taken with defaults:
- TTL: 600s.
- Pre-warm: `__env_default__` only.
- Validate-on-save: skipped.
