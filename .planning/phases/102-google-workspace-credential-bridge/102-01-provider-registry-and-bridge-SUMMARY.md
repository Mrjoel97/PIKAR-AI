---
phase: 102-google-workspace-credential-bridge
plan: 01
subsystem: integrations.google_workspace
tags: [oauth, credentials, agents, callback]
requirements: [WORKSPACE-02, WORKSPACE-03, WORKSPACE-06]
dependency_graph:
  requires:
    - app.services.google_workspace_auth_service.GoogleWorkspaceAuthService.resolve_credentials (sync)
    - app.config.integration_providers.ProviderConfig dataclass
    - app.agents.context_extractor._get_callback_user_id helper
  provides:
    - PROVIDER_REGISTRY["google_workspace"] entry with 8 OAuth scopes
    - _try_load_google_workspace_credentials helper writing state["google_provider_token"]
    - _warn_missing_google_workspace_env() startup guard
    - GOOGLE_WORKSPACE_{CLIENT_ID,CLIENT_SECRET,REDIRECT_URI} env var convention
  affects:
    - 9 existing readers of state["google_provider_token"] (docs, gmail, sheets, calendar, forms, gmail_inbox, briefing_tools, document_editor, etc.)
tech_stack:
  added: []
  patterns:
    - Sync best-effort helper invoked from before_model_callback (mirrors _try_load_brand_profile)
    - Sentinel state key for per-session idempotence (mirrors _CROSS_SESSION_LOADED_KEY)
    - Module-import-time WARN with PYTEST_CURRENT_TEST suppression
key_files:
  created:
    - tests/unit/test_integration_providers.py
    - tests/unit/test_workspace_bridge.py
    - tests/unit/test_settings_validation.py
  modified:
    - app/config/integration_providers.py
    - app/agents/context_extractor.py
    - app/integrations/google/client.py
    - .env.example
decisions:
  - Module-scope import of get_google_workspace_auth_service in context_extractor (not inline) so test patches target app.agents.context_extractor.get_google_workspace_auth_service.
  - Hybrid sync-refresh helper pattern (per 102-CONTEXT lock): the bridge calls the synchronous resolve_credentials API directly from the sync before_model_callback. No asyncio.run, no async upgrade.
  - Top-level except wraps the bridge call site so even an unexpected exception inside the helper cannot block the model call (defense-in-depth on top of helper's own try/except).
  - Kept gmail.readonly scope per the plan even though Open Question 1 in 102-CONTEXT flagged it as Restricted Scope (Google verification required). Plan author decided keep-with-followup; verification is a 102-03 concern.
metrics:
  duration_minutes: ~25
  completed: 2026-05-09
  tests_added: 11
  tests_passing: 11
---

# Phase 102 Plan 01: Provider Registry + Credential Bridge Summary

JWT-style credential bridge that resolves a connected user's encrypted Google Workspace tokens out of `integration_credentials` and injects them into the ADK `before_model_callback` state, unblocking the 9 existing readers (docs, gmail, sheets, calendar, forms, gmail_inbox, briefing_tools, document_editor) without touching any tool code.

## What Shipped

### WORKSPACE-02: Provider registry entry

`app/config/integration_providers.py` line **201**: new `"google_workspace"` entry in `PROVIDER_REGISTRY` between `google_ads` and `meta_ads`. 8 scopes, oauth2, canonical Google `auth_url`/`token_url`, env var names `GOOGLE_WORKSPACE_{CLIENT_ID,CLIENT_SECRET}`, productivity category.

Scopes locked (same set as plan):
```
documents, spreadsheets, drive.file, gmail.send,
gmail.readonly, calendar, forms.body, userinfo.email
```

### WORKSPACE-03: Credential bridge in before_model_callback

`app/agents/context_extractor.py`:

- **Line 29-31** — module-scope import:
  ```python
  from app.services.google_workspace_auth_service import (
      get_google_workspace_auth_service,
  )
  ```
- **Line 42** — sentinel constant:
  `_GOOGLE_WORKSPACE_LOADED_KEY = "_google_workspace_creds_loaded"`
- **Line 334-388** — `_try_load_google_workspace_credentials(callback_context)` helper. Mirrors `_try_load_brand_profile` pattern: sentinel-first, user-id check, sync `resolve_credentials(user_id, allow_legacy_fallback=True)`, writes `google_provider_token` / `google_refresh_token` / `google_token_expires_at` into state, swallows exceptions with debug log.
- **Line 1067-1075** — invocation inside `context_memory_before_model_callback` immediately after `_try_load_cross_session_context` (line 1062), wrapped in a top-level try/except for defense-in-depth.

Confirmed: `context_memory_before_model_callback` remains synchronous. No `asyncio.run`, no async upgrade.

### WORKSPACE-06: Startup WARN + .env.example

`app/integrations/google/client.py`:

- **Line 13-16** — moved `import os` and `import logging` to module level; added `logger = logging.getLogger(__name__)`.
- **Line 131-156** — `_warn_missing_google_workspace_env()` function. Skips when `PYTEST_CURRENT_TEST` is set. Iterates the three required env vars, emits exactly one WARN naming only the missing ones.
- **Line 158** — module-import-time call: `_warn_missing_google_workspace_env()`.

`.env.example` lines **23-32**: new commented block after `GOOGLE_API_KEY` documenting the three vars with the explicit "DIFFERENT from GOOGLE_API_KEY and GOOGLE_CLIENT_ID" callout requested by the plan.

## Tests

| File | Tests | Status |
|------|------:|:------:|
| `tests/unit/test_integration_providers.py` | 1 | GREEN |
| `tests/unit/test_workspace_bridge.py` | 6 | GREEN |
| `tests/unit/test_settings_validation.py` | 4 | GREEN |
| **Total** | **11** | **11/11 GREEN** |

Regression check on `tests/unit/app/test_google_workspace_auth_service.py` (11 tests): all passing.
Regression check on `tests/unit/agents/` (29 tests): all passing.

## Module-scope vs inline import decision

Chose **module-scope** import of `get_google_workspace_auth_service` in `context_extractor.py` per the plan's recommendation. This pins test patch targets at `app.agents.context_extractor.get_google_workspace_auth_service`, which is the consumer-module patching convention used throughout this codebase. Inline imports would have forced patches to target the producer module and made the bridge harder to mock in isolation.

## Commits

| Hash | Message |
|------|---------|
| `a1861e01` | test(102-01): add failing tests for provider registry, bridge function, and startup WARN (WORKSPACE-02, -03, -06) |
| `cb8fedb2` | feat(102-01): wire Google Workspace credential bridge in before_model_callback (WORKSPACE-02, WORKSPACE-03) |
| `335a565e` | feat(102-01): startup WARN + .env.example for Google Workspace OAuth env vars (WORKSPACE-06) |

## Deviations from Plan

### Branch / co-tenancy turbulence

The first commit (`a1861e01`, the RED test commit) **inadvertently captured pre-staged work from the parallel v12.0 session** (handoff_packet, briefing_pdf_export, sse_markdown_synthesis, summarizer_health, approval_widget, et al.). This was not a reverted commit — those changes were already staged in the working tree by another session before `git add` ran on the test files. The 3 new test files I authored were correctly included; the unrelated co-tenant changes were a side-effect of staging-area pollution. Subsequent commits (`cb8fedb2`, `335a565e`) included **only the plan's intended files** because I re-staged paths individually.

Mid-execution the branch HEAD was briefly observed on `v12.0-wave3-clean` (parallel session checked out a different branch). Re-running `git status` showed the branch back on `feat/vault-fixes-and-agent-actions` shortly after, but my Task 2 working-tree edits to `context_extractor.py` and `integration_providers.py` were lost during the swap and had to be re-applied. The re-applied edits are exactly the same as originally written; the only impact was wall-clock time.

### Auto-fixed lint issues during Task 2 (Rule 1)

`ruff check` flagged `# noqa: BLE001` directives as unused because BLE001 is not enabled in this project's ruff config. Replaced both noqa comments with inline explanatory comments. Pre-existing `I001` (unsorted imports at line 217-218) and `B007` (unused `domain` loop var at line 763) errors in unrelated parts of `context_extractor.py` were left untouched per scope-boundary rules and are documented as deferred items below.

### Removed redundant `import os` inside `get_user_gmail_credentials`

Since I moved `os` to a module-level import for `_warn_missing_google_workspace_env`, the existing inline `import os` at line 86 of `app/integrations/google/client.py` became redundant. Removed it. No behavior change.

## Deferred Items (out of scope)

- `app/agents/context_extractor.py:217-218` — pre-existing `I001` unsorted imports inside `_try_load_cross_session_context`. Not introduced by this plan.
- `app/agents/context_extractor.py:763` — pre-existing `B007` unused loop variable `domain` in `_get_routing_signals`. Not introduced by this plan.
- Pre-existing test collection errors (`tests/unit/test_tools.py` basename collision with `tests/unit/app/agents/strategic/test_tools.py`, plus 4 others). Affect full-suite collection but not targeted test runs.

## Self-Check: PASSED

- `app/config/integration_providers.py` contains `google_workspace`: FOUND (line 201)
- `app/agents/context_extractor.py` contains `_try_load_google_workspace_credentials`: FOUND (line 334)
- `app/agents/context_extractor.py` contains `_GOOGLE_WORKSPACE_LOADED_KEY`: FOUND (line 42)
- `app/integrations/google/client.py` contains `_warn_missing_google_workspace_env`: FOUND (line 131)
- `.env.example` contains `GOOGLE_WORKSPACE_CLIENT_ID`: FOUND
- `tests/unit/test_integration_providers.py`: FOUND
- `tests/unit/test_workspace_bridge.py`: FOUND
- `tests/unit/test_settings_validation.py`: FOUND
- Commit `a1861e01` (RED tests): FOUND
- Commit `cb8fedb2` (Task 2 GREEN): FOUND
- Commit `335a565e` (Task 3 GREEN): FOUND
- All 11 new tests: GREEN
- 11 existing GoogleWorkspaceAuthService tests: still GREEN (no regression)
- 29 agent callback tests: still GREEN (no regression)
