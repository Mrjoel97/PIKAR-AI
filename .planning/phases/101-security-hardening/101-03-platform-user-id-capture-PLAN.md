---
phase: 101-security-hardening
plan: 03
type: execute
wave: 2
depends_on: ["101-02"]
files_modified:
  - app/social/connector.py
  - tests/unit/social/test_profile_capture.py
autonomous: true
requirements: [AUTH-04]

must_haves:
  truths:
    - "After `SocialConnector.handle_callback` completes for any of the 6 in-scope platforms (linkedin, twitter, facebook, instagram, tiktok, youtube), the upserted row in `connected_accounts` contains `platform_user_id` and `platform_username` populated from that provider's profile endpoint — verified by per-provider unit tests that mock the profile-endpoint response and assert the upserted payload"
    - "Profile-fetch failure (404, 5xx, scope-missing, network timeout) does NOT abort the OAuth flow — the row is still upserted with `platform_user_id=None`/`platform_username=None`, the user sees the account as connected, and a WARNING is logged with the provider, status code, and user_id"
    - "Threads and Pinterest are explicitly OUT OF SCOPE for this plan (deferred to Phase 108 hygiene per RESEARCH §Open Questions §5); attempting to capture a profile for an unsupported platform short-circuits to `(None, None)` without an error"
    - "TikTok captures `platform_user_id` (open_id) but NOT `platform_username` (the `user.info.profile` scope is not in `PLATFORM_CONFIGS[\"tiktok\"][\"scopes\"]` per RESEARCH §Pitfall 4 — adding scopes is Phase 108 hygiene)"
  artifacts:
    - path: "app/social/connector.py"
      provides: "Adds private async helper `_fetch_platform_profile(platform, access_token, http) -> tuple[str | None, str | None]` covering linkedin, twitter, facebook, instagram (best-effort via me/accounts), tiktok (open_id only), youtube. `handle_callback` calls this helper after token exchange, before upsert; merges the returned ids into `connection_data` keys `platform_user_id`/`platform_username`. Failures caught and logged at WARNING; flow continues."
      contains: "_fetch_platform_profile"
    - path: "tests/unit/social/test_profile_capture.py"
      provides: "Six per-provider unit tests + one integration-style test verifying the failure-tolerance contract. Each provider test mocks the profile-endpoint HTTP call with a canned JSON response matching that provider's documented schema (per RESEARCH §AUTH-04 endpoint matrix), runs `await connector.handle_callback(...)`, and asserts `client.connected_account_upserts[0]` contains the expected `platform_user_id` + `platform_username`."
      contains: "test_linkedin_profile_capture"
  key_links:
    - from: "app/social/connector.py:handle_callback"
      to: "app/social/connector.py:_fetch_platform_profile"
      via: "After token exchange, before upsert: `pid, pname = await self._fetch_platform_profile(platform, access_token, http)` then `connection_data[\"platform_user_id\"] = pid; connection_data[\"platform_username\"] = pname`"
      pattern: "_fetch_platform_profile"
    - from: "app/social/connector.py:_fetch_platform_profile"
      to: "httpx.AsyncClient.get (provider profile endpoints)"
      via: "Per-platform branch: linkedin /v2/userinfo (sub, name); twitter /2/users/me (data.id, data.username); facebook /v18.0/me?fields=id,name (id, name); instagram /v18.0/me/accounts?fields=instagram_business_account{id,username} (page[0].instagram_business_account.{id,username}); tiktok /v2/user/info/?fields=open_id (data.user.open_id, None); youtube /youtube/v3/channels?mine=true&part=snippet,id (items[0].id, items[0].snippet.title)"
      pattern: "httpx.AsyncClient"
---

<objective>
Add the missing per-provider profile capture step to `SocialConnector.handle_callback` so `connected_accounts.platform_user_id` and `platform_username` are populated for all 6 in-scope social platforms (LinkedIn, Twitter, Facebook, Instagram, TikTok, YouTube).

Purpose: Satisfy AUTH-04 success criterion #4 (profile populated for every supported provider). Per RESEARCH §AUTH-04, the connection_data dict at `connector.py:326-334` does NOT populate `platform_user_id` or `platform_username`, even though both columns exist (`0010_connected_accounts.sql:8-9`) — and downstream consumers are broken because of it: `app/social/publisher.py:162` hardcodes `urn:li:person:PERSON_ID` (Phase 103 depends on this fix), `app/routers/configuration.py:480` shows `None` as the connected account name in the UI. The per-provider endpoint matrix is fully verified in RESEARCH §AUTH-04 with HIGH-confidence sources for LinkedIn, TikTok, Facebook, YouTube and MEDIUM for Twitter.

Per RESEARCH §Open Questions §4-5: Threads and Pinterest are out of `PLATFORM_CONFIGS` entirely and are deferred to Phase 108 hygiene; TikTok username requires a missing `user.info.profile` scope and is also deferred — TikTok captures only `open_id` here. The plan is scoped to the 6 platforms that already have working OAuth flows.

Output: One new private async method `_fetch_platform_profile` and a one-line wiring change in `handle_callback`. Six per-provider unit tests and one failure-tolerance test.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/101-security-hardening/101-RESEARCH.md
@.planning/phases/101-security-hardening/101-CONTEXT.md
@.planning/phases/101-security-hardening/101-02-pkce-redis-async-refresh-PLAN.md
@app/social/connector.py
@tests/unit/social/test_pkce_redis.py
@supabase/migrations/0010_connected_accounts.sql

<interfaces>
<!-- Provider profile endpoint matrix — verified in RESEARCH §AUTH-04 §Endpoint matrix -->
<!-- Use these EXACTLY. Do not change URLs, headers, or field paths without re-verifying against linked official docs. -->

| Platform | Endpoint (GET) | Auth | ID field | Username field |
|---|---|---|---|---|
| linkedin | https://api.linkedin.com/v2/userinfo | Bearer | resp.json()["sub"] | resp.json().get("name") |
| twitter | https://api.twitter.com/2/users/me | Bearer | resp.json()["data"]["id"] | resp.json()["data"]["username"] |
| facebook | https://graph.facebook.com/v18.0/me?fields=id,name | Bearer | resp.json()["id"] | resp.json()["name"] |
| instagram | https://graph.facebook.com/v18.0/me/accounts?fields=instagram_business_account{id,username} | Bearer | data[0]["instagram_business_account"]["id"] | data[0]["instagram_business_account"]["username"] |
| tiktok | https://open.tiktokapis.com/v2/user/info/?fields=open_id | Bearer | resp.json()["data"]["user"]["open_id"] | None (scope gap — Phase 108) |
| youtube | https://www.googleapis.com/youtube/v3/channels?part=snippet,id&mine=true | Bearer | items[0]["id"] | items[0]["snippet"]["title"] |

From app/social/connector.py (POST 101-02 — async signatures):
```python
class SocialConnector:
    async def handle_callback(self, platform, code, state, redirect_uri) -> dict[str, Any]:
        # ... PKCE read via Redis (post-101-02) ...
        async with httpx.AsyncClient() as http:
            resp = await http.post(config["token_url"], data=token_data)
            tokens = resp.json()
        access_token = tokens.get("access_token")
        # ... encryption ...
        connection_data = {
            "user_id": user_id,
            "platform": platform,
            "access_token": encrypted_access_token,
            "refresh_token": encrypted_refresh_token,
            # NEW: insert platform_user_id and platform_username here
            "token_expires_at": expires_at.isoformat(),
            "scopes": config["scopes"],
            "status": "active",
        }
        self.client.table("connected_accounts").upsert(...).execute()
```

The `_fetch_platform_profile` helper to add (full skeleton — copy and adapt):
```python
async def _fetch_platform_profile(
    self,
    platform: str,
    access_token: str,
    http: httpx.AsyncClient,
) -> tuple[str | None, str | None]:
    """Fetch (platform_user_id, platform_username) from the provider's profile endpoint.

    Returns (None, None) on any failure — the OAuth flow MUST NOT abort because
    profile capture failed. Failures are logged at WARNING level.

    Out-of-scope platforms (threads, pinterest) short-circuit to (None, None).
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        if platform == "linkedin":
            resp = await http.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=10.0)
            if resp.status_code == 200:
                j = resp.json()
                return j.get("sub"), j.get("name")
        elif platform == "twitter":
            resp = await http.get("https://api.twitter.com/2/users/me", headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return data.get("id"), data.get("username")
        elif platform == "facebook":
            resp = await http.get(
                "https://graph.facebook.com/v18.0/me",
                headers=headers,
                params={"fields": "id,name"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                j = resp.json()
                return j.get("id"), j.get("name")
        elif platform == "instagram":
            # Two-step (RESEARCH §Pitfall 5): /me/accounts -> page.instagram_business_account
            resp = await http.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                headers=headers,
                params={"fields": "instagram_business_account{id,username}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                pages = resp.json().get("data", []) or []
                for page in pages:
                    iba = page.get("instagram_business_account") or {}
                    if iba.get("id"):
                        return iba.get("id"), iba.get("username")
        elif platform == "tiktok":
            resp = await http.get(
                "https://open.tiktokapis.com/v2/user/info/",
                headers=headers,
                params={"fields": "open_id"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                user = (resp.json().get("data") or {}).get("user") or {}
                return user.get("open_id"), None  # username requires user.info.profile scope (Phase 108)
        elif platform == "youtube":
            resp = await http.get(
                "https://www.googleapis.com/youtube/v3/channels",
                headers=headers,
                params={"part": "snippet,id", "mine": "true"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                items = resp.json().get("items") or []
                if items:
                    snippet = items[0].get("snippet") or {}
                    return items[0].get("id"), snippet.get("title")
        # google_search_console, google_analytics — capture deferred (admin/API-only access, not user-facing)
        # threads, pinterest — not in PLATFORM_CONFIGS yet (Phase 108)

    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "Profile capture failed for platform=%s: %s",
            platform, exc,
        )

    return None, None
```

Existing test fixture pattern (REUSE from `tests/unit/social/test_pkce_redis.py`):
```python
# Same _FakeClient/_FakeTable + redis_mock fixture; the new test file should
# import or duplicate them. Recommendation: extract to tests/unit/social/conftest.py
# during Task 1 here so all three social test files (test_connector_encryption,
# test_pkce_redis, test_profile_capture) share fixtures.
```

Mocking httpx.AsyncClient for multi-call sequences:
```python
class _MockAsyncClient:
    def __init__(self, responses: list[dict]):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []
    async def __aenter__(self): return self
    async def __aexit__(self, *_): return False
    async def post(self, url, data=None, **kwargs):
        self.calls.append(("POST", {"url": url, "data": data}))
        return _MockResponse(self._responses.pop(0))
    async def get(self, url, headers=None, params=None, **kwargs):
        self.calls.append(("GET", {"url": url, "headers": headers, "params": params}))
        return _MockResponse(self._responses.pop(0))
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave-0 failing tests for per-provider profile capture</name>
  <files>tests/unit/social/conftest.py, tests/unit/social/test_profile_capture.py</files>
  <behavior>
    Seven tests, ALL FAILING initially because `_fetch_platform_profile` does not exist and `handle_callback` does not populate `platform_user_id`/`platform_username` in the upsert payload.

    Test parametrization: write SIX positive tests (one per platform: linkedin, twitter, facebook, instagram, tiktok, youtube) plus ONE negative test (failure tolerance). Each positive test follows this template:

    ```python
    @pytest.mark.asyncio
    async def test_<platform>_profile_capture(redis_mock, monkeypatch):
        client = _FakeClient()
        connector = _connector(client)
        state = "user-1:abc"
        # Configure redis_mock to return PKCE hit for the state
        redis_mock.get_generic = AsyncMock(return_value=CacheResult.hit({"verifier": "v", "platform": "<platform>"}))
        redis_mock.delete = AsyncMock(return_value=True)

        # Configure mock httpx: first POST = token exchange (200 OK with access_token);
        # second GET = profile endpoint (200 OK with the canned response)
        token_response = {"access_token": "real-bearer", "expires_in": 3600}
        profile_response = <CANNED PROVIDER JSON FROM TABLE BELOW>

        monkeypatch.setenv("<PLATFORM>_CLIENT_ID", "id")
        monkeypatch.setenv("<PLATFORM>_CLIENT_SECRET", "secret")

        with (
            patch("httpx.AsyncClient", _MockAsyncClient),
            patch("app.social.connector.encrypt_secret", side_effect=lambda v: f"enc:{v}"),
        ):
            _MockAsyncClient.responses = [token_response, profile_response]
            result = await connector.handle_callback("<platform>", "code", state, "https://app.test/cb")

        assert result.get("success") is True
        upsert = client.connected_account_upserts[-1]
        assert upsert["platform_user_id"] == "<EXPECTED_ID>"
        assert upsert["platform_username"] == "<EXPECTED_USERNAME>"
    ```

    Canned response payloads per platform (use these exactly to maintain doc-fidelity):

    | Platform | Canned profile response | Expected (id, username) |
    |---|---|---|
    | linkedin | `{"sub": "li-12345", "name": "Test User", "given_name": "Test", "family_name": "User"}` | `("li-12345", "Test User")` |
    | twitter | `{"data": {"id": "tw-67890", "username": "testhandle", "name": "Test"}}` | `("tw-67890", "testhandle")` |
    | facebook | `{"id": "fb-111", "name": "Test FB"}` | `("fb-111", "Test FB")` |
    | instagram | `{"data": [{"id": "page-1", "instagram_business_account": {"id": "ig-222", "username": "testig"}}]}` | `("ig-222", "testig")` |
    | tiktok | `{"data": {"user": {"open_id": "tt-333"}}}` | `("tt-333", None)` |
    | youtube | `{"items": [{"id": "yt-444", "snippet": {"title": "Test Channel"}}]}` | `("yt-444", "Test Channel")` |

    Special test:

    7. **test_profile_capture_failure_does_not_abort_callback**: Token exchange POST succeeds with `{"access_token": "real-bearer"}`. Profile GET returns 500 with body `"server error"`. Run `await connector.handle_callback("linkedin", ...)`. Assert: `result["success"] is True` (flow completes); `upsert["platform_user_id"] is None`; `upsert["platform_username"] is None`; a WARNING was logged with substring `"Profile capture failed"` and `"linkedin"`. Use `caplog.set_level(logging.WARNING, logger="app.social.connector")`.

    Run `uv run pytest tests/unit/social/test_profile_capture.py -x -v 2>&1 | tail -25`. ALL 7 fail.

    Commit message: `test(101-03): add failing tests for per-provider profile capture (AUTH-04)`.
  </behavior>
  <action>
    1. Create `tests/unit/social/conftest.py`. Move the `_FakeClient`/`_FakeTable` helpers (currently duplicated across `test_connector_encryption.py` and `test_pkce_redis.py`) into this module. Export them as `FakeClient` (drop the leading underscore for module-public consumption). Export a `redis_mock` fixture that patches `app.social.connector.get_cache_service` and yields a MagicMock with `set_generic`/`get_generic`/`delete` as `AsyncMock`s (default return values: `set_generic=True`, `get_generic=CacheResult.miss()`, `delete=True`). Update `test_connector_encryption.py` and `test_pkce_redis.py` to import from `conftest.py` and drop their local copies — this is incidental cleanup, NOT a behavior change.
    2. Create `tests/unit/social/test_profile_capture.py`. Imports: `from __future__ import annotations`, `import logging`, `import pytest`, `from unittest.mock import AsyncMock, patch`, `from app.services.cache import CacheResult`, `from app.social.connector import SocialConnector`, plus the `FakeClient` from conftest.
    3. Implement `_MockAsyncClient` and `_MockResponse` per the skeleton in <interfaces>. Class-attribute `responses` is reset per-test by the test body (NOT a fixture — keeps the test bodies self-contained).
    4. Six positive tests + one negative test, exactly per the canned-response table.
    5. Verify FAIL: `uv run pytest tests/unit/social/test_profile_capture.py -x -v 2>&1 | tail -25` — all 7 fail. Failure mode: `KeyError: "platform_user_id"` or `assert None == "li-12345"` (the upsert payload is missing the field entirely).
    6. Verify the conftest refactor did not break the OTHER social tests: `uv run pytest tests/unit/social/ -x 2>&1 | tail -20` — `test_connector_encryption.py` and `test_pkce_redis.py` still pass (after their imports are updated to use the conftest fixture).
    7. Lint: `uv run ruff check tests/unit/social/ --fix`.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_profile_capture.py -x -v 2>&1 | tail -25 && uv run pytest tests/unit/social/test_connector_encryption.py tests/unit/social/test_pkce_redis.py -x 2>&1 | tail -10</automated>
  </verify>
  <done>
    `tests/unit/social/conftest.py` exists with shared `FakeClient` + `redis_mock` fixture. The other two social test files import from conftest (their local fakes are removed) and still pass. `tests/unit/social/test_profile_capture.py` has 7 tests, ALL FAIL because `platform_user_id`/`platform_username` are not in the upsert payload. `ruff check` clean. Commit `test(101-03): add failing tests for per-provider profile capture (AUTH-04)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement `_fetch_platform_profile` and wire into handle_callback</name>
  <files>app/social/connector.py</files>
  <behavior>
    After this task, all 7 tests in Task 1 are GREEN. Other social tests still pass.

    Edits to `app/social/connector.py`:

    1. **Add `_fetch_platform_profile`** as a private method on `SocialConnector` (insert after the existing `_decrypt_token` method around current line 150). Body matches the skeleton in <interfaces>:
       - 6 platform branches (linkedin, twitter, facebook, instagram, tiktok, youtube) per the endpoint matrix.
       - Each branch: `await http.get(URL, headers=headers, [params=params,] timeout=10.0)`.
       - Each branch: on `resp.status_code == 200`, parse the documented field path; return `(id, username)`. On non-200, fall through to the bottom return.
       - Wrap the entire branching block in `try/except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:` — catches network errors, malformed JSON (KeyError on dict access), and unexpected types. Log at WARNING with platform + exc.
       - Default return at the bottom: `return None, None`.
       - The `http` parameter is the existing `httpx.AsyncClient` instance from `handle_callback`'s `async with httpx.AsyncClient()` block — REUSE the same client; do NOT open a second one.

    2. **Wire into `handle_callback`** (around current line 308 after token-exchange parsing, before encryption around line 314):
       ```python
       # Fetch provider profile to populate platform_user_id / platform_username (AUTH-04).
       # Best-effort: failures do not abort the OAuth flow.
       platform_user_id, platform_username = await self._fetch_platform_profile(
           platform, access_token, http,
       )
       ```
       Place this INSIDE the `async with httpx.AsyncClient() as http:` block (current line 302-308) so the same client is reused.
       The variable `access_token` referenced here is the plaintext token from `tokens.get("access_token")` — this is BEFORE encryption, intentionally, because the provider needs the bearer for the profile call.

    3. **Insert into `connection_data`** (current lines 326-334):
       ```python
       connection_data = {
           "user_id": user_id,
           "platform": platform,
           "access_token": encrypted_access_token,
           "refresh_token": encrypted_refresh_token,
           "platform_user_id": platform_user_id,    # NEW
           "platform_username": platform_username,  # NEW
           "token_expires_at": expires_at.isoformat(),
           "scopes": config["scopes"],
           "status": "active",
       }
       ```

    4. Run `uv run pytest tests/unit/social/ -x -v 2>&1 | tail -30` — all tests GREEN (existing 11 + new 7 = 18).

    5. Lint + types: `uv run ruff check app/social/connector.py --fix && uv run ruff format app/social/connector.py && uv run ty check app/social/connector.py`.

    Commit message: `feat(101-03): capture platform_user_id and platform_username on OAuth callback for 6 supported platforms (AUTH-04)`.
  </behavior>
  <action>
    1. Open `app/social/connector.py` and locate the `_decrypt_token` method (around line 131-150). Insert `_fetch_platform_profile` immediately after it (before `get_authorization_url`).
    2. The body is roughly 60 lines — reproduce the skeleton from <interfaces> verbatim, with the comprehensive try/except wrapping the platform branches.
    3. Locate `handle_callback` (around line 257). After the token-exchange `tokens = resp.json()` line (around line 308) and the access_token guard, BEFORE the encryption block (line 314), add the three-line profile fetch call.
    4. Update `connection_data` (around line 326) to include the two new keys.
    5. Verify GREEN: `uv run pytest tests/unit/social/ -x -v` — all 18 tests pass.
    6. Verify the `httpx` import at module scope (post-101-02 should already have it). If still inline, hoist to module imports.
    7. Lint + types as listed.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/ -x -v 2>&1 | tail -30 && uv run ruff check app/social/connector.py 2>&1 | tail -5</automated>
  </verify>
  <done>
    `app/social/connector.py` has `_fetch_platform_profile` defined with 6 platform branches matching the endpoint matrix exactly. `handle_callback` calls it and merges results into `connection_data`. All 18 tests in `tests/unit/social/` pass (including the 7 new ones). `ruff check` and `ty check` clean. Commit `feat(101-03): capture platform_user_id and platform_username on OAuth callback for 6 supported platforms (AUTH-04)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end:
1. `uv run pytest tests/unit/social/ -x -v` — 18 tests GREEN.
2. `uv run pytest tests/unit tests/integration -x` — full suite GREEN (record any unrelated failures and confirm baseline unchanged).
3. `grep -n "platform_user_id\|platform_username" app/social/connector.py` — confirm both keys appear in the `connection_data` dict literal AND `_fetch_platform_profile` returns the right tuple shape.
4. `grep -n "_fetch_platform_profile" app/social/connector.py` — exactly 2 matches: definition + the call site in `handle_callback`.

Manual UAT (deferred to phase-level UAT):
- Run a real LinkedIn OAuth round-trip; query `SELECT platform_user_id, platform_username FROM connected_accounts WHERE platform='linkedin' AND user_id = current_user_id ORDER BY connected_at DESC LIMIT 1` and confirm both columns are non-null.
- Repeat for Twitter (verifies the MEDIUM-confidence twitter endpoint per RESEARCH).
</verification>

<success_criteria>
- `app/social/connector.py` has `_fetch_platform_profile` with exactly 6 platform branches: linkedin, twitter, facebook, instagram, tiktok, youtube.
- `handle_callback` calls `_fetch_platform_profile` once after token exchange and before the upsert.
- `connection_data` dict literal includes `platform_user_id` and `platform_username` keys.
- Profile-fetch failures (HTTPError, KeyError, TypeError, ValueError) are caught and logged at WARNING with the platform name in the message — flow continues.
- 7 new tests in `tests/unit/social/test_profile_capture.py` are GREEN; existing 11 social tests still GREEN.
- `tests/unit/social/conftest.py` exists with shared `FakeClient` and `redis_mock` fixture; the two earlier test files import from it.
- `ruff check` and `ty check` clean for `app/social/connector.py` and the new test file.
- TikTok captures `open_id` only (`platform_username = None`) per RESEARCH §Pitfall 4 — documented as a Phase 108 follow-up.
- Threads and Pinterest are NOT in `_fetch_platform_profile` — the function returns `(None, None)` for any unknown platform.
</success_criteria>

<output>
After completion, create `.planning/phases/101-security-hardening/101-03-platform-user-id-capture-SUMMARY.md` documenting:
- Exact line ranges of the new `_fetch_platform_profile` method and the wiring change in `handle_callback`
- TikTok username scope deferral (linked to Phase 108 hygiene)
- Threads/Pinterest deferral (linked to Phase 108 hygiene; success criterion #4 of 101 was reduced from 8 to 6 platforms — note this in the SUMMARY so the milestone tracker is accurate)
- Test count delta (existing 11 → 18 in social/ scope)
</output>
