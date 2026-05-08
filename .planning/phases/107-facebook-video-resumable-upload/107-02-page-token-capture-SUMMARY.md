---
phase: 107-facebook-video-resumable-upload
plan: 02
subsystem: auth
tags: [oauth, facebook, meta-graph-api, page-tokens, social-media, fernet, encryption]

# Dependency graph
requires:
  - phase: 101-oauth-callback-and-row-hardening
    provides: "_fetch_platform_profile (User token + name capture); existing handle_callback OAuth flow scaffold"
provides:
  - "SocialConnector._fetch_facebook_pages helper (GET /v23.0/me/accounts) returning the user's manageable Pages with page-scoped access tokens"
  - "Facebook branch of handle_callback that auto-selects the first Page, encrypts the Page token + User token separately, and writes platform_user_id=page_id, platform_username=page_name, access_token=encrypted_page_token, metadata={user_token_enc, available_pages, selected_page_id, selected_page_name}"
  - "Structured error contract: facebook_no_pages_found (zero Pages, no row written) and facebook_pages_fetch_failed (HTTP / network failure on /me/accounts, no row written)"
  - "PLATFORM_CONFIGS facebook + instagram bumped to v23.0 (matching v18.0 retirement 2026-01-26)"
affects:
  - 107-01-three-phase-upload (will resolve platform_user_id + access_token from this row to call POST /{PAGE_ID}/videos with phase=start)
  - 108-social-hygiene (Page-selection UI, /me/accounts revoke-on-disconnect, Twitter/LinkedIn/etc. platform_user_id capture)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-platform branch in handle_callback for token-shape-divergent providers"
    - "metadata.{provider}_token_enc stash for tokens needed at provider operations beyond access_token"
    - "Auto-select-first + stash-the-list pattern for Page/Workspace selection (UI deferred)"

key-files:
  created:
    - tests/unit/social/test_connector_facebook_pages.py
  modified:
    - app/social/connector.py
    - tests/unit/social/test_profile_capture.py

key-decisions:
  - "Auto-select first Page on multi-Page accounts (D-5 from 107-CONTEXT) — Page-selection UI deferred to Phase 108"
  - "Stash full Pages list in metadata.available_pages for future endpoint that switches selected Page without re-OAuth"
  - "Stash User token in metadata.user_token_enc separately so a future endpoint can re-list /me/accounts without forcing re-OAuth"
  - "API version bump v18.0 → v23.0 across PLATFORM_CONFIGS facebook + instagram entries AND _fetch_platform_profile facebook + instagram URL strings (v18.0 retired by Meta 2026-01-26)"

patterns-established:
  - "Provider-specific post-token-exchange branch in handle_callback for tokens that require additional API calls before storage"
  - "Structured error returns ({error: <slug>, detail: <human-readable>}) with no row written when the callback cannot satisfy the storage contract"

requirements-completed: [POST-09]

# Metrics
duration: 35min
completed: 2026-05-09
---

# Phase 107 Plan 02: Facebook Page Token Capture Summary

**Facebook OAuth callback now exchanges the User token for per-Page access tokens via /v23.0/me/accounts, auto-selects the first Page, and stores the Page-scoped token (not the User token) in connected_accounts so the publisher's POST /{PAGE_ID}/videos call can authenticate.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-05-09 (immediately after stash-pop conflict resolution)
- **Completed:** 2026-05-09
- **Tasks:** 2 (both TDD: RED test → GREEN implementation)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- New `SocialConnector._fetch_facebook_pages` helper at `app/social/connector.py:435` calls `GET https://graph.facebook.com/v23.0/me/accounts?fields=id,name,access_token` and returns the `data` array (raises `httpx.HTTPStatusError` / `httpx.RequestError` on failure).
- Facebook branch of `handle_callback` rewritten at `app/social/connector.py:599-684`: on success, writes `platform_user_id=page.id`, `platform_username=page.name`, `access_token=encrypt(page.access_token)`, and `metadata={user_token_enc, available_pages, selected_page_id, selected_page_name}`.
- Non-Facebook callback paths unchanged at `app/social/connector.py:686-708` — Twitter/LinkedIn/Instagram/YouTube/TikTok still rely on `_fetch_platform_profile` for `platform_user_id` capture (Phase 101 / 103 / 104 territory).
- v18.0 → v23.0 bump applied to all 6 occurrences in `app/social/connector.py`:
  - `PLATFORM_CONFIGS["facebook"]["auth_url"]` (line 57)
  - `PLATFORM_CONFIGS["facebook"]["token_url"]` (line 58)
  - `PLATFORM_CONFIGS["instagram"]["auth_url"]` (line 69)
  - `PLATFORM_CONFIGS["instagram"]["token_url"]` (line 70)
  - `_fetch_platform_profile` facebook `/me` URL (line 304)
  - `_fetch_platform_profile` instagram `/me/accounts` URL (line 316)
- `grep -nE "v18\.0" app/social/connector.py` is empty (verified).
- 4 new pytest tests in `tests/unit/social/test_connector_facebook_pages.py` cover the four cases (single Page, multi-Page auto-select, zero Pages → error, /me/accounts HTTP 400 → error). All GREEN.
- Existing `test_facebook_profile_capture` updated to assert the new Page-id contract (was asserting User-id). GREEN.
- Full `tests/unit/social/` directory: **13 passed, 1 pre-existing failure** (LinkedIn warning shape mismatch, deferred — see below).

## Task Commits

Each task was committed atomically (TDD RED + GREEN + format-pass for Task 2):

1. **Task 1 (RED — Task 2's tests authored first per TDD): failing tests for Facebook Page-token capture** — `6b4e7944` (test)
2. **Task 1 (GREEN): connector implementation** — `c59d05a9` (feat)
3. **Task 2 (style pass): ruff format on new test file** — `f9d7d992` (style)

_(The plan's task numbering had Task 1 = connector and Task 2 = tests, but TDD execution wrote tests first to drive the connector. Same artifacts, just authored RED-first per `tdd="true"` flag.)_

## Files Created/Modified

- **`tests/unit/social/test_connector_facebook_pages.py`** (created) — 4 unit tests covering single-Page success, multi-Page auto-select, zero Pages, and /me/accounts HTTP 400 (no row written on errors).
- **`app/social/connector.py`** (modified) — Added `_fetch_facebook_pages`, rewired Facebook branch of `handle_callback`, bumped 6 v18.0 → v23.0 strings.
- **`tests/unit/social/test_profile_capture.py`** (modified) — Added `raise_for_status` to `_MockResponse` to support the new Facebook code path; updated `test_facebook_profile_capture` to assert the new Page-id contract.

## Decisions Made

- **Auto-select first Page** (per locked decision D-5 in `107-CONTEXT.md`). The full Pages list is stashed in `metadata.available_pages` so a future endpoint (Phase 108 HYGIENE-04) can switch the selected Page without forcing re-OAuth.
- **Stash User token in `metadata.user_token_enc`** — needed to re-list `/me/accounts` later without re-OAuth, so the Page-switching endpoint can call `_fetch_facebook_pages` again.
- **Bump v18.0 → v23.0 EVERYWHERE in connector.py** — including the `_fetch_platform_profile` URLs (which the plan didn't explicitly call out but the verification step `grep -nE "v18\.0" app/social/connector.py` is empty) requires.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `respx` is NOT a project dependency**
- **Found during:** Task 2 (test authoring)
- **Issue:** Plan 107-02 Task 2 specified `respx.mock` for HTTP mocking. `respx` is not in `pyproject.toml` and adding it would have been an architectural change (Rule 4 territory).
- **Fix:** Reused the existing `_MockAsyncClient` FIFO pattern from `tests/unit/social/test_profile_capture.py`. Tests still cover all four cases.
- **Files modified:** `tests/unit/social/test_connector_facebook_pages.py`
- **Verification:** All 4 new tests GREEN.
- **Committed in:** `6b4e7944` (RED commit)

**2. [Rule 3 — Blocking] `fake_user_id` fixture does not exist**
- **Found during:** Task 2 (test authoring)
- **Issue:** Plan 107-02 Task 2 imports a `fake_user_id` fixture from a conftest. No such fixture exists in `tests/unit/social/conftest.py` (which provides `FakeClient` + `make_connector` only). Plan noted this as a coordination concern: "If 107-01 Task 1 has NOT landed yet... inline the fixture."
- **Fix:** Used the project's existing convention `state = "user-1:abc"` (matches `test_profile_capture.py`). No new fixture needed; the user_id is parsed from the state string.
- **Files modified:** `tests/unit/social/test_connector_facebook_pages.py`
- **Verification:** Tests run cleanly.
- **Committed in:** `6b4e7944` (RED commit)

**3. [Rule 1 — Bug] `_MockResponse` lacked `raise_for_status` in `test_profile_capture.py`**
- **Found during:** Task 1 (running existing facebook test against new connector code)
- **Issue:** The existing `_MockResponse` test double had no `raise_for_status` method. The new Facebook branch calls `resp.raise_for_status()` inside `_fetch_facebook_pages`, so the existing `test_facebook_profile_capture` crashed with `AttributeError: '_MockResponse' object has no attribute 'raise_for_status'` when re-run against the new code path.
- **Fix:** Added `raise_for_status` to `_MockResponse` that builds a real `httpx.Response` and raises `httpx.HTTPStatusError` on 4xx/5xx (parity with httpx behavior).
- **Files modified:** `tests/unit/social/test_profile_capture.py`
- **Verification:** All 13 social tests pass (excluding 1 pre-existing failure).
- **Committed in:** `c59d05a9` (Task 1 GREEN commit)

**4. [Rule 3 — Blocking] `test_facebook_profile_capture` asserted obsolete behavior**
- **Found during:** Task 1 (running full social test suite)
- **Issue:** The existing test at `tests/unit/social/test_profile_capture.py::test_facebook_profile_capture` asserted `platform_user_id == "fb-111"` (the User ID from `/me`). That contract is explicitly replaced by D-5 in 107-CONTEXT: Facebook now stores the Page id as `platform_user_id`. Without updating the test, 107-02 would have shipped with a regression.
- **Fix:** Updated the test to enqueue an additional `/me/accounts` GET response and assert the new Page-id contract (`platform_user_id == "page-fb-1"`, `platform_username == "Test FB Page"`, `access_token == "enc:pt-1"`, `metadata.selected_page_id == "page-fb-1"`).
- **Files modified:** `tests/unit/social/test_profile_capture.py`
- **Verification:** Updated test GREEN.
- **Committed in:** `c59d05a9` (Task 1 GREEN commit)

**5. [Rule 1 — Bug] Encoding corruption from PowerShell `git show > file` redirect**
- **Found during:** Task 1 GREEN (after stash-pop conflict resolution)
- **Issue:** A concurrent commit on the branch (`a65e771e`, 104-02 RED tests, swept by autosaver) reverted my Task 1 connector edits because `git stash pop` wouldn't apply (publisher.py modified by 104-02). I extracted the connector content from the stash via `git show 'stash@{0}:app/social/connector.py' > C:\...\connector_stashed.py` (PowerShell), which writes UTF-16 LE. Copying that back over `app/social/connector.py` made Python fail to parse it (`source code string cannot contain null bytes`).
- **Fix:** Wrote a small Python script `C:\Users\expert\AppData\Local\Temp\fix_encoding.py` to read the file as UTF-16 LE (stripping BOM if present) and re-encode as UTF-8.
- **Files modified:** `app/social/connector.py` (re-encoded UTF-16 → UTF-8)
- **Verification:** `file app/social/connector.py` returns `ASCII text executable, with CRLF line terminators`. All tests pass.
- **Committed in:** `c59d05a9` (Task 1 GREEN commit)

**6. [Out of scope — deferred] Pre-existing failure: `test_profile_capture_failure_does_not_abort_callback`**
- **Found during:** Task 1 GREEN (full social-suite run)
- **Issue:** This test asserts the LinkedIn-specific warning log emits the legacy string `"Profile capture failed for platform=linkedin"`. The connector's `_fetch_linkedin_identity` (line 230) emits a different shape: `"LinkedIn /v2/userinfo failed: status=500 body=..."`. Verified pre-existing on `main` (via `git stash` + isolated run on the pre-change tree).
- **Fix:** **NOT FIXED** — out of 107-02 scope (LinkedIn helper, not Facebook). Logged to `.planning/phases/107-facebook-video-resumable-upload/deferred-items.md`.
- **Owner:** Phase 108 hygiene (or whoever revisits AUTH-04).

---

**Total deviations:** 5 auto-fixed (1 bug + 1 bug-with-impact + 3 blocking) + 1 deferred (out of scope).
**Impact on plan:** All auto-fixes were correctness-preserving. No scope creep — every change served the plan's success criteria. The encoding-corruption fix was fully accidental (PowerShell quirk).

## Issues Encountered

- **Concurrent activity sweep:** During Task 1 GREEN, the autosaver dropped commit `a65e771e` (104-02 RED tests) on top of my work, and `git stash` conflicts forced me to recover connector.py via `git show stash@{0}:...`. This is the same co-tenancy pattern noted in STATE.md from 102-02. Mitigation worked (encoding fix script); no data lost.
- **`ty` type-checker not installed:** `uv run ty check app/social/connector.py` errored with `'ty' is not recognized`. Skipped — `ruff check` is clean.

## Verification

End-to-end automated checks:

- [x] `uv run pytest tests/unit/social/test_connector_facebook_pages.py -x -v` — **4 passed**
- [x] `uv run pytest tests/unit/social/test_profile_capture.py::test_facebook_profile_capture -v` — **1 passed** (with new contract)
- [x] `uv run pytest tests/unit/social/ -v` — **13 passed, 1 pre-existing failure** (deferred)
- [x] `uv run ruff check app/social/connector.py` — **All checks passed!**
- [x] `uv run ruff format app/social/ tests/unit/social/test_*.py` — **Clean**
- [x] `! grep -nE "v18\.0" app/social/connector.py` — **Empty** (no v18.0 strings remain)
- [ ] `uv run ty check app/social/connector.py` — **Skipped** (`ty` not installed in this venv)

Manual smoke (deferred to phase-level UAT per plan):
- Run a real Facebook OAuth flow in `make local-backend`. Confirm the `connected_accounts` row has `platform_user_id` (Page ID), `platform_username` (Page name), `metadata.available_pages` (full list), and `metadata.user_token_enc`. The `access_token` column should decrypt to a Page token.

## Next Phase Readiness

- **107-01 (`_get_facebook_page_context`)** can now resolve the row written by this plan: `select platform_user_id, access_token from connected_accounts where platform='facebook'`. The Page-token contract is intact.
- **108 hygiene targets:**
  - Multi-Page selection UI (uses `metadata.available_pages` from this plan).
  - `disconnect` revoke-on-disconnect for Facebook (call `DELETE /{user_id}/permissions` with the User token from `metadata.user_token_enc`).
  - Fix the pre-existing LinkedIn warning-log assertion.
  - Twitter / LinkedIn / TikTok / YouTube `platform_user_id` capture (Phase 101/103/104 owned, partially shipped via `_fetch_platform_profile`).

## Self-Check

```
$ ls .planning/phases/107-facebook-video-resumable-upload/107-02-page-token-capture-SUMMARY.md
FOUND
$ ls app/social/connector.py
FOUND
$ ls tests/unit/social/test_connector_facebook_pages.py
FOUND
$ git log --oneline | grep -E "6b4e7944|c59d05a9|f9d7d992"
6b4e7944 test(107-02): failing tests for Facebook Page-token capture (POST-09)
c59d05a9 feat(107-02): capture Facebook Page tokens at OAuth callback via /me/accounts (POST-09)
f9d7d992 style(107-02): ruff format Facebook Page-token tests
```

## Self-Check: PASSED

---
*Phase: 107-facebook-video-resumable-upload*
*Plan: 02*
*Completed: 2026-05-09*
