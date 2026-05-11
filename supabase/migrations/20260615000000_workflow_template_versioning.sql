-- Migration: 20260615000000_workflow_template_versioning.sql
-- Phase 110-01 (Spec B Phase 2) — workflow template version history + run-time pinning.
--
-- Purpose
-- -------
-- Introduce immutable per-template version rows so every Save creates a new
-- entry instead of overwriting the canvas, and pin executions to a specific
-- version so mid-flight template edits do not affect running workflows.
--
-- This migration:
--   1. Creates a new table ``workflow_template_versions`` (one row per Save,
--      version_number monotonic per template, parent_version_id links the
--      history chain, graph_nodes/edges/layout snapshotted at Save time).
--   2. Adds ``workflow_templates.current_version_id`` (pointer to the most
--      recent version row for that template).
--   3. Adds ``workflow_executions.template_version_id`` (run-time pinning;
--      NULL for legacy executions that were started before this migration).
--   4. Eager-backfills a ``version_number = 1`` row for every existing
--      ``workflow_templates`` row whose Phase 109 graph projection succeeded
--      (i.e. ``graph_nodes IS NOT NULL``).
--   5. Coexists with the legacy ``workflow_executions.template_version INT``
--      column (added by 0051) — both columns live side-by-side until a
--      future cleanup migration; legacy executions stay queryable.
--
-- Idempotency
-- -----------
-- Every DDL statement uses an ``IF NOT EXISTS`` / ``IF EXISTS`` variant.
-- The eager backfill DO block is guarded by ``WHERE current_version_id IS
-- NULL`` so a second run iterates zero rows. RLS policies are created
-- inside a DO block with ``EXCEPTION WHEN duplicate_object THEN NULL`` so
-- a re-apply does not raise.
--
-- supabase CLI 2.75 dollar-quote bug
-- ----------------------------------
-- This migration uses ``$BODY$ ... $BODY$`` named dollar quotes (NOT bare
-- ``$$``) for DO blocks because supabase CLI 2.75 mis-parses ``$$`` token
-- boundaries inside migration files.  See Phase 109 SUMMARY's note on the
-- same bug.
--
-- See: docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md
--      .planning/phases/110-workflow-node-editor-editable/110-CONTEXT.md
--      .planning/phases/110-workflow-node-editor-editable/110-01-versioning-migration-PLAN.md

-- 1. workflow_template_versions table (idempotent).
--    Every Save creates a row here; rows are immutable post-insert.
--    version_number is monotonic per template_id (enforced by UNIQUE).
--    parent_version_id chains the history (NULL = v1 / backfill root).
CREATE TABLE IF NOT EXISTS workflow_template_versions (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id         uuid NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,
  version_number      int  NOT NULL,
  parent_version_id   uuid REFERENCES workflow_template_versions(id),
  graph_nodes         jsonb NOT NULL,
  graph_edges         jsonb NOT NULL,
  graph_layout        jsonb,
  saved_by_user_id    uuid,
  saved_at            timestamptz NOT NULL DEFAULT now(),
  comment             text,
  UNIQUE (template_id, version_number)
);

COMMENT ON TABLE workflow_template_versions IS
    'Immutable per-Save history rows for workflow_templates. Every Save creates '
    'one row; version_number is monotonic per template; parent_version_id chains '
    'history. Run-time executions pin to a specific row via workflow_executions.template_version_id.';

COMMENT ON COLUMN workflow_template_versions.saved_by_user_id IS
    'NULL = system backfill (Phase 110 v1); NOT NULL otherwise';

COMMENT ON COLUMN workflow_template_versions.parent_version_id IS
    'Previous version in the history chain. NULL for v1 / backfilled rows. '
    'Revert-to-vN creates a NEW version whose parent points at vN.';

COMMENT ON COLUMN workflow_template_versions.comment IS
    'Optional Save message (e.g. "Added approval step"). NULL allowed.';

-- 2. Indexes (idempotent).
CREATE INDEX IF NOT EXISTS idx_workflow_template_versions_template_id
    ON workflow_template_versions(template_id);

CREATE INDEX IF NOT EXISTS idx_workflow_template_versions_saved_at
    ON workflow_template_versions(saved_at DESC);

-- 3. RLS — readers may see versions of templates they own OR global seeds
--    (workflow_templates.created_by IS NULL); writes are service-role only
--    (Plan 02's engine uses the supabase_client / service-role connection).
--    Wrapped in DO + EXCEPTION so a re-apply is a no-op.
ALTER TABLE workflow_template_versions ENABLE ROW LEVEL SECURITY;

DO $BODY$
BEGIN
  CREATE POLICY workflow_template_versions_select
    ON workflow_template_versions
    FOR SELECT
    USING (
      auth.uid() = (SELECT created_by FROM workflow_templates WHERE id = template_id)
      OR (SELECT created_by FROM workflow_templates WHERE id = template_id) IS NULL
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END;
$BODY$;

DO $BODY$
BEGIN
  CREATE POLICY workflow_template_versions_service_write
    ON workflow_template_versions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL;
END;
$BODY$;

-- 4. workflow_templates.current_version_id — pointer to the most recent
--    version row for this template. NULL until the row's Phase 109 graph
--    projection succeeded AND this migration's backfill ran (task 01-03).
--    After backfill, app code maintains the invariant that any saved
--    template has a non-NULL pointer. Idempotent via ADD COLUMN IF NOT EXISTS.
ALTER TABLE workflow_templates
    ADD COLUMN IF NOT EXISTS current_version_id UUID
        REFERENCES workflow_template_versions(id);

COMMENT ON COLUMN workflow_templates.current_version_id IS
    'FK to workflow_template_versions(id) — points at the latest Save for this '
    'template. NULL only for templates whose Phase 109 graph projection yielded '
    'NULL graph_nodes (empty phases). Plan 02 seed-copy path fills it on first Edit.';

CREATE INDEX IF NOT EXISTS idx_workflow_templates_current_version_id
    ON workflow_templates(current_version_id);

-- 5. workflow_executions.template_version_id — run-time pinning. The engine
--    writes template.current_version_id into this column when an execution
--    starts so mid-flight Saves do not affect the running workflow.
--    NULL = legacy execution started before Phase 110 (or before Plan 02's
--    engine update). The legacy ``template_version INT`` column from 0051
--    is preserved alongside this new column — both nullable, both queryable.
--    Idempotent via ADD COLUMN IF NOT EXISTS.
ALTER TABLE workflow_executions
    ADD COLUMN IF NOT EXISTS template_version_id UUID
        REFERENCES workflow_template_versions(id);

COMMENT ON COLUMN workflow_executions.template_version_id IS
    'FK to workflow_template_versions(id) — pinned snapshot of the template '
    'graph at execution start. NULL = legacy execution (pre-Phase-110, or '
    'pre-Plan-02 engine update). The legacy template_version INT column '
    'remains unchanged alongside this UUID column.';

CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_version_id
    ON workflow_executions(template_version_id);

-- 6. Eager backfill — create a v1 row for every workflow_templates row whose
--    Phase 109 graph projection succeeded (graph_nodes IS NOT NULL), and
--    point current_version_id at it. Rows with NULL graph_nodes (empty-phases
--    sentinel from 109-01) are LEFT ALONE — Plan 02's seed-copy path creates
--    the v1 row on first Edit.
--
--    Idempotency
--    -----------
--    The ``WHERE current_version_id IS NULL`` predicate ensures a second run
--    of this migration iterates zero rows (rows already backfilled have a
--    non-NULL pointer). Per-row failures land in a RAISE NOTICE log instead
--    of aborting the migration — mirrors Phase 109's pattern but lighter
--    touch (Phase 109's projection should have guaranteed valid JSONB).
--
--    Dollar-quote note
--    -----------------
--    Uses $BODY$ named dollar quotes, NOT bare $$, per the supabase CLI 2.75
--    bug noted in 110-CONTEXT.md and Phase 109's SUMMARY.
DO $BODY$
DECLARE
  tmpl RECORD;
  new_version_id UUID;
BEGIN
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
      -- Per-row failure here is unexpected (Phase 109's projection should have
      -- guaranteed valid JSONB). Log via RAISE NOTICE and leave
      -- current_version_id NULL so Plan 02's seed-copy path picks the row up
      -- on first Edit.
      RAISE NOTICE 'Phase 110 backfill skipped template_id=% reason=%', tmpl.id, SQLERRM;
    END;
  END LOOP;
END;
$BODY$;

-- 7. ROLLBACK PROCEDURE (manual; not auto-executed)
--
-- To fully roll back this migration:
--
--   ALTER TABLE workflow_executions DROP COLUMN IF EXISTS template_version_id;
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS current_version_id;
--   DROP TABLE IF EXISTS workflow_template_versions CASCADE;
--
-- After Plan 02 ships, additionally drop legacy columns:
--
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_nodes;
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_edges;
--   ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_layout;
--
-- That second cleanup is deferred to "Phase 110.5" — not part of this
-- migration. The legacy ``workflow_executions.template_version INT`` column
-- (from 0051) is intentionally NOT dropped here; it stays alongside the new
-- ``template_version_id UUID`` column until a future cleanup migration.
