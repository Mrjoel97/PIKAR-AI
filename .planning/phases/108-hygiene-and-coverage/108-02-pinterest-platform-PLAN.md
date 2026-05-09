---
phase: 108-hygiene-and-coverage
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - .env.example
  - app/social/connector.py
  - app/social/publisher.py
  - app/agents/tools/social.py
  - supabase/migrations/20260509000100_pinterest_platform.sql
  - tests/unit/social/test_connector_callback.py
  - tests/unit/social/test_publisher_per_platform.py
autonomous: true
requirements: [HYGIENE-02]

must_haves:
  truths:
    - "User can initiate a Pinterest OAuth flow: get_oauth_url(platform='pinterest', user_id=...) returns an authorization URL pointing at https://www.pinterest.com/oauth/ with PINTEREST_CLIENT_ID and the boards:read + pins:write + user_accounts:read scopes"
    - "Pinterest OAuth callback exchanges the authorization code at https://api.pinterest.com/v5/oauth/token using HTTP Basic auth (Authorization: Basic base64(client_id:client_secret)) — NOT body-encoded credentials — and upserts the connection"
    - "When the Pinterest token response does not include user_id, handle_callback issues a follow-up GET https://api.pinterest.com/v5/user_account with the bearer token and stores the returned 'username' field as platform_username"
    - "Marketing/Content agent can create a pin: publish_to_social(platform='pinterest', content='caption', media_url='https://...jpg', media_type='image', extra={'board_id':'BOARD_X'}) issues ONE POST to https://api.pinterest.com/v5/pins with JSON body containing board_id, title (≤100 chars), description (≤500 chars), media_source.source_type='image_url', media_source.url=<media_url>"
    - "If extra['board_id'] is missing, publisher returns a structured error 'Pinterest requires a board_id; pass via extra={\"board_id\":...}' WITHOUT making any HTTP call"
    - "If no media_url is provided, publisher returns a structured error 'Pinterest pins require an image URL' WITHOUT making any HTTP call"
    - "publish_to_social tool signature accepts an optional extra: dict[str, Any] | None = None param and forwards it to post_with_media"
    - "_refresh_token branches on auth_method: form-encoded credentials in body for 'form' platforms, HTTP Basic header for 'basic' platforms"
    - "supabase 'platform' CHECK constraint accepts 'pinterest'"
  artifacts:
    - path: ".env.example"
      provides: "PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET documented with link to Pinterest developer dashboard"
      contains: "PINTEREST_CLIENT_ID"
    - path: "app/social/connector.py"
      provides: "PLATFORM_CONFIGS['pinterest'] entry with auth_method='basic'; handle_callback branches on auth_method to send Basic auth or form auth; follow-up /v5/user_account call for platform_username; _refresh_token also branches on auth_method"
      contains: "pinterest.com/oauth"
    - path: "app/social/publisher.py"
      provides: "post_with_media gains optional `extra: dict[str, Any] | None = None` param; pinterest branch issues single POST to /v5/pins with structured JSON body"
      contains: "api.pinterest.com/v5/pins"
    - path: "app/agents/tools/social.py"
      provides: "publish_to_social tool gains `extra` kwarg forwarded to post_with_media; docstring mentions Pinterest's board_id requirement"
      contains: "extra: dict[str, Any] | None"
    - path: "supabase/migrations/20260509000100_pinterest_platform.sql"
      provides: "Adds 'pinterest' to connected_accounts platform CHECK constraint"
      contains: "ADD CONSTRAINT connected_accounts_platform_check"
    - path: "tests/unit/social/test_connector_callback.py"
      provides: "Pinterest callback tests: state round-trip, Basic-auth header on token exchange, follow-up /v5/user_account call when token response lacks user_id, platform_username captured"
      contains: "test_pinterest_callback"
    - path: "tests/unit/social/test_publisher_per_platform.py"
      provides: "Pinterest publisher tests: post_pin success, missing board_id, missing media_url, no token, API error 4xx"
      contains: "test_pinterest_post"
  key_links:
    - from: "app/social/connector.py:handle_callback"
      to: "https://api.pinterest.com/v5/oauth/token"
      via: "When config['auth_method'] == 'basic', send credentials via httpx auth=(client_id, client_secret) instead of body fields client_id/client_secret"
      pattern: "auth_method"
    - from: "app/social/connector.py:handle_callback"
      to: "https://api.pinterest.com/v5/user_account"
      via: "Best-effort follow-up GET when platform_user_id/platform_username missing from token response; failure is non-blocking"
      pattern: "user_account"
    - from: "app/social/publisher.py:post_with_media (pinterest branch)"
      to: "extra['board_id'] from caller"
      via: "Required field; missing → structured error; present → JSON body 'board_id' field on /v5/pins"
      pattern: "board_id"
    - from: "app/agents/tools/social.py:publish_to_social"
      to: "app/social/publisher.py:post_with_media"
      via: "extra kwarg forwarded as-is into post_with_media call (only Pinterest reads it today)"
      pattern: "extra=extra"
---

<objective>
Add Pinterest as a new platform: separate OAuth client (`PINTEREST_CLIENT_ID`/`SECRET`), HTTP Basic-auth at the token endpoint (RFC 6749-strict), follow-up `/v5/user_account` call to capture `platform_username`, and a single-POST pin creation flow against `POST /v5/pins`. Wire an `extra: dict | None` kwarg through `publish_to_social → post_with_media` so callers can pass `{"board_id": "..."}` (Pinterest requires it; other platforms ignore it). Add `'pinterest'` to the `connected_accounts` platform CHECK constraint via SQL migration.

Purpose: Satisfy HYGIENE-02 ("User can connect Pinterest accounts and the Marketing agent can post pins"). Resolves the auth-method drift between Pinterest (Basic-auth, RFC 6749) and existing platforms (body-encoded credentials) by adding an `auth_method` discriminator to `PLATFORM_CONFIGS`.

Output: `'pinterest'` end-to-end through `connector → publisher → SOCIAL_TOOLS`. Pin creation via `publish_to_social(platform="pinterest", content="caption", media_url="https://cdn/img.jpg", media_type="image", extra={"board_id":"BOARD_X"})` lands a real pin and returns `{success: true, post_id: <pin_id>, ...}`. The `auth_method` discriminator and `extra` kwarg are general-purpose — both 108-04 (revoke endpoint dispatcher) and any future platform with non-standard auth or required platform-specific fields will reuse them.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/108-hygiene-and-coverage/108-CONTEXT.md
@.planning/phases/108-hygiene-and-coverage/108-RESEARCH.md
@app/social/connector.py
@app/social/publisher.py
@app/agents/tools/social.py
@supabase/migrations/0010_connected_accounts.sql
@supabase/migrations/20260320000000_social_analytics_listening.sql

<interfaces>
<!-- Key contracts the executor needs. Use these directly. -->

Pinterest API contract (verified 2026-05-08):
- Auth: `https://www.pinterest.com/oauth/?client_id=...&redirect_uri=...&response_type=code&scope=boards%3Aread+pins%3Awrite+user_accounts%3Aread&state=...&code_challenge=...&code_challenge_method=S256`
- Token exchange: `POST https://api.pinterest.com/v5/oauth/token`
  - Headers: `Authorization: Basic base64(client_id:client_secret)`, `Content-Type: application/x-www-form-urlencoded`
  - Body: `grant_type=authorization_code&code=...&redirect_uri=...&code_verifier=...` (NO client_id/client_secret in body — Pinterest rejects)
  - Response: `{"access_token":"...", "refresh_token":"...", "expires_in":2592000, "token_type":"bearer", "scope":"boards:read pins:write user_accounts:read"}` — note: NO user_id field, must follow up.
- User profile: `GET https://api.pinterest.com/v5/user_account` with `Authorization: Bearer <access_token>` → `{"account_type":"BUSINESS","profile_image":"...","website_url":"...","username":"<username>"}`. Use `username` as `platform_username`.
- Create pin: `POST https://api.pinterest.com/v5/pins` with `Authorization: Bearer <token>` and JSON body:
  ```json
  {
    "board_id": "<required>",
    "title": "<≤100 chars>",
    "description": "<≤500 chars>",
    "media_source": {"source_type": "image_url", "url": "<public-image-url>"}
  }
  ```
  Response: `201 Created` with `{"id": "<pin-id>", ...}`.

Existing post_with_media signature (publisher.py:84-91) — SHIP-COMPATIBLE EXTENSION:
```python
async def post_with_media(
    self, user_id: str, platform: str, content: str,
    media_urls: list[str] | None = None, media_type: str = "image",
    # NEW (this plan):
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]: ...
```

Existing publish_to_social tool signature (app/agents/tools/social.py:34-42) — SAME EXTENSION:
```python
def publish_to_social(
    user_id: str, platform: str, content: str,
    media_url: str | None = None, media_urls: list[str] | None = None,
    media_type: str = "text", utm_params: dict[str, str] | None = None,
    # NEW:
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]: ...
```

Conftest fixtures from 108-01 (already in place):
- `mock_supabase_client`, `mock_httpx_async_client`, `patch_encryption`, `fresh_connector`, `fresh_publisher`
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migration + PLATFORM_CONFIGS auth_method + Pinterest callback (Basic-auth + /v5/user_account)</name>
  <files>
    supabase/migrations/20260509000100_pinterest_platform.sql,
    .env.example,
    app/social/connector.py,
    tests/unit/social/test_connector_callback.py
  </files>
  <behavior>
    **RED — tests/unit/social/test_connector_callback.py::TestPinterestCallback (5 tests):**

    Setup: `monkeypatch.setenv("PINTEREST_CLIENT_ID", "test-pin-id")` and `PINTEREST_CLIENT_SECRET="test-pin-secret"`.

    1. `test_pinterest_authorization_url_uses_pinterest_dot_com` — `get_authorization_url("pinterest", "user-1", "https://example.com/cb")["authorization_url"]` starts with `https://www.pinterest.com/oauth/?` and contains `client_id=test-pin-id`, scope (URL-encoded — note the colons): `boards%3Aread+pins%3Awrite+user_accounts%3Aread` (or `boards:read+pins:write+user_accounts:read` depending on `urlencode` defaults — match what `urlencode({"scope": " ".join(scopes)})` actually produces, which by default does NOT encode colons but DOES encode spaces as `+`).

    2. `test_pinterest_callback_uses_basic_auth_header` — patch httpx so first `post` call captures kwargs. Pre-load PKCE verifier `"user-9:abc"` → `"ver-9"` via `connector._pkce_verifiers`. First mocked POST response (`api.pinterest.com/v5/oauth/token`): `status_code=200, json={"access_token":"AT-PIN","refresh_token":"RT-PIN","expires_in":2592000,"token_type":"bearer","scope":"boards:read pins:write user_accounts:read"}`. Second mocked GET (`api.pinterest.com/v5/user_account`): `status_code=200, json={"username":"alice_pins","account_type":"BUSINESS"}`.

       Assertions:
       - The token POST call kwargs include `auth=("test-pin-id", "test-pin-secret")` (httpx `auth=` tuple → Basic header).
       - The token POST `data` body does NOT contain `client_id` or `client_secret` keys (Pinterest rejects body-encoded credentials).
       - The token POST `data` body DOES contain `grant_type="authorization_code"`, `code="CODE-X"`, `redirect_uri="https://example.com/cb"`, `code_verifier="ver-9"`.

    3. `test_pinterest_callback_followup_user_account_call` — same setup. After the token POST, assert `mock_client.get` was called once with URL `https://api.pinterest.com/v5/user_account` and headers `Authorization: Bearer AT-PIN`. Assert the supabase upsert payload includes `platform_username="alice_pins"`. Assert `platform_user_id` is `None` (Pinterest token response has no user_id; we capture username only — that's enough for posts since `/v5/pins` only needs the bearer token).

    4. `test_pinterest_callback_user_account_call_failure_does_not_break_connection` — token POST succeeds, but `mock_client.get` returns `status_code=500`. Connection STILL succeeds (`{"success": True, "platform": "pinterest"}` returned). `platform_username=None` in the upsert payload (best-effort — we have a working access_token).

    5. `test_pinterest_callback_token_exchange_4xx_returns_error` — token POST returns `status_code=401, text='{"error":"invalid_client"}'`. Return value contains `"error"` mentioning "Token exchange failed". No follow-up GET is made.

    Run `uv run pytest tests/unit/social/test_connector_callback.py -x -k pinterest` — confirm 5 fail (RED).

    Commit: `test(108-02): add failing Pinterest connector tests (HYGIENE-02)`.

    **GREEN — implementation:**

    1. **Migration `supabase/migrations/20260509000100_pinterest_platform.sql`:**
       ```sql
       -- Migration: 20260509000100_pinterest_platform.sql
       -- Description: Add 'pinterest' to connected_accounts platform CHECK constraint (HYGIENE-02)

       DO $$
       DECLARE
           constraint_name TEXT;
       BEGIN
           SELECT conname INTO constraint_name
           FROM pg_constraint
           WHERE conrelid = 'connected_accounts'::regclass
             AND contype = 'c'
             AND pg_get_constraintdef(oid) LIKE '%platform%IN%';
           IF constraint_name IS NOT NULL THEN
               EXECUTE 'ALTER TABLE connected_accounts DROP CONSTRAINT ' || constraint_name;
           END IF;

           ALTER TABLE connected_accounts ADD CONSTRAINT connected_accounts_platform_check
               CHECK (platform IN (
                   'twitter','linkedin','facebook','instagram','tiktok','youtube',
                   'google_search_console','google_analytics','threads','pinterest'
               ));
       END $$;
       ```

       Note: the migration must run AFTER `20260509000000_threads_platform.sql` (108-01). Sequencing is enforced by file timestamp; both plans are wave 1 but the migrations are commutative (each drops the constraint and recreates it with its own enum). Whichever lands second leaves the canonical set. To make this safe regardless of ordering, recreate the constraint with BOTH `'threads'` AND `'pinterest'` even though 108-01 only added `'threads'` — Postgres tolerates the duplicate `'threads'` literal in the IN list. **The 108-01 migration's IN list is allowed to be a subset; the 108-02 migration's IN list is the canonical end state.**

    2. **`.env.example`:**
       ```
       # Pinterest API — separate OAuth client (NOT shared with any other Meta/Google entry)
       # Get from: https://developers.pinterest.com/apps/
       PINTEREST_CLIENT_ID=
       PINTEREST_CLIENT_SECRET=
       ```

    3. **`app/social/connector.py` — add to `PLATFORM_CONFIGS`:**
       ```python
       "pinterest": {
           "auth_url": "https://www.pinterest.com/oauth/",
           "token_url": "https://api.pinterest.com/v5/oauth/token",
           "scopes": ["boards:read", "pins:write", "user_accounts:read"],
           "client_id_env": "PINTEREST_CLIENT_ID",
           "client_secret_env": "PINTEREST_CLIENT_SECRET",
           "auth_method": "basic",
           "user_account_url": "https://api.pinterest.com/v5/user_account",  # for follow-up profile call
       },
       ```

    4. **`handle_callback` — branch on `auth_method`:**

       Replace the existing token POST block (lines 293-308) with:
       ```python
       client_id = os.environ.get(config["client_id_env"])
       client_secret = os.environ.get(config["client_secret_env"])
       auth_method = config.get("auth_method", "form")

       token_data = {
           "grant_type": "authorization_code",
           "code": code,
           "redirect_uri": redirect_uri,
           "code_verifier": verifier,
       }
       request_kwargs: dict[str, Any] = {"data": token_data}
       if auth_method == "basic":
           request_kwargs["auth"] = (client_id, client_secret)
       else:
           token_data["client_id"] = client_id
           token_data["client_secret"] = client_secret

       async with httpx.AsyncClient() as http:
           resp = await http.post(config["token_url"], **request_kwargs)
           if resp.status_code != 200:
               return {"error": f"Token exchange failed: {resp.text}"}
           tokens = resp.json()

           # Capture platform_user_id and platform_username from token response (108-01 behavior)
           platform_user_id = tokens.get("user_id")
           platform_username = tokens.get("username") or tokens.get("screen_name")

           # Best-effort follow-up profile call when configured and missing identity fields
           user_account_url = config.get("user_account_url")
           if user_account_url and not (platform_user_id or platform_username):
               try:
                   profile_resp = await http.get(
                       user_account_url,
                       headers={"Authorization": f"Bearer {tokens.get('access_token')}"},
                   )
                   if profile_resp.status_code == 200:
                       profile = profile_resp.json()
                       platform_user_id = platform_user_id or profile.get("id") or profile.get("user_id")
                       platform_username = platform_username or profile.get("username")
               except Exception as exc:
                   logger.warning("Profile follow-up call failed for %s: %s", platform, exc)
       ```

       (The `connection_data` upsert dict and `platform_user_id`/`platform_username` keys were already added in 108-01 Task 1. This task only changes the token-exchange request shape and adds the follow-up GET.)

    5. **`_refresh_token` — also branch on `auth_method`:**

       Replace the existing `http.post(config["token_url"], data={...})` (lines 425-434) with:
       ```python
       refresh_body = {"grant_type": "refresh_token", "refresh_token": refresh_token}
       refresh_kwargs: dict[str, Any] = {"data": refresh_body}
       if config.get("auth_method") == "basic":
           refresh_kwargs["auth"] = (client_id, client_secret)
       else:
           refresh_body["client_id"] = client_id
           refresh_body["client_secret"] = client_secret

       with httpx.Client(timeout=30.0) as http:
           resp = http.post(config["token_url"], **refresh_kwargs)
       ```

    Run `uv run pytest tests/unit/social/test_connector_callback.py -x -k pinterest` — 5 GREEN.

    Lint: `uv run ruff check app/social/connector.py --fix && uv run ruff format app/social/connector.py && uv run ty check app/social/connector.py`.

    Commit: `feat(108-02): Pinterest PLATFORM_CONFIGS + Basic-auth token exchange + /v5/user_account profile capture (HYGIENE-02)`.
  </behavior>
  <action>
    Implement RED tests first, run, then implement.

    **`mock_httpx_async_client` extension for this task:** the conftest mock from 108-01 must support BOTH `post` and `get` as AsyncMocks. If 108-01 only set `post`, extend the conftest to also set `get`. Use side_effects to chain responses across calls.

    **Sequencing the post and get mock calls:**
    ```python
    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: TOKEN_RESP))
    mock_client.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: PROFILE_RESP))
    ```

    Linters as in 108-01.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_connector_callback.py -x -k pinterest 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    5 TestPinterestCallback tests GREEN. `PLATFORM_CONFIGS["pinterest"]` exists with `auth_method="basic"` and `user_account_url`. `handle_callback` sends Basic-auth credentials when `auth_method=="basic"` and form-encoded otherwise. Follow-up `/v5/user_account` GET captures `platform_username` (and `platform_user_id` if present) when missing from token response, and is best-effort (failure does NOT break the connection). `_refresh_token` also branches on `auth_method`. Existing connector tests (Threads from 108-01, others) NOT regressed. Migration file created. `.env.example` updated. Ruff + ty clean. Commit lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Pinterest publisher branch + extra kwarg threading + tool wiring</name>
  <files>
    app/social/publisher.py,
    app/agents/tools/social.py,
    tests/unit/social/test_publisher_per_platform.py
  </files>
  <behavior>
    **RED — tests/unit/social/test_publisher_per_platform.py::TestPinterestPublisher (5 tests):**

    Setup: `mock_connector.get_access_token.return_value="AT-PIN"`. `mock_connector.get_platform_user_id.return_value=None` (Pinterest doesn't need it).

    1. `test_pinterest_post_pin_success` — `publisher.post_with_media(user_id="u1", platform="pinterest", content="my pin caption", media_urls=["https://cdn/img.jpg"], media_type="image", extra={"board_id":"BOARD_X"})`. Mock POST response: `status_code=201, json={"id":"PIN-99","board_id":"BOARD_X","media_source":{"images":{"originals":{"url":"https://cdn/img.jpg"}}}}`.
       - Assert `mock_client.post` called once with URL `https://api.pinterest.com/v5/pins`.
       - Assert headers include `Authorization: Bearer AT-PIN` and `Content-Type: application/json`.
       - Assert `json=` body shape: `{"board_id":"BOARD_X","title":"my pin caption","description":"my pin caption","media_source":{"source_type":"image_url","url":"https://cdn/img.jpg"}}`. (Title and description both derive from content; truncate per Pinterest limits if longer than 100/500 chars.)
       - Return value: `{"success": True, "platform": "pinterest", "post_id": "PIN-99", "media_type": "image", "message": "Posted to pinterest successfully"}`.

    2. `test_pinterest_post_truncates_long_content` — `content` is 200 chars long. Body `title` is exactly the first 100 chars; `description` is the first 500 chars (so all 200, untruncated for description).

    3. `test_pinterest_post_missing_board_id_returns_error_without_http` — same call but `extra={}` (or `extra=None`). Returns `{"error": "Pinterest requires a board_id; pass via extra={'board_id': ...}"}`. `mock_client.post` NEVER called.

    4. `test_pinterest_post_missing_media_url_returns_error_without_http` — `media_urls=None`, `extra={"board_id":"BOARD_X"}`. Returns `{"error": "Pinterest pins require an image URL"}`. No HTTP call.

    5. `test_pinterest_post_api_error_surfaces` — POST returns `status_code=400, text='{"code":2,"message":"Invalid board_id"}'`. Return value contains `"error"` and the response text/status.

    Run `uv run pytest tests/unit/social/test_publisher_per_platform.py -x -k pinterest` — confirm 5 fail (RED).

    Commit: `test(108-02): add failing Pinterest publisher tests (HYGIENE-02)`.

    **GREEN — implementation:**

    1. **`app/social/publisher.py` — extend `post_with_media` signature:**
       ```python
       async def post_with_media(
           self,
           user_id: str,
           platform: str,
           content: str,
           media_urls: list[str] | None = None,
           media_type: str = "image",
           extra: dict[str, Any] | None = None,  # NEW — per-platform kwargs (e.g., Pinterest board_id)
       ) -> dict[str, Any]:
           """...

           Args:
               extra: Optional per-platform kwargs. Pinterest requires
                      `extra={'board_id': '<board>'}`. Other platforms ignore.
           """
       ```

    2. **Add Pinterest branch** (after `youtube`, before the catch-all `else`):
       ```python
       # ----- PINTEREST -----
       elif platform == "pinterest":
           board_id = (extra or {}).get("board_id")
           if not board_id:
               return {
                   "error": "Pinterest requires a board_id; pass via "
                   "extra={'board_id': ...}"
               }
           if not has_media:
               return {"error": "Pinterest pins require an image URL"}
           resp = await http.post(
               "https://api.pinterest.com/v5/pins",
               headers={**headers, "Content-Type": "application/json"},
               json={
                   "board_id": board_id,
                   "title": content[:100],
                   "description": content[:500],
                   "media_source": {
                       "source_type": "image_url",
                       "url": media_urls[0],
                   },
               },
           )
       ```

       The shared response handler at lines 336-352 maps `status_code in [200,201,202]` and pulls `id` from the response, returning the standard success envelope.

    3. **`post_text` shim** (lines 69-82): also forward `extra=None` for forward-compat (text-only posts on Pinterest are not supported, so the extra kwarg won't matter, but keep the shim consistent):
       ```python
       async def post_text(self, user_id: str, platform: str, content: str) -> dict[str, Any]:
           return await self.post_with_media(
               user_id=user_id, platform=platform, content=content,
               media_urls=None, media_type="text", extra=None,
           )
       ```

    4. **`app/agents/tools/social.py` — extend `publish_to_social`:**
       ```python
       def publish_to_social(
           user_id: str,
           platform: str,
           content: str,
           media_url: str | None = None,
           media_urls: list[str] | None = None,
           media_type: str = "text",
           utm_params: dict[str, str] | None = None,
           extra: dict[str, Any] | None = None,  # NEW
       ) -> dict[str, Any]:
           """...

           Args:
               extra: Per-platform kwargs. Required for Pinterest:
                      extra={'board_id': '<board id>'}. Ignored by other
                      platforms.
           """
       ```

       Inside the function, change the final `loop.run_until_complete(...)` call:
       ```python
       return loop.run_until_complete(
           publisher.post_with_media(
               user_id=user_id,
               platform=platform,
               content=content,
               media_urls=resolved_urls,
               media_type=media_type,
               extra=extra,
           )
       )
       ```

       Also extend the docstring's `Platforms:` line to mention Pinterest and Threads.

    Run:
    ```
    uv run pytest tests/unit/social/test_publisher_per_platform.py -x -k pinterest
    uv run pytest tests/unit/social/ -x       # full suite — verify no regressions
    ```

    Lint: `uv run ruff check app/social/publisher.py app/agents/tools/social.py --fix && uv run ruff format app/social/publisher.py app/agents/tools/social.py && uv run ty check app/social/publisher.py app/agents/tools/social.py`.

    Commit: `feat(108-02): Pinterest /v5/pins branch + extra kwarg through publish_to_social tool (HYGIENE-02)`.
  </behavior>
  <action>
    Implement RED tests first, run, then implement.

    **Verifying body shape:** Pinterest uses JSON (not form-encoded), so:
    ```python
    call = mock_client.post.call_args_list[0]
    assert "api.pinterest.com/v5/pins" in call.args[0]
    assert call.kwargs["json"]["board_id"] == "BOARD_X"
    assert call.kwargs["json"]["media_source"]["source_type"] == "image_url"
    assert call.kwargs["headers"]["Authorization"] == "Bearer AT-PIN"
    ```

    **Forward compat for `extra` in `publish_to_social`:** The Marketing/Content agent LLM doesn't yet know about `extra`. Update the marketing agent's social sub-agent instruction (in 108-04 if discovered then; out of scope for this plan) so it knows how to set `extra={"board_id":"..."}` for Pinterest. For now, the tool surface accepts the kwarg; LLMs can still call it without `extra` and Pinterest will return the structured error guiding them to retry with a board_id.

    Linters as in Task 1.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/ -x -k pinterest 2>&amp;1 | tail -30 &amp;&amp; uv run pytest tests/unit/social/ -x 2>&amp;1 | tail -10</automated>
  </verify>
  <done>
    5 TestPinterestPublisher tests GREEN. `post_with_media` signature accepts `extra: dict[str, Any] | None = None`. Pinterest branch issues a single POST to `/v5/pins` with the correct JSON body shape, truncating title to 100 chars and description to 500. Missing `board_id` returns structured error without HTTP call. Missing media returns structured error without HTTP call. `publish_to_social` tool forwards `extra` to `post_with_media`. `post_text` shim updated to forward `extra=None`. All Threads tests (from 108-01) still pass — no regression. Existing `tests/unit/test_phase89_media_tagging.py` and other unrelated tests unaffected. Ruff + ty clean. Commit lands.
  </done>
</task>

</tasks>

<verification>
End-to-end verification for plan 108-02:

```
uv run pytest tests/unit/social/ -x -k pinterest 2>&1 | tail -10
uv run pytest tests/unit/social/ -x 2>&1 | tail -10        # full suite, no regressions
```

10 Pinterest-specific tests GREEN (5 callback + 5 publisher). All Threads tests from 108-01 still GREEN.

Spot-check the Basic-auth wire format manually:
```python
import base64
expected = "Basic " + base64.b64encode(b"test-pin-id:test-pin-secret").decode()
# httpx auth=(id, secret) tuple produces this header automatically
```
</verification>

<success_criteria>
- `app/social/connector.py` has `PLATFORM_CONFIGS["pinterest"]` with `auth_method="basic"` and `user_account_url="https://api.pinterest.com/v5/user_account"`.
- `handle_callback` branches on `auth_method`: form-encoded body for `"form"`, `auth=(client_id, client_secret)` httpx kwarg for `"basic"`.
- `handle_callback` issues a follow-up GET to `user_account_url` (best-effort, non-blocking) when token response lacks `user_id`/`username`.
- `_refresh_token` ALSO branches on `auth_method` (Pinterest refresh tokens use Basic auth too).
- `app/social/publisher.py:post_with_media` accepts `extra: dict[str, Any] | None = None` kwarg.
- Pinterest branch in `post_with_media` issues `POST https://api.pinterest.com/v5/pins` with JSON body containing `board_id`, `title` (≤100 chars), `description` (≤500 chars), `media_source.source_type="image_url"`, `media_source.url=<media>`.
- Missing `extra["board_id"]` → structured error, no HTTP call.
- Missing media URL → structured error, no HTTP call.
- `app/agents/tools/social.py:publish_to_social` accepts and forwards `extra` kwarg; docstring updated.
- `supabase/migrations/20260509000100_pinterest_platform.sql` adds `'pinterest'` (plus `'threads'` for safety) to platform CHECK constraint.
- `.env.example` documents `PINTEREST_CLIENT_ID` and `PINTEREST_CLIENT_SECRET`.
- 10 new Pinterest tests pass; all 11 Threads tests from 108-01 still pass; 0 regressions across the rest of the test suite.
- `uv run ruff check app/social/ app/agents/tools/social.py` clean; `uv run ty check app/social/ app/agents/tools/social.py` clean.
</success_criteria>

<output>
After completion, create `.planning/phases/108-hygiene-and-coverage/108-02-pinterest-platform-SUMMARY.md` documenting:
- Exact line numbers of `PLATFORM_CONFIGS["pinterest"]`, the `auth_method` branch in `handle_callback` and `_refresh_token`, the pinterest branch in `post_with_media`, and the `extra` kwarg additions
- Whether the `auth_method` discriminator was added at module level or per-call (and why)
- Test count: 10 new (5 callback + 5 publisher)
- Migration file reasoning (canonical end-state platform list including both 'threads' and 'pinterest')
- Any deviations from this plan
</output>
