---
phase: 56-gdpr-rag-hardening
plan: "01"
subsystem: auth
tags: [gdpr, privacy, export, supabase, fastapi, nextjs, json-archive]

# Dependency graph
requires:
  - phase: 55-integration-quality-load-testing
    provides: stable integration layer that is the source of integration_credentials data included in the export
provides:
  - PersonalDataExportService: backend-owned export bundle covering 14 user-data domains with recursive secret redaction
  - POST /account/export: authenticated export endpoint returning signed 24h download URL
  - Settings Data & Privacy section: user-facing export CTA with loading/success/error states
affects: [56-02-deletion-hardening, privacy, account, settings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backend-owned export bundle: service gathers all user-scoped tables, redacts secrets recursively, uploads JSON to Supabase Storage, returns signed URL"
    - "SENSITIVE_KEYWORDS tuple drives recursive redaction: any dict key matching token/secret/api_key/apikey/password/private_key/authorization/credential is redacted"
    - "is_sensitive config row detection: config_value redacted when is_sensitive=True or config_key matches sensitive keywords"
    - "sync_cursor always redacted in integration_sync_state to prevent opaque cursor leakage"
    - "Non-fatal export warnings: per-section try/except logs warning and continues rather than failing the archive"
    - "Router test isolation: stub app.routers.onboarding before account router import to bypass 4-level deep service/personas/supabase chain"

key-files:
  created:
    - app/services/personal_data_export_service.py
    - tests/unit/services/test_personal_data_export_service.py
    - tests/unit/app/routers/test_account_router.py
  modified:
    - app/routers/account.py
    - frontend/src/app/settings/page.tsx

key-decisions:
  - "JSON-only archive format (not CSV): single downloadable file covering all sections is simpler for users and easier to audit for secrets"
  - "Recursive _redact_sensitive_data covers nested dicts and lists: session_events.event_data.access_token and similar nested secrets are always caught"
  - "stub app.routers.onboarding (not app.app_utils.auth) for router tests: stubs only the re-export point so account.py import chain is minimal"
  - "Auth-gate test uses real get_current_user_id via dependency_overrides on the stub function: proves HTTPBearer gate fires without reloading the router"

patterns-established:
  - "PersonalDataExportService(user_id): construct per-request, _safe_query_rows/_safe_query_one for all table reads"
  - "Per-section warning accumulation: _record_warning appends to self._warnings for manifest inclusion"

requirements-completed: [GDPR-01]

# Metrics
duration: 20min
completed: 2026-04-11
---

# Phase 56 Plan 01: Personal Data Export Summary

**Self-service GDPR export delivering a signed JSON archive across 14 user-data domains with recursive OAuth-token and API-key redaction, backed by 8 regression tests**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-11T13:03:00Z
- **Completed:** 2026-04-11T13:23:31Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `PersonalDataExportService` gathers account metadata, sessions, initiatives, workflows, content bundles, vault documents, sales, finance, operations, support, people, compliance, integrations, and configuration into one signed JSON archive
- Recursive `_redact_sensitive_data` ensures OAuth tokens, refresh tokens, API keys, encrypted credential blobs, and sensitive config values never appear in the export
- `POST /account/export` authenticated endpoint on the account router returns a 24h signed download URL; service errors map to HTTP 500 without leaking internals
- Settings "Data & Privacy" section gives users a clear export CTA beside delete-account controls, with honest disclosure that secrets are excluded

## Task Commits

Each task was committed atomically:

1. **Task 1: Build PersonalDataExportService** - `61ebefff` (feat)
2. **Task 2: Add authenticated account export endpoint** - `db72b2ec` (feat)
3. **Task 3: Wire Settings privacy surface** - `a72fe535` (feat)

## Files Created/Modified
- `app/services/personal_data_export_service.py` - PersonalDataExportService: 14-domain archive builder, recursive redaction, signed URL upload
- `tests/unit/services/test_personal_data_export_service.py` - 3 tests: redaction rules, empty-section safety, upload/sign pipeline
- `app/routers/account.py` - Added PersonalDataExportResponse model and POST /account/export route
- `tests/unit/app/routers/test_account_router.py` - 5 router tests: authenticated success, response contract, user scoping, service error → 500, auth gate → 401/403
- `frontend/src/app/settings/page.tsx` - Data & Privacy section with export CTA, loading/success/error states, download link

## Decisions Made
- JSON archive format chosen over CSV: a single file covering all sections is simpler to audit for secrets and easier for users to store
- Recursive redaction covers nested structures (e.g. `session_events.event_data.access_token`) to catch secrets regardless of nesting depth
- `stub app.routers.onboarding` pattern for router tests avoids the 4-level import chain (onboarding → user_onboarding_service → user_agent_factory → personas) while still allowing auth-gate test to use the real `get_current_user_id` via `dependency_overrides`

## Deviations from Plan

None - plan executed exactly as written. All three files were implemented matching the plan's artifact spec and all verifications pass.

## Issues Encountered

- **Router test import chain**: `app.routers.account` imports `get_current_user_id` from `app.routers.onboarding`, which pulls in a 4-level chain ending at `app.personas` (which requires the full Supabase client). Fixed by stubbing `app.routers.onboarding` before the router is imported, then using a `dependency_overrides` trick to inject the real `get_current_user_id` for the auth-gate test only. No plan deviation — purely test isolation.

## User Setup Required

None - no external service configuration required. The export writes to the existing `generated-documents` Supabase Storage bucket that `DataExportService` already uses.

## Next Phase Readiness
- Privacy export surface is complete; `56-02` can now inventory every section exported here as the scope for deletion cascade hardening
- The 14 domains enumerated in `PersonalDataExportService.build_export_payload` serve as the authoritative checklist of user-linked tables that `delete_user_account()` must cover

## Self-Check: PASSED

All 6 expected files present. All 3 task commits verified in git log.

---
*Phase: 56-gdpr-rag-hardening*
*Completed: 2026-04-11*
