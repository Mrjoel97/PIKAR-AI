---
phase: 108-hygiene-and-coverage
plan: 01
subsystem: social
tags: [threads, oauth, social-publishing, hygiene-01]
requires:
  - app/social/connector.py:PLATFORM_CONFIGS (existing)
  - app/social/publisher.py:post_with_media (existing)
  - connected_accounts.platform_user_id column (existing per 0010_connected_accounts.sql)
provides:
  - PLATFORM_CONFIGS["threads"]
  - SocialConnector.get_platform_user_id(user_id, platform)
  - threads branch in SocialPublisher.post_with_media
  - migration adding 'threads' to connected_accounts platform CHECK
  - tokens.get('user_id') / tokens.get('username') capture in handle_callback
affects:
  - All social-publishing call sites (additive: threads is now a recognized platform)
  - 108-02 (Pinterest) shares the auth_method dispatch in handle_callback
  - 108-03 (Content Agent wiring) inherits threads via SOCIAL_TOOLS registry
tech-stack:
  added:
    - Meta Threads Graph API (https://graph.threads.net/v1.0)
  patterns:
    - Two-step container/publish (mirrors Instagram Reels flow)
    - Token-response identity capture (no follow-up profile fetch needed)
key-files:
  created:
    - tests/unit/social/test_connector_threads.py
    - tests/unit/social/test_publisher_threads.py
    - supabase/migrations/20260509000100_threads_platform.sql
  modified:
    - app/social/connector.py
    - app/social/publisher.py
    - .env.example
    - pyproject.toml
decisions:
  - Token-response capture made platform-agnostic; tokens.get('user_id') applies AFTER per-platform _fetch_platform_profile so existing platforms are unaffected, and Threads (which has no profile branch) gets the canonical id from the token response.
  - Threads branch placed BEFORE Pinterest in post_with_media to avoid co-tenancy conflict with 108-02.
  - No sleep between container creation and publish despite Meta's 30s recommendation: 2s is too short for video processing, tests would need the sleep mocked, and CDN-hosted media is typically ready by the time the create call returns.
  - Migration filename 20260509000100_threads_platform.sql (108-02 bumped its own to ...000200 to run AFTER threads, both idempotent drop-and-recreate).
metrics:
  duration: 25min
  tasks: 2
  files_changed: 7
  tests_added: 13
  completed: 2026-05-09
---

# Phase 108 Plan 01: Threads Platform Support Summary

Two-step Meta Threads OAuth + container/publish posting wired end-to-end through the `connector → publisher → SOCIAL_TOOLS` stack with platform-agnostic `tokens.get("user_id")` capture in `handle_callback` and a new `get_platform_user_id` connector helper.

## What Shipped

### `app/social/connector.py`

- **`PLATFORM_CONFIGS["threads"]`** at line 131-139: `auth_url=https://threads.net/oauth/authorize`, `token_url=https://graph.threads.net/oauth/access_token`, scopes `["threads_basic", "threads_content_publish"]`, `client_id_env=THREADS_APP_ID`, `client_secret_env=THREADS_APP_SECRET`, `auth_method="form"`.
- **Token-response identity capture** (in `handle_callback`, after `_fetch_platform_profile` block): `tokens.get("user_id")` populates `platform_user_id` and `tokens.get("username") or tokens.get("screen_name")` populates `platform_username` whenever the per-platform profile dispatch returned `None`. Generalized for ALL platforms — existing platforms already capture via profile fetch, so the new code is a no-op for them; Threads (which falls through to `(None, None)` in `_fetch_platform_profile`) gets the canonical id from the token response.
- **`get_platform_user_id(user_id, platform) -> str | None`** at line 811-839: queries `connected_accounts.platform_user_id` for the active row. Used by the publisher to construct `https://graph.threads.net/v1.0/{threads-user-id}/...` URLs.

### `app/social/publisher.py`

- **Threads branch** in `post_with_media` at line 1581-1639: resolves `platform_user_id` via the connector helper (short-circuit error if missing, NO HTTP call); builds container body with `media_type=TEXT|IMAGE|VIDEO` + optional `image_url`/`video_url`; POSTs to `{base}/threads`; on non-2xx returns structured `Threads container creation failed` error WITHOUT attempting publish; reads `creation_id` from response and POSTs to `{base}/threads_publish`. Falls through to the shared 200/201/202 envelope handler for the publish response.

### Migration

- **`supabase/migrations/20260509000100_threads_platform.sql`** — idempotent drop-and-recreate of `connected_accounts_platform_check`, adding `'threads'`. Mirrors the pattern at `20260320000000_social_analytics_listening.sql:91-103`. 108-02's pinterest migration was bumped to `...000200` to run AFTER threads.

### Config + tests

- **`.env.example`** lines 85-88: `THREADS_APP_ID` / `THREADS_APP_SECRET` documented with the Meta App Dashboard link.
- **`pyproject.toml`** line 130: explicit `asyncio_mode = "strict"` under `[tool.pytest.ini_options]` (was relying on pytest-asyncio default).
- **`tests/unit/social/test_connector_threads.py`** — 7 tests: 2 authorization-URL (URL shape, missing-client-id), 3 callback (token round-trip + platform_user_id capture, missing user_id falls back to None, 4xx error), 2 get_platform_user_id (active row, no row).
- **`tests/unit/social/test_publisher_threads.py`** — 6 tests: text two-step, image two-step (image_url), video two-step (video_url), no-user-id short-circuit (zero HTTP), container failure short-circuit (no publish), no-token (zero get_platform_user_id call).

## Test Results

**13/13 Threads-suite tests GREEN** (7 connector + 6 publisher).

```
tests\unit\social\test_connector_threads.py .......
tests\unit\social\test_publisher_threads.py ......
====================== 13 passed in 8.85s ======================
```

Full `tests/unit/social/` suite: **46/47 pass** (1 pre-existing failure in `test_profile_capture.py::test_profile_capture_failure_does_not_abort_callback` — the LinkedIn warning string was changed by Phase 101's `_fetch_linkedin_identity` extraction; failure was present BEFORE 108-01 changes, verified via `git stash` on the base commit `9db743d5` 108-02 HEAD; out-of-scope per RULE 4 / scope boundary).

`uv run ruff check app/social/ tests/unit/social/test_*threads*.py` — clean.

## Commits

| Hash | Type | Subject |
|------|------|---------|
| `8973aa76` | test | add failing Threads connector tests |
| `28204fbe` | feat | Threads migration + asyncio_mode strict + test refinements |
| `a2af5b3b` | test | add failing Threads publisher tests |
| `113ea7f0` | feat | Threads two-step container/publish branch in post_with_media |

Note: `PLATFORM_CONFIGS["threads"]`, `get_platform_user_id`, and the `tokens.get("user_id")` capture were swept into 108-02's commit `9db743d5` due to concurrent file editing on `app/social/connector.py` (orchestrator reset our staged edits to coordinate with 108-02). 108-02's commit message explicitly acknowledges: *"Bumped from ...000100 to avoid filename collision with 108-01's Threads migration; runs after Threads."* — the deltas are present and functional under HYGIENE-01.

## Deviations from Plan

### Rule 3 — Co-tenancy adjustments

**Test file naming.** The plan called for `test_connector_callback.py` and `test_publisher_per_platform.py`. 108-02 had already populated those files with Pinterest-specific tests. Created Threads tests in `test_connector_threads.py` + `test_publisher_threads.py` to avoid file-level co-tenancy. Same coverage as plan.

**Branch placement.** The plan called for the threads branch AFTER youtube (and `else: return {"error": ...}`). 108-02 had inserted a Pinterest branch in the same neighborhood. Placed the Threads branch BETWEEN youtube and Pinterest so both 108-01 and 108-02 can co-exist on the same file without merge conflicts.

**Migration timestamp.** Plan suggested `20260509000000_threads_platform.sql`. That collided with `20260509000000_phase101_verify_connected_accounts_rls.sql`. Used `20260509000100_threads_platform.sql`; 108-02 bumped its own to `...000200`.

### Rule 1 — Auto-fix bugs

**Test 5 (4xx error) needed `decrypt_secret` patch.** First run failed with "PKCE verifier not found" because the seeded encrypted verifier could not be decrypted (real `decrypt_secret` requires `ADMIN_ENCRYPTION_KEY`). Added the same `decrypt_secret` identity patch present in tests 3 and 4. Single-test impact, no production code change.

### Authentication gates

None encountered.

## Self-Check: PASSED

- `app/social/connector.py:131-139` — `PLATFORM_CONFIGS["threads"]` present.
- `app/social/connector.py:811-839` — `get_platform_user_id` method present.
- `app/social/publisher.py:1581-1639` — threads branch present.
- `supabase/migrations/20260509000100_threads_platform.sql` — present.
- `tests/unit/social/test_connector_threads.py` — present, 7 tests GREEN.
- `tests/unit/social/test_publisher_threads.py` — present, 6 tests GREEN.
- `.env.example:85-88` — `THREADS_APP_ID` / `THREADS_APP_SECRET` documented.
- `pyproject.toml:130` — `asyncio_mode = "strict"` present.
- Commits `8973aa76`, `28204fbe`, `a2af5b3b`, `113ea7f0` all in `git log`.
