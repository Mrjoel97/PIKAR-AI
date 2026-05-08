# Phase 106 Research: TikTok Publish Completion

**Researched:** 2026-05-08
**Domain:** TikTok Content Posting API (v2) — direct post + status polling
**Confidence:** HIGH (verified against TikTok developer docs)

## Summary

The TikTok Content Posting API is a two-step asynchronous flow. `init/` returns a
`publish_id` immediately; the caller must poll `/v2/post/publish/status/fetch/`
until a terminal state. The current code at `app/social/publisher.py:284-310`
performs only the init step, then the wrapping handler at lines 337-350 returns
`success: true` with the `publish_id` — false success: video may never appear,
or appears with an error TikTok never surfaces back to us.

**Two material defects in current code besides the missing poll:**

1. **Wrong endpoint.** Code uses `/v2/post/publish/content/init/` (line 292), which
   is the **photo/carousel** endpoint. Video direct post requires
   `/v2/post/publish/video/init/`. Both endpoints accept a `publish_id` so the
   call may have been silently working OR silently failing with a 4xx — needs
   verification but the docs are explicit that `/video/init/` is the video path.
2. **Missing required field for FILE_UPLOAD path.** Not relevant for this phase
   since current code uses `PULL_FROM_URL`, but worth noting for completeness.

**Primary recommendation:** Fix the endpoint to `/v2/post/publish/video/init/`,
then add an async polling loop using `asyncio.sleep(5)` between calls (initial
5s delay, hard cap 5 minutes = 60 polls max), with structured error mapping for
the documented `fail_reason` enum and a distinct cap-exceeded error.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POST-08 | TikTok video posting polls `POST /v2/post/publish/status/fetch/` after `init/` returns `publish_id` until `status` is `PUBLISH_COMPLETE` or terminal failure; returns the resulting video ID to the caller | Status endpoint, status enum, fail_reason enum, response shape all verified below; `video_id` field is delivered via `publicaly_available_post_id` (TikTok's spelling — sic) |
</phase_requirements>

## Current State

**File:** `app/social/publisher.py:284-310` (TikTok branch in `post_to_platform`).

```python
elif platform == "tiktok":
    if not has_media or media_type != "video":
        return {"error": "TikTok requires video content. ..."}
    resp = await http.post(
        "https://open.tiktokapis.com/v2/post/publish/content/init/",  # ← WRONG endpoint
        headers={**headers, "Content-Type": "application/json; charset=UTF-8"},
        json={
            "post_info": {
                "title": content[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": media_urls[0],
            },
        },
    )
```

**Wrapping return** at `publisher.py:337-350` falls through to the generic
2xx-handler that maps `resp.json().get("publish_id")` → `post_id` and returns
`success: True`. This is the false-success the phase fixes.

**Connector config** at `app/social/connector.py:73-79` has scopes
`["user.info.basic", "video.publish", "video.upload"]` — `video.publish` is the
required scope per TikTok docs, so OAuth side is correct.

## API Reference (verified)

### Init endpoint (must change)

| Property | Value |
|----------|-------|
| Method | POST |
| URL | `https://open.tiktokapis.com/v2/post/publish/video/init/` |
| Auth | `Authorization: Bearer {access_token}` |
| Scope | `video.publish` |
| Content-Type | `application/json; charset=UTF-8` |
| Returns | `data.publish_id` (string) |

Photo/carousel uses `/v2/post/publish/content/init/` — **not** what we want.

Source: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post

### Status fetch endpoint

| Property | Value |
|----------|-------|
| Method | POST |
| URL | `https://open.tiktokapis.com/v2/post/publish/status/fetch/` |
| Auth | `Authorization: Bearer {access_token}` |
| Body | `{"publish_id": "<from init response>"}` |
| Rate limit | **30 requests / minute / access_token** |

Source: https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status

### Status enum (exhaustive)

| Value | Terminal? | Meaning |
|-------|-----------|---------|
| `PROCESSING_UPLOAD` | no | FILE_UPLOAD path: TikTok still receiving bytes |
| `PROCESSING_DOWNLOAD` | no | PULL_FROM_URL path: TikTok pulling video from `video_url` |
| `SEND_TO_USER_INBOX` | yes (success-ish) | Video saved to user's drafts (only for inbox/init flow, not direct post — should not appear here) |
| `PUBLISH_COMPLETE` | yes (success) | Video posted publicly; `publicaly_available_post_id` populated |
| `FAILED` | yes (failure) | `fail_reason` populated |

### fail_reason enum (exhaustive)

| Value | Category | User-facing remedy |
|-------|----------|--------------------|
| `file_format_check_failed` | input | Re-encode source video |
| `duration_check_failed` | input | Trim/extend video to TikTok limits |
| `frame_rate_check_failed` | input | Re-encode at supported fps |
| `picture_size_check_failed` | input | Resize to supported dimensions |
| `internal` | tiktok | Retry later |
| `video_pull_failed` | network | URL unreachable / not on verified domain |
| `photo_pull_failed` | network | (carousel; not relevant for video phase but kept for completeness) |
| `publish_cancelled` | user | User cancelled in TikTok app |
| `auth_removed` | auth | Token revoked — re-authenticate |
| `spam_risk_too_many_posts` | rate | Wait and retry |
| `spam_risk_user_banned_from_posting` | rate | Account banned |
| `spam_risk_text` | content | Caption flagged |
| `spam_risk` | content | Generic spam flag |

### Status response shape (success)

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

**Note the typo** — TikTok's field name is literally `publicaly_available_post_id`
(missing the second "l" in "publicly"). This is a known wart of the API. It is
a **list** of strings — for direct post one element; we read `[0]` as the
returned `video_id`.

### Status response shape (failure)

```json
{
  "data": {
    "status": "FAILED",
    "fail_reason": "video_pull_failed"
  },
  "error": {"code": "ok", "message": ""}
}
```

The HTTP-level `error.code` is "ok" even when the publish itself failed — `error`
only reflects the API call. Always inspect `data.status`.

## Implementation Approach

### Polling loop (per success criterion §1)

Add a private async helper alongside the existing `_upload_media_twitter` family:

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
    """Poll TikTok publish status until terminal state.

    Returns dict with success/error in same shape as post_to_platform.
    Uses asyncio.sleep so the event loop remains free.
    """
    import asyncio

    await asyncio.sleep(initial_delay)
    deadline = asyncio.get_event_loop().time() + max_total_seconds

    while asyncio.get_event_loop().time() < deadline:
        resp = await http.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            headers={**headers, "Content-Type": "application/json; charset=UTF-8"},
            json={"publish_id": publish_id},
        )
        if resp.status_code != 200:
            return {"error": f"TikTok status fetch failed ({resp.status_code}): {resp.text}"}

        data = resp.json().get("data", {})
        status = data.get("status")

        if status == "PUBLISH_COMPLETE":
            ids = data.get("publicaly_available_post_id") or []
            return {
                "success": True,
                "platform": "tiktok",
                "post_id": ids[0] if ids else publish_id,
                "video_id": ids[0] if ids else None,
                "publish_id": publish_id,
                "media_type": "video",
                "message": "Posted to tiktok successfully",
            }
        if status == "FAILED":
            return {
                "error": f"TikTok publish failed: {data.get('fail_reason', 'unknown')}",
                "fail_reason": data.get("fail_reason"),
                "publish_id": publish_id,
            }
        # PROCESSING_UPLOAD / PROCESSING_DOWNLOAD → keep polling
        await asyncio.sleep(poll_interval)

    return {
        "error": "publish_pending — check TikTok manually",
        "publish_id": publish_id,
    }
```

### Wire-in point

After the existing init call at `publisher.py:291-310`, branch the response
handling so TikTok bypasses the generic 2xx fall-through at line 337:

```python
# After init response, before generic handler:
if platform == "tiktok" and resp.status_code in (200, 201, 202):
    publish_id = resp.json().get("data", {}).get("publish_id")
    if not publish_id:
        return {"error": f"TikTok init returned no publish_id: {resp.text}"}
    return await self._poll_tiktok_publish_status(http, headers, publish_id)
```

Note: TikTok's init response wraps `publish_id` inside `data` — the generic
handler at line 342 reads `resp_data.get("publish_id")` at the top level and
would currently miss it. Another reason TikTok needs its own return path.

### Why fixed 5s and not exponential

Phase success criterion mandates exact cadence: 5s initial delay, 5s interval,
300s cap. That gives **at most 60 polls** — well under the 30-req/min rate
limit (we'd hit ~12 req/min worst case). No backoff needed; cadence is
explicitly specified.

### Endpoint correction (must ship in same plan)

Change line 292 from `/v2/post/publish/content/init/` to
`/v2/post/publish/video/init/`. This is **mandatory** — without it, TikTok
either rejects the request (it's the photo endpoint, payload schema differs) or
returns a `publish_id` for a draft that never publishes. Either way, polling
won't help if init goes to the wrong endpoint.

## Key Risks

1. **PULL_FROM_URL requires verified domain.** TikTok requires the `video_url`
   host to be on the connected app's verified-domain list (set in TikTok
   developer portal). If Supabase Storage public URLs are not verified, every
   poll will return `FAILED` with `video_pull_failed`. **Mitigation:** Add the
   Supabase Storage host (`*.supabase.co`) to the verified domains in TikTok
   dev portal. Document this as deploy-time prerequisite. If verification is
   blocked, fall back to FILE_UPLOAD (out of scope for this phase per phase
   definition).
2. **Rate limit (30 req/min).** Our 12 req/min ceiling is safe for one publish
   in flight. **If many publishes run concurrently per user**, polls aggregate
   against the same access_token. Mitigation: phase-scope is single publish; if
   parallel publishes appear later, queue or back off.
3. **Long moderation tail.** Docs say moderation "usually finishes within one
   minute" but "in some cases may take a few hours." Our 5-minute cap means
   slow-moderation videos surface as `publish_pending` even though they later
   succeed. The cap-exceeded error message ("check TikTok manually") is the
   correct response — don't extend the cap; very-long polls block the calling
   request.
4. **Field name typo.** `publicaly_available_post_id` — must spell it the
   broken way. Add a code comment so future readers don't "fix" it.
5. **`SEND_TO_USER_INBOX` shouldn't appear** for direct post but TikTok could
   surface it as a fallback. Treat it as terminal failure with a distinct
   message ("video saved as draft instead of published") rather than infinite
   poll.

## Testing Strategy

Project convention is `pytest` with `pytest-asyncio`, `unittest.mock.AsyncMock`,
and monkeypatch (see `tests/unit/test_workflow_publish_contracts.py:25-40` for
the canonical async-test idiom).

### Required tests (per success criteria)

**File:** `tests/unit/social/test_tiktok_publish_polling.py` (new — directory
needs creation; check whether `tests/unit/social/__init__.py` exists in Wave 0).

1. `test_tiktok_publish_polls_until_complete` — patches `httpx.AsyncClient`
   with a sequence of 4 responses: init returns `publish_id`, then status fetch
   returns `PROCESSING_UPLOAD`, then `PROCESSING_DOWNLOAD`, then
   `PUBLISH_COMPLETE` with `publicaly_available_post_id: ["7012..."]`. Patches
   `asyncio.sleep` to AsyncMock to avoid real-time delays. Asserts:
   - Final return has `success: True`, `video_id: "7012..."`, `publish_id` set
   - `asyncio.sleep` called 4 times: once with `5.0` (initial), thrice with
     `5.0` (between polls)
   - `httpx.AsyncClient.post` called 4 times with correct URLs in order
2. `test_tiktok_publish_failed_returns_structured_error` — status sequence ends
   in `FAILED` with `fail_reason: "video_pull_failed"`. Asserts return shape
   includes `error` and `fail_reason` keys.
3. `test_tiktok_publish_cap_exceeded_returns_pending` — patches a clock so
   deadline passes after first poll while status remains `PROCESSING_DOWNLOAD`.
   Asserts return contains `"publish_pending — check TikTok manually"`.
4. `test_tiktok_polling_uses_asyncio_sleep_not_time_sleep` — patch
   `time.sleep` and assert it is **never** called; patch `asyncio.sleep` and
   assert it **is** awaited (not just called sync).
5. `test_tiktok_init_uses_video_endpoint_not_content_endpoint` — regression
   test asserting the URL passed to `httpx.post` for the init step is exactly
   `https://open.tiktokapis.com/v2/post/publish/video/init/`.

### Mock pattern

```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

@pytest.mark.asyncio
async def test_tiktok_publish_polls_until_complete(monkeypatch):
    init_response = MagicMock(status_code=200,
        json=lambda: {"data": {"publish_id": "p_123"}})
    polls = [
        MagicMock(status_code=200, json=lambda: {"data": {"status": "PROCESSING_UPLOAD"}}),
        MagicMock(status_code=200, json=lambda: {"data": {"status": "PROCESSING_DOWNLOAD"}}),
        MagicMock(status_code=200, json=lambda: {"data": {
            "status": "PUBLISH_COMPLETE",
            "publicaly_available_post_id": ["7012345678901234567"],
        }}),
    ]
    client = AsyncMock()
    client.post = AsyncMock(side_effect=[init_response, *polls])
    client.__aenter__.return_value = client
    monkeypatch.setattr("httpx.AsyncClient", lambda **kw: client)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    # ... (token/connector mocks)
    result = await publisher.post_to_platform(
        user_id="u1", platform="tiktok", content="hi",
        media_urls=["https://example.com/v.mp4"], media_type="video",
    )
    assert result["success"] is True
    assert result["video_id"] == "7012345678901234567"
```

## Plan Decomposition Hint

**Likely a single plan: `106-01-tiktok-status-polling`** covering:

1. Fix init endpoint (`/content/init/` → `/video/init/`) at `publisher.py:292`
2. Adjust `publish_id` extraction to read `data.publish_id` not top-level
3. Add `_poll_tiktok_publish_status` helper with the constants from success criteria
4. Branch the TikTok response path before the generic 2xx handler at line 337
5. Add structured error mapping for FAILED states
6. Add 5 unit tests above

Single-plan because all changes are in one file (`app/social/publisher.py`)
plus one test file, ~120 LOC, single conceptual change. No DB migration, no
config change, no router work.

If the planner sees the endpoint correction as separable, it could become
`106-01-fix-init-endpoint` (small) + `106-02-add-status-polling` (main), but
shipping the endpoint fix without polling makes the false-success bug worse
(real publishes now, no telemetry on outcome). Recommend single plan.

## Validation Architecture

Phase config has `nyquist_validation: true` (`.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `pyproject.toml` (project default) |
| Quick run command | `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x` |
| Full suite command | `make test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| POST-08 | 3-poll path returns `video_id` | unit | `pytest tests/unit/social/test_tiktok_publish_polling.py::test_tiktok_publish_polls_until_complete -x` | ❌ Wave 0 |
| POST-08 | FAILED returns structured error | unit | `pytest ...::test_tiktok_publish_failed_returns_structured_error -x` | ❌ Wave 0 |
| POST-08 | Cap-exceeded returns pending | unit | `pytest ...::test_tiktok_publish_cap_exceeded_returns_pending -x` | ❌ Wave 0 |
| POST-08 §2 | Uses `asyncio.sleep` not `time.sleep` | unit | `pytest ...::test_tiktok_polling_uses_asyncio_sleep_not_time_sleep -x` | ❌ Wave 0 |
| POST-08 (regression) | Uses `/video/init/` endpoint | unit | `pytest ...::test_tiktok_init_uses_video_endpoint_not_content_endpoint -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/social/test_tiktok_publish_polling.py -x` (≈2s)
- **Per wave merge:** `uv run pytest tests/unit/social/ -x` (≈10s)
- **Phase gate:** `make test` green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/social/__init__.py` — package marker (verify whether it
      exists; create if missing)
- [ ] `tests/unit/social/test_tiktok_publish_polling.py` — covers POST-08
- [ ] No new fixtures needed; existing `monkeypatch` + `AsyncMock` idiom suffices

## Sources

### Primary (HIGH confidence)
- TikTok Content Posting API — Direct Post: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- TikTok Status fetch endpoint: https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status
- TikTok Get Started — Upload Content: https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content
- `app/social/publisher.py:284-310` — current init-only flow
- `app/social/connector.py:73-79` — TikTok scope config (`video.publish` confirmed)
- `app/social/publisher.py:337-350` — generic 2xx handler that mis-reads init response
- `tests/unit/test_workflow_publish_contracts.py:25-40` — async test convention reference

### Secondary (MEDIUM confidence)
- WebSearch corroborating `/video/init/` (videos) vs `/content/init/` (photos) split

### Tertiary (LOW confidence)
- None — all critical claims (endpoint URLs, status enum, fail_reason enum,
  rate limit, scope) verified against official TikTok docs.

## Metadata

**Confidence breakdown:**
- API endpoints/shapes: HIGH (direct quotes from TikTok docs)
- Status/fail_reason enums: HIGH (exhaustive list from docs)
- Polling cadence safety vs rate limit: HIGH (math: 12 req/min worst case <
  30 req/min limit)
- Implementation approach: HIGH (mirrors existing httpx.AsyncClient usage at
  line 116; asyncio.sleep is stdlib; pattern is conventional)
- Verified-domain risk: MEDIUM (docs mention requirement; can't verify whether
  Supabase host is currently on TikTok app's verified list without checking
  the dev portal — flag for deploy verification)

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days; TikTok API is stable but not stagnant)
