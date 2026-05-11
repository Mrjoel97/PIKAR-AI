---
phase: 110-workflow-node-editor-editable
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - supabase/migrations/20260615000000_workflow_template_versioning.sql
  - tests/integration/test_workflow_template_versioning_migration.py
autonomous: true
requirements:
  - NODEEDITOR-VERSION-01
gap_closure: false

must_haves:
  truths:
    - "workflow_template_versions table exists with the seven required columns (id, template_id, version_number, parent_version_id, graph_nodes, graph_edges, graph_layout, saved_by_user_id, saved_at, comment) and UNIQUE (template_id, version_number)"
    - "workflow_templates.current_version_id column exists and points at the row's most recent workflow_template_versions row after the eager backfill"
    - "workflow_executions.template_version_id column exists and is nullable (legacy executions stay valid)"
    - "workflow_executions.template_version (legacy INT column from 0051) is preserved alongside the new template_version_id UUID column — both nullable, both queryable"
    - "Every pre-existing workflow_templates row whose graph_nodes was non-NULL after Phase 109 has a corresponding workflow_template_versions row with version_number = 1"
    - "Re-running the migration is a no-op (idempotent via CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS + WHERE current_version_id IS NULL guard on backfill); migration apply twice in succession is observably indistinguishable from a single apply"
  artifacts:
    - path: "supabase/migrations/20260615000000_workflow_template_versioning.sql"
      provides: "CREATE TABLE IF NOT EXISTS workflow_template_versions + ALTER TABLE workflow_templates ADD current_version_id + ALTER TABLE workflow_executions ADD template_version_id + idempotent eager backfill"
      contains: "workflow_template_versions"
    - path: "tests/integration/test_workflow_template_versioning_migration.py"
      provides: "Integration tests verifying column/table existence, FK integrity, idempotency, backfill correctness, NULL-template-version-id permitted on legacy executions, AND legacy template_version INT column preservation (round-trip test)"
      contains: "skipif"
  key_links:
    - from: "workflow_templates.current_version_id"
      to: "workflow_template_versions.id"
      via: "Foreign key"
      pattern: "REFERENCES workflow_template_versions"
    - from: "workflow_template_versions.parent_version_id"
      to: "workflow_template_versions.id"
      via: "Self-referencing foreign key (history chain)"
      pattern: "REFERENCES workflow_template_versions"
    - from: "workflow_executions.template_version_id"
      to: "workflow_template_versions.id"
      via: "Foreign key (run-time pinning, NULL allowed for legacy)"
      pattern: "REFERENCES workflow_template_versions"
---

<objective>
Ship the schema and one-shot backfill for Phase 110 versioning. Creates `workflow_template_versions` (every Save creates a row), adds `current_version_id` pointer to `workflow_templates`, adds `template_version_id` to `workflow_executions` for run-time pinning, and backfills a `version_number = 1` row for every existing graph-projected template. All downstream plans depend on this migration landing first — Plan 02 (backend save) writes rows here, Plan 04/05 (frontend) read history from here.

Purpose: Unblocks Spec B Phase 2 decisions 5 (Version rows) and 6 (If-Match — `updated_at` for ETag lives on the version row from now on).
Output: One SQL migration file (idempotent) + one integration test file (7 tests skip-on-no-creds pattern, +1 for legacy INT column preservation).
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/110-workflow-node-editor-editable/110-CONTEXT.md
@.planning/phases/109-workflow-node-editor-viewer/109-01-SUMMARY.md
@supabase/migrations/0007_workflow_steps.sql
@supabase/migrations/0051_workflow_lifecycle_and_execution_metadata.sql
@supabase/migrations/20260511130100_atomic_workflow_execution_start_goal.sql
@supabase/migrations/20260601000000_workflow_template_graph_projection.sql
@tests/integration/test_workflow_template_graph_projection.py

<interfaces>
<!-- Existing schema state inherited from Phase 109 + earlier migrations -->

workflow_templates (post-Phase 109, observed in code):
  - id UUID PRIMARY KEY
  - name TEXT NOT NULL
  - description TEXT
  - phases JSONB NOT NULL                                -- on-disk shape; nested phases[].steps
  - category TEXT NOT NULL
  - created_at TIMESTAMPTZ
  - updated_at TIMESTAMPTZ
  - template_key TEXT NOT NULL                           -- from 0051; legacy versioning key
  - version INTEGER NOT NULL                             -- legacy versioning (NOT the new versioning)
  - lifecycle_status TEXT NOT NULL                       -- 'draft'|'published'|'archived'
  - is_generated BOOLEAN
  - personas_allowed JSONB
  - created_by UUID                                      -- ownership column (NULL for seeded templates)
  - published_by UUID
  - published_at TIMESTAMPTZ
  - graph_nodes JSONB                                    -- from Phase 109 (NULL for empty-phase rows)
  - graph_edges JSONB                                    -- from Phase 109
  - graph_layout JSONB                                   -- from Phase 109

workflow_executions (post-0051):
  - id UUID PRIMARY KEY
  - user_id UUID NOT NULL
  - template_id UUID REFERENCES workflow_templates(id)
  - template_version INTEGER                             -- LEGACY: integer copied from workflow_templates.version
  - started_by UUID
  - run_source TEXT
  - status TEXT
  - context JSONB
  - goal TEXT                                            -- from 20260511130100
  - created_at, updated_at, completed_at TIMESTAMPTZ

start_workflow_execution_atomic(p_user_id, p_template_id, p_template_version INT DEFAULT NULL, ...)
  -- existing RPC at 20260511130100_atomic_workflow_execution_start_goal.sql
  -- Phase 110 should NOT modify this RPC in Plan 01; Plan 02 will widen it (or add a new
  -- RPC variant) to accept p_template_version_id UUID. Plan 01 just adds the column.

pikar.flatten_phases_to_steps(phases jsonb) -> jsonb     -- from Phase 109; available
pikar.project_steps_to_nodes(steps jsonb) -> jsonb       -- from Phase 109
pikar.project_steps_to_edges(steps jsonb) -> jsonb       -- from Phase 109
pikar.compute_dagre_layout(steps jsonb) -> jsonb         -- from Phase 109
</interfaces>

<context_notes>
- CRITICAL: ownership column is `created_by` (UUID, nullable), NOT `owner_user_id`. CONTEXT.md misnames it. Use `created_by` everywhere. Seeded templates have `created_by IS NULL` and are treated as global read-only seeds. The Spec B "owner_user_id" terminology is aspirational; the on-disk schema uses `created_by`. Do NOT add an `owner_user_id` alias — Plan 02 will read `created_by` directly.
- The existing `workflow_executions.template_version` (INT, from 0051) is the LEGACY versioning column. It is NOT being removed. Phase 110 adds a NEW column `template_version_id UUID` alongside it. The two columns coexist until a future cleanup migration. Existing executions keep `template_version_id IS NULL` (legacy behavior). New executions started by Plan 02's updated engine path will have it set. Plan 01 must ALSO add a regression test (Task 01-04 test #7) asserting the legacy INT column is preserved — see B-6 fix below.
- Existing `list_template_versions` in `app/workflows/engine.py:479` queries by `template_key` ordering by integer `version` — that's the LEGACY mechanism (publish-flow versioning). Plan 02 will add a NEW method `list_template_history()` that reads from `workflow_template_versions`. Keep both working.
- Backfill scope: every workflow_templates row whose `graph_nodes IS NOT NULL` (post-109 backfill) gets a v1 row. Rows where graph_nodes IS NULL (empty-phases sentinel from 109-01) get current_version_id = NULL and are handled by Plan 02's seed-copy path (clicking Edit will create a v1 row at that moment).
- Migration filename MUST be timestamp `20260615000000_workflow_template_versioning.sql` — strictly later than 20260601000000 (Phase 109's migration). Confirmed via Phase 109 SUMMARY.
- supabase CLI 2.75 has a `$$` dollar-quote bug. Use `$BODY$ ... $BODY$` named dollar quotes for any function bodies, NOT bare `$$`. DO blocks are fine.
- Integration tests: follow Phase 109's pattern at `tests/integration/test_workflow_template_graph_projection.py` — real Supabase service client, `skipif` when `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` absent, no mocks. CI without local Supabase shows tests as skipped, not failed.
- Branch hygiene: `git branch --show-current` MUST be checked before every commit (parallel GSD automation hazard from Phase 109). Task 01-01 includes an automated branch-check verify step.
- ALL DDL in this migration MUST use IF NOT EXISTS / IF EXISTS variants for full idempotency — re-running the migration twice in succession is a no-op (verified via repeated `supabase db push --local` in the test step).
</context_notes>
</context>

<tasks>

<task type="auto">
  <name>Task 01-01: Create workflow_template_versions table + foreign keys (fully idempotent DDL)</name>
  <files>supabase/migrations/20260615000000_workflow_template_versioning.sql</files>
  <action>
PRECONDITION: verify the current git branch matches the expected Phase 110 branch pattern before touching files. Run `git branch --show-current` and confirm it matches `^plan-(109|110)-` (parallel GSD automation has dropped commits onto unrelated branches twice this session — abort the task if the branch is wrong).

Create the migration file at `supabase/migrations/20260615000000_workflow_template_versioning.sql`. The file's first SQL block must:

1. Create the `workflow_template_versions` table using `CREATE TABLE IF NOT EXISTS` (B-5 fix — full idempotency). Columns per CONTEXT.md decision 5:
   - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
   - `template_id UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE`
   - `version_number INT NOT NULL` (per-template, starts at 1)
   - `parent_version_id UUID REFERENCES workflow_template_versions(id)` (nullable; NULL means v1)
   - `graph_nodes JSONB NOT NULL`
   - `graph_edges JSONB NOT NULL`
   - `graph_layout JSONB` (nullable)
   - `saved_by_user_id UUID` (nullable to permit v1 backfill of seeded templates whose `created_by IS NULL`)
   - `saved_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `comment TEXT` (nullable)
   - `UNIQUE (template_id, version_number)`

2. Indexes (each with IF NOT EXISTS):
   - `CREATE INDEX IF NOT EXISTS idx_workflow_template_versions_template_id ON workflow_template_versions(template_id);` (History pane lookups)
   - `CREATE INDEX IF NOT EXISTS idx_workflow_template_versions_saved_at ON workflow_template_versions(saved_at DESC);` (ordering)

3. Document the relaxed `saved_by_user_id` NULL semantics:
   `COMMENT ON COLUMN workflow_template_versions.saved_by_user_id IS 'NULL = system backfill (Phase 110 v1); NOT NULL otherwise';`

4. Enable RLS on the new table with two policies, both wrapped in `DO $BODY$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $BODY$;` for idempotency:
   - SELECT policy: users can read versions of templates they own OR templates with `created_by IS NULL` (global seeds): `auth.uid() = (SELECT created_by FROM workflow_templates WHERE id = template_id) OR (SELECT created_by FROM workflow_templates WHERE id = template_id) IS NULL`
   - INSERT/UPDATE: service-role only (Plan 02's engine uses `supabase_client`/service-role connection): `USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role')`.

5. `ALTER TABLE workflow_template_versions ENABLE ROW LEVEL SECURITY;` — safe to repeat; PostgreSQL is idempotent on this statement.
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('supabase/migrations/20260615000000_workflow_template_versioning.sql','utf8');const needed=['CREATE TABLE IF NOT EXISTS workflow_template_versions','UNIQUE (template_id, version_number)','REFERENCES workflow_templates(id)','ENABLE ROW LEVEL SECURITY','CREATE INDEX IF NOT EXISTS idx_workflow_template_versions_template_id','CREATE INDEX IF NOT EXISTS idx_workflow_template_versions_saved_at'];for(const n of needed){if(!text.includes(n)){console.error('MISSING:',n);process.exit(1);}}console.log('OK');"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Migration file exists; contains CREATE TABLE IF NOT EXISTS for workflow_template_versions with UNIQUE constraint, foreign key to workflow_templates(id), RLS enabled, and two indexes (template_id, saved_at) — all idempotent. Branch verified.</done>
</task>

<task type="auto">
  <name>Task 01-02: Add current_version_id to workflow_templates + template_version_id to workflow_executions (fully idempotent DDL)</name>
  <files>supabase/migrations/20260615000000_workflow_template_versioning.sql</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Append to the SAME migration file (all statements idempotent — B-5):

1. `ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS current_version_id UUID REFERENCES workflow_template_versions(id);`
   - Nullable for now — backfill in Task 01-03 sets it. After backfill, app code maintains the invariant that a saved template has a non-NULL pointer.
   - `CREATE INDEX IF NOT EXISTS idx_workflow_templates_current_version_id ON workflow_templates(current_version_id);`

2. `ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS template_version_id UUID REFERENCES workflow_template_versions(id);`
   - Nullable. Legacy executions keep it NULL forever. Plan 02 sets it on new executions.
   - `CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_version_id ON workflow_executions(template_version_id);`

3. Add SQL comment blocks above each ALTER explaining what each column does and what NULL means. These comments are load-bearing — Plan 02's engine query refers to them when reading rows.

Use `ADD COLUMN IF NOT EXISTS` for idempotency. Do NOT touch the existing `template_version INT` column on `workflow_executions` — it stays (Task 01-04 test #7 asserts this). Do NOT touch existing `version`/`template_key` on `workflow_templates` — they stay.
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('supabase/migrations/20260615000000_workflow_template_versioning.sql','utf8');for(const n of ['current_version_id UUID','template_version_id UUID','ADD COLUMN IF NOT EXISTS current_version_id','ADD COLUMN IF NOT EXISTS template_version_id','CREATE INDEX IF NOT EXISTS idx_workflow_templates_current_version_id','CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_version_id']){if(!text.includes(n)){console.error('MISSING:',n);process.exit(1);}}console.log('OK');"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Migration file contains ALTER TABLE for both new columns with IF NOT EXISTS, foreign keys, and per-column indexes (all idempotent). Existing `template_version INT` and `version` columns untouched.</done>
</task>

<task type="auto">
  <name>Task 01-03: Backfill v1 rows for templates with non-NULL graph_nodes</name>
  <files>supabase/migrations/20260615000000_workflow_template_versioning.sql</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Append a DO block at the end of the same migration that performs the eager backfill:

```sql
DO $BODY$
DECLARE
  tmpl RECORD;
  new_version_id UUID;
BEGIN
  -- Idempotency: skip rows that already have current_version_id set
  FOR tmpl IN
    SELECT id, graph_nodes, graph_edges, graph_layout, created_by
    FROM workflow_templates
    WHERE current_version_id IS NULL
      AND graph_nodes IS NOT NULL
  LOOP
    BEGIN
      INSERT INTO workflow_template_versions (
        template_id, version_number, parent_version_id,
        graph_nodes, graph_edges, graph_layout,
        saved_by_user_id, comment
      )
      VALUES (
        tmpl.id, 1, NULL,
        tmpl.graph_nodes, tmpl.graph_edges, tmpl.graph_layout,
        tmpl.created_by,                              -- NULL for seeded templates
        'Phase 110 backfill: v1 from initial graph projection'
      )
      RETURNING id INTO new_version_id;

      UPDATE workflow_templates
      SET current_version_id = new_version_id
      WHERE id = tmpl.id;
    EXCEPTION WHEN OTHERS THEN
      -- Mirror Phase 109's per-row failure log pattern, but lighter-touch:
      -- a backfill failure here is unexpected (Phase 109's projection should have
      -- guaranteed valid JSONB). Log via RAISE NOTICE and leave current_version_id
      -- as NULL so Plan 02's seed-copy path picks the row up on first Edit.
      RAISE NOTICE 'Phase 110 backfill skipped template_id=% reason=%', tmpl.id, SQLERRM;
    END;
  END LOOP;
END;
$BODY$;
```

Use `$BODY$` named dollar quotes (NOT `$$`) per the supabase CLI 2.75 bug noted in CONTEXT.md. The block is wrapped in BEGIN/EXCEPTION so per-row failures do not abort the migration. Idempotency is achieved via the `WHERE current_version_id IS NULL` predicate — re-running this migration after a successful run will iterate zero rows.

After the DO block, append an inline rollback procedure as a SQL comment block (mirror Phase 109's pattern):

```sql
-- ROLLBACK PROCEDURE (manual; not auto-executed)
--
-- To fully roll back this migration:
--
-- ALTER TABLE workflow_executions DROP COLUMN IF EXISTS template_version_id;
-- ALTER TABLE workflow_templates DROP COLUMN IF EXISTS current_version_id;
-- DROP TABLE IF EXISTS workflow_template_versions CASCADE;
--
-- After Plan 02 ships, additionally drop legacy columns:
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_nodes;
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_edges;
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_layout;
-- That second cleanup is deferred to "Phase 110.5" — not part of this migration.
```
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('supabase/migrations/20260615000000_workflow_template_versioning.sql','utf8');for(const n of ['DO $BODY$','EXCEPTION WHEN OTHERS','WHERE current_version_id IS NULL','RAISE NOTICE','ROLLBACK PROCEDURE','Phase 110 backfill: v1 from initial graph projection']){if(!text.includes(n)){console.error('MISSING:',n);process.exit(1);}}console.log('OK');"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>DO block exists with $BODY$ dollar quotes (NOT bare $$), idempotent WHERE guard, per-row EXCEPTION handler, and an inline rollback comment block. Re-running the migration is a no-op.</done>
</task>

<task type="auto">
  <name>Task 01-04: Integration tests for migration shape + idempotency + backfill + legacy column preservation</name>
  <files>tests/integration/test_workflow_template_versioning_migration.py</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

Create `tests/integration/test_workflow_template_versioning_migration.py` modeled on `tests/integration/test_workflow_template_graph_projection.py` (Phase 109's pattern). The file must:

1. Use `pytest.importorskip("supabase")` at module top and `pytestmark = pytest.mark.skipif(not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"), reason="Requires Supabase creds")`.

2. Define a fixture that returns a service-role `supabase.Client`. Copy the pattern from `test_workflow_template_graph_projection.py:fixture_supabase_client` if present, or re-create using `create_client(url, service_key)`.

3. SEVEN test functions (six original + one new for B-6 legacy column preservation):
   - `test_workflow_template_versions_table_exists` — `client.table("workflow_template_versions").select("id").limit(1).execute()` does not raise.
   - `test_current_version_id_column_exists` — `client.table("workflow_templates").select("current_version_id").limit(1).execute()` does not raise.
   - `test_template_version_id_column_exists` — `client.table("workflow_executions").select("template_version_id").limit(1).execute()` does not raise.
   - `test_backfill_populates_v1_for_graph_projected_templates` — Query `workflow_templates` where `graph_nodes IS NOT NULL`, assert each row's `current_version_id` is non-NULL. For one such row, fetch its version: `workflow_template_versions.select("*").eq("template_id", row.id).eq("version_number", 1).single()` — assert `parent_version_id IS NULL`, `comment` starts with "Phase 110 backfill".
   - `test_backfill_skips_null_graph_rows` — Query `workflow_templates` where `graph_nodes IS NULL`, assert `current_version_id IS NULL` for all. These will be filled on first Edit (Plan 02).
   - `test_legacy_workflow_executions_keep_null_template_version_id` — Query `workflow_executions` rows created before today (use `created_at` filter), assert `template_version_id IS NULL`. (At minimum just assert NO existing execution has a non-NULL value — Phase 110 has not added Plan 02 code yet that writes this column.)
   - **NEW (B-6 fix): `test_legacy_template_version_int_column_preserved`** — Catches any future migration that accidentally drops the legacy INT column. Specifically:
     1. Query `information_schema.columns` for table `workflow_executions` filtered to the two columns of interest. Use the supabase service client's `.rpc()` or a raw query via `client.postgrest.session.get(...)` if a direct SQL helper isn't ergonomic — alternative: assert via two table selects (one for each column).
     2. Assert BOTH columns exist:
        - `template_version` with `data_type = 'integer'`
        - `template_version_id` with `data_type = 'uuid'`
     3. Assert both are nullable (`is_nullable = 'YES'`).
     4. INSERT a synthetic test row into `workflow_executions` with `template_version=1` and `template_version_id=NULL`, plus minimal required fields (user_id, template_id from a known seed). SELECT it back. Assert both columns round-trip correctly (the INT comes back as 1, the UUID stays NULL).
     5. Clean up: DELETE the synthetic row at test end.
     6. If clean-insert is infeasible due to FK constraints, replace step 4-5 with a read-only assertion: "fetch any existing `workflow_executions` row, assert it has both columns accessible (no PostgREST schema error), and assert `template_version` is integer-typed when non-NULL".

4. Each test must be a standalone function (NOT inside a class) so pytest collection is flat. Use ruff-clean imports and docstrings (≥1 sentence each, per project pre-commit config requiring docstring coverage).

5. Run `uv run pytest tests/integration/test_workflow_template_versioning_migration.py --collect-only` to confirm collection. Tests will SKIP locally without Supabase creds — that is the expected and acceptable state.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_workflow_template_versioning_migration.py --collect-only -q 2>&1 | grep -E "test_|collected" | head -10</automated>
    <automated>grep -c "test_legacy_template_version_int_column_preserved" tests/integration/test_workflow_template_versioning_migration.py</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Test file exists with 7 tests collected by pytest (six original + new legacy-INT preservation). Each test SKIPS cleanly when Supabase creds absent (no failures, no errors).</done>
</task>

<task type="auto">
  <name>Task 01-05: Apply migration locally + verify backfill + verify idempotency (re-apply)</name>
  <files></files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

This task is conditional. Check whether a local Supabase stack is running:

```bash
supabase status 2>&1 | grep -q "API URL" && echo "RUNNING" || echo "NOT_RUNNING"
```

If RUNNING:
1. `supabase db push --local` (first apply — applies the new migration).
2. **B-5 idempotency check:** `supabase migration up --include-all` a SECOND time. The second run MUST be observably indistinguishable from the first — verify by capturing the table row counts in `workflow_template_versions` before and after the second apply (must be equal). The CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS + WHERE-guarded backfill DO block together guarantee this.
3. Run the integration tests against the local DB: `uv run pytest tests/integration/test_workflow_template_versioning_migration.py -v`.
4. All 7 tests should PASS.

If NOT_RUNNING (the typical local dev case on this Windows machine):
1. Skip apply — just verify the migration file is syntactically valid by checking dollar-quote balance and required keywords (mirror Phase 109's static-check approach in `supabase/migrations/20260601000000_workflow_template_graph_projection.sql`).
2. Verify every DDL statement in the migration uses an idempotent variant (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS, ADD COLUMN IF NOT EXISTS, WHERE-guarded backfill).
3. Document in the plan SUMMARY that real-DB apply + double-apply idempotency will run in CI / on deploy.

Either path is acceptable. The CI pipeline runs `supabase db push --local` as part of `make test`, so the apply will happen automatically when the PR runs CI.

Do NOT run `supabase db push` against the REMOTE prod project from this workstation. Migration application to prod is the user's manual step after PR merge.
  </action>
  <verify>
    <automated>node -e "const fs=require('fs');const text=fs.readFileSync('supabase/migrations/20260615000000_workflow_template_versioning.sql','utf8');const dollars=(text.match(/\$BODY\$/g)||[]).length;if(dollars%2!==0){console.error('Unbalanced $BODY$ count:',dollars);process.exit(1);}const idempotent=(text.match(/IF NOT EXISTS/g)||[]).length;if(idempotent < 5){console.error('Too few IF NOT EXISTS guards:',idempotent);process.exit(1);}const lines=text.split('\\n');console.log('Lines:',lines.length,'$BODY$ count:',dollars,'IF NOT EXISTS count:',idempotent,'OK');"</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Migration file has balanced $BODY$ tokens (even count) and >=5 `IF NOT EXISTS` guards (table + 2 column adds + 3 index creates = 6 minimum). If local Supabase running, migration applied + re-applied (double-apply is no-op) and all 7 integration tests PASS; if not, plan SUMMARY documents that CI will exercise idempotency on PR.</done>
</task>

</tasks>

<verification>
Post-plan verification checklist:

1. `supabase/migrations/20260615000000_workflow_template_versioning.sql` exists on disk.
2. Migration filename timestamp is strictly greater than `20260601000000` (Phase 109's migration).
3. Migration uses `$BODY$` named dollar quotes (NOT bare `$$`) for function bodies and DO blocks per supabase CLI 2.75 bug.
4. Migration uses `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS` everywhere — re-applying the migration twice in succession is observably a no-op (B-5).
5. `tests/integration/test_workflow_template_versioning_migration.py` exists; 7 tests collected by pytest (six original + new `test_legacy_template_version_int_column_preserved` from B-6).
6. Ruff clean on the test file: `uv run ruff check tests/integration/test_workflow_template_versioning_migration.py`.
7. Re-running the migration produces zero changes (idempotent — verify by inspecting the IF NOT EXISTS guards on DDL + the WHERE clause on the backfill DO block + the row-count delta on a second apply).
8. Branch hygiene: `git branch --show-current` returns `plan-109-spec-b-phase-1` (or whatever branch Phase 110 is being authored on, matching `^plan-(109|110)-`). NOT `main` or another phase's branch — every task in this plan includes an automated branch-check verify step (W-6).
</verification>

<success_criteria>
This plan ships when:
- One new migration file at `supabase/migrations/20260615000000_workflow_template_versioning.sql` (estimated ~130-200 lines).
- One new integration test file at `tests/integration/test_workflow_template_versioning_migration.py` (~140-200 lines, 7 tests including legacy INT column preservation).
- Each of 5 tasks committed atomically with conventional-commits message: `feat(workflow-versioning): <task description> [110-01-NN]`.
- Plan SUMMARY committed to `.planning/phases/110-workflow-node-editor-editable/110-01-SUMMARY.md`.
- Address roadmap success criterion #2 (every Save creates a version row — Plan 02 implements the save side; Plan 01 establishes the schema).
- Address roadmap success criterion #3 (execution pins template_version_id at start — Plan 02 implements the write; Plan 01 establishes the column).
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-01-SUMMARY.md` with: phase/plan frontmatter, duration metric, files created/modified, decisions made, deviations from plan, and a "Ready for Plan 02" Next-Phase-Readiness section listing the columns + table that Plan 02 will read/write. Also document the idempotency proof (whether double-apply was exercised locally or deferred to CI).
</output>
</content>
</invoke>