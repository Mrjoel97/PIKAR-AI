---
phase: 103-linkedin-posting-fix
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/connector.py
  - app/social/publisher.py
  - tests/unit/test_social_publisher_linkedin.py
  - tests/unit/test_social_connector_linkedin_identity.py
autonomous: true
requirements: [POST-01, POST-02]

must_haves:
  truths:
    - "LinkedIn OAuth callback writes the OIDC sub claim from /v2/userinfo into connected_accounts.platform_user_id (bare sub, not the full URN); platform_username is set from the name or given_name claim"
    - "LinkedIn text posts go to https://api.linkedin.com/rest/posts with headers LinkedIn-Version: 202401 and X-Restli-Protocol-Version: 2.0.0 and an author of urn:li:person:{platform_user_id} (never the literal urn:li:person:PERSON_ID)"
    - "LinkedIn image posts perform initializeUpload -> PUT bytes -> /rest/posts with content.media.id set to the returned urn:li:image:..."
    - "LinkedIn video posts perform initializeUpload -> PUT each chunk capturing etag -> finalizeUpload -> /rest/posts with content.media.id set to the returned urn:li:video:..."
    - "When a connected account has platform_user_id IS NULL at publish time, the publisher lazily fetches /v2/userinfo, persists the sub, and proceeds with the post (no reconnect prompt)"
    - "All existing connector tests in tests/unit/test_social_connector_security.py still pass (regression)"
  artifacts:
    - path: "app/social/connector.py"
      provides: "_fetch_linkedin_identity helper + handle_callback dispatches to it for platform=='linkedin' before the connected_accounts upsert"
      contains: "_fetch_linkedin_identity"
    - path: "app/social/publisher.py"
      provides: "Rewritten LinkedIn branch in post_with_media: _post_linkedin dispatch, _upload_linkedin_image, _upload_linkedin_video; lazy URN backfill; LinkedIn-Version: 202401 header"
      contains: "_post_linkedin"
    - path: "tests/unit/test_social_connector_linkedin_identity.py"
      provides: "Unit tests for OIDC userinfo fetch + handle_callback URN persistence + decode failure path"
      contains: "test_linkedin_callback_captures_urn"
    - path: "tests/unit/test_social_publisher_linkedin.py"
      provides: "Unit tests for /rest/posts request shape (text), /rest/images flow, /rest/videos flow, lazy backfill, missing-URN failure mode"
      contains: "test_linkedin_text_post_request_shape"
  key_links:
    - from: "app/social/connector.py:handle_callback"
      to: "app/social/connector.py:_fetch_linkedin_identity"
      via: "inline call after token exchange when platform=='linkedin'"
      pattern: "_fetch_linkedin_identity"
    - from: "app/social/publisher.py:post_with_media (linkedin branch)"
      to: "app/social/publisher.py:_post_linkedin"
      via: "dispatch when platform == 'linkedin'"
      pattern: "_post_linkedin"
    - from: "app/social/publisher.py:_post_linkedin"
      to: "https://api.linkedin.com/rest/posts"
      via: "httpx.AsyncClient.post with LinkedIn-Version + X-Restli-Protocol-Version headers"
      pattern: "rest/posts"
    - from: "app/social/publisher.py:_upload_linkedin_image"
      to: "https://api.linkedin.com/rest/images?action=initializeUpload"
      via: "httpx.AsyncClient.post then PUT to value.uploadUrl with no auth header"
      pattern: "rest/images"
    - from: "app/social/publisher.py:_upload_linkedin_video"
      to: "https://api.linkedin.com/rest/videos?action=initializeUpload + ?action=finalizeUpload"
      via: "init -> chunk PUTs collecting etag -> finalize"
      pattern: "rest/videos"
---

<objective>
Replace the literal `urn:li:person:PERSON_ID` placeholder at `app/social/publisher.py:162` with a real, OIDC-derived author URN AND migrate from the deprecated `/v2/ugcPosts` endpoint to the versioned `/rest/posts` API. Implements POST-01 (URN capture in OAuth callback + lazy backfill at publish time) and POST-02 (Posts API migration with text, single-image, and video support via `/rest/images` and `/rest/videos` initialize-upload flows).

Purpose: unblock every member-authored LinkedIn post. Today every LinkedIn post fails with `INVALID_URN_ID` from LinkedIn's URN validator AND uses a deprecated endpoint that will sunset on schedule. After this plan, LinkedIn text/image/video posts succeed end-to-end.

Output: `connector.py` gains `_fetch_linkedin_identity` and dispatches to it from `handle_callback`; `publisher.py` gains `_post_linkedin`, `_upload_linkedin_image`, `_upload_linkedin_video` and removes the legacy ugcPosts envelope; two new test files cover the contract end-to-end with mocked `httpx.AsyncClient`.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/103-linkedin-posting-fix/103-CONTEXT.md
@.planning/phases/103-linkedin-posting-fix/103-RESEARCH.md
@app/social/connector.py
@app/social/publisher.py
@tests/unit/test_social_connector_security.py

<interfaces>
<!-- Contracts the executor MUST use. Extracted from the codebase. -->

From app/social/connector.py (existing — DO NOT change signatures):
```python
class SocialConnector:
    client: Client  # supabase service-role client
    _pkce_verifiers: dict[str, str]

    def _encrypt_token(self, token: str | None) -> str | None: ...
    def _decrypt_token(self, token: str | None) -> str | None: ...

    async def handle_callback(
        self, platform: str, code: str, state: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Returns {'success': True, 'platform': str, 'message': str} or {'error': str}."""

    def get_access_token(self, user_id: str, platform: str) -> str | None:
        """Returns plaintext (decrypted) access_token, refreshing if expired."""
```

From app/social/publisher.py (existing):
```python
class SocialPublisher:
    connector: SocialConnector

    def _get_token_or_error(
        self, user_id: str, platform: str
    ) -> tuple[str | None, dict | None]:
        """Returns (token, None) or (None, {'error': msg})."""

    async def post_text(
        self, user_id: str, platform: str, content: str
    ) -> dict[str, Any]: ...

    async def post_with_media(
        self,
        user_id: str,
        platform: str,
        content: str,
        media_urls: list[str] | None = None,
        media_type: str = "image",  # 'text' | 'image' | 'video' | 'carousel'
    ) -> dict[str, Any]:
        """Returns {'success': True, 'platform': str, 'post_id': str, 'media_type': str, 'message': str}
                 OR {'error': str}."""
```

LinkedIn API contracts (verified against Microsoft Learn 2026-04 docs — see 103-RESEARCH.md sections A-D):

OIDC userinfo:
```
GET https://api.linkedin.com/v2/userinfo
Authorization: Bearer <access_token>

Response 200:
{
  "sub": "782bbtaQ",
  "name": "John Doe",
  "given_name": "John",
  "email": "...",
  ...
}
```

Posts API text:
```
POST https://api.linkedin.com/rest/posts
LinkedIn-Version: 202401
X-Restli-Protocol-Version: 2.0.0
Authorization: Bearer <token>
Content-Type: application/json

{
  "author": "urn:li:person:782bbtaQ",
  "commentary": "<text>",
  "visibility": "PUBLIC",
  "distribution": {
    "feedDistribution": "MAIN_FEED",
    "targetEntities": [],
    "thirdPartyDistributionChannels": []
  },
  "lifecycleState": "PUBLISHED",
  "isReshareDisabledByAuthor": false
}

Response: 201 Created. x-restli-id header contains the post URN.
```

Image upload (3 steps):
```
1) POST https://api.linkedin.com/rest/images?action=initializeUpload
   (same LinkedIn-Version + X-Restli-Protocol-Version headers)
   Body: {"initializeUploadRequest": {"owner": "urn:li:person:<sub>"}}
   Response 200: {"value": {"uploadUrl": "...", "image": "urn:li:image:...", "uploadUrlExpiresAt": ...}}

2) PUT <uploadUrl>
   Content-Type: application/octet-stream
   Body: <raw image bytes>
   NO Authorization header (URL is pre-signed)
   Response: 200

3) POST /rest/posts with body adding:
   "content": {"media": {"id": "urn:li:image:...", "altText": "..."}}
```

Video upload (4 steps):
```
1) POST https://api.linkedin.com/rest/videos?action=initializeUpload
   Body: {"initializeUploadRequest": {"owner": "urn:li:person:<sub>", "fileSizeBytes": <int>, "uploadCaptions": false, "uploadThumbnail": false}}
   Response 200: {"value": {"video": "urn:li:video:...", "uploadInstructions": [{"uploadUrl": "...", "firstByte": 0, "lastByte": 4194303}, ...], "uploadToken": "..."}}

2) For each instruction:
   PUT <uploadUrl>
   Content-Type: application/octet-stream
   Body: <bytes [firstByte..lastByte] inclusive>
   Response: 200; CAPTURE response.headers.get("etag") or get("ETag")

3) POST https://api.linkedin.com/rest/videos?action=finalizeUpload
   Body: {"finalizeUploadRequest": {"video": "urn:li:video:...", "uploadToken": "...", "uploadedPartIds": ["<etag1>", ...]}}
   Response: 200

4) POST /rest/posts with body adding:
   "content": {"media": {"id": "urn:li:video:...", "title": "<short title>"}}
```

From tests/unit/test_social_connector_security.py (TEST FIXTURE PATTERN — match this idiom):
```python
class _FakeClient:
    """In-memory Supabase fake. Tracks pkce_rows, connected_accounts,
    connected_account_upserts, connected_account_updates."""

class _AsyncClient:
    """Manually-rolled httpx.AsyncClient stand-in.
    async def post(self, url, data=None, json=None, headers=None) -> _Response."""

# Patch pattern:
with patch("httpx.AsyncClient", _AsyncClient):
    ...
```
Reuse this `_FakeClient` / `_AsyncClient` pattern. Do NOT add `respx` as a dependency.

From `app/social/connector.py:33-40` (LinkedIn config — already correct, DO NOT change):
```python
"linkedin": {
    "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
    "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
    "scopes": ["openid", "profile", "w_member_social"],  # /v2/userinfo works with these
    "client_id_env": "LINKEDIN_CLIENT_ID",
    "client_secret_env": "LINKEDIN_CLIENT_SECRET",
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — write failing tests for OIDC userinfo capture and Posts API request shapes</name>
  <files>tests/unit/test_social_connector_linkedin_identity.py, tests/unit/test_social_publisher_linkedin.py</files>
  <behavior>
    Two NEW test files with comprehensive failing-RED coverage. All tests must FAIL initially (target the contract that does not yet exist in production code).

    **File 1: tests/unit/test_social_connector_linkedin_identity.py**

    Reuse the `_FakeClient` / `_FakeTable` fixture pattern from `tests/unit/test_social_connector_security.py` (copy or import). Add three tests:

    - **test_linkedin_callback_captures_urn**: Patches `httpx.AsyncClient` so that:
      - The token-exchange POST to `https://www.linkedin.com/oauth/v2/accessToken` returns `{"access_token": "AT", "refresh_token": "RT", "expires_in": 1800}`.
      - The userinfo GET to `https://api.linkedin.com/v2/userinfo` (with `Authorization: Bearer AT`) returns `{"sub": "782bbtaQ", "name": "John Doe", "given_name": "John", "email": "doe@example.com"}`.
      Then calls `connector.handle_callback("linkedin", "auth-code", "<user>:state", "https://x.test/cb")` and asserts:
      - The recorded `connected_account_upserts[0]["platform_user_id"] == "782bbtaQ"` (BARE sub, not full URN).
      - The recorded `connected_account_upserts[0]["platform_username"] == "John Doe"` (falls back to `given_name` only when `name` absent).
      - Result is `{"success": True, ...}`.

    - **test_linkedin_callback_userinfo_failure_does_not_block_callback**: userinfo GET returns 500 (non-200). The callback STILL succeeds — the row is upserted with `platform_user_id=None` and `platform_username=None`. Assert a `WARNING` log was emitted mentioning `userinfo`. (Lazy backfill will recover at publish time.)

    - **test_non_linkedin_platform_does_not_call_userinfo**: For `platform="twitter"` with otherwise valid token exchange, no GET to `/v2/userinfo` is recorded (only the existing token-exchange POST). The Twitter row is upserted with `platform_user_id` and `platform_username` both unset / None.

    Use `caplog.set_level(logging.WARNING, logger="app.social.connector")` for the warning assertion.

    **File 2: tests/unit/test_social_publisher_linkedin.py**

    Build a `_FakeAsyncClient` that records every call as a list of `(method, url, headers, json|data, content)` and lets each test seed return values per URL. Use `pytest.mark.asyncio` for all async tests.

    Tests:

    - **test_linkedin_text_post_request_shape**: `connected_accounts` row has `platform_user_id="782bbtaQ"`, `platform="linkedin"`, `status="active"`, valid token. Call `publisher.post_text("user-1", "linkedin", "hello world")`. Assert exactly one `POST` to `https://api.linkedin.com/rest/posts` with:
      - `headers["LinkedIn-Version"] == "202401"`
      - `headers["X-Restli-Protocol-Version"] == "2.0.0"`
      - `headers["Authorization"] == "Bearer <token>"`
      - `headers["Content-Type"] == "application/json"`
      - JSON body matches:
        ```python
        {
          "author": "urn:li:person:782bbtaQ",
          "commentary": "hello world",
          "visibility": "PUBLIC",
          "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
          "lifecycleState": "PUBLISHED",
          "isReshareDisabledByAuthor": False,
        }
        ```
      - No `content` key in the body (text-only).
      Mock response: 201 with header `x-restli-id: urn:li:share:6844785523593134080`. Assert `result["success"] is True`, `result["post_id"] == "urn:li:share:6844785523593134080"`, `result["platform"] == "linkedin"`.

    - **test_linkedin_image_post_three_step_flow**: Single image URL. Mock:
      - GET to media URL returns `b"\x89PNG\r\n..."` (mock httpx GET in the same `_FakeAsyncClient`, used to fetch media bytes from the public URL).
      - POST `/rest/images?action=initializeUpload` returns `{"value": {"uploadUrl": "https://www.linkedin.com/dms-uploads/X", "image": "urn:li:image:IMG_URN"}}`.
      - PUT to `https://www.linkedin.com/dms-uploads/X` returns 200 (no body needed).
      - POST `/rest/posts` returns 201 with `x-restli-id` header.
      Assert all four calls happen in order. Assert:
      - PUT to `dms-uploads/X` does NOT include `Authorization` header.
      - PUT body content == the bytes returned by GET media URL.
      - `/rest/posts` body includes `content.media.id == "urn:li:image:IMG_URN"` and `content.media.altText` is a non-empty string (truncated commentary, max 120 chars).
      - initializeUpload body == `{"initializeUploadRequest": {"owner": "urn:li:person:782bbtaQ"}}`.

    - **test_linkedin_video_post_four_step_flow**: Single video URL. Mock:
      - GET media URL returns ~6MB bytes (`b"\x00" * 6_000_000`).
      - POST `/rest/videos?action=initializeUpload` returns `{"value": {"video": "urn:li:video:VID_URN", "uploadInstructions": [{"uploadUrl": "https://dms-uploads/v0", "firstByte": 0, "lastByte": 4194303}, {"uploadUrl": "https://dms-uploads/v1", "firstByte": 4194304, "lastByte": 5999999}], "uploadToken": "TOK"}}`.
      - PUT to each `uploadUrl` returns 200 with `etag` header `"etag0"` and `"etag1"` respectively.
      - POST `/rest/videos?action=finalizeUpload` returns 200.
      - POST `/rest/posts` returns 201 with `x-restli-id`.
      Assert:
      - initializeUpload body has `fileSizeBytes == 6_000_000`, `uploadCaptions == False`, `uploadThumbnail == False`.
      - PUT 0 body == bytes [0:4194304] (note: the slice is `firstByte:lastByte+1`); PUT 1 body == bytes [4194304:6000000].
      - finalizeUpload body == `{"finalizeUploadRequest": {"video": "urn:li:video:VID_URN", "uploadToken": "TOK", "uploadedPartIds": ["etag0", "etag1"]}}`.
      - `/rest/posts` body includes `content.media.id == "urn:li:video:VID_URN"`.

    - **test_linkedin_lazy_urn_backfill**: `connected_accounts` row has `platform_user_id=None` (existing pre-Phase-103 connection). Mock GET `/v2/userinfo` to return `{"sub": "BACKFILLED_SUB", "name": "Late Joiner"}`. Call `publisher.post_text("user-1", "linkedin", "hi")`. Assert:
      - GET to `/v2/userinfo` happened.
      - The `connected_accounts` table got an `update` recording `platform_user_id="BACKFILLED_SUB"` for `(user_id="user-1", platform="linkedin")`.
      - The subsequent `/rest/posts` body uses `author="urn:li:person:BACKFILLED_SUB"`.

    - **test_linkedin_post_without_urn_after_backfill_failure_returns_error**: `platform_user_id=None` AND `/v2/userinfo` GET returns 500. Result is `{"error": "<msg containing 'reconnect'>"}`. No POST to `/rest/posts` happens.

    - **test_linkedin_post_uses_persisted_urn_no_backfill_call**: `platform_user_id="EXISTING"` is set. Verify NO GET to `/v2/userinfo` happens during the publish path. Assert author URN uses `EXISTING`.

    All tests fail on `AttributeError`, `AssertionError`, or "wrong endpoint" / "missing header" mismatches against the current `publisher.py:155-171` implementation (which still hits `/v2/ugcPosts` with no LinkedIn-Version header and the `urn:li:person:PERSON_ID` placeholder).

    Run: `uv run pytest tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_publisher_linkedin.py -x -v`. Expect 9 failing tests (3 + 6).

    Commit message: `test(103-01): add failing tests for LinkedIn URN capture + Posts API migration (POST-01, POST-02)`.
  </behavior>
  <action>
    1. Create `tests/unit/test_social_connector_linkedin_identity.py`:
       - Import `pytest`, `logging`, `AsyncMock`, `patch` from `unittest.mock`, `datetime`/`timedelta`/`timezone`, and `SocialConnector` from `app.social.connector`.
       - Either copy the `_Result` / `_FakeTable` / `_FakeClient` / `_connector` fixtures from `tests/unit/test_social_connector_security.py` (preferred — keeps tests independent) or import them via a shared helper (acceptable). Going with copy keeps each test file self-contained and avoids cross-file fixture coupling.
       - Build a `_RecordingAsyncClient` whose `post(url, data=..., json=...)` and `get(url, headers=...)` record calls in a `requests` list. Each call returns a `_Response(status_code, json_data, headers={})` constructed from a per-test dispatch dict keyed by URL substring (e.g. `"oauth/v2/accessToken"` -> token response, `"v2/userinfo"` -> userinfo response).
       - Patch `app.social.connector.encrypt_secret` and `decrypt_secret` to identity (`lambda v: f"enc:{v}"` / passthrough) — match `test_social_connector_security.py:172-173`.
       - Set env via `monkeypatch.setenv("LINKEDIN_CLIENT_ID", "id")`, `("LINKEDIN_CLIENT_SECRET", "sec")`.
       - Pre-seed `client.pkce_rows[state]` with a non-expired row matching `platform="linkedin"` so `_pop_pkce_verifier` succeeds.
       - Write the 3 tests described in `<behavior>`.

    2. Create `tests/unit/test_social_publisher_linkedin.py`:
       - Import `pytest`, `pytest.mark.asyncio` decorator, mocking primitives, `SocialPublisher` and `SocialConnector` from `app.social.{publisher,connector}`.
       - Build `_FakeConnectorClient` that exposes `.table("connected_accounts").select().eq().eq().eq().execute()` returning a configured row, and `.table("connected_accounts").update({...}).eq().eq().execute()` recording the update for backfill assertions.
       - Build `_RecordingHttpx` with both `.post(url, headers=, json=, data=, content=)` and `.put(url, headers=, content=)` and `.get(url, headers=)` methods. Each test seeds a URL-keyed response dict.
         - `_Response` exposes `.status_code`, `.headers` (case-insensitive dict; fine to use a `Headers` shim that lowercases keys), `.text`, `.content`, and `.json()`.
       - Use `async with` ctx-manager pattern matching real `httpx.AsyncClient` (`__aenter__`, `__aexit__`).
       - Construct the publisher with a SocialConnector built via `SocialConnector.__new__(SocialConnector)` whose `client` attribute is `_FakeConnectorClient` — same shortcut as `test_social_connector_security.py:_connector()`.
       - Patch `httpx.AsyncClient` at the publisher import site: `with patch("httpx.AsyncClient", _RecordingHttpx)`.
       - Patch `connector.get_access_token` to return a deterministic token (avoids touching the decrypt path).
       - Write the 6 tests described in `<behavior>`.

    3. Run tests, confirm all 9 fail. Do NOT modify production code in this task.

    4. Lint: `uv run ruff check tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_publisher_linkedin.py --fix && uv run ruff format tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_publisher_linkedin.py`.

    5. Commit: `test(103-01): add failing tests for LinkedIn URN capture + Posts API migration (POST-01, POST-02)`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_publisher_linkedin.py -x -v 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    Both new test files exist. All 9 new tests FAIL with assertion errors referencing missing URN, wrong endpoint (`/v2/ugcPosts` instead of `/rest/posts`), or missing `LinkedIn-Version` header. Existing `tests/unit/test_social_connector_security.py` still passes. `ruff check` clean on the two new files. Commit `test(103-01): add failing tests for LinkedIn URN capture + Posts API migration (POST-01, POST-02)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement _fetch_linkedin_identity and wire it into handle_callback</name>
  <files>app/social/connector.py</files>
  <behavior>
    After this task, the 3 tests in `test_social_connector_linkedin_identity.py` are GREEN. All existing tests in `test_social_connector_security.py` still pass.

    Add a new private async method on `SocialConnector`:

    ```python
    async def _fetch_linkedin_identity(
        self, http: "httpx.AsyncClient", access_token: str
    ) -> tuple[str | None, str | None]:
        """Fetch (sub, display_name) from LinkedIn /v2/userinfo.

        Returns (sub, name) on success; (None, None) on any failure. Never raises.
        Display name prefers 'name'; falls back to 'given_name'; finally None.
        """
    ```

    Implementation calls `await http.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=10.0)`. On non-200, log a `WARNING` (`"LinkedIn /v2/userinfo failed: %s %s"`, status, truncated body) and return `(None, None)`. On exception, `logger.exception("LinkedIn /v2/userinfo fetch raised")` and return `(None, None)`. On 200, return `(json["sub"], json.get("name") or json.get("given_name"))`.

    In `handle_callback`, after the existing token exchange (the block currently spanning lines 302-312) and BEFORE the `connection_data = {...}` dict construction (line 326), dispatch by platform:

    ```python
    platform_user_id: str | None = None
    platform_username: str | None = None
    if platform == "linkedin":
        platform_user_id, platform_username = await self._fetch_linkedin_identity(
            http, access_token
        )
    # NOTE: Phase 101 AUTH-04 will refactor this into a generic dispatch
    # registry. Keep _fetch_linkedin_identity's signature stable so the
    # registry refactor is a one-line wiring change.
    ```

    Crucially the `httpx.AsyncClient` is opened inside `async with httpx.AsyncClient() as http:` at line 302. The userinfo call MUST be made inside this same block so the client is reused. Move the `connection_data = {...}` and `self.client.table("connected_accounts").upsert(...)` block INSIDE the `async with` block (or extract a local variable for `userinfo` before the block closes — easier).

    Add the two new keys to `connection_data`:
    ```python
    "platform_user_id": platform_user_id,
    "platform_username": platform_username,
    ```

    Run `uv run pytest tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_connector_security.py -x -v`. All tests GREEN.

    Lint clean: `uv run ruff check app/social/connector.py --fix && uv run ruff format app/social/connector.py && uv run ty check app/social/connector.py`.

    Commit: `feat(103-01): capture LinkedIn member URN from /v2/userinfo at OAuth callback (POST-01)`.
  </behavior>
  <action>
    1. Open `app/social/connector.py`.

    2. After the `_pop_pkce_verifier` method (around line 211) and before `get_authorization_url` (line 213), insert `_fetch_linkedin_identity` as defined in `<behavior>`. Type hint the `http` parameter as `"httpx.AsyncClient"` (string forward reference; `httpx` is imported lazily in `handle_callback`).

    3. Restructure `handle_callback`:
       - Currently the `async with httpx.AsyncClient() as http:` block at lines 302-308 only contains the token-exchange POST. Extend it to include the userinfo call.
       - After the existing token-exchange and inside the `async with` block:
         ```python
         platform_user_id: str | None = None
         platform_username: str | None = None
         if platform == "linkedin":
             platform_user_id, platform_username = await self._fetch_linkedin_identity(
                 http, access_token
             )
         ```
       - Note `access_token` is referenced before the `tokens.get("access_token")` line — pull `access_token = tokens.get("access_token")` UP into the `async with` block (current location is line 310, OUTSIDE the block).
       - Keep the `if not access_token: return {"error": ...}` guard inside the block too.
       - Encryption / expiry / connection_data construction can stay where they are (after the `async with` block); only the URN fetch needs the open client.

    4. Add `platform_user_id` and `platform_username` keys into `connection_data` between `"user_id"` and `"access_token"` (logical ordering).

    5. Run `uv run pytest tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_connector_security.py -x -v` — confirm all GREEN.

    6. Lint + format + type check.

    7. Commit: `feat(103-01): capture LinkedIn member URN from /v2/userinfo at OAuth callback (POST-01)`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_connector_security.py -x -v 2>&amp;1 | tail -30 &amp;&amp; uv run ruff check app/social/connector.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    `app/social/connector.py` has `_fetch_linkedin_identity` method. `handle_callback` calls it for `platform == "linkedin"` and persists `platform_user_id` + `platform_username` in the upsert. All 3 new connector tests pass. All 4 pre-existing security tests still pass (regression). `ruff check` clean. `ty check` clean. Commit `feat(103-01): capture LinkedIn member URN from /v2/userinfo at OAuth callback (POST-01)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Rewrite LinkedIn publisher branch — Posts API + image/video upload helpers + lazy URN backfill</name>
  <files>app/social/publisher.py</files>
  <behavior>
    After this task, all 6 tests in `test_social_publisher_linkedin.py` are GREEN. All existing publisher behavior for non-LinkedIn platforms is unchanged.

    Replace the entire `elif platform == "linkedin":` branch in `post_with_media` (current lines 135-171) with a single dispatch:

    ```python
    elif platform == "linkedin":
        return await self._post_linkedin(
            http, token, user_id, content, media_urls, media_type
        )
    ```

    The helper `_post_linkedin` performs the full flow and returns the same `{success/error}` envelope shape that the rest of `post_with_media` produces. (Returning early from inside `post_with_media` is acceptable here; the existing pattern in `post_with_media` handles `resp` after the if/elif chain — bypass that for LinkedIn since success / error decode is endpoint-specific.)

    Add three new private async methods to `SocialPublisher`:

    ```python
    async def _resolve_linkedin_author_urn(
        self, http: "httpx.AsyncClient", token: str, user_id: str
    ) -> str | None:
        """Resolve urn:li:person:{sub} for a user. Lazy-backfill platform_user_id when null."""

    async def _upload_linkedin_image(
        self,
        http: "httpx.AsyncClient",
        api_headers: dict,
        author_urn: str,
        media_url: str,
    ) -> str | None:
        """Run /rest/images initializeUpload + PUT bytes. Return urn:li:image:... or None."""

    async def _upload_linkedin_video(
        self,
        http: "httpx.AsyncClient",
        api_headers: dict,
        author_urn: str,
        media_url: str,
    ) -> str | None:
        """Run /rest/videos initializeUpload + PUT chunks + finalizeUpload. Return urn:li:video:... or None."""

    async def _post_linkedin(
        self,
        http: "httpx.AsyncClient",
        token: str,
        user_id: str,
        content: str,
        media_urls: list[str] | None,
        media_type: str,
    ) -> dict[str, Any]:
        """Post to /rest/posts with text / image / video. Return success or error dict."""
    ```

    `_resolve_linkedin_author_urn` logic:
    1. Read the connected_accounts row: `self.connector.client.table("connected_accounts").select("platform_user_id").eq("user_id", user_id).eq("platform", "linkedin").eq("status", "active").execute()`.
    2. If `platform_user_id` is set: return `f"urn:li:person:{platform_user_id}"`.
    3. Else: lazy backfill — call `await self.connector._fetch_linkedin_identity(http, token)`. If still None, return None (caller surfaces the "reconnect required" error). Otherwise update the row: `self.connector.client.table("connected_accounts").update({"platform_user_id": sub}).eq("user_id", user_id).eq("platform", "linkedin").execute()` and return `f"urn:li:person:{sub}"`.

    `_upload_linkedin_image` logic:
    1. POST `https://api.linkedin.com/rest/images?action=initializeUpload` with `api_headers` and JSON body `{"initializeUploadRequest": {"owner": author_urn}}`. On non-200, log warning and return None.
    2. Extract `uploadUrl` and `image_urn = response["value"]["image"]`.
    3. GET `media_url` with no auth (public URL) to fetch raw bytes. On non-200, log + None.
    4. PUT bytes to `uploadUrl` with `Content-Type: application/octet-stream` and NO `Authorization` header. On non-200, log + None.
    5. Return `image_urn`.

    `_upload_linkedin_video` logic:
    1. GET media_url to fetch bytes; compute `file_size = len(bytes)`.
    2. POST `https://api.linkedin.com/rest/videos?action=initializeUpload` with body `{"initializeUploadRequest": {"owner": author_urn, "fileSizeBytes": file_size, "uploadCaptions": False, "uploadThumbnail": False}}`. On non-200, log + None.
    3. Extract `video_urn`, `upload_token`, `instructions`.
    4. For each instruction: PUT bytes `[firstByte:lastByte+1]` to `instruction["uploadUrl"]` with `Content-Type: application/octet-stream` and NO auth header. Capture `etag = resp.headers.get("etag") or resp.headers.get("ETag")` (defensive). On non-200 or missing etag, log + None.
    5. POST `https://api.linkedin.com/rest/videos?action=finalizeUpload` with body `{"finalizeUploadRequest": {"video": video_urn, "uploadToken": upload_token, "uploadedPartIds": etags}}`. On non-200, log + None.
    6. Return `video_urn`.

    `_post_linkedin` logic:
    1. Resolve `author_urn = await self._resolve_linkedin_author_urn(http, token, user_id)`. If None, return `{"error": "LinkedIn account missing platform_user_id; reconnect required"}`.
    2. Build `api_headers`:
       ```python
       api_headers = {
           "Authorization": f"Bearer {token}",
           "LinkedIn-Version": "202401",
           "X-Restli-Protocol-Version": "2.0.0",
           "Content-Type": "application/json",
       }
       ```
    3. Build base body (matches `<interfaces>` Posts API text shape).
    4. If `media_urls and media_type == "image"`:
       - `image_urn = await self._upload_linkedin_image(http, api_headers, author_urn, media_urls[0])`.
       - On None, return error dict.
       - Add `body["content"] = {"media": {"id": image_urn, "altText": content[:120]}}`.
    5. Elif `media_urls and media_type == "video"`:
       - `video_urn = await self._upload_linkedin_video(http, api_headers, author_urn, media_urls[0])`.
       - On None, return error dict.
       - Add `body["content"] = {"media": {"id": video_urn, "title": content[:100]}}`.
    6. POST `https://api.linkedin.com/rest/posts` with `api_headers` and `json=body`. On 201, extract post URN from `resp.headers.get("x-restli-id")` and return success dict; on other status, return error dict.

    Edge cases for the test contract:
    - `media_type == "carousel"` for LinkedIn: out of scope this phase. Treat as text-only for now (just post the commentary, no media). Add a `# TODO: LinkedIn carousel via /rest/documents — out of scope POST-02` comment.
    - On any helper failure, the publisher logs at WARNING/ERROR with the failing step name and returns `{"error": "<step>: <status>: <body[:200]>"}`.

    Run `uv run pytest tests/unit/test_social_publisher_linkedin.py tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_connector_security.py -x -v`. All GREEN.

    Lint + format + type check `app/social/publisher.py`.

    Commit: `feat(103-01): migrate LinkedIn posting to /rest/posts with image+video flows (POST-02)`.
  </behavior>
  <action>
    1. Open `app/social/publisher.py`.

    2. Add `from typing import TYPE_CHECKING` import. Wrap `if TYPE_CHECKING: import httpx` so the forward references in helper signatures resolve. (Or keep using string `"httpx.AsyncClient"` annotations — fine either way; do NOT change the lazy `import httpx` inside `post_with_media`.)

    3. Insert the four new methods (`_resolve_linkedin_author_urn`, `_upload_linkedin_image`, `_upload_linkedin_video`, `_post_linkedin`) AFTER `_upload_media_twitter` (line 63) and BEFORE the `# Public posting methods` separator (line 65).

    4. In `post_with_media`, replace the entire `elif platform == "linkedin":` block (lines 135-171) with the dispatch:
       ```python
       elif platform == "linkedin":
           return await self._post_linkedin(
               http, token, user_id, content, media_urls, media_type
           )
       ```
       Note: this returns early. The existing `# Response handling` block at lines 336-352 is NOT executed for LinkedIn since `_post_linkedin` returns its own envelope. Verify with `pytest -v` that no other branch is broken.

    5. The final `else: return {"error": ...}` at line 333 must remain reachable for unsupported platforms; ensure the new LinkedIn `return` does not accidentally fall through.

    6. Helper method bodies follow the `<behavior>` block. Notable specifics:
       - All HTTP calls use the open `http: httpx.AsyncClient` passed in from `post_with_media`. Do NOT open new clients.
       - For PUT to pre-signed URLs, pass `headers={"Content-Type": "application/octet-stream"}` ONLY — no `Authorization`. Per pitfall #3 in research.
       - For chunk byte slicing: `chunk = body[instruction["firstByte"]:instruction["lastByte"] + 1]` (note the `+1` — LinkedIn's range is inclusive).
       - For etag capture: `resp.headers.get("etag") or resp.headers.get("ETag")` (defensive — `httpx` normalizes but tests may set either).
       - GET media_url: `await http.get(media_url)` with NO auth headers; if `resp.status_code != 200`, log and return None.

    7. Run pytest + ruff + ty.

    8. Commit: `feat(103-01): migrate LinkedIn posting to /rest/posts with image+video flows (POST-02)`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_social_publisher_linkedin.py tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_connector_security.py -x -v 2>&amp;1 | tail -40 &amp;&amp; uv run ruff check app/social/publisher.py app/social/connector.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    `app/social/publisher.py` has `_post_linkedin`, `_resolve_linkedin_author_urn`, `_upload_linkedin_image`, `_upload_linkedin_video` methods. The `elif platform == "linkedin":` branch in `post_with_media` is a single dispatch line. The literal string `"urn:li:person:PERSON_ID"` no longer appears anywhere in `app/social/`. The literal `"/v2/ugcPosts"` no longer appears in `app/social/publisher.py`. All 9 new tests pass; all 4 existing security tests pass (regression). `ruff check` clean. `ty check` clean. Commit `feat(103-01): migrate LinkedIn posting to /rest/posts with image+video flows (POST-02)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end: `uv run pytest tests/unit/test_social_publisher_linkedin.py tests/unit/test_social_connector_linkedin_identity.py tests/unit/test_social_connector_security.py -x -v` -> all GREEN.

Grep verifications (run after Task 3):
- `grep -rn "urn:li:person:PERSON_ID" app/` -> empty (placeholder gone).
- `grep -rn "/v2/ugcPosts" app/social/` -> empty (deprecated endpoint gone).
- `grep -rn "LinkedIn-Version" app/social/publisher.py` -> at least one match (header is being sent).
- `grep -rn "_fetch_linkedin_identity" app/social/` -> matches in connector.py (defined) and publisher.py (used in `_resolve_linkedin_author_urn`).

Manual smoke (deferred to phase-level UAT after 103-02):
- Connect a real LinkedIn account in dev. Confirm `connected_accounts` row has `platform_user_id` populated to a non-null bare-sub value.
- Run agent prompt "post 'hello world' to LinkedIn". Confirm 201 response and post appears on the account's feed within 30s.
- (If `INVALID_URN_ID` error surfaces: this is Open Question 1 — file follow-up phase to add `/v2/me` fallback.)
</verification>

<success_criteria>
- ROADMAP success criterion #1 (POST-01): `connected_accounts.platform_user_id` is the bare OIDC `sub` after callback; `/rest/posts` body uses `urn:li:person:{platform_user_id}` (NOT placeholder). Verified by `test_linkedin_callback_captures_urn` and `test_linkedin_text_post_request_shape`.
- ROADMAP success criterion #2 (POST-02): `/rest/posts` request shape correct including `LinkedIn-Version: 202401`. Verified by `test_linkedin_text_post_request_shape`. Image flow: `test_linkedin_image_post_three_step_flow`. Video flow: `test_linkedin_video_post_four_step_flow`.
- Lazy backfill works for pre-Phase-103 connections: `test_linkedin_lazy_urn_backfill`.
- Missing-URN-after-backfill-failure surfaces a reconnect error: `test_linkedin_post_without_urn_after_backfill_failure_returns_error`.
- No regression in existing connector security tests (4 tests).
- `ruff check` and `ty check` clean on both modified files.
- `urn:li:person:PERSON_ID` and `/v2/ugcPosts` strings absent from `app/social/`.
</success_criteria>

<output>
After completion, create `.planning/phases/103-linkedin-posting-fix/103-01-urn-capture-and-posts-api-migration-SUMMARY.md` documenting:
- Exact line ranges of `_fetch_linkedin_identity` (connector.py) and the 4 new publisher helpers.
- Test count delta: 0 -> 9 GREEN (3 connector + 6 publisher).
- Whether the pairwise-sub Open Question 1 surfaced during testing (it should NOT in mocked tests; flag for live UAT only).
- Any deviations from this plan.
</output>
