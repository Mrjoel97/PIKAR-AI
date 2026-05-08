---
phase: 102-google-workspace-credential-bridge
plan: 02
type: execute
wave: 2
depends_on: [102-01]
files_modified:
  - app/services/google_workspace_token_refresh.py
  - app/services/google_workspace_auth_service.py
  - app/agents/tools/docs.py
  - app/agents/tools/gmail.py
  - app/agents/tools/google_sheets.py
  - app/agents/tools/calendar_tool.py
  - app/agents/tools/forms.py
  - app/agents/tools/gmail_inbox.py
  - app/agents/tools/briefing_tools.py
  - app/agents/tools/document_editor.py
  - tests/unit/test_workspace_token_refresh.py
  - tests/unit/test_google_workspace_auth_service.py
autonomous: true
requirements: [WORKSPACE-04, WORKSPACE-05]

must_haves:
  truths:
    - "When tool_context.state['google_token_expires_at'] is within 5 minutes of now, refresh_if_expiring posts to https://oauth2.googleapis.com/token with grant_type=refresh_token and updates state with the new access token"
    - "When tool_context.state['google_token_expires_at'] is more than 5 minutes away, refresh_if_expiring is a no-op (no HTTP call)"
    - "When tool_context.state['google_token_expires_at'] is None (legacy fallback path), refresh_if_expiring is a no-op (cannot determine expiry)"
    - "After a successful refresh, GoogleWorkspaceAuthService.sync_credentials persists the new token to integration_credentials so future sessions benefit"
    - "Each of the 7 Google Workspace tool helpers (_get_docs_service, _get_gmail_service, _get_sheets_service, _get_calendar_service, _get_forms_service, _get_gmail_reader, briefing_tools.approve_draft inline read) calls refresh_if_expiring(tool_context) before reading google_provider_token from state"
    - "GoogleWorkspaceAuthService.disconnect resolves the access token, POSTs to https://oauth2.googleapis.com/revoke, then deletes integration_credentials AND legacy rows even if the revoke call fails"
    - "Disconnect with no stored token returns gracefully (no HTTP call attempted, no exception)"
  artifacts:
    - path: "app/services/google_workspace_token_refresh.py"
      provides: "Sync refresh_if_expiring(tool_context, *, threshold_minutes=5) helper plus _is_expiring_soon timestamp parser"
      contains: "def refresh_if_expiring"
    - path: "app/services/google_workspace_auth_service.py"
      provides: "Modified disconnect() that POSTs to oauth2.googleapis.com/revoke before deleting rows"
      contains: "oauth2.googleapis.com/revoke"
    - path: "app/agents/tools/docs.py"
      provides: "_get_docs_service calls refresh_if_expiring(tool_context) before reading google_provider_token"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/gmail.py"
      provides: "Same wiring for _get_gmail_service"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/google_sheets.py"
      provides: "Same wiring for _get_sheets_service"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/calendar_tool.py"
      provides: "Same wiring for _get_calendar_service"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/forms.py"
      provides: "Same wiring for _get_forms_service"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/gmail_inbox.py"
      provides: "Same wiring for _get_gmail_reader"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/briefing_tools.py"
      provides: "Same wiring at the inline state read inside approve_draft"
      contains: "refresh_if_expiring"
    - path: "app/agents/tools/document_editor.py"
      provides: "Same wiring if/where the helper reads google_provider_token (verify and apply)"
      contains: "refresh_if_expiring"
    - path: "tests/unit/test_workspace_token_refresh.py"
      provides: "Pytest module covering refresh-when-expiring, no-op-when-fresh, no-op-when-expires-at-None, sync_credentials persists after refresh, refresh failure is best-effort"
      contains: "test_refresh_when_expiring"
    - path: "tests/unit/test_google_workspace_auth_service.py"
      provides: "New TestDisconnectRevoke class covering revoke-success-then-delete, revoke-failure-still-deletes, no-token-no-http-call"
      contains: "TestDisconnectRevoke"
  key_links:
    - from: "app/services/google_workspace_token_refresh.py:refresh_if_expiring"
      to: "https://oauth2.googleapis.com/token"
      via: "httpx.Client.post (sync) with grant_type=refresh_token"
      pattern: "oauth2.googleapis.com/token"
    - from: "app/services/google_workspace_token_refresh.py:refresh_if_expiring"
      to: "app/services/google_workspace_auth_service.py:GoogleWorkspaceAuthService.sync_credentials"
      via: "best-effort persist of refreshed token to integration_credentials"
      pattern: "sync_credentials"
    - from: "app/agents/tools/docs.py:_get_docs_service"
      to: "app/services/google_workspace_token_refresh.py:refresh_if_expiring"
      via: "synchronous call before reading google_provider_token"
      pattern: "refresh_if_expiring\\(tool_context"
    - from: "app/services/google_workspace_auth_service.py:disconnect"
      to: "https://oauth2.googleapis.com/revoke"
      via: "httpx.Client.post (sync) with token={access_token}"
      pattern: "oauth2.googleapis.com/revoke"
---

<objective>
Complete the credential lifecycle: tokens auto-refresh within 5 minutes of expiry without rewriting all tool helpers to async, and disconnects revoke at Google before deleting local rows. After this plan, the auto-refresh success criterion (RESEARCH §Target State #3) and the revoke-on-disconnect success criterion (#4) are met, and 102-03's frontend Disconnect button has a working backend to point at.

This plan does **NOT** add the frontend Connect/Disconnect UI (102-03). It assumes 102-01's bridge has populated `state["google_provider_token"]`, `state["google_refresh_token"]`, and `state["google_token_expires_at"]` and adds the **point-of-use refresh** that keeps tokens fresh.

**Key architectural decision (locked in 102-CONTEXT):** Hybrid sync-refresh model (Approach C). The `before_model_callback` is sync; rewriting 7 helpers + 30+ tool functions to async is rejected as too risky for v13.0. Instead, a sync `refresh_if_expiring` helper using `httpx.Client` (sync) replicates the refresh logic of the async `IntegrationManager._refresh_token`. Strict reading of WORKSPACE-04 says "calls `IntegrationManager.get_valid_token`" — we ship the hybrid because it satisfies the **success criterion** (auto-refresh within 5 min, verifiable by clock-patched unit test). 102-CONTEXT documents this deviation; 102-02 SUMMARY must restate it.

Purpose: Satisfies WORKSPACE-04 (auto-refresh) and WORKSPACE-05 (disconnect-revoke). Closes the audit gap where today an expired token surfaces as a 401 to the user with no recovery path.

Output: New module `app/services/google_workspace_token_refresh.py` providing `refresh_if_expiring`. Modified `GoogleWorkspaceAuthService.disconnect` calls Google's revoke endpoint before deleting rows. All 7 Google Workspace tool helpers call `refresh_if_expiring(tool_context)` as the first line of their `_get_X_service` body. Two new pytest test files / extensions pin all 7 observable truths.
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
@.planning/phases/102-google-workspace-credential-bridge/102-01-provider-registry-and-bridge-PLAN.md
@app/services/google_workspace_auth_service.py
@app/services/integration_manager.py
@app/integrations/google/client.py
@app/agents/tools/docs.py
@app/agents/tools/gmail.py
@app/agents/tools/google_sheets.py
@app/agents/tools/calendar_tool.py
@app/agents/tools/forms.py
@app/agents/tools/gmail_inbox.py
@app/agents/tools/briefing_tools.py
@app/agents/tools/document_editor.py
@tests/unit/test_google_workspace_auth_service.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->

From app/services/google_workspace_auth_service.py:
```python
class GoogleWorkspaceAuthService:
    def sync_credentials(
        self,
        *,
        user_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: str | None = None,
        scopes: list[str] | None = None,
        account_name: str | None = None,
    ) -> bool:
        """Persist (or update) the per-user row in integration_credentials.
        Encrypts access_token + refresh_token via Phase 101 Fernet helpers.
        SYNCHRONOUS. Used by the new sync refresh helper to write back."""

    def disconnect(self, user_id: str) -> bool:
        """Currently (lines 234-266): deletes integration_credentials,
        user_google_tokens, user_oauth_tokens, integration_sync_state rows;
        sets disconnect marker. Does NOT call revoke today."""

    def resolve_credentials(self, user_id: str, *, allow_legacy_fallback: bool = True) -> dict | None:
        """Returns {access_token, refresh_token, expires_at, source, ...}
        SYNCHRONOUS. Used by disconnect() to fetch token before revoking."""
```

From app/services/integration_manager.py:259-260 (REFRESH ROTATION FALLBACK pattern — mirror in sync helper):
```python
new_access = token_data.get("access_token", "")
new_refresh = token_data.get("refresh_token", refresh_token)  # fallback to old if not rotated
```

Existing 9 reader sites (READ before editing — confirm exact pattern):
```python
# app/agents/tools/docs.py:21-33 — _get_docs_service
# app/agents/tools/gmail.py:18-31 — _get_gmail_service
# app/agents/tools/google_sheets.py:91-112 — _get_sheets_service
# app/agents/tools/calendar_tool.py:36-49 — _get_calendar_service
# app/agents/tools/forms.py:56-68 — _get_forms_service
# app/agents/tools/gmail_inbox.py:19-41 — _get_gmail_reader
# app/agents/tools/briefing_tools.py:139-178 — inline read inside approve_draft
# app/agents/tools/document_editor.py — exact line varies; verify during execution
```

Each reader has the same shape:
```python
def _get_X_service(tool_context: ToolContextType):
    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")
    if not provider_token:
        raise ValueError("Google authentication required for ...")
    credentials = get_google_credentials(provider_token, refresh_token)
    return GoogleXService(credentials)
```

The patch is ONE LINE at the start of each helper:
```python
def _get_X_service(tool_context: ToolContextType):
    refresh_if_expiring(tool_context)  # NEW
    provider_token = tool_context.state.get("google_provider_token")
    # ... rest unchanged ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add failing tests for refresh helper and disconnect-revoke</name>
  <files>tests/unit/test_workspace_token_refresh.py, tests/unit/test_google_workspace_auth_service.py</files>
  <behavior>
    Create one new pytest module and extend an existing one. ALL new tests must FAIL initially (RED).

    **`tests/unit/test_workspace_token_refresh.py`** (NEW) — covers WORKSPACE-04. Add 8 tests in a class `TestRefreshIfExpiring`. Helper: a `_make_tool_context(state)` function returning a `MagicMock` with a mutable dict at `.state`.

    - **test_refresh_when_expiring**: state has `user_id="user-1"`, `google_provider_token="old-access"`, `google_refresh_token="rt-1"`, `google_token_expires_at = (now + 2 minutes).isoformat()` (within the 5-min threshold). Patch `httpx.Client` (via context manager) so `.post()` returns a mock with `status_code=200` and `json()=={"access_token": "new-access", "refresh_token": "rt-2", "expires_in": 3600}`. Patch env: `GOOGLE_WORKSPACE_CLIENT_ID="cid"`, `GOOGLE_WORKSPACE_CLIENT_SECRET="cs"`. Patch `app.services.google_workspace_token_refresh.get_google_workspace_auth_service` to return a service whose `sync_credentials` is a `MagicMock(return_value=True)`. Call `refresh_if_expiring(tool_context)`. Assert:
      - `httpx.Client.post` called exactly once with URL `"https://oauth2.googleapis.com/token"` and `data["grant_type"] == "refresh_token"`, `data["refresh_token"] == "rt-1"`, `data["client_id"] == "cid"`, `data["client_secret"] == "cs"`
      - `state["google_provider_token"] == "new-access"`
      - `state["google_refresh_token"] == "rt-2"`
      - `state["google_token_expires_at"]` parses as a datetime ~3600 seconds from now (±5 min tolerance)
      - service.sync_credentials called once with `user_id="user-1"`, `access_token="new-access"`, `refresh_token="rt-2"`, `expires_at=<the new ISO string>`

    - **test_no_op_when_token_fresh**: same setup but `google_token_expires_at = (now + 30 minutes).isoformat()` (NOT within the 5-min threshold). Call helper. Assert `httpx.Client.post` was NOT called. Assert state unchanged.

    - **test_no_op_when_expires_at_none**: state has `google_token_expires_at = None` (legacy-source fallback path). Call helper. Assert no HTTP call. State unchanged.

    - **test_no_op_when_no_user_id**: state lacks `user_id`. Assert no HTTP call.

    - **test_no_op_when_no_refresh_token**: state has `user_id` and `expires_at` within threshold but `google_refresh_token = None`. Assert no HTTP call.

    - **test_no_op_when_env_unconfigured**: state set up to refresh but `GOOGLE_WORKSPACE_CLIENT_ID` is unset. Assert no HTTP call.

    - **test_refresh_token_rotation_fallback**: response has `access_token` and `expires_in` but NO `refresh_token` field. Assert state's `google_refresh_token` is unchanged from the pre-call value `"rt-1"`. Assert `sync_credentials` was called with `refresh_token="rt-1"`.

    - **test_refresh_failure_is_best_effort**: `httpx.Client.post` raises `httpx.RequestError("network down")`. Call helper. Assert no exception bubbles up. Assert state unchanged. Assert WARNING log captured matching `"refresh_if_expiring|token refresh failed"`.

    Total: 8 tests in this file.

    **`tests/unit/test_google_workspace_auth_service.py`** (EXTEND) — covers WORKSPACE-05. Append a new class `TestDisconnectRevoke` (after the existing tests). Add 4 tests:

    - **test_disconnect_revokes_then_deletes**: mock `service.resolve_credentials` to return `{"access_token": "ya29.test"}`. Patch `httpx.Client.post` to return `Mock(status_code=200)`. Call `service.disconnect(user_id="user-1")`. Assert `httpx.Client.post` called once with `"https://oauth2.googleapis.com/revoke"`, `data={"token": "ya29.test"}`, `headers={"content-type": "application/x-www-form-urlencoded"}`. Spy on `service._delete_rows` to confirm at least 1 invocation against `integration_credentials`. Return value `True`.

    - **test_disconnect_revoke_failure_still_deletes**: `httpx.Client.post` raises `httpx.RequestError("revoke endpoint down")`. Call disconnect. Assert `_delete_rows` was STILL called. Assert WARNING captured matching `"Google revoke failed|revoke returned"`. Return value `True`.

    - **test_disconnect_revoke_non200_logs_warning**: `httpx.Client.post` returns `Mock(status_code=400, text="error=invalid_token")`. Call disconnect. Assert deletion still happened. Assert WARNING captured naming the status code (`400`).

    - **test_disconnect_no_token_no_http_call**: `resolve_credentials` returns `None`. Call disconnect. Assert `httpx.Client.post` NOT called. Assert `_delete_rows` STILL invoked (idempotent disconnect).

    Run: `uv run pytest tests/unit/test_workspace_token_refresh.py tests/unit/test_google_workspace_auth_service.py::TestDisconnectRevoke -x`. ALL must FAIL with ImportError or AssertionError.

    Commit message: `test(102-02): add failing tests for token refresh and disconnect-revoke (WORKSPACE-04, WORKSPACE-05)`.
  </behavior>
  <action>
    **For test_workspace_token_refresh.py:** create from scratch. Use `freezegun` if already in dev deps for clock control; otherwise `monkeypatch` `datetime.datetime.now` inside `app.services.google_workspace_token_refresh`. Verify `freezegun` availability via `grep -r "freezegun" pyproject.toml tests/` first.

    Mocking strategy for `httpx.Client`:
    ```python
    @patch("app.services.google_workspace_token_refresh.httpx.Client")
    def test_refresh_when_expiring(self, mock_client_cls, monkeypatch):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"access_token": "new-access", "refresh_token": "rt-2", "expires_in": 3600}
        mock_client.post.return_value = mock_response
        monkeypatch.setenv("GOOGLE_WORKSPACE_CLIENT_ID", "cid")
        monkeypatch.setenv("GOOGLE_WORKSPACE_CLIENT_SECRET", "cs")
    ```

    **For test_google_workspace_auth_service.py:** read the existing test file first to confirm fixture patterns. Append `TestDisconnectRevoke` as the last class. Mock `httpx.Client` at the module path inside `google_workspace_auth_service` (Task 3 will add the import).

    Lint test files. Verify all new tests fail with the expected import / assertion errors.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_workspace_token_refresh.py tests/unit/test_google_workspace_auth_service.py::TestDisconnectRevoke -x 2>&amp;1 | tail -40</automated>
  </verify>
  <done>
    8 new tests in test_workspace_token_refresh.py + 4 new tests in test_google_workspace_auth_service.py::TestDisconnectRevoke. ALL FAIL (RED). Existing test_google_workspace_auth_service.py tests still pass. Commit `test(102-02): add failing tests for token refresh and disconnect-revoke (WORKSPACE-04, WORKSPACE-05)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement google_workspace_token_refresh.py and wire into 7 tool helpers</name>
  <files>app/services/google_workspace_token_refresh.py, app/agents/tools/docs.py, app/agents/tools/gmail.py, app/agents/tools/google_sheets.py, app/agents/tools/calendar_tool.py, app/agents/tools/forms.py, app/agents/tools/gmail_inbox.py, app/agents/tools/briefing_tools.py, app/agents/tools/document_editor.py</files>
  <behavior>
    After this task, all 8 tests in `test_workspace_token_refresh.py` are GREEN. All existing tests in `tests/unit/test_calendar_tools.py`, `test_gmail_inbox_tools.py`, etc. still pass (regression).

    **Create `app/services/google_workspace_token_refresh.py`:**

    ```python
    """Synchronous Google Workspace OAuth token refresh.

    Companion to GoogleWorkspaceAuthService for the in-flight tool helper path,
    which is sync. Mirrors the logic of IntegrationManager._refresh_token (async)
    but uses httpx.Client (sync) so it can be called from sync ADK before_model
    callbacks and tool functions without hitting the async/sync boundary.

    Phase 102, requirement WORKSPACE-04 (auto-refresh within 5 min of expiry).
    """
    from __future__ import annotations

    import logging
    import os
    from datetime import datetime, timedelta, timezone

    import httpx

    from app.services.google_workspace_auth_service import (
        get_google_workspace_auth_service,
    )

    logger = logging.getLogger(__name__)

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


    def _is_expiring_soon(expires_at_iso: str | None, *, minutes: int) -> bool:
        """Return True if the ISO-8601 expiry is within `minutes` of now (UTC)."""
        if not expires_at_iso:
            return False
        try:
            expires_at = datetime.fromisoformat(expires_at_iso)
        except (ValueError, TypeError):
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at - datetime.now(tz=timezone.utc) < timedelta(minutes=minutes)


    def refresh_if_expiring(tool_context, *, threshold_minutes: int = 5) -> None:
        """Refresh google_provider_token in tool_context if within threshold of expiry.

        Best-effort: silently no-ops on missing user_id, missing refresh token,
        unconfigured env, expires_at=None (legacy fallback), or network failure.
        Persists the new token to integration_credentials via sync_credentials
        so future sessions benefit.
        """
        state = tool_context.state
        if not _is_expiring_soon(
            state.get("google_token_expires_at"), minutes=threshold_minutes,
        ):
            return

        user_id = state.get("user_id")
        refresh_token = state.get("google_refresh_token")
        if not user_id or not refresh_token:
            return

        client_id = os.environ.get("GOOGLE_WORKSPACE_CLIENT_ID", "")
        client_secret = os.environ.get("GOOGLE_WORKSPACE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return

        try:
            with httpx.Client(timeout=30.0) as http:
                resp = http.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.warning("refresh_if_expiring: token refresh failed: %s", exc)
            return

        new_access = data.get("access_token", "")
        new_refresh = data.get("refresh_token", refresh_token)
        expires_in = data.get("expires_in")
        new_expires_at = (
            (datetime.now(tz=timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
            if expires_in else None
        )

        if new_access:
            state["google_provider_token"] = new_access
        if new_refresh:
            state["google_refresh_token"] = new_refresh
        if new_expires_at:
            state["google_token_expires_at"] = new_expires_at

        try:
            get_google_workspace_auth_service().sync_credentials(
                user_id=user_id,
                access_token=new_access,
                refresh_token=new_refresh,
                expires_at=new_expires_at,
            )
        except Exception as exc:  # noqa: BLE001 — best-effort persistence
            logger.debug("refresh_if_expiring: sync_credentials failed: %s", exc)
    ```

    **Wire into the 7 tool helpers:** in each of the listed files, add ONE LINE at the top of the helper body and ONE IMPORT at the top of the file. Pattern:

    ```python
    # Top of file, with other imports:
    from app.services.google_workspace_token_refresh import refresh_if_expiring

    # First line of the helper body:
    def _get_docs_service(tool_context: ToolContextType):
        refresh_if_expiring(tool_context)  # auto-refresh if within 5 min of expiry
        provider_token = tool_context.state.get("google_provider_token")
        # ... rest unchanged ...
    ```

    Apply identically to:
    1. `app/agents/tools/docs.py` -> `_get_docs_service`
    2. `app/agents/tools/gmail.py` -> `_get_gmail_service`
    3. `app/agents/tools/google_sheets.py` -> `_get_sheets_service`
    4. `app/agents/tools/calendar_tool.py` -> `_get_calendar_service`
    5. `app/agents/tools/forms.py` -> `_get_forms_service`
    6. `app/agents/tools/gmail_inbox.py` -> `_get_gmail_reader`
    7. `app/agents/tools/briefing_tools.py` -> at the inline read inside `approve_draft` (line ~168). Insert `refresh_if_expiring(tool_context)` immediately before `provider_token = tool_context.state.get("google_provider_token")`.
    8. `app/agents/tools/document_editor.py` -> grep for `google_provider_token`; if a helper is found, apply the same wiring. If the reference is only in a docstring (per RESEARCH section 1.8, line 1027 is "referenced in docstring"), no code change is needed for this file — note this in the SUMMARY. Verify with grep.

    Run `uv run pytest tests/unit/test_workspace_token_refresh.py -x` -> all 8 GREEN.
    Run `uv run pytest tests/unit/test_calendar_tools.py tests/unit/test_gmail_inbox_tools.py -x` -> no regression.
    Run `uv run pytest tests/unit/ -k "tools" -x` -> no broader regression.

    Lint all 9 modified files: `uv run ruff check app/services/google_workspace_token_refresh.py app/agents/tools/docs.py app/agents/tools/gmail.py app/agents/tools/google_sheets.py app/agents/tools/calendar_tool.py app/agents/tools/forms.py app/agents/tools/gmail_inbox.py app/agents/tools/briefing_tools.py app/agents/tools/document_editor.py --fix`. Then `uv run ruff format` and `uv run ty check` on the same files.

    Commit message: `feat(102-02): sync Google OAuth refresh helper + wire into 7 tool helpers (WORKSPACE-04)`.
  </behavior>
  <action>
    First, **grep** to confirm the exact line of each helper:
    ```bash
    grep -n "def _get_docs_service\|def _get_gmail_service\|def _get_sheets_service\|def _get_calendar_service\|def _get_forms_service\|def _get_gmail_reader" app/agents/tools/*.py
    grep -n "google_provider_token" app/agents/tools/briefing_tools.py app/agents/tools/document_editor.py
    ```

    Create `google_workspace_token_refresh.py` exactly as specified. Use `from __future__ import annotations` so `str | None` syntax works. Project rules: no print, no bare except (use `except Exception` with `# noqa: BLE001`), docstrings on all public functions.

    For each tool helper file: read the file, add the import in the existing import block (alphabetical placement), add the one-line call at the top of each `_get_X_service` body. Do NOT re-order or refactor existing code.

    Note `briefing_tools.py:approve_draft` reads `google_provider_token` inline (not via a helper) per RESEARCH section 1.7. Insert `refresh_if_expiring(tool_context)` directly before that line.

    For `document_editor.py`: grep first; if no actual read site exists (RESEARCH says line 1027 is only a docstring reference), skip the file but note in SUMMARY.

    Run tests + lint + type check. Verify GREEN.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_workspace_token_refresh.py -x 2>&amp;1 | tail -20 &amp;&amp; uv run pytest tests/unit/test_calendar_tools.py tests/unit/test_gmail_inbox_tools.py -x 2>&amp;1 | tail -10 &amp;&amp; uv run ruff check app/services/google_workspace_token_refresh.py app/agents/tools/docs.py app/agents/tools/gmail.py app/agents/tools/google_sheets.py app/agents/tools/calendar_tool.py app/agents/tools/forms.py app/agents/tools/gmail_inbox.py app/agents/tools/briefing_tools.py 2>&amp;1 | tail -5</automated>
  </verify>
  <done>
    All 8 tests in test_workspace_token_refresh.py GREEN. No regressions in test_calendar_tools.py / test_gmail_inbox_tools.py. New module `app/services/google_workspace_token_refresh.py` exists with `refresh_if_expiring` exported. All 7 (or 8) tool helpers call `refresh_if_expiring(tool_context)` as the first line of their body. `ruff check`, `ruff format`, `ty check` clean across all 9 files. Commit `feat(102-02): sync Google OAuth refresh helper + wire into 7 tool helpers (WORKSPACE-04)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add revoke call to GoogleWorkspaceAuthService.disconnect</name>
  <files>app/services/google_workspace_auth_service.py</files>
  <behavior>
    After this task, all 4 tests in `test_google_workspace_auth_service.py::TestDisconnectRevoke` are GREEN. All existing tests in test_google_workspace_auth_service.py still pass.

    Modify the existing `disconnect` method (lines 234-266). Insert revoke logic BEFORE the existing `_delete_rows` calls.

    Replacement body shape:

    ```python
    def disconnect(self, user_id: str) -> bool:
        """Revoke at Google, then remove reusable Google Workspace credentials.

        Best-effort revoke: if the network call fails or returns non-200, we log
        a warning and proceed with local row deletion so the user is never stuck
        in a half-disconnected state.
        """
        # Resolve the access token BEFORE deletion so we can revoke it.
        access_token: str | None = None
        try:
            creds = self.resolve_credentials(user_id, allow_legacy_fallback=True)
            access_token = creds.get("access_token") if creds else None
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.debug("disconnect: resolve_credentials failed: %s", exc)

        # Revoke at Google (best-effort).
        if access_token:
            try:
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
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning("Google revoke failed for user=%s: %s", user_id, exc)

        # Existing delete logic — preserve current row deletions verbatim.
        deleted_any = False
        deleted_any = self._delete_rows(
            "integration_credentials", user_id=user_id, provider=GOOGLE_WORKSPACE_PROVIDER,
        ) or deleted_any
        deleted_any = self._delete_rows("user_google_tokens", user_id=user_id) or deleted_any
        deleted_any = self._delete_rows(
            "user_oauth_tokens", user_id=user_id, provider="google",
        ) or deleted_any
        deleted_any = self._delete_rows(
            "integration_sync_state", user_id=user_id, provider=GOOGLE_WORKSPACE_PROVIDER,
        ) or deleted_any
        self._set_disconnect_marker(user_id)

        return bool(access_token) or deleted_any
    ```

    **Critical:** preserve the EXACT set of `_delete_rows` calls and the `_set_disconnect_marker` call from the current implementation (lines 234-266). DO NOT add or remove rows. Read the file first to confirm the current call list before editing — the constants `GOOGLE_WORKSPACE_PROVIDER` and table names must match what's already in the file.

    Add `import httpx` at the top of the file if not already imported. RESEARCH section "Standard Stack" confirms httpx is already a project dep.

    Run `uv run pytest tests/unit/test_google_workspace_auth_service.py -x` -> all existing + 4 new tests GREEN.

    Lint: `uv run ruff check app/services/google_workspace_auth_service.py --fix && uv run ruff format app/services/google_workspace_auth_service.py && uv run ty check app/services/google_workspace_auth_service.py`.

    Commit message: `feat(102-02): revoke at Google before deleting local rows on disconnect (WORKSPACE-05)`.
  </behavior>
  <action>
    Read `app/services/google_workspace_auth_service.py:234-266` first to capture the exact current `_delete_rows` call list and constants. Confirm `import httpx` status (likely already imported alongside other service imports — if not, add it).

    Replace the existing `disconnect` method body (NOT the signature) with the new body that wraps revoke around the existing delete logic. Project rules: no print, no bare except (`except Exception` with `# noqa: BLE001`), preserve the existing docstring style.

    Run tests. Verify all GREEN.

    Lint clean.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/test_google_workspace_auth_service.py -x 2>&amp;1 | tail -20 &amp;&amp; uv run ruff check app/services/google_workspace_auth_service.py 2>&amp;1 | tail -3</automated>
  </verify>
  <done>
    4/4 TestDisconnectRevoke tests GREEN. All existing test_google_workspace_auth_service.py tests still GREEN. `disconnect()` resolves the access token, attempts revoke against `https://oauth2.googleapis.com/revoke`, then ALWAYS proceeds to delete local rows (revoke failure is best-effort). `ruff check` and `ty check` clean. Commit `feat(102-02): revoke at Google before deleting local rows on disconnect (WORKSPACE-05)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end (per-task): see each `<verify>` block.

Plan-level: `uv run pytest tests/unit/test_workspace_token_refresh.py tests/unit/test_google_workspace_auth_service.py -x` -> all 12 new tests + all existing tests GREEN.

Regression: `uv run pytest tests/unit/ -x` -> all unit tests pass.

Manual smoke (deferred to phase-level UAT after 102-03):
1. Connect Google Workspace via the new card (Plan 102-03).
2. Manually edit `integration_credentials.expires_at` to be 2 minutes in the future for the test user.
3. Send a chat message asking the agent to "create a Google Doc". Verify (via logs) that `refresh_if_expiring` posts to `/token` exactly once and the doc is created with the new bearer token.
4. Click Disconnect in the UI. Verify (via logs and a network capture) that the backend posts to `oauth2.googleapis.com/revoke` and the row is removed from `integration_credentials`. Subsequent agent tool calls return "Google authentication required" (not stale 401).
</verification>

<success_criteria>
- `app/services/google_workspace_token_refresh.py` exists, exports `refresh_if_expiring`, uses `httpx.Client` (sync) — NOT `httpx.AsyncClient`.
- `_is_expiring_soon` correctly handles None / unparseable / naive-datetime / future-by-minutes inputs.
- All 7 tool helpers (docs, gmail, google_sheets, calendar_tool, forms, gmail_inbox, briefing_tools.approve_draft inline read; document_editor verified-no-op) call `refresh_if_expiring(tool_context)` before reading state.
- `GoogleWorkspaceAuthService.disconnect` posts to `https://oauth2.googleapis.com/revoke` with `application/x-www-form-urlencoded` body `token={access_token}` BEFORE deleting rows; revoke failure does NOT prevent deletion.
- 12 new pytest tests GREEN (8 in test_workspace_token_refresh.py + 4 in TestDisconnectRevoke).
- No regressions: `uv run pytest tests/unit/ -x` clean.
- Lint: `ruff check`, `ruff format`, `ty check` clean on all 10 modified files.
- Hybrid sync-refresh deviation from literal WORKSPACE-04 wording (which says "calls IntegrationManager.get_valid_token") is documented in 102-CONTEXT and restated in this plan's SUMMARY.
</success_criteria>

<output>
After completion, create `.planning/phases/102-google-workspace-credential-bridge/102-02-token-refresh-and-disconnect-revoke-SUMMARY.md` documenting:
- New module path + line counts
- Exact list of which tool helper files were modified, including whether `document_editor.py` was actually edited or left as-is (per RESEARCH section 1.8 "referenced in docstring" — confirm via grep)
- Test count delta (existing N -> existing N + 12 GREEN)
- Confirmation that the hybrid sync-refresh model (Approach C from RESEARCH) is what was implemented; literal call to async `IntegrationManager.get_valid_token` was NOT made (deviation locked in 102-CONTEXT)
- Any unexpected refactors needed in the helpers (should be ZERO — this should be one-line additions)
- Whether `GOOGLE_WORKSPACE_PROVIDER` constant existed already or had to be added
</output>
