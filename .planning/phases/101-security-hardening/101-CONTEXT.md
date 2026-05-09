# Phase 101 Context: Security Hardening for `connected_accounts`

**Milestone:** v13.0 Authentication & Connections Hardening
**Goal:** Stop the bleeding on `connected_accounts` before any user is told their tokens are safe. Replace permissive RLS, encrypt tokens at rest, persist PKCE in Redis (multi-instance safe), capture `platform_user_id` per provider, and convert token refresh to non-blocking async I/O.

## Inputs Read

- `.planning/phases/101-security-hardening/101-RESEARCH.md` — verified-against-docs research, file:line citations across all 5 requirements, per-provider endpoint matrix.
- `.planning/ROADMAP.md` (lines 446-461) — phase definition, 5 success criteria, dependency graph.
- `.planning/REQUIREMENTS.md` v13.0 — AUTH-01 through AUTH-05.
- `app/social/connector.py` — current implementation (PKCE Postgres-backed, encryption already correct, refresh sync).
- `app/services/{encryption,cache,integration_manager}.py` — reference patterns for Fernet, Redis with circuit breaker, async refresh with per-key Lock.
- `supabase/migrations/{20260415113000_harden_connected_accounts_rls.sql, 20260508123000_social_oauth_security.sql}` — existing RLS hardening + PKCE Postgres table.
- `tests/unit/test_social_connector_security.py` — 3 existing tests (PKCE Postgres + encryption smoke).

## State Reconciliation (Important)

The 2026-05-08 audit description in REQUIREMENTS.md slightly overstates the gap. **Already shipped:** AUTH-01 (RLS migration `20260415113000`), AUTH-02 (encryption code in connector.py is correct), AUTH-03 partial (PKCE persisted in Postgres table `oauth_pkce_states`). **Real remaining gaps:** (1) no integration test asserts cross-user RLS denial; (2) no backfill script for legacy plaintext token rows; (3) PKCE storage should move from Postgres to Redis per the project's standard pattern (`pikar:integration:` namespace); (4) profile capture for `platform_user_id`/`platform_username` not implemented; (5) `get_access_token`/`_refresh_token` still sync — block the event loop when called from async tools.

## Plan Decomposition (3 plans, 2 waves)

- **101-01** (Wave 1, autonomous) — RLS verification + encryption boundary tests + legacy-token backfill script. AUTH-01 + AUTH-02. 5 atomic tasks. Does NOT modify `connector.py` (already correct for AUTH-02).
- **101-02** (Wave 1, autonomous) — Redis-backed PKCE replaces Postgres `oauth_pkce_states`; `get_authorization_url`/`get_access_token`/`_refresh_token` become async with per-key `asyncio.Lock`. Updates 5 caller files. AUTH-03 + AUTH-05. 4 atomic tasks. Drops the in-memory PKCE fallback (fail-closed when Redis unhealthy per RESEARCH §Open Q3).
- **101-03** (Wave 2, autonomous, depends_on 101-02) — `_fetch_platform_profile` helper + wiring in `handle_callback` for 6 platforms (linkedin, twitter, facebook, instagram, tiktok-open_id-only, youtube). AUTH-04. 2 atomic tasks. Threads + Pinterest deferred to Phase 108 (per RESEARCH §Open Q5); TikTok username deferred to Phase 108 (scope gap, Open Q4).

Wave-2 dependency: 101-03 needs the async `handle_callback` shape from 101-02 to use the same `httpx.AsyncClient` for both token exchange and profile fetch. 101-01 is independent and can run in parallel with 101-02.

## Out of Scope (Explicit Deferrals)

- Threads + Pinterest profile capture (NOT in `PLATFORM_CONFIGS`) → Phase 108 hygiene.
- TikTok `platform_username` (requires `user.info.profile` scope, breaking change for existing users) → Phase 108 hygiene.
- Dropping the now-orphaned `oauth_pkce_states` Postgres table → Phase 108 hygiene.
- Reconciling REQUIREMENTS.md AUTH-01 wording (`auth.uid()::text = user_id`) with implemented expression (`(SELECT auth.uid()) = user_id`, typing-correct for UUID column) → cosmetic; integration test is authoritative.

## Risks Acknowledged

1. **Redis-down behavior is fail-closed** — `get_authorization_url` returns "OAuth temporarily unavailable" instead of falling back to in-memory. This is a deliberate degradation (in-memory doesn't survive multi-instance routing anyway).
2. **Legacy plaintext rows** — backfill script ships in 101-01; `_decrypt_token` already tolerates plaintext during the transition (see `connector.py:140-144`).
3. **TikTok username scope gap** — captures `open_id` only; documented in 101-03 SUMMARY as Phase 108 followup.

## Verification Strategy

| Criterion | Test |
|---|---|
| AUTH-01 RLS denies cross-user reads | `tests/integration/test_connected_accounts_rls.py` against local Supabase (skip if not running) |
| AUTH-02 Tokens stored Fernet-encrypted | `tests/unit/social/test_connector_encryption.py` (3 tests: encryption write, legacy plaintext fallback, gAAAAA-corrupted handling) |
| AUTH-02 Legacy backfill | `tests/unit/scripts/test_migrate_connected_accounts_encryption.py` (3 tests: dry-run, plaintext-only migrate, idempotent) |
| AUTH-03 PKCE survives instance routing | `tests/unit/social/test_pkce_redis.py` (5 tests: write, read+delete, miss, circuit-breaker error, fail-closed contract) |
| AUTH-04 Profile populated | `tests/unit/social/test_profile_capture.py` (6 per-provider + 1 failure-tolerance) |
| AUTH-05 Async refresh doesn't block | `tests/unit/social/test_async_refresh.py` (3 tests: awaitable, single HTTP under 5-way contention, heartbeat continues) |

Total new tests across phase: 21. Total existing tests retired (now-obsolete Postgres-PKCE): 2. Net +19.
