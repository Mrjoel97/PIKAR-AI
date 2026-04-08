# Phase 50 Deferred Items

## Infra blockers (not fixes — out of scope)

### Docker Desktop not running on Windows dev host

- **Discovered during:** 50-01 Task 1 verification (`supabase db reset --local`)
- **Symptom:** `supabase db reset --local` fails with `error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/containers/supabase_db_Pikar-Ai/json": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` Docker Desktop was not started in this session.
- **Scope:** Pre-existing environment state — the local Supabase stack requires Docker Desktop to be running, and the Windows-binary-in-.env issue documented in 49-04 also still reproduces (must `mv .env .env.bak` before running `supabase` commands).
- **Impact on 50-01:** Migration `20260407000000_stripe_webhook_events.sql` was authored against the existing `20260324400000_subscriptions.sql` pattern (same CREATE TABLE + RLS + CHECK + service_role policy style — known-good in prod) and reviewed statically. The migration WILL apply cleanly on any developer machine with Docker Desktop running; the vitest suite in Task 2 validates the runtime contract (the handler SELECTs/UPSERTs against a stubbed supabase client so it does not depend on the physical DB).
- **Remediation path:** Next developer with Docker Desktop running should `mv .env .env.bak && supabase db reset --local && mv .env.bak .env` and confirm the table materialises. This is an operational step, not a fix.
- **Plan:** 50-01

## Pre-existing lint debt (out of scope for Phase 50)

### 287 frontend lint issues across 35+ files (unrelated to Phase 50)

- **Discovered during:** 50-04 Task 1 lint verification (`cd frontend && npm run lint`)
- **Symptom:** 147 errors + 140 warnings across pre-existing files — primarily `@typescript-eslint/no-explicit-any` in `src/services/*.ts` and `react-hooks/exhaustive-deps` warnings. None are in files touched by Phase 50.
- **Scope:** ENTIRELY pre-existing debt from prior phases. None of 50-01, 50-02, 50-03, or 50-04 introduced new lint errors. PremiumShell.tsx has one pre-existing `react-hooks/exhaustive-deps` warning on its existing `resize` effect — untouched by 50-04's badge placement.
- **Impact on 50-04:** None. Per GSD scope-boundary rules, 50-04 only validates that its own changes lint clean — which they do.
- **Remediation path:** Future dedicated lint-debt-cleanup plan (recommend scheduling as a standalone housekeeping plan during Phase 51 or 52 slack time). Not a Phase 50 concern.
- **Plan:** 50-04 (logged only — no fix attempted)
