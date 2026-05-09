---
phase: 108-hygiene-and-coverage
plan: 02
subsystem: social-publishing
tags: [pinterest, oauth, hygiene, social, publisher, basic-auth, rfc-6749]
requirements: [HYGIENE-02]
dependency_graph:
  requires:
    - "app.social.connector.SocialConnector OAuth scaffolding (Phase 100+)"
    - "app.social.publisher.SocialPublisher per-platform dispatch"
    - "app.agents.tools.social.publish_to_social agent tool"
  provides:
    - "Pinterest end-to-end: OAuth connect (HTTP Basic auth) + pin creation via /v5/pins"
    - "PLATFORM_CONFIGS auth_method discriminator (form|basic) — reusable for any future RFC-6749-strict provider"
    - "post_with_media `extra: dict | None` kwarg — generic per-platform escape hatch"
  affects:
    - "Future plans wanting platform-specific kwargs (e.g. carousel ordering, scheduled publishing) — pattern established"
    - "108-04 (revoke endpoint dispatcher) — auth_method discriminator already in place"
tech_stack:
  added:
    - "Pinterest API v5 (POST /v5/pins, GET /v5/user_account)"
  patterns:
    - "RFC-6749-strict Basic auth via httpx auth=(id, secret) tuple"
    - "Best-effort follow-up profile call (non-blocking on 5xx)"
    - "Per-platform kwarg passthrough via single `extra` dict"
key_files:
  created:
    - "supabase/migrations/20260509000200_pinterest_platform.sql"
    - "tests/unit/social/test_connector_callback.py"
    - "tests/unit/social/test_publisher_per_platform.py"
  modified:
    - ".env.example"
    - "app/social/connector.py"
    - "app/social/publisher.py"
    - "app/agents/tools/social.py"
decisions:
  - "auth_method discriminator at PLATFORM_CONFIGS dict level (not per-call): keeps the platform contract declarative; handle_callback and _refresh_token both look it up the same way."
  - "Migration timestamp bumped from plan-specified 20260509000100 to 20260509000200 because 108-01's Threads migration claimed 000100 first when both plans shipped concurrently in wave 1."
  - "Pinterest IN list in the migration includes BOTH 'threads' and 'pinterest' to keep the constraint canonical regardless of which migration replays last."
  - "follow-up /v5/user_account call lives inline in handle_callback (after _fetch_platform_profile short-circuits to None,None for unsupported platforms) rather than adding a new dispatch arm — keeps the change surgical."
metrics:
  duration_seconds: 677
  completed: 2026-05-09
---

# Phase 108 Plan 02: Pinterest Platform Support Summary

Adds Pinterest as the 9th supported social platform in the connector + publisher stack: separate OAuth client, RFC-6749-strict HTTP Basic auth at the token endpoint, follow-up `/v5/user_account` call to capture `platform_username`, and single-POST pin creation against `POST /v5/pins`. Introduces two general-purpose mechanisms — a `PLATFORM_CONFIGS["...auth_method"]` discriminator and an `extra: dict | None` kwarg through `publish_to_social` — that any future platform with non-standard auth or required platform-specific fields will reuse.

## Tasks Completed

| Task | Name                                                                  | Commit     |
| ---- | --------------------------------------------------------------------- | ---------- |
| 1    | Migration + PLATFORM_CONFIGS auth_method + Pinterest callback         | `9db743d5` |
| 2    | Pinterest publisher branch + extra kwarg threading + tool wiring      | `0f5f3cbc` |

Plus RED test commits: `86a4a982` (connector tests), `63ff4b2d` (publisher tests).

## Exact Line Locations

### `app/social/connector.py`

- **`PLATFORM_CONFIGS["pinterest"]`** — lines 118–126
  - `auth_url` (119), `token_url` (120), `scopes` (121), `client_id_env` (122), `client_secret_env` (123)
  - `auth_method: "basic"` (124) — the discriminator
  - `user_account_url: "https://api.pinterest.com/v5/user_account"` (125) — drives the follow-up profile call
- **`handle_callback` Basic-auth branch** — lines 572–593
  - reads `config.get("auth_method", "form")` (576)
  - `request_kwargs["auth"] = (client_id, client_secret)` for basic (585)
  - falls back to body-encoded `client_id`/`client_secret` for `form` platforms (588)
- **`handle_callback` follow-up profile call** — lines 615–648
  - guarded by `user_account_url and not (platform_user_id or platform_username)` (620)
  - failures log a WARNING but do NOT abort the OAuth flow (645–647)
  - reads `username` from the response and assigns to `platform_username` (635)
- **`_refresh_token` Basic-auth branch** — lines 968–977
  - same `auth_method` lookup; mirrors the callback contract for refresh-token grants

### `app/social/publisher.py`

- **`post_with_media` signature** — line 1298: `extra: dict[str, Any] | None = None`
- **Pinterest dispatch arm** — lines 1642–1671
  - missing `extra["board_id"]` → structured error, zero HTTP (1648–1654)
  - missing media → structured error, zero HTTP (1655–1656)
  - single JSON POST to `https://api.pinterest.com/v5/pins` (1657–1669)
  - falls through to shared 200/201/202 envelope handler (1670–1671)
- **`post_text` shim** — line 1288: `extra=None` forwarded for signature consistency

### `app/agents/tools/social.py`

- **`publish_to_social` signature** — line 42: `extra: dict[str, Any] | None = None`
- **Docstring contract** — lines 49–50, 55, 69–73: documents Pinterest's board_id requirement
- **Forwarding to publisher** — line 126: `extra=extra` passed to `post_with_media`

### `supabase/migrations/20260509000200_pinterest_platform.sql`

- Drops the existing `connected_accounts_platform_check` (IN-list) constraint and recreates it with both `'threads'` and `'pinterest'` (canonical end-state).

### `.env.example`

- New `PINTEREST_CLIENT_ID` and `PINTEREST_CLIENT_SECRET` entries with link to Pinterest's developer dashboard and a note explaining the Basic-auth requirement.

## Auth Method Discriminator: Module-level Decision

The `auth_method` field lives on each `PLATFORM_CONFIGS` entry (module-level dict), NOT as a per-call argument. Reasons:

1. **Platform contract is static.** Pinterest's token endpoint always wants Basic auth; LinkedIn's always wants form-encoded. The discriminator describes the platform's contract, not anything about the specific call.
2. **Both `handle_callback` and `_refresh_token` need to branch the same way.** Putting the field on the config means both code paths look it up identically — no risk of drift.
3. **Reusable for future platforms.** Any future RFC-6749-strict provider just needs `auth_method: "basic"` — no new code path, no new test fixtures.

Default is `"form"` (the RFC-6749 fallback most platforms accept, including LinkedIn, Twitter, Facebook, Instagram, TikTok, YouTube, Threads).

## Test Count

| Suite                                        | New Tests | Status |
| -------------------------------------------- | --------- | ------ |
| `test_connector_callback.py` (Pinterest)     | 5         | GREEN  |
| `test_publisher_per_platform.py` (Pinterest) | 6         | GREEN  |

(Note: plan called for 5 publisher tests; we added an extra test covering `extra=None` distinct from `extra={}` to lock both no-board-id paths.)

Total: **11 new tests, all GREEN**. Existing suites unaffected:
- `test_profile_capture.py` — 6/7 pass (1 pre-existing failure in `test_profile_capture_failure_does_not_abort_callback`, unrelated to this plan; verified via `git stash`).
- `test_async_refresh.py`, `test_connector_facebook_pages.py`, `test_publisher_facebook.py`, `test_tiktok_publish_polling.py` — all GREEN.
- `tests/unit/test_phase89_media_tagging.py` — 3/3 GREEN (regression check).

## Migration File Reasoning

- **Filename bumped from `...000100` to `...000200`** because Plan 108-01's Threads migration shipped concurrently and claimed `20260509000100`. Using the same timestamp would have created two files differing only by name — Postgres sorts by filename, so behavior would have been ambiguous.
- **IN list includes BOTH `'threads'` and `'pinterest'`** — Postgres's CHECK constraint accepts duplicate literals in the IN list (108-01's `'threads'` is also redundantly listed in 108-02's migration). This makes the rollout order-insensitive: whichever migration lands last leaves the canonical end state.

## Deviations from Plan

1. **Migration filename** (already explained above): bumped from `20260509000100_pinterest_platform.sql` to `20260509000200_pinterest_platform.sql`. SUMMARY frontmatter records the new filename.
2. **Extra publisher test added**: 6 publisher tests instead of the planned 5. Added `test_pinterest_post_extra_none_returns_error_without_http` to assert the `extra=None` path is identical to `extra={}` — both must short-circuit with the missing-board-id error before issuing HTTP. Locks both no-board-id call shapes.
3. **`auth_method` field also added to Threads config** (line 137: `"auth_method": "form"`). Plan 108-01 added Threads with no `auth_method` field at all, but my Task 1 work changed `handle_callback` to look it up via `.get("auth_method", "form")`. To keep Threads' contract explicit (rather than relying on the default), I left Threads' config as it was added by 108-01 — the default `"form"` does the right thing, no functional change. This is a no-op for behavior but worth noting for future readers.
4. **One pre-existing test is RED** (`test_profile_capture_failure_does_not_abort_callback`): asserts a WARNING log message contains "Profile capture failed" + "linkedin", but the actual log says "LinkedIn /v2/userinfo failed". Verified pre-existing via `git stash` — NOT caused by 108-02. Out of scope per the deviation rules' SCOPE BOUNDARY (only auto-fix issues directly caused by current task's changes). Logged here for the next plan that touches `_fetch_linkedin_identity`.

## Authentication Gates

None encountered. All work was offline (test-driven), no live OAuth flow exercised during execution.

## Self-Check: PASSED

- File `supabase/migrations/20260509000200_pinterest_platform.sql`: FOUND
- File `tests/unit/social/test_connector_callback.py`: FOUND
- File `tests/unit/social/test_publisher_per_platform.py`: FOUND
- Modified files (`.env.example`, `app/social/connector.py`, `app/social/publisher.py`, `app/agents/tools/social.py`): FOUND with expected Pinterest content
- Commit `9db743d5` (Task 1 GREEN): FOUND in git log
- Commit `0f5f3cbc` (Task 2 GREEN): FOUND in git log
- Commit `86a4a982` (Task 1 RED): FOUND
- Commit `63ff4b2d` (Task 2 RED): FOUND
- 11 Pinterest tests: GREEN (5 connector + 6 publisher)
