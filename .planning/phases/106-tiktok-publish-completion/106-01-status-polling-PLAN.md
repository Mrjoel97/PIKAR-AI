---
phase: 106-tiktok-publish-completion
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/publisher.py
  - tests/unit/social/__init__.py
  - tests/unit/social/test_tiktok_publish_polling.py
autonomous: true
requirements: [POST-08]

must_haves:
  truths:
    - "A TikTok publish via SocialPublisher.post_with_media polls /v2/post/publish/status/fetch/ after init/ until a terminal status is reached"
    - "On PUBLISH_COMPLETE the return dict contains success=True and video_id populated from data.publicaly_available_post_id[0] (note TikTok's typo, preserved verbatim)"
    - "On FAILED the return dict contains an error key and the fail_reason verbatim from data.fail_reason"
    - "On 5-minute cap exceeded the return dict contains 'publish_pending — check TikTok manually' as the error and does NOT report success"
    - "The init request URL is /v2/post/publish/video/init/ (video endpoint), not /v2/post/publish/content/init/ (photo/carousel endpoint)"
    - "The polling loop calls asyncio.sleep — never time.sleep — so the event loop is not blocked"
    - "Polling cadence is exactly 5.0s initial delay then 5.0s between polls; deadline is 300.0s wall-clock from the first sleep"
  artifacts:
    - path: "app/social/publisher.py"
      provides: "SocialPublisher gains _poll_tiktok_publish_status helper; post_with_media TikTok branch fixed-endpoint + polls + returns video_id"
      contains: "_poll_tiktok_publish_status"
    - path: "tests/unit/social/__init__.py"
      provides: "Package marker for tests.unit.social so pytest discovers the new test file"
      contains: ""
    - path: "tests/unit/social/test_tiktok_publish_polling.py"
      provides: "Five unit tests covering 3-poll happy path, FAILED structured error, cap-exceeded pending, asyncio.sleep usage assertion, video-endpoint regression"
      contains: "test_tiktok_publish_polls_until_complete"
  key_links:
    - from: "app/social/publisher.py:post_with_media (tiktok branch)"
      to: "app/social/publisher.py:_poll_tiktok_publish_status"
      via: "direct method call after init/ returns 2xx and data.publish_id is extracted"
      pattern: "_poll_tiktok_publish_status"
    - from: "app/social/publisher.py:_poll_tiktok_publish_status"
      to: "TikTok status/fetch endpoint"
      via: "httpx.AsyncClient.post to https://open.tiktokapis.com/v2/post/publish/status/fetch/ in a loop"
      pattern: "v2/post/publish/status/fetch"
    - from: "app/social/publisher.py:_poll_tiktok_publish_status"
      to: "asyncio.sleep"
      via: "await asyncio.sleep(5.0) once before first poll, then between each non-terminal poll"
      pattern: "asyncio\\.sleep"
    - from: "app/social/publisher.py:post_with_media (tiktok branch)"
      to: "TikTok video init endpoint"
      via: "POST /v2/post/publish/video/init/ (not /content/init/)"
      pattern: "v2/post/publish/video/init"
---

<objective>
Replace the TikTok init-only publish flow at `app/social/publisher.py:284-310` with a complete async two-step flow: corrected `/video/init/` endpoint, then a bounded polling loop against `/v2/post/publish/status/fetch/` that returns the real `video_id` on success, a structured error on `FAILED`, and a `publish_pending` error on the 5-minute cap. Today the publisher reports `success: True` immediately on the `publish_id` response — but TikTok may take 5–60 seconds to actually publish, and the video may never appear if it fails moderation, fails to download from the source URL, or is cancelled by the user. The agent currently has no signal of these outcomes.

Purpose: Satisfy ROADMAP success criterion 1 ("polls every 5s starting 5s after init/, with a hard cap of 5 minutes; on PUBLISH_COMPLETE returns the video_id; on FAILED raises a structured error containing the failure reason; on cap-exceeded raises a 'publish_pending — check TikTok manually' error") AND success criterion 2 ("uses asyncio.sleep between polls, not time.sleep") AND POST-08. Closes the false-success bug surfaced by the v13.0 audit (2026-05-08).

Output: `app/social/publisher.py` with corrected init endpoint, new `_poll_tiktok_publish_status` helper, and a TikTok-specific return path that bypasses the generic 2xx fall-through. Five new pytest tests in `tests/unit/social/test_tiktok_publish_polling.py` covering the 3-poll happy path, FAILED structured error, cap-exceeded pending, `asyncio.sleep` non-blocking usage, and the `/video/init/` endpoint regression. New `tests/unit/social/__init__.py` package marker so the test directory is discoverable.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/106-tiktok-publish-completion/106-CONTEXT.md
@.planning/phases/106-tiktok-publish-completion/106-RESEARCH.md
@app/social/publisher.py
@app/social/connector.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase and TikTok docs. -->
<!-- Use these directly — no codebase exploration needed. -->

From app/social/publisher.py (current shape — DO NOT regress):
```python
class SocialPublisher:
    def __init__(self):
        self.connector = get_social_connector()

    def _get_token_or_error(
        self, user_id: str, platform: str
    ) -> tuple[str | None, dict | None]:
        """Return (token, None) or (None, error_dict)."""

    async def _upload_media_twitter(
        self, http, headers: dict, media_url: str, media_type: str
    ) -> str | None:
        """Upload media to Twitter and return media_id."""

    async def post_with_media(
        self,
        user_id: str,
        platform: str,
        content: str,
        media_urls: list[str] | None = None,
        media_type: str = "image",
    ) -> dict[str, Any]:
        """Post content with optional media attachments.
        Returns: dict with 'success' or 'error' plus platform-specific keys.
        """
```

The current TikTok branch at lines 284-310 issues `POST /v2/post/publish/content/init/`
and falls through to the generic 2xx handler at line 337 which mis-reads the nested
`publish_id`. The branch must be replaced (not extended) with a correct two-step flow.

Existing httpx.AsyncClient context at line 116:
```python
async with httpx.AsyncClient(timeout=60.0) as http:
    # all platform branches share this client
```

The polling helper REUSES this `http` object — no new client creation.

TikTok status fetch contract (from RESEARCH.md, verified against TikTok docs):
- POST https://open.tiktokapis.com/v2/post/publish/status/fetch/
- Headers: `Authorization: Bearer {token}`, `Content-Type: application/json; charset=UTF-8`
- Body: `{"publish_id": "<from init response>"}`
- Rate limit: 30 req/min/access_token (our worst case 12 req/min)

Status enum (data.status):
- `PROCESSING_UPLOAD` — non-terminal, keep polling
- `PROCESSING_DOWNLOAD` — non-terminal, keep polling
- `PUBLISH_COMPLETE` — terminal success; read `data.publicaly_available_post_id[0]` (sic)
- `FAILED` — terminal failure; read `data.fail_reason`
- `SEND_TO_USER_INBOX` — should not appear for direct post; if it does, treat as terminal failure with message "video saved as draft instead of published"

fail_reason values (verbatim, all lowercase): `file_format_check_failed`,
`duration_check_failed`, `frame_rate_check_failed`, `picture_size_check_failed`,
`internal`, `video_pull_failed`, `photo_pull_failed`, `publish_cancelled`,
`auth_removed`, `spam_risk_too_many_posts`, `spam_risk_user_banned_from_posting`,
`spam_risk_text`, `spam_risk`.

Init response shape (success):
```json
{"data": {"publish_id": "v_pub_url~abc123"}, "error": {"code": "ok", "message": ""}}
```
Note: `publish_id` is nested under `data`, NOT top-level. The current generic handler
reads `resp.json().get("publish_id")` which would return `None` for TikTok.

Status response shape (success):
```json
{
  "data": {
    "status": "PUBLISH_COMPLETE",
    "publicaly_available_post_id": ["7012345678901234567"],
    "uploaded_bytes": 12345678
  },
  "error": {"code": "ok", "message": ""}
}
```
**The field name typo `publicaly_available_post_id` is verbatim from TikTok's API.** Read
it exactly as misspelled. Add an inline `# noqa`-style code comment so future readers do
not "fix" it.

Status response shape (failure):
```json
{
  "data": {"status": "FAILED", "fail_reason": "video_pull_failed"},
  "error": {"code": "ok", "message": ""}
}
```
The HTTP-level `error.code` says "ok" even when publish failed — always inspect
`data.status`.

Project async test idiom (reference: tests/unit/test_workflow_publish_contracts.py:25-40):
```python
@pytest.mark.asyncio
async def test_xxx(monkeypatch):
    client = AsyncMock()
    client.post = AsyncMock(side_effect=[response_a, response_b])
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave-0 — package marker + 5 failing unit tests for TikTok polling contract</name>
  <files>tests/unit/social/__init__.py, tests/unit/social/test_tiktok_publish_polling.py</files>
  <behavior>
    Create the test package marker and 5 unit tests that ALL FAIL initially (RED). Tests assert behavior that does not yet exist in `app/social/publisher.py`.

    **File 1:** `tests/unit/social/__init__.py` — empty file (just a package marker so pytest discovers the directory; mirrors the convention at `tests/unit/services/__init__.py` and `tests/unit/agents/__init__.py`).

    **File 2:** `tests/unit/social/test_tiktok_publish_polling.py` — five tests in a single module-level test function set (no class needed, but a `TestTikTokPolling` class is acceptable for grouping):

    1. **`test_tiktok_publish_polls_until_complete`** — 3-poll happy path. Patches `httpx.AsyncClient` to a sequence of 4 responses on `client.post`:
        - Init: `200`, json `{"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}}`
        - Poll 1: `200`, json `{"data": {"status": "PROCESSING_UPLOAD"}, "error": {"code": "ok"}}`
        - Poll 2: `200`, json `{"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}}`
        - Poll 3: `200`, json `{"data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": ["7012345678901234567"], "uploaded_bytes": 12345678}, "error": {"code": "ok"}}`

       Patches `asyncio.sleep` to an `AsyncMock()` (no real-time delays). Patches the connector via `monkeypatch.setattr("app.social.publisher.get_social_connector", lambda: <mock_connector>)` where `mock_connector.get_access_token` returns `"tok_xyz"`. Calls `await SocialPublisher().post_with_media(user_id="u1", platform="tiktok", content="hello world", media_urls=["https://example.com/v.mp4"], media_type="video")`.

       Asserts:
       - `result["success"] is True`
       - `result["platform"] == "tiktok"`
       - `result["video_id"] == "7012345678901234567"`
       - `result["post_id"] == "7012345678901234567"` (post_id mirrors video_id for TikTok success)
       - `result["publish_id"] == "p_abc123"`
       - `result["media_type"] == "video"`
       - `client.post.await_count == 4` (1 init + 3 polls)
       - `asyncio.sleep` was awaited at least 4 times (1 initial + 3 between-poll), each with `5.0` as the only positional arg (use `mock_sleep.await_args_list` and assert each is `call(5.0)`)
       - First `client.post` call URL is exactly `https://open.tiktokapis.com/v2/post/publish/video/init/`
       - All subsequent `client.post` calls URL is exactly `https://open.tiktokapis.com/v2/post/publish/status/fetch/`
       - The status-fetch JSON body contains `{"publish_id": "p_abc123"}`

    2. **`test_tiktok_publish_failed_returns_structured_error`** — failure path. Sequence: init OK, then one poll returning `{"data": {"status": "FAILED", "fail_reason": "video_pull_failed"}, "error": {"code": "ok"}}`. Asserts:
       - `result.get("success") is not True` (no success key OR success=False)
       - `"error" in result` and "video_pull_failed" appears in `result["error"]`
       - `result["fail_reason"] == "video_pull_failed"`
       - `result["publish_id"] == "p_abc123"`
       - `client.post.await_count == 2` (init + one poll, no further polls after FAILED)

    3. **`test_tiktok_publish_cap_exceeded_returns_pending`** — clock-patch test. Use `monkeypatch.setattr` to replace the deadline-clock source the implementation uses. Two acceptable strategies (executor picks based on the implementation's deadline approach):
       - **If the implementation uses `asyncio.get_event_loop().time()`:** patch a stable returnable clock by patching the loop's time. Simpler: patch `asyncio.get_event_loop` to return a mock loop whose `.time()` first returns `0.0`, then returns `301.0` on subsequent calls.
       - **If the implementation uses a counter (`for _ in range(60):`):** drive the loop to exhaust by feeding `PROCESSING_DOWNLOAD` to all polls and asserting the cap-exceeded path is hit after 60 polls. (Faster: parametrize the cap to a low value via dependency injection if the helper accepts `max_total_seconds`.)

       Easiest portable strategy: feed the helper an init response, then on the very next poll return `PROCESSING_DOWNLOAD`, advance the patched clock past 300.0, and assert the loop exits with the pending error. Asserts:
       - `result.get("success") is not True`
       - `"publish_pending" in result["error"]` AND "check TikTok manually" in `result["error"]`
       - `result["publish_id"] == "p_abc123"`

    4. **`test_tiktok_polling_uses_asyncio_sleep_not_time_sleep`** — non-blocking-loop assertion. Patch `time.sleep` (the stdlib top-level function used as `time.sleep` from `import time`) with a `MagicMock()`. Patch `asyncio.sleep` with an `AsyncMock()`. Drive the 3-poll happy path. Asserts:
       - `time.sleep.called is False` (NEVER called — would block the event loop)
       - `asyncio.sleep.await_count >= 4` (initial + 3 between-poll)
       - At least one call to `asyncio.sleep` is `await`-style (use `inspect.iscoroutine` on the return value of `mock_sleep()` OR rely on `AsyncMock`'s `await_count` which only increments on actual `await`)

    5. **`test_tiktok_init_uses_video_endpoint_not_content_endpoint`** — regression test for the endpoint correction. Drive the 3-poll happy path. Asserts:
       - The first `client.post` call URL is exactly `"https://open.tiktokapis.com/v2/post/publish/video/init/"`
       - The string `"content/init"` does NOT appear in any URL passed to `client.post` across any of its calls

    All 5 tests MUST FAIL initially with one of:
    - `AssertionError` (wrong URL still — TikTok branch still uses `/content/init/`)
    - `AssertionError` (poll count is 1, not 4 — no polling loop yet)
    - `AssertionError` (no `video_id` in result — generic handler returns `publish_id` as `post_id`)
    - `AttributeError` / `KeyError` for missing helper

    Run `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x` and confirm all 5 fail. This is the RED state. Commit message: `test(106-01): add failing tests for TikTok publish status polling (POST-08)`.
  </behavior>
  <action>
    1. **Create `tests/unit/social/__init__.py`** — empty file (just touch it; package marker only).

    2. **Create `tests/unit/social/test_tiktok_publish_polling.py`** with the 5 tests above. Skeleton:

    ```python
    """Unit tests for TikTok publish status polling (Phase 106-01, POST-08)."""
    from __future__ import annotations

    import time
    from typing import Any
    from unittest.mock import AsyncMock, MagicMock

    import pytest

    from app.social.publisher import SocialPublisher


    def _resp(status_code: int, payload: dict[str, Any]) -> MagicMock:
        m = MagicMock()
        m.status_code = status_code
        m.json = MagicMock(return_value=payload)
        m.text = str(payload)
        return m


    def _wire_async_client(monkeypatch, post_responses: list[MagicMock]) -> AsyncMock:
        """Patch httpx.AsyncClient so its async-context-manager yields a mock client.

        Returns the inner mock client so tests can assert against `.post.await_args_list`.
        """
        client = AsyncMock()
        client.post = AsyncMock(side_effect=post_responses)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
        return client


    def _wire_connector(monkeypatch, token: str = "tok_xyz") -> None:
        connector = MagicMock()
        connector.get_access_token = MagicMock(return_value=token)
        monkeypatch.setattr("app.social.publisher.get_social_connector", lambda: connector)


    @pytest.mark.asyncio
    async def test_tiktok_publish_polls_until_complete(monkeypatch):
        init_resp = _resp(200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}})
        poll1 = _resp(200, {"data": {"status": "PROCESSING_UPLOAD"}, "error": {"code": "ok"}})
        poll2 = _resp(200, {"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}})
        poll3 = _resp(200, {
            "data": {
                "status": "PUBLISH_COMPLETE",
                "publicaly_available_post_id": ["7012345678901234567"],
                "uploaded_bytes": 12345678,
            },
            "error": {"code": "ok"},
        })
        client = _wire_async_client(monkeypatch, [init_resp, poll1, poll2, poll3])
        _wire_connector(monkeypatch)
        sleep_mock = AsyncMock()
        monkeypatch.setattr("asyncio.sleep", sleep_mock)

        result = await SocialPublisher().post_with_media(
            user_id="u1", platform="tiktok", content="hello world",
            media_urls=["https://example.com/v.mp4"], media_type="video",
        )

        assert result["success"] is True
        assert result["platform"] == "tiktok"
        assert result["video_id"] == "7012345678901234567"
        assert result["post_id"] == "7012345678901234567"
        assert result["publish_id"] == "p_abc123"
        assert result["media_type"] == "video"
        assert client.post.await_count == 4

        # Sleep cadence: at least 4 awaits, each with 5.0
        assert sleep_mock.await_count >= 4
        for call_args in sleep_mock.await_args_list:
            assert call_args.args[0] == 5.0

        # URL assertions
        first_url = client.post.await_args_list[0].args[0]
        assert first_url == "https://open.tiktokapis.com/v2/post/publish/video/init/"
        for poll_call in client.post.await_args_list[1:]:
            assert poll_call.args[0] == "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        # Status-fetch body contains publish_id
        first_poll_kwargs = client.post.await_args_list[1].kwargs
        assert first_poll_kwargs["json"]["publish_id"] == "p_abc123"


    @pytest.mark.asyncio
    async def test_tiktok_publish_failed_returns_structured_error(monkeypatch):
        init_resp = _resp(200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}})
        fail_resp = _resp(200, {
            "data": {"status": "FAILED", "fail_reason": "video_pull_failed"},
            "error": {"code": "ok"},
        })
        client = _wire_async_client(monkeypatch, [init_resp, fail_resp])
        _wire_connector(monkeypatch)
        monkeypatch.setattr("asyncio.sleep", AsyncMock())

        result = await SocialPublisher().post_with_media(
            user_id="u1", platform="tiktok", content="hi",
            media_urls=["https://example.com/v.mp4"], media_type="video",
        )

        assert result.get("success") is not True
        assert "error" in result
        assert "video_pull_failed" in result["error"]
        assert result["fail_reason"] == "video_pull_failed"
        assert result["publish_id"] == "p_abc123"
        assert client.post.await_count == 2


    @pytest.mark.asyncio
    async def test_tiktok_publish_cap_exceeded_returns_pending(monkeypatch):
        init_resp = _resp(200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}})
        # Always return non-terminal — the deadline must trip the loop exit.
        processing_resp = _resp(200, {"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}})
        # Provide a generous side_effect list (more than the cap can poll) so we never run out.
        client = _wire_async_client(monkeypatch, [init_resp] + [processing_resp] * 200)
        _wire_connector(monkeypatch)
        monkeypatch.setattr("asyncio.sleep", AsyncMock())

        # Patch the clock so deadline trips after the first poll.
        # The implementation uses asyncio.get_event_loop().time(); patch the loop.
        clock_values = iter([0.0, 1.0, 999.0, 999.0, 999.0])  # init-time, then trip
        mock_loop = MagicMock()
        mock_loop.time = MagicMock(side_effect=lambda: next(clock_values, 999.0))
        monkeypatch.setattr("asyncio.get_event_loop", lambda: mock_loop)

        result = await SocialPublisher().post_with_media(
            user_id="u1", platform="tiktok", content="hi",
            media_urls=["https://example.com/v.mp4"], media_type="video",
        )

        assert result.get("success") is not True
        assert "publish_pending" in result["error"]
        assert "check TikTok manually" in result["error"]
        assert result["publish_id"] == "p_abc123"


    @pytest.mark.asyncio
    async def test_tiktok_polling_uses_asyncio_sleep_not_time_sleep(monkeypatch):
        init_resp = _resp(200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}})
        poll1 = _resp(200, {"data": {"status": "PROCESSING_UPLOAD"}, "error": {"code": "ok"}})
        poll2 = _resp(200, {"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}})
        poll3 = _resp(200, {
            "data": {
                "status": "PUBLISH_COMPLETE",
                "publicaly_available_post_id": ["7012345678901234567"],
            },
            "error": {"code": "ok"},
        })
        _wire_async_client(monkeypatch, [init_resp, poll1, poll2, poll3])
        _wire_connector(monkeypatch)

        time_sleep_mock = MagicMock()
        monkeypatch.setattr(time, "sleep", time_sleep_mock)
        async_sleep_mock = AsyncMock()
        monkeypatch.setattr("asyncio.sleep", async_sleep_mock)

        result = await SocialPublisher().post_with_media(
            user_id="u1", platform="tiktok", content="hi",
            media_urls=["https://example.com/v.mp4"], media_type="video",
        )

        assert result["success"] is True
        assert time_sleep_mock.called is False, "time.sleep blocks the event loop — must use asyncio.sleep"
        assert async_sleep_mock.await_count >= 4


    @pytest.mark.asyncio
    async def test_tiktok_init_uses_video_endpoint_not_content_endpoint(monkeypatch):
        init_resp = _resp(200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}})
        poll1 = _resp(200, {
            "data": {"status": "PUBLISH_COMPLETE", "publicaly_available_post_id": ["7012"]},
            "error": {"code": "ok"},
        })
        client = _wire_async_client(monkeypatch, [init_resp, poll1])
        _wire_connector(monkeypatch)
        monkeypatch.setattr("asyncio.sleep", AsyncMock())

        await SocialPublisher().post_with_media(
            user_id="u1", platform="tiktok", content="hi",
            media_urls=["https://example.com/v.mp4"], media_type="video",
        )

        first_url = client.post.await_args_list[0].args[0]
        assert first_url == "https://open.tiktokapis.com/v2/post/publish/video/init/"
        for call_args in client.post.await_args_list:
            assert "content/init" not in call_args.args[0]
    ```

    3. Run `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x 2>&1 | tail -40` and confirm ALL 5 tests fail. The exact failure mode varies by test:
       - `test_tiktok_init_uses_video_endpoint_not_content_endpoint` fails on URL assertion (current code uses `/content/init/`)
       - `test_tiktok_publish_polls_until_complete` fails because `client.post.await_count == 1` (no polling) AND `video_id` key missing
       - `test_tiktok_publish_failed_returns_structured_error` fails for same reason
       - `test_tiktok_publish_cap_exceeded_returns_pending` fails because no loop, returns false success
       - `test_tiktok_polling_uses_asyncio_sleep_not_time_sleep` fails because `async_sleep_mock.await_count == 0`

    4. Do NOT touch `app/social/publisher.py` in this task.

    5. Commit: `test(106-01): add failing tests for TikTok publish status polling (POST-08)`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    `tests/unit/social/__init__.py` exists. `tests/unit/social/test_tiktok_publish_polling.py` exists with 5 tests. All 5 tests FAIL (RED state) with assertion errors referencing missing polling, missing `video_id`, or wrong endpoint. No other test files modified. Commit `test(106-01): add failing tests for TikTok publish status polling (POST-08)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire endpoint fix + polling helper into SocialPublisher</name>
  <files>app/social/publisher.py</files>
  <behavior>
    After this task, all 5 tests from Task 1 are GREEN, and `make test` still passes.

    **Change 1 — endpoint correction at `publisher.py:292`:**
    Replace `https://open.tiktokapis.com/v2/post/publish/content/init/` with
    `https://open.tiktokapis.com/v2/post/publish/video/init/`. This is the video
    direct-post endpoint (the previous URL was the photo/carousel endpoint).

    **Change 2 — add `_poll_tiktok_publish_status` helper:**
    Add as an async instance method on `SocialPublisher`, placed alongside
    `_upload_media_twitter` (around lines 43-63). Signature:

    ```python
    async def _poll_tiktok_publish_status(
        self,
        http: "httpx.AsyncClient",
        headers: dict,
        publish_id: str,
        *,
        initial_delay: float = 5.0,
        poll_interval: float = 5.0,
        max_total_seconds: float = 300.0,
    ) -> dict[str, Any]:
        """Poll TikTok /v2/post/publish/status/fetch/ until terminal state.

        Cadence: initial_delay seconds before first poll, then poll_interval
        seconds between polls. Hard-caps at max_total_seconds wall-clock from the
        first sleep. Uses asyncio.sleep so the event loop stays unblocked.

        Returns:
            On PUBLISH_COMPLETE: {"success": True, "platform": "tiktok",
              "post_id": <video_id>, "video_id": <video_id>,
              "publish_id": publish_id, "media_type": "video", "message": ...}
            On FAILED: {"error": "TikTok publish failed: <fail_reason>",
              "fail_reason": <fail_reason>, "publish_id": publish_id}
            On SEND_TO_USER_INBOX (unexpected for direct post):
              {"error": "TikTok saved video as draft instead of publishing",
               "fail_reason": "send_to_user_inbox", "publish_id": publish_id}
            On status-fetch HTTP error: {"error": "TikTok status fetch failed
              ({code}): {body}", "publish_id": publish_id}
            On 5-minute cap: {"error": "publish_pending — check TikTok manually",
              "publish_id": publish_id}
        """
        import asyncio

        await asyncio.sleep(initial_delay)
        deadline = asyncio.get_event_loop().time() + max_total_seconds

        while asyncio.get_event_loop().time() < deadline:
            resp = await http.post(
                "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                headers={
                    **headers,
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={"publish_id": publish_id},
            )
            if resp.status_code != 200:
                return {
                    "error": f"TikTok status fetch failed ({resp.status_code}): {resp.text}",
                    "publish_id": publish_id,
                }

            data = resp.json().get("data", {}) or {}
            status = data.get("status")

            if status == "PUBLISH_COMPLETE":
                # NOTE: TikTok's API field is literally "publicaly_available_post_id"
                # (one 'l' — sic). Do NOT rename to "publicly_..." — that breaks the
                # contract with TikTok's response shape.
                ids = data.get("publicaly_available_post_id") or []
                video_id = ids[0] if ids else None
                return {
                    "success": True,
                    "platform": "tiktok",
                    "post_id": video_id or publish_id,
                    "video_id": video_id,
                    "publish_id": publish_id,
                    "media_type": "video",
                    "message": "Posted to tiktok successfully",
                }
            if status == "FAILED":
                fail_reason = data.get("fail_reason", "unknown")
                logger.warning(
                    "TikTok publish %s FAILED: %s", publish_id, fail_reason,
                )
                return {
                    "error": f"TikTok publish failed: {fail_reason}",
                    "fail_reason": fail_reason,
                    "publish_id": publish_id,
                }
            if status == "SEND_TO_USER_INBOX":
                # Should not occur on direct post path, but TikTok could fall back.
                logger.warning(
                    "TikTok publish %s saved as draft instead of published",
                    publish_id,
                )
                return {
                    "error": "TikTok saved video as draft instead of publishing",
                    "fail_reason": "send_to_user_inbox",
                    "publish_id": publish_id,
                }
            # PROCESSING_UPLOAD / PROCESSING_DOWNLOAD / unknown → keep polling
            await asyncio.sleep(poll_interval)

        return {
            "error": "publish_pending — check TikTok manually",
            "publish_id": publish_id,
        }
    ```

    **Change 3 — wire the polling into the TikTok branch of `post_with_media`:**

    After the existing init `resp = await http.post(...)` call (lines 291-310, with the
    URL now corrected per Change 1), insert a TikTok-specific return path BEFORE the
    generic 2xx handler at line 337. The branch must:

    1. Check the init response status code is in `(200, 201, 202)`.
    2. Extract `publish_id` from `resp.json().get("data", {}).get("publish_id")` —
       NOT from the top level (which is what the generic handler reads).
    3. If `publish_id` is missing, return `{"error": f"TikTok init returned no publish_id: {resp.text}"}`.
    4. Call `await self._poll_tiktok_publish_status(http, headers, publish_id)` and
       return its result directly.
    5. If the init status code is NOT in (200, 201, 202), fall through to the generic
       error handler at line 351.

    Insertion sketch (after the closing `)` of the TikTok init `http.post(...)` call,
    indented to match the `elif platform == "tiktok":` block, BEFORE the
    `# ----- YOUTUBE -----` block):

    ```python
                    # TikTok response: branch BEFORE generic 2xx handler because
                    # publish_id is nested under data and we must poll for outcome.
                    if resp.status_code in (200, 201, 202):
                        tiktok_data = resp.json().get("data", {}) or {}
                        publish_id = tiktok_data.get("publish_id")
                        if not publish_id:
                            return {
                                "error": f"TikTok init returned no publish_id: {resp.text}"
                            }
                        return await self._poll_tiktok_publish_status(
                            http, headers, publish_id,
                        )
                    # Non-2xx: fall through to generic error handler below.
    ```

    The generic 2xx handler at lines 337-352 is left untouched for other platforms.
    Other platform branches (twitter, linkedin, facebook, instagram, youtube) are
    unchanged.

    **Change 4 — preserve all project-rule compliance:**
    - No bare `except:`.
    - No mutable default args.
    - Docstring on the new helper (passes `interrogate` 80% threshold).
    - No `print()` calls.
    - Use `logger` (already imported at line 18) for warnings on terminal failures.

    **Verify GREEN:**
    1. `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x 2>&1 | tail -20` — all 5 tests pass.
    2. `uv run pytest tests/unit/test_workflow_publish_contracts.py -x 2>&1 | tail -10` — no regression on the existing publisher contract tests.
    3. `uv run ruff check app/social/publisher.py 2>&1 | tail -5` — clean.
    4. `uv run ruff format app/social/publisher.py 2>&1 | tail -5` — formats clean.
    5. `uv run ty check app/social/publisher.py 2>&1 | tail -5` — clean.

    Commit message: `feat(106-01): poll TikTok publish status until terminal state (POST-08)`.
  </behavior>
  <action>
    Edit `app/social/publisher.py`:

    1. **Add the helper method** between `_upload_media_twitter` (ends ~line 63) and the `# ---- Public posting methods ----` divider (line 65). Use the exact body from the behavior section above. Do NOT inline `import asyncio` if there is already a top-level `import asyncio` — add a top-level `import asyncio` after `import logging` (line 13) instead, since the loop runs many times and module-scope imports are preferred per project conventions.

    2. **Fix the init URL** at line 292. Change:
       ```python
       "https://open.tiktokapis.com/v2/post/publish/content/init/",
       ```
       to:
       ```python
       "https://open.tiktokapis.com/v2/post/publish/video/init/",
       ```

    3. **Insert the TikTok response branch** immediately after the closing `)` of the TikTok init `http.post(...)` call (after current line 310, before the `# ----- YOUTUBE -----` comment at line 312). Use the exact branch from the behavior section above. Make sure indentation matches the `elif platform == "tiktok":` block (16 spaces for the `if`, 20 for the body) — check by reading lines 285-310 first to confirm the indent depth used by other branches in `post_with_media`.

    4. **Confirm no other change is needed** in the TikTok branch: the body shape, headers, and source_info are correct per RESEARCH.md (PULL_FROM_URL with `video_url` is acceptable for the video init endpoint). Only the URL changes.

    5. Run `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x 2>&1 | tail -30` — confirm all 5 tests GREEN.

    6. Run `uv run pytest tests/unit/test_workflow_publish_contracts.py -x 2>&1 | tail -10` — confirm no regression.

    7. Run `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py && uv run ty check app/social/publisher.py 2>&1 | tail -5` — clean.

    8. Commit: `feat(106-01): poll TikTok publish status until terminal state (POST-08)`.

    **CAREFUL:** The TikTok response branch must come BEFORE the `else:` clause at line 333 (`return {"error": f"Posting not implemented for {platform}"}`) but AFTER the entire `elif platform == "tiktok":` block has emitted its `resp = await http.post(...)` call. The simplest placement is to add the new `if resp.status_code in (200, 201, 202): return await self._poll_...` block as the LAST statement inside the `elif platform == "tiktok":` block (so that block ends with either an early-return for success path or falls through with `resp` set for the generic error handler). Do NOT add a new `elif` — keep the existing `elif platform == "tiktok":` and append the branching at its end.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_tiktok_publish_polling.py tests/unit/test_workflow_publish_contracts.py -x 2>&amp;1 | tail -30 &amp;&amp; uv run ruff check app/social/publisher.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    All 5 TestTikTokPolling tests pass. `tests/unit/test_workflow_publish_contracts.py` still passes (no regression). `ruff check` clean on publisher.py. `ty check` clean. The init URL is `/video/init/`. The new helper `_poll_tiktok_publish_status` exists. The TikTok branch in `post_with_media` returns from the helper directly on 2xx and never reaches the generic 2xx handler. Commit `feat(106-01): poll TikTok publish status until terminal state (POST-08)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end:
1. `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x` — all 5 GREEN.
2. `uv run pytest tests/unit/test_workflow_publish_contracts.py -x` — no regression.
3. `uv run ruff check app/social/publisher.py && uv run ty check app/social/publisher.py` — clean.
4. Grep regression: `grep -n "content/init" app/social/publisher.py` returns nothing (the photo endpoint reference is gone).
5. Grep confirmation: `grep -n "video/init" app/social/publisher.py` returns exactly one hit.
6. Grep confirmation: `grep -n "publicaly_available_post_id" app/social/publisher.py` returns the helper code with the typo preserved.

Manual smoke (deferred to phase-level UAT, NOT required for this plan): connect a TikTok account via `/configuration`, ask the agent to post a short test video — confirm the agent's reply includes the actual TikTok video URL (not just a `publish_id`) within 60 seconds.
</verification>

<success_criteria>
- `app/social/publisher.py` line 292 init URL is `https://open.tiktokapis.com/v2/post/publish/video/init/` (was `/content/init/`).
- `SocialPublisher._poll_tiktok_publish_status` exists with signature `(http, headers, publish_id, *, initial_delay=5.0, poll_interval=5.0, max_total_seconds=300.0) -> dict`.
- The helper uses `await asyncio.sleep(...)` exclusively — no `time.sleep` anywhere in `app/social/publisher.py`.
- The helper reads `data.publicaly_available_post_id` (literal misspelling preserved with inline comment).
- The helper returns the documented dict shapes for PUBLISH_COMPLETE / FAILED / SEND_TO_USER_INBOX / HTTP error / cap exceeded.
- `post_with_media` TikTok branch on 2xx extracts `publish_id` from `data.publish_id` (not top-level), then returns `await self._poll_tiktok_publish_status(...)` directly — bypassing the generic 2xx handler.
- 5 new pytest tests in `tests/unit/social/test_tiktok_publish_polling.py` are GREEN.
- `tests/unit/test_workflow_publish_contracts.py` still passes (regression check).
- `tests/unit/social/__init__.py` exists as empty package marker.
- `ruff check app/social/publisher.py` clean. `ty check app/social/publisher.py` clean.
- `grep -n "content/init" app/social/publisher.py` returns no matches.
</success_criteria>

<output>
After completion, create `.planning/phases/106-tiktok-publish-completion/106-01-status-polling-SUMMARY.md` documenting:
- Exact line numbers of the new helper method and the TikTok response branch
- Confirmation that the init URL is `/video/init/` and the typo `publicaly_available_post_id` is preserved verbatim
- Test count delta (0 → 5 in tests/unit/social/) and full-suite pass confirmation
- Any deviations from this plan (e.g., counter-based deadline vs loop-time deadline)
- Verified-domain risk note for deploy: confirm whether the source URL host (Supabase Storage / Cloud Storage) is on the TikTok app's verified-domain list; if not, `video_pull_failed` will be the dominant fail_reason
</output>
