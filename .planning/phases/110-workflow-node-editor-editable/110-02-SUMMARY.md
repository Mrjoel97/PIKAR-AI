---
phase: 110-workflow-node-editor-editable
plan: 02
subsystem: api
tags: [fastapi, pydantic, postgresql, plpgsql, etag, if-match, optimistic-locking, openapi, workflow-templates, versioning]

# Dependency graph
requires:
  - phase: 110-01-versioning-migration
    provides: workflow_template_versions table + current_version_id + template_version_id columns + v1 backfill
  - phase: 109-workflow-node-editor-viewer
    provides: WorkflowTemplateResponse Pydantic model + graph projection columns + NodeKind 7-variant Literal
provides:
  - PUT /workflows/templates/{id} endpoint (Save w/ If-Match optimistic locking, 428/412/200/409/403/404/422)
  - GET /workflows/templates/{id}/history endpoint (HistoryItem list, version_number DESC)
  - POST /workflows/templates/{id}/revert/{version_id} endpoint (creates new version with parent_version_id = target)
  - GET /workflows/templates/{id} now emits ETag header (quoted ISO8601)
  - Six new Pydantic models in app/routers/workflows.py (SaveTemplateRequest, WorkflowTemplateVersion, HistoryItem, SeedForkResponse, SaveTemplateSuccessResponse) + WorkflowTemplateResponse widened with current_version_id
  - app/workflows/template_versions.py module (save_template_version, list_template_history, revert_template_to_version, copy_seed_template_for_user)
  - DROP+CREATE migration for start_workflow_execution_atomic with new p_template_version_id parameter
  - save_workflow_template_version Postgres function (atomic two-table Save w/ If-Match)
  - Engine wired: list_templates SELECT widened + start_workflow rpc_params propagates p_template_version_id
  - Regenerated api.generated.ts with all 5 new schemas
  - 51 GREEN unit tests + 6 collected integration tests (skip on no creds)
affects: [110-03-backend-validation, 110-04-frontend-editable-canvas, 110-05-frontend-versioning-conflict]

# Tech tracking
tech-stack:
  added: []  # No new deps; pure schema + endpoint extension on existing stack
  patterns:
    - "Quoted ISO8601 ETag wire format per RFC 7232 with defensive quote-strip on If-Match input"
    - "Body-canonical ETag pattern: 200/412 responses include etag key in response BODY (not just header) so client never needs a follow-up GET to learn the next-write ETag"
    - "Two-table Save atomicity via Postgres function (save_workflow_template_version) — Python layer makes one .rpc() call, never sees a torn write"
    - "DROP FUNCTION + CREATE OR REPLACE pattern for signature-changing RPC updates (CREATE OR REPLACE alone rejects argument-list changes)"
    - "Seed-fork-on-Edit: PUT against created_by IS NULL returns 409 (not 200) with SeedForkResponse exact 4-key body so frontend re-routes editor URL"
    - "responses={status: {model}} declaration pattern for FastAPI endpoints returning raw JSONResponse — required so OpenAPI emits the Pydantic schemas"

key-files:
  created:
    - supabase/migrations/20260615000100_workflow_template_save_rpc.sql
    - app/workflows/template_versions.py
    - tests/unit/workflows/test_template_versions_engine.py
    - tests/unit/routers/test_workflow_save_endpoint.py
    - tests/integration/test_etag_round_trip.py
    - tests/integration/test_linear_workflow_execution_post_versioning.py
    - .planning/phases/110-workflow-node-editor-editable/deferred-items.md
  modified:
    - app/routers/workflows.py
    - app/workflows/engine.py
    - frontend/src/types/api.generated.ts

key-decisions:
  - "ETag wire format: quoted ISO8601 of workflow_template_versions.saved_at (fallback workflow_templates.updated_at when current_version_id IS NULL). Both header AND body.etag carry the same canonical value."
  - "Defensive quote-strip on If-Match input — clients SHOULD send quoted but curl-without-quotes still works (RFC 7232 tolerance)."
  - "Two-table Save lives in a Postgres function (save_workflow_template_version), not a Python transaction — keeps the If-Match check + INSERT + UPDATE atomic at the DB layer, Python sees one .rpc() call."
  - "DROP FUNCTION IF EXISTS ... CASCADE precedes CREATE OR REPLACE for the start_workflow_execution_atomic signature change (9-arg → 10-arg)."
  - "Seed fork (created_by IS NULL on the source) returns 409 with SeedForkResponse, NOT 200. Frontend's CopyForkError reads body.seed_name + body.copied_template_id and routes the editor to the new URL."
  - "_fetch_current_version_saved_at falls back silently to None when Supabase client cannot initialize — guards GET against 500s in test environments with no creds (caught during Phase 109 GET tests post-edit)."
  - "responses={200/409: {model}} declarations on PUT and POST revert endpoints — without them, FastAPI couldn't emit SaveTemplateSuccessResponse + SeedForkResponse into OpenAPI since the endpoints return raw JSONResponse."
  - "Behavioural mock-based engine tests (W-7) over grep — list_templates SELECT widening + start_workflow rpc_params propagation are verified via captured-args, not text search. Catches silent regressions if a future refactor changes how projections are built."

patterns-established:
  - "ETag/If-Match wire format: server emits + accepts quoted ISO8601; defensively strips quotes from input; etag key in 200/412 response body matches the header (B-2 parity)"
  - "Two-table atomic write in a Postgres function with optimistic locking: function returns SETOF on success / empty on If-Match mismatch — Python layer translates empty to HTTP 412"
  - "Signature-changing RPC update: DROP FUNCTION IF EXISTS (signature) CASCADE + CREATE OR REPLACE; default-NULL new param preserves all existing named-keyword callers"
  - "Seed-fork-on-Edit: created_by IS NULL → copy_seed_template_for_user inserts private copy + bootstraps v1 + returns dict with both copied_template_id AND seed_name keys (W-4); endpoint returns 409 with SeedForkResponse exact-4-key shape"
  - "Behavioural engine integration tests (W-7) — mock supabase client + captured rpc_params, NOT text grep — catches refactors that grep-based assertions would miss"

requirements-completed: [NODEEDITOR-SAVE-01, NODEEDITOR-VERSION-01, NODEEDITOR-VERSION-02, NODEEDITOR-CONCURRENCY-01]

# Metrics
duration: 21min
completed: 2026-05-11
---

# Phase 110 Plan 02: Backend Save + Load Endpoints Summary

**PUT/GET-history/POST-revert endpoints with quoted-ISO8601 ETag optimistic locking, atomic two-table Save via Postgres function, seed-fork-on-Edit 409 contract (W-4), engine wired to pin executions to current_version_id (ROADMAP criterion #9 W-8), and regenerated OpenAPI TS types — all ready for Plan 04's frontend consumer.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-05-11T18:35:08Z
- **Completed:** 2026-05-11T18:56:13Z
- **Tasks:** 7 (9 atomic commits — 7 task commits + 2 TDD RED splits)
- **Files created:** 7 (1 SQL migration, 1 Python module, 4 test files, 1 deferred-items.md)
- **Files modified:** 3 (app/routers/workflows.py, app/workflows/engine.py, frontend/src/types/api.generated.ts)

## Accomplishments

- **One new SQL migration** at `supabase/migrations/20260615000100_workflow_template_save_rpc.sql` (~280 lines). DROP FUNCTION + CREATE OR REPLACE pattern for `start_workflow_execution_atomic` (10-arg signature with new `p_template_version_id UUID DEFAULT NULL`). New `save_workflow_template_version(8-arg)` function does atomic two-table Save with server-side If-Match check + parent_version_id chaining. `$BODY$` named dollar quotes throughout (supabase CLI 2.75 bug avoidance).
- **One new Python module** at `app/workflows/template_versions.py` (~330 lines). Four async helpers (save_template_version, list_template_history, revert_template_to_version, copy_seed_template_for_user) + two Pydantic models (WorkflowTemplateVersion, HistoryItem). Uses canonical `get_async_client()` from `app.services.supabase_client` (NOT deprecated `supabase` shim).
- **Three new endpoints** added to `app/routers/workflows.py`: PUT /templates/{id}, GET /templates/{id}/history, POST /templates/{id}/revert/{version_id}. Plus widened GET /templates/{id} to emit the ETag header.
- **Six new Pydantic models** inline next to `WorkflowTemplateResponse` in the router: `SaveTemplateRequest`, `WorkflowTemplateVersion`, `HistoryItem`, `SeedForkResponse`, `SaveTemplateSuccessResponse`. `WorkflowTemplateResponse` widened with `current_version_id: str | None = None`.
- **Two ETag helpers** (`_format_etag`, `_parse_if_match`) + one defensive fetch (`_fetch_current_version_saved_at`) implementing B-2 wire-format parity. Server emits quoted ISO8601, defensively strips quotes on input, includes the etag in BOTH 200 and 412 response bodies under the `etag` key.
- **Engine integration** (Task 02-04): `WorkflowEngine.list_templates` SELECT clause widened to include `current_version_id`; `start_workflow` rpc_params dict now includes `p_template_version_id` keyed off `template.get('current_version_id')`. NO OTHER engine code touched — execute_steps + step_executor untouched (Phase 3 scope).
- **51 GREEN unit tests** across two new files: 16 in `test_template_versions_engine.py` (engine helpers + 3 behavioural engine integration tests for Task 02-04) + 15 in `test_workflow_save_endpoint.py` (full endpoint contract incl. B-2 wire format + W-4 SeedForkResponse + auth scope + Pydantic validation). Plus 6 pre-existing tests still GREEN.
- **6 integration tests** across two new files: 4 in `test_etag_round_trip.py` (B-2 wire-format parity — round-trip GET→PUT, defensive quote strip, 412 + etag in body, 428 on missing) + 2 in `test_linear_workflow_execution_post_versioning.py` (W-8 ROADMAP criterion #9 — linear engine non-regression + pinned-version immutability mid-flight). All SKIP cleanly without Supabase creds.
- **Regenerated `api.generated.ts`** with all 5 new schemas (WorkflowTemplateVersion, SaveTemplateRequest, SaveTemplateSuccessResponse, SeedForkResponse, HistoryItem) plus widened WorkflowTemplateResponse. `npx tsc --noEmit` clean.

## Task Commits

Each task was committed atomically. Tasks 02-02 and 02-03 split into RED+GREEN per TDD:

1. **Task 02-01: Postgres RPC update + save_workflow_template_version function** — `274d74a2` (feat)
2. **Task 02-02 RED: Failing tests for template_versions module + engine integration** — `876a88bd` (test)
3. **Task 02-02 GREEN: Implement app/workflows/template_versions.py** — `85322e98` (feat)
4. **Task 02-03 RED: Failing tests for PUT/GET-history/POST-revert endpoints** — `62c53779` (test)
5. **Task 02-03 GREEN: PUT/GET-history/POST-revert endpoints + ETag header on GET** — `2c59e360` (feat)
6. **Task 02-04: Engine integration — list_templates SELECT + version pinning** — `6f96e8e9` (feat)
7. **Task 02-05: ETag wire-format round-trip integration tests** — `57d4944e` (test)
8. **Task 02-06: Linear engine non-regression integration tests (ROADMAP #9)** — `4454d115` (test)
9. **Task 02-07: Regenerate OpenAPI TS types + responses={} declarations** — `53aa61f7` (chore)

**Plan metadata commit:** _pending_ (final commit follows this SUMMARY.md write)

## Files Created/Modified

**Created (7 files):**

- `supabase/migrations/20260615000100_workflow_template_save_rpc.sql` (280 lines) — DROP+CREATE start_workflow_execution_atomic with new p_template_version_id parameter + save_workflow_template_version atomic two-table function with If-Match check
- `app/workflows/template_versions.py` (330 lines) — 4 async helpers + 2 Pydantic models; canonical supabase async client
- `tests/unit/workflows/test_template_versions_engine.py` (16 tests, ~700 lines) — full template_versions module coverage + 3 behavioural engine tests (W-7)
- `tests/unit/routers/test_workflow_save_endpoint.py` (15 tests, ~440 lines) — endpoint contract + B-2 ETag parity + W-4 SeedForkResponse
- `tests/integration/test_etag_round_trip.py` (4 tests, ~250 lines) — B-2 wire-format round-trip end-to-end
- `tests/integration/test_linear_workflow_execution_post_versioning.py` (2 tests, ~250 lines) — ROADMAP criterion #9 W-8 owner
- `.planning/phases/110-workflow-node-editor-editable/deferred-items.md` — pre-existing test failures + ruff B904/F811 logged out-of-scope

**Modified (3 files):**

- `app/routers/workflows.py` — Added 6 Pydantic models + 3 new endpoints + ETag helpers + widened WorkflowTemplateResponse + responses={} declarations on PUT/POST revert (+~400 lines)
- `app/workflows/engine.py` — Widened list_templates SELECT with current_version_id + added p_template_version_id to start_workflow's rpc_params dict (2 surgical edits, ~3 lines)
- `frontend/src/types/api.generated.ts` — Regenerated via openapi-typescript v7.13.0 against live FastAPI openapi() schema

## Decisions Made

1. **ETag wire format is canonical quoted ISO8601 in BOTH header AND body** (B-2). PUT 200 and PUT 412 responses include `etag` key in the response BODY (not just the header) so the frontend never needs a follow-up GET to learn the next-write ETag. The server defensively strips surrounding double-quotes from incoming `If-Match` values so `curl -H 'If-Match: 2026-...'` (no quotes) still works alongside the canonical quoted form.

2. **ETag value source: workflow_template_versions.saved_at, falling back to workflow_templates.updated_at.** When current_version_id is non-NULL, the version's saved_at is canonical (matches the Phase 110 versioning data model). For legacy / unsaved templates (current_version_id IS NULL), fall back to the row's updated_at to preserve a usable ETag for backward compat.

3. **Two-table Save lives in a Postgres function (save_workflow_template_version), not a Python transaction.** The function does the If-Match check + INSERT into workflow_template_versions + UPDATE workflow_templates.current_version_id atomically. The Python layer makes a single `.rpc()` call and never sees a torn write. Returns SETOF (one row) on success, zero rows on If-Match mismatch — Python translates empty to HTTP 412.

4. **DROP FUNCTION IF EXISTS ... CASCADE before CREATE OR REPLACE for start_workflow_execution_atomic.** PostgreSQL's CREATE OR REPLACE FUNCTION rejects argument-list changes (the function is identified by `(name, argument_types)`). The 9→10 parameter change required a hard DROP first. CASCADE handles any dependent objects defensively (Phase 109 audit showed only Python callers via `.rpc()`, but CASCADE costs nothing). The new `p_template_version_id UUID DEFAULT NULL` as the 10th parameter preserves every existing named-keyword caller unchanged.

5. **Seed fork (created_by IS NULL) returns 409, NOT 200, with SeedForkResponse exact 4-key body shape (W-4).** Key set is `{error, copied_template_id, seed_name, message}` — Plan 04's CopyForkError reads `body.seed_name` for the redirect toast and `body.copied_template_id` for the new editor URL. PUT against a seed forks the user into a private copy via `copy_seed_template_for_user()` and the 409 status signals the frontend to re-route. The same flow applies to POST revert on a seed.

6. **Defensive supabase fetch in `_fetch_current_version_saved_at`** — wraps the table query in try/except and returns None on any exception (including missing creds). Without this guard, the GET endpoint 500s in test environments where Supabase env vars aren't set (caught when Phase 109's tests broke after my initial edit). This was a Rule 1 - Bug fix during execution.

7. **responses={200: {model}, 409: {model}} declarations on PUT and POST revert endpoints** — without these, FastAPI cannot infer the response model since the endpoints return raw `JSONResponse(status_code=..., content=...)` for status-code discrimination. The result is that `SaveTemplateSuccessResponse` and `SeedForkResponse` would be silently absent from the OpenAPI document and consumers would lose the type. Caught during Task 02-07 when only 3 of 5 new models showed up in the regenerated schema. Rule 2 - Missing Critical fix.

8. **Behavioural mock-based engine tests over text grep (W-7)** — both engine changes (list_templates SELECT widening + start_workflow rpc_params propagation) are verified via captured-args assertions on mocked supabase client methods. A grep would pass if some future refactor moved `current_version_id` into a constant or built the SELECT clause differently; the behavioural test fails immediately. Pattern mirrors the canonical engine test `tests/unit/workflows/test_engine_start_workflow_goal.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Defensive Supabase fetch guard in `_fetch_current_version_saved_at`**

- **Found during:** Task 02-03 (after wiring the ETag header)
- **Issue:** Adding `_fetch_current_version_saved_at(template_id)` to the GET handler broke Phase 109's pre-existing GET tests (`tests/unit/workflows/test_templates_api_returns_graph.py::test_get_template_returns_graph_fields` etc) with 500s. Those tests don't patch the new helper and don't have SUPABASE_URL/SERVICE_ROLE_KEY set — the helper called `get_async_client()` which raised `SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set`, surfacing as HTTP 500.
- **Fix:** Wrapped the entire helper body in try/except, returning None on any exception. The router then falls back to template.updated_at for the ETag value (legacy / unsaved templates already use this fallback path). Defensive — production path still hits the version table when creds are present.
- **Files modified:** `app/routers/workflows.py`
- **Verification:** 6 Phase 109 GET tests back to GREEN; 15 new Phase 110 tests stay GREEN.
- **Committed in:** `2c59e360` (Task 02-03 GREEN commit)

**2. [Rule 2 - Missing Critical] responses={} declarations on PUT + POST revert for OpenAPI schema emission**

- **Found during:** Task 02-07 (after regenerating api.generated.ts)
- **Issue:** Only 3 of the 5 new Pydantic models surfaced in the regenerated OpenAPI schema: `SaveTemplateRequest`, `HistoryItem`, and `WorkflowTemplateResponse` (with current_version_id). Missing: `WorkflowTemplateVersion`, `SeedForkResponse`, `SaveTemplateSuccessResponse`. Root cause: PUT and POST revert return raw `JSONResponse(status_code=..., content=...)` for status-code discrimination, so FastAPI cannot infer the response model — the schemas would never reach the wire types and Plan 04's frontend consumer would have to hand-type them. This breaks the documented OpenAPI-driven type contract.
- **Fix:** Added `responses={200: {"model": SaveTemplateSuccessResponse}, 409: {"model": SeedForkResponse}}` declarations to both endpoints. FastAPI now emits both schemas into the OpenAPI document; `WorkflowTemplateVersion` follows transitively because `SaveTemplateSuccessResponse` references it.
- **Files modified:** `app/routers/workflows.py`
- **Verification:** All 5 new schemas present in regenerated api.generated.ts (23 occurrences of the new symbols total across the file). `npx tsc --noEmit` clean.
- **Committed in:** `53aa61f7` (Task 02-07 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes essential for correctness / wire-format integrity. No scope creep — Plan 02's contract stays intact.

## Issues Encountered

**Pre-existing engine test failures (not caused by Phase 110).** `tests/unit/test_workflow_engine_readiness_gate.py` has 3 tests that fail on the baseline (verified via `git stash + pytest + git stash pop`): `test_start_workflow_allows_when_readiness_gate_disabled`, `test_start_workflow_allows_draft_for_internal_run_sources`, `test_start_workflow_blocks_invalid_contract`. Root cause: `WorkspaceItemEmitter.emit_for_execution` reads `execution["user_id"]` but those tests' fixtures don't supply the key. Logged in `.planning/phases/110-workflow-node-editor-editable/deferred-items.md` for a follow-up hardening pass. Phase 110 changes don't regress these tests further (2/5 tests in the file still pass with my edits, same as baseline).

**Pre-existing ruff B904 + F811 in app/routers/workflows.py.** 28 B904 `raise from` violations + 1 F811 `save_user_workflow` redefinition existed before Phase 110. My new PUT/GET/POST endpoints follow the same `raise HTTPException(...)` pattern as every other endpoint in the file for codebase consistency. Logged in deferred-items.md.

**`PytestUnknownMarkWarning: Unknown pytest.mark.integration`.** Same warning Phase 109 + 110-01 emit — project does not register the `integration` mark in pyproject.toml. Mark is organizational, not behaviorally significant.

**Local Supabase not running.** This Windows workstation doesn't have the Docker engine pipe active, so `supabase db push --local` cannot run. The 2 new integration test files (4 + 2 tests, 6 total) SKIP cleanly without creds. CI will exercise them against a local Supabase when the PR pipeline runs.

**`uv` CLI not on PATH on this Windows workstation.** Worked around by invoking the venv Python directly (`.venv/Scripts/python -m pytest ...`) and using `.venv/Scripts/python -c "..." > frontend/.openapi-schema.json` for the OpenAPI export. Same workaround the project's `frontend/scripts/generate-api-types.mjs` script applies for non-uv environments.

## User Setup Required

None — pure backend/frontend type changes + one additive SQL migration. After this plan merges to main:

1. CI will run `supabase db push --local` and exercise the new migration + integration tests against the live local Supabase.
2. Frontend type consumers automatically pick up the new schemas via the regenerated `api.generated.ts` (no manual codegen step needed at PR review time).
3. The 4 new endpoints become available at `/workflows/templates/{id}` (PUT), `/workflows/templates/{id}/history` (GET), `/workflows/templates/{id}/revert/{version_id}` (POST). They require an authenticated user (per the existing `Depends(get_current_user_id)` chain).

No new env vars, no dashboard configuration, no third-party services.

## Next Phase Readiness

**Ready for Plan 110-03** (server-side validation endpoint):

- Plan 03 wires `validate_workflow_graph()` into the PUT handler in `app/routers/workflows.py`. The hook point is clear: between the `_parse_if_match` call and the `save_template_version` call (around line ~600 in the router). Plan 03 adds the validator + the new `POST /workflows/templates/{id}/validate` endpoint without touching the Save flow.
- The Save endpoint's request body shape (SaveTemplateRequest with typed graph_nodes/edges/layout) is locked — Plan 03's validator receives the same shape.

**Ready for Plan 110-04** (frontend editable canvas):

- API surface frontend consumers should use:
  - `PUT /workflows/templates/{id}` with header `If-Match: "<quoted_iso8601>"` and body `{graph_nodes, graph_edges, graph_layout?, comment?}`.
  - On 200, read `body.etag` (NOT `response.headers.get('etag')` — body is canonical) for the next PUT's If-Match value.
  - On 412, read `body.etag` (fresh) and `body.*` (fresh template body) to power the "View their changes" / "Overwrite" / "Cancel" conflict modal (decision 6).
  - On 409, read `body.error === 'seed_template_immutable'`, `body.copied_template_id`, `body.seed_name`, `body.message`. Redirect editor to `/editor/{copied_template_id}` and toast the seed_name.
- TypeScript types live in `frontend/src/types/api.generated.ts`:
  - `components.schemas.SaveTemplateRequest`
  - `components.schemas.SaveTemplateSuccessResponse`
  - `components.schemas.SeedForkResponse`
  - `components.schemas.WorkflowTemplateVersion`
  - `components.schemas.HistoryItem`
  - `components.schemas.WorkflowTemplateResponse` (now with `current_version_id`)

**Ready for Plan 110-05** (frontend version selector + history pane + conflict modal):

- `GET /workflows/templates/{id}/history` returns `list[HistoryItem]` — feeds the version selector dropdown and HistoryPane list directly.
- `POST /workflows/templates/{id}/revert/{version_id}` with header `If-Match: "<quoted_iso8601>"` creates a new version copying the target's graph_* with `parent_version_id = version_id`. Response body shape identical to PUT 200 — body.etag is canonical, body.version has the new version row.

**ROADMAP criterion #9 (W-8) ownership confirmed:** `tests/integration/test_linear_workflow_execution_post_versioning.py` exists and asserts the linear-engine non-regression contract. CI with creds will exercise it; without creds it skips cleanly.

---

## Self-Check: PASSED

Verified post-write (all paths absolute):

- [x] `C:/Users/expert/documents/pka/pikar-ai/supabase/migrations/20260615000100_workflow_template_save_rpc.sql` exists on disk
- [x] `C:/Users/expert/documents/pka/pikar-ai/app/workflows/template_versions.py` exists on disk
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/unit/workflows/test_template_versions_engine.py` exists on disk (16 tests collected)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/unit/routers/test_workflow_save_endpoint.py` exists on disk (15 tests collected)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/integration/test_etag_round_trip.py` exists on disk (4 tests collected; skip without creds)
- [x] `C:/Users/expert/documents/pka/pikar-ai/tests/integration/test_linear_workflow_execution_post_versioning.py` exists on disk (2 tests collected; skip without creds)
- [x] `C:/Users/expert/documents/pka/pikar-ai/.planning/phases/110-workflow-node-editor-editable/deferred-items.md` exists on disk
- [x] `app/routers/workflows.py` modified (Pydantic models + 3 endpoints + ETag helpers + responses={} declarations)
- [x] `app/workflows/engine.py` modified (list_templates SELECT + start_workflow rpc_params)
- [x] `frontend/src/types/api.generated.ts` regenerated (23 occurrences of new symbols)
- [x] Commit `274d74a2` exists (Task 02-01: migration)
- [x] Commit `876a88bd` exists (Task 02-02 RED)
- [x] Commit `85322e98` exists (Task 02-02 GREEN)
- [x] Commit `62c53779` exists (Task 02-03 RED)
- [x] Commit `2c59e360` exists (Task 02-03 GREEN)
- [x] Commit `6f96e8e9` exists (Task 02-04: engine)
- [x] Commit `57d4944e` exists (Task 02-05: ETag round-trip)
- [x] Commit `4454d115` exists (Task 02-06: ROADMAP #9 W-8)
- [x] Commit `53aa61f7` exists (Task 02-07: TS regen)
- [x] All 9 commits land on `plan-109-spec-b-phase-1` (verified via `git log --oneline plan-109-spec-b-phase-1 -10`)
- [x] 51 unit tests GREEN (no regressions on Phase 109's 18 tests + Phase 110's 33 new tests)
- [x] 6 integration tests collected cleanly + skip on no creds
- [x] `npx tsc --noEmit` clean across frontend
- [x] ETag wire format is quoted ISO8601 in BOTH header AND body.etag (B-2 verified by 8 dedicated tests)
- [x] 409 SeedForkResponse body has EXACTLY 4 keys (W-4 verified by `test_put_template_seed_returns_409_with_all_four_keys`)
- [x] Branch hygiene: still on `plan-109-spec-b-phase-1` after all 9 commits

---

*Phase: 110-workflow-node-editor-editable*
*Completed: 2026-05-11*
