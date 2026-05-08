# Phase 105 Research: YouTube Resumable Upload

**Researched:** 2026-05-08
**Domain:** YouTube Data API v3 — videos.insert resumable upload protocol
**Confidence:** HIGH (Google official docs verified for protocol; MEDIUM for chunk-size sweet spot)

## Summary

The current YouTube path in `SocialPublisher.post_with_media` (`app/social/publisher.py:319-331`) is non-functional: it `POST`s a JSON body containing a fictional `"source_url"` field to the resumable upload endpoint while *omitting* `uploadType=resumable`. YouTube's API has no `source_url` field — videos.insert requires either multipart, direct, or resumable upload of the actual video bytes. Every call from this code path currently fails (likely with `400 mediaBodyRequired` after YouTube routes the request through the simple-upload path).

The fix is a two-step resumable handshake:
1. `POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` with snippet/status JSON metadata + `X-Upload-Content-Type` and `X-Upload-Content-Length` headers — server returns `200 OK` and a session URL in the `Location` response header.
2. `PUT <session_url>` with the raw video bytes, `Content-Type: video/*`, and `Content-Length` — on success returns `201 Created` with the full video resource (containing `id`).

Bytes must be obtained from the public `media_urls[0]` (typically a Pikar-hosted Supabase Storage URL) by streaming download with `httpx`, then either uploaded in a single PUT (≤5MB happy path) or in 256KB-aligned chunks (8MB recommended) for larger files with `Content-Range` resumption support.

**Primary recommendation:** Build a single async helper `_upload_video_youtube(http, headers, media_url, snippet, status) -> dict` that performs the two-step handshake, downloads media bytes with `httpx`, supports chunked PUT with 308-Resume-Incomplete handling, and returns a structured `{success, post_id, ...}` or `{error, reason, retriable}` dict. Cover all error branches with mock-based unit tests.

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase — proceeding with default scope from ROADMAP.md and the orchestrator-supplied scope.

**Locked Decisions** (from orchestrator scope):
- MUST replace JSON `source_url` field with the proper resumable protocol
- MUST use `POST /upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` then PUT bytes
- The fictional `source_url` MUST be deleted from the codebase (verifiable by grep — success criterion 1)
- Failures MUST surface structured errors with remediation hints (success criterion 2)

**Claude's Discretion:**
- Chunk size (recommend 8MB for non-trivial files; single-PUT for ≤5MB happy path)
- Whether to stream download from Supabase URL vs. download fully into memory (recommend stream-then-PUT for ≤25MB, chunk-streamed PUT above)
- Helper-method placement (recommend new `_upload_video_youtube` peer to `_upload_media_twitter`)
- Whether to add token-refresh on 401 (out of scope — Phase 101 owns token lifecycle; document as follow-up)

**Deferred Ideas:** None applicable.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POST-07 | YouTube uploads use resumable protocol (`POST .../videos?uploadType=resumable&part=snippet,status` → session URL → PUT bytes); replace JSON `source_url` | API Reference section (full request shapes verified against developers.google.com); Implementation Approach section (concrete async function); Error Mapping section (covers SC2) |

## Current State

**File:** `app/social/publisher.py:312-331`

```python
# ----- YOUTUBE -----
elif platform == "youtube":
    if not has_media or media_type != "video":
        return {"error": "YouTube requires video content. ..."}
    resp = await http.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?part=snippet,status",                       # MISSING uploadType=resumable
        headers=headers,                              # ONLY Authorization
        json={
            "snippet": {"title": content[:100], "description": content},
            "status": {"privacyStatus": "public"},
            "source_url": media_urls[0],              # FICTIONAL FIELD — does not exist
        },
    )
```

**Bugs:**
1. `source_url` is not a YouTube API field — videos.insert ignores it and demands actual binary video content.
2. `uploadType=resumable` is missing — without it YouTube treats this as a metadata-only call that returns `400 mediaBodyRequired`.
3. No `X-Upload-Content-Type` / `X-Upload-Content-Length` headers (required for resumable initiation).
4. No second-step PUT of the binary.
5. No `Content-Type: application/json; charset=UTF-8` on the metadata POST.
6. OAuth scopes in `connector.py:66-69` are correct (`youtube.upload` + `youtube`), so token side is fine.

**Connector (correct):** `app/social/connector.py:63-72` declares Google OAuth with `youtube.upload` and `youtube` scopes; reuses `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (`.env.example:55-72` references `GOOGLE_*` vars).

## Target State

Two-step resumable upload, all bytes flow from `media_urls[0]` (e.g., Supabase Storage signed URL) through Pikar to YouTube:

```
[1] DOWNLOAD                       [2] INITIATE                          [3] UPLOAD
Supabase URL ─httpx GET──>  Pikar  ──POST resumable──>  YouTube  ──PUT bytes──>  YouTube
(stream)                    (RAM/  (snippet+status JSON;     (Location: session_url)   (201 Created;
                            chunk) X-Upload-Content-*)                                  video.id returned)
```

## API Reference (verified)

**Sources:**
- https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol (HIGH — official protocol)
- https://developers.google.com/youtube/v3/docs/videos/insert (HIGH — endpoint reference)
- https://developers.google.com/youtube/v3/docs/errors (HIGH — error reasons)

### Step 1 — Initiate Resumable Session

**Method:** `POST`
**URL:** `https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`

**Request headers (all required):**
| Header | Value |
|--------|-------|
| `Authorization` | `Bearer {access_token}` |
| `Content-Type` | `application/json; charset=UTF-8` |
| `Content-Length` | size of the JSON metadata body |
| `X-Upload-Content-Type` | `video/mp4` (or `video/*`, `application/octet-stream`) |
| `X-Upload-Content-Length` | total video file size in bytes |

**Request body** (snippet.title and snippet.categoryId are de-facto required to avoid `invalidVideoMetadata`):
```json
{
  "snippet": {
    "title": "string (required, ≤100 chars)",
    "description": "string (≤5000 chars)",
    "tags": ["optional"],
    "categoryId": "22"
  },
  "status": {
    "privacyStatus": "private | unlisted | public",
    "selfDeclaredMadeForKids": false,
    "embeddable": true,
    "license": "youtube"
  }
}
```

**Note on categoryId:** YouTube returns `400 invalidCategoryId` if missing/invalid for some regions. `"22"` ("People & Blogs") is the safest default; for richer behavior, call `videoCategories.list` (out of scope here).

**Note on privacyStatus default:** Unverified API projects (post-2020-07-28) force every upload to `private` regardless of requested value until audited. The implementation should set the requested status anyway and surface a docs link in the response message if `private` is returned despite a `public` request.

**Successful response:**
- Status: `200 OK`
- Header: `Location: https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=XXX&part=snippet,status`
- Body: empty
- **Action:** capture `Location` header — this is the `session_url` for Step 2.

### Step 2 — Upload Video Bytes (single PUT, ≤256GB)

**Method:** `PUT`
**URL:** the `session_url` from Step 1's `Location` header

**Request headers:**
| Header | Value |
|--------|-------|
| `Authorization` | `Bearer {access_token}` *(redundant per Google docs but harmless; some HTTP clients drop it on cross-host PUT, so include explicitly)* |
| `Content-Type` | matches `X-Upload-Content-Type` from Step 1 (e.g., `video/mp4`) |
| `Content-Length` | total video bytes |

**Request body:** raw binary video bytes.

**Successful response:**
- Status: `201 Created`
- Body: full Video resource — extract `id` for `post_id`:
```json
{
  "kind": "youtube#video",
  "id": "dQw4w9WgXcQ",
  "snippet": { /* ... */ },
  "status": { "privacyStatus": "public", "uploadStatus": "uploaded" }
}
```

### Step 2-Alt — Chunked Upload (recommended for files > 8MB)

**Per chunk (PUT to session_url):**
```
PUT {session_url} HTTP/1.1
Authorization: Bearer {token}
Content-Length: {chunk_size}
Content-Type: video/mp4
Content-Range: bytes {start}-{end}/{total_size}

{chunk_bytes}
```

**Constraints:**
- Each chunk except the last MUST be a multiple of **256 KB** (262144 bytes).
- All non-final chunks should be the same size.
- Recommended chunk size: **8 MB** (8388608 bytes — divisible by 256KB, balances memory vs. RTT).
- Maximum file size: **256 GB**.

**Per-chunk responses:**
- Intermediate chunks: `308 Resume Incomplete` with header `Range: bytes=0-{last_received_byte}` (extract upper bound to compute next chunk start).
- Final chunk: `201 Created` with full Video resource.

**Resume after network interrupt:** send empty PUT with `Content-Range: bytes */{total_size}` → response `308` with `Range: bytes=0-{N}` indicates how much YouTube actually received. Resume from byte `N+1`.

### Quota & limits

- **Quota cost:** 100 units per `videos.insert` call (default daily quota = 10,000 units → ~100 uploads/day per project).
- **Rate-limit (429):** transient; exponential backoff.
- **Quota exhausted (403 quotaExceeded):** wait 24h or request quota increase in Google Cloud Console.

## Implementation Approach

### Recommended structure

Add a new method on `SocialPublisher` (peer to `_upload_media_twitter`):

```python
# app/social/publisher.py — new helper

# Constants at module top
YOUTUBE_RESUMABLE_INIT_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)
YOUTUBE_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB, multiple of 256KB
YOUTUBE_SINGLE_PUT_THRESHOLD = 25 * 1024 * 1024  # ≤25MB → single PUT
YOUTUBE_DEFAULT_CATEGORY_ID = "22"  # People & Blogs
DEFAULT_VIDEO_MIME = "video/mp4"


async def _upload_video_youtube(
    self,
    http: "httpx.AsyncClient",
    token: str,
    media_url: str,
    title: str,
    description: str,
    privacy_status: str = "public",
    category_id: str = YOUTUBE_DEFAULT_CATEGORY_ID,
    mime_type: str = DEFAULT_VIDEO_MIME,
) -> dict[str, Any]:
    """Two-step resumable upload to YouTube.

    Returns:
        Success: {"success": True, "post_id": video_id, "platform": "youtube",
                  "privacy_status": status_from_response}
        Error:   {"success": False, "error": message, "reason": code,
                  "retriable": bool, "remedy": hint}
    """
    # 1. Download bytes (small files: full read; large: stream + collect)
    try:
        async with http.stream("GET", media_url) as src:
            if src.status_code != 200:
                return {
                    "success": False,
                    "error": f"Could not fetch media from {media_url}: HTTP {src.status_code}",
                    "reason": "media_fetch_failed",
                    "retriable": True,
                    "remedy": "verify the media URL is accessible and retry",
                }
            video_bytes = await src.aread()
    except httpx.RequestError as exc:
        return {
            "success": False,
            "error": f"Network error fetching media: {exc}",
            "reason": "media_fetch_network",
            "retriable": True,
            "remedy": "retry now",
        }

    total_size = len(video_bytes)

    # 2. Initiate resumable session
    init_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": mime_type,
        "X-Upload-Content-Length": str(total_size),
    }
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    init_resp = await http.post(
        YOUTUBE_RESUMABLE_INIT_URL,
        headers=init_headers,
        json=metadata,
    )
    if init_resp.status_code != 200:
        return _map_youtube_error(init_resp, stage="initiate")

    session_url = init_resp.headers.get("Location")
    if not session_url:
        return {
            "success": False,
            "error": "YouTube did not return a session URL",
            "reason": "missing_location_header",
            "retriable": True,
            "remedy": "retry now",
        }

    # 3. PUT bytes (single shot for small files; chunked for large)
    if total_size <= YOUTUBE_SINGLE_PUT_THRESHOLD:
        put_resp = await http.put(
            session_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": mime_type,
                "Content-Length": str(total_size),
            },
            content=video_bytes,
        )
        if put_resp.status_code == 201:
            data = put_resp.json()
            return {
                "success": True,
                "platform": "youtube",
                "post_id": data.get("id"),
                "privacy_status": data.get("status", {}).get("privacyStatus"),
            }
        return _map_youtube_error(put_resp, stage="upload",
                                  session_url=session_url)

    # Chunked path (>25MB) — see "Chunked uploader" below
    return await _put_chunked(http, token, session_url, video_bytes,
                              total_size, mime_type)
```

### Chunked uploader (≥25MB path)

```python
async def _put_chunked(http, token, session_url, video_bytes, total_size, mime_type):
    """PUT bytes in 8MB chunks, handle 308 Resume Incomplete."""
    offset = 0
    while offset < total_size:
        end = min(offset + YOUTUBE_CHUNK_SIZE, total_size) - 1
        chunk = video_bytes[offset : end + 1]
        resp = await http.put(
            session_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Length": str(len(chunk)),
                "Content-Type": mime_type,
                "Content-Range": f"bytes {offset}-{end}/{total_size}",
            },
            content=chunk,
        )
        if resp.status_code == 201:
            data = resp.json()
            return {"success": True, "platform": "youtube",
                    "post_id": data.get("id"),
                    "privacy_status": data.get("status", {}).get("privacyStatus")}
        if resp.status_code == 308:
            # Range header tells us how much YouTube actually received
            range_hdr = resp.headers.get("Range", f"bytes=0-{end}")
            try:
                received_upper = int(range_hdr.split("-")[-1])
                offset = received_upper + 1
            except (ValueError, IndexError):
                offset = end + 1
            continue
        return _map_youtube_error(resp, stage="upload_chunk",
                                  session_url=session_url)
    return {"success": False, "error": "Upload finished without 201",
            "reason": "no_terminal_response", "retriable": True,
            "remedy": "retry now"}
```

### Wire into `post_with_media`

Replace `app/social/publisher.py:312-331` with:

```python
elif platform == "youtube":
    if not has_media or media_type != "video":
        return {"error": "YouTube requires video content. "
                         "Provide a video URL with media_type='video'."}
    result = await self._upload_video_youtube(
        http, token, media_urls[0],
        title=content[:100], description=content,
        privacy_status="public",
    )
    if not result.get("success"):
        return {"error": result.get("error"), "reason": result.get("reason"),
                "retriable": result.get("retriable"),
                "remedy": result.get("remedy")}
    return {**result, "media_type": media_type,
            "message": "Posted to youtube successfully"}
```

This early-returns from the YouTube branch (skipping the unified response handling at lines 336+) since the resumable flow has its own success/error shape.

## Error Mapping (for success criterion 2)

Helper used by `_upload_video_youtube`:

```python
def _map_youtube_error(resp, *, stage: str, session_url: str | None = None):
    code = resp.status_code
    try:
        body = resp.json()
        err = body.get("error", {})
        reason = (err.get("errors", [{}])[0].get("reason")
                  or err.get("status") or str(code))
        message = err.get("message") or resp.text[:300]
    except Exception:
        reason, message = str(code), resp.text[:300]

    mapping = {
        # 400 — invalid metadata; non-retriable, fix-then-retry
        "invalidVideoMetadata": ("re-check title and categoryId before retrying", False),
        "invalidTitle":         ("provide a non-empty video title", False),
        "invalidDescription":   ("clean up the description and retry", False),
        "invalidCategoryId":    ("use a valid YouTube category id (e.g. 22)", False),
        "invalidTags":          ("remove problematic tags and retry", False),
        "mediaBodyRequired":    ("internal: video bytes were not sent — file a bug", False),

        # 401 — token issue
        "authorizationRequired": ("re-authenticate the YouTube account", False),
        "youtubeSignupRequired": ("the connected Google account has no YouTube channel — "
                                  "create one at youtube.com and reconnect", False),

        # 403 — permission/quota
        "quotaExceeded":           ("wait ~24h for daily quota reset, or request a quota "
                                    "increase in Google Cloud Console", True),
        "uploadLimitExceeded":     ("YouTube upload limit hit; wait before retrying", True),
        "rateLimitExceeded":       ("retry with exponential backoff", True),
        "forbiddenPrivacySetting": ("use 'public', 'unlisted', or 'private'", False),
        "forbiddenLicenseSetting": ("use a supported license value", False),
        "insufficientPermissions": ("re-authenticate and grant youtube.upload scope", False),
        "forbidden":               ("re-authenticate the account", False),

        # 404 — expired session URL
        "404":         ("upload session expired; re-initiate from step 1", True),
        "notFound":    ("upload session expired; re-initiate from step 1", True),

        # 5xx + 429 — transient
        "backendError":      ("retry with exponential backoff", True),
        "processingFailure": ("retry with exponential backoff", True),
    }
    remedy, retriable = mapping.get(reason, _default_remedy(code))
    return {
        "success": False,
        "error": f"YouTube {stage} failed ({code} {reason}): {message}",
        "reason": reason,
        "retriable": retriable,
        "remedy": remedy,
        "stage": stage,
    }


def _default_remedy(code: int) -> tuple[str, bool]:
    if code == 401: return ("re-authenticate the YouTube account", False)
    if code == 404: return ("upload session expired; re-initiate from step 1", True)
    if code == 429: return ("rate-limited; retry with backoff", True)
    if 500 <= code < 600: return ("transient YouTube server error; retry with backoff", True)
    if 400 <= code < 500: return ("non-retriable client error; fix request and retry", False)
    return ("unexpected response; retry once then escalate", True)
```

**Failure mode → remedy table** (this is what the unit test asserts for success criterion 2):

| Failure mode | HTTP | reason | retriable | remedy |
|--------------|------|--------|-----------|--------|
| Network interrupt mid-PUT | (httpx exception) | `media_fetch_network` / chunk PUT exception | yes | "retry now" |
| Expired session URL | 404 | `notFound` | yes | "upload session expired; re-initiate from step 1" |
| Rejected metadata (bad title) | 400 | `invalidTitle` | no | "provide a non-empty video title" |
| Bad category | 400 | `invalidCategoryId` | no | "use a valid YouTube category id (e.g. 22)" |
| Token expired | 401 | `authorizationRequired` | no | "re-authenticate the YouTube account" |
| Quota exhausted | 403 | `quotaExceeded` | yes (24h) | "wait ~24h for daily quota reset…" |
| Rate limit | 429 / 403 rateLimitExceeded | `rateLimitExceeded` | yes | "retry with exponential backoff" |
| YouTube 5xx | 500/502/503/504 | `backendError` / status code | yes | "transient YouTube server error; retry with backoff" |
| No channel on account | 401 | `youtubeSignupRequired` | no | "create a YouTube channel and reconnect" |

## Key Risks

1. **Token expiry mid-upload** (large files >100MB take >60s): the OAuth bearer applies to BOTH steps. If the token expires between Step 1 and a late chunk in Step 2, YouTube returns `401`. Mitigation: capture token at function entry (already done — single `token` arg); document that Phase 101's encrypted token reads + future refresh logic owns this. Out of scope here.
2. **Memory pressure on large files**: `await src.aread()` loads the full file into RAM. For Pikar's typical short social videos (≤25MB) this is fine; for >100MB videos, switch to streaming download to a `tempfile.SpooledTemporaryFile` and chunked PUT from disk. **Recommendation:** ship the in-memory path first; flag tempfile path as a follow-up if observed file sizes exceed 50MB.
3. **Chunk-size compliance**: ALL non-final chunks MUST be exact multiples of 256KB. Off-by-one in chunk math → YouTube rejects with `400`. Mitigation: use `YOUTUBE_CHUNK_SIZE = 8 * 1024 * 1024` constant; only the final chunk computes `min(offset + CHUNK, total)`.
4. **`Location` header missing**: rare but possible — handle as retriable `missing_location_header` error rather than crashing.
5. **Unverified API project restriction**: any account/project that hasn't passed YouTube API audit gets uploads forced to `private`. Detect by comparing requested `privacyStatus` to response `status.privacyStatus`; surface a non-fatal warning.
6. **httpx default `follow_redirects=False`**: the Step-1 response is `200` (not a 3xx redirect), so this is fine — but if YouTube ever 308's in step 1, httpx would not follow. Document but don't act.
7. **Quota cost**: 100 units per upload. With Pikar's default 10k quota, that's 100 uploads/day across all users. Surfacing `quotaExceeded` clearly is critical.

## Testing Strategy

### Unit tests (mock-based, REQUIRED for success criteria)

**Framework:** pytest + `pytest-asyncio` (pikar standard — `make test` already runs these). Mock `httpx.AsyncClient` with `respx` (preferred — semantic, route-based) or `unittest.mock.AsyncMock` (already widespread in codebase).

`tests/unit/test_youtube_publisher.py` — minimum cases:

| Test | Asserts |
|------|---------|
| `test_youtube_resumable_two_step_sequence` | Mock 200 init w/ `Location` header + 201 PUT → result has `success=True, post_id="abc123"`; verify exactly one POST to `.../videos?uploadType=resumable&part=snippet,status` and one PUT to the session URL |
| `test_youtube_init_request_shape` | POST headers include `Authorization`, `Content-Type: application/json; charset=UTF-8`, `X-Upload-Content-Type: video/mp4`, `X-Upload-Content-Length: <bytes>`; body has `snippet.title`, `snippet.categoryId`, `status.privacyStatus`; body does NOT contain `source_url` |
| `test_youtube_put_request_shape` | PUT headers include `Content-Type: video/mp4`, `Content-Length: <bytes>`; body equals the downloaded media bytes |
| `test_youtube_no_source_url_in_codebase` | Grep assertion: `"source_url"` does not appear in `app/social/publisher.py` (covers SC1 grep clause) |
| `test_youtube_error_400_invalid_metadata` | 400 `invalidTitle` → `{success:False, reason:"invalidTitle", retriable:False, remedy:"provide a non-empty video title"}` |
| `test_youtube_error_401_token_expired` | 401 `authorizationRequired` → `retriable:False, remedy:"re-authenticate..."` |
| `test_youtube_error_403_quota_exceeded` | 403 `quotaExceeded` → `retriable:True, remedy:"wait ~24h..."` |
| `test_youtube_error_404_expired_session` | 404 on PUT → `retriable:True, remedy:"upload session expired..."` |
| `test_youtube_error_5xx_transient` | 503 → `retriable:True, remedy:"transient YouTube server error..."` |
| `test_youtube_network_interrupt_during_put` | `httpx.RequestError` raised on PUT → structured error, `retriable:True, remedy:"retry now"` |
| `test_youtube_missing_location_header` | 200 init with no Location → structured error, `retriable:True` |
| `test_youtube_chunked_upload_resume_path` | File > threshold → multiple PUTs with `Content-Range`; mock 308 with `Range: bytes=0-N` then 201 → success; assert chunk math |

### Smoke test (feature-flagged — REQUIRED for SC1 "real-API smoke test")

`tests/smoke/test_youtube_real_upload.py` — gated behind `PIKAR_RUN_YOUTUBE_SMOKE=1` env flag (mirroring twitter pattern). Uses a dedicated test channel/account credentials from CI secrets. Uploads a 1MB MP4 fixture (`tests/fixtures/test_video_1mb.mp4`), asserts the returned `post_id` resolves via `videos.list?id=<id>` to a video on the channel.

### Pre-existing infrastructure

- `pytest` + `pytest-asyncio` in `pyproject.toml` ✅
- `httpx` already in deps ✅
- `respx` — verify with `uv pip show respx`; if absent, add to dev deps
- No existing `tests/unit/test_*social*.py` or `test_publisher*.py` — Wave 0 will create the file from scratch (no fixtures to retrofit)

## Validation Architecture

`workflow.nyquist_validation = true` in `.planning/config.json`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (Python 3.10+) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/unit/test_youtube_publisher.py -x` |
| Full suite command | `make test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| POST-07 | Two-step resumable handshake (POST → Location → PUT) | unit | `uv run pytest tests/unit/test_youtube_publisher.py::test_youtube_resumable_two_step_sequence -x` | ❌ Wave 0 |
| POST-07 | `source_url` absent from codebase | unit (grep) | `uv run pytest tests/unit/test_youtube_publisher.py::test_youtube_no_source_url_in_codebase -x` | ❌ Wave 0 |
| POST-07 | Init request shape (headers + body) | unit | `uv run pytest tests/unit/test_youtube_publisher.py::test_youtube_init_request_shape -x` | ❌ Wave 0 |
| POST-07 SC2 | Error mapping for 5+ failure modes | unit | `uv run pytest tests/unit/test_youtube_publisher.py -k error -x` | ❌ Wave 0 |
| POST-07 SC1 | Real upload to test channel | smoke (gated) | `PIKAR_RUN_YOUTUBE_SMOKE=1 uv run pytest tests/smoke/test_youtube_real_upload.py` | ❌ Wave 0 (manual fixture acceptable) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_youtube_publisher.py -x`
- **Per wave merge:** `make test`
- **Phase gate:** `make test` green AND smoke test green (manually triggered) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_youtube_publisher.py` — covers POST-07 unit cases (12 tests above)
- [ ] `tests/smoke/test_youtube_real_upload.py` — gated smoke test for SC1
- [ ] `tests/fixtures/test_video_1mb.mp4` — 1MB MP4 fixture for smoke test (one-time)
- [ ] Verify `respx` is in dev deps: `uv pip show respx` → if missing, `uv add --dev respx`

## Plan Decomposition Hint

**Recommendation: 1 plan, 3 waves (~5 tasks total)**

This phase is small and focused (single helper method + error mapper + tests). One plan keeps the work cohesive.

**Plan: `105-01-youtube-resumable-upload.md`**

| Wave | Tasks |
|------|-------|
| **W0 — Test scaffolding** | T1: Create `tests/unit/test_youtube_publisher.py` with all 12 test stubs (xfail until W2); ensure `respx` available. T2: Add 1MB MP4 fixture and gated smoke test stub. |
| **W1 — Implementation** | T3: Add `_upload_video_youtube` + `_put_chunked` + `_map_youtube_error` helpers + module constants (`YOUTUBE_*`). T4: Replace `publisher.py:312-331` with the new flow; delete `source_url`. |
| **W2 — Verification** | T5: Un-xfail tests, fix any drift, run `make test`. Manual smoke test with real test-channel creds. |

**Why 1 plan, not 2:** the helper, the call-site change, and the tests are tightly coupled — splitting them creates merge friction since `post_with_media` references symbols defined in the helper module.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | already pinned | Async HTTP client for both download + upload | Already used by `app/social/publisher.py:106`; supports streaming, custom headers, async PUT |
| `pytest` + `pytest-asyncio` | already pinned | Test framework | Pikar's standard (`make test`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `respx` | latest | HTTP mocking | Cleanest way to mock the two-step sequence; falls back to `unittest.mock.AsyncMock` if not adoptable |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled httpx PUT | `google-api-python-client` MediaFileUpload | Adds a heavy sync-only dep; `googleapiclient` is sync (would need `asyncio.to_thread`); already-used `httpx` keeps the publisher uniform across all 6 platforms. **Stick with httpx.** |
| Single-PUT path | Always-chunked PUT | Single-PUT is simpler and handles ≤25MB cleanly; chunked is only needed for larger files. Hybrid (threshold-based) is best. |
| In-memory bytes | Streamed file upload via `httpx`'s async generator | Streaming is more memory-efficient but adds complexity; defer until profiling shows >25MB videos in production. |

**Installation:** `uv add --dev respx` (only if not present).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth token refresh | Custom Google OAuth refresh in this phase | Phase 101's token lifecycle | Out of scope; touching it here couples phases. |
| Resumable protocol state machine | Custom retry/resume FSM beyond 308 handling | The 308-Range header IS the state — just parse it | YouTube's protocol is already idempotent; over-engineering creates bugs. |
| Video MIME detection | Hand-rolled magic-byte sniff | Trust `media_type=='video'` + default `video/mp4`, optionally pass through filename `.mp4`/`.mov`/`.webm` | Edge cases are rare; the API accepts `video/*`. |
| Multipart upload variant | The `uploadType=multipart` form | Stick to resumable-only | Resumable handles all sizes; multipart is a special case for ≤5MB single-shot — not worth two code paths. |

**Key insight:** YouTube's resumable protocol is well-specified and idempotent. The risk surface is the *error mapping* (success criterion 2), not the protocol itself.

## Common Pitfalls

### Pitfall 1: Forgetting `uploadType=resumable`
**What goes wrong:** YouTube treats it as simple-upload metadata-only, expects multipart body, returns `400 mediaBodyRequired`.
**Why it happens:** Easy to copy `videos.insert` URL from the reference docs without the upload variant.
**How to avoid:** Use the constant `YOUTUBE_RESUMABLE_INIT_URL` exclusively.
**Warning sign:** Step 1 response is `400` instead of `200`.

### Pitfall 2: Sending `Authorization` to the session URL but stripping `X-Upload-Content-*`
**What goes wrong:** Step 2's session URL is on the same host (`googleapis.com`) — httpx won't strip headers automatically. But if you reuse the dict from Step 1 for Step 2, the `X-Upload-Content-*` headers leak (harmless) and `Content-Type: application/json; charset=UTF-8` overrides the binary content type (BREAKS upload).
**How to avoid:** Build a fresh headers dict for the PUT — only `Authorization`, `Content-Type: video/mp4`, `Content-Length`.

### Pitfall 3: Reading `Location` case-sensitively
**What goes wrong:** Some HTTP clients lower-case header names; assuming `resp.headers["Location"]` may KeyError on `"location"`.
**How to avoid:** httpx's `Headers` is case-insensitive — fine. But document the assumption in tests so future refactors don't break it.

### Pitfall 4: Forgetting `categoryId`
**What goes wrong:** YouTube returns `400 invalidVideoMetadata` if `snippet.title` is set but `categoryId` is missing — the doc says BOTH are required when updating snippet.
**How to avoid:** Always include `categoryId` (default `"22"` — People & Blogs).
**Warning sign:** Init returns `400 invalidVideoMetadata`.

### Pitfall 5: Trusting `privacyStatus` round-trip
**What goes wrong:** Unverified API projects (post-2020-07-28) force every upload to `private`. Code assumes `privacyStatus="public"` request → `public` response and reports the wrong status to the user.
**How to avoid:** Read `status.privacyStatus` FROM the response and surface mismatch.

### Pitfall 6: Chunk size not multiple of 256 KB
**What goes wrong:** YouTube rejects with `400 invalidUploadRequest`.
**How to avoid:** Use a constant that IS a multiple (`8 * 1024 * 1024`); only the *last* chunk may be smaller.

### Pitfall 7: Mock leakage between Step 1 and Step 2
**What goes wrong:** A test that mocks both POST and PUT but routes by URL only may accidentally route the Step-2 PUT (which uses the session URL, NOT the init URL) to the wrong handler.
**How to avoid:** When using `respx`, route by `(method, url)` pair, not URL alone.

## Code Examples

### Example 1 — Two-step happy path (verified shape)

```python
# Source: https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol

# Step 1: initiate
async with httpx.AsyncClient(timeout=60.0) as http:
    init = await http.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(len(video_bytes)),
        },
        json={
            "snippet": {
                "title": "My video",
                "description": "Posted from Pikar",
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        },
    )
    assert init.status_code == 200
    session_url = init.headers["Location"]

    # Step 2: upload bytes
    upload = await http.put(
        session_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_bytes)),
        },
        content=video_bytes,
    )
    assert upload.status_code == 201
    video_id = upload.json()["id"]
```

### Example 2 — Mock-based unit test skeleton (respx)

```python
# tests/unit/test_youtube_publisher.py
import httpx, pytest, respx
from app.social.publisher import SocialPublisher

@pytest.mark.asyncio
@respx.mock
async def test_youtube_resumable_two_step_sequence():
    # Mock: media URL → 1KB bytes
    respx.get("https://supabase.local/test.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    # Mock: init → 200 + Location header
    init_route = respx.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    ).mock(return_value=httpx.Response(
        200, headers={"Location": "https://www.googleapis.com/upload/youtube/v3/videos?upload_id=XYZ"}
    ))
    # Mock: PUT bytes → 201 + video resource
    put_route = respx.put(
        "https://www.googleapis.com/upload/youtube/v3/videos?upload_id=XYZ"
    ).mock(return_value=httpx.Response(
        201, json={"id": "abc123", "status": {"privacyStatus": "public"}}
    ))

    pub = SocialPublisher()
    pub.connector.get_access_token = lambda u, p: "fake_token"

    result = await pub.post_with_media(
        user_id="u1", platform="youtube",
        content="hello", media_urls=["https://supabase.local/test.mp4"],
        media_type="video",
    )
    assert result["success"] is True
    assert result["post_id"] == "abc123"
    assert init_route.call_count == 1
    assert put_route.call_count == 1
    # Verify init body
    sent = init_route.calls[0].request
    body = sent.read().decode()
    assert "source_url" not in body  # SC1 — fictional field gone
    assert "snippet" in body and "categoryId" in body
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Submit fictional `source_url` JSON field | Two-step resumable POST → PUT bytes | YouTube has never supported `source_url`; it was always wrong | Mandatory — current code is 100% non-functional |
| `googleapiclient` MediaFileUpload (sync) | Direct httpx async calls | Pikar is async-throughout (CLAUDE.md) | Avoid sync deps in async paths |

**Deprecated/outdated:**
- The `videos.insert` `multipart` upload variant: still works but resumable supersedes it for any production use — only useful for ≤5MB single-shot.

## Open Questions

1. **What's the realistic file-size distribution for YouTube uploads in Pikar?**
   - What we know: agent-generated videos via Director/Remotion are typically 30s @ 1080p ≈ 8-25MB.
   - What's unclear: whether longer-form content is generated.
   - Recommendation: implement single-PUT happy path + chunked path with a 25MB threshold. If profiling shows files routinely >50MB, add streaming-from-disk in a follow-up.

2. **Does Pikar's Google OAuth flow currently request `youtube.upload` scope?**
   - What we know: `connector.py:66-69` declares it.
   - What's unclear: whether existing connected accounts have it (token issued before scope was added would lack it → `403 insufficientPermissions`).
   - Recommendation: covered by error mapping (`insufficientPermissions` → "re-authenticate"); test asserts the friendly message.

3. **Should `categoryId` be configurable per upload?**
   - What we know: YouTube has ~30 categories; `"22"` (People & Blogs) is universal.
   - What's unclear: whether marketing agent wants to set categories like Education, Howto, Entertainment for SEO.
   - Recommendation: ship with hardcoded `"22"` default; add `category_id` kwarg to the helper for future use; defer wiring it to the agent layer.

4. **Should this phase add OAuth token refresh on 401?**
   - What we know: Phase 101 owns encrypted token reads.
   - What's unclear: whether refresh-on-401 belongs to 101 or here.
   - Recommendation: leave token refresh out of this phase; surface `401 authorizationRequired` with "re-authenticate" remedy. Document as follow-up.

## Sources

### Primary (HIGH confidence)
- **YouTube Resumable Upload Protocol** — https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol (verified: full request shape, headers, response codes, 308 resume, chunk-size rule)
- **videos.insert reference** — https://developers.google.com/youtube/v3/docs/videos/insert (verified: required `part`, OAuth scopes, body schema, 256GB limit, quota cost)
- **YouTube Data API errors** — https://developers.google.com/youtube/v3/docs/errors (verified: error reasons, retry semantics, remediation hints)

### Secondary (MEDIUM confidence)
- Chunk-size 8MB recommendation: 256KB is the protocol minimum unit; 8MB is community-standard balance — verified by Google's own resumable upload examples but not specifically prescribed.

### Tertiary (LOW confidence)
- None — all critical claims have HIGH-confidence official-doc backing.

## Metadata

**Confidence breakdown:**
- API protocol shape: **HIGH** — directly verified against developers.google.com
- Error reasons & remediation: **HIGH** — verified against official errors doc
- Implementation approach: **HIGH** — uses existing httpx pattern in publisher.py
- Chunk size choice (8MB): **MEDIUM** — protocol-compliant but not officially prescribed
- Single-PUT threshold (25MB): **LOW** — Pikar-specific judgment based on typical video sizes; adjustable

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (YouTube Data API v3 is stable; protocol unchanged since ~2018)
