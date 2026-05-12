---
phase: 111-workflow-node-editor-branching-execution
plan: 03
type: execute
wave: 2
depends_on:
  - "111-01"
files_modified:
  - app/workflows/engine.py
  - app/workflows/step_executor.py
  - tests/unit/workflows/test_engine_dispatch.py
  - tests/unit/workflows/test_step_executor_graph_node_id.py
  - tests/unit/workflows/test_advance_workflow_dispatch.py
  - tests/integration/test_branching_workflow_execution.py
  - tests/integration/test_linear_workflow_execution_post_branching.py
autonomous: true
gap_closure: false
risk_note: |
  Plan 03 is 6 tasks (vs 4 originally) after plan-checker iteration 1.
  Blocker #3 (no production call site for decide_next_graph_nodes) required
  adding Task 03-05 (wire dispatch into _advance_workflow + _enqueue_graph_node_step)
  and Task 03-06 (end-to-end integration tests through the production wire).
  This intentionally exceeds the 5-task soft cap, mirroring Phase 110 Plan 04's
  precedent of documenting an over-cap split when the alternative is shipping
  a primitive nothing in production uses. ROADMAP criterion 1 ("a 2-branch
  template, when started, executes via the new graph_executor.py codepath")
  is load-bearing for Phase 111 and cannot be deferred without renegotiating
  the phase scope.
requirements:
  - NODEEDITOR-ENGINE-01
  - NODEEDITOR-COMPAT-01

must_haves:
  truths:
    - "WorkflowEngine has a new helper _load_template_graph(template_version_id) -> dict that fetches graph_nodes/graph_edges from workflow_template_versions for a pinned version (NOT workflow_templates)"
    - "WorkflowEngine has a new dispatch helper requires_graph_executor(graph_nodes) -> bool wired from graph_executor._template_requires_graph_executor"
    - "StepExecutor.execute_step now writes the originating graph node id into step.output_data._execution_meta.graph_node_id when present in step.step_definition (defense — no migration required; node_id flows via JSONB)"
    - "A new method WorkflowEngine.decide_next_graph_nodes(execution_id) -> list[str] computes next-node ids using graph_executor.decide_next_nodes() by: (a) fetching the pinned version's graph_nodes/edges, (b) building execution_context from completed workflow_steps for this execution_id (previous_outcomes keyed by graph_node_id), (c) finding the most-recently completed step's graph_node_id as current_node_id, (d) calling decide_next_nodes()"
    - "WorkflowEngine._advance_workflow is wired: when the execution's pinned template requires the graph executor, _advance_workflow calls decide_next_graph_nodes() and inserts the next workflow_steps rows via _enqueue_graph_node_step (status='running'). For linear templates, _advance_workflow falls through to the existing Edge Function delegation (no change to linear path)."
    - "WorkflowEngine._enqueue_graph_node_step(execution_id, node_id) inserts a workflow_steps row with status='running', step_index = next index in the execution, step_definition derived from the graph node's config + kind, and output_data._execution_meta.graph_node_id = node_id (JSONB workaround per Decision 8 — no migration)"
    - "A linear template (no condition/parallel/merge/human-approval kinds) does NOT trigger the graph dispatcher — requires_graph_executor returns False, _advance_workflow delegates to the Edge Function as before, and the worker loop drives steps through the unchanged step_executor codepath (ROADMAP criterion 2 + 9)"
    - "A template with one condition node, evaluated against a synthetic previous_outcomes context, returns the correct 'true' OR 'false' branch's outgoing edge target (ROADMAP criterion 1 — unit-tested in Task 03-02; production-wired in Task 03-05)"
    - "An end-to-end integration test creates a 2-branch template, starts execution via the EXISTING WorkflowEngine.start_workflow public method (RPC pins template_version_id), then drives _advance_workflow against a seeded completed condition step and asserts the correct branch's workflow_steps row is inserted via _enqueue_graph_node_step (ROADMAP criterion 1 end-to-end through the production wire)"
    - "A non-regression end-to-end test starts a linear template via WorkflowEngine.start_workflow, calls _advance_workflow, and asserts the Edge Function delegation path fires (no graph_executor calls, no new workflow_steps rows inserted by Python — the EF continues to own linear orchestration) (ROADMAP criterion 9)"
    - "Spec A's OutcomeWriter and event_bus are NOT modified — the new dispatch path reuses them as-is. A signature-guard test pins OutcomeWriter.write_for_step's actual parameter names (self, step_id, tool_output, status, tool_name, duration_ms, error_message) (ROADMAP criterion 10)"
    - "The atomic RPC start_workflow_execution_atomic continues to pin template_version_id (Phase 110 Plan 02's signature) — Plan 03 does NOT modify the RPC or the migration"
    - "Cycle detection at engine start is NOT added in this plan (ROADMAP criterion 11 — deferred to Phase 4). The save-time rule 3 (Phase 110) + rule 4 (Plan 02) are the guards; _enqueue_graph_node_step assumes acyclic input"
  artifacts:
    - path: "app/workflows/engine.py"
      provides: "Dispatch helpers + decide_next_graph_nodes + _load_template_graph + _enqueue_graph_node_step + wired _advance_workflow"
      contains: "decide_next_graph_nodes"
    - path: "app/workflows/step_executor.py"
      provides: "graph_node_id propagation into output_data._execution_meta"
      contains: "graph_node_id"
    - path: "tests/unit/workflows/test_engine_dispatch.py"
      provides: "Unit tests for requires_graph_executor + decide_next_graph_nodes (mock supabase client)"
      min_lines: 200
    - path: "tests/unit/workflows/test_step_executor_graph_node_id.py"
      provides: "Unit test for graph_node_id flow into _execution_meta"
      min_lines: 80
    - path: "tests/unit/workflows/test_advance_workflow_dispatch.py"
      provides: "Unit tests for the wired _advance_workflow path (graph vs linear) + _enqueue_graph_node_step"
      min_lines: 200
    - path: "tests/integration/test_branching_workflow_execution.py"
      provides: "End-to-end branching test through production wire (start_workflow → _advance_workflow → workflow_steps insert) (ROADMAP criterion 1)"
      min_lines: 200
    - path: "tests/integration/test_linear_workflow_execution_post_branching.py"
      provides: "Non-regression integration test (linear path unchanged) + OutcomeWriter signature guard (ROADMAP criterion 2 + 9 + 10)"
      min_lines: 120
  key_links:
    - from: "app/workflows/engine.py"
      to: "app.workflows.graph_executor"
      via: "from app.workflows.graph_executor import decide_next_nodes, _template_requires_graph_executor"
      pattern: "from app.workflows.graph_executor"
    - from: "app/workflows/engine.py:_load_template_graph"
      to: "workflow_template_versions table"
      via: "supabase client .select('graph_nodes, graph_edges').eq('id', template_version_id)"
      pattern: "workflow_template_versions"
    - from: "app/workflows/engine.py:_advance_workflow"
      to: "WorkflowEngine.decide_next_graph_nodes + _enqueue_graph_node_step"
      via: "if requires_graph_executor(graph_nodes): for node_id in decide_next_graph_nodes(...): await _enqueue_graph_node_step(...)"
      pattern: "decide_next_graph_nodes|_enqueue_graph_node_step"
    - from: "app/workflows/step_executor.py:_finalize_step"
      to: "workflow_steps.output_data._execution_meta.graph_node_id"
      via: "JSONB write — graph_node_id read from step.get('step_definition', {}).get('graph_node_id')"
      pattern: "graph_node_id"
    - from: "app/workflows/engine.py:_enqueue_graph_node_step"
      to: "workflow_steps INSERT"
      via: "client.table('workflow_steps').insert({status: 'running', output_data: {_execution_meta: {graph_node_id: ...}}, ...})"
      pattern: "_enqueue_graph_node_step"
---

<objective>
Wire `graph_executor` (Plan 01) into `WorkflowEngine` so that templates whose graph contains non-linear node kinds dispatch through JSONLogic-driven routing, while linear templates continue to run via the existing Edge Function delegation unchanged. Adds `requires_graph_executor()` dispatch helper, `_load_template_graph(template_version_id)` to fetch graphs from `workflow_template_versions` (pinned per Phase 110 Plan 02), `decide_next_graph_nodes(execution_id)` that builds the execution context from completed `workflow_steps` and calls `decide_next_nodes`, and — critically — wires `_advance_workflow` to actually CALL the dispatcher and insert the next `workflow_steps` row via `_enqueue_graph_node_step`. The worker's existing `get_runnable_steps` polling loop then picks up the inserted row and routes it through `step_executor` unchanged. Bridges graph node ids into the existing `workflow_steps` rows via `output_data._execution_meta.graph_node_id` — no schema migration needed.

Purpose: Close ROADMAP criteria 1 (branching end-to-end **through a real production call site**), 2 (dispatch on non-linear kinds), 7 (execution context fully populated), 9 (no regression on linear runs), and 10 (Spec A unchanged). Iteration 1 of plan-checker flagged that shipping the primitives without a production wire would deliver a dispatch primitive that nothing in production uses; this plan now ships the full wire end-to-end.

Output: Surgical edits to `engine.py` (~150 new lines for helpers + the wired `_advance_workflow` + `_enqueue_graph_node_step`), one surgical edit to `step_executor.py` (~5-10 lines to propagate graph_node_id), 5 new test files totaling ~75 tests + a real end-to-end integration test, no SQL migration, no router changes, no Edge Function changes.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-CONTEXT.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-01-backend-graph-executor-PLAN.md
@.planning/phases/110-workflow-node-editor-editable/110-02-SUMMARY.md
@app/workflows/engine.py
@app/workflows/step_executor.py
@app/workflows/graph_executor.py
@app/workflows/worker.py
@app/workflows/outcome_writer.py
@CLAUDE.md

<interfaces>
<!-- Plan 01 (Wave 1) output — verify these names match what shipped before depending on them. -->

```python
# app/workflows/graph_executor.py (from Plan 01)

NON_LINEAR_KINDS: frozenset[str]  # {"condition", "parallel", "merge", "human-approval"}

class ExecutionContext(TypedDict):
    previous_outcomes: dict[str, Any]   # keyed by graph node id
    current_step: dict[str, Any]
    user_context: dict[str, Any]

class GraphExecutorError(Exception): ...

def _template_requires_graph_executor(graph_nodes: list[dict]) -> bool: ...

def decide_next_nodes(
    graph_nodes: list[dict],
    graph_edges: list[dict],
    *,
    current_node_id: str,
    execution_context: ExecutionContext,
    completed_node_ids: set[str],
) -> list[str]: ...
```

<!-- Phase 110 Plan 02 output — engine state Plan 03 starts from. -->

```python
# app/workflows/engine.py (Phase 110 Plan 02, line ~642)

class WorkflowEngine:
    async def _get_client(self): ...  # canonical async supabase client

    async def start_workflow(...) -> dict[str, Any]:
        # ...
        # Phase 110 Plan 02 already pins template_version_id:
        rpc_params = {
            "p_user_id": user_id,
            "p_template_id": template["id"],
            "p_template_version": template.get("version"),
            ...
            "p_template_version_id": template.get("current_version_id"),  # NEW
        }
        res_exec = await client.rpc(
            "start_workflow_execution_atomic", rpc_params
        ).execute()
        # ...
        # Then delegates to Edge Function to start orchestration:
        trigger_result = await edge_function_client.execute_workflow(
            execution_id, action="start"
        )
        # ...

    # list_templates already SELECTs current_version_id (Plan 110-02)

    # _advance_workflow at line ~1587 is currently a SHIM that delegates to the
    # Edge Function. Plan 03 wires it: graph-executor templates hit the new
    # Python dispatch; linear templates continue to delegate to the EF.
    async def _advance_workflow(
        self, execution: dict, phases: list[dict]
    ) -> dict[str, Any]:
        client = await self._get_client()
        await edge_function_client.execute_workflow(execution["id"], action="advance")
        return {"status": "processing", "message": "Workflow advancement triggered"}
```

```python
# app/workflows/step_executor.py (existing — Phase 109/110)

class StepExecutor:
    async def execute_step(self, step: dict, workflow_engine=None) -> dict[str, Any]:
        # step contains: id, tool_name, execution_id, step_definition (dict),
        # workflow_executions (joined row), input_data, prev_step_output, ...
        # _finalize_step writes output_data into workflow_steps row.

    async def _finalize_step(
        self,
        *,
        step: dict[str, Any],
        status: str,
        tool_output: Any,
        duration_ms: int,
        error_message: str | None,
    ) -> None:
        # Writes outcome_text via OutcomeWriter, publishes SSE event
        # 'workflow.step.{status}' on channel 'workflow.execution.{exec_id}'
```

```python
# app/workflows/outcome_writer.py (Spec A — DO NOT MODIFY)

class OutcomeWriter:
    def __init__(self, client: Any | None = None) -> None: ...

    async def write_for_step(
        self,
        *,
        step_id: str,
        tool_output: Any,
        status: str,
        tool_name: str,
        duration_ms: int,
        error_message: str | None = None,
    ) -> None: ...
    # PUBLIC parameter names: step_id, tool_output, status, tool_name, duration_ms, error_message
    # ("text" and "source" are INTERNAL _derive() return values, NOT params.)
```

```python
# app/workflows/worker.py (Phase 109 — DO NOT MODIFY)

class WorkflowWorker:
    async def get_runnable_steps(self) -> list[dict]:
        # Polls workflow_steps WHERE status = 'running', joins with template.
        # Plan 03's _enqueue_graph_node_step inserts rows with status='running'
        # so this same poll picks up graph-dispatched steps without any worker change.
```

```sql
-- workflow_template_versions (Phase 110 Plan 01)
-- Columns: id, template_id, version_number, parent_version_id,
--          graph_nodes (JSONB), graph_edges (JSONB), graph_layout (JSONB),
--          saved_by_user_id, saved_at, comment
-- UNIQUE (template_id, version_number)

-- workflow_executions
-- template_version_id UUID (Phase 110 Plan 01, pinning column)

-- workflow_steps (Plan 03 does NOT add a node_id column — graph_node_id
-- goes inside output_data._execution_meta JSONB, no migration)
-- Columns (per supabase/migrations/0007_workflow_steps.sql +
--          20260425183000_reconcile_workflow_steps_runtime_schema.sql):
--   id, execution_id, step_index, phase_index, phase_name, step_name,
--   status, started_at, completed_at, input_data, output_data (JSONB),
--   error_message, attempt_count, idempotency_key, outcome_text, outcome_source
```
</interfaces>

<context_notes>
**No new migrations.** This plan does NOT add a `node_id` column to `workflow_steps`. Instead, Plan 03 stores the graph node UUID in `output_data._execution_meta.graph_node_id` (JSONB). See CONTEXT.md decision 8 (updated 2026-05-12) for the canonical decision.

**Wiring decision (BLOCKER #3 fix from plan-checker iteration 1):**

The original Plan 03 draft shipped `decide_next_graph_nodes` as a primitive with no production caller — only an integration test invoked it directly. That would mean ROADMAP criterion 1 ("a 2-branch template, when started, executes via the new graph_executor.py codepath") was NOT actually closed by Phase 111. The fix is to wire the dispatcher into a real production call site so branched templates execute end-to-end.

**The production wire:**

- `WorkflowEngine._advance_workflow` is currently a thin shim that delegates to the Edge Function for ALL templates (line ~1587 in `engine.py`). Plan 03 rewrites it to:
  1. Check `requires_graph_executor(graph_nodes)` for the execution's pinned template version.
  2. If graph executor required: call `decide_next_graph_nodes(execution_id)`; for each next node id, insert a `workflow_steps` row via `_enqueue_graph_node_step`. RETURN — skip the EF delegation entirely for graph templates.
  3. If linear template (or no pinned version): fall through to the existing `edge_function_client.execute_workflow(execution["id"], action="advance")` call. The EF continues to own linear orchestration.

- `_enqueue_graph_node_step(execution_id, node_id)` is the new helper that does the INSERT. It:
  - Computes the next `step_index` by querying `MAX(step_index)+1` for the execution (or simply COUNT of existing steps).
  - Loads the graph node's `kind` and `config` from the pinned template version's `graph_nodes`.
  - Derives `step_definition` from the node:
    - `agent-action`: `step_definition = {"tool": node.config["tool_name"], "name": node.label, "graph_node_id": node.id, ...other config keys}`. The worker's `get_runnable_steps` will resolve the tool and `step_executor` runs it.
    - `condition`: `step_definition = {"name": node.label, "graph_node_id": node.id, "kind": "condition", "config": node.config}`. The condition node row exists for SSE visibility but completes immediately with no tool — `_advance_workflow` re-fires on its completion and `decide_next_graph_nodes` consumes the condition's `config.expression` to choose the next branch. (For Phase 111 simplicity, the inserted condition row is marked `status='completed'` immediately with a synthetic `output_data._execution_meta = {graph_node_id, kind: 'condition'}` so the next call to `_advance_workflow` finds it.)
    - `output`: `step_definition = {"name": node.label, "graph_node_id": node.id, "kind": "output"}`; insert with `status='completed'` and on insert mark the parent execution `status='completed'` (terminal node).
    - `trigger`: not enqueued; triggers are entry points, not work units.
    - `parallel`/`merge`/`human-approval`: NotImplementedError — Phase 4 work. Document and return.
  - Inserts via `client.table("workflow_steps").insert({...}).execute()`.

- For the condition node case, the immediate self-complete is the simplest Phase 111 approach. The worker doesn't need to run condition logic — the engine does it in-process when `_advance_workflow` is next called by the step that completed before the condition. Concretely the flow is:
  1. Agent-action a1 completes → step_executor calls workflow_engine._advance_workflow.
  2. _advance_workflow detects graph template; calls decide_next_graph_nodes (current_node_id=a1, returns c1).
  3. _enqueue_graph_node_step inserts a condition row for c1 with status='completed' (immediate).
  4. _advance_workflow re-evaluates (or recurses) → decide_next_graph_nodes (current=c1, evaluates expression with a1's outcome, returns t-out).
  5. _enqueue_graph_node_step inserts the t-out output row with status='completed' → marks execution complete.

  To avoid unbounded recursion, `_advance_workflow` loops over the dispatcher result and only stops when the next-node list contains an `agent-action` (which needs the worker to run) or is empty. Implementation detail: bound the loop with a `max_iterations = len(graph_nodes)` safety to prevent infinite loops in case of save-time validation gaps.

**Why this design works without EF changes:**

The EF's role is ONLY to start workflows and advance linear ones. For graph templates, the Python engine takes full ownership of "decide what runs next + create the workflow_steps row". The worker (`worker.py:get_runnable_steps`) polls for `status='running'` rows regardless of how they got there — so a graph-dispatched agent-action step is indistinguishable to the worker from a linear one. The runtime path through `step_executor.execute_step` is identical; only the "what comes next" decision differs.

**Execution-context build pattern (Plan 03 owns this — same as original draft):**

```python
async def decide_next_graph_nodes(self, execution_id: str) -> list[str]:
    client = await self._get_client()

    # 1. Fetch execution + pinned version
    exec_res = await (
        client.table("workflow_executions")
        .select("id, template_version_id, context")
        .eq("id", execution_id)
        .single()
        .execute()
    )
    execution = exec_res.data
    template_version_id = execution.get("template_version_id")
    if not template_version_id:
        return []

    # 2. Load pinned graph
    graph_nodes, graph_edges = await self._load_template_graph(template_version_id)

    # 3. Dispatch decision
    if not self.requires_graph_executor(graph_nodes):
        return []

    # 4. Build previous_outcomes from completed steps
    steps_res = await (
        client.table("workflow_steps")
        .select("id, status, output_data, completed_at")
        .eq("execution_id", execution_id)
        .eq("status", "completed")
        .order("completed_at")
        .execute()
    )
    completed_node_ids: set[str] = set()
    previous_outcomes: dict[str, Any] = {}
    current_node_id: str | None = None
    for row in steps_res.data or []:
        meta = (row.get("output_data") or {}).get("_execution_meta") or {}
        node_id = meta.get("graph_node_id")
        if not node_id:
            continue
        completed_node_ids.add(node_id)
        previous_outcomes[node_id] = row.get("output_data") or {}
        current_node_id = node_id  # last one wins (rows are ordered)

    if current_node_id is None:
        # No steps completed yet — start from the trigger node
        triggers = [n for n in graph_nodes if n.get("kind") == "trigger"]
        if not triggers:
            return []
        current_node_id = triggers[0]["id"]

    # 5. Build context dict
    context: ExecutionContext = {
        "previous_outcomes": previous_outcomes,
        "current_step": {"node_id": current_node_id},
        "user_context": execution.get("context") or {},
    }

    # 6. Delegate
    return decide_next_nodes(
        graph_nodes,
        graph_edges,
        current_node_id=current_node_id,
        execution_context=context,
        completed_node_ids=completed_node_ids,
    )
```

**StepExecutor graph_node_id propagation (~5 line edit):**

In `app/workflows/step_executor.py`, `_finalize_step` (line ~730 in the current file) calls `OutcomeWriter.write_for_step(...)`. The graph_node_id flows via a separate path: when the executor writes `output_data` back to `workflow_steps`, it needs to include `_execution_meta.graph_node_id` if `step.step_definition` has it. Find the section where `output_data` is finalized (look for `_execution_meta` literal or the step row UPDATE; Phase 111 inspects the live file).

**Spec A non-regression (ROADMAP criterion 10):** `OutcomeWriter` and `event_bus.publish_workflow_event` are NOT modified. Verify by `grep -rn "OutcomeWriter\|publish_workflow_event" app/workflows/engine.py app/workflows/step_executor.py app/workflows/graph_executor.py` — references are unchanged from Phase 110.

**OutcomeWriter signature pin (BLOCKER #1 fix from plan-checker iteration 1):**

The original Plan 03 Task 03-04 signature-guard test asserted `"text" in params and "source" in params` — those are `_derive()` INTERNAL return values, NOT public method parameters. The actual `OutcomeWriter.write_for_step` signature (verified against `app/workflows/outcome_writer.py:30-39` on 2026-05-12) is:

```python
async def write_for_step(
    self,
    *,
    step_id: str,
    tool_output: Any,
    status: str,
    tool_name: str,
    duration_ms: int,
    error_message: str | None = None,
) -> None
```

The corrected pin is in Task 03-04 below.

**Branch hygiene:** `git branch --show-current` before every commit — `plan-109-spec-b-phase-1`.

**CLAUDE.md conventions:** Async-throughout backend (engine.py is fully async), uv, Ruff, ty, Google-style docstrings, NO bare except, NO print.
</context_notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 03-01: Engine dispatch helpers (requires_graph_executor + _load_template_graph)</name>
  <files>app/workflows/engine.py, tests/unit/workflows/test_engine_dispatch.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`.
    Verify Plan 01 is shipped: `.venv/Scripts/python -c "from app.workflows.graph_executor import _template_requires_graph_executor, decide_next_nodes, GraphExecutorError, NON_LINEAR_KINDS; print('OK')"`.
  </precondition>
  <behavior>
    **RED — `tests/unit/workflows/test_engine_dispatch.py`, ≥10 tests:**

    1. `test_requires_graph_executor_linear_returns_false` — calls `WorkflowEngine().requires_graph_executor([{id, kind:'trigger'}, {id, kind:'agent-action'}, {id, kind:'output'}])` → False.
    2. `test_requires_graph_executor_with_condition_returns_true` — condition kind triggers True.
    3. `test_requires_graph_executor_with_parallel_returns_true` — parallel kind triggers True.
    4. `test_requires_graph_executor_with_merge_returns_true` — merge kind triggers True.
    5. `test_requires_graph_executor_with_human_approval_returns_true` — human-approval kind triggers True.
    6. `test_requires_graph_executor_empty_graph_returns_false` — empty list → False.
    7. `test_load_template_graph_fetches_from_versions_table` — mock supabase client; assert `.table("workflow_template_versions").select(...)` is called with the version_id (NOT workflow_templates).
    8. `test_load_template_graph_returns_nodes_and_edges` — mock returns a row with graph_nodes + graph_edges; helper returns the tuple `(nodes_list, edges_list)`.
    9. `test_load_template_graph_returns_empty_when_version_not_found` — mock returns empty data → returns `([], [])` (graceful for legacy templates with NULL current_version_id).
    10. `test_load_template_graph_handles_null_graph_fields` — mock returns `{graph_nodes: None, graph_edges: None}` → returns `([], [])`.

    Mock pattern from Phase 110 Plan 02 (see `tests/unit/workflows/test_template_versions_engine.py`):
    ```python
    from unittest.mock import AsyncMock, MagicMock, patch

    @patch("app.workflows.engine.WorkflowEngine._get_client")
    async def test_xxx(mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        # ... configure .table().select().eq().single().execute() chain ...
    ```

    Commit RED: `test(111-03): add failing tests for engine dispatch helpers`.

    **GREEN — extend `app/workflows/engine.py`:**

    Add at module-top (with other imports):
    ```python
    from app.workflows.graph_executor import (
        GraphExecutorError,
        _template_requires_graph_executor,
        decide_next_nodes,
    )
    ```

    Add inside `class WorkflowEngine`:
    ```python
    def requires_graph_executor(self, graph_nodes: list[dict[str, Any]]) -> bool:
        """Delegate to graph_executor module helper. Discretion #5 Option A: any
        non-linear node kind in graph_nodes flips dispatch from step_executor to
        graph_executor.

        Args:
            graph_nodes: list of node dicts (id, kind, label, config, ...)

        Returns:
            True when graph_nodes contains any of condition / parallel / merge /
            human-approval; False otherwise (linear graph, linear executor).
        """
        return _template_requires_graph_executor(graph_nodes)

    async def _load_template_graph(
        self, template_version_id: str | None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch graph_nodes + graph_edges from workflow_template_versions for
        the pinned version.

        Args:
            template_version_id: UUID from workflow_executions.template_version_id
                (Phase 110 Plan 02 pinning column). May be None for legacy
                executions started before Phase 110 shipped — returns ([], [])
                so the linear-path fallback runs.

        Returns:
            Tuple (nodes, edges). Both empty when version not found / NULL.
        """
        if not template_version_id:
            return [], []
        client = await self._get_client()
        try:
            res = await (
                client.table("workflow_template_versions")
                .select("graph_nodes, graph_edges")
                .eq("id", template_version_id)
                .single()
                .execute()
            )
        except Exception:  # postgrest returns when row missing
            logger.warning(
                "workflow_template_versions row not found: %s",
                template_version_id,
            )
            return [], []
        data = res.data if res else None
        if not data:
            return [], []
        return (data.get("graph_nodes") or []), (data.get("graph_edges") or [])
    ```

    Commit GREEN: `feat(111-03): add WorkflowEngine.requires_graph_executor + _load_template_graph`.

    Verify: 10 new tests GREEN. 16 Phase 110 Plan 02 engine tests still GREEN (`tests/unit/workflows/test_template_versions_engine.py`). Ruff + ty clean.
  </behavior>
  <action>
    Follow the behavior block. Mirror the mock-supabase pattern from Phase 110 Plan 02's test files for credibility. Use the canonical `from app.services.supabase_client import get_async_client` chain if needed (engine.py already has `_get_client()` — use that, NOT the deprecated `supabase` shim).
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/test_engine_dispatch.py -v --tb=short</automated>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/test_template_versions_engine.py -v --tb=short -q</automated>
    <automated>.venv/Scripts/python -m ruff check app/workflows/engine.py tests/unit/workflows/test_engine_dispatch.py</automated>
  </verify>
  <done>
    - `WorkflowEngine.requires_graph_executor` + `WorkflowEngine._load_template_graph` exist with docstrings.
    - 10 new tests in `test_engine_dispatch.py` GREEN.
    - 16 Phase 110 Plan 02 engine tests still GREEN.
    - Two commits on `plan-109-spec-b-phase-1` (RED, GREEN).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-02: Engine decide_next_graph_nodes + graph_node_id flow in StepExecutor</name>
  <files>app/workflows/engine.py, app/workflows/step_executor.py, tests/unit/workflows/test_engine_dispatch.py, tests/unit/workflows/test_step_executor_graph_node_id.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 03-01 is committed.
  </precondition>
  <behavior>
    **RED phase — additional tests:**

    APPEND to `tests/unit/workflows/test_engine_dispatch.py` (≥8 more tests):

    1. `test_decide_next_graph_nodes_linear_returns_empty` — mock execution with linear template (NON_LINEAR_KINDS absent in graph_nodes) → returns `[]` (caller falls back to step_executor).
    2. `test_decide_next_graph_nodes_no_steps_starts_from_trigger` — mock execution with branching template, zero completed workflow_steps → current_node_id auto-resolves to the trigger node id; verifies return list is the trigger's outgoing edges.
    3. `test_decide_next_graph_nodes_condition_true_branch` — mock: execution has 1 completed step (agent-action) with `_execution_meta.graph_node_id='a1'`; graph has trigger→agent-action(a1)→condition(c1) with edges to t-out (handle 'true') and f-out (handle 'false'); previous_outcomes builds with a1's output_data; condition config evaluates truthy → returns `['t-out']`.
    4. `test_decide_next_graph_nodes_condition_false_branch` — same but evaluates falsy → returns `['f-out']`.
    5. `test_decide_next_graph_nodes_missing_template_version_id_returns_empty` — execution row has `template_version_id=None` (legacy) → returns `[]` (linear fallback).
    6. `test_decide_next_graph_nodes_user_context_propagated` — mock execution has `context={"user_var": 42}`; condition expression uses `{"var": "user_var"}` → routes correctly. Verifies ROADMAP criterion 7 (user_context is reachable).
    7. `test_decide_next_graph_nodes_previous_outcomes_keyed_by_graph_node_id` — mock 2 completed steps, both with distinct graph_node_id values in _execution_meta; assert previous_outcomes dict has both keys.
    8. `test_decide_next_graph_nodes_raises_on_malformed_condition` — condition config missing 'expression' → propagates GraphExecutorError out of decide_next_graph_nodes (caller handles).

    Create `tests/unit/workflows/test_step_executor_graph_node_id.py` with ≥3 tests:

    1. `test_step_executor_writes_graph_node_id_to_execution_meta` — construct a step dict with `step_definition = {"graph_node_id": "node-uuid-123", ...}`; execute_step (mocked tool); assert the workflow_steps update call carries `output_data._execution_meta.graph_node_id == "node-uuid-123"`.
    2. `test_step_executor_omits_graph_node_id_when_not_set` — step_definition without graph_node_id; assert `_execution_meta.graph_node_id` is NOT present (or is None) — no regression for linear runs.
    3. `test_step_executor_preserves_other_execution_meta` — existing fields (trust_class, tool_name, etc.) still present alongside the new graph_node_id field — no regression in the meta dict shape.

    Commit RED: `test(111-03): add failing tests for decide_next_graph_nodes + graph_node_id flow`.

    **GREEN phase — implement:**

    In `app/workflows/engine.py`, add method (after `_load_template_graph`):

    ```python
    async def decide_next_graph_nodes(
        self, execution_id: str
    ) -> list[str]:
        """Compute the next graph node id(s) to execute, given the current
        state of workflow_steps for this execution.

        Returns [] when:
          - the execution's template is linear (caller routes to step_executor)
          - the execution has no pinned template_version_id (legacy/linear)
          - the version row is not found / has empty graph

        Otherwise delegates to graph_executor.decide_next_nodes() with an
        ExecutionContext built from:
          - previous_outcomes: keyed by graph_node_id from each completed
            workflow_steps row's output_data._execution_meta.graph_node_id
          - current_step: {node_id: most-recently-completed graph_node_id}
            (falls back to the trigger node when no steps have completed)
          - user_context: workflow_executions.context dict (start-time inputs)

        Raises GraphExecutorError if a current_node_id cannot be resolved or
        if a condition node has malformed expression (propagated from
        decide_next_nodes).
        """
        client = await self._get_client()
        exec_res = await (
            client.table("workflow_executions")
            .select("id, template_version_id, context")
            .eq("id", execution_id)
            .single()
            .execute()
        )
        execution = (exec_res.data if exec_res else None) or {}
        template_version_id = execution.get("template_version_id")
        if not template_version_id:
            return []

        graph_nodes, graph_edges = await self._load_template_graph(
            template_version_id
        )
        if not self.requires_graph_executor(graph_nodes):
            return []

        steps_res = await (
            client.table("workflow_steps")
            .select("id, status, output_data, completed_at")
            .eq("execution_id", execution_id)
            .eq("status", "completed")
            .order("completed_at")
            .execute()
        )
        completed_node_ids: set[str] = set()
        previous_outcomes: dict[str, Any] = {}
        current_node_id: str | None = None
        for row in steps_res.data or []:
            output_data = row.get("output_data") or {}
            meta = (
                output_data.get("_execution_meta")
                if isinstance(output_data, dict)
                else {}
            ) or {}
            node_id = meta.get("graph_node_id")
            if not node_id:
                continue
            completed_node_ids.add(node_id)
            previous_outcomes[node_id] = output_data
            current_node_id = node_id

        if current_node_id is None:
            triggers = [n for n in graph_nodes if n.get("kind") == "trigger"]
            if not triggers:
                return []
            current_node_id = triggers[0]["id"]

        context_payload: dict[str, Any] = {
            "previous_outcomes": previous_outcomes,
            "current_step": {"node_id": current_node_id},
            "user_context": execution.get("context") or {},
        }
        return decide_next_nodes(
            graph_nodes,
            graph_edges,
            current_node_id=current_node_id,
            execution_context=context_payload,  # type: ignore[arg-type]
            completed_node_ids=completed_node_ids,
        )
    ```

    In `app/workflows/step_executor.py`, find the section building `output_data._execution_meta` (look for `_execution_meta` literal in the file). Add a surgical edit:

    ```python
    # In _finalize_step or wherever execution_meta is assembled, after
    # existing keys are set:
    graph_node_id = (step.get("step_definition") or {}).get("graph_node_id")
    if graph_node_id:
        execution_meta["graph_node_id"] = graph_node_id
    ```

    This is purely additive — linear runs never set graph_node_id on step_definition so the new key is absent and existing test assertions don't change.

    Commit GREEN: `feat(111-03): WorkflowEngine.decide_next_graph_nodes + StepExecutor graph_node_id flow`.

    Verify all tests GREEN. 8 new + 3 new step_executor tests + 10 Task 03-01 tests + Phase 110 16 engine tests + Phase 109 + 110-02-03-04-05 tests = NO regression.
  </behavior>
  <action>
    Follow the behavior block. Mock supabase clients per Phase 110 Plan 02's patterns. After both phases (RED + GREEN), run the broader test suite to catch any unintended regression: `.venv/Scripts/python -m pytest tests/unit/workflows/ -v -q --tb=short`.
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/test_engine_dispatch.py tests/unit/workflows/test_step_executor_graph_node_id.py -v --tb=short</automated>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/ -v -q --no-header --tb=line</automated>
    <automated>.venv/Scripts/python -m ruff check app/workflows/engine.py app/workflows/step_executor.py tests/unit/workflows/test_engine_dispatch.py tests/unit/workflows/test_step_executor_graph_node_id.py</automated>
    <automated>grep -c "graph_node_id" app/workflows/step_executor.py</automated>
  </verify>
  <done>
    - `WorkflowEngine.decide_next_graph_nodes` async method exists with docstring.
    - `StepExecutor` propagates `graph_node_id` from `step.step_definition` into `output_data._execution_meta` (when present).
    - 18 total tests in `test_engine_dispatch.py` GREEN (10 from Task 03-01 + 8 from Task 03-02).
    - 3 tests in `test_step_executor_graph_node_id.py` GREEN.
    - All Phase 110 + Phase 109 unit tests still GREEN.
    - Two commits on `plan-109-spec-b-phase-1` (RED, GREEN).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-03: Dispatcher unit-level branching test (no DB) — ROADMAP criterion 1 primitive coverage</name>
  <files>tests/integration/test_branching_workflow_execution.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 03-01 + 03-02 committed.
  </precondition>
  <behavior>
    Create `tests/integration/test_branching_workflow_execution.py` (~150 lines, ≥2 tests, SKIP cleanly without SUPABASE creds — match Phase 110 Plan 02's integration test pattern at `tests/integration/test_linear_workflow_execution_post_versioning.py`).

    This task covers ROADMAP criterion 1 at the dispatcher-primitive level. Task 03-06 covers the same criterion through the PRODUCTION WIRE (start_workflow → _advance_workflow → workflow_steps INSERT) for end-to-end confidence.

    Both tests follow this pattern:
    1. Skip if SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY absent (use the same pytest.skip pattern as Phase 110).
    2. Create a fresh test template directly in the DB (INSERT into `workflow_templates` + `workflow_template_versions` v1 with the branching graph).
    3. Insert a `workflow_executions` row pinned to that template_version_id.
    4. Insert seed `workflow_steps` rows representing completed upstream steps with `output_data._execution_meta.graph_node_id` set + `output_data.lead_score` (or similar) set in the parent dict.
    5. Call `WorkflowEngine().decide_next_graph_nodes(execution_id)` and assert the returned list contains the correct branch's target node id.
    6. Cleanup: DELETE the test rows on teardown (or use a transactional test fixture if the project has one).

    **Test 1: `test_dispatcher_routes_to_true_branch_when_expression_truthy`**

    Graph design:
    - t1 (trigger)
    - a1 (agent-action, simulating an upstream step that produces lead_score)
    - c1 (condition, config.expression = `{">": [{"var": "lead_score"}, 50]}` — using direct var reference; or use `{">": [{"var": "previous_outcomes.a1.lead_score"}, 50]}` if previous_outcomes dotted-path resolution is supported by Plan 01)
    - t-out (output) on 'true' branch
    - f-out (output) on 'false' branch
    Edges: t1→a1, a1→c1, c1→t-out (handle 'true'), c1→f-out (handle 'false')

    Seed approach: seed 2 completed workflow_steps rows — one for a1 (graph_node_id=a1, output_data has lead_score=75 at top level OR nested per the expression's var path), and one for c1 (graph_node_id=c1, marking the condition as "just evaluated").

    Assertion:
    - `decide_next_graph_nodes(execution_id)` (called with current = c1, latest completed) evaluates the expression against the merged context and returns `['t-out']`.

    **Test 2: `test_dispatcher_routes_to_false_branch_when_expression_falsy`**

    Same graph, but seed a1's lead_score = 25. Assertion: `next_nodes == ['f-out']`.

    Both tests CLEANUP DB rows on teardown (try/finally with DELETE).

    Commit: `test(111-03): dispatcher-level branching integration test (ROADMAP criterion 1 primitive)`.
  </behavior>
  <action>
    Mirror the file structure of Phase 110 Plan 02's `tests/integration/test_linear_workflow_execution_post_versioning.py` exactly. Use `pytest.mark.integration` (project doesn't register it but the warning is benign — Phase 110 documents this). Use canonical `from app.services.supabase_client import get_async_client` for DB access. Skip without creds, cleanup on teardown.

    This test directly exercises `WorkflowEngine().decide_next_graph_nodes()`. Task 03-06 builds the end-to-end version that goes through start_workflow + _advance_workflow.
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_branching_workflow_execution.py --collect-only -q</automated>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_branching_workflow_execution.py -v --tb=short -q</automated>
    <automated>.venv/Scripts/python -m ruff check tests/integration/test_branching_workflow_execution.py</automated>
  </verify>
  <done>
    - File exists, 2 tests collected.
    - Both tests SKIP cleanly when SUPABASE creds absent (no test failure).
    - CI environment with creds will exercise them (deferred — same as Phase 110 Plan 02's pattern).
    - One commit on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-04: Linear non-regression integration test + Spec A OutcomeWriter signature guard (ROADMAP criteria 2, 9, 10)</name>
  <files>tests/integration/test_linear_workflow_execution_post_branching.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 03-01/02/03 committed.
  </precondition>
  <behavior>
    Create `tests/integration/test_linear_workflow_execution_post_branching.py` (~120 lines, ≥3 tests, SKIP-on-no-creds for DB tests).

    Pattern mirrors Phase 110 Plan 02's `test_linear_workflow_execution_post_versioning.py` — verify linear-template execution didn't regress after the new dispatcher landed.

    **Test 1: `test_linear_template_decide_next_returns_empty_for_dispatch`** (skip-on-no-creds)

    Setup:
    - Create template with linear graph: t1 (trigger) → a1 (agent-action) → o1 (output). NO non-linear kinds.
    - Create execution pinned to this template_version_id.

    Assertion:
    - `decide_next_graph_nodes(execution_id)` returns `[]` (linear template — caller falls back to step_executor).
    - `requires_graph_executor(graph_nodes)` returns False.
    - This is the load-bearing assertion for ROADMAP criterion 2.

    **Test 2: `test_linear_template_with_null_template_version_id_returns_empty`** (skip-on-no-creds)

    Setup:
    - Create execution with `template_version_id = NULL` (legacy execution from before Phase 110).

    Assertion:
    - `decide_next_graph_nodes(execution_id)` returns `[]` (graceful — legacy executions follow the linear codepath).

    **Test 3: `test_outcome_writer_signature_unchanged`** (no DB needed, ALWAYS runs)

    BLOCKER #1 fix from plan-checker iteration 1: this test pins the ACTUAL public signature of `OutcomeWriter.write_for_step` as verified against `app/workflows/outcome_writer.py:30-39` on 2026-05-12. The previous draft incorrectly asserted `"text" in params and "source" in params` — those are `_derive()` INTERNAL return values, not public method parameters.

    ```python
    def test_outcome_writer_signature_unchanged():
        """Pin OutcomeWriter contract — Spec A invariant per ROADMAP criterion 10.

        Verifies the public method signature has not drifted. If this fails,
        Phase 111 (or a later phase) has modified Spec A's outcome-writing
        path and the live-workspace view may regress.
        """
        import inspect
        from app.workflows.outcome_writer import OutcomeWriter

        # __init__ contract: (self, client) — Spec A's signature
        sig = inspect.signature(OutcomeWriter.__init__)
        init_params = list(sig.parameters.keys())
        assert init_params == ["self", "client"], (
            f"OutcomeWriter.__init__ signature changed: {init_params}"
        )

        # write_for_step contract (verified against app/workflows/outcome_writer.py:30-39):
        #   write_for_step(self, *, step_id, tool_output, status, tool_name,
        #                  duration_ms, error_message=None)
        sig2 = inspect.signature(OutcomeWriter.write_for_step)
        params2 = list(sig2.parameters.keys())
        expected = {
            "self",
            "step_id",
            "tool_output",
            "status",
            "tool_name",
            "duration_ms",
            "error_message",
        }
        assert set(params2) == expected, (
            f"OutcomeWriter.write_for_step signature changed: got {params2}, "
            f"expected exactly {sorted(expected)}"
        )
    ```

    No DB access needed for Test 3 — runs regardless of creds. This is the load-bearing static check for ROADMAP criterion 10.

    Commit: `test(111-03): linear non-regression + OutcomeWriter signature guard (ROADMAP criteria 2, 9, 10)`.
  </behavior>
  <action>
    Mirror Phase 110 Plan 02's integration test file structure. Test 3 is a pure-import test and runs without DB. Tests 1 + 2 skip gracefully without SUPABASE creds.

    Critical: the expected param set in Test 3 uses set-equality (`set(params2) == expected`), not subset checks. This catches both added AND removed parameters. The exact names come from `app/workflows/outcome_writer.py:30-39` — re-verify against that file at execution time and update this test if the actual file has drifted (then file a follow-up issue noting the drift).
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_linear_workflow_execution_post_branching.py -v --tb=short</automated>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_linear_workflow_execution_post_branching.py::test_outcome_writer_signature_unchanged -v</automated>
    <automated>.venv/Scripts/python -m ruff check tests/integration/test_linear_workflow_execution_post_branching.py</automated>
  </verify>
  <done>
    - File exists, 3 tests collected.
    - Tests 1 + 2 SKIP without creds.
    - Test 3 PASSES regardless (pure-import) — and uses the CORRECT parameter names.
    - One commit on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-05: Wire dispatch into _advance_workflow + _enqueue_graph_node_step (BLOCKER #3 — production call site)</name>
  <files>app/workflows/engine.py, tests/unit/workflows/test_advance_workflow_dispatch.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 03-01/02/03/04 committed.
    Re-read `app/workflows/engine.py` lines 1587-1599 (current `_advance_workflow` shim) — confirm it still delegates to `edge_function_client.execute_workflow(execution["id"], action="advance")` before editing.
  </precondition>
  <behavior>
    **RED — `tests/unit/workflows/test_advance_workflow_dispatch.py`, ≥10 tests:**

    Mock supabase + edge_function_client per Phase 110 Plan 02's patterns. The new method's contract:

    1. `test_advance_workflow_linear_template_delegates_to_edge_function` — execution row's template_version_id points to a LINEAR template (graph_nodes have only trigger/agent-action/output). Call `_advance_workflow(execution, phases)`. Assert: `edge_function_client.execute_workflow(execution_id, action="advance")` was called exactly once; `_enqueue_graph_node_step` was NOT called. Return value matches the existing shim's `{"status": "processing", ...}`.

    2. `test_advance_workflow_legacy_null_version_delegates_to_edge_function` — execution has `template_version_id=None` (pre-Phase-110 execution). Assert: EF call fires, dispatch NOT invoked.

    3. `test_advance_workflow_graph_template_calls_decide_next_graph_nodes` — execution pinned to a branching version. Assert: `decide_next_graph_nodes` was called with the execution_id; EF call did NOT fire (Python owns this path).

    4. `test_advance_workflow_graph_template_enqueues_next_nodes` — mock `decide_next_graph_nodes` to return `["next-node-uuid"]`. Assert: `_enqueue_graph_node_step(execution_id, "next-node-uuid")` was called once.

    5. `test_advance_workflow_graph_template_enqueues_multiple_when_dispatcher_returns_multiple` — `decide_next_graph_nodes` returns `["n1", "n2"]` (e.g. a parallel kind — Phase 4 forward-compat). Assert: `_enqueue_graph_node_step` called twice with both ids.

    6. `test_advance_workflow_graph_template_handles_dispatcher_returning_empty` — `decide_next_graph_nodes` returns `[]` (no next nodes — workflow done). Assert: NO `_enqueue_graph_node_step` calls; NO EF call; execution status may be updated to 'completed' or left untouched (verify behavior matches implementation).

    7. `test_advance_workflow_propagates_graph_executor_error` — `decide_next_graph_nodes` raises `GraphExecutorError`. Assert: `_advance_workflow` either re-raises OR returns `{"error": "...", "error_code": "graph_executor_error"}` (planner picks; document choice). The execution should be marked 'failed' so the user sees the failure rather than a silent hang.

    8. `test_enqueue_graph_node_step_inserts_workflow_steps_row` — mock supabase insert; call `_enqueue_graph_node_step(execution_id, node_id)` for an `agent-action` graph node; assert the `.table("workflow_steps").insert({...})` call was made with: `status="running"`, `step_index` set, `output_data._execution_meta.graph_node_id == node_id`, `step_definition` containing the node's tool_name + graph_node_id.

    9. `test_enqueue_graph_node_step_handles_condition_kind` — condition graph node. Assert: inserted row has `status="completed"` (immediate self-complete per Phase 111 design), `output_data._execution_meta = {"graph_node_id": node_id, "kind": "condition"}`. This is the seed row that the next `_advance_workflow` call reads to evaluate the condition expression.

    10. `test_enqueue_graph_node_step_handles_output_kind` — output graph node. Assert: inserted row has `status="completed"`; the parent execution row's `status` is updated to 'completed' (terminal node).

    11. `test_enqueue_graph_node_step_raises_for_parallel_kind` — `kind="parallel"` graph node. Assert: `NotImplementedError` raised with "Phase 4" in the message. Same for merge + human-approval.

    12. `test_advance_workflow_loops_until_agent_action_or_terminal` — sequence: a1 (agent-action) just completed → next is c1 (condition) → c1 enqueued+self-completed → re-evaluate → next is o1 (output) → o1 enqueued+execution completes. Assert: `_enqueue_graph_node_step` called for both c1 and o1 in a single `_advance_workflow` invocation (the loop runs internally until an agent-action or terminal node is reached).

    13. `test_advance_workflow_stops_when_next_is_agent_action` — sequence: a1 just completed → next is a2 (agent-action). Assert: `_enqueue_graph_node_step` called once for a2 with `status='running'`; the loop terminates (a2 needs the worker to run, which happens asynchronously via `get_runnable_steps`).

    14. `test_advance_workflow_max_iterations_safety` — pathological case (would normally loop forever). Assert: loop bounded by `max_iterations = len(graph_nodes) * 2` (or similar safety bound); raises `GraphExecutorError` or logs a warning + returns an error result if exceeded.

    Commit RED: `test(111-03): add failing tests for _advance_workflow dispatch wiring + _enqueue_graph_node_step`.

    **GREEN phase — implement two surgical edits to `app/workflows/engine.py`:**

    **Edit 1: New method `_enqueue_graph_node_step` (added inside class WorkflowEngine, after `decide_next_graph_nodes`):**

    ```python
    async def _enqueue_graph_node_step(
        self,
        execution_id: str,
        node_id: str,
    ) -> dict[str, Any]:
        """Insert a workflow_steps row for the given graph node.

        Maps a graph node id to a workflow_steps row. The row's
        output_data._execution_meta.graph_node_id JSONB key carries the
        association (no schema migration — per CONTEXT.md decision 8 as
        updated 2026-05-12).

        For agent-action nodes: row inserts with status='running' so the
            worker's get_runnable_steps poll picks it up and step_executor
            runs the tool.
        For condition nodes: row inserts with status='completed' (immediate
            self-complete) carrying the node's config so the NEXT call to
            _advance_workflow re-evaluates and routes the branch.
        For output nodes: row inserts with status='completed' and the
            parent execution is marked 'completed' (terminal).
        For trigger nodes: not enqueued (triggers are entry points).
        For parallel/merge/human-approval: NotImplementedError (Phase 4).

        Args:
            execution_id: UUID of workflow_executions row.
            node_id: UUID of the graph node to enqueue.

        Returns:
            The inserted/updated row data, or {} for no-op cases (trigger).

        Raises:
            GraphExecutorError: when the node id is not found in the pinned
                graph or when the node kind is unsupported.
            NotImplementedError: when the node kind is parallel/merge/
                human-approval (Phase 4 work).
        """
        client = await self._get_client()

        # Load pinned graph to resolve node metadata
        exec_res = await (
            client.table("workflow_executions")
            .select("id, template_version_id, status, current_step_index")
            .eq("id", execution_id)
            .single()
            .execute()
        )
        execution = (exec_res.data if exec_res else None) or {}
        graph_nodes, _edges = await self._load_template_graph(
            execution.get("template_version_id")
        )
        node = next((n for n in graph_nodes if n.get("id") == node_id), None)
        if node is None:
            raise GraphExecutorError(
                f"Graph node {node_id} not found in pinned template version "
                f"for execution {execution_id}"
            )

        kind = node.get("kind")
        if kind == "trigger":
            return {}
        if kind in {"parallel", "merge", "human-approval"}:
            raise NotImplementedError(
                f"Phase 4: graph node kind '{kind}' enqueue not yet implemented"
            )

        # Compute next step_index
        count_res = await (
            client.table("workflow_steps")
            .select("step_index", count="exact")
            .eq("execution_id", execution_id)
            .order("step_index", desc=True)
            .limit(1)
            .execute()
        )
        max_idx = (
            (count_res.data[0].get("step_index") if count_res.data else None)
            or -1
        )
        next_step_index = max_idx + 1

        config = node.get("config") or {}
        label = node.get("label") or node.get("id")
        step_definition: dict[str, Any] = {
            "name": label,
            "graph_node_id": node_id,
            "kind": kind,
            "config": config,
        }

        execution_meta: dict[str, Any] = {
            "graph_node_id": node_id,
            "kind": kind,
        }

        if kind == "agent-action":
            tool_name = config.get("tool_name") or config.get("tool")
            if not tool_name:
                raise GraphExecutorError(
                    f"agent-action node {node_id} missing config.tool_name"
                )
            step_definition["tool"] = tool_name
            row = {
                "execution_id": execution_id,
                "step_index": next_step_index,
                "phase_index": 0,
                "phase_name": "graph",
                "step_name": label,
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "input_data": {},
                "output_data": {"_execution_meta": execution_meta},
                "step_definition": step_definition,
                "idempotency_key": (
                    f"{execution_id}:graph:{node_id}:1"
                ),
            }
            insert_res = await (
                client.table("workflow_steps").insert(row).execute()
            )
            return insert_res.data[0] if insert_res.data else {}

        # condition / output: self-complete immediately
        completed_status = "completed"
        now_iso = datetime.now().isoformat()
        row = {
            "execution_id": execution_id,
            "step_index": next_step_index,
            "phase_index": 0,
            "phase_name": "graph",
            "step_name": label,
            "status": completed_status,
            "started_at": now_iso,
            "completed_at": now_iso,
            "input_data": {},
            "output_data": {"_execution_meta": execution_meta},
            "step_definition": step_definition,
            "idempotency_key": f"{execution_id}:graph:{node_id}:1",
        }
        insert_res = await (
            client.table("workflow_steps").insert(row).execute()
        )

        if kind == "output":
            # Terminal node — mark execution complete
            await (
                client.table("workflow_executions")
                .update(
                    {
                        "status": "completed",
                        "completed_at": now_iso,
                    }
                )
                .eq("id", execution_id)
                .execute()
            )

        return insert_res.data[0] if insert_res.data else {}
    ```

    **Edit 2: Rewrite `_advance_workflow` (line ~1587) to dispatch on graph vs linear:**

    ```python
    async def _advance_workflow(
        self, execution: dict, phases: list[dict]
    ) -> dict[str, Any]:
        """Advance the workflow to the next step.

        For graph-executor templates: calls decide_next_graph_nodes and
        enqueues the next workflow_steps row(s) via _enqueue_graph_node_step.
        Loops internally while the next-node list resolves to immediately-
        complete kinds (condition/output) so a single _advance_workflow
        invocation can chain trigger→condition→output without intermediate
        worker passes. Stops when next is an agent-action (needs worker)
        OR the dispatcher returns empty (workflow done) OR the loop guard
        is exceeded.

        For linear templates (or executions without a pinned version_id):
        delegates to the Edge Function as before (no behavior change).

        Args:
            execution: workflow_executions row dict (with template_version_id).
            phases: template phases JSONB (legacy linear path; unused for
                graph path).

        Returns:
            {"status": "processing", "message": "..."} for both paths.
            For graph path with errors: {"error": "...", "error_code": "..."}.
        """
        execution_id = execution["id"]

        # Determine path: graph vs linear
        template_version_id = execution.get("template_version_id")
        if not template_version_id:
            # Legacy execution — linear path
            await edge_function_client.execute_workflow(
                execution_id, action="advance"
            )
            return {"status": "processing", "message": "Workflow advancement triggered"}

        graph_nodes, _edges = await self._load_template_graph(template_version_id)
        if not self.requires_graph_executor(graph_nodes):
            # Linear template — delegate to EF as before
            await edge_function_client.execute_workflow(
                execution_id, action="advance"
            )
            return {"status": "processing", "message": "Workflow advancement triggered"}

        # Graph executor path — Python owns this from here
        max_iterations = max(1, len(graph_nodes) * 2)
        for _ in range(max_iterations):
            try:
                next_node_ids = await self.decide_next_graph_nodes(execution_id)
            except GraphExecutorError as exc:
                logger.error(
                    "Graph executor failed for execution %s: %s",
                    execution_id,
                    exc,
                )
                client = await self._get_client()
                await (
                    client.table("workflow_executions")
                    .update(
                        {
                            "status": "failed",
                            "error_message": str(exc),
                            "completed_at": datetime.now().isoformat(),
                        }
                    )
                    .eq("id", execution_id)
                    .execute()
                )
                return {
                    "error": str(exc),
                    "error_code": "graph_executor_error",
                }

            if not next_node_ids:
                # No more nodes — workflow done (or waiting on async work)
                return {
                    "status": "processing",
                    "message": "No further graph nodes to enqueue",
                }

            # Enqueue each next node
            any_agent_action = False
            for node_id in next_node_ids:
                node = next(
                    (n for n in graph_nodes if n.get("id") == node_id), None
                )
                kind = node.get("kind") if node else None
                await self._enqueue_graph_node_step(execution_id, node_id)
                if kind == "agent-action":
                    any_agent_action = True

            # If we enqueued an agent-action, stop — the worker takes over.
            # If we only enqueued condition/output rows, loop again so the
            # next decide_next_graph_nodes call sees the new state.
            if any_agent_action:
                return {
                    "status": "processing",
                    "message": "Graph executor enqueued agent-action step",
                }
        else:
            logger.warning(
                "Graph executor loop exceeded max_iterations=%d for execution %s",
                max_iterations,
                execution_id,
            )
            return {
                "error": "Graph executor loop bound exceeded",
                "error_code": "graph_executor_loop_exceeded",
            }
    ```

    Commit GREEN: `feat(111-03): wire _advance_workflow to graph dispatch (BLOCKER #3 fix)`.

    Verify the 14 new tests + all previous tests still GREEN. Especially run the WHOLE workflows suite to catch any regression: `.venv/Scripts/python -m pytest tests/unit/workflows/ -v -q --tb=line`.
  </behavior>
  <action>
    Follow the behavior block. Mock `edge_function_client.execute_workflow` in tests via `@patch("app.workflows.engine.edge_function_client")` to assert it IS or IS NOT called. Mock the supabase chain per existing Phase 110 patterns.

    Key implementation note: the `_advance_workflow` signature stays the same `(execution: dict, phases: list[dict])` for backward compat (existing callers in `step_executor._try_advance` pass these args). Only the body changes.

    Verify ruff + ty clean on `engine.py`. Run the broader integration smoke: `.venv/Scripts/python -m pytest tests/unit/workflows/ tests/unit/routers/ -v -q --tb=line` to make sure no router test broke (none should — `_advance_workflow` is only called by `step_executor._try_advance`).
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/test_advance_workflow_dispatch.py -v --tb=short</automated>
    <automated>.venv/Scripts/python -m pytest tests/unit/workflows/ -v -q --tb=line --no-header</automated>
    <automated>.venv/Scripts/python -m ruff check app/workflows/engine.py tests/unit/workflows/test_advance_workflow_dispatch.py</automated>
    <automated>grep -n "decide_next_graph_nodes\|_enqueue_graph_node_step" app/workflows/engine.py</automated>
  </verify>
  <done>
    - `WorkflowEngine._enqueue_graph_node_step` method exists with docstring + handles all 7 node kinds (4 implemented for Phase 111, 3 raise NotImplementedError for Phase 4).
    - `WorkflowEngine._advance_workflow` body REWRITTEN: graph templates go through Python dispatch + workflow_steps INSERTs; linear templates delegate to EF unchanged.
    - 14 tests in `test_advance_workflow_dispatch.py` GREEN.
    - All previous workflow tests (Plan 110 + Phase 111 Tasks 03-01/02) still GREEN.
    - `grep` for the new method names returns ≥2 hits (defined + called).
    - Two commits on `plan-109-spec-b-phase-1` (RED, GREEN).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 03-06: End-to-end integration tests through the production wire (ROADMAP criterion 1 closure)</name>
  <files>tests/integration/test_branching_workflow_execution.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 03-05 committed. Re-confirm Task 03-03's existing tests in this file are still GREEN before extending.
  </precondition>
  <behavior>
    EXTEND `tests/integration/test_branching_workflow_execution.py` with ≥3 additional tests that exercise the FULL production wire: `start_workflow` (existing public method, RPC pins version) → simulated upstream agent-action completion → `_advance_workflow` → `_enqueue_graph_node_step` INSERTs the next workflow_steps row → assert the inserted row matches the expected branch.

    These tests close ROADMAP criterion 1 end-to-end. Task 03-03's existing tests cover the dispatcher primitive; Task 03-06 covers the production call site.

    All tests SKIP gracefully without SUPABASE creds (same pattern as Task 03-03).

    **Test 3: `test_e2e_start_workflow_routes_truthy_branch_via_advance_workflow`**

    Flow:
    1. SEED: a branching template in DB (workflow_templates row + workflow_template_versions v1 row with `graph_nodes` containing trigger t1 + agent-action a1 + condition c1 + output t-out (true) + output f-out (false), `graph_edges` wiring them with handles).
    2. CALL the EXISTING public method `WorkflowEngine().start_workflow(...)` to start an execution (RPC pins template_version_id). Capture `execution_id`.
       - Mock or bypass the Edge Function call inside `start_workflow` — the e2e test focuses on the Python advance path, not the EF's initial step trigger. Pattern: `@patch("app.workflows.engine.edge_function_client.execute_workflow")` to make the start trigger a no-op. (The EF would normally enqueue the trigger node; the test simulates that next step.)
    3. SIMULATE upstream completion: directly INSERT a `workflow_steps` row for a1 with `status='completed'`, `output_data = {"lead_score": 75, "_execution_meta": {"graph_node_id": "<a1_id>"}}`.
    4. CALL `engine._advance_workflow(execution_row, phases=[])` (fetch the execution row first).
    5. ASSERT:
       - A new workflow_steps row exists for c1 with `status='completed'` (condition self-complete) and `_execution_meta.graph_node_id = <c1_id>`.
       - A new workflow_steps row exists for t-out with `status='completed'` and `_execution_meta.graph_node_id = <t-out_id>`.
       - NO row for f-out (the false branch was not taken).
       - The execution row's `status='completed'` (output node marked it terminal).
       - `edge_function_client.execute_workflow` was NOT called for `action='advance'` (Python owned the dispatch).
    6. CLEANUP DB rows in try/finally.

    **Test 4: `test_e2e_start_workflow_routes_falsy_branch_via_advance_workflow`**

    Same setup but a1's output_data carries `lead_score=25`. Assertions:
    - c1 enqueued + completed.
    - f-out enqueued + completed (false branch).
    - NO t-out row.
    - execution row marked completed.

    **Test 5: `test_e2e_advance_workflow_for_linear_template_delegates_to_ef_and_inserts_no_rows`**

    Non-regression for ROADMAP criterion 9 through the production wire.

    Flow:
    1. SEED: linear template (trigger t1 → agent-action a1 → output o1, NO branching kinds).
    2. CALL `start_workflow` (mock EF). Capture execution_id. Count existing workflow_steps rows for this execution = 0.
    3. CALL `engine._advance_workflow(execution, phases=[])`.
    4. ASSERT:
       - `edge_function_client.execute_workflow(execution_id, action="advance")` was called exactly once.
       - The Python engine inserted ZERO additional workflow_steps rows (the EF owns linear orchestration).
       - Return value is `{"status": "processing", ...}` matching the legacy shim.
    5. CLEANUP.

    Tests use the SAME `start_workflow` public method that real users hit. The only mock is the EF client (because spinning up Deno + the EF in pytest is out of scope).

    Commit: `test(111-03): end-to-end branching + linear non-regression through production wire (ROADMAP criterion 1)`.
  </behavior>
  <action>
    Mirror Phase 110 Plan 02's e2e integration test patterns. Use `pytest.fixture` for DB cleanup, `@patch` for EF client mocking, real `WorkflowEngine` instance for everything else.

    Implementation tip: the start_workflow method also requires a normalize-template-for-execution step + persona resolution. For a minimal test, seed the template with the minimum fields the engine requires (name, phases, lifecycle_status='published', persona) and bypass persona gating by mocking `_resolve_workflow_persona` and `_should_block_workflow_start_for_persona` if needed. Phase 110 Plan 02's tests show the exact set of mocks required.

    Alternative simpler approach: skip the `start_workflow` step entirely in Tests 3/4 and directly INSERT the workflow_executions row with the right template_version_id, then call `_advance_workflow`. This is closer to the integration-test-with-DB pattern Phase 110 uses. The test still hits the REAL `_advance_workflow + decide_next_graph_nodes + _enqueue_graph_node_step` production code path — which is the load-bearing assertion.

    Pick whichever variant ships faster. Document the choice in the test docstring. The non-negotiable requirement: the test exercises the REAL `_advance_workflow` method through to the REAL `_enqueue_graph_node_step` INSERT, with no monkey-patching of those methods.
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_branching_workflow_execution.py --collect-only -q</automated>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_branching_workflow_execution.py -v --tb=short -q</automated>
    <automated>.venv/Scripts/python -m ruff check tests/integration/test_branching_workflow_execution.py</automated>
  </verify>
  <done>
    - File extended with 3 new tests (5 total in the file).
    - All 5 tests SKIP cleanly when SUPABASE creds absent.
    - With creds, the e2e tests exercise the FULL production call site through `_advance_workflow + _enqueue_graph_node_step`.
    - One commit on `plan-109-spec-b-phase-1`.
    - ROADMAP criterion 1 now genuinely closed: a real branching template, started via the same public method real users hit, routes through `_advance_workflow` → `decide_next_graph_nodes` → `_enqueue_graph_node_step` → workflow_steps INSERT, with the correct branch taken.
  </done>
</task>

</tasks>

<verification>
**Plan-level checks before SUMMARY:**

1. `git branch --show-current` returns `plan-109-spec-b-phase-1`.
2. `.venv/Scripts/python -m pytest tests/unit/workflows/ -v -q --tb=line --no-header` — all tests still GREEN, with ~45 new tests (18 dispatch + 3 step_executor + 14 advance_workflow_dispatch + ~10 from Plan 02's graph_validation extension).
3. `.venv/Scripts/python -m pytest tests/integration/test_branching_workflow_execution.py tests/integration/test_linear_workflow_execution_post_branching.py --collect-only -q` — 8 tests collected (2 from Task 03-03 + 3 from Task 03-04 + 3 from Task 03-06).
4. `.venv/Scripts/python -m pytest tests/integration/test_linear_workflow_execution_post_branching.py::test_outcome_writer_signature_unchanged -v` — PASSES (no creds needed).
5. `grep -c "from app.workflows.graph_executor" app/workflows/engine.py` → 1 (one import line).
6. `grep -c "_template_requires_graph_executor\|decide_next_nodes" app/workflows/engine.py` → ≥2 (both used).
7. `grep -c "graph_node_id" app/workflows/step_executor.py` → ≥1 (the new metadata write).
8. `grep -c "_enqueue_graph_node_step\|decide_next_graph_nodes" app/workflows/engine.py` → ≥4 (each method defined + called from _advance_workflow).
9. `.venv/Scripts/python -m ruff check app/workflows/engine.py app/workflows/step_executor.py` — clean.
10. NO migrations added in this plan: `ls supabase/migrations/2026* | wc -l` should match the count before this plan started (Phase 110 left it at ...100 + the 0511 view file).
11. NO router changes: `git diff plan-109-spec-b-phase-1 -- app/routers/workflows.py` should be empty for THIS plan (Plan 110-03 already wired validation; Plan 02 of THIS phase extends graph_validation only).
12. Spec A files untouched: `git diff -- app/workflows/outcome_writer.py app/workflows/event_bus.py` should be empty.
13. Edge Function NOT modified: `git diff -- supabase/functions/` should be empty for Plan 03.
14. `_advance_workflow` actually CALLS the dispatch: `grep -B2 -A20 "async def _advance_workflow" app/workflows/engine.py | grep -c "decide_next_graph_nodes"` ≥ 1.
</verification>

<success_criteria>
- ROADMAP criterion 1 SHIPPED end-to-end: `start_workflow` → `_advance_workflow` (wired) → `decide_next_graph_nodes` → `_enqueue_graph_node_step` → `workflow_steps` INSERT. Task 03-06's e2e integration tests exercise the FULL production call site for both true-branch and false-branch routing.
- ROADMAP criterion 2 SHIPPED: `requires_graph_executor` dispatch helper + unit tests for all linear vs non-linear cases + integration test asserting linear templates delegate to EF unchanged.
- ROADMAP criterion 7 SHIPPED: execution context contains `previous_outcomes` (keyed by graph_node_id from completed `_execution_meta`), `current_step` (most-recent or trigger), `user_context` (from `workflow_executions.context`); unit tests assert each key.
- ROADMAP criterion 9 SHIPPED via non-regression integration test (linear executions unchanged — EF delegation path fires; zero Python-side workflow_steps INSERTs).
- ROADMAP criterion 10 SHIPPED via OutcomeWriter signature-guard test (CORRECT parameter names per `outcome_writer.py:30-39` — BLOCKER #1 fix) + grep verification that outcome_writer.py and event_bus.py are untouched.
- ROADMAP criterion 11 covered by documentation: no engine-time cycle detection added; save-time rule 3 + rule 4 (Plan 02) are the guards. The `max_iterations` loop bound in `_advance_workflow` prevents pathological cases from hanging.
- No new migrations. No new router endpoints. No new dependencies (Plan 01 added json-logic; Plan 03 only consumes it). No Edge Function changes.
- ~10-12 atomic commits on `plan-109-spec-b-phase-1` (RED + GREEN for 5 TDD tasks + 1 commit for Task 03-04).
</success_criteria>

<output>
After completion, create `.planning/phases/111-workflow-node-editor-branching-execution/111-03-SUMMARY.md` mirroring Phase 110 Plan 02's SUMMARY structure (the engine-touching plan SUMMARY format). In the "Deviations from Plan" section, document the iteration-1 plan-checker fixes: Blocker #1 (OutcomeWriter signature pin), Blocker #3 (wire dispatch in production via Tasks 03-05 + 03-06), risk_note (6 tasks vs original 4 — over the soft cap with intentional precedent).
</output>
