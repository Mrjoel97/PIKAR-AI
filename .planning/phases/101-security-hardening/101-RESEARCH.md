# Phase 101 Research: Security Hardening for `connected_accounts`

**Researched:** 2026-05-08
**Domain:** OAuth 2.0 token storage, RLS hardening, PKCE persistence, async refresh
**Confidence:** HIGH (most claims verified against repo files + official provider docs)

## Phase Requirements

| ID | Description (from `.planning/REQUIREMENTS.md:16-20`) | Research Support |
|----|------|------|
| AUTH-01 | RLS policy enforces `auth.uid()::text = user_id` (USING + WITH CHECK) replacing permissive `USING (true)` | Existing migration `20260415113000_harden_connected_accounts_rls.sql` already does this with `(SELECT auth.uid()) = user_id`; gap to verify is whether prod actually has the migration applied. See "Current State / AUTH-01" |
| AUTH-02 | `access_token`/`refresh_token` Fernet-encrypted at rest via `encrypt_secret`/`decrypt_secret` | Ready-made helpers in `app/services/encryption.py:60-100`; reference pattern in `app/services/integration_manager.py:124-143` |
| AUTH-03 | PKCE verifiers persisted in Redis with 10-min TTL keyed by state token | Ready cache API: `cache.set_generic`/`get_generic`/`delete` in `app/services/cache.py:670-725`; identical pattern at `app/routers/integrations.py:148-153` |
| AUTH-04 | OAuth callback captures `platform_user_id` + `platform_username` from each provider's profile endpoint | Provider profile endpoint matrix verified for LinkedIn, Threads, TikTok, YouTube via official docs; Twitter/Pinterest from training (LOW–MEDIUM) |
| AUTH-05 | Token refresh path uses `httpx.AsyncClient`; does not block event loop | `IntegrationManager._refresh_token` already async (`integration_manager.py:207-256`); `SocialConnector._refresh_token` is sync (`connector.py:288-355`) — the gap |

## Summary

The 2026-05-08 audit description for AUTH-01 is **partially stale**: a hardening migration (`20260415113000_harden_connected_accounts_rls.sql`) already exists in the repo and replaces `USING (true)` with `(SELECT auth.uid()) = user_id` (typing-correct since `connected_accounts.user_id` is `UUID`, not `TEXT`). The phase still has work to do on AUTH-01 — verify the migration is applied in prod, add a regression test, and reconcile the requirement wording (`auth.uid()::text = user_id` is incorrect for a UUID column).

AUTH-02 (Fernet at rest), AUTH-03 (PKCE → Redis), AUTH-04 (`platform_user_id` capture), and AUTH-05 (sync→async refresh) all have ready-made primitives in the codebase: `encrypt_secret`/`decrypt_secret` (`app/services/encryption.py`), `CacheService.set_generic`/`get_generic`/`delete` (`app/services/cache.py:670-725`), and a working async refresh implementation in `IntegrationManager._refresh_token` (`app/services/integration_manager.py:207-256`) that the social connector should mirror.

**Primary recommendation:** Treat this phase as **integration**, not greenfield — every primitive already exists for `integration_credentials`. The work is mostly applying those patterns to `SocialConnector`, plus per-provider profile-endpoint calls.

## Current State (verified by reading files)

### AUTH-01 — RLS on `connected_accounts`

- `supabase/migrations/0010_connected_accounts.sql:6` — `user_id UUID NOT NULL` (UUID, **not text**).
- `supabase/migrations/0010_connected_accounts.sql:28-31` — original permissive policy:
  ```sql
  CREATE POLICY "Users manage own accounts" ON connected_accounts
      USING (true) WITH CHECK (true);
  ```
- `supabase/migrations/0028_fix_advisor_issues.sql:256-262` — added a `service_role`-only policy named `"Service Role manages all"`. The permissive `"Users manage own accounts"` policy was **not** dropped here.
- `supabase/migrations/20260415113000_harden_connected_accounts_rls.sql` — **already drops** `"Users manage own accounts"` (line 6) and creates four user-scoped policies using `(SELECT auth.uid()) = user_id` (lines 13-36) plus the `service_role` bypass (lines 38-43). This file looks correct and complete.
- `supabase/migrations/20260322400000_fix_rls_wrapped_auth_uid.sql` — establishes the project convention of wrapping `auth.uid()` in `(SELECT ...)` for RLS perf. The existing harden migration follows this convention; AUTH-01 should keep it.

**Net:** The codified migration history is good. The remaining gap is **verification + test coverage**, not new SQL.

### AUTH-02 — Token encryption at rest

- `app/social/connector.py:222-232` — `handle_callback` writes `access_token` and `refresh_token` directly:
  ```python
  connection_data = {
      ...
      "access_token": tokens.get("access_token"),
      "refresh_token": tokens.get("refresh_token"),
      ...
  }
  self.client.table("connected_accounts").upsert(connection_data, on_conflict="user_id,platform").execute()
  ```
  No call to `encrypt_secret`. Plaintext tokens hit the DB.
- `app/social/connector.py:286, 342-353` — `get_access_token` / `_refresh_token` read raw `access_token` from the row and write raw new tokens on refresh.
- `app/services/encryption.py:60-100` — Fernet helpers (`encrypt_secret`, `decrypt_secret`) backed by `MultiFernet` reading `ADMIN_ENCRYPTION_KEY` (comma-separated for rotation). Already used by `IntegrationManager.store_credentials` (`integration_manager.py:124-125`) — exact pattern to mirror.

### AUTH-03 — PKCE verifier persistence

- `app/social/connector.py:105` — class instance attribute `self._pkce_verifiers: dict[str, str] = {}` (per-process dict).
- `app/social/connector.py:144` — written during `get_authorization_url`: `self._pkce_verifiers[state] = verifier`.
- `app/social/connector.py:189` — read+pop during `handle_callback`: `verifier = self._pkce_verifiers.pop(state, None)`.
- `SocialConnector` is a process-singleton (`get_social_connector` at `connector.py:362-366`). On Cloud Run with N>1 instances, the authorize and callback can land on different containers; the verifier is `None` and the flow fails (root cause stated in audit).
- `app/services/cache.py:30-42` — `REDIS_KEY_PREFIXES["integration"] = "pikar:integration:"` is the convention to reuse.
- `app/services/cache.py:670-725` — `get_generic`, `set_generic` (TTL-aware, JSON-serialized) plus `delete` at `app/services/cache.py:645-667`. All circuit-breaker-decorated.
- `app/routers/integrations.py:148-153` — exact same pattern in production for OAuth state:
  ```python
  await cache.set_generic(f"pikar:integration:oauth_state:{state}", state_data, ttl=600)
  ```
  and read+delete at `integrations.py:228-242`.

### AUTH-04 — Profile capture (`platform_user_id`, `platform_username`)

- `app/social/connector.py:218-227` — `connection_data` does **not** populate `platform_user_id` or `platform_username`. Both columns exist (`0010_connected_accounts.sql:8-9`; `platform_user_id` re-added defensively at `0034_user_configurations.sql:88-97`).
- `app/social/publisher.py:162` — direct downstream consumer is broken because of the missing capture: hardcoded `"author": "urn:li:person:PERSON_ID"` literal placeholder. Phase 103 depends on this fix.
- `app/routers/configuration.py:480` — UI reads `connection.get("platform_username")` to show the connected account name, currently always `None`.

### AUTH-05 — Sync refresh on async path

- `app/social/connector.py:317-353` — `_refresh_token` uses `with httpx.Client(timeout=30.0) as http: ...` (sync, blocking).
- `app/social/connector.py:259-286` — `get_access_token` is `def` (sync) and calls `_refresh_token` synchronously.
- Callers of `connector.get_access_token` invoked from async contexts (would block the event loop):
  - `app/social/publisher.py:35` — `_get_token_or_error` (sync method) called from async `post_with_media`.
  - `app/social/analytics.py:37` — `_get_token` (sync) called from many `async def get_*_metrics`.
  - `app/mcp/tools/social_listening.py:126` — async tool.
  - `app/mcp/tools/google_seo.py:77` — async tool.
- For comparison, `IntegrationManager._refresh_token` (`integration_manager.py:207-279`) does it correctly with `async with httpx.AsyncClient(timeout=30.0)` plus an `asyncio.Lock` per `(user_id, provider)` to prevent concurrent refresh races.

## Target State

### AUTH-01 — RLS verified and tested
- Final RLS state on `public.connected_accounts`:
  - `Users can view own connected accounts` — SELECT, USING `(SELECT auth.uid()) = user_id`
  - `Users can insert own connected accounts` — INSERT, WITH CHECK same
  - `Users can update own connected accounts` — UPDATE, USING + WITH CHECK same
  - `Users can delete own connected accounts` — DELETE, USING same
  - `Service Role manages all` — FOR ALL TO `service_role`, USING/WITH CHECK `true`
- ROADMAP success criterion #1: "an integration test asserts cross-user denial." That test does not yet exist; must be added.
- The REQUIREMENTS.md wording `auth.uid()::text = user_id` should be reconciled to the actual implemented expression (see Open Questions §1).

### AUTH-02 — Encryption envelope on every write/read
- Every `connected_accounts.access_token` and `refresh_token` value in the DB is a Fernet token (URL-safe base64 starting with `gAAAAA...`).
- `connector.handle_callback` encrypts before upsert; `connector.get_access_token` decrypts before returning.
- `connector._refresh_token` decrypts the stored refresh token before sending it to the provider, then encrypts the new access/refresh before update.
- Existing rows in prod (if any) must be migrated — see "Implementation / AUTH-02" for the data-migration approach.
- Success criterion #2: raw `SELECT access_token FROM connected_accounts` returns Fernet ciphertext, not a bearer token.

### AUTH-03 — PKCE in Redis, 10-min TTL
- `get_authorization_url` writes verifier to Redis: key `pikar:integration:pkce:{state}`, value `{"verifier": "...", "platform": "..."}`, TTL 600s.
- `handle_callback` reads via `get_generic`, validates, deletes via `delete`. The in-process `_pkce_verifiers` dict is removed.
- Behavior under Redis outage: per project's **circuit-breaker pattern** (`app/services/cache.py:64-93`), a Redis failure must surface a clear error to the user ("OAuth session lost — please retry"), not silently fall back to in-memory (because in-memory still doesn't survive multi-instance routing). See Open Questions §3.

### AUTH-04 — Profile populated on every callback
After successful token exchange, `connector.handle_callback` calls each provider's profile endpoint with the new access token, extracts the canonical id + username, and includes both in the `connected_accounts` upsert. Endpoint matrix below.

### AUTH-05 — Async I/O end-to-end
`SocialConnector.get_access_token` and `SocialConnector._refresh_token` become `async def` and use `httpx.AsyncClient`. Callers are updated to `await`. Add an `asyncio.Lock` per `(user_id, platform)` to mirror `IntegrationManager._refresh_locks` (`integration_manager.py:70-88`) and prevent the thundering-herd problem when N parallel publishes hit an expired token.

## Implementation Approach

### AUTH-01 — Migration (idempotent, safe to re-apply)

Add a verification migration `supabase/migrations/{ts}_phase101_verify_connected_accounts_rls.sql` that **re-asserts** the policies (idempotent DROP+CREATE — same shape as `20260415113000`). This guarantees prod ends up in the correct state regardless of whether the existing harden migration was applied. Pseudo-code:

```sql
ALTER TABLE public.connected_accounts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users manage own accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can view own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can insert own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can update own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Users can delete own connected accounts" ON public.connected_accounts;
DROP POLICY IF EXISTS "Service Role manages all" ON public.connected_accounts;

-- Recreate the four user-scoped policies + service_role bypass
-- (same body as 20260415113000_harden_connected_accounts_rls.sql)
```

**Why service_role still works:** Supabase's `service_role` JWT bypasses RLS entirely (Postgres `BYPASSRLS` attribute or equivalent). Server-side code in `app/routers/integrations.py:320-326` and `app/social/connector.py:107-108` uses `get_service_client()` so writes/reads from the FastAPI process are unaffected. End-user reads from the Cloudflare-native social-status endpoint (`configuration.py:451-456`) go through the anon client + caller JWT and are now properly scoped.

**Test (success criterion #1):** an integration test that creates two users with seeded rows and asserts user A's anon-client-with-A's-JWT can read only A's rows.

### AUTH-02 — Encryption + data migration

**Code changes** in `app/social/connector.py`:
1. Import `from app.services.encryption import encrypt_secret, decrypt_secret`.
2. In `handle_callback` (lines 218-232): wrap `access_token` and `refresh_token` with `encrypt_secret(...)` before building `connection_data`; `refresh_token` is optional so guard with `if tokens.get("refresh_token")`.
3. In `get_access_token` (line 286): `return decrypt_secret(account["access_token"])`.
4. In `_refresh_token` (line 303): `refresh_token = decrypt_secret(account["refresh_token"])` before posting; in `update_data` (lines 341-347), `encrypt_secret(new_access)` and `encrypt_secret(tokens["refresh_token"])`.

**Data migration (one-time):** Existing rows in prod likely contain plaintext tokens. Recommended approach is a **one-time Python script** (not SQL/PL/pgSQL — Fernet primitives live in Python and avoid shipping a key into the DB). Plan:

```python
# scripts/migrate_connected_accounts_encryption.py
# Read all rows; for any row whose access_token does NOT start with "gAAAAA"
# (Fernet header), encrypt and update via service-role client. Idempotent.
```

A "is-already-Fernet" detector — `try: decrypt_secret(value); return True; except InvalidToken: return False` — makes the script safe to re-run.

**Alternative considered:** An accompanying SQL migration that adds a `token_encrypted BOOLEAN DEFAULT FALSE` column and lets the application encrypt-on-read-fallback. Rejected — adds permanent code complexity to dodge a one-time migration.

**Test (success criterion #2):** unit test patches `encrypt_secret`/`decrypt_secret` to verify that the value passed to `.upsert()` is the ciphertext output and that `get_access_token` returns the decrypted plaintext.

### AUTH-03 — PKCE in Redis

**Code changes** in `app/social/connector.py`:
1. Drop `self._pkce_verifiers: dict[str, str] = {}` at line 105.
2. Make `get_authorization_url` `async def` (it's currently sync). Inject the cache:
   ```python
   from app.services.cache import get_cache_service
   cache = get_cache_service()
   await cache.set_generic(
       f"pikar:integration:pkce:{state}",
       {"verifier": verifier, "platform": platform},
       ttl=600,
   )
   ```
3. In `handle_callback` (already async), replace lines 188-191:
   ```python
   cached = await cache.get_generic(f"pikar:integration:pkce:{state}")
   if cached.is_miss or cached.is_error or not cached.value:
       return {"error": "PKCE verifier not found. Session may have expired."}
   verifier = cached.value["verifier"]
   await cache.delete(f"pikar:integration:pkce:{state}")
   ```

**Key namespace:** reuse the existing `pikar:integration:` prefix (`cache.py:39`). Specifically `pikar:integration:pkce:{state}` to disambiguate from `pikar:integration:oauth_state:{state}` already used by `app/routers/integrations.py:150`.

**Caller updates:** `get_authorization_url` becomes async — must update three callers:
- `app/routers/configuration.py:660-664` (already inside an `async def` route — just add `await`).
- `app/agents/tools/social.py:144` (`get_oauth_url` is sync; needs `asyncio.run` or convert to async tool).
- `app/agents/tools/integration_setup.py:113-115` (check call site).

**TTL behavior:** `set_generic` with `ttl=600` matches the existing OAuth-state pattern (`integrations.py:152`). Redis `SET EX 600` causes the key to disappear at 10 min, which is the success criterion.

**Redis-unavailable behavior:** the circuit-breaker decorator (`cache.py:64-93`) returns `False` from `set_generic` and `CacheResult.from_error(...)` from `get_generic` when Redis is down. We should surface this as a user-visible error (return `{"error": "OAuth temporarily unavailable, please retry"}`) rather than fall back to the in-memory dict — falling back doesn't help because the callback will still land on a different instance. **This is a deliberate degradation** — see Open Questions §3.

### AUTH-04 — Profile capture

After successful token exchange in `handle_callback`, before the upsert, call the provider's profile endpoint and merge `platform_user_id`/`platform_username` into `connection_data`.

**Endpoint matrix (verified):**

| Platform | Endpoint | Method | Auth | ID field | Username field | Confidence | Source |
|---|---|---|---|---|---|---|---|
| `linkedin` | `https://api.linkedin.com/v2/userinfo` | GET | `Authorization: Bearer <token>` | `sub` | `name` (or `given_name + family_name`) | HIGH | [Microsoft Learn — Sign In with LinkedIn using OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2) |
| `twitter` | `https://api.twitter.com/2/users/me` | GET | Bearer | `data.id` | `data.username` | MEDIUM | Training + multiple developer-forum threads (devcommunity.x.com); official docs blocked by host. Already required by ROADMAP success criterion #4 |
| `facebook` | `https://graph.facebook.com/v18.0/me?fields=id,name` | GET | `access_token=<token>` query or Bearer header | `id` | `name` | HIGH | Existing repo usage at `publisher.py:177-182` confirms `graph.facebook.com/v18.0/me` |
| `instagram` | `https://graph.facebook.com/v18.0/me/accounts?fields=instagram_business_account{id,username}` | GET | Bearer | `instagram_business_account.id` | `instagram_business_account.username` | MEDIUM | Standard IG-Graph pattern; the FB user token must be exchanged for the IG Business account. Plan must call this out — single-step like LinkedIn won't work for IG |
| `tiktok` | `https://open.tiktokapis.com/v2/user/info/?fields=open_id,username` | GET | Bearer | `data.user.open_id` | `data.user.username` | HIGH (with caveat) | [TikTok docs](https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info/) — **but** `username` requires `user.info.profile` scope, **not currently in `PLATFORM_CONFIGS["tiktok"]["scopes"]`** at `connector.py:76`. Must add scope or only capture `open_id`. |
| `youtube` | `https://www.googleapis.com/youtube/v3/channels?part=snippet,id&mine=true` | GET | Bearer | `items[0].id` | `items[0].snippet.title` | HIGH | [YouTube Data API v3 docs](https://developers.google.com/youtube/v3/docs/channels/list) |
| `threads` | `https://graph.threads.net/v1.0/me?fields=id,username` | GET | `access_token=<token>` query | `id` | `username` | HIGH | [Meta Threads API docs](https://developers.facebook.com/docs/threads/threads-profiles); Threads NOT yet in `PLATFORM_CONFIGS` — adding it is part of phase 108 hygiene, not 101. Plan can skip Threads or scaffold the helper for later. |
| `pinterest` | `https://api.pinterest.com/v5/user_account` | GET | Bearer | `username` (Pinterest uses username as canonical id) | `username` | LOW | Pinterest API v5 [`Get user account`](https://developers.pinterest.com/docs/api/v5/user_account-get/) — could not deep-fetch the schema. Pinterest also NOT in `PLATFORM_CONFIGS` — same caveat as Threads. |

**Implementation pattern in `connector.py`:**

```python
async def _fetch_platform_profile(
    self, platform: str, access_token: str, http: httpx.AsyncClient
) -> tuple[str | None, str | None]:
    """Return (platform_user_id, platform_username) for the connected account."""
    headers = {"Authorization": f"Bearer {access_token}"}
    if platform == "linkedin":
        r = await http.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        if r.status_code == 200:
            j = r.json()
            return j.get("sub"), j.get("name")
    elif platform == "twitter":
        r = await http.get("https://api.twitter.com/2/users/me", headers=headers)
        if r.status_code == 200:
            j = r.json().get("data", {})
            return j.get("id"), j.get("username")
    # ...etc per provider
    return None, None
```

The caller in `handle_callback` adds:
```python
platform_user_id, platform_username = await self._fetch_platform_profile(
    platform, tokens["access_token"], http
)
connection_data["platform_user_id"] = platform_user_id
connection_data["platform_username"] = platform_username
```

**Failure handling:** if profile fetch fails (404, scope missing, transient), do not abort the OAuth flow — store `None` for both, log the failure, and let the user see their account as connected. A separate background backfill job (out of scope for 101) can retry. Phase 103 (LinkedIn URN) depends on a non-null value but for LinkedIn we have HIGH confidence the call will succeed.

**Test (success criterion #4):** per-provider unit tests that mock `httpx.AsyncClient.get` to return canned profile JSON and assert the resulting `connection_data` carries the correct `platform_user_id`/`platform_username`.

### AUTH-05 — Async refresh

**Code changes** in `app/social/connector.py`:
1. `def get_access_token(self, user_id, platform) -> str | None:` → `async def get_access_token(...)`.
2. Replace the Supabase `.execute()` (sync) with `await self.client.execute(...)`. Note: `get_service_client()` returns the sync `supabase.Client`. For DB calls in async context, either keep the sync calls and wrap with `asyncio.to_thread(...)` (low-risk) **or** migrate to the async client. Given the rest of `connector.py` is sync I/O on Supabase, recommend `asyncio.to_thread` wrapping for the AUTH-05 PR — large client refactor is out of scope.
3. `_refresh_token` becomes `async def _refresh_token(...)` with `async with httpx.AsyncClient(timeout=30.0) as http` (mirror `integration_manager.py:246-256`).
4. Add a class-level lock registry (mirror `integration_manager.py:70-88`):
   ```python
   _refresh_locks: ClassVar[dict[tuple[str, str], asyncio.Lock]] = {}
   _locks_guard = asyncio.Lock()
   ```
   so concurrent publishes for the same expired account refresh once.
5. Update three caller files:
   - `app/social/publisher.py:35` — `_get_token_or_error` becomes async; callers in `post_with_media` add `await`.
   - `app/social/analytics.py:37` — `_get_token` becomes async; callers add `await`.
   - `app/mcp/tools/social_listening.py:126`, `app/mcp/tools/google_seo.py:77` — both already in async functions, so adding `await` is mechanical.

**Test (success criterion #5):** load test that fires 5 concurrent `get_access_token` calls for an expired token, mocks the token endpoint with a 1s delay, asserts only one HTTP call is made (lock works) and that an event-loop heartbeat task continues incrementing during the refresh window.

## Standard Stack

| Library | Version | Purpose | Why standard here |
|---------|---------|---------|-------------------|
| `cryptography` (`Fernet` / `MultiFernet`) | already pinned | Token encryption at rest with key rotation | Used by `app/services/encryption.py`; no need to introduce alternative |
| `httpx.AsyncClient` | already pinned | Non-blocking HTTP for refresh + profile calls | Already used by `IntegrationManager._refresh_token` and `routers/integrations.py:274` |
| `redis.asyncio` via `CacheService` | already pinned | PKCE persistence, circuit-breaker-aware | Project convention via `app/services/cache.py` singleton |
| `supabase-py` (sync) wrapped in `asyncio.to_thread` | already pinned | DB writes from async paths in `connector.py` | Avoids a separate async-Supabase migration for this phase |

**Don't introduce:** new encryption library, new HTTP client, new Redis client, new in-memory cache. Every primitive exists.

## Architecture Patterns

### Pattern 1: encrypt-on-write, decrypt-on-read at the service boundary
Reference: `IntegrationManager.store_credentials` (`integration_manager.py:124-143`) and `get_valid_token` (`integration_manager.py:189, 201, 205`). Plaintext never touches the DB; decrypted plaintext never escapes the service method.

### Pattern 2: per-key asyncio.Lock for refresh races
Reference: `IntegrationManager._refresh_locks` + `_get_refresh_lock` (`integration_manager.py:70-88`) and the double-check inside the lock (`integration_manager.py:193-204`). Mirror exactly in `SocialConnector`.

### Pattern 3: Redis-keyed short-TTL state, namespace `pikar:integration:`
Reference: `app/routers/integrations.py:148-153` and `:228-242`. Use `set_generic`/`get_generic`/`delete` from `cache.py`. Don't reach for `redis.asyncio` directly.

### Anti-patterns
- **Per-process dict for OAuth state** (current `_pkce_verifiers` at `connector.py:105`) — cannot survive horizontal scaling. The audit's whole reason for AUTH-03.
- **Sync HTTP inside an async method** — blocks the event loop; current bug at `connector.py:318`. Phase must eliminate it.
- **Plaintext OAuth tokens in DB** — current bug at `connector.py:222-223`. Phase must eliminate it.
- **`USING (true)` RLS** — already eliminated by `20260415113000` migration; phase verifies and tests.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Symmetric encryption with key rotation | Custom AES wrapper | `app.services.encryption.encrypt_secret/decrypt_secret` | Already implements `MultiFernet` rotation, IV randomness; tested via integration_credentials |
| Redis serialization + circuit breaker | Direct `redis.asyncio` calls | `CacheService.set_generic`/`get_generic`/`delete` | Existing CB at `cache.py:64-93` integrates with health endpoints |
| Per-key async locking | New `dict[str, asyncio.Lock]` from scratch | Mirror `IntegrationManager._get_refresh_lock` (`integration_manager.py:74-88`) | Includes the double-check pattern that prevents lost refreshes |
| OAuth state encoding | Custom JWT or signed cookie | The existing `state = f"{user_id}:{token_urlsafe(16)}"` plus Redis lookup | Project convention; integrated with `routers/integrations.py` already |

## Common Pitfalls

### Pitfall 1: Type mismatch in RLS expression
**What goes wrong:** Writing `auth.uid()::text = user_id` when `user_id` is `UUID` works (text comparison after cast) but is slower and contradicts the project pattern (`20260322400000_fix_rls_wrapped_auth_uid.sql`). The REQUIREMENTS wording is misleading.
**Avoid:** Use `(SELECT auth.uid()) = user_id` exactly, matching `20260415113000:17`.

### Pitfall 2: Forgetting to migrate existing plaintext tokens
**What goes wrong:** Code starts encrypting on write but cannot read pre-existing rows because they fail `decrypt_secret`.
**Avoid:** Run the one-time encrypt-existing-rows script as part of the deployment gate. Make `decrypt_secret` callsites guard `InvalidToken` and surface a "please reconnect" error rather than crash.

### Pitfall 3: Redis circuit-breaker open during OAuth
**What goes wrong:** With Redis down, `set_generic` returns `False` and `get_generic` returns `is_error=True`. If we silently fall back to in-memory, multi-instance Cloud Run still loses the verifier on the callback.
**Avoid:** Treat Redis-down as a **flow-failure** for OAuth: return a clear "OAuth temporarily unavailable" message. Document in PLAN.md.

### Pitfall 4: TikTok username scope gap
**What goes wrong:** `PLATFORM_CONFIGS["tiktok"]["scopes"]` at `connector.py:76` lacks `user.info.profile`, so `/v2/user/info/` will return `open_id` but **not** `username` (TikTok docs explicitly call this out).
**Avoid:** Add `user.info.profile` to TikTok scopes, **or** accept storing only `open_id` for `platform_user_id` with `platform_username = None` and document.

### Pitfall 5: Instagram is two-step
**What goes wrong:** Treating Instagram like a one-call profile endpoint. IG Business accounts are accessed via the FB user's pages: `me/accounts` returns FB pages, each page has an `instagram_business_account` sub-object. A single `me` call returns the FB user, not the IG identity.
**Avoid:** For IG specifically, plan must call `me/accounts?fields=instagram_business_account{id,username}` and pick the connected page (or all pages — multi-account scenario). May warrant deferring IG profile capture to phase 108.

### Pitfall 6: Refresh lock dictionary leak
**What goes wrong:** `_refresh_locks` grows unbounded as new (user_id, platform) pairs appear. `IntegrationManager` already has the same property; not blocking, just note.
**Avoid:** Same as IntegrationManager — leave it. This is a tiny memory cost (one Lock per user-platform).

## Code Examples

### Encrypt on write (mirror `integration_manager.py:124-143`)
```python
# In SocialConnector.handle_callback, replacing lines 219-227
encrypted_access = encrypt_secret(tokens["access_token"])
encrypted_refresh = (
    encrypt_secret(tokens["refresh_token"])
    if tokens.get("refresh_token") else None
)
connection_data = {
    "user_id": user_id,
    "platform": platform,
    "access_token": encrypted_access,
    "refresh_token": encrypted_refresh,
    "platform_user_id": platform_user_id,    # AUTH-04
    "platform_username": platform_username,  # AUTH-04
    "token_expires_at": expires_at.isoformat(),
    "scopes": config["scopes"],
    "status": "active",
}
```

### PKCE write/read via Redis (mirror `routers/integrations.py:148-153, 228-242`)
```python
# Write (in get_authorization_url, replacing self._pkce_verifiers[state] = verifier)
await get_cache_service().set_generic(
    f"pikar:integration:pkce:{state}",
    {"verifier": verifier, "platform": platform},
    ttl=600,
)
# Read+delete (in handle_callback, replacing lines 188-191)
cache = get_cache_service()
cached = await cache.get_generic(f"pikar:integration:pkce:{state}")
if cached.is_miss or cached.is_error or not cached.value:
    return {"error": "PKCE verifier not found. Session may have expired."}
verifier = cached.value["verifier"]
await cache.delete(f"pikar:integration:pkce:{state}")
```

### Async refresh with per-key lock (mirror `integration_manager.py:166-205`)
```python
async def get_access_token(self, user_id: str, platform: str) -> str | None:
    account = await asyncio.to_thread(self._fetch_account_row, user_id, platform)
    if not account:
        return None
    if not _is_expiring_soon(account.get("token_expires_at")):
        return decrypt_secret(account["access_token"])
    lock = await self._get_refresh_lock(user_id, platform)
    async with lock:
        account = await asyncio.to_thread(self._fetch_account_row, user_id, platform)
        if not _is_expiring_soon(account.get("token_expires_at")):
            return decrypt_secret(account["access_token"])
        new_account = await self._refresh_token(user_id, platform, account)
        return decrypt_secret(new_account["access_token"]) if new_account else None
```

## Key Risks & Open Questions

1. **REQUIREMENTS wording vs actual implementation.** The requirement says `auth.uid()::text = user_id` but the typing-correct expression is `(SELECT auth.uid()) = user_id` because `connected_accounts.user_id` is `UUID`. **Recommendation:** treat the test as the authoritative spec ("user A cannot read user B's row") and implement the typing-correct expression. The planner should reconcile the wording in PLAN.md.

2. **Production data state for AUTH-02 migration.** The audit doesn't quantify how many plaintext rows exist in prod. **Recommendation:** the planner should specify the data-migration script as a separate task with an idempotent `is-already-Fernet` guard so it can be re-run safely. If prod is empty (greenfield), the script is a no-op.

3. **Redis-unavailable behavior for PKCE.** The project's circuit-breaker pattern degrades gracefully for caches but here the cache is the **only** source of truth. **Recommendation:** fail closed (user sees "OAuth temporarily unavailable") rather than silently fall back to in-memory. Confirm with user before locking in.

4. **TikTok scope addition.** Adding `user.info.profile` requires re-consenting all already-connected TikTok users on next refresh. **Recommendation:** scope addition belongs in phase 108 hygiene; for 101 capture only `open_id`.

5. **Threads + Pinterest endpoints.** Both providers are listed in success criterion #4 but **neither exists in `PLATFORM_CONFIGS`** (`connector.py:24-97`). **Recommendation:** scope phase 101 to the 6 currently-supported platforms (linkedin, twitter, facebook, instagram, tiktok, youtube) and let phase 108 hygiene add Threads + Pinterest with profile capture wired in from the start.

6. **`get_authorization_url` becoming async.** Three call sites (`configuration.py:660`, `agents/tools/social.py:144`, `agents/tools/integration_setup.py:113`). Two are already async; one ADK tool may need to remain sync via `asyncio.run`. **Recommendation:** include the caller updates in the same PR as the async conversion.

## Testing Strategy

| Success criterion | Verification approach |
|---|---|
| #1 RLS denies cross-user reads | Integration test in `tests/integration/test_connected_accounts_rls.py`: seed two users via service-role, then connect each with their own anon-key + JWT and assert `select` from user A's client returns 0 rows for B's user_id (and 1 for A's). Run against a local Supabase started via `supabase start`. |
| #2 Tokens stored as Fernet | Unit test in `tests/unit/social/test_connector_encryption.py`: mock the Supabase client, call `handle_callback` with a fake provider response, assert the value passed to `.upsert()` for `access_token` decrypts back to the plaintext via `decrypt_secret`. |
| #3 PKCE survives instance routing | Integration test: call `get_authorization_url` on connector instance A, blow away `_pkce_verifiers` from instance B (simulating different Cloud Run container), call `handle_callback` on B, assert it succeeds. Plus a unit test that `set_generic` was called with the expected key/TTL. |
| #4 Profile populated | Per-provider unit tests in `tests/unit/social/test_profile_capture.py`. Each test mocks the relevant `httpx.AsyncClient.get` for the provider profile endpoint, calls `handle_callback`, asserts upserted row contains `platform_user_id` and `platform_username` matching the canned response. |
| #5 Async refresh doesn't block | Async test that uses `asyncio.create_task` to run a heartbeat counter while a `get_access_token` triggers refresh against a mocked endpoint with `await asyncio.sleep(1)`; assert heartbeat counter advances ≥5 times during the 1s refresh, AND assert exactly one `httpx.post` is made for 5 parallel `get_access_token` calls (lock works). |

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | `pytest` (per `.planning/config.json:19`) + `pytest-asyncio` |
| Config file | `pyproject.toml` (project convention) |
| Quick run command | `uv run pytest tests/unit/social/ -x` |
| Full suite command | `uv run pytest tests/unit tests/integration -x` |
| Sampling rate | per task commit: quick; per wave: full social subset; phase gate: full unit + integration green |

### Wave 0 Gaps
- [ ] `tests/unit/social/__init__.py` — directory does not yet exist (no social tests anywhere in `tests/`)
- [ ] `tests/unit/social/test_connector_encryption.py` — covers AUTH-02
- [ ] `tests/unit/social/test_pkce_redis.py` — covers AUTH-03
- [ ] `tests/unit/social/test_profile_capture.py` — covers AUTH-04
- [ ] `tests/unit/social/test_async_refresh.py` — covers AUTH-05
- [ ] `tests/integration/test_connected_accounts_rls.py` — covers AUTH-01 (requires `supabase start` in CI; check existing pattern in repo for Supabase-backed integration tests)
- [ ] Shared fixture for `ADMIN_ENCRYPTION_KEY` in `tests/conftest.py` (probably already exists for integration_credentials tests — verify)

## Plan Decomposition Hint

Suggested 3-plan split for `/gsd:plan-phase 101`:

- **101-01 RLS verification + encryption + data migration** (AUTH-01 + AUTH-02)
  - New idempotent RLS migration; integration test for cross-user denial.
  - `connector.py` encrypt/decrypt around access/refresh tokens.
  - One-time `scripts/migrate_connected_accounts_encryption.py`.
  - Unit tests for encryption boundary.
  - Most security-urgent; ships first.

- **101-02 PKCE persistence + async refresh** (AUTH-03 + AUTH-05)
  - Replace `_pkce_verifiers` dict with Redis via `cache.set_generic`.
  - Convert `get_access_token` + `_refresh_token` to async + per-key lock.
  - Update three caller files.
  - Tests for Redis round-trip and async heartbeat.
  - These two ship together because they both touch `connector.py` method signatures.

- **101-03 Profile capture** (AUTH-04)
  - Add `_fetch_platform_profile` helper covering 6 supported providers.
  - Wire into `handle_callback`; populate `platform_user_id`/`platform_username`.
  - Per-provider unit tests with mocked profile endpoints.
  - Defer Threads + Pinterest to phase 108 hygiene (see Open Questions §5).
  - Defer TikTok username (scope gap) to phase 108 (see Open Questions §4).

This split respects the success criteria's natural boundaries, isolates the highest-risk data migration into its own plan, and keeps `connector.py` signature changes in a single PR (101-02) so the caller-update ripple is bounded.

## Sources

### Primary (HIGH confidence) — repo files
- `supabase/migrations/0010_connected_accounts.sql` — current table + permissive policy.
- `supabase/migrations/0028_fix_advisor_issues.sql:256-262` — service_role policy.
- `supabase/migrations/0034_user_configurations.sql:84-97` — `platform_user_id` column add.
- `supabase/migrations/20260322400000_fix_rls_wrapped_auth_uid.sql` — `(SELECT auth.uid())` convention.
- `supabase/migrations/20260415113000_harden_connected_accounts_rls.sql` — **the existing harden migration**.
- `supabase/migrations/20260404500000_integration_infrastructure.sql:20-68` — Fernet+RLS reference.
- `app/social/connector.py` — full file read; gaps identified line-by-line.
- `app/services/encryption.py` — Fernet helpers.
- `app/services/cache.py:30-42, 64-93, 645-725` — namespace + circuit-breaker + generic API.
- `app/routers/integrations.py:148-153, 228-242, 320-345` — Redis state + service-role storage pattern.
- `app/services/integration_manager.py:70-88, 124-143, 166-205, 207-279` — async lock + encryption + async refresh.
- `app/social/publisher.py:35, 162` — caller to AUTH-05; LinkedIn URN gap (phase 103 dep).
- `app/social/analytics.py:35-37` — async caller to AUTH-05.

### Primary (HIGH) — official provider docs
- LinkedIn `/v2/userinfo`: [Microsoft Learn — Sign In with LinkedIn using OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2)
- TikTok `/v2/user/info/`: [TikTok Developer docs — Get user info](https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info/)
- Threads `/v1.0/me`: [Meta Developers — Threads profiles](https://developers.facebook.com/docs/threads/threads-profiles)
- YouTube `/youtube/v3/channels?mine=true`: [Google Developers — channels.list](https://developers.google.com/youtube/v3/docs/channels/list)

### Secondary (MEDIUM)
- Twitter `/2/users/me`: orchestrator-supplied; cross-confirmed via [X developer community threads](https://devcommunity.x.com/t/bearer-token-no-longer-working-for-accessing-get-2-users-me/211784) and [OAuth 2.0 docs](https://developer.twitter.com/en/docs/authentication/oauth-2-0). Direct fetch of the api-reference page failed (host blocked).
- Facebook `/v18.0/me?fields=id,name`: standard Graph API pattern; in-repo usage at `publisher.py:177` confirms host.

### Tertiary (LOW — flag for validation)
- Pinterest `/v5/user_account`: [Pinterest API v5 docs index](https://developers.pinterest.com/docs/api/v5/) — schema details could not be deep-fetched. The endpoint exists; field names should be re-verified before implementing phase 108 Pinterest support.
- Instagram `me/accounts?fields=instagram_business_account{id,username}`: standard pattern; should be re-verified at implementation time given Meta API churn.

## Metadata

**Confidence breakdown:**
- Standard stack (encryption + Redis + httpx): HIGH — all primitives already in use elsewhere in the repo.
- RLS migration shape: HIGH — existing migration matches the requirement intent.
- Profile endpoints: HIGH for LinkedIn/TikTok/YouTube/Threads; MEDIUM for Twitter/Facebook; LOW for Pinterest/Instagram (which are out-of-scope or two-step).
- Async refresh pattern: HIGH — direct mirror of `IntegrationManager`.

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days; OAuth provider APIs are stable but Twitter/Meta change without notice)
