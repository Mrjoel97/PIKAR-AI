# Phase 50 Deferred Items

## Infra blockers (not fixes — out of scope)

### Docker Desktop not running on Windows dev host

- **Discovered during:** 50-01 Task 1 verification (`supabase db reset --local`)
- **Symptom:** `supabase db reset --local` fails with `error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/containers/supabase_db_Pikar-Ai/json": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` Docker Desktop was not started in this session.
- **Scope:** Pre-existing environment state — the local Supabase stack requires Docker Desktop to be running, and the Windows-binary-in-.env issue documented in 49-04 also still reproduces (must `mv .env .env.bak` before running `supabase` commands).
- **Impact on 50-01:** Migration `20260407000000_stripe_webhook_events.sql` was authored against the existing `20260324400000_subscriptions.sql` pattern (same CREATE TABLE + RLS + CHECK + service_role policy style — known-good in prod) and reviewed statically. The migration WILL apply cleanly on any developer machine with Docker Desktop running; the vitest suite in Task 2 validates the runtime contract (the handler SELECTs/UPSERTs against a stubbed supabase client so it does not depend on the physical DB).
- **Remediation path:** Next developer with Docker Desktop running should `mv .env .env.bak && supabase db reset --local && mv .env.bak .env` and confirm the table materialises. This is an operational step, not a fix.
- **Plan:** 50-01
