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

-- 4. Projection helpers (pikar schema).
--    All three return NULL on NULL or empty input.  All three are STABLE
--    so Postgres may inline them in plain SELECTs.

CREATE OR REPLACE FUNCTION pikar.project_steps_to_nodes(steps jsonb)
RETURNS jsonb AS $fn$
DECLARE
  result jsonb := '[]'::jsonb;
  step   jsonb;
  idx    int := 0;
BEGIN
  IF steps IS NULL OR jsonb_typeof(steps) <> 'array' OR jsonb_array_length(steps) = 0 THEN
    RETURN NULL;
  END IF;

  -- Trigger sentinel node.
  result := result || jsonb_build_array(
    jsonb_build_object('id', 'trigger', 'kind', 'trigger', 'label', 'Start')
  );

  FOR step IN SELECT value FROM jsonb_array_elements(steps)
  LOOP
    result := result || jsonb_build_array(
      jsonb_build_object(
        'id', 'step-' || idx::text,
        'kind', 'agent-action',
        'label', COALESCE(step->>'name', 'Step ' || (idx + 1)::text),
        'config', jsonb_build_object(
          'tool_name', step->>'tool',
          'arguments', COALESCE(step->'arguments', '{}'::jsonb),
          'agent_role', step->>'agent_role'
        )
      )
    );
    idx := idx + 1;
  END LOOP;

  -- Output sentinel node.
  result := result || jsonb_build_array(
    jsonb_build_object('id', 'output', 'kind', 'output', 'label', 'Done')
  );

  RETURN result;
END;
$fn$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION pikar.project_steps_to_nodes(jsonb) IS
    'Project a linear steps array into [trigger, step-0..step-N, output] node objects. '
    'Returns NULL for NULL or empty input.';

CREATE OR REPLACE FUNCTION pikar.project_steps_to_edges(steps jsonb)
RETURNS jsonb AS $fn$
DECLARE
  result jsonb := '[]'::jsonb;
  n int;
  i int := 0;
BEGIN
  IF steps IS NULL OR jsonb_typeof(steps) <> 'array' OR jsonb_array_length(steps) = 0 THEN
    RETURN NULL;
  END IF;

  n := jsonb_array_length(steps);

  -- trigger -> step-0
  result := result || jsonb_build_array(
    jsonb_build_object(
      'id', 'e-trigger-step-0',
      'source', 'trigger',
      'target', 'step-0'
    )
  );

  -- step-i -> step-(i+1)
  WHILE i < n - 1 LOOP
    result := result || jsonb_build_array(
      jsonb_build_object(
        'id', 'e-step-' || i::text || '-step-' || (i + 1)::text,
        'source', 'step-' || i::text,
        'target', 'step-' || (i + 1)::text
      )
    );
    i := i + 1;
  END LOOP;

  -- step-(n-1) -> output
  result := result || jsonb_build_array(
    jsonb_build_object(
      'id', 'e-step-' || (n - 1)::text || '-output',
      'source', 'step-' || (n - 1)::text,
      'target', 'output'
    )
  );

  RETURN result;
END;
$fn$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION pikar.project_steps_to_edges(jsonb) IS
    'Project a linear steps array into a left-to-right chain of edges. '
    'For N steps, returns N + 1 edges (trigger->step-0, step-i->step-(i+1), step-(n-1)->output).';

CREATE OR REPLACE FUNCTION pikar.compute_dagre_layout(steps jsonb)
RETURNS jsonb AS $fn$
DECLARE
  result jsonb := '{}'::jsonb;
  n int;
  i int := 0;
BEGIN
  IF steps IS NULL OR jsonb_typeof(steps) <> 'array' OR jsonb_array_length(steps) = 0 THEN
    RETURN NULL;
  END IF;

  n := jsonb_array_length(steps);

  -- Trigger at origin.
  result := jsonb_set(result, '{trigger}', jsonb_build_object('x', 0, 'y', 0));

  -- step-i at x = 200 * (i + 1).
  WHILE i < n LOOP
    result := jsonb_set(
      result,
      ARRAY['step-' || i::text],
      jsonb_build_object('x', 200 * (i + 1), 'y', 0),
      true
    );
    i := i + 1;
  END LOOP;

  -- Output one column to the right of the last step.
  result := jsonb_set(result, '{output}', jsonb_build_object('x', 200 * (n + 1), 'y', 0));

  RETURN result;
END;
$fn$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION pikar.compute_dagre_layout(jsonb) IS
    'Compute left-to-right {x, y} layout for trigger + N step nodes + output. '
    'Step-i lands at x = 200 * (i + 1); output at x = 200 * (n + 1).';

-- 5. Helper that flattens the legacy ``phases`` JSONB column (an array of
--    phases, each with a nested ``steps`` array) into a single steps array
--    suitable for the projection helpers above.  Plan 109-01's helper
--    signature is ``(steps jsonb)``; the on-disk column is ``phases``.
--    Centralising the flatten here keeps the helpers oblivious to the
--    phases-vs-steps split.
CREATE OR REPLACE FUNCTION pikar.flatten_phases_to_steps(phases jsonb)
RETURNS jsonb AS $fn$
DECLARE
  flat jsonb := '[]'::jsonb;
  ph   jsonb;
BEGIN
  IF phases IS NULL OR jsonb_typeof(phases) <> 'array' OR jsonb_array_length(phases) = 0 THEN
    RETURN NULL;
  END IF;

  FOR ph IN SELECT value FROM jsonb_array_elements(phases)
  LOOP
    -- A phase may itself be a single step (legacy shape) or carry a
    -- nested ``steps`` array.  Handle both shapes.
    IF ph ? 'steps' AND jsonb_typeof(ph->'steps') = 'array' THEN
      flat := flat || ph->'steps';
    ELSE
      flat := flat || jsonb_build_array(ph);
    END IF;
  END LOOP;

  IF jsonb_array_length(flat) = 0 THEN
    RETURN NULL;
  END IF;

  RETURN flat;
END;
$fn$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION pikar.flatten_phases_to_steps(jsonb) IS
    'Flatten workflow_templates.phases (array of phases-with-steps) into a '
    'single steps array, so the project_steps_to_* helpers can consume it.';

-- 6. Eager projection: populate graph columns for every existing row.
--    Per-row failures land in workflow_template_migration_errors; the
--    migration as a whole completes successfully even if individual rows
--    have malformed phases JSON.  The ``WHERE graph_nodes IS NULL`` guard
--    ensures re-runs are no-ops.
DO $migrate$
DECLARE
  tmpl  record;
  flat  jsonb;
BEGIN
  FOR tmpl IN
    SELECT id, phases
    FROM workflow_templates
    WHERE graph_nodes IS NULL
  LOOP
    BEGIN
      flat := pikar.flatten_phases_to_steps(tmpl.phases);

      UPDATE workflow_templates SET
        graph_nodes  = pikar.project_steps_to_nodes(flat),
        graph_edges  = pikar.project_steps_to_edges(flat),
        graph_layout = pikar.compute_dagre_layout(flat)
      WHERE id = tmpl.id;
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO workflow_template_migration_errors (template_id, error_message)
      VALUES (tmpl.id, SQLERRM);
    END;
  END LOOP;
END
$migrate$;

-- 7. ROLLBACK (commented; manual application if needed)
--    Phase 2 (109-02/109-03) of Spec B will migrate the graph columns onto
--    a workflow_template_versions table; that work supersedes the columns
--    added here. If a full rollback of plan 109-01 is required before then,
--    apply the statements below in order:
--
--      ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_nodes;
--      ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_edges;
--      ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_layout;
--      DROP FUNCTION IF EXISTS pikar.project_steps_to_nodes(jsonb);
--      DROP FUNCTION IF EXISTS pikar.project_steps_to_edges(jsonb);
--      DROP FUNCTION IF EXISTS pikar.compute_dagre_layout(jsonb);
--      DROP FUNCTION IF EXISTS pikar.flatten_phases_to_steps(jsonb);
--      DROP TABLE IF EXISTS workflow_template_migration_errors;
--      -- Optional: DROP SCHEMA pikar (only if no other migration uses it).
