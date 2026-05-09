---
phase: 107-facebook-video-resumable-upload
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/social/connector.py
  - tests/unit/social/test_connector_facebook_pages.py
autonomous: true
requirements: [POST-09]

must_haves:
  truths:
    - "When the Facebook OAuth callback succeeds, the User access token is exchanged for the user's Page list via GET https://graph.facebook.com/v23.0/me/accounts before any row is written to connected_accounts"
    - "If the user has zero Pages, no connected_accounts row is written and the callback returns {'error': 'facebook_no_pages_found'}"
    - "If the user has at least one Page, the connected_accounts row stores: platform_user_id = selected Page's id, platform_username = selected Page's name, access_token = Fernet-encrypted Page access token (NOT the User token), metadata.user_token_enc = Fernet-encrypted User token (kept for future Page re-listing), metadata.available_pages = full Pages list, metadata.selected_page_id = chosen Page id"
    - "Multi-Page users auto-select the first Page returned by /me/accounts (UI for selection deferred to Phase 108); the full list is stashed in metadata.available_pages so a future endpoint can switch"
    - "Twitter, LinkedIn, Instagram, YouTube, TikTok callback paths are unchanged (the new behavior is gated on platform == 'facebook')"
  artifacts:
    - path: "app/social/connector.py"
      provides: "_fetch_facebook_pages helper (GET /me/accounts); facebook branch of handle_callback rewritten to fetch Pages, select one, encrypt the Page token + stash User token, write the row with platform_user_id + platform_username + metadata; PLATFORM_CONFIGS facebook + instagram entries bumped to v23.0"
      contains: "_fetch_facebook_pages"
    - path: "tests/unit/social/test_connector_facebook_pages.py"
      provides: "Unit tests asserting: (1) successful single-Page callback writes the right row, (2) multi-Page callback auto-selects first and stashes list, (3) zero-Page callback returns error and writes no row, (4) /me/accounts HTTP failure returns error and writes no row"
      contains: "test_callback_writes_page_id_for_single_page_user"
  key_links:
    - from: "app/social/connector.py:handle_callback (facebook branch)"
      to: "Meta Graph API GET https://graph.facebook.com/v23.0/me/accounts"
      via: "_fetch_facebook_pages helper after token exchange, before row insert"
      pattern: "me/accounts"
    - from: "app/social/connector.py:handle_callback (facebook branch)"
      to: "connected_accounts table (platform_user_id, platform_username, access_token, metadata)"
      via: "client.table('connected_accounts').upsert(...) with the selected Page's data"
      pattern: "platform_user_id"
    - from: "Plan 107-01:_get_facebook_page_context"
      to: "the row written by this plan"
      via: "select platform_user_id, access_token from connected_accounts where platform='facebook'"
      pattern: "platform_user_id"
---

<objective>
Augment `app/social/connector.py:handle_callback` so that the Facebook OAuth callback exchanges the User access token for a per-Page access token (via `GET /me/accounts`) and stores the Page-level credentials in `connected_accounts`. Without this change, Plan 107-01's three-phase video upload will pass unit tests but fail live: `phase=start` on `/{PAGE_ID}/videos` requires a Page token, and today's callback only stores a User token.

Purpose: Resolve the Page-vs-User auth gap flagged in `107-RESEARCH.md` (Path A — recommended, smaller scope). Audit confirmed (2026-05-08) that `app/social/connector.py:handle_callback` (lines 257-345) writes whatever token comes back from the OAuth code-exchange to `connected_accounts.access_token`, leaves `platform_user_id` NULL, and writes nothing to `metadata`. The Facebook OAuth scopes are already correct (`pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `read_insights` — all User-token-granted scopes that authorize the `/me/accounts` exchange). What's missing is the post-token-exchange step that follows Meta's documented Page-token flow.

This plan IS REQUIRED. It was made conditional in the planning prompt pending an audit of whether Phase 102 already captures Page tokens; that audit ran during planning and confirmed Phase 102 is scoped to Google Workspace only (per ROADMAP Phase 102 description: "Google Workspace Credential Bridge") and contains no Facebook code path. Phase 101 captures `platform_user_id` but its scope per ROADMAP wording is the generic "OAuth callback" — and the existing connector.py code today does not implement that capture either. Either way, Phase 107 cannot satisfy SC-1 without this plan.

Output: An async helper `_fetch_facebook_pages(access_token: str, api_version: str = "v23.0") -> list[dict]` that calls `GET https://graph.facebook.com/{api_version}/me/accounts?fields=id,name,access_token` and returns the `data` array. The `facebook` branch of `handle_callback` is rewritten to: (a) call `_fetch_facebook_pages`, (b) auto-select the first Page (or return error if zero), (c) encrypt the Page's access token and the User token separately, (d) upsert the row with `platform_user_id=page.id`, `platform_username=page.name`, `access_token=encrypted_page_token`, `metadata={"user_token_enc": ..., "available_pages": [...], "selected_page_id": ..., "selected_page_name": ...}`. The Facebook + Instagram entries in `PLATFORM_CONFIGS` are bumped to v23.0 (matching the standardization decided in 107-CONTEXT D-1). Four new unit tests in `tests/unit/social/test_connector_facebook_pages.py` cover the success, multi-Page, zero-Page, and HTTP-failure paths.

Plan 107-02 has NO dependency on Plan 107-01 (they touch different files). Both plans are Wave 1 and can execute in parallel. The full Phase-107 UAT (live posting) requires BOTH plans.
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
@app/social/connector.py
@supabase/migrations/0010_connected_accounts.sql

<interfaces>
<!-- Existing connector primitives the executor reuses (NO regression). -->

From app/social/connector.py:
```python
class SocialConnector:
    client: Client  # Supabase service client

    PLATFORM_CONFIGS = {
        "facebook": {
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",     # bump to v23.0
            "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",  # bump to v23.0
            "scopes": ["pages_show_list", "pages_manage_posts",
                       "pages_read_engagement", "read_insights"],
            "client_id_env": "FACEBOOK_APP_ID",
            "client_secret_env": "FACEBOOK_APP_SECRET",
        },
        "instagram": { ... v18.0 strings — bump to v23.0 ... },
        ...
    }

    def _encrypt_token(self, raw: str | None) -> str | None:
        """Fernet-encrypt or raise RuntimeError if not configured."""

    def _decrypt_token(self, encrypted: str | None) -> str | None:
        """Fernet-decrypt or return None."""

    def _pop_pkce_verifier(self, state: str, platform: str) -> str | None:
        """Already exists; consumed once."""

    async def handle_callback(
        self, platform: str, code: str, state: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Lines 257-345 today. Targeted edit: only the post-token-exchange
        block for platform == 'facebook' changes."""
```

From Meta Graph API docs (verified 2026-05-08):
```
GET https://graph.facebook.com/v23.0/me/accounts?fields=id,name,access_token
Authorization: Bearer <USER_ACCESS_TOKEN>

Response:
{
  "data": [
    {"id": "123456789", "name": "My Business Page", "access_token": "EAAG_PAGE_TOKEN_..."},
    {"id": "987654321", "name": "Another Page", "access_token": "EAAG_PAGE_TOKEN_..."}
  ],
  "paging": {...}
}
```

Note: the `/me/accounts` endpoint accepts the User token via either `Authorization: Bearer ...` header OR `?access_token=...` query string. Use the query-string form for parity with Meta's reference examples and to keep error messages legible (`Authorization` header errors are sometimes opaque). Page tokens returned in this list are long-lived if the User token was exchanged for a long-lived token; Meta's default flow already returns long-lived User tokens for `pages_*` scopes.

From connected_accounts schema (0010_connected_accounts.sql):
```sql
platform_user_id TEXT,            -- Will hold the Facebook Page ID
platform_username TEXT,           -- Will hold the Facebook Page name
access_token TEXT NOT NULL,       -- Will hold Fernet-encrypted Page access token
metadata JSONB DEFAULT '{}',      -- Will hold {"user_token_enc": str, "available_pages": [...], "selected_page_id": str, "selected_page_name": str}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _fetch_facebook_pages helper, rewire handle_callback facebook branch, bump v18.0 -> v23.0 in PLATFORM_CONFIGS</name>
  <files>app/social/connector.py</files>
  <behavior>
After this task, `app/social/connector.py`:

1. Defines a new module-level helper (or `SocialConnector` instance method — pick instance method for ergonomic test patching):

```python
async def _fetch_facebook_pages(
    self, user_access_token: str, api_version: str = "v23.0"
) -> list[dict]:
    """Fetch the user's manageable Facebook Pages.

    Calls GET /me/accounts with fields=id,name,access_token and returns the
    `data` array. Returns [] if the user has no Pages.

    Raises:
        httpx.HTTPStatusError: on non-2xx response from Meta.
    """
    import httpx

    url = f"https://graph.facebook.com/{api_version}/me/accounts"
    params = {"fields": "id,name,access_token", "access_token": user_access_token}
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.get(url, params=params)
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", [])
```

2. Rewrites the **post-token-exchange** block of `handle_callback` for `platform == "facebook"`. The token-exchange step (lines 290-313 today) is unchanged. After the User token is obtained, but BEFORE the row is upserted, insert the Facebook-specific branch:

```python
# After: access_token = tokens.get("access_token") (line 310 today)
# After: try: encrypted_access_token = self._encrypt_token(access_token) ... (lines 314-319 today)
# REPLACE the connection_data + upsert block (lines 326-339) with:

if platform == "facebook":
    # Exchange the User token for per-Page tokens via /me/accounts.
    try:
        pages = await self._fetch_facebook_pages(access_token, api_version="v23.0")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Facebook /me/accounts fetch failed: %s — %s",
            exc.response.status_code, exc.response.text,
        )
        return {
            "error": "facebook_pages_fetch_failed",
            "detail": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
        }
    except httpx.RequestError as exc:
        logger.warning("Facebook /me/accounts network error: %s", exc)
        return {"error": "facebook_pages_fetch_failed", "detail": str(exc)}

    if not pages:
        return {
            "error": "facebook_no_pages_found",
            "detail": (
                "No Facebook Pages found for this account. "
                "The user must be an admin/editor of at least one Page."
            ),
        }

    # Auto-select the first Page (multi-Page selection UI deferred to Phase 108).
    selected_page = pages[0]
    page_id = selected_page["id"]
    page_name = selected_page.get("name", "")
    page_access_token = selected_page["access_token"]

    try:
        encrypted_page_token = self._encrypt_token(page_access_token)
        encrypted_user_token = self._encrypt_token(access_token)
        encrypted_refresh_token = self._encrypt_token(tokens.get("refresh_token"))
    except RuntimeError:
        logger.exception("Social token encryption is not configured")
        return {"error": "Social token encryption is not configured"}

    expires_in = tokens.get("expires_in", 3600)
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    # Stash the User token + full Pages list in metadata for future re-listing.
    available_pages_meta = [
        {"id": p["id"], "name": p.get("name", "")} for p in pages
    ]

    connection_data = {
        "user_id": user_id,
        "platform": platform,
        "platform_user_id": page_id,
        "platform_username": page_name,
        "access_token": encrypted_page_token,  # the PAGE token, not user token
        "refresh_token": encrypted_refresh_token,
        "token_expires_at": expires_at.isoformat(),
        "scopes": config["scopes"],
        "status": "active",
        "metadata": {
            "user_token_enc": encrypted_user_token,
            "available_pages": available_pages_meta,
            "selected_page_id": page_id,
            "selected_page_name": page_name,
        },
    }

    self.client.table("connected_accounts").upsert(
        connection_data, on_conflict="user_id,platform"
    ).execute()

    return {
        "success": True,
        "platform": platform,
        "page_id": page_id,
        "page_name": page_name,
        "available_pages": available_pages_meta,
        "message": (
            f"Successfully connected Facebook Page '{page_name}'"
            + (
                f" ({len(pages)} Pages available; auto-selected first)"
                if len(pages) > 1 else ""
            )
        ),
    }
```

3. Bump v18.0 → v23.0 in `PLATFORM_CONFIGS` for `facebook` and `instagram`:
   - `auth_url`: `https://www.facebook.com/v18.0/dialog/oauth` → `https://www.facebook.com/v23.0/dialog/oauth`
   - `token_url`: `https://graph.facebook.com/v18.0/oauth/access_token` → `https://graph.facebook.com/v23.0/oauth/access_token`
   - Apply to both the `facebook` and `instagram` entries (Instagram uses Facebook's OAuth).

4. The non-Facebook branches of `handle_callback` keep using the existing `connection_data` shape (no `platform_user_id`, no `metadata`). This minimizes blast radius. The existing `connection_data` block (lines 326-339 today) is moved INSIDE an `else:` branch:

```python
else:  # all non-facebook platforms
    connection_data = {
        "user_id": user_id,
        "platform": platform,
        "access_token": encrypted_access_token,
        "refresh_token": encrypted_refresh_token,
        "token_expires_at": expires_at.isoformat(),
        "scopes": config["scopes"],
        "status": "active",
    }
    self.client.table("connected_accounts").upsert(
        connection_data, on_conflict="user_id,platform"
    ).execute()
    return {
        "success": True,
        "platform": platform,
        "message": f"Successfully connected {platform} account",
    }
```

(Capturing `platform_user_id` for Twitter/LinkedIn/etc. is a Phase 101 / 103 / 104 concern — out of scope here.)

5. Add `import httpx` at module scope (it's currently lazy-imported inside `handle_callback`; promoting it to module scope makes the helper signature cleaner and the test patching simpler). If keeping lazy imports is preferred for memory, leave `_fetch_facebook_pages` with its inline `import httpx`. Recommendation: **keep the inline import inside `_fetch_facebook_pages`** to match the existing style of `handle_callback`. The `except httpx.HTTPStatusError`/`except httpx.RequestError` catches in the facebook branch ALSO need `import httpx` accessible — since `handle_callback` already has `import httpx` inline (line 271 today), reuse that scope. (The `httpx` import in `handle_callback` happens early enough that the facebook branch sees it.)

6. Run `uv run ruff check app/social/connector.py --fix && uv run ruff format app/social/connector.py && uv run ty check app/social/connector.py`. Clean.

7. Run `grep -nE "v18\.0" app/social/connector.py` — output MUST be empty.

8. Run the existing test suite to confirm no regression: `uv run pytest tests/ -x -k "connector or oauth or social"`. If there are no existing connector tests, this is a no-op (acceptable).

Commit message: `feat(107-02): capture Facebook Page tokens at OAuth callback via /me/accounts (POST-09)`.
  </behavior>
  <action>
1. Open `app/social/connector.py`.

2. Locate `PLATFORM_CONFIGS` (lines ~33-90). In the `facebook` and `instagram` entries, replace `v18.0` with `v23.0` in `auth_url` and `token_url`. (4 string replacements total: 2 per platform.)

3. Add the `_fetch_facebook_pages` method to `SocialConnector`. Place it near the other instance helpers (e.g., right before `handle_callback`):

```python
async def _fetch_facebook_pages(
    self, user_access_token: str, api_version: str = "v23.0"
) -> list[dict]:
    """Fetch Facebook Pages the user can manage.

    Calls GET /me/accounts with fields=id,name,access_token and returns the
    `data` array (may be empty).

    Raises:
        httpx.HTTPStatusError on non-2xx; httpx.RequestError on network failure.
    """
    import httpx

    url = f"https://graph.facebook.com/{api_version}/me/accounts"
    params = {
        "fields": "id,name,access_token",
        "access_token": user_access_token,
    }
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.get(url, params=params)
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", [])
```

4. In `handle_callback`, locate the block from `# Store connection` (around line 325) through the final `return {"success": True, ...}` (around line 345). REPLACE that block with:

```python
# Store connection — Facebook needs the Page-token exchange first.
if platform == "facebook":
    try:
        pages = await self._fetch_facebook_pages(access_token, api_version="v23.0")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Facebook /me/accounts fetch failed: %s — %s",
            exc.response.status_code, exc.response.text,
        )
        return {
            "error": "facebook_pages_fetch_failed",
            "detail": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
        }
    except httpx.RequestError as exc:
        logger.warning("Facebook /me/accounts network error: %s", exc)
        return {"error": "facebook_pages_fetch_failed", "detail": str(exc)}

    if not pages:
        return {
            "error": "facebook_no_pages_found",
            "detail": (
                "No Facebook Pages found for this account. "
                "The user must be an admin/editor of at least one Page."
            ),
        }

    selected_page = pages[0]
    page_id = selected_page["id"]
    page_name = selected_page.get("name", "")
    page_access_token = selected_page["access_token"]

    try:
        encrypted_page_token = self._encrypt_token(page_access_token)
        encrypted_user_token = self._encrypt_token(access_token)
        encrypted_refresh_token = self._encrypt_token(tokens.get("refresh_token"))
    except RuntimeError:
        logger.exception("Social token encryption is not configured")
        return {"error": "Social token encryption is not configured"}

    expires_in = tokens.get("expires_in", 3600)
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    available_pages_meta = [
        {"id": p["id"], "name": p.get("name", "")} for p in pages
    ]

    connection_data = {
        "user_id": user_id,
        "platform": platform,
        "platform_user_id": page_id,
        "platform_username": page_name,
        "access_token": encrypted_page_token,
        "refresh_token": encrypted_refresh_token,
        "token_expires_at": expires_at.isoformat(),
        "scopes": config["scopes"],
        "status": "active",
        "metadata": {
            "user_token_enc": encrypted_user_token,
            "available_pages": available_pages_meta,
            "selected_page_id": page_id,
            "selected_page_name": page_name,
        },
    }

    self.client.table("connected_accounts").upsert(
        connection_data, on_conflict="user_id,platform"
    ).execute()

    return {
        "success": True,
        "platform": platform,
        "page_id": page_id,
        "page_name": page_name,
        "available_pages": available_pages_meta,
        "message": (
            f"Successfully connected Facebook Page '{page_name}'"
            + (
                f" ({len(pages)} Pages available; auto-selected first)"
                if len(pages) > 1 else ""
            )
        ),
    }

# All non-facebook platforms — keep the original behavior.
connection_data = {
    "user_id": user_id,
    "platform": platform,
    "access_token": encrypted_access_token,
    "refresh_token": encrypted_refresh_token,
    "token_expires_at": expires_at.isoformat(),
    "scopes": config["scopes"],
    "status": "active",
}

self.client.table("connected_accounts").upsert(
    connection_data, on_conflict="user_id,platform"
).execute()

return {
    "success": True,
    "platform": platform,
    "message": f"Successfully connected {platform} account",
}
```

5. Verify `httpx` is in scope inside `handle_callback` (it's already imported at line 271 today: `import httpx`). The new `except httpx.HTTPStatusError`/`except httpx.RequestError` lines reuse that import.

6. Run `uv run ruff check app/social/connector.py --fix && uv run ruff format app/social/connector.py && uv run ty check app/social/connector.py`. Clean.

7. Run `grep -nE "v18\.0" app/social/connector.py` — empty.

8. Run `uv run pytest tests/ -x -k "connector or oauth"` — no regressions (or no tests collected, both acceptable).

DO NOT touch `publisher.py` (Plan 107-01 owns it).
  </action>
  <verify>
    <automated>uv run ruff check app/social/connector.py 2>&amp;1 | tail -5 &amp;&amp; uv run ty check app/social/connector.py 2>&amp;1 | tail -5 &amp;&amp; (! grep -nE "v18\.0" app/social/connector.py)</automated>
  </verify>
  <done>
- `app/social/connector.py` defines `SocialConnector._fetch_facebook_pages`.
- `handle_callback` for `platform == "facebook"` calls `_fetch_facebook_pages`, handles zero-Pages and HTTP-failure cases (returns structured error, writes no row), auto-selects the first Page on success, encrypts the Page token + User token separately, and upserts a row with `platform_user_id`, `platform_username`, `metadata.user_token_enc`, `metadata.available_pages`, `metadata.selected_page_id`, `metadata.selected_page_name`.
- All other platforms keep their original `connection_data` shape (in the `else` branch).
- `PLATFORM_CONFIGS` `facebook` and `instagram` entries have `auth_url` and `token_url` bumped to v23.0 (4 string changes).
- `grep -nE "v18\.0" app/social/connector.py` empty.
- `ruff check`, `ty check` clean.
- Commit `feat(107-02): capture Facebook Page tokens at OAuth callback via /me/accounts (POST-09)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Unit tests for the Facebook page-token capture flow</name>
  <files>tests/unit/social/test_connector_facebook_pages.py</files>
  <behavior>
After this task, `tests/unit/social/test_connector_facebook_pages.py` contains four tests, all GREEN against the Task-1 implementation:

1. **test_callback_writes_page_id_for_single_page_user** (happy single-Page path):
   - Patches `httpx.AsyncClient.post` (token-exchange) AND `httpx.AsyncClient.get` (`/me/accounts`) via `respx`.
   - Token-exchange POST returns `{"access_token": "USER_TOKEN", "expires_in": 3600}`.
   - `/me/accounts` GET returns `{"data": [{"id": "PAGE_1", "name": "My Page", "access_token": "PAGE_TOKEN_1"}]}`.
   - Patches `SocialConnector.client.table().upsert().execute()` via `unittest.mock.MagicMock`.
   - Patches `_pop_pkce_verifier` to return `"FAKE_VERIFIER"`.
   - Patches `_encrypt_token` to return f`enc({raw})` (deterministic).
   - Calls `await connector.handle_callback(platform="facebook", code="CODE", state=f"{user_id}:STATE", redirect_uri="https://example.com/cb")`.
   - Asserts: result["success"] is True.
   - Asserts: result["page_id"] == "PAGE_1".
   - Asserts: result["page_name"] == "My Page".
   - Asserts: the upsert was called once.
   - Asserts: the upsert payload's `platform_user_id == "PAGE_1"`.
   - Asserts: the upsert payload's `platform_username == "My Page"`.
   - Asserts: the upsert payload's `access_token == "enc(PAGE_TOKEN_1)"` (the PAGE token, encrypted).
   - Asserts: the upsert payload's `metadata["user_token_enc"] == "enc(USER_TOKEN)"`.
   - Asserts: the upsert payload's `metadata["available_pages"] == [{"id": "PAGE_1", "name": "My Page"}]`.
   - Asserts: the upsert payload's `metadata["selected_page_id"] == "PAGE_1"`.

2. **test_callback_auto_selects_first_page_for_multi_page_user**:
   - `/me/accounts` GET returns 3 Pages: PAGE_A, PAGE_B, PAGE_C.
   - Asserts: result["page_id"] == "PAGE_A" (first in list).
   - Asserts: result["available_pages"] has 3 entries with the expected ids.
   - Asserts: result["message"] contains `"3 Pages available"`.
   - Asserts: the upsert payload's `metadata["available_pages"]` has 3 entries.

3. **test_callback_returns_error_when_user_has_no_pages**:
   - `/me/accounts` GET returns `{"data": []}`.
   - Asserts: result["error"] == "facebook_no_pages_found".
   - Asserts: the upsert mock was NOT called (no row written).

4. **test_callback_returns_error_when_me_accounts_fails_http**:
   - `/me/accounts` GET returns HTTP 400 `{"error": {"message": "Invalid OAuth access token"}}`.
   - Asserts: result["error"] == "facebook_pages_fetch_failed".
   - Asserts: result["detail"] starts with "HTTP 400:".
   - Asserts: the upsert mock was NOT called.

Each async test uses `@pytest.mark.asyncio` AND `@respx.mock`. The Supabase client is faked entirely via `MagicMock` — these are pure unit tests with no DB.

Run `uv run pytest tests/unit/social/test_connector_facebook_pages.py -x -v`. All 4 tests GREEN.

Commit message: `test(107-02): unit tests for Facebook Page-token capture at OAuth callback (POST-09)`.
  </behavior>
  <action>
Create `tests/unit/social/test_connector_facebook_pages.py`:

```python
"""Unit tests for the Facebook Page-token capture step in handle_callback.

Covers POST-09 SC-1 prerequisite (Plan 107-02): the OAuth callback must
exchange the User token for a per-Page access token and store the Page
ID + Page token in connected_accounts so Plan 107-01's three-phase
upload can resolve them.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from app.social.connector import SocialConnector


def _make_connector_with_mocks(
    upsert_mock: MagicMock,
    select_mock: MagicMock | None = None,
) -> SocialConnector:
    """Build a SocialConnector with a faked Supabase client.

    upsert_mock: the MagicMock that connector.client.table('connected_accounts').upsert(...).execute returns.
    """
    connector = SocialConnector.__new__(SocialConnector)  # bypass __init__
    fake_client = MagicMock()

    # connector.client.table("connected_accounts").upsert(...).execute()
    table_mock = MagicMock()
    upsert_chain = MagicMock()
    upsert_chain.execute = upsert_mock
    table_mock.upsert.return_value = upsert_chain
    if select_mock is not None:
        select_chain = MagicMock()
        select_chain.execute = select_mock
        table_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value = select_chain  # noqa: E501

    fake_client.table.return_value = table_mock
    connector.client = fake_client
    return connector


@pytest.fixture
def connector_factory():
    return _make_connector_with_mocks


@pytest.fixture
def patched_env(monkeypatch):
    """Set Facebook client_id / client_secret env vars."""
    monkeypatch.setenv("FACEBOOK_APP_ID", "FAKE_APP_ID")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "FAKE_APP_SECRET")
    yield


@pytest.mark.asyncio
@respx.mock
async def test_callback_writes_page_id_for_single_page_user(
    connector_factory, patched_env, fake_user_id
):
    upsert_execute = MagicMock()
    connector = connector_factory(upsert_execute)
    state = f"{fake_user_id}:STATE_TOKEN"

    # Mock /v23.0/oauth/access_token (token exchange)
    respx.post("https://graph.facebook.com/v23.0/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "USER_TOKEN", "expires_in": 3600},
        )
    )
    # Mock /v23.0/me/accounts (Page list)
    respx.get("https://graph.facebook.com/v23.0/me/accounts").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"id": "PAGE_1", "name": "My Page", "access_token": "PAGE_TOKEN_1"},
                ]
            },
        )
    )

    # Patch _pop_pkce_verifier and _encrypt_token
    with patch.object(connector, "_pop_pkce_verifier", return_value="FAKE_VERIFIER"), \
         patch.object(
             connector,
             "_encrypt_token",
             side_effect=lambda raw: f"enc({raw})" if raw is not None else None,
         ):
        result = await connector.handle_callback(
            platform="facebook",
            code="CODE",
            state=state,
            redirect_uri="https://example.com/cb",
        )

    assert result["success"] is True
    assert result["page_id"] == "PAGE_1"
    assert result["page_name"] == "My Page"
    assert upsert_execute.call_count == 1

    upsert_call_args = (
        connector.client.table.return_value.upsert.call_args
    )
    payload = upsert_call_args.args[0]
    assert payload["platform_user_id"] == "PAGE_1"
    assert payload["platform_username"] == "My Page"
    assert payload["access_token"] == "enc(PAGE_TOKEN_1)"
    assert payload["metadata"]["user_token_enc"] == "enc(USER_TOKEN)"
    assert payload["metadata"]["available_pages"] == [
        {"id": "PAGE_1", "name": "My Page"},
    ]
    assert payload["metadata"]["selected_page_id"] == "PAGE_1"
    assert payload["metadata"]["selected_page_name"] == "My Page"


@pytest.mark.asyncio
@respx.mock
async def test_callback_auto_selects_first_page_for_multi_page_user(
    connector_factory, patched_env, fake_user_id
):
    upsert_execute = MagicMock()
    connector = connector_factory(upsert_execute)
    state = f"{fake_user_id}:STATE_TOKEN"

    respx.post("https://graph.facebook.com/v23.0/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "USER_TOKEN", "expires_in": 3600},
        )
    )
    respx.get("https://graph.facebook.com/v23.0/me/accounts").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"id": "PAGE_A", "name": "Page A", "access_token": "PT_A"},
                    {"id": "PAGE_B", "name": "Page B", "access_token": "PT_B"},
                    {"id": "PAGE_C", "name": "Page C", "access_token": "PT_C"},
                ]
            },
        )
    )

    with patch.object(connector, "_pop_pkce_verifier", return_value="FV"), \
         patch.object(
             connector, "_encrypt_token",
             side_effect=lambda raw: f"enc({raw})" if raw is not None else None,
         ):
        result = await connector.handle_callback(
            platform="facebook",
            code="CODE",
            state=state,
            redirect_uri="https://example.com/cb",
        )

    assert result["success"] is True
    assert result["page_id"] == "PAGE_A"  # first auto-selected
    assert len(result["available_pages"]) == 3
    assert {p["id"] for p in result["available_pages"]} == {"PAGE_A", "PAGE_B", "PAGE_C"}
    assert "3 Pages available" in result["message"]

    payload = connector.client.table.return_value.upsert.call_args.args[0]
    assert len(payload["metadata"]["available_pages"]) == 3
    assert payload["platform_user_id"] == "PAGE_A"
    assert payload["access_token"] == "enc(PT_A)"


@pytest.mark.asyncio
@respx.mock
async def test_callback_returns_error_when_user_has_no_pages(
    connector_factory, patched_env, fake_user_id
):
    upsert_execute = MagicMock()
    connector = connector_factory(upsert_execute)
    state = f"{fake_user_id}:STATE_TOKEN"

    respx.post("https://graph.facebook.com/v23.0/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "USER_TOKEN", "expires_in": 3600},
        )
    )
    respx.get("https://graph.facebook.com/v23.0/me/accounts").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with patch.object(connector, "_pop_pkce_verifier", return_value="FV"), \
         patch.object(connector, "_encrypt_token", side_effect=lambda r: f"enc({r})"):
        result = await connector.handle_callback(
            platform="facebook",
            code="CODE",
            state=state,
            redirect_uri="https://example.com/cb",
        )

    assert result["error"] == "facebook_no_pages_found"
    assert upsert_execute.call_count == 0  # no row written


@pytest.mark.asyncio
@respx.mock
async def test_callback_returns_error_when_me_accounts_fails_http(
    connector_factory, patched_env, fake_user_id
):
    upsert_execute = MagicMock()
    connector = connector_factory(upsert_execute)
    state = f"{fake_user_id}:STATE_TOKEN"

    respx.post("https://graph.facebook.com/v23.0/oauth/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "USER_TOKEN", "expires_in": 3600},
        )
    )
    respx.get("https://graph.facebook.com/v23.0/me/accounts").mock(
        return_value=httpx.Response(
            400, json={"error": {"message": "Invalid OAuth access token"}},
        )
    )

    with patch.object(connector, "_pop_pkce_verifier", return_value="FV"), \
         patch.object(connector, "_encrypt_token", side_effect=lambda r: f"enc({r})"):
        result = await connector.handle_callback(
            platform="facebook",
            code="CODE",
            state=state,
            redirect_uri="https://example.com/cb",
        )

    assert result["error"] == "facebook_pages_fetch_failed"
    assert result["detail"].startswith("HTTP 400:")
    assert upsert_execute.call_count == 0
```

Run:
- `uv run pytest tests/unit/social/test_connector_facebook_pages.py -x -v 2>&1 | tail -40`. All 4 tests GREEN.
- `uv run pytest tests/unit/social/ -x` — directory-level pass (joins the 4 from Plan 107-01 if both have landed).
- `uv run ruff check tests/unit/social/test_connector_facebook_pages.py --fix && uv run ruff format tests/unit/social/test_connector_facebook_pages.py`. Clean.

NOTE: this file imports `fake_user_id` from `conftest.py`. If Plan 107-01 Task 1 has NOT landed yet (defining the fixture), this test file will fail at collection. Plan 107-01 Task 1 (Wave-0 scaffolding) is a hard prerequisite for THIS task. Coordinate execution: 107-01 Task 1 must land before 107-02 Task 2. Either: (a) execute 107-01 first, or (b) inline the `fake_user_id` fixture into THIS test file as a backup. Recommendation: option (a) — wait for 107-01 Task 1 — to keep fixtures DRY.

If running in parallel and 107-01 Task 1 has not committed yet, this task should locally create `tests/unit/social/__init__.py` and a minimal `tests/unit/social/conftest.py` containing just the `fake_user_id` fixture. The 107-01 conftest then ADDITIVELY adds the publisher-test fixtures (matching imports). Note this in the SUMMARY.

Recommended sequencing in execute-phase: run 107-01 first (or 107-01 Task 1 first), then 107-02. The plans are otherwise independent.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/social/test_connector_facebook_pages.py -x -v 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
- `tests/unit/social/test_connector_facebook_pages.py` exists with 4 tests covering single-Page success, multi-Page auto-select, zero-Pages error, and `/me/accounts` HTTP-failure error.
- All 4 tests GREEN under `uv run pytest tests/unit/social/test_connector_facebook_pages.py -x`.
- `tests/unit/social/` directory passes in full when combined with 107-01's tests.
- `ruff check` clean on the new test file.
- Commit `test(107-02): unit tests for Facebook Page-token capture at OAuth callback (POST-09)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end automated:
1. `uv run pytest tests/unit/social/test_connector_facebook_pages.py -x -v` — all 4 tests GREEN.
2. `uv run pytest tests/unit/social/ -x` — directory-level pass (4 from 107-01 + 4 from 107-02 = 8 tests total once both plans land).
3. `uv run ruff check app/social/connector.py tests/unit/social/test_connector_facebook_pages.py` — clean.
4. `uv run ty check app/social/connector.py` — clean.
5. `! grep -nE "v18\.0" app/social/connector.py` — empty.

Manual smoke (deferred to phase-level UAT):
- Run a real Facebook OAuth flow in `make local-backend`. Confirm `connected_accounts` row has `platform_user_id` (Page ID), `platform_username` (Page name), `metadata.available_pages` (full list), and `metadata.user_token_enc`. The `access_token` column should decrypt to a Page token (starts with `EAAG...` and tests as a Page token by calling `GET /v23.0/{page_id}?fields=id,name&access_token=<decrypted>` returning that Page's id/name).
</verification>

<success_criteria>
- `app/social/connector.py` defines `SocialConnector._fetch_facebook_pages(user_access_token, api_version="v23.0") -> list[dict]` calling `GET /me/accounts?fields=id,name,access_token`.
- `handle_callback` for `platform == "facebook"` calls `_fetch_facebook_pages` after token exchange and BEFORE the row insert.
- Zero-Page response returns `{"error": "facebook_no_pages_found", ...}` and writes no row.
- HTTP failure on `/me/accounts` returns `{"error": "facebook_pages_fetch_failed", "detail": "HTTP {code}: ..."}` and writes no row.
- On success: row stores `platform_user_id=page.id`, `platform_username=page.name`, `access_token=encrypt(page.access_token)`, `metadata={"user_token_enc": ..., "available_pages": [{"id": ..., "name": ...}, ...], "selected_page_id": ..., "selected_page_name": ...}`.
- Multi-Page users auto-select the first Page; success message includes `"N Pages available"` when N > 1.
- Other platforms (twitter, linkedin, instagram, youtube, tiktok) keep their original `connection_data` shape (no `platform_user_id` / `metadata` set here — those are Phase 101/103/104 concerns).
- `PLATFORM_CONFIGS` `facebook` and `instagram` entries use v23.0 (no `v18.0` substring left in `connector.py`).
- 4 new pytest tests in `tests/unit/social/test_connector_facebook_pages.py` are GREEN.
- `ruff check` and `ty check` clean for `app/social/connector.py`.
- No regression to non-Facebook OAuth flows.
</success_criteria>

<output>
After completion, create `.planning/phases/107-facebook-video-resumable-upload/107-02-page-token-capture-SUMMARY.md` documenting:
- Exact line numbers of `_fetch_facebook_pages` and the rewritten `handle_callback` facebook branch.
- Which v18.0 strings were bumped to v23.0.
- Test count delta.
- Any deviations from this plan, with rationale.
- Confirmation that `grep -nE "v18\.0" app/social/connector.py` returns empty.
- Note that Plan 107-01's `_get_facebook_page_context` reads the row written by this plan; the two plans together close POST-09.
- Follow-up notes: multi-Page selection UI (Phase 108), `disconnect` revoke (Phase 108 HYGIENE-04), Twitter/LinkedIn/etc. `platform_user_id` capture (Phase 101 / 103 / 104).
</output>
