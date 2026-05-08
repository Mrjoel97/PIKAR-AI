---
phase: 104-twitter-media-upload-fix
plan: 02
subsystem: social-media-publishing
tags: [twitter, x, video, chunked-upload, media-upload, oauth, post]
requirements: [POST-05]
dependency-graph:
  requires: [104-01]
  provides:
    - "_upload_video_twitter (full chunked flow: INIT/APPEND/FINALIZE/STATUS poll)"
    - "Twitter video posting end-to-end (media_type='video' branch in post_with_media)"
  affects:
    - "Phase 104 final state: image + video both ship; v1.1 fully purged"
tech-stack:
  added: []
  patterns:
    - "X v2 chunked media upload state machine (pending/in_progress/succeeded/failed)"
    - "API-driven backoff via processing_info.check_after_secs (fallback 2s, cap 600s)"
    - "Module-scope asyncio import for stable test patch targets"
key-files:
  created:
    - ".planning/phases/104-twitter-media-upload-fix/deferred-items.md"
  modified:
    - "app/social/publisher.py (lines 13, 101-240, ~597-605)"
    - "tests/unit/test_twitter_publisher.py (+5 video tests, -1 obsolete stub class)"
    - "tests/smoke/test_twitter_live.py (+1 test_video_post)"
decisions:
  - "Sleep ordering: sleep BEFORE each STATUS GET (honors API's check_after_secs hint). 3 polls = 3 sleeps in happy path."
  - "APPEND endpoint shape: defaulted to command=APPEND against /2/media/upload (per RESEARCH.md). Smoke test pivot path retained as future contingency."
  - "Memory >100MB: logged warning, proceeded in-memory. Tempfile fallback deferred (CONTEXT open question #2)."
  - "Removed obsolete TestVideoStubRaises empty class entirely (replaced by TestVideoChunkedUpload)."
metrics:
  duration: "~30 minutes"
  completed: "2026-05-08"
  task_count: 2
  file_count: 3
  test_delta: "+5 unit tests, -1 obsolete stub test, +1 smoke test"
  commits: 2
---

# Phase 104 Plan 02: Twitter Video Chunked Upload Summary

Replaces the `_upload_video_twitter` stub from Plan 104-01 with the full X v2 chunked upload state machine: GET media bytes → INIT → APPEND chunks → FINALIZE → STATUS poll until succeeded. Honors `processing_info.check_after_secs`, caps total wait at 600s, surfaces structured errors on `failed` state and timeout, and logs a warning for videos >100MB while still proceeding in-memory.

## Outcome

- **POST-05 satisfied:** `media_type=='video'` branch in `post_with_media` no longer returns "not yet available". Mock-based tests cover the full state machine without network calls.
- **Phase 104 final state:** `_upload_image_twitter` (104-01) + `_upload_video_twitter` (104-02) both shipped, `media.write` scope live in `connector.py:51`, v1.1 `upload.twitter.com` fully purged, fictional `source_url` confirmed absent in Twitter branch (still asserted by `test_no_fictional_source_url_in_twitter_branch`).
- **9/9 unit tests pass** in `tests/unit/test_twitter_publisher.py`. Smoke suite gated by `RUN_LIVE=1` (2 skipped without env vars).

## Implementation

### A. Module-scope asyncio import

`app/social/publisher.py:13`:
```python
import asyncio
```
Required so unit tests can patch `app.social.publisher.asyncio.sleep` and `app.social.publisher.asyncio.get_event_loop` from a stable fully-qualified path.

### B. `_upload_video_twitter` body — `app/social/publisher.py` lines 101–240

Five-step flow:

1. **GET bytes** (lines 122–129): `await http.get(media_url)`, derive `mime` from `content-type` header (split on `;`, fallback `video/mp4`).
2. **>100MB warning** (lines 131–138): contains substring `>100MB`. Upload still proceeds (no tempfile fallback).
3. **INIT** (lines 141–161): JSON POST to `https://api.x.com/2/media/upload/initialize` with `{media_type, total_bytes, media_category: "tweet_video"}` and `Content-Type: application/json`. Accepts 200/201/202. Extracts `media_id` from `data.id` with `media_id_string` fallback.
4. **APPEND loop** (lines 164–185): `for i in range(0, total_bytes, 4*1024*1024)`, `seg_idx = i // chunk_size`. POST to `https://api.x.com/2/media/upload` with `data={command: "APPEND", media_id, segment_index}` and `files={"media": ("chunk", chunk, "application/octet-stream")}`. Accepts 200/204.
5. **FINALIZE** (lines 188–198): POST to `https://api.x.com/2/media/upload/{media_id}/finalize`, no body. Accepts 200/201.
6. **STATUS poll** (lines 200–238): if FINALIZE returns no `processing_info` (or already `succeeded`), return `media_id`. Otherwise compute `deadline = loop.time() + 600` once, then loop while state ∈ {pending, in_progress}: check deadline first (timeout → log `"timed out"` and return None), `sleep(check_after_secs or 2)`, GET `?command=STATUS&media_id=`, update `proc`. After loop: if `state == "failed"`, log `code=...message=...` warning and return None. Else return `media_id`.

### C. Dispatch cleanup (`post_with_media` twitter branch)

Removed the `try/except NotImplementedError` wrapper around `_upload_video_twitter` at the former lines ~602–611 — now a straight `await`. Falls through to the same shared "Twitter media upload failed... please reconnect" error string when `_upload_video_twitter` returns None, exactly per CONTEXT open question #3.

### D. Tests

**`tests/unit/test_twitter_publisher.py` — `TestVideoChunkedUpload` (5 new tests, all GREEN):**

1. **`test_video_chunked_upload_succeeds`** — 10MB video → 3 APPENDs → FINALIZE pending → STATUS poll [pending → in_progress → succeeded] → tweet POST. Asserts: 6 POST calls in exact order with correct URLs/bodies; 4 GET calls (1 fetch + 3 STATUS); 3 `asyncio.sleep` awaits.
2. **`test_video_chunked_upload_segment_index_sequence`** — 16,777,217 bytes (4·4MB + 1) → 5 APPENDs with `segment_index` exactly `[0,1,2,3,4]`. Verifies the off-by-one boundary (Pitfall 5 from RESEARCH.md).
3. **`test_video_chunked_upload_failed_state`** — STATUS returns `{"state": "failed", "error": {"code": "FailedToParseVideo", "message": "ProcessFailed"}}` → `result["error"]` contains "Twitter media upload failed", tweet POST not issued, WARNING log contains both `FailedToParseVideo` and `ProcessFailed`.
4. **`test_video_chunked_upload_timeout`** — Patched `loop.time()` returns `[0.0, 601.0, 602.0, ...]` → first poll iteration succeeds, second iteration trips deadline → WARNING log contains `"timed out"`, tweet POST not issued.
5. **`test_video_large_logs_memory_warning_but_proceeds`** — 101MB → 26 APPENDs (indices 0..25), WARNING log contains `">100MB"`, FINALIZE returns no `processing_info` so STATUS poll is skipped, tweet POST issued successfully.

**`tests/smoke/test_twitter_live.py`** — Added `test_video_post` gated by `RUN_LIVE=1` and skipped further if `TWITTER_TEST_VIDEO_URL` is unset.

**Removed:** `TestVideoStubRaises` empty class (had served its 104-01 stub-guard purpose).

## Sleep Ordering Rationale

Chose **sleep-before-each-STATUS-GET** because the X API explicitly returns `processing_info.check_after_secs` telling the client when to come back. Polling immediately would either:
- Get a stale `pending` repeatedly (waste of API quota), or
- Race the upstream encoder before it's done.

Result: for the [pending → in_progress → succeeded] state machine, exactly 3 sleeps and 3 STATUS GETs. The first STATUS GET happens AFTER the FINALIZE response's `check_after_secs` hint has been honored.

## Open Question Outcomes

- **#1 (APPEND endpoint shape):** Defaulted to `command=APPEND` against `/2/media/upload` per RESEARCH.md. Pivot to `/2/media/upload/append` left as a documented contingency in the implementation comments — to be re-evaluated only if live smoke testing returns 4xx with "unknown command" or "endpoint not found".
- **#2 (Memory >100MB):** Confirmed deferred. Warning logged, in-memory upload only. Future perf phase can add a tempfile path keyed off the same `>100MB` threshold.
- **#3 (OAuth2+media.write reliability):** No change — reuses 104-01's reconnect copy from `post_with_media` when `_upload_video_twitter` returns None.

## Test Count Delta

| Suite                                    | Before | After | Delta |
|------------------------------------------|--------|-------|-------|
| `tests/unit/test_twitter_publisher.py`   | 4      | 9     | +5    |
| `tests/smoke/test_twitter_live.py`       | 1      | 2     | +1    |
| Obsolete `TestVideoStubRaises` test      | 1      | 0     | -1    |

Net: **+5 unit, -1 obsolete, +1 smoke = +5 unit / +1 smoke after removal**.

## Deviations from Plan

### Out-of-Scope Discovery (Logged, NOT Fixed)

**`app/social/connector.py` corrupted with null bytes.** Discovered when running the regression sweep `pytest tests/unit/test_social_connector_security.py`: `SyntaxError: source code string cannot contain null bytes`. Inspection: 36,076 null bytes in 72,154 total. The prompt explicitly told this executor not to touch `connector.py` — the documented owner is concurrent Plan 107-02. Logged to `.planning/phases/104-twitter-media-upload-fix/deferred-items.md`. Plan 104-02's own files (`app/social/publisher.py`) verified clean (0 null bytes), and the Plan 104-02 unit tests (which import `SocialPublisher` directly without going through `app.social.__init__`) all pass 9/9.

### Auto-Fixed (Rule 3 - Blocking)

**Removed obsolete `try/except NotImplementedError`** in `post_with_media` twitter video branch. With the chunked upload now landed, `_upload_video_twitter` no longer raises `NotImplementedError`, so the catch block was dead code returning the now-impossible "not yet available" error. Replaced with a straight `await`; failure path still funnels through the shared `if not media_id: return {"error": "Twitter media upload failed..."}` block.

### None Otherwise

The plan executed exactly as written for all five tests + implementation, lint, and commit boundaries.

## Phase 104 Final State

- [x] **POST-04** (104-01): `_upload_image_twitter` simple-shot v2 upload (≤5MB), reconnect prompt on 403.
- [x] **POST-05** (104-02): `_upload_video_twitter` full chunked flow with STATUS poll.
- [x] **media.write scope** in `app/social/connector.py:51` (PLATFORM_CONFIGS["twitter"]).
- [x] **Migration filed** in `supabase/migrations/` (per 104-01).
- [x] **No `source_url` regression** in twitter branch (asserted by `test_no_fictional_source_url_in_twitter_branch`).
- [x] **No `upload.twitter.com`** v1.1 endpoint references in twitter branch.
- [x] **`_upload_media_twitter`** (single-function legacy) is gone.

Phase 104 is ready for `/gsd:verify-work` and live UAT.

## Commits

| Wave | Hash       | Message                                                                              |
|------|------------|--------------------------------------------------------------------------------------|
| 0    | `a65e771e` | test(104-02): add failing tests for Twitter video chunked upload state machine (POST-05) |
| 1    | `94d7257d` | feat(104-02): implement Twitter video chunked upload with STATUS poll (POST-05)      |

## Self-Check: PASSED

- `app/social/publisher.py` line 13: `import asyncio` — FOUND
- `app/social/publisher.py` lines 101–240: `_upload_video_twitter` body — FOUND
- `app/social/publisher.py`: no `NotImplementedError` references — VERIFIED (0 matches)
- `tests/unit/test_twitter_publisher.py`: `TestVideoChunkedUpload` class — FOUND
- `tests/smoke/test_twitter_live.py`: `test_video_post` — FOUND
- `.planning/phases/104-twitter-media-upload-fix/deferred-items.md` — FOUND
- Commit `a65e771e` — FOUND
- Commit `94d7257d` — FOUND
- `pytest tests/unit/test_twitter_publisher.py` → 9/9 passed — VERIFIED
- `pytest tests/smoke/` → 2/2 skipped (RUN_LIVE not set) — VERIFIED
- `ruff check app/social/publisher.py tests/unit/test_twitter_publisher.py` → All checks passed — VERIFIED
