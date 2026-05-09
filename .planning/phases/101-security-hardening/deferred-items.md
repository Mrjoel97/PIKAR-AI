# Phase 101 Deferred Items

Out-of-scope discoveries during 101-01 execution. Logged here per the GSD scope-boundary rule (only auto-fix issues directly caused by current task changes).

## Pre-existing test collection failures

### `tests/unit/test_workflow_template_tool_resolution.py`

**Status:** Cannot be collected — `ModuleNotFoundError: No module named 'scripts.verify'`.

**Symptom:** `from scripts.verify.validate_workflow_templates import validate_templates` fails because `scripts/verify/` lacks an `__init__.py` AND has no `tests/unit/.../conftest.py` that adds the repo root to `sys.path` early enough for the import. Same root cause as the 101-01 backfill-test issue, but with a different scoping problem (`scripts.verify` is one level deeper than the top-level `scripts.migrate_*`).

**Why deferred:** This file existed and was broken BEFORE phase 101-01 started (verified — the import statement is in commit 861a2bc9 already). Not caused by 101-01 work, so out of scope per `<deviation_rules>` SCOPE BOUNDARY.

**Suggested fix (for a future cleanup phase):** Either move the script content under `app/` or add a top-level `conftest.py` that ensures the project root is on `sys.path`.

## Local Supabase verification gate

**Status:** `supabase db reset --local` cannot run in this environment because Docker Desktop is not running.

**What was verified statically:**
- `supabase/migrations/20260509000000_phase101_verify_connected_accounts_rls.sql` body is byte-for-byte identical to `20260415113000_harden_connected_accounts_rls.sql` (verified via `diff` skipping the comment headers).
- All `CREATE POLICY` statements are preceded by `DROP POLICY IF EXISTS` (idempotent re-application is safe).

**What needs runtime verification (next environment with Docker):**
- `supabase db reset --local` end-to-end success.
- `pg_policy` query returning exactly 5 policies on `public.connected_accounts` post-apply.
- `tests/integration/test_connected_accounts_rls.py` PASSING (currently SKIPS).
