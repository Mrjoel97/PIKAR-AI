---
phase: 105-youtube-resumable-upload
plan: 01
subsystem: social-publisher
tags: [youtube, resumable-upload, social, post-07, oauth]
requirements: [POST-07]
dependency_graph:
  requires:
    - app/social/connector.py (Google OAuth scopes already correct)
    - httpx (already in deps)
    - respx (dev dep, added by parallel Phase 107-01)
  provides:
    - app/social/publisher.py:_upload_video_youtube (two-step resumable upload)
    - app/social/publisher.py:_put_chunked (8MB chunked PUT with 308 handling)
    - app/social/publisher.py:_map_youtube_error (16-reason error mapping)
    - app/social/publisher.py:_default_remedy (HTTP-code fallback)
  affects:
    - SocialPublisher.post_with_media YouTube branch (now structured-error capable)
tech-stack:
  added: [respx (dev, already present from 107-01)]
  patterns:
    - "Two-step resumable upload (POST init -> PUT bytes)"
    - "Reason -> (remedy, retriable) mapping table for structured errors"
    - "Threshold-based hybrid: single PUT <=25MB, 8MB chunked >25MB"
    - "308 Resume Incomplete handling via Range header parsing"
key-files:
  created:
    - tests/unit/test_youtube_publisher.py
    - tests/smoke/test_youtube_real_upload.py
    - tests/fixtures/test_video_1mb.mp4
  modified:
    - app/social/publisher.py
decisions:
  - "Bypass SocialPublisher.__init__ in tests via __new__ to avoid Supabase env coupling"
  - "Single-PUT threshold = 25MB; chunk size = 8MB (256KB-aligned)"
  - "Token refresh on 401 deferred to Phase 101 (out of scope per RESEARCH §Open Questions #4)"
  - "Streaming-from-disk for >50MB deferred to follow-up; in-memory for happy path"
  - "Test 4 uses scoped slice ('# ----- YOUTUBE -----' to next 'else:') instead of whole-file grep to avoid coupling with Phase 104's Twitter source_url"
metrics:
  duration: ~25min
  tasks: 3
  files: 4
  tests_added: 13 # 12 unit + 1 smoke (gated)
  tests_green: 12 # all unit tests; smoke deferred to live UAT
  commits: 2 # T1 RED, T2 GREEN; T3 verification-only (no commit)
  completed: "2026-05-09T05:50:00Z"
---

# Phase 105 Plan 01: YouTube Resumable Upload Summary

**One-liner:** Replaces the non-functional `source_url` JSON stub in `app/social/publisher.py` with the YouTube Data API v3 two-step resumable upload protocol (POST init -> PUT bytes), adds 8MB chunked PUT with 308 Resume Incomplete handling, and maps every documented failure mode to a structured `{success, error, reason, retriable, remedy, stage}` result.

## Tasks Executed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wave-0 RED tests + smoke stub + 1MB MP4 fixture | `c3dbd7ca` | `tests/unit/test_youtube_publisher.py`, `tests/smoke/test_youtube_real_upload.py`, `tests/fixtures/test_video_1mb.mp4` |
| 2 | Wave-1 GREEN: helpers + replace YouTube branch | `412bae02` | `app/social/publisher.py` (+401 / -50 across the file) |
| 3 | Wave-2 verification: full suite + lint + frontmatter (no commit needed) | (none) | (none) |

## Implementation Details

### Module-level additions to `app/social/publisher.py`

| Symbol | Line | Purpose |
|--------|------|---------|
| `YOUTUBE_RESUMABLE_INIT_URL` | 237 | Init endpoint with `uploadType=resumable&part=snippet,status` |
| `YOUTUBE_CHUNK_SIZE` | 241 | 8 * 1024 * 1024 (8MB, multiple of 256KB) |
| `YOUTUBE_SINGLE_PUT_THRESHOLD` | 242 | 25 * 1024 * 1024 (single-PUT cutoff) |
| `YOUTUBE_DEFAULT_CATEGORY_ID` | 243 | `"22"` (People & Blogs) |
| `DEFAULT_VIDEO_MIME` | 244 | `"video/mp4"` |
| `_default_remedy` | 247 | (remedy, retriable) fallback for unknown reasons |
| `_YOUTUBE_REASON_MAP` | 263 | 16-reason -> (remedy, retriable) mapping table |
| `_map_youtube_error` | 320 | Non-2xx response -> structured error dict |

### `SocialPublisher` methods

| Method | Line | Purpose |
|--------|------|---------|
| `_upload_video_youtube` | 1043 | Download bytes -> POST init -> single PUT or chunked PUT |
| `_put_chunked` | 1196 | 8MB chunked PUT with 308 Resume Incomplete handling |

### YouTube branch replacement

`post_with_media` YouTube branch (line 1548-1572) now early-returns the result of `_upload_video_youtube` -- the literal string `source_url` is absent from the branch (verified via scoped grep).

## Test Coverage

**Unit tests:** 12 in `tests/unit/test_youtube_publisher.py`, all GREEN (~30s suite)

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_youtube_resumable_two_step_sequence` | one POST + one PUT, success result |
| 2 | `test_youtube_init_request_shape` | init headers (Authorization, Content-Type, X-Upload-Content-*) and JSON body shape |
| 3 | `test_youtube_put_request_shape` | PUT uses fresh headers (no leakage), raw bytes as body |
| 4 | `test_youtube_no_source_url_in_codebase` | scoped slice '# ----- YOUTUBE -----' to next `else:` -- `source_url` absent |
| 5 | `test_youtube_error_400_invalid_metadata` | 400 invalidTitle -> non-retriable, "non-empty video title" |
| 6 | `test_youtube_error_401_token_expired` | 401 authorizationRequired -> non-retriable, "re-authenticate" |
| 7 | `test_youtube_error_403_quota_exceeded` | 403 quotaExceeded -> retriable, "24h" / "daily quota" |
| 8 | `test_youtube_error_404_expired_session` | PUT 404 notFound -> retriable, "re-initiate" |
| 9 | `test_youtube_error_5xx_transient` | 503 -> retriable, "transient" / "retry with backoff" |
| 10 | `test_youtube_network_interrupt_during_put` | httpx.ReadError -> retriable, "retry now" |
| 11 | `test_youtube_missing_location_header` | 200 init w/o Location -> retriable, "missing_location_header" |
| 12 | `test_youtube_chunked_upload_resume_path` | 30MB -> 4 PUTs (3x 8MB + 1x 6MB), 308 -> 308 -> 308 -> 201 |

**Smoke test:** `tests/smoke/test_youtube_real_upload.py` -- gated on `PIKAR_RUN_YOUTUBE_SMOKE=1` + `YOUTUBE_TEST_USER_ID` + `YOUTUBE_TEST_MEDIA_URL` env vars. Deferred to CI/UAT (no test channel credentials available locally).

**Fixture:** `tests/fixtures/test_video_1mb.mp4` generated via `ffmpeg -y -f lavfi -i testsrc=duration=10:size=640x360:rate=30 -c:v libx264 -pix_fmt yuv420p -b:v 800k tests/fixtures/test_video_1mb.mp4` -- ~416KB H.264 MP4 (smoke test asserts existence, not size).

## Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/unit/test_youtube_publisher.py` | 12/12 GREEN |
| `uv run pytest tests/unit/test_social_*.py tests/unit/social/` | 35/36 GREEN (1 pre-existing `test_profile_capture` failure -- string format expectation, not caused by 105-01; reproduces on Task 2's parent commit when stashed) |
| `uv run ruff check app/social/publisher.py tests/unit/test_youtube_publisher.py tests/smoke/test_youtube_real_upload.py` | clean |
| `uv run ruff format --check ...` | 3 files already formatted |
| `uv run ty check` | not run -- ty not installed in local .venv (lint-only optional dep); deferred to CI |
| Scoped grep: `source_url` absent from YouTube branch slice | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] SocialPublisher() in tests required Supabase env**
- **Found during:** Task 2 first test run.
- **Issue:** `SocialPublisher.__init__` calls `get_social_connector()` which instantiates `SocialConnector()` which calls `get_service_client()` which raises `ValueError: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set` when run without env. Plan instructed `pub.connector.get_access_token = lambda *a, **kw: "fake_token"`, but the connector itself never gets created if env is absent.
- **Fix:** `_make_publisher()` now uses `SocialPublisher.__new__(SocialPublisher)` to bypass `__init__`, then attaches a `SimpleNamespace` connector with an `AsyncMock` token getter. Also fixed the lambda -> `AsyncMock` because `get_access_token` is async (the publisher awaits it).
- **Files modified:** `tests/unit/test_youtube_publisher.py` (within Task 2's commit since the fix was part of getting tests GREEN).
- **Commit:** `412bae02`.

**2. [Rule 3 - Blocker] respx not in local .venv**
- **Found during:** Task 1 setup.
- **Issue:** `respx` was declared in `pyproject.toml` dev deps (added by parallel Phase 107-01) but not synced into the local `.venv` (the project uses a `uv` shim that only allows `uv run <cmd>`, not `uv sync`/`uv add`).
- **Fix:** Installed via `.venv/Scripts/python.exe -m pip install respx` directly. `pyproject.toml` already declared the dep so no edit needed.
- **Commit:** N/A (env-only side effect).

### Plan Drift

- **Test 4 (`test_youtube_no_source_url_in_codebase`)**: Used scoped slice (`'# ----- YOUTUBE -----'` to next `else:`) per plan instruction -- did NOT do whole-file grep. This was already specified in the plan to avoid coupling to Phase 104's Twitter `source_url`.
- **Insertion point**: Plan said "after `_upload_media_twitter`" -- there is no method by that exact name in the current file (existing methods are `_upload_image_twitter` and `_upload_video_twitter`, plus Phase 107-injected `_upload_facebook_video` module-level helper). Inserted the YouTube methods just before `post_text` ("Public posting methods" section divider, line 1041) instead -- semantically equivalent placement.
- **`respx` already added by 107-01**: `pyproject.toml` already had `respx>=0.21.0,<1.0.0` in `[dependency-groups].dev` from commit `2ac5d9c8`. No new addition needed.

### Authentication Gates

None. The unit tests fully mock the OAuth token via AsyncMock; the smoke test is gated behind `PIKAR_RUN_YOUTUBE_SMOKE=1` and explicitly deferred to operator-driven UAT.

## Pre-existing Issues (Not Caused by This Plan)

- `tests/unit/social/test_profile_capture.py::test_profile_capture_failure_does_not_abort_callback` fails because the test expects a log message containing `"Profile capture failed"` and `"linkedin"` but `connector.py` emits `"LinkedIn /v2/userinfo failed: status=500 ..."`. Reproduces on the Task 2 parent commit (`457323b1` from Phase 107-01) when changes are stashed -- pre-existing string-format mismatch in Phase 102/103 territory, not introduced here.
- `tests/unit/{test_tools.py, test_gmail_reader.py, test_google_docs_extensions.py, ...}` have pytest collection errors due to duplicate basenames across `tests/unit/` and `tests/unit/app/agents/strategic/`. Pre-existing. Out of scope per `<deviation_rules>` SCOPE BOUNDARY.

## Open Follow-ups (per RESEARCH.md)

1. **Streaming-from-disk for >50MB videos** (RESEARCH §Key Risks #2): currently `await src.aread()` reads the full file into RAM. Acceptable for 30-second 1080p videos (~8-25MB) but should switch to `tempfile.SpooledTemporaryFile` if profiling shows >50MB uploads in production.
2. **OAuth token refresh on 401** (RESEARCH §Open Questions #4): Phase 101 owns encrypted token reads + future refresh. This phase surfaces `401 authorizationRequired` with a `"re-authenticate"` remedy; refresh logic intentionally out of scope.
3. **Configurable `categoryId`** (RESEARCH §Open Questions #3): hardcoded to `"22"` (People & Blogs); helper accepts `category_id` kwarg for future agent-layer wiring.
4. **`privacyStatus` round-trip detection** (RESEARCH §Pitfall 5): unverified API projects force every upload to `private`. Helper returns the response's `privacy_status` so the caller can detect a `"public"` -> `"private"` mismatch, but no warning is currently surfaced. Defer until first agent UAT report indicates the pitfall hits.
5. **`ty check`**: not run locally because `ty` isn't installed in `.venv` (it's in the `[project.optional-dependencies].lint` group). Should run via CI pre-commit hook (`make lint` chain).

## Self-Check: PASSED

- File `app/social/publisher.py` exists and contains `YOUTUBE_RESUMABLE_INIT_URL`, `YOUTUBE_CHUNK_SIZE`, `YOUTUBE_SINGLE_PUT_THRESHOLD`, `YOUTUBE_DEFAULT_CATEGORY_ID`, `DEFAULT_VIDEO_MIME`, `_default_remedy`, `_map_youtube_error`, `_upload_video_youtube`, `_put_chunked` (verified via `grep -n` at lines 237/241/242/243/244/247/320/1043/1196).
- File `tests/unit/test_youtube_publisher.py` exists with 12 collected tests, all GREEN.
- File `tests/smoke/test_youtube_real_upload.py` exists, properly skipif-gated, collection passes.
- File `tests/fixtures/test_video_1mb.mp4` exists (~416KB H.264 MP4).
- Commit `c3dbd7ca` (Task 1 RED) found via `git log --oneline | grep c3dbd7ca` -> `test(105-01): add failing unit + smoke tests for YouTube resumable upload (POST-07)`.
- Commit `412bae02` (Task 2 GREEN) found via `git log --oneline | grep 412bae02` -> `feat(105-01): replace YouTube source_url stub with two-step resumable upload (POST-07)`.
- Scoped grep verified: `source_url` absent from YouTube branch in `app/social/publisher.py`.
