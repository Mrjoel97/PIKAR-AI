# Phase 107 Research: Facebook Video Resumable Upload

**Researched:** 2026-05-08
**Domain:** Facebook Graph API video publishing (chunked / resumable)
**Confidence:** HIGH (Meta official reference + multiple corroborating sources)

## Summary

The current Facebook video path in `app/social/publisher.py:175-183` POSTs JSON `{"description": ..., "file_url": ...}` to `https://graph.facebook.com/v18.0/me/videos`. This is broken on three axes: (1) `file_url` is not a documented field on `/{page_id}/videos`, (2) the request must be `multipart/form-data` not JSON, and (3) `me/videos` requires a User token but the OAuth scopes (`pages_*`) are configured for Page tokens. The fix is the documented three-phase chunked upload (`upload_phase=start|transfer|finish`) on `/{page_id}/videos` using a Page access token, plus a single-retry wrapper around chunk transfers.

API version v18.0 expires **2026-01-26** (already past as of today, 2026-05-08). Upgrade to **v23.0+** (v25.0 is current GA per Meta's versioning page). The endpoint accepts both `graph.facebook.com` and `graph-video.facebook.com`; Meta's official reference uses `graph.facebook.com` and that's what we'll standardize on.

**Primary recommendation:** Replace the JSON `file_url` POST with an async three-phase chunked upload using `httpx.AsyncClient` + `multipart/form-data`. Drive the chunk loop from server-returned `start_offset`/`end_offset` pairs. Wrap each `transfer` chunk in a retry-once helper. Resolve the target Page ID + Page access token from `connected_accounts` (captured at OAuth callback — see Page-vs-User Auth section).

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 107 (this phase ran research-only, no `/gsd:discuss-phase` step). Constraints derived directly from ROADMAP.md Phase 107 success criteria:

### Locked Decisions (from Success Criteria)
- Use `https://graph-video.facebook.com/v{API_VERSION}/{PAGE_ID}/videos` endpoint shape (per SC-1 wording). Note: `graph.facebook.com` host is also valid per Meta reference; both are documented. **Recommendation:** standardize on `graph.facebook.com` (Meta's reference docs use it; `graph-video.*` is legacy alias kept alive for compat).
- Three sequential POSTs: `phase=start` → `phase=transfer` (one or more) → `phase=finish`.
- The broken `file_url` parameter must be **absent from the codebase** (verifiable by grep).
- A **mock-based unit test** asserts the three-phase request sequence with a 2-chunk path and the resulting Page-feed POST shape.
- Failures during transfer (network drop, server-rejected chunk) trigger **a single retry** of the failed chunk before surfacing a structured error. Unit test asserts retry-once.

### Claude's Discretion
- API version selection (recommend v23.0 — see API Reference section).
- Chunk size handling: respect server's `start_offset`/`end_offset` window per response (Meta does not return a separate `video_file_chunk_size` field in the documented response — the SC-1 wording is slightly inaccurate; window is conveyed via offsets).
- Whether to read media URL → bytes synchronously or stream. **Recommendation:** stream via `httpx.AsyncClient.stream()` to keep memory bounded for 100MB+ videos.
- Page selection UX for users with multiple Pages.
- Structured error shape returned to caller (recommend `{"error": str, "phase": str, "session_id": str|None}`).

### Deferred Ideas (OUT OF SCOPE)
- Instagram video posting (it's separate publisher branch at `publisher.py:202-224` and uses the container/publish flow — Phase 108).
- Resumption of partial uploads across process restarts (the SC says "retry once" not "persist session and resume later").
- Scheduled/draft posts via `scheduled_publish_time` (not in SC; `published=true` is the default and matches current immediate-post intent).
- Page selection UI (covered by Phase 102 OAuth flow if not already; this phase assumes Page ID + Page token are available).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POST-09 | Replace broken Facebook video upload (`file_url` JSON to `/me/videos`) with three-phase resumable upload (`upload_phase=start|transfer|finish`) on `/{page_id}/videos`, with retry-once on chunk failure | Verified Meta Graph API v25.0 reference for `POST /{page-id}/videos` accepts the four `upload_phase` enum values; response fields per phase documented. See API Reference section. |
</phase_requirements>

## Current State (broken)

**File:** `app/social/publisher.py:175-183`

```python
elif platform == "facebook":
    if has_media and media_type == "video":
        resp = await http.post(
            "https://graph.facebook.com/v18.0/me/videos",
            headers=headers,
            json={
                "description": content,
                "file_url": media_urls[0],
            },
        )
```

**Three problems:**
1. `file_url` is not documented on `/{page_id}/videos` — it works on **photos** (`/me/photos`, line 191 — `url`) but not videos. The endpoint silently ignores it and returns a video record with no media (or 400).
2. Body is JSON; the videos endpoint expects `multipart/form-data` (or at minimum `application/x-www-form-urlencoded` for non-binary phases).
3. Token in `headers` is whatever was stored at OAuth callback. Configured scopes (`connector.py:42-47`) are `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `read_insights` — Page-token scopes — but `me/videos` resolves `me` from the **access token's owner**. If the stored token is a User token, `me` is the user account (not a Page) and posting requires `publish_video` (deprecated) / `publish_actions` (also deprecated). Either way: wrong target.

**API version:** Hardcoded `v18.0` across LinkedIn-adjacent and Facebook calls. v18.0 expired **2026-01-26** ([Meta versioning](https://developers.facebook.com/docs/graph-api/changelog/versions)). Must upgrade.

**Tests:** None. `tests/unit/` has no `test_facebook_*` or `test_publisher.py` covering the video path.

## API Reference (verified)

Source of truth: [Graph API Reference v25.0: Page Videos](https://developers.facebook.com/docs/graph-api/reference/page/videos/) ([Meta]).

### Endpoint
```
POST https://graph.facebook.com/v23.0/{PAGE_ID}/videos
Content-Type: multipart/form-data
```

(`graph-video.facebook.com` is also documented as a valid host alias; the SC-1 text uses it. Both work. Meta's reference page uses `graph.facebook.com` — recommend standardizing there.)

### `upload_phase` enum
Documented values: `start`, `transfer`, `finish`, `cancel`. We implement the first three; `cancel` is optional cleanup on caller-aborted uploads (out of scope per SC-1).

### Phase 1: `start`
**Request fields** (multipart form):
| Field | Value |
|-------|-------|
| `upload_phase` | `start` |
| `access_token` | Page access token |
| `file_size` | Total bytes of the video file |

**Response (200 OK):**
```json
{
  "upload_session_id": "1234567890",
  "video_id": "9876543210",
  "start_offset": "0",
  "end_offset": "5242880"
}
```

The `start_offset`/`end_offset` pair defines the **first chunk window**. The size of the chunk to send = `end_offset - start_offset`. Meta does **not** return a separate `video_file_chunk_size` field in the documented response — the Phase 107 SC-1 wording mentioning `video_file_chunk_size` is technically inaccurate; the window is conveyed via offsets. (Some legacy SDKs surface a derived `video_file_chunk_size` property — that's a client-side convenience, not a server field.)

### Phase 2: `transfer` (looped)
**Request fields** (multipart form):
| Field | Value |
|-------|-------|
| `upload_phase` | `transfer` |
| `access_token` | Page access token |
| `upload_session_id` | From phase=start response |
| `start_offset` | Current offset (from previous response) |
| `video_file_chunk` | Binary slice of file: bytes `[start_offset, end_offset)` |

**Response (200 OK):**
```json
{
  "start_offset": "5242880",
  "end_offset": "10485760"
}
```

**Loop termination:** when response returns `start_offset == end_offset` (server signals "no more bytes to send").

### Phase 3: `finish`
**Request fields** (form, no binary):
| Field | Value |
|-------|-------|
| `upload_phase` | `finish` |
| `access_token` | Page access token |
| `upload_session_id` | From phase=start response |
| `description` *(optional)* | Caption text |
| `title` *(optional)* | Video title |
| `published` *(optional)* | `true` (default) or `false` for drafts |
| `scheduled_publish_time` *(optional)* | Unix timestamp for scheduling (requires `published=false`) |

**Response (200 OK):**
```json
{ "success": true }
```

The video then becomes available on the Page; the `video_id` from phase=start is the canonical ID for subsequent reads/inserts.

## Page-vs-User Auth (CRITICAL DECISION)

**Meta requirement:** Posting video to a Page **requires a Page access token**, not a User access token. The user grants `pages_manage_posts` (and friends) on the User token; the application then exchanges that User token for per-Page tokens via `GET /me/accounts`.

**Current OAuth flow (`connector.py`):** Stores whatever token comes back from the OAuth callback. Likely a User token. Page tokens are **not** automatically populated.

**Decision:** This phase **assumes Page ID + Page token resolution is the caller's responsibility** (i.e., already stored in `connected_accounts.platform_user_id` = Page ID and the access token field stores the Page token). If that storage scheme is User-token-only today, the SC-1 deliverable cannot pass without OAuth callback changes.

**Two paths forward:**

### Path A (recommended, smaller scope): Resolve Page at OAuth callback
- After User token issued, call `GET https://graph.facebook.com/v23.0/me/accounts` to list Pages.
- If exactly one Page → store `(page_id, page_access_token)` automatically.
- If multiple → return list to UI, user picks one, store the chosen Page.
- This change lives in `connector.py:handle_callback` for the `facebook` branch.

### Path B (larger scope, defer): Page selection UI
- New endpoint `GET /api/social/facebook/pages` returning user's Pages.
- New endpoint `POST /api/social/facebook/select-page` updating the stored row.
- More UX work; not justified for Phase 107 scope.

**Plan implication:** A Path-A subtask must exist in the plan to capture Page ID + Page token, OR there must be a precondition that Phase 102 (OAuth) already does this. Audit needed during planning. **Suggested plan structure:**
- Plan 107-01: Three-phase upload implementation in `publisher.py`
- Plan 107-02 (only if needed after audit): Augment `connector.py:handle_callback` for facebook to fetch + store Page token

If Phase 102 already does the Page-token capture, the planner can collapse to a single plan.

## Implementation Approach

### Function signature
```python
# app/social/publisher.py
async def _upload_facebook_video(
    http: httpx.AsyncClient,
    page_id: str,
    page_access_token: str,
    video_bytes: bytes,        # or async iterator for streaming
    description: str,
    title: str | None = None,
    api_version: str = "v23.0",
) -> dict[str, Any]:
    """Three-phase chunked upload to a Facebook Page.

    Returns: {"video_id": str, "success": bool} on success.
    Raises: FacebookUploadError with phase + session_id context on failure.
    """
```

### Algorithm
```
1. POST phase=start with file_size → get session_id, start_offset, end_offset
2. Loop while start_offset < end_offset:
     chunk = video_bytes[start_offset:end_offset]
     POST phase=transfer with session_id, start_offset, video_file_chunk=chunk
       wrapped in _retry_once_on_failure
     start_offset, end_offset = response["start_offset"], response["end_offset"]
3. POST phase=finish with session_id + description (+ optional title)
4. Return {"video_id": video_id_from_start, "success": True}
```

### Retry-once helper (per SC-2)
```python
async def _post_chunk_with_retry(
    http: httpx.AsyncClient,
    url: str,
    data: dict,
    files: dict,
) -> httpx.Response:
    """POST a transfer chunk; retry exactly once on network or 5xx error."""
    for attempt in (1, 2):
        try:
            resp = await http.post(url, data=data, files=files, timeout=60.0)
            if resp.status_code < 500:
                return resp  # 2xx or 4xx — return; let caller decide
            # 5xx — retry once
        except (httpx.RequestError, httpx.ReadTimeout):
            if attempt == 2:
                raise
            continue
    return resp  # last response (after retry)
```

Retry triggers (per SC-2): "network drop mid-chunk" → `httpx.RequestError`/`ReadTimeout`; "server-rejected chunk size" → 5xx response. 4xx responses (auth failure, bad session) do **not** retry — they surface immediately as structured errors.

### Wire-up in `post_with_media`
Replace lines 175-183 with a call to `_upload_facebook_video`, passing `page_id` and `page_access_token` resolved from the `connected_accounts` row (caller of `post_with_media` already has account context).

### Streaming consideration
For 30s 1080p MP4 (~5-15MB), in-memory `bytes` is fine. For larger uploads, prefer `httpx.AsyncClient.stream("POST", ...)` with an async generator yielding the chunk slice. **Recommendation:** Start with `bytes` for v1; document streaming as a follow-up if memory becomes an issue. SC-1 explicitly says "30-second 1080p MP4" so the simple path is sufficient.

## Key Risks

1. **Token type mismatch (HIGH):** If `connected_accounts` stores a User token, `phase=start` will fail with permission error. Mitigation: audit Phase 102's OAuth handler. If Page-token capture is missing, add a sub-plan (see Page-vs-User section, Path A).

2. **API version drift (MEDIUM):** Hardcoding `v23.0` will eventually expire. Mitigation: extract to module-level constant `FB_GRAPH_API_VERSION = "v23.0"` at top of `publisher.py`. Plan a Phase 108-or-later audit when v26.0 ships.

3. **Chunk size respect (LOW):** Server-driven offsets mean we don't pick chunk size. If a server returns an unusually large window for very large files, we'd need to subdivide. Mitigation: SC scope is 30s 1080p MP4; not an issue at this size. Document as a follow-up note.

4. **Long-running uploads / timeouts (LOW for SC scope):** `httpx` default timeout is 5s; large chunks need 60s+. Mitigation: explicit `timeout=httpx.Timeout(60.0, read=120.0)` on chunk POSTs.

5. **`graph-video.*` vs `graph.facebook.com` (LOW):** Both work. SC-1 wording uses `graph-video.*`; Meta reference uses `graph.facebook.com`. **Recommendation:** Standardize on `graph.facebook.com` (current Meta reference; aligns with the rest of `publisher.py`). Document in plan that SC-1's URL example is interchangeable with `graph.facebook.com`.

6. **Mock fidelity (LOW):** Unit tests must mock `httpx.AsyncClient` correctly. Use `respx` (already idiomatic for httpx mocking) or `unittest.mock.AsyncMock` — see Testing Strategy.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio + respx (httpx mocking) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/unit/social/test_publisher_facebook.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| POST-09 (SC-1, three-phase shape) | Mock `httpx` and assert phase=start → 2× phase=transfer → phase=finish request sequence with correct multipart fields and a 2-chunk path | unit | `uv run pytest tests/unit/social/test_publisher_facebook.py::test_video_upload_three_phase_two_chunks -x` | ❌ Wave 0 |
| POST-09 (SC-1, no `file_url`) | Static grep — `file_url` string absent from `app/social/` | static | `! grep -r "file_url" app/social/` (passes when no match) | ❌ Wave 0 |
| POST-09 (SC-2, retry-once) | Mock `httpx` to fail first transfer with 500, succeed on retry; assert exactly 2 attempts for that chunk | unit | `uv run pytest tests/unit/social/test_publisher_facebook.py::test_video_upload_retries_chunk_once_on_5xx -x` | ❌ Wave 0 |
| POST-09 (SC-2, no infinite retry) | Mock `httpx` to fail chunk twice; assert structured error returned, not a third attempt | unit | `uv run pytest tests/unit/social/test_publisher_facebook.py::test_video_upload_surfaces_error_after_retry_exhausted -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/social/test_publisher_facebook.py -x`
- **Per wave merge:** `uv run pytest tests/unit/social/ -x`
- **Phase gate:** Full unit suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/social/__init__.py` — empty package marker
- [ ] `tests/unit/social/test_publisher_facebook.py` — covers POST-09 unit cases (three-phase shape, retry-once, error surfacing, grep verification can live here as a static check)
- [ ] `tests/unit/social/conftest.py` — shared fixtures: mock httpx client via `respx`, fake page_id/access_token, sample MP4 bytes

Add `respx` to dev deps if not already present: `uv add --dev respx`.

## Testing Strategy

### Mock-based unit tests (per SC-1 / SC-2 requirements)

**Test 1: three-phase happy path with 2 chunks**
```python
@respx.mock
async def test_video_upload_three_phase_two_chunks():
    # Set up: 10MB fake video, server returns 5MB windows
    video_bytes = b"\x00" * (10 * 1024 * 1024)

    start_route = respx.post(
        "https://graph.facebook.com/v23.0/PAGE_ID/videos"
    ).mock(side_effect=[
        # phase=start
        httpx.Response(200, json={
            "upload_session_id": "SESSION",
            "video_id": "VID",
            "start_offset": "0",
            "end_offset": "5242880",
        }),
        # phase=transfer (chunk 1)
        httpx.Response(200, json={
            "start_offset": "5242880",
            "end_offset": "10485760",
        }),
        # phase=transfer (chunk 2)
        httpx.Response(200, json={
            "start_offset": "10485760",
            "end_offset": "10485760",
        }),
        # phase=finish
        httpx.Response(200, json={"success": True}),
    ])

    result = await _upload_facebook_video(...)

    assert result == {"video_id": "VID", "success": True}
    assert start_route.call_count == 4
    # Inspect each call's multipart body for upload_phase value
    phases = [_extract_phase(c.request) for c in start_route.calls]
    assert phases == ["start", "transfer", "transfer", "finish"]
```

**Test 2: retry-once on 5xx**
```python
@respx.mock
async def test_video_upload_retries_chunk_once_on_5xx():
    # phase=start succeeds; first transfer 500, retry 200; finish succeeds
    respx.post(...).mock(side_effect=[
        httpx.Response(200, json={"upload_session_id": ..., "start_offset": "0", "end_offset": "5242880", ...}),
        httpx.Response(500, json={"error": "server_busy"}),
        httpx.Response(200, json={"start_offset": "5242880", "end_offset": "5242880"}),
        httpx.Response(200, json={"success": True}),
    ])
    result = await _upload_facebook_video(...)
    assert result["success"] is True
    # Assert 4 total POSTs: start + transfer-fail + transfer-retry + finish
```

**Test 3: retry exhausted → structured error**
```python
async def test_video_upload_surfaces_error_after_retry_exhausted():
    # Two consecutive 500s → no third attempt, structured error returned
    with pytest.raises(FacebookUploadError) as exc:
        await _upload_facebook_video(...)
    assert exc.value.phase == "transfer"
    assert exc.value.session_id == "SESSION"
```

**Static check** (can live in same test file or in `tests/unit/social/test_no_legacy_file_url.py`):
```python
def test_no_legacy_file_url_in_publisher():
    with open("app/social/publisher.py") as f:
        assert "file_url" not in f.read()
```

## Plan Decomposition Hint

**Recommended:** 1 plan, 4-5 tasks.

- **Plan 107-01: Three-phase Facebook video upload**
  - Task 107-01-01: Add `FB_GRAPH_API_VERSION = "v23.0"` constant + replace all `v18.0` references in `publisher.py` (and audit `connector.py` for the same)
  - Task 107-01-02: Implement `_upload_facebook_video()` and `_post_chunk_with_retry()` helpers; add `FacebookUploadError` exception class
  - Task 107-01-03: Replace lines 175-183 in `post_with_media()` with call to `_upload_facebook_video`; thread `page_id` / `page_access_token` through from caller
  - Task 107-01-04: Wave 0 test scaffolding — `tests/unit/social/__init__.py`, `conftest.py`, install `respx`
  - Task 107-01-05: Unit tests covering SC-1 (three-phase 2-chunk shape), SC-2 (retry-once on 5xx, error after exhaustion), static grep check for `file_url` absence

**Conditional Plan 107-02** (only if audit of Phase 102 OAuth callback shows Page tokens are NOT being captured):
  - Augment `connector.py:handle_callback` for facebook to call `GET /me/accounts` and store the first/selected Page's `(id, access_token)`.
  - 2-3 tasks.

Planner should run a quick audit during planning: `grep -n "me/accounts" app/social/` and check `connector.py:handle_callback` — if Page-token resolution exists, drop 107-02; if not, add it.

## Sources

### Primary (HIGH confidence)
- [Meta — Graph API Reference v25.0: Page Videos](https://developers.facebook.com/docs/graph-api/reference/page/videos/) — Confirms `upload_phase` enum {start, transfer, finish, cancel}, response field set, required Page token + `pages_manage_posts` scope, current API version v25.0
- [Meta — Graph API Versions Changelog](https://developers.facebook.com/docs/graph-api/changelog/versions) — Confirms v18.0 expiration 2026-01-26; v22.0/v23.0/v24.0/v25.0 active
- [Meta — Video API Publishing Guide](https://developers.facebook.com/docs/video-api/guides/publishing) — Newer `/{app_id}/uploads` resumable API (alternative path, NOT what we use here)

### Secondary (MEDIUM confidence — corroborate Meta primary)
- [Video Chunked Upload in JavaScript (ki1cx blog)](https://ki1cx.github.io/facebook/api/javascript/video-chunked-upload/) — Concrete request/response examples for the legacy `upload_phase=start|transfer|finish` flow; matches Meta reference
- [GitHub: mrdotb/facebook-api-video-upload](https://github.com/mrdotb/facebook-api-video-upload) — Reference implementation in JS using the same three-phase contract

### Tertiary (LOW confidence — used only for cross-reference)
- [Reintech blog: Using Facebook Video API](https://reintech.io/blog/using-facebook-video-api-for-uploading-managing-videos) — confirms `graph.facebook.com` host (not `graph-video.*`) for the chunked flow

## Metadata

**Confidence breakdown:**
- API contract (three phases, fields, responses): HIGH — Meta v25.0 reference + 2 corroborating sources agree
- API version recommendation (v23.0): HIGH — Meta versioning page
- Page-vs-User token requirement: HIGH — Meta reference explicitly states Page token + `CREATE_CONTENT` capability
- `video_file_chunk_size` field absence: HIGH — Meta reference does not list it; SC-1 wording is slightly off, but offsets convey the same info
- Host (`graph.facebook.com` vs `graph-video.*`): MEDIUM — both are documented; Meta reference uses `graph.facebook.com`; SC-1 uses `graph-video.*`. Both work; recommendation is to standardize on `graph.facebook.com`

**Research date:** 2026-05-08
**Valid until:** 2026-08-08 (Meta API versions are stable for ~6 months; chunked-upload contract has been stable for years)
