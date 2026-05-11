---
phase: 109-workflow-node-editor-viewer
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - supabase/migrations/20260601000000_workflow_template_graph_projection.sql
  - tests/integration/test_workflow_template_graph_projection.py
autonomous: true
requirements: [NODEEDITOR-MIGRATION-01]

must_haves:
  truths:
    - "workflow_templates table has three new nullable JSONB columns: graph_nodes, graph_edges, graph_layout"
    - "Three Postgres helper functions exist in the pikar schema: pikar.project_steps_to_nodes(steps jsonb) returns jsonb, pikar.project_steps_to_edges(steps jsonb) returns jsonb, pikar.compute_dagre_layout(steps jsonb) returns jsonb. Each is STABLE LANGUAGE plpgsql and returns NULL on NULL/empty input."
    - "After migration, every row in workflow_templates where steps IS NOT NULL AND jsonb_array_length(steps) > 0 has graph_nodes IS NOT NULL — the projection ran successfully"
    - "Projection for a 4-step template [{name:'s1',...}, {name:'s2',...}, {name:'s3',...}, {name:'s4',...}] produces graph_nodes with exactly 6 entries (trigger, s1, s2, s3, s4, output) and graph_edges with exactly 5 entries connecting them in order"
    - "A new workflow_template_migration_errors table exists: (template_id uuid, error_message text, errored_at timestamptz default now()) — errors during projection write here but DO NOT raise; migration completes successfully"
    - "Migration is idempotent: running it a second time is a no-op (no duplicate rows added, no errors). Helper functions use CREATE OR REPLACE; column adds use IF NOT EXISTS"
    - "Rollback path documented in the migration file as a comment: ALTER TABLE workflow_templates DROP COLUMN graph_nodes, DROP COLUMN graph_edges, DROP COLUMN graph_layout; DROP FUNCTION pikar.project_steps_to_nodes; DROP FUNCTION pikar.project_steps_to_edges; DROP FUNCTION pikar.compute_dagre_layout; DROP TABLE workflow_template_migration_errors;"
  artifacts:
    - path: "supabase/migrations/20260601000000_workflow_template_graph_projection.sql"
      provides: "ALTER TABLE adding 3 nullable JSONB columns + CREATE OR REPLACE FUNCTION for 3 projection helpers + CREATE TABLE workflow_template_migration_errors + one-shot UPDATE projecting existing rows + DO BLOCK with EXCEPTION handler that captures per-row errors"
      contains: "pikar.project_steps_to_nodes"
    - path: "tests/integration/test_workflow_template_graph_projection.py"
      provides: "Integration tests against a local Supabase: idempotency, 4-step projection shape, trigger/output node injection, error row writing for malformed steps, graph_layout x/y positions monotone increasing"
      contains: "test_idempotent_rerun"
  key_links:
    - from: "supabase/migrations/20260601000000_workflow_template_graph_projection.sql:ALTER TABLE"
      to: "app/workflows/registry.py:WorkflowTemplate (Plan 02 reads these columns)"
      via: "Adds graph_nodes/graph_edges/graph_layout as JSONB nullable — Pydantic model in Plan 02 picks them up via the existing field-from-row machinery"
      pattern: "ADD COLUMN graph_nodes"
    - from: "supabase/migrations/20260601000000_workflow_template_graph_projection.sql:UPDATE projection"
      to: "frontend/src/components/workflows/editor/NodeCanvas.tsx (Plan 03 renders these)"
      via: "Eager projection populates graph_nodes; Plan 03's NodeCanvas reads them via the API in Plan 02 and feeds React Flow"
      pattern: "UPDATE workflow_templates SET graph_nodes"
---

<objective>
Add the graph_nodes / graph_edges / graph_layout JSONB columns to workflow_templates, create three Postgres helper functions that project a linear `steps` list into graph form, and eagerly populate every existing row's graph fields in a single SQL migration. Errors during projection write to a new workflow_template_migration_errors table without raising. Migration is idempotent.

Purpose: Satisfy NODEEDITOR-MIGRATION-01 (one-shot eager projection per Spec B locked decision #4). Phase 1's frontend (Plan 03) can assume every template row has populated graph fields and skip runtime projection.

Output: Database schema ready for the Plan 02 API extension to expose the new fields, and for the Plan 03 React Flow viewer to consume them.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/109-workflow-node-editor-viewer/109-CONTEXT.md
@docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md
@app/workflows/registry.py
@supabase/migrations/20260511130000_workflow_run_view.sql
@supabase/migrations/20260511130100_workflow_steps_outcome.sql

<interfaces>
<!-- Current WorkflowTemplate.steps shape from app/workflows/registry.py — projection must handle this -->

```python
# Each step in WorkflowTemplate.steps is a dict with these keys:
{
    "name": str,             # e.g. "Generate outline"
    "tool": str,             # e.g. "generate_outline"
    "arguments": dict,       # e.g. {"topic": "{topic}"}
    "agent_role": str | None,
    "human_gated": bool,     # default False
}
```

<!-- Target node shape for graph_nodes (from Spec B § "Graph node shape") -->

```jsonc
[
  { "id": "trigger", "kind": "trigger", "label": "Start" },
  { "id": "step-0", "kind": "agent-action", "label": "<steps[0].name>", "config": { "tool_name": "<steps[0].tool>", "arguments": <steps[0].arguments>, "agent_role": "<steps[0].agent_role>" } },
  // ... one node per step
  { "id": "output", "kind": "output", "label": "Done" }
]
```

<!-- Target edge shape -->

```jsonc
[
  { "id": "e-trigger-step-0", "source": "trigger", "target": "step-0" },
  { "id": "e-step-0-step-1", "source": "step-0", "target": "step-1" },
  // ... one edge per gap
  { "id": "e-step-N-output", "source": "step-N", "target": "output" }
]
```

<!-- Target layout shape (x/y for canvas positions; computed left-to-right) -->

```jsonc
{
  "trigger": { "x": 0,   "y": 0 },
  "step-0":  { "x": 200, "y": 0 },
  "step-1":  { "x": 400, "y": 0 },
  // ... step-N at x = 200 * (N+1)
  "output":  { "x": 200 * (last_step_index + 2), "y": 0 }
}
```
</interfaces>
</context>

<tasks>

<task id="01-01" desc="Add the three JSONB columns to workflow_templates">
Write the column-add portion of `supabase/migrations/20260601000000_workflow_template_graph_projection.sql`:

```sql
-- 1. Add graph columns (idempotent)
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS graph_nodes  jsonb;
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS graph_edges  jsonb;
ALTER TABLE workflow_templates ADD COLUMN IF NOT EXISTS graph_layout jsonb;

-- 2. Migration error log table
CREATE TABLE IF NOT EXISTS workflow_template_migration_errors (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id   uuid NOT NULL,
  error_message text NOT NULL,
  errored_at    timestamptz NOT NULL DEFAULT now()
);
```
</task>

<task id="01-02" desc="Implement the three projection helper functions">
Add to the migration:

```sql
-- 3. Projection helpers
CREATE OR REPLACE FUNCTION pikar.project_steps_to_nodes(steps jsonb)
RETURNS jsonb AS $$
DECLARE
  result jsonb := '[]'::jsonb;
  step   jsonb;
  idx    int := 0;
BEGIN
  IF steps IS NULL OR jsonb_array_length(steps) = 0 THEN
    RETURN NULL;
  END IF;

  result := result || jsonb_build_object('id', 'trigger', 'kind', 'trigger', 'label', 'Start');

  FOR step IN SELECT value FROM jsonb_array_elements(steps)
  LOOP
    result := result || jsonb_build_object(
      'id', 'step-' || idx::text,
      'kind', 'agent-action',
      'label', step->>'name',
      'config', jsonb_build_object(
        'tool_name', step->>'tool',
        'arguments', COALESCE(step->'arguments', '{}'::jsonb),
        'agent_role', step->>'agent_role'
      )
    );
    idx := idx + 1;
  END LOOP;

  result := result || jsonb_build_object('id', 'output', 'kind', 'output', 'label', 'Done');
  RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION pikar.project_steps_to_edges(steps jsonb)
RETURNS jsonb AS $$
DECLARE
  result jsonb := '[]'::jsonb;
  n int;
  i int := 0;
BEGIN
  IF steps IS NULL OR jsonb_array_length(steps) = 0 THEN
    RETURN NULL;
  END IF;

  n := jsonb_array_length(steps);

  -- trigger → step-0
  result := result || jsonb_build_object(
    'id', 'e-trigger-step-0',
    'source', 'trigger',
    'target', 'step-0'
  );

  -- step-i → step-(i+1)
  WHILE i < n - 1 LOOP
    result := result || jsonb_build_object(
      'id', 'e-step-' || i || '-step-' || (i + 1),
      'source', 'step-' || i,
      'target', 'step-' || (i + 1)
    );
    i := i + 1;
  END LOOP;

  -- step-(n-1) → output
  result := result || jsonb_build_object(
    'id', 'e-step-' || (n - 1) || '-output',
    'source', 'step-' || (n - 1),
    'target', 'output'
  );

  RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION pikar.compute_dagre_layout(steps jsonb)
RETURNS jsonb AS $$
DECLARE
  result jsonb := '{}'::jsonb;
  n int;
  i int := 0;
BEGIN
  IF steps IS NULL OR jsonb_array_length(steps) = 0 THEN
    RETURN NULL;
  END IF;

  n := jsonb_array_length(steps);

  result := jsonb_set(result, '{trigger}', jsonb_build_object('x', 0, 'y', 0));

  WHILE i < n LOOP
    result := jsonb_set(result, ARRAY['step-' || i], jsonb_build_object('x', 200 * (i + 1), 'y', 0));
    i := i + 1;
  END LOOP;

  result := jsonb_set(result, '{output}', jsonb_build_object('x', 200 * (n + 1), 'y', 0));
  RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;
```

If the `pikar` schema doesn't already exist, add `CREATE SCHEMA IF NOT EXISTS pikar;` at the top of the migration.
</task>

<task id="01-03" desc="One-shot eager projection with per-row error handling">
Add to the migration:

```sql
-- 4. Eager projection: populate graph columns for every existing row
DO $$
DECLARE
  tmpl  record;
BEGIN
  FOR tmpl IN SELECT id, steps FROM workflow_templates WHERE graph_nodes IS NULL
  LOOP
    BEGIN
      UPDATE workflow_templates SET
        graph_nodes  = pikar.project_steps_to_nodes(tmpl.steps),
        graph_edges  = pikar.project_steps_to_edges(tmpl.steps),
        graph_layout = pikar.compute_dagre_layout(tmpl.steps)
      WHERE id = tmpl.id;
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO workflow_template_migration_errors (template_id, error_message)
      VALUES (tmpl.id, SQLERRM);
    END;
  END LOOP;
END $$;
```

The `WHERE graph_nodes IS NULL` guard ensures re-runs don't overwrite anything already populated — which is what makes the migration idempotent on subsequent runs.
</task>

<task id="01-04" desc="Add a rollback comment block at the end of the migration">
Append to the migration:

```sql
-- ROLLBACK (commented; manual application if needed):
-- ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_nodes;
-- ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_edges;
-- ALTER TABLE workflow_templates DROP COLUMN IF EXISTS graph_layout;
-- DROP FUNCTION IF EXISTS pikar.project_steps_to_nodes(jsonb);
-- DROP FUNCTION IF EXISTS pikar.project_steps_to_edges(jsonb);
-- DROP FUNCTION IF EXISTS pikar.compute_dagre_layout(jsonb);
-- DROP TABLE IF EXISTS workflow_template_migration_errors;
```
</task>

<task id="01-05" desc="Write the integration test file">
Create `tests/integration/test_workflow_template_graph_projection.py`. The test uses the existing Supabase test-client fixture pattern (see `tests/integration/test_*` for examples) and asserts:

1. `test_migration_creates_columns` — after migration runs, `information_schema.columns` shows graph_nodes/graph_edges/graph_layout exist on workflow_templates.
2. `test_4_step_template_projects_to_6_nodes` — insert a row with `steps: [{"name":"s1","tool":"t1"}, {"name":"s2","tool":"t2"}, {"name":"s3","tool":"t3"}, {"name":"s4","tool":"t4"}]`; rerun the eager projection; assert `jsonb_array_length(graph_nodes) = 6`, `jsonb_array_length(graph_edges) = 5`, trigger/output nodes present at ends.
3. `test_4_step_template_layout_monotone_x` — for the same row, assert the x-coordinate is strictly increasing across the 6 nodes (trigger:0, step-0:200, step-1:400, step-2:600, step-3:800, output:1000).
4. `test_idempotent_rerun` — run the eager-projection DO block twice; assert row count in workflow_template_migration_errors stays at 0 and graph_nodes hash is unchanged.
5. `test_malformed_steps_writes_error_row` — insert a row with `steps: '[{"broken": true}]'::jsonb` that would cause the projection to fail (e.g., missing 'name' key — adjust the projection to access non-existent keys via `->>` which returns NULL safely, so this test may need to use a more pathological input like non-array `steps`); assert an error row was written and the migration didn't raise.
6. `test_null_steps_leaves_graph_null` — insert a row with `steps = NULL`; eager projection should leave `graph_nodes` as NULL (the projection functions return NULL on NULL input).
</task>

</tasks>

<verification>
After all 5 tasks complete, run the migration locally:

```bash
supabase db reset --local  # rebuilds DB from migration chain + seed
```

Then:
1. `\d workflow_templates` in psql shows the three new columns.
2. `SELECT count(*) FROM workflow_templates WHERE graph_nodes IS NULL;` returns 0 (all rows projected).
3. `SELECT jsonb_array_length(graph_nodes) FROM workflow_templates LIMIT 1;` returns >= 2 (trigger + output minimum).
4. `pytest tests/integration/test_workflow_template_graph_projection.py -v` — all 6 tests pass.
5. Re-running `supabase db push --local` against the same DB completes with no errors and no new rows in `workflow_template_migration_errors`.
</verification>
