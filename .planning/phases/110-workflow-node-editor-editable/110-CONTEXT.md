# Phase 110: Workflow Node Editor — Phase 2 (Editable + Save + Versioning) — Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Source:** PRD Express Path — `docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md` (Spec B) § "Phase 2 — Editable graph + save" + locked decisions 5, 6

<domain>
## Phase Boundary

**This phase delivers ONLY Phase 2 of Spec B** — the editable node editor, save persistence, version history, and optimistic-locking conflict resolution. The engine continues to execute linear-only graphs; branching execution is Phase 3.

What ships:

1. **Editable canvas.** Users can drag nodes from a left-rail palette onto the React Flow canvas (Phase 109 shipped the canvas in read-only mode). Users can connect nodes by dragging from one node's output handle to another's input handle. Clicking a node opens a right-side properties drawer with a Zod-driven form to edit `label` and per-kind `config`.

2. **Save persistence.** A new `PUT /workflows/templates/{id}` endpoint accepts `graph_nodes` + `graph_edges` + `graph_layout` and persists them. Save creates a new row in a new `workflow_template_versions` table (auto-incrementing `version_number`, `parent_version_id` pointing at prior version, `saved_by_user_id` from auth context, optional `comment`). `workflow_templates.current_version_id` is updated to point at the new row. Version rows are never deleted.

3. **Run-time pinning.** When a workflow execution starts, `start_workflow_execution()` reads `template.current_version_id` and writes it to `workflow_executions.template_version_id`. The engine executes the pinned version. Mid-flight edits to the template do not affect the running execution.

4. **Version history UI.** Editor toolbar has a version selector dropdown listing recent versions. A "View History" pane lists all versions with timestamp + saved_by + comment. "Revert to version X" creates a NEW version (never overwrites or deletes).

5. **If-Match optimistic locking.** Every `GET /workflows/templates/{id}` response includes the current version's `updated_at` in an `ETag` HTTP header. Every `PUT /workflows/templates/{id}` requires an `If-Match: <etag>` header. Server compares and returns `412 Precondition Failed` with the latest version's body on mismatch. The editor catches 412 and surfaces a conflict modal with three buttons: View their changes / Overwrite / Cancel.

6. **Validation (rules 1, 2, 3, 6, 7).** Client + server validate: exactly one trigger node (rule 1), every node reachable from trigger (rule 2), no cycles in directed graph (rule 3), at least one output node (rule 6), each node's `config` passes its per-kind Zod schema (rule 7). Failed validation renders red badges on offending nodes; Save is blocked. New endpoint: `POST /workflows/templates/{id}/validate` returns `{ errors: [{ node_id, message }, ...] }`.

7. **Edit button rewires to editable editor.** Phase 109 already rewired the Edit button on `/dashboard/workflows/templates` cards to point at `/dashboard/workflows/editor/[templateId]`. This phase swaps the page contents from read-only viewer to editable canvas while keeping the same route.

What does NOT ship in this phase (deferred to Phase 3-4):

- **Branching engine.** A `condition` node saves but does NOT execute conditionally yet — the engine still walks the graph as if linear. Phase 3 adds the branching graph_executor.
- **Validation rules 4 and 5.** Condition outgoing degree (rule 4) and parallel/merge pairing (rule 5) are Phase 3 (condition) and Phase 4 (parallel/merge) — adding a `condition` node in Phase 2 saves without those structural enforcements.
- **Dual-tab condition expression UX.** The Guided/Advanced JSONLogic tabs are Phase 3 — for now the `ConditionNode` properties drawer shows a placeholder ("Condition logic coming in Phase 3") and saves an empty expression.
- **Parallel, merge, human-approval node kinds.** Their visual nodes can be dragged from the palette but executing them is Phase 4. (Decision pending in planning: do we hide them from the palette in Phase 2, or show them with "Phase 4 — not yet executable" labels? See Claude's Discretion below.)
- **Test-run button + cost modal.** The "Test" button with cost estimate modal is Phase 3+. Phase 2 lets users save but not test from the editor.
- **Cycle detection at engine start.** Phase 4 adds engine-time cycle rejection. Phase 2 catches cycles via the save-time client + server validator only.
- **Sub-workflow nodes, loops, custom node kinds.** Out of scope for Spec B entirely (Spec C+).

</domain>

<decisions>
## Implementation Decisions

All six Spec B decisions were locked 2026-05-11. The four relevant to Phase 2:

### Decision 1 — Condition expression authoring UX (Guided + Advanced tabs)

Phase 3 work primarily. Phase 2 only needs to make the `ConditionNode` selectable from the palette and savable with placeholder config. The Zod schema for `ConditionConfig` should accept an empty `expression` field temporarily so saves don't fail; Phase 3 will tighten this to require a JSONLogic value.

### Decision 3 — Per-user scope (private templates)

`workflow_templates.owner_user_id` is the scope key (already exists from prior work). Seeded templates have `owner_user_id = NULL` and are treated as read-only global seeds. **Critical for Phase 2:** clicking Edit on a seeded template must NOT mutate the seed row. Instead, it should create a private copy in the current user's `owner_user_id` and redirect to that copy's editor URL. The new copy becomes the user's editable working version; the seed stays pristine.

### Decision 5 — Version rows (every Save creates a new version) — LOAD-BEARING for Phase 2

Two-table data model:

```sql
-- existing table, repurposed as a "current version pointer"
CREATE TABLE workflow_templates (
  id              UUID PRIMARY KEY,
  owner_user_id   UUID NOT NULL,
  name            TEXT NOT NULL,
  category        TEXT,
  current_version_id UUID NOT NULL REFERENCES workflow_template_versions(id),
  created_at      TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ,
  -- legacy: steps, graph_nodes, graph_edges, graph_layout kept until cleanup migration
);

-- new table: every Save creates a row here
CREATE TABLE workflow_template_versions (
  id                 UUID PRIMARY KEY,
  template_id        UUID NOT NULL REFERENCES workflow_templates(id),
  version_number     INT NOT NULL,           -- 1, 2, 3, ... per template
  parent_version_id  UUID REFERENCES workflow_template_versions(id),
  graph_nodes        JSONB NOT NULL,
  graph_edges        JSONB NOT NULL,
  graph_layout       JSONB,
  saved_by_user_id   UUID NOT NULL,
  saved_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  comment            TEXT,                    -- optional save message
  UNIQUE (template_id, version_number)
);
```

**Migration approach:** Phase 110 migration must (a) create `workflow_template_versions`, (b) backfill every existing `workflow_templates` row by creating a `version_number = 1` row with the row's current `graph_nodes`/`graph_edges`/`graph_layout` (already populated by Phase 109's eager projection), (c) add `current_version_id` column to `workflow_templates` and set it to the backfilled v1 row, (d) leave the legacy `graph_*` columns on `workflow_templates` untouched (cleanup migration deferred to "Phase 1.5 / 2.5 cleanup" — out of scope).

**Run-time pinning:** `workflow_executions.template_version_id` (UUID) is added by this migration. `start_workflow_execution()` reads `template.current_version_id` and writes it to this new column. Existing in-flight executions are unaffected.

**UI:**
- Version selector dropdown in editor toolbar (top-right area).
- "View History" pane: full version list with timestamp, saved_by user name, comment, and "Revert" button.
- Revert creates a new version (`version_number = max + 1`) with `parent_version_id` pointing to the version being reverted to, and `graph_*` fields copied from that version.

**Storage cost:** ~10kb per version × hundreds of versions per active user = bounded. GC: a future cron archives versions older than 90 days with no active run-pin references. Phase 110 does NOT implement GC.

### Decision 6 — If-Match optimistic locking (from v1) — LOAD-BEARING for Phase 2

Implementation:
- `GET /workflows/templates/{id}` response sets `ETag: <quoted updated_at ISO8601>` header (e.g. `ETag: "2026-05-11T19:30:00.000Z"`).
- `PUT /workflows/templates/{id}` requires `If-Match: <etag>` header. Missing → 428 Precondition Required. Stale → 412 Precondition Failed with the current version body in the response (so the client can show "their changes").
- Frontend: every `getTemplate` call stores the returned ETag; every `saveTemplate` sends it back. On 412, the editor surfaces the conflict modal.

**Server logic:** `WHERE updated_at = ?` clause on the UPDATE statement (single round-trip optimistic check). On mismatch (0 rows affected), refetch and return 412 with the fresh body.

**Frontend conflict modal** has three buttons:
1. **View their changes** — loads the latest version into the canvas, discarding local edits.
2. **Overwrite** — re-sends the PUT with the new ETag (winning the race; their changes lost). Confirms with a secondary prompt to avoid accidental overwrites.
3. **Cancel** — closes the modal, local state preserved, user can copy-paste their work elsewhere before reloading.

### Claude's Discretion

Areas where Spec B is intentionally light, leaving choices to the planner:

1. **Palette UI structure.** Left rail vs right rail vs floating; categorized (Triggers / Actions / Logic / Output) or flat. Spec B says "left rail: drag sources" — defer styling and categorization to planner.

2. **Properties drawer scope per node kind in Phase 2:**
   - `trigger`, `agent-action`, `output` — fully editable (label + config) since these execute today.
   - `condition`, `parallel`, `merge`, `human-approval` — Phase 2 must decide:
     - **Option A:** Hide from palette entirely until Phase 3-4 lands.
     - **Option B:** Show in palette with greyed/disabled appearance and a tooltip "Available in Phase 3" / "Available in Phase 4".
     - **Option C:** Allow drag + save with placeholder config; engine ignores them (won't execute) but they're visually present.
   - Recommend Option C — lets users sketch future workflows without re-doing the work when Phase 3-4 ships.

3. **Save UX detail:** auto-save on edit vs explicit Save button. Recommend explicit Save button — clearer mental model + bounded version row generation.

4. **Validation feedback positioning.** Red badges on offending nodes (per spec) + a top-of-canvas validation summary banner with per-error click-to-jump? Or just node badges? Planner's call.

5. **Version comment UX.** Modal on Save asking for an optional commit message vs auto-generated comments (e.g. "Saved at 14:32"). Recommend optional modal that defaults to blank — keep friction low.

6. **Backend version-row creation transactionality.** Versions must be created atomically with `current_version_id` update. Use a Postgres function or a transaction in `WorkflowEngine.save_template_version`. Planner's call on the abstraction.

7. **Frontend state management for canvas dirty tracking.** Existing project conventions (Zustand store? React Query? local component state?). Planner should grep the frontend for existing patterns and match.

8. **Edit-on-seed UX:** when a user clicks Edit on a global seed template (`owner_user_id IS NULL`), the system creates a copy. The copy URL should be the new template's ID, not the seed's. Should the user see a brief "Created a copy of [seed name]" toast? Recommend yes.

</decisions>

<specifics>
## Specific References from Spec B

### Architecture diagram (Spec B § Architecture)

```
USER (canvas, non-technical)
    │ drag, connect, configure, save
    ▼
frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx  [exists, swap from read-only to editable]
+ frontend/src/components/workflows/editor/
    NodeCanvas.tsx                        [exists from Phase 109 — wire in drag/connect handlers]
    NodePalette.tsx                       [NEW: left rail drag sources]
    NodePropertiesDrawer.tsx              [NEW: right rail per-node form]
    nodes/{Trigger,AgentAction,Output}Node.tsx  [exist from Phase 109]
    nodes/{Condition,Parallel,Merge,HumanApproval}Node.tsx  [NEW: visual only, no execution]
    useGraphSchema.ts                     [NEW: Zod schema per node kind]
    useGraphValidation.ts                 [NEW: client cycle/reachability detection]
    │
    │ PUT /workflows/templates/{id}
    ▼
app/routers/workflows.py
    • new endpoint: PUT /templates/{id}                  [NEW]
    • new endpoint: POST /templates/{id}/validate        [NEW]
    • existing GET /templates includes ETag header       [extend]
    │
    ▼
app/workflows/registry.py
    • WorkflowTemplate.current_version_id: UUID          [NEW column]
    • WorkflowTemplateVersion model                      [NEW row type]
    • WorkflowEngine.save_template_version()             [NEW method]
    │
    ▼ (on start_workflow_execution)
app/workflows/engine.py
    • Reads template.current_version_id                  [extend]
    • Writes workflow_executions.template_version_id     [extend]
    • Execution logic unchanged (still linear-only)
```

### File paths grounded in current codebase (post-Phase 109)

**Backend (already on disk):**
- `app/routers/workflows.py` — `WorkflowTemplateResponse` Pydantic model lives here (NOT in `registry.py` per Phase 109 deviation #1). Endpoints: `GET /workflows/templates`, `GET /workflows/templates/{id}`. Phase 2 must add `PUT /workflows/templates/{id}` and `POST /workflows/templates/{id}/validate` here too.
- `app/workflows/engine.py` — `WorkflowEngine.list_templates()` SELECT was widened in Phase 109 to read `graph_nodes/edges/layout`. Phase 2 needs to add `save_template_version()` and update `start_workflow_execution()` for version pinning. Execution logic itself must NOT be touched in Phase 2 — that's Phase 3.
- `app/workflows/registry.py` — workflow factory registry; not the response model. Phase 2 may add a `WorkflowTemplateVersion` Pydantic model here or in a new file.
- `supabase/migrations/20260601000000_workflow_template_graph_projection.sql` — Phase 109 migration. Phase 2's migration must be dated after this (e.g., `20260615000000_workflow_template_versioning.sql`).

**Frontend (already on disk):**
- `frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx` — route param is `[templateId]`, NOT `[id]` (Phase 109 deviation #1). Currently renders read-only `NodeCanvas`. Phase 2 swaps to editable.
- `frontend/src/components/workflows/editor/NodeCanvas.tsx` — React Flow wrapper. Module-scope `NODE_TYPES`, useMemo over `graph_nodes`. Phase 2 must wire `onNodesChange`, `onEdgesChange`, `onConnect`, drag-from-palette drop handler.
- `frontend/src/components/workflows/editor/nodes/{Trigger,AgentAction,Output}Node.tsx` — exist. Phase 2 adds the missing 4: `ConditionNode`, `ParallelNode`, `MergeNode`, `HumanApprovalNode` (visual-only, see Claude's Discretion #2).
- `frontend/src/services/workflows.ts` — canonical service path (NOT `frontend/src/lib/api/workflows.ts` per Phase 109 deviation). Already exports `GraphNode`, `GraphEdge`, `NodePosition`, `NodeKind` (7-variant Literal). Phase 2 adds `saveTemplate(id, graph, etag, comment?)`, `validateTemplate(id, graph)`, `getTemplateHistory(id)`, `revertTemplate(id, versionId)`.
- `frontend/src/components/workflows/WorkflowTemplateCard.tsx` — Edit button already routes to `/dashboard/workflows/editor/[templateId]`. Phase 2 needs no change here.

### Data shape gotchas inherited from Phase 109

- **On-disk shape is nested `phases[].steps`, NOT flat `steps`.** Phase 109's `pikar.flatten_phases_to_steps` SQL adapter bridges this; the React Flow fallback projection mirrors it. Phase 2's editable canvas reads from `graph_nodes`/`graph_edges` (already populated post-109 backfill), so the nested-vs-flat shape shouldn't recur — but if save logic ever needs to write back to legacy `steps`, the same adapter applies.
- **`WorkflowEngine.list_templates()` does explicit SELECT.** Phase 109 widened it for graph fields. Phase 2's version-pinning logic needs `current_version_id` added to that SELECT, plus a JOIN or separate fetch of `workflow_template_versions` to retrieve the actual graph data being executed.

### Validation rules to enforce in Phase 2 (Spec B § Validation contract)

Rules 1, 2, 3, 6, 7 only. Rules 4 and 5 are deferred:

1. **Single trigger.** Exactly one node has `kind: 'trigger'` and zero incoming edges.
2. **Reachability.** Every node is reachable from the trigger via directed edges.
3. **No cycles.** Topological sort succeeds (DAG-only).
6. **At least one output.** At least one node has `kind: 'output'`.
7. **Properties valid.** Each node's `config` passes its per-kind Zod schema.

### Branch context

- Current branch: `plan-109-spec-b-phase-1` (will be renamed/forked for Phase 110 work).
- Phase 109 shipped on this branch; 18 commits including all 3 plan summaries + ROADMAP entries + VERIFICATION.md.
- **Branch pollution risk:** Parallel GSD automation has caused branch switching mid-session multiple times. Phase 110 work must `git branch --show-current` before every commit; if drifted, switch back. (Memory note: `project_branch_pollution_2026_05_09.md`, `project_workflow_node_editor_phase1.md`.)

### Dependencies to add

- Backend: none new (json-logic-py is deferred to Phase 3).
- Frontend: none new beyond Phase 109's `@xyflow/react ^12.10.2`. Optional consideration: a Zod resolver helper for the properties drawer forms (likely `@hookform/resolvers` if not already present — planner to grep).

### Cost vs effort

Spec B § "Effort estimate" puts Phase 2 at ~5 calendar weeks (4.5 engineering weeks). +1.5 weeks vs original draft for versioning (decision 5), +0.5 weeks for If-Match (decision 6). Dominant work is versioning UI + backend persistence; React Flow editing itself is mostly off-the-shelf.

</specifics>

<deferred>
## Deferred Ideas

From Spec B Phase 2 spec, explicitly NOT in this phase:

- **Branching execution** — Phase 3 (`app/workflows/graph_executor.py`, JSONLogic eval, condition routing, parallel/merge execution)
- **Dual-tab condition expression UX** — Phase 3 (Guided form + Advanced JSON tabs)
- **Test-run button + cost estimation modal** — Phase 3+ (real-cost runs, sum of `cost_table.py` entries)
- **Parallel + merge + human-approval execution** — Phase 4 (asyncio.gather, asyncio.wait, Spec A approval endpoint integration)
- **Validation rules 4 & 5** — Phase 3 (condition outgoing degree) + Phase 4 (parallel/merge pairing)
- **Cycle detection at engine start** — Phase 4 (Phase 2 catches at save-time only)
- **Mobile-first editor** — Spec C+ (mobile gets read-only graph view from Phase 109)
- **Multi-user collaborative editing** — Spec C+ (Phase 2 is single-user-at-a-time, last-save-wins modulo If-Match)
- **User-defined custom node kinds** — Spec C+ (Phase 2 ships fixed 7-kind palette, frozen by Phase 109's NodeKind Literal)
- **Loops / iteration nodes** — Spec C+ (DAG-only in v1)
- **Sub-workflow nodes** — Spec C+ (reuse via copy-paste template only)
- **Cleanup migration** — Phase 2.5 or later (drop legacy `graph_nodes`/`graph_edges`/`graph_layout`/`steps` columns from `workflow_templates` once `workflow_template_versions` is fully canonical)
- **Version row garbage collection** — Future spec (90-day-old archive cron with no run-pin reference)
- **Template marketplace / sharing across users** — Spec C+ (Phase 2 is per-user private; seeds are global read-only)
- **Migrating WorkflowTimelineWidget to graph layout** — Spec C+ (linear timeline stays; Spec A's widget unchanged)

</deferred>

---

*Phase: 110-workflow-node-editor-editable*
*Context gathered: 2026-05-11 via PRD Express Path*
*Source: `docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md` (Spec B) § Phase 2 + locked decisions 5, 6*
