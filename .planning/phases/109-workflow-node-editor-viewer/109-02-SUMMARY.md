---
phase: 109-workflow-node-editor-viewer
plan: 02
subsystem: api
tags: [fastapi, pydantic, openapi, typescript, graph-projection, workflow-templates, react-flow]

# Dependency graph
requires:
  - phase: 109-01-graph-projection-migration (shipped 2026-05-11)
    provides: graph_nodes/graph_edges/graph_layout JSONB columns on workflow_templates
provides:
  - WorkflowTemplateResponse.graph_nodes / graph_edges / graph_layout (Pydantic, optional)
  - GraphNode / GraphEdge / NodePosition Pydantic sub-models
  - NodeKind 7-variant Literal union (forward-compat with Spec B Phases 3-4)
  - components.schemas.GraphNode / GraphEdge / NodePosition in api.generated.ts
  - Named TS exports of GraphNode / GraphEdge / NodePosition / NodeKind from frontend/src/services/workflows.ts
  - Engine SELECT widened to read the 3 new columns on list_templates
affects: [109-03-frontend-graph-viewer]

# Tech tracking
tech-stack:
  added: []  # No new deps; pure schema widening on existing stack
  patterns:
    - "Inline Pydantic sub-models in router file (NodePosition/GraphNode/GraphEdge) — same pattern as existing WorkflowHistoryItem"
    - "Optional fields with `| None = None` defaults preserve backward-compatible API widening"
    - "Forward-compatible Literal union — Phase 1 ships all 7 NodeKind variants even though only 3 render"
    - "Named TS interface exports for sub-types (Plan 109-03 imports by name, not via components['schemas'] indexing)"

key-files:
  created:
    - tests/unit/workflows/test_registry_graph_fields.py
    - tests/unit/workflows/test_templates_api_returns_graph.py
  modified:
    - app/routers/workflows.py
    - app/workflows/engine.py
    - frontend/src/services/workflows.ts
    - frontend/src/types/api.generated.ts

key-decisions:
  - "Sub-models live in app/routers/workflows.py, not app/workflows/registry.py — the plan's files_modified listed registry.py, but that file is the workflow factory registry, not the response model. The Pydantic model lives next to the FastAPI router. [Rule 3 - Blocking fix]"
  - "WorkflowTemplateResponse widened with three optional fields, all defaulting to None — backward-compatible with the v8 `_seed_template_metadata` fallback path that returns rows without graph fields"
  - "Engine.list_templates SELECT explicitly enumerates graph_nodes/edges/layout — without this widening, the API would silently drop the columns even though the model accepts them"
  - "get_template needed zero changes — it does select('*') and returns the raw dict, no response_model gate"
  - "Frontend keeps `WorkflowTemplate = components['schemas']['WorkflowTemplateResponse']` alias + adds named TS exports for GraphNode/GraphEdge/NodePosition/NodeKind so Plan 109-03 imports them by name"
  - "NodeKind union includes condition/parallel/merge/human-approval even though Phase 1 only renders trigger/agent-action/output — locks the wire format so Phases 3-4 don't break frontend types"
  - "API tests mount only the workflows router on a fresh FastAPI app (no full-app boot, no real DB) — get_current_user_id is overridden via app.dependency_overrides, get_workflow_engine is patched in each test"

patterns-established:
  - "Inline Pydantic graph sub-models in app/routers/workflows.py (mirrored in frontend/src/services/workflows.ts named exports)"
  - "Tests that need to hit a single router can use FastAPI TestClient with dependency_overrides + per-test patch on get_workflow_engine — avoids the heavy sys.modules stubbing pattern used in test_workflow_execution_stream.py"

requirements-completed: [NODEEDITOR-API-01]

# Metrics
duration: 8min
completed: 2026-05-11
---

# Phase 109 Plan 02: Backend API Extension Summary

**Widens GET /workflows/templates and GET /workflows/templates/{id} to expose graph_nodes/graph_edges/graph_layout fields backed by typed Pydantic sub-models (GraphNode/GraphEdge/NodePosition); regenerates OpenAPI types so the frontend WorkflowTemplate alias picks up the new shape automatically**

## Performance

- **Duration:** ~8 min (execution); plus context-load time
- **Started:** 2026-05-11T16:16:35Z
- **Completed:** 2026-05-11T16:24:23Z
- **Tasks:** 7 (collapsed into 4 atomic commits: model+engine, frontend interfaces, regen types, tests)
- **Files created:** 2 (both test files)
- **Files modified:** 4 (router, engine, services/workflows.ts, api.generated.ts)

## Accomplishments

- `WorkflowTemplateResponse` extended with three new optional fields: `graph_nodes: list[GraphNode] | None`, `graph_edges: list[GraphEdge] | None`, `graph_layout: dict[str, NodePosition] | None`. All default to `None` so every existing caller continues to work unchanged.
- Four new Pydantic sub-models in `app/routers/workflows.py`:
  - `NodePosition(x: int, y: int)`
  - `NodeKind = Literal['trigger','agent-action','condition','parallel','merge','human-approval','output']`
  - `GraphNode(id: str, kind: NodeKind, label: str, config: dict[str, Any] | None = None)`
  - `GraphEdge(id: str, source: str, target: str, source_handle: str | None = None, label: str | None = None)`
- `WorkflowEngine.list_templates` SELECT clause widened to include the three graph columns. Without this widening, the columns would not arrive on the wire even though the response model accepts them.
- Router-level `list_templates` endpoint passes the three new fields through into `WorkflowTemplateResponse(...)` construction.
- `get_template` endpoint required zero changes — it does `select("*")` and returns the raw dict, no `response_model` gate; the new columns flow through automatically.
- Frontend `WorkflowTemplate` type stays aliased to the generated `components['schemas']['WorkflowTemplateResponse']` and now picks up `graph_nodes/edges/layout` automatically after regen.
- Added named TS interface exports (`NodePosition`, `NodeKind`, `GraphNode`, `GraphEdge`) in `frontend/src/services/workflows.ts` so Plan 109-03's NodeCanvas component can import them by name instead of digging through `components['schemas']`.
- Regenerated `frontend/src/types/api.generated.ts` via `npm run generate:types`; the schema now includes `GraphNode`, `GraphEdge`, `NodePosition` schemas and the three new `WorkflowTemplateResponse` fields. `npx tsc --noEmit` clean post-regen.
- 18 new unit tests across two files:
  - `test_registry_graph_fields.py` (12 tests): Pydantic round-trip, defaults, model_dump, model_validate from raw JSONB dicts, invalid-kind rejection, every NodeKind accepted, source_handle/label defaults, int coercion, graph_layout dict shape.
  - `test_templates_api_returns_graph.py` (6 tests): GET endpoints return graph fields, legacy rows yield None, mixed responses, backward-compat for existing fields.

## Task Commits

Tasks 02-01 and 02-04 were pure inspection (no code change). Tasks 02-02 + 02-03 were inseparable (the model uses the sub-models at definition time, so they had to land in one commit). The remaining tasks are 1-commit-each. Final commit ordering on `plan-109-spec-b-phase-1`:

1. **Tasks 02-01 + 02-02 + 02-03 + 02-04: Pydantic models + engine widening** — `47fa9291` (feat)
   - Add NodePosition, NodeKind, GraphNode, GraphEdge in app/routers/workflows.py
   - Widen WorkflowTemplateResponse with graph_nodes / graph_edges / graph_layout
   - Update WorkflowEngine.list_templates SELECT to include the three new columns
   - Pass new fields through in the router endpoint's response construction
2. **Task 02-05: Frontend interfaces** — `49a05b3d` (feat)
   - Add named TS exports for NodePosition, NodeKind, GraphNode, GraphEdge in services/workflows.ts
3. **Task 02-06: Regenerate OpenAPI types** — `96dc0099` (chore)
   - Run npm run generate:types
   - Verify `npx tsc --noEmit` clean
4. **Task 02-07: Backend unit tests** — `7b65c3b1` (test)
   - 12 Pydantic round-trip tests + 6 API endpoint tests, all GREEN

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write)

## Files Created/Modified

**Created (2 files, 446 lines total):**

- `tests/unit/workflows/test_registry_graph_fields.py` — 12 Pydantic-level tests
- `tests/unit/workflows/test_templates_api_returns_graph.py` — 6 router-level tests via FastAPI TestClient + dependency overrides

**Modified (4 files):**

- `app/routers/workflows.py` — Added NodePosition/NodeKind/GraphNode/GraphEdge sub-models + extended WorkflowTemplateResponse with three optional graph fields + passed them through in list_templates endpoint construction
- `app/workflows/engine.py` — Widened the explicit column SELECT in list_templates to include graph_nodes/edges/layout
- `frontend/src/services/workflows.ts` — Added named exports for NodePosition / NodeKind / GraphNode / GraphEdge TS interfaces
- `frontend/src/types/api.generated.ts` — Regenerated to include the three new schemas + widened WorkflowTemplateResponse

## Decisions Made

1. **Sub-models live in `app/routers/workflows.py`, not `app/workflows/registry.py`.** The plan's `files_modified` listed `app/workflows/registry.py`, but on reading that file it's the workflow factory registry (a singleton that maps workflow names to factory callables), not the response model. The Pydantic model `WorkflowTemplateResponse` actually lives in `app/routers/workflows.py:79-90`. We added the new sub-models inline next to `WorkflowTemplateResponse` rather than fabricating a Pydantic model in `registry.py` that nobody imports.

2. **Engine SELECT widening is load-bearing.** `WorkflowEngine.list_templates` does an explicit field-by-field SELECT — without adding `graph_nodes, graph_edges, graph_layout` to that SELECT, Supabase wouldn't return the columns at all, and the API would silently emit `null` regardless of what was in the DB. `get_template`, by contrast, does `select("*")` and needed no change.

3. **WorkflowTemplate alias stays generated-only.** The frontend `WorkflowTemplate` type stays as a type alias to `components['schemas']['WorkflowTemplateResponse']`. This means the three new fields appear on `WorkflowTemplate` automatically after regen. We did NOT add a parallel hand-maintained interface for the top-level template (which would have drifted). We DID add named TS exports for the four sub-types (GraphNode, GraphEdge, NodePosition, NodeKind) because Plan 109-03's NodeCanvas would otherwise have to write `components['schemas']['GraphNode']` everywhere — ugly and not future-proof if we ever switch generators.

4. **NodeKind ships all 7 variants now.** Phase 1 only renders `trigger`, `agent-action`, `output`. The remaining four (`condition`, `parallel`, `merge`, `human-approval`) are reserved for Spec B Phases 3-4. We included them in the Literal union now so the wire format is forward-stable — Phases 3-4 won't break frontend types by adding new kinds.

5. **API tests use TestClient + dependency_overrides, not heavy sys.modules stubbing.** Existing tests in `tests/unit/routers/test_workflow_execution_stream.py` stub 15+ modules into `sys.modules` to avoid full-app startup. For this plan's tests, we took the simpler path: mount only the workflows router on a fresh FastAPI app, override `get_current_user_id` via `app.dependency_overrides`, and patch `get_workflow_engine` per-test. Result: ~150 lines of test setup instead of ~400+, and the tests don't depend on stub coverage of unrelated modules.

6. **Rate-limiter autouse fixture.** SlowAPI's `@limiter.limit` decorator would otherwise gate test requests at high volumes. The autouse `_disable_rate_limiter` fixture flips `limiter.enabled = False` for the duration of each test and restores it after. Mirrors the pattern already established in `_rl_mod.enabled = False` in the heavy-stubbing test files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's files_modified listed `app/workflows/registry.py`, which is the wrong file**

- **Found during:** Task 02-01 (initial file read)
- **Issue:** The plan's `<must_haves>` and `files_modified` block referred to `app/workflows/registry.py` as the file housing the `WorkflowTemplate` Pydantic model. On reading the file, it's the workflow factory **registry** (a singleton class that maps workflow names to factory callables) — there is no Pydantic model in it. The actual `WorkflowTemplateResponse` model lives at `app/routers/workflows.py:79-90`.
- **Fix:** Added the four new Pydantic sub-models (NodePosition, NodeKind, GraphNode, GraphEdge) and extended `WorkflowTemplateResponse` in `app/routers/workflows.py`. Did NOT touch `app/workflows/registry.py`. The plan's intent (widen the API response shape) is fully satisfied; only the file location differs.
- **Files modified:** app/routers/workflows.py (instead of app/workflows/registry.py)
- **Verification:** Smoke import via `python -c "from app.routers.workflows import WorkflowTemplateResponse, GraphNode, ..."` succeeds; all 18 new unit tests pass.
- **Committed in:** `47fa9291`

**2. [Rule 2 - Missing Critical] Engine SELECT clause was stripping the new columns**

- **Found during:** Task 02-04 (verifying router serialization)
- **Issue:** `WorkflowEngine.list_templates` (`app/workflows/engine.py:152-154`) does an explicit field-by-field SELECT. Even after the Pydantic model accepts `graph_nodes/edges/layout`, the columns would never reach the model because Supabase only returns the columns named in `.select(...)`. The router endpoint would silently emit `null` for all three fields regardless of what the migration populated in the DB.
- **Fix:** Widened the SELECT to include `graph_nodes, graph_edges, graph_layout`. Verified by reading `engine.get_template` (which uses `select("*")`) — that path was already correct.
- **Files modified:** app/workflows/engine.py
- **Verification:** API tests `test_list_templates_returns_graph_fields` and `test_list_templates_handles_mixed_rows` exercise this path with the engine mocked to return graph-populated rows; they assert the API response actually contains the populated graph fields.
- **Committed in:** `47fa9291`

---

**Total deviations:** 2 auto-fixed (1 blocking - wrong file path in plan; 1 missing critical - engine SELECT widening). No architectural changes; no checkpoints required.

## Issues Encountered

**Branch was on wrong head at session start.** Working tree was on `docs/agent-operating-model-w3-plan` (likely set by a parallel GSD automation between 109-01 completion and 109-02 start). Switched back to `plan-109-spec-b-phase-1` via `git checkout` before any work began; no commits landed on the wrong branch. Per project memory `project_branch_pollution_2026_05_09.md`, this is the documented hazard with parallel GSD automation. Confirmed `git branch --show-current` returned `plan-109-spec-b-phase-1` before every commit.

**No local `ty` install.** Plan verification step 2 (`uv run ty check`) couldn't run in this dev environment — `ty` isn't in this venv's editable installs. CI runs ty as a pre-commit hook; the type check will gate the PR. Compensating coverage: Pydantic models are exercised end-to-end by 18 unit tests, and `npx tsc --noEmit` runs clean on the frontend side.

**LF→CRLF git warnings on Windows.** Cosmetic only — git emits "LF will be replaced by CRLF the next time Git touches it" warnings when staging text files from this Windows checkout. No functional impact. Same behavior as Plan 109-01's commits.

## User Setup Required

None — pure additive backend/frontend type changes. After this plan merges to main:

1. CI will regenerate API types fresh (no manual action needed; PR includes the regen).
2. Frontend `WorkflowTemplate` consumers automatically gain `graph_nodes?`, `graph_edges?`, `graph_layout?` access — no code change required at call sites.
3. The new fields are `null` for rows that had empty phases (per Plan 109-01's contract). Plan 109-03 should treat `template.graph_nodes == null` as the legacy-rendering fallback signal.

No new env vars, no dashboard config, no third-party services.

## Next Phase Readiness

**Ready for Plan 109-03** (frontend graph viewer):

- `template.graph_nodes`, `template.graph_edges`, `template.graph_layout` are now typed on the frontend via the generated `WorkflowTemplate` alias.
- Named TS interfaces (`GraphNode`, `GraphEdge`, `NodePosition`, `NodeKind`) are importable directly from `@/services/workflows`.
- `NodeKind` union covers all 7 variants — Plan 109-03's React Flow node renderer needs branches only for `trigger`, `agent-action`, `output` (Phase 1 scope), but TypeScript will warn if it tries to handle an unknown kind.
- The wire format is locked: backend Pydantic + frontend TS + generated schema all agree on field names, types, and nullability.
- Engine widens the SELECT only on `list_templates`; `get_template` uses `select("*")` so it already returns the full row including any future columns.

**Self-Check:** see below.

---

## Self-Check: PASSED

Verified post-write:

- [x] `app/routers/workflows.py` modified — sub-models + WorkflowTemplateResponse widened + list_templates passes through new fields (verified via Python smoke import)
- [x] `app/workflows/engine.py` modified — list_templates SELECT widened (verified by reading lines 152-156)
- [x] `frontend/src/services/workflows.ts` modified — named exports for NodePosition/NodeKind/GraphNode/GraphEdge added
- [x] `frontend/src/types/api.generated.ts` modified — regenerated, contains GraphNode/GraphEdge/NodePosition schemas + widened WorkflowTemplateResponse (grep confirmed)
- [x] `tests/unit/workflows/test_registry_graph_fields.py` exists on disk (12 tests, all PASSED)
- [x] `tests/unit/workflows/test_templates_api_returns_graph.py` exists on disk (6 tests, all PASSED)
- [x] Commit `47fa9291` exists in `git log` (Tasks 02-02 + 02-03)
- [x] Commit `49a05b3d` exists in `git log` (Task 02-05)
- [x] Commit `96dc0099` exists in `git log` (Task 02-06)
- [x] Commit `7b65c3b1` exists in `git log` (Task 02-07)
- [x] All commits land on `plan-109-spec-b-phase-1` branch (verified `git branch --show-current` + `git log` from branch tip)
- [x] All 35 tests in `tests/unit/workflows/` pass (18 new + 17 pre-existing)
- [x] `npx tsc --noEmit` clean on the frontend
- [x] `ruff check` clean on both new test files

---

*Phase: 109-workflow-node-editor-viewer*
*Completed: 2026-05-11*
