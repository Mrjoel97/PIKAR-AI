---
phase: 107-facebook-video-resumable-upload
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/publisher.py
  - tests/unit/social/__init__.py
  - tests/unit/social/conftest.py
  - tests/unit/social/test_publisher_facebook.py
  - pyproject.toml
autonomous: true
requirements: [POST-09]

must_haves:
  truths:
    - "Calling SocialPublisher.post_with_media(platform='facebook', media_type='video', media_urls=[mp4_url]) issues exactly three POSTs to https://graph.facebook.com/v23.0/{PAGE_ID}/videos in order: upload_phase=start, upload_phase=transfer (one or more), upload_phase=finish — verified by mock-based unit test on a 2-chunk path"
    - "When the first transfer chunk returns HTTP 500, the same chunk is POSTed exactly once more (single retry); on second 5xx the call surfaces a structured FacebookUploadError with phase='transfer' and the upload_session_id"
    - "The string 'file_url' is absent from app/social/ after this plan lands (verifiable by grep)"
    - "All Facebook URL constructions in app/social/publisher.py interpolate the FB_GRAPH_API_VERSION='v23.0' constant (no remaining hardcoded v18.0 in publisher.py)"
    - "Posting a non-video Facebook payload (image or text-only) keeps working — the existing /me/photos and /me/feed branches are unchanged in behavior"
  artifacts:
    - path: "app/social/publisher.py"
      provides: "Module-level FB_GRAPH_API_VERSION constant; FacebookUploadError exception; _post_chunk_with_retry helper; _upload_facebook_video helper performing three-phase chunked upload; _get_facebook_page_context helper resolving (page_id, page_access_token) from connected_accounts; Facebook video sub-branch in post_with_media rewired to use these helpers"
      contains: "_upload_facebook_video"
    - path: "tests/unit/social/__init__.py"
      provides: "Empty package marker for the new test directory"
      contains: ""
    - path: "tests/unit/social/conftest.py"
      provides: "Shared fixtures: fake page_id, fake page_access_token, sample MP4 bytes, helper to extract upload_phase from a respx-captured multipart request"
      contains: "fake_page_id"
    - path: "tests/unit/social/test_publisher_facebook.py"
      provides: "Unit tests covering POST-09 SC-1 (three-phase 2-chunk happy path), SC-2 (retry-once on 5xx, structured error after retry exhausted), and the static grep check that file_url is absent from app/social/"
      contains: "test_video_upload_three_phase_two_chunks"
    - path: "pyproject.toml"
      provides: "respx added to [dev] dependencies for httpx mocking"
      contains: "respx"
  key_links:
    - from: "app/social/publisher.py:post_with_media (Facebook video branch)"
      to: "app/social/publisher.py:_upload_facebook_video"
      via: "direct call after resolving (page_id, page_access_token) via _get_facebook_page_context"
      pattern: "_upload_facebook_video"
    - from: "app/social/publisher.py:_upload_facebook_video"
      to: "app/social/publisher.py:_post_chunk_with_retry"
      via: "wraps each phase=transfer POST"
      pattern: "_post_chunk_with_retry"
    - from: "app/social/publisher.py:_get_facebook_page_context"
      to: "connected_accounts table row (platform='facebook')"
      via: "SocialConnector.client.table('connected_accounts').select() + _decrypt_token on access_token + read platform_user_id as page_id"
      pattern: "platform_user_id"
    - from: "tests/unit/social/test_publisher_facebook.py"
      to: "app/social/publisher.py via respx mocking of graph.facebook.com"
      via: "@respx.mock decorator on async test functions"
      pattern: "respx.post"
---

<objective>
Replace the broken Facebook video upload at app/social/publisher.py:175-183 (which POSTs JSON `{"description": ..., "file_url": ...}` to `/me/videos`) with the documented three-phase resumable chunked upload to `/{PAGE_ID}/videos` using `multipart/form-data`. Wrap each transfer chunk in a single-retry helper. Standardize on Graph API v23.0. Add the SC-1 and SC-2 mock-based unit tests on a Wave-0-scaffolded `tests/unit/social/` directory.

Purpose: Satisfy ROADMAP Phase 107 success criteria 1 and 2 (POST-09). Today's code path silently fails — the API silently ignores `file_url` on `/me/videos` and v18.0 expired 2026-01-26. After this plan, the wire shape matches Meta's documented contract, the broken parameter is grep-absent, and unit tests assert the three-phase shape, retry-once behavior, and structured-error-after-exhaustion.

Output: An async `_upload_facebook_video(http, page_id, page_access_token, video_bytes, description, title=None, api_version="v23.0") -> dict[str, Any]` helper, a `_post_chunk_with_retry` helper, a `FacebookUploadError` exception, and a `_get_facebook_page_context(user_id)` helper — all in `app/social/publisher.py`. Three new unit tests + one static-grep test in `tests/unit/social/test_publisher_facebook.py`. `respx` added to dev deps. The `[Facebook][video]` sub-branch of `post_with_media` resolves (page_id, page_token) from `connected_accounts`, fetches the media URL into bytes, and delegates to `_upload_facebook_video`.

This plan has a HARD dependency on the storage-side fix in Plan 107-02 (Page-token capture during OAuth callback): `_get_facebook_page_context` reads `connected_accounts.platform_user_id` and the Page token from the same row. Plan 107-02 must land FIRST (Wave 1) so this plan (Wave 2) has data to read. The unit tests in this plan can run in isolation (they mock the connector entirely) but live posting will not work until 107-02 also lands.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/107-facebook-video-resumable-upload/107-CONTEXT.md
@.planning/phases/107-facebook-video-resumable-upload/107-RESEARCH.md
@app/social/publisher.py
@app/social/connector.py
@supabase/migrations/0010_connected_accounts.sql

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->
<!-- Use these directly — no codebase exploration needed. -->

From app/social/connector.py (existing — DO NOT regress):
```python
class SocialConnector:
    client: Client  # Supabase service client (self.client.table("connected_accounts"))

    def get_access_token(self, user_id: str, platform: str) -> str | None:
        """Return decrypted access_token for an active connection, or None.
        Auto-refreshes on expiry via _refresh_token. Already exists."""

    def _decrypt_token(self, encrypted: str | None) -> str | None:
        """Fernet-decrypt or return None. Already exists."""

    def _encrypt_token(self, raw: str | None) -> str | None:
        """Fernet-encrypt or return None. Raises RuntimeError if encryption not configured."""
```

From app/social/publisher.py (current shape — TARGETED edits only):
```python
class SocialPublisher:
    def __init__(self):
        self.connector = get_social_connector()

    def _get_token_or_error(self, user_id: str, platform: str) -> tuple[str | None, dict | None]:
        """Returns (token, None) on success or (None, {"error": ...}) on failure."""

    async def post_with_media(
        self,
        user_id: str,
        platform: str,
        content: str,
        media_urls: list[str] | None = None,
        media_type: str = "image",
    ) -> dict[str, Any]:
        """The Facebook video sub-branch is at lines 175-183 today. Only that
        sub-branch changes in this plan. Other branches (twitter/linkedin/
        instagram/photos/feed) are unchanged."""
```

From connected_accounts schema (supabase/migrations/0010_connected_accounts.sql):
```sql
CREATE TABLE connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    platform TEXT NOT NULL,           -- 'facebook' for this plan
    platform_user_id TEXT,            -- Page ID (set by Plan 107-02)
    platform_username TEXT,           -- Page name (set by Plan 107-02)
    access_token TEXT NOT NULL,       -- Fernet-encrypted Page access token (set by Plan 107-02)
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',      -- Plan 107-02 stashes user_token + available_pages here
    status TEXT,                      -- 'active' for queries
    UNIQUE(user_id, platform)
);
```

Meta API v23.0 contract (from RESEARCH.md, verified against Meta v25.0 reference):
```
POST https://graph.facebook.com/v23.0/{PAGE_ID}/videos
Content-Type: multipart/form-data

# Phase 1: start
fields: upload_phase=start, access_token=<page_token>, file_size=<int>
response: {"upload_session_id": "...", "video_id": "...", "start_offset": "0", "end_offset": "5242880"}

# Phase 2: transfer (loop until start_offset == end_offset)
fields: upload_phase=transfer, access_token=<page_token>, upload_session_id=<id>,
        start_offset=<int>, video_file_chunk=<binary slice>
response: {"start_offset": "...", "end_offset": "..."}

# Phase 3: finish
fields: upload_phase=finish, access_token=<page_token>, upload_session_id=<id>,
        description=<caption>, [title=<optional>]
response: {"success": true}
```
</interfaces>

<existing_test_patterns>
The repo uses pytest-asyncio + AsyncMock heavily. `respx` is NEW for this phase — add it to `[dev]` deps in pyproject.toml. Sample respx idiom:

```python
import httpx
import pytest
import respx
from unittest.mock import patch

@pytest.mark.asyncio
@respx.mock
async def test_video_upload_three_phase_two_chunks(fake_page_id, fake_page_token, mp4_bytes):
    route = respx.post(f"https://graph.facebook.com/v23.0/{fake_page_id}/videos").mock(
        side_effect=[
            httpx.Response(200, json={"upload_session_id": "SID", "video_id": "VID",
                                      "start_offset": "0", "end_offset": "5242880"}),
            httpx.Response(200, json={"start_offset": "5242880", "end_offset": "10485760"}),
            httpx.Response(200, json={"start_offset": "10485760", "end_offset": "10485760"}),
            httpx.Response(200, json={"success": True}),
        ]
    )
    async with httpx.AsyncClient() as http:
        result = await _upload_facebook_video(
            http, fake_page_id, fake_page_token, mp4_bytes, description="cap"
        )
    assert result == {"video_id": "VID", "success": True}
    assert route.call_count == 4
    phases = [extract_upload_phase(call.request) for call in route.calls]
    assert phases == ["start", "transfer", "transfer", "finish"]
```

Helper to extract `upload_phase` from a multipart `httpx.Request` body (place in conftest.py):
```python
def extract_upload_phase(request: httpx.Request) -> str:
    """Parse multipart body and return the upload_phase form field value."""
    # respx captures the raw body; use email.parser or naive substring match.
    body = request.content  # bytes
    # multipart bodies contain `name="upload_phase"\r\n\r\n<value>\r\n`
    import re
    m = re.search(rb'name="upload_phase"\r\n\r\n([a-z]+)', body)
    return m.group(1).decode() if m else ""
```
</existing_test_patterns>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wave-0 test scaffolding — create tests/unit/social/, add respx to dev deps, write fixtures</name>
  <files>tests/unit/social/__init__.py, tests/unit/social/conftest.py, pyproject.toml</files>
  <action>
1. Create `tests/unit/social/__init__.py` as an empty file (package marker).

2. Add `respx>=0.21.0` to the `dev` dependency list in `pyproject.toml`. The `dev = [...]` array is around the line that begins with `dev = [` (alongside `pytest>=8.3.4`, `pytest-asyncio`, etc.). Insert `"respx>=0.21.0,<1.0.0",` alphabetically (after `pytest-mock` if present, otherwise after `pytest-cov`).

3. Run `uv sync --dev` to install respx. If `uv sync` complains about a lockfile mismatch, also run `uv lock`.

4. Create `tests/unit/social/conftest.py` with these fixtures and helpers:

```python
"""Shared fixtures for app/social/ unit tests."""
import re

import httpx
import pytest


@pytest.fixture
def fake_page_id() -> str:
    return "PAGE_1234567890"


@pytest.fixture
def fake_page_token() -> str:
    return "EAAG_FAKE_PAGE_ACCESS_TOKEN"


@pytest.fixture
def fake_user_id() -> str:
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mp4_bytes() -> bytes:
    """10 MB of zero bytes — stand-in for a 30s 1080p MP4 (typically 5-15 MB)."""
    return b"\x00" * (10 * 1024 * 1024)


def extract_upload_phase(request: httpx.Request) -> str:
    """Parse a multipart request body and return the upload_phase form field value.

    Returns empty string if the field is not found (helps tests fail loudly).
    """
    body = request.content if request.content else b""
    match = re.search(rb'name="upload_phase"\r?\n\r?\n([a-z]+)', body)
    return match.group(1).decode() if match else ""


def extract_form_field(request: httpx.Request, field_name: str) -> str:
    """Parse a multipart request body and return the value of a named text form field."""
    body = request.content if request.content else b""
    pattern = rb'name="' + field_name.encode() + rb'"\r?\n\r?\n([^\r\n]+)'
    match = re.search(pattern, body)
    return match.group(1).decode() if match else ""
```

5. Verify the Wave-0 scaffold:
   - `uv run python -c "import respx; print(respx.__version__)"` succeeds.
   - `uv run pytest tests/unit/social/ --collect-only` produces 0 tests collected (file is empty package marker — Task 4 adds the actual tests).
   - `ls tests/unit/social/` shows `__init__.py` and `conftest.py`.

DO NOT add publisher logic in this task. DO NOT create test_publisher_facebook.py yet (Task 4 does that).

Commit message: `test(107-01): scaffold tests/unit/social with respx (POST-09 wave 0)`.
  </action>
  <verify>
    <automated>uv run python -c "import respx; import sys; sys.exit(0)" &amp;&amp; uv run pytest tests/unit/social/ --collect-only 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
- `tests/unit/social/__init__.py` exists, empty.
- `tests/unit/social/conftest.py` exists with `fake_page_id`, `fake_page_token`, `fake_user_id`, `mp4_bytes` fixtures and `extract_upload_phase` + `extract_form_field` helpers.
- `pyproject.toml` `[dev]` deps include `respx>=0.21.0,<1.0.0`.
- `uv sync --dev` succeeded; `import respx` works.
- `uv run pytest tests/unit/social/ --collect-only` reports "no tests collected" (no test files yet) and DOES NOT error on the conftest import.
- Commit `test(107-01): scaffold tests/unit/social with respx (POST-09 wave 0)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement FB_GRAPH_API_VERSION + FacebookUploadError + _post_chunk_with_retry + _upload_facebook_video helpers</name>
  <files>app/social/publisher.py</files>
  <behavior>
After this task, `app/social/publisher.py` defines the four primitives needed by Task 3 and Task 4:

1. **Module-level constant** `FB_GRAPH_API_VERSION = "v23.0"` near the top of the file (under the existing imports, before `SocialPublisher`).

2. **Exception class** `FacebookUploadError(Exception)`:
   - Constructor: `__init__(self, message: str, *, phase: str, session_id: str | None = None, status_code: int | None = None)`.
   - Stores `phase`, `session_id`, `status_code` as instance attributes for caller introspection.
   - Calls `super().__init__(message)`.

3. **Helper** `async def _post_chunk_with_retry(http, url, data, files=None, timeout=60.0) -> httpx.Response`:
   - Attempts the POST up to **2 times** (one initial + one retry).
   - **Retry triggers (attempt 1 only):** `httpx.RequestError` (covers `httpx.ConnectError`, `httpx.ReadTimeout`, etc.) AND any 5xx status code.
   - **Non-retry conditions:** 2xx and 4xx are returned immediately on the first attempt.
   - **Sleep between attempts:** `await asyncio.sleep(0.5)` before the retry to avoid hammering the server.
   - **After retry exhaustion:** Returns the last `httpx.Response` (5xx case) OR re-raises the captured `httpx.RequestError` (network case). The CALLER decides whether to surface a `FacebookUploadError` based on the response code.
   - Add `import asyncio` at the top of the file if it's not already imported.

4. **Helper** `async def _upload_facebook_video(http, page_id, page_access_token, video_bytes, description, title=None, api_version=FB_GRAPH_API_VERSION) -> dict[str, Any]`:
   - URL: `f"https://graph.facebook.com/{api_version}/{page_id}/videos"`.
   - **Phase 1 (start):** `await http.post(url, data={"upload_phase": "start", "access_token": page_access_token, "file_size": str(len(video_bytes))}, timeout=60.0)`. On non-200, raise `FacebookUploadError(f"phase=start failed: {resp.text}", phase="start", status_code=resp.status_code)`. Parse JSON; capture `upload_session_id`, `video_id`, `start_offset`, `end_offset` (both offsets are strings — convert to int).
   - **Phase 2 (transfer loop):** While `start_offset < end_offset`:
       - `chunk = video_bytes[start_offset:end_offset]`
       - `data = {"upload_phase": "transfer", "access_token": page_access_token, "upload_session_id": upload_session_id, "start_offset": str(start_offset)}`
       - `files = {"video_file_chunk": ("chunk", chunk, "application/octet-stream")}`
       - `resp = await _post_chunk_with_retry(http, url, data, files=files, timeout=120.0)`
       - If `resp.status_code != 200`: raise `FacebookUploadError(f"phase=transfer failed at offset {start_offset}: {resp.text}", phase="transfer", session_id=upload_session_id, status_code=resp.status_code)`.
       - `body = resp.json(); start_offset = int(body["start_offset"]); end_offset = int(body["end_offset"])`.
       - Log `logger.info("Facebook upload chunk: session=%s start=%s end=%s", upload_session_id, start_offset, end_offset)`.
       - **Termination:** when `start_offset == end_offset` after the response, exit the loop.
   - **Phase 3 (finish):** `data = {"upload_phase": "finish", "access_token": page_access_token, "upload_session_id": upload_session_id, "description": description}`. If `title`: `data["title"] = title`. POST. On non-200, raise `FacebookUploadError(..., phase="finish", session_id=upload_session_id, status_code=resp.status_code)`. On 200, parse `success = body.get("success", False)`.
   - **Return:** `{"video_id": video_id, "success": bool(success)}`.

5. Use the existing module logger (`logger = logging.getLogger(__name__)` already in publisher.py).

6. **Existing branches MUST NOT regress.** The `if/elif` chain in `post_with_media` for twitter/linkedin/instagram and the Facebook photo/feed sub-branches MUST keep their current behavior. Only the Facebook video sub-branch is rewired in Task 3.

7. **No `file_url` substring** anywhere in `app/social/publisher.py` after this task lands.

8. Run `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py && uv run ty check app/social/publisher.py` — all clean.

Commit message: `feat(107-01): add FB three-phase upload helpers + retry-once + FacebookUploadError (POST-09)`.

NOTE: This task does NOT change `post_with_media`. The Facebook video branch still has the broken JSON `file_url` POST until Task 3. Existing tests (none for FB video) won't change. The new helpers are unused until Task 3.

WAIT — re-read step 7: "No `file_url` substring anywhere in publisher.py after this task lands." That means Task 2 ALSO removes the `file_url` line. Yes — to make the grep test pass at the end of this task, remove the JSON `file_url` POST and replace it with a placeholder that raises `NotImplementedError("Wired in Task 3 of plan 107-01")`. Task 3 then replaces the placeholder with the real wiring. This split keeps each task's blast radius small.

Updated step 7 wording: Replace lines 175-183 of `publisher.py` with:
```python
elif platform == "facebook":
    if has_media and media_type == "video":
        # NOTE: rewired in Task 3 of plan 107-01 to use _upload_facebook_video.
        # Placeholder kept so the file_url string is grep-absent after Task 2.
        raise NotImplementedError(
            "Facebook video upload is being migrated to the three-phase resumable "
            "API in plan 107-01. Will be wired in Task 3."
        )
```
This intentionally breaks live FB video posting between Task 2 and Task 3 commits — acceptable because the prior code was already broken (file_url silently failed).
  </behavior>
  <action>
1. Open `app/social/publisher.py`.

2. Add `import asyncio` to the imports block (alphabetical placement: it's the first standard-lib import, so before `import logging`).

3. Just below the `logger = logging.getLogger(__name__)` line, add:

```python
FB_GRAPH_API_VERSION = "v23.0"


class FacebookUploadError(Exception):
    """Raised when a Facebook three-phase video upload fails irrecoverably.

    Attributes:
        phase: Which upload phase failed: 'start', 'transfer', or 'finish'.
        session_id: The upload_session_id (None if failure was in phase=start).
        status_code: HTTP status code from Meta (None if the failure was a
            network exception with no response).
    """

    def __init__(
        self,
        message: str,
        *,
        phase: str,
        session_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.session_id = session_id
        self.status_code = status_code


async def _post_chunk_with_retry(
    http,
    url: str,
    data: dict,
    files: dict | None = None,
    timeout: float = 60.0,
):
    """POST a Facebook upload phase request; retry exactly once on 5xx or network error.

    4xx responses are NOT retried — they surface immediately so the caller can
    raise a structured FacebookUploadError. The caller handles status-code
    interpretation; this helper only handles the retry loop.
    """
    import httpx as _httpx  # local alias for type clarity

    last_exc: Exception | None = None
    last_resp = None
    for attempt in (1, 2):
        try:
            resp = await http.post(url, data=data, files=files, timeout=timeout)
            if resp.status_code < 500:
                return resp  # 2xx or 4xx — return; caller decides
            # 5xx — retry once
            last_resp = resp
            if attempt == 1:
                logger.warning(
                    "Facebook chunk POST returned %s; retrying once",
                    resp.status_code,
                )
                await asyncio.sleep(0.5)
                continue
            return resp  # second 5xx — return so caller can raise structured error
        except _httpx.RequestError as exc:
            last_exc = exc
            if attempt == 1:
                logger.warning(
                    "Facebook chunk POST raised %s; retrying once", type(exc).__name__,
                )
                await asyncio.sleep(0.5)
                continue
            raise
    # unreachable — both branches return or raise above; defensive fallback:
    if last_resp is not None:
        return last_resp
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("_post_chunk_with_retry: unexpected fall-through")


async def _upload_facebook_video(
    http,
    page_id: str,
    page_access_token: str,
    video_bytes: bytes,
    description: str,
    title: str | None = None,
    api_version: str = FB_GRAPH_API_VERSION,
) -> dict[str, Any]:
    """Three-phase resumable upload of a video to a Facebook Page.

    See https://developers.facebook.com/docs/graph-api/reference/page/videos/

    Args:
        http: An open httpx.AsyncClient.
        page_id: Facebook Page ID (target of the upload).
        page_access_token: A Page access token with pages_manage_posts scope.
        video_bytes: Full video file bytes (in-memory; SC scope is 30s 1080p MP4).
        description: Caption / post body.
        title: Optional video title.
        api_version: Graph API version (default v23.0).

    Returns:
        Dict {"video_id": str, "success": bool}.

    Raises:
        FacebookUploadError: with .phase, .session_id, .status_code on any
        non-recoverable failure (after the single retry, if applicable).
    """
    url = f"https://graph.facebook.com/{api_version}/{page_id}/videos"
    file_size = len(video_bytes)

    # Phase 1: start
    start_resp = await http.post(
        url,
        data={
            "upload_phase": "start",
            "access_token": page_access_token,
            "file_size": str(file_size),
        },
        timeout=60.0,
    )
    if start_resp.status_code != 200:
        raise FacebookUploadError(
            f"phase=start failed: {start_resp.text}",
            phase="start",
            status_code=start_resp.status_code,
        )
    start_body = start_resp.json()
    upload_session_id = start_body["upload_session_id"]
    video_id = start_body["video_id"]
    start_offset = int(start_body["start_offset"])
    end_offset = int(start_body["end_offset"])
    logger.info(
        "Facebook upload start: session=%s video_id=%s file_size=%d first_chunk=[%d, %d)",
        upload_session_id, video_id, file_size, start_offset, end_offset,
    )

    # Phase 2: transfer (loop)
    while start_offset < end_offset:
        chunk = video_bytes[start_offset:end_offset]
        transfer_resp = await _post_chunk_with_retry(
            http,
            url,
            data={
                "upload_phase": "transfer",
                "access_token": page_access_token,
                "upload_session_id": upload_session_id,
                "start_offset": str(start_offset),
            },
            files={"video_file_chunk": ("chunk", chunk, "application/octet-stream")},
            timeout=120.0,
        )
        if transfer_resp.status_code != 200:
            raise FacebookUploadError(
                f"phase=transfer failed at offset {start_offset}: {transfer_resp.text}",
                phase="transfer",
                session_id=upload_session_id,
                status_code=transfer_resp.status_code,
            )
        transfer_body = transfer_resp.json()
        start_offset = int(transfer_body["start_offset"])
        end_offset = int(transfer_body["end_offset"])
        logger.info(
            "Facebook upload chunk done: session=%s next=[%d, %d)",
            upload_session_id, start_offset, end_offset,
        )

    # Phase 3: finish
    finish_data: dict[str, Any] = {
        "upload_phase": "finish",
        "access_token": page_access_token,
        "upload_session_id": upload_session_id,
        "description": description,
    }
    if title:
        finish_data["title"] = title
    finish_resp = await http.post(url, data=finish_data, timeout=60.0)
    if finish_resp.status_code != 200:
        raise FacebookUploadError(
            f"phase=finish failed: {finish_resp.text}",
            phase="finish",
            session_id=upload_session_id,
            status_code=finish_resp.status_code,
        )
    finish_body = finish_resp.json()
    success = bool(finish_body.get("success", False))
    logger.info(
        "Facebook upload finish: session=%s video_id=%s success=%s",
        upload_session_id, video_id, success,
    )
    return {"video_id": video_id, "success": success}
```

4. Replace the existing Facebook video sub-branch (lines ~175-183 today, find it by searching for `"https://graph.facebook.com/v18.0/me/videos"`) with the placeholder:

```python
elif platform == "facebook":
    if has_media and media_type == "video":
        # NOTE: rewired in Task 3 of plan 107-01 to use _upload_facebook_video.
        # Placeholder kept so the legacy 'file_url' string is grep-absent after Task 2.
        raise NotImplementedError(
            "Facebook video upload is being migrated to the three-phase resumable "
            "API in plan 107-01. Wired in Task 3."
        )
```

5. **Bump remaining v18.0 references in publisher.py to use the new constant.** Search for `"v18.0"` in `publisher.py` — there are several (Facebook photo/feed branches, Instagram container/publish, etc.). Replace each URL string with an f-string using `FB_GRAPH_API_VERSION`. Example: `"https://graph.facebook.com/v18.0/me/photos"` becomes `f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/me/photos"`. Do this for ALL Facebook-host URLs in publisher.py (the `graph.facebook.com` ones — Twitter and LinkedIn URLs are unaffected).

6. Run `grep -n "file_url\|v18\.0" app/social/publisher.py` — output MUST be empty.

7. Run `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py`. Then `uv run ty check app/social/publisher.py`. All clean.

8. Run the existing test suite to confirm no regression: `uv run pytest tests/unit/ -x -k "social or publisher" 2>&1 | tail -20`. If there are no existing tests touching publisher.py, this is a no-op (acceptable).

DO NOT touch `connector.py` in this task (Plan 107-02 owns connector changes).
  </action>
  <verify>
    <automated>uv run ruff check app/social/publisher.py 2>&amp;1 | tail -5 &amp;&amp; uv run ty check app/social/publisher.py 2>&amp;1 | tail -5 &amp;&amp; (! grep -nE "file_url|v18\.0" app/social/publisher.py)</automated>
  </verify>
  <done>
- `app/social/publisher.py` defines `FB_GRAPH_API_VERSION = "v23.0"`, `FacebookUploadError`, `_post_chunk_with_retry`, and `_upload_facebook_video` at module scope.
- All Facebook-host URLs in publisher.py interpolate `FB_GRAPH_API_VERSION` (no `v18.0` string remains in the file).
- The legacy Facebook video branch is replaced with a `NotImplementedError`-raising placeholder (no `file_url` substring).
- `grep -nE "file_url|v18\.0" app/social/publisher.py` returns nothing.
- `ruff check` and `ty check` clean.
- Commit `feat(107-01): add FB three-phase upload helpers + retry-once + FacebookUploadError (POST-09)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire post_with_media Facebook video branch + add _get_facebook_page_context helper</name>
  <files>app/social/publisher.py</files>
  <behavior>
After this task, `SocialPublisher.post_with_media(platform="facebook", media_type="video", media_urls=[mp4_url], content=caption, user_id=user_id)`:

1. Resolves the Page ID + Page access token from `connected_accounts` via a new helper `_get_facebook_page_context(user_id)`:
   - Reads the row where `user_id=user_id, platform='facebook', status='active'`.
   - On missing row → returns `(None, {"error": "No active Facebook Page connection. Reconnect Facebook to grant Page access."})`.
   - On missing `platform_user_id` → returns `(None, {"error": "Facebook connection is missing the Page ID. Reconnect to capture Page access."})`. (This is the "user connected before Plan 107-02 landed" defensive case.)
   - On success → returns `((page_id, page_access_token), None)` where `page_access_token = self.connector._decrypt_token(row["access_token"])`.

2. Fetches `media_urls[0]` via `httpx.AsyncClient.get(...)` inside the existing `async with httpx.AsyncClient(timeout=60.0) as http:` block. On non-200 → returns `{"error": f"Failed to fetch media URL: {fetch_resp.status_code}"}`. Otherwise reads `.content` into `video_bytes`.

3. Calls `await _upload_facebook_video(http, page_id, page_token, video_bytes, description=content)`.

4. On `FacebookUploadError as exc`: returns the structured error dict `{"error": str(exc), "phase": exc.phase, "session_id": exc.session_id, "status_code": exc.status_code}`.

5. On success: sets `resp` to a fake-shaped object that the existing tail of `post_with_media` (the `if resp.status_code in [200, 201]:` block at the end) can handle — OR (cleaner) returns directly from the FB-video branch with `{"success": True, "platform": "facebook", "video_id": result["video_id"], "post_id": result["video_id"]}`. Pick option B (early return). This avoids hacking a fake httpx.Response into the tail.

6. The placeholder `raise NotImplementedError(...)` from Task 2 is gone.

7. Existing branches (twitter, linkedin, FB photo/feed, instagram) are unchanged.

Run `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py && uv run ty check app/social/publisher.py` — clean.

Commit message: `feat(107-01): wire post_with_media Facebook video to three-phase upload (POST-09)`.
  </behavior>
  <action>
1. Add the `_get_facebook_page_context` method to `SocialPublisher` (place it next to `_get_token_or_error`):

```python
def _get_facebook_page_context(
    self, user_id: str
) -> tuple[tuple[str, str] | None, dict | None]:
    """Resolve (page_id, page_access_token) for a user's Facebook connection.

    The Page ID is stored in connected_accounts.platform_user_id (set by Plan
    107-02's OAuth callback augmentation). The Page access token is stored in
    connected_accounts.access_token (Fernet-encrypted; decrypt before returning).

    Returns:
        ((page_id, page_token), None) on success, (None, {"error": ...}) otherwise.
    """
    result = (
        self.connector.client.table("connected_accounts")
        .select("platform_user_id, access_token, status")
        .eq("user_id", user_id)
        .eq("platform", "facebook")
        .eq("status", "active")
        .execute()
    )
    if not result.data:
        return None, {
            "error": "No active Facebook Page connection. "
            "Reconnect Facebook to grant Page access."
        }
    row = result.data[0]
    page_id = row.get("platform_user_id")
    if not page_id:
        return None, {
            "error": "Facebook connection is missing the Page ID. "
            "Reconnect to capture Page access (Plan 107-02 OAuth update required)."
        }
    encrypted_token = row.get("access_token")
    try:
        page_token = self.connector._decrypt_token(encrypted_token)
    except Exception as exc:
        logger.warning("Facebook page token decryption failed: %s", exc)
        return None, {"error": "Failed to decrypt Facebook Page token."}
    if not page_token:
        return None, {"error": "Facebook Page token is empty after decryption."}
    return (page_id, page_token), None
```

2. Replace the Task-2 placeholder in the Facebook video branch:

```python
elif platform == "facebook":
    if has_media and media_type == "video":
        page_ctx, ctx_err = self._get_facebook_page_context(user_id)
        if ctx_err:
            return ctx_err
        page_id, page_token = page_ctx

        # Fetch the public media URL into memory (SC-1 scope: 30s 1080p MP4 ~5-15 MB)
        fetch_resp = await http.get(media_urls[0])
        if fetch_resp.status_code != 200:
            return {
                "error": (
                    f"Failed to fetch media URL "
                    f"({fetch_resp.status_code}): {media_urls[0]}"
                )
            }
        video_bytes = fetch_resp.content

        try:
            result = await _upload_facebook_video(
                http,
                page_id=page_id,
                page_access_token=page_token,
                video_bytes=video_bytes,
                description=content,
            )
        except FacebookUploadError as exc:
            return {
                "error": str(exc),
                "phase": exc.phase,
                "session_id": exc.session_id,
                "status_code": exc.status_code,
            }

        return {
            "success": True,
            "platform": "facebook",
            "video_id": result["video_id"],
            "post_id": result["video_id"],
        }
    elif has_media and media_type in ("image", "carousel"):
        # ... existing photo branch unchanged ...
```

(Keep the rest of the elif chain — image, feed, etc. — exactly as it was.)

3. The `try/except` block that wraps the whole `async with httpx.AsyncClient(...)` is not changed; the early `return` from the FB video branch exits naturally.

4. Run `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py && uv run ty check app/social/publisher.py`. Clean.

5. Confirm grep still empty: `grep -nE "file_url|v18\.0|NotImplementedError" app/social/publisher.py`. No `file_url`, no `v18.0`, no leftover `NotImplementedError` from Task 2's placeholder.

6. Run the existing pytest sweep: `uv run pytest tests/unit/ -x -k "social or publisher" 2>&1 | tail -20`. No regressions.

DO NOT add tests in this task. Task 4 owns the test_publisher_facebook.py file.
  </action>
  <verify>
    <automated>uv run ruff check app/social/publisher.py 2>&amp;1 | tail -5 &amp;&amp; uv run ty check app/social/publisher.py 2>&amp;1 | tail -5 &amp;&amp; (! grep -nE "file_url|v18\.0|NotImplementedError" app/social/publisher.py)</automated>
  </verify>
  <done>
- `_get_facebook_page_context` method exists on `SocialPublisher`.
- The Facebook video sub-branch in `post_with_media` resolves (page_id, page_token), fetches the media URL into bytes, calls `_upload_facebook_video`, and returns either a structured-error dict (on `FacebookUploadError`) or `{"success": True, "platform": "facebook", "video_id": ..., "post_id": ...}` on success.
- The Task-2 `NotImplementedError` placeholder is gone.
- `ruff check`, `ty check` clean. `grep -nE "file_url|v18\.0|NotImplementedError" app/social/publisher.py` empty.
- Existing tests still pass (no regression in twitter/linkedin/instagram/FB-photo paths).
- Commit `feat(107-01): wire post_with_media Facebook video to three-phase upload (POST-09)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Add SC-1 + SC-2 mock-based unit tests + grep-absence static check</name>
  <files>tests/unit/social/test_publisher_facebook.py</files>
  <behavior>
After this task, `tests/unit/social/test_publisher_facebook.py` contains four tests, all GREEN against the Task-2/Task-3 implementation:

1. **test_video_upload_three_phase_two_chunks** (SC-1, three-phase shape):
   - Uses `respx` to mock the Facebook videos endpoint with a 4-response side-effect list (start → transfer → transfer → finish).
   - Calls `_upload_facebook_video(http, "PAGE_1234567890", "FAKE_TOKEN", mp4_bytes, description="test caption")`.
   - Asserts: result == `{"video_id": "VID_999", "success": True}`.
   - Asserts: `route.call_count == 4`.
   - Asserts: `[extract_upload_phase(c.request) for c in route.calls] == ["start", "transfer", "transfer", "finish"]`.
   - Asserts: the second call's `start_offset` form field equals `"0"` (first chunk starts at offset 0).
   - Asserts: the third call's `start_offset` form field equals `"5242880"` (second chunk starts at the end of the first).
   - Asserts: the finish call's `description` form field equals `"test caption"`.

2. **test_video_upload_retries_chunk_once_on_5xx** (SC-2, retry-once):
   - Mock side-effect: start (200) → transfer #1 (500) → transfer retry (200, advances offset) → finish (200).
   - Calls `_upload_facebook_video(...)`.
   - Asserts: result["success"] is True.
   - Asserts: total POST count is 4 (start + 500 + retry + finish — not 3, not 5).
   - Asserts: the second AND third calls both carry `upload_phase=transfer` (the retry replays the same phase).

3. **test_video_upload_surfaces_error_after_retry_exhausted** (SC-2, no infinite retry):
   - Mock side-effect: start (200) → transfer #1 (500) → transfer retry (500). No finish call expected.
   - Asserts: `pytest.raises(FacebookUploadError) as exc_info`.
   - Asserts: `exc_info.value.phase == "transfer"`.
   - Asserts: `exc_info.value.session_id == "SID_RETRY_EXHAUSTED"` (the session_id from the start response).
   - Asserts: `exc_info.value.status_code == 500`.
   - Asserts: total POST count is 3 (start + 500 + 500-retry; no third transfer attempt; no finish).

4. **test_no_legacy_file_url_in_publisher** (SC-1, static grep):
   - Reads `app/social/publisher.py` as text.
   - Asserts: `"file_url" not in source`.
   - Asserts: `"v18.0" not in source`.
   - This is a synchronous test (no asyncio).

Each async test is decorated with `@pytest.mark.asyncio` AND `@respx.mock`. Each uses `httpx.AsyncClient` directly (not via `SocialPublisher` — these tests target the helper, not the full method). Test 1's network setup uses `mp4_bytes` (10 MB fixture) so the second chunk window matches `[5242880, 10485760)`.

Run `uv run pytest tests/unit/social/test_publisher_facebook.py -x -v 2>&1 | tail -30`. All 4 tests GREEN. No warnings about respx version or pytest-asyncio mode.

Commit message: `test(107-01): add three-phase + retry-once + grep tests for Facebook video upload (POST-09)`.
  </behavior>
  <action>
Create `tests/unit/social/test_publisher_facebook.py`:

```python
"""Unit tests for the Facebook three-phase video upload (Plan 107-01).

Covers POST-09 success criteria:
  SC-1: three-phase request sequence (start -> transfer x N -> finish) on a 2-chunk path
  SC-1: legacy `file_url` string is grep-absent from app/social/publisher.py
  SC-2: failed transfer chunk retries exactly once before surfacing structured error
  SC-2: structured FacebookUploadError raised after retry exhausted
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from app.social.publisher import (
    FB_GRAPH_API_VERSION,
    FacebookUploadError,
    _upload_facebook_video,
)
from tests.unit.social.conftest import extract_form_field, extract_upload_phase

PAGE_ID = "PAGE_1234567890"
PAGE_TOKEN = "EAAG_FAKE_PAGE_ACCESS_TOKEN"
URL = f"https://graph.facebook.com/{FB_GRAPH_API_VERSION}/{PAGE_ID}/videos"


@pytest.mark.asyncio
@respx.mock
async def test_video_upload_three_phase_two_chunks(mp4_bytes):
    """SC-1: start -> transfer (chunk 1) -> transfer (chunk 2) -> finish."""
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "upload_session_id": "SID_HAPPY",
                    "video_id": "VID_999",
                    "start_offset": "0",
                    "end_offset": "5242880",
                },
            ),
            httpx.Response(
                200,
                json={"start_offset": "5242880", "end_offset": "10485760"},
            ),
            httpx.Response(
                200,
                json={"start_offset": "10485760", "end_offset": "10485760"},
            ),
            httpx.Response(200, json={"success": True}),
        ]
    )

    async with httpx.AsyncClient() as http:
        result = await _upload_facebook_video(
            http,
            page_id=PAGE_ID,
            page_access_token=PAGE_TOKEN,
            video_bytes=mp4_bytes,
            description="test caption",
        )

    assert result == {"video_id": "VID_999", "success": True}
    assert route.call_count == 4

    phases = [extract_upload_phase(call.request) for call in route.calls]
    assert phases == ["start", "transfer", "transfer", "finish"]

    # First transfer chunk starts at offset 0
    assert extract_form_field(route.calls[1].request, "start_offset") == "0"
    # Second transfer chunk starts at end of first
    assert extract_form_field(route.calls[2].request, "start_offset") == "5242880"
    # Finish carries the caption
    assert (
        extract_form_field(route.calls[3].request, "description") == "test caption"
    )


@pytest.mark.asyncio
@respx.mock
async def test_video_upload_retries_chunk_once_on_5xx(mp4_bytes):
    """SC-2: a single 5xx on a transfer chunk triggers exactly one retry."""
    # 5 MB video so single-chunk window suffices
    small_bytes = b"\x00" * (5 * 1024 * 1024)

    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "upload_session_id": "SID_RETRY",
                    "video_id": "VID_R",
                    "start_offset": "0",
                    "end_offset": "5242880",
                },
            ),
            httpx.Response(500, json={"error": "server_busy"}),
            httpx.Response(
                200,
                json={"start_offset": "5242880", "end_offset": "5242880"},
            ),
            httpx.Response(200, json={"success": True}),
        ]
    )

    async with httpx.AsyncClient() as http:
        result = await _upload_facebook_video(
            http,
            page_id=PAGE_ID,
            page_access_token=PAGE_TOKEN,
            video_bytes=small_bytes,
            description="retry test",
        )

    assert result["success"] is True
    assert route.call_count == 4  # start + 500 + retry + finish

    phases = [extract_upload_phase(call.request) for call in route.calls]
    assert phases == ["start", "transfer", "transfer", "finish"]


@pytest.mark.asyncio
@respx.mock
async def test_video_upload_surfaces_error_after_retry_exhausted(mp4_bytes):
    """SC-2: two consecutive 5xx on the same chunk -> FacebookUploadError, no third attempt."""
    small_bytes = b"\x00" * (5 * 1024 * 1024)

    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "upload_session_id": "SID_RETRY_EXHAUSTED",
                    "video_id": "VID_E",
                    "start_offset": "0",
                    "end_offset": "5242880",
                },
            ),
            httpx.Response(500, json={"error": "server_busy"}),
            httpx.Response(500, json={"error": "still_busy"}),
        ]
    )

    async with httpx.AsyncClient() as http:
        with pytest.raises(FacebookUploadError) as exc_info:
            await _upload_facebook_video(
                http,
                page_id=PAGE_ID,
                page_access_token=PAGE_TOKEN,
                video_bytes=small_bytes,
                description="exhaustion test",
            )

    assert exc_info.value.phase == "transfer"
    assert exc_info.value.session_id == "SID_RETRY_EXHAUSTED"
    assert exc_info.value.status_code == 500
    # No third transfer attempt and no finish call
    assert route.call_count == 3


def test_no_legacy_file_url_in_publisher():
    """SC-1 static check: legacy `file_url` JSON parameter is grep-absent."""
    publisher_path = (
        Path(__file__).resolve().parents[3] / "app" / "social" / "publisher.py"
    )
    source = publisher_path.read_text(encoding="utf-8")
    assert "file_url" not in source, (
        "Legacy `file_url` JSON parameter must not appear in app/social/publisher.py"
    )
    assert "v18.0" not in source, (
        "Hardcoded API version v18.0 must not appear in app/social/publisher.py "
        "(use FB_GRAPH_API_VERSION constant)"
    )
```

Run:
- `uv run pytest tests/unit/social/test_publisher_facebook.py -x -v 2>&1 | tail -30`. All 4 tests GREEN.
- `uv run pytest tests/unit/social/ -x` — full directory pass.
- `uv run pytest tests/unit/ -x -k "publisher or social"` — broader sweep, no regressions.
- `uv run ruff check tests/unit/social/test_publisher_facebook.py --fix && uv run ruff format tests/unit/social/test_publisher_facebook.py`. Clean.

If `pytest-asyncio` is in `auto` mode (check pyproject.toml), the `@pytest.mark.asyncio` decorators are still safe (idempotent). If it's in `strict` mode, the decorators are required (and present).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_publisher_facebook.py -x -v 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
- `tests/unit/social/test_publisher_facebook.py` exists with 4 tests covering: three-phase 2-chunk happy path (SC-1), retry-once on 5xx (SC-2), structured error after retry exhausted (SC-2), and grep-absence of `file_url` and `v18.0` in publisher.py (SC-1 static).
- All 4 tests GREEN under `uv run pytest tests/unit/social/test_publisher_facebook.py -x`.
- `tests/unit/social/` directory passes in full (`uv run pytest tests/unit/social/ -x`).
- No regressions in the broader unit suite.
- `ruff check` clean on the new test file.
- Commit `test(107-01): add three-phase + retry-once + grep tests for Facebook video upload (POST-09)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end automated:
1. `uv run pytest tests/unit/social/test_publisher_facebook.py -x -v` — all 4 tests GREEN.
2. `uv run pytest tests/unit/social/ -x` — directory-level pass (107-02 tests join here when that plan lands).
3. `uv run ruff check app/social/publisher.py tests/unit/social/` — clean.
4. `uv run ty check app/social/publisher.py` — clean.
5. `! grep -nE "file_url|v18\.0|NotImplementedError" app/social/publisher.py` — empty (the placeholder from Task 2 is gone after Task 3, the legacy params are gone after Task 2).

Manual smoke (deferred to phase-level UAT after 107-02 also lands):
- In a `make local-backend` session with a Facebook account connected (post-107-02 OAuth), upload a 30-second 1080p test MP4 via the Marketing agent. Confirm the video appears in the Page's feed within 60 seconds.
</verification>

<success_criteria>
- `app/social/publisher.py` defines `FB_GRAPH_API_VERSION = "v23.0"` at module scope.
- `app/social/publisher.py` defines `FacebookUploadError(Exception)` with `phase`, `session_id`, `status_code` attributes.
- `app/social/publisher.py` defines `_post_chunk_with_retry` (single retry on 5xx or `httpx.RequestError`; no retry on 4xx).
- `app/social/publisher.py` defines `_upload_facebook_video(http, page_id, page_access_token, video_bytes, description, title=None, api_version="v23.0")` performing three sequential POSTs: phase=start, phase=transfer (looped on offsets), phase=finish.
- `SocialPublisher._get_facebook_page_context(user_id)` resolves `(page_id, page_token)` from `connected_accounts.platform_user_id` + decrypted `access_token`.
- The Facebook video sub-branch in `post_with_media` resolves the page context, fetches the media URL bytes, calls `_upload_facebook_video`, catches `FacebookUploadError` to a structured-error dict, and returns `{"success": True, "platform": "facebook", "video_id": ..., "post_id": ...}` on success.
- All Facebook URLs in `publisher.py` interpolate `FB_GRAPH_API_VERSION` (no `v18.0` hardcode left).
- `file_url` and `v18.0` substrings are both grep-absent from `app/social/publisher.py`.
- 4 new pytest tests in `tests/unit/social/test_publisher_facebook.py` are GREEN. The `tests/unit/social/` package and its `conftest.py` exist.
- `respx>=0.21.0` is in `[dev]` dependencies in `pyproject.toml`; `uv sync --dev` succeeded.
- Existing `tests/unit/` does not regress (twitter/linkedin/instagram/FB-photo paths unchanged).
- `ruff check`, `ruff format`, `ty check` all clean for `app/social/publisher.py` and `tests/unit/social/`.
</success_criteria>

<output>
After completion, create `.planning/phases/107-facebook-video-resumable-upload/107-01-three-phase-upload-SUMMARY.md` documenting:
- Exact line numbers of the new `FB_GRAPH_API_VERSION` constant, `FacebookUploadError`, `_post_chunk_with_retry`, `_upload_facebook_video`, `_get_facebook_page_context`, and the rewired Facebook video sub-branch.
- Test count delta (existing N → existing N + 4 GREEN in `tests/unit/social/`).
- Any deviations from this plan (with rationale).
- Confirmation that `grep -nE "file_url|v18\.0" app/social/publisher.py` returns empty.
- Note that live Facebook video posting requires Plan 107-02 to also land (Page-token capture).
- Follow-up notes: streaming uploads (D-7 deferred), `upload_phase=cancel` cleanup, multi-Page selection UI (Phase 108).
</output>
