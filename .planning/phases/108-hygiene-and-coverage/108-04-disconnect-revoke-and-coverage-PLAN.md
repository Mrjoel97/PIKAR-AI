---
phase: 108-hygiene-and-coverage
plan: 04
type: execute
wave: 2
depends_on: ["108-01", "108-02"]
files_modified:
  - app/social/connector.py
  - app/agents/tools/social.py
  - tests/unit/social/conftest.py
  - tests/unit/social/test_connector_callback.py
  - tests/unit/social/test_connector_refresh.py
  - tests/unit/social/test_publisher_per_platform.py
  - tests/unit/social/test_disconnect_revoke.py
  - tests/unit/social/test_pkce_state.py
  - Makefile
autonomous: true
requirements: [HYGIENE-04]

must_haves:
  truths:
    - "disconnect_account(user_id, platform) is async; loads the access token, calls _revoke_at_provider, then updates connected_accounts.status='revoked' — in that order — for every platform that has a remote revoke endpoint"
    - "For LinkedIn (no public revoke endpoint), disconnect_account makes ZERO HTTP calls; the local row is still updated to status='revoked'; the response includes remote_revoked=False with reason 'no_remote_revoke_endpoint'"
    - "If the remote revoke call fails (4xx/5xx/network error), disconnect_account STILL updates the local row to status='revoked' and returns a partial-success response with remote_revoked=False and remote_error set — the user is never permanently stuck connected"
    - "revoke_connection (sync wrapper) is preserved as backward-compat for app/agents/tools/social.py:disconnect_social_account; it calls asyncio.run(self.disconnect_account(...))"
    - "pytest --cov=app.social tests/unit/social/ reports ≥80% line coverage"
    - "Per-platform handle_callback tests exist for ALL 8 platforms (linkedin, twitter, facebook, instagram, youtube, tiktok, threads, pinterest): each asserts state token round-trip, PKCE verifier resolution, platform_user_id capture, and token-exchange-failure handling"
    - "Per-platform post_with_media tests exist for ALL 8 platforms: each asserts request URL, headers (Authorization: Bearer ...), body shape, and at least one media-handling case"
    - "Per-platform _refresh_token tests exist for platforms that issue refresh tokens (twitter, linkedin, threads, pinterest, tiktok, youtube): branch on auth_method correctly"
    - "Per-platform disconnect ordering test asserts (via mock_calls inspection) that the revoke HTTP call precedes the supabase update"
    - "PKCE state utilities (_generate_pkce, state round-trip via _store_pkce_verifier and _pop_pkce_verifier including expiry) have dedicated tests"
  artifacts:
    - path: "app/social/connector.py"
      provides: "New async disconnect_account method with _revoke_at_provider per-platform dispatch (linkedin no-op, twitter, google-family, facebook, instagram, threads, tiktok, pinterest); preserved sync revoke_connection wrapper"
      contains: "_revoke_at_provider"
    - path: "app/agents/tools/social.py"
      provides: "disconnect_social_account uses connector.revoke_connection (unchanged surface); behavior: now makes a remote revoke call before updating the DB row"
    - path: "tests/unit/social/test_connector_callback.py"
      provides: "Adds callback tests for the existing 6 platforms not covered by 108-01/02 (linkedin, twitter, facebook, instagram, youtube, tiktok). Each: state round-trip, PKCE resolved, token exchange success, platform_user_id captured (where applicable per provider), token exchange failure"
      contains: "test_linkedin_callback"
    - path: "tests/unit/social/test_connector_refresh.py"
      provides: "Per-platform refresh tests asserting auth_method branching (form vs basic) and token rotation (when provider returns a new refresh_token)"
      contains: "test_pinterest_refresh_uses_basic_auth"
    - path: "tests/unit/social/test_publisher_per_platform.py"
      provides: "Adds publisher tests for the existing 6 platforms (twitter text+image, linkedin text+image, facebook text+photo+video, instagram image+video+carousel, youtube video, tiktok video). Each verifies request URL, headers, body shape; covers no_token and api_error cases"
      contains: "test_linkedin_post_text"
    - path: "tests/unit/social/test_disconnect_revoke.py"
      provides: "Per-platform ordering tests: revoke HTTP call precedes supabase update (parent MagicMock with attach_mock); LinkedIn skips HTTP; revoke failure still updates local row; all 8 platforms covered"
      contains: "test_twitter_disconnect_calls_revoke_before_db_update"
    - path: "tests/unit/social/test_pkce_state.py"
      provides: "Tests for _generate_pkce (S256 challenge correctness), _store_pkce_verifier+_pop_pkce_verifier round-trip via supabase mock, expired verifier returns None, in-memory fallback when supabase write fails"
      contains: "test_generate_pkce_produces_s256"
    - path: "Makefile"
      provides: "New test-social target running pytest with --cov-fail-under=80; main `make test` runbook unchanged but suite passes when running with coverage"
      contains: "test-social"
  key_links:
    - from: "app/social/connector.py:disconnect_account"
      to: "app/social/connector.py:_revoke_at_provider"
      via: "Per-platform dispatch matrix (see provider revoke endpoint table below)"
      pattern: "_revoke_at_provider"
    - from: "app/social/connector.py:disconnect_account"
      to: "connected_accounts.status='revoked' update"
      via: "Always runs AFTER the revoke attempt, regardless of revoke success/failure (best-effort revoke; user can always disconnect locally)"
      pattern: "status.*revoked"
    - from: "app/agents/tools/social.py:disconnect_social_account"
      to: "app/social/connector.py:revoke_connection (sync wrapper)"
      via: "Sync wrapper internally calls asyncio.run(self.disconnect_account(...)) for backward compat with the LLM tool surface"
      pattern: "revoke_connection"

  # Provider revoke endpoint matrix (verified 2026-05-08 from research)
  revoke_endpoints:
    - platform: linkedin
      endpoint: NONE
      method: "—"
      auth: "—"
      notes: "LinkedIn has no public revoke endpoint. Microsoft Learn search returns zero hits. Members revoke via linkedin.com/mypreferences/d/data-sharing-for-permitted-services. Skip HTTP, update local row only."
      confidence: HIGH (negative claim verified)
    - platform: twitter
      endpoint: "https://api.x.com/2/oauth2/revoke"
      method: POST
      auth: "Authorization: Basic base64(client_id:client_secret) (confidential client) + form body token=<token>&client_id=<id>"
      notes: "api.twitter.com also resolves; use api.twitter.com for consistency with existing codebase (publisher.py:130)"
      confidence: HIGH
    - platform: youtube / google_search_console / google_analytics
      endpoint: "https://oauth2.googleapis.com/revoke"
      method: POST
      auth: "Content-Type: application/x-www-form-urlencoded; body: token=<token>"
      notes: "Single endpoint for all Google products"
      confidence: HIGH
    - platform: facebook
      endpoint: "https://graph.facebook.com/v18.0/me/permissions"
      method: DELETE
      auth: "Authorization: Bearer <access_token>"
      notes: "Same endpoint for Instagram (Meta App)"
      confidence: HIGH
    - platform: instagram
      endpoint: "https://graph.facebook.com/v18.0/me/permissions"
      method: DELETE
      auth: "Authorization: Bearer <access_token>"
      notes: "Same as Facebook"
      confidence: HIGH
    - platform: threads
      endpoint: "https://graph.threads.net/v1.0/me/permissions"
      method: DELETE
      auth: "Authorization: Bearer <access_token>"
      notes: "Mirrors Meta pattern (graph.threads.net domain). Verify with a real account before merge."
      confidence: MEDIUM (extrapolated from FB/IG; no Threads-specific docs page found)
    - platform: tiktok
      endpoint: "https://open.tiktokapis.com/v2/oauth/revoke/"
      method: POST
      auth: "Content-Type: application/x-www-form-urlencoded; body: client_key=<key>&client_secret=<secret>&token=<token>"
      notes: "Note: TikTok uses 'client_key' not 'client_id' in the body"
      confidence: HIGH
    - platform: pinterest
      endpoint: "https://api.pinterest.com/v5/oauth/token/revoke"
      method: POST
      auth: "Authorization: Basic base64(client_id:client_secret); Content-Type: application/x-www-form-urlencoded; body: token=<token>&token_type_hint=access_token"
      notes: "Same Basic-auth pattern as Pinterest's token endpoint"
      confidence: HIGH
---

<objective>
Backfill the test coverage and disconnect-revoke logic gaps that the audit flagged. Two parallel concerns:

1. **Behavior change — `disconnect_account` does what its name claims.** Refactor `revoke_connection` (currently: just flips `status='revoked'`) into an async `disconnect_account` that loads the token, POSTs to the provider's revoke endpoint per the matrix above, then updates the local row. Best-effort: a 4xx/5xx/network failure on the remote revoke does NOT block the local update — the user can always disconnect locally even if the provider is down. LinkedIn has no remote revoke endpoint; for it, skip the HTTP call but still update locally. Preserve the sync `revoke_connection` wrapper for the existing tool-side caller.

2. **Test backfill — ≥80% line coverage on `app/social/`.** Currently 0%. Build out `tests/unit/social/` with per-platform `handle_callback`, `post_with_media`, `_refresh_token`, and `disconnect_account` tests for all 8 platforms (existing 6 + Threads from 108-01 + Pinterest from 108-02). Add `_generate_pkce` / state round-trip tests. Add a `make test-social` target with `--cov-fail-under=80`.

Purpose: Satisfy HYGIENE-04 ("Mock-based unit tests cover connector.handle_callback per platform … and publisher.post_with_media request shape per platform … minimum 80% line coverage on app/social/; calling disconnect_account issues an HTTP POST to the provider's revoke endpoint BEFORE deleting the local connected_accounts row").

Output: Real disconnect with provider revoke for 7/8 platforms (LinkedIn skipped). 50+ new unit tests across 5 test modules. CI-enforced ≥80% line coverage on `app/social/`. The disconnect-ordering test pattern (via `MagicMock.attach_mock` recording the order of `http_post` and `db_update` mock calls) is the canonical example future phases can reuse for any "side-effect ordering" assertion.
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
@.planning/phases/108-hygiene-and-coverage/108-01-threads-platform-PLAN.md
@.planning/phases/108-hygiene-and-coverage/108-02-pinterest-platform-PLAN.md
@app/social/connector.py
@app/social/publisher.py
@app/agents/tools/social.py
@pyproject.toml
@tests/unit/test_phase89_media_tagging.py

<interfaces>
<!-- Key contracts the executor needs. -->

From app/social/connector.py (after 108-01 + 108-02 land):
```python
class SocialConnector:
    async def handle_callback(self, platform, code, state, redirect_uri) -> dict[str, Any]: ...
    def get_authorization_url(self, platform, user_id, redirect_uri) -> dict[str, Any]: ...
    def get_access_token(self, user_id, platform) -> str | None: ...
    def list_connections(self, user_id) -> list[dict]: ...
    def get_platform_user_id(self, user_id, platform) -> str | None: ...   # added in 108-01
    def revoke_connection(self, user_id, platform) -> dict[str, Any]: ...  # SYNC — to be refactored
    def _refresh_token(self, user_id, platform, account) -> str | None: ...
    def _generate_pkce(self) -> tuple[str, str]: ...
    def _store_pkce_verifier(self, state, user_id, platform, verifier) -> None: ...
    def _pop_pkce_verifier(self, state, platform) -> str | None: ...
    def _decrypt_token(self, token: str | None) -> str | None: ...

PLATFORM_CONFIGS now has 10 entries (8 originals + threads + pinterest).
```

Provider revoke endpoint matrix — see frontmatter `key_links.revoke_endpoints` for the canonical reference.

Disconnect ordering test pattern (from research, project-validated):
```python
@pytest.mark.asyncio
async def test_<platform>_disconnect_calls_revoke_before_db_update(fresh_connector, mock_supabase_client):
    parent = MagicMock()
    http_post_mock = AsyncMock(return_value=MagicMock(status_code=200))
    db_update_mock = MagicMock()
    parent.attach_mock(http_post_mock, "http_post")
    parent.attach_mock(db_update_mock, "db_update")

    # Pre-load a stored token for the platform
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"access_token": "ENC(test-token)", "refresh_token": None, "token_expires_at": "2099-01-01T00:00:00Z"}
    ]
    # Patch update branch to record into parent
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute = db_update_mock

    with patch("httpx.AsyncClient.__aenter__", return_value=AsyncMock(post=http_post_mock, delete=http_post_mock)):
        result = await fresh_connector.disconnect_account(user_id="u1", platform="<platform>")

    # Order assertion: http_post call name comes BEFORE db_update in mock_calls
    call_names = [c[0] for c in parent.mock_calls if c[0] in ("http_post", "db_update")]
    assert call_names.index("http_post") < call_names.index("db_update"), (
        f"Revoke HTTP call must precede DB update; saw {call_names}"
    )
    assert result["success"] is True
    assert result.get("remote_revoked") is True
```

For LinkedIn the test instead asserts NO http_post call:
```python
assert "http_post" not in [c[0] for c in parent.mock_calls]
assert "db_update" in [c[0] for c in parent.mock_calls]
assert result["remote_revoked"] is False
assert result["remote_error"] == "no_remote_revoke_endpoint"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Refactor revoke_connection → async disconnect_account with _revoke_at_provider matrix</name>
  <files>
    app/social/connector.py,
    app/agents/tools/social.py,
    tests/unit/social/test_disconnect_revoke.py,
    tests/unit/social/conftest.py
  </files>
  <behavior>
    **RED — tests/unit/social/test_disconnect_revoke.py (10 tests, 8 platforms):**

    Set up parent-MagicMock recording per the pattern in the interfaces block. Tests:

    1. `test_twitter_disconnect_calls_revoke_before_db_update` — http_post to `https://api.x.com/2/oauth2/revoke` (or `api.twitter.com` — pick one and document); body `token=test-token` + `client_id=test-twitter-id`; auth tuple `(client_id, client_secret)`. Order: http_post → db_update.

    2. `test_linkedin_disconnect_skips_remote_revoke` — NO http_post call. db_update fires. `result["remote_revoked"]=False, result["remote_error"]="no_remote_revoke_endpoint"`. `result["success"]=True`.

    3. `test_facebook_disconnect_calls_delete_permissions_before_db_update` — http_delete to `https://graph.facebook.com/v18.0/me/permissions` with `Authorization: Bearer test-token`. Order: http_delete → db_update. (`mock_client.delete` is the recorded mock, `attach_mock(http_delete_mock, "http_delete")`.)

    4. `test_instagram_disconnect_calls_delete_permissions_before_db_update` — same endpoint as Facebook (Meta App). Order asserted.

    5. `test_youtube_disconnect_calls_google_revoke_before_db_update` — http_post to `https://oauth2.googleapis.com/revoke`, body `token=test-token`. Order asserted.

    6. `test_google_search_console_disconnect_uses_google_revoke_endpoint` — same as YouTube (single Google endpoint).

    7. `test_tiktok_disconnect_uses_client_key_in_body` — http_post to `https://open.tiktokapis.com/v2/oauth/revoke/`, body MUST contain `client_key=test-tiktok-key` (NOT `client_id`), `client_secret=...`, `token=test-token`. Order asserted.

    8. `test_threads_disconnect_calls_delete_permissions_on_threads_net` — http_delete to `https://graph.threads.net/v1.0/me/permissions` with bearer auth. Order asserted.

    9. `test_pinterest_disconnect_uses_basic_auth_token_revoke` — http_post to `https://api.pinterest.com/v5/oauth/token/revoke`, auth tuple, body `token=test-token&token_type_hint=access_token`. Order asserted.

    10. `test_disconnect_revoke_failure_still_updates_local_row` — using twitter as the example. http_post returns `status_code=500`. db_update STILL fires. Result: `{"success": True, "remote_revoked": False, "remote_error": <str>}`. Local row marked revoked.

    Bonus tests:

    11. `test_disconnect_with_no_stored_token_skips_remote_call` — supabase select returns no rows. Result: `{"success": True}` with local mark; no http call attempted.

    12. `test_revoke_connection_sync_wrapper_works` — calls `connector.revoke_connection("u1", "twitter")` (sync), confirms it returned the same shape as the async path (asserts the http and db calls were made). Use `asyncio.run` in test or rely on wrapper's own asyncio handling.

    Run `uv run pytest tests/unit/social/test_disconnect_revoke.py -x` — confirm all fail (RED).

    Commit: `test(108-04): add failing per-platform disconnect-revoke ordering tests (HYGIENE-04)`.

    **GREEN — implementation in `app/social/connector.py`:**

    1. **Add `_revoke_at_provider` method** (place after `_refresh_token`):
       ```python
       async def _revoke_at_provider(
           self, platform: str, token: str
       ) -> tuple[bool, str | None]:
           """POST to the provider's OAuth revoke endpoint.

           Returns (ok, error_message_or_None).
           Returns (False, "no_remote_revoke_endpoint") for LinkedIn (no public endpoint).
           Best-effort: any HTTP error is captured and returned, never raised.
           """
           import httpx

           if platform == "linkedin":
               return False, "no_remote_revoke_endpoint"

           config = PLATFORM_CONFIGS.get(platform, {})
           client_id = os.environ.get(config.get("client_id_env", ""))
           client_secret = os.environ.get(config.get("client_secret_env", ""))

           try:
               async with httpx.AsyncClient(timeout=15.0) as http:
                   if platform == "twitter":
                       resp = await http.post(
                           "https://api.twitter.com/2/oauth2/revoke",
                           data={"token": token, "client_id": client_id},
                           auth=(client_id, client_secret) if client_secret else None,
                       )
                   elif platform in ("youtube", "google_search_console", "google_analytics"):
                       resp = await http.post(
                           "https://oauth2.googleapis.com/revoke",
                           data={"token": token},
                       )
                   elif platform in ("facebook", "instagram"):
                       resp = await http.delete(
                           "https://graph.facebook.com/v18.0/me/permissions",
                           headers={"Authorization": f"Bearer {token}"},
                       )
                   elif platform == "threads":
                       resp = await http.delete(
                           "https://graph.threads.net/v1.0/me/permissions",
                           headers={"Authorization": f"Bearer {token}"},
                       )
                   elif platform == "tiktok":
                       resp = await http.post(
                           "https://open.tiktokapis.com/v2/oauth/revoke/",
                           data={
                               "client_key": client_id,
                               "client_secret": client_secret,
                               "token": token,
                           },
                       )
                   elif platform == "pinterest":
                       resp = await http.post(
                           "https://api.pinterest.com/v5/oauth/token/revoke",
                           auth=(client_id, client_secret),
                           data={"token": token, "token_type_hint": "access_token"},
                       )
                   else:
                       return False, f"unknown_platform:{platform}"

                   if resp.status_code in (200, 204):
                       return True, None
                   return False, f"{resp.status_code} {resp.text[:200]}"
           except Exception as exc:
               return False, str(exc)
       ```

    2. **Add async `disconnect_account` method** (place after `_revoke_at_provider`):
       ```python
       async def disconnect_account(
           self, user_id: str, platform: str
       ) -> dict[str, Any]:
           """Revoke at provider then mark the local row as revoked.

           Order is guaranteed: provider revoke is attempted first; the local
           row is updated regardless of remote outcome (best-effort revoke).
           """
           token = self.get_access_token(user_id, platform)

           remote_ok, remote_err = (False, None)
           if token:
               remote_ok, remote_err = await self._revoke_at_provider(platform, token)

           # Always update the local row last
           try:
               self.client.table("connected_accounts").update(
                   {"status": "revoked"}
               ).eq("user_id", user_id).eq("platform", platform).execute()
           except Exception as exc:
               logger.exception("Failed to mark %s connection revoked locally", platform)
               return {
                   "success": False,
                   "platform": platform,
                   "error": str(exc),
                   "remote_revoked": remote_ok,
                   "remote_error": remote_err,
               }

           return {
               "success": True,
               "platform": platform,
               "message": f"Disconnected {platform}",
               "remote_revoked": remote_ok,
               "remote_error": remote_err,
           }
       ```

    3. **Refactor `revoke_connection`** (sync wrapper for backward compat with `app/agents/tools/social.py:disconnect_social_account`):
       ```python
       def revoke_connection(self, user_id: str, platform: str) -> dict[str, Any]:
           """Sync wrapper; calls async disconnect_account.

           Tools running in non-async contexts (e.g., the LLM tool registry's
           sync function in app/agents/tools/social.py) call this. Async
           callers should call disconnect_account directly.
           """
           import asyncio
           try:
               loop = asyncio.get_event_loop()
               if loop.is_running():
                   # Already in an event loop; cannot use run_until_complete
                   import concurrent.futures
                   with concurrent.futures.ThreadPoolExecutor() as pool:
                       future = pool.submit(
                           asyncio.run, self.disconnect_account(user_id, platform)
                       )
                       return future.result(timeout=30)
           except RuntimeError:
               pass
           return asyncio.run(self.disconnect_account(user_id, platform))
       ```

    4. **`app/agents/tools/social.py`** — no signature change. The existing `disconnect_social_account` already calls `connector.revoke_connection(user_id, platform)`. The behavior change (now actually calling the provider) is transparent.

    Run `uv run pytest tests/unit/social/test_disconnect_revoke.py -x` — all 12 GREEN.

    Lint: `uv run ruff check app/social/connector.py app/agents/tools/social.py --fix && uv run ruff format app/social/connector.py app/agents/tools/social.py && uv run ty check app/social/connector.py app/agents/tools/social.py`.

    Commit: `feat(108-04): disconnect_account calls provider revoke before local row update (HYGIENE-04)`.
  </behavior>
  <action>
    Implement RED tests first, run them, then refactor.

    **Mocking strategy for the ordering tests:**

    The cleanest way to record both `httpx.AsyncClient.post`/`delete` calls AND the supabase `update().eq().eq().execute()` call into a single ordered MagicMock is via `attach_mock`:

    ```python
    parent = MagicMock()
    http_call = AsyncMock(return_value=MagicMock(status_code=200, text="ok"))
    db_call = MagicMock()
    parent.attach_mock(http_call, "http_call")
    parent.attach_mock(db_call, "db_call")

    # Patch the supabase chain so .update().eq().eq().execute -> db_call
    mock_supabase_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute = db_call

    # Patch httpx.AsyncClient to return a context manager that exposes http_call as both .post and .delete
    class _FakeAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        post = http_call
        delete = http_call

    with patch("httpx.AsyncClient", return_value=_FakeAsyncClient()):
        await fresh_connector.disconnect_account(user_id="u1", platform="twitter")

    # parent.mock_calls is in chronological order
    names = [c[0] for c in parent.mock_calls]
    assert names.index("http_call") < names.index("db_call")
    ```

    **Token-loading branch:** `disconnect_account` calls `get_access_token(user_id, platform)` which queries supabase and decrypts. Pre-load the supabase mock to return a token row:
    ```python
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"access_token": "ENC(test-token)", "refresh_token": None, "token_expires_at": None}]
    )
    ```
    The `patch_encryption` autouse fixture already makes `decrypt_secret("ENC(test-token)") == "test-token"`.

    **conftest.py extension:** Add a helper `make_revoke_test_setup(platform, env_overrides)` that returns the parent mock + fresh connector pre-wired for a given platform, so each test file is concise.

    Linters as in 108-01.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_disconnect_revoke.py -x 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    12 tests in test_disconnect_revoke.py GREEN. `_revoke_at_provider` dispatch matches the matrix in must_haves.revoke_endpoints exactly. `disconnect_account` is async and calls revoke before DB update. `revoke_connection` sync wrapper preserved for tool-side backward compat. LinkedIn returns `(False, "no_remote_revoke_endpoint")` without HTTP. Revoke failure does not block the local update. Existing tests pass. Ruff + ty clean. Commit lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Backfill per-platform handle_callback + post_with_media + _refresh_token tests for the existing 6 platforms</name>
  <files>
    tests/unit/social/test_connector_callback.py,
    tests/unit/social/test_connector_refresh.py,
    tests/unit/social/test_publisher_per_platform.py,
    tests/unit/social/conftest.py
  </files>
  <behavior>
    **No source code changes in this task — tests only.** This task delivers the bulk of the coverage gain by writing ~30+ tests for the existing 6 platforms. The tests assert the EXISTING behavior of the callback + publisher branches; if a test reveals a real bug (e.g., LinkedIn's `urn:li:person:PERSON_ID` placeholder making posts unusable), the fix is OUT OF SCOPE for plan 108-04 — surface it in the SUMMARY as "discovered bug, defer to Phase 103". The test for LinkedIn posting can ASSERT the placeholder behavior (i.e., the test confirms the current shape WITH the placeholder) and link the comment to POST-01 / Phase 103.

    **Per-platform callback tests** (tests/unit/social/test_connector_callback.py — extend the file from 108-01/02):

    For each of: linkedin, twitter, facebook, instagram, youtube, tiktok — add a test class `TestXxxCallback` with at least 3 tests:

    a. `test_<platform>_authorization_url_uses_correct_endpoint` — assert the auth URL matches `PLATFORM_CONFIGS[<platform>]["auth_url"]`, includes the env-configured `client_id`, the configured scopes (joined by spaces, URL-encoded), state with the user_id prefix, and the PKCE code_challenge with `code_challenge_method=S256`.

    b. `test_<platform>_callback_state_round_trip_and_token_exchange` — pre-load PKCE verifier, mock token endpoint to return a successful token response, assert supabase upsert called with `platform="<platform>"`, `user_id=` correctly extracted from state, encrypted access/refresh tokens, status="active".

    c. `test_<platform>_callback_token_exchange_4xx_returns_error` — assert error response shape when the token POST returns a 4xx.

    For platforms that include `user_id` in their token response (currently Threads — handled in 108-01), no extra capture test is needed. For LinkedIn/Twitter, the platform_user_id stays `None` until Phases 103/104 add follow-up profile calls — assert `platform_user_id` is `None` (current behavior; documents the gap).

    Total new tests in this file from this task: **18** (6 platforms × 3 tests).

    **Per-platform refresh tests** (tests/unit/social/test_connector_refresh.py — NEW FILE):

    For each platform that has a refresh path: linkedin, twitter, facebook, instagram, youtube, tiktok, threads, pinterest:

    - `test_<platform>_refresh_uses_correct_auth_method` — pre-load a row with expired `token_expires_at` and a `refresh_token`. Patch `httpx.Client` (sync) to return new tokens. Assert:
      - For `auth_method="form"` platforms: refresh body contains `client_id` and `client_secret`.
      - For `auth_method="basic"` platforms (pinterest only today): refresh request includes `auth=(client_id, client_secret)` and body does NOT contain client credentials.
      - In all cases, supabase update fires with the new access_token and (if returned) new refresh_token.

    - `test_<platform>_refresh_4xx_returns_none_keeps_old_token` — refresh returns 401; `_refresh_token` returns None; supabase row is unchanged.

    Total: **16** tests (8 platforms × 2 cases).

    **Per-platform publisher tests** (tests/unit/social/test_publisher_per_platform.py — extend from 108-01/02):

    For each of: twitter, linkedin, facebook, instagram, youtube, tiktok — add `TestXxxPublisher` with at least 3 tests:

    a. `test_<platform>_post_text_request_shape` — for platforms that allow text-only (twitter, linkedin, facebook), assert the URL, headers, JSON/data body. For text-only-rejecting platforms (instagram, youtube, tiktok), assert the structured error WITHOUT HTTP call.

    b. `test_<platform>_post_with_media_request_shape` — the primary media path per platform (twitter image, linkedin image, facebook photo, instagram image-via-container-publish, youtube video, tiktok pull-from-URL). Verify URL, headers, body shape.

    c. `test_<platform>_post_no_token_returns_error_without_http` — `get_access_token` returns None; `_get_token_or_error` returns the no-connection error; `mock_client.post` NEVER called.

    Special cases:
    - Instagram carousel test (`test_instagram_post_carousel_creates_children_then_container_then_publishes`) — assert the 3-step flow: N child container POSTs, 1 carousel container POST, 1 publish POST.
    - Instagram video → REELS test — assert media_type="REELS" in container body.
    - Facebook video test — assert request hits `me/videos` with `file_url` (CURRENT BEHAVIOR; broken per Phase 107 audit; the test documents the broken state and a code comment links to POST-09).

    Total new tests in this file from this task: **20+** (6 platforms × ~3.5 tests average).

    **PKCE state tests** (tests/unit/social/test_pkce_state.py — NEW FILE):

    - `test_generate_pkce_produces_s256_challenge` — verifier is a urlsafe string of expected length; `base64url(sha256(verifier))` (without padding) equals the challenge.
    - `test_store_and_pop_pkce_verifier_round_trip_via_supabase` — `_store_pkce_verifier(state, user_id, platform, verifier)` upserts into `oauth_pkce_states`; `_pop_pkce_verifier(state, platform)` returns the same verifier and deletes the row.
    - `test_pop_pkce_verifier_expired_returns_none` — pre-load a row with `expires_at` in the past; pop returns None and deletes the row.
    - `test_pop_pkce_verifier_wrong_platform_returns_none` — row has platform="twitter", pop is called with "linkedin"; returns None.
    - `test_store_pkce_verifier_falls_back_to_in_memory_on_db_error` — supabase upsert raises; verifier lands in `_pkce_verifiers` dict instead.
    - `test_pop_pkce_verifier_in_memory_fallback` — supabase select raises; verifier is read from `_pkce_verifiers` dict.

    Total: **6** tests.

    Run `uv run pytest tests/unit/social/ -x` — all tests GREEN.

    Run with coverage:
    ```
    uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing
    ```
    Confirm coverage ≥ 80% on `app/social/`. If below 80%, identify the uncovered lines (typically: defensive try/excepts in `_decrypt_token`, dead branches in `_refresh_token`, the `get_post_analytics` delegate) and add 1-2 targeted tests until threshold met.

    Commit: `test(108-04): per-platform callback + refresh + publisher + pkce coverage backfill (HYGIENE-04)`.
  </behavior>
  <action>
    Tests only — no source code changes (with one exception: minor refactors to make the existing code more testable are allowed if absolutely necessary, but flag in SUMMARY).

    **Splitting strategy:** if this task generates 60+ tests in one file, the executor MAY split into per-platform sub-files (e.g., `test_publisher_twitter.py`, `test_publisher_linkedin.py`) — but the goal is one file per concern (callback, refresh, publisher, pkce). Use test classes within each file.

    **Conftest extensions:** Add platform-specific env fixtures (`linkedin_env`, `twitter_env`, etc.) similar to `threads_env` and `pinterest_env` from 108-01/02. Add a `valid_token_response` factory that returns a different shape per platform.

    **Coverage tactics if below 80%:**
    - `_decrypt_token` has 4 except branches; write 4 tests with different mock side_effects.
    - `_refresh_token` has a `try/except Exception: return None` at line 463; force an exception via mock side_effect.
    - `get_post_analytics` delegates to `SocialAnalyticsService` — patch it with a MagicMock returning a known shape, verify delegation.

    **Edge case — encryption is patched in conftest:** the autouse `patch_encryption` fixture from 108-01 makes encrypt/decrypt identity-ish. Tests that specifically need to validate encrypted-shape behavior should disable the autouse fixture for that test class via `pytest.mark.usefixtures(...)` overrides or by importing the real functions directly.

    Linters: skipped (test files; ruff still checks them but the project's existing test files are loosely linted).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/ -x 2>&amp;1 | tail -10 &amp;&amp; uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing --cov-fail-under=80 2>&amp;1 | tail -25</automated>
  </verify>
  <done>
    All `tests/unit/social/` tests GREEN. Coverage report shows ≥80% line coverage on `app/social/`. Test counts by file:
    - `test_connector_callback.py`: 11 (108-01) + 5 (108-02) + 18 (this task) = ~34 tests
    - `test_connector_refresh.py` (NEW): 16 tests
    - `test_publisher_per_platform.py`: 6 (108-01) + 5 (108-02) + 20 (this task) = ~31 tests
    - `test_disconnect_revoke.py`: 12 tests (Task 1)
    - `test_pkce_state.py` (NEW): 6 tests
    - **Grand total: ~99 tests across plan 108-04 + carryover from 108-01/02**

    Any discovered bugs (e.g., LinkedIn placeholder URN, Facebook `file_url`) are documented in SUMMARY as "tested current behavior; fix tracked in Phase 103 / 107" — NOT fixed in 108-04. Commit lands.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Add make test-social target with --cov-fail-under=80</name>
  <files>
    Makefile
  </files>
  <behavior>
    Add a new convenience target near the existing `test:` target:

    ```makefile
    test-social:
    	uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing --cov-fail-under=80
    ```

    Run `make test-social` and confirm:
    - Exit code 0 (≥80% coverage achieved)
    - Coverage report printed to stdout

    Commit: `chore(108-04): add make test-social target with 80% coverage gate (HYGIENE-04)`.
  </behavior>
  <action>
    Use a real TAB character (Makefile syntax requirement) for the recipe line, not spaces. Insert near the existing `test:` target. Don't modify the main `test:` target — keep `make test` running its full existing suite (changing it would require coordinating with CI).

    Verify by running:
    ```
    make test-social
    ```
    If on Windows / PowerShell, run via `make test-social` in WSL or `bash -c 'make test-social'`. The Makefile target itself is portable; only invocation differs.
  </action>
  <verify>
    <automated>make test-social 2>&amp;1 | tail -25</automated>
  </verify>
  <done>
    Makefile has a `test-social` target that runs the social test suite with the 80% coverage gate. `make test-social` exits 0. Commit lands.
  </done>
</task>

</tasks>

<verification>
End-to-end verification for plan 108-04:

```
# Full social test suite
uv run pytest tests/unit/social/ -x 2>&1 | tail -10

# Coverage gate
uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing --cov-fail-under=80 2>&1 | tail -25

# Convenience target
make test-social 2>&1 | tail -10

# No regressions to broader test suite
uv run pytest tests/unit/ -x --no-header -q 2>&1 | tail -10
```

Manual verification (deferred to phase-level UAT, not gating this plan):
- Smoke test against a real Twitter/Threads/Pinterest dev account: connect → post → disconnect; verify the disconnect actually invalidates the token at the provider (subsequent post attempts return 401).
- Spot-check the migration applies cleanly on a fresh Supabase: `supabase db reset --local` then `\d connected_accounts` shows the platform CHECK with all 10 platforms.
</verification>

<success_criteria>
- `app/social/connector.py` has new methods: `_revoke_at_provider(platform, token) -> tuple[bool, str|None]` and `async disconnect_account(user_id, platform) -> dict`.
- `_revoke_at_provider` dispatches to the correct endpoint per the matrix in `must_haves.revoke_endpoints`. LinkedIn returns `(False, "no_remote_revoke_endpoint")` without HTTP.
- `disconnect_account` calls `_revoke_at_provider` BEFORE the supabase update — provable via mock_calls ordering test.
- Revoke failure (4xx/5xx/exception) does NOT prevent the local update; response includes `remote_revoked=False, remote_error=<str>`.
- `revoke_connection` sync wrapper preserved; `app/agents/tools/social.py:disconnect_social_account` unchanged in signature; behavior change is transparent.
- `tests/unit/social/test_disconnect_revoke.py` has ≥10 ordering tests (8 platforms + LinkedIn-skip + revoke-failure).
- Per-platform callback tests cover ALL 8 platforms with state round-trip + PKCE + token exchange success + token exchange failure.
- Per-platform `_refresh_token` tests cover all 8 platforms with `auth_method` branching.
- Per-platform `post_with_media` tests cover ALL 8 platforms with URL + headers + body shape + no-token + api-error cases.
- PKCE state tests cover `_generate_pkce`, supabase round-trip, expiry, wrong platform, in-memory fallback.
- `pytest --cov=app.social tests/unit/social/ --cov-fail-under=80` passes.
- `make test-social` exits 0.
- No regressions to other unit tests.
- `uv run ruff check app/social/ app/agents/tools/social.py` clean.
- Discovered bugs (LinkedIn URN placeholder, Facebook video file_url, Twitter chunked-upload incomplete) documented in SUMMARY but NOT fixed (Phase 103/104/107 territory).
</success_criteria>

<output>
After completion, create `.planning/phases/108-hygiene-and-coverage/108-04-disconnect-revoke-and-coverage-SUMMARY.md` documenting:
- Final test count breakdown per file (callback, refresh, publisher, disconnect, pkce)
- Final coverage percentage on `app/social/` from the cov report
- Provider revoke endpoint matrix as IMPLEMENTED (any deviation from the planned matrix flagged with rationale; specifically note Twitter `api.x.com` vs `api.twitter.com` choice and Threads MEDIUM-confidence verification status)
- List of bugs the test backfill SURFACED but did not fix (hand off to Phase 103, 104, 105, 107 as appropriate; cite file:line)
- Whether the in-memory `_pkce_verifiers` fallback is still adequate for production multi-worker (note: out of scope; AUTH-03 territory) — reassert decision from CONTEXT
- Confirmation that the 80% coverage gate is enforced via the new Makefile target
- Any deviations from this plan
</output>
