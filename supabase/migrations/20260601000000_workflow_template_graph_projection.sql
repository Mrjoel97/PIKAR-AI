-- Migration: 20260601000000_workflow_template_graph_projection.sql
-- Phase 109-01 (Spec B Phase 1) — read-only workflow node editor.
--
-- Purpose
-- -------
-- Add graph projection columns to ``workflow_templates`` plus three pikar.*
-- helper functions that project a template's linear steps list into the
-- node/edge/layout shape consumed by the React Flow viewer (Plan 109-03).
-- The migration also runs a one-shot eager projection for every existing
-- row; per-row failures land in ``workflow_template_migration_errors`` rather
-- than aborting the migration.
--
-- Data model note
-- ---------------
-- ``workflow_templates.phases`` is a JSONB array of phases, each containing
-- a ``steps`` array.  Plan 109-01's projection helpers were specified
-- against a single flat ``steps`` list (per the plan's interfaces block);
-- we satisfy both by **flattening phases.*.steps into a single steps array
-- at the call site** before invoking the helpers.  This keeps the helpers'
-- signatures (``steps jsonb``) honoured and lets Plan 109-02/03 stay
-- agnostic of the phases-vs-steps split.
--
-- Idempotency
-- -----------
-- All ALTER TABLEs use ``IF NOT EXISTS``; helper functions use
-- ``CREATE OR REPLACE``; the eager projection is gated by
-- ``WHERE graph_nodes IS NULL`` so a second run is a no-op.
--
-- See: docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md
--      .planning/phases/109-workflow-node-editor-viewer/109-01-graph-projection-migration-PLAN.md

-- 1. Ensure the pikar schema exists (helper functions live here).
CREATE SCHEMA IF NOT EXISTS pikar;

-- 2. Add graph columns (idempotent).
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS graph_nodes  jsonb;
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS graph_edges  jsonb;
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS graph_layout jsonb;

COMMENT ON COLUMN workflow_templates.graph_nodes IS
    'React Flow node array projected from phases/steps. NULL until the first projection runs.';
COMMENT ON COLUMN workflow_templates.graph_edges IS
    'React Flow edge array (linear: trigger -> step-0 -> ... -> output).';
COMMENT ON COLUMN workflow_templates.graph_layout IS
    'Per-node {x, y} positions used as React Flow initial layout.';

-- 3. Migration error log — per-row projection failures land here without
--    raising, so a single bad row cannot abort the migration.
CREATE TABLE IF NOT EXISTS workflow_template_migration_errors (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id   uuid NOT NULL,
  error_message text NOT NULL,
  errored_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE workflow_template_migration_errors IS
    'Per-row failures captured during the 20260601 graph projection migration. '
    'A non-empty table after deploy = operator should inspect and decide on a backfill strategy.';
