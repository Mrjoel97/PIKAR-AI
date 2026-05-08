---
phase: 105-youtube-resumable-upload
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/publisher.py
  - tests/unit/test_youtube_publisher.py
  - tests/smoke/test_youtube_real_upload.py
  - tests/fixtures/test_video_1mb.mp4
  - pyproject.toml
autonomous: true
requirements: [POST-07]

must_haves:
  truths:
    - "A YouTube upload of a small (≤5MB) MP4 issues exactly one POST to /upload/youtube/v3/videos?uploadType=resumable&part=snippet,status with snippet+status JSON + X-Upload-Content-Type/Length headers, captures the Location response header, then PUTs the video bytes to that session URL with Content-Type: video/* and Content-Length, and returns {success: True, post_id, privacy_status} on 201"
    - "Files larger than 25MB upload via chunked PUT in 8MB (256KB-aligned) chunks with Content-Range headers; intermediate 308 Resume Incomplete responses extract Range header to compute next offset; final 201 returns video.id"
    - "The string `source_url` is ABSENT from the YouTube branch of app/social/publisher.py — verifiable by grep (success criterion 1 of POST-07). The Twitter `source_url` at line 57 is owned by Phase 104 and is out of scope here."
    - "Every failure mode (network interrupt mid-PUT, expired session URL 404, rejected metadata 400, expired token 401, quotaExceeded 403, rate limit 429, backend 5xx, missing Location header) returns structured {success: False, error, reason, retriable, remedy, stage} — never a generic 500 or unhandled exception (success criterion 2 of POST-07)"
    - "A real-API smoke test gated behind PIKAR_RUN_YOUTUBE_SMOKE=1 uploads a 1MB MP4 fixture to a test channel and confirms the returned video_id is a real YouTube video"
    - "A mock-based unit test asserts the two-step request sequence (one POST to init URL, one PUT to session URL) and request shapes (init headers + body, PUT headers + body)"
  artifacts:
    - path: "app/social/publisher.py"
      provides: "Two-step YouTube resumable upload helpers: `_upload_video_youtube`, `_put_chunked`, `_map_youtube_error`, `_default_remedy`; module constants `YOUTUBE_RESUMABLE_INIT_URL`, `YOUTUBE_CHUNK_SIZE`, `YOUTUBE_SINGLE_PUT_THRESHOLD`, `YOUTUBE_DEFAULT_CATEGORY_ID`, `DEFAULT_VIDEO_MIME`. The youtube branch in `post_with_media` (lines 312-331) is replaced to call `_upload_video_youtube` and early-return its structured result."
      contains: "uploadType=resumable&part=snippet,status"
    - path: "tests/unit/test_youtube_publisher.py"
      provides: "12 mock-based unit tests using respx covering: two-step sequence, init/PUT request shape, source_url-absent grep (scoped to YouTube branch), 8 error mapping cases, missing Location header, chunked upload with 308 resume."
      contains: "test_youtube_resumable_two_step_sequence"
    - path: "tests/smoke/test_youtube_real_upload.py"
      provides: "Feature-flagged real-API smoke test (skipped unless PIKAR_RUN_YOUTUBE_SMOKE=1); uploads tests/fixtures/test_video_1mb.mp4 and verifies via post_id presence."
      contains: "PIKAR_RUN_YOUTUBE_SMOKE"
    - path: "tests/fixtures/test_video_1mb.mp4"
      provides: "1MB MP4 fixture for smoke test (one-time creation via ffmpeg)."
      min_bytes: 524288
    - path: "pyproject.toml"
      provides: "respx added to dev/test deps if not already present."
      contains: "respx"
  key_links:
    - from: "app/social/publisher.py:post_with_media (youtube branch)"
      to: "app/social/publisher.py:_upload_video_youtube"
      via: "direct call with token + media_urls[0] + content"
      pattern: "_upload_video_youtube"
    - from: "app/social/publisher.py:_upload_video_youtube"
      to: "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
      via: "httpx.AsyncClient.post with snippet+status JSON and X-Upload-Content-* headers"
      pattern: "uploadType=resumable&part=snippet,status"
    - from: "app/social/publisher.py:_upload_video_youtube"
      to: "session_url from init response Location header"
      via: "httpx.AsyncClient.put with raw video bytes (or chunked PUT for >25MB)"
      pattern: "headers\\.get\\(\"Location\"\\)"
    - from: "app/social/publisher.py:_upload_video_youtube"
      to: "app/social/publisher.py:_map_youtube_error"
      via: "any non-2xx response → structured error dict"
      pattern: "_map_youtube_error"
---

<objective>
Replace the non-functional YouTube upload code in `app/social/publisher.py:312-331` (which posts a fictional `source_url` JSON field to a missing `uploadType=resumable` endpoint, causing every upload to fail) with the proper two-step YouTube Data API v3 resumable upload protocol. Wire structured error responses for every documented failure mode, plus a chunked PUT path for files >25MB with 308-Resume-Incomplete handling.

Purpose: Satisfy ROADMAP Phase 105 success criteria — (1) live YouTube upload completes and the video appears on the user's channel, with a mock-based unit test for the two-step request sequence and a feature-flagged real-API smoke test; (2) all failure modes (network interrupt, expired session, rejected metadata, token expiry, quota, rate limit, server errors) surface structured `{success, error, reason, retriable, remedy}` to the caller instead of a generic 500. Closes POST-07.

Output: Three new helpers (`_upload_video_youtube`, `_put_chunked`, `_map_youtube_error`) plus module constants in `app/social/publisher.py`; the YouTube branch in `post_with_media` rewritten to call them; 12 mock-based unit tests in `tests/unit/test_youtube_publisher.py`; gated smoke test + 1MB MP4 fixture in `tests/smoke/`; `respx` added to dev deps if missing.
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
@.planning/phases/105-youtube-resumable-upload/105-RESEARCH.md
@.planning/phases/105-youtube-resumable-upload/105-CONTEXT.md
@app/social/publisher.py
@app/social/connector.py

<interfaces>
<!-- Key contracts the executor needs. Use these directly — no codebase exploration required. -->

From app/social/publisher.py (current shape — DO NOT regress non-YouTube branches):
```python
class SocialPublisher:
    def __init__(self): ...

    def _get_token_or_error(
        self, user_id: str, platform: str
    ) -> tuple[str | None, dict | None]:
        """Return (token, None) or (None, error_dict)."""

    async def _upload_media_twitter(
        self, http, headers: dict, media_url: str, media_type: str
    ) -> str | None:
        """Upload media to Twitter and return media_id. (Phase 104 will fix this — leave as-is.)"""

    async def post_with_media(
        self, user_id: str, platform: str, content: str,
        media_urls: list[str] | None = None, media_type: str = "image",
    ) -> dict[str, Any]:
        """Returns success: {"success": True, "platform": str, "post_id": str,
                             "media_type": str, "message": str, ...}
        Returns error:   {"error": str, ...} (older shape) OR
                         {"success": False, "error": str, "reason": str,
                          "retriable": bool, "remedy": str} (NEW for YouTube)"""
```

The current YouTube branch (lines 312-331) to be REPLACED:
```python
elif platform == "youtube":
    if not has_media or media_type != "video":
        return {"error": "YouTube requires video content. ..."}
    resp = await http.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?part=snippet,status",                       # MISSING uploadType=resumable
        headers=headers,
        json={
            "snippet": {"title": content[:100], "description": content},
            "status": {"privacyStatus": "public"},
            "source_url": media_urls[0],              # FICTIONAL FIELD — DELETE
        },
    )
```

YouTube Data API v3 resumable upload protocol (verified — see RESEARCH.md API Reference):

Step 1 — Init session:
```
POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
Headers:
  Authorization: Bearer {token}
  Content-Type: application/json; charset=UTF-8
  X-Upload-Content-Type: video/mp4
  X-Upload-Content-Length: <total_bytes>
Body:
  {"snippet": {"title", "description", "categoryId": "22"},
   "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": false}}

→ 200 OK, response header `Location: <session_url>` (this is the URL for Step 2)
```

Step 2 — PUT bytes (single PUT, ≤25MB):
```
PUT {session_url}
Headers:
  Authorization: Bearer {token}
  Content-Type: video/mp4
  Content-Length: <total_bytes>
Body: raw video bytes

→ 201 Created with full Video resource:
   {"kind": "youtube#video", "id": "abc123",
    "snippet": {...}, "status": {"privacyStatus": "public", "uploadStatus": "uploaded"}}
```

Step 2-Alt — Chunked PUT (>25MB), 8MB chunks (multiple of 256KB):
```
PUT {session_url}
Headers:
  Authorization: Bearer {token}
  Content-Length: <chunk_size>
  Content-Type: video/mp4
  Content-Range: bytes <start>-<end>/<total_size>
Body: chunk_bytes

→ Intermediate: 308 Resume Incomplete with `Range: bytes=0-{last_received}` header
→ Final: 201 Created with Video resource
```

Error reasons (mapped in `_map_youtube_error` — see RESEARCH.md Error Mapping table for the complete mapping):
- 400 invalidVideoMetadata / invalidTitle / invalidDescription / invalidCategoryId / invalidTags / mediaBodyRequired → non-retriable, fix-then-retry
- 401 authorizationRequired / youtubeSignupRequired → non-retriable, "re-authenticate"
- 403 quotaExceeded → retriable (24h), "wait for daily quota reset"
- 403 rateLimitExceeded / 429 → retriable, "exponential backoff"
- 403 forbiddenPrivacySetting / forbiddenLicenseSetting / insufficientPermissions / forbidden → non-retriable
- 404 / notFound → retriable, "upload session expired; re-initiate from step 1"
- 5xx backendError / processingFailure → retriable, "exponential backoff"

OAuth scopes (already correct — DO NOT modify):
```python
# app/social/connector.py:63-72 — Google OAuth declares youtube.upload + youtube
```

Module structure to add at top of `app/social/publisher.py`:
```python
YOUTUBE_RESUMABLE_INIT_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)
YOUTUBE_CHUNK_SIZE = 8 * 1024 * 1024      # 8MB, multiple of 256KB
YOUTUBE_SINGLE_PUT_THRESHOLD = 25 * 1024 * 1024  # ≤25MB → single PUT
YOUTUBE_DEFAULT_CATEGORY_ID = "22"        # People & Blogs
DEFAULT_VIDEO_MIME = "video/mp4"
```

Signature for the new helper:
```python
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
    """Two-step resumable upload to YouTube. Returns success or structured error dict."""
```

Project conventions (from CLAUDE.md):
- Python 3.10+ async-throughout (no `asyncio.to_thread` for httpx — already async)
- `uv run` for all commands (NOT raw pip)
- Linter: `uv run ruff check app/ --fix`, `uv run ruff format app/`, `uv run ty check .`
- Pre-commit: no print, no bare except (`except Exception`), no mutable default args, 80%+ docstring coverage
- `make test` runs unit + integration suites
- `pytest-asyncio` already in deps; `respx` likely missing — add via `uv add --dev respx`

Connector behavior already proven by `test_social_connector_security.py` — DO NOT touch `connector.py`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave-0 — Add 12 failing unit tests + smoke test stub + respx dependency</name>
  <files>tests/unit/test_youtube_publisher.py, tests/smoke/test_youtube_real_upload.py, tests/fixtures/test_video_1mb.mp4, pyproject.toml</files>
  <behavior>
    Twelve tests written as `respx`-mocked async tests in `tests/unit/test_youtube_publisher.py`. ALL must FAIL initially (RED state) — they assert behavior that does not yet exist in `publisher.py` (`_upload_video_youtube` is undefined; YouTube `source_url` is still in the source). One gated smoke test stub. One MP4 fixture. `respx` available in dev deps.

    **Test file: `tests/unit/test_youtube_publisher.py`** — module-level functions matching the existing `test_social_connector_security.py` style. Required tests:

    1. **test_youtube_resumable_two_step_sequence**: Mock `respx.get("https://supabase.local/test.mp4")` → 200 with `b"\x00" * 1024`. Mock `respx.post(YOUTUBE_RESUMABLE_INIT_URL)` → 200 with `Location: https://www.googleapis.com/upload/youtube/v3/videos?upload_id=XYZ`. Mock `respx.put` (use `re.compile(r"upload_id=XYZ")`) → 201 with `{"id": "abc123", "status": {"privacyStatus": "public", "uploadStatus": "uploaded"}}`. Patch `pub.connector.get_access_token = lambda *a, **kw: "fake_token"`. Assert: `result["success"] is True`, `result["post_id"] == "abc123"`, init route called exactly once, PUT route called exactly once.

    2. **test_youtube_init_request_shape**: Same mocks. After call, inspect `init_route.calls[0].request`:
       - Headers contain `Authorization: Bearer fake_token`, `Content-Type: application/json; charset=UTF-8`, `X-Upload-Content-Type: video/mp4`, `X-Upload-Content-Length: 1024`.
       - JSON body has `snippet.title` (≤100 chars), `snippet.description`, `snippet.categoryId == "22"`, `status.privacyStatus`, `status.selfDeclaredMadeForKids == False`.
       - JSON body does NOT contain key `"source_url"`.
       - URL exactly equals `https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` (the `YOUTUBE_RESUMABLE_INIT_URL` constant).

    3. **test_youtube_put_request_shape**: After successful flow, inspect `put_route.calls[0].request`:
       - Headers: `Authorization: Bearer fake_token`, `Content-Type: video/mp4`, `Content-Length: 1024`.
       - Headers do NOT contain `X-Upload-Content-Type` or `X-Upload-Content-Length` or `application/json` (Pitfall 2 — fresh dict, no leakage).
       - Body bytes equal the 1024 zero bytes from the media URL fetch.

    4. **test_youtube_no_source_url_in_codebase**: Scoped grep — read `app/social/publisher.py`, slice from `"# ----- YOUTUBE -----"` to the next `else:` (line ~333), assert `"source_url"` not in that slice. (Phase 104 owns Twitter `source_url` at line 57; this test must NOT couple phases.) Sample assertion:
       ```python
       src = Path("app/social/publisher.py").read_text(encoding="utf-8")
       yt_start = src.index("# ----- YOUTUBE -----")
       yt_end = src.index("\n        else:", yt_start)
       assert "source_url" not in src[yt_start:yt_end]
       ```

    5. **test_youtube_error_400_invalid_metadata**: Init mock returns `400` with `{"error": {"errors": [{"reason": "invalidTitle"}], "message": "Invalid title"}}`. Assert: `result["success"] is False`, `result["reason"] == "invalidTitle"`, `result["retriable"] is False`, `result["remedy"]` contains `"non-empty video title"`, `result["stage"] == "initiate"`.

    6. **test_youtube_error_401_token_expired**: Init mock returns `401` `{"error": {"errors": [{"reason": "authorizationRequired"}], "message": "Login required"}}`. Assert: `retriable=False`, `remedy` contains `"re-authenticate"`.

    7. **test_youtube_error_403_quota_exceeded**: Init mock returns `403` `{"error": {"errors": [{"reason": "quotaExceeded"}], "message": "Quota exceeded"}}`. Assert: `retriable=True`, `remedy` contains `"24h"` or `"daily quota"`.

    8. **test_youtube_error_404_expired_session**: Init succeeds (200 + Location). PUT mock returns `404` `{"error": {"errors": [{"reason": "notFound"}], "message": "Upload session not found"}}`. Assert: `retriable=True`, `remedy` contains `"re-initiate"` or `"session expired"`, `stage == "upload"`.

    9. **test_youtube_error_5xx_transient**: Init returns `503`. Assert: `retriable=True`, `remedy` contains `"transient"` or `"retry with backoff"`.

    10. **test_youtube_network_interrupt_during_put**: Init succeeds. PUT route mocked with `side_effect=httpx.RequestError("connection reset")`. Assert: `result["success"] is False`, `result["reason"]` is set, `result["retriable"] is True`, `remedy` contains `"retry"`. (The `_upload_video_youtube` body MUST `try/except httpx.RequestError` around the PUT — Task 2 implements this.)

    11. **test_youtube_missing_location_header**: Init returns 200 with empty headers (no `Location`). Assert: `success=False`, `reason="missing_location_header"`, `retriable=True`.

    12. **test_youtube_chunked_upload_resume_path**: Mock media URL → 30MB of bytes (`b"\x00" * (30 * 1024 * 1024)` — fits in CI memory). Init succeeds. PUT route configured with side-effect list returning in order: `308 Range: bytes=0-8388607`, `308 Range: bytes=0-16777215`, `308 Range: bytes=0-25165823`, `201 {"id": "chunked_video_id", "status": {"privacyStatus": "public"}}`. Assert: `result["success"] is True`, `post_id == "chunked_video_id"`, `put_route.call_count == 4`, each `Content-Range` header is correctly formatted (`bytes <start>-<end>/31457280`), each non-final chunk size equals 8388608 bytes (8MB), final chunk is the remainder (6291456 bytes).

    All tests use `pytest.mark.asyncio` and `@respx.mock` decorator. Import `from app.social.publisher import SocialPublisher, YOUTUBE_RESUMABLE_INIT_URL` (the constant import will FAIL until Task 2 — the desired RED state).

    **Smoke test: `tests/smoke/test_youtube_real_upload.py`** — gated:
    ```python
    """Real-API smoke test for YouTube resumable upload.

    Skipped unless PIKAR_RUN_YOUTUBE_SMOKE=1 is set. Requires:
      - YOUTUBE_TEST_USER_ID env var pointing to a Pikar user with a connected YouTube test channel
      - YOUTUBE_TEST_MEDIA_URL env var pointing to a publicly fetchable URL of the 1MB MP4 fixture
        (e.g., a Supabase Storage signed URL)
    """
    import os
    import pytest
    from pathlib import Path

    pytestmark = pytest.mark.skipif(
        os.environ.get("PIKAR_RUN_YOUTUBE_SMOKE") != "1",
        reason="Set PIKAR_RUN_YOUTUBE_SMOKE=1 to run real-API YouTube smoke test",
    )

    @pytest.mark.asyncio
    async def test_real_upload_to_test_channel():
        from app.social.publisher import get_social_publisher

        user_id = os.environ["YOUTUBE_TEST_USER_ID"]
        media_url = os.environ["YOUTUBE_TEST_MEDIA_URL"]
        fixture = Path(__file__).parent.parent / "fixtures" / "test_video_1mb.mp4"
        assert fixture.exists(), f"Missing fixture: {fixture}"

        pub = get_social_publisher()
        result = await pub.post_with_media(
            user_id=user_id, platform="youtube",
            content="Pikar smoke test upload — DELETE ME",
            media_urls=[media_url], media_type="video",
        )
        assert result.get("success") is True, f"Upload failed: {result}"
        assert result.get("post_id"), "post_id missing from result"
        # Manual verification at https://youtube.com/watch?v={post_id}
    ```

    **Fixture: `tests/fixtures/test_video_1mb.mp4`** — generate a real ~1MB MP4 (NOT zero-bytes). Use ffmpeg if available:
    ```bash
    ffmpeg -y -f lavfi -i testsrc=duration=10:size=640x360:rate=30 -c:v libx264 -pix_fmt yuv420p -b:v 800k tests/fixtures/test_video_1mb.mp4
    ```
    If ffmpeg is unavailable, document this in the task summary; smoke test will skipif fixture missing. The unit tests do NOT depend on this fixture — only the smoke test does.

    **Dependency: `pyproject.toml`** — verify `respx` available:
    ```bash
    uv pip show respx
    ```
    If absent: `uv add --dev respx` (modifies `pyproject.toml` and `uv.lock`).

    **Verification of RED state**: `uv run pytest tests/unit/test_youtube_publisher.py -x 2>&1 | tail -40`. Expected: `ImportError: cannot import name 'YOUTUBE_RESUMABLE_INIT_URL'` OR all 12 tests fail with assertion/attribute errors.

    Commit message: `test(105-01): add failing unit + smoke tests for YouTube resumable upload (POST-07)`.
  </behavior>
  <action>
    1. Check respx availability: `uv pip show respx`. If absent, run `uv add --dev respx`.

    2. Create `tests/unit/test_youtube_publisher.py` with the 12 tests above. Patterns:
       - Module-level helper `_make_publisher()` returning a `SocialPublisher()` with `pub.connector.get_access_token = lambda *a, **kw: "fake_token"`.
       - For test 4, use the scoped-grep snippet (slice between `"# ----- YOUTUBE -----"` and the next `else:` in the file) — DO NOT do a whole-file grep (couples to Phase 104).
       - For test 12, derive expected chunk count: `expected_chunks = -(-total // YOUTUBE_CHUNK_SIZE)` (= 4 for 30MB).
       - For test 10's exception path: `respx.put(re.compile(r"upload_id=XYZ")).mock(side_effect=httpx.RequestError("connection reset"))`.
       - For all error tests, use the exact YouTube error JSON shape: `{"error": {"errors": [{"reason": "<reason>"}], "message": "<msg>", "code": <code>}}`.

    3. Create `tests/smoke/test_youtube_real_upload.py` with the gated structure above.

    4. Generate `tests/fixtures/test_video_1mb.mp4` via ffmpeg if available; if not, document the gap in the task summary and proceed (unit tests are independent of the fixture).

    5. Verify RED state: `uv run pytest tests/unit/test_youtube_publisher.py -x 2>&1 | tail -40`. Confirm tests fail because `YOUTUBE_RESUMABLE_INIT_URL` cannot be imported OR the YouTube branch still contains `source_url`.

    6. Stage and commit: `tests/unit/test_youtube_publisher.py`, `tests/smoke/test_youtube_real_upload.py`, `tests/fixtures/test_video_1mb.mp4` (if generated), `pyproject.toml`, `uv.lock`. Use the commit message above.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_youtube_publisher.py --collect-only 2>&amp;1 | tail -20 ; uv run pytest tests/unit/test_youtube_publisher.py -x 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    `tests/unit/test_youtube_publisher.py` exists with 12 collected tests under expected names. ALL 12 fail with import errors (constant/symbol missing) or assertion errors. `tests/smoke/test_youtube_real_upload.py` exists and is properly skipif-gated (passes collection). `respx` is available in the dev environment. `pyproject.toml` + `uv.lock` updated if respx was added. RED state confirmed; the implementation in Task 2 will turn them GREEN. Commit `test(105-01): add failing unit + smoke tests for YouTube resumable upload (POST-07)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wave-1 — Implement two-step resumable helpers + replace publisher.py:312-331</name>
  <files>app/social/publisher.py</files>
  <behavior>
    After this task, all 12 tests from Task 1 are GREEN. The fictional `source_url` field is GONE from the YouTube branch of `publisher.py` (test 4 passes via scoped slice). All other publisher branches (twitter, linkedin, facebook, instagram, tiktok) are UNCHANGED — they have their own dedicated phases (104, 103, 107, etc.). The Twitter `source_url` at line 57 belongs to Phase 104 — DO NOT remove it here.

    **Code added at the top of `app/social/publisher.py`** (after the `import logging` block, before `class SocialPublisher`):

    ```python
    # YouTube resumable upload constants — see RESEARCH.md
    YOUTUBE_RESUMABLE_INIT_URL = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )
    YOUTUBE_CHUNK_SIZE = 8 * 1024 * 1024            # 8MB, multiple of 256KB
    YOUTUBE_SINGLE_PUT_THRESHOLD = 25 * 1024 * 1024  # ≤25MB → single PUT
    YOUTUBE_DEFAULT_CATEGORY_ID = "22"               # People & Blogs
    DEFAULT_VIDEO_MIME = "video/mp4"
    ```

    **New module-level helpers** (after constants, before `class SocialPublisher`):

    `_default_remedy(code: int) -> tuple[str, bool]`:
    ```python
    def _default_remedy(code: int) -> tuple[str, bool]:
        """Fallback (remedy, retriable) for unrecognized YouTube error codes."""
        if code == 401:
            return ("re-authenticate the YouTube account", False)
        if code == 404:
            return ("upload session expired; re-initiate from step 1", True)
        if code == 429:
            return ("rate-limited; retry with backoff", True)
        if 500 <= code < 600:
            return ("transient YouTube server error; retry with backoff", True)
        if 400 <= code < 500:
            return ("non-retriable client error; fix request and retry", False)
        return ("unexpected response; retry once then escalate", True)
    ```

    `_map_youtube_error(resp, *, stage: str, session_url: str | None = None) -> dict[str, Any]` — extracts `error.errors[0].reason` and `error.message` from the JSON body; falls back to `_default_remedy(status_code)` when reason is unknown. Returns `{"success": False, "error": str, "reason": str, "retriable": bool, "remedy": str, "stage": str}`. The full reason→(remedy, retriable) mapping must include all 16 reasons listed in RESEARCH.md "Error Mapping" section. Wrap JSON parsing in `try/except Exception` (NOT bare except) so non-JSON 5xx responses still return a structured error.

    **New methods on `SocialPublisher`** (placed after `_upload_media_twitter`, before `post_text`):

    `_upload_video_youtube` — signature in the interfaces block. Implementation per RESEARCH.md "Implementation Approach":
    1. **Download bytes** via `http.stream("GET", media_url)`. Read fully into memory (`await src.aread()`). Wrap in `try/except httpx.RequestError as exc` → return `{success:False, error:f"Network error fetching media: {exc}", reason:"media_fetch_network", retriable:True, remedy:"retry now", stage:"download"}`. If status != 200 → `{success:False, error:..., reason:"media_fetch_failed", retriable:True, remedy:"verify the media URL is accessible and retry", stage:"download"}`.
    2. **Init resumable session** — POST to `YOUTUBE_RESUMABLE_INIT_URL` with init headers + metadata JSON. On non-200 → return `_map_youtube_error(init_resp, stage="initiate")`. Extract `session_url = init_resp.headers.get("Location")`; if missing → `{success:False, error:"YouTube did not return a session URL", reason:"missing_location_header", retriable:True, remedy:"retry now", stage:"initiate"}`.
    3. **PUT bytes**:
       - If `total_size <= YOUTUBE_SINGLE_PUT_THRESHOLD` → single PUT with FRESH headers dict containing only `Authorization`, `Content-Type`, `Content-Length` (Pitfall 2 — no leakage from init dict). On 201 → return `{success:True, platform:"youtube", post_id:data.get("id"), privacy_status:data.get("status",{}).get("privacyStatus")}`; else → `_map_youtube_error(put_resp, stage="upload", session_url=session_url)`. Wrap PUT in `try/except httpx.RequestError as exc` → `{success:False, error:..., reason:"network_error", retriable:True, remedy:"retry now", stage:"upload"}`.
       - Else → call `await self._put_chunked(http, token, session_url, video_bytes, total_size, mime_type)`.

    `_put_chunked` — implements 8MB chunked PUT loop with 308 Resume Incomplete handling per RESEARCH.md. While `offset < total_size`:
    - `end = min(offset + YOUTUBE_CHUNK_SIZE, total_size) - 1`; `chunk = video_bytes[offset:end+1]`
    - PUT with headers `{Authorization, Content-Length: len(chunk), Content-Type: mime_type, Content-Range: f"bytes {offset}-{end}/{total_size}"}`. Wrap in try/except httpx.RequestError → structured network error.
    - On 201 → return success dict (extract `id` and `privacy_status`).
    - On 308 → parse `Range` header (`Range: bytes=0-N`), extract `received_upper = int(range_hdr.split("-")[-1])`, set `offset = received_upper + 1`. Use `try/except (ValueError, IndexError)` falling back to `offset = end + 1`.
    - On any other status → return `_map_youtube_error(resp, stage="upload_chunk", session_url=session_url)`.

    After the loop terminates without 201 → return `{success:False, error:"Upload finished without 201", reason:"no_terminal_response", retriable:True, remedy:"retry now", stage:"upload_chunk"}`.

    **Replace `app/social/publisher.py:312-331`** (the YouTube branch in `post_with_media`):
    ```python
    # ----- YOUTUBE -----
    elif platform == "youtube":
        if not has_media or media_type != "video":
            return {
                "error": "YouTube requires video content. "
                "Provide a video URL with media_type='video'."
            }
        result = await self._upload_video_youtube(
            http, token, media_urls[0],
            title=content[:100],
            description=content,
            privacy_status="public",
        )
        if result.get("success"):
            return {
                **result,
                "media_type": media_type,
                "message": "Posted to youtube successfully",
            }
        # Structured error — pass through with the original error fields
        return result
    ```
    This early-returns from the YouTube branch (before the unified `if resp.status_code in [200, 201, 202]:` block at line 337).

    **Constraints**:
    - DO NOT modify any other platform branch (twitter, linkedin, facebook, instagram, tiktok) or `_upload_media_twitter`. Phase 104 owns Twitter.
    - DO NOT modify `app/social/connector.py` — scopes already correct.
    - DO NOT add OAuth refresh logic — Phase 101 owns token lifecycle.
    - DO NOT use `print`. Use `logger`. No bare `except:` — always `except Exception` (or specific exceptions like `httpx.RequestError`).
    - All new helpers/methods must have docstrings (interrogate hook requires 80%+).
    - Type hints reference `httpx.AsyncClient` as a forward-ref string (e.g., `http: "httpx.AsyncClient"`) so we don't need to move the inside-function `import httpx` to module scope.

    **Verify GREEN state**:
    ```bash
    uv run pytest tests/unit/test_youtube_publisher.py -x
    uv run ruff check app/social/publisher.py --fix
    uv run ruff format app/social/publisher.py
    uv run ty check app/social/publisher.py
    ```
    All 12 unit tests GREEN. Lint and type check clean.

    Commit message: `feat(105-01): replace YouTube source_url stub with two-step resumable upload (POST-07)`.
  </behavior>
  <action>
    1. Edit `app/social/publisher.py`:
       a. Add the 5 module constants above `class SocialPublisher`.
       b. Add module-level `_default_remedy` and `_map_youtube_error` helpers.
       c. Add `_upload_video_youtube` and `_put_chunked` async methods on `SocialPublisher` (after `_upload_media_twitter`, before `post_text`).
       d. Replace lines 312-331 (the YouTube branch) with the new dispatch.
       e. Leave the inside-function `import httpx` at line 106 alone — minimize diff.

    2. Run quality gates (in order — fix any issues before proceeding):
       ```bash
       uv run pytest tests/unit/test_youtube_publisher.py -x 2>&1 | tail -30
       uv run ruff check app/social/publisher.py --fix
       uv run ruff format app/social/publisher.py
       uv run ty check app/social/publisher.py
       ```
       All 12 tests GREEN. Lint and type check clean.

    3. Run regression check on the broader unit suite (exclude the new file to isolate signal):
       ```bash
       uv run pytest tests/unit/ -x --ignore=tests/unit/test_youtube_publisher.py 2>&1 | tail -10
       ```
       Existing tests should be unaffected — only the YouTube branch changed.

    4. Stage `app/social/publisher.py`. Commit with the message above.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_youtube_publisher.py -x 2>&amp;1 | tail -30 ; uv run ruff check app/social/publisher.py 2>&amp;1 | tail -5 ; echo "--YT-SOURCE_URL CHECK--" ; uv run python -c "from pathlib import Path; src = Path('app/social/publisher.py').read_text(encoding='utf-8'); s = src.index('# ----- YOUTUBE -----'); e = src.index('\n        else:', s); assert 'source_url' not in src[s:e], 'FAIL: source_url still in YouTube branch'; print('OK: source_url absent from YouTube branch')"</automated>
  </verify>
  <done>
    All 12 tests in `tests/unit/test_youtube_publisher.py` are GREEN. `_upload_video_youtube`, `_put_chunked`, `_map_youtube_error`, `_default_remedy` exist in `app/social/publisher.py`. The YouTube branch (originally lines 312-331) now calls `_upload_video_youtube` and `source_url` is absent from that branch (the verify command's grep confirms). Other platform branches unchanged. `ruff check`, `ruff format`, `ty check` all clean. The other unit tests in `tests/unit/` still pass (no regressions). Commit `feat(105-01): replace YouTube source_url stub with two-step resumable upload (POST-07)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wave-2 — Full suite + manual smoke verification + lint sweep</name>
  <files>(no new files — verification only; commits any final lint touch-ups)</files>
  <behavior>
    Run the full project test suite to confirm no cross-cutting regressions. Run lint + type check on all changed files. Document the smoke-test outcome.

    1. **Full unit suite**:
       ```bash
       uv run pytest tests/unit/ 2>&1 | tail -20
       ```
       Expected: all tests pass (existing + 12 new). If any unrelated test fails, investigate and either fix (if caused by Task 2) or document as pre-existing breakage in the summary.

    2. **Project lint sweep**:
       ```bash
       uv run ruff check app/ tests/unit/test_youtube_publisher.py tests/smoke/test_youtube_real_upload.py
       uv run ruff format --check app/social/publisher.py tests/unit/test_youtube_publisher.py tests/smoke/test_youtube_real_upload.py
       ```
       Both must exit 0. If `ruff format --check` fails, run `uv run ruff format <file>` and re-commit as a follow-up.

    3. **Type check**:
       ```bash
       uv run ty check app/social/publisher.py
       ```
       Must exit 0.

    4. **Manual smoke (CHECKPOINT — operator action)**:
       The smoke test is gated and requires real credentials. The executor MUST attempt one of:
       - **(Preferred)** Set `PIKAR_RUN_YOUTUBE_SMOKE=1`, `YOUTUBE_TEST_USER_ID=<a Pikar user id with a connected YouTube test channel>`, `YOUTUBE_TEST_MEDIA_URL=<publicly fetchable URL of the 1MB MP4>`, then run `uv run pytest tests/smoke/test_youtube_real_upload.py -v`. Confirm the printed `video_id` resolves at `https://youtube.com/watch?v={video_id}` (manual visual check). Delete the test video from the channel afterward.
       - **(Fallback)** If no test channel/credentials are available locally, document this in the SUMMARY as "Smoke test deferred — requires CI secrets". The unit tests + grep already cover POST-07 SC1 sequence assertions; the live upload is a UAT step.

    5. **No new code commit expected** — Task 3 is verification only. If `ruff format --check` flagged whitespace, commit the fix:
       ```
       chore(105-01): ruff format pass over publisher.py and tests
       ```
       Otherwise no additional commit.

    6. **Frontmatter validation** of this plan (sanity check after the executor reads STATE.md):
       ```bash
       node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" frontmatter validate .planning/phases/105-youtube-resumable-upload/105-01-resumable-upload-PLAN.md --schema plan
       node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" verify plan-structure .planning/phases/105-youtube-resumable-upload/105-01-resumable-upload-PLAN.md
       ```
       Both should report `valid: true`.
  </behavior>
  <action>
    1. Run `uv run pytest tests/unit/ 2>&1 | tail -20`. If any FAIL, diagnose: was the failure caused by changes to `publisher.py` (then fix in Task 2 amendment) or pre-existing (document in summary)?

    2. Run `uv run ruff check app/ tests/unit/test_youtube_publisher.py tests/smoke/test_youtube_real_upload.py 2>&1 | tail -10`.

    3. Run `uv run ruff format --check app/social/publisher.py tests/unit/test_youtube_publisher.py tests/smoke/test_youtube_real_upload.py 2>&1 | tail -10`. Apply formatting if check fails.

    4. Run `uv run ty check app/social/publisher.py 2>&1 | tail -10`.

    5. Smoke test (gated, optional): if `YOUTUBE_TEST_USER_ID` and `YOUTUBE_TEST_MEDIA_URL` are present in env, run `PIKAR_RUN_YOUTUBE_SMOKE=1 uv run pytest tests/smoke/test_youtube_real_upload.py -v 2>&1 | tail -20`. Otherwise mark the smoke as deferred in summary.

    6. Validate plan frontmatter via gsd-tools (commands above).

    7. Write the plan summary to `.planning/phases/105-youtube-resumable-upload/105-01-resumable-upload-SUMMARY.md` (per `<output>` block below).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/ 2>&amp;1 | tail -5 ; uv run ruff check app/social/publisher.py 2>&amp;1 | tail -3 ; uv run ty check app/social/publisher.py 2>&amp;1 | tail -3</automated>
  </verify>
  <done>
    Full unit suite passes. ruff check, ruff format --check, ty check all clean for `app/social/publisher.py`, `tests/unit/test_youtube_publisher.py`, `tests/smoke/test_youtube_real_upload.py`. Smoke test either passed live (preferred) or is documented as deferred for CI/UAT in the SUMMARY. Plan frontmatter validates. SUMMARY.md written.
  </done>
</task>

</tasks>

<verification>
End-to-end: `uv run pytest tests/unit/ -x` → all tests GREEN (existing + 12 new). `uv run ruff check app/social/publisher.py` clean. `uv run ty check app/social/publisher.py` clean.

Scoped grep verification (POST-07 SC1):
```bash
uv run python -c "from pathlib import Path; src = Path('app/social/publisher.py').read_text(encoding='utf-8'); s = src.index('# ----- YOUTUBE -----'); e = src.index('\n        else:', s); assert 'source_url' not in src[s:e]; print('OK')"
```

Manual smoke (deferred to phase-level UAT if no test creds locally): with `PIKAR_RUN_YOUTUBE_SMOKE=1` set, upload `tests/fixtures/test_video_1mb.mp4` to a real test channel and confirm the returned `post_id` resolves as a real YouTube video.
</verification>

<success_criteria>
- `app/social/publisher.py` defines `YOUTUBE_RESUMABLE_INIT_URL`, `YOUTUBE_CHUNK_SIZE`, `YOUTUBE_SINGLE_PUT_THRESHOLD`, `YOUTUBE_DEFAULT_CATEGORY_ID`, `DEFAULT_VIDEO_MIME` at module scope.
- `app/social/publisher.py` defines `_default_remedy`, `_map_youtube_error` at module scope and `_upload_video_youtube`, `_put_chunked` on `SocialPublisher`.
- The YouTube branch in `post_with_media` calls `_upload_video_youtube` and the literal string `"source_url"` is ABSENT from that branch.
- `_map_youtube_error` covers all 16 reasons in RESEARCH.md's failure-mode table; unknown reasons fall back to `_default_remedy(status_code)`.
- 12 new unit tests in `tests/unit/test_youtube_publisher.py` pass; all 8 error-mapping tests assert the documented `(retriable, remedy)` pair.
- The chunked PUT path correctly handles `308 Resume Incomplete`, parses the `Range` header, and emits the expected number of PUTs for 30MB input.
- A gated smoke test exists at `tests/smoke/test_youtube_real_upload.py` — collection passes, runs only when `PIKAR_RUN_YOUTUBE_SMOKE=1`.
- `respx` is installed in dev deps (added if missing).
- `ruff check`, `ruff format --check`, `ty check` all clean for changed files.
- Other platform branches (twitter, linkedin, facebook, instagram, tiktok) and `_upload_media_twitter` are byte-identical (only YouTube branch changed).
</success_criteria>

<output>
After completion, create `.planning/phases/105-youtube-resumable-upload/105-01-resumable-upload-SUMMARY.md` documenting:
- Exact line numbers of the new helpers and the replaced YouTube branch
- Whether `respx` was already present or added
- Whether the 1MB MP4 fixture was generated (and how) or deferred
- Whether the gated smoke test was run live (with `video_id` redacted) or deferred to CI/UAT
- Test count delta (existing N → existing N + 12 GREEN)
- Any deviations from this plan (especially: did test 4 need scoped-slice instead of whole-file grep — yes/no)
- Open follow-ups (per RESEARCH.md): streaming-from-disk for >50MB videos; OAuth token refresh on 401 (Phase 101 owns)
</output>
