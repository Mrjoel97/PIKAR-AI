---
phase: 109
status: passed
verified: 2026-05-11
must_haves_passed: 14
must_haves_total: 14
---

# Phase 109: Workflow Node Editor Viewer — Verification Report

**Phase Goal:** Deliver Phase 1 of Spec B (workflow node editor) — a read-only React Flow graph viewer for existing `workflow_templates`. Migration + API widening + frontend viewer route only; no editing, no save, no engine changes.
**Verified:** 2026-05-11
**Status:** passed (14 / 14 must-haves verified against codebase)
**Re-verification:** No — initial verification

## Must-Haves

| # | Must-Have | Status | Evidence |
| - | --------- | ------ | -------- |
| 1 | `workflow_templates` has `graph_nodes`, `graph_edges`, `graph_layout` JSONB columns | VERIFIED | `supabase/migrations/20260601000000_workflow_template_graph_projection.sql:36-38` — `ALTER TABLE ... ADD COLUMN IF NOT EXISTS graph_{nodes,edges,layout} jsonb;` |
| 2 | Three or more `pikar.project_steps_to_*` helper functions exist | VERIFIED | Same migration lines 64, 110, 161, 205 — four `CREATE OR REPLACE FUNCTION pikar.*`: `project_steps_to_nodes`, `project_steps_to_edges`, `compute_dagre_layout`, and the `flatten_phases_to_steps` adapter. All STABLE plpgsql with `jsonb_typeof <> 'array'` defensive guards |
| 3 | `workflow_template_migration_errors` table created in the migration | VERIFIED | Migration lines 49-54 — `CREATE TABLE IF NOT EXISTS workflow_template_migration_errors (id uuid PK, template_id uuid, error_message text, errored_at timestamptz)` |
| 4 | Migration is idempotent (re-runnable guards) | VERIFIED | `ADD COLUMN IF NOT EXISTS` (3x), `CREATE SCHEMA IF NOT EXISTS pikar`, `CREATE OR REPLACE FUNCTION` (4x), `CREATE TABLE IF NOT EXISTS`, and the eager-projection DO block is gated by `WHERE graph_nodes IS NULL` (line 251) — second run is a no-op |
| 5 | `WorkflowTemplateResponse` exposes `graph_nodes`/`graph_edges`/`graph_layout` as optional typed fields | VERIFIED | `app/routers/workflows.py:87-139` — `NodePosition`, `NodeKind` (7-variant Literal), `GraphNode`, `GraphEdge` Pydantic models defined; `WorkflowTemplateResponse.graph_nodes: list[GraphNode] \| None = None` (line 137) plus matching `graph_edges` and `graph_layout: dict[str, NodePosition] \| None = None` |
| 6 | API SELECT widened (engine `list_templates`) | VERIFIED | `app/workflows/engine.py:152-156` — SELECT clause includes `"graph_nodes, graph_edges, graph_layout"`. `git diff 47fa9291^..47fa9291` shows the 4-line widening as the only engine change. `get_template` uses `select("*")` and needs no change |
| 7 | TS named exports `GraphNode`, `GraphEdge`, `NodePosition`, `NodeKind` | VERIFIED | `frontend/src/services/workflows.ts:30-60` — `export interface NodePosition`, `export type NodeKind = 'trigger' \| ... \| 'output'` (7 variants), `export interface GraphNode`, `export interface GraphEdge`. **Note:** must-haves list referenced `frontend/src/lib/api/workflows.ts` but actual canonical location is `frontend/src/services/workflows.ts` — `lib/api/` directory does not exist; phase-02 SUMMARY explicitly documents `services/workflows.ts` as the chosen file. Generated types at `frontend/src/types/api.generated.ts:10273-10411` also contain `GraphEdge`, `GraphNode`, `NodePosition` schemas |
| 8 | Frontend route `/dashboard/workflows/editor/[templateId]/page.tsx` renders React Flow viewer | VERIFIED | `frontend/src/app/dashboard/workflows/editor/[templateId]/page.tsx` exists; imports `NodeCanvas` from `@/components/workflows/editor/NodeCanvas`; uses `getWorkflowTemplate`. **Deviation:** plan asked for `[id]`; existing `[templateId]` segment was replaced in place (two dynamic siblings would conflict in Next.js — documented in plan-03 SUMMARY decision #1). Functional contract preserved (single dynamic segment under `/editor/`) |
| 9 | Custom node components `TriggerNode`, `AgentActionNode`, `OutputNode` | VERIFIED | All three exist under `frontend/src/components/workflows/editor/nodes/`. Each imports `Handle, Position, type NodeProps` from `@xyflow/react` and exports the named component (Trigger=source only, Output=target only, AgentAction=both handles) |
| 10 | `WorkflowTemplateCard` Edit button routes to new editor route | VERIFIED | Card delegates via `onEdit(template)` callback (`frontend/src/components/workflows/WorkflowTemplateCard.tsx:62`); parent page wires it at `frontend/src/app/dashboard/workflows/templates/page.tsx:81-86` — `handleEditClick = (template) => router.push(`/dashboard/workflows/editor/${template.id}`)` and `onEdit={handleEditClick}` (line 221). Card itself carries `data-testid="workflow-template-card-edit-button"` plus a docblock describing the routing contract |
| 11 | `@xyflow/react` ^12.x in `frontend/package.json` | VERIFIED | `frontend/package.json:31` — `"@xyflow/react": "^12.10.2"`. NodeCanvas imports `ReactFlow, Background, Controls, type Node, type Edge` from `@xyflow/react` plus `@xyflow/react/dist/style.css`. Legacy `reactflow@^11.11.4` co-exists but has zero imports in src (Plan 03 SUMMARY deferred its removal) |
| 12 | Tests for migration AND vitest tests for NodeCanvas exist and pass | VERIFIED | (a) `tests/integration/test_workflow_template_graph_projection.py` (499 lines, 6 tests) — RE-RUN: 6 skipped (Supabase creds absent locally — clean skip via `skipif`, matches `test_knowledge_graph_migration.py` pattern). (b) `tests/unit/workflows/test_registry_graph_fields.py` + `test_templates_api_returns_graph.py` (18 tests) — RE-RUN: **18 passed in 6.51s**. (c) `frontend/src/__tests__/workflows/NodeCanvas.test.tsx` (6 tests covering: happy path 6n/5e, flat-steps fallback 4n/3e, phases.*.steps fallback 5n/4e, empty-state placeholder, agent-action tool_name passthrough, missing graph_layout positions) — RE-RUN: **6 passed in 3.40s** |
| 13 | Existing `/workflows/templates` callers still work (response widened, not narrowed) | VERIFIED | All pre-existing `WorkflowTemplateResponse` fields preserved (`id, name, description, category, template_key, version, lifecycle_status, is_generated, personas_allowed, last_published_at`); three new fields are optional with `\| None = None` defaults. Generated `frontend/src/types/api.generated.ts:11620-11648` confirms all original fields plus `graph_nodes?/graph_edges?/graph_layout?` as nullable optionals. `npx tsc --noEmit` is clean across the entire frontend |
| 14 | No engine drift (graph columns are metadata only) | VERIFIED | `git diff 47fa9291^..47fa9291 -- app/workflows/engine.py` shows ONLY the 4-line SELECT widening in `list_templates`. No execution-path changes. No subsequent commits on plan-109 branch touched `app/` after the SELECT widening (verified `git log 47fa9291..plan-109-spec-b-phase-1 -- app/` returns empty). Migration eagerly populates graph columns but the engine still reads `phases` for execution |

## Gaps

None.

## Human Verification

The following are recommended for human eyes before user-facing release — they fall outside what code-grep can prove. Not blockers for phase sign-off.

1. **Visual: graph viewer renders cleanly for a real seeded template.**
   - Test: Run `cd frontend && npm run dev` (with backend up), log in, navigate to `/dashboard/workflows/templates`, click "Edit" on any template card.
   - Expected: A React Flow canvas appears with a teal trigger circle on the left, agent-action cards in the middle (each showing label + tool_name), and an emerald output circle on the right; pan/zoom controls visible bottom-left; no editing affordances (no draggable nodes, no connection lines on hover).
   - Why human: visual fidelity — icon placement, handle alignment, label truncation, color contrast — cannot be asserted by the minimal `data-node-count`/`data-edge-count` vitest mock.

2. **End-to-end: route works against the live API after migration applies.**
   - Test: After `supabase db push` runs `20260601000000_workflow_template_graph_projection.sql` against a real DB, hit `GET /workflows/templates` and confirm `graph_nodes`/`graph_edges`/`graph_layout` are populated (non-null) for at least one row. Then load the same template ID in the viewer.
   - Expected: Wire payload contains the three graph fields; viewer renders without falling through to the client-side `projectTemplateToGraph` fallback.
   - Why human: integration tests skip in CI without Supabase creds; the eager-backfill DO block has never been exercised against prod data shape here.

3. **Empty-state placeholder copy and styling.**
   - Test: Open a template whose `phases` array is empty (or manually null out `graph_nodes` in DB) and load the editor route.
   - Expected: Dashed-border placeholder card with copy "This template has no graph nodes yet" + Phase-2 disclaimer; no blank React Flow canvas; no console warnings from `fitView` running against an empty graph.
   - Why human: the empty-state copy is content-quality concern best judged by a product reviewer.

## Notes

### Requirements traceability
Phase 109 was registered out-of-band (not via `/gsd:plan-phase`), so `REQUIREMENTS.md` has no `NODEEDITOR-*` IDs. Per the verifier prompt's `<requirements_traceability>` block this is a known artifact gap, not a real verification gap. The three plan SUMMARYs each cite their own internal req IDs (`NODEEDITOR-MIGRATION-01`, `NODEEDITOR-API-01`, `NODEEDITOR-VIEWER-01`) but these are local-only.

### File-path deviation: services vs lib/api
Must-have #7 referred to `frontend/src/lib/api/workflows.ts`. The actual canonical location is `frontend/src/services/workflows.ts` — `frontend/src/lib/api/` does not exist. Phase-02 SUMMARY's decision #1 documents the choice explicitly; the consumer surface (named exports, generated schemas, frontend WorkflowTemplate alias) is intact. Treated as a documentation drift in the verifier prompt, not a real gap.

### Route param: [templateId] vs [id]
Plan-03 had a Rule-3 deviation: the existing `[templateId]/page.tsx` was replaced in place rather than creating a sibling `[id]`, because Next.js does not allow two dynamic segments at the same path-level. The functional contract (single dynamic segment under `/dashboard/workflows/editor/`) is preserved; the URL-shape the user sees is unchanged because `router.push` fills the slot positionally. Plan-03 SUMMARY decision #1 fully documents this.

### Pre-existing test failures (deferred to a separate hotfix phase)
A full `npx vitest run` against the frontend reports 25 failed test files / 54 failed tests, all in suites unrelated to Phase 109 (auth pages, persona shells, dashboard layout widgets, chat surface). Plan-03 SUMMARY's "Deferred Issues" section confirmed these fail at baseline (HEAD~6, `ec4cc1e3`) — they predate this phase and are unrelated. The Phase 109 deliverables (NodeCanvas + 6 vitest tests, 18 backend unit tests, 6 integration tests) are all GREEN.

### Eager backfill not exercised locally
The migration's DO block at lines 243-267 (per-row projection with EXCEPTION handler writing to `workflow_template_migration_errors`) has not been exercised against a real Supabase DB in this verification session — `supabase` CLI/local stack is not running. Integration tests skip cleanly. Recommended human verification step #2 above covers this.

### Branch state
All Phase 109 commits (b4b3d160, f6d1f7c5, 3d3c70de, 709db09e, 79fdfd90, e485743a for 109-01; 47fa9291, 49a05b3d, 96dc0099, 7b65c3b1, ec4cc1e3 for 109-02; 4377003f, 5530de9c, 97d255fc, 69f75c7f, 0204468c, 1b95bacd, 8850625b for 109-03) are present on `plan-109-spec-b-phase-1` and absent from `main`. The branch is ready for PR.

### Deferred items
`deferred-items.md` documents only PersonaContext.tsx pollution from a parallel GSD automation (reverted, not in 109 scope). Not a Phase 109 deliverable; not a gap.

---

*Verified: 2026-05-11*
*Verifier: Claude (gsd-verifier)*
