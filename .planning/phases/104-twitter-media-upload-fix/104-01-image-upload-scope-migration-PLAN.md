---
phase: 104-twitter-media-upload-fix
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/connector.py
  - app/social/publisher.py
  - supabase/migrations/20260508130000_twitter_reconnect_required.sql
  - tests/unit/test_twitter_publisher.py
  - tests/unit/test_social_connector_security.py
  - tests/smoke/__init__.py
  - tests/smoke/test_twitter_live.py
autonomous: true
requirements: [POST-04, POST-06]

must_haves:
  truths:
    - "Twitter OAuth2 PKCE scope list includes media.write (required for v2 media upload)"
    - "Posting an image to Twitter issues exactly one POST to https://api.x.com/2/media/upload (multipart, media_category=tweet_image) followed by exactly one POST to https://api.twitter.com/2/tweets with media.media_ids=[<id>]"
    - "The fictional source_url form field is absent from the Twitter branch of app/social/publisher.py"
    - "Existing Twitter connections are marked status='reconnect_required' so the frontend can prompt re-authorization with the new scope"
    - "A 403 from Twitter media upload surfaces a user-friendly error directing the user to reconnect, not a generic 500"
    - "_upload_video_twitter exists as a stub raising NotImplementedError — Plan 104-02 fills it in"
  artifacts:
    - path: "app/social/connector.py"
      provides: "PLATFORM_CONFIGS['twitter']['scopes'] contains 'media.write'; get_access_token treats 'reconnect_required' status the same as 'revoked' (returns None)"
      contains: "media.write"
    - path: "app/social/publisher.py"
      provides: "_upload_image_twitter (simple multipart POST to api.x.com/2/media/upload), _upload_video_twitter stub, refactored Twitter branch in post_with_media that dispatches by media_type and surfaces 403 reconnect message"
      contains: "_upload_image_twitter"
    - path: "supabase/migrations/20260508130000_twitter_reconnect_required.sql"
      provides: "One-shot UPDATE marking all platform='twitter' rows status='reconnect_required'"
      contains: "UPDATE connected_accounts"
    - path: "tests/unit/test_twitter_publisher.py"
      provides: "TestImageUpload (happy path), TestNoFictionalSourceUrl (grep absence), TestAuthErrorMessage (403 reconnect prompt), TestVideoStubRaises (NotImplementedError until 104-02)"
      contains: "test_image_simple_upload"
    - path: "tests/unit/test_social_connector_security.py"
      provides: "test_twitter_scopes asserting media.write present"
      contains: "test_twitter_scopes"
    - path: "tests/smoke/__init__.py"
      provides: "Empty package marker for the new smoke test directory"
    - path: "tests/smoke/test_twitter_live.py"
      provides: "Gated (RUN_LIVE=1) live tests; test_image_post posts a real 4MB JPEG to a sandbox X account and asserts the tweet has the image"
      contains: "RUN_LIVE"
  key_links:
    - from: "app/social/publisher.py:post_with_media (twitter branch)"
      to: "app/social/publisher.py:_upload_image_twitter"
      via: "media_type-dispatch when has_media and media_type in {'image','carousel','gif'}"
      pattern: "_upload_image_twitter"
    - from: "app/social/publisher.py:_upload_image_twitter"
      to: "https://api.x.com/2/media/upload"
      via: "multipart POST with files={'media': ...}, data={'media_category': 'tweet_image'}"
      pattern: "api\\.x\\.com/2/media/upload"
    - from: "app/social/connector.py:PLATFORM_CONFIGS"
      to: "OAuth2 authorization URL"
      via: "scopes list joined with space and url-encoded into the &scope= query param at get_authorization_url"
      pattern: "media\\.write"
    - from: "supabase/migrations/20260508130000_twitter_reconnect_required.sql"
      to: "frontend reconnect UI"
      via: "connected_accounts.status = 'reconnect_required' on existing rows; get_access_token returns None for non-active status, triggering existing 'No active connection' error path"
      pattern: "reconnect_required"
---

<objective>
Migrate the Twitter publisher's media upload from the dead v1.1 endpoint to the v2 simple upload endpoint, add the missing `media.write` OAuth2 scope, and ship the database migration that forces existing Twitter connections to re-authorize. Replace the broken `_upload_media_twitter` (publisher.py:43-63) with a working `_upload_image_twitter` for images and a stub `_upload_video_twitter` (filled in by Plan 104-02). Delete the fictional `source_url` form field. Add a clear reconnect-required error path for OAuth2 403s. Wave 0 scaffolds the failing tests; Wave 1 turns them green.

Purpose: Satisfy POST-04 (image upload happy path + tweet attach) and POST-06 (auth strategy + scope decision documented and enforced). Unblocks Plan 104-02 (video chunked upload) which depends on the new scope being live and the dispatch in `post_with_media` already routing by `media_type`.

Output: A Twitter post with an image attached produces exactly two HTTP calls (one media upload, one tweet POST), the resulting `media_id` is attached, the tweet renders the image. Existing Twitter users are nudged to reconnect on next post (clear error message). All Wave 0 tests are GREEN; `source_url` literal is gone from the Twitter branch.
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
@app/social/connector.py
@app/social/publisher.py
@tests/unit/test_social_connector_security.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase + RESEARCH.md. -->
<!-- Use these directly — no codebase exploration needed. -->

From app/social/connector.py (current shape — DO NOT regress):
```python
PLATFORM_CONFIGS = {
    ...
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access"],  # << ADD "media.write"
        "client_id_env": "TWITTER_CLIENT_ID",
        "client_secret_env": "TWITTER_CLIENT_SECRET",
    },
    ...
}

class SocialConnector:
    def get_access_token(self, user_id: str, platform: str) -> str | None:
        # Currently filters .eq("status", "active"). After this plan, accounts
        # marked 'reconnect_required' must NOT yield a token (same as 'revoked').
        # The existing .eq("status", "active") filter already produces the
        # correct behavior — no code change needed in get_access_token; only
        # the migration flips status. Verify with a unit test.
        ...
```

From app/social/publisher.py (current Twitter branch — to be replaced):
```python
# Lines 43-63 — DELETE
async def _upload_media_twitter(self, http, headers, media_url, media_type) -> str | None:
    init_resp = await http.post(
        "https://upload.twitter.com/1.1/media/upload.json",  # DEAD
        headers=headers,
        data={
            "command": "INIT",
            "media_type": "video/mp4" if media_type == "video" else "image/jpeg",
            "media_category": "tweet_video" if media_type == "video" else "tweet_image",
            "source_url": media_url,  # FICTIONAL
        },
    )
    if init_resp.status_code not in [200, 201, 202]:
        logger.warning("Twitter media INIT failed: %s", init_resp.text)
        return None
    return init_resp.json().get("media_id_string")

# Lines 117-134 — Twitter branch in post_with_media
if platform == "twitter":
    tweet_payload: dict[str, Any] = {"text": content}
    if has_media:
        media_id = await self._upload_media_twitter(http, headers, media_urls[0], media_type)
        if media_id:
            tweet_payload["media"] = {"media_ids": [media_id]}
    resp = await http.post(
        "https://api.twitter.com/2/tweets",
        headers=headers,
        json=tweet_payload,
    )
```

Target shape (this plan):
```python
async def _upload_image_twitter(
    self, http, headers: dict, media_url: str
) -> str | None:
    """Simple-shot image upload to X v2. Returns media_id or None on failure."""
    img_resp = await http.get(media_url)
    img_resp.raise_for_status()
    img_bytes = img_resp.content
    mime = img_resp.headers.get("content-type", "image/jpeg").split(";")[0].strip() or "image/jpeg"

    if len(img_bytes) > 5 * 1024 * 1024:
        logger.warning(
            "Twitter image %s is %d bytes (>5MB); v2 simple upload will reject. "
            "Caller should resize or use video chunked path.",
            media_url, len(img_bytes),
        )
        return None

    upload_resp = await http.post(
        "https://api.x.com/2/media/upload",
        headers=headers,
        files={"media": ("upload", img_bytes, mime)},
        data={"media_category": "tweet_image"},
    )
    if upload_resp.status_code == 403:
        logger.warning(
            "Twitter media upload returned 403 — token likely lacks media.write scope. "
            "User must reconnect. Body: %s", upload_resp.text,
        )
        return None
    if upload_resp.status_code not in (200, 201):
        logger.warning("Twitter image upload failed (%d): %s", upload_resp.status_code, upload_resp.text)
        return None

    body = upload_resp.json()
    return body.get("data", {}).get("id") or body.get("media_id_string")


async def _upload_video_twitter(
    self, http, headers: dict, media_url: str
) -> str | None:
    """Chunked video upload — implemented in Plan 104-02."""
    raise NotImplementedError(
        "Twitter video chunked upload is implemented in Plan 104-02"
    )


# post_with_media Twitter branch
if platform == "twitter":
    tweet_payload: dict[str, Any] = {"text": content}
    if has_media:
        if media_type == "video":
            try:
                media_id = await self._upload_video_twitter(http, headers, media_urls[0])
            except NotImplementedError as exc:
                return {"error": f"Twitter video upload not yet available: {exc}"}
        else:
            media_id = await self._upload_image_twitter(http, headers, media_urls[0])
        if not media_id:
            return {
                "error": (
                    "Twitter media upload failed. If you previously connected your "
                    "Twitter account, please reconnect to grant the new media.write "
                    "permission."
                )
            }
        tweet_payload["media"] = {"media_ids": [media_id]}
    resp = await http.post(
        "https://api.twitter.com/2/tweets",
        headers={**headers, "Content-Type": "application/json"},
        json=tweet_payload,
    )
```

From tests/unit/test_social_connector_security.py (existing test file — extend, do not rewrite):
```python
# Existing fakes _Result, _FakeTable, _FakeClient already wire upsert/select/eq/execute
# for connected_accounts and oauth_pkce_states. Reuse for the new test.
from app.social.connector import SocialConnector, PLATFORM_CONFIGS

def test_twitter_scopes():
    """POST-06: media.write must be present in the Twitter OAuth2 scope list."""
    scopes = PLATFORM_CONFIGS["twitter"]["scopes"]
    assert "media.write" in scopes
    # Sanity: the existing scopes are still there
    for required in ("tweet.read", "tweet.write", "users.read", "offline.access"):
        assert required in scopes
```

From RESEARCH.md §"Common Pitfalls" (do not repeat):
- Pitfall 1: Forgetting `media.write` scope — addressed by this plan.
- Pitfall 2: Wrong host (`api.twitter.com` vs `api.x.com` for media). Use `api.x.com` for `/2/media/upload`.
- Pitfall 6: Re-downloading media. Acceptable — caller passes URL, helper fetches once.

Test fixture conventions (from existing test files):
- `unittest.mock.AsyncMock` for httpx.AsyncClient methods.
- Pattern: build a `MagicMock` with `status_code=200`, `text="..."`, `json=lambda: {...}`, `content=b"..."`, `headers={...}`. Wire it as the `return_value` of an `AsyncMock`.
- Use `caplog.set_level(logging.WARNING, logger="app.social.publisher")` to capture the warning lines.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave-0 RED — scaffold failing tests for image upload, scope check, and reconnect error path</name>
  <files>tests/unit/test_twitter_publisher.py, tests/unit/test_social_connector_security.py, tests/smoke/__init__.py, tests/smoke/test_twitter_live.py</files>
  <behavior>
    Add 6 new failing unit tests + 1 smoke test stub. ALL unit tests must FAIL initially (RED) — they assert behavior not yet in publisher.py / connector.py. The smoke test must be SKIPPED by default (gated by `RUN_LIVE=1`); when `RUN_LIVE` is unset, `pytest tests/smoke -x` exits 0 with all tests skipped.

    **A. Create `tests/unit/test_twitter_publisher.py`** with module-level imports:

    ```python
    from __future__ import annotations
    import logging
    from unittest.mock import AsyncMock, MagicMock, patch
    import pytest
    ```

    Add 4 new test classes:

    **TestImageUpload:**
    - `test_image_simple_upload` — Build a `SocialPublisher`, patch `connector.get_access_token` to return `"FAKE_TOKEN"`, patch `httpx.AsyncClient` so the `__aenter__` mock returns an object whose:
        - First call (the bytes fetch via `http.get(media_url)`) returns `MagicMock(status_code=200, content=b"x" * 4_000_000, headers={"content-type": "image/jpeg"})` and `raise_for_status` is a no-op.
        - Second call (`http.post("https://api.x.com/2/media/upload", ...)`) returns `MagicMock(status_code=200, text="ok", json=lambda: {"data": {"id": "MEDIA_ID_123"}})`.
        - Third call (`http.post("https://api.twitter.com/2/tweets", ...)`) returns `MagicMock(status_code=201, text="ok", json=lambda: {"data": {"id": "TWEET_ID"}})`.
      Call `await publisher.post_with_media(user_id="u1", platform="twitter", content="hello world", media_urls=["https://example.test/photo.jpg"], media_type="image")`.
      Assert:
        - `http.post.call_count == 2` (one media upload, one tweet POST).
        - First `http.post` call args[0] == `"https://api.x.com/2/media/upload"`; kwargs contain `files` with key `"media"` and `data == {"media_category": "tweet_image"}`.
        - Second `http.post` call args[0] == `"https://api.twitter.com/2/tweets"`; the JSON body equals `{"text": "hello world", "media": {"media_ids": ["MEDIA_ID_123"]}}`.
        - The `Authorization` header on both calls equals `"Bearer FAKE_TOKEN"`.

    - `test_image_simple_upload_too_large_returns_error` — Same setup but the bytes-fetch returns `content=b"x" * (5 * 1024 * 1024 + 1)` (5MB + 1 byte). Assert:
        - The publisher's return dict contains `"error"` (matches the reconnect-required copy: substring `"Twitter media upload failed"`).
        - `http.post` to `api.x.com/2/media/upload` is NEVER called (size guard rejects before upload).
        - `http.post` to `/2/tweets` is NEVER called.
        - A WARNING is logged containing the substring `">5MB"`.

    **TestAuthErrorMessage:**
    - `test_403_returns_reconnect_message` — Same setup but the `http.post` to `/2/media/upload` returns `status_code=403, text="missing scope: media.write"`. Assert:
        - `result["error"]` contains the substring `"reconnect"` (case-insensitive ok).
        - The tweet POST is NEVER called (failed media upload short-circuits).
        - A WARNING is logged containing both `"403"` and `"media.write"`.

    **TestNoFictionalSourceUrl:**
    - `test_no_fictional_source_url_in_twitter_branch` — A grep-style test:
      ```python
      from pathlib import Path
      src = Path("app/social/publisher.py").read_text(encoding="utf-8")
      # Slice to just the Twitter branch (between "TWITTER / X" comment and "LINKEDIN" comment)
      twitter_section = src.split("# ----- TWITTER / X -----", 1)[1].split("# ----- LINKEDIN -----", 1)[0]
      assert "source_url" not in twitter_section, (
          "Phase 104: source_url is fictional and must not appear in the Twitter branch"
      )
      assert "_upload_image_twitter" in twitter_section
      assert "upload.twitter.com" not in twitter_section
      assert "api.x.com/2/media/upload" in src  # appears at least once in the helper
      ```
      *(Note: scoped to the Twitter branch only because YouTube branch line 329 still references `source_url` until Phase 105.)*

    **TestVideoStubRaises:**
    - `test_video_path_returns_not_yet_available_error` — Same setup with `media_type="video"`. Patch `_upload_video_twitter` is NOT necessary; rely on the stub raising NotImplementedError. Assert:
        - `result["error"]` contains the substring `"not yet available"`.
        - The tweet POST is NEVER called.

    **B. Extend `tests/unit/test_social_connector_security.py`** with one new test:

    ```python
    def test_twitter_scopes():
        """POST-06: media.write must be present in the Twitter OAuth2 scope list."""
        from app.social.connector import PLATFORM_CONFIGS
        scopes = PLATFORM_CONFIGS["twitter"]["scopes"]
        assert "media.write" in scopes, (
            "Phase 104 / POST-06: OAuth2 token must request media.write to upload "
            "media via /2/media/upload"
        )
        for required in ("tweet.read", "tweet.write", "users.read", "offline.access"):
            assert required in scopes
    ```

    Place it at module level (not inside a class) to match the file's existing top-level test layout.

    **C. Create `tests/smoke/__init__.py`** (empty file, package marker).

    **D. Create `tests/smoke/test_twitter_live.py`** with one skipped test:

    ```python
    """Live smoke tests for Twitter publisher (Phase 104).

    Gated by RUN_LIVE=1 to keep CI hermetic. Requires:
      - TWITTER_TEST_USER_ID env var (a connected pikar-ai user with active twitter row)
      - TWITTER_TEST_IMAGE_URL env var (a public 4MB JPEG)
      - The connected account must be on a paid X tier (free tier rate-limit is ~17/24h)
    """
    from __future__ import annotations
    import os
    import pytest

    pytestmark = pytest.mark.skipif(
        os.environ.get("RUN_LIVE") != "1",
        reason="Live smoke tests gated by RUN_LIVE=1",
    )

    @pytest.mark.asyncio
    async def test_image_post():
        """POST-04 success criterion 1: 4MB JPEG attached to live tweet."""
        from app.social.publisher import SocialPublisher
        user_id = os.environ["TWITTER_TEST_USER_ID"]
        image_url = os.environ["TWITTER_TEST_IMAGE_URL"]
        result = await SocialPublisher().post_with_media(
            user_id=user_id, platform="twitter",
            content=f"Phase 104 image smoke test {os.urandom(4).hex()}",
            media_urls=[image_url], media_type="image",
        )
        assert "error" not in result, f"Live tweet failed: {result}"
        # Tweet response shape: {"data": {"id": "...", "text": "..."}}
        # Detailed shape assertion is defensive — adapt if X changes the envelope.
    ```

    **Verify (RED state):** Run `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py::test_twitter_scopes -x 2>&1 | tail -40`. Expected: 6 unit tests fail with assertion errors / module errors referencing the missing helpers and missing scope. Then run `uv run pytest tests/smoke/ -x` — expect "all skipped" (RUN_LIVE not set).

    Commit message: `test(104-01): add failing tests for Twitter v2 media upload + media.write scope (POST-04, POST-06)`.
  </behavior>
  <action>
    1. Create `tests/unit/test_twitter_publisher.py` with the 4 test classes / 4 tests above plus the grep test (5 unit tests). Use `unittest.mock.AsyncMock` and `MagicMock`; do NOT introduce `respx` (not yet a dep). Use the `caplog` fixture for warning-log assertions:
       `with caplog.at_level(logging.WARNING, logger="app.social.publisher"):`.

       For mocking `httpx.AsyncClient` use:
       ```python
       fake_client = MagicMock()
       fake_client.get = AsyncMock(side_effect=[fake_get_response])
       fake_client.post = AsyncMock(side_effect=[fake_upload_response, fake_tweet_response])
       fake_async_client = MagicMock()
       fake_async_client.__aenter__ = AsyncMock(return_value=fake_client)
       fake_async_client.__aexit__ = AsyncMock(return_value=None)
       with patch("httpx.AsyncClient", return_value=fake_async_client):
           ...
       ```

       Patch `SocialPublisher().connector.get_access_token` to return `"FAKE_TOKEN"`:
       ```python
       publisher = SocialPublisher()
       publisher.connector = MagicMock()
       publisher.connector.get_access_token.return_value = "FAKE_TOKEN"
       ```

    2. Append `test_twitter_scopes` to `tests/unit/test_social_connector_security.py` at module level (not inside a class). Match the file's import style (`from app.social.connector import ...` at the top of the file).

    3. Create `tests/smoke/__init__.py` (empty file).

    4. Create `tests/smoke/test_twitter_live.py` exactly as specified above; the gating decorator must reference env var `RUN_LIVE` (not a pytest marker — markers would require pyproject.toml registration).

    5. Run `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py -x 2>&1 | tail -50` and confirm:
        - `test_twitter_scopes` FAILS with `AssertionError: assert "media.write" in [...]`.
        - 5 publisher tests FAIL — most likely with `AttributeError: '_upload_image_twitter'` or assertions on the deleted `source_url` literal (still present, so the grep test will FAIL too).

    6. Run `uv run pytest tests/smoke/ -x` and confirm "1 skipped" exit 0.

    7. Do NOT modify production code in this task.

    8. `git add` and commit with the message above.

    Lint: `uv run ruff check tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py tests/smoke/test_twitter_live.py --fix && uv run ruff format tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py tests/smoke/test_twitter_live.py`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py::test_twitter_scopes -x 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    `tests/unit/test_twitter_publisher.py` exists with 5 failing tests across 4 classes. `tests/unit/test_social_connector_security.py` has a new `test_twitter_scopes` that fails. `tests/smoke/__init__.py` exists. `tests/smoke/test_twitter_live.py` exists and is fully skipped without `RUN_LIVE=1`. All ruff/format clean. Commit `test(104-01): add failing tests for Twitter v2 media upload + media.write scope (POST-04, POST-06)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wave-1 GREEN — add media.write scope, ship reconnect migration, replace _upload_media_twitter with _upload_image_twitter + video stub</name>
  <files>app/social/connector.py, app/social/publisher.py, supabase/migrations/20260508130000_twitter_reconnect_required.sql</files>
  <behavior>
    After this task: all 6 Wave-0 unit tests are GREEN. All existing tests in `tests/unit/test_social_connector_security.py` and `tests/unit/` still pass (regression).

    **A. `app/social/connector.py:44`** — Append `"media.write"` to the Twitter scopes list:
    ```python
    "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access", "media.write"],
    ```
    No other changes to connector.py. The existing `get_access_token` filter `.eq("status", "active")` already excludes `reconnect_required` rows; verify this with the existing fake-table tests by running `uv run pytest tests/unit/test_social_connector_security.py -x`.

    **B. `app/social/publisher.py`** — Replace lines 43-63 (`_upload_media_twitter`) with two new helpers, and replace lines 117-134 (Twitter branch in `post_with_media`) with the dispatch shown in the interfaces block:

    1. **DELETE** `_upload_media_twitter` entirely.

    2. **ADD** `_upload_image_twitter`:
       ```python
       async def _upload_image_twitter(
           self, http, headers: dict, media_url: str
       ) -> str | None:
           """Simple-shot image upload to X v2 (≤5MB).

           Returns the media_id string on success, None on any failure
           (logged at WARNING). 403s are treated as a likely missing-scope
           condition and the caller surfaces a reconnect prompt.
           """
           img_resp = await http.get(media_url)
           img_resp.raise_for_status()
           img_bytes = img_resp.content
           mime = (
               img_resp.headers.get("content-type", "image/jpeg")
               .split(";")[0]
               .strip()
               or "image/jpeg"
           )

           if len(img_bytes) > 5 * 1024 * 1024:
               logger.warning(
                   "Twitter image %s is %d bytes (>5MB); v2 simple upload will reject. "
                   "Resize the image or use the video chunked path.",
                   media_url,
                   len(img_bytes),
               )
               return None

           upload_resp = await http.post(
               "https://api.x.com/2/media/upload",
               headers=headers,
               files={"media": ("upload", img_bytes, mime)},
               data={"media_category": "tweet_image"},
           )
           if upload_resp.status_code == 403:
               logger.warning(
                   "Twitter media upload returned 403 — token likely lacks "
                   "media.write scope. User must reconnect. Body: %s",
                   upload_resp.text,
               )
               return None
           if upload_resp.status_code not in (200, 201):
               logger.warning(
                   "Twitter image upload failed (%d): %s",
                   upload_resp.status_code,
                   upload_resp.text,
               )
               return None

           body = upload_resp.json()
           return body.get("data", {}).get("id") or body.get("media_id_string")
       ```

    3. **ADD** `_upload_video_twitter` stub (Plan 104-02 fills it in):
       ```python
       async def _upload_video_twitter(
           self, http, headers: dict, media_url: str
       ) -> str | None:
           """Chunked video upload to X v2.

           Implemented in Plan 104-02 (INIT → APPEND → FINALIZE → STATUS).
           Stubbed here so Plan 104-01 can ship the dispatch path.
           """
           raise NotImplementedError(
               "Twitter video chunked upload is implemented in Plan 104-02"
           )
       ```

    4. **REPLACE** the Twitter branch in `post_with_media` (was lines 117-134):
       ```python
       if platform == "twitter":
           tweet_payload: dict[str, Any] = {"text": content}
           if has_media:
               if media_type == "video":
                   try:
                       media_id = await self._upload_video_twitter(
                           http, headers, media_urls[0]
                       )
                   except NotImplementedError as exc:
                       return {"error": f"Twitter video upload not yet available: {exc}"}
               else:
                   media_id = await self._upload_image_twitter(
                       http, headers, media_urls[0]
                   )
               if not media_id:
                   return {
                       "error": (
                           "Twitter media upload failed. If you previously connected "
                           "your Twitter account, please reconnect to grant the new "
                           "media.write permission."
                       )
                   }
               tweet_payload["media"] = {"media_ids": [media_id]}
           resp = await http.post(
               "https://api.twitter.com/2/tweets",
               headers={**headers, "Content-Type": "application/json"},
               json=tweet_payload,
           )
       ```

    Project rules: no `print`; no bare `except` (use `except Exception` if needed — no new ones in this task); no mutable default args.

    **C. `supabase/migrations/20260508130000_twitter_reconnect_required.sql`** — One-shot migration:
    ```sql
    -- Phase 104 (POST-06): Twitter OAuth2 scope expanded to include media.write.
    -- Existing tokens were issued without that scope and cannot upload media.
    -- Mark all existing twitter rows for re-authorization. The frontend already
    -- treats non-active status as "Click to connect" / "Reconnect".
    --
    -- Idempotent: only flips rows currently active. Does NOT touch rows that
    -- the user has already manually revoked.
    UPDATE connected_accounts
    SET status = 'reconnect_required'
    WHERE platform = 'twitter'
      AND status = 'active';

    COMMENT ON COLUMN connected_accounts.status IS
      'One of: active, revoked, reconnect_required. Phase 104 added '
      'reconnect_required to flag accounts whose token scope is stale.';
    ```

    Run `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py -x` and confirm all 6 new tests + all existing tests pass.

    Lint: `uv run ruff check app/social/ --fix && uv run ruff format app/social/ && uv run ty check app/social/connector.py app/social/publisher.py`.

    Commit message: `feat(104-01): migrate Twitter image upload to v2 endpoint, add media.write scope, ship reconnect migration (POST-04, POST-06)`.
  </behavior>
  <action>
    1. Edit `app/social/connector.py` line 44 — append `"media.write"` to the scopes list. No other edits.

    2. Edit `app/social/publisher.py`:
       - Delete `_upload_media_twitter` (lines 43-63).
       - Insert `_upload_image_twitter` and `_upload_video_twitter` in the same `# Internal helpers` section (after `_get_token_or_error`).
       - Replace the Twitter branch inside `post_with_media` with the dispatch above (find by the `# ----- TWITTER / X -----` comment).
       - Keep the `# ----- TWITTER / X -----` and `# ----- LINKEDIN -----` comment markers — the grep test relies on them.

    3. Create `supabase/migrations/20260508130000_twitter_reconnect_required.sql` with the SQL above. Filename uses today's UTC date (2026-05-08) at 13:00:00 to land just after the latest existing migration `20260508123000_social_oauth_security.sql`.

    4. Run `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py -x 2>&1 | tail -30` — confirm all 6 GREEN.

    5. Regression: `uv run pytest tests/unit -x --ignore=tests/unit/admin 2>&1 | tail -20` (skip admin which has its own conftest). Confirm no new failures vs baseline.

    6. Lint: `uv run ruff check app/social/ tests/unit/test_twitter_publisher.py --fix && uv run ruff format app/social/ tests/unit/test_twitter_publisher.py && uv run ty check app/social/connector.py app/social/publisher.py`.

    7. Commit `feat(104-01): ...` with the files above.

    NOTE on migration application: this plan does NOT run `supabase db push` — that is a deploy-time step. The SQL file landing in `supabase/migrations/` is sufficient; the next prod migration cycle picks it up. Document this in the SUMMARY so the deployer knows.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py -x 2>&amp;1 | tail -25 &amp;&amp; uv run ruff check app/social/ 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    All 6 Wave-0 unit tests are GREEN. Existing tests in `tests/unit/test_social_connector_security.py` (and the broader unit suite excluding admin) still pass. `app/social/publisher.py` no longer contains `_upload_media_twitter`, no longer references `upload.twitter.com`, no longer references `source_url` in the Twitter branch. `app/social/connector.py:44` includes `"media.write"`. `supabase/migrations/20260508130000_twitter_reconnect_required.sql` exists. `ruff check` and `ty check` clean. Commit `feat(104-01): migrate Twitter image upload to v2 endpoint, add media.write scope, ship reconnect migration (POST-04, POST-06)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end (CI-safe): `uv run pytest tests/unit/test_twitter_publisher.py tests/unit/test_social_connector_security.py -x` → all GREEN.

Smoke (manual, gated): `RUN_LIVE=1 TWITTER_TEST_USER_ID=<id> TWITTER_TEST_IMAGE_URL=<url> uv run pytest tests/smoke/test_twitter_live.py::test_image_post -x`. Requires a connected paid-tier X account that has been re-authorized post-migration. Defer to phase-level UAT.

Regression: `uv run pytest tests/unit -x --ignore=tests/unit/admin` — no new failures vs baseline.

Migration: filename `20260508130000_twitter_reconnect_required.sql` exists in `supabase/migrations/`. Applied by the next deploy's migration step (not by this plan).
</verification>

<success_criteria>
- `app/social/connector.py:44` `PLATFORM_CONFIGS["twitter"]["scopes"]` contains `"media.write"`.
- `app/social/publisher.py` no longer defines `_upload_media_twitter`; defines `_upload_image_twitter` (working) and `_upload_video_twitter` (raises NotImplementedError).
- The Twitter branch of `app/social/publisher.py` does NOT contain `source_url` or `upload.twitter.com`. Verifiable by the `test_no_fictional_source_url_in_twitter_branch` grep test.
- `_upload_image_twitter` issues exactly one POST to `https://api.x.com/2/media/upload` with `multipart` body containing `media` (binary) and `media_category=tweet_image`.
- A 403 from the upload endpoint produces a user-facing error containing the word "reconnect"; the tweet POST is not attempted.
- `supabase/migrations/20260508130000_twitter_reconnect_required.sql` exists and updates `connected_accounts.status` from `active` → `reconnect_required` for `platform='twitter'`.
- 5 new tests in `tests/unit/test_twitter_publisher.py` pass + 1 new test (`test_twitter_scopes`) in `tests/unit/test_social_connector_security.py` passes.
- `tests/smoke/test_twitter_live.py` is skipped without `RUN_LIVE=1`.
- `ruff check` and `ty check` clean for touched files.
</success_criteria>

<output>
After completion, create `.planning/phases/104-twitter-media-upload-fix/104-01-image-upload-scope-migration-SUMMARY.md` documenting:
- Exact line numbers of the new `_upload_image_twitter` and `_upload_video_twitter` helpers.
- Confirmation that the migration file landed in `supabase/migrations/` but was NOT applied by this plan (deployer applies on next cycle).
- Test count delta (new file `test_twitter_publisher.py`: 5 tests; extended `test_social_connector_security.py`: +1 test).
- Whether any frontend copy update was needed for the `reconnect_required` status (per CONTEXT, the existing `connected: false` rendering in `frontend/src/app/dashboard/configuration/page.tsx:290` already covers it; if executor confirms, document "no frontend change").
- Open question status: APPEND endpoint shape — N/A for image plan, deferred to Plan 104-02.
</output>
