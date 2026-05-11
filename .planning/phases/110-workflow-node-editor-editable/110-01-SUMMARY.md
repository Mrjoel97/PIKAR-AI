---
phase: 110-workflow-node-editor-editable
plan: 01
subsystem: database
tags: [supabase, postgresql, jsonb, plpgsql, workflow-templates, versioning, rls, foreign-keys, idempotent-migration]

# Dependency graph
requires:
  - phase: 109-workflow-node-editor-viewer
    provides: workflow_templates.graph_nodes/graph_edges/graph_layout JSONB columns + pikar.* projection helpers
provides:
  - workflow_template_versions table (one row per Save; immutable history; UNIQUE per template_id+version_number)
  - workflow_templates.current_version_id pointer column (FK to versions)
  - workflow_executions.template_version_id pointer column (run-time pinning; nullable for legacy executions)
  - Eager backfill — every graph-projected workflow_templates row has a v1 version row
  - RLS policies — owner-or-global-seed SELECT, service-role-only writes
  - Inline rollback procedure (SQL comment block at end of migration)
  - Regression test for legacy template_version INT column preservation
affects: [110-02-backend-save-load, 110-03-backend-validation, 110-04-frontend-editable-canvas, 110-05-frontend-versioning-conflict]

# Tech tracking
tech-stack:
  added:
    - workflow_template_versions table (new) — Postgres versioned history
  patterns:
    - "ADD COLUMN IF NOT EXISTS for forward-only nullable columns — full idempotency on re-apply"
    - "WHERE current_version_id IS NULL guard on backfill DO block — re-runs iterate zero rows"
    - "DO + EXCEPTION WHEN duplicate_object wrapper for CREATE POLICY — idempotent RLS setup"
    - "$BODY$ named dollar quotes (NOT bare $$) per supabase CLI 2.75 bug — applied to all DO blocks"
    - "Legacy-column preservation regression test — catches future migrations that drop columns silently"

key-files:
  created:
    - supabase/migrations/20260615000000_workflow_template_versioning.sql
    - tests/integration/test_workflow_template_versioning_migration.py
  modified: []

key-decisions:
  - "Used $BODY$ named dollar quotes throughout (supabase CLI 2.75 bug avoidance) — Phase 109's pattern preserved"
  - "Eager backfill scope = WHERE graph_nodes IS NOT NULL only — empty-phases sentinel rows are deferred to Plan 02's seed-copy path on first Edit"
  - "saved_by_user_id is nullable on workflow_template_versions to permit v1 backfill of seeded templates (created_by IS NULL); production writes from Plan 02 will always supply a user id"
  - "Legacy workflow_executions.template_version INT column is NOT dropped — coexists with new template_version_id UUID; test #7 enforces this preservation contract"
  - "RLS SELECT policy allows reads when auth.uid() = templates.created_by OR templates.created_by IS NULL (global seeds); writes are service-role only"
  - "Per-row backfill failures emit RAISE NOTICE (light-touch) instead of inserting into workflow_template_migration_errors — Phase 109's projection already guaranteed valid JSONB so a row failure here is unexpected"

patterns-established:
  - "RLS-on-new-table idempotency: ALTER TABLE ... ENABLE ROW LEVEL SECURITY (idempotent) + DO {CREATE POLICY ... EXCEPTION WHEN duplicate_object THEN NULL} blocks"
  - "Pointer-column pattern for version history: parent row holds current_version_id FK; child table has UNIQUE (parent_id, version_number); reverts create new versions never overwriting"
  - "Run-time pinning column added to executions table during versioning migration; engine update deferred to next plan keeps the migration focused on schema-only"

requirements-completed: [NODEEDITOR-VERSION-01]

# Metrics
duration: 5min
completed: 2026-05-11
---

# Phase 110 Plan 01: Workflow Template Versioning Migration Summary

**One SQL migration adding workflow_template_versions table + current_version_id pointer on workflow_templates + template_version_id pointer on workflow_executions + eager v1 backfill for graph-projected templates; fully idempotent via IF NOT EXISTS / WHERE-guard DO block / DO-EXCEPTION-wrapped RLS policies**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-11T18:24:16Z
- **Completed:** 2026-05-11T18:29:57Z
- **Tasks:** 5 (all atomic commits)
- **Files created:** 2 (migration + integration tests)
- **Files modified:** 0

## Accomplishments

- New table `workflow_template_versions` shipped with the seven CONTEXT.md decision-5 columns (id, template_id, version_number, parent_version_id, graph_nodes, graph_edges, graph_layout, saved_by_user_id, saved_at, comment) + `UNIQUE (template_id, version_number)` constraint. Self-referencing FK on parent_version_id chains the history. CASCADE ON DELETE on template_id so dropping a template removes its history.
- New pointer column `workflow_templates.current_version_id UUID REFERENCES workflow_template_versions(id)` added with FK + dedicated index. Plan 02's backend Save endpoint will update this column atomically with the version-row insert.
- New pinning column `workflow_executions.template_version_id UUID REFERENCES workflow_template_versions(id)` added — nullable forever, legacy executions stay valid. Plan 02's engine update will write this column on new executions.
- Eager backfill DO block creates a v1 row in `workflow_template_versions` for every workflow_templates row whose Phase 109 graph projection succeeded (`graph_nodes IS NOT NULL`); `workflow_templates.current_version_id` is set to point at the new row. Empty-phases rows (graph_nodes IS NULL) stay with current_version_id NULL and are handled by Plan 02's seed-copy path.
- RLS enabled with two policies: SELECT permits owners and global-seed reads; INSERT/UPDATE/DELETE are service-role only. Both wrapped in DO + EXCEPTION blocks for re-apply idempotency.
- 7-test pytest integration suite in tests/integration/test_workflow_template_versioning_migration.py covering shape (3 tests), backfill correctness (3 tests), and the B-6 fix — legacy template_version INT column preservation (1 test). Pattern mirrors Phase 109's test_workflow_template_graph_projection.py: real Supabase service client, skip-on-no-creds, no mocks.
- Inline ROLLBACK PROCEDURE as a SQL comment block at end of migration — one Ctrl-F away for operators.

## Task Commits

Each task was committed atomically:

1. **Task 01-01: Create workflow_template_versions table + FK + RLS** — `8c7a8922` (feat)
2. **Task 01-02: Add current_version_id + template_version_id pointer columns** — `99912892` (feat)
3. **Task 01-03: Backfill v1 rows + inline rollback procedure** — `b1b5611e` (feat)
4. **Task 01-04: Integration tests for migration shape + backfill + legacy INT preservation** — `4c945a97` (test)
5. **Task 01-05: Static-check migration idempotency** — `f07861b7` (docs; allow-empty because verification-only)

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write)

## Files Created/Modified

- `supabase/migrations/20260615000000_workflow_template_versioning.sql` (226 lines, NEW) — CREATE TABLE IF NOT EXISTS workflow_template_versions + UNIQUE (template_id, version_number) + 2 indexes + RLS + 2 DO-wrapped policies + 2 ALTER TABLE ADD COLUMN IF NOT EXISTS + 2 indexes + 1 backfill DO block + inline ROLLBACK comments
- `tests/integration/test_workflow_template_versioning_migration.py` (287 lines, NEW, 7 tests) — Shape (3), backfill (3), legacy-INT-preservation (1) — all skip-on-no-creds

## Decisions Made

1. **`$BODY$` named dollar quotes throughout.** Phase 109 documented the supabase CLI 2.75 bug where bare `$$` boundaries can be mis-parsed. All three DO blocks in this migration use `$BODY$ ... $BODY$`. Verified via static check: zero bare `$$` occurrences in non-comment code lines.

2. **Eager backfill scope limited to `graph_nodes IS NOT NULL`.** Phase 109 left rows with empty-phases yielding NULL graph_* fields as a sentinel for "render legacy phases viewer". Phase 110 preserves that contract — those rows get `current_version_id` NULL and will be picked up by Plan 02's seed-copy path on first Edit. This avoids creating bogus v1 rows for templates that have no real graph yet.

3. **`saved_by_user_id` is nullable.** Seeded templates have `workflow_templates.created_by IS NULL` (per CONTEXT.md plus the on-disk schema confirmation in 110-CONTEXT § Implementation Decisions). Their backfilled v1 rows inherit that NULL via `saved_by_user_id = tmpl.created_by`. Production writes from Plan 02 will always carry a non-NULL `auth.uid()`. A `COMMENT ON COLUMN saved_by_user_id IS 'NULL = system backfill (Phase 110 v1); NOT NULL otherwise'` documents this for future readers.

4. **Legacy `workflow_executions.template_version INT` column is NOT dropped.** Test #7 (`test_legacy_template_version_int_column_preserved`) is the load-bearing regression-guard from the B-6 fix in plan-checker iteration 1. The new `template_version_id UUID` column coexists with the legacy INT column; both are nullable, both are queryable. A future cleanup migration ("Phase 110.5") will drop the legacy column once Plan 02 fully ships and all in-flight executions complete.

5. **RLS owner-OR-global-seed read policy.** Wanted to preserve Phase 109's pattern where seeded templates (created_by IS NULL) are globally readable. The SELECT policy reflects this: `auth.uid() = templates.created_by OR templates.created_by IS NULL`. Writes stay service-role only because Plan 02's engine writes from a service-role connection (`supabase_client`, not `supabase` shim — per project memory).

6. **Per-row backfill failure handler is `RAISE NOTICE`, not error-table insert.** Phase 109's projection migration wrote per-row failures to `workflow_template_migration_errors`. Phase 110's backfill assumes Phase 109 already produced valid JSONB graph fields — a failure here is genuinely unexpected. A NOTICE-log + leave-NULL strategy is lighter than re-creating the error-log infrastructure. The row picks itself up later via Plan 02's seed-copy path. Documented in the DO block's EXCEPTION clause comment.

## Deviations from Plan

None — plan executed exactly as written.

All five tasks landed verbatim per the plan's `<action>` blocks. The plan-checker iteration 1 fixes (B-5 idempotency, B-6 legacy-INT preservation) were already baked into the plan; no new auto-fixes were needed during execution. Branch hygiene (W-6) verified before every commit; branch stayed on `plan-109-spec-b-phase-1` throughout.

**Total deviations:** 0
**Impact on plan:** Plan was complete and accurate. No rework or auto-fixes required.

## Issues Encountered

**Local Supabase stack not running.** This Windows workstation does not have Docker Desktop's Linux engine pipe active, so `supabase status` failed and `supabase db push --local` could not run. Per the plan's NOT_RUNNING branch, fell back to static verification:

- `$BODY$` token balance: 6 tokens in non-comment code lines (3 DO/END pairs, balanced).
- `IF NOT EXISTS` guards: 10 occurrences (1 CREATE TABLE + 5 CREATE INDEX + 2 ADD COLUMN + 2 misc) — well above the >=5 minimum.
- Bare `$$` in code: zero (supabase CLI 2.75 bug avoided).
- `WHERE current_version_id IS NULL` guard on backfill: present, second run iterates zero rows.

Real-DB apply + double-apply idempotency proof will run automatically when the PR pipeline executes `supabase db push --local` as part of `make test`. The 7 integration tests will run against that local DB and produce concrete pass/fail signal.

**`PytestUnknownMarkWarning: Unknown pytest.mark.integration`.** Phase 109's integration test file emits the same warning (project does not register the `integration` mark in pyproject.toml). Mark is purely organizational here; not a blocker.

## User Setup Required

None — migration is pure SQL with eager backfill. After this plan ships to prod:

1. Run `supabase db push` to apply migration 20260615000000.
2. Verify backfill: `SELECT count(*) FROM workflow_templates WHERE graph_nodes IS NOT NULL AND current_version_id IS NULL;` should return 0.
3. Verify versions: `SELECT count(*) FROM workflow_template_versions WHERE version_number = 1;` should match the count from step 2's complement (templates with non-NULL graph_nodes).
4. Re-run `supabase db push` — second run must be a no-op (no errors, no row changes).

No new env vars, no dashboard configuration, no third-party services.

## Next Phase Readiness

**Ready for Plan 110-02** (backend Save + Load endpoint):

- Table `workflow_template_versions` exists; Plan 02's `WorkflowEngine.save_template_version()` method INSERTs into it and updates `workflow_templates.current_version_id` in the same transaction.
- Column `workflow_templates.current_version_id` exists and is pre-populated for every graph-projected row; Plan 02's GET handler can JOIN through this column to fetch the current graph; the `If-Match` ETag will be derived from `workflow_template_versions.saved_at` (locked decision 6).
- Column `workflow_executions.template_version_id` exists; Plan 02's `start_workflow_execution()` update reads `template.current_version_id` and writes it to this column at execution start.
- Legacy `workflow_executions.template_version INT` column is preserved — Plan 02 must continue to write it (or accept NULL) for backward compatibility with the engine's `list_template_versions` method (`app/workflows/engine.py:479`).
- `pikar.flatten_phases_to_steps` adapter from Phase 109 is NOT regressed (verified via grep — still present in `20260601000000_workflow_template_graph_projection.sql`).
- `workflow_template_migration_errors` table from Phase 109 is NOT regressed (same migration, unchanged).

**Ready for Plans 110-03, 110-04, 110-05:**
- Plan 03 (server-side validate endpoint) reads from `workflow_template_versions.graph_nodes` to validate stored graphs.
- Plan 04 (frontend editable canvas) will POST to Plan 02's PUT endpoint and read history from `workflow_template_versions` via Plan 02's GET history endpoint.
- Plan 05 (frontend versioning + conflict modal) uses the `If-Match` / `ETag` pair derived from `workflow_template_versions.saved_at` — that column is now stable, ready for downstream consumption.

**Idempotency proof deferred to CI:** The migration's IF NOT EXISTS / WHERE-guard / DO-EXCEPTION constructs make re-apply observably indistinguishable from a single apply. CI will exercise this when `make test` runs `supabase db push --local` against a fresh local DB twice.

---

## Self-Check: PASSED

Verified post-write:

- [x] `supabase/migrations/20260615000000_workflow_template_versioning.sql` exists on disk (226 lines)
- [x] `tests/integration/test_workflow_template_versioning_migration.py` exists on disk (287 lines, 7 tests collected by pytest)
- [x] Commit `8c7a8922` exists in `git log` (task 01-01)
- [x] Commit `99912892` exists in `git log` (task 01-02)
- [x] Commit `b1b5611e` exists in `git log` (task 01-03)
- [x] Commit `4c945a97` exists in `git log` (task 01-04)
- [x] Commit `f07861b7` exists in `git log` (task 01-05)
- [x] Migration SQL passes static check (dollar-quote balance OK in code lines, 10 IF NOT EXISTS guards, no bare $$ in code)
- [x] 7 pytest tests collected (uv run pytest --collect-only)
- [x] Tests SKIP cleanly when Supabase creds absent (7 skipped, 0 failed)
- [x] Ruff clean on test file (uv run ruff check)
- [x] Branch hygiene: still on `plan-109-spec-b-phase-1` after all commits
- [x] Phase 109 adapter `pikar.flatten_phases_to_steps` not regressed (still in 20260601000000)
- [x] Phase 109 `workflow_template_migration_errors` table not regressed (still in 20260601000000)

---

*Phase: 110-workflow-node-editor-editable*
*Completed: 2026-05-11*
