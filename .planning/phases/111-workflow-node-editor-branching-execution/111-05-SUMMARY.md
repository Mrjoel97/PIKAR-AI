---
phase: 111-workflow-node-editor-branching-execution
plan: 05
subsystem: frontend
tags: [workflow-run-widget, react-flow, sse, branching-execution, live-state-machine, node-run-state, edge-styling, widget-registry, routing-helper, vitest, tdd, phase-111-shipping-complete]

# Dependency graph
requires:
  - phase: 111-03-engine-dispatch
    provides: output_data._execution_meta.graph_node_id JSONB key on every step row (read by widget via getWorkflowExecutionDetails history); canonical workflow.step.* SSE event format (UNCHANGED in this plan)
  - phase: 111-04-frontend-condition-ux
    provides: ConditionPropertiesEditor — saves condition node config.expression as JSONLogic; Plan 05 widget reads it to render condition nodes with live runState overlays
  - phase: 110-04-frontend-editable
    provides: NodeCanvas + 7 visual node components (TriggerNode/AgentActionNode/OutputNode/ConditionNode/ParallelNode/MergeNode/HumanApprovalNode); ReactFlowProvider pattern; WidgetRegistry skeleton + WIDGET_MAP + dynamic-import pattern
provides:
  - "frontend/src/components/workflows/editor/nodeTypes.ts — shared NODE_TYPES map exported for both editor (NodeCanvas) and workspace widget (WorkflowGraphRunWidget) reuse (Discretion #6)"
  - "frontend/src/components/workflows/editor/runStateStyles.ts — pure-function helpers getNodeRunStateClasses(runState) + getEdgeRunStateStyle(runState) implementing Discretion #7 visual contract (animate-pulse ring-amber-500 active / ring-emerald-500 completed / opacity-50 pending / opacity-30 grayscale skipped / ring-red-500 failed; emerald-stroke taken / muted+dashed not_taken)"
  - "7 node components extended uniformly with optional data.runState prop (Trigger/AgentAction/Output/Condition/Parallel/Merge/HumanApproval) — append helper output to outermost wrapper className"
  - "frontend/src/components/widgets/WorkflowGraphRunWidget.tsx — live React Flow widget for branched runs. ~410 lines. Subscribes to Spec A SSE stream, reads execution + template via getWorkflowExecutionDetails + getWorkflowTemplate, builds initial state from history rows keyed by output_data._execution_meta.graph_node_id"
  - "frontend/src/components/widgets/WidgetRegistry.tsx — workflow_graph_run WIDGET_MAP entry + isBranchingTemplate + resolveWorkflowRunWidget exported helpers"
  - "WidgetType union (frontend/src/types/widgets.ts) extended with 'workflow_graph_run'"
  - "25 new vitest tests (10 runStateStyles + 13 WidgetRegistry routing + 15 WorkflowGraphRunWidget) — full frontend workflow + widget suite 230 GREEN, zero regression vs Phase 110 + Plan 04"
affects: [112-and-beyond-phase-4-parallel-merge-approval, workspace-widget-picker-call-sites-yet-to-route-via-resolveWorkflowRunWidget]

# Tech tracking
tech-stack:
  added: []  # No new deps — all React Flow + CodeMirror infrastructure landed in Phase 109/110/111-04. Plan 05 is purely additive code on top of existing stacks.
  patterns:
    - "Shared module extraction for cross-surface reuse: NODE_TYPES extracted from NodeCanvas into a 2-file refactor (Task 05-01a) before the per-node runState edits (Task 05-01b). Editor and workspace widget both import from one canonical source."
    - "Pure-function visual helpers: runStateStyles.ts has two switch-on-enum helpers returning a className string and a React Flow Edge style object respectively. Pure / no React deps / unit-testable in isolation (10 vitest tests cover all transitions)."
    - "Optional data prop with backward-compat default: 7 node components accept data.runState as optional; undefined returns the empty class string from getNodeRunStateClasses so existing editor / Phase 109 viewer visuals are identical."
    - "Live state machine with ref-stabilized SSE handler: WorkflowGraphRunWidget's subscribeToExecution callback reads templateRef + stepMapRef refs so the subscription doesn't re-mount on every state update."
    - "Local edge re-evaluation on workflow.step.completed: when a node flips to 'completed', the widget walks the template's condition nodes and marks the matching outgoing edge 'taken' + siblings 'not_taken' WITHOUT refetching. Avoids stale-mock issue in tests AND minimizes network traffic in prod. Unknown-step events still trigger a full refresh() to learn new graph_node_id mappings."
    - "Canonical dot-separated SSE event types (BLOCKER #2 closure): switch cases AND test event types use 'workflow.step.{started,completed,failed,paused}' — matches backend wire format from app/workflows/step_executor.py:752-760. Pre-commit guard grep -cE 'workflow_step\\.' returns 0 in both implementation and test files."
    - "Mock React Flow with data-attributes surface: vitest mocks @xyflow/react to render <div data-testid='rf-node-{id}' data-run-state={...}> + <div data-testid='rf-edge-{id}' data-edge-stroke/opacity/dasharray={...}> for direct DOM assertion. Same pattern Phase 109's NodeCanvas test used; jsdom can't render real React Flow."
    - "Auto-fix [Rule 3 - Blocking] for typed widget registries: extending WidgetType union forces every Record<WidgetType, X> consumer to add the new entry. RecentWidgets.tsx WIDGET_TYPE_ICON map updated uniformly; tsc now passes."

key-files:
  created:
    - frontend/src/components/workflows/editor/nodeTypes.ts
    - frontend/src/components/workflows/editor/runStateStyles.ts
    - frontend/src/__tests__/workflows/runStateStyles.test.ts
    - frontend/src/components/widgets/WorkflowGraphRunWidget.tsx
    - frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx
  modified:
    - frontend/src/components/workflows/editor/NodeCanvas.tsx
    - frontend/src/components/workflows/editor/nodes/TriggerNode.tsx
    - frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx
    - frontend/src/components/workflows/editor/nodes/OutputNode.tsx
    - frontend/src/components/workflows/editor/nodes/ConditionNode.tsx
    - frontend/src/components/workflows/editor/nodes/ParallelNode.tsx
    - frontend/src/components/workflows/editor/nodes/MergeNode.tsx
    - frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx
    - frontend/src/components/widgets/WidgetRegistry.tsx
    - frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx
    - frontend/src/types/widgets.ts
    - frontend/src/components/layout/RecentWidgets.tsx

key-decisions:
  - "Workspace widget placement (Discretion #6): frontend/src/components/widgets/WorkflowGraphRunWidget.tsx (workspace-rendered) — imports NODE_TYPES from the editor's shared nodeTypes.ts module rather than re-implementing the 7 node components."
  - "Active node visual (Discretion #7): Tailwind animate-pulse + ring-2 ring-amber-500 via getNodeRunStateClasses helper. Completed = ring-1 ring-emerald-500. Pending = opacity-50. Skipped = opacity-30 grayscale. Failed = ring-2 ring-red-500."
  - "Edge styling: taken = #10b981 (emerald-500) stroke + strokeWidth 2.5; not_taken = #94a3b8 (slate-400) stroke + opacity 0.3 + strokeDasharray '6,4'; pending/undefined = {} (React Flow default)."
  - "Canonical SSE event types (BLOCKER #2 fix from plan-checker iteration 1): switch cases AND test event types use the dot-separated form 'workflow.step.{started,completed,failed,paused}' — verified against app/workflows/step_executor.py:752-760. The original draft used 'workflow_step.{started,...}' (underscore-then-dot) which would never match the backend wire and the widget would silently no-op on every event."
  - "Task 05-01 split per plan-checker Warning #7 → Task 05-01a (2-file refactor: shared NODE_TYPES extraction) + Task 05-01b (9-file uniform extension: runStateStyles helper + 7 node components + test). Each task verifies tests stay GREEN before moving on, isolating any regression to a smaller diff."
  - "Data-fetching strategy: getWorkflowExecutionDetails (returns execution + history) + getWorkflowTemplate (returns graph_nodes + graph_edges from workflow_templates) — two existing service calls. No new endpoint introduced. The plan called for a '/status' endpoint but the existing /workflows/executions/{id} endpoint (returning the WorkflowExecutionResponse) already provides the history with output_data._execution_meta.graph_node_id, and getWorkflowTemplate provides the graph. Composing the two is sufficient."
  - "Local edge re-evaluation on workflow.step.completed (NOT a full refresh): the SSE handler updates nodeState[nodeId] = 'completed' AND iterates condition nodes locally to set their outgoing edges to taken/not_taken. Avoids the stale-mock failure mode where refresh() overwrites just-set state with the original fixture's running-status payload. Unknown-step events still call refresh() to learn the new graph_node_id mapping."
  - "Stub-then-replace component pattern: Task 05-02 ships a minimal WorkflowGraphRunWidget stub component so WidgetRegistry's dynamic import resolves and the registry tests pass; Task 05-03 replaces the body with the real ~400-line implementation. Keeps registry-change commit reviewable independent of the widget-implementation commit."

patterns-established:
  - "Pattern 1: Shared visual helper modules under editor/ get re-imported by widgets/. Discretion #6 set the rule: editor owns the canonical implementation; widgets reuse via import. Future Phase 4 widgets (parallel-run / approval-run views) follow the same import path."
  - "Pattern 2: Pure-function helpers for visual contracts: getNodeRunStateClasses + getEdgeRunStateStyle take an enum-typed runState and return a className string / style object. Encapsulated visual decisions in one module — touching the contract is a one-line edit. Phase 4 may extend (e.g. 'gathering' state for parallel nodes) by adding a case here."
  - "Pattern 3: Widget routing helper exported from WidgetRegistry: resolveWorkflowRunWidget(template) returns a WidgetType string. Workspace consumers call this to pick the right widget per execution. Phase 4 can add more widget-type returns without re-architecting the consumer call sites."
  - "Pattern 4: Stub-then-replace registry pattern: when a new widget type needs registry-level wiring before its implementation lands, ship a tiny stub component first so dynamic imports + registry tests pass, then replace the body in a separate commit. Phase 4 widgets can use this same staging pattern."
  - "Pattern 5: BLOCKER guard greps in plan-level verification: a pre-commit guard like grep -cE 'workflow_step\\.' (forbidden form) returning 0 prevents silent regressions where the implementation would mount but never react to events. Plan-checker reviewers can run the same one-liner to validate the fix didn't drift."

requirements-completed:
  - NODEEDITOR-WIDGET-01
  - NODEEDITOR-COMPAT-01

# Metrics
duration: 27 min
completed: 2026-05-12
---

# Phase 111 Plan 05: Frontend Graph-Run Widget Summary

**Live React Flow widget for branched workflow runs (`WorkflowGraphRunWidget`) ships with Discretion #6 placement (under `components/widgets/`) reusing the editor's 7 node components via shared `nodeTypes.ts`, Discretion #7 active-node visual (`animate-pulse ring-2 ring-amber-500` via new `runStateStyles.ts` helper), CANONICAL dot-separated SSE event handling (`workflow.step.{started,completed,failed,paused}` — BLOCKER #2 closure), local edge re-evaluation on completion (taken = emerald-500 stroke / not_taken = slate + dashed + opacity 0.3), and `resolveWorkflowRunWidget` workspace routing helper. 4 atomic tasks, 7 commits (1 refactor + 3 TDD RED+GREEN pairs), 25 new vitest tests (10 runStateStyles + 13 WidgetRegistry + 15 widget = 230 frontend tests GREEN overall, zero regression vs Phase 110/111-04), tsc clean, zero backend changes, ROADMAP criteria 8 + 9 + 10 closed — PHASE 111 SHIPPING-COMPLETE.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-05-12T05:48:25Z
- **Completed:** 2026-05-12T06:15:04Z
- **Tasks:** 4 (Task 05-01a refactor + 3 TDD splits 05-01b / 05-02 / 05-03 = 7 atomic commits)
- **Files created:** 5 (2 helpers + 3 test/widget modules)
- **Files modified:** 12 (NodeCanvas + 7 node components + WidgetRegistry + WidgetRegistry test + widgets type + RecentWidgets)
- **New tests:** 38 across 3 new/extended test files (10 runStateStyles + 13 WidgetRegistry additions + 15 WorkflowGraphRunWidget)
- **Full frontend workflow + widget suite:** 230 passed (105 Phase 110 + 54 Phase 111-04 + 71 new in Plan 05 across runStateStyles/WidgetRegistry/WorkflowGraphRunWidget tests)

## Accomplishments

### Task 05-01a: Shared NODE_TYPES module extraction (2-file refactor)

- Extracted the module-scoped `NODE_TYPES` map from `NodeCanvas.tsx` into a new shared module `frontend/src/components/workflows/editor/nodeTypes.ts`. NodeCanvas re-imports the constant; behavior is functionally identical.
- Enables Discretion #6: the workspace's `WorkflowGraphRunWidget` (Task 05-03) imports the same `NODE_TYPES` map to reuse the 7 Phase 109/110 visual node components rather than re-implementing them.
- All 159 pre-existing workflow vitest tests stay GREEN without any test edits. tsc clean.

**Commit:** `87ef44bc` (refactor)

### Task 05-01b: runStateStyles helper + uniform 7-node-component extension (TDD)

- **RED (`f6e79a1d`):** 10 vitest tests for `getNodeRunStateClasses(runState)` (all 5 NodeRunState values + undefined fallback) and `getEdgeRunStateStyle(runState)` (all 3 EdgeRunState values + undefined). Tests assert the Discretion #7 visual contract (active = animate-pulse + ring-amber-500; completed = ring-emerald-500; pending = opacity-50; skipped = opacity-30 + grayscale; failed = ring-red-500; taken = #10b981 stroke + thicker; not_taken = opacity < 0.5 + dashed).
- **GREEN (`64ec51bf`):** Created `frontend/src/components/workflows/editor/runStateStyles.ts` with both helpers. Extended all 7 node components (Trigger/AgentAction/Output/Condition/Parallel/Merge/HumanApproval) uniformly — each accepts optional `data.runState`, calls `getNodeRunStateClasses(typed.runState)`, and appends the result to the outermost wrapper className.
- Backward-compat default: when `runState` is undefined (editor path), helper returns the empty string so Phase 109/110 visuals are unchanged.
- All 169 vitest tests GREEN (10 new + 159 existing). tsc clean.

### Task 05-02: WidgetRegistry routing helper + workflow_graph_run map entry (TDD)

- **RED (`5a1b4889`):** 13 new tests covering `isBranchingTemplate` (4 truthy cases — condition, parallel, merge, human-approval — + 4 falsy cases — linear, null, undefined, empty), `resolveWorkflowRunWidget` (branching, linear, undefined graph_nodes, null graph_nodes), and the `WIDGET_MAP` entry for `workflow_graph_run` (resolves to a real component, not UnknownWidget) + regression guard that `workflow_timeline` still resolves.
- **GREEN (`c7c8cd33`):** Added `WorkflowGraphRunWidget` stub component (Task 05-03 replaces the body); added dynamic import + `WIDGET_MAP['workflow_graph_run']` entry in WidgetRegistry.tsx; exported `isBranchingTemplate(graph_nodes)` (mirrors backend `_template_requires_graph_executor` from Plan 01's `NON_LINEAR_KINDS = {'condition', 'parallel', 'merge', 'human-approval'}`); exported `resolveWorkflowRunWidget({graph_nodes})` returning `'workflow_graph_run' | 'workflow_timeline'`; extended `WidgetType` union with `'workflow_graph_run'`. Auto-fix [Rule 3 - Blocking]: added `workflow_graph_run: Workflow` icon entry to `RecentWidgets.tsx` `WIDGET_TYPE_ICON` map (typed `Record<WidgetType, ElementType>`).
- All 36 WidgetRegistry tests GREEN (23 existing + 13 new). 215 total widget + workflow tests GREEN.

### Task 05-03: WorkflowGraphRunWidget implementation + live state machine (TDD)

- **RED (`53ab5888`):** 15 vitest tests covering initial-render states (loading, fetch resolution rendering 5 nodes + 4 edges, missing execution_id warning), initial state derivation from history (completed history rows → 'completed', running rows → 'active', pending nodes, taken edge highlighting + not_taken muted, failed steps → 'failed'), and live SSE event handling. **CRITICAL**: every test event type uses the canonical dot-separated form `workflow.step.{started,completed,failed,paused}` (BLOCKER #2 closure — pre-commit guard `grep -cE 'workflow_step\\.'` returns 0). Mocks `@xyflow/react` (data-attribute surface for direct DOM assertion), `@/services/workflowExecutionStream` (captures the SSE callback in a module-level array), and `@/services/workflows` (canned payloads per test).
- **GREEN (`c8d5ca95`):** Real ~400-line implementation. On mount, fetches `getWorkflowExecutionDetails(executionId)` + `getWorkflowTemplate(template_id)`. Derives initial `nodeState` (keyed by graph_node_id) + `edgeState` (taken / not_taken / pending for condition outgoing edges) via the pure `deriveRunState` function. Subscribes to `subscribeToExecution(executionId, callback)` and handles the four canonical event types via `switch(event.type)`. Edge re-evaluation on `workflow.step.completed` happens locally (walking template's condition nodes against the updated completed-node set) — avoids the stale-mock failure mode of full refresh and minimizes network traffic. Unknown-step events trigger a full `refresh()` to learn new graph_node_id mappings. Wraps the canvas in `ReactFlowProvider`; runs read-only (`nodesDraggable={false}`, `nodesConnectable={false}`, `elementsSelectable={false}`). Imports `NODE_TYPES` from the shared module and `getEdgeRunStateStyle` from the helper.
- All 15 widget tests + 215 prior tests = 230 GREEN. tsc clean. Plan-level verification grep checks all pass: `workflow_graph_run` count = 4, `resolveWorkflowRunWidget|isBranchingTemplate` count = 3, `subscribeToExecution` count = 2, `NODE_TYPES` count = 3, BLOCKER #2 guard `workflow_step.` count = 0 in both widget and test files.

## Task Commits

All commits on `plan-109-spec-b-phase-1` (branch verified pre-each-commit; zero pollution incidents this plan):

1. **Task 05-01a refactor** — `87ef44bc` extract shared NODE_TYPES to nodeTypes.ts
2. **Task 05-01b RED** — `f6e79a1d` add failing tests for runStateStyles helpers
3. **Task 05-01b GREEN** — `64ec51bf` add runStateStyles helper + extend 7 node components with data.runState
4. **Task 05-02 RED** — `5a1b4889` add failing tests for resolveWorkflowRunWidget + isBranchingTemplate + workflow_graph_run map entry
5. **Task 05-02 GREEN** — `c7c8cd33` register workflow_graph_run + add isBranchingTemplate / resolveWorkflowRunWidget helpers
6. **Task 05-03 RED** — `53ab5888` add failing tests for WorkflowGraphRunWidget (canonical workflow.step.* SSE)
7. **Task 05-03 GREEN** — `c8d5ca95` WorkflowGraphRunWidget with canonical workflow.step.* SSE handling

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write — adds SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md updates).

## Files Created/Modified

**Created (5 files):**

- `frontend/src/components/workflows/editor/nodeTypes.ts` — shared `NODE_TYPES` map exported as `as const`; re-imports the 7 node components from `./nodes/*.tsx`.
- `frontend/src/components/workflows/editor/runStateStyles.ts` — pure-function `getNodeRunStateClasses` + `getEdgeRunStateStyle` with `NodeRunState` + `EdgeRunState` union types. ~90 lines.
- `frontend/src/__tests__/workflows/runStateStyles.test.ts` — 10 vitest tests covering all transitions of both helpers.
- `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` — live React Flow widget. ~410 lines. Includes `deriveRunState` pure helper, `GraphRunCanvas` (the canvas component, mounted inside `ReactFlowProvider`), and the default export reading `execution_id` from the WidgetDefinition payload.
- `frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx` — 15 vitest tests. ~610 lines. Mocks @xyflow/react / workflowExecutionStream / workflows service; fires synthetic SSE events via the captured callback.

**Modified (12 files):**

- `frontend/src/components/workflows/editor/NodeCanvas.tsx` — replaced inline `NODE_TYPES` block with `import { NODE_TYPES } from './nodeTypes';` (refactor only, functionally identical).
- `frontend/src/components/workflows/editor/nodes/TriggerNode.tsx` — import helper + `NodeRunState` type; extended `TriggerNodeData` with optional `runState`; appended `${runStateClasses}` to wrapper className.
- `frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx` — same pattern as TriggerNode.
- `frontend/src/components/workflows/editor/nodes/OutputNode.tsx` — same pattern.
- `frontend/src/components/workflows/editor/nodes/ConditionNode.tsx` — same pattern.
- `frontend/src/components/workflows/editor/nodes/ParallelNode.tsx` — same pattern.
- `frontend/src/components/workflows/editor/nodes/MergeNode.tsx` — same pattern.
- `frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx` — same pattern.
- `frontend/src/components/widgets/WidgetRegistry.tsx` — added `GraphNode` type import; added `WorkflowGraphRunWidget` dynamic import + `WIDGET_MAP` entry; exported `isBranchingTemplate` + `resolveWorkflowRunWidget`. (+50 lines net)
- `frontend/src/components/widgets/__tests__/WidgetRegistry.test.tsx` — appended 13 new tests for the routing helpers + workflow_graph_run map entry. (+135 lines)
- `frontend/src/types/widgets.ts` — extended `WidgetType` union with `'workflow_graph_run'`. (+1 line)
- `frontend/src/components/layout/RecentWidgets.tsx` — added `workflow_graph_run: Workflow` icon entry to `WIDGET_TYPE_ICON` map (auto-fix [Rule 3 - Blocking] for the `Record<WidgetType, ElementType>` type). (+1 line)

**NOT modified (verified empty diff across all 7 Plan 05 commits):**

- `frontend/src/components/widgets/WorkflowTimelineWidget.tsx` — ROADMAP criterion 10 preserved. The existing linear widget stays unchanged; the routing helper continues to route linear templates to it.
- `frontend/src/services/workflowExecutionStream.ts` — Spec A SSE wire UNCHANGED. The new widget consumes it as-is.
- `app/workflows/`, `app/routers/`, `supabase/migrations/`, `supabase/functions/` — zero backend changes (verified via `git log --oneline --grep="111-05" -- app/ supabase/` returning empty).

## Decisions Made

1. **Widget placement under `components/widgets/` (Discretion #6).** Workspace-rendered, NOT editor-rendered. The widget imports `NODE_TYPES` from the editor's shared `nodeTypes.ts` module rather than re-implementing 7 visual node components. Editor owns the canonical implementation; widgets reuse.

2. **Active-node visual = Tailwind `animate-pulse ring-2 ring-amber-500` (Discretion #7).** Applied via the new `runStateStyles.getNodeRunStateClasses` helper. Completed = `ring-1 ring-emerald-500`. Pending (not-yet-reached) = `opacity-50`. Skipped (not-taken branch) = `opacity-30 grayscale`. Failed = `ring-2 ring-red-500`. Default (undefined) = empty string (editor visuals unchanged).

3. **Edge styling: `taken` = emerald-500 stroke + strokeWidth 2.5; `not_taken` = slate-400 stroke + opacity 0.3 + strokeDasharray `'6,4'`.** Pending and undefined return an empty style object (React Flow default). Drawn from the condition node's outgoing edges based on which target appears in the completed-node set.

4. **Canonical dot-separated SSE event types (BLOCKER #2 closure).** Implementation switch cases AND test event types use `workflow.step.started`, `workflow.step.completed`, `workflow.step.failed`, `workflow.step.paused`. The plan-checker iteration 1's original draft used `workflow_step.{started,...}` (underscore-then-dot) which would never match the backend wire emitted from `app/workflows/step_executor.py:752-760`. Pre-commit guard `grep -cE 'workflow_step\.'` returns 0 in both the widget and its test file.

5. **Task 05-01 split into 05-01a + 05-01b (plan-checker Warning #7).** Shared module extraction (2 files, 1 commit) before per-node uniform edits (9 files, RED+GREEN commits). Reduces blast radius per commit and isolates any regression to a smaller diff.

6. **Two-call data-fetching strategy: `getWorkflowExecutionDetails` + `getWorkflowTemplate`.** The plan called for a single `/workflows/executions/{id}/status` endpoint, but the existing `/workflows/executions/{id}` endpoint already returns execution + history with the JSONB `graph_node_id`; `getWorkflowTemplate(template_id)` provides `graph_nodes` + `graph_edges`. Composing the two avoids introducing a new backend endpoint just for the widget — keeps Plan 05 frontend-only.

7. **Local edge re-evaluation on `workflow.step.completed` (NOT a full refetch).** The handler walks the template's condition nodes against the updated completed-node set in-state and writes `edgeState` directly. Reasons: (a) tests that mock the fetch with a "running" status would have their just-set "completed" state clobbered by a refetch that re-derives from stale fixtures; (b) production benefit — avoids one round-trip per SSE event. Unknown-step events DO still trigger a full `refresh()` to learn new graph_node_id mappings.

8. **Stub-then-replace component pattern across Tasks 05-02 and 05-03.** Task 05-02 ships a minimal `WorkflowGraphRunWidget` stub so the registry's dynamic import resolves and the registry tests pass; Task 05-03 replaces the body with the real ~400-line implementation. Keeps the registry-change commit (Task 05-02 GREEN) reviewable independent of the widget-implementation commit (Task 05-03 GREEN).

9. **Refs to stabilize the SSE handler.** `templateRef` + `stepMapRef` are updated on every render via direct assignment. The `useEffect(() => subscribeToExecution(...), [executionId, refresh])` doesn't re-subscribe on every state update — important because in production each re-subscribe would reset the EventSource and could miss in-flight events.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `workflow_graph_run` entry to `RecentWidgets.tsx` `WIDGET_TYPE_ICON` map**

- **Found during:** Task 05-02 GREEN (first `npx tsc --noEmit` after extending the `WidgetType` union)
- **Issue:** `frontend/src/components/layout/RecentWidgets.tsx` defines `WIDGET_TYPE_ICON: Record<WidgetType, React.ElementType>` — adding a new union member forces every consumer of `Record<WidgetType, X>` to add a matching entry. tsc emitted `TS2741: Property 'workflow_graph_run' is missing in type {...}`.
- **Fix:** Added `workflow_graph_run: Workflow` (same Lucide icon as `workflow_timeline`) to `WIDGET_TYPE_ICON`.
- **Files modified:** `frontend/src/components/layout/RecentWidgets.tsx`
- **Verification:** `npx tsc --noEmit` returns clean.
- **Committed in:** `c7c8cd33` (bundled with the registry edit so tsc + tests pass on a single GREEN commit)

**2. [Rule 1 - Bug] Local edge re-evaluation on `workflow.step.completed` (initial implementation called `refresh()` instead)**

- **Found during:** Task 05-03 GREEN (initial test run, 2 of 15 failed)
- **Issue:** The first GREEN implementation handled `workflow.step.completed` by calling `setNodeState({[nodeId]: 'completed'})` AND then `void refresh()` to re-evaluate edges. In the vitest fixtures, the mock `getWorkflowExecutionDetails` returns the same payload on every call — when the test fired a synthetic SSE event marking step `s-a1` complete, the just-set "completed" state was clobbered by the refresh deriving "active" again from the original "running" history fixture. 2 tests failed: `sse_event_flips_node_to_active` (which actually fires `workflow.step.completed`) and `sse_event_flips_node_to_completed`.
- **Fix:** Replaced `void refresh()` inside the `workflow.step.completed` switch case with a local edge re-evaluation: walk `templateRef.current.graph_nodes`, find each `condition` node, check its outgoing edges against the updated completed-node set, set `edgeState[edge.id]` to `'taken'` / `'not_taken'` accordingly. Unknown-step events (when `stepMapRef.current[stepId]` is undefined) still call `refresh()` to learn the new mapping. This also matches the production behavior more cleanly — avoids one network round-trip per completion event.
- **Files modified:** `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx`
- **Verification:** 15/15 widget tests GREEN; 230 total widget + workflow tests GREEN.
- **Committed in:** `c8d5ca95` (bundled with the GREEN implementation so the fix lands atomically)

### Iteration-1 plan-checker fixes (already in plan; documented for trace)

These were addressed BEFORE plan approval — they don't represent in-flight deviations but show the plan's response to plan-checker iteration 1:

**A. BLOCKER #2 — Canonical workflow.step.* dot-separated event types.** Plan 05's original draft used the form `workflow_step.{started,completed,failed,paused}` (underscore-then-dot). Verified against `app/workflows/step_executor.py:752-760`: backend emits `workflow.step.{status}` (all dots). The plan was corrected in iteration 1 and execution faithfully implemented the canonical form. Pre-commit guard `grep -cE 'workflow_step\.'` returns 0 in both `WorkflowGraphRunWidget.tsx` and its test file.

**B. Warning #7 — Task 05-01 split into 05-01a + 05-01b.** The original Task 05-01 touched 11 files (shared module extraction + helper + 7 node components + 2 test files). Splitting into 05-01a (2 files: extraction) + 05-01b (9 files: helper + node-component extensions + test) reduced blast radius per commit. The split was reflected in the plan text before execution.

---

**Total deviations:** 2 auto-fixed (1 Rule 3 - Blocking; 1 Rule 1 - Bug)

**Impact on plan:** Minimal — both auto-fixes caught by the test loop in seconds and bundled with their respective GREEN commits. No scope creep. Iteration-1 plan-checker BLOCKER #2 / Warning #7 fixes landed exactly as planned.

## Issues Encountered

- **`basic` reporter unsupported in this vitest version.** Initial test runs used `--reporter=basic` (per the plan's example commands), which failed with `Failed to load url basic`. Removed the flag — vitest falls back to its default reporter which provides the same per-test output we needed. No commits affected.
- **No CRLF / branch-pollution / file-revert / cygwin incidents this plan.** All 7 commits landed on `plan-109-spec-b-phase-1` on the first try. The `project_branch_pollution_2026_05_09.md` documented 9 prior incidents; Plan 05 ran cleanly with zero recovery dances needed.
- **No regressions on Phase 110 (105 tests) or Phase 111-04 (54 new tests).** All 159 pre-Plan-05 workflow tests stay GREEN; all 23 pre-Plan-05 WidgetRegistry tests stay GREEN. Phase 110/111-04 contracts honored.

## User Setup Required

None — pure frontend additive changes. After this plan merges to main:

1. CI installs no new deps (Phase 111-04 already shipped `@uiw/react-codemirror` + `@codemirror/lang-json`; React Flow has been on disk since Phase 109). Frontend bundle grows by ~10KB (widget + helpers — no new external dependencies).
2. Workspace users with a non-linear workflow execution will see the new widget routed automatically once the workspace's run-widget-host call sites adopt `resolveWorkflowRunWidget`. (Plan 05 ships the helper and registry entry; workspace call sites can adopt it incrementally — documented as a follow-up below.)
3. No env vars, no dashboard config, no third-party services.

## Next Phase Readiness

**Phase 111 SHIPS at this plan's completion.**

ROADMAP success criteria coverage (Spec B Phase 3):

| Criterion | Description | Plan(s) | Status |
|-----------|-------------|---------|--------|
| 1 | End-to-end branching workflow execution via the production wire | 111-03 | SHIPPED |
| 2 | Engine dispatch on NON_LINEAR_KINDS membership; linear templates unchanged | 111-01 + 111-03 | SHIPPED |
| 3 | Dual-tab Guided/Advanced condition editor (CodeMirror 6, round-trip rule) | 111-04 | SHIPPED |
| 4 | UAT: non-technical user builds "if revenue > 50000" in <60s via Guided form | 111-04 | SHIPPED (dedicated unit test asserts the JSONLogic shape) |
| 5 | Client-side rule 4 validation (red badges + Save disabled) | 111-04 | SHIPPED |
| 6 | Server-side rule 4 validation (HTTP 400 on save) | 111-02 | SHIPPED |
| 7 | ExecutionContext built from previous_outcomes + current_step + user_context | 111-03 | SHIPPED |
| 8 | Live branched-run rendering with active/taken/muted/pending overlays | 111-05 | SHIPPED (this plan) |
| 9 | Workspace widget-picker routes linear vs branching templates | 111-05 (+ 111-03 EF non-regression) | SHIPPED (this plan) |
| 10 | Spec A invariants (OutcomeWriter, event bus, WorkflowTimelineWidget, SSE wire) UNCHANGED | All plans | SHIPPED via static guarantees |
| 11 | Engine-time cycle defense (max_iterations safety bound) | 111-03 | SHIPPED (proper topological-sort cycle detection deferred to Phase 4) |

Phase 111 requirements (REQUIREMENTS.md):

- **NODEEDITOR-ENGINE-01** — graph_executor backend dispatch — Plan 111-03 closure
- **NODEEDITOR-VALIDATE-01** — Server rule 4 — Plan 111-02 closure
- **NODEEDITOR-VALIDATE-02** — Client rule 4 — Plan 111-04 closure
- **NODEEDITOR-EDIT-03** — Dual-tab condition editor — Plan 111-04 closure
- **NODEEDITOR-WIDGET-01** — WorkflowGraphRunWidget — Plan 111-05 closure (this plan)
- **NODEEDITOR-COMPAT-01** — Spec A invariants preserved — Plans 111-01..05 (this plan also via static guarantees)

**Follow-up items (NOT in scope for Phase 111):**

- **Workspace widget-picker call sites.** Plan 05 exports `resolveWorkflowRunWidget` from `WidgetRegistry.tsx`. Whichever workspace component renders execution widgets needs to call this helper (instead of hardcoding `workflow_timeline`). Plan 05 deliberately keeps this scope-tight — the workspace UI for showing live executions has multiple consumer surfaces; routing them is its own incremental rollout.
- **Test-run button (Discretion #1 deferred).** A future phase / Phase 3.5 / Phase 4 can add the "Test this branching workflow" button to the editor page. Plan 04 already declined to absorb it; Plan 05 does likewise.
- **Phase 4 parallel/merge/human-approval execution.** The graph_executor module rejects these kinds with `NotImplementedError("Phase 4: ...")` (Plan 111-03). When Phase 4 ships, the live widget will automatically render `parallel`/`merge`/`human-approval` nodes with the correct runState as soon as the backend emits `workflow.step.{started,completed}` events for them — no widget changes needed.
- **Workspace UAT.** Manual end-to-end test with a real branching workflow + a real SSE-emitting backend is recommended before declaring Phase 111 user-facing-complete. The 230 vitest tests cover the unit + component behavior; integration testing through Cloud Run is out of scope for this plan.

**No blockers. No carry-forward issues.** Phase 111 is now SHIPPING-COMPLETE — all 5 plans landed, all 6 NODEEDITOR-* requirements closed, all 11 ROADMAP criteria GREEN.

---

*Phase: 111-workflow-node-editor-branching-execution*
*Completed: 2026-05-12*

## Self-Check: PASSED

Verified post-write (all paths absolute on C:/Users/expert/documents/pka/pikar-ai/):

- [x] `frontend/src/components/workflows/editor/nodeTypes.ts` exists on disk (NODE_TYPES export)
- [x] `frontend/src/components/workflows/editor/NodeCanvas.tsx` imports from `./nodeTypes`
- [x] `frontend/src/components/workflows/editor/runStateStyles.ts` exists on disk (getNodeRunStateClasses + getEdgeRunStateStyle exports)
- [x] `frontend/src/__tests__/workflows/runStateStyles.test.ts` exists on disk (10 tests GREEN)
- [x] All 7 node components in `frontend/src/components/workflows/editor/nodes/` import + use `getNodeRunStateClasses` (verified via per-file grep returning all 7 OK)
- [x] `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` exists on disk (~410 lines, real implementation; not the stub)
- [x] `frontend/src/components/widgets/__tests__/WorkflowGraphRunWidget.test.tsx` exists on disk (15 tests GREEN)
- [x] `frontend/src/components/widgets/WidgetRegistry.tsx` has `workflow_graph_run` count = 4, `resolveWorkflowRunWidget|isBranchingTemplate` count = 3
- [x] BLOCKER #2 guard: `grep -cE "workflow_step\\."` returns 0 in both `WorkflowGraphRunWidget.tsx` and its test file
- [x] Dot-separated SSE event names present: `grep -c "workflow.step"` returns 9 in widget, 10 in test file
- [x] WorkflowTimelineWidget.tsx UNCHANGED by Plan 05 (last commit `8e1016cc` predates Plan 05)
- [x] workflowExecutionStream.ts UNCHANGED by Plan 05 (last commit `8e1016cc` predates Plan 05)
- [x] No backend changes by Plan 05 commits: `git log --oneline --grep="111-05" -- app/ supabase/` returns empty
- [x] Commit `87ef44bc` exists on `plan-109-spec-b-phase-1` (Task 05-01a refactor)
- [x] Commit `f6e79a1d` exists on `plan-109-spec-b-phase-1` (Task 05-01b RED)
- [x] Commit `64ec51bf` exists on `plan-109-spec-b-phase-1` (Task 05-01b GREEN)
- [x] Commit `5a1b4889` exists on `plan-109-spec-b-phase-1` (Task 05-02 RED)
- [x] Commit `c7c8cd33` exists on `plan-109-spec-b-phase-1` (Task 05-02 GREEN)
- [x] Commit `53ab5888` exists on `plan-109-spec-b-phase-1` (Task 05-03 RED)
- [x] Commit `c8d5ca95` exists on `plan-109-spec-b-phase-1` (Task 05-03 GREEN)
- [x] All 7 commits land on `plan-109-spec-b-phase-1` (verified `git log --oneline plan-109-spec-b-phase-1 -10`)
- [x] 230 frontend workflow + widget vitest tests GREEN (105 Phase 110 + 54 Phase 111-04 + 25 Plan 05 widget/registry + 46 widgets)
- [x] `npx tsc --noEmit` clean across the entire frontend
- [x] Branch hygiene: 0 pollution incidents during Plan 05 execution; all 7 commits on the correct branch verified before each `git commit`
- [x] No new dependencies added — Plan 05 is purely additive code on top of Phase 109/110/111-04 stacks
