---
phase: 104-twitter-media-upload-fix
plan: 02
type: execute
wave: 2
depends_on: [104-01]
files_modified:
  - app/social/publisher.py
  - tests/unit/test_twitter_publisher.py
  - tests/smoke/test_twitter_live.py
autonomous: true
requirements: [POST-05]

must_haves:
  truths:
    - "Posting a video to Twitter issues exactly four kinds of HTTP calls in order: (1) GET media_url to fetch bytes, (2) POST /2/media/upload/initialize (JSON, total_bytes, media_category=tweet_video), (3) one or more POST /2/media/upload (multipart, command=APPEND, monotonically increasing segment_index from 0), (4) POST /2/media/upload/{id}/finalize (empty body), then optionally GET /2/media/upload?command=STATUS until processing_info.state is 'succeeded'"
    - "STATUS poll honors processing_info.check_after_secs from each response; falls back to 2 seconds; total wait capped at 600 seconds"
    - "Processing state 'failed' surfaces a structured error containing the upstream error code/message instead of a generic failure"
    - "Total wait timeout (>600s) returns an error containing the substring 'timed out' and does NOT attach the unfinished media_id to a tweet"
    - "Memory warning logged for videos >100MB; upload still proceeds (tempfile fallback is deferred — see CONTEXT open question 2)"
    - "_upload_video_twitter no longer raises NotImplementedError; the media_type=='video' dispatch in post_with_media now succeeds end-to-end"
  artifacts:
    - path: "app/social/publisher.py"
      provides: "_upload_video_twitter — full chunked upload with INIT/APPEND/FINALIZE/STATUS poll, honoring check_after_secs and 600s cap"
      contains: "/2/media/upload/initialize"
    - path: "tests/unit/test_twitter_publisher.py"
      provides: "TestVideoChunkedUpload — happy path (state machine), failed-state path, timeout path, segment_index sequence assertion, large-video memory warning"
      contains: "test_video_chunked_upload_succeeds"
    - path: "tests/smoke/test_twitter_live.py"
      provides: "test_video_post — gated RUN_LIVE=1 live test that posts a real 30s 1080p video and asserts the tweet plays"
      contains: "test_video_post"
  key_links:
    - from: "app/social/publisher.py:post_with_media (twitter branch, media_type=='video')"
      to: "app/social/publisher.py:_upload_video_twitter"
      via: "media_type-dispatch (already wired in Plan 104-01)"
      pattern: "_upload_video_twitter"
    - from: "app/social/publisher.py:_upload_video_twitter"
      to: "https://api.x.com/2/media/upload/initialize"
      via: "JSON POST with total_bytes, media_type, media_category=tweet_video"
      pattern: "/2/media/upload/initialize"
    - from: "app/social/publisher.py:_upload_video_twitter"
      to: "https://api.x.com/2/media/upload (command=APPEND)"
      via: "multipart POST per chunk; segment_index monotonically increasing from 0"
      pattern: "command.*APPEND"
    - from: "app/social/publisher.py:_upload_video_twitter"
      to: "https://api.x.com/2/media/upload/{media_id}/finalize"
      via: "empty-body POST after last APPEND"
      pattern: "/finalize"
    - from: "app/social/publisher.py:_upload_video_twitter"
      to: "https://api.x.com/2/media/upload?command=STATUS"
      via: "GET poll loop honoring check_after_secs from each processing_info response; cap 600s"
      pattern: "command.*STATUS"
---

<objective>
Replace the `_upload_video_twitter` stub (added by Plan 104-01) with the complete X v2 chunked upload flow: download bytes → INIT → APPEND chunks → FINALIZE → STATUS poll until `succeeded`. Honor `check_after_secs` from each STATUS response. Cap total wait at 600 seconds. Surface structured errors on `processing_info.state == "failed"` and on timeout. Log a memory warning for videos >100MB but still proceed (tempfile fallback deferred per CONTEXT). Wave 0 scaffolds the failing state-machine tests; Wave 1 turns them green. The smoke test stub from 104-01 grows a `test_video_post` case.

Purpose: Satisfy POST-05 (full chunked upload + STATUS poll). Closes the last hole in Phase 104 — once this lands, both image and video posting via Twitter work end-to-end, the `media_type=='video'` branch no longer returns "not yet available", and the v1.1 dependency is fully purged from the codebase.

Output: A 30-second 1080p video uploaded via the publisher results in a live tweet that plays the video. Mock-based tests exercise the full state machine (`pending → in_progress → succeeded`, `pending → failed`, timeout) without hitting the network. The grep-absence test from 104-01 still passes (no `source_url` regression).
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/104-twitter-media-upload-fix/104-CONTEXT.md
@.planning/phases/104-twitter-media-upload-fix/104-RESEARCH.md
@.planning/phases/104-twitter-media-upload-fix/104-01-image-upload-scope-migration-PLAN.md
@app/social/publisher.py
@tests/unit/test_twitter_publisher.py
@tests/smoke/test_twitter_live.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from RESEARCH.md and Plan 104-01 output. -->

After Plan 104-01 lands, `app/social/publisher.py` has this stub (this plan replaces the body):

```python
async def _upload_video_twitter(
    self, http, headers: dict, media_url: str
) -> str | None:
    """Chunked video upload to X v2."""
    raise NotImplementedError(
        "Twitter video chunked upload is implemented in Plan 104-02"
    )
```

Target shape (from RESEARCH.md §"Implementation Approach"):

```python
async def _upload_video_twitter(
    self, http, headers: dict, media_url: str
) -> str | None:
    """Chunked video upload: GET → INIT → APPEND chunks → FINALIZE → STATUS poll.

    Returns media_id on success (processing_info.state == 'succeeded'), or None on
    any failure (logged at WARNING). Honors processing_info.check_after_secs;
    caps total wait at 600s.
    """
    import asyncio  # local import; existing module imports asyncio elsewhere if needed

    # 1. Download bytes
    vid_resp = await http.get(media_url)
    vid_resp.raise_for_status()
    vid_bytes = vid_resp.content
    total_bytes = len(vid_bytes)
    mime = (
        vid_resp.headers.get("content-type", "video/mp4")
        .split(";")[0]
        .strip()
        or "video/mp4"
    )

    if total_bytes > 100 * 1024 * 1024:
        logger.warning(
            "Twitter video %s is %d bytes (>100MB); reading into memory. "
            "Cloud Run memory pressure may surface — see Phase 104 CONTEXT "
            "open question #2.",
            media_url, total_bytes,
        )

    # 2. INIT
    init_resp = await http.post(
        "https://api.x.com/2/media/upload/initialize",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "media_type": mime,
            "total_bytes": total_bytes,
            "media_category": "tweet_video",
        },
    )
    if init_resp.status_code not in (200, 201, 202):
        logger.warning("Twitter video INIT failed (%d): %s",
                       init_resp.status_code, init_resp.text)
        return None
    init_body = init_resp.json()
    media_id = init_body.get("data", {}).get("id") or init_body.get("media_id_string")
    if not media_id:
        logger.warning("Twitter video INIT returned no media_id: %s", init_body)
        return None

    # 3. APPEND chunks (≤4MB each, segment_index monotonic from 0)
    chunk_size = 4 * 1024 * 1024
    for i in range(0, total_bytes, chunk_size):
        chunk = vid_bytes[i : i + chunk_size]
        seg_idx = i // chunk_size
        append_resp = await http.post(
            "https://api.x.com/2/media/upload",
            headers=headers,
            data={
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": seg_idx,
            },
            files={"media": ("chunk", chunk, "application/octet-stream")},
        )
        if append_resp.status_code not in (200, 204):
            logger.warning(
                "Twitter APPEND seg=%d failed (%d): %s",
                seg_idx, append_resp.status_code, append_resp.text,
            )
            return None

    # 4. FINALIZE
    final_resp = await http.post(
        f"https://api.x.com/2/media/upload/{media_id}/finalize",
        headers=headers,
    )
    if final_resp.status_code not in (200, 201):
        logger.warning(
            "Twitter FINALIZE failed (%d): %s",
            final_resp.status_code, final_resp.text,
        )
        return None

    # 5. STATUS poll (only if FINALIZE returned processing_info)
    proc = final_resp.json().get("data", {}).get("processing_info")
    if not proc:
        return media_id  # already succeeded per docs

    deadline = asyncio.get_event_loop().time() + 600  # 10-min cap
    while proc and proc.get("state") in ("pending", "in_progress"):
        if asyncio.get_event_loop().time() > deadline:
            logger.warning(
                "Twitter STATUS poll timed out for media_id=%s after 600s",
                media_id,
            )
            return None
        await asyncio.sleep(proc.get("check_after_secs", 2))
        status_resp = await http.get(
            "https://api.x.com/2/media/upload",
            headers=headers,
            params={"command": "STATUS", "media_id": media_id},
        )
        if status_resp.status_code != 200:
            logger.warning(
                "Twitter STATUS failed (%d): %s",
                status_resp.status_code, status_resp.text,
            )
            return None
        proc = status_resp.json().get("data", {}).get("processing_info")

    if proc and proc.get("state") == "failed":
        err = proc.get("error", {})
        logger.warning(
            "Twitter media processing failed for media_id=%s: %s",
            media_id, err,
        )
        return None
    return media_id
```

From RESEARCH.md §"processing_info.state lifecycle":
- States: `pending → in_progress → (succeeded | failed)`.
- `check_after_secs` is provided by the API; honor it. Fallback 2s.
- Never attach a `media_id` whose state is anything but `succeeded`.

From RESEARCH.md §"Open Questions":
- **#1 (APPEND endpoint shape):** default to `command=APPEND` against `/2/media/upload`. Pivot to `/2/media/upload/append` only if smoke test returns 4xx.
- **#2 (Memory >100MB):** log warning, proceed in-memory. Tempfile fallback deferred.
- **#3 (OAuth2 reliability):** robust 403 path already shipped in 104-01; this plan reuses the same `error` shape from `post_with_media` when `_upload_video_twitter` returns None.

Test pattern for the state machine — chain three STATUS responses in `side_effect`:
```python
status_responses = [
    MagicMock(status_code=200, json=lambda: {"data": {"processing_info": {"state": "pending", "check_after_secs": 1}}}),
    MagicMock(status_code=200, json=lambda: {"data": {"processing_info": {"state": "in_progress", "check_after_secs": 1, "progress_percent": 50}}}),
    MagicMock(status_code=200, json=lambda: {"data": {"processing_info": {"state": "succeeded"}}}),
]
fake_client.get = AsyncMock(side_effect=[bytes_resp, *status_responses])
```

Patch `asyncio.sleep` with `AsyncMock()` to avoid real delays in tests:
```python
with patch("app.social.publisher.asyncio.sleep", new_callable=AsyncMock):
    ...
```
(Place the `import asyncio` inside `_upload_video_twitter` OR at module scope — match Plan 104-01's chosen import location for the patch target. Recommendation: module-scope `import asyncio` at the top of `app/social/publisher.py` for a stable patch path.)

For the timeout test: patch `asyncio.get_event_loop().time` (or wrap deadline in a helper) so the loop sees `current > deadline` after the first iteration.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave-0 RED — add failing tests for the chunked upload state machine + memory warning + timeout</name>
  <files>tests/unit/test_twitter_publisher.py, tests/smoke/test_twitter_live.py</files>
  <behavior>
    Add 5 new failing unit tests in a new `TestVideoChunkedUpload` class in `tests/unit/test_twitter_publisher.py`, plus extend the smoke test file with `test_video_post` (gated). All unit tests must FAIL initially (RED) — `_upload_video_twitter` still raises `NotImplementedError` from Plan 104-01, so tests will fail at the dispatch boundary.

    **A. `tests/unit/test_twitter_publisher.py`** — Add `TestVideoChunkedUpload`:

    1. **test_video_chunked_upload_succeeds** — Happy path through INIT → APPEND (3 chunks for ~10MB video) → FINALIZE → STATUS pending → in_progress → succeeded.
       Setup chains:
       - `http.get` side_effect = `[bytes_resp_10mb, status_pending, status_in_progress, status_succeeded]`
       - `http.post` side_effect = `[init_resp, append_0, append_1, append_2, finalize_resp_with_pending, tweet_resp]`
       Call `await publisher.post_with_media(user_id="u1", platform="twitter", content="video test", media_urls=["https://example.test/clip.mp4"], media_type="video")`.
       Assert:
       - `result` does NOT contain `"error"` (or contains a `data` key matching tweet response).
       - `http.post` calls in order:
         - call 0: URL `"https://api.x.com/2/media/upload/initialize"`, JSON body `{"media_type": "video/mp4", "total_bytes": <int>, "media_category": "tweet_video"}`.
         - calls 1-3: URL `"https://api.x.com/2/media/upload"`, multipart `data` with `command=="APPEND"`, `media_id=="VID_42"`, `segment_index` sequence `[0, 1, 2]` exactly.
         - call 4: URL `"https://api.x.com/2/media/upload/VID_42/finalize"`, no body.
         - call 5: URL `"https://api.twitter.com/2/tweets"`, JSON body `{"text": "video test", "media": {"media_ids": ["VID_42"]}}`.
       - `http.get` calls 1-3 are STATUS polls with params `command=STATUS, media_id=VID_42`.
       - `asyncio.sleep` was awaited 2 times (between status polls — first poll fires immediately after FINALIZE, sleep happens before each subsequent poll). Acceptable range: 1-3 (executor's choice on whether to sleep before first poll). Document the chosen ordering in the SUMMARY.

    2. **test_video_chunked_upload_segment_index_sequence** — Subset of test 1, but specifically asserts that for a video of size `4 * chunk_size + 1 byte` (= 16,777,217 bytes; chunk_size = 4MB), the APPEND calls have `segment_index` exactly `[0, 1, 2, 3, 4]` (5 chunks: four full + one 1-byte tail). No skipped or duplicated indices. (Pitfall 5 from RESEARCH.)

    3. **test_video_chunked_upload_failed_state** — STATUS returns `{"state": "failed", "error": {"code": "FailedToParseVideo", "message": "ProcessFailed"}}` after FINALIZE. Assert:
       - `_upload_video_twitter` returns None (verified indirectly via `post_with_media`'s error path).
       - `result["error"]` contains `"Twitter media upload failed"` (the reconnect copy from 104-01 — accept that string).
       - The tweet POST was NOT issued.
       - A WARNING log contains both `"FailedToParseVideo"` and `"ProcessFailed"`.

    4. **test_video_chunked_upload_timeout** — STATUS keeps returning `{"state": "in_progress", "check_after_secs": 100}` indefinitely. Patch `asyncio.get_event_loop().time` (or a module-level helper if executor extracted one) so first call returns `0` and second returns `601` (exceeds 600s deadline). Assert:
       - `result["error"]` contains substring `"Twitter media upload failed"` (from the `not media_id` branch in `post_with_media`).
       - A WARNING log contains the substring `"timed out"`.
       - Tweet POST was NOT issued.

    5. **test_video_large_logs_memory_warning_but_proceeds** — `bytes_resp` returns 101MB of bytes. Provide a happy-path INIT → 26 APPENDs → FINALIZE-already-succeeded (no processing_info on finalize → skip STATUS poll fast). Assert:
       - WARNING log contains substring `">100MB"` (or `"100MB"`).
       - Upload still completes (`result` has no `"error"` key).
       - APPEND was called 26 times (101MB / 4MB = 25.25, so 26 chunks; `segment_index` 0..25).

    **B. Extend `tests/smoke/test_twitter_live.py`** — Add a second test under the same `RUN_LIVE` skip marker:

    ```python
    @pytest.mark.asyncio
    async def test_video_post():
        """POST-05 success criterion 1: 30s 1080p video posts and plays."""
        from app.social.publisher import SocialPublisher
        user_id = os.environ["TWITTER_TEST_USER_ID"]
        video_url = os.environ.get("TWITTER_TEST_VIDEO_URL")
        if not video_url:
            pytest.skip("TWITTER_TEST_VIDEO_URL not set")
        result = await SocialPublisher().post_with_media(
            user_id=user_id, platform="twitter",
            content=f"Phase 104 video smoke test {os.urandom(4).hex()}",
            media_urls=[video_url], media_type="video",
        )
        assert "error" not in result, f"Live video tweet failed: {result}"
    ```

    **Verify (RED state):** `uv run pytest tests/unit/test_twitter_publisher.py::TestVideoChunkedUpload -x 2>&1 | tail -50` — all 5 tests FAIL with assertion errors that surface the `"not yet available"` error from `post_with_media` (because `_upload_video_twitter` still raises NotImplementedError). The grep test from 104-01 still passes. Smoke tests still skip without `RUN_LIVE=1`.

    Commit message: `test(104-02): add failing tests for Twitter video chunked upload state machine (POST-05)`.
  </behavior>
  <action>
    1. Open `tests/unit/test_twitter_publisher.py` (created in Plan 104-01). Append `TestVideoChunkedUpload` after the existing classes.

    2. Add reusable fixtures or helpers at module scope (so tests stay readable):
       ```python
       def _make_resp(*, status: int = 200, json_body: dict | None = None,
                     text: str = "ok", content: bytes = b"", headers: dict | None = None):
           m = MagicMock()
           m.status_code = status
           m.text = text
           m.content = content
           m.headers = headers or {}
           m.json = MagicMock(return_value=json_body or {})
           m.raise_for_status = MagicMock()
           return m

       def _build_fake_client(*, gets: list, posts: list):
           client = MagicMock()
           client.get = AsyncMock(side_effect=gets)
           client.post = AsyncMock(side_effect=posts)
           async_client = MagicMock()
           async_client.__aenter__ = AsyncMock(return_value=client)
           async_client.__aexit__ = AsyncMock(return_value=None)
           return async_client, client
       ```

    3. Implement the 5 tests above. For the timeout test, patch the time source. The cleanest path is to import `asyncio` at module scope in `app/social/publisher.py` (Task 2 of this plan) and patch `app.social.publisher.asyncio.get_event_loop` to return a mock whose `.time()` returns the fake sequence. Document the patch target as part of the test docstring so Task 2's executor knows to import asyncio at module scope.

    4. For `asyncio.sleep`, patch `app.social.publisher.asyncio.sleep` with `AsyncMock()` to avoid real delays. Use a single `with patch(...)` context wrapping all the Wave-0 video tests OR per-test patches — executor's call.

    5. Extend `tests/smoke/test_twitter_live.py` with `test_video_post` exactly as specified.

    6. Run `uv run pytest tests/unit/test_twitter_publisher.py::TestVideoChunkedUpload -x 2>&1 | tail -40`. Confirm 5 tests fail. Confirm all earlier tests (image, scope, grep, video stub) still pass — i.e. only the new TestVideoChunkedUpload tests are RED.

    7. Run `uv run pytest tests/smoke/ -x` — confirm 2 skipped, exit 0.

    8. Lint: `uv run ruff check tests/unit/test_twitter_publisher.py tests/smoke/test_twitter_live.py --fix && uv run ruff format tests/unit/test_twitter_publisher.py tests/smoke/test_twitter_live.py`.

    9. Commit `test(104-02): ...`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_twitter_publisher.py::TestVideoChunkedUpload -x 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    5 new tests in `TestVideoChunkedUpload` exist and FAIL (RED). Existing 5 tests + scope test still pass. `tests/smoke/test_twitter_live.py` has `test_video_post`; smoke suite still all-skip without `RUN_LIVE=1`. Lint clean. Commit `test(104-02): add failing tests for Twitter video chunked upload state machine (POST-05)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wave-1 GREEN — implement _upload_video_twitter (INIT/APPEND/FINALIZE/STATUS) and module-scope asyncio import</name>
  <files>app/social/publisher.py</files>
  <behavior>
    After this task: all 5 Wave-0 video tests are GREEN. The image tests, scope test, grep test, and video-stub test from 104-01 still pass (the stub test will need an update — see step 5 below).

    **A.** Add `import asyncio` at module scope in `app/social/publisher.py` (top of the file, alphabetical with `import logging`). This stabilizes the patch target `app.social.publisher.asyncio.sleep` and `.get_event_loop` for the unit tests.

    **B.** Replace the body of `_upload_video_twitter` (currently `raise NotImplementedError(...)`) with the full chunked flow shown in the interfaces block. Keep the function signature unchanged.

    Step-by-step:

    1. Download bytes via `await http.get(media_url)`; capture `content`, `headers`, derive `mime` (split on `;`, strip, fallback to `video/mp4`).
    2. Compute `total_bytes`. If `> 100 * 1024 * 1024`, log a WARNING with substring `">100MB"` (the exact log message must contain those characters because the test asserts on them).
    3. POST to `https://api.x.com/2/media/upload/initialize` with `Content-Type: application/json` (added to the headers dict via `{**headers, "Content-Type": "application/json"}`) and JSON body `{"media_type": mime, "total_bytes": total_bytes, "media_category": "tweet_video"}`. Accept 200/201/202; otherwise log + return None.
    4. Extract `media_id` from `init_resp.json().get("data", {}).get("id")` with fallback to `media_id_string`. If missing, log + return None.
    5. APPEND loop: `for i in range(0, total_bytes, chunk_size)` with `chunk_size = 4 * 1024 * 1024`. Each iteration computes `seg_idx = i // chunk_size` and POSTs to `https://api.x.com/2/media/upload` with `data={"command": "APPEND", "media_id": media_id, "segment_index": seg_idx}` and `files={"media": ("chunk", chunk, "application/octet-stream")}`. Accept 200 and 204; otherwise log + return None.
    6. FINALIZE: POST to `f"https://api.x.com/2/media/upload/{media_id}/finalize"` with no body. Accept 200/201; otherwise log + return None.
    7. STATUS poll: read `final_resp.json().get("data", {}).get("processing_info")`. If missing or already `succeeded`, return `media_id`. Otherwise loop while state ∈ `{"pending", "in_progress"}`:
       - Compute `deadline = asyncio.get_event_loop().time() + 600` BEFORE entering the loop.
       - Inside loop: if `asyncio.get_event_loop().time() > deadline`, log WARNING with substring `"timed out"` and return None.
       - `await asyncio.sleep(proc.get("check_after_secs", 2))` (sleep BEFORE the GET — the API explicitly tells us when to come back).
       - `await http.get("https://api.x.com/2/media/upload", headers=headers, params={"command": "STATUS", "media_id": media_id})`.
       - If `status_code != 200`, log + return None.
       - Update `proc = status_resp.json().get("data", {}).get("processing_info")`.
    8. After loop: if `proc and proc.get("state") == "failed"`, log WARNING with `proc.get("error")` (must contain both code and message in the log line — the test asserts on both substrings) and return None.
    9. Return `media_id`.

    **C.** No other changes to `publisher.py`. The Twitter branch dispatch from Plan 104-01 already handles `_upload_video_twitter` returning None via the same `"Twitter media upload failed... reconnect"` message — no change needed.

    **D.** Update the `test_video_path_returns_not_yet_available_error` test from Plan 104-01 — it asserts `"not yet available"` in the error, but after Task 2 the video path succeeds (or returns the reconnect message on real failure). **REWRITE** that test to instead assert the happy path under mocking, OR delete it and replace with one of the new TestVideoChunkedUpload tests. Recommendation: delete the obsolete stub test in this task; it has served its purpose as a guard for Plan 104-01.

    Run `uv run pytest tests/unit/test_twitter_publisher.py -x 2>&1 | tail -30` — all tests GREEN.

    Lint: `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py && uv run ty check app/social/publisher.py`.

    Commit message: `feat(104-02): implement Twitter video chunked upload with STATUS poll (POST-05)`.
  </behavior>
  <action>
    1. Edit `app/social/publisher.py`:
       - Add `import asyncio` at module scope (top of file with `import logging`).
       - Replace the body of `_upload_video_twitter` with the full implementation. The function signature stays `async def _upload_video_twitter(self, http, headers: dict, media_url: str) -> str | None`.
       - Use exact endpoint URLs:
         - `https://api.x.com/2/media/upload/initialize`
         - `https://api.x.com/2/media/upload` (for APPEND with `command=APPEND` form)
         - `https://api.x.com/2/media/upload/{media_id}/finalize`
         - `https://api.x.com/2/media/upload?command=STATUS&media_id={media_id}` (via `params=`)
       - WARNING log lines MUST contain the exact substrings the tests assert on:
         - Memory warning: contains `">100MB"`.
         - Timeout: contains `"timed out"`.
         - Failed state: log `proc.get("error")` such that both the `code` and `message` values appear in the formatted log line. Example: `logger.warning("Twitter media processing failed for media_id=%s: code=%s message=%s", media_id, err.get("code"), err.get("message"))`.

    2. Open `tests/unit/test_twitter_publisher.py` and remove the `test_video_path_returns_not_yet_available_error` test (or convert it into a smoke comment). Mention this in the SUMMARY.

    3. Run `uv run pytest tests/unit/test_twitter_publisher.py -x 2>&1 | tail -30`. Expect all tests GREEN. If a test fails because of a chosen sleep ordering (sleep-before vs sleep-after first STATUS poll), adjust the sleep-count assertion in the relevant test to match the implementation; document the choice in the SUMMARY.

    4. Run regression: `uv run pytest tests/unit -x --ignore=tests/unit/admin 2>&1 | tail -15`. No new failures.

    5. Lint: `uv run ruff check app/social/publisher.py tests/unit/test_twitter_publisher.py --fix && uv run ruff format app/social/publisher.py tests/unit/test_twitter_publisher.py && uv run ty check app/social/publisher.py`.

    6. Commit.

    7. **Open Question handling (CONTEXT #1, APPEND endpoint shape):** the implementation defaults to `command=APPEND` against `/2/media/upload` per RESEARCH.md. If the smoke test in step 8 of phase verification returns 4xx with "unknown command" / "endpoint not found", pivot to `https://api.x.com/2/media/upload/append` and re-run unit tests (update assertions). Do NOT pre-emptively change the URL — defaults first, observe, pivot only if needed. Document the outcome in the SUMMARY.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_twitter_publisher.py -x 2>&amp;1 | tail -25 &amp;&amp; uv run ruff check app/social/publisher.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    `app/social/publisher.py` has `import asyncio` at module scope and a fully-implemented `_upload_video_twitter` (INIT → APPEND → FINALIZE → STATUS poll, honoring `check_after_secs` and the 600s cap). All 5 video tests + all 4 image-side tests + scope test + grep test pass. The obsolete `test_video_path_returns_not_yet_available_error` is removed. `ruff check` and `ty check` clean. Commit `feat(104-02): implement Twitter video chunked upload with STATUS poll (POST-05)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end (CI-safe): `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py -x` → all tests GREEN.

Smoke (manual, gated): `RUN_LIVE=1 TWITTER_TEST_USER_ID=<id> TWITTER_TEST_IMAGE_URL=<url> TWITTER_TEST_VIDEO_URL=<url> uv run pytest tests/smoke/test_twitter_live.py -x`. Run after the connected account has been re-authorized post Phase 104-01 migration. Expect tweet with image and tweet with video to land.

Regression: `uv run pytest tests/unit -x --ignore=tests/unit/admin` — no new failures.

Grep absence (final state): `grep -F 'source_url' app/social/publisher.py` returns at most ONE match (the YouTube branch line ~329, addressed by Phase 105). The Twitter branch must be clean — confirmed by the `test_no_fictional_source_url_in_twitter_branch` test from 104-01.
</verification>

<success_criteria>
- `app/social/publisher.py` imports `asyncio` at module scope.
- `_upload_video_twitter` has a full implementation (no `NotImplementedError`).
- INIT call shape: POST `https://api.x.com/2/media/upload/initialize` with `Content-Type: application/json` and JSON body containing `media_type`, `total_bytes`, `media_category="tweet_video"`.
- APPEND call shape: POST `https://api.x.com/2/media/upload` with multipart `command=APPEND`, `media_id`, monotonic `segment_index` from 0, `files={"media": (..., chunk_bytes, ...)}`. Chunk size = 4 MB.
- FINALIZE call shape: POST `https://api.x.com/2/media/upload/{media_id}/finalize` with no body.
- STATUS poll: GET `https://api.x.com/2/media/upload?command=STATUS&media_id={id}` honoring `check_after_secs`, fallback 2s, capped at 600s total.
- `processing_info.state == "failed"` triggers a WARNING log with the upstream error code and message; function returns None.
- Timeout (>600s) triggers a WARNING log with substring `"timed out"`; function returns None.
- Videos >100MB log a WARNING with substring `">100MB"` and proceed (no tempfile fallback in v13.0).
- 5 new unit tests in `TestVideoChunkedUpload` pass; existing publisher tests still pass; the obsolete `test_video_path_returns_not_yet_available_error` is removed.
- `tests/smoke/test_twitter_live.py::test_video_post` exists and is gated by `RUN_LIVE=1`.
- `ruff check` and `ty check` clean for touched files.
</success_criteria>

<output>
After completion, create `.planning/phases/104-twitter-media-upload-fix/104-02-video-chunked-upload-SUMMARY.md` documenting:
- Exact line numbers of the new `_upload_video_twitter` body.
- Sleep ordering chosen (sleep-before-first-poll vs sleep-only-between-polls) and rationale.
- Open question #1 (APPEND endpoint shape) outcome — did the default `command=APPEND` against `/2/media/upload` work in smoke testing? If pivot was needed, document the change.
- Open question #2 (memory pressure) — confirmed deferred; logged warning + in-memory upload only.
- Test count delta (+5 in `TestVideoChunkedUpload`, -1 obsolete stub test, +1 smoke test).
- Combined Phase 104 final state: confirm `_upload_media_twitter` is gone, `_upload_image_twitter` and `_upload_video_twitter` both shipped, `media.write` scope live, migration filed in `supabase/migrations/`. Phase 104 ready for `/gsd:verify-work` and UAT.
</output>
