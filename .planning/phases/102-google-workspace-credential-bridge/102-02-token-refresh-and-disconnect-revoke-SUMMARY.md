---
phase: 102-google-workspace-credential-bridge
plan: 02
subsystem: agents/credential-bridge
tags: [google-workspace, oauth, token-refresh, disconnect, revoke, tdd]
requirements: [WORKSPACE-04, WORKSPACE-05]
dependency_graph:
  requires:
    - 102-01 (provider registry + before_model_callback bridge populates state["google_provider_token"], state["google_refresh_token"], state["google_token_expires_at"])
  provides:
    - "Sync refresh_if_expiring(tool_context) helper for in-flight token refresh"
    - "GoogleWorkspaceAuthService.disconnect() that revokes at Google before deleting local rows"
  affects:
    - "All 7 Google Workspace tool helpers (docs, gmail, sheets, calendar, forms, gmail_inbox, briefing)"
    - "Configuration router /configuration/google-workspace DELETE (uses disconnect)"
tech_stack:
  added: []
  patterns:
    - "Sync httpx.Client mirror of async IntegrationManager._refresh_token (Approach C from RESEARCH)"
    - "Best-effort point-of-use refresh (silent no-op on missing user_id, refresh token, env, expiry, or network failure)"
    - "Best-effort revoke before delete (revoke failure does NOT block local cleanup)"
key_files:
  created:
    - "app/services/google_workspace_token_refresh.py (124 lines)"
    - "tests/unit/test_workspace_token_refresh.py (273 lines, 8 tests)"
  modified:
    - "app/services/google_workspace_auth_service.py (+47/-9, added httpx import + revoke logic in disconnect)"
    - "app/agents/tools/docs.py (_get_docs_service: +2)"
    - "app/agents/tools/gmail.py (_get_gmail_service: +2)"
    - "app/agents/tools/google_sheets.py (_get_sheets_service: +2)"
    - "app/agents/tools/calendar_tool.py (_get_calendar_service: +2; ruff also reformatted untouched lines)"
    - "app/agents/tools/forms.py (_get_forms_service: +2)"
    - "app/agents/tools/gmail_inbox.py (_get_gmail_reader: +2)"
    - "app/agents/tools/briefing_tools.py (approve_draft inline read: +2)"
    - "tests/unit/app/test_google_workspace_auth_service.py (+162, 4 new tests in TestDisconnectRevoke)"
decisions:
  - "Hybrid sync-refresh model (Approach C from 102-RESEARCH): refresh_if_expiring uses httpx.Client (sync) to avoid the async/sync boundary the tool helpers and before_model_callback live on. Literal call to async IntegrationManager.get_valid_token (WORKSPACE-04 wording) was NOT made — locked in 102-CONTEXT and restated here."
  - "5-minute expiry threshold matches IntegrationManager pattern; configurable via threshold_minutes kwarg for future tuning."
  - "Revoke is best-effort: a failed revoke logs WARNING but proceeds to delete local rows so users never get stuck half-disconnected."
  - "document_editor.py was confirmed (via grep) to reference google_provider_token only in a docstring at line 1027 — no code wiring needed."
metrics:
  tasks_completed: 3
  tests_added: 12
  tests_passing_before: 11
  tests_passing_after: 23
  files_created: 2
  files_modified: 9
  duration_minutes: 8
  completed_date: 2026-05-09
---

# Phase 102 Plan 02: Token Refresh + Disconnect Revoke Summary

Synchronous Google OAuth token auto-refresh wired into 7 tool helpers, plus revoke-at-Google on disconnect — completing the credential lifecycle without rewriting in-flight tool code to async.

## Tasks Completed

### Task 1 — Add failing tests (RED) — commit `1db9e340`

Created `tests/unit/test_workspace_token_refresh.py` with **8 tests** in `TestRefreshIfExpiring`:

1. `test_refresh_when_expiring` — fires HTTP POST when expiry < 5 min, updates state, persists via `sync_credentials`
2. `test_no_op_when_token_fresh` — expiry > 5 min: no HTTP call, state unchanged
3. `test_no_op_when_expires_at_none` — legacy fallback: no HTTP call
4. `test_no_op_when_no_user_id` — anonymous context: no HTTP call
5. `test_no_op_when_no_refresh_token` — refresh token absent: no HTTP call
6. `test_no_op_when_env_unconfigured` — no `GOOGLE_WORKSPACE_CLIENT_ID`: no HTTP call
7. `test_refresh_token_rotation_fallback` — response omits `refresh_token`: keep old one
8. `test_refresh_failure_is_best_effort` — network error logs WARNING, no exception bubbles

Extended `tests/unit/app/test_google_workspace_auth_service.py` with **4 tests** in `TestDisconnectRevoke`:

1. `test_disconnect_revokes_then_deletes` — POST `https://oauth2.googleapis.com/revoke` with `{token: <access>}`, form-encoded headers, then runs deletes (first call against `integration_credentials`)
2. `test_disconnect_revoke_failure_still_deletes` — `httpx.RequestError` logs WARNING; deletion still runs
3. `test_disconnect_revoke_non200_logs_warning` — 400 response logs WARNING naming the status code
4. `test_disconnect_no_token_no_http_call` — no resolved token: skip HTTP, still delete + mark

All 12 tests verified RED (8 ImportError, 4 AttributeError on missing `httpx` module attribute) before implementation.

### Task 2 — Refresh helper + 7 helper wirings (GREEN) — commit `260ecf14`

Created `app/services/google_workspace_token_refresh.py` (124 lines):

- `_is_expiring_soon(expires_at_iso, *, minutes)` — handles None, unparseable, naive datetime, future-by-minutes
- `refresh_if_expiring(tool_context, *, threshold_minutes=5)` — best-effort sync refresh:
  - No-op when expiry > threshold, expiry None, no user_id, no refresh_token, no env
  - POSTs to `https://oauth2.googleapis.com/token` via `httpx.Client`
  - Mutates `tool_context.state` in place + writes through to `integration_credentials` via `sync_credentials`
  - Catches all exceptions, logs WARNING, never raises

Wired the helper as the first line of every Google Workspace tool helper:

| File | Helper | Pattern |
|------|--------|---------|
| `app/agents/tools/docs.py` | `_get_docs_service` | import + `refresh_if_expiring(tool_context)` |
| `app/agents/tools/gmail.py` | `_get_gmail_service` | import + `refresh_if_expiring(tool_context)` |
| `app/agents/tools/google_sheets.py` | `_get_sheets_service` | import + `refresh_if_expiring(tool_context)` |
| `app/agents/tools/calendar_tool.py` | `_get_calendar_service` | import + `refresh_if_expiring(tool_context)` |
| `app/agents/tools/forms.py` | `_get_forms_service` | import + `refresh_if_expiring(tool_context)` |
| `app/agents/tools/gmail_inbox.py` | `_get_gmail_reader` | import + `refresh_if_expiring(tool_context)` |
| `app/agents/tools/briefing_tools.py` | `approve_draft` (inline read) | import + `refresh_if_expiring(tool_context)` |

`document_editor.py` confirmed (via grep) to reference `google_provider_token` only in a docstring at line 1027 — **no code change needed** (matches RESEARCH §1.8 prediction).

All 8 `TestRefreshIfExpiring` tests went GREEN. No regressions in `test_calendar_tools.py`, `test_gmail_inbox_tools.py`, `test_docs_widget_emit.py`, `test_sheets_widget_emit.py`, `test_briefing_tools.py` (55 tests pass).

### Task 3 — Revoke on disconnect (GREEN) — commit `deec7740`

Modified `GoogleWorkspaceAuthService.disconnect()` in `app/services/google_workspace_auth_service.py`:

1. Added `import httpx` at module top
2. Resolves access token via `resolve_credentials()` BEFORE deletion (was already used for `had_connection` boolean; now also captured for revoke)
3. POSTs to `https://oauth2.googleapis.com/revoke` with `{token: <access_token>}`, `content-type: application/x-www-form-urlencoded`
4. Non-200 response logs WARNING with status code and truncated body
5. `httpx.RequestError` and other exceptions log WARNING but do NOT block deletion
6. Existing `_delete_rows` calls (4 tables) and `_set_disconnect_marker` preserved verbatim
7. No-token path: skips HTTP, still runs deletion + marker (idempotent)

All 4 `TestDisconnectRevoke` tests went GREEN. All 7 existing `TestGoogleWorkspaceAuthService` + 4 `TestConfigurationRouterGoogleWorkspace` tests still GREEN.

## Verification

| Check | Result |
|-------|--------|
| `tests/unit/test_workspace_token_refresh.py` | 8/8 PASS |
| `tests/unit/app/test_google_workspace_auth_service.py` | 15/15 PASS (11 existing + 4 new) |
| `test_calendar_tools.py + test_gmail_inbox_tools.py + test_docs_widget_emit.py + test_sheets_widget_emit.py + test_briefing_tools.py` | 55/55 PASS (no regressions) |
| `ruff check` (all 10 modified files) | clean |
| `ruff format` | applied (1 file reformatted, others unchanged) |
| `ty check` | unavailable in this venv (`ty` not installed); ruff acted as the type-checker proxy |

## Deviations from Plan

### Locked architectural deviation (documented in 102-CONTEXT, restated here)

**Hybrid sync-refresh model used instead of literal WORKSPACE-04 wording.** The requirement says "calls `IntegrationManager.get_valid_token`" — that method is async. The 7 tool helpers and the `before_model_callback` are sync. Rewriting them to async would touch 30+ tool functions and is rejected as too risky for v13.0. Instead, `refresh_if_expiring` mirrors the refresh logic of `IntegrationManager._refresh_token` using `httpx.Client` (sync). The success criterion (auto-refresh within 5 min, verifiable by clock-patched unit test) is satisfied.

### Auto-fixed scope drift (Rule 3 — pre-existing index state)

When committing Tasks 1 and 2, the git index already contained staged content from concurrent plans (103-02 LinkedIn webhook + 104-01 Twitter publisher). Specifically:

- Commit `1db9e340` (Task 1) also picked up: `tests/smoke/__init__.py`, `tests/smoke/test_twitter_live.py`, `tests/unit/test_twitter_publisher.py`, `tests/unit/test_social_connector_security.py` modifications
- Commit `260ecf14` (Task 2) also picked up: `app/social/connector.py`, `app/social/publisher.py`, `supabase/migrations/20260508130000_twitter_reconnect_required.sql`

These files were untouched by my edits but were already staged in the index when I began. Per the co-tenancy fence I avoided editing them; however, `git add <my-files>` lands a commit with the entire current index. The orchestrator noted that 103-02 and 104-01 were running in parallel — those plans evidently staged but did not commit their own work before 102-02 began, so my commits incorporated their staged content. The Task 3 commit (`deec7740`) was clean (only `google_workspace_auth_service.py`).

**No content modification by me** to any 103/104 file. All `refresh_if_expiring` and revoke logic is fully isolated to the 102-02 scope. Task 3's commit is the cleanest representation of the 102-02 delta.

### No other deviations

- All 7 helpers wired with one-line additions exactly as specified
- `document_editor.py` confirmed docstring-only reference (matches RESEARCH §1.8)
- `GOOGLE_WORKSPACE_PROVIDER` constant existed already (line 17) — no addition needed
- Zero unexpected refactors required

## Commits

| Hash | Message |
|------|---------|
| `1db9e340` | test(102-02): add failing tests for token refresh and disconnect-revoke (WORKSPACE-04, WORKSPACE-05) |
| `260ecf14` | feat(102-02): sync Google OAuth refresh helper + wire into 7 tool helpers (WORKSPACE-04) |
| `deec7740` | feat(102-02): revoke at Google before deleting local rows on disconnect (WORKSPACE-05) |

## Self-Check: PASSED

- `app/services/google_workspace_token_refresh.py` exists (124 lines)
- `tests/unit/test_workspace_token_refresh.py` exists (273 lines, 8 tests)
- `app/services/google_workspace_auth_service.py` modified (revoke logic in disconnect, +47/-9)
- All 7 tool helper files contain `refresh_if_expiring` import and call
- 12 new tests GREEN; 11 existing tests still GREEN; 55 regression tests still GREEN
- All 3 commits present in git log on `feat/vault-fixes-and-agent-actions`
