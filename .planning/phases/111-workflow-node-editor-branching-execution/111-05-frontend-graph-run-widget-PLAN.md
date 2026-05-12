---
phase: 111-workflow-node-editor-branching-execution
plan: 05
type: execute
wave: 4
depends_on:
  - "111-03"
  - "111-04"
files_modified:
  - frontend/src/components/widgets/WorkflowGraphRunWidget.tsx
  - frontend/src/components/widgets/WidgetRegistry.tsx
  - frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx
  - frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx
  - frontend/src/services/workflowExecutionStream.ts
autonomous: true
gap_closure: false
risk_note: |
  Plan 05 is 4 tasks after plan-checker iteration 1's Warning #7 split (Task 05-01
  → Task 05-01a + Task 05-01b). The 11-file edit in the original Task 05-01 had
  too high a coordination cost; splitting into a 2-file shared-module extraction
  (05-01a) followed by a 9-file uniform extension (05-01b) reduces blast radius
  per commit. Still under the 5-task soft cap. Mirrors Phase 110 Plan 04's
  similar split-vs-keep decision.
requirements:
  - NODEEDITOR-WIDGET-01
  - NODEEDITOR-COMPAT-01

must_haves:
  truths:
    - "A new widget WorkflowGraphRunWidget exists at frontend/src/components/widgets/WorkflowGraphRunWidget.tsx — fetches the execution + its pinned template version's graph, then renders a live React Flow canvas with status overlays"
    - "WidgetRegistry maps the widget-type string 'workflow_graph_run' (or similar — planner picks; reuse if a routing function already exists) to WorkflowGraphRunWidget"
    - "WorkflowGraphRunWidget consumes the existing Spec A SSE event bus via subscribeToExecution (Phase 109/110) — NO modifications to the SSE wire format"
    - "WorkflowGraphRunWidget imports NODE_TYPES from frontend/src/components/workflows/editor/nodeTypes.ts (extracted shared module) — reuses the 7 visual node components rather than re-implementing them (Discretion #6)"
    - "The widget renders the currently-executing node with an active-state visual (pulsing border via Tailwind animate-pulse + ring-amber-500) — Discretion #7"
    - "The widget highlights the edge from a condition node whose branch was TAKEN (visible in workflow_steps rows) — the not-taken edge is muted (opacity-30)"
    - "Not-yet-reached nodes are rendered at reduced opacity (opacity-50) — the user can visually distinguish 'queued', 'active', 'completed', and 'skipped/not-taken'"
    - "A vitest test mocks the SSE stream + the GET execution endpoint and asserts that the DOM reflects the active/taken/muted states on a 2-branch conditional template (ROADMAP criterion 8)"
    - "All SSE event type strings in the widget AND its tests use the canonical dot-separated form 'workflow.step.started', 'workflow.step.completed', 'workflow.step.failed', 'workflow.step.paused' (BLOCKER #2 fix — backend emits this form per app/workflows/step_executor.py:752-760 and the original draft used 'workflow_step.started' which would never match)"
    - "The workspace's auto-widget-picker routes runs whose template has non-linear graph_nodes to WorkflowGraphRunWidget; linear-template runs continue to route to WorkflowTimelineWidget (ROADMAP criterion 9 client-side)"
    - "A vitest test asserts the routing helper returns 'workflow_graph_run' for non-linear templates and 'workflow_timeline' for linear templates (ROADMAP criterion 9 unit test)"
    - "The widget's React Flow integration wraps the canvas in ReactFlowProvider (same pattern as Phase 109's read-only viewer + Phase 110's editable canvas) — read-only props (no edge connect, no node drag in run-time mode)"
    - "Graph node id ↔ workflow_steps row mapping uses the output_data._execution_meta.graph_node_id JSONB key (Plan 03 writes this on completed steps) — the widget reads via the existing GET /workflows/executions/{id}/status response or via the new GET endpoint introduced for graph runs (planner decides whether to extend the existing one or add a small companion endpoint — recommend reuse the existing get_execution_status return shape)"
    - "Spec A's existing WorkflowTimelineWidget is NOT modified (ROADMAP criterion 10)"
    - "Existing Phase 110 + Phase 109 frontend tests all still pass (no regression in ~90 workflow vitest tests)"
  artifacts:
    - path: "frontend/src/components/widgets/WorkflowGraphRunWidget.tsx"
      provides: "Live branched-run rendering widget"
      min_lines: 250
    - path: "frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx"
      provides: "SSE-mocked tests asserting active/taken/muted DOM states"
      min_lines: 200
    - path: "frontend/src/components/widgets/WidgetRegistry.tsx"
      provides: "workflow_graph_run widget mapping + routing helper"
      contains: "workflow_graph_run"
    - path: "frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx"
      provides: "Routing logic tests for linear-vs-branching template detection"
      contains: "workflow_graph_run"
  key_links:
    - from: "frontend/src/components/widgets/WorkflowGraphRunWidget.tsx"
      to: "frontend/src/services/workflowExecutionStream.ts"
      via: "subscribeToExecution(executionId, onEvent)"
      pattern: "subscribeToExecution"
    - from: "frontend/src/components/widgets/WorkflowGraphRunWidget.tsx"
      to: "frontend/src/components/workflows/editor/nodeTypes.ts"
      via: "import { NODE_TYPES } from extracted shared module"
      pattern: "NODE_TYPES|nodeTypes"
    - from: "frontend/src/components/widgets/WorkflowGraphRunWidget.tsx"
      to: "output_data._execution_meta.graph_node_id (Plan 03 write)"
      via: "step.output_data._execution_meta.graph_node_id read on each SSE event / status fetch"
      pattern: "_execution_meta"
    - from: "frontend/src/components/widgets/WidgetRegistry.tsx"
      to: "WorkflowGraphRunWidget"
      via: "dynamic import + WIDGET_MAP entry"
      pattern: "WorkflowGraphRunWidget"
---

<objective>
Ship `WorkflowGraphRunWidget` (Discretion #6: under `frontend/src/components/widgets/`), the live React Flow renderer for branched workflow runs. Consume Spec A's existing SSE event stream + execution status payload to drive node/edge status overlays: active node (pulsing border via Tailwind animate-pulse + ring-amber), taken edge highlighted, not-taken edge muted (opacity-30), pending nodes at opacity-50. Wire the workspace's auto-widget-picker (`WidgetRegistry.resolveWidget` / routing helper) so non-linear templates route to the new widget and linear templates continue to render in `WorkflowTimelineWidget` unchanged. Reuse the 7 Phase 109/110 node components (Discretion #6: import shared `NODE_TYPES`).

Purpose: Close ROADMAP criteria 8 (live branched-run rendering with overlays), 9 (workspace widget-picker routes linear vs branching), and 10 (Spec A SSE + OutcomeWriter unchanged). This is the user-visible payoff of Phase 111 — once Plan 03 routes a real branching execution, this widget visualizes it.

Output: 1 new widget component (~250 lines), 1 new test file (~200 lines), 2 surgical edits to WidgetRegistry (component map entry + routing helper), 0 backend changes, 0 SSE wire-format changes.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-CONTEXT.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-03-engine-dispatch-PLAN.md
@.planning/phases/111-workflow-node-editor-branching-execution/111-04-frontend-condition-ux-PLAN.md
@frontend/src/components/widgets/WorkflowTimelineWidget.tsx
@frontend/src/components/widgets/WidgetRegistry.tsx
@frontend/src/components/workflows/editor/NodeCanvas.tsx
@frontend/src/services/workflowExecutionStream.ts
@app/workflows/step_executor.py
@CLAUDE.md

<interfaces>
<!-- Phase 109 + 110 — already on disk, reuse without modification. -->

```typescript
// frontend/src/services/workflowExecutionStream.ts (existing — Phase 109 / Spec A)
export interface WorkflowEvent {
    type: string;          // e.g. 'workflow.step.started', 'workflow.step.completed'
                           // — note DOT-SEPARATED (workflow.step.X), NOT 'workflow_step.X'.
                           // This matches the backend wire format per
                           // app/workflows/step_executor.py:752-760 which publishes
                           // event.type = f"workflow.step.{status}"
    step_id?: string;      // workflow_steps row id
    status?: string;
    duration_ms?: number;
    [key: string]: unknown;  // forward-compat
}

export function subscribeToExecution(
    executionId: string,
    onEvent: (event: WorkflowEvent) => void,
): () => void;  // returns unsubscribe
```

```typescript
// frontend/src/components/workflows/editor/NodeCanvas.tsx (Phase 109 + 110)
// Exposes a module-scoped NODE_TYPES map with all 7 visual components:
//   { trigger: TriggerNode, 'agent-action': AgentActionNode, output: OutputNode,
//     condition: ConditionNode, parallel: ParallelNode, merge: MergeNode,
//     'human-approval': HumanApprovalNode }
//
// Task 05-01a (refactor) extracts this map into:
// frontend/src/components/workflows/editor/nodeTypes.ts
// (small refactor, ~10 lines), keeping NodeCanvas backward-compat by re-import.
```

```typescript
// frontend/src/components/widgets/WidgetRegistry.tsx (existing)
// Add a new entry to WIDGET_MAP:
//   workflow_graph_run: WorkflowGraphRunWidget
//
// Add a routing helper (new function, exported):
//   export function resolveWorkflowRunWidget(template: {graph_nodes?: GraphNode[]}): WidgetType {
//     return _isBranchingTemplate(template.graph_nodes ?? []) ? 'workflow_graph_run' : 'workflow_timeline';
//   }
```

```typescript
// frontend/src/types/api.generated.ts (Phase 109)
// Provides:
//   components.schemas.WorkflowTemplateResponse (with graph_nodes, graph_edges, graph_layout, current_version_id)
//   components.schemas.GraphNode / GraphEdge / NodePosition / NodeKind
```

<!-- Backend SSE wire format (canonical — verified against app/workflows/step_executor.py:752-760) -->

```python
# In StepExecutor._finalize_step:
await publish_workflow_event(
    f"workflow.execution.{execution_id}",
    {
        "type": f"workflow.step.{status}",   # ← DOT-SEPARATED.
        # Concretely emits one of:
        #   "workflow.step.started"
        #   "workflow.step.completed"
        #   "workflow.step.failed"
        #   "workflow.step.paused"   (via _on_step_paused_for_approval)
        "step_id": step["id"],
        "status": status,
        "duration_ms": duration_ms,
    },
)
```

**BLOCKER #2 from plan-checker iteration 1:** the original Plan 05 draft used the format `workflow_step.started` (underscore-then-dot). Backend emits `workflow.step.started` (all dots). This plan corrects every reference. The widget would mount but never react to any SSE events under the wrong form.

<!-- Execution status payload (existing — engine.get_execution_status) -->

```python
# Returns a dict like:
{
  "execution": { "id": ..., "status": ..., "template_version_id": ..., ... },
  "workflow_templates": { "phases": ..., "graph_nodes": [...], "graph_edges": [...], ... },
  "history": [
    { "id": ..., "status": "completed", "output_data": {
        "_execution_meta": { "graph_node_id": "node-uuid-123", ... },
        ...
      }, ... },
    ...
  ],
}
```

The widget reads `history[*].output_data._execution_meta.graph_node_id` to map step rows → graph nodes. Plan 03 writes this; Plan 05 reads it.
</interfaces>

<context_notes>
**Discretion decisions documented (from CONTEXT.md):**

- **#6 Widget placement:** `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` (workspace-rendered). The widget IMPORTS the 7 node components from the shared `nodeTypes.ts` extracted from NodeCanvas.
- **#7 Active-node visual:** Tailwind `animate-pulse` + `ring-2 ring-amber-500` on the active node's outer wrapper. Add this via the React Flow node's `data.runState` prop (state machine: 'active' | 'completed' | 'pending' | 'skipped' | 'failed'); the existing node components (TriggerNode etc.) need a small extension to read `data.runState` and apply CSS classes accordingly. Plan 05 extends the existing node components (5-line edit per file = 35 lines total in Task 05-01b).
- **#8 SSE event shape:** Use existing `subscribeToExecution`. Map `event.step_id` → look up the corresponding workflow_steps row from the cached state → read `_execution_meta.graph_node_id` → flip that node's runState to 'completed' (or 'active' if the event is `workflow.step.started`).

**Canonical SSE event types (BLOCKER #2 fix from plan-checker iteration 1):**

ALL references to SSE event type strings in this plan + its tests use the dot-separated form. Concretely:

| Form to use | Form to AVOID |
|-------------|---------------|
| `'workflow.step.started'`   | ~~`'workflow_step.started'`~~ |
| `'workflow.step.completed'` | ~~`'workflow_step.completed'`~~ |
| `'workflow.step.failed'`    | ~~`'workflow_step.failed'`~~ |
| `'workflow.step.paused'`    | ~~`'workflow_step.paused'`~~ |

The implementation's `switch (event.type)` cases AND every test that fires a synthetic SSE event MUST use the dot-separated form. The widget executor should grep its own implementation + tests for `workflow_step\.` (underscore-then-dot, escaped) before committing — any match is a bug.

**Live state machine:**

```typescript
type NodeRunState = 'pending' | 'active' | 'completed' | 'skipped' | 'failed';
type EdgeRunState = 'pending' | 'taken' | 'not_taken';

interface RunStateMap {
  nodes: Record<string, NodeRunState>;  // keyed by graph_node_id
  edges: Record<string, EdgeRunState>;  // keyed by edge_id
}
```

Initial state on mount:
- Fetch execution + template via GET `/workflows/executions/{executionId}` (or whatever Spec A's existing endpoint is — check `frontend/src/services/workflows.ts` and `workflowExecutionStream.ts`).
- For each completed step in history: mark its graph_node_id 'completed'.
- For each running/pending step: mark its graph_node_id 'active' or 'pending'.
- For each condition node with a downstream completed step: mark the taken edge 'taken' (the one whose target's graph_node_id appears in the completed history); mark the other edge 'not_taken'.

On SSE event (note the DOT-separated forms):
- `workflow.step.started`: flip that step's graph_node_id to 'active' (and any previously 'active' to 'completed' if upstream).
- `workflow.step.completed`: flip to 'completed'. Re-evaluate edges (the just-completed step's outgoing chosen edge becomes 'taken').
- `workflow.step.failed`: flip to 'failed'.
- `workflow.step.paused`: optional — could flip to a 'paused' visual or treat as 'active'.

This is computed entirely client-side from data the existing SSE + execution-status endpoints already deliver. NO backend changes.

**WidgetRegistry routing helper signature (recommended):**

```typescript
import type { components } from '@/types/api.generated';
type GraphNode = components['schemas']['GraphNode'];

export function isBranchingTemplate(graphNodes: GraphNode[] | null | undefined): boolean {
  if (!graphNodes) return false;
  return graphNodes.some(n =>
    n.kind === 'condition' || n.kind === 'parallel' || n.kind === 'merge' || n.kind === 'human-approval'
  );
}

export function resolveWorkflowRunWidget(template: { graph_nodes?: GraphNode[] | null }): 'workflow_graph_run' | 'workflow_timeline' {
  return isBranchingTemplate(template.graph_nodes) ? 'workflow_graph_run' : 'workflow_timeline';
}
```

**Workspace-level integration:** Where does the workspace decide which widget to render for an execution? Plan 05 needs to look at the workspace's existing execution-render flow:
- If there's a centralized picker (e.g. in `WidgetRegistry` or a separate `WorkspaceRunWidget` component), update it to call `resolveWorkflowRunWidget`.
- If routing is per-call-site, Plan 05 picks ONE high-leverage call site (the workspace's run-widget host) and updates it; document any other call sites in the SUMMARY for follow-up.

Plan 05 SHOULD NOT touch the chat-bubble-rendered widgets pipeline.

**Node-component extension for runState (Task 05-01b):** The 7 node components (TriggerNode, AgentActionNode, OutputNode, ConditionNode, ParallelNode, MergeNode, HumanApprovalNode) currently read `data.label`, `data.config`, and (Phase 110 Plan 04) `data.validationErrors`. Plan 05 adds `data.runState?: NodeRunState` and applies CSS classes:
- 'active': `animate-pulse ring-2 ring-amber-500`
- 'completed': `ring-1 ring-emerald-500`
- 'pending': `opacity-50`
- 'skipped': `opacity-30 grayscale`
- 'failed': `ring-2 ring-red-500`
- (undefined): default (current Phase 110 styling)

This is a 3-5 line addition per node component file. Plan 05 makes all 7 changes uniformly via a shared helper `getRunStateClasses(runState)`.

**Edge styling:** React Flow edges support custom styles per edge id. Plan 05 passes an `edgeStyleMap` derived from `RunStateMap.edges` to the ReactFlow component via the `edges` array (each edge gets `style: {...}` and/or `className: ...` based on its EdgeRunState).

**Mock pattern for SSE in tests (note the DOT-separated event types):**

```typescript
const eventCallbacks: Array<(e: WorkflowEvent) => void> = [];
vi.mock('@/services/workflowExecutionStream', () => ({
  subscribeToExecution: (id: string, cb: (e: WorkflowEvent) => void) => {
    eventCallbacks.push(cb);
    return () => { /* unsubscribe noop */ };
  },
}));

// In test:
act(() => {
  eventCallbacks[0]({ type: 'workflow.step.started', step_id: 'step-uuid-1' });
  //                       ^^^^^^^^^^^^^^^^^^^^^^^ — DOT-SEPARATED.
});
// Then assert the DOM reflects the new active node.
```

**Branch hygiene:** `git branch --show-current` before every commit — `plan-109-spec-b-phase-1`.

**No backend changes in Plan 05.** All needed Python data flow (graph_node_id in _execution_meta) was added in Plan 03. The widget is purely a frontend addition.

**Warning #7 split rationale (plan-checker iteration 1):** The original Task 05-01 touched 11 files (shared module extraction + helper + 7 node components + 2 test files). Splitting into 05-01a (2 files: shared module extraction + NodeCanvas re-import) + 05-01b (9 files: helper + 7 node components + test) reduces blast radius. Each task can verify ALL existing tests pass before moving on, isolating any regression to the smaller diff.
</context_notes>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 05-01a: Extract shared NODE_TYPES module (2-file refactor)</name>
  <files>frontend/src/components/workflows/editor/nodeTypes.ts, frontend/src/components/workflows/editor/NodeCanvas.tsx</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Plan 03 + Plan 04 committed.
  </precondition>
  <action>
    Surgical 2-file refactor before any runState work begins. Isolating the extraction from the per-node edits keeps the diff small and confirms no regression in Phase 109/110 tests.

    **Edit 1:** Create `frontend/src/components/workflows/editor/nodeTypes.ts`:

    ```typescript
    // Shared node type map — used by NodeCanvas (editor) + WorkflowGraphRunWidget (workspace).
    import TriggerNode from './nodes/TriggerNode';
    import AgentActionNode from './nodes/AgentActionNode';
    import OutputNode from './nodes/OutputNode';
    import ConditionNode from './nodes/ConditionNode';
    import ParallelNode from './nodes/ParallelNode';
    import MergeNode from './nodes/MergeNode';
    import HumanApprovalNode from './nodes/HumanApprovalNode';

    export const NODE_TYPES = {
      trigger: TriggerNode,
      'agent-action': AgentActionNode,
      output: OutputNode,
      condition: ConditionNode,
      parallel: ParallelNode,
      merge: MergeNode,
      'human-approval': HumanApprovalNode,
    } as const;
    ```

    **Edit 2:** Update `frontend/src/components/workflows/editor/NodeCanvas.tsx` to import from the new module: replace the local NODE_TYPES definition with `import { NODE_TYPES } from './nodeTypes';`.

    The extraction is functionally identical — Phase 109's tests (NodeCanvas + per-node component tests) should ALL still pass without any test edits.

    Commit message: `refactor(111-05): extract shared NODE_TYPES to nodeTypes.ts (workspace+editor reuse)`.

    Verify by running the FULL workflows test suite. ANY failure here is a refactor bug — fix immediately, don't proceed.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
    <automated>grep -c "NODE_TYPES" frontend/src/components/workflows/editor/nodeTypes.ts</automated>
    <automated>grep -c "from './nodeTypes'" frontend/src/components/workflows/editor/NodeCanvas.tsx</automated>
  </verify>
  <done>
    - `nodeTypes.ts` shared module exists, exports NODE_TYPES.
    - NodeCanvas.tsx imports from the new module (local map removed).
    - All Phase 109/110 workflow vitest tests still GREEN — zero test edits required.
    - tsc clean.
    - One commit on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 05-01b: runStateStyles helper + uniform 7-node-component extension</name>
  <files>frontend/src/components/workflows/editor/runStateStyles.ts, frontend/src/components/workflows/editor/nodes/TriggerNode.tsx, frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx, frontend/src/components/workflows/editor/nodes/OutputNode.tsx, frontend/src/components/workflows/editor/nodes/ConditionNode.tsx, frontend/src/components/workflows/editor/nodes/ParallelNode.tsx, frontend/src/components/workflows/editor/nodes/MergeNode.tsx, frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx, frontend/src/__tests__/workflows/runStateStyles.test.ts</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 05-01a committed.
  </precondition>
  <behavior>
    **RED phase — write `frontend/src/__tests__/workflows/runStateStyles.test.ts` with ≥7 tests:**

    Tests for `getNodeRunStateClasses`:
    1. `returns_active_classes_for_active` — input 'active' → output contains 'animate-pulse' AND 'ring-amber-500'.
    2. `returns_completed_classes_for_completed` → 'ring-emerald-500'.
    3. `returns_pending_classes_for_pending` → 'opacity-50'.
    4. `returns_skipped_classes_for_skipped` → 'opacity-30' AND 'grayscale'.
    5. `returns_failed_classes_for_failed` → 'ring-red-500'.
    6. `returns_empty_string_for_undefined` → empty string.

    Tests for `getEdgeRunStateStyle`:
    7. `returns_emerald_stroke_for_taken` → object with `stroke` set.
    8. `returns_muted_style_for_not_taken` → opacity < 0.5 AND strokeDasharray set.
    9. `returns_empty_object_for_pending_or_undefined` → empty object.

    Optional: 1-2 tests on a representative node component (e.g. ConditionNode) verifying that when `data.runState` changes, the rendered className updates. Use React Testing Library + the Phase 110 node component test patterns.

    Commit RED: `test(111-05): add failing tests for runStateStyles helper + per-node runState rendering`.

    **GREEN phase — implement:**

    Create `frontend/src/components/workflows/editor/runStateStyles.ts`:

    ```typescript
    export type NodeRunState = 'pending' | 'active' | 'completed' | 'skipped' | 'failed';
    export type EdgeRunState = 'pending' | 'taken' | 'not_taken';

    export function getNodeRunStateClasses(runState: NodeRunState | undefined): string {
      switch (runState) {
        case 'active': return 'animate-pulse ring-2 ring-amber-500';
        case 'completed': return 'ring-1 ring-emerald-500';
        case 'pending': return 'opacity-50';
        case 'skipped': return 'opacity-30 grayscale';
        case 'failed': return 'ring-2 ring-red-500';
        default: return '';
      }
    }

    export function getEdgeRunStateStyle(runState: EdgeRunState | undefined): { stroke?: string; strokeWidth?: number; opacity?: number; strokeDasharray?: string } {
      switch (runState) {
        case 'taken': return { stroke: '#10b981', strokeWidth: 2.5 };
        case 'not_taken': return { stroke: '#94a3b8', opacity: 0.3, strokeDasharray: '6,4' };
        case 'pending':
        default: return {};
      }
    }
    ```

    Extend each of the 7 node components uniformly. The edit pattern per file (2-3 lines):

    ```tsx
    // 1. Import (add to existing imports):
    import { getNodeRunStateClasses, type NodeRunState } from '../runStateStyles';

    // 2. Extend the data prop interface:
    runState?: NodeRunState;

    // 3. Apply to the outermost wrapper className:
    <div className={`... existing-classes ... ${getNodeRunStateClasses(data.runState)}`}>
    ```

    **Per-component verification step:** After editing EACH of the 7 components, run `npx tsc --noEmit` before moving to the next. This catches any typo or import path issue with a tight loop.

    Apply uniformly via a single pass — each node file's edit is identical except for the existing class string in the wrapper. Use a consistent pattern (e.g. always append the runState classes at the END of the existing className string).

    Commit GREEN: `feat(111-05): add runStateStyles helper + extend 7 node components with data.runState`.

    Run the FULL workflows test suite — all Phase 109/110 tests + the new runStateStyles tests must pass.
  </behavior>
  <action>
    Follow the behavior block. The 7-file uniform edit pattern: do them one at a time, running `npx tsc --noEmit` after each, before moving to the next. This catches any divergence early.

    Verify uniformity post-commit:
    ```bash
    for f in frontend/src/components/workflows/editor/nodes/*.tsx; do
      grep -l "getNodeRunStateClasses" "$f" || echo "MISSING: $f"
    done
    ```
    Should list all 7 files with the helper imported. Any "MISSING" line is a bug.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/runStateStyles.test.ts --reporter=verbose</automated>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/ConditionNode.tsx</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/TriggerNode.tsx</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/OutputNode.tsx</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/ParallelNode.tsx</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/MergeNode.tsx</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx</automated>
  </verify>
  <done>
    - `runStateStyles.ts` with `getNodeRunStateClasses` + `getEdgeRunStateStyle` exists.
    - All 7 node components read `data.runState` and apply classes (verified via per-file grep).
    - 7+ runStateStyles tests GREEN.
    - All Phase 109/110 workflow tests still GREEN (runState defaults to undefined → empty class string → no visual change).
    - tsc clean.
    - Two commits on `plan-109-spec-b-phase-1` (RED, GREEN).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 05-02: WidgetRegistry routing helper + workflow_graph_run map entry</name>
  <files>frontend/src/components/widgets/WidgetRegistry.tsx, frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 05-01a + 05-01b committed.
  </precondition>
  <behavior>
    **RED — extend `frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx` with ≥5 new tests:**

    1. `resolveWorkflowRunWidget_returns_workflow_graph_run_for_branching` — template with `graph_nodes` containing a condition kind → returns `'workflow_graph_run'`.
    2. `resolveWorkflowRunWidget_returns_workflow_timeline_for_linear` — template with only trigger/agent-action/output → returns `'workflow_timeline'`.
    3. `resolveWorkflowRunWidget_returns_timeline_for_undefined_graph_nodes` — template missing `graph_nodes` (legacy) → returns `'workflow_timeline'`.
    4. `isBranchingTemplate_returns_true_for_parallel` — parallel kind triggers branching detection.
    5. `isBranchingTemplate_returns_true_for_human_approval` — human-approval also triggers branching.
    6. `WIDGET_MAP_has_workflow_graph_run` — assert `resolveWidget('workflow_graph_run')` returns a non-Unknown component (the new WorkflowGraphRunWidget — at this point the import is a stub, replaced in Task 05-03).
    7. `existing_widget_resolutions_unchanged` — `resolveWidget('workflow_timeline')` still returns the existing WorkflowTimelineWidget (regression guard).

    Commit RED.

    **GREEN — extend `frontend/src/components/widgets/WidgetRegistry.tsx`:**

    Add the import + WIDGET_MAP entry. Initially, the import target is a stub that Task 05-03 replaces:
    ```tsx
    const WorkflowGraphRunWidget = dynamic(() => import('./WorkflowGraphRunWidget'), {
      loading: WidgetSkeleton,
      ssr: false,
    });

    const WIDGET_MAP: Record<string, ComponentType<WidgetProps>> = {
      ...existing entries...,
      workflow_graph_run: WorkflowGraphRunWidget,
    };
    ```

    Add the routing helpers (exported functions):
    ```typescript
    import type { components } from '@/types/api.generated';
    type GraphNode = components['schemas']['GraphNode'];

    /**
     * Discretion #5 / Plan 01 mirror — predicate matches the backend's
     * _template_requires_graph_executor.
     */
    export function isBranchingTemplate(
      graphNodes: GraphNode[] | null | undefined,
    ): boolean {
      if (!graphNodes) return false;
      return graphNodes.some(
        n =>
          n.kind === 'condition' ||
          n.kind === 'parallel' ||
          n.kind === 'merge' ||
          n.kind === 'human-approval',
      );
    }

    export function resolveWorkflowRunWidget(
      template: { graph_nodes?: GraphNode[] | null },
    ): 'workflow_graph_run' | 'workflow_timeline' {
      return isBranchingTemplate(template.graph_nodes)
        ? 'workflow_graph_run'
        : 'workflow_timeline';
    }
    ```

    Create a stub `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` so the dynamic import resolves (Task 05-03 replaces it with the real implementation):
    ```tsx
    'use client';
    import React from 'react';
    import { WidgetProps } from './WidgetRegistry';

    export default function WorkflowGraphRunWidget(_: WidgetProps) {
      return <div data-testid="workflow-graph-run-widget-stub">Loading branched run...</div>;
    }
    ```

    Commit GREEN. Verify all 7 new tests + ~30 existing WidgetRegistry tests GREEN.
  </behavior>
  <action>
    Follow the behavior block. The stub component is intentional — Task 05-03 replaces the body with real implementation. Splitting the registry change from the component implementation keeps each commit reviewable.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/widgets/__tests__/WidgetRegistry.test.tsx --reporter=verbose</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
    <automated>grep -c "workflow_graph_run" frontend/src/components/widgets/WidgetRegistry.tsx</automated>
    <automated>grep -c "resolveWorkflowRunWidget\|isBranchingTemplate" frontend/src/components/widgets/WidgetRegistry.tsx</automated>
  </verify>
  <done>
    - WidgetRegistry has `workflow_graph_run` entry + `isBranchingTemplate` + `resolveWorkflowRunWidget` exports.
    - Stub `WorkflowGraphRunWidget.tsx` exists.
    - 7+ new tests GREEN, no regression.
    - Two commits on `plan-109-spec-b-phase-1`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 05-03: WorkflowGraphRunWidget implementation + live state machine (with canonical SSE event names)</name>
  <files>frontend/src/components/widgets/WorkflowGraphRunWidget.tsx, frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 05-01a + 05-01b + 05-02 committed.
  </precondition>
  <behavior>
    **CRITICAL — SSE event type names (BLOCKER #2 fix):** The backend emits dot-separated event types: `workflow.step.started`, `workflow.step.completed`, `workflow.step.failed`, `workflow.step.paused`. The original Plan 05 draft used `workflow_step.started` (underscore-then-dot) which would NEVER match the backend wire. EVERY reference in this task — implementation switch cases AND test event types — uses the canonical dot-separated form.

    Verification before commit: `grep -E "workflow_step\." frontend/src/components/widgets/WorkflowGraphRunWidget.tsx frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx` MUST return ZERO matches.

    **RED — `frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx`, ≥12 tests:**

    Setup helpers (top of file):
    - Mock `@xyflow/react` (mirror the pattern from `frontend/src/__tests__/workflows/NodeCanvas.test.tsx`).
    - Mock `@/services/workflowExecutionStream.subscribeToExecution` to capture the event callback in a module-level array.
    - Mock `@/services/api.fetchWithAuth` (or the relevant function) to return a deterministic execution status payload.

    Tests:

    1. `renders_loading_state_initially` — definition exists, fetch in-flight → "Loading..." / spinner present.
    2. `renders_graph_after_fetch_resolves` — fetch resolves with template + history → React Flow canvas (mocked) renders with the correct node count + edge count.
    3. `marks_completed_steps_as_completed_on_mount` — history has 2 completed steps with graph_node_id values → both corresponding nodes have `data.runState === 'completed'`.
    4. `marks_running_step_as_active_on_mount` — history has 1 'running' step → that node has `data.runState === 'active'`.
    5. `highlights_taken_edge_after_condition` — history shows trigger→condition completed AND a downstream 'true'-branch step completed → the 'true'-handle edge has `style.stroke === '#10b981'` (or matches `getEdgeRunStateStyle('taken')` output); the 'false'-handle edge has `opacity === 0.3` (taken='not_taken' style).
    6. `sse_event_flips_node_to_active` — call the captured event callback with `{type: 'workflow.step.started', step_id: 'sx'}` → the node corresponding to that step's graph_node_id gets `data.runState === 'active'`. (The widget needs to maintain a step_id ↔ graph_node_id lookup map.)  **NOTE: use the DOT-SEPARATED form `workflow.step.started`.**
    7. `sse_event_flips_node_to_completed` — fire `{type: 'workflow.step.completed', ...}` → runState becomes 'completed'.
    8. `pending_nodes_are_muted` — nodes that have no corresponding step row (not yet executed) have `data.runState === 'pending'` (opacity-50).
    9. `linear_template_without_branching_renders_with_no_taken_edges` — defense — even if a linear template somehow reaches this widget (shouldn't via routing helper, but Plan 05 must not crash), it renders without errors and all edges have undefined/pending runState.
    10. `unsubscribes_sse_on_unmount` — unmount component → captured unsubscribe function was called.
    11. `failed_step_marks_node_failed` — SSE event `{type: 'workflow.step.failed', ...}` or history status 'failed' → node has `data.runState === 'failed'` (red ring).
    12. `re_evaluates_taken_edge_after_late_completion` — initial mount has trigger+condition completed but no downstream; later SSE event `{type: 'workflow.step.completed', ...}` flips a downstream node to completed → re-renders with the now-taken edge highlighted.

    For CodeMirror-style heavy components, mock `@uiw/react-codemirror` if needed (Plan 04 already mocked it). For React Flow, mirror the existing NodeCanvas.test.tsx mock.

    Commit RED: `test(111-05): add failing tests for WorkflowGraphRunWidget (canonical workflow.step.* SSE)`.

    **GREEN — implement `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` (~250-300 lines):**

    Replace the stub. Real implementation:

    ```tsx
    'use client';

    import React, { useEffect, useMemo, useState, useCallback } from 'react';
    import { ReactFlow, ReactFlowProvider, Background, Controls, type Node, type Edge } from '@xyflow/react';
    import '@xyflow/react/dist/style.css';
    import { WidgetProps } from './WidgetRegistry';
    import { fetchWithAuth } from '@/services/api';
    import { subscribeToExecution, type WorkflowEvent } from '@/services/workflowExecutionStream';
    import { NODE_TYPES } from '@/components/workflows/editor/nodeTypes';
    import {
      type NodeRunState,
      type EdgeRunState,
      getEdgeRunStateStyle,
    } from '@/components/workflows/editor/runStateStyles';

    interface ExecutionPayload {
      execution: {
        id: string;
        status: string;
        template_version_id: string | null;
      };
      workflow_templates: {
        graph_nodes?: Array<{ id: string; kind: string; label?: string; config?: Record<string, unknown>; position?: { x: number; y: number } }>;
        graph_edges?: Array<{ id: string; source: string; target: string; source_handle?: string | null; label?: string | null }>;
      };
      history: Array<{
        id: string;
        status: string;
        output_data?: { _execution_meta?: { graph_node_id?: string } } | null;
      }>;
    }

    function deriveRunState(payload: ExecutionPayload): {
      nodeState: Record<string, NodeRunState>;
      edgeState: Record<string, EdgeRunState>;
      stepIdToNodeId: Record<string, string>;
    } {
      const nodeState: Record<string, NodeRunState> = {};
      const edgeState: Record<string, EdgeRunState> = {};
      const stepIdToNodeId: Record<string, string> = {};

      // Initial: all nodes pending
      for (const n of payload.workflow_templates.graph_nodes ?? []) {
        nodeState[n.id] = 'pending';
      }
      // All edges pending
      for (const e of payload.workflow_templates.graph_edges ?? []) {
        edgeState[e.id] = 'pending';
      }

      // Walk history: map step → node, set runState
      const completedNodeIds = new Set<string>();
      for (const step of payload.history) {
        const nodeId = step.output_data?._execution_meta?.graph_node_id;
        if (!nodeId) continue;
        stepIdToNodeId[step.id] = nodeId;
        switch (step.status) {
          case 'completed':
            nodeState[nodeId] = 'completed';
            completedNodeIds.add(nodeId);
            break;
          case 'running':
          case 'pending':
            nodeState[nodeId] = 'active';
            break;
          case 'failed':
            nodeState[nodeId] = 'failed';
            break;
          case 'skipped':
            nodeState[nodeId] = 'skipped';
            break;
        }
      }

      // For each condition node that has at least one completed downstream:
      // the edge to the completed downstream is 'taken'; the other is 'not_taken'.
      const edges = payload.workflow_templates.graph_edges ?? [];
      const nodes = payload.workflow_templates.graph_nodes ?? [];
      for (const node of nodes) {
        if (node.kind !== 'condition') continue;
        const outEdges = edges.filter(e => e.source === node.id);
        for (const edge of outEdges) {
          if (completedNodeIds.has(edge.target)) {
            edgeState[edge.id] = 'taken';
          } else if (outEdges.some(e2 => completedNodeIds.has(e2.target))) {
            edgeState[edge.id] = 'not_taken';
          }
        }
      }

      return { nodeState, edgeState, stepIdToNodeId };
    }

    function GraphRunCanvas({ executionId }: { executionId: string }) {
      const [payload, setPayload] = useState<ExecutionPayload | null>(null);
      const [nodeState, setNodeState] = useState<Record<string, NodeRunState>>({});
      const [edgeState, setEdgeState] = useState<Record<string, EdgeRunState>>({});
      const [stepIdToNodeId, setStepIdToNodeId] = useState<Record<string, string>>({});
      const [error, setError] = useState<string | null>(null);

      // Fetch execution + template on mount
      useEffect(() => {
        let cancelled = false;
        (async () => {
          try {
            const res = await fetchWithAuth(`/workflows/executions/${executionId}/status`);
            if (cancelled) return;
            const data: ExecutionPayload = await res.json();
            setPayload(data);
            const derived = deriveRunState(data);
            setNodeState(derived.nodeState);
            setEdgeState(derived.edgeState);
            setStepIdToNodeId(derived.stepIdToNodeId);
          } catch (err) {
            if (!cancelled) setError(String(err));
          }
        })();
        return () => { cancelled = true; };
      }, [executionId]);

      // SSE subscription — handles canonical workflow.step.* dot-separated events.
      // BLOCKER #2 fix from plan-checker iteration 1: backend emits
      // `workflow.step.{status}` (dot-separated), NOT `workflow_step.{status}`.
      useEffect(() => {
        const unsub = subscribeToExecution(executionId, (event: WorkflowEvent) => {
          const stepId = event.step_id;
          if (!stepId) return;
          const nodeId = stepIdToNodeId[stepId];
          if (!nodeId) {
            // New step not in initial fetch — refetch status to learn its node mapping
            fetchWithAuth(`/workflows/executions/${executionId}/status`)
              .then(r => r.json())
              .then((data: ExecutionPayload) => {
                const derived = deriveRunState(data);
                setNodeState(derived.nodeState);
                setEdgeState(derived.edgeState);
                setStepIdToNodeId(derived.stepIdToNodeId);
              })
              .catch(() => { /* non-fatal */ });
            return;
          }
          setNodeState(prev => {
            const next = { ...prev };
            switch (event.type) {
              case 'workflow.step.started':
                next[nodeId] = 'active';
                break;
              case 'workflow.step.completed':
                next[nodeId] = 'completed';
                // Re-eval edges for this node's upstream conditions
                if (payload) {
                  const upstream = (payload.workflow_templates.graph_edges ?? []).find(e => e.target === nodeId);
                  if (upstream) {
                    const sourceNode = (payload.workflow_templates.graph_nodes ?? []).find(n => n.id === upstream.source);
                    if (sourceNode?.kind === 'condition') {
                      const allOut = (payload.workflow_templates.graph_edges ?? []).filter(e => e.source === sourceNode.id);
                      setEdgeState(prevE => {
                        const nextE = { ...prevE };
                        for (const e of allOut) {
                          nextE[e.id] = e.id === upstream.id ? 'taken' : 'not_taken';
                        }
                        return nextE;
                      });
                    }
                  }
                }
                break;
              case 'workflow.step.failed':
                next[nodeId] = 'failed';
                break;
              case 'workflow.step.paused':
                // Optional: visualize paused state as active for now.
                next[nodeId] = 'active';
                break;
            }
            return next;
          });
        });
        return unsub;
      }, [executionId, stepIdToNodeId, payload]);

      const reactFlowNodes: Node[] = useMemo(() => {
        if (!payload) return [];
        return (payload.workflow_templates.graph_nodes ?? []).map(n => ({
          id: n.id,
          type: n.kind,  // matches NODE_TYPES keys
          position: n.position ?? { x: 0, y: 0 },
          data: {
            label: n.label ?? '',
            config: n.config ?? {},
            runState: nodeState[n.id],
          },
        }));
      }, [payload, nodeState]);

      const reactFlowEdges: Edge[] = useMemo(() => {
        if (!payload) return [];
        return (payload.workflow_templates.graph_edges ?? []).map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.source_handle ?? undefined,
          label: e.label ?? undefined,
          style: getEdgeRunStateStyle(edgeState[e.id]),
        }));
      }, [payload, edgeState]);

      if (error) {
        return <div className="text-sm text-red-500 p-4">Failed to load run: {error}</div>;
      }
      if (!payload) {
        return <div className="text-sm text-slate-500 p-4">Loading branched run...</div>;
      }
      return (
        <div data-testid="workflow-graph-run-widget" className="w-full h-[480px] bg-slate-50 rounded-lg">
          <ReactFlow
            nodes={reactFlowNodes}
            edges={reactFlowEdges}
            nodeTypes={NODE_TYPES}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            fitView
          >
            <Background />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      );
    }

    export default function WorkflowGraphRunWidget({ definition }: WidgetProps) {
      const executionId = (definition.data?.execution_id ?? definition.data?.executionId) as string | undefined;
      if (!executionId) {
        return <div className="text-sm text-amber-600 p-3">No execution_id provided.</div>;
      }
      return (
        <ReactFlowProvider>
          <GraphRunCanvas executionId={executionId} />
        </ReactFlowProvider>
      );
    }
    ```

    **Pre-commit guard:** run `grep -E "workflow_step\." frontend/src/components/widgets/WorkflowGraphRunWidget.tsx frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx` — output MUST be empty. If any match: revert to `workflow.step.` and re-run tests.

    Commit GREEN: `feat(111-05): WorkflowGraphRunWidget with canonical workflow.step.* SSE handling`.

    Verify all 12+ widget tests GREEN, all Phase 109/110 vitest tests still GREEN.
  </behavior>
  <action>
    Follow the behavior block. Use the SSE mock pattern from `<context_notes>`. The widget is the largest deliverable in Plan 05 — keep the implementation focused on the live state machine.

    Before commit, run the guard grep to ensure no `workflow_step.` (underscore-then-dot) form leaked in:
    ```bash
    grep -nE "workflow_step\." frontend/src/components/widgets/WorkflowGraphRunWidget.tsx frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx
    ```
    Empty output = clean. Any match = bug.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx --reporter=verbose</automated>
    <automated>cd frontend && npx vitest run src/components/widgets/__tests__/ src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
    <automated>grep -c "workflow.step.started\|workflow.step.completed\|workflow.step.failed" frontend/src/components/widgets/WorkflowGraphRunWidget.tsx</automated>
    <automated>grep -cE "workflow_step\." frontend/src/components/widgets/WorkflowGraphRunWidget.tsx frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx</automated>
  </verify>
  <done>
    - `WorkflowGraphRunWidget.tsx` implements live state machine + SSE subscription + initial fetch.
    - All 4 SSE switch cases use CANONICAL dot-separated event types: `workflow.step.started`, `workflow.step.completed`, `workflow.step.failed`, `workflow.step.paused`.
    - Guard grep returns ZERO matches for `workflow_step.` (underscore-then-dot) form.
    - 12+ widget tests GREEN, with ≥3 tests firing canonical dot-separated SSE events.
    - Phase 109/110 workflow + widget tests still GREEN (no regression).
    - tsc clean.
    - Two commits on `plan-109-spec-b-phase-1` (RED, GREEN).
  </done>
</task>

</tasks>

<verification>
**Plan-level checks before SUMMARY:**

1. `git branch --show-current` returns `plan-109-spec-b-phase-1`.
2. `cd frontend && npx vitest run src/components/widgets/__tests__/ src/__tests__/workflows/ --reporter=basic` — all tests GREEN (Phase 109 + 110 + 111 widget + 111 workflows).
3. `cd frontend && npx tsc --noEmit` — clean.
4. `grep -c "workflow_graph_run" frontend/src/components/widgets/WidgetRegistry.tsx` ≥ 2.
5. `grep -c "resolveWorkflowRunWidget\|isBranchingTemplate" frontend/src/components/widgets/WidgetRegistry.tsx` ≥ 2.
6. `grep -c "subscribeToExecution" frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` ≥ 1.
7. `grep -c "NODE_TYPES" frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` ≥ 1 (imports from shared module).
8. **BLOCKER #2 guard:** `grep -cE "workflow_step\." frontend/src/components/widgets/WorkflowGraphRunWidget.tsx frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx` → 0 matches across both files.
9. **Canonical event names present:** `grep -c "workflow.step.completed" frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` ≥ 1.
10. WorkflowTimelineWidget unchanged: `git diff plan-109-spec-b-phase-1~10 -- frontend/src/components/widgets/WorkflowTimelineWidget.tsx` should show no Plan 05 commits modified it.
11. Spec A SSE service unchanged: `git diff plan-109-spec-b-phase-1~10 -- frontend/src/services/workflowExecutionStream.ts` should show no Plan 05 changes.
12. No backend changes in this plan: `git diff plan-109-spec-b-phase-1~5 -- app/ supabase/` should be empty for Plan 05 commits.
13. The 7 node components updated uniformly: `for f in frontend/src/components/workflows/editor/nodes/*.tsx; do grep -l "getNodeRunStateClasses" "$f"; done` should list all 7.
</verification>

<success_criteria>
- ROADMAP criterion 8 SHIPPED: `WorkflowGraphRunWidget` renders branched runs with: active node (pulsing border via animate-pulse), taken edge highlighted (emerald stroke), not-taken edge muted (opacity 0.3 + dashed), pending nodes at opacity 0.5. Vitest test asserts DOM reflects state transitions via mocked SSE.
- **BLOCKER #2 closed:** ALL SSE event type strings use canonical dot-separated form (`workflow.step.started/completed/failed/paused`). The widget actually reacts to backend events instead of silently no-op'ing as in the original draft.
- ROADMAP criterion 9 SHIPPED: `resolveWorkflowRunWidget` routes branching templates to `workflow_graph_run`, linear templates to `workflow_timeline`. Unit tests for both cases.
- ROADMAP criterion 10 SHIPPED via static guarantee: Spec A's `OutcomeWriter`, `event_bus`, `workflowExecutionStream.ts`, and `WorkflowTimelineWidget.tsx` are NOT modified by Plan 05. Grep + git-diff verification.
- 7 node components support `data.runState` via shared `runStateStyles.ts` helper — uniform visual treatment.
- Shared `nodeTypes.ts` module extracted from NodeCanvas — editor + widget reuse the same components (Discretion #6).
- CodeMirror 6 NOT pulled in by Plan 05 (already in Plan 04) — no new deps added by Plan 05.
- ~7-9 commits on `plan-109-spec-b-phase-1` (RED/GREEN splits across 4 tasks; Task 05-01a is a single refactor commit).
</success_criteria>

<output>
After completion, create `.planning/phases/111-workflow-node-editor-branching-execution/111-05-SUMMARY.md` mirroring Phase 110 Plan 05's SUMMARY structure.

This SUMMARY also closes Phase 111: include a section "**Phase 111 SHIPS at this plan's completion**" listing the 6 NODEEDITOR-* requirement IDs mapped to plans, plus a ROADMAP success criteria table covering all 11 criteria.

In "Deviations from Plan", document iteration-1 plan-checker fixes: Blocker #2 (canonical workflow.step.* event names) + Warning #7 (Task 05-01 split into 05-01a + 05-01b).
</output>
