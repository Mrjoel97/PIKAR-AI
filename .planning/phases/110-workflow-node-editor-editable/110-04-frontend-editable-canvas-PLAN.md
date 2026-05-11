---
phase: 110-workflow-node-editor-editable
plan: 04
type: execute
wave: 3
depends_on: [110-02, 110-03]
files_modified:
  - frontend/src/components/workflows/editor/nodes/ConditionNode.tsx
  - frontend/src/components/workflows/editor/nodes/ParallelNode.tsx
  - frontend/src/components/workflows/editor/nodes/MergeNode.tsx
  - frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx
  - frontend/src/components/workflows/editor/NodePalette.tsx
  - frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx
  - frontend/src/components/workflows/editor/NodeCanvas.tsx
  - frontend/src/components/workflows/editor/useGraphSchema.ts
  - frontend/src/components/workflows/editor/useGraphValidation.ts
  - frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx
  - frontend/src/services/workflows.ts
  - frontend/src/__tests__/workflows/NodeCanvas.test.tsx
  - frontend/src/__tests__/workflows/NodePalette.test.tsx
  - frontend/src/__tests__/workflows/NodePropertiesDrawer.test.tsx
  - frontend/src/__tests__/workflows/useGraphValidation.test.ts
  - frontend/package.json
  - frontend/package-lock.json
autonomous: true
requirements:
  - NODEEDITOR-EDIT-01
  - NODEEDITOR-EDIT-02
  - NODEEDITOR-VALIDATE-01
gap_closure: false

must_haves:
  truths:
    - "A user can drag any of the 7 node kinds from a left-rail NodePalette onto the React Flow canvas (Phase 110 ships all 7 visual node components even though only 3 execute today — decision 2C from Claude's Discretion)"
    - "A user can connect a source handle of one node to a target handle of another node by dragging an edge between them; the new edge persists in NodeCanvas state"
    - "Clicking a node opens a right-side NodePropertiesDrawer that renders a Zod-driven form for the node's label + per-kind config; edits update NodeCanvas state and dirty-flag the canvas"
    - "Clicking Save opens an optional comment modal (default empty per Claude's Discretion #5) then POSTs to PUT /workflows/templates/{id} with the current graph + If-Match header + comment; success closes modal and reloads from server"
    - "Client-side validation (useGraphValidation hook) runs on every edit and renders red node badges for rule-1/2/3/6/7 failures; Save button is disabled when errors exist; matches server validation exactly (POST /validate returns the same error list)"
    - "Clicking Edit on a seed template (created_by IS NULL) triggers PUT which the backend returns 409 with copied_template_id; the editor router.push()es to /dashboard/workflows/editor/{copied_template_id} and surfaces a sonner toast 'Created your private copy of \"<seed name>\"'"
    - "Adding a Phase-3/4-only node kind (condition/parallel/merge/human-approval) saves without error; properties drawer shows a placeholder body ('Coming in Phase 3/4 — node saves but won't execute yet') and an empty config object"
  artifacts:
    - path: "frontend/src/components/workflows/editor/NodeCanvas.tsx"
      provides: "Now editable: onNodesChange/onEdgesChange/onConnect wired; drag-from-palette drop handler; selection-driven properties drawer integration; dirty tracking; saveTemplate call from Save button; conflict modal show on 412"
      contains: "onConnect"
    - path: "frontend/src/components/workflows/editor/NodePalette.tsx"
      provides: "Left rail palette with 7 draggable node kinds; categorized as Trigger / Actions / Logic / Output (per Claude's Discretion #1)"
      contains: "onDragStart"
    - path: "frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx"
      provides: "Right rail drawer; per-kind Zod-validated form for label + config; uses native HTML forms (no react-hook-form dependency)"
      contains: "onChange"
    - path: "frontend/src/components/workflows/editor/useGraphSchema.ts"
      provides: "Zod schemas per node kind (mirrors app/workflows/graph_validation.py per-kind config schemas); zodSafeParse helper"
      contains: "z.object"
    - path: "frontend/src/components/workflows/editor/useGraphValidation.ts"
      provides: "Client-side validator (rules 1/2/3/6/7) matching server validate_workflow_graph; returns ValidationError[] keyed by node_id"
      contains: "validateGraph"
    - path: "frontend/src/services/workflows.ts"
      provides: "saveTemplate(id, graph, etag, comment?) + validateTemplate(id, graph) service methods; 409/412 surfaced as typed errors"
      contains: "saveTemplate"
    - path: "frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx"
      provides: "Editor page swaps from read-only viewer to editable editor; mounts NodeCanvas + NodePalette + NodePropertiesDrawer; routes copied_template_id redirects"
      contains: "NodePalette"
  key_links:
    - from: "Save button onClick"
      to: "saveTemplate() in services/workflows.ts"
      via: "fetch PUT /workflows/templates/{id} with If-Match header and JSON body"
      pattern: "saveTemplate"
    - from: "saveTemplate 409 response"
      to: "router.push('/dashboard/workflows/editor/{copied_template_id}')"
      via: "Typed CopyForkError thrown by saveTemplate; caught in page.tsx + toast.success"
      pattern: "copied_template_id"
    - from: "useGraphValidation"
      to: "Node badge rendering in custom node components"
      via: "validationErrors prop passed via React Flow node data field"
      pattern: "validationErrors"
    - from: "Drag from NodePalette"
      to: "onDrop handler in NodeCanvas adds new GraphNode to React Flow state"
      via: "HTML5 drag/drop API with dataTransfer.setData('application/reactflow', nodeKind)"
      pattern: "application/reactflow"
---

<objective>
Convert the read-only graph viewer shipped in Phase 109-03 into a fully editable canvas. Drag-drop palette, connect handles, click-to-edit properties drawer, client-side validation matching server, Save flow with If-Match concurrency check, seed-template-copy redirect on 409. Ships all 7 visual node components (Phase 110 only enforces tight schemas for trigger/agent-action/output; condition/parallel/merge/human-approval get placeholder Zod schemas + a "Coming in Phase 3/4" drawer body — decision Option C from Claude's Discretion).

Purpose: Implements roadmap success criteria 1, 7, and 10 — user-facing editing surface. Plan 05 adds the version history and conflict-resolution UI on top of this.
Output: 4 new node components + 2 new editor UI components (palette, drawer) + 2 new hooks + page.tsx rewrite + service.ts extensions + 4 new test files. ~1500 lines added.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/110-workflow-node-editor-editable/110-CONTEXT.md
@.planning/phases/110-workflow-node-editor-editable/110-02-SUMMARY.md
@.planning/phases/110-workflow-node-editor-editable/110-03-SUMMARY.md
@.planning/phases/109-workflow-node-editor-viewer/109-03-SUMMARY.md
@frontend/src/components/workflows/editor/NodeCanvas.tsx
@frontend/src/components/workflows/editor/nodes/TriggerNode.tsx
@frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx
@frontend/src/components/workflows/editor/nodes/OutputNode.tsx
@frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx
@frontend/src/services/workflows.ts

<interfaces>
<!-- Already on disk from Phase 109-03: -->
// frontend/src/components/workflows/editor/NodeCanvas.tsx
//   Props: { template: WorkflowTemplate }
//   Module-scope NODE_TYPES = { trigger, 'agent-action', output, ... } (with 3 components today)
//   useMemo over template -> { nodes, edges, isEmpty }
//   Renders <ReactFlow nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} fitView>
//
// frontend/src/components/workflows/editor/nodes/{Trigger,AgentAction,Output}Node.tsx
//   Custom React Flow node components — NodeProps contract from @xyflow/react v12
//
// frontend/src/services/workflows.ts
//   export type WorkflowTemplate = components['schemas']['WorkflowTemplateResponse'];
//   export interface { NodePosition, GraphNode, GraphEdge, NodeKind, ValidationError, ValidateGraphResponse } (Plans 03 + 110-02 add types)
//   export async function getWorkflowTemplate(templateId: string): Promise<any>   // returns any — cast at call site
//
// frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx
//   Phase 109-03 currently mounts read-only NodeCanvas inside GatedPage + DashboardErrorBoundary + PremiumShell
//   Route param name is [templateId], NOT [id]

<!-- Plan 02 ships (will be on disk by the time this plan runs): -->
// app/routers/workflows.py:
//   PUT /workflows/templates/{id}                   -> requires If-Match; 412/428/409/200
//   GET /workflows/templates/{id}                   -> sets ETag header
//   GET /workflows/templates/{id}/history           -> list[HistoryItem]
//   POST /workflows/templates/{id}/revert/{vid}     -> returns new version
//
// frontend/src/services/workflows.ts:
//   export type WorkflowTemplateVersion = components['schemas']['WorkflowTemplateVersion'];
//   (current_version_id present on WorkflowTemplateResponse)

<!-- Plan 03 ships: -->
// app/routers/workflows.py:
//   POST /workflows/templates/{id}/validate         -> 200 with {errors: ValidationErrorItem[]}
//
// frontend/src/services/workflows.ts:
//   export type ValidationError = components['schemas']['ValidationErrorItem'];
//   export type ValidateGraphResponse = components['schemas']['ValidateGraphResponse'];
</interfaces>

<context_notes>
- This plan DEPENDS on Plans 02 + 03 backend endpoints being live. Wave 3 — runs after Wave 2 fully completes. If Plan 03 has not landed at Plan 04 execution time, fall back to client-side validation only (server validation can still ship later — the editor just runs without server-confirm).
- New frontend dependencies — DO add: `zod` (^3.23+) for runtime config validation per node kind. Verify: `grep "zod" frontend/package.json` returns 0 — confirms it's new. Add via `cd frontend && npm install zod`.
- Optional consideration: `@hookform/resolvers` + `react-hook-form` — DO NOT ADD. No existing forms use them in this codebase (verified via grep). Use raw `<input>` + `useState` + onBlur validation via Zod schemas. Simpler, fewer deps, matches existing codebase patterns. Plan 04 deviates from CONTEXT.md's optional consideration explicitly here.
- State management: existing codebase has no zustand, no React Query (verified via grep). Use React `useState` + `useCallback` + `useMemo` inside the editor page component. Plan 04 takes Claude's Discretion #7 = "local component state in the page component, lifted as props".
- Phase 109-03 made NodeCanvas READ-ONLY (`nodesDraggable={false} nodesConnectable={false}`). Plan 04 must flip those to `true` for the editor route. The viewer-mode use case from 109 will be preserved via an `editable?: boolean` prop on NodeCanvas (default `false` for backward-compat; the editor page passes `editable={true}`).
- Phase 109-03 added 3 custom node components (Trigger, AgentAction, Output). Plan 04 adds the missing 4 (Condition, Parallel, Merge, HumanApproval) with placeholder visuals + always-show-both-handles. Mirror the styling of the existing 3 (circular for trigger/output, rounded-rect card for actions).
- Save UX: explicit Save button (per Claude's Discretion #3). Disabled when canvas is not dirty OR when validation errors exist. Comment modal on Save (per Discretion #5) defaults empty, user can skip.
- Conflict modal on 412 is Plan 05's responsibility — Plan 04 catches the 412 from `saveTemplate` and just shows a sonner toast for now ("Conflict — refresh and try again. (Conflict modal coming in next plan)"). Plan 05 replaces the toast with the real three-button modal.
- Seed-copy redirect: caught client-side as a typed `CopyForkError` thrown by `saveTemplate()` when the PUT response is 409 with `copied_template_id`. The editor page catches it, surfaces sonner toast `"Created your private copy of \"${seedName}\""`, then `router.push('/dashboard/workflows/editor/' + copied_template_id)`. The user loses no work — the v1 of the copy starts with the same graph they were editing.
- Drag/drop from palette: HTML5 dataTransfer pattern. NodePalette's draggable nodes call `event.dataTransfer.setData('application/reactflow', JSON.stringify({kind, label}))`. NodeCanvas's onDrop reads this, computes the drop position via React Flow's `project()` helper, generates a UUID via crypto.randomUUID(), appends to the nodes state. Use `event.preventDefault()` in onDragOver to enable drop.
- React Flow v12 hooks: `useReactFlow()` provides `screenToFlowPosition()` (the v12 rename of `project()`). Use it inside the onDrop handler.
- Branch hygiene: check current branch before every commit. The Phase 110 branch should be `plan-110-spec-b-phase-2` or similar.
- Pre-existing frontend test failures (54 from Phase 109-03 deferred-items.md): Plan 04's new tests must NOT touch the failing test files. Only add new tests in new files.
- Vitest mock for @xyflow/react: 109-03's `NodeCanvas.test.tsx` already has a minimal mock. Plan 04 expands it to support drag/drop simulation — likely just adding `useReactFlow` to the mock returning `{screenToFlowPosition: vi.fn().mockReturnValue({x:0,y:0})}`.
</context_notes>
</context>

<tasks>

<task type="auto">
  <name>Task 04-01: Add zod dependency + four new node components (visual-only, Phase 3/4 kinds)</name>
  <files>frontend/package.json, frontend/package-lock.json, frontend/src/components/workflows/editor/nodes/ConditionNode.tsx, frontend/src/components/workflows/editor/nodes/ParallelNode.tsx, frontend/src/components/workflows/editor/nodes/MergeNode.tsx, frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx</files>
  <action>
1. Install zod: `cd frontend && npm install zod` (the latest in the ^3 range; will be ^3.23.x or higher).

2. Create four new node components matching the style + contract of the existing 3 in `nodes/`:

   - `ConditionNode.tsx` — diamond-ish shape (use `rotate-45` square trick or polygon SVG). Yellow/amber palette. ONE target handle (left); TWO source handles (right-top labeled "true", right-bottom labeled "false"). Body shows label + "Condition" subtitle. Phase 3 will tighten; Phase 110 just renders.
   - `ParallelNode.tsx` — wide rounded-rect with a "fork" icon (lucide-react `GitFork`). Blue palette. ONE target handle (left); N source handles (right, but Phase 110 visual = 2 default handles labeled "branch-1" "branch-2"). Body: label + "Parallel fork".
   - `MergeNode.tsx` — wide rounded-rect with a "merge" icon (lucide-react `GitMerge`). Blue palette. N target handles (left, Phase 110 visual = 2); ONE source handle (right). Body: label + "Merge branches".
   - `HumanApprovalNode.tsx` — rounded-rect with `UserCheck` icon. Purple palette. ONE target (left); ONE source (right). Body: label + "Human approval".

3. All four use the same `NodeProps` contract as the existing 3 components. Each accepts `data: { label: string; validationErrors?: ValidationError[] }`. When `validationErrors` is non-empty, show a red dot badge in the top-right corner with the count + tooltip listing the rules violated.

4. Add an `editable` prop check — in editable mode, nodes show a small "drag to delete" affordance on hover (Phase 110 = drag the node off-canvas; React Flow handles this via the standard delete shortcut or via a custom dropzone in Plan 04's drawer). Keep it simple: just style differences in editable mode (border accent), no special delete affordance — React Flow's built-in `nodesDraggable` + Delete key handle it.

5. No tests for these visual components individually — coverage comes via Plan 04's NodeCanvas tests + NodePalette tests + manual UAT. Add `data-testid="node-{kind}"` to each so tests can assert presence.
  </action>
  <verify>
    <automated>cd frontend && ls src/components/workflows/editor/nodes/ | sort | tr '\n' ' '; echo; grep -l "data-testid=\"node-" src/components/workflows/editor/nodes/*.tsx | wc -l</automated>
  </verify>
  <done>Four new files exist; each has a data-testid attribute; zod is in package.json; package-lock.json updated.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-02: useGraphSchema (per-kind Zod schemas) + useGraphValidation (client validator mirroring server)</name>
  <files>frontend/src/components/workflows/editor/useGraphSchema.ts, frontend/src/components/workflows/editor/useGraphValidation.ts, frontend/src/__tests__/workflows/useGraphValidation.test.ts</files>
  <behavior>
    Tests must mirror the Phase 110 server-side test cases (target 15-20 tests):
    - Rule 1: no trigger / multiple triggers / trigger with incoming edge
    - Rule 2: unreachable node from trigger
    - Rule 3: 2-cycle, 3-cycle, DAG (no cycle)
    - Rule 6: no output / one output / multiple outputs
    - Rule 7: agent-action missing tool_name, agent-action with extras, condition with empty config (placeholder permissive)
    - Happy path: trigger → agent-action → output returns []
    - Empty graph: returns rule-1 error
    - Output type: ValidationError[] with shape {node_id?: string, rule: number, message: string}
    - Result list is identical (in count + content) to what server returns for the same input (use a fixture file shared between Plan 03's server tests and this plan's client tests if practical; otherwise just hand-mirror cases)
  </behavior>
  <action>
1. Create `frontend/src/components/workflows/editor/useGraphSchema.ts`:

```typescript
import { z } from 'zod';
import type { NodeKind } from '@/services/workflows';

// Tight schemas for kinds that execute in Phase 110:
export const TriggerConfigSchema = z.object({
  trigger_type: z.enum(['manual','schedule','event']).optional(),
}).passthrough();

export const AgentActionConfigSchema = z.object({
  tool_name: z.string().min(1, 'Tool name is required'),
  arguments: z.record(z.string(), z.unknown()).default({}),
  agent_role: z.string().optional(),
}).passthrough();

export const OutputConfigSchema = z.object({
  output_format: z.string().optional(),
}).passthrough();

// Placeholder permissive schemas — Phase 3/4 will tighten:
const PermissiveConfigSchema = z.object({}).passthrough();

export const CONFIG_SCHEMAS: Record<NodeKind, z.ZodTypeAny> = {
  'trigger':         TriggerConfigSchema,
  'agent-action':    AgentActionConfigSchema,
  'output':          OutputConfigSchema,
  'condition':       PermissiveConfigSchema,
  'parallel':        PermissiveConfigSchema,
  'merge':           PermissiveConfigSchema,
  'human-approval':  PermissiveConfigSchema,
};

export function validateNodeConfig(kind: NodeKind, config: unknown): z.SafeParseReturnType<unknown, unknown> {
  return CONFIG_SCHEMAS[kind].safeParse(config ?? {});
}
```

2. Create `frontend/src/components/workflows/editor/useGraphValidation.ts`:

```typescript
import type { GraphNode, GraphEdge, ValidationError } from '@/services/workflows';
import { validateNodeConfig } from './useGraphSchema';

export function validateGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
): ValidationError[] {
  // Hand-mirror app/workflows/graph_validation.py logic exactly.
  // Rule 1: single trigger with no incoming edges
  // Rule 2: BFS reachability from trigger
  // Rule 3: Kahn's algorithm topological sort
  // Rule 6: at least one output
  // Rule 7: per-kind config validation via validateNodeConfig
  // ...implementation...
}
```

Implementation: copy the algorithm from `app/workflows/graph_validation.py` (Plan 03 Task 03-01) and translate to TypeScript. The two MUST produce the same result for the same input. Note: server returns `{node_id, rule, message}`; client mirror returns the same shape (mapped to the `ValidationError` TS type Plan 03 exports).

3. Tests at `frontend/src/__tests__/workflows/useGraphValidation.test.ts` (vitest, no jsdom needed — pure function). >=15 tests covering every rule + happy path + edge cases. Use the same case fixtures from Plan 03's `test_graph_validation.py` if useful.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/useGraphValidation.test.ts 2>&1 | tail -15</automated>
  </verify>
  <done>Two new hook files exist; >=15 useGraphValidation tests pass; ruff equivalent (eslint) clean if applicable.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-03: NodePalette + NodePropertiesDrawer components</name>
  <files>frontend/src/components/workflows/editor/NodePalette.tsx, frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx, frontend/src/__tests__/workflows/NodePalette.test.tsx, frontend/src/__tests__/workflows/NodePropertiesDrawer.test.tsx</files>
  <behavior>
    NodePalette tests must assert (target 4-6 tests):
    - Renders 7 draggable items, one per node kind
    - Categorized into Trigger / Actions / Logic / Output sections (per Claude's Discretion #1)
    - Each draggable has draggable={true} attribute
    - dragstart event calls dataTransfer.setData with the right kind
    - Phase-3/4 kinds (condition/parallel/merge/human-approval) have a "Coming soon" badge but are still draggable (per decision Option C from Claude's Discretion)

    NodePropertiesDrawer tests must assert (target 6-10 tests):
    - When no node selected, drawer shows empty state "Select a node to edit"
    - When trigger node selected, shows label input + trigger_type dropdown
    - When agent-action node selected, shows label input + tool_name input + arguments JSON textarea
    - When condition/parallel/merge/human-approval selected, shows label input + placeholder body "Coming in Phase 3/4 — node saves but won't execute yet"
    - onChange of label or config calls onUpdate prop with the new node data
    - Submit invalid config (e.g. agent-action without tool_name) shows inline error message + prevents update
  </behavior>
  <action>
1. Create `frontend/src/components/workflows/editor/NodePalette.tsx`:

```typescript
'use client';
import type { NodeKind } from '@/services/workflows';
import { Play, Wand2, GitBranch, GitFork, GitMerge, UserCheck, CheckCircle2 } from 'lucide-react';

const PALETTE = [
  { category: 'Trigger', items: [{ kind: 'trigger' as NodeKind, label: 'Trigger', icon: Play, comingSoon: false }] },
  { category: 'Actions', items: [{ kind: 'agent-action' as NodeKind, label: 'Agent action', icon: Wand2, comingSoon: false }] },
  { category: 'Logic', items: [
    { kind: 'condition' as NodeKind, label: 'Condition', icon: GitBranch, comingSoon: true },
    { kind: 'parallel' as NodeKind,  label: 'Parallel',  icon: GitFork,   comingSoon: true },
    { kind: 'merge' as NodeKind,     label: 'Merge',     icon: GitMerge,  comingSoon: true },
    { kind: 'human-approval' as NodeKind, label: 'Human approval', icon: UserCheck, comingSoon: true },
  ]},
  { category: 'Output', items: [{ kind: 'output' as NodeKind, label: 'Output', icon: CheckCircle2, comingSoon: false }] },
];

export function NodePalette() {
  const onDragStart = (event: React.DragEvent, kind: NodeKind, label: string) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ kind, label }));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="w-56 border-r border-zinc-200 dark:border-zinc-800 p-3 space-y-4 overflow-y-auto" data-testid="node-palette">
      {PALETTE.map(group => (
        <section key={group.category}>
          <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-1">{group.category}</h3>
          <ul className="space-y-1">
            {group.items.map(item => (
              <li
                key={item.kind}
                draggable
                onDragStart={(e) => onDragStart(e, item.kind, item.label)}
                className="..."
                data-testid={`palette-item-${item.kind}`}
              >
                <item.icon size={14} />
                <span>{item.label}</span>
                {item.comingSoon && <span className="text-[10px] bg-amber-100 px-1 rounded">Phase 3+</span>}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </aside>
  );
}
```

2. Create `frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx`:

```typescript
'use client';
import type { GraphNode } from '@/services/workflows';
import { validateNodeConfig } from './useGraphSchema';

type Props = {
  node: GraphNode | null;
  onUpdate: (id: string, updates: Partial<GraphNode>) => void;
  onClose: () => void;
};

export function NodePropertiesDrawer({ node, onUpdate, onClose }: Props) {
  if (!node) {
    return (
      <aside className="w-80 border-l border-zinc-200 p-4" data-testid="properties-drawer">
        <p className="text-sm text-zinc-500">Select a node to edit its properties.</p>
      </aside>
    );
  }
  // ...per-kind form fields, label input, config-specific fields, validation surface
}
```

Render per-kind forms inline (switch on `node.kind`). For trigger/agent-action/output: real fields. For condition/parallel/merge/human-approval: placeholder text "Coming in Phase 3/4 — node saves but won't execute yet" + a single readonly label input.

Use sonner toast for save errors. Validate config on every change via `validateNodeConfig(node.kind, newConfig)`; show inline error if `.success === false`.

3. Tests at `frontend/src/__tests__/workflows/NodePalette.test.tsx` and `frontend/src/__tests__/workflows/NodePropertiesDrawer.test.tsx`. Use @testing-library/react + vitest. Mock dataTransfer.setData for drag tests.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/NodePalette.test.tsx src/__tests__/workflows/NodePropertiesDrawer.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <done>Both components exist; combined >=10 tests pass; ESLint/tsc clean.</done>
</task>

<task type="auto">
  <name>Task 04-04: Make NodeCanvas editable — wire onNodesChange/onEdgesChange/onConnect + drag-drop drop handler</name>
  <files>frontend/src/components/workflows/editor/NodeCanvas.tsx</files>
  <action>
Modify `NodeCanvas.tsx` to accept new props for editable mode:

```typescript
type Props = {
  template: WorkflowTemplate;
  editable?: boolean;
  onChange?: (graph: { nodes: GraphNode[]; edges: GraphEdge[]; layout: Record<string, NodePosition> }) => void;
  selectedNodeId?: string | null;
  onSelectNode?: (id: string | null) => void;
  validationErrors?: ValidationError[];
};
```

Implementation:

1. Module-scope `NODE_TYPES` extended with the 4 new components (Condition, Parallel, Merge, HumanApproval). All 7 kinds now mapped.

2. State: use React Flow's `useNodesState` and `useEdgesState` (v12 hooks) when `editable=true`. When `editable=false` (the Phase 109 read-only consumer path), keep the existing useMemo-derived static read.

3. When editable:
   - `nodesDraggable={true}`, `nodesConnectable={true}`, `elementsSelectable={true}`
   - `onNodesChange`: standard React Flow applyNodeChanges; emit `onChange` with the new graph
   - `onEdgesChange`: standard applyEdgeChanges; emit `onChange`
   - `onConnect`: validate the connection (e.g. don't allow trigger→trigger), apply via addEdge; emit `onChange`
   - `onSelectionChange`: extract selected node id, call onSelectNode

4. Drag/drop drop handler:

```typescript
const reactFlowInstance = useReactFlow();

const onDragOver = useCallback((event: React.DragEvent) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
}, []);

const onDrop = useCallback((event: React.DragEvent) => {
  event.preventDefault();
  const raw = event.dataTransfer.getData('application/reactflow');
  if (!raw) return;
  const { kind, label } = JSON.parse(raw);
  const position = reactFlowInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY });
  const newNode = {
    id: crypto.randomUUID(),
    type: kind,
    position,
    data: { label, config: {} },
  };
  setNodes((nds) => nds.concat(newNode));
  // Emit onChange so parent (editor page) can track dirty state
}, [reactFlowInstance, setNodes, onChange]);
```

5. Wrap the editor render in `<ReactFlowProvider>` (required by `useReactFlow` hook) — but since `NodeCanvas` is itself the React Flow surface, the parent (editor page) wraps it.

6. Pass `validationErrors` down to nodes via React Flow's `data` field — augment each node's data with the errors filtered to that node_id.

7. Backward-compat: When `editable` is false or unset (Phase 109 viewer call site), behavior is IDENTICAL to today. No regression. Add a vitest test that asserts this.

8. Module-scope NODE_TYPES means importing the 4 new components added in Task 04-01.

9. Empty-state behavior preserved: when `editable=true` AND graph is empty, show NodePalette + an empty canvas with "Drag a Trigger from the palette to start" placeholder (instead of the read-only "Phase 2 will let you add nodes" message).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/NodeCanvas.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <done>NodeCanvas accepts editable prop; existing Phase 109 tests still pass (backward-compat); new tests cover editable mode wiring + drop handler + onConnect.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-05: Service methods saveTemplate / validateTemplate + typed errors</name>
  <files>frontend/src/services/workflows.ts</files>
  <behavior>
    Tests (added to an existing or new services test file — target 6-10 tests):
    - saveTemplate sends PUT with If-Match header; on 200 returns the new version
    - saveTemplate on 412 throws ETagMismatchError carrying the fresh template body + fresh ETag
    - saveTemplate on 409 throws CopyForkError carrying copied_template_id
    - saveTemplate on 428 throws a generic Error with "If-Match required"
    - validateTemplate sends POST with body; returns errors[]
    - getTemplate captures ETag from response and stores in returned object (so caller can pass to next save)
  </behavior>
  <action>
In `frontend/src/services/workflows.ts`:

1. Define typed error classes:

```typescript
export class ETagMismatchError extends Error {
  constructor(public readonly currentTemplate: WorkflowTemplate, public readonly freshEtag: string) {
    super('Template was modified by another save; refresh to see latest');
  }
}

export class CopyForkError extends Error {
  constructor(public readonly copiedTemplateId: string, public readonly seedName: string) {
    super(`Created a private copy of the seed template`);
  }
}
```

2. Extend getWorkflowTemplate to capture the ETag from the response headers and store on the returned object:

```typescript
export interface WorkflowTemplateWithEtag extends WorkflowTemplate {
  _etag?: string;
}

export async function getWorkflowTemplateWithEtag(templateId: string): Promise<WorkflowTemplateWithEtag> {
  const res = await fetch(`${API_BASE}/workflows/templates/${templateId}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to load template: ${res.status}`);
  const body = await res.json();
  const etag = res.headers.get('ETag') ?? undefined;
  return { ...body, _etag: etag };
}
```

(Keep the existing `getWorkflowTemplate` for backward compat; add `getWorkflowTemplateWithEtag` as the new editor-only consumer.)

3. Add saveTemplate:

```typescript
export async function saveTemplate(
  templateId: string,
  payload: { graph_nodes: GraphNode[]; graph_edges: GraphEdge[]; graph_layout: Record<string, NodePosition>; comment?: string },
  etag: string,
): Promise<WorkflowTemplateVersion> {
  const res = await fetch(`${API_BASE}/workflows/templates/${templateId}`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'If-Match': etag,
    },
    body: JSON.stringify(payload),
  });
  if (res.status === 412) {
    const fresh = await res.json();
    const freshEtag = res.headers.get('ETag') ?? '';
    throw new ETagMismatchError(fresh, freshEtag);
  }
  if (res.status === 409) {
    const body = await res.json();
    throw new CopyForkError(body.copied_template_id, body.seed_name ?? 'template');
  }
  if (!res.ok) throw new Error(`Save failed: ${res.status} ${await res.text()}`);
  return res.json();
}
```

4. Add validateTemplate:

```typescript
export async function validateTemplate(
  templateId: string,
  graph: { graph_nodes: GraphNode[]; graph_edges: GraphEdge[] },
): Promise<ValidationError[]> {
  const res = await fetch(`${API_BASE}/workflows/templates/${templateId}/validate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(graph),
  });
  if (!res.ok) throw new Error(`Validate failed: ${res.status}`);
  const body: ValidateGraphResponse = await res.json();
  return body.errors;
}
```

5. Use the existing `withBackendBase` / `getAuthHeaders` helpers if present; mirror the patterns of other service methods in the file.

6. Tests via fetch mocking (msw or vi.spyOn(globalThis, 'fetch')). Pattern: many existing service tests in the codebase, find one and copy the boilerplate.
  </action>
  <verify>
    <automated>cd frontend && grep -c "ETagMismatchError\|CopyForkError\|saveTemplate\|validateTemplate" src/services/workflows.ts</automated>
  </verify>
  <done>Three new service functions + two typed errors exported; >=6 tests pass; npx tsc --noEmit clean.</done>
</task>

<task type="auto">
  <name>Task 04-06: Editor page rewrite — mount palette + canvas + drawer + Save flow</name>
  <files>frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx</files>
  <action>
Replace the current read-only viewer page contents at `frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx` with the editable layout:

```typescript
'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ReactFlowProvider } from '@xyflow/react';
import { toast } from 'sonner';

import { GatedPage } from '@/components/access/GatedPage';
import { PremiumShell } from '@/components/layouts/PremiumShell';
import { DashboardErrorBoundary } from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';
import { NodePalette } from '@/components/workflows/editor/NodePalette';
import { NodePropertiesDrawer } from '@/components/workflows/editor/NodePropertiesDrawer';
import { validateGraph } from '@/components/workflows/editor/useGraphValidation';
import {
  getWorkflowTemplateWithEtag,
  saveTemplate,
  ETagMismatchError,
  CopyForkError,
  type WorkflowTemplate,
  type GraphNode,
  type GraphEdge,
  type NodePosition,
} from '@/services/workflows';

export default function EditorPage() {
  const params = useParams();
  const router = useRouter();
  const templateId = params?.templateId as string;

  const [template, setTemplate] = useState<WorkflowTemplate | null>(null);
  const [etag, setEtag] = useState<string>('');
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [layout, setLayout] = useState<Record<string, NodePosition>>({});
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCommentModal, setShowCommentModal] = useState(false);
  const [comment, setComment] = useState('');

  useEffect(() => {
    if (!templateId || templateId === 'new') return;
    getWorkflowTemplateWithEtag(templateId).then(t => {
      setTemplate(t);
      setEtag(t._etag ?? '');
      setNodes(t.graph_nodes ?? []);
      setEdges(t.graph_edges ?? []);
      setLayout(t.graph_layout ?? {});
    }).catch(err => toast.error(`Failed to load: ${err.message}`));
  }, [templateId]);

  const validationErrors = validateGraph(nodes, edges);
  const canSave = dirty && validationErrors.length === 0 && !saving;

  const handleSave = useCallback(async () => {
    setShowCommentModal(true);
  }, []);

  const confirmSave = useCallback(async () => {
    setSaving(true);
    try {
      const newVersion = await saveTemplate(
        templateId,
        { graph_nodes: nodes, graph_edges: edges, graph_layout: layout, comment: comment || undefined },
        etag,
      );
      toast.success(`Saved as version ${newVersion.version_number}`);
      setEtag(newVersion.saved_at);   // new ETag for next save
      setDirty(false);
      setShowCommentModal(false);
      setComment('');
    } catch (err) {
      if (err instanceof ETagMismatchError) {
        toast.error('Conflict — refresh and try again (full conflict modal coming in Plan 05).');
      } else if (err instanceof CopyForkError) {
        toast.success(`Created your private copy of "${template?.name}"`);
        router.push(`/dashboard/workflows/editor/${err.copiedTemplateId}`);
      } else {
        toast.error(`Save failed: ${(err as Error).message}`);
      }
    } finally {
      setSaving(false);
    }
  }, [templateId, nodes, edges, layout, comment, etag, router, template?.name]);

  const selectedNode = nodes.find(n => n.id === selectedNodeId) ?? null;
  const handleUpdateNode = useCallback((id: string, updates: Partial<GraphNode>) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, ...updates } : n));
    setDirty(true);
  }, []);

  if (templateId === 'new') {
    return /* blank canvas mode — Phase 110 supports editing only existing templates; "new" route stays minimal */;
  }

  return (
    <GatedPage featureKey="workflows">
      <DashboardErrorBoundary>
        <PremiumShell>
          <Breadcrumb segments={[
            { label: 'Home', href: '/dashboard' },
            { label: 'Workflows', href: '/dashboard/workflows' },
            { label: 'Templates', href: '/dashboard/workflows/templates' },
            { label: template?.name ?? '…' },
          ]} />
          <div className="flex h-[calc(100vh-160px)] overflow-hidden">
            <NodePalette />
            <ReactFlowProvider>
              <main className="flex-1 relative" data-testid="editor-canvas-container">
                <div className="absolute top-3 right-3 z-10 flex gap-2 items-center">
                  {validationErrors.length > 0 && (
                    <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                      {validationErrors.length} validation error{validationErrors.length === 1 ? '' : 's'}
                    </span>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={!canSave}
                    className="px-3 py-1.5 rounded bg-emerald-600 text-white disabled:opacity-50"
                    data-testid="editor-save-button"
                  >
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </div>
                <NodeCanvas
                  template={template ?? ({} as WorkflowTemplate)}
                  editable
                  onChange={({ nodes, edges, layout }) => { setNodes(nodes); setEdges(edges); setLayout(layout); setDirty(true); }}
                  selectedNodeId={selectedNodeId}
                  onSelectNode={setSelectedNodeId}
                  validationErrors={validationErrors}
                />
              </main>
            </ReactFlowProvider>
            <NodePropertiesDrawer
              node={selectedNode}
              onUpdate={handleUpdateNode}
              onClose={() => setSelectedNodeId(null)}
            />
          </div>
          {showCommentModal && (
            <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" data-testid="comment-modal">
              <div className="bg-white dark:bg-zinc-900 p-6 rounded shadow-xl w-96 space-y-3">
                <h2 className="font-semibold">Save changes</h2>
                <p className="text-sm text-zinc-500">Optional: describe what changed in this version.</p>
                <textarea
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                  placeholder="e.g. Added approval step before publish"
                  className="w-full border rounded p-2 text-sm"
                  rows={3}
                />
                <div className="flex justify-end gap-2">
                  <button onClick={() => setShowCommentModal(false)} className="px-3 py-1.5 rounded border">Cancel</button>
                  <button onClick={confirmSave} disabled={saving} className="px-3 py-1.5 rounded bg-emerald-600 text-white">
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </PremiumShell>
      </DashboardErrorBoundary>
    </GatedPage>
  );
}
```

Edge cases:
- `templateId === 'new'`: show a placeholder/Phase 3+ message (creating new templates from scratch is deferred to a follow-up; this plan only edits existing).
- Loading state while template is null.
- Error state if getWorkflowTemplateWithEtag fails.
- Save button keyboard shortcut: optional, add Cmd/Ctrl+S handler if time permits.

DO NOT break the existing read-only call sites of NodeCanvas (Plan 04 ensures backward-compat via the `editable` prop default `false`).
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit 2>&1 | grep -E "editor/.+page|NodeCanvas|NodePalette" | head -10; echo "OK if no errors above"</automated>
  </verify>
  <done>Page renders editor layout; Save flow works end-to-end (manual smoke or vitest with mocked fetch); validation badges appear when graph invalid; 412 surfaces sonner toast; 409 redirects + shows copy toast.</done>
</task>

</tasks>

<verification>
End-to-end manual UAT (post-merge of Plans 02 + 03 + 04):

1. Visit `/dashboard/workflows/templates` → click Edit on any template → see editable canvas with NodePalette on left, NodePropertiesDrawer on right.
2. Drag "Agent action" from palette onto canvas → new node appears; canvas marks dirty; Save button enables.
3. Click an existing node → properties drawer populates with label + config fields; edit; see canvas update.
4. Delete trigger node → red badges + Save disabled (validation rule 1 violated).
5. Click Save → comment modal opens; type "test save" → Save → toast "Saved as version 2".
6. Reload page → version 2 graph loads correctly.
7. Open same template in two tabs → save in tab 1 → in tab 2 try to save → 412 toast appears.
8. Click Edit on a seeded template → save → toast "Created your private copy of X" → URL changes to the new template id.
9. Add a Condition node → properties drawer shows "Coming in Phase 3" placeholder → save → no validation error (per Phase 110 placeholder schema).

Automated:
- `cd frontend && npx vitest run src/__tests__/workflows/` — all tests pass.
- `cd frontend && npx tsc --noEmit` — clean.
- `cd frontend && npx eslint src/components/workflows/editor/` — clean.
- Branch hygiene: `git branch --show-current` confirms the Phase 110 branch on every commit.
</verification>

<success_criteria>
This plan ships when:
- 4 new node components + 2 new editor UI components + 2 new hooks + page.tsx rewrite + 3 service functions + 2 typed errors.
- zod added to package.json.
- Combined >=35 new vitest tests pass.
- npx tsc --noEmit clean across the whole frontend.
- ESLint clean on new files.
- Backward-compat: existing Phase 109 NodeCanvas read-only consumer continues to work (editable defaults false).
- Plan SUMMARY committed.
- Addresses roadmap success criteria #1 (drag/connect/configure/save), #7 (client-side validation blocks save with red badges), #8 (server validation parity via shared algorithm + parallel test cases), #10 (Edit button reaches editable editor at same route).
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-04-SUMMARY.md` with the standard sections. Specifically document: (a) why react-hook-form was rejected, (b) which exact Zod version landed, (c) how the empty-state for the "new" route was handled, (d) any deviations from the page.tsx template above driven by existing layout patterns, (e) "Ready for Plan 05" notes describing what the conflict modal + history pane will plug into.
</output>
