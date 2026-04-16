---
phase: 55-integration-quality-load-testing
plan: "01"
subsystem: oauth-lifecycle-truthfulness
tags: [backend, frontend, oauth, integrations, google-workspace]

requires: [54-02]

provides:
  - Generic integration disconnect now clears stale sync-state residue and no longer reports disconnected providers as sync errors
  - Google Workspace has a backend-owned disconnect path that clears reusable stored rows and suppresses legacy fallback credentials until reconnect
  - Configuration UI now exposes a verified Google Workspace disconnect action without exposing tokens in the browser

affects:
  - app/services/integration_manager.py
  - app/services/google_workspace_auth_service.py
  - app/routers/configuration.py
  - frontend/src/app/dashboard/configuration/page.tsx
  - tests/unit/test_integration_manager.py
  - tests/unit/app/test_google_workspace_auth_service.py

tech-stack:
  added: []
  patterns:
    - "disconnect lifecycle cleanup clears credential and sync-state residue together"
    - "explicit disconnect marker suppresses legacy Google refresh-token fallbacks until callback sync clears it"
    - "configuration UI uses backend-owned disconnect endpoints rather than handling secrets in the browser"

requirements-completed: [INTG-01]

completed: 2026-04-11
---

# Phase 55 Plan 01: OAuth Lifecycle Truthfulness Summary

Completed the first Phase 55 slice by making disconnect and reconnect state truthful for both generic integrations and Google Workspace.

## Accomplishments

- Updated `app/services/integration_manager.py` so provider disconnect now clears both:
  - `integration_credentials`
  - matching `integration_sync_state`
- Hardened aggregated integration status so a disconnected provider no longer surfaces an old sync error state just because stale sync metadata exists
- Added a canonical `disconnect()` lifecycle to `app/services/google_workspace_auth_service.py` that:
  - removes reusable Google Workspace rows from canonical and legacy token stores
  - clears Google Workspace sync-state residue
  - records an explicit disconnect marker so legacy refresh-token fallbacks do not keep the integration falsely connected after the user disconnects
- Added `DELETE /configuration/google-workspace` in `app/routers/configuration.py` so Google Workspace disconnect stays backend-owned
- Updated `frontend/src/app/dashboard/configuration/page.tsx` so the connected Google Workspace card now exposes a disconnect action and refreshes truthful status after completion
- Added regression coverage in:
  - `tests/unit/test_integration_manager.py`
  - `tests/unit/app/test_google_workspace_auth_service.py`

## Verification

- `uv run pytest tests/unit/test_integration_manager.py tests/unit/app/test_google_workspace_auth_service.py -x` passed
- `cd frontend && .\node_modules\.bin\tsc.cmd --noEmit` passed

## Deviations From Plan

- Google Workspace disconnect needed one extra guard beyond simple row deletion: an explicit disconnect marker in `user_configurations`. Without that marker, legacy refresh-token fallbacks could still make the UI report Google Workspace as connected after a user intentionally disconnected it.
- Generic integration truthfulness also needed a status-layer correction so stale sync errors only count when usable credentials still exist. This keeps already-disconnected providers from showing misleading error state even before cleanup reaches every older row.

## Next Phase Readiness

- `55-01` is complete
- `55-02` is now the next live Phase 55 slice: SSE multi-user isolation regression coverage and guardrails

## Self-Check: PASSED

Disconnect and reconnect state is now truthful for the targeted integration paths, Google Workspace disconnect remains server-owned, and focused regression coverage protects the new contract.
