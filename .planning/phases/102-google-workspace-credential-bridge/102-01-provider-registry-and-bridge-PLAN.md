---
phase: 102-google-workspace-credential-bridge
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/config/integration_providers.py
  - app/agents/context_extractor.py
  - app/integrations/google/client.py
  - .env.example
  - tests/unit/test_integration_providers.py
  - tests/unit/test_workspace_bridge.py
  - tests/unit/test_settings_validation.py
autonomous: true
requirements: [WORKSPACE-02, WORKSPACE-03, WORKSPACE-06]

must_haves:
  truths:
    - "PROVIDER_REGISTRY['google_workspace'] resolves with the 8 required scopes and uses GOOGLE_WORKSPACE_CLIENT_ID / GOOGLE_WORKSPACE_CLIENT_SECRET env var names"
    - "When a session has user_id != 'anonymous' and an integration_credentials row exists for that user with provider='google_workspace', context_memory_before_model_callback writes state['google_provider_token'], state['google_refresh_token'], and state['google_token_expires_at'] BEFORE any tool call"
    - "The bridge function is idempotent within a session: calling context_memory_before_model_callback N times resolves credentials at most ONCE (sentinel _GOOGLE_WORKSPACE_LOADED_KEY honored)"
    - "Bridge function never raises into the model-callback caller — any unexpected exception from resolve_credentials is swallowed with a debug log"
    - "On app boot in non-test environments, missing GOOGLE_WORKSPACE_CLIENT_ID, _SECRET, or _REDIRECT_URI emits exactly one WARNING log per missing var"
    - "PYTEST_CURRENT_TEST being truthy suppresses the startup WARN (no log noise during pytest)"
  artifacts:
    - path: "app/config/integration_providers.py"
      provides: "google_workspace ProviderConfig entry inside PROVIDER_REGISTRY with all 8 scopes"
      contains: "google_workspace"
    - path: "app/agents/context_extractor.py"
      provides: "_try_load_google_workspace_credentials helper + invocation inside context_memory_before_model_callback + _GOOGLE_WORKSPACE_LOADED_KEY sentinel constant"
      contains: "_try_load_google_workspace_credentials"
    - path: "app/integrations/google/client.py"
      provides: "_warn_missing_google_workspace_env() function called at module import time"
      contains: "_warn_missing_google_workspace_env"
    - path: ".env.example"
      provides: "Documented GOOGLE_WORKSPACE_CLIENT_ID, GOOGLE_WORKSPACE_CLIENT_SECRET, GOOGLE_WORKSPACE_REDIRECT_URI entries"
      contains: "GOOGLE_WORKSPACE_CLIENT_ID"
    - path: "tests/unit/test_integration_providers.py"
      provides: "Pytest module asserting google_workspace is registered with correct auth_type, auth_url, token_url, scopes, and env var names"
      contains: "test_google_workspace_registered"
    - path: "tests/unit/test_workspace_bridge.py"
      provides: "Pytest module covering: anonymous user short-circuit, no-creds case, successful inject path, sentinel idempotence, exception swallowing"
      contains: "test_credentials_injected"
    - path: "tests/unit/test_settings_validation.py"
      provides: "Pytest module asserting startup WARN fires for each missing env var and is suppressed when PYTEST_CURRENT_TEST is set"
      contains: "test_workspace_env_warn"
  key_links:
    - from: "app/agents/context_extractor.py:context_memory_before_model_callback"
      to: "app/services/google_workspace_auth_service.py:GoogleWorkspaceAuthService.resolve_credentials"
      via: "_try_load_google_workspace_credentials helper, sync call inside best-effort try/except"
      pattern: "resolve_credentials"
    - from: "app/agents/context_extractor.py:_try_load_google_workspace_credentials"
      to: "tool_context.state['google_provider_token']"
      via: "callback_context.state assignment after successful resolve"
      pattern: "google_provider_token.*="
    - from: "app/routers/integrations.py:authorize/callback (existing, unmodified)"
      to: "app/config/integration_providers.py:PROVIDER_REGISTRY['google_workspace']"
      via: "registry lookup at request time — no router changes required"
      pattern: "PROVIDER_REGISTRY\\[.google_workspace.\\]"
---

<objective>
Wire the broken credential bridge for Google Workspace at the **point of injection** (sync `before_model_callback`) and at the **point of OAuth registration** (`PROVIDER_REGISTRY`), plus environment-variable plumbing. After this plan, an existing `integration_credentials` row for a connected user is read at the start of every model callback and written to `tool_context.state["google_provider_token"]` so the 9 existing readers (docs, gmail, sheets, calendar, forms, gmail_inbox, briefing_tools, document_editor) start working without code changes.

This plan does **NOT** add per-helper auto-refresh (102-02), revoke-on-disconnect (102-02), or the frontend Connect card (102-03). It establishes the foundation those plans depend on.

Purpose: Satisfies WORKSPACE-02 (registry entry), WORKSPACE-03 (bridge in callback), WORKSPACE-06 (env var docs + startup WARN). Closes the "9 readers / 0 writers" gap identified in the 2026-05-08 audit (`102-RESEARCH.md` §Current State).

Output: `google_workspace` is a first-class entry in `PROVIDER_REGISTRY`; `context_memory_before_model_callback` calls a new sync helper `_try_load_google_workspace_credentials` that reads from `GoogleWorkspaceAuthService` and populates state; `.env.example` documents the three new env vars; module-level WARN at app boot complains about missing vars in non-test environments. Three new pytest modules pin all six observable truths.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/102-google-workspace-credential-bridge/102-CONTEXT.md
@.planning/phases/102-google-workspace-credential-bridge/102-RESEARCH.md
@app/config/integration_providers.py
@app/agents/context_extractor.py
@app/services/google_workspace_auth_service.py
@app/integrations/google/client.py
@.env.example

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->

From app/services/google_workspace_auth_service.py (sync API — DO NOT change):
```python
class GoogleWorkspaceAuthService:
    def resolve_credentials(
        self,
        user_id: str,
        *,
        provider_token: str | None = None,
        allow_legacy_fallback: bool = True,
    ) -> dict | None:
        """Returns {access_token, refresh_token, expires_at, source, is_canonical, ...}
        or None when no credentials exist. SYNCHRONOUS. Safe to call from sync
        before_model_callback. Already does its own try/except internally.
        """

def get_google_workspace_auth_service() -> GoogleWorkspaceAuthService:
    """Module-level singleton accessor. SYNCHRONOUS."""
```

From app/agents/context_extractor.py (existing precedent — match this pattern):
```python
# Lines 36-37 — sentinel keys are module-level constants
_CROSS_SESSION_LOADED_KEY = "_cross_session_context_loaded"
_BRAND_PROFILE_LOADED_KEY = "_brand_profile_loaded"

# Lines 56-63 — user_id extraction helper, already exists
def _get_callback_user_id(callback_context: CallbackContext) -> str:
    """Returns 'anonymous' when no user_id in state."""

# Lines 241-321 — _try_load_brand_profile pattern: sentinel check, sync work,
# best-effort try/except, debug log on success/skip. MIRROR THIS.

# Lines 788-942 — context_memory_before_model_callback: insert the new helper
# call AFTER the existing _try_load_cross_session_context call (~line 811)
# and BEFORE the personalization lookup.
```

From app/config/integration_providers.py (template at lines 174-200):
```python
# bigquery and google_ads entries use Google's auth/token URLs verbatim:
# auth_url="https://accounts.google.com/o/oauth2/v2/auth"
# token_url="https://oauth2.googleapis.com/token"
# Append the new entry after google_ads (line 200), before meta_ads.
```

From .env.example (current Google block, lines 12-21):
```
# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=...
GOOGLE_API_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=...
# (no GOOGLE_WORKSPACE_* entries today)
```

From app/integrations/google/client.py:87-94 (existing WARN precedent):
```python
# Existing pattern: at module import, complain when client_id/secret are
# unresolvable. The new _warn_missing_google_workspace_env should be a
# parallel module-level call placed near the existing logger setup.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add failing tests for registry entry, bridge function, and startup WARN</name>
  <files>tests/unit/test_integration_providers.py, tests/unit/test_workspace_bridge.py, tests/unit/test_settings_validation.py</files>
  <behavior>
    Create three new pytest modules. ALL tests must FAIL initially (RED) — they assert behavior that does not yet exist in the codebase.

    **`tests/unit/test_integration_providers.py`** — covers WORKSPACE-02. Add 1 test:
    - **test_google_workspace_registered**: imports `PROVIDER_REGISTRY` from `app.config.integration_providers` and asserts:
      - `"google_workspace" in PROVIDER_REGISTRY`
      - `entry.auth_type == "oauth2"`
      - `entry.auth_url == "https://accounts.google.com/o/oauth2/v2/auth"`
      - `entry.token_url == "https://oauth2.googleapis.com/token"`
      - `entry.client_id_env == "GOOGLE_WORKSPACE_CLIENT_ID"`
      - `entry.client_secret_env == "GOOGLE_WORKSPACE_CLIENT_SECRET"`
      - `set(entry.scopes) == {"https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/forms.body", "https://www.googleapis.com/auth/userinfo.email"}`

    **`tests/unit/test_workspace_bridge.py`** — covers WORKSPACE-03. Add 5 tests in a class `TestGoogleWorkspaceBridge`. Use `unittest.mock.MagicMock()` to fake `CallbackContext` with a mutable dict at `.state`. Patch target: `app.agents.context_extractor.get_google_workspace_auth_service` (module-scope import strategy — Task 2 will add the import).
    - **test_anonymous_user_short_circuits**: state has `user_id == "anonymous"`. Call `_try_load_google_workspace_credentials(callback_context)`. Assert `get_google_workspace_auth_service` was NOT called. Assert state has no `google_provider_token`. Assert sentinel `_google_workspace_creds_loaded` is set (so retry doesn't happen).
    - **test_no_user_id_short_circuits**: state has no `user_id` key (returns "anonymous" via `_get_callback_user_id` default). Same assertions.
    - **test_no_credentials_returns_silently**: state has `user_id == "user-1"`. Patched service returns `resolve_credentials.return_value = None`. Assert state has no `google_provider_token`. Assert sentinel is set. Assert no exception raised.
    - **test_credentials_injected**: state has `user_id == "user-1"`. Patched service returns `{"access_token": "ya29.test", "refresh_token": "1//test", "expires_at": "2026-05-08T12:00:00+00:00", "source": "integration_credentials"}`. After call, assert `state["google_provider_token"] == "ya29.test"`, `state["google_refresh_token"] == "1//test"`, `state["google_token_expires_at"] == "2026-05-08T12:00:00+00:00"`, sentinel set, AND `resolve_credentials` was called with `user_id="user-1"` and `allow_legacy_fallback=True`.
    - **test_sentinel_makes_call_idempotent**: state already has `_google_workspace_creds_loaded == True`. Call helper. Assert `get_google_workspace_auth_service` was NOT called.
    - **test_resolve_exception_is_swallowed**: patched service's `resolve_credentials` raises `RuntimeError("supabase down")`. Call helper. Assert no exception bubbles up. Assert sentinel is set (so we don't retry on every callback). Assert state has no `google_provider_token`. Assert a DEBUG-level log was emitted matching `"GoogleWorkspace.*Cred injection skipped"` (use `caplog.set_level(logging.DEBUG, logger="app.agents.context_extractor")`).

    **`tests/unit/test_settings_validation.py`** — covers WORKSPACE-06. Add 4 tests:
    - **test_workspace_env_warn_all_missing**: `monkeypatch.delenv` for all three vars; `monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)`; capture WARN logs; call the (yet-to-be-created) `_warn_missing_google_workspace_env()` function from `app.integrations.google.client`. Assert exactly one WARNING log line containing all three var names.
    - **test_workspace_env_warn_partial_missing**: only `GOOGLE_WORKSPACE_REDIRECT_URI` is unset; the other two are set; `PYTEST_CURRENT_TEST` unset. Call helper. Assert exactly one WARN naming only `GOOGLE_WORKSPACE_REDIRECT_URI`. Assert the other two var names do NOT appear in the captured message.
    - **test_workspace_env_warn_all_set_no_log**: all three set, `PYTEST_CURRENT_TEST` unset. Call helper. Assert NO WARN log emitted.
    - **test_workspace_env_warn_suppressed_in_pytest**: all three vars unset BUT `PYTEST_CURRENT_TEST` is set (default in pytest run). Call helper. Assert NO WARN log emitted.

    Run all three test files: ALL tests must FAIL with `ImportError`, `AssertionError`, or `AttributeError` referencing the missing entry / function / sentinel. This is the RED state.

    Commit message: `test(102-01): add failing tests for provider registry, bridge function, and startup WARN (WORKSPACE-02, -03, -06)`.
  </behavior>
  <action>
    Create the three new test files. Use existing patterns from `tests/unit/test_calendar_tools.py` (line 29 — `tool_context.state["google_provider_token"]` mock) and `tests/unit/test_google_workspace_auth_service.py` for fixture style.

    **For test_workspace_bridge.py — fake CallbackContext pattern:**
    ```python
    from unittest.mock import MagicMock, patch
    import logging

    def _make_callback_context(state: dict | None = None):
        ctx = MagicMock(spec_set=["state"])
        ctx.state = state if state is not None else {}
        return ctx
    ```

    **Patch target convention:** `app.agents.context_extractor.get_google_workspace_auth_service` — this requires Task 2 to import `from app.services.google_workspace_auth_service import get_google_workspace_auth_service` at module scope. If Task 2 instead uses an inline import (`from app.services... import ...` inside the helper), patches must target `app.services.google_workspace_auth_service.get_google_workspace_auth_service`. **Recommendation: module-scope import in Task 2 + patch at consumer module.** Pin this convention in the test file's docstring.

    **For test_settings_validation.py:** the function `_warn_missing_google_workspace_env` does not exist yet — Task 3 will create it in `app/integrations/google/client.py`. Tests should `from app.integrations.google.client import _warn_missing_google_workspace_env` (will ImportError until Task 3 lands → RED).

    **Lint:** new test files must pass `uv run ruff check tests/unit/test_integration_providers.py tests/unit/test_workspace_bridge.py tests/unit/test_settings_validation.py`. Test files are EXEMPT from interrogate docstring coverage but should have one-line module docstrings.

    Verify: every test fails (ImportError or AssertionError) because the production code does not yet have the registry entry, bridge function, or startup WARN.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_integration_providers.py tests/unit/test_workspace_bridge.py tests/unit/test_settings_validation.py -x 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    Three new test files exist with 10 total tests (1 + 6 + 4). All tests FAIL with ImportError (missing function/import) or AssertionError (missing registry entry / state injection). Commit `test(102-01): add failing tests for provider registry, bridge function, and startup WARN (WORKSPACE-02, -03, -06)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add google_workspace to PROVIDER_REGISTRY and wire bridge into context_extractor</name>
  <files>app/config/integration_providers.py, app/agents/context_extractor.py</files>
  <behavior>
    After this task, the test_integration_providers.py test (1 test) and test_workspace_bridge.py tests (6 tests) all turn GREEN. Existing context_extractor tests still pass.

    **In `app/config/integration_providers.py`:** append a new `google_workspace` entry to `PROVIDER_REGISTRY` after the `google_ads` entry (line 200) and before any subsequent provider:

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
            "https://www.googleapis.com/auth/gmail.readonly",
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

    Field types/required-ness mirror the bigquery/google_ads templates. If `ProviderConfig` is a dataclass without an `icon_url` or `category` field, drop those keyword args; if it requires additional fields, copy them from the bigquery template (read the file before editing).

    **In `app/agents/context_extractor.py`:** add the bridge in three steps.

    1. **Module-scope import** (near the top, alongside other service imports):
       ```python
       from app.services.google_workspace_auth_service import (
           get_google_workspace_auth_service,
       )
       ```

    2. **Add sentinel constant** (alongside `_BRAND_PROFILE_LOADED_KEY` and `_CROSS_SESSION_LOADED_KEY` at lines 36-37):
       ```python
       _GOOGLE_WORKSPACE_LOADED_KEY = "_google_workspace_creds_loaded"
       ```

    3. **Add the helper function** (place near `_try_load_brand_profile` at lines 241-321 to mirror the pattern):
       ```python
       def _try_load_google_workspace_credentials(
           callback_context: CallbackContext,
       ) -> None:
           """Resolve the requesting user's Google Workspace credentials and inject
           them into tool_context.state so the 9 existing readers can find them.

           Cached per-session via _GOOGLE_WORKSPACE_LOADED_KEY to avoid
           re-querying on every model callback (callback fires ~25x per turn for
           multi-agent flows).

           Best-effort: any exception is swallowed with a debug log so credential
           resolution never blocks the model call. Mid-session disconnect leaves
           the stale token in state; tool helpers will surface the resulting 401.
           """
           if callback_context.state.get(_GOOGLE_WORKSPACE_LOADED_KEY):
               return
           callback_context.state[_GOOGLE_WORKSPACE_LOADED_KEY] = True

           user_id = _get_callback_user_id(callback_context)
           if not user_id or user_id == "anonymous":
               return

           try:
               creds = get_google_workspace_auth_service().resolve_credentials(
                   user_id, allow_legacy_fallback=True,
               )
               if not creds:
                   return

               access_token = creds.get("access_token")
               refresh_token = creds.get("refresh_token")
               expires_at = creds.get("expires_at")
               if access_token:
                   callback_context.state["google_provider_token"] = access_token
               if refresh_token:
                   callback_context.state["google_refresh_token"] = refresh_token
               if expires_at:
                   callback_context.state["google_token_expires_at"] = expires_at

               logger.debug(
                   "[GoogleWorkspace] Injected creds for user=%s source=%s",
                   user_id, creds.get("source"),
               )
           except Exception as exc:
               logger.debug(
                   "[GoogleWorkspace] Cred injection skipped: %s", exc,
               )
       ```

    4. **Call from `context_memory_before_model_callback`** — locate the existing call to `_try_load_cross_session_context(callback_context)` (around line 811) and insert the new call DIRECTLY AFTER it, BEFORE the personalization lookup. Wrap in a top-level best-effort try/except so even an unexpected exception inside the helper cannot block the model call:
       ```python
       # --- Google Workspace credential bridge (Phase 102) ---
       try:
           _try_load_google_workspace_credentials(callback_context)
       except Exception:  # noqa: BLE001 — bridge is best-effort
           pass
       ```

    Run `uv run pytest tests/unit/test_integration_providers.py tests/unit/test_workspace_bridge.py -x` and confirm ALL 7 tests are GREEN.

    Run `uv run pytest tests/unit/ -k "context_extractor" -x` to catch regressions in any existing context_extractor tests.

    Lint: `uv run ruff check app/config/integration_providers.py app/agents/context_extractor.py --fix && uv run ruff format app/config/integration_providers.py app/agents/context_extractor.py && uv run ty check app/config/integration_providers.py app/agents/context_extractor.py`.

    Commit message: `feat(102-01): wire Google Workspace credential bridge in before_model_callback (WORKSPACE-02, WORKSPACE-03)`.
  </behavior>
  <action>
    Read `app/config/integration_providers.py` first to confirm the ProviderConfig dataclass shape and the exact line where google_ads ends. Read `app/agents/context_extractor.py` first to confirm the existing sentinel pattern, `_get_callback_user_id` location, and the exact line in `context_memory_before_model_callback` where the cross-session block ends.

    Make the edits as specified. Project rules: no print, no bare except (use `except Exception` with a `# noqa: BLE001` comment for the best-effort wrapper), no mutable default args, docstring on the new helper (interrogate enforces 80%+ docstring coverage).

    Verify GREEN: `uv run pytest tests/unit/test_integration_providers.py tests/unit/test_workspace_bridge.py -x` → all 7 pass.

    Verify NO REGRESSION: `uv run pytest tests/unit/ -k "context_extractor or before_model" -x` → all green.

    Lint clean.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_integration_providers.py tests/unit/test_workspace_bridge.py -x 2>&amp;1 | tail -25 &amp;&amp; uv run ruff check app/config/integration_providers.py app/agents/context_extractor.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    All 7 tests in test_integration_providers.py + test_workspace_bridge.py are GREEN. No regressions in existing context_extractor tests. `ruff check` and `ty check` clean on both modified files. The new entry in PROVIDER_REGISTRY is positioned after google_ads. The new helper in context_extractor.py is positioned near `_try_load_brand_profile` and is invoked from `context_memory_before_model_callback` immediately after the cross-session block. Commit `feat(102-01): wire Google Workspace credential bridge in before_model_callback (WORKSPACE-02, WORKSPACE-03)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add startup WARN and document env vars in .env.example</name>
  <files>app/integrations/google/client.py, .env.example</files>
  <behavior>
    After this task, all 4 tests in `tests/unit/test_settings_validation.py` are GREEN. Existing tests in test files that import from `app/integrations/google/client.py` still pass.

    **In `app/integrations/google/client.py`:** add a module-level function and call it at import time. Place it near the existing logger setup (around lines 87-94 where the existing `client_id`/`secret` complaint logic lives):

    ```python
    def _warn_missing_google_workspace_env() -> None:
        """Emit WARN for missing Google Workspace OAuth env vars in non-test environments.

        Skipped automatically when PYTEST_CURRENT_TEST is set so pytest runs are quiet.
        Mirrors the existing pattern at app/integrations/google/client.py for
        unresolvable client_id/secret.
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
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
                "Per-user Google Workspace integration will be unavailable until set.",
                ", ".join(missing),
            )

    # Call at module import:
    _warn_missing_google_workspace_env()
    ```

    Order constraint: the function must be defined BEFORE the bottom-of-module call. The bottom-of-module call must be after `logger = logging.getLogger(__name__)` is set.

    **In `.env.example`:** append a new block after the existing Google block (after line 21):

    ```bash
    # Google Workspace per-user OAuth (Phase 102)
    # Required for in-app "Connect Google Workspace" flow that stores reusable
    # refresh tokens in integration_credentials. DIFFERENT from GOOGLE_API_KEY
    # (Vertex/Gemini API) and GOOGLE_CLIENT_ID (legacy Supabase Auth Google identity).
    # Get from Google Cloud Console -> APIs & Services -> Credentials -> OAuth 2.0 Client IDs.
    # Recommendation: use a SEPARATE OAuth client from GOOGLE_CLIENT_ID so scope grants
    # and disconnects are independent.
    # GOOGLE_WORKSPACE_CLIENT_ID=your_oauth_client_id.apps.googleusercontent.com
    # GOOGLE_WORKSPACE_CLIENT_SECRET=your_oauth_client_secret
    # GOOGLE_WORKSPACE_REDIRECT_URI=https://your-domain.com/integrations/google_workspace/callback
    ```

    All three lines must be **commented out** (leading `#`) so the example file does not shadow the user's real env. Comments above must explain what each var is for and call out the difference from `GOOGLE_API_KEY` and `GOOGLE_CLIENT_ID`.

    Run `uv run pytest tests/unit/test_settings_validation.py -x` and confirm all 4 tests GREEN.

    Lint: `uv run ruff check app/integrations/google/client.py --fix && uv run ruff format app/integrations/google/client.py && uv run ty check app/integrations/google/client.py`.

    Commit message: `feat(102-01): startup WARN + .env.example for Google Workspace OAuth env vars (WORKSPACE-06)`.
  </behavior>
  <action>
    Read `app/integrations/google/client.py` first to confirm the existing logger setup line and the existing client_id/secret complaint pattern. Match imports (`os`, `logging`) — both are likely already imported.

    Place the new function near the existing complaint logic. The bottom-of-module `_warn_missing_google_workspace_env()` call must execute on import, but must NOT raise (`os.environ.get` returns `None` gracefully).

    Append to `.env.example` exactly as specified above. Maintain the leading `#` on the three var lines so users uncomment + fill them in.

    Verify GREEN: `uv run pytest tests/unit/test_settings_validation.py -x` → all 4 pass.

    Verify NO REGRESSION: `uv run pytest tests/unit/ -k "google_client or settings" -x` → green.

    Lint clean.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_settings_validation.py -x 2>&amp;1 | tail -15 &amp;&amp; uv run ruff check app/integrations/google/client.py 2>&amp;1 | tail -3</automated>
  </verify>
  <done>
    4/4 test_settings_validation.py tests GREEN. `.env.example` documents all three new vars with explanatory comments. `_warn_missing_google_workspace_env` is called at module import. `ruff check` and `ty check` clean. Commit `feat(102-01): startup WARN + .env.example for Google Workspace OAuth env vars (WORKSPACE-06)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end (per-task): see each `<verify>` block.

Plan-level: `uv run pytest tests/unit/test_integration_providers.py tests/unit/test_workspace_bridge.py tests/unit/test_settings_validation.py -x` → all 11 tests GREEN.

Regression: `uv run pytest tests/unit/ -x` → all unit tests GREEN (no existing test broken).

Manual smoke (deferred to phase-level UAT after 102-03): in `make local-backend`, log in as a user, manually insert an `integration_credentials` row for that user with `provider='google_workspace'` (encrypted token from existing Phase 101 helper), send a chat message that routes to the Marketing agent, then add a `logger.info` breakpoint in `context_extractor` confirming `google_provider_token` was written to state. Real OAuth flow tested in 102-03.
</verification>

<success_criteria>
- `PROVIDER_REGISTRY["google_workspace"]` exists with all 8 scopes, correct env var names, and the canonical Google auth/token URLs.
- `app/agents/context_extractor.py` defines `_GOOGLE_WORKSPACE_LOADED_KEY` and `_try_load_google_workspace_credentials`, and invokes the latter from `context_memory_before_model_callback` immediately after `_try_load_cross_session_context`.
- The bridge is best-effort: no exception path from `resolve_credentials` blocks the model call.
- Sentinel makes the resolve call idempotent within a session.
- `app/integrations/google/client.py` defines `_warn_missing_google_workspace_env` and calls it at module import time. Skipped under `PYTEST_CURRENT_TEST`.
- `.env.example` documents `GOOGLE_WORKSPACE_CLIENT_ID`, `GOOGLE_WORKSPACE_CLIENT_SECRET`, `GOOGLE_WORKSPACE_REDIRECT_URI` with comments explaining the difference from `GOOGLE_API_KEY` and `GOOGLE_CLIENT_ID`.
- All 11 new pytest tests in 3 new test files GREEN.
- No regressions: `uv run pytest tests/unit/ -x` clean.
- Lint: `ruff check`, `ruff format`, `ty check` clean on all modified files.
</success_criteria>

<output>
After completion, create `.planning/phases/102-google-workspace-credential-bridge/102-01-provider-registry-and-bridge-SUMMARY.md` documenting:
- Exact line numbers of the registry entry, sentinel constant, helper function, callback wiring, and startup WARN
- Module-scope vs inline import decision and rationale (matching 102-CONTEXT lock)
- Test count delta (existing N → existing N + 11 GREEN)
- Any deviations from this plan, especially scope set adjustments if `gmail.readonly` was dropped due to verification status (Open Question 1 in 102-CONTEXT)
- Confirmation that `context_memory_before_model_callback` is still sync (no `asyncio.run` introduced)
</output>
