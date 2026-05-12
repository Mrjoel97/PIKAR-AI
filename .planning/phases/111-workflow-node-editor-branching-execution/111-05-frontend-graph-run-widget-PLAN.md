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
requirements:
  - NODEEDITOR-WIDGET-01
  - NODEEDITOR-COMPAT-01

must_haves:
  truths:
    - "A new widget WorkflowGraphRunWidget exists at frontend/src/components/widgets/WorkflowGraphRunWidget.tsx — fetches the execution + its pinned template version's graph, then renders a live React Flow canvas with status overlays"
    - "WidgetRegistry maps the widget-type string 'workflow_graph_run' (or similar — planner picks; reuse if a routing function already exists) to WorkflowGraphRunWidget"
    - "WorkflowGraphRunWidget consumes the existing Spec A SSE event bus via subscribeToExecution (Phase 109/110) — NO modifications to the SSE wire format"
    - "WorkflowGraphRunWidget imports NODE_TYPES from frontend/src/components/workflows/editor/NodeCanvas.tsx (or extracts a shared module) — reuses the 7 visual node components rather than re-implementing them (Discretion #6)"
    - "The widget renders the currently-executing node with an active-state visual (pulsing border via Tailwind animate-pulse + ring-amber-500) — Discretion #7"
    - "The widget highlights the edge from a condition node whose branch was TAKEN (visible in workflow_steps rows) — the not-taken edge is muted (opacity-30)"
    - "Not-yet-reached nodes are rendered at reduced opacity (opacity-50) — the user can visually distinguish 'queued', 'active', 'completed', and 'skipped/not-taken'"
    - "A vitest test mocks the SSE stream + the GET execution endpoint and asserts that the DOM reflects the active/taken/muted states on a 2-branch conditional template (ROADMAP criterion 8)"
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
      to: "frontend/src/components/workflows/editor/NodeCanvas.tsx"
      via: "import { NODE_TYPES } or extracted shared NODE_TYPES module"
      pattern: "NODE_TYPES|NodeTypes"
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
@CLAUDE.md

<interfaces>
<!-- Phase 109 + 110 — already on disk, reuse without modification. -->

```typescript
// frontend/src/services/workflowExecutionStream.ts (existing — Phase 109 / Spec A)
export interface WorkflowEvent {
    type: string;          // e.g. 'workflow_step.started', 'workflow_step.completed'
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
// Plan 05 needs to either (a) export this map, or (b) extract it into a
// shared module both NodeCanvas + WorkflowGraphRunWidget import from.
//
// Recommended: extract to frontend/src/components/workflows/editor/nodeTypes.ts
// (small refactor, ~10 lines), keeping NodeCanvas backward-compat by re-export.
// Plan 05 should make this extraction surgical.
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
//
// The workspace's run-widget-picker (or wherever the widget-type-string is decided
// for a given execution) calls this helper. If no existing picker exists at the
// call site, Plan 05 may add a small extension at the workspace level — DOCUMENT
// where in the plan SUMMARY.
```

```typescript
// frontend/src/types/api.generated.ts (Phase 109)
// Provides:
//   components.schemas.WorkflowTemplateResponse (with graph_nodes, graph_edges, graph_layout, current_version_id)
//   components.schemas.GraphNode / GraphEdge / NodePosition / NodeKind
```

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

- **#6 Widget placement:** `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` (workspace-rendered). The widget IMPORTS the 7 node components from the editor module (or a shared `nodeTypes.ts` extracted from NodeCanvas).
- **#7 Active-node visual:** Tailwind `animate-pulse` + `ring-2 ring-amber-500` on the active node's outer wrapper. Add this via the React Flow node's `data.runState` prop (state machine: 'active' | 'completed' | 'pending' | 'skipped' | 'failed'); the existing node components (TriggerNode etc.) need a small extension to read `data.runState` and apply CSS classes accordingly — OR Plan 05 wraps each rendered node in a sibling overlay. Recommendation: extend the existing node components (5-line edit per file = 35 lines total) to read `data.runState`. This keeps the visual logic close to the node UI.
- **#8 SSE event shape:** Use existing `subscribeToExecution`. Map `event.step_id` → look up the corresponding workflow_steps row from the cached state → read `_execution_meta.graph_node_id` → flip that node's runState to 'completed' (or 'active' if the event is 'workflow_step.started').

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

On SSE event:
- `workflow_step.started`: flip that step's graph_node_id to 'active' (and any previously 'active' to 'completed' if upstream).
- `workflow_step.completed`: flip to 'completed'. Re-evaluate edges (the just-completed step's outgoing chosen edge becomes 'taken').
- `workflow_step.failed`: flip to 'failed'.

This is computed entirely client-side from data the existing SSE + execution-status endpoints already deliver. NO backend changes.

**WidgetRegistry routing helper signature (recommended):**

```typescript
// In WidgetRegistry.tsx or a sibling util file:
import type { GraphNode } from '@/types/api.generated';

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

This mirrors `_template_requires_graph_executor` on the backend — same predicate, different runtime.

**Workspace-level integration:** Where does the workspace decide which widget to render for an execution? Plan 05 needs to look at the workspace's existing execution-render flow:
- If there's a centralized picker (e.g. in `WidgetRegistry` or a separate `WorkspaceRunWidget` component), update it to call `resolveWorkflowRunWidget`.
- If routing is per-call-site, Plan 05 picks ONE high-leverage call site (the workspace's run-widget host) and updates it; document any other call sites in the SUMMARY for follow-up.

Plan 05 SHOULD NOT touch the chat-bubble-rendered widgets pipeline (which uses `WidgetRegistry.resolveWidget(definition.type)` with a server-supplied type) — those agent-emitted widgets get their type from the LLM and Plan 05 doesn't change that.

**Node-component extension for runState:** The 7 node components (TriggerNode, AgentActionNode, OutputNode, ConditionNode, ParallelNode, MergeNode, HumanApprovalNode) currently read `data.label`, `data.config`, and (Phase 110 Plan 04) `data.validationErrors`. Plan 05 adds `data.runState?: NodeRunState` and applies CSS classes:
- 'active': `animate-pulse ring-2 ring-amber-500`
- 'completed': `ring-1 ring-emerald-500`
- 'pending': `opacity-50`
- 'skipped': `opacity-30 grayscale`
- 'failed': `ring-2 ring-red-500`
- (undefined): default (current Phase 110 styling)

This is a 3-5 line addition per node component file. Plan 05 makes all 7 changes uniformly via a shared helper `getRunStateClasses(runState)`.

**Edge styling:** React Flow edges support custom styles per edge id. Plan 05 passes an `edgeStyleMap` derived from `RunStateMap.edges` to the ReactFlow component via the `edges` array (each edge gets `style: {...}` and/or `className: ...` based on its EdgeRunState).

**Mock pattern for SSE in tests:**

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
  eventCallbacks[0]({ type: 'workflow_step.started', step_id: 'step-uuid-1' });
});
// Then assert the DOM reflects the new active node.
```

**Branch hygiene:** `git branch --show-current` before every commit — `plan-109-spec-b-phase-1`.

**No backend changes in Plan 05.** All needed Python data flow (graph_node_id in _execution_meta) was added in Plan 03. The widget is purely a frontend addition.
</context_notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 05-01: Extract shared NODE_TYPES + extend node components with runState</name>
  <files>frontend/src/components/workflows/editor/nodeTypes.ts, frontend/src/components/workflows/editor/NodeCanvas.tsx, frontend/src/components/workflows/editor/nodes/TriggerNode.tsx, frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx, frontend/src/components/workflows/editor/nodes/OutputNode.tsx, frontend/src/components/workflows/editor/nodes/ConditionNode.tsx, frontend/src/components/workflows/editor/nodes/ParallelNode.tsx, frontend/src/components/workflows/editor/nodes/MergeNode.tsx, frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx, frontend/src/components/workflows/editor/runStateStyles.ts, frontend/src/__tests__/workflows/runStateStyles.test.ts</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Plan 03 + Plan 04 committed.
  </precondition>
  <behavior>
    **Two surgical refactors before Plan 05's widget can ship:**

    **Refactor 1 — Extract NODE_TYPES to a shared module:**

    Create `frontend/src/components/workflows/editor/nodeTypes.ts`:
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

    Update `frontend/src/components/workflows/editor/NodeCanvas.tsx` to import from the new module: replace the local NODE_TYPES definition with `import { NODE_TYPES } from './nodeTypes';`. Verify Phase 109 + 110 tests still pass (the local map was inlined for Phase 109; the extraction is functionally identical).

    **Refactor 2 — runState helper + per-node className extension:**

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

    Tests for `runStateStyles.ts` (≥6 vitest tests covering all node + edge states + undefined fallback).

    Extend each of the 7 node components: read `data.runState` and merge `getNodeRunStateClasses(runState)` into the outermost wrapper's `className`. This is a 2-3 line edit per file:

    ```tsx
    // Inside e.g. ConditionNode.tsx:
    import { getNodeRunStateClasses, type NodeRunState } from '../runStateStyles';

    // In data prop interface:
    runState?: NodeRunState;

    // In the JSX:
    <div className={`... existing-classes ... ${getNodeRunStateClasses(data.runState)}`}>
    ```

    **RED phase:** Write tests first for `runStateStyles.ts` + 1-2 tests verifying a node component re-renders with the right className when data.runState changes (use ConditionNode as the representative — Phase 110 already has tests around it). Commit RED.

    **GREEN phase:** Implement the extraction + extensions. Commit GREEN.

    Phase 109 + Phase 110 Plan 04 tests for NodeCanvas + node components should ALL STILL PASS — this is a pure extraction + additive prop change (runState defaults to undefined and the additional className becomes empty).
  </behavior>
  <action>
    Follow the behavior block. Verify ALL existing workflow vitest tests still pass: `cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic`.

    The 7-file uniform edit pattern: use a single search+replace pass to add the runState className merge. Verify each file individually with `git diff` to catch any divergence.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/runStateStyles.test.ts --reporter=verbose</automated>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
    <automated>grep -c "NODE_TYPES" frontend/src/components/workflows/editor/nodeTypes.ts</automated>
    <automated>grep -c "getNodeRunStateClasses" frontend/src/components/workflows/editor/nodes/ConditionNode.tsx</automated>
  </verify>
  <done>
    - `nodeTypes.ts` shared module exists, exports NODE_TYPES.
    - NodeCanvas.tsx imports from the new module (local map removed).
    - `runStateStyles.ts` with `getNodeRunStateClasses` + `getEdgeRunStateStyle` exists.
    - All 7 node components read `data.runState` and apply classes.
    - 6+ runStateStyles tests GREEN.
    - All Phase 109/110 workflow tests still GREEN.
    - tsc clean.
    - Two commits on `plan-109-spec-b-phase-1` (RED, GREEN).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 05-02: WidgetRegistry routing helper + workflow_graph_run map entry</name>
  <files>frontend/src/components/widgets/WidgetRegistry.tsx, frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Task 05-01 committed.
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
  <name>Task 05-03: WorkflowGraphRunWidget implementation + live state machine</name>
  <files>frontend/src/components/widgets/WorkflowGraphRunWidget.tsx, frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx</files>
  <precondition>
    Run `git branch --show-current` — MUST return `plan-109-spec-b-phase-1`. Verify Tasks 05-01 + 05-02 committed.
  </precondition>
  <behavior>
    **RED — `frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx`, ≥10 tests:**

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
    6. `sse_event_flips_node_to_active` — call the captured event callback with `{type: 'workflow_step.started', step_id: 'sx'}` → the node corresponding to that step's graph_node_id gets `data.runState === 'active'`. (The widget needs to maintain a step_id ↔ graph_node_id lookup map.)
    7. `sse_event_flips_node_to_completed` — fire 'workflow_step.completed' → runState becomes 'completed'.
    8. `pending_nodes_are_muted` — nodes that have no corresponding step row (not yet executed) have `data.runState === 'pending'` (opacity-50).
    9. `linear_template_without_branching_renders_with_no_taken_edges` — defense — even if a linear template somehow reaches this widget (shouldn't via routing helper, but Plan 05 must not crash), it renders without errors and all edges have undefined/pending runState.
    10. `unsubscribes_sse_on_unmount` — unmount component → captured unsubscribe function was called.
    11. `failed_step_marks_node_failed` — SSE event 'workflow_step.failed' or history status 'failed' → node has `data.runState === 'failed'` (red ring).
    12. `re_evaluates_taken_edge_after_late_completion` — initial mount has trigger+condition completed but no downstream; later SSE event flips a downstream node to completed → re-renders with the now-taken edge highlighted.

    Commit RED.

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

      // SSE subscription
      useEffect(() => {
        const unsub = subscribeToExecution(executionId, (event: WorkflowEvent) => {
          const stepId = event.step_id;
          if (!stepId) return;
          const nodeId = stepIdToNodeId[stepId];
          if (!nodeId) {
            // New step not in initial fetch — refetch status to learn its node mapping
            // (lazy refetch; full implementation may merge incrementally instead)
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
              case 'workflow_step.started':
                next[nodeId] = 'active';
                break;
              case 'workflow_step.completed':
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
              case 'workflow_step.failed':
                next[nodeId] = 'failed';
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

    Commit GREEN.

    Verify all 12+ widget tests GREEN, all Phase 109/110 vitest tests still GREEN.
  </behavior>
  <action>
    Follow the behavior block. Use the SSE mock pattern from `<context_notes>`. The widget is the largest deliverable in Plan 05 — keep the implementation focused on the live state machine; defer "pretty" auto-layout to a future polish task (use whatever positions the saved template has).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx --reporter=verbose</automated>
    <automated>cd frontend && npx vitest run src/components/widgets/__tests__/ src/__tests__/workflows/ --reporter=basic</automated>
    <automated>cd frontend && npx tsc --noEmit</automated>
  </verify>
  <done>
    - `WorkflowGraphRunWidget.tsx` implements live state machine + SSE subscription + initial fetch.
    - 12+ widget tests GREEN.
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
8. WorkflowTimelineWidget unchanged: `git diff plan-109-spec-b-phase-1~10 -- frontend/src/components/widgets/WorkflowTimelineWidget.tsx` should show no Plan 05 commits modified it.
9. Spec A SSE service unchanged: `git diff plan-109-spec-b-phase-1~10 -- frontend/src/services/workflowExecutionStream.ts` should show no Plan 05 changes.
10. No backend changes in this plan: `git diff plan-109-spec-b-phase-1~5 -- app/ supabase/` should be empty for Plan 05 commits.
11. The 7 node components updated uniformly: `for f in frontend/src/components/workflows/editor/nodes/*.tsx; do grep -l "getNodeRunStateClasses" "$f"; done` should list all 7.
</verification>

<success_criteria>
- ROADMAP criterion 8 SHIPPED: `WorkflowGraphRunWidget` renders branched runs with: active node (pulsing border via animate-pulse), taken edge highlighted (emerald stroke), not-taken edge muted (opacity 0.3 + dashed), pending nodes at opacity 0.5. Vitest test asserts DOM reflects state transitions via mocked SSE.
- ROADMAP criterion 9 SHIPPED: `resolveWorkflowRunWidget` routes branching templates to `workflow_graph_run`, linear templates to `workflow_timeline`. Unit tests for both cases.
- ROADMAP criterion 10 SHIPPED via static guarantee: Spec A's `OutcomeWriter`, `event_bus`, `workflowExecutionStream.ts`, and `WorkflowTimelineWidget.tsx` are NOT modified by Plan 05. Grep + git-diff verification.
- 7 node components support `data.runState` via shared `runStateStyles.ts` helper — uniform visual treatment.
- Shared `nodeTypes.ts` module extracted from NodeCanvas — editor + widget reuse the same components (Discretion #6).
- CodeMirror 6 NOT pulled in by Plan 05 (already in Plan 04) — no new deps added by Plan 05.
- ~6-8 commits on `plan-109-spec-b-phase-1` (RED/GREEN splits across 3 tasks).
</success_criteria>

<output>
After completion, create `.planning/phases/111-workflow-node-editor-branching-execution/111-05-SUMMARY.md` mirroring Phase 110 Plan 05's SUMMARY structure.

This SUMMARY also closes Phase 111: include a section "**Phase 111 SHIPS at this plan's completion**" listing the 6 NODEEDITOR-* requirement IDs mapped to plans, plus a ROADMAP success criteria table covering all 11 criteria.
</output>
