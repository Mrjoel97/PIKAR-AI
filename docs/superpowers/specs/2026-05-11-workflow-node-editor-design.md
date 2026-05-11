# Workflow Node Editor & Branching Engine — Design Spec (Spec B)

**Date:** 2026-05-11
**Status:** Draft, pending user review
**Scope:** Spec B of two. Follow-up to [Spec A — Live Workspace Workflow View](2026-05-11-live-workspace-workflow-view-design.md), which shipped 2026-05-11 in PR #23 and gives users a transparency layer for *watching* workflows execute. Spec B gives them a visual canvas for *authoring* workflows — including branching, conditionals, parallel paths, and human-approval nodes — replacing the current YAML/code-only authoring path.

## Summary

Today, workflows are authored as `WorkflowTemplate` rows whose `steps` field is a linear JSON list. Non-technical users cannot create or modify workflows; they can only pick from a pre-seeded template browser at `/dashboard/workflows/templates` and click "Start". There is no canvas, no graph, no conditional, no human-readable branching primitive — anywhere in the codebase. A `grep -i "reactflow\|node-graph\|node editor"` over the repo returns zero results.

This spec adds:

1. A **visual node editor** at `/dashboard/workflows/editor/[id]` built on React Flow (`@xyflow/react`), letting users drag-drop nodes, connect them with edges, set per-node properties, and save the result as a `WorkflowTemplate` with an extended graph-aware schema.
2. A **branching engine** in `app/workflows/engine.py` that can execute templates whose graph contains conditional edges, parallel forks, joins, and human-approval gates — not just linear sequences.
3. A **migration path** for existing linear templates so they auto-render as straight-line graphs in the editor without schema rewrites.

This is the "non-technical user can build their own workflow" pillar of the product. Until Spec B ships, that pillar is unimplemented.

## Problem

The current workflow authoring story is broken for the target persona:

- **No editor UI.** `/dashboard/workflows` redirects to `/dashboard/workflows/templates` which lists pre-seeded cards. The "Create Draft" button at `frontend/src/app/dashboard/workflows/templates/page.tsx:146` routes to `/dashboard/workflows/editor/new` but this route doesn't exist on prod — confirmed by `Glob "frontend/src/app/dashboard/workflows/editor/**"` returning no results. Clicking the button 404s or renders a blank page.
- **No branching primitive.** `WorkflowTemplate.steps` is a `list[dict]` in `app/workflows/registry.py`; `engine.execute()` walks the list sequentially and short-circuits on the first failure. There is no conditional dispatch, no per-step outcome-driven routing, no parallel fork, no merge. A user who wants "if the lead scores > 80, route to AE; else nurture" has no way to express it.
- **No visual representation of existing templates.** Even the linear templates today are invisible — a user clicking "Edit" on a template card hits the same missing editor route. The shape of a template (what it does, in what order, with what tools) is hidden behind YAML inside the seed files.
- **Spec A's data contract is one-sided.** Spec A added `workflow_executions.goal`, `workflow_steps.outcome_text`, and SSE streaming for live execution. The producing side — how a workflow ends up running — was deferred. Spec B closes that loop: editor produces the graph; engine consumes it; Spec A widget watches it run.

## Goals

1. **A non-technical user can build a working multi-step workflow from scratch in under 15 minutes.** Drag nodes, connect edges, fill in properties, click Save & Test. No YAML, no code, no terminal.
2. **The editor supports branching.** At least three node types beyond "agent action": `condition` (if/else evaluated against prior-step outcome), `parallel` (fork two or more branches), `merge` (join branches), and `human-approval` (pause and surface in workspace via Spec A's existing approval flow).
3. **Existing linear templates render as graphs without data migration.** The 30+ seeded templates in `app/workflows/registry.py` open in the editor as straight-line graphs; the editor saves them back in the new graph schema; the engine treats them identically.
4. **The engine actually executes the new node types.** A condition node evaluates a JSONLogic expression against the execution context and routes to the matching outgoing edge. A parallel node runs all outgoing branches concurrently with `asyncio.gather`. A merge waits for all incoming branches before continuing.
5. **Spec A widgets render branched runs correctly.** The `WorkflowTimelineWidget` adapts to show simultaneous branches and the path actually taken through conditionals. No regression for purely-linear runs.

## Non-Goals

- **Multi-user collaborative editing.** v1 is single-user-at-a-time; last-save-wins. Real-time co-editing is a future spec.
- **User-defined custom node types.** v1 ships a fixed palette: trigger, agent-action, condition, parallel, merge, human-approval, output. Users can configure node properties but cannot add new kinds.
- **Loops.** v1 only supports directed acyclic graphs (DAGs). The engine rejects cyclic templates at save time. Iteration / "do until" is a future spec.
- **Sub-workflow nodes.** A node that calls another workflow as a sub-routine is out of scope; reuse via copy-paste-template only.
- **Mobile-first editor UX.** v1 is desktop-only. Mobile gets read-only graph view.
- **Migrating Spec A's `WorkflowTimelineWidget` to a graph layout.** Linear timeline view continues to work for linear runs; we add a *separate* `WorkflowGraphRunWidget` for branched runs and let the workspace canvas auto-pick.
- **Custom expression language for conditions.** v1 uses [JSONLogic](https://jsonlogic.com/) as-is; no DSL.

## Decisions (open until reviewed)

| Question | Proposed decision | Rationale |
|---|---|---|
| Graph library | React Flow (`@xyflow/react` v12+) | Industry standard; used by n8n, Retool, etc.; ~150kb bundle; framework-agnostic; built-in pan/zoom/minimap |
| Storage schema | Extend `workflow_templates` with `graph_nodes` (JSONB) and `graph_edges` (JSONB) columns; keep `steps` populated for backward compat on linear templates | Avoids a parallel table; lets old engine code still work on linear-only templates while new engine reads graph |
| Edge condition language | JSONLogic JSON expressions evaluated against `{previous_outcomes, current_step, user_context}` | Mature, language-agnostic, no eval risk; ships as `json-logic-js` (frontend) + `json-logic-py` (backend); equivalent semantics |
| Engine extension | New `app/workflows/graph_executor.py` alongside existing `step_executor.py`; `engine.execute()` dispatches based on template's `graph_nodes` presence | Keeps linear-path codepath untouched; isolates new complexity; easier to feature-flag |
| Node-property panel | Right-side drawer that opens on node-click; properties driven by per-node-type Zod schema | Reuses existing form components; per-type schema = type-safe + autogenerated UI |
| Save-and-test loop | Save creates a hidden "test draft" template; Test runs it once with synthetic inputs and shows the Spec A timeline widget inline below the canvas | Same widget for authoring preview and live monitoring = one mental model |
| Feature flag | `WORKFLOW_NODE_EDITOR` env var on backend (default off), `NEXT_PUBLIC_WORKFLOW_NODE_EDITOR` on frontend (default off) | Mirrors `LIVE_WORKFLOW_VIEW` pattern from Spec A; lets us ship Phase 1 to internal users only |

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  USER (canvas, non-technical)                                        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ drag, connect, configure, save
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  frontend/src/app/dashboard/workflows/editor/[id]/page.tsx    [NEW]  │
│  + frontend/src/components/workflows/editor/                         │
│       NodeCanvas.tsx          (React Flow wrapper)                   │
│       NodePalette.tsx         (left rail: drag sources)              │
│       NodePropertiesDrawer.tsx (right rail: per-node form)           │
│       nodes/AgentActionNode.tsx, ConditionNode.tsx, ParallelNode.tsx │
│            MergeNode.tsx, HumanApprovalNode.tsx, OutputNode.tsx      │
│       useGraphSchema.ts       (Zod schema per node type)             │
│       useGraphValidation.ts   (client-side cycle/dangling detection) │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ PUT /workflows/templates/{id}
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  app/routers/workflows.py                                            │
│     • new endpoint: PUT /templates/{id}  (replace graph)      [NEW]  │
│     • new endpoint: POST /templates/{id}/validate             [NEW]  │
│     • existing GET /templates returns graph_nodes/edges if set       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  app/workflows/registry.py                                           │
│     • WorkflowTemplate.graph_nodes: list[GraphNode] | None    [NEW]  │
│     • WorkflowTemplate.graph_edges: list[GraphEdge] | None    [NEW]  │
│     • .steps remains for linear-only templates (back-compat)         │
│     • .is_linear() helper returns True when graph_* are None         │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼  (on start_workflow_execution)
┌──────────────────────────────────────────────────────────────────────┐
│  app/workflows/engine.py                                             │
│     • if template.is_linear(): existing step_executor path           │
│     • else: new graph_executor path                            [NEW] │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  app/workflows/graph_executor.py                              [NEW]  │
│     • Topological sort with parallel layers                          │
│     • For each ready node:                                           │
│         - agent-action: existing step_executor.execute()             │
│         - condition: eval JSONLogic; pick matching outgoing edge     │
│         - parallel: asyncio.gather over outgoing edges               │
│         - merge: wait for all incoming to complete                   │
│         - human-approval: write workflow_steps row with              │
│             status='waiting_approval', emit Spec A SSE event,        │
│             suspend until approve/reject endpoint fires              │
│         - output: write final outcome, mark execution complete       │
│     • Cycle detection at start; abort with engine error              │
│     • Reuses Spec A's OutcomeWriter + WorkspaceItemEmitter           │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ event_bus SSE (Spec A transport)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  frontend/src/components/widgets/WorkflowGraphRunWidget.tsx   [NEW]  │
│     • Renders the same React Flow graph with live status overlays    │
│     • Active node glows; taken edge highlighted; pending nodes muted │
│     • Same approve/reject inline interaction as Spec A widget        │
│  + WorkflowTimelineWidget.tsx                            [UNCHANGED] │
│     • Continues to render linear runs unchanged                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Model

### New columns on `workflow_templates`

```sql
ALTER TABLE workflow_templates
  ADD COLUMN graph_nodes  JSONB,
  ADD COLUMN graph_edges  JSONB,
  ADD COLUMN graph_layout JSONB;  -- node positions (x, y) for canvas
```

`graph_nodes` is `NULL` for legacy linear templates. `graph_edges` is `NULL`. The engine treats `graph_nodes IS NULL` as "linear path; use existing `steps` field". This is the back-compat hinge.

### Graph node shape

```ts
type GraphNode = {
  id: string;                        // stable uuid, used as edge endpoint
  kind:
    | 'trigger'
    | 'agent-action'
    | 'condition'
    | 'parallel'
    | 'merge'
    | 'human-approval'
    | 'output';
  label: string;                     // user-visible name
  config: AgentActionConfig
        | ConditionConfig
        | HumanApprovalConfig
        | ...;                       // per-kind Zod-validated
  position?: { x: number; y: number };  // for canvas rendering only
};

type AgentActionConfig = {
  tool_name: string;
  arguments: Record<string, unknown>;
  agent_role?: string;  // defaults to ExecutiveAgent
};

type ConditionConfig = {
  expression: JsonLogicValue;        // e.g. {">": [{"var": "lead_score"}, 80]}
};

type HumanApprovalConfig = {
  prompt: string;
  default_decision?: 'approve' | 'reject';
  timeout_seconds?: number;
};
```

### Graph edge shape

```ts
type GraphEdge = {
  id: string;
  source: string;                    // node id
  target: string;                    // node id
  source_handle?: 'true' | 'false'   // for condition nodes
                 | 'branch-1' | ...; // for parallel nodes
  label?: string;
};
```

A `condition` node has exactly two outgoing edges keyed by `source_handle: 'true' | 'false'`. A `parallel` node has N outgoing edges. A `merge` node has exactly one outgoing edge but N incoming. The validator enforces this at save time.

### Validation contract

Both client (before allowing Save) and server (in `POST /templates/{id}/validate`) must enforce:

1. **Single trigger.** Exactly one node has `kind: 'trigger'` and zero incoming edges.
2. **Reachability.** Every node is reachable from the trigger via directed edges.
3. **No cycles.** Topological sort succeeds. (DAG-only in v1.)
4. **Condition outgoing degree.** A `condition` node has exactly 2 outgoing edges with `source_handle` values `{'true', 'false'}` (set equality).
5. **Parallel/merge pairing.** Every `parallel` has a corresponding `merge` downstream on all branches before any `output`.
6. **At least one output.** At least one node has `kind: 'output'`.
7. **Properties valid.** Each node's `config` passes its per-kind Zod schema.

Failed validation returns a structured `{ errors: [{ node_id, message }, ...] }` the editor renders as red badges on offending nodes.

## Migration path for existing templates

Linear-to-graph projection (one-time, performed on first edit, NOT during ETL):

```
seeded_template.steps = [s1, s2, s3, s4]

becomes

graph_nodes = [
  { id: 'trigger', kind: 'trigger', label: 'Start' },
  { id: 's1', kind: 'agent-action', label: s1.name, config: { tool_name: s1.tool, ... } },
  { id: 's2', kind: 'agent-action', label: s2.name, config: { ... } },
  { id: 's3', kind: 'agent-action', label: s3.name, config: { ... } },
  { id: 's4', kind: 'agent-action', label: s4.name, config: { ... } },
  { id: 'output', kind: 'output', label: 'Done' },
]
graph_edges = [
  { source: 'trigger', target: 's1' },
  { source: 's1', target: 's2' },
  { source: 's2', target: 's3' },
  { source: 's3', target: 's4' },
  { source: 's4', target: 'output' },
]
graph_layout = computed by dagre auto-layout on first render
```

The legacy `steps` column stays populated; the engine prefers `graph_nodes` if present. A user who opens an old template, makes no changes, and clicks Save promotes it to the new format and the engine flips to the new path.

## Phased rollout

Four shippable phases. Each phase is testable end-to-end on its own; user value compounds.

### Phase 1 — Read-only graph viewer (2 weeks)

**Deliverables:**
- `frontend/src/components/workflows/editor/NodeCanvas.tsx` with React Flow, pan/zoom, but no editing
- Linear-to-graph projection function in `frontend/src/services/workflows.ts`
- `/dashboard/workflows/editor/[id]` route that fetches a template and renders it as a static graph
- No backend changes

**User value:** Users can SEE the shape of every existing template visually. Today they can't.

**Acceptance:**
- Every one of the 30+ seeded templates renders as a connected graph without errors
- Trigger/output nodes show distinctly from agent-action nodes
- Pan, zoom, fit-to-screen work

### Phase 2 — Editable graph + save (3 weeks)

**Deliverables:**
- Drag-from-palette to add nodes; click-to-edit properties drawer
- `NodePropertiesDrawer` with Zod-driven forms per node kind
- `PUT /workflows/templates/{id}` accepts `graph_nodes` + `graph_edges`
- Client + server validation (rules 1, 2, 3, 6, 7 above)
- Linear-only execution still — adding a condition node saves but doesn't run yet

**User value:** Users can create new linear templates visually. Can edit existing templates' tool args, names, etc. Cannot yet branch.

**Acceptance:**
- New template creatable from blank canvas with at least 3 connected nodes
- Edits to existing templates persist
- Validation errors render as red node badges and block save
- A new graph-only template, when started, runs end-to-end via the existing linear engine (because all edges are sequential)

### Phase 3 — Branching execution (4 weeks)

**Deliverables:**
- `app/workflows/graph_executor.py` with topological execution
- Condition node evaluation via `json-logic-py`
- `WorkflowGraphRunWidget` for live runs with branch highlighting
- Validation rules 4 (condition outgoing degree)

**User value:** Users can build "if X then A else B" workflows and they actually run.

**Acceptance:**
- Round-trip: design a 2-branch conditional in the editor → save → start execution → observe the correct branch run live in the widget → both branches' outcomes appear when forced via test
- Existing linear templates continue to run unchanged
- Branched run's outcomes flow through Spec A's `outcome_writer` and SSE pipeline

### Phase 4 — Parallel + human-approval nodes (4 weeks)

**Deliverables:**
- Parallel node executes outgoing edges via `asyncio.gather`
- Merge node waits for all incoming via `asyncio.wait`
- Human-approval node integrates with Spec A's approval endpoint
- Validation rule 5 (parallel/merge pairing)
- Cycle detection at save time

**User value:** Users can build "do A and B in parallel; require human approval for C; merge results" workflows.

**Acceptance:**
- A workflow with one parallel fork and one human-approval gate executes correctly
- Pausing for approval surfaces in the Spec A workspace item and resumes on approve/reject
- Cycle detection rejects invalid graphs at save time with a clear error

## Open questions

The following need user input before Phase 1 begins:

1. **Condition expression authoring UX.** JSONLogic JSON is engineer-friendly but not user-friendly. Should v1 ship with (a) raw JSON editor for power users, (b) a guided form ("if [previous outcome field] [is greater than] [80]"), or (c) both behind a tab toggle? Recommend (c) but it doubles Phase 3 frontend work.

2. **Test-run sandboxing.** When the user clicks "Test" should we (a) call real agent tools with real cost, (b) call them with a `dry_run=true` flag that we'd have to thread through every tool, or (c) build a fixture-based mock-execution engine? Recommend (a) for v1 with a clear cost-incurred warning; (b)/(c) are big projects.

3. **Per-user vs per-org template scope.** Are user-created templates private to the user, shared with the workspace team (Spec A is per-user), or shared org-wide? Recommend per-workspace (matches Team Workspace tier feature) but this needs an `owner_workspace_id` column on `workflow_templates`.

4. **Migration trigger.** Do we eagerly project ALL existing linear templates to graph format on Phase 1 deploy, or lazily on first edit? Lazy is safer (no data migration risk) but means the read-only viewer in Phase 1 must do projection at render time. Recommend lazy.

5. **Versioning.** Saving an edit on a published template — does it (a) overwrite (simple, loses history), (b) create a new version row (needs `version` column + parent-version FK), or (c) require explicit Publish vs Save Draft (matches industry tools but bigger UX)? Recommend (a) for v1; flag for upgrade.

6. **Concurrency on save.** No optimistic locking today. Two users editing the same template will silently overwrite each other. Recommend adding `updated_at`-based If-Match in Phase 2.

## Dependencies & risks

- **Depends on Spec A's data contract** (`workflow_executions.goal`, `workflow_steps.outcome_text`, SSE event bus, `OutcomeWriter`). Already shipped; Spec B reuses without modification.
- **Adds a frontend dependency:** `@xyflow/react` v12+ (~150kb gz), `json-logic-js` (~5kb).
- **Adds a backend dependency:** `json-logic-py` (~10kb).
- **Risk: branching engine introduces nondeterminism.** Existing tests assume linear execution; we MUST keep `engine.execute()` linear-only when `graph_nodes IS NULL`. The graph executor is a parallel codepath, not a replacement.
- **Risk: React Flow canvas perf with > 200 nodes.** Limit v1 to 100 nodes per template; surface as validation warning.
- **Risk: Human-approval nodes can deadlock the engine** if the approve endpoint never fires. Phase 4 must include a `timeout_seconds` on the human-approval node with a default of 7 days, after which the engine auto-rejects with a logged reason.

## Out of scope (deferred to Spec C+)

- Loops (`while`, `for-each`)
- Sub-workflow nodes
- Real-time multi-user co-editing
- User-defined node kinds / custom plugins
- Template marketplace / sharing across orgs
- Mobile-first editor
- Versioning and rollback UI

## Effort estimate

| Phase | Engineering weeks | Calendar weeks (with QA + UAT) |
|---|---|---|
| 1 — Read-only viewer | 1.5 | 2 |
| 2 — Editable + save | 2.5 | 3 |
| 3 — Branching execution | 3 | 4 |
| 4 — Parallel + human-approval | 3 | 4 |
| **Total (v1)** | **10** | **13** |

This is dominated by Phase 3+4 backend engine work. Frontend graph rendering is mostly off-the-shelf via React Flow. Phase 1+2 alone (read-only graph + editable save) is shippable in ~5 calendar weeks and provides immediate user value (users can finally *see* their workflows) without the engine risk.

## What unblocks this spec from leaving Draft

1. User answers the six open questions above (or accepts the recommendation in each).
2. Confirmation that v1 scope = Phases 1-4 above; Spec C handles loops/sub-workflows/marketplace.
3. Confirmation of phased shipping — i.e. Phase 1 can go live on its own with `WORKFLOW_NODE_EDITOR=true` for internal users only.
4. Sign-off on the new schema columns (`graph_nodes`, `graph_edges`, `graph_layout`) being JSONB rather than relational. The alternative — separate `workflow_graph_nodes` / `workflow_graph_edges` tables — gives queryability but adds migration risk and join overhead with no clear v1 benefit.

Once those four boxes are checked, the next step is `/gsd:plan-phase` to create Phase 1's `PLAN.md`.
