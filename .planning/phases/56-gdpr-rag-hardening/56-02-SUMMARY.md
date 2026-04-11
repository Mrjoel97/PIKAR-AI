---
phase: 56-gdpr-rag-hardening
plan: "02"
subsystem: auth
tags: [gdpr, privacy, deletion, anonymization, supabase, fastapi, nextjs]

# Dependency graph
requires:
  - phase: 56-01
    provides: 14-domain inventory that is the authoritative checklist for deletion cascade scope
provides:
  - delete_user_account: hardened SQL function covering 40+ user-linked tables added after March 2026
  - governance_audit_log anonymization: actor identity removed, action trail preserved for compliance
  - 36 automated tests: cascade coverage proof + audit anonymization contract + router deletion paths
affects: [56-03-vault-auth, privacy, account, settings, governance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anonymize-not-delete pattern: governance_audit_log user_id set to sentinel UUID '00000000-0000-0000-0000-000000000000', ip_address set to NULL; rows survive with action trail intact"
    - "Sentinel UUID for anonymization: well-known deleted-user placeholder so governance viewer enrichment gracefully returns not-found instead of crashing"
    - "SQL function hardening: GROUP 6 block in delete_user_account() covers all post-March-2026 tables (braindump, marketing, integrations, action history, alerts, etc.)"
    - "Context manager test pattern _DeleteAppContext: keeps get_service_client patch active across the TestClient lifetime so RPC mock is properly intercepted"
    - "Migration-as-SQL-source-of-truth testing: integration tests parse the migration file to assert table coverage rather than mocking DB state"

key-files:
  created:
    - supabase/migrations/20260411153000_gdpr_deletion_hardening.sql
    - tests/integration/test_account_deletion_cascade.py
  modified:
    - app/routers/account.py
    - frontend/src/app/settings/page.tsx
    - tests/unit/app/routers/test_account_router.py

key-decisions:
  - "Anonymize governance_audit_log rather than delete: rows serve compliance audit trail; actor identity removed via sentinel UUID + NULL ip_address so viewer enrichment fails gracefully"
  - "Sentinel UUID '00000000-0000-0000-0000-000000000000' chosen over NULL: governance_audit_log.user_id is NOT NULL so altering the column or NULLing would require a schema change; sentinel is safe and unambiguous"
  - "approval_chains deleted (not anonymized): these are pending approval workflows owned by the user, not shared compliance records; deleting is correct"
  - "Test integration tests parse migration SQL: proves coverage at the file level without requiring a live DB, making the tests runnable in CI with no Supabase instance"
  - "Fix Rule 1 Bug inline: privacy@pikar.ai typo in 500 error detail corrected to privacy@pikar-ai.com to match canonical contact used everywhere else"

requirements-completed: [GDPR-02, GDPR-03]

# Metrics
duration: 15min
completed: 2026-04-11
---

# Phase 56 Plan 02: Deletion Cascade Hardening Summary

**Hardened `delete_user_account()` against the current schema with governance audit anonymization, covering 40+ user-linked tables added after the March 2026 migration, proven by 36 automated tests**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-11T13:31:09Z
- **Completed:** 2026-04-11T13:45:52Z
- **Tasks:** 3
- **Files modified:** 4 (1 SQL migration, 1 Python router, 1 TypeScript page, 2 test files)

## Accomplishments

- `supabase/migrations/20260411153000_gdpr_deletion_hardening.sql` replaces `delete_user_account()` with a hardened version that covers all tables added between March 2026 and April 2026, organized into 6 groups
- `governance_audit_log` rows are anonymized rather than deleted: `user_id` → sentinel UUID, `ip_address` → NULL; the action trail (action_type, resource_type, resource_id, details) is preserved intact
- `approval_chains` (no FK to auth.users) is explicitly deleted; `approval_chain_steps` cascades automatically
- `subscriptions`, `onboarding_drip_emails`, `onboarding_checklist`, `app_projects`, `metric_baselines` — all tables with no FK constraint — are now covered
- `data_deletion_requests` audit trail behavior is unchanged (ON DELETE SET NULL means the row survives auth.users deletion)
- 36 tests prove cascade coverage, anonymization contract, audit trail preservation, and router success/failure/auth paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Refresh DB deletion function + RED/GREEN integration tests** — `ff6c374b` (feat)
2. **Task 2: Router-level deletion unit tests** — `48bc97ad` (test)
3. **Task 3: Deletion UX and response copy truthfulness** — `6fdf1255` (feat)

## Files Created/Modified

- `supabase/migrations/20260411153000_gdpr_deletion_hardening.sql` — Hardened `delete_user_account()`: Group 6 adds 20+ post-March tables, Step 0 anonymizes governance_audit_log with sentinel UUID
- `tests/integration/test_account_deletion_cascade.py` — 30 tests: migration SQL coverage assertions, anonymization contract, simulated post-deletion state, data_deletion_requests preservation
- `tests/unit/app/routers/test_account_router.py` — Added 6 deletion tests: success path, response contract, user-scoped RPC, DB failure → 500, privacy contact in error, auth gate
- `app/routers/account.py` — Updated `DeleteAccountResponse` message to truthfully describe anonymization; fixed `privacy@pikar.ai` → `privacy@pikar-ai.com` typo in 500 detail
- `frontend/src/app/settings/page.tsx` — Modal warning and Danger Zone description updated to disclose that compliance audit records are anonymized (not deleted)

## Decisions Made

- Anonymize-not-delete for governance_audit_log: the admin governance viewer reads these rows and enriches them with actor emails; after deletion the viewer receives a graceful "not found" rather than a crash or a row with a dangling identity reference
- Sentinel UUID chosen over schema ALTER: governance_audit_log.user_id is `NOT NULL`, so NULLing would require altering the column definition; the sentinel `00000000-0000-0000-0000-000000000000` is unambiguous to any code that checks it and avoids a column-type migration
- Migration-as-truth-source testing: the integration tests assert the migration SQL file directly rather than spinning up a Supabase instance, keeping all 36 tests runnable in zero-infrastructure CI

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed inconsistent privacy contact email in account router 500 detail**
- **Found during:** Task 2 (test for privacy contact in error detail failed)
- **Issue:** `app/routers/account.py` used `privacy@pikar.ai` (missing hyphen) while `settings/page.tsx` and the plan consistently use `privacy@pikar-ai.com`
- **Fix:** Updated the 500 detail string to `privacy@pikar-ai.com`
- **Files modified:** `app/routers/account.py`
- **Commit:** `48bc97ad`

## Next Phase Readiness

- Deletion cascade is now schema-accurate and proven; `56-03` can proceed to Knowledge Vault auth + ingestion correctness
- The sentinel UUID anonymization pattern for governance_audit_log is documented and reusable for any future tables that must survive account deletion with identity removed

## Self-Check: PASSED

All 4 expected files present. All 3 task commits verified in git log (ff6c374b, 48bc97ad, 6fdf1255).

---
*Phase: 56-gdpr-rag-hardening*
*Completed: 2026-04-11*
