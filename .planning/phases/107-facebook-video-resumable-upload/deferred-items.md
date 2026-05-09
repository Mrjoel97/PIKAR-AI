# Phase 107 — Deferred Items

Out-of-scope discoveries logged during plan execution. NOT fixed in 107-02
per SCOPE BOUNDARY (issues unrelated to the current task's changes).

## From 107-01 (Facebook Three-Phase Resumable Upload)

### 1. Pre-existing failure observed during regression sweep

- **File:** `tests/unit/social/test_profile_capture.py::test_profile_capture_failure_does_not_abort_callback`
- Re-confirmed pre-existing on the pre-Task-2 tree via `git stash` isolation. Same root cause documented under 107-02 below. NOT touched.

## From 107-02 (Facebook Page Token Capture)

### 1. Pre-existing failure: `test_profile_capture_failure_does_not_abort_callback`

- **File:** `tests/unit/social/test_profile_capture.py:328`
- **Status:** Failing on `main` BEFORE 107-02 began (verified via `git stash` + isolated run on the pre-change tree).
- **Symptom:** Test asserts the LinkedIn-specific warning log uses the legacy `"Profile capture failed for platform=linkedin"` string, but the LinkedIn helper at `app/social/connector.py:230` already emits a different shape: `"LinkedIn /v2/userinfo failed: status=500 body=..."`.
- **Root cause:** Test expectations were not updated when the LinkedIn dispatch arm was refactored to use `_fetch_linkedin_identity` (AUTH-04 / Phase 101-03).
- **Owner:** Phase 101 / 108 hygiene — fix the assertion to match the new log shape, or add a back-compat wrapper log line in `_fetch_linkedin_identity`.
- **Why deferred:** Touches LinkedIn code path; outside 107-02's Facebook-only scope fence.

## Deviations explicitly applied (Rule 3 — blocking issues)

### A. `respx` is NOT a project dependency

- **Found in:** Plan 107-02 Task 2 specified `respx.mock` for HTTP mocking.
- **Fix:** Reused the existing `_MockAsyncClient` FIFO pattern from `tests/unit/social/test_profile_capture.py` instead. Tests still cover all four cases (single Page, multi-Page, zero Pages, HTTP 400).
- **Rule:** Rule 3 (blocking issue — pip install would have been an architectural change).

### B. `fake_user_id` fixture does not exist

- **Found in:** Plan 107-02 Task 2 imports `fake_user_id` from a conftest.
- **Fix:** Used the project's existing convention `state = "user-1:abc"` (matches `test_profile_capture.py`).
- **Rule:** Rule 3 (blocking issue — fixture didn't exist; matched local idiom).

### C. `_MockResponse` lacked `raise_for_status`

- **Found in:** `tests/unit/social/test_profile_capture.py` `_MockResponse` had no `raise_for_status` method, so the new Facebook branch in `handle_callback` (which calls `resp.raise_for_status()` inside `_fetch_facebook_pages`) crashed with `AttributeError` when the existing `test_facebook_profile_capture` ran against the new code path.
- **Fix:** Added `raise_for_status` to the existing `_MockResponse`. This is correctness/parity with httpx (Rule 1 — bug in the test double).
- **Rule:** Rule 1 (bug — fix the test double to match the real httpx response interface).

### D. `test_facebook_profile_capture` was asserting the OBSOLETE behavior

- **Found in:** `tests/unit/social/test_profile_capture.py::test_facebook_profile_capture` asserted `platform_user_id == "fb-111"` (User ID from `/me`), which is the pre-107-02 contract.
- **Fix:** Updated the test to enqueue the additional `/me/accounts` GET response and assert the NEW contract: `platform_user_id == page_id`, `platform_username == page_name`, `access_token == enc:page_token`, `metadata.selected_page_id == page_id`.
- **Rule:** Rule 3 (blocking issue — existing test asserted the contract that 107-02 explicitly replaces per locked decision D-5).
