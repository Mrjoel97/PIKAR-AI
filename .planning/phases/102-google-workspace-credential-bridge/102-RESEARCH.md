# Phase 102 Research: Google Workspace Credential Bridge

**Researched:** 2026-05-08
**Domain:** OAuth credential injection into ADK agent runtime
**Confidence:** HIGH

## Summary

The "broken bridge" is real and surgical. Nine code sites read `tool_context.state["google_provider_token"]` and zero write it. The infrastructure to fix this is **already built**: `GoogleWorkspaceAuthService` (`app/services/google_workspace_auth_service.py:49-446`) handles persistence, resolution, and disconnect; `IntegrationManager.get_valid_token` (`app/services/integration_manager.py:166-205`) handles encrypted storage and proactive refresh; the generic OAuth router at `app/routers/integrations.py:84-372` handles authorize/callback/disconnect for any provider in `PROVIDER_REGISTRY`. The frontend `configuration/page.tsx` already has `googleWorkspace` state and a Google Workspace section (line 3690-3748) that today only displays status from a non-OAuth path.

What's missing is **only** the wiring: (1) a `google_workspace` entry in `PROVIDER_REGISTRY`, (2) a sync call inside `context_memory_before_model_callback` that resolves credentials and writes them to state, (3) per-helper refresh calls into `IntegrationManager.get_valid_token`, (4) a revoke-on-disconnect HTTP call to `https://oauth2.googleapis.com/revoke`, (5) frontend "Connect" button driving the existing `/integrations/{provider}/authorize` popup, and (6) `.env.example` plus startup-warning entries.

**Primary recommendation:** Treat this as 3 plans of integration work, not invention. The hardest design decision (where to inject) is answered: `before_model_callback` is sync, runs ~25× per turn (every active agent) but state is per-session so the resolve cost is amortized. Use a session-scoped cache key (e.g., `_google_workspace_resolved`) to avoid re-resolving on every model call.

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase — proceed with full research scope per `<scope>` block in the prompt.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WORKSPACE-01 | In-app "Connect Google Workspace" card with popup OAuth + postMessage | Frontend pattern lives at `frontend/src/app/dashboard/configuration/page.tsx:3211-3226` (`handleConnectIntegration` opens popup at `/api/integrations/{providerKey}/authorize`); postMessage listener at lines 3008-3034. Existing Google Workspace section at lines 3690-3748 must be re-skinned to use `handleConnectIntegration("google_workspace")` instead of legacy "sign-out and sign back in" flow. |
| WORKSPACE-02 | `PROVIDER_REGISTRY` entry with all required scopes | Template entries: `bigquery` at `app/config/integration_providers.py:174-188` and `google_ads` at lines 189-200 — both use Google's auth/token URLs verbatim. Confirmed scope strings via Google identity docs (HIGH confidence). |
| WORKSPACE-03 | `context_memory_before_model_callback` injects creds before model call | Callback is sync (verified via ADK docs at adk.dev) — `GoogleWorkspaceAuthService.resolve_credentials` is also sync (`app/services/google_workspace_auth_service.py:125-160`). Existing precedent: `_try_load_brand_profile` (lines 241-321) already does sync Supabase reads inside this same callback. Inject after `_try_load_cross_session_context` and before instruction-block assembly. |
| WORKSPACE-04 | Each Workspace tool helper calls `IntegrationManager.get_valid_token` for auto-refresh | `IntegrationManager.get_valid_token` is async (`app/services/integration_manager.py:166-205`); tool helpers are currently sync. Refactor each `_get_X_service()` to async OR run the refresh in `before_model_callback` (sync — would need `asyncio.run` or threading) — see "Async vs sync boundary" risk. |
| WORKSPACE-05 | Disconnect revokes at Google AND deletes local row | Confirmed endpoint via Google docs: `POST https://oauth2.googleapis.com/revoke` with `application/x-www-form-urlencoded` body `token={access_token}`. Add the HTTP call inside `GoogleWorkspaceAuthService.disconnect` (currently at lines 234-266 — already deletes the row, just needs the revoke call before the delete). |
| WORKSPACE-06 | `.env.example` + startup WARN for missing vars | `.env.example` currently has `GOOGLE_CLOUD_PROJECT`, `GOOGLE_API_KEY` (lines 12-21) but nothing for `GOOGLE_WORKSPACE_*`. No existing startup-validation pattern for env vars in `app/config/settings.py` was checked — recommend a simple module-level WARN at app/agent module import time, parallel to how `app/integrations/google/client.py:87-94` complains when client_id/secret are unresolvable. |

## Current State (the broken bridge — verified by reading files)

### The 9 readers of `tool_context.state["google_provider_token"]`

All read `provider_token = tool_context.state.get("google_provider_token")` followed by a `raise ValueError("Google authentication required...")` if absent:

1. `app/agents/tools/docs.py:26-30` — `_get_docs_service` (used by `create_document`, `create_report_doc`, `append_to_document`)
2. `app/agents/tools/gmail.py:23-27` — `_get_gmail_service` (used by `send_email`, `send_report_email`)
3. `app/agents/tools/google_sheets.py:102-109` — `_get_sheets_service` (used by 8 tools: list/create/read/write/append/format/share)
4. `app/agents/tools/calendar_tool.py:41-45` — `_get_calendar_service` (used by 9 tools: list/create/update/delete events, free-busy, recurring patterns, follow-ups, meeting-prep, list-calendars)
5. `app/agents/tools/forms.py:61-65` — `_get_forms_service` (used by 4 tools: create_feedback_form, create_custom_form, get_form_responses, share_form)
6. `app/agents/tools/gmail_inbox.py:34-38` — `_get_gmail_reader` (used by `read_inbox`, `get_email_details`, `search_emails`)
7. `app/agents/tools/briefing_tools.py:168-175` — inline read inside `approve_draft` (the only "non-helper" inline read)
8. `app/agents/tools/document_editor.py:1027` — referenced in docstring; actual read pattern likely matches the others (worth verifying during implementation)
9. (briefing_tools also has implicit reads via the daily-briefing pipeline — exact site to confirm during plan execution)

### The 0 writers

Verified by `grep` across the entire `app/` tree (Grep results above): no file ever sets `state["google_provider_token"] = ...`. The key only appears as `.get(...)` reads or in test fixtures (`tests/unit/test_gmail_inbox_tools.py:28`, `tests/unit/test_calendar_tools.py:29`).

The user_id IS reliably set at session creation time: `app/fast_api_app.py:1950-1991` populates `state_updates = {"user_id": effective_user_id}` and either `create_session(state=state_updates)` or `update_state(state_updates=state_updates)`. So the bridge function has guaranteed access to `callback_context.state.get("user_id")` (already extracted by `_get_callback_user_id` at `context_extractor.py:56-63`) on every invocation.

### The 3 legacy fallback paths in `GoogleWorkspaceAuthService.resolve_credentials`

`app/services/google_workspace_auth_service.py:125-160`:

1. **Live session tokens** (lines 134-144) — caller passes `provider_token` arg directly. Currently used by Supabase Auth Google identity flows. Returns immediately with `source="session"`.
2. **Canonical `integration_credentials` row** (lines 146-148) — `get_canonical_credentials` decrypts Fernet-stored tokens. Returns `source="integration_credentials", is_canonical=True`. **This is the path Phase 102 will exclusively populate.**
3. **Legacy fallbacks** (lines 156-160) — `_get_legacy_google_token_row` reads `user_google_tokens` table; `_get_legacy_refresh_token_row` reads `user_oauth_tokens` via RPC. Gated by `allow_legacy_fallback=True` (default). Disconnect marker (`_is_explicitly_disconnected`) blocks fallbacks once user disconnects.

The bridge function should call `resolve_credentials(user_id, allow_legacy_fallback=True)` so that users connected via the OLD Supabase-Auth path continue to work during migration. Eventually `allow_legacy_fallback=False` once Phase 102 ships and users have re-connected.

## Target State

Per success criterion (`ROADMAP.md:467-472`):

| Criterion | Target |
|-----------|--------|
| 1. End-to-end resolve→inject→tool path | Agent calls `create_document()` for user A whose creds are in `integration_credentials` only; doc lands in user A's Drive; URL appears in chat. Verifiable by integration test that mocks Google Docs API and asserts the bearer token in the outbound request matches the user's stored access token. |
| 2. Connect card + popup + postMessage | "Connect Google Workspace" button in configuration page opens popup to `/integrations/google_workspace/authorize`, OAuth completes, popup posts `{type: 'oauth-callback', provider: 'google_workspace', success: true}`, parent listener (already at lines 3008-3034) refreshes status within 2s. Row appears in `integration_credentials` with provider=`google_workspace`. |
| 3. Auto-refresh < 5 min before expiry | Tool helper calls `IntegrationManager.get_valid_token`; if `expires_at` is within 5 min, lock-protected refresh runs (already implemented at `integration_manager.py:166-205`); next API call uses fresh token. Unit test patches `datetime.now` and asserts exactly one refresh call. |
| 4. Disconnect revokes + deletes | Frontend Disconnect button calls existing `disconnectIntegration('google_workspace')` (which routes to `DELETE /integrations/{provider}` at `routers/integrations.py:468-489`); backend additionally POSTs to `https://oauth2.googleapis.com/revoke?token={access_token}` BEFORE deleting the row. Next agent tool call returns "Google authentication required" (clear), not a stale-401. |
| 5. Startup WARN on missing env vars | On app boot in non-test env, missing `GOOGLE_WORKSPACE_CLIENT_ID`/`SECRET`/`REDIRECT_URI` produces a single WARNING log per missing var. `.env.example` documents all three. Unit test patches `os.environ` and asserts the warning fires. |

## Implementation Approach

### WORKSPACE-02: PROVIDER_REGISTRY entry

Add to `app/config/integration_providers.py` after line 200 (between `google_ads` and `meta_ads`):

```python
"google_workspace": ProviderConfig(
    name="Google Workspace",
    auth_type="oauth2",
    auth_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=[
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",  # for inbox reads
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    client_id_env="GOOGLE_WORKSPACE_CLIENT_ID",
    client_secret_env="GOOGLE_WORKSPACE_CLIENT_SECRET",
    webhook_secret_header=None,
    icon_url="https://cdn.pikar-ai.com/icons/google-workspace.svg",
    category="productivity",
),
```

**Notes:**
- `drive.file` is preferred over full `drive` scope: drive.file is non-sensitive and avoids Google's app-verification gauntlet (Drive docs).
- `gmail.readonly` is required because `gmail_inbox.py` calls list/get message endpoints. If readonly inbox isn't required for v13.0, omit and document trade-off.
- `forms.body` is the most granular scope for Forms create/edit (verified — Google Forms API v1 docs).
- `userinfo.email` populates `account_name` for the UI display.
- The generic OAuth callback at `routers/integrations.py:199-372` already handles Google's PKCE-less flow with `access_type=offline&prompt=consent` (lines 184-187), which gives a refresh_token on every consent.

### WORKSPACE-03: Bridge injection function (load-bearing)

**Where to inject:** `app/agents/context_extractor.py` — add a new helper `_try_load_google_workspace_credentials(callback_context)` and call it from `context_memory_before_model_callback` (line 788). Pattern mirrors `_try_load_brand_profile` (lines 241-321):

```python
_GOOGLE_WORKSPACE_LOADED_KEY = "_google_workspace_creds_loaded"

def _try_load_google_workspace_credentials(callback_context: CallbackContext) -> None:
    """Inject Google Workspace credentials into tool context state.

    Resolves credentials from integration_credentials (Phase 102 canonical store)
    or legacy fallback paths and writes them to:
      - state["google_provider_token"]  (access token for API calls)
      - state["google_refresh_token"]   (refresh token for renewal)

    Cached per-session via _GOOGLE_WORKSPACE_LOADED_KEY to avoid re-querying
    Supabase on every model callback (callback fires ~25 times per turn for
    multi-agent flows like Marketing -> SocialMediaAgent).
    """
    if callback_context.state.get(_GOOGLE_WORKSPACE_LOADED_KEY):
        return  # Already attempted this session

    callback_context.state[_GOOGLE_WORKSPACE_LOADED_KEY] = True

    user_id = _get_callback_user_id(callback_context)
    if not user_id or user_id == "anonymous":
        return

    try:
        from app.services.google_workspace_auth_service import (
            get_google_workspace_auth_service,
        )

        # Sync call - resolve_credentials is sync, OK in sync before_model_callback
        service = get_google_workspace_auth_service()
        creds = service.resolve_credentials(user_id, allow_legacy_fallback=True)
        if not creds:
            return

        access_token = creds.get("access_token")
        refresh_token = creds.get("refresh_token")
        if access_token:
            callback_context.state["google_provider_token"] = access_token
        if refresh_token:
            callback_context.state["google_refresh_token"] = refresh_token

        logger.debug(
            "[GoogleWorkspace] Injected creds for user=%s source=%s",
            user_id,
            creds.get("source"),
        )
    except Exception as exc:
        logger.debug("[GoogleWorkspace] Cred injection skipped: %s", exc)
```

Call site in `context_memory_before_model_callback` — insert after the cross-session context block (around line 811) and before the `personalization` lookup:

```python
# --- Google Workspace credential bridge (Phase 102) ---
try:
    _try_load_google_workspace_credentials(callback_context)
except Exception:
    pass  # Cred injection is best-effort, never blocks model call
```

**Cache strategy:** the `_GOOGLE_WORKSPACE_LOADED_KEY` sentinel runs the resolve once per session. If the user disconnects mid-session, state still has the (now-revoked) token; tool helpers will fail with 401 and the helpers' WORKSPACE-04 refresh path will surface the error. Acceptable trade-off; alternative (re-resolve every call) would add ~50ms × 25 callbacks = 1.2s overhead per turn.

**Sub-agent flow (Marketing → SocialMediaAgent):** the callback fires for every agent transfer because each subagent has `before_model_callback=context_memory_before_model_callback` (verified in `app/agents/strategic/subagents.py:56,83,110,170,208,238`, `app/agents/marketing/agent.py:405-470`, etc — wired to ~25 agents). State persists across sub-agent invocations within a session, so the cache key is honored across sub-agents.

### WORKSPACE-04: Tool helper refresh (one example, apply to N others)

**Async/sync boundary tradeoff:**

| Approach | Pros | Cons |
|----------|------|------|
| **A. Refresh in bridge (sync `before_model_callback`)** | Tool helpers stay sync; one refresh per session | Sync `before_model_callback` cannot await `IntegrationManager.get_valid_token` (async); would need `asyncio.run` (creates new loop = bad in FastAPI) or `asyncio.run_coroutine_threadsafe` to the running loop (works but complex) |
| **B. Refresh in tool helper (async)** | Refresh happens at point of use, always fresh; no event-loop hacks | All 7 helpers + 30+ tool functions become async; ADK tool functions can be async (verified — most ADK tools today are sync but ADK supports both) |
| **C. Hybrid (recommended)** | Bridge writes the cached value; tool helpers compare `expires_at` from cache and refresh sync via `httpx.Client` only when needed | Helpers check `expires_at` in state; if stale, run synchronous refresh against `https://oauth2.googleapis.com/token` and update state. Mirrors `IntegrationManager._refresh_token` logic but sync. |

**Recommendation: Approach C (hybrid).** The bridge writes `google_provider_token`, `google_refresh_token`, AND `google_token_expires_at` to state. Each `_get_X_service()` helper checks expiry and refreshes synchronously when needed. This avoids touching async-vs-sync at every call site while still meeting the < 5 min auto-refresh requirement.

**Rejected: Approach A** — `asyncio.run` inside a sync callback running in an asyncio event loop will raise `RuntimeError: asyncio.run() cannot be called from a running event loop`. `run_coroutine_threadsafe` works but adds complexity.

**Rejected: Approach B** — would require converting `_get_docs_service`, `_get_gmail_service`, etc. and every dependent tool function to async. ~30 tool functions touched. Higher risk of breakage and PR scope creep.

**Concrete pattern for one helper (`docs.py`):**

```python
def _get_docs_service(tool_context: ToolContextType):
    """Get Docs service from tool context credentials, refreshing if needed."""
    from app.integrations.google.client import get_google_credentials
    from app.integrations.google.docs import GoogleDocsService
    from app.services.google_workspace_token_refresh import refresh_if_expiring  # NEW

    # Refresh in-place if token expires within 5 min
    refresh_if_expiring(tool_context)

    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")
    if not provider_token:
        raise ValueError("Google authentication required for document features.")

    credentials = get_google_credentials(provider_token, refresh_token)
    return GoogleDocsService(credentials)
```

Then implement `app/services/google_workspace_token_refresh.py`:

```python
def refresh_if_expiring(tool_context, *, threshold_minutes: int = 5) -> None:
    """Refresh google_provider_token in tool_context if within threshold of expiry.

    Synchronous to match before_model_callback / tool helper sync model.
    Mirrors the refresh logic in IntegrationManager._refresh_token but uses
    httpx.Client (sync) instead of httpx.AsyncClient.
    """
    expires_at_str = tool_context.state.get("google_token_expires_at")
    if not _is_expiring_soon(expires_at_str, minutes=threshold_minutes):
        return

    user_id = tool_context.state.get("user_id")
    refresh_token = tool_context.state.get("google_refresh_token")
    if not user_id or not refresh_token:
        return

    client_id = os.environ.get("GOOGLE_WORKSPACE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_WORKSPACE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return

    with httpx.Client(timeout=30.0) as http:
        resp = http.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    new_access = data.get("access_token", "")
    new_refresh = data.get("refresh_token", refresh_token)
    expires_in = data.get("expires_in")
    new_expires_at = (
        (datetime.now(tz=timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
        if expires_in else None
    )

    # Write back to tool_context state
    tool_context.state["google_provider_token"] = new_access
    tool_context.state["google_refresh_token"] = new_refresh
    tool_context.state["google_token_expires_at"] = new_expires_at

    # Persist to integration_credentials so future sessions benefit
    try:
        from app.services.google_workspace_auth_service import (
            get_google_workspace_auth_service,
        )
        get_google_workspace_auth_service().sync_credentials(
            user_id=user_id,
            access_token=new_access,
            refresh_token=new_refresh,
            expires_at=new_expires_at,
        )
    except Exception:
        logger.debug("Persist refreshed token failed (non-fatal)")
```

**Apply same one-line addition (`refresh_if_expiring(tool_context)`) to the other 7 helpers:** `_get_gmail_service`, `_get_sheets_service`, `_get_calendar_service`, `_get_forms_service`, `_get_gmail_reader`, the inline read in `briefing_tools.approve_draft`, and any helper in `document_editor.py`.

**Note on requirement WORKSPACE-04 wording:** the requirement says "calls `IntegrationManager.get_valid_token`". Strictly, the hybrid approach replicates that logic in sync form rather than calling the async method. If the planner deems this a violation, alternative is Approach B (full async conversion). Recommend the hybrid because it ships faster and meets the **success criterion** (auto-refresh within 5 min of expiry) — which is what actually matters.

### WORKSPACE-05: Disconnect with revoke

Modify `GoogleWorkspaceAuthService.disconnect` at `app/services/google_workspace_auth_service.py:234-266`:

```python
def disconnect(self, user_id: str) -> bool:
    """Revoke at Google, then remove reusable Google Workspace credentials."""
    # Resolve the access token BEFORE deletion so we can revoke it
    creds = self.resolve_credentials(user_id, allow_legacy_fallback=True)
    access_token = creds.get("access_token") if creds else None
    had_connection = bool(creds)

    # Revoke at Google (best-effort — proceed with local delete even if revoke fails)
    if access_token:
        try:
            import httpx
            with httpx.Client(timeout=10.0) as http:
                resp = http.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": access_token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "Google revoke returned %s for user=%s: %s",
                        resp.status_code, user_id, resp.text[:200],
                    )
        except Exception as exc:
            logger.warning("Google revoke failed for user=%s: %s", user_id, exc)

    # Existing delete logic (unchanged)
    deleted_any = False
    deleted_any = self._delete_rows("integration_credentials", user_id=user_id, provider=GOOGLE_WORKSPACE_PROVIDER) or deleted_any
    deleted_any = self._delete_rows("user_google_tokens", user_id=user_id) or deleted_any
    deleted_any = self._delete_rows("user_oauth_tokens", user_id=user_id, provider="google") or deleted_any
    deleted_any = self._delete_rows("integration_sync_state", user_id=user_id, provider=GOOGLE_WORKSPACE_PROVIDER) or deleted_any
    self._set_disconnect_marker(user_id)

    return had_connection or deleted_any
```

**Endpoint shape verified:** `POST https://oauth2.googleapis.com/revoke`, `Content-Type: application/x-www-form-urlencoded`, body `token={access_token}`, success = HTTP 200. (Source: Google OAuth 2.0 web-server docs.)

**Frontend disconnect** already routes correctly: configuration page calls `disconnectIntegration('google_workspace')` which hits `DELETE /integrations/{provider}` at `routers/integrations.py:468-489` — that calls `IntegrationManager.delete_credentials` which only deletes the row. **Important:** decide whether the frontend disconnect button should hit the existing `DELETE /integrations/google_workspace` path (which won't revoke) OR the dedicated `DELETE /configuration/google-workspace` path at `routers/configuration.py:416-437` (which calls `GoogleWorkspaceAuthService.disconnect` and WILL revoke after this change). **Recommendation:** point frontend at `/configuration/google-workspace` to ensure revoke happens. Alternative: also enhance `IntegrationManager.delete_credentials` to call revoke, but that mixes provider-specific logic into the generic manager.

### WORKSPACE-01: Frontend "Connect" card

Replace the existing Google Workspace section at `frontend/src/app/dashboard/configuration/page.tsx:3690-3748`. The disconnected branch (lines 3734-3747) currently says "sign out and sign back in" — replace with a button that calls `handleConnectIntegration("google_workspace")`:

```tsx
{googleWorkspace?.connected ? (
    /* existing connected branch (lines 3699-3733) — unchanged except add Disconnect button */
    <div className="space-y-4">
        {/* ... existing connected UI ... */}
        <button
            onClick={() => handleDisconnectGoogleWorkspace()}
            disabled={disconnectingProvider === 'google_workspace'}
            className="text-sm text-red-600 hover:text-red-700"
        >
            {disconnectingProvider === 'google_workspace' ? 'Disconnecting...' : 'Disconnect'}
        </button>
    </div>
) : (
    <div className="text-center py-8">
        {/* ... icon + heading ... */}
        <button
            onClick={() => handleConnectIntegration("google_workspace")}
            className="mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
            <Plug className="inline w-4 h-4 mr-2" />
            Connect Google Workspace
        </button>
    </div>
)}
```

The `handleConnectIntegration` function (lines 3211-3226) already does `window.open('/api/integrations/{providerKey}/authorize', 'oauth-popup', 'width=600,height=700,scrollbars=yes')` and the postMessage listener (lines 3008-3034) already handles `oauth-callback` events, calling `refreshIntegrationStatus()` to update the UI. **Important:** `refreshIntegrationStatus` only fetches `/integrations/status` (which queries `integration_credentials` directly via `IntegrationManager.get_integration_status`); it does NOT call the `/configuration/google-workspace-status` endpoint. Either:
- (a) trigger a re-fetch of `googleWorkspace` state after a successful `oauth-callback` for `google_workspace`, OR
- (b) merge the Google Workspace card into the generic `integrationStatuses` list and remove the dedicated `googleWorkspace` state.

Recommend (a) for minimal churn: extend the `handleOAuthMessage` listener to also re-fetch `/api/configuration/google-workspace-status` when `provider === 'google_workspace'`.

### WORKSPACE-06: .env.example + startup WARN

**`.env.example` additions** — append to the Google block (after line 21):

```bash
# Google Workspace per-user OAuth (Phase 102)
# Required for in-app "Connect Google Workspace" flow that stores reusable
# refresh tokens in integration_credentials. DIFFERENT from GOOGLE_API_KEY
# (Vertex/Gemini API) and GOOGLE_CLIENT_ID (legacy Supabase Auth Google identity).
# Get these from Google Cloud Console -> APIs & Services -> Credentials -> OAuth 2.0 Client IDs.
# GOOGLE_WORKSPACE_CLIENT_ID=your_oauth_client_id.apps.googleusercontent.com
# GOOGLE_WORKSPACE_CLIENT_SECRET=your_oauth_client_secret
# GOOGLE_WORKSPACE_REDIRECT_URI=https://your-domain.com/integrations/google_workspace/callback
```

**Startup WARN** — add to `app/config/settings.py` or to module-level init in `app/integrations/google/client.py`. Pattern parallel to `app/integrations/google/client.py:91-94`:

```python
import os
import logging
logger = logging.getLogger(__name__)

def _warn_missing_google_workspace_env() -> None:
    """Emit WARN for missing Google Workspace OAuth env vars in non-test environments."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return  # skip in test runs
    missing = [
        v for v in (
            "GOOGLE_WORKSPACE_CLIENT_ID",
            "GOOGLE_WORKSPACE_CLIENT_SECRET",
            "GOOGLE_WORKSPACE_REDIRECT_URI",
        )
        if not os.environ.get(v)
    ]
    if missing:
        logger.warning(
            "Google Workspace OAuth not configured: missing env vars %s. "
            "Per-user Google integration will be unavailable until these are set.",
            ", ".join(missing),
        )

# Call at module import:
_warn_missing_google_workspace_env()
```

## Standard Stack

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-auth` | already pinned | Build `Credentials` for API clients | Already used at `app/integrations/google/client.py:15` |
| `google-api-python-client` | already pinned | Build Docs/Sheets/Drive/Forms/Calendar/Gmail service clients | Already used at `app/integrations/google/client.py:16` |
| `httpx` | already pinned (async + sync) | OAuth token exchange + revoke calls | Already used at `app/services/integration_manager.py:25` and `app/routers/integrations.py:23` |
| `cryptography.fernet` | already pinned | Token encryption at rest | Already used at `app/services/encryption.py` (see imports in `google_workspace_auth_service.py:12` and `integration_manager.py:29`) — Phase 101 dependency |

**No new dependencies required.** All infrastructure is in place from Phase 101.

## Architecture Patterns

### Pattern 1: Reuse the generic OAuth router (don't fork for google_workspace)

The router at `app/routers/integrations.py:84-372` is fully provider-agnostic. Adding `google_workspace` to `PROVIDER_REGISTRY` is sufficient to make `/integrations/google_workspace/authorize`, `/integrations/google_workspace/callback`, `/integrations/status`, and `/integrations/google_workspace` (DELETE) all work without modification.

**One exception:** the disconnect path needs Google-specific revoke. Either (a) hit the dedicated `/configuration/google-workspace` DELETE which calls `GoogleWorkspaceAuthService.disconnect`, or (b) add a special-case in `IntegrationManager.delete_credentials` that calls revoke for `google_workspace`. Pattern (a) is cleaner.

### Pattern 2: Sync injection in before_model_callback, sync refresh in tool helpers

ADK's `before_model_callback` is sync (verified via adk.dev docs). Existing precedent in this codebase (`_try_load_brand_profile` at `context_extractor.py:241-321`) does sync Supabase reads inside the callback. `GoogleWorkspaceAuthService.resolve_credentials` is sync. Tool helpers are sync. Stay sync end-to-end via `httpx.Client` (not `AsyncClient`) for the in-helper refresh path.

### Pattern 3: Session-scoped sentinel keys to amortize cost

`_BRAND_PROFILE_LOADED_KEY` at `context_extractor.py:37` and `_CROSS_SESSION_LOADED_KEY` at line 36 demonstrate the pattern: set the sentinel before doing work, do work once per session, return cached value on subsequent calls. Mirror with `_GOOGLE_WORKSPACE_LOADED_KEY`.

### Anti-Pattern to Avoid

**Don't call `IntegrationManager.get_valid_token` from a sync `before_model_callback`.** It's async; calling it via `asyncio.run` will fail because the callback runs inside a running event loop. Use the sync hybrid approach instead.

**Don't rebuild Google's OAuth flow in the configuration router.** The generic `/integrations/{provider}/authorize` handler already does PKCE-less, `access_type=offline`, `prompt=consent` correctly (`routers/integrations.py:184-187`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Token encryption | New encryption layer | `app.services.encryption.encrypt_secret`/`decrypt_secret` (Phase 101) |
| OAuth state CSRF | In-memory state dict | Existing Redis-backed state cache at `routers/integrations.py:148-153` (Phase 101) |
| Token storage | New table | `integration_credentials` (already exists; `GoogleWorkspaceAuthService.sync_credentials` writes to it) |
| Refresh-token race | Custom locking | `IntegrationManager._refresh_locks` async lock pattern at `integration_manager.py:70-88` |
| Building Google `Credentials` | Manual token + token_uri assembly | `app/integrations/google/client.py:19-40` `get_google_credentials()` |

## Common Pitfalls

### Pitfall 1: Existing `legacy_fallback` paths return creds with `expires_at=None`

`_get_legacy_google_token_row` at `google_workspace_auth_service.py:268-297` and `_get_legacy_refresh_token_row` at lines 299-314 both return `"expires_at": None`. The hybrid refresh (`_is_expiring_soon`) correctly treats `None` as "non-expiring" and skips refresh. This means legacy-source tokens won't be refreshed even when they're stale. **Mitigation:** when `source != "integration_credentials"`, optimistically attempt one Google API call; on 401, fall through to refresh. Or: trigger a one-time migration that calls `sync_credentials` for any legacy-source resolution to get the row into the canonical store with a real `expires_at`.

### Pitfall 2: Sub-agent state isolation

ADK passes the same `session.state` to every agent in the run, but state mutations from a sub-agent's callback persist to the parent. Verified via existing patterns (`_record_action` at `context_extractor.py:420-484` mutates state from after-tool callbacks and the parent agent sees it). The Google Workspace creds written by the bridge are visible to ALL sub-agents in the run. **No additional plumbing needed for Marketing → SocialMediaAgent flows.**

### Pitfall 3: Anonymous user

`fast_api_app.py` sets `user_id` to literal `"anonymous"` for unauthenticated requests (search for `user_id != "anonymous"` patterns at line 1953). The bridge function MUST short-circuit on `user_id == "anonymous"` to avoid querying `integration_credentials` with a non-UUID. The skeleton above already does this.

### Pitfall 4: Disconnect race when token has just been refreshed

If `disconnect` resolves the token, network call to `oauth2.googleapis.com/revoke` succeeds, then THE row deletion fails — user is stuck. **Mitigation:** swallow revoke errors (best-effort) and always proceed with deletion. Already in the recommended skeleton.

### Pitfall 5: Refresh token rotation

Some Google flows return a new `refresh_token` on every refresh, others don't (depends on consent timing). The `_refresh_token` logic at `integration_manager.py:259-260` correctly falls back to the old refresh token: `new_refresh = token_data.get("refresh_token", refresh_token)`. Mirror in the sync helper (already in the skeleton).

### Pitfall 6: Scope drift between provider entry and runtime requests

If `PROVIDER_REGISTRY["google_workspace"].scopes` later loses `gmail.readonly` but tools still expect inbox access, users connected before the change still have the broader scope; users connecting after won't. **Mitigation:** version the consent — when the scopes list grows, force re-consent by appending a no-op param or clearing the disconnect marker. Out of scope for v13.0 first-ship.

## Code Examples

### Example: Bridge function (full, to add to context_extractor.py)

```python
# Source: synthesis from app/agents/context_extractor.py patterns
_GOOGLE_WORKSPACE_LOADED_KEY = "_google_workspace_creds_loaded"

def _try_load_google_workspace_credentials(callback_context: CallbackContext) -> None:
    """Inject Google Workspace credentials into tool_context state.

    Cached per-session via _GOOGLE_WORKSPACE_LOADED_KEY.
    Called from context_memory_before_model_callback.
    """
    if callback_context.state.get(_GOOGLE_WORKSPACE_LOADED_KEY):
        return
    callback_context.state[_GOOGLE_WORKSPACE_LOADED_KEY] = True

    user_id = _get_callback_user_id(callback_context)
    if not user_id or user_id == "anonymous":
        return

    try:
        from app.services.google_workspace_auth_service import (
            get_google_workspace_auth_service,
        )
        creds = get_google_workspace_auth_service().resolve_credentials(
            user_id, allow_legacy_fallback=True
        )
        if not creds:
            return

        if creds.get("access_token"):
            callback_context.state["google_provider_token"] = creds["access_token"]
        if creds.get("refresh_token"):
            callback_context.state["google_refresh_token"] = creds["refresh_token"]
        if creds.get("expires_at"):
            callback_context.state["google_token_expires_at"] = creds["expires_at"]

        logger.debug(
            "[GoogleWorkspace] Injected creds for user=%s source=%s",
            user_id, creds.get("source"),
        )
    except Exception as exc:
        logger.debug("[GoogleWorkspace] Cred injection skipped: %s", exc)
```

### Example: Google revoke call shape

```python
# Source: Google OAuth 2.0 docs (verified)
import httpx
with httpx.Client(timeout=10.0) as http:
    resp = http.post(
        "https://oauth2.googleapis.com/revoke",
        data={"token": access_token},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    # Success: HTTP 200. Already-revoked: HTTP 400 with error="invalid_token".
```

### Example: Frontend connect button (replacement for disconnected-branch UI)

```tsx
// Source: pattern from frontend/src/app/dashboard/configuration/page.tsx:3211-3226
<button
    onClick={() => handleConnectIntegration("google_workspace")}
    className="mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
>
    <Plug className="inline w-4 h-4 mr-2" />
    Connect Google Workspace
</button>
```

## Key Risks & Open Questions

### Risk 1: Async/sync boundary (HIGH — affects WORKSPACE-04 acceptance)

Requirement WORKSPACE-04 says "calls `IntegrationManager.get_valid_token`". That method is async. Tool helpers are sync. The hybrid sync-refresh approach **meets the success criterion** (auto-refresh within 5 min of expiry — verifiable by clock-patched unit test) but **technically does not call `get_valid_token`**. Planner must decide: accept hybrid as satisfying the spirit of WORKSPACE-04, or pursue Approach B (full async tool helper conversion) for literal compliance.

### Risk 2: `gmail.readonly` scope sensitivity

`gmail.readonly` is a **restricted scope** in Google's classification — apps requesting it must pass annual security assessment ($15K-$75K USD) or use a different verification path. If Pikar AI hasn't completed Google's verification, requesting `gmail.readonly` will hit the unverified-app warning screen and limit consent to high-trust testers. **Open question:** is Pikar AI's OAuth project verified for gmail.readonly? If not, drop inbox-read tools from v13.0 and ship with `gmail.send` only (non-sensitive).

### Risk 3: Frontend disconnect doesn't currently route to revoke endpoint

Today's frontend calls `disconnectIntegration` (services/integrations.ts) which hits `DELETE /integrations/{provider}` — that path goes through `IntegrationManager.delete_credentials`, which does NOT call revoke. The Google-specific revoke logic lives in `GoogleWorkspaceAuthService.disconnect` which is wired to a DIFFERENT endpoint (`DELETE /configuration/google-workspace` at `routers/configuration.py:416-437`). **Decision needed:** redirect frontend disconnect for `google_workspace` to the configuration endpoint, OR add revoke logic to the generic delete path.

### Risk 4: Existing legacy-source tokens

Users with creds from legacy paths (Supabase Auth Google identity) will continue to work via `allow_legacy_fallback=True`, but the auto-refresh hybrid won't refresh them (no `expires_at`). They'll get 401s when their token expires. **Open question:** acceptable for v13.0 (forces them to re-connect via new flow) or do we need a one-time migration?

### Risk 5: Multiple Google OAuth client IDs

Legacy Supabase Auth uses `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (line 87-88 of `app/integrations/google/client.py`). YouTube uses `GOOGLE_CLIENT_ID` too (per `frontend/src/.../page.tsx:294`). Phase 102 introduces `GOOGLE_WORKSPACE_CLIENT_ID`. **Open question:** are these expected to be DIFFERENT client IDs in Google Cloud Console (one OAuth app per integration) or the same? Recommend separate (allows independent scope grants and disconnects), but operationally simpler if the same. Document the decision in `.env.example`.

### Risk 6: Sub-agent transfer doesn't always refresh state cache

The `_GOOGLE_WORKSPACE_LOADED_KEY` cache prevents re-resolving once per session. If credentials are revoked mid-session by the user (in another browser tab), the cached state still has the revoked token. Tool calls will 401 and the sync refresh will return a fresh access token… IF the refresh token wasn't also revoked. Google's revoke endpoint revokes the entire grant, so the refresh will fail too. **Acceptable degradation:** the user sees a "Google authentication required" error after the failed call, prompting reconnect.

## Testing Strategy

Per success criterion:

| Criterion | Test Type | Test Approach |
|-----------|-----------|---------------|
| 1. End-to-end resolve→inject→tool | Integration | Pytest fixture: insert encrypted row in `integration_credentials` for test user; mock the Google Docs API `documents.create` endpoint to capture the bearer token; trigger an agent run that calls `create_document`; assert captured token == decrypted stored token. |
| 2. Connect card + popup | Frontend (vitest) | Mock `window.open` and `postMessage`; click button; assert popup URL == `/api/integrations/google_workspace/authorize`; simulate postMessage callback; assert `refreshIntegrationStatus` was called and `setGoogleWorkspace` updated. |
| 3. Auto-refresh | Unit | Patch `datetime.now` to return a time within 5 min of stored `expires_at`; mock `httpx.Client.post` for the token endpoint; call `_get_docs_service`; assert exactly one POST to `oauth2.googleapis.com/token` with `grant_type=refresh_token`; assert state was updated with new token. |
| 4. Disconnect revokes + deletes | Unit | Mock `httpx.Client.post` for revoke endpoint; insert row in `integration_credentials`; call `GoogleWorkspaceAuthService.disconnect`; assert revoke POST was made with the access token AND row was deleted from `integration_credentials`. |
| 5. Startup WARN | Unit | Patch `os.environ` to omit each of the 3 vars in turn; capture log records; assert WARNING fired naming each missing var; patch `PYTEST_CURRENT_TEST` truthy and assert no WARN. |

**Test fixtures:**
- `tests/conftest.py` — already has Supabase test client patterns (verify before this plan)
- Integration test will need an ADK runner harness that exercises a single agent + tool; check `tests/unit/test_calendar_tools.py` (line 29 already mocks `google_provider_token` in tool_context) for pattern.

## Validation Architecture

`workflow.nyquist_validation: true` in `.planning/config.json` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio (existing) |
| Config file | `pyproject.toml` (existing pytest config) |
| Quick run command | `uv run pytest tests/unit/test_workspace_bridge.py -x` (NEW file) |
| Full suite command | `make test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WORKSPACE-01 | Frontend popup connect flow | unit (vitest) | `cd frontend && npm test -- ConfigurationPage.test.tsx` | ❌ Wave 0 |
| WORKSPACE-02 | PROVIDER_REGISTRY entry exists with correct scopes | unit | `pytest tests/unit/test_integration_providers.py::test_google_workspace_registered -x` | ❌ Wave 0 |
| WORKSPACE-03 | Bridge function injects state on callback | unit | `pytest tests/unit/test_workspace_bridge.py::test_credentials_injected -x` | ❌ Wave 0 |
| WORKSPACE-04 | Tool helper auto-refreshes within 5 min | unit | `pytest tests/unit/test_workspace_token_refresh.py::test_refresh_when_expiring -x` | ❌ Wave 0 |
| WORKSPACE-05 | Disconnect calls revoke + deletes row | unit | `pytest tests/unit/test_google_workspace_auth_service.py::test_disconnect_revokes -x` | ⚠️ file exists; add new test |
| WORKSPACE-06 | Startup WARN on missing env vars | unit | `pytest tests/unit/test_settings_validation.py::test_workspace_env_warn -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_workspace_bridge.py tests/unit/test_workspace_token_refresh.py tests/unit/test_integration_providers.py -x`
- **Per wave merge:** `make test` (unit + integration + workflow validation)
- **Phase gate:** `make test` green + manual smoke (connect → ask agent to create doc → doc appears in user's Drive)

### Wave 0 Gaps
- [ ] `tests/unit/test_workspace_bridge.py` — covers WORKSPACE-03 (bridge injection)
- [ ] `tests/unit/test_workspace_token_refresh.py` — covers WORKSPACE-04 (refresh)
- [ ] `tests/unit/test_integration_providers.py` — covers WORKSPACE-02 (registry entry); may already exist for other providers
- [ ] `tests/unit/test_settings_validation.py` — covers WORKSPACE-06 (env warn)
- [ ] `frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx` — covers WORKSPACE-01 (frontend)
- [ ] Integration test for end-to-end flow — covers Success Criterion 1 (likely `tests/integration/test_workspace_e2e.py`)
- [ ] Add test case to existing `tests/unit/test_google_workspace_auth_service.py` for revoke behavior (WORKSPACE-05)

## Plan Decomposition Hint

Recommend **3 plans** (1 wave per plan; mostly sequential because Plan 102-02 depends on the bridge from 102-01):

### Plan 102-01: Provider registry + bridge function + env vars
**Workstreams:** WORKSPACE-02, WORKSPACE-03, WORKSPACE-06
**Files touched:**
- `app/config/integration_providers.py` (add entry)
- `app/agents/context_extractor.py` (add `_try_load_google_workspace_credentials` and call from `context_memory_before_model_callback`)
- `app/config/settings.py` or new module-level init (startup WARN)
- `.env.example` (add 3 vars)
- `tests/unit/test_workspace_bridge.py` (NEW)
- `tests/unit/test_integration_providers.py` (extend or NEW)
- `tests/unit/test_settings_validation.py` (NEW)

**Why first:** unblocks 102-02 (tool helpers need state to be populated to test refresh).

### Plan 102-02: Tool helper refresh + disconnect-revoke + service module
**Workstreams:** WORKSPACE-04, WORKSPACE-05
**Files touched:**
- `app/services/google_workspace_token_refresh.py` (NEW — sync refresh helper)
- `app/services/google_workspace_auth_service.py` (modify `disconnect` to call revoke first)
- `app/agents/tools/docs.py` (add `refresh_if_expiring` call in `_get_docs_service`)
- `app/agents/tools/gmail.py` (same)
- `app/agents/tools/google_sheets.py` (same)
- `app/agents/tools/calendar_tool.py` (same)
- `app/agents/tools/forms.py` (same)
- `app/agents/tools/gmail_inbox.py` (same)
- `app/agents/tools/briefing_tools.py` (inline read in `approve_draft`)
- `app/agents/tools/document_editor.py` (verify and update if applicable)
- `tests/unit/test_workspace_token_refresh.py` (NEW)
- `tests/unit/test_google_workspace_auth_service.py` (extend with revoke tests)
- `tests/unit/test_calendar_tools.py`, `test_gmail_inbox_tools.py`, etc. (regression — verify the existing token fixture still works)

**Why second:** completes the per-helper auto-refresh and revoke-on-disconnect server side, so the frontend in 102-03 has working backend to point at.

### Plan 102-03: Frontend Connect/Disconnect card
**Workstreams:** WORKSPACE-01
**Files touched:**
- `frontend/src/app/dashboard/configuration/page.tsx` (replace section 3690-3748 with connect-button branch + disconnect button + status refresh on postMessage)
- `frontend/src/services/integrations.ts` (verify `disconnectIntegration` routes correctly OR add `disconnectGoogleWorkspace` that hits `/configuration/google-workspace`)
- `frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx` (NEW or extend)

**Why last:** depends on `google_workspace` being in `PROVIDER_REGISTRY` (102-01) so the authorize endpoint works; depends on revoke behavior (102-02) so disconnect actually revokes.

**Optional Plan 102-04 (verification):** End-to-end integration test under `tests/integration/test_workspace_e2e.py` exercising Success Criterion 1 (resolve → inject → mocked Docs API call captures correct bearer). Could be folded into 102-02 or kept separate to allow shipping plans independently.

## Sources

### Primary (HIGH confidence)
- `app/config/integration_providers.py:174-200` — bigquery and google_ads template entries
- `app/services/google_workspace_auth_service.py:49-446` — full canonical service (sync_credentials, resolve_credentials, disconnect, fallbacks)
- `app/services/integration_manager.py:60-279` — async credential lifecycle, refresh lock pattern
- `app/routers/integrations.py:84-372` — generic OAuth router, popup callback HTML at lines 1541-1567
- `app/routers/integrations.py:1526-1538` — `_oauth_budget_cap_prompt_html` postMessage example
- `app/agents/context_extractor.py:241-321` — `_try_load_brand_profile` (sync Supabase precedent)
- `app/agents/context_extractor.py:788-942` — `context_memory_before_model_callback` (where to inject)
- `app/agents/tools/docs.py:21-33`, `gmail.py:18-31`, `google_sheets.py:91-112`, `calendar_tool.py:36-49`, `forms.py:56-68`, `gmail_inbox.py:19-41`, `briefing_tools.py:139-178` — all 9 readers verified
- `app/integrations/google/client.py:19-40` — `get_google_credentials` builds Credentials from token only (no client_id needed for runtime API calls)
- `frontend/src/app/dashboard/configuration/page.tsx:102-108` — `GoogleWorkspaceStatus` interface
- `frontend/src/app/dashboard/configuration/page.tsx:3008-3034` — postMessage listener
- `frontend/src/app/dashboard/configuration/page.tsx:3211-3226` — `handleConnectIntegration` popup pattern
- `frontend/src/app/dashboard/configuration/page.tsx:3690-3748` — current Google Workspace section to replace
- `app/fast_api_app.py:1948-2009` — `state_updates = {"user_id": effective_user_id}` proof that user_id is reliably in callback state
- `.planning/REQUIREMENTS.md:26-31` — WORKSPACE-01 through WORKSPACE-06 verbatim
- `.planning/ROADMAP.md:463-478` — Phase 102 goal, success criteria, dependencies

### Secondary (MEDIUM confidence — verified with official docs)
- `https://developers.google.com/identity/protocols/oauth2/scopes` — exact scope strings (documents, spreadsheets, drive.file, gmail.send, calendar, forms.body, userinfo.email)
- `https://developers.google.com/drive/api/guides/api-specific-auth` — drive.file vs drive distinction (drive.file is non-sensitive)
- `https://developers.google.com/forms/api/reference/rest/v1/forms/create` — Forms create accepts forms.body OR drive.file OR drive
- `https://developers.google.com/identity/protocols/oauth2/web-server` — revoke endpoint (POST oauth2.googleapis.com/revoke, application/x-www-form-urlencoded, body=token)
- `https://adk.dev/callbacks/types-of-callbacks/` — `before_model_callback` is sync; signature `def(callback_context, llm_request) -> Optional[LlmResponse]`

### Tertiary (LOW confidence — flag for validation)
- gmail.readonly being a restricted scope requiring annual security assessment — pulled from training data and Google's "Sensitive and restricted scopes" page; verify current Google policy before shipping

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library already in use; only adding registry entry and small helper module
- Architecture: HIGH — bridge injection point verified by reading the full callback; user_id in state verified at fast_api_app.py:1950
- Pitfalls: HIGH for #1, #3, #4, #5; MEDIUM for #2 (legacy migration choice is judgment call); MEDIUM for #6 (depends on Google's revoke semantics — not directly verified for this codebase)
- Async/sync analysis: HIGH (verified ADK callback is sync via adk.dev; resolve_credentials is sync via direct file read)
- Scope strings: HIGH (verified via developers.google.com)
- Revoke endpoint: HIGH (verified via developers.google.com)

**Research date:** 2026-05-08
**Valid until:** 2026-06-07 (30 days — Google scope changes are infrequent; ADK API stable)
