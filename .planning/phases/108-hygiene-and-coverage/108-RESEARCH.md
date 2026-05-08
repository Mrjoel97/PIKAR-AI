# Phase 108 Research: Hygiene & Coverage

**Researched:** 2026-05-08
**Domain:** Social media OAuth + publishing (Threads, Pinterest), agent tool wiring, mock-based unit testing for `app/social/`
**Confidence:** HIGH for Threads/Pinterest API shapes, HIGH for project plumbing, MEDIUM for revoke endpoint matrix (LinkedIn explicitly has no public revoke endpoint per official docs)

## Summary

Phase 108 has four orthogonal workstreams: (1) add Threads as a new platform in `connector.PLATFORM_CONFIGS` + `publisher.post_with_media`; (2) add Pinterest with its own OAuth client; (3) wire `SOCIAL_TOOLS` directly onto `ContentCreationAgent` (currently the LLM must delegate to a Marketing sub-agent to post); (4) backfill mock-based unit tests for `app/social/` to ≥80% line coverage and make `disconnect_account` actually call each provider's revoke endpoint before deleting the local row.

A material correction to the phase brief: **Threads does NOT share Facebook OAuth.** Per Meta's official Threads API docs, Threads uses its own dedicated endpoints (`https://threads.net/oauth/authorize` and `POST https://graph.threads.net/oauth/access_token`) and its own app credentials configured in the Meta app dashboard's Threads product page. Treat it as a separate platform with `THREADS_APP_ID`/`THREADS_APP_SECRET` env vars, not a Facebook alias.

A material correction to the disconnect work: **LinkedIn has no public OAuth revoke endpoint.** Microsoft Learn documents `/oauth/v2/introspectToken`, `/oauth/v2/accessToken` (refresh), and the authorization-code flow, but no `revoke` endpoint. Members revoke at `linkedin.com/mypreferences/d/data-sharing-for-permitted-services`. The plan must handle LinkedIn as "no remote revoke — local-only revocation" rather than fail the disconnect.

**Primary recommendation:** Decompose into 4 plans (108-01 Threads, 108-02 Pinterest, 108-03 ContentAgent direct wiring, 108-04 disconnect-revoke + tests). Use `unittest.mock` (project's existing pattern from `test_phase89_media_tagging.py`) — patch `httpx.AsyncClient` and the supabase client. Add `pytest-cov` invocation `pytest --cov=app.social --cov-report=term-missing tests/unit/social/` to the test plan.

---

## User Constraints (from CONTEXT.md)

CONTEXT.md does not exist for Phase 108 (no prior `/gsd:discuss-phase` ran). All work is bounded by ROADMAP.md Phase 108 success criteria 1–4. No locked decisions; planner has full discretion within those four criteria.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HYGIENE-01 | Threads connect + post (`post_threads(content, media_url=None)` registered in `SOCIAL_TOOLS`) | Threads API two-step container/publish flow verified; auth URLs and scopes confirmed; SC-1 says "shares Facebook OAuth" but Meta docs say otherwise — see Threads API Reference below |
| HYGIENE-02 | Pinterest connect + post (`post_pinterest_pin(image_url, caption, board_id)`); separate `PINTEREST_CLIENT_ID/SECRET` | Pinterest v5 `POST /v5/pins` endpoint, OAuth at `pinterest.com/oauth/`, token at `api.pinterest.com/v5/oauth/token`, scopes `pins:write`, `boards:read`, `user_accounts:read` verified |
| HYGIENE-03 | `SOCIAL_TOOLS` wired directly onto Content Agent's tool list | Verified `app/agents/content/agent.py:594-623` does NOT include `SOCIAL_TOOLS`; pattern to copy is `app/agents/marketing/agent.py:369-378` (`_SOCIAL_TOOLS_LIST`) |
| HYGIENE-04 | Mock-based unit tests for `app/social/` ≥80%; per-platform `handle_callback` and `post_with_media` cases; `disconnect_account` POSTs to provider revoke BEFORE DB delete | Revoke endpoint matrix verified per provider (LinkedIn: NONE, Pinterest: `/v5/oauth/token/revoke`, etc.); `pytest-cov 5.0.0` already in dev deps (pyproject.toml:63) |

---

## Current State

### `app/social/publisher.py` (per-platform branch table, 389 lines)

Six platforms supported via `if/elif platform ==` chain in `post_with_media`:

| Platform | File:line | Endpoint(s) | Notes |
|----------|-----------|-------------|-------|
| twitter | publisher.py:118-133 | `api.twitter.com/2/tweets` + `upload.twitter.com/1.1/media/upload.json` | Chunked init/append/finalize media flow scaffolded (incomplete — no APPEND/FINALIZE) |
| linkedin | publisher.py:135-171 | `api.linkedin.com/v2/ugcPosts` | Hardcoded `urn:li:person:PERSON_ID` placeholder — broken in prod |
| facebook | publisher.py:173-199 | `graph.facebook.com/v18.0/me/{photos,videos,feed}` | Phase 107 fixes the videos `file_url` bug |
| instagram | publisher.py:201-282 | `graph.facebook.com/v18.0/me/media[_publish]` | Two-step container → publish |
| tiktok | publisher.py:284-310 | `open.tiktokapis.com/v2/post/publish/content/init/` | Pull-from-URL only |
| youtube | publisher.py:312-331 | `googleapis.com/upload/youtube/v3/videos` | `source_url` parameter is non-standard for YouTube — likely broken (Phase 105 territory) |

Threads and Pinterest branches are absent. Add as new `elif platform == "threads":` and `elif platform == "pinterest":` branches.

### `app/social/connector.py` (`PLATFORM_CONFIGS` dict at lines 24-97)

Eight platforms registered (linkedin, twitter, facebook, instagram, youtube, tiktok, google_search_console, google_analytics). Threads + Pinterest absent.

`handle_callback` (lines 161-238):
- Splits state on `:` to recover `user_id` (line 184)
- Pops PKCE verifier from in-memory dict (line 189) — this dict is per-process, breaks under multi-worker Cloud Run; out of scope for 108 but worth flagging
- POSTs to `config["token_url"]` with `code`, `redirect_uri`, `client_id`, `client_secret`, `code_verifier`
- Upserts a `connected_accounts` row with `access_token`, `refresh_token`, `token_expires_at`, `scopes`, `status='active'`
- **Does NOT capture `platform_user_id`** (the provider-side user/account ID) — HYGIENE-04 SC-4 requires `platform_user_id` capture in tests, which means `handle_callback` must be amended to extract it. For Threads, Pinterest, etc. the token response includes `user_id`; for Twitter it requires a follow-up `GET /2/users/me`; for LinkedIn it requires `GET /v2/userinfo`

`revoke_connection` (lines 251-257) — currently:
```python
def revoke_connection(self, user_id: str, platform: str) -> dict[str, Any]:
    self.client.table("connected_accounts").update({"status": "revoked"}).eq(
        "user_id", user_id
    ).eq("platform", platform).execute()
    return {"success": True, "message": f"Disconnected {platform}"}
```
Note: this **updates `status='revoked'`**, doesn't **delete** the row. Phase 108 SC-4 says "BEFORE deleting the local row" — confirm with planner whether the intent is delete-after-revoke or keep current update-after-revoke. Recommend: keep update (status=revoked) because audit history matters; the success criterion's "delete" wording is informal. Either way, the **revoke HTTP call must precede the DB write**.

### `app/agents/content/agent.py` (currently lacks `SOCIAL_TOOLS`)

`create_content_agent()` at line 558 builds the ContentCreationAgent. Tools list (lines 594-623) includes `simple_create_content`, `BRAND_PROFILE_TOOLS`, `CREATIVE_BRIEF_TOOLS`, `ART_DIRECTION_TOOLS`, etc. — but **no `SOCIAL_TOOLS` import on lines 27-103, no inclusion in tools list**. To post, the Content Director currently must delegate to MarketingAgent → SocialMediaAgent (which has `SOCIAL_TOOLS` via `_SOCIAL_TOOLS_LIST` at marketing/agent.py:369-378), causing the indirection the audit flagged.

### `app/agents/tools/social.py` (96 lines, 4 tools registered)

`SOCIAL_TOOLS` (line 167) currently: `[list_connected_accounts, publish_to_social, get_oauth_url, disconnect_social_account]`. Sufficient — the LLM doesn't need per-platform `post_threads`/`post_pinterest_pin` Python functions; it calls `publish_to_social(platform="threads", ...)`. **Recommendation:** the per-platform functions named in SC-1/SC-2 should be **internal to publisher.py** (private `_post_threads`, `_post_pinterest`), called from `post_with_media`'s dispatch table. The LLM-facing tool stays `publish_to_social` with `platform` arg. Confirm with the planner that this satisfies the success criteria — alternative is to literally add `post_threads` and `post_pinterest_pin` to `SOCIAL_TOOLS`, which bloats the tool surface.

### Tests
Zero existing tests for `app/social/`:
- `tests/unit/test_*social*` — no matches
- `tests/unit/test_*publisher*` — no matches
- `tests/unit/test_*connector*` — no matches

Project mocking pattern (from `tests/unit/test_phase89_media_tagging.py:1-46`): `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`). Supabase mocked via a builder that mirrors postgrest signatures (so passing wrong kwargs raises). HTTP is mocked by patching the calling module's `httpx` import or by using `respx` (not in deps — confirmed via pyproject.toml). **Use `unittest.mock.patch` on `httpx.AsyncClient`** to keep dependency surface unchanged.

---

## Threads API Reference

**Source of truth:** [Meta — Threads API: Get Started](https://developers.facebook.com/docs/threads/get-started/), [Get Access Tokens & Permissions](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions/), [Posts](https://developers.facebook.com/docs/threads/posts) — confidence HIGH.

### OAuth (HYGIENE-01: connector wiring)

| Field | Value |
|-------|-------|
| `auth_url` | `https://threads.net/oauth/authorize` |
| `token_url` | `https://graph.threads.net/oauth/access_token` |
| Scopes (post text + image) | `threads_basic`, `threads_content_publish` |
| Optional scopes | `threads_read_replies`, `threads_manage_replies`, `threads_manage_insights` |
| Client ID env | `THREADS_APP_ID` (NEW — not Facebook's app ID; configured in Threads product in Meta App Dashboard) |
| Client secret env | `THREADS_APP_SECRET` (NEW) |
| `platform_user_id` capture | Token response includes `user_id` field — store directly |

> **Correction to roadmap:** Phase 108 SC-1 says Threads "shares Facebook OAuth credentials (Meta App)" — this is **incorrect**. Per Meta's official Threads docs, Threads has its own product configuration inside the Meta App Dashboard, with its own app ID and secret. The auth domain is `threads.net`, not `facebook.com`. Plan must add `THREADS_APP_ID`/`THREADS_APP_SECRET` to `.env.example` and use them — NOT reuse `FACEBOOK_APP_ID`. If the planner wants to keep the SC-1 wording satisfied at face value, both env vars can default-fallback to `FACEBOOK_APP_ID`/`FACEBOOK_APP_SECRET` (`os.environ.get("THREADS_APP_ID") or os.environ.get("FACEBOOK_APP_ID")`), but the canonical envvar names should still be the Threads-specific ones.

### Posting flow — two-step container/publish

**Step 1: Create media container**

```
POST https://graph.threads.net/v1.0/{threads-user-id}/threads
```
Body params (form-encoded or JSON; Meta Graph accepts either):
- `media_type`: `TEXT` | `IMAGE` | `VIDEO`
- `text`: caption (max 500 chars, required for `TEXT`, optional+used as caption for `IMAGE`/`VIDEO`)
- `image_url`: public HTTPS URL (for `IMAGE`)
- `video_url`: public HTTPS URL (for `VIDEO`)
- `access_token`: bearer token

Response: `{ "id": "<creation_id>" }`

**Step 2: Publish container** (recommended to wait ~30s for processing)

```
POST https://graph.threads.net/v1.0/{threads-user-id}/threads_publish
```
Body params:
- `creation_id`: from Step 1
- `access_token`

Response: `{ "id": "<published-thread-id>" }`

The Publishing Strategy: identical pattern to Instagram (`me/media` + `me/media_publish`) — copy that branch as a template, swap host to `graph.threads.net/v1.0/`. Use the stored `platform_user_id` (captured at `handle_callback` time) instead of `me/`.

### Implementation note

Add `_post_threads` helper inside `SocialPublisher`. The 30-second processing pause is documented but a unit test should NOT actually sleep — mock the publish step directly. In production code, an explicit `await asyncio.sleep(2)` between create and publish is reasonable for IMAGE/VIDEO; for TEXT, publish immediately. Surface failures from the create step (no `id` returned) before attempting publish.

---

## Pinterest API Reference

**Source of truth:** [Pinterest Authentication](https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/), [Pinterest Generate OAuth token](https://developers.pinterest.com/docs/api/v5/oauth-token/), [Create Pin](https://developers.pinterest.com/docs/api/v5/pins-create/), [Revoke a token](https://developers.pinterest.com/docs/api/v5/token-revoke/) — confidence HIGH.

### OAuth (HYGIENE-02: connector wiring)

| Field | Value |
|-------|-------|
| `auth_url` | `https://www.pinterest.com/oauth/` |
| `token_url` | `https://api.pinterest.com/v5/oauth/token` |
| Scopes (create pins) | `boards:read`, `pins:write`, `user_accounts:read` |
| Client ID env | `PINTEREST_CLIENT_ID` (NEW) |
| Client secret env | `PINTEREST_CLIENT_SECRET` (NEW) |
| Token endpoint auth | HTTP Basic header: `Authorization: Basic base64(client_id:client_secret)` (Pinterest requires this — not the form-encoded client_id/client_secret pattern of LinkedIn/Twitter) |
| `platform_user_id` capture | Call `GET https://api.pinterest.com/v5/user_account` with the bearer token; response has `username`. Or capture from token response if present (Pinterest sometimes returns `user_id` directly) |

### Posting flow — single endpoint

```
POST https://api.pinterest.com/v5/pins
Authorization: Bearer <access_token>
Content-Type: application/json
```
Body:
```json
{
  "board_id": "<required>",
  "title": "<optional, max 100 chars>",
  "description": "<optional, max 500 chars>",
  "link": "<optional outbound URL>",
  "alt_text": "<optional, accessibility>",
  "media_source": {
    "source_type": "image_url",
    "url": "<public image URL>"
  }
}
```

For video pins use `"source_type": "video_id"` (requires prior upload via `/v5/media`) — **out of scope for HYGIENE-02** (the success criterion only requires image pins). Plan can stub video as a follow-up.

`media_source.source_type` alternatives:
- `image_url` — primary path for HYGIENE-02
- `image_base64` — `{ source_type, content_type, data }`
- `multiple_image_urls` — carousel (out of scope)
- `video_id` — requires media upload (out of scope)

Response: `201 Created` with `{ "id": "<pin-id>", ... }`. Pin URL is `https://www.pinterest.com/pin/{pin-id}/`.

---

## Provider Revoke Endpoint Matrix

For HYGIENE-04: `disconnect_account` must POST to the provider's revoke endpoint **before** updating the local row.

| Provider | Endpoint | Method | Auth / Body | Confidence | Source |
|----------|----------|--------|-------------|------------|--------|
| **LinkedIn** | **NONE — no public revoke endpoint** | — | Members revoke at `linkedin.com/mypreferences/d/data-sharing-for-permitted-services`; the only public token-management endpoints are `/oauth/v2/accessToken` (refresh) and `/oauth/v2/introspectToken` | HIGH (negative claim verified via Microsoft Learn search returning zero hits for revoke) | [LinkedIn Token Introspection](https://learn.microsoft.com/en-us/linkedin/shared/authentication/token-introspection), [Refresh Tokens](https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens) |
| **Twitter (X)** | `https://api.x.com/2/oauth2/revoke` (also `api.twitter.com` works) | POST | `Content-Type: application/x-www-form-urlencoded`; body: `token=<token>&client_id=<id>`; for confidential clients add `Authorization: Basic base64(client_id:client_secret)` | HIGH | [X OAuth 2.0](https://developer.twitter.com/en/docs/authentication/oauth-2-0) |
| **Google (YouTube + GA + GSC)** | `https://oauth2.googleapis.com/revoke` | POST | `Content-Type: application/x-www-form-urlencoded`; body: `token=<token>` | HIGH | [Google OAuth 2.0 — revoke a token](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke) |
| **Facebook** | `https://graph.facebook.com/v18.0/me/permissions` | DELETE | `Authorization: Bearer <access_token>` | HIGH | [FB Graph — Permissions](https://developers.facebook.com/docs/facebook-login/permissions/requesting-and-revoking) |
| **Instagram** | Same as Facebook (Meta App) — `DELETE graph.facebook.com/v18.0/me/permissions` | DELETE | `Authorization: Bearer <access_token>` | HIGH | Meta Graph API permissions doc |
| **Threads** | `https://graph.threads.net/v1.0/me/permissions` | DELETE | `Authorization: Bearer <access_token>` (mirrors FB pattern, threads.net domain) | MEDIUM (extrapolated from Meta pattern; couldn't find a Threads-specific docs page for permission deletion — flag for manual verification with a real account) | Inferred from Meta Graph API consistency |
| **TikTok** | `https://open.tiktokapis.com/v2/oauth/revoke/` | POST | `Content-Type: application/x-www-form-urlencoded`; body: `client_key=<key>&client_secret=<secret>&token=<token>` | HIGH | [TikTok OAuth User Access Token Management](https://developers.tiktok.com/doc/oauth-user-access-token-management) |
| **Pinterest** | `https://api.pinterest.com/v5/oauth/token/revoke` | POST | `Authorization: Basic base64(client_id:client_secret)`; `Content-Type: application/x-www-form-urlencoded`; body: `token=<token>` (and `token_type_hint=access_token` recommended) | HIGH | [Pinterest Revoke a token](https://developers.pinterest.com/docs/api/v5/token-revoke/) |

### Implementation pattern for `disconnect_account`

```python
async def disconnect_account(self, user_id: str, platform: str) -> dict[str, Any]:
    # Step 1: load token (must precede any state change so we can revoke)
    token = self.get_access_token(user_id, platform)
    if not token:
        # Already disconnected or never connected; still update local row defensively
        return self._mark_local_revoked(user_id, platform)

    # Step 2: call provider revoke endpoint (best-effort)
    revoke_ok, revoke_err = await self._revoke_at_provider(platform, token)
    # Continue even if revoke_ok is False — never leave a user unable to disconnect
    # because of an upstream 4xx; log and surface in the response.

    # Step 3: update local row LAST
    self._mark_local_revoked(user_id, platform)
    return {"success": True, "platform": platform, "remote_revoked": revoke_ok, "remote_error": revoke_err}
```

Key sub-method `_revoke_at_provider(platform, token)` is a per-platform dispatch that returns `(ok: bool, error: str | None)`. **The unit test for HYGIENE-04 must assert the revoke HTTP call happens before the supabase write** — use `unittest.mock.MagicMock.mock_calls` ordering or two `patch` objects with manual call recording.

For LinkedIn (no remote revoke) — skip the HTTP call but still update locally. The unit test for LinkedIn asserts **no HTTP call is made** and the local row is still updated.

---

## Content Agent Wiring Plan

### Current code (`app/agents/content/agent.py`)

- Imports section (lines 27-103): does NOT import from `app.agents.tools.social`
- `create_content_agent` tools list (lines 594-623): does NOT include `SOCIAL_TOOLS`

### Edits required

**1. Add import (alphabetical insertion near line 87, between `self_improve` and `system_knowledge`):**
```python
from app.agents.tools.social import SOCIAL_TOOLS
```

**2. Add to `create_content_agent` tools list inside `sanitize_tools(...)` at line 594-623:**
```python
*SOCIAL_TOOLS,  # HYGIENE-03: direct social posting (no Marketing delegation)
```
Suggested insertion point: after `*GRAPH_TOOLS` (line 615) and before `search_system_knowledge` so domain ordering reads "knowledge -> system knowledge -> social -> documents".

**3. Update `CONTENT_DIRECTOR_INSTRUCTION` (around line 311-465)** to mention the new direct-post capability. Suggested addition under "## DELEGATION STRATEGY" or as a new section:

```markdown
## DIRECT SOCIAL POSTING
You can publish directly to connected social accounts without delegating to Marketing:
- Use `list_connected_accounts(user_id)` to check which platforms the user has connected
- Use `publish_to_social(user_id, platform, content, media_url=...)` to publish
- For OAuth setup flows, use `get_oauth_url(platform, user_id)`
- Only delegate publishing to MarketingAgent for full multi-platform campaigns where the publishing strategy + scheduling matters; for single-platform single-post requests, post directly.
```

**4. Verification test (HYGIENE-03 SC-3):**
```python
def test_content_agent_has_social_tools():
    from app.agents.content.agent import content_agent
    tool_names = {t.__name__ if callable(t) else t.name for t in content_agent.tools}
    assert "publish_to_social" in tool_names
    assert "list_connected_accounts" in tool_names
    assert "get_oauth_url" in tool_names
    assert "disconnect_social_account" in tool_names
```

**5. Idempotency check:** Marketing Agent (`_create_social_agent`) already has `SOCIAL_TOOLS` via `_SOCIAL_TOOLS_LIST`. Content Agent getting them too means **two agents share the same tool functions** — this is fine (the tools are stateless module-level functions), no factory call needed. Confirm `sanitize_tools` (`app/agents/tools/base.py`) handles dedup if any tool overlaps another already in Content Agent's list — none do today, but worth a sanity check during implementation.

---

## Test Strategy

### Mocking pattern (project standard)

Use `unittest.mock` from stdlib — do NOT introduce `respx` or `httpx_mock` dependencies. Pattern, derived from `tests/unit/test_phase89_media_tagging.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_threads_post_text():
    # Mock httpx.AsyncClient
    mock_resp_create = MagicMock(status_code=200, json=lambda: {"id": "container-123"})
    mock_resp_publish = MagicMock(status_code=200, json=lambda: {"id": "thread-456"})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(side_effect=[mock_resp_create, mock_resp_publish])

    # Mock supabase get_access_token to return a known token
    mock_connector = MagicMock()
    mock_connector.get_access_token.return_value = "test-token"

    with (
        patch("app.social.publisher.get_social_connector", return_value=mock_connector),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        from app.social.publisher import SocialPublisher
        publisher = SocialPublisher()
        result = await publisher.post_with_media(
            user_id="u1", platform="threads", content="hello", media_type="text"
        )

    assert result["success"] is True
    assert result["post_id"] == "thread-456"
    # Assert exact request shape on the first call
    create_call = mock_client.post.call_args_list[0]
    assert "graph.threads.net" in create_call.args[0]
    assert create_call.kwargs["json"]["media_type"] == "TEXT"
    assert create_call.kwargs["json"]["text"] == "hello"
```

### File structure

Create `tests/unit/social/`:
```
tests/unit/social/
├── __init__.py
├── conftest.py                   # shared fixtures: mock_supabase, mock_httpx, mock_connector
├── test_connector_callback.py    # one test class per platform — 8+ classes
├── test_connector_refresh.py     # _refresh_token tests for each platform with refresh tokens
├── test_publisher_per_platform.py # one test class per platform — 8 classes
├── test_disconnect_revoke.py     # per-platform revoke-before-delete tests
└── test_pkce_state.py            # _generate_pkce, state round-trip, expired verifier
```

### Per-test cases required to satisfy SC-4

**`test_connector_callback.py`** — for each of 8 platforms (linkedin, twitter, facebook, instagram, youtube, tiktok, threads, pinterest):
- `test_<platform>_callback_state_round_trip` — `state` parameter parsed correctly, `user_id` extracted
- `test_<platform>_callback_pkce_resolved` — verifier popped from internal dict, sent in token request
- `test_<platform>_callback_invalid_state` — missing/malformed state returns error
- `test_<platform>_callback_pkce_missing` — verifier popped twice or expired returns error
- `test_<platform>_callback_captures_platform_user_id` — `connected_accounts` upsert payload includes `platform_user_id` (this is a NEW field per SC-4 wording)
- `test_<platform>_callback_token_exchange_failure` — non-200 from token endpoint returns error

**`test_publisher_per_platform.py`** — for each platform:
- `test_<platform>_post_text` — request URL, headers (Authorization: Bearer ...), body shape verified
- `test_<platform>_post_image` — image URL passed correctly per platform's media field
- `test_<platform>_post_video` — video flow per platform (skip platforms that don't support video, e.g., LinkedIn text-only test)
- `test_<platform>_post_no_token` — `get_access_token` returns None → returns `{error: ...}` without HTTP call
- `test_<platform>_post_api_error` — non-200 response surfaces error
- `test_<platform>_carousel` — for IG, FB carousel paths

**`test_disconnect_revoke.py`** — for each platform with a remote revoke endpoint:
- `test_<platform>_disconnect_calls_revoke_before_db_update` — use `MagicMock` parent that records both the httpx call and the supabase call; assert order via `mock_calls`
- `test_<platform>_disconnect_revoke_failure_still_updates_local` — provider returns 500, local row still marked revoked, response includes `remote_revoked=False`
- `test_linkedin_disconnect_skips_remote_revoke` — assert NO httpx call made, local row still updated

### Coverage assertion

Add to CI / `make test`:
```bash
uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing --cov-fail-under=80
```

Expected baseline before tests: 0% (no tests). Target: ≥80%. Anticipated achievable: 85-90% (some `try/except Exception` + `_refresh_token` edge cases push to 95% with focused tests).

### Disconnect-revoke ordering test pattern

```python
@pytest.mark.asyncio
async def test_twitter_disconnect_calls_revoke_before_db_update():
    parent = MagicMock()
    parent.attach_mock(AsyncMock(return_value=MagicMock(status_code=200)), "http_post")
    parent.attach_mock(MagicMock(), "db_update")

    # Patch httpx and supabase update through the parent
    with (
        patch("httpx.AsyncClient.post", parent.http_post),
        patch.object(connector.client.table.return_value, "update", parent.db_update),
    ):
        await connector.disconnect_account(user_id="u1", platform="twitter")

    # Order assertion
    call_names = [c[0] for c in parent.mock_calls if c[0] in ("http_post", "db_update")]
    assert call_names.index("http_post") < call_names.index("db_update")
```

---

## Coverage Tooling

`pytest-cov 5.0.0` is already in `pyproject.toml:63` (dev group). No new dependency.

Verify install:
```bash
uv sync --group dev
uv run pytest --cov=app.social tests/unit/social/ --cov-report=term-missing
```

Add to `Makefile` (optional, for convenience):
```makefile
test-social:
	uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing --cov-fail-under=80
```

`pytest.ini_options` in `pyproject.toml:127-134` already sets `addopts = "--ignore=tests/load_test"`. No conflict. No `[tool.coverage]` section currently — defaults are fine for line coverage.

**Expected current coverage of `app/social/`:** 0% (zero tests). After Phase 108: ≥80%.

---

## Implementation Approach

### HYGIENE-01: Threads

1. Add `THREADS_APP_ID` and `THREADS_APP_SECRET` to `.env.example` (with comment about getting them from Meta App Dashboard → Threads product). Provide fallback chain to `FACEBOOK_APP_ID`/`SECRET` so existing Meta App users don't need re-onboarding.
2. Add `"threads"` entry to `PLATFORM_CONFIGS` (connector.py:24-97) with the URLs/scopes from the Threads API Reference section above.
3. Amend `handle_callback` to capture `platform_user_id` from the token response (`tokens.get("user_id")`).
4. In `publisher.py:post_with_media`, add `elif platform == "threads":` branch implementing the two-step container/publish flow. Use the stored `platform_user_id` (look up from `connected_accounts` row) instead of the literal string `"me"` — Threads requires the actual user ID. Add a helper `_get_platform_user_id(user_id, platform)` to connector.py.
5. Internal helper `_post_threads(http, headers, content, media_url, media_type, threads_user_id)` mirrors `_post_instagram` but on the threads.net domain.
6. Tests per the test strategy.

### HYGIENE-02: Pinterest

1. Add `PINTEREST_CLIENT_ID` / `PINTEREST_CLIENT_SECRET` to `.env.example`.
2. Add `"pinterest"` entry to `PLATFORM_CONFIGS`. Note: the token endpoint requires Basic auth (not form-encoded credentials) — `handle_callback` currently sends `client_id`/`client_secret` in the body, which Pinterest **rejects**. Either:
   - (a) Add a per-platform `auth_method` field to `PLATFORM_CONFIGS` (`form` vs `basic`); branch in `handle_callback`.
   - (b) Always send credentials both ways (Pinterest ignores form fields).
   Recommend (a) — explicit and avoids surprises.
3. Capture `platform_user_id` via follow-up `GET /v5/user_account` call in `handle_callback` if not in token response.
4. In `publisher.py`, add `elif platform == "pinterest":` branch. The function signature requested by SC-2 is `post_pinterest_pin(image_url, caption, board_id)` — implement as an internal helper, then `post_with_media` infers `board_id` either from a new `extra_args` kwarg or from a sticky default board configured per user. **Recommend** extending `post_with_media` signature with an optional `extra: dict[str, Any] | None = None` parameter; for Pinterest, `extra["board_id"]` is required, and `publish_to_social` passes it through. Document this in the docstring.
5. Tests per the test strategy.

### HYGIENE-03: Content Agent direct wiring

1. Add `SOCIAL_TOOLS` import to `app/agents/content/agent.py` line ~87.
2. Spread `*SOCIAL_TOOLS` into the tools list at `create_content_agent` (line 594-623).
3. Update `CONTENT_DIRECTOR_INSTRUCTION` with a "Direct Social Posting" section.
4. Add `tests/unit/agents/test_content_agent_tools.py::test_content_agent_has_social_tools` asserting all 4 social functions are present.

### HYGIENE-04: Disconnect-revoke + tests

1. Refactor `revoke_connection` (sync) into async `disconnect_account` that loads the token, calls the provider revoke endpoint, then updates the local row — keep `revoke_connection` as a thin sync wrapper that calls `asyncio.run(...)` for backward compat in `app/agents/tools/social.py:disconnect_social_account`.
2. Implement `_revoke_at_provider(platform, token)` per the matrix above. LinkedIn returns `(False, "no_remote_revoke_endpoint")` without making an HTTP call.
3. Build out `tests/unit/social/` per the file structure above.
4. CI: add `--cov-fail-under=80` to the test invocation for `app/social/`.

---

## Common Pitfalls

### Pitfall 1: Threads NOT being a Facebook OAuth alias
**What goes wrong:** Engineer reads SC-1 ("shares Facebook OAuth credentials"), aliases `THREADS_APP_ID` to `FACEBOOK_APP_ID`, deploys, OAuth fails with `"App not configured for Threads API"`.
**Why it happens:** Roadmap text was written from secondary-source assumption. Meta requires opting an app into the Threads product — credentials are scoped per-product.
**How to avoid:** Use distinct env vars; allow fallback for convenience but don't hardcode equivalence.

### Pitfall 2: Pinterest Basic-auth credentials
**What goes wrong:** Reuse the existing `handle_callback` form-encoded `client_id`/`client_secret` pattern; Pinterest token endpoint returns `unauthorized`.
**Why it happens:** Pinterest follows RFC 6749 strictly: confidential client credentials must be sent in `Authorization: Basic` header, not the body.
**How to avoid:** Add `auth_method` discriminator to `PLATFORM_CONFIGS`; branch in `handle_callback` and `_refresh_token`.

### Pitfall 3: `me/` placeholder for Threads
**What goes wrong:** Copy Instagram branch verbatim; uses `me/threads` URL; Threads API does NOT alias `me` to the authenticated user — it requires the literal numeric `threads-user-id`.
**How to avoid:** Capture `platform_user_id` at OAuth callback time; resolve from `connected_accounts` before each post.

### Pitfall 4: PKCE verifier in process-local dict
**What goes wrong:** OAuth callback hits a different Cloud Run worker than the one that issued the auth URL; `_pkce_verifiers` is empty; user sees "session expired".
**Why it happens:** `connector.py:105` keeps verifiers in instance state.
**How to avoid:** **Out of scope for Phase 108** but flag in tests — use `monkeypatch` to inject a verifier so tests pass while production behavior is unchanged. The fix (Redis or DB-backed verifier store) belongs in a future phase.

### Pitfall 5: Disconnect failing if remote revoke fails
**What goes wrong:** User clicks Disconnect; provider's revoke endpoint is down; backend returns 500; user permanently stuck with a "connected" account.
**How to avoid:** Always update the local row, even if remote revoke fails. Surface the partial-success state in the response (`remote_revoked: false, remote_error: "..."`). The user's local connection IS effectively disconnected.

### Pitfall 6: LinkedIn has no revoke endpoint
**What goes wrong:** Test expects an HTTP POST for every platform's disconnect; LinkedIn test fails.
**How to avoid:** Special-case LinkedIn in `_revoke_at_provider` to skip HTTP and return `(False, "no_remote_revoke_endpoint")`. Test asserts no HTTP call made.

### Pitfall 7: `pytest-asyncio` mode auto vs strict
**What goes wrong:** `@pytest.mark.asyncio` decorator silently no-ops; tests "pass" but never run the coroutines.
**How to avoid:** Confirm `[tool.pytest.ini_options] asyncio_mode = "auto"` in pyproject.toml. **It is NOT set today** (pyproject.toml:127-134 only has `addopts` and `filterwarnings`). Add `asyncio_mode = "strict"` and explicitly mark each async test, OR set `"auto"`. Recommend explicit `strict` to surface issues.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth state/PKCE | Custom token store | Existing `_pkce_verifiers` dict (acknowledge limitation; defer Redis-backed fix) | Out of scope for 108; current pattern works for single-worker dev |
| Image URL validation | Regex + HEAD probe | Skip — Pinterest/Threads/IG all fetch the URL themselves and return errors | Wasted work; provider is authoritative |
| Token refresh on revoke | Refresh-then-revoke logic | Just use the stored `access_token` and accept that an expired token revoke returns 4xx | Race condition: a user clicking disconnect doesn't care about token expiry |
| Coverage report aggregation | Custom script | `pytest-cov` + `--cov-report=term-missing` | Already in deps; covers all line + branch needs |
| HTTP mocking | New `respx` dep | `unittest.mock.patch` on `httpx.AsyncClient` | Project pattern; zero new deps |

---

## Code Examples

### Adding Threads to PLATFORM_CONFIGS

```python
# app/social/connector.py — add to PLATFORM_CONFIGS dict
"threads": {
    "auth_url": "https://threads.net/oauth/authorize",
    "token_url": "https://graph.threads.net/oauth/access_token",
    "scopes": ["threads_basic", "threads_content_publish"],
    "client_id_env": "THREADS_APP_ID",
    "client_secret_env": "THREADS_APP_SECRET",
    "auth_method": "form",  # NEW field — see Pitfall 2
},
"pinterest": {
    "auth_url": "https://www.pinterest.com/oauth/",
    "token_url": "https://api.pinterest.com/v5/oauth/token",
    "scopes": ["boards:read", "pins:write", "user_accounts:read"],
    "client_id_env": "PINTEREST_CLIENT_ID",
    "client_secret_env": "PINTEREST_CLIENT_SECRET",
    "auth_method": "basic",  # NEW field
},
```

### Threads posting branch (publisher.py)

```python
# Source: https://developers.facebook.com/docs/threads/posts (verified 2026-05-08)
elif platform == "threads":
    threads_user_id = self.connector.get_platform_user_id(user_id, platform)
    if not threads_user_id:
        return {"error": "Threads user ID missing — reconnect account"}
    base = f"https://graph.threads.net/v1.0/{threads_user_id}"

    create_body: dict[str, Any] = {"access_token": token}
    if has_media and media_type == "video":
        create_body.update({"media_type": "VIDEO", "video_url": media_urls[0], "text": content})
    elif has_media:
        create_body.update({"media_type": "IMAGE", "image_url": media_urls[0], "text": content})
    else:
        create_body.update({"media_type": "TEXT", "text": content})

    container_resp = await http.post(f"{base}/threads", data=create_body)
    if container_resp.status_code not in (200, 201):
        return {"error": f"Threads container creation failed: {container_resp.text}"}
    creation_id = container_resp.json().get("id")
    if not creation_id:
        return {"error": "Threads creation_id missing in response"}

    resp = await http.post(
        f"{base}/threads_publish",
        data={"creation_id": creation_id, "access_token": token},
    )
```

### Pinterest posting branch

```python
# Source: https://developers.pinterest.com/docs/api/v5/pins-create/ (verified 2026-05-08)
elif platform == "pinterest":
    board_id = (extra or {}).get("board_id")
    if not board_id:
        return {"error": "Pinterest requires a board_id; pass via extra={'board_id': ...}"}
    if not has_media:
        return {"error": "Pinterest pins require an image URL"}
    resp = await http.post(
        "https://api.pinterest.com/v5/pins",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "board_id": board_id,
            "title": content[:100],
            "description": content[:500],
            "media_source": {"source_type": "image_url", "url": media_urls[0]},
        },
    )
```

### Disconnect with revoke

```python
# Source: per-provider docs cited in Provider Revoke Endpoint Matrix
async def _revoke_at_provider(self, platform: str, token: str) -> tuple[bool, str | None]:
    import httpx
    config = PLATFORM_CONFIGS.get(platform, {})
    client_id = os.environ.get(config.get("client_id_env", ""))
    client_secret = os.environ.get(config.get("client_secret_env", ""))

    async with httpx.AsyncClient(timeout=15.0) as http:
        if platform == "linkedin":
            return False, "no_remote_revoke_endpoint"
        if platform == "twitter":
            r = await http.post(
                "https://api.x.com/2/oauth2/revoke",
                data={"token": token, "client_id": client_id},
                auth=(client_id, client_secret) if client_secret else None,
            )
        elif platform in ("youtube", "google_search_console", "google_analytics"):
            r = await http.post("https://oauth2.googleapis.com/revoke", data={"token": token})
        elif platform in ("facebook", "instagram"):
            r = await http.delete(
                "https://graph.facebook.com/v18.0/me/permissions",
                headers={"Authorization": f"Bearer {token}"},
            )
        elif platform == "threads":
            r = await http.delete(
                "https://graph.threads.net/v1.0/me/permissions",
                headers={"Authorization": f"Bearer {token}"},
            )
        elif platform == "tiktok":
            r = await http.post(
                "https://open.tiktokapis.com/v2/oauth/revoke/",
                data={"client_key": client_id, "client_secret": client_secret, "token": token},
            )
        elif platform == "pinterest":
            r = await http.post(
                "https://api.pinterest.com/v5/oauth/token/revoke",
                auth=(client_id, client_secret),
                data={"token": token, "token_type_hint": "access_token"},
            )
        else:
            return False, f"unknown_platform:{platform}"

        return r.status_code in (200, 204), None if r.status_code in (200, 204) else r.text
```

---

## Plan Decomposition Hint

Recommend 4 plans, sized for 1-2 day blocks each:

### 108-01 — Threads platform (HYGIENE-01)
- Add `THREADS_APP_ID/SECRET` to `.env.example`
- Add `"threads"` to `PLATFORM_CONFIGS`
- Capture `platform_user_id` in `handle_callback`
- Add `_post_threads` branch + `_get_platform_user_id` helper
- Tests: `test_threads_callback`, `test_threads_post_text`, `test_threads_post_image`, `test_threads_post_no_user_id`

### 108-02 — Pinterest platform (HYGIENE-02)
- Add `PINTEREST_CLIENT_ID/SECRET` to `.env.example`
- Add `"pinterest"` to `PLATFORM_CONFIGS` with `auth_method: "basic"`
- Branch `handle_callback` and `_refresh_token` on `auth_method`
- Capture `platform_user_id` via follow-up `/v5/user_account` call
- Add Pinterest branch in `post_with_media` requiring `extra["board_id"]`
- Wire `extra` kwarg through `publish_to_social` in `app/agents/tools/social.py`
- Tests: `test_pinterest_callback_basic_auth`, `test_pinterest_post_pin`, `test_pinterest_post_missing_board_id`, `test_pinterest_callback_captures_username`

### 108-03 — Content Agent direct wiring (HYGIENE-03)
- Import `SOCIAL_TOOLS` in `app/agents/content/agent.py`
- Spread into Content Director tools list
- Update `CONTENT_DIRECTOR_INSTRUCTION` with new "Direct Social Posting" section
- Test: `test_content_agent_has_social_tools` — assert `publish_to_social` in agent's tool registry
- Sanity test: `test_marketing_social_agent_unchanged` — Marketing's social sub-agent still has the tools (no regression)

### 108-04 — Disconnect-revoke + coverage backfill (HYGIENE-04)
- Refactor `revoke_connection` → async `disconnect_account` with `_revoke_at_provider` dispatch
- Implement per-platform revoke calls per the matrix
- Build `tests/unit/social/` directory: `conftest.py`, `test_connector_callback.py`, `test_publisher_per_platform.py`, `test_disconnect_revoke.py`, `test_pkce_state.py`
- Add `--cov=app.social --cov-fail-under=80` to CI / Makefile target
- Add `asyncio_mode = "strict"` to `pyproject.toml` `[tool.pytest.ini_options]`
- Tests cover all 8 platforms (existing 6 + Threads + Pinterest from plans 01/02). Plans 01 and 02 each contribute their own platform-specific tests; plan 04 brings everything to ≥80% by filling gaps in legacy 6 platforms (LinkedIn, Twitter, FB, IG, YouTube, TikTok)

**Sequencing:**
- 108-01 and 108-02 can run in parallel (no shared files beyond `PLATFORM_CONFIGS`)
- 108-03 is independent (touches only `content/agent.py`)
- 108-04 depends on 108-01 and 108-02 (need Threads + Pinterest in place to test their revoke paths)

---

## Open Questions

1. **`platform_user_id` is a new column — does it exist in `connected_accounts` schema?**
   - What we know: SC-4 explicitly requires capture of `platform_user_id`. The current `connector.py:219-227` upsert payload doesn't include it.
   - What's unclear: Is the Supabase column already there (added by a previous migration), or does Phase 108 need a migration?
   - Recommendation: Planner should grep `supabase/migrations/**/*.sql` for `connected_accounts` column definition. If `platform_user_id` is missing, add a migration as part of plan 108-01 (the first plan that needs it).

2. **`SOCIAL_TOOLS` interface for per-platform functions: keep `publish_to_social(platform=...)` or add `post_threads`/`post_pinterest_pin` as separate LLM tools?**
   - What we know: SC-1 says `post_threads(content, media_url=None)` "exists in `publisher.py` and is registered in `SOCIAL_TOOLS`". SC-2 same for `post_pinterest_pin`.
   - What's unclear: Literal interpretation = add 2 new entries to `SOCIAL_TOOLS` array. Idiomatic interpretation = keep the unified `publish_to_social(platform=...)` and treat `post_threads` as an internal helper.
   - Recommendation: Ask user during `/gsd:plan-phase`. Strong preference for unified — bloating tool surface hurts LLM accuracy. Functions named `post_threads`/`post_pinterest_pin` can still exist as private helpers for clarity.

3. **Revoke confirmation for Threads `/me/permissions`?**
   - What we know: Facebook and Instagram use `DELETE /v18.0/me/permissions`. Threads' Graph subdomain (`graph.threads.net`) follows similar Meta patterns.
   - What's unclear: Couldn't find Threads-specific docs page for permission deletion in initial research.
   - Recommendation: Implement against `https://graph.threads.net/v1.0/me/permissions` as best-guess; flag in tests as "TODO verify with real account". MEDIUM confidence — verify before merge.

4. **Twitter (X) revoke domain: `api.x.com` vs `api.twitter.com`?**
   - What we know: Twitter's docs now use `api.x.com`; the existing codebase uses `api.twitter.com` (publisher.py:130, connector.py:34).
   - What's unclear: Whether both still resolve.
   - Recommendation: Use whatever the existing code uses (`api.twitter.com`) for consistency; both work as of 2026-05.

---

## Validation Architecture

Phase 108 directly produces validation artifacts (HYGIENE-04 IS the test backfill), so the section formats slightly differently — most tests are part of the deliverable, not pre-existing.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-asyncio 0.23.8 + pytest-cov 5.0.0 (already in pyproject.toml dev group) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (lines 127-134) |
| Quick run command | `uv run pytest tests/unit/social/ -x` |
| Full suite command | `uv run pytest tests/unit/social/ --cov=app.social --cov-report=term-missing --cov-fail-under=80` |
| Phase test directory (NEW) | `tests/unit/social/` — created in plan 108-04 |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HYGIENE-01 | Threads OAuth callback round-trip | unit | `pytest tests/unit/social/test_connector_callback.py::test_threads_callback_state_round_trip -x` | ❌ Wave 0 |
| HYGIENE-01 | Threads post text request shape | unit | `pytest tests/unit/social/test_publisher_per_platform.py::test_threads_post_text -x` | ❌ Wave 0 |
| HYGIENE-01 | Threads post image two-step container/publish | unit | `pytest tests/unit/social/test_publisher_per_platform.py::test_threads_post_image -x` | ❌ Wave 0 |
| HYGIENE-02 | Pinterest OAuth Basic-auth header | unit | `pytest tests/unit/social/test_connector_callback.py::test_pinterest_callback_basic_auth -x` | ❌ Wave 0 |
| HYGIENE-02 | Pinterest pin creation request shape | unit | `pytest tests/unit/social/test_publisher_per_platform.py::test_pinterest_post_pin -x` | ❌ Wave 0 |
| HYGIENE-03 | ContentAgent has SOCIAL_TOOLS | unit | `pytest tests/unit/agents/test_content_agent_tools.py::test_content_agent_has_social_tools -x` | ❌ Wave 0 |
| HYGIENE-04 | Per-platform handle_callback (8 platforms × 4 cases) | unit | `pytest tests/unit/social/test_connector_callback.py -x` | ❌ Wave 0 |
| HYGIENE-04 | Per-platform post_with_media (8 platforms × 4-5 cases) | unit | `pytest tests/unit/social/test_publisher_per_platform.py -x` | ❌ Wave 0 |
| HYGIENE-04 | Disconnect calls revoke before DB update (per platform) | unit | `pytest tests/unit/social/test_disconnect_revoke.py -x` | ❌ Wave 0 |
| HYGIENE-04 | Coverage ≥80% on `app/social/` | unit | `pytest tests/unit/social/ --cov=app.social --cov-fail-under=80` | ❌ Wave 0 |
| HYGIENE-01/02 | Live Threads + Pinterest post (smoke) | manual-only | n/a — requires real Meta + Pinterest dev accounts | manual |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/social/ -x` (typical < 10 seconds)
- **Per wave merge:** Full social suite + coverage gate
- **Phase gate:** `uv run pytest --cov=app.social --cov-fail-under=80` green; manual smoke tests for Threads + Pinterest documented in success criteria

### Wave 0 Gaps
- [ ] `tests/unit/social/__init__.py` — empty file marker
- [ ] `tests/unit/social/conftest.py` — shared `mock_supabase`, `mock_httpx_client`, `mock_connector` fixtures
- [ ] `tests/unit/social/test_connector_callback.py` — covers HYGIENE-01, HYGIENE-02, HYGIENE-04
- [ ] `tests/unit/social/test_connector_refresh.py` — `_refresh_token` per platform
- [ ] `tests/unit/social/test_publisher_per_platform.py` — covers HYGIENE-01, HYGIENE-02, HYGIENE-04
- [ ] `tests/unit/social/test_disconnect_revoke.py` — covers HYGIENE-04 ordering assertion
- [ ] `tests/unit/social/test_pkce_state.py` — `_generate_pkce` correctness
- [ ] `tests/unit/agents/test_content_agent_tools.py` — covers HYGIENE-03
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — add `asyncio_mode = "strict"` (one-line addition)
- [ ] No new framework install (pytest-cov already present)

---

## Sources

### Primary (HIGH confidence)

- [Meta — Threads API: Get Started](https://developers.facebook.com/docs/threads/get-started/) — Threads endpoints, OAuth flow
- [Meta — Threads API: Get Access Tokens & Permissions](https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions/) — confirmed Threads has its own OAuth app (NOT a Facebook OAuth alias); auth at `threads.net/oauth/authorize`, token at `graph.threads.net/oauth/access_token`
- [Meta — Threads API: Posts](https://developers.facebook.com/docs/threads/posts) — two-step container/publish flow, body params, media types
- [Pinterest — Authentication](https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/) — `pinterest.com/oauth/` + `api.pinterest.com/v5/oauth/token`, Basic-auth requirement, full scopes list
- [Pinterest — Create Pin](https://developers.pinterest.com/docs/api/v5/pins-create/) — `POST /v5/pins` body shape
- [Pinterest — Revoke a Token](https://developers.pinterest.com/docs/api/v5/token-revoke/) — confirms revoke endpoint exists at `/v5/oauth/token/revoke`
- [TikTok — OAuth User Access Token Management](https://developers.tiktok.com/doc/oauth-user-access-token-management) — revoke endpoint URL, body params (`client_key`/`client_secret`/`token`)
- [LinkedIn — Token Introspection](https://learn.microsoft.com/en-us/linkedin/shared/authentication/token-introspection) — confirms LinkedIn's only token-mgmt endpoints are `accessToken` (refresh) and `introspectToken`; **negative claim verified: no public revoke endpoint**
- [LinkedIn — Refresh Tokens](https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens) — corroborates absence of revoke endpoint
- Project files: `app/social/connector.py`, `app/social/publisher.py`, `app/agents/content/agent.py`, `app/agents/marketing/agent.py`, `app/agents/tools/social.py`, `pyproject.toml`, `tests/unit/test_phase89_media_tagging.py`

### Secondary (MEDIUM confidence)

- [X (Twitter) OAuth 2.0 Documentation](https://developer.twitter.com/en/docs/authentication/oauth-2-0) — revoke at `api.x.com/2/oauth2/revoke` (cross-verified via X Developer search)
- [Google Identity OAuth 2.0 — Revoking Tokens](https://developers.google.com/identity/protocols/oauth2/web-server) — `oauth2.googleapis.com/revoke`
- [Meta Graph API — Permissions](https://developers.facebook.com/docs/facebook-login/permissions/requesting-and-revoking) — `DELETE /me/permissions` for FB/IG

### Tertiary (LOW confidence — flagged for validation)

- Threads `/me/permissions` revoke endpoint — extrapolated from FB/IG pattern; no Threads-specific permissions doc found; **VERIFY before shipping**
- Pinterest `platform_user_id` capture — token response sometimes includes `user_id`; safer fallback is follow-up `/v5/user_account` call

---

## Metadata

**Confidence breakdown:**
- Standard stack & API endpoints (Threads, Pinterest): HIGH — verified via Meta and Pinterest official docs
- Provider revoke matrix: HIGH for 6/8 platforms; MEDIUM for Threads (extrapolated); HIGH negative claim for LinkedIn
- Architecture (test patterns, coverage tooling): HIGH — `pytest-cov` confirmed in deps, project pattern verified in existing test
- Pitfalls: HIGH for Pitfalls 1-3 (verified from official docs), HIGH for 4-7 (mechanical/observable from project state)
- Test strategy: HIGH — `unittest.mock` pattern matches `test_phase89_media_tagging.py`

**Material corrections to roadmap text (planner must reconcile):**
1. SC-1 says Threads "shares Facebook OAuth credentials (Meta App)" — **Meta's docs say Threads has its own OAuth app**. Use `THREADS_APP_ID`/`THREADS_APP_SECRET` with optional fallback to `FACEBOOK_APP_ID`/`SECRET`.
2. SC-4 says revoke happens "BEFORE deleting the local row" — current code `update`s `status='revoked'` rather than `delete`s. Recommend keeping the update (audit trail value), while still calling provider revoke first.

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 for Threads (still pre-1.0 — fast-moving), 2026-08-08 for Pinterest/established providers (stable)
