---
phase: 110-workflow-node-editor-editable
plan: 03
subsystem: api
tags: [fastapi, pydantic, graph-validation, kahn-algorithm, scc-detection, dag, openapi, workflow-templates, shared-fixture]

# Dependency graph
requires:
  - phase: 110-02-backend-save-load
    provides: PUT /workflows/templates/{id} handler + SaveTemplateRequest model + GraphNode/GraphEdge Pydantic models + WorkflowTemplateResponse
  - phase: 110-01-versioning-migration
    provides: workflow_template_versions table + save_template_version helper
  - phase: 109-workflow-node-editor-viewer
    provides: 7-variant NodeKind Literal + GraphNode/GraphEdge frontend types
provides:
  - app/workflows/graph_validation.py - pure-functional validate_workflow_graph(graph_nodes, graph_edges, *, strict=False) with rules 1, 2, 3, 6, 7
  - POST /workflows/templates/{id}/validate endpoint with ValidateGraphRequest/Response models
  - validate_workflow_graph wired UNCONDITIONALLY into Plan 02's PUT handler (B-1 wave-3 wiring) - 400 short-circuit BEFORE save_template_version
  - tests/fixtures/graph_validation_cases.json - shared canonical fixture (B-4) for client/server parity (8 named cases)
  - 3 new Pydantic models in app/routers/workflows.py - ValidateGraphRequest, ValidationErrorItem, ValidateGraphResponse
  - 2 named TS type aliases - ValidationError, ValidateGraphResponse - in frontend/src/services/workflows.ts
  - Regenerated frontend/src/types/api.generated.ts with the 3 new schemas
  - 42 unit tests across 2 new files (30 in graph_validation + 12 in validate endpoint)
affects: [110-04-frontend-editable-canvas, 110-05-frontend-versioning-conflict]

# Tech tracking
tech-stack:
  added: []  # Pure-Python; no new deps. Pydantic + collections only.
  patterns:
    - "Pure-functional validator module (no DB, no async, no IO) with Pydantic models for typed errors"
    - "Shared JSON fixture (tests/fixtures/graph_validation_cases.json) as the single source of truth for client/server validator parity - both pytest and vitest parametrize over the same file"
    - "Kahn's algorithm + SCC refinement for cycle detection - distinguishes true cycle members from downstream-of-cycle nodes (cleaner UX than naive Kahn leftover)"
    - "Per-kind Pydantic config schemas - tight for executing kinds (trigger/agent-action/output), permissive placeholder for visual-only kinds (condition/parallel/merge/human-approval)"
    - "strict=True flag pattern for forward-compat - raises NotImplementedError on rules 4/5 so Phase 3/4 can flip the default without changing the function signature"
    - "Deterministic error emission order via graph_nodes iteration (not set iteration) - shared fixture assertions become stable across Python implementations"
    - "Unconditional wave-3 wiring (B-1) - Plan 03 patches Plan 02's existing PUT handler with no 'if shipped' conditional, since Wave 3 guarantees Plan 02 is on disk"

key-files:
  created:
    - app/workflows/graph_validation.py
    - tests/fixtures/graph_validation_cases.json
    - tests/unit/workflows/test_graph_validation.py
    - tests/unit/routers/test_workflow_validate_endpoint.py
  modified:
    - app/routers/workflows.py
    - frontend/src/types/api.generated.ts
    - frontend/src/services/workflows.ts

key-decisions:
  - "Validator is a pure-functional module (no DB, no async) - both POST /validate and the PUT save path call it via direct function call. Easy to unit test, easy to import from anywhere"
  - "Shared JSON fixture at tests/fixtures/graph_validation_cases.json is the canonical contract for client/server parity (B-4) - Plan 04 vitest will load the same file; any change to validator behavior must update the fixture, both test suites catch divergence"
  - "Cycle detection uses Kahn's algorithm + a second-pass SCC check - flags only true cycle members, NOT downstream-of-cycle nodes. Better UX: users fix one cycle and downstream errors disappear automatically"
  - "BFS reachability seeds from ALL trigger nodes, not just the first - prevents extra triggers (rule 1 violation) from double-flagging as unreachable (rule 2 violation). Less noisy error lists"
  - "Per-kind config schemas tight for executing kinds (TriggerConfig allows manual/schedule/event, AgentActionConfig requires tool_name); permissive _PermissiveConfig placeholder for condition/parallel/merge/human-approval - Phase 3/4 will tighten these without breaking Plan 04's frontend"
  - "strict=True raises NotImplementedError - signals Phase 3/4 callers that rules 4 + 5 (condition outgoing degree, parallel/merge pairing) aren't implemented yet. Default strict=False silently skips them. Phase 3/4 can flip the default without changing the function signature"
  - "Cycle error emission walks graph_nodes in order (not set iteration) - deterministic test assertions across Python implementations (set iteration order varies in some test sessions)"
  - "Wiring into PUT handler is unconditional (B-1 wave-3) - no 'if Plan 02 has shipped' hedge. Wave 3 means Plan 02 IS on disk; the validate call goes between auth check and save_template_version, returning 400 with detail={error: 'validation_failed', errors: [...]} on any rule violation"
  - "ValidationErrorItem schema in the router mirrors app.workflows.graph_validation.ValidationError byte-for-byte - the frontend's ValidationError type alias is a direct re-export of components['schemas']['ValidationErrorItem']"
  - "Validate endpoint does NOT actually load the template graph from DB - the proposed graph is in the request body. Only DB hit is the auth check (engine.get_template for created_by). Lets the frontend run validation on every keystroke without DB round-trips"

patterns-established:
  - "Validator as pure-functional module - no DB/async/IO. Composes with both endpoint handlers and save-path enforcement. Testable in isolation with zero fixtures"
  - "Shared JSON fixture for client/server parity - tests/fixtures/graph_validation_cases.json is loaded by pytest (server) AND vitest (Plan 04 client). Behavior divergence caught by either suite"
  - "Kahn + SCC for cycle detection - O(V+E) topological sort identifies leftover nodes; second pass restricted to leftover set distinguishes cycle members from downstream-of-cycle nodes"
  - "Per-kind Pydantic config schemas with permissive placeholders - tight schemas for executing kinds, _PermissiveConfig for visual-only kinds. Phase 3/4 tightens individual placeholders without breaking Plan 04's frontend"
  - "Unconditional wave-N wiring pattern - when planning explicitly serializes plans by wave, follow-up plans patch earlier plans' handlers without 'if shipped' hedges"
  - "Mock-asserted save-path short-circuit - tests verify save_template_version was NEVER awaited when validation fails (mock_calls assertion), not just response body. Catches future regressions where validation accidentally moves AFTER the save"

requirements-completed: [NODEEDITOR-VALIDATE-01]

# Metrics
duration: 17min
completed: 2026-05-11
---

# Phase 110 Plan 03: Backend Validation Summary

**Pure-functional graph validator (rules 1, 2, 3, 6, 7) + POST /validate endpoint + unconditional wiring into Plan 02's PUT save handler + shared client/server parity fixture - all wired through Pydantic models with regenerated OpenAPI types.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-05-11T19:04:34Z
- **Completed:** 2026-05-11T19:21:16Z
- **Tasks:** 3 (5 atomic commits — 2 TDD RED+GREEN splits + 1 chore commit)
- **Files created:** 4 (1 Python module, 2 test files, 1 JSON fixture)
- **Files modified:** 3 (app/routers/workflows.py, frontend/src/types/api.generated.ts, frontend/src/services/workflows.ts)

## Accomplishments

- **One new pure-functional validator module** at `app/workflows/graph_validation.py` (~317 lines). `validate_workflow_graph(graph_nodes, graph_edges, *, strict=False) -> list[ValidationError]`. Enforces Phase 110 in-scope rules: 1 (single trigger, zero incoming), 2 (BFS reachability from all triggers), 3 (Kahn's algorithm + SCC refinement so only true cycle members are flagged), 6 (≥1 output node), 7 (per-kind Pydantic config validation). Pydantic ValidationError model with `node_id: str | None`, `rule: int`, `message: str`.

- **One new POST endpoint** at `app/routers/workflows.py`: `POST /workflows/templates/{template_id}/validate`. Returns `{errors: list[ValidationErrorItem]}` (empty iff valid). Auth mirrors GET (seed templates globally readable; private templates owner-only via `created_by` check). Does NOT write to DB; only DB hit is auth check.

- **B-1 wave-3 wiring** (unconditional): Plan 02's PUT handler at line ~745 in `app/routers/workflows.py` now calls `validate_workflow_graph()` BETWEEN the auth check and `save_template_version()`. On any validation error: short-circuits to HTTP 400 with `detail={"error": "validation_failed", "errors": [...]}` BEFORE save_template_version runs. Mock-asserted by `test_put_with_invalid_graph_returns_400_and_skips_save`. Closes the bypass risk where direct API users could skip POST /validate.

- **Three new Pydantic models** added to `app/routers/workflows.py` next to the Plan 02 model cluster: `ValidateGraphRequest`, `ValidationErrorItem`, `ValidateGraphResponse`. ValidationErrorItem mirrors `app.workflows.graph_validation.ValidationError` byte-for-byte.

- **One new shared JSON fixture** at `tests/fixtures/graph_validation_cases.json` (B-4 contract, 8 named cases): `valid_minimal`, `no_trigger`, `two_triggers`, `trigger_with_incoming_edge`, `unreachable_node`, `cycle_two_nodes`, `no_output`, `bad_agent_action_config`. Both Plan 03 pytest AND Plan 04 vitest will parametrize over this same file. The `message_contains` substring assertion lets server and client phrase messages naturally without forced literal equality.

- **42 GREEN unit tests** across two new files: 30 in `tests/unit/workflows/test_graph_validation.py` (8 fixture-parametrized + 22 individual rule + edge case + ValidationError model tests) + 12 in `tests/unit/routers/test_workflow_validate_endpoint.py` (3 happy-path + 3 auth/scope + 2 body validation + 1 no-DB-write + 3 B-1 wiring tests). Plus 15 Plan 02 save endpoint tests still GREEN (no regression).

- **Regenerated `frontend/src/types/api.generated.ts`** via openapi-typescript v7.13.0 against the live FastAPI openapi() schema. All 3 new schemas (ValidateGraphRequest, ValidationErrorItem, ValidateGraphResponse) present (9 occurrences across schema defs + path references).

- **Two named TS type aliases** in `frontend/src/services/workflows.ts`: `ValidationError = components['schemas']['ValidationErrorItem']` and `ValidateGraphResponse = components['schemas']['ValidateGraphResponse']`. Plan 04's `useGraphValidation` hook will import these by name instead of digging through the components index. `npx tsc --noEmit` clean.

## Task Commits

Each task was committed atomically. Tasks 03-01 and 03-02 split into RED+GREEN per TDD:

1. **Task 03-01 RED: failing tests + shared fixture** — `29d59652` (test)
2. **Task 03-01 GREEN: validate_workflow_graph() pure-functional validator** — `ae0fde1f` (feat)
3. **Task 03-02 RED: failing tests for /validate endpoint + PUT wiring** — `23087cfc` (test)
4. **Task 03-02 GREEN: POST /validate endpoint + wire validation into PUT** — `797f2d32` (feat)
5. **Task 03-03: regenerate OpenAPI types + named TS exports** — `0aed6b71` (chore)

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write)

## Files Created/Modified

**Created (4 files):**

- `app/workflows/graph_validation.py` (317 lines) - `validate_workflow_graph()` + 5 per-kind config schemas + `ValidationError` Pydantic model + Kahn-with-SCC cycle detection + BFS reachability
- `tests/fixtures/graph_validation_cases.json` (8 named cases) - shared canonical contract for client/server parity (B-4)
- `tests/unit/workflows/test_graph_validation.py` (~430 lines, 30 tests) - fixture parametrize + 22 individual rule + edge tests + 2 model contract tests + 2 strict-flag tests
- `tests/unit/routers/test_workflow_validate_endpoint.py` (~470 lines, 12 tests) - 9 endpoint contract + 3 B-1 wave-3 wiring tests with mock assertions

**Modified (3 files):**

- `app/routers/workflows.py` - Added 3 Pydantic models + 1 new endpoint + 1 import + 14-line validation block inside PUT handler (~136 new lines)
- `frontend/src/types/api.generated.ts` - Regenerated via openapi-typescript v7.13.0 (130 new lines for the 3 new schemas)
- `frontend/src/services/workflows.ts` - Added 2 named TS type aliases (`ValidationError`, `ValidateGraphResponse`) with documentation (~17 new lines)

## Decisions Made

1. **Validator is pure-functional (no DB, no async, no IO).** Both POST /validate and the PUT save path call it as a sync function. Easy to unit test, easy to import from anywhere. Mirrors the design Plan 04's `useGraphValidation` will use on the frontend.

2. **Shared JSON fixture as the canonical contract.** `tests/fixtures/graph_validation_cases.json` (8 named cases with `name`, `input`, `expected_errors`) is loaded by pytest (Plan 03) AND vitest (Plan 04). The `message_contains` substring assertion (not exact match) lets server and client phrase messages naturally while still asserting the message conveys the right concept. Any change to validator behavior must update the fixture, both suites catch divergence automatically.

3. **Kahn's algorithm + SCC refinement for cycle detection.** Naive Kahn's leftover (`in_degree > 0` after topological sort terminates) flags BOTH true cycle members AND downstream-of-cycle nodes. For user feedback, we only want to flag actual cycle members - fixing the cycle automatically fixes downstream issues. A second pass restricted to leftover nodes (DFS to check if a node can reach itself) distinguishes the two. The two-node cycle test case (`a1 ↔ a2` between trigger and output) shows o1 is downstream of the cycle but NOT flagged.

4. **BFS reachability seeds from ALL trigger nodes** (not just the first). When rule 1 is already firing on extra triggers, we don't want rule 2 to ALSO fire on those same extra triggers as unreachable - that's noisy and confusing. Seeding BFS from all triggers means extra-trigger errors stay scoped to rule 1.

5. **Per-kind config schemas: tight for executing kinds, permissive for visual-only kinds.** `TriggerConfig` validates trigger_type ∈ {manual, schedule, event} with extras allowed. `AgentActionConfig` requires `tool_name` (str), optional `agent_role` and `arguments`. `OutputConfig` has optional `output_format`. The remaining 4 kinds (condition, parallel, merge, human-approval) use `_PermissiveConfig` (extra=allow, no required fields) - Phase 3/4 will tighten each individually without breaking Plan 04's frontend or migrations.

6. **strict=True raises NotImplementedError.** Signals callers that rules 4 (condition outgoing degree, Phase 3) and 5 (parallel/merge pairing, Phase 4) aren't implemented. Default `strict=False` silently skips them. Phase 3/4 can flip the default without changing the function signature - just implement the strict branch.

7. **Cycle error emission is deterministic via graph_nodes iteration.** Initial implementation used set iteration (`for nid in in_cycle:`), which produces non-deterministic order across Python implementations. Fixed by iterating over `graph_nodes` and emitting only nodes whose id is in the `in_cycle` set - now matches the fixture's expected order (a1 before a2, t1 before a1).

8. **Wiring into the PUT handler is unconditional (B-1 wave-3).** The plan's must_haves spelled out "no 'if Plan 02 has shipped' hedge" because Wave 3 means Plan 02 IS on disk. The validation call goes between the auth check and `save_template_version()`. Returns HTTP 400 with `detail={error: 'validation_failed', errors: [...]}` on any rule violation. Closes the bypass risk - direct API users can no longer call PUT with an invalid graph and skip POST /validate.

9. **ValidationErrorItem in the router mirrors graph_validation.ValidationError byte-for-byte.** The frontend's `ValidationError` type alias is a direct re-export of `components['schemas']['ValidationErrorItem']`. One canonical shape across the entire stack: Python validator → Pydantic schema → OpenAPI → TypeScript type → frontend hook.

10. **Validate endpoint does NOT load the graph from DB.** The proposed graph is in the request body. Only DB hit is the auth check on the template row (engine.get_template for created_by). Lets the frontend run validation on every keystroke without DB round-trips. The template_id in the URL is only used for auth (does the user have read access?), not for graph retrieval.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Refined cycle detection to distinguish cycle members from downstream-of-cycle nodes**

- **Found during:** Task 03-01 GREEN (when fixture cases `cycle_two_nodes` and `trigger_with_incoming_edge` failed)
- **Issue:** Naive Kahn's algorithm leftover (`in_degree > 0` after topological sort terminates) flags BOTH true cycle members AND downstream-of-cycle nodes. The `cycle_two_nodes` case (t1 → a1 → a2 → a1, then a2 → o1) expected ONLY a1 and a2 to be flagged. Initial implementation also flagged o1 (in_degree never reached 0 because its only inbound edge comes from a2, locked in the cycle).
- **Fix:** Added a second-pass SCC-style check after Kahn's algorithm. For each leftover node, DFS through its outgoing edges restricted to the leftover set - if a node can reach itself, it's IN the cycle; otherwise it's downstream of one. Only the true cycle members get rule-3 errors.
- **Files modified:** `app/workflows/graph_validation.py`
- **Verification:** All 8 fixture cases pass; 22 individual tests pass; user feedback is cleaner (fix one cycle, downstream errors disappear).
- **Committed in:** `ae0fde1f` (Task 03-01 GREEN commit)

**2. [Rule 2 - Missing Critical] BFS reachability seeds from ALL trigger nodes (not just the first)**

- **Found during:** Task 03-01 GREEN (when fixture case `two_triggers` failed)
- **Issue:** Initial implementation seeded BFS from `triggers[0]['id']` only. The `two_triggers` case (t1, t2 both with `t→o1`) expected ONLY a rule-1 error for t2 (extra trigger). Initial implementation ALSO emitted a rule-2 error for t2 (unreachable from t1) - noisy and confusing because rule 1 already explained the t2 problem.
- **Fix:** Seed BFS queue with ALL trigger node ids: `deque(t["id"] for t in triggers)`. Extra-trigger errors stay scoped to rule 1; rule 2 only fires for nodes that truly cannot be reached from any trigger.
- **Files modified:** `app/workflows/graph_validation.py`
- **Verification:** `two_triggers` fixture case now passes (single rule-1 error for t2, no rule-2 noise).
- **Committed in:** `ae0fde1f` (Task 03-01 GREEN commit)

**3. [Rule 1 - Bug] Cycle errors emitted in graph_nodes order for deterministic test assertions**

- **Found during:** Task 03-01 GREEN (when `cycle_two_nodes` fixture failed with node_id mismatch a2 vs a1)
- **Issue:** Initial implementation iterated `in_cycle` set, which produces non-deterministic order across Python implementations (set iteration depends on hash randomization). Fixture expected a1 before a2 (graph_nodes order); some test runs got a2 before a1.
- **Fix:** Iterate `graph_nodes` in order, emit a rule-3 error for any node whose id is in `in_cycle`. Order now deterministic across all runs.
- **Files modified:** `app/workflows/graph_validation.py`
- **Verification:** Tests stable across multiple runs; matches fixture expected order.
- **Committed in:** `ae0fde1f` (Task 03-01 GREEN commit)

**4. [Rule 3 - Blocking] Corrected `trigger_with_incoming_edge` fixture to include the cycle errors**

- **Found during:** Task 03-01 fixture authoring
- **Issue:** The plan's fixture example for `trigger_with_incoming_edge` (edges t1→a1, a1→t1, a1→o1) expected ONLY a rule-1 error for t1. But the algorithm correctly detects that t1↔a1 forms a 2-node cycle - rule 3 SHOULD fire for both. Either the algorithm needed a special case (skip rule 3 if rule 1 already fired) OR the fixture needed to reflect reality.
- **Fix:** Updated the fixture's `expected_errors` to include both rule-1 (t1, zero incoming) AND rule-3 errors (t1 + a1, cycle). Reflects what the algorithm actually outputs; client and server stay aligned via the same canonical fixture.
- **Files modified:** `tests/fixtures/graph_validation_cases.json`
- **Verification:** `trigger_with_incoming_edge` test passes; client (Plan 04) will see the same 3-error expectation when it parametrizes over the same fixture.
- **Committed in:** `29d59652` (Task 03-01 RED commit)

### Branch hygiene incidents

**Branch pollution detected mid-Task-03-03.** While running `npm run` and `npx tsc` commands, the working tree briefly switched to `feat/agent-operating-model-w3-section-b` (another concurrent branch). Detected via `git branch --show-current` before commit; switched back to `plan-109-spec-b-phase-1`. W3-Section-B's edits to `app/agent.py` and `app/fast_api_app.py` had been swept into my working tree by the pollution - reverted with `git checkout HEAD -- app/agent.py app/fast_api_app.py` before committing Task 03-03. No W3-B content landed on this branch. Pattern matches memory notes `project_branch_pollution_2026_05_09.md` and `project_workflow_node_editor_phase1.md`.

---

**Total deviations:** 4 auto-fixed (3 bugs, 1 missing critical, 1 fixture correction) + 1 branch-pollution incident successfully navigated
**Impact on plan:** All fixes essential for correctness (cycle UX + deterministic emission + reachability semantics) or alignment between fixture and algorithm. Branch pollution caught before any cross-contamination committed. No scope creep.

## Issues Encountered

**Pre-existing ruff B904 in `app/routers/workflows.py` (29 violations + 1 F811).** Inherited from before Phase 110; documented in `.planning/phases/110-workflow-node-editor-editable/deferred-items.md` by Plan 02. My new POST /validate endpoint uses `raise HTTPException(...) from e` correctly (no new B904). Total ruff count stays at 30 (29 pre-existing + 1 F811, unchanged from baseline). Verified via `git stash`/`stash pop` cycle.

**Pre-existing engine test failures.** `tests/unit/test_workflow_engine_readiness_gate.py` has 3 failing tests (KeyError 'user_id' in WorkspaceItemEmitter) - baseline issue from before Phase 110, documented in deferred-items.md by Plan 02. My changes don't touch the engine; not regressed further.

**`uv` CLI not on PATH on this Windows workstation.** Worked around by invoking the venv Python directly (`.venv/Scripts/python -m ...`) and using `.venv/Scripts/python -c "..."` for the OpenAPI schema export. Same workaround Plan 02 used; documented in its SUMMARY.

**stderr leaking into the OpenAPI JSON output.** Initial `python -c "...print(json)"` redirected stderr into the same file as stdout, polluting the JSON with config warnings. Fixed with explicit `2>/dev/null` redirect.

**Branch pollution mid-execution.** As above - working tree switched to a different feature branch while I was running `npm` / `npx` commands. Resolved without cross-contamination by reverting non-Plan-03 changes before committing.

## User Setup Required

None - pure backend/frontend type changes. After this plan merges to main:

1. The new endpoint becomes available at `POST /workflows/templates/{template_id}/validate` (requires authenticated user via existing `Depends(get_current_user_id)`).
2. The existing PUT endpoint now enforces validation server-side - direct API callers can no longer save invalid graphs.
3. Frontend type consumers automatically pick up the new schemas via the regenerated `api.generated.ts` and the named exports in `services/workflows.ts`.

No new env vars, no dashboard configuration, no third-party services.

## Next Phase Readiness

**Ready for Plan 110-04** (frontend editable canvas):

- Service API: import `ValidationError` and `ValidateGraphResponse` from `frontend/src/services/workflows.ts` (named exports, NOT components['schemas'] index).
- Endpoint: `POST /workflows/templates/{id}/validate` with body `{graph_nodes, graph_edges}`. Returns 200 with `{errors: ValidationError[]}`.
- Client-side validator: implement `validateGraphClient(nodes, edges)` in `frontend/src/components/workflows/editor/useGraphValidation.ts`. MUST parametrize its vitest tests over the SAME `tests/fixtures/graph_validation_cases.json` (load via `import fixtures from '../../../../tests/fixtures/graph_validation_cases.json'` or equivalent). Any divergence from the server validator behavior will be caught by either suite.
- Visual feedback: render red badges on offending nodes (per spec); top-of-canvas summary banner with click-to-jump is at the planner's discretion.
- Save flow: on PUT 400 with `detail.error === 'validation_failed'`, surface the errors list AND keep local state intact - users should be able to fix the errors and retry without losing their work.

**Ready for Plan 110-05** (frontend version selector + conflict modal):

- No direct dependency on this plan. 110-05 uses the GET /history + POST /revert endpoints shipped by Plan 02.

**ROADMAP criterion #8 (server-side validation enforces same rules + returns structured errors + wired into save path):** SHIPPED. Both `POST /validate` (returns `{errors: [...]}`) and PUT (short-circuits to 400 with `detail.errors` before save) are in place. Direct API callers cannot bypass validation.

---

## Self-Check: PASSED

Verified post-write (all paths absolute):

- [x] `C:/Users/expert/documents/pka/pikar-ai/app/workflows/graph_validation.py` exists on disk (317 lines)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/fixtures/graph_validation_cases.json` exists on disk (8 named cases verified via JSON parse)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/unit/workflows/test_graph_validation.py` exists on disk (30 tests collected)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/unit/routers/test_workflow_validate_endpoint.py` exists on disk (12 tests collected)
- [x] `app/routers/workflows.py` modified (3 Pydantic models + 1 endpoint + 14-line validation block inside PUT handler + 1 import)
- [x] `frontend/src/types/api.generated.ts` regenerated (9 occurrences of ValidationErrorItem/ValidateGraphResponse/ValidateGraphRequest)
- [x] `frontend/src/services/workflows.ts` has 2 named TS type aliases (ValidationError + ValidateGraphResponse)
- [x] Commit `29d59652` exists (Task 03-01 RED)
- [x] Commit `ae0fde1f` exists (Task 03-01 GREEN)
- [x] Commit `23087cfc` exists (Task 03-02 RED)
- [x] Commit `797f2d32` exists (Task 03-02 GREEN)
- [x] Commit `0aed6b71` exists (Task 03-03)
- [x] All 5 commits land on `plan-109-spec-b-phase-1` (verified via `git log --oneline -5`)
- [x] 42 unit tests GREEN (30 graph_validation + 12 validate endpoint)
- [x] 15 Plan 02 save endpoint tests still GREEN (no regression)
- [x] `npx tsc --noEmit` clean across frontend (no TS errors from my new types)
- [x] Ruff clean on all new files (graph_validation.py + 2 test files)
- [x] Branch hygiene: still on `plan-109-spec-b-phase-1` after all 5 commits (pollution detected and reverted mid-Task-03-03)

---

*Phase: 110-workflow-node-editor-editable*
*Completed: 2026-05-11*
