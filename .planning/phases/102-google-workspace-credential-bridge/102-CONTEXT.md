# Phase 102 Context: Google Workspace Credential Bridge

**Created:** 2026-05-08
**Phase:** 102-google-workspace-credential-bridge
**Plans:** 3 (102-01, 102-02, 102-03)
**Source of truth:** [`102-RESEARCH.md`](./102-RESEARCH.md) (verified 2026-05-08; 9 readers / 0 writers gap of `tool_context.state["google_provider_token"]`)

---

## Goal

Wire the existing per-user Google Workspace credential store (`integration_credentials` + `GoogleWorkspaceAuthService`) to the existing 9 tool helpers that read `tool_context.state["google_provider_token"]`. Today the bridge is broken — the readers exist, the storage exists, the OAuth router exists, but **no code path writes the state value**. This phase adds (1) the registry entry, (2) the bridge function in the model callback, (3) per-helper auto-refresh, (4) revoke-on-disconnect, (5) the frontend Connect card, and (6) env-var docs + startup WARN.

This is the **load-bearing** phase of v13.0: until it ships, every Google Workspace tool fails for users who connected via the new per-integration OAuth flow rather than the legacy Supabase Auth Google identity.

## Locked decisions (from RESEARCH.md)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Hybrid sync-refresh model** (Approach C) for WORKSPACE-04: bridge writes `expires_at` to state; per-helper sync `refresh_if_expiring` runs `httpx.Client` token exchange when within 5 min of expiry | `before_model_callback` is sync (verified via adk.dev); `IntegrationManager.get_valid_token` is async; `asyncio.run` inside a running event loop raises `RuntimeError`. Hybrid satisfies the SUCCESS CRITERION (auto-refresh < 5 min) without rewriting 7 helpers + 30 tool functions to async. |
| 2 | **Module-scope import strategy** in `context_extractor.py`: import `get_google_workspace_auth_service` at module top so test patches have a single stable target | Matches the pattern used by Plan 89-01 for `ingest_document_content` (module-scope import → patch at consumer's module). |
| 3 | **Session-scoped sentinel** `_GOOGLE_WORKSPACE_LOADED_KEY` to amortize cred resolution across the ~25 `before_model_callback` invocations per turn | Mirrors `_BRAND_PROFILE_LOADED_KEY` pattern at `context_extractor.py:37`. Trade-off accepted: mid-session disconnect leaves stale token in state; tool helpers will 401 → user reconnects (acceptable degradation per RESEARCH §Risk 6). |
| 4 | **Frontend disconnect routes to `/configuration/google-workspace` DELETE endpoint** (not the generic `/integrations/{provider}` path) so revoke happens before row deletion | Generic `IntegrationManager.delete_credentials` does NOT call revoke; pushing Google-specific logic into it would mix provider-specific code into a generic manager. Cleaner to keep revoke in `GoogleWorkspaceAuthService.disconnect`. |
| 5 | **Scope set:** `documents`, `spreadsheets`, `drive.file`, `gmail.send`, `gmail.readonly`, `calendar`, `forms.body`, `userinfo.email` | Verified via Google identity docs. `drive.file` (non-sensitive) preferred over `drive`. `gmail.readonly` is a restricted scope — see Open Question 1. |
| 6 | **`allow_legacy_fallback=True`** on the bridge call so users connected via the OLD Supabase Auth Google identity continue working during migration | Disconnect marker (`_is_explicitly_disconnected`) blocks fallbacks once user disconnects. Eventually flip to `False` after Phase 102 ships and users have re-connected. |

## Deferred ideas

| Idea | Why deferred |
|------|--------------|
| One-time migration of legacy `user_google_tokens` rows into `integration_credentials` | Out of scope for v13.0 first-ship; legacy users get 401 on token expiry → re-connect via new flow (RESEARCH §Risk 4). |
| Forced re-consent on scope drift | RESEARCH §Pitfall 6 — out of scope for v13.0; revisit if scopes are added post-launch. |
| Full async conversion of tool helpers (Approach B) | Would touch ~30 tool functions; rejected in favor of hybrid sync-refresh. |
| Calling `IntegrationManager.get_valid_token` literally from helpers | Async/sync boundary makes this infeasible without `run_coroutine_threadsafe`. Hybrid satisfies the success criterion (auto-refresh < 5 min); literal API compliance is sacrificed for shippability. **Document this deviation in 102-02 SUMMARY.** |

## Open questions (resolve during execution or before ship)

| # | Question | Default |
|---|----------|---------|
| 1 | Is the Pikar AI OAuth project verified by Google for `gmail.readonly` (restricted scope)? If not, requesting it triggers the unverified-app warning. | **Default:** include `gmail.readonly` in registry. If verification status is unknown, planner should ship with `gmail.send` only and add `gmail.readonly` after verification completes. Decision lives in 102-01 Task 1. |
| 2 | Are `GOOGLE_CLIENT_ID` (legacy Supabase Auth + YouTube) and `GOOGLE_WORKSPACE_CLIENT_ID` the **same** OAuth client in Google Cloud Console, or separate? | **Default:** separate (allows independent scope grants and disconnects). Document the chosen convention in `.env.example`. |
| 3 | Which OAuth refresh token rotation policy is in effect for this Google Cloud project? | **Default:** the sync refresh helper falls back to the old `refresh_token` if the response omits a new one (mirrors `IntegrationManager._refresh_token` at `integration_manager.py:259-260`). |

## Plan decomposition (3 plans, sequential dependencies)

```
102-01 (wave 1) ──▶ 102-02 (wave 2) ──▶ 102-03 (wave 3)
   │                    │                     │
   │                    │                     └─ Frontend Connect card + disconnect button
   │                    └─ Per-helper sync refresh + disconnect-revoke
   └─ Provider registry + bridge function + .env.example + startup WARN
```

| Plan | Requirements | Files | TDD |
|------|--------------|-------|-----|
| **102-01** Provider registry + bridge function + env vars | WORKSPACE-02, WORKSPACE-03, WORKSPACE-06 | `app/config/integration_providers.py`, `app/agents/context_extractor.py`, `.env.example`, `app/integrations/google/client.py` (or new module) for startup WARN, plus 3 new test files | Test-first for bridge function and startup WARN |
| **102-02** Token refresh helper + disconnect-revoke + 7 helpers | WORKSPACE-04, WORKSPACE-05 | `app/services/google_workspace_token_refresh.py` (NEW), `app/services/google_workspace_auth_service.py`, `app/agents/tools/{docs,gmail,google_sheets,calendar_tool,forms,gmail_inbox,briefing_tools}.py`, plus 2 new/extended test files | Test-first for refresh helper and disconnect-revoke |
| **102-03** Frontend Connect/Disconnect card | WORKSPACE-01 | `frontend/src/app/dashboard/configuration/page.tsx`, `frontend/src/services/integrations.ts`, plus 1 new test file | vitest unit test for connect button + postMessage listener |

## Verification map (per RESEARCH §Validation Architecture)

| Req | Test file | Command |
|-----|-----------|---------|
| WORKSPACE-02 | `tests/unit/test_integration_providers.py` (NEW) | `uv run pytest tests/unit/test_integration_providers.py::test_google_workspace_registered -x` |
| WORKSPACE-03 | `tests/unit/test_workspace_bridge.py` (NEW) | `uv run pytest tests/unit/test_workspace_bridge.py -x` |
| WORKSPACE-04 | `tests/unit/test_workspace_token_refresh.py` (NEW) | `uv run pytest tests/unit/test_workspace_token_refresh.py -x` |
| WORKSPACE-05 | `tests/unit/test_google_workspace_auth_service.py` (extend) | `uv run pytest tests/unit/test_google_workspace_auth_service.py::TestDisconnectRevoke -x` |
| WORKSPACE-06 | `tests/unit/test_settings_validation.py` (NEW) | `uv run pytest tests/unit/test_settings_validation.py::test_workspace_env_warn -x` |
| WORKSPACE-01 | `frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx` (NEW) | `cd frontend && npm test -- ConfigurationPage` |

**Phase gate (manual smoke):** `make local-backend` → connect Google Workspace via the new card → ask agent "create a Google Doc titled 'Phase 102 smoke test'" → doc URL appears in chat → opening URL shows the doc in the connecting user's Drive. Disconnect → ask again → expect "Google authentication required" error (not stale-401).

## Dependencies

- **Hard:** Phase 101 (Fernet token storage at rest, durable Redis-backed PKCE state). 102 PLANNING does not depend on 101 plans existing on disk; 102 EXECUTION does.
- **Soft:** none. Bridge function, refresh helper, and frontend can be planned in parallel waves but execute sequentially because 102-02 tests need 102-01's bridge to populate state, and 102-03 frontend needs 102-01's `PROVIDER_REGISTRY` entry for `/integrations/google_workspace/authorize` to work.
