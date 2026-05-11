# Phase 111: Workflow Node Editor — Phase 3 (Branching Execution + Condition UX) — Context

**Gathered:** 2026-05-12
**Status:** Ready for planning
**Source:** PRD Express Path — `docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md` (Spec B) § "Phase 3 — Branching execution (4 weeks)" + locked decision 1 (dual-tab condition expression UX)

<domain>
## Phase Boundary

**This phase delivers ONLY Phase 3 of Spec B** — branching execution, condition node UX, validation rule 4, and live-run rendering for branched workflows. Parallel/merge/human-approval execution stays deferred to Phase 4.

What ships:

1. **New backend codepath: `app/workflows/graph_executor.py`.** Sits alongside the existing linear step_executor. `WorkflowEngine.execute()` dispatches to one or the other based on whether the template's `graph_nodes` contains any non-linear node kinds (specifically `condition` in Phase 3; later phases will trigger on `parallel`/`merge`/`human-approval`).

2. **JSONLogic evaluation.** `json-logic-py` library added as a backend dep. `condition` nodes evaluate their `config.expression` (a JSONLogic JSON document) against an execution context dict `{previous_outcomes, current_step, user_context}`. Result is truthy/falsy; engine routes to the outgoing edge whose `source_handle` matches (`'true'` or `'false'`).

3. **Dual-tab condition properties UX.** The `ConditionNode` properties drawer in the editor (which currently shows a "Coming in Phase 3" placeholder from Phase 110) gets replaced by a tab switcher:
   - **Guided** (default) — three dropdowns: `[Field selector] [Operator] [Value]`. Field selector lists named outputs from previous nodes (computed from the upstream subgraph at edit time). Operator list is `==`, `!=`, `<`, `<=`, `>`, `>=`, `contains`, `in`, `not in`. Saving translates this to JSONLogic JSON behind the scenes.
   - **Advanced (JSON)** — raw JSONLogic editor with syntax highlighting (use a lightweight code editor — likely Monaco or CodeMirror; spec doesn't pin one; planner decides).
   - **Round-trip rule:** if an Advanced edit cannot translate cleanly back to the Guided form (e.g., nested logic, multiple operators), the Guided tab becomes read-only and shows "Complex expression — edit in Advanced tab."

4. **Validation rule 4 (client + server).** A `condition` node MUST have exactly 2 outgoing edges with `source_handle` values forming the set `{'true', 'false'}`. Enforced in `app/workflows/graph_validation.py` (server) and `useGraphValidation.ts` (client). New fixture cases added to `tests/fixtures/graph_validation_cases.json` and parametrized in both pytest and vitest.

5. **`WorkflowGraphRunWidget` (new frontend widget).** Renders branched workflow runs as a live React Flow graph: currently-executing node has an active visual (pulsing border), the taken edge from a condition node is highlighted, the not-taken edge is muted, not-yet-reached nodes are at reduced opacity. Reuses Spec A's existing SSE event bus and `OutcomeWriter` — no backend wire-format changes.

6. **Workspace auto-widget routing.** The workspace's run-widget picker chooses `WorkflowGraphRunWidget` for runs whose template has non-linear nodes, and continues to route linear runs to the existing `WorkflowTimelineWidget` (no regression).

What does NOT ship in this phase (deferred to Phase 4):

- **Parallel + merge + human-approval execution.** Their visual nodes exist (Phase 110, Option C) and save without exec; Phase 4 adds the asyncio.gather/wait orchestration + Spec A approval-endpoint integration.
- **Validation rule 5 (parallel/merge pairing).** Still stubbed in `graph_validation.py` (raises NotImplementedError only on `strict=True`).
- **Engine-time cycle detection.** Phase 110 catches cycles at save time (rule 3); Phase 111 does NOT add engine-side cycle rejection. Phase 4 will add a topological-sort precondition in `graph_executor.py` for defense in depth.
- **Test-run button + cost modal.** Deferred to Phase 3+ per Spec B locked decision 2 — but the spec puts the Test button under Phase 3's umbrella. **Decision pending:** does Phase 111 include the Test button? Recommend NO — see Claude's Discretion #1 below; keep Phase 111 scoped tight.
- **Per-version preview that loads v3's graph.** Phase 110's I-2 scope reduction. Phase 111 does NOT add the `GET /templates/{id}/versions/{vid}` endpoint either (still deferred).
- **Mobile-first editor UX.** Out of Spec B v1.
- **Loops, sub-workflows, custom node kinds, multi-user co-editing.** Out of Spec B v1.

</domain>

<decisions>
## Implementation Decisions

The six Spec B decisions were locked 2026-05-11. The two relevant to Phase 3:

### Decision 1 — Condition expression authoring UX (Guided + Advanced tabs) — LOAD-BEARING for Phase 3

The `ConditionNode` properties drawer ships with both a Guided form and an Advanced JSON tab, with tab toggle.

- **Guided tab (default).** Three dropdowns: `[Field selector] [Operator] [Value]`.
  - **Field selector** lists named outputs from previous nodes. The set of fields is computed by walking the upstream subgraph from the current `condition` node and collecting `agent-action` node outputs. Each output is named by `{node_id}.{outcome_key}` (the outcome keys come from Spec A's `outcome_text` shape — they're free-form strings, so the Guided form must let the user type a custom key as well, or just expose the raw outcome dict keys; planner decides).
  - **Operator** dropdown: `==`, `!=`, `<`, `<=`, `>`, `>=`, `contains`, `in`, `not in`.
  - **Value** is a typed input (string / number / boolean autodetected from operator + field type).
  - **Save translation:** the form produces JSONLogic JSON. E.g., `[lead_score] [>] [80]` → `{">": [{"var": "lead_score"}, 80]}`. The translator function lives client-side; the server stores the JSONLogic JSON as-is.

- **Advanced (JSON) tab.** Raw JSONLogic editor. Use a lightweight code editor (Monaco, CodeMirror, or even a textarea with manual `JSON.parse` validation). Show syntax highlighting if practical; don't block on it. Show a "Test expression" button that evaluates against a small set of synthetic context inputs (planner can defer this if it pushes scope).

- **Round-trip rule.** When the user switches Guided → Advanced, the current Guided form translates to JSONLogic and pre-populates the Advanced editor. When the user switches Advanced → Guided, we attempt to parse the JSONLogic back into the three-dropdown shape. If parsing fails (nested operators, unsupported logic constructs), the Guided tab becomes read-only and shows the message "Complex expression — edit in Advanced tab."

- **UAT criterion (ROADMAP success #4):** a non-technical user can build "if revenue > 50000 then escalate" using only the Guided tab in under 60 seconds. The Guided form must produce `{">": [{"var": "revenue"}, 50000]}`.

### Decision 4 — Eager migration (carried over from Phase 110)

Already shipped. Phase 109 + 110 backfilled every template's `graph_nodes`/`graph_edges`/`graph_layout`. Phase 111 inherits a world where every template has a graph representation; no new migration needed for the engine work.

### Reused from Phase 110: per-user scope (decision 3), version pinning (decision 5), If-Match concurrency (decision 6)

All three are already wired. Phase 111 doesn't re-litigate. Execution still pins to `template_version_id` from `workflow_executions`.

### Claude's Discretion

Areas where Spec B is intentionally light, leaving choices to the planner:

1. **Scope of the Test-run button.** Spec B § "Save-and-test loop" puts the Test button under decision 7 / future phase work. Spec B Phase 3's locked-decision-2 note says "Clicking Test runs against actual agent backend, costing real LLM tokens." The Phase 3 deliverable list does NOT explicitly include the Test button — but a "save → test → observe live in widget" loop is the implicit promise of Phase 3 to make branching tangible. **Recommend:** ship a Test button in Phase 111 but make it explicit-action (cost modal first), NOT auto-test. Effort: ~0.5 weeks within the existing 4.5 estimate. Planner decides whether to absorb this or push to Phase 3.5/Phase 4 as a separate plan.

2. **JSON editor library for Advanced tab.** Monaco (heavyweight, ~1MB), CodeMirror 6 (medium, ~300KB), or plain `<textarea>` + manual `JSON.parse` validation (free, ugly). Recommend CodeMirror 6 for the balance — light, supports JSON syntax highlighting, good a11y. Planner decides; the spec doesn't pin one.

3. **Operator semantics for "contains" and "in".** JSONLogic has `in` (membership in array or substring in string). "contains" is typically string-contains; "in" is array-membership. The Guided UI could collapse these into one ("in") or keep them separate. Recommend keep both for clarity; translator decides which JSONLogic op to emit based on the value type.

4. **Field selector data source.** Where does the Guided "Field selector" get its list of fields from? Two options:
   - **Option A (static):** every node kind declares a static list of output fields in its Zod schema; the field selector walks the upstream subgraph and collects them.
   - **Option B (dynamic):** read from `workflow_steps.outcome_text` of prior runs of the same template; only fields that have ever appeared in real runs show up.
   - Recommend Option A — deterministic, doesn't depend on run history, lets users build a workflow before any runs exist. Phase 111 may need to extend `useGraphSchema.ts` to declare per-kind output shapes.

5. **Dispatch trigger in `engine.execute()`.** What makes the engine pick `graph_executor` vs `step_executor`? Two options:
   - **Option A:** "any non-linear node kind present in `graph_nodes`" — i.e., scan for `kind in ('condition', 'parallel', 'merge', 'human-approval')`. Future-proof for Phase 4.
   - **Option B:** "any node with multiple outgoing edges sharing the same source" — i.e., look at edge topology instead of node kinds.
   - Recommend Option A — simpler, doesn't change semantics for Phase 4 when more kinds become executable. Document the dispatch helper as `_template_requires_graph_executor(graph_nodes) -> bool`.

6. **`WorkflowGraphRunWidget` placement.** New file under `frontend/src/components/widgets/`? Or under `frontend/src/components/workflows/editor/` to share with the editor's `NodeCanvas`? Recommend `frontend/src/components/widgets/` — widgets are workspace-rendered, editor components are editor-rendered; the widget can import `NODE_TYPES` from the editor module to reuse the 7 visual components.

7. **Active-node visual treatment.** "Pulsing border" is the spec's wording. Concretely: CSS `@keyframes` border animation, or React Flow's built-in `selected` style, or a tailwind animate-pulse class on the node component? Planner decides; visual polish is judgement-call territory.

8. **SSE event shape for branched runs.** Spec A's SSE event bus already streams `workflow_step.started/completed/failed` events with `step_id`. For Phase 111's widget to render the active/taken state, it needs to know which `node_id` is active. **Decision:** map `workflow_steps.node_id` to the graph node UUIDs. Spec A's existing schema already supports a `node_id` field on `workflow_steps` (Phase 109 + 110 used it for graph projection). Phase 111 doesn't need to add new SSE events — just consume the existing stream and re-render.

</decisions>

<specifics>
## Specific References from Spec B

### Architecture (Spec B § Phase 3 + § Architecture diagram)

```
USER builds conditional in Phase 110 editor → saves → starts execution
                                ▼
                  app/workflows/engine.py
                  WorkflowEngine.execute()
                                │
                                ▼
        ┌──────────────────────┴───────────────────────┐
        │ _template_requires_graph_executor(graph)?    │
        └──────────────────────┬───────────────────────┘
                ┌──────────────┴───────────────┐
        no (linear)                          yes (branching)
                ▼                                ▼
   step_executor (existing)         app/workflows/graph_executor.py
   walks steps[] sequentially       [NEW Phase 3]
                                    Topological execution layer:
                                    • For each ready node:
                                        - agent-action → step_executor.execute_one()
                                        - condition → json_logic.eval + pick edge
                                        - output → write final outcome
                                    • Reuses Spec A's OutcomeWriter + WorkspaceItemEmitter
                                    • Reuses workflow_steps + SSE event bus
                                ▼
                  Spec A SSE event stream (UNCHANGED)
                                ▼
    ┌───────────────────────────┴────────────────────────────┐
    │ workspace widget-picker: choose widget by template     │
    └───────────────────────────┬────────────────────────────┘
        ┌───────────────────────┴───────────────────────┐
linear template                                 non-linear template
        ▼                                               ▼
WorkflowTimelineWidget (existing)            WorkflowGraphRunWidget [NEW Phase 3]
unchanged                                    React Flow + live status overlays
```

### File paths grounded in post-Phase-110 codebase

**Backend (already on disk after Phase 110):**
- `app/workflows/engine.py` — has `WorkflowEngine.execute()` (linear), `start_workflow_execution()` (pins template_version_id from Phase 110), `list_templates()` (SELECT widened in Phase 110). Phase 111 adds: `_template_requires_graph_executor()` dispatch helper + calls into new graph_executor module.
- `app/workflows/step_executor.py` — existing linear executor; do NOT modify in Phase 111. Phase 111's graph_executor calls `step_executor.execute_one()` (or its equivalent — planner verifies exact function signature) per agent-action node.
- `app/workflows/template_versions.py` — Phase 110 module; not modified.
- `app/workflows/graph_validation.py` — Phase 110 module; Phase 111 extends with rule 4 implementation (currently stubbed under `strict=True` NotImplementedError).
- `app/routers/workflows.py` — Phase 110 endpoints intact; Phase 111 doesn't add new endpoints (unless the Test-run button choice from Discretion #1 says yes — then `POST /workflows/templates/{id}/test` enters scope).
- `app/workflows/graph_executor.py` — **NEW Phase 111**. Pure async module. Topological execution layer with JSONLogic-driven condition routing.

**Frontend (already on disk after Phase 110):**
- `frontend/src/components/workflows/editor/nodes/ConditionNode.tsx` — Phase 110 visual-only stub. Phase 111: properties drawer logic moves OUT of this file (which is the React Flow node component) into the `NodePropertiesDrawer` component or a sibling `ConditionPropertiesEditor.tsx`.
- `frontend/src/components/workflows/editor/NodePropertiesDrawer.tsx` — Phase 110 drawer host. Phase 111: when the selected node is `condition`, render the dual-tab UX instead of the "Coming in Phase 3" placeholder.
- `frontend/src/components/workflows/editor/useGraphSchema.ts` — Phase 110 per-kind Zod schemas. Phase 111: tighten the `condition` schema from permissive `z.object({}).passthrough()` to `z.object({ expression: z.unknown() }).strict()` (JSONLogic JSON is "unknown" structurally; we validate semantically via json-logic-js at evaluate time).
- `frontend/src/components/workflows/editor/useGraphValidation.ts` — Phase 110 client validator. Phase 111: implement rule 4 (mirrors server's new rule-4 in graph_validation.py).
- `frontend/src/components/widgets/WorkflowGraphRunWidget.tsx` — **NEW Phase 111**.
- `frontend/src/components/widgets/WorkflowTimelineWidget.tsx` — existing; do NOT modify.

**Tests:**
- `tests/fixtures/graph_validation_cases.json` — Phase 110 shared fixture. Phase 111 adds rule-4 cases: `condition_no_outgoing`, `condition_one_outgoing`, `condition_three_outgoing`, `condition_wrong_source_handles`, `condition_valid_two_handles`.
- `tests/unit/workflows/test_graph_validation.py` — Phase 110 pytest suite. Phase 111: new fixture cases auto-parametrize.
- `tests/integration/test_branching_workflow_execution.py` — NEW. Designs a 2-branch conditional, starts execution, asserts the correct branch's `workflow_steps` rows.
- `tests/unit/workflows/test_graph_executor.py` — NEW. Mocks `step_executor.execute_one`, exercises condition routing logic with synthetic context.
- `tests/unit/workflows/test_json_logic.py` — NEW (or inline in test_graph_executor). Sanity test for the json-logic-py dep itself.
- `frontend/src/__tests__/workflows/ConditionPropertiesEditor.test.tsx` — NEW. Tests Guided form, Advanced JSON tab, round-trip rule, save-translation.
- `frontend/src/__tests__/workflows/useGraphValidation.test.ts` — Phase 110 vitest. Phase 111: rule-4 fixture cases auto-parametrize via the shared JSON.
- `frontend/src/__tests__/widgets/WorkflowGraphRunWidget.test.tsx` — NEW. Mocks SSE event stream, asserts active/taken/muted visual states.

### Data shape gotchas inherited from prior phases

- **`workflow_executions.template_version_id` (UUID, Phase 110)** pins the run to a specific version row. graph_executor reads this and fetches the graph from `workflow_template_versions`, NOT from `workflow_templates`.
- **`workflow_executions.template_version` (INT, legacy)** is still preserved alongside. Don't drop, don't read for graph_executor.
- **`workflow_steps.node_id` (TEXT/UUID)** already exists for the linear executor's per-step rows. graph_executor populates it with the graph node UUID for the executed node. Spec A's SSE consumer already keys off this field.
- **Per-row Spec A outcome shape (`outcome_text`)** — free-form text per step. Phase 111's condition evaluator reads from `workflow_steps.outcome_text` (or a parsed/structured equivalent if Phase 110's `OutcomeWriter` exposes one). The execution context's `previous_outcomes` dict is built by collecting all completed `workflow_steps` for this execution and keying by `node_id`.

### Validation rule 4 (Spec B § Validation contract)

> **Condition outgoing degree.** A `condition` node has exactly 2 outgoing edges with `source_handle` values `{'true', 'false'}` (set equality).

Implementation:
- **Server (`graph_validation.py`):** add a `_validate_rule_4_condition_outgoing_degree(nodes, edges)` helper. For each `condition` node, collect outgoing edges, check `len == 2` and `set(handles) == {'true', 'false'}`. Append `ValidationError(rule=4, node_id=..., message=...)` if not. Remove the existing `if strict: raise NotImplementedError` stub for rule 4.
- **Client (`useGraphValidation.ts`):** mirror the algorithm exactly. Same fixture cases drive both.
- **Fixture cases (additions to `graph_validation_cases.json`):**
  - `condition_no_outgoing` — condition node with zero outgoing edges → rule 4 error
  - `condition_one_outgoing` — one outgoing edge → rule 4 error
  - `condition_three_outgoing` — three outgoing edges → rule 4 error
  - `condition_wrong_source_handles` — two outgoing with `{'left', 'right'}` instead of `{'true', 'false'}` → rule 4 error
  - `condition_valid_two_handles` — two outgoing with correct handles → no errors

### Dependencies to add

- **Backend:** `json-logic-py` (~10kb, pure-Python). Pin in `pyproject.toml`; lock in `uv.lock` via `uv sync`.
- **Frontend (Discretion #2):** likely `@codemirror/lang-json` + `codemirror` + `@codemirror/state` + `@codemirror/view` for the Advanced tab — total ~300KB gzipped. OR `monaco-editor` ~1MB if richer features wanted. OR plain `<textarea>` if scope cut.

### Effort estimate (Spec B § "Effort estimate")

Phase 3: 3.5 engineering weeks / 4.5 calendar weeks. +0.5 weeks vs original draft for the guided condition form (decision 1). Dominant work: graph_executor.py (~1.5wk), dual-tab condition UX (~1wk), WorkflowGraphRunWidget (~0.5wk), validation rule 4 (~0.25wk), tests + integration polish (~0.75wk).

### Branch context

- Current branch: `plan-109-spec-b-phase-1` (with two unrelated W3 Section B pollution commits + Phase 110 stashed voice-session change still pending cleanup). Phase 111 work starts here and inherits the polluted history unless the user creates a fresh branch first.
- **Recommendation surfaced to user (end-of-Phase-110 message):** cherry-pick Phases 109+110 onto a fresh branch from `main` before pushing, dropping the pollution commits. Phase 111 work should ideally start on that fresh branch.
- **Branch pollution risk active:** the same parallel automation that polluted the Phase 110 session is presumably still running. Every executor must `git branch --show-current` before every commit; abort + recover if drift detected.

</specifics>

<deferred>
## Deferred Ideas

From Spec B Phase 3 scope, explicitly NOT in this phase:

- **Parallel + merge + human-approval execution** — Phase 4
- **Validation rule 5 (parallel/merge pairing)** — Phase 4
- **Engine-time cycle detection** — Phase 4 (save-time covers it for now)
- **Per-version preview that loads v3's actual graph** — needs `GET /templates/{id}/versions/{vid}` (deferred from Phase 110)
- **`GET /templates/{id}/versions/{vid}`** — out of scope unless we adopt Discretion #1 and add the Test button
- **Multi-user collaborative editing** — Spec C+
- **User-defined custom node kinds** — Spec C+
- **Loops / iteration** — Spec C+
- **Sub-workflow nodes** — Spec C+
- **Mobile-first editor UX** — Spec C+ (mobile gets read-only graph view from Phase 109)
- **Template marketplace / sharing** — Spec C+
- **Migrating WorkflowTimelineWidget to a graph layout** — Spec C+ (linear timeline stays; we add a separate WorkflowGraphRunWidget)

</deferred>

---

*Phase: 111-workflow-node-editor-branching-execution*
*Context gathered: 2026-05-12 via PRD Express Path*
*Source: `docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md` (Spec B) § Phase 3 + locked decision 1*
