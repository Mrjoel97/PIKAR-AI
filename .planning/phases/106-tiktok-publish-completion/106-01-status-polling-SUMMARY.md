---
phase: 106-tiktok-publish-completion
plan: 01
subsystem: social-publisher
tags: [tiktok, publish, polling, post-08, async, httpx]
requires:
  - app/social/publisher.py:SocialPublisher.post_with_media (existing TikTok branch)
  - app/social/connector.py:get_social_connector (token retrieval)
  - asyncio.sleep / asyncio.get_event_loop().time() (non-blocking cadence + deadline)
  - httpx.AsyncClient (status/fetch HTTP calls reuse the post_with_media client)
provides:
  - SocialPublisher._poll_tiktok_publish_status (async helper, 5s/5s/300s cadence)
  - TikTok dispatch path in post_with_media that returns video_id on PUBLISH_COMPLETE
  - Structured error shapes for FAILED, SEND_TO_USER_INBOX, status-fetch HTTP error, cap exceeded
affects:
  - app/social/publisher.py:1064-1099 (TikTok branch in post_with_media)
  - tests/unit/social/test_tiktok_publish_polling.py (5 new unit tests)
tech-stack:
  added:
    - "(none -- all dependencies already present: asyncio, httpx, pytest, pytest-asyncio)"
  patterns:
    - "Async polling with wall-clock deadline (mirrors _upload_video_twitter)"
    - "Mock httpx.AsyncClient via monkeypatch.setattr(\"httpx.AsyncClient\", lambda *a, **kw: client)"
    - "Mock connector via monkeypatch.setattr(\"app.social.publisher.get_social_connector\", lambda: mock)"
key-files:
  created:
    - tests/unit/social/test_tiktok_publish_polling.py
  modified:
    - app/social/publisher.py
decisions:
  - "Plan asserted >=4 sleep awaits per 3-poll happy path; mathematically only 3 occur (1 initial + 2 between non-terminal polls; terminal poll returns immediately). Loosened test assertions to >=3 with explanatory comment. Plan-spec intent (non-blocking sleep, 5.0s cadence) preserved."
  - "Error string uses ASCII double-hyphen (\"publish_pending -- check TikTok manually\") rather than Unicode em-dash. Tests assert substring containment on \"publish_pending\" and \"check TikTok manually\" so both styles satisfy the contract; double-hyphen avoids encoding gotchas in logs / Slack alerts."
metrics:
  duration: ~25min
  completed: 2026-05-09
---

# Phase 106 Plan 01: TikTok Publish Status Polling Summary

**One-liner:** Replace TikTok's fire-and-forget init-only publish with a bounded async polling loop against `/v2/post/publish/status/fetch/`, fixing the wrong-endpoint regression (`/content/init/` -> `/video/init/`) and surfacing real `video_id` / `fail_reason` instead of false success on the bare `publish_id`.

## Scope Delivered

### Endpoint correction (1 line)
`app/social/publisher.py:1065` -- the TikTok video init URL is now `https://open.tiktokapis.com/v2/post/publish/video/init/` (was `/content/init/`, the photo / carousel endpoint).

### New helper: `_poll_tiktok_publish_status`
`app/social/publisher.py:454-554` -- async instance method on `SocialPublisher`.

Signature:
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
```

Behavior:
- `await asyncio.sleep(initial_delay)` BEFORE first poll.
- Deadline established via `asyncio.get_event_loop().time() + max_total_seconds` AFTER initial sleep.
- Loop: `POST /v2/post/publish/status/fetch/` with `{"publish_id": publish_id}`; switch on `data.status`:
  - `PUBLISH_COMPLETE` -> read `data.publicaly_available_post_id[0]` (TikTok typo verbatim, sic, with inline NOTE comment at `publisher.py:513-516` warning future readers not to "fix" it). Return `{success: True, platform: tiktok, post_id: video_id, video_id, publish_id, media_type: video, message: ...}`.
  - `FAILED` -> log warning; return `{error: "TikTok publish failed: <reason>", fail_reason, publish_id}`.
  - `SEND_TO_USER_INBOX` -> log warning; return `{error: "TikTok saved video as draft instead of publishing", fail_reason: "send_to_user_inbox", publish_id}`.
  - `PROCESSING_UPLOAD` / `PROCESSING_DOWNLOAD` / unknown -> `await asyncio.sleep(poll_interval)` and continue.
- HTTP non-200 -> immediate return `{error: "TikTok status fetch failed (<code>): <body>", publish_id}`.
- Deadline exceeded -> return `{error: "publish_pending -- check TikTok manually", publish_id}`.

### TikTok dispatch in `post_with_media`
`app/social/publisher.py:1084-1099` -- inserted directly after the (now-correct) init `http.post(...)` call, BEFORE the generic 2xx handler. On 2xx init response: extract `data.publish_id` (nested, NOT top-level), validate, then `return await self._poll_tiktok_publish_status(...)`. Non-2xx falls through to the existing generic error handler. Other platform branches (twitter, linkedin, facebook, instagram, youtube) untouched.

### Tests (5 new, all GREEN)
`tests/unit/social/test_tiktok_publish_polling.py`:
1. `test_tiktok_publish_polls_until_complete` -- 3-poll happy path (PROCESSING_UPLOAD -> PROCESSING_DOWNLOAD -> PUBLISH_COMPLETE). Asserts `video_id == "7012345678901234567"`, `post_id == video_id`, `publish_id == "p_abc123"`, `client.post.await_count == 4` (1 init + 3 polls), `asyncio.sleep` awaited >=3 times each at `5.0`, init URL `/video/init/`, poll URL `/status/fetch/`, status-fetch body carries `publish_id`.
2. `test_tiktok_publish_failed_returns_structured_error` -- FAILED on first poll with `fail_reason="video_pull_failed"`. Asserts no `success=True`, `error` contains `"video_pull_failed"`, `fail_reason` field verbatim, `await_count == 2` (no further polls).
3. `test_tiktok_publish_cap_exceeded_returns_pending` -- patches `asyncio.get_event_loop().time` so deadline trips after the first poll while feeding non-terminal `PROCESSING_DOWNLOAD`. Asserts no success, error contains `"publish_pending"` and `"check TikTok manually"`.
4. `test_tiktok_polling_uses_asyncio_sleep_not_time_sleep` -- patches `time.sleep` and `asyncio.sleep`; asserts `time.sleep.called is False` and `asyncio.sleep.await_count >= 3`.
5. `test_tiktok_init_uses_video_endpoint_not_content_endpoint` -- regression: first URL is `/v2/post/publish/video/init/`; substring `"content/init"` appears in zero `client.post` calls.

### Test count delta
`tests/unit/social/`: 4 -> 5 test files (added `test_tiktok_publish_polling.py`); +5 unit tests for TikTok publish.

## Verification

| Check | Result |
| --- | --- |
| `uv run pytest tests/unit/social/test_tiktok_publish_polling.py` | 5 passed in 7.08s |
| `uv run pytest tests/unit/test_workflow_publish_contracts.py` | 2 passed in 11.32s (no regression) |
| `uv run ruff check app/social/publisher.py` | All checks passed |
| `uv run ruff format app/social/publisher.py` | clean |
| `grep -n "content/init" app/social/publisher.py` | zero matches |
| `grep -n "video/init" app/social/publisher.py` | exactly one hit (line 1065) |
| `grep -n "publicaly_available_post_id" app/social/publisher.py` | helper code, typo preserved |
| `grep -n "time.sleep" app/social/publisher.py` | zero matches (asyncio.sleep only) |
| `grep -n "_poll_tiktok_publish_status" app/social/publisher.py` | 3 hits: helper def (455), TikTok branch call (1096), inline reference |

`ty check` not executed: the `uv` shim in this Windows environment supports only `uv run <command>`, blocking the `--with ty` invocation. Ruff lint clean and the helper's type annotations match the surrounding async-method idiom (`_upload_video_twitter` etc.) which already typechecks under `make lint` in CI. Project rules around `make lint` will run `ty check` in CI on the next PR.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test cadence assertion arithmetic was off-by-one**

- **Found during:** Task 2 (first GREEN run)
- **Issue:** Plan spec asserted `sleep_mock.await_count >= 4` for the 3-poll happy path, justified as "1 initial + 3 between-poll". With 3 polls (2 non-terminal + 1 terminal), only 2 between-poll sleeps occur (terminal poll returns immediately, no sleep after). Total awaits = 1 initial + 2 between = 3, not 4.
- **Fix:** Loosened both assertions (`test_tiktok_publish_polls_until_complete` line ~119, `test_tiktok_polling_uses_asyncio_sleep_not_time_sleep` line ~258) from `>= 4` to `>= 3`. Added inline comments documenting the math: "With 3 polls (..., PUBLISH_COMPLETE) the terminal poll returns immediately, so total awaits == 3 (initial + 2 between)."
- **Files modified:** `tests/unit/social/test_tiktok_publish_polling.py`
- **Commit:** `19d4ac32`
- **Plan-spec must_have preserved:** "Polling cadence is exactly 5.0s initial delay then 5.0s between polls" -- still validated by the per-call `assert call_args.args[0] == 5.0` loop.

### Cosmetic deviations (not bugs)

- **Em-dash vs double-hyphen in error string.** Plan text uses `"publish_pending — check TikTok manually"` (Unicode em-dash). Implementation uses `"publish_pending -- check TikTok manually"` (ASCII double-hyphen) to avoid Unicode quoting gotchas in logs / Slack alerts. Tests use substring containment on `"publish_pending"` and `"check TikTok manually"` so both styles satisfy the contract.
- **Reused module-level `import asyncio`** at `publisher.py:13` (already present from Phase 104 video-upload work) instead of inlining `import asyncio` inside the helper as the plan suggested. Module-scope is preferred per project conventions and avoids re-import overhead in the polling loop.

## Verified-Domain Risk Note (Deploy)

**Important for prod rollout:** TikTok's `PULL_FROM_URL` source mode requires the source domain to be on the TikTok Developer app's **Verified Domains** list. If the host (likely Supabase Storage `*.supabase.co` or our Cloud Storage bucket) is not pre-verified in the TikTok app config, the polling loop will reliably surface `fail_reason: "video_pull_failed"` -- which now propagates to the user as a structured error rather than silent false success.

Action item for Phase 106 close-out (NOT this plan's scope):
- Add the production storage domain to `https://developers.tiktok.com/apps/<app_id>/verified-domains` BEFORE first prod video.
- Alternatively, switch TikTok publish to `FILE_UPLOAD` source mode with chunked transfer (matches the Twitter/Facebook idiom). Tracked as a Phase 106 follow-up if `video_pull_failed` rate exceeds 5% in shadow.

## Commits (this plan)

- `29578c19` -- `test(106-01): add failing tests for TikTok publish status polling (POST-08)` (RED, 5 tests)
- `19d4ac32` -- `feat(106-01): poll TikTok publish status until terminal state (POST-08)` (GREEN, helper + dispatch + cadence-math fix)

Note on `29578c19`: the commit transcript also includes the `app/fast_api_app.py` -> `app/routers/{cache_admin,feedback,health}.py` extraction that was already-staged from a prior in-flight session; that work is unrelated to plan 106-01 but was carried by `git commit` because it was in the index at commit time. The plan-relevant delta is the `tests/unit/social/test_tiktok_publish_polling.py` addition.

## Self-Check: PASSED

- `app/social/publisher.py` exists with `_poll_tiktok_publish_status` (line 454) and TikTok dispatch (line 1084-1099): FOUND
- `tests/unit/social/test_tiktok_publish_polling.py` exists with 5 tests: FOUND
- Commit `29578c19`: FOUND
- Commit `19d4ac32`: FOUND
- All 5 new tests pass: VERIFIED (5 passed in 7.08s)
- Regression `test_workflow_publish_contracts` passes: VERIFIED (2 passed)
- Ruff check clean on publisher.py: VERIFIED
- `content/init` removed from publisher.py: VERIFIED (zero matches)
- `time.sleep` absent from publisher.py: VERIFIED (zero matches)
