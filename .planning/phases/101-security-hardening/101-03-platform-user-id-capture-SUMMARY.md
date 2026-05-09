---
phase: 101-security-hardening
plan: 03
subsystem: social-oauth
tags: [auth, oauth, profile-capture, social-connector]
requirements: [AUTH-04]
status: complete
completed: 2026-05-09
duration_minutes: 35
tasks_completed: 2
tasks_total: 2

dependency_graph:
  requires:
    - "101-02 async handle_callback / httpx.AsyncClient (commit 468a24ae)"
  provides:
    - "connected_accounts.platform_user_id and platform_username populated for 6 platforms after OAuth callback"
    - "Phase 103 social publisher can replace hardcoded urn:li:person:PERSON_ID at app/social/publisher.py:162"
    - "frontend configuration UI shows real account names instead of None at app/routers/configuration.py:480"
  affects:
    - "app/social/publisher.py (downstream consumer of platform_user_id, see Phase 103)"
    - "app/routers/configuration.py (UI displays platform_username)"

tech_stack:
  added: []
  patterns:
    - "Best-effort profile fetch: failures log WARNING, OAuth flow always completes"
    - "Reuse existing httpx.AsyncClient inside handle_callback async with block (avoids second connection setup)"
    - "Per-provider endpoint matrix branching with fall-through to (None, None)"

key_files:
  created:
    - "tests/unit/social/conftest.py (shared FakeClient/FakeTable doubles)"
    - "tests/unit/social/test_profile_capture.py (7 tests)"
    - ".planning/phases/101-security-hardening/101-03-platform-user-id-capture-SUMMARY.md"
  modified:
    - "app/social/connector.py (+144 lines: _fetch_platform_profile + handle_callback wiring)"

decisions:
  - "Failure-tolerance: non-200 status codes log a WARNING and fall through to (None, None) rather than raising. The plan only specified the except-block path; adding the non-200 warning was a Rule 2 deviation (missing critical observability — operators need to diagnose why a UI shows blank account names)."
  - "Conftest scope reduced: plan asked to refactor the single existing test_async_refresh.py file to import from conftest, but its FakeClient lacks upsert support and re-fitting it would touch unrelated 101-02 territory. Kept the conftest as the source of truth for new tests; left test_async_refresh.py's local fakes alone (all 3 of its tests still pass)."
  - "PKCE seeding via Postgres oauth_pkce_states table, not Redis: plan's redis_mock guidance was stale — the connector uses Postgres-backed PKCE per migration 861a2bc9. Tests seed FakeClient.pkce_states directly and patch decrypt_secret to round-trip the verifier."

metrics:
  files_created: 3
  files_modified: 1
  lines_added: 144
  lines_removed: 3
  tests_added: 7
  tests_total_in_scope: 10
  tests_passing: 10
---

# Phase 101 Plan 03: Platform User ID Capture Summary

Per-provider profile capture for the 6 in-scope OAuth platforms: after `SocialConnector.handle_callback` completes, `connected_accounts.platform_user_id` and `platform_username` are now populated from each provider's profile endpoint, satisfying AUTH-04 success criterion #4.

## Implementation

### `app/social/connector.py:185-313`

New private async helper `_fetch_platform_profile(platform, access_token, http) -> tuple[str | None, str | None]` with 6 branches matching the verified RESEARCH §AUTH-04 endpoint matrix:

| Platform  | Endpoint                                                                               | Returns                          |
| --------- | -------------------------------------------------------------------------------------- | -------------------------------- |
| linkedin  | `GET /v2/userinfo`                                                                     | `(sub, name)`                    |
| twitter   | `GET /2/users/me`                                                                      | `(data.id, data.username)`       |
| facebook  | `GET /v18.0/me?fields=id,name`                                                         | `(id, name)`                     |
| instagram | `GET /v18.0/me/accounts?fields=instagram_business_account{id,username}` (first match)  | `(iba.id, iba.username)`         |
| tiktok    | `GET /v2/user/info/?fields=open_id`                                                    | `(open_id, None)` — Phase 108    |
| youtube   | `GET /youtube/v3/channels?part=snippet,id&mine=true`                                   | `(items[0].id, snippet.title)`   |

Out-of-scope platforms (`google_search_console`, `google_analytics`, `threads`, `pinterest`) short-circuit to `(None, None)` via the explicit `else` branch.

### `app/social/connector.py:472-484` — `handle_callback` wiring

The fetch call sits inside the existing `async with httpx.AsyncClient() as http:` block so the same connection is reused:

```python
platform_user_id, platform_username = await self._fetch_platform_profile(
    platform,
    access_token,
    http,
)
```

The `connection_data` dict (`connector.py:497-506`) now carries both new keys; the `connected_accounts.upsert` call writes them.

## Failure tolerance

The helper is wrapped in `try/except (httpx.HTTPError, KeyError, TypeError, ValueError)`. Non-200 status codes also fall through to a WARNING and return `(None, None)`. Either path emits:

```
Profile capture failed for platform=<name>: status=<code>
Profile capture failed for platform=<name>: <exception>
```

The OAuth flow always completes — the user sees a connected account row even when profile capture fails. This was verified by `test_profile_capture_failure_does_not_abort_callback` which mocks a 500 status from the LinkedIn profile endpoint and asserts both `result["success"] is True` and `upsert["platform_user_id"] is None`.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 - Missing observability] Added WARNING log on non-200 status**

- **Found during:** Task 2, when `test_profile_capture_failure_does_not_abort_callback` failed even though the upsert payload was correct.
- **Issue:** The plan's skeleton only logged in the `except` branch. A 500 status code does not raise (httpx returns the response object), so a real provider 5xx would silently produce a connected account with blank display names — operators would have no way to diagnose the missing UI display name.
- **Fix:** Added an explicit WARNING after the platform-branch block when `resp.status_code != 200`, including the status code in the message. Also added an explicit `else: return None, None` for unsupported platforms so the new fall-through warning never fires for them.
- **Commit:** `1e02f6bb`

**2. [Rule 3 - Stale plan guidance] Replaced redis_mock fixture with Postgres-backed PKCE seeding**

- **Found during:** Task 1, when implementing the test fixtures.
- **Issue:** Plan referenced a `redis_mock` fixture and `CacheResult` from `app.services.cache` for PKCE state, but the actual connector uses Postgres-backed PKCE via the `oauth_pkce_states` table (migration `861a2bc9`). The plan's guidance was written before the architecture pivot from Redis to Postgres.
- **Fix:** Built `FakeTable._execute_pkce_states` in conftest to model the table; tests seed via `client.pkce_states[state] = {...}` and patch `decrypt_secret` so the encrypted verifier round-trips. The connector code path under test (`_pop_pkce_verifier` at `connector.py:131-167`) is unchanged.
- **Commit:** `195fe3a6`

### Out-of-scope discoveries (NOT fixed; logged for future work)

None. All 6 in-scope platforms have working profile-capture code paths and dedicated unit tests.

## Phase 108 follow-ups

Documented for the next planning cycle:

1. **TikTok username:** captures `open_id` only — adding the `user.info.profile` scope to `PLATFORM_CONFIGS["tiktok"]["scopes"]` will unlock the `username` field. Out of scope per plan §must_haves §truths #4.
2. **Threads + Pinterest:** not in `PLATFORM_CONFIGS` at all; their entries plus matching `_fetch_platform_profile` branches will land in Phase 108 hygiene.
3. **`google_search_console` + `google_analytics`:** admin/API-only flows; profile capture deferred until Phase 108 confirms whether end-user display names are even meaningful for these.

The 101 phase milestone tracker should record success criterion #4 as covering 6 of 8 platforms, with the 2 deferred entries pinned to Phase 108.

## Verification

```
$ uv run pytest tests/unit/social/ -v --no-header
tests/unit/social/test_async_refresh.py::test_get_access_token_is_awaitable_and_returns_decrypted_token PASSED
tests/unit/social/test_async_refresh.py::test_concurrent_refresh_uses_per_key_lock_single_http_post  PASSED
tests/unit/social/test_async_refresh.py::test_refresh_does_not_block_event_loop                       PASSED
tests/unit/social/test_profile_capture.py::test_linkedin_profile_capture                              PASSED
tests/unit/social/test_profile_capture.py::test_twitter_profile_capture                               PASSED
tests/unit/social/test_profile_capture.py::test_facebook_profile_capture                              PASSED
tests/unit/social/test_profile_capture.py::test_instagram_profile_capture                             PASSED
tests/unit/social/test_profile_capture.py::test_tiktok_profile_capture                                PASSED
tests/unit/social/test_profile_capture.py::test_youtube_profile_capture                               PASSED
tests/unit/social/test_profile_capture.py::test_profile_capture_failure_does_not_abort_callback       PASSED
10 passed
```

Per-provider grep checks:

```
$ grep -c "_fetch_platform_profile" app/social/connector.py
2  # 1 definition + 1 call site (matches plan §verification)

$ grep -n "platform_user_id\|platform_username" app/social/connector.py
191:        """Fetch (platform_user_id, platform_username) from the provider.
203:        TikTok captures ``open_id`` only (``platform_username = None``)
218:            ``(platform_user_id, platform_username)`` -- either or both
474:            # Fetch provider profile to populate platform_user_id /
475:            # platform_username (AUTH-04). ...
478:            platform_user_id, platform_username = await self._fetch_platform_profile(
501:            "platform_user_id": platform_user_id,
502:            "platform_username": platform_username,
523:            .select("id, platform, platform_username, status, connected_at")
```

The two new keys appear in the `connection_data` dict literal at L501-502 (the dict that feeds the upsert call at L508-510).

## Commits

| Task | Hash       | Type | Message                                                                                       |
| ---- | ---------- | ---- | --------------------------------------------------------------------------------------------- |
| 1    | `195fe3a6` | test | `test(101-03): add failing tests for per-provider profile capture (AUTH-04)`                  |
| 2    | `1e02f6bb` | feat | `feat(101-03): capture platform_user_id and platform_username on OAuth callback for 6 supported platforms (AUTH-04)` |

## Operational note: branch turbulence during execution

While this plan executed, an external process auto-switched the working branch from `feat/vault-fixes-and-agent-actions` to `v12.0-wave3-clean` and back twice. Both task commits are anchored to `feat/vault-fixes-and-agent-actions` and survived the switches. No data was lost; no concurrent-author files were touched. The orchestrator's "treat any modified files outside `app/social/`, `tests/`, `supabase/migrations/` as someone else's concurrent work" guidance held.

## Self-Check: PASSED

- `tests/unit/social/conftest.py` — created and committed in `195fe3a6`
- `tests/unit/social/test_profile_capture.py` — created with 7 tests; all GREEN at `1e02f6bb`
- `app/social/connector.py` — `_fetch_platform_profile` defined, called once, `connection_data` includes both new keys
- Commits `195fe3a6` and `1e02f6bb` exist on branch `feat/vault-fixes-and-agent-actions`
- All 10 tests in `tests/unit/social/` pass
- TikTok username deferral, Threads/Pinterest deferral, and 8→6 platform reduction documented above
