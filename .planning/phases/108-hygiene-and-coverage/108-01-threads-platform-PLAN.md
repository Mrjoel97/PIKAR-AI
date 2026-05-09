---
phase: 108-hygiene-and-coverage
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .env.example
  - app/social/connector.py
  - app/social/publisher.py
  - supabase/migrations/20260509000000_threads_platform.sql
  - tests/unit/social/__init__.py
  - tests/unit/social/conftest.py
  - tests/unit/social/test_connector_callback.py
  - tests/unit/social/test_publisher_per_platform.py
  - pyproject.toml
autonomous: true
requirements: [HYGIENE-01]

must_haves:
  truths:
    - "User can initiate a Threads OAuth flow: get_oauth_url(platform='threads', user_id=...) returns an authorization URL pointing at https://threads.net/oauth/authorize with the configured THREADS_APP_ID and the threads_basic + threads_content_publish scopes"
    - "Threads OAuth callback exchanges the authorization code at https://graph.threads.net/oauth/access_token, captures platform_user_id from the token response, and upserts into connected_accounts with status='active'"
    - "Marketing/Content agent can post a TEXT thread: publish_to_social(platform='threads', content='hello', media_type='text') performs ONE POST to graph.threads.net/v1.0/{threads-user-id}/threads with media_type=TEXT then ONE POST to .../threads_publish with the returned creation_id"
    - "Marketing/Content agent can post an IMAGE thread: publish_to_social(platform='threads', content='caption', media_url='https://...jpg', media_type='image') performs the two-step container/publish flow with media_type=IMAGE and image_url set"
    - "If platform_user_id is missing from connected_accounts (legacy row), publisher returns a structured error 'Threads user ID missing — reconnect account' WITHOUT making any HTTP call"
    - "The supabase 'platform' CHECK constraint on connected_accounts accepts 'threads' (a row insert with platform='threads' succeeds)"
  artifacts:
    - path: ".env.example"
      provides: "THREADS_APP_ID and THREADS_APP_SECRET documented with comment about Meta App Dashboard → Threads product"
      contains: "THREADS_APP_ID"
    - path: "app/social/connector.py"
      provides: "PLATFORM_CONFIGS['threads'] entry; get_platform_user_id helper; handle_callback captures tokens.get('user_id') as platform_user_id"
      contains: "threads.net"
    - path: "app/social/publisher.py"
      provides: "elif platform == 'threads' branch implementing two-step container/publish on graph.threads.net/v1.0/{threads-user-id}/threads + threads_publish"
      contains: "graph.threads.net"
    - path: "supabase/migrations/20260509000000_threads_platform.sql"
      provides: "Adds 'threads' to the connected_accounts platform CHECK constraint (drop-and-recreate idempotent migration)"
      contains: "ADD CONSTRAINT connected_accounts_platform_check"
    - path: "tests/unit/social/__init__.py"
      provides: "Empty package marker so pytest discovers the new test directory"
    - path: "tests/unit/social/conftest.py"
      provides: "Shared fixtures: mock_supabase, mock_httpx_client, mock_connector, threads_token_response, image_url. Reused by 108-02 and 108-04."
      contains: "def mock_supabase"
    - path: "tests/unit/social/test_connector_callback.py"
      provides: "Threads-specific callback tests: state round-trip, PKCE resolved, token exchange success, platform_user_id captured, missing user_id, token exchange failure"
      contains: "test_threads_callback"
    - path: "tests/unit/social/test_publisher_per_platform.py"
      provides: "Threads post tests: post_text (TEXT branch), post_image (IMAGE branch with two-step), post_no_user_id, post_container_creation_failed, post_no_token"
      contains: "test_threads_post"
    - path: "pyproject.toml"
      provides: "[tool.pytest.ini_options] asyncio_mode = 'strict' added (one-line addition under existing addopts)"
      contains: "asyncio_mode"
  key_links:
    - from: "app/social/connector.py:PLATFORM_CONFIGS"
      to: "Meta Threads API: https://threads.net/oauth/authorize and https://graph.threads.net/oauth/access_token"
      via: "PLATFORM_CONFIGS['threads'] entry with auth_url, token_url, scopes, client_id_env, client_secret_env, auth_method='form'"
      pattern: "\"threads\": \\{"
    - from: "app/social/connector.py:handle_callback"
      to: "connected_accounts.platform_user_id column"
      via: "Add `platform_user_id = tokens.get('user_id')` and include in connection_data dict before upsert"
      pattern: "platform_user_id"
    - from: "app/social/publisher.py:post_with_media (threads branch)"
      to: "app/social/connector.py:get_platform_user_id"
      via: "New connector method that selects platform_user_id from connected_accounts where (user_id, platform); publisher resolves the threads-user-id before constructing URLs"
      pattern: "get_platform_user_id"
    - from: "app/social/publisher.py:_post_threads container request"
      to: "app/social/publisher.py:_post_threads publish request"
      via: "creation_id from container response is passed into the threads_publish POST body"
      pattern: "creation_id"
---

<objective>
Add Threads as a fully-supported platform: OAuth connect (`get_oauth_url(platform="threads", ...)`) plus two-step container/publish posting for text and image threads. Capture `platform_user_id` at callback time so subsequent posts can resolve `https://graph.threads.net/v1.0/{threads-user-id}/...` instead of the broken `me/` placeholder. Establish the `tests/unit/social/` test directory with shared fixtures (reused by 108-02 and 108-04) and Threads-specific callback + publisher tests. Add `asyncio_mode="strict"` to pytest config so the new async tests don't silently no-op. Adds `'threads'` to the `connected_accounts` platform CHECK constraint via SQL migration.

Purpose: Satisfy HYGIENE-01 ("User can connect Threads accounts and the Marketing agent can post text/image to Threads (Meta Threads API)"). Resolves the ROADMAP SC-1 wording ambiguity per the locked decision in `108-CONTEXT.md` — Threads has its own OAuth credentials, NOT Facebook's.

Output: `'threads'` recognized end-to-end through the `connector → publisher → SOCIAL_TOOLS` stack. New test infrastructure (`tests/unit/social/`) ready for 108-02 (Pinterest) and 108-04 (coverage backfill) to extend. The `platform_user_id` capture pattern established in `handle_callback` is generalized — every existing platform inherits it for free (a token response with `user_id` will be captured; platforms without that field are unaffected).
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
@tests/unit/test_phase89_media_tagging.py

<interfaces>
<!-- Key contracts the executor needs. Use these directly — no codebase exploration required. -->

From app/social/connector.py (current shape — keep stable):
```python
PLATFORM_CONFIGS: dict[str, dict] = { ... }  # see existing entries lines 33-106

class SocialConnector:
    def get_authorization_url(self, platform: str, user_id: str, redirect_uri: str) -> dict[str, Any]: ...
    async def handle_callback(self, platform: str, code: str, state: str, redirect_uri: str) -> dict[str, Any]: ...
    def get_access_token(self, user_id: str, platform: str) -> str | None: ...
    def list_connections(self, user_id: str) -> list[dict[str, Any]]: ...
    def revoke_connection(self, user_id: str, platform: str) -> dict[str, Any]: ...
    def _refresh_token(self, user_id: str, platform: str, account: dict[str, Any]) -> str | None: ...

def get_social_connector() -> SocialConnector: ...  # singleton
```

From app/social/publisher.py:
```python
class SocialPublisher:
    async def post_with_media(
        self, user_id: str, platform: str, content: str,
        media_urls: list[str] | None = None, media_type: str = "image",
    ) -> dict[str, Any]: ...
```

Threads API contract (from research, verified 2026-05-08):
- Auth: `https://threads.net/oauth/authorize?client_id=...&redirect_uri=...&scope=threads_basic,threads_content_publish&response_type=code&state=...&code_challenge=...&code_challenge_method=S256`
- Token exchange: `POST https://graph.threads.net/oauth/access_token` with form-encoded {grant_type, code, redirect_uri, client_id, client_secret, code_verifier}. Response: `{"access_token": "...", "user_id": "1234567890", "expires_in": 3600}`.
- Create container: `POST https://graph.threads.net/v1.0/{threads-user-id}/threads` with form data `{media_type: TEXT|IMAGE|VIDEO, text, image_url?, video_url?, access_token}`. Response `{"id": "<creation_id>"}`.
- Publish: `POST https://graph.threads.net/v1.0/{threads-user-id}/threads_publish` with `{creation_id, access_token}`. Response `{"id": "<thread_id>"}`.

Existing platform CHECK constraint (supabase/migrations/20260320000000_social_analytics_listening.sql:91-98):
```sql
ALTER TABLE connected_accounts ADD CONSTRAINT connected_accounts_platform_check
  CHECK (platform IN ('twitter','linkedin','facebook','instagram','tiktok','youtube','google_search_console','google_analytics'));
```
Migration in this plan adds 'threads' (and leaves room for 108-02 to add 'pinterest').

Existing test pattern (tests/unit/test_phase89_media_tagging.py — DO NOT regress):
- `unittest.mock.patch` on `httpx.AsyncClient`
- supabase mocked via `MagicMock()` builder mirroring postgrest signatures
- `@pytest.mark.asyncio` on async tests
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migration + PLATFORM_CONFIGS + handle_callback platform_user_id capture</name>
  <files>
    supabase/migrations/20260509000000_threads_platform.sql,
    .env.example,
    app/social/connector.py,
    pyproject.toml,
    tests/unit/social/__init__.py,
    tests/unit/social/conftest.py,
    tests/unit/social/test_connector_callback.py
  </files>
  <behavior>
    Failing tests FIRST (RED), then implementation (GREEN).

    **RED — tests/unit/social/test_connector_callback.py::TestThreadsCallback (5 tests, all initially fail):**

    1. `test_threads_authorization_url_uses_threads_net` — `get_authorization_url("threads", "user-1", "https://example.com/cb")` returns a dict whose `authorization_url` starts with `https://threads.net/oauth/authorize?` AND contains `client_id=test-threads-id`, `scope=threads_basic+threads_content_publish` (URL-encoded space), `code_challenge_method=S256`, `state=user-1:...`. Patch `os.environ` with `THREADS_APP_ID=test-threads-id`.

    2. `test_threads_authorization_url_missing_client_id_returns_error` — when `THREADS_APP_ID` is unset, returns `{"error": "Missing THREADS_APP_ID in environment"}` (matches existing `get_authorization_url` error shape at connector.py:233).

    3. `test_threads_callback_state_round_trip_and_token_exchange` — patch `httpx.AsyncClient` to return `{"access_token":"AT","refresh_token":"RT","user_id":"1122334455","expires_in":3600}` from `graph.threads.net/oauth/access_token`. Patch the supabase client. Pre-load a PKCE verifier for state `"user-9:abc"` via `connector._pkce_verifiers["user-9:abc"] = "ver-9"` (legacy in-memory fallback path — the persisted-state DB lookup returns `[]`). Call `await connector.handle_callback("threads", code="CODE-X", state="user-9:abc", redirect_uri="https://example.com/cb")`.
       - Assert the POST body sent to `graph.threads.net/oauth/access_token` includes `code_verifier=ver-9`, `code=CODE-X`, `client_id=test-threads-id`, `client_secret=test-threads-secret`.
       - Assert the supabase upsert was called on `connected_accounts` with `platform="threads"`, `user_id="user-9"`, `platform_user_id="1122334455"`, encrypted `access_token`, encrypted `refresh_token`, `status="active"`.
       - Assert return value is `{"success": True, "platform": "threads", "message": "Successfully connected threads account"}`.

    4. `test_threads_callback_token_response_without_user_id_falls_back_to_none_platform_user_id` — token response is `{"access_token":"AT","expires_in":3600}` (no user_id). Upsert payload `platform_user_id` key is `None` (column is nullable; do not error). Connection still succeeds.

    5. `test_threads_callback_token_exchange_4xx_returns_error` — POST returns `status_code=400` with body `{"error":"invalid_grant"}`. Return value contains `"error"` mentioning "Token exchange failed".

    **conftest.py fixtures (shared across all `tests/unit/social/` modules):**

    ```python
    @pytest.fixture
    def mock_supabase_client():
        """Returns a MagicMock that mimics the postgrest fluent API.

        Supports: client.table(name).{select,insert,update,upsert,delete}(...).{eq,limit,...}.execute().
        Each terminal `.execute()` returns a MagicMock with `.data` defaulting to `[]`.
        Test code can override per-call via `mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [...]`.
        """
        client = MagicMock()
        return client

    @pytest.fixture
    def mock_httpx_async_client():
        """AsyncMock that mimics httpx.AsyncClient as an async context manager.

        Yields a tuple (cm_patch_target, mock_client) where mock_client.post / .delete / .get are AsyncMock
        instances the test can configure with side_effect or return_value.
        """
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.post = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.get = AsyncMock()
        return mock_client

    @pytest.fixture(autouse=True)
    def patch_encryption(monkeypatch):
        """Replace encrypt_secret/decrypt_secret with identity for tests."""
        monkeypatch.setattr("app.social.connector.encrypt_secret", lambda s: f"ENC({s})")
        monkeypatch.setattr("app.social.connector.decrypt_secret", lambda s: s.removeprefix("ENC(").removesuffix(")") if isinstance(s, str) else s)

    @pytest.fixture
    def threads_env(monkeypatch):
        monkeypatch.setenv("THREADS_APP_ID", "test-threads-id")
        monkeypatch.setenv("THREADS_APP_SECRET", "test-threads-secret")
    ```

    Run `uv run pytest tests/unit/social/test_connector_callback.py -x` and confirm 5 tests fail (RED state — `PLATFORM_CONFIGS["threads"]` doesn't exist; the supabase upsert payload doesn't include `platform_user_id`).

    Commit: `test(108-01): add failing Threads connector tests (HYGIENE-01)`.

    **GREEN — implementation:**

    1. **Migration** `supabase/migrations/20260509000000_threads_platform.sql`:
       ```sql
       -- Migration: 20260509000000_threads_platform.sql
       -- Description: Add 'threads' to the connected_accounts platform CHECK constraint (HYGIENE-01)

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
                   'google_search_console','google_analytics','threads'
               ));
       END $$;
       ```
       (Mirrors the drop-and-recreate pattern at `20260320000000_social_analytics_listening.sql:91-98`.)

    2. **`.env.example`**: add at the bottom of the social-OAuth env block:
       ```
       # Meta Threads API — separate OAuth app inside the Meta App Dashboard's Threads product.
       # Get from: https://developers.facebook.com/apps → your-app → Threads → Configuration
       THREADS_APP_ID=
       THREADS_APP_SECRET=
       ```

    3. **`app/social/connector.py`**:
       - Add to `PLATFORM_CONFIGS` (append after `google_analytics`):
         ```python
         "threads": {
             "auth_url": "https://threads.net/oauth/authorize",
             "token_url": "https://graph.threads.net/oauth/access_token",
             "scopes": ["threads_basic", "threads_content_publish"],
             "client_id_env": "THREADS_APP_ID",
             "client_secret_env": "THREADS_APP_SECRET",
             "auth_method": "form",  # NEW field — Pinterest will use "basic" in 108-02
         },
         ```
       - In `handle_callback` (line 257-345), AFTER `tokens = resp.json()` and BEFORE the upsert, capture:
         ```python
         platform_user_id = tokens.get("user_id")  # Threads/Pinterest include it in token response
         platform_username = tokens.get("username") or tokens.get("screen_name")
         ```
         Add to `connection_data` dict:
         ```python
         "platform_user_id": platform_user_id,
         "platform_username": platform_username,
         ```
         (Both columns already exist per `migrations/0010_connected_accounts.sql:8-9`. Generalizing this capture for all platforms is a free win — platforms that don't return `user_id` in the token response simply store `None`. LinkedIn/Twitter that need a follow-up profile call are addressed in their respective phases 103/104.)
       - Add a NEW public method (after `revoke_connection`, before `get_access_token`):
         ```python
         def get_platform_user_id(self, user_id: str, platform: str) -> str | None:
             """Return the provider-side user/account ID for a connected account, or None."""
             result = (
                 self.client.table("connected_accounts")
                 .select("platform_user_id")
                 .eq("user_id", user_id)
                 .eq("platform", platform)
                 .eq("status", "active")
                 .limit(1)
                 .execute()
             )
             rows = result.data or []
             return rows[0].get("platform_user_id") if rows else None
         ```

    4. **`pyproject.toml`** — add `asyncio_mode = "strict"` line under `[tool.pytest.ini_options]`:
       ```toml
       [tool.pytest.ini_options]
       addopts = "--ignore=tests/load_test"
       asyncio_mode = "strict"
       filterwarnings = [...]
       ```

    Run `uv run pytest tests/unit/social/test_connector_callback.py -x` — all 5 tests GREEN.

    Commit: `feat(108-01): Threads PLATFORM_CONFIGS + platform_user_id capture in handle_callback (HYGIENE-01)`.
  </behavior>
  <action>
    Implement RED tests first, run them and confirm failure, then implement the migration, .env.example update, connector.py changes, and pyproject.toml change.

    **Patch targets for tests:**
    - `patch("app.social.connector.encrypt_secret", lambda s: f"ENC({s})")` (autouse fixture)
    - `patch("httpx.AsyncClient", return_value=mock_httpx_async_client)`
    - `patch("app.social.connector.get_service_client", return_value=mock_supabase_client)` — patch BEFORE instantiating `SocialConnector()` since `__init__` calls it.

    **Note on the existing `_get_supabase` design:** the connector caches the supabase client in `__init__`. Tests must instantiate a fresh `SocialConnector` after the supabase patch is in place. Recommend a fixture:
    ```python
    @pytest.fixture
    def fresh_connector(mock_supabase_client, monkeypatch):
        monkeypatch.setattr("app.social.connector.get_service_client", lambda: mock_supabase_client)
        # Bust the singleton too, in case other tests cached one
        import app.social.connector as conn_mod
        conn_mod._connector = None
        return conn_mod.SocialConnector()
    ```

    Run linters at end:
    ```
    uv run ruff check app/social/connector.py --fix
    uv run ruff format app/social/connector.py tests/unit/social/
    uv run ty check app/social/connector.py
    ```
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_connector_callback.py -x 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    5 TestThreadsCallback tests GREEN. `PLATFORM_CONFIGS["threads"]` exists with the correct auth_url/token_url/scopes. `handle_callback` upsert payload includes `platform_user_id` and `platform_username`. `get_platform_user_id(user_id, platform)` method exists. Migration file created with idempotent drop-and-recreate of platform CHECK including `'threads'`. `.env.example` documents the two new env vars. `pyproject.toml` has `asyncio_mode = "strict"`. Ruff + ty clean. Commit lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Threads publisher branch (two-step container/publish) + tests</name>
  <files>
    app/social/publisher.py,
    tests/unit/social/test_publisher_per_platform.py
  </files>
  <behavior>
    **RED — tests/unit/social/test_publisher_per_platform.py::TestThreadsPublisher (5 tests):**

    Setup pattern: patch `app.social.publisher.get_social_connector` to return a `MagicMock` with `get_access_token.return_value="AT"` and `get_platform_user_id.return_value="1122334455"`. Patch `httpx.AsyncClient` similarly to Task 1.

    1. `test_threads_post_text_two_step` — `publisher.post_with_media(user_id="u1", platform="threads", content="hello world", media_type="text")`:
       - Asserts mock_client.post was called exactly TWICE.
       - First call: URL is `https://graph.threads.net/v1.0/1122334455/threads`; body data contains `media_type=TEXT`, `text=hello world`, `access_token=AT`.
       - Second call: URL is `https://graph.threads.net/v1.0/1122334455/threads_publish`; body data contains `creation_id=container-A`, `access_token=AT`.
       - Mock first response: `status_code=200, json={"id":"container-A"}`. Mock second response: `status_code=200, json={"id":"thread-XYZ"}`.
       - Return value: `{"success": True, "platform": "threads", "post_id": "thread-XYZ", "media_type": "text", "message": "Posted to threads successfully"}`.

    2. `test_threads_post_image_uses_image_url` — `media_type="image"`, `media_urls=["https://cdn.example.com/pic.jpg"]`. First call body: `media_type=IMAGE`, `image_url=https://cdn.example.com/pic.jpg`, `text=caption`. Second call as above. Returns success with `media_type="image"`.

    3. `test_threads_post_video_uses_video_url` — `media_type="video"`, `media_urls=["https://cdn.example.com/clip.mp4"]`. First call body: `media_type=VIDEO`, `video_url=...`. Returns success.

    4. `test_threads_post_no_user_id_returns_error_without_http_call` — `get_platform_user_id` returns `None`. `post_with_media` returns `{"error": "Threads user ID missing — reconnect account"}`. `mock_client.post` was NEVER called.

    5. `test_threads_post_container_creation_failure_short_circuits` — first POST returns `status_code=400, text="invalid image url"`. Return value contains `"error"` mentioning "Threads container creation failed". Second POST is NEVER made.

    Bonus test (covers SC-1 verification):
    6. `test_threads_post_no_token_returns_error` — `get_access_token` returns `None`. Return value contains `"No active connection for threads"`. Both `post` calls AND `get_platform_user_id` are NEVER called (token check happens first per `_get_token_or_error`).

    Run `uv run pytest tests/unit/social/test_publisher_per_platform.py -x` — confirm 6 tests fail (RED).

    Commit: `test(108-01): add failing Threads publisher tests (HYGIENE-01)`.

    **GREEN — implementation in `app/social/publisher.py`:**

    Inside `post_with_media`, AFTER the existing `youtube` branch and BEFORE the catch-all `else: return {"error": f"Posting not implemented for {platform}"}`, add:

    ```python
    # ----- THREADS -----
    elif platform == "threads":
        threads_user_id = self.connector.get_platform_user_id(user_id, platform)
        if not threads_user_id:
            return {"error": "Threads user ID missing — reconnect account"}

        base = f"https://graph.threads.net/v1.0/{threads_user_id}"
        create_body: dict[str, Any] = {"access_token": token, "text": content}
        if has_media and media_type == "video":
            create_body["media_type"] = "VIDEO"
            create_body["video_url"] = media_urls[0]
        elif has_media:
            create_body["media_type"] = "IMAGE"
            create_body["image_url"] = media_urls[0]
        else:
            create_body["media_type"] = "TEXT"

        container_resp = await http.post(f"{base}/threads", data=create_body)
        if container_resp.status_code not in (200, 201):
            return {"error": f"Threads container creation failed: {container_resp.text}"}
        creation_id = container_resp.json().get("id")
        if not creation_id:
            return {"error": "Threads creation_id missing in container response"}

        resp = await http.post(
            f"{base}/threads_publish",
            data={"creation_id": creation_id, "access_token": token},
        )
    ```

    The shared response-handling block at `publisher.py:336-352` (`if resp.status_code in [200,201,202]: ... post_id = resp_data.get("id") ...`) handles success/error mapping correctly for Threads (the publish response shape is `{"id": "<thread-id>"}`).

    **Important:** do NOT add an `await asyncio.sleep(2)` between create and publish despite the research suggesting it for production. Reasoning: (a) for image/video Meta says "wait ~30s for processing" — 2s won't help much; (b) tests would either need the sleep mocked or actually slow down; (c) in practice Meta's API still queues if not ready and most images/videos hosted on a CDN are immediately ready. Document this trade-off in a code comment.

    Run `uv run pytest tests/unit/social/test_publisher_per_platform.py -x` — all 6 GREEN.

    Lint: `uv run ruff check app/social/publisher.py --fix && uv run ruff format app/social/publisher.py && uv run ty check app/social/publisher.py`.

    Run the full Threads suite to make sure 108-01 cross-files pass together:
    `uv run pytest tests/unit/social/ -x -k "threads or Threads"`.

    Commit: `feat(108-01): Threads two-step container/publish branch in post_with_media (HYGIENE-01)`.
  </behavior>
  <action>
    Implement tests first, run, then add the publisher branch.

    **Patch targets:**
    - `patch("app.social.publisher.get_social_connector", return_value=MagicMock(get_access_token=MagicMock(return_value="AT"), get_platform_user_id=MagicMock(return_value="1122334455")))`. Note: `SocialPublisher.__init__` calls `get_social_connector()` once and caches it; bust the singleton between tests:
      ```python
      @pytest.fixture
      def fresh_publisher(monkeypatch, ...):
          import app.social.publisher as pub_mod
          pub_mod._publisher = None
          monkeypatch.setattr(pub_mod, "get_social_connector", lambda: mock_connector)
          return pub_mod.SocialPublisher()
      ```
    - `patch("httpx.AsyncClient", return_value=mock_httpx_async_client)` (passed in via fixture).

    Body assertions: `mock_client.post.call_args_list[0]` — for the threads branch the test must check the `data=` kwarg (form-encoded) NOT `json=`. Use:
    ```python
    first_call = mock_client.post.call_args_list[0]
    assert "graph.threads.net/v1.0/1122334455/threads" in first_call.args[0]
    assert first_call.kwargs["data"]["media_type"] == "TEXT"
    ```

    Edge: `_get_token_or_error` is called BEFORE the threads branch checks `get_platform_user_id`. For test 6 (no token), the publisher returns the no-connection error from line 36-41 before any platform-specific code runs.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/ -x -k "threads or Threads" 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    6 TestThreadsPublisher tests GREEN. The threads branch in `post_with_media` performs two POSTs to `graph.threads.net/v1.0/{platform_user_id}/{threads,threads_publish}` with the correct body shape per media_type. Missing `platform_user_id` short-circuits without HTTP. Container failure short-circuits the publish call. Token absence is caught by `_get_token_or_error` before any branch logic. Existing publisher tests are NOT regressed (existing six platforms still work — diff is purely additive). `ruff check` and `ty check` clean for publisher.py. Commit lands.
  </done>
</task>

</tasks>

<verification>
End-to-end verification for plan 108-01:

```
uv run pytest tests/unit/social/ -x -k "threads or Threads" 2>&1 | tail -10
```

All 11 Threads-specific tests (5 callback + 6 publisher) GREEN.

Spot-check the SQL migration locally (Supabase CLI required):
```
supabase db reset --local
# verify: psql ... -c "\\d connected_accounts" shows the platform CHECK constraint includes 'threads'
```
</verification>

<success_criteria>
- `app/social/connector.py` has `PLATFORM_CONFIGS["threads"]` with the correct auth_url, token_url, scopes (`threads_basic`, `threads_content_publish`), client_id_env (`THREADS_APP_ID`), client_secret_env (`THREADS_APP_SECRET`), and `auth_method="form"`.
- `handle_callback` captures `platform_user_id = tokens.get("user_id")` AND `platform_username = tokens.get("username") or tokens.get("screen_name")` and includes both in the upsert payload (works for ALL platforms, not just Threads).
- `SocialConnector.get_platform_user_id(user_id, platform) -> str | None` exists and queries `connected_accounts.platform_user_id`.
- `app/social/publisher.py` has a `threads` branch implementing the two-step container/publish flow against `https://graph.threads.net/v1.0/{threads-user-id}/threads` then `.../threads_publish`.
- Missing `platform_user_id` returns a structured error without making any HTTP request.
- Container creation failure returns a structured error without attempting publish.
- `supabase/migrations/20260509000000_threads_platform.sql` adds `'threads'` to the platform CHECK constraint via idempotent drop-and-recreate.
- `.env.example` documents `THREADS_APP_ID` and `THREADS_APP_SECRET`.
- `pyproject.toml` has `asyncio_mode = "strict"` under `[tool.pytest.ini_options]`.
- New `tests/unit/social/__init__.py`, `conftest.py`, `test_connector_callback.py`, `test_publisher_per_platform.py` files exist.
- 11 new tests pass; 0 existing tests regressed.
- `uv run ruff check app/social/` clean; `uv run ty check app/social/` clean.
</success_criteria>

<output>
After completion, create `.planning/phases/108-hygiene-and-coverage/108-01-threads-platform-SUMMARY.md` documenting:
- Exact line numbers of the new `PLATFORM_CONFIGS["threads"]` entry, `get_platform_user_id` method, and `threads` branch in `post_with_media`
- Whether `platform_user_id` capture was made platform-agnostic (recommended) or threads-only — and why
- Test count: 11 new (5 callback + 6 publisher)
- Migration file created and any deviations from the recommended drop-and-recreate pattern
- Confirmation of `pyproject.toml` `asyncio_mode = "strict"` change
- Any deviations from this plan
</output>
