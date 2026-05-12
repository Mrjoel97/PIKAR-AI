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
  - tests/integration/test_branching_workflow_execution.py
  - tests/integration/test_linear_workflow_execution_post_branching.py
autonomous: true
gap_closure: false
requirements:
  - NODEEDITOR-ENGINE-01
  - NODEEDITOR-COMPAT-01

must_haves:
  truths:
    - "WorkflowEngine has a new helper _load_template_graph(template_version_id) -> dict that fetches graph_nodes/graph_edges from workflow_template_versions for a pinned version (NOT workflow_templates)"
    - "WorkflowEngine has a new dispatch helper requires_graph_executor(graph_nodes) -> bool wired from graph_executor._template_requires_graph_executor"
    - "StepExecutor.execute_step now writes the originating graph node id into step.output_data._execution_meta.graph_node_id when present in step.step_definition (defense — no migration required; node_id flows via JSONB)"
    - "A new method WorkflowEngine.decide_next_graph_nodes(execution_id) -> list[str] computes next-node ids using graph_executor.decide_next_nodes() by: (a) fetching the pinned version's graph_nodes/edges, (b) building execution_context from completed workflow_steps for this execution_id (previous_outcomes keyed by graph_node_id), (c) finding the most-recently completed step's graph_node_id as current_node_id, (d) calling decide_next_nodes()"
    - "A linear template (no condition/parallel/merge/human-approval kinds) does NOT trigger the graph dispatcher — requires_graph_executor returns False and the existing step_executor codepath runs unchanged (ROADMAP criterion 2)"
    - "A template with one condition node, evaluated against a synthetic previous_outcomes context, returns the correct 'true' OR 'false' branch's outgoing edge target (ROADMAP criterion 1)"
    - "An integration test creates a 2-branch template, starts execution (RPC pins template_version_id), advances through trigger → condition → output, and asserts the correct branch's workflow_steps row is created — verifying end-to-end the engine routes correctly (ROADMAP criterion 1 end-to-end)"
    - "Spec A's OutcomeWriter and event_bus are NOT modified — the new dispatch path reuses them as-is (ROADMAP criterion 10)"
    - "A non-regression integration test starts a linear template (trigger → agent-action → output, all linear kinds) and asserts execution completes via the existing step_executor codepath — no rows mention graph_executor, no behavior change (ROADMAP criterion 2 + 9)"
    - "The atomic RPC start_workflow_execution_atomic continues to pin template_version_id (Phase 110 Plan 02's signature) — Plan 03 does NOT modify the RPC or the migration"
    - "Cycle detection at engine start is NOT added in this plan (ROADMAP criterion 11 — deferred to Phase 4). An integration test asserts the engine assumes acyclic input — the topological sort at save time prevents cycles from reaching the engine"
  artifacts:
    - path: "app/workflows/engine.py"
      provides: "Dispatch helpers + decide_next_graph_nodes + _load_template_graph"
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
    - path: "tests/integration/test_branching_workflow_execution.py"
      provides: "End-to-end branching test (ROADMAP criterion 1)"
      min_lines: 150
    - path: "tests/integration/test_linear_workflow_execution_post_branching.py"
      provides: "Non-regression integration test (ROADMAP criterion 2 + 9)"
      min_lines: 100
  key_links:
    - from: "app/workflows/engine.py"
      to: "app.workflows.graph_executor"
      via: "from app.workflows.graph_executor import decide_next_nodes, _template_requires_graph_executor"
      pattern: "from app.workflows.graph_executor"
    - from: "app/workflows/engine.py:_load_template_graph"
      to: "workflow_template_versions table"
      via: "supabase client .select('graph_nodes, graph_edges').eq('id', template_version_id)"
      pattern: "workflow_template_versions"
    - from: "app/workflows/step_executor.py:_finalize_step"
      to: "workflow_steps.output_data._execution_meta.graph_node_id"
      via: "JSONB write — graph_node_id read from step.get('step_definition', {}).get('graph_node_id')"
      pattern: "graph_node_id"
---

<objective>
Wire `graph_executor` (Plan 01) into `WorkflowEngine` so that templates whose graph contains non-linear node kinds dispatch through JSONLogic-driven routing, while linear templates continue to run via `step_executor` unchanged. Adds `requires_graph_executor()` dispatch helper, `_load_template_graph(template_version_id)` to fetch graphs from `workflow_template_versions` (pinned per Phase 110 Plan 02), and `decide_next_graph_nodes(execution_id)` that builds the execution context from completed `workflow_steps` and calls `decide_next_nodes`. Bridges graph node ids into the existing `workflow_steps` rows via `output_data._execution_meta.graph_node_id` — no schema migration needed.

Purpose: Close ROADMAP criteria 1 (branching end-to-end), 2 (dispatch on non-linear kinds), 7 (execution context fully populated), 9 (no regression on linear runs), and 10 (Spec A unchanged). The Edge Function `execute-workflow` is NOT modified in this plan — the dispatch is added at the Python engine layer so it's testable in unit + integration tests without Deno tooling; future plans (or Phase 4) may push the dispatch decision into the EF if needed.

Output: Two surgical edits to `engine.py` (~80 new lines for helpers), one surgical edit to `step_executor.py` (~5-10 lines to propagate graph_node_id), 4 new test files totaling ~50 tests, no SQL migration, no router changes.
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

    # list_templates already SELECTs current_version_id (Plan 110-02)
    # _advance_workflow exists (line ~1587) — delegates to Edge Function
```

```python
# app/workflows/step_executor.py (existing)

class StepExecutor:
    async def execute_step(self, step: dict, workflow_engine=None) -> dict[str, Any]:
        # step contains: id, tool_name, execution_id, step_definition (dict),
        # workflow_executions (joined row), input_data, prev_step_output, ...
        # _finalize_step writes output_data into workflow_steps row
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
```
</interfaces>

<context_notes>
**No new migrations.** This plan does NOT add a `node_id` column to `workflow_steps`. Instead, Plan 03 stores the graph node UUID in `output_data._execution_meta.graph_node_id` (JSONB). Rationale:
- Phase 111's CONTEXT.md is wrong about `workflow_steps.node_id` existing — verified by grep over `supabase/migrations/`. The column was never added.
- A migration to add `node_id` would: (a) require a new SQL file postdating `20260615000100_workflow_template_save_rpc.sql`, (b) backfill empty for legacy rows, (c) introduce supabase CLI 2.75 dollar-quote risk for any new function. None of that is necessary for Phase 111's scope.
- `output_data` is already a JSONB column with `_execution_meta` keys actively used (see `app/workflows/engine.py` lines ~967-995 in `get_execution_status`).
- Plan 05's frontend widget will read this same JSONB path from the GET execution status response. Plan 03's job is to write it on the StepExecutor side.

**Decision documented:** No migration in Phase 111. If a future phase wants a proper `node_id` column, it can be added as a non-breaking ALTER + backfill from `output_data._execution_meta.graph_node_id`.

**Edge Function execute-workflow is NOT modified.** The dispatch lives in Python. For Phase 111's scope (condition routing only), the engine can be invoked synchronously from the worker (`app/workflows/worker.py:execute_step`) or from a future advance-callback. The integration test will simulate the dispatch path directly via `WorkflowEngine.decide_next_graph_nodes()` rather than going through the EF — this matches Phase 110's testing patterns and avoids Deno dependencies. If at Phase 4 time it turns out the EF needs to consult `decide_next_graph_nodes`, a new plan can add a thin HTTP endpoint OR call into the Python engine directly (the EF already calls Python via the engine's `_advance_workflow` flow).

**Execution-context build pattern (Plan 03 owns this):**

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
        # Linear template — caller should route to step_executor instead
        return []

    # 2. Load pinned graph
    graph_nodes, graph_edges = await self._load_template_graph(template_version_id)

    # 3. Dispatch decision
    if not _template_requires_graph_executor(graph_nodes):
        return []  # caller routes to linear executor

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
    current_node = next((n for n in graph_nodes if n["id"] == current_node_id), None)
    if current_node is None:
        raise GraphExecutorError(f"current_node_id {current_node_id} not in graph")
    return decide_next_nodes(
        graph_nodes,
        graph_edges,
        current_node_id=current_node_id,
        execution_context=context,
        completed_node_ids=completed_node_ids,
    )
```

**StepExecutor graph_node_id propagation (~5 line edit):**

In `app/workflows/step_executor.py`, the `_finalize_step` method (or wherever output_data._execution_meta is assembled) needs to pick up `step.get("step_definition", {}).get("graph_node_id")` if present and write it into `_execution_meta.graph_node_id`. This is purely additive — for linear runs (which never set graph_node_id on the step definition) the field is absent and behavior is unchanged.

How does graph_node_id reach `step.step_definition`? For Phase 111's integration test, we'll seed it directly when constructing the step row. For real branching runs, the dispatch loop (future plan or Phase 4) will project graph nodes into step rows with the node_id attached. Plan 03's integration test will create steps via direct INSERTs with graph_node_id pre-populated — simulating what a future dispatcher would do.

**ROADMAP criterion 11 ("Cycle detection at save time was already shipped in Phase 110; Phase 111 does NOT add engine-time cycle rejection"):**
- Plan 110-03 ships rule 3 (Kahn's algorithm + SCC refinement) at save time.
- Plan 03's integration test confirms the engine assumes acyclic input: if a hypothetical cyclic graph reached `decide_next_graph_nodes`, the function would loop indefinitely (Phase 111 doesn't add topological-sort defense). The test simply documents this contract — "save-time validation is the only guard, deferred engine-time guard to Phase 4."

**Spec A non-regression (ROADMAP criterion 10):** `OutcomeWriter` and `event_bus.publish_workflow_event` are NOT modified. Verify by `grep -rn "OutcomeWriter\|publish_workflow_event" app/workflows/engine.py app/workflows/step_executor.py app/workflows/graph_executor.py` — references are unchanged from Phase 110. The integration test (`test_linear_workflow_execution_post_branching.py`) re-runs Phase 110 Plan 02's linear non-regression scenario.

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

        Args:
            execution_id: UUID of workflow_executions row.

        Returns:
            List of graph_node_id strings to execute next. Empty list means
            "linear path — use step_executor".
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
  <name>Task 03-03: Branching execution integration test (ROADMAP criterion 1)</name>
  <files>tests/integration/test_branching_workflow_execution.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 03-01 + 03-02 committed.
  </precondition>
  <behavior>
    Create `tests/integration/test_branching_workflow_execution.py` (~150 lines, ≥2 tests, SKIP cleanly without SUPABASE creds — match Phase 110 Plan 02's integration test pattern at `tests/integration/test_linear_workflow_execution_post_versioning.py`).

    Both tests follow this pattern:
    1. Skip if SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY absent (use the same pytest.skip pattern as Phase 110).
    2. Create a fresh test template directly in the DB (INSERT into `workflow_templates` + `workflow_template_versions` v1 with the branching graph).
    3. Insert a `workflow_executions` row pinned to that template_version_id.
    4. Insert seed `workflow_steps` rows representing completed upstream steps with `output_data._execution_meta.graph_node_id` set + `output_data.lead_score` (or similar) set in the parent dict.
    5. Call `WorkflowEngine().decide_next_graph_nodes(execution_id)` and assert the returned list contains the correct branch's target node id.
    6. Cleanup: DELETE the test rows on teardown (or use a transactional test fixture if the project has one).

    **Test 1: `test_branching_routes_to_true_branch_when_expression_truthy`**

    Graph design:
    - t1 (trigger)
    - a1 (agent-action, simulating an upstream step that produces lead_score)
    - c1 (condition, config.expression = `{">": [{"var": "previous_outcomes.a1.lead_score"}, 50]}`)
    - t-out (output) on 'true' branch
    - f-out (output) on 'false' branch
    Edges: t1→a1, a1→c1, c1→t-out (handle 'true'), c1→f-out (handle 'false')

    Seed:
    - 1 workflow_steps row: graph_node_id='a1', output_data={lead_score: 75, _execution_meta: {graph_node_id: 'a1'}}, status='completed'

    Assertion:
    - `decide_next_graph_nodes(execution_id)` returns `['c1']` (since current is a1, next is c1 — c1 is the condition itself, evaluated on the NEXT iteration).

    Wait — actually we need to think about this more carefully. The pattern is:
    - current_node_id = the LAST COMPLETED node. So if a1 just completed, current_node_id = a1, and we want to know what runs next, which is c1.
    - But c1 is a condition — the dispatcher returns c1 ITSELF (linear-like) to be "executed", and on c1's "completion" the executor evaluates the condition and the NEXT call to decide_next_graph_nodes returns t-out or f-out.

    Refine the test:
    - **Test 1a**: After a1 completes, `decide_next_graph_nodes` returns `['c1']` (next-node after agent-action is the condition).
    - **Test 1b**: After c1 "completes" (a completed workflow_steps row with graph_node_id='c1' AND condition expression has already been evaluated by some upstream mechanism — for Phase 111 the simpler approach is: when the LAST completed step is a condition, the dispatcher uses the condition's config.expression directly + previous_outcomes + user_context to pick the next branch). Verify in unit tests, integration test focuses on the END-TO-END routing — most importantly that the WRITTEN workflow_steps row for c1's _execution_meta.graph_node_id is read correctly.

    Simpler test design for integration:
    - Seed 2 completed steps: (a1 with lead_score=75) and (c1 — a "completed" condition row representing the condition evaluation having happened).
    - When decide_next_graph_nodes is called with `current_node_id = c1` (most recent completed), it: (a) finds c1 in graph_nodes, (b) evaluates c1's config.expression against previous_outcomes (where a1's lead_score=75 is keyed), (c) returns the 'true' branch target.

    Assertion: `next_nodes == ['t-out']`.

    **Test 2: `test_branching_routes_to_false_branch_when_expression_falsy`**

    Same graph, but seed a1's output_data.lead_score = 25. Assertion: `next_nodes == ['f-out']`.

    Both tests CLEANUP DB rows on teardown (try/finally with DELETE).

    Commit: `test(111-03): integration test for branching workflow execution (ROADMAP criterion 1)`.
  </behavior>
  <action>
    Mirror the file structure of Phase 110 Plan 02's `tests/integration/test_linear_workflow_execution_post_versioning.py` exactly. Use `pytest.mark.integration` (project doesn't register it but the warning is benign — Phase 110 documents this). Use canonical `from app.services.supabase_client import get_async_client` for DB access. Skip without creds, cleanup on teardown.

    The test must NOT depend on the worker/EF execution loop — it directly exercises `WorkflowEngine().decide_next_graph_nodes()`. This is the "dispatch" unit, and asserting it routes correctly with realistic DB rows IS the integration test.
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
  <name>Task 03-04: Linear execution non-regression integration test (ROADMAP criteria 2, 9, 10)</name>
  <files>tests/integration/test_linear_workflow_execution_post_branching.py</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 03-01/02/03 committed.
  </precondition>
  <behavior>
    Create `tests/integration/test_linear_workflow_execution_post_branching.py` (~100 lines, ≥3 tests, SKIP-on-no-creds).

    Pattern mirrors Phase 110 Plan 02's `test_linear_workflow_execution_post_versioning.py` — verify linear-template execution didn't regress after the new dispatcher landed.

    **Test 1: `test_linear_template_decide_next_returns_empty_for_dispatch`**

    Setup:
    - Create template with linear graph: t1 (trigger) → a1 (agent-action) → o1 (output). NO non-linear kinds.
    - Create execution pinned to this template_version_id.

    Assertion:
    - `decide_next_graph_nodes(execution_id)` returns `[]` (linear template — caller falls back to step_executor).
    - `requires_graph_executor(graph_nodes)` returns False.
    - This is the load-bearing assertion for ROADMAP criterion 2.

    **Test 2: `test_linear_template_with_null_template_version_id_returns_empty`**

    Setup:
    - Create execution with `template_version_id = NULL` (legacy execution from before Phase 110).

    Assertion:
    - `decide_next_graph_nodes(execution_id)` returns `[]` (graceful — legacy executions follow the linear codepath).

    **Test 3: `test_spec_a_outcome_writer_unchanged`**

    Setup:
    - Static check: assert `app.workflows.outcome_writer.OutcomeWriter` exists (import succeeds).
    - Static check: assert no file under `app/workflows/` other than `engine.py`, `step_executor.py`, `graph_executor.py` was modified by Phase 111 (check via git diff against a known-good baseline — simpler version: assert the OutcomeWriter class signature matches a known-good reference using inspect.signature).

    Pure unit-test-style assertion in an integration test file is fine — the goal is a single committed assertion that Phase 4 / future plans can't silently regress Spec A.

    Specifically:
    ```python
    def test_outcome_writer_signature_unchanged():
        from app.workflows.outcome_writer import OutcomeWriter
        import inspect
        # OutcomeWriter.__init__ takes (self, client) — Spec A's signature
        sig = inspect.signature(OutcomeWriter.__init__)
        params = list(sig.parameters.keys())
        assert params == ["self", "client"], f"OutcomeWriter signature changed: {params}"

        # write_for_step takes (self, *, step_id, text, source) per Spec A
        sig2 = inspect.signature(OutcomeWriter.write_for_step)
        params2 = list(sig2.parameters.keys())
        assert "step_id" in params2 and "text" in params2 and "source" in params2
    ```

    No DB access needed for Test 3 — runs regardless of creds.

    Commit: `test(111-03): linear execution non-regression + Spec A signature guard (ROADMAP criteria 2, 9, 10)`.
  </behavior>
  <action>
    Mirror Phase 110 Plan 02's integration test file structure. Test 3 is a pure-import test and runs without DB.
  </action>
  <verify>
    <automated>.venv/Scripts/python -m pytest tests/integration/test_linear_workflow_execution_post_branching.py -v --tb=short</automated>
    <automated>.venv/Scripts/python -m ruff check tests/integration/test_linear_workflow_execution_post_branching.py</automated>
  </verify>
  <done>
    - File exists, 3 tests collected.
    - Tests 1 + 2 SKIP without creds.
    - Test 3 PASSES regardless (pure-import).
    - One commit on `plan-109-spec-b-phase-1`.
  </done>
</task>

</tasks>

<verification>
**Plan-level checks before SUMMARY:**

1. `git branch --show-current` returns `plan-109-spec-b-phase-1`.
2. `.venv/Scripts/python -m pytest tests/unit/workflows/ -v -q --tb=line --no-header` — all tests still GREEN, with ~31 new tests (18 dispatch + 3 step_executor + ~10 from Plan 02's graph_validation extension if rolled together).
3. `.venv/Scripts/python -m pytest tests/integration/test_branching_workflow_execution.py tests/integration/test_linear_workflow_execution_post_branching.py --collect-only -q` — 5 tests collected.
4. `.venv/Scripts/python -m pytest tests/integration/test_linear_workflow_execution_post_branching.py::test_outcome_writer_signature_unchanged -v` — PASSES (no creds needed).
5. `grep -c "from app.workflows.graph_executor" app/workflows/engine.py` → 1 (one import line).
6. `grep -c "_template_requires_graph_executor\|decide_next_nodes" app/workflows/engine.py` → ≥2 (both used).
7. `grep -c "graph_node_id" app/workflows/step_executor.py` → ≥1 (the new metadata write).
8. `.venv/Scripts/python -m ruff check app/workflows/engine.py app/workflows/step_executor.py` — clean.
9. NO migrations added in this plan: `ls supabase/migrations/2026* | wc -l` should match the count before this plan started (Phase 110 left it at ...100 + the 0511 view file).
10. NO router changes: `git diff plan-109-spec-b-phase-1 -- app/routers/workflows.py` should be empty for THIS plan (Plan 110-03 already wired validation; Plan 02 of THIS phase extends graph_validation only).
11. Spec A files untouched: `git diff -- app/workflows/outcome_writer.py app/workflows/event_bus.py` should be empty.
</verification>

<success_criteria>
- ROADMAP criterion 1 SHIPPED (with integration test in `test_branching_workflow_execution.py`): a 2-branch template, started via the existing RPC (Phase 110 Plan 02 pinning), routes through `decide_next_graph_nodes` to the correct branch.
- ROADMAP criterion 2 SHIPPED: `requires_graph_executor` dispatch helper + unit tests for all linear vs non-linear cases + integration test asserting linear templates return empty from `decide_next_graph_nodes` (linear codepath unchanged).
- ROADMAP criterion 7 SHIPPED: execution context contains `previous_outcomes` (keyed by graph_node_id from completed `_execution_meta`), `current_step` (most-recent or trigger), `user_context` (from `workflow_executions.context`); unit tests assert each key.
- ROADMAP criterion 9 SHIPPED via non-regression integration test (linear executions unchanged).
- ROADMAP criterion 10 SHIPPED via Spec A signature-guard test (OutcomeWriter, event_bus untouched) + grep verification.
- ROADMAP criterion 11 covered by documentation: no engine-time cycle detection added; save-time rule 3 + new rule 4 are the guards.
- No new migrations. No new router endpoints. No new dependencies (Plan 01 added json-logic; Plan 03 only consumes it).
- ~6 atomic commits on `plan-109-spec-b-phase-1` (3 RED + 3 GREEN for tasks 01+02 if TDD-split; 1-2 commits for the integration test tasks).
</success_criteria>

<output>
After completion, create `.planning/phases/111-workflow-node-editor-branching-execution/111-03-SUMMARY.md` mirroring Phase 110 Plan 02's SUMMARY structure (the engine-touching plan SUMMARY format).
</output>
