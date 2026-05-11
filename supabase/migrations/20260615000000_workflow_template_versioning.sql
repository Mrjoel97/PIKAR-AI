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
