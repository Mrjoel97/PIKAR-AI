---
phase: 110-workflow-node-editor-editable
plan: 04
type: execute
wave: 4
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

risk_note: "Plan 04 is the largest in the phase by file count (16 files modified). Executor MUST commit each task individually (one atomic commit per task) and MUST verify the current branch matches the expected pattern (`^plan-(109|110)-`) before EVERY commit via `git branch --show-current`. Phase 109 successfully shipped Plan 109-03 with 7 tasks — this scope is comparable and proven manageable. The 5+-task warning is overridden by precedent + the risk_note + per-task branch checks (W-2 + W-6)."

context_notes_for_executor: "Reads `tests/fixtures/graph_validation_cases.json` (created by Plan 110-03). The shared fixture is a READ dependency for Plan 04's vitest suite — appears in Plan 03's files_modified, NOT this plan's. Plan 04's `useGraphValidation.test.ts` imports + parametrizes over the same cases via `import cases from '../../../tests/fixtures/graph_validation_cases.json'` (relative path from frontend → repo root). The contract: server (Plan 03) and client (Plan 04) must produce equivalent error counts + rule numbers + node_ids for every case, with message_contains substring matching."

must_haves:
  truths:
    - "A user can drag any of the 7 node kinds from a left-rail NodePalette onto the React Flow canvas (Phase 110 ships all 7 visual node components even though only 3 execute today — decision 2C from Claude's Discretion)"
    - "A user can connect a source handle of one node to a target handle of another node by dragging an edge between them; the new edge persists in NodeCanvas state"
    - "Clicking a node opens a right-side NodePropertiesDrawer that renders a Zod-driven form for the node's label + per-kind config; edits update NodeCanvas state and dirty-flag the canvas"
    - "Clicking Save opens an optional comment modal (default empty per Claude's Discretion #5) then POSTs to PUT /workflows/templates/{id} with the current graph + If-Match header + comment; success closes modal and reloads from server"
    - "saveTemplate consumes the response BODY's `etag` field (not response header) as the canonical new ETag after every successful PUT — matches Plan 02's B-2 wire-format contract"
    - "Client-side validation (useGraphValidation hook) runs on every edit and renders red node badges for rule-1/2/3/6/7 failures; Save button is disabled when errors exist; client validator matches server byte-for-byte on every case in tests/fixtures/graph_validation_cases.json (parametrized vitest suite)"
    - "Clicking Edit on a seed template (created_by IS NULL) triggers PUT which the backend returns 409 with {error, copied_template_id, seed_name, message}; CopyForkError reads `body.seed_name` (W-4 contract — Plan 02 guarantees the key) and the editor router.push()es to /dashboard/workflows/editor/{copied_template_id} surfacing a sonner toast 'Created your private copy of \"<seed name>\"'"
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
      provides: "Client-side validator (rules 1/2/3/6/7) matching server validate_workflow_graph EXACTLY on every case in tests/fixtures/graph_validation_cases.json; returns ValidationError[] keyed by node_id"
      contains: "validateGraph"
    - path: "frontend/src/services/workflows.ts"
      provides: "saveTemplate(id, graph, etag, comment?) + validateTemplate(id, graph) service methods; 409/412 surfaced as typed errors; saveTemplate captures new etag from response body (not header) per B-2"
      contains: "saveTemplate"
    - path: "frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx"
      provides: "Editor page swaps from read-only viewer to editable editor; mounts NodeCanvas + NodePalette + NodePropertiesDrawer; routes copied_template_id redirects"
      contains: "NodePalette"
  key_links:
    - from: "Save button onClick"
      to: "saveTemplate() in services/workflows.ts"
      via: "fetch PUT /workflows/templates/{id} with If-Match header and JSON body"
      pattern: "saveTemplate"
    - from: "saveTemplate 200 response"
      to: "Updated local ETag state for next save"
      via: "Read response.body.etag (NOT response.headers — body is canonical per Plan 02 B-2)"
      pattern: "body.etag"
    - from: "saveTemplate 409 response"
      to: "router.push('/dashboard/workflows/editor/{copied_template_id}')"
      via: "Typed CopyForkError thrown by saveTemplate carrying body.copied_template_id + body.seed_name (W-4); caught in page.tsx + toast.success"
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

B-1: Plan 04 moved to Wave 4 (depends_on [110-02, 110-03]) since Plan 03 was promoted to Wave 3. Plans 02 and 03 both have to land before Plan 04's frontend consumers can wire to the backend.

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
@tests/fixtures/graph_validation_cases.json

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
//   export interface { NodePosition, GraphNode, GraphEdge, NodeKind, ValidationError, ValidateGraphResponse }
//   export async function getWorkflowTemplate(templateId: string): Promise<any>   // returns any — cast at call site
//
// frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx
//   Phase 109-03 currently mounts read-only NodeCanvas inside GatedPage + DashboardErrorBoundary + PremiumShell
//   Route param name is [templateId], NOT [id]

<!-- Plan 02 ships (on disk by Wave 4): -->
// app/routers/workflows.py:
//   PUT /workflows/templates/{id}                   -> requires If-Match; 412/428/409/200
//     200 response BODY: { version: WorkflowTemplateVersion, etag: "<quoted ISO8601>" }   ← B-2 canonical etag from body
//     412 response BODY: { ...WorkflowTemplateResponse, etag: "<quoted ISO8601>" }       ← B-2 fresh etag in body
//     409 response BODY: { error: "seed_template_immutable", copied_template_id, seed_name, message }   ← W-4 exact shape
//     428 if If-Match header missing
//   GET /workflows/templates/{id}                   -> sets ETag header (quoted ISO8601)
//   GET /workflows/templates/{id}/history           -> list[HistoryItem]
//   POST /workflows/templates/{id}/revert/{vid}     -> returns new version + etag in body
//
// frontend/src/services/workflows.ts:
//   export type WorkflowTemplateVersion = components['schemas']['WorkflowTemplateVersion'];
//   export type SeedForkResponse = components['schemas']['SeedForkResponse'];   ← W-4 typed body
//   export type SaveTemplateSuccessResponse = components['schemas']['SaveTemplateSuccessResponse'];   ← B-2 typed body
//   (current_version_id present on WorkflowTemplateResponse)

<!-- Plan 03 ships (on disk by Wave 4): -->
// app/routers/workflows.py:
//   POST /workflows/templates/{id}/validate         -> 200 with {errors: ValidationErrorItem[]}
//   PUT /workflows/templates/{id}                   -> now calls validate_workflow_graph() before save (returns 400 on invalid)
//
// frontend/src/services/workflows.ts:
//   export type ValidationError = components['schemas']['ValidationErrorItem'];
//   export type ValidateGraphResponse = components['schemas']['ValidateGraphResponse'];
//
// tests/fixtures/graph_validation_cases.json (READ dependency, B-4 shared fixture)
</interfaces>

<context_notes>
- **B-1 (wave 4):** Plan 04 depends on Plans 02 + 03 backend endpoints being live. Wave 4 — runs after Wave 3 fully completes (Plan 03 wired validation into Plan 02's PUT handler). Plan 04's saveTemplate consumer expects the PUT endpoint to validate-then-save unconditionally; if a stale invalid graph escapes client-side checks, the server returns 400 — Plan 04 must surface that as a toast.
- **B-2 ETag wire format (matches Plan 02 contract):** Every saveTemplate response (200, 412, revert 200) carries the next-write ETag in the response BODY under `etag` (quoted ISO8601). saveTemplate stores `body.etag` (NOT `res.headers.get('ETag')`) as the new local state. On every PUT request, send `'If-Match': etag` verbatim (already quoted from the source — never re-quote or unquote on the client). The server defensively strips quotes, but the client never needs to send unquoted. GET initial load still uses `res.headers.get('ETag')` — the header is canonical for GET responses; the body has the canonical for PUT/POST responses.
- **B-4 shared fixture import:** Plan 04's `useGraphValidation.test.ts` imports `tests/fixtures/graph_validation_cases.json` (created by Plan 03) and parametrizes its `validateGraphClient()` tests over the same cases. Server (Plan 03 pytest) and client (Plan 04 vitest) must produce equivalent error counts + rule numbers + node_ids for every case. Use a relative import path from the frontend test file to the repo-root fixture. Vitest config may need a JSON import-attribute or a tsconfig path alias if module resolution complains; check `vitest.config.ts` for existing patterns.
- New frontend dependencies — DO add: `zod` (^3.23+) for runtime config validation per node kind. Verify: `grep "zod" frontend/package.json` returns 0 — confirms it's new. Add via `cd frontend && npm install zod`.
- Optional consideration: `@hookform/resolvers` + `react-hook-form` — DO NOT ADD. No existing forms use them in this codebase (verified via grep). Use raw `<input>` + `useState` + onBlur validation via Zod schemas. Simpler, fewer deps, matches existing codebase patterns. Plan 04 deviates from CONTEXT.md's optional consideration explicitly here.
- State management: existing codebase has no zustand, no React Query (verified via grep). Use React `useState` + `useCallback` + `useMemo` inside the editor page component. Plan 04 takes Claude's Discretion #7 = "local component state in the page component, lifted as props".
- Phase 109-03 made NodeCanvas READ-ONLY (`nodesDraggable={false} nodesConnectable={false}`). Plan 04 must flip those to `true` for the editor route. The viewer-mode use case from 109 will be preserved via an `editable?: boolean` prop on NodeCanvas (default `false` for backward-compat; the editor page passes `editable={true}`).
- Phase 109-03 added 3 custom node components (Trigger, AgentAction, Output). Plan 04 adds the missing 4 (Condition, Parallel, Merge, HumanApproval) with placeholder visuals + always-show-both-handles. Mirror the styling of the existing 3 (circular for trigger/output, rounded-rect card for actions).
- Save UX: explicit Save button (per Claude's Discretion #3). Disabled when canvas is not dirty OR when validation errors exist. Comment modal on Save (per Discretion #5) defaults empty, user can skip.
- Conflict modal on 412 is Plan 05's responsibility — Plan 04 catches the 412 from `saveTemplate` and just shows a sonner toast for now ("Conflict — refresh and try again. (Conflict modal coming in next plan)"). Plan 05 replaces the toast with the real three-button modal. **B-2: on 412, store the fresh ETag from `body.etag` (NOT header) — when Plan 05's ConflictModal Overwrite path fires, it'll use this stored value.**
- Seed-copy redirect: caught client-side as a typed `CopyForkError` thrown by `saveTemplate()` when the PUT response is 409 with the SeedForkResponse body (W-4). The editor page catches it, surfaces sonner toast `"Created your private copy of \"${err.seedName}\""` (reads `body.seed_name` per W-4 contract — Plan 02 guarantees this key), then `router.push('/dashboard/workflows/editor/' + err.copiedTemplateId)`. The user loses no work — the v1 of the copy starts with the same graph they were editing.
- Drag/drop from palette: HTML5 dataTransfer pattern. NodePalette's draggable nodes call `event.dataTransfer.setData('application/reactflow', JSON.stringify({kind, label}))`. NodeCanvas's onDrop reads this, computes the drop position via React Flow's `project()` helper, generates a UUID via crypto.randomUUID(), appends to the nodes state. Use `event.preventDefault()` in onDragOver to enable drop.
- React Flow v12 hooks: `useReactFlow()` provides `screenToFlowPosition()` (the v12 rename of `project()`). Use it inside the onDrop handler.
- **W-2 scope risk_note** (see plan frontmatter): Plan 04 has 6 tasks, which exceeds the checker's "5+ task" warning threshold. Phase 109 shipped 7-task plans successfully — the scope is proven. Mitigations: per-task atomic commits + per-task automated branch-check (W-6).
- **W-6 branch hygiene:** every task includes `git branch --show-current | grep -Eq '^plan-(109|110)-'` as an automated verify step. Phase 109 was burned by this twice.
- Pre-existing frontend test failures (54 from Phase 109-03 deferred-items.md): Plan 04's new tests must NOT touch the failing test files. Only add new tests in new files.
- Vitest mock for @xyflow/react: 109-03's `NodeCanvas.test.tsx` already has a minimal mock. Plan 04 expands it to support drag/drop simulation — likely just adding `useReactFlow` to the mock returning `{screenToFlowPosition: vi.fn().mockReturnValue({x:0,y:0})}`.
</context_notes>
</context>

<tasks>

<task type="auto">
  <name>Task 04-01: Add zod dependency + four new node components (visual-only, Phase 3/4 kinds)</name>
  <files>frontend/package.json, frontend/package-lock.json, frontend/src/components/workflows/editor/nodes/ConditionNode.tsx, frontend/src/components/workflows/editor/nodes/ParallelNode.tsx, frontend/src/components/workflows/editor/nodes/MergeNode.tsx, frontend/src/components/workflows/editor/nodes/HumanApprovalNode.tsx</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted (W-6).

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
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Four new files exist; each has a data-testid attribute; zod is in package.json; package-lock.json updated.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-02: useGraphSchema (per-kind Zod schemas) + useGraphValidation (client validator) + parametrized fixture tests (B-4)</name>
  <files>frontend/src/components/workflows/editor/useGraphSchema.ts, frontend/src/components/workflows/editor/useGraphValidation.ts, frontend/src/__tests__/workflows/useGraphValidation.test.ts</files>
  <behavior>
    Tests must mirror the Phase 110 server-side test cases via the SHARED fixture (B-4, target 15-20 tests):
    - **Parametrized over tests/fixtures/graph_validation_cases.json:** every named case must produce the documented `expected_errors` list — error count match, rule number match, node_id match, message_contains substring check (case-insensitive).
    - Rule 1: no trigger / multiple triggers / trigger with incoming edge (covered by fixture cases `no_trigger`, `two_triggers`, `trigger_with_incoming_edge`)
    - Rule 2: unreachable node from trigger (fixture case `unreachable_node`)
    - Rule 3: 2-cycle (fixture case `cycle_two_nodes`); plus an additional non-fixture test for 3-cycle
    - Rule 6: no output (fixture case `no_output`)
    - Rule 7: agent-action missing tool_name (fixture case `bad_agent_action_config`); plus non-fixture tests for agent-action with extras, condition with empty config (Phase 110 permissive)
    - Valid happy-path graph (fixture case `valid_minimal`) returns []
    - Empty graph: returns rule-1 error
    - Output type: ValidationError[] with shape {node_id: string|null, rule: number, message: string}
    - **Parity assertion (B-4):** for every fixture case, the count + rule numbers + node_ids of the client's output match what Plan 03's server test would produce. (We don't actually call the server in vitest — we trust the server tests parametrize over the same fixture, so equivalence is established by both sides asserting the same `expected_errors`.)
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

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

Implementation: copy the algorithm from `app/workflows/graph_validation.py` (Plan 03 Task 03-01) and translate to TypeScript. The two MUST produce the same result for the same input — both parametrize over the shared fixture (B-4).

Server returns `{node_id: string|null, rule: number, message: string}`; client mirror returns the same shape (mapped to the `ValidationError` TS type Plan 03 exports).

3. Tests at `frontend/src/__tests__/workflows/useGraphValidation.test.ts` (vitest, no jsdom needed — pure function). >=15 tests.

**B-4 parametrized fixture loader (canonical pattern):**

```typescript
import { describe, it, expect } from 'vitest';
import cases from '../../../../tests/fixtures/graph_validation_cases.json';  // relative path frontend → repo root
import { validateGraph } from '@/components/workflows/editor/useGraphValidation';

describe('useGraphValidation — shared fixture parity (B-4)', () => {
  cases.forEach((tc: any) => {
    it(`case: ${tc.name}`, () => {
      const actual = validateGraph(tc.input.graph_nodes, tc.input.graph_edges);
      expect(actual.length).toBe(tc.expected_errors.length);
      tc.expected_errors.forEach((expected: any, i: number) => {
        expect(actual[i].node_id).toBe(expected.node_id);
        expect(actual[i].rule).toBe(expected.rule);
        if (expected.message_contains) {
          expect(actual[i].message.toLowerCase()).toContain(
            expected.message_contains.toLowerCase()
          );
        }
      });
    });
  });
});
```

Add additional non-fixture tests for edge cases (3-cycle, empty graph, agent-action with extras passes, condition with empty config passes).

**If vitest module resolution complains about the relative import to tests/fixtures/**, add a path alias in `vitest.config.ts` (or `tsconfig.json` paths section if present) — pattern: `'@fixtures/*': '../tests/fixtures/*'`. Use whatever works for the existing repo setup; do not over-engineer.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/__tests__/workflows/useGraphValidation.test.ts 2>&1 | tail -15</automated>
    <automated>test -f tests/fixtures/graph_validation_cases.json && echo FIXTURE_EXISTS</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Two new hook files exist; >=15 useGraphValidation tests pass (including parametrized fixture tests); the shared fixture is the canonical contract — both client and server agree on every case.</done>
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
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

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
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Both components exist; combined >=10 tests pass; ESLint/tsc clean.</done>
</task>

<task type="auto">
  <name>Task 04-04: Make NodeCanvas editable — wire onNodesChange/onEdgesChange/onConnect + drag-drop drop handler</name>
  <files>frontend/src/components/workflows/editor/NodeCanvas.tsx</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

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
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>NodeCanvas accepts editable prop; existing Phase 109 tests still pass (backward-compat); new tests cover editable mode wiring + drop handler + onConnect.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 04-05: Service methods saveTemplate / validateTemplate + typed errors with body-canonical ETag (B-2 + W-4)</name>
  <files>frontend/src/services/workflows.ts</files>
  <behavior>
    Tests (target 8-12 tests):
    - saveTemplate sends PUT with If-Match header (the captured quoted ETag, sent verbatim)
    - **B-2:** saveTemplate on 200 reads `body.etag` (NOT response header) as the canonical new ETag; returned object has `.etag` field for caller to store
    - **B-2:** saveTemplate on 412 throws ETagMismatchError carrying the fresh template body + `body.etag` (NOT header etag); error has `.freshEtag` field readable by Plan 05's ConflictModal
    - **W-4:** saveTemplate on 409 throws CopyForkError reading `body.copied_template_id` AND `body.seed_name` (both required; Plan 02 guarantees both keys)
    - saveTemplate on 428 throws a generic Error with "If-Match required"
    - saveTemplate on 400 throws a typed ValidationFailedError carrying the server's validation errors list (Plan 03 returns 400 from PUT if validate_workflow_graph finds errors)
    - validateTemplate sends POST with body; returns errors[]
    - getWorkflowTemplateWithEtag captures ETag from response HEADERS (canonical for GET) and stores in returned object
  </behavior>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

In `frontend/src/services/workflows.ts`:

1. Define typed error classes:

```typescript
export class ETagMismatchError extends Error {
  constructor(public readonly currentTemplate: WorkflowTemplate, public readonly freshEtag: string) {
    super('Template was modified by another save; refresh to see latest');
  }
}

export class CopyForkError extends Error {
  // W-4: reads body.copied_template_id AND body.seed_name from the 409 response
  constructor(public readonly copiedTemplateId: string, public readonly seedName: string) {
    super(`Created a private copy of the seed template`);
  }
}

export class ValidationFailedError extends Error {
  constructor(public readonly errors: ValidationError[]) {
    super(`Validation failed: ${errors.length} error(s)`);
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
  // GET response: ETag is canonical in headers (per Plan 02 contract — body has no etag field on GET)
  const etag = res.headers.get('ETag') ?? undefined;
  return { ...body, _etag: etag };
}
```

(Keep the existing `getWorkflowTemplate` for backward compat; add `getWorkflowTemplateWithEtag` as the new editor-only consumer.)

3. Add saveTemplate (B-2 wire format — body etag is canonical for PUT response):

```typescript
export type SaveTemplateResult = {
  version: WorkflowTemplateVersion;
  etag: string;   // new ETag for the next save — read from response BODY per Plan 02 contract
};

export async function saveTemplate(
  templateId: string,
  payload: { graph_nodes: GraphNode[]; graph_edges: GraphEdge[]; graph_layout: Record<string, NodePosition>; comment?: string },
  etag: string,   // current local ETag — sent verbatim (already quoted from prior GET or PUT)
): Promise<SaveTemplateResult> {
  const res = await fetch(`${API_BASE}/workflows/templates/${templateId}`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'If-Match': etag,   // already quoted from source; do NOT re-quote or strip
    },
    body: JSON.stringify(payload),
  });

  if (res.status === 412) {
    const body = await res.json();
    // B-2: fresh ETag is in body.etag (NOT header) per Plan 02 contract
    throw new ETagMismatchError(body, body.etag);
  }
  if (res.status === 409) {
    const body = await res.json();
    // W-4: body has {error, copied_template_id, seed_name, message} — Plan 02 guarantees all keys
    throw new CopyForkError(body.copied_template_id, body.seed_name);
  }
  if (res.status === 400) {
    // Plan 03 wired validate_workflow_graph into PUT — bad graph → 400 with validation errors
    const body = await res.json();
    const errors = body.detail?.errors ?? body.errors ?? [];
    throw new ValidationFailedError(errors);
  }
  if (res.status === 428) {
    throw new Error('If-Match header required (428 Precondition Required)');
  }
  if (!res.ok) throw new Error(`Save failed: ${res.status} ${await res.text()}`);

  // 200: body has {version, etag} per Plan 02 SaveTemplateSuccessResponse model
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

Specifically add these B-2 assertions to the tests:
- `test_saveTemplate_200_returns_etag_from_body_not_header` — mock response with `body.etag = '"X"'` and `headers.etag = '"WRONG"'`; assert returned `result.etag === '"X"'`
- `test_saveTemplate_412_throws_ETagMismatchError_with_body_etag` — mock 412 with `body.etag = '"X"'` and `headers.etag = '"WRONG"'`; assert thrown error's `.freshEtag === '"X"'`
- `test_saveTemplate_If_Match_header_sent_verbatim` — pass `etag = '"2026-05-11T..."'` (with quotes); assert fetch was called with `headers['If-Match'] === '"2026-05-11T..."'` (verbatim, no re-quoting)
- `test_saveTemplate_409_CopyForkError_reads_both_copied_template_id_and_seed_name` — assert error has both fields populated from body (W-4)
  </action>
  <verify>
    <automated>cd frontend && grep -c "ETagMismatchError\|CopyForkError\|ValidationFailedError\|saveTemplate\|validateTemplate" src/services/workflows.ts</automated>
    <automated>cd frontend && npx vitest run src/__tests__/services 2>&1 | tail -10 || cd frontend && npx vitest run src/__tests__/workflows 2>&1 | grep -E "saveTemplate|validateTemplate" | tail -10</automated>
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Three new service functions + three typed errors exported; saveTemplate reads body.etag as canonical (B-2); CopyForkError reads body.seed_name AND body.copied_template_id (W-4); If-Match sent verbatim; ValidationFailedError surfaces Plan 03's 400 responses; >=8 tests pass; npx tsc --noEmit clean.</done>
</task>

<task type="auto">
  <name>Task 04-06: Editor page rewrite — mount palette + canvas + drawer + Save flow</name>
  <files>frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx</files>
  <action>
PRECONDITION: `git branch --show-current` matches `^plan-(109|110)-`. Abort if drifted.

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
  ValidationFailedError,
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
      setEtag(t._etag ?? '');                        // ETag from GET response HEADER (canonical for GET)
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
      const result = await saveTemplate(
        templateId,
        { graph_nodes: nodes, graph_edges: edges, graph_layout: layout, comment: comment || undefined },
        etag,
      );
      toast.success(`Saved as version ${result.version.version_number}`);
      // B-2: PUT 200 response BODY carries the new ETag canonically (NOT header)
      setEtag(result.etag);
      setDirty(false);
      setShowCommentModal(false);
      setComment('');
    } catch (err) {
      if (err instanceof ETagMismatchError) {
        toast.error('Conflict — refresh and try again (full conflict modal coming in Plan 05).');
        // B-2: stash the fresh etag from body for when Plan 05 ConflictModal Overwrite path fires
        // (Plan 05 will replace this temporary toast with the real modal; the fresh etag from
        //  err.freshEtag — read from body.etag per Plan 02 — is the value the Overwrite PUT will use)
      } else if (err instanceof CopyForkError) {
        // W-4: err.seedName + err.copiedTemplateId both populated from 409 body
        toast.success(`Created your private copy of "${err.seedName}"`);
        router.push(`/dashboard/workflows/editor/${err.copiedTemplateId}`);
      } else if (err instanceof ValidationFailedError) {
        // Plan 03's PUT-with-invalid-graph → 400 path
        toast.error(`Save failed: ${err.errors.length} validation error(s). Fix red badges and retry.`);
      } else {
        toast.error(`Save failed: ${(err as Error).message}`);
      }
    } finally {
      setSaving(false);
    }
  }, [templateId, nodes, edges, layout, comment, etag, router]);

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
    <automated>git branch --show-current | grep -Eq '^plan-(109|110)-' && echo BRANCH_OK || (echo BRANCH_WRONG && exit 1)</automated>
  </verify>
  <done>Page renders editor layout; Save flow works end-to-end (manual smoke or vitest with mocked fetch); validation badges appear when graph invalid; 412 surfaces sonner toast (Plan 05 replaces with modal); 409 redirects + shows copy toast using err.seedName (W-4); 400 surfaces validation error toast.</done>
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
8. Click Edit on a seeded template → save → toast "Created your private copy of X" (X = seed_name from body, W-4) → URL changes to the new template id.
9. Add a Condition node → properties drawer shows "Coming in Phase 3" placeholder → save → no validation error (per Phase 110 placeholder schema).
10. Submit a hand-crafted invalid graph (e.g. cycle) via direct API call → server returns 400 → client surfaces ValidationFailedError toast (Plan 03's PUT-validation wire).

Automated:
- `cd frontend && npx vitest run src/__tests__/workflows/` — all tests pass.
- `cd frontend && npx tsc --noEmit` — clean.
- `cd frontend && npx eslint src/components/workflows/editor/` — clean.
- Branch hygiene: `git branch --show-current` confirms the Phase 110 branch on every commit (W-6, automated in every task).
- B-4 shared fixture parity: `useGraphValidation.test.ts` parametrized cases ALL pass (validating against tests/fixtures/graph_validation_cases.json).
</verification>

<success_criteria>
This plan ships when:
- 4 new node components + 2 new editor UI components + 2 new hooks + page.tsx rewrite + 3 service functions + 3 typed errors (incl. ValidationFailedError for B-1 wave-3 wiring on PUT).
- zod added to package.json.
- Combined >=35 new vitest tests pass, including B-4 parametrized fixture tests for client/server parity.
- npx tsc --noEmit clean across the whole frontend.
- ESLint clean on new files.
- Backward-compat: existing Phase 109 NodeCanvas read-only consumer continues to work (editable defaults false).
- B-2 wire format: saveTemplate reads body.etag (not header) on PUT 200/412; sends If-Match verbatim.
- W-4: CopyForkError reads both `body.copied_template_id` AND `body.seed_name`; editor toast uses `err.seedName`.
- W-6: every task commit verifies branch via automated check.
- W-2: risk_note in frontmatter acknowledges 6-task scope is intentional and proven by Phase 109 precedent.
- Plan SUMMARY committed.
- Addresses roadmap success criteria #1 (drag/connect/configure/save), #7 (client-side validation blocks save with red badges), #8 (server validation parity via shared fixture + parametrized test cases), #10 (Edit button reaches editable editor at same route).
</success_criteria>

<output>
After completion, create `.planning/phases/110-workflow-node-editor-editable/110-04-SUMMARY.md` with the standard sections. Specifically document: (a) why react-hook-form was rejected, (b) which exact Zod version landed, (c) how the empty-state for the "new" route was handled, (d) any deviations from the page.tsx template above driven by existing layout patterns, (e) the actual relative import path used for tests/fixtures/graph_validation_cases.json in vitest (and whether a path alias was added), (f) confirmation that all B-4 fixture cases pass parametrized client tests, (g) "Ready for Plan 05" notes describing what the conflict modal + history pane will plug into (specifically: the freshEtag from body.etag stashed in error state).
</output>
</content>
</invoke>