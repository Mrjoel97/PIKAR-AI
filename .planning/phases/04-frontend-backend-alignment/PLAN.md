# Plan: Phase 4 - Frontend-Backend Alignment

**Objective:** Align the authenticated frontend with the backend contract so user-facing pages stop failing on auth/header mismatches, initiative pages use the normalized API shape, and workflow SSE survives proxy idle windows.

## Scope Rules
- Preserve the existing product flows; this phase is about contract alignment, not feature expansion.
- Keep the public token approval-link experience public unless a route is explicitly authenticated.
- Prefer typed frontend service wrappers over page-level raw `fetch()` or browser Supabase mutations.
- Reuse existing backend normalization (`normalize_operational_state`) instead of duplicating business logic in the browser.
- Add narrow verification for each repaired integration seam.

## 1. Lock In Existing Header/CORS Truth
**Goal:** treat FE-01 as an invariant that Phase 4 must preserve.

**Tasks:**
- Keep `app/fast_api_app.py` CORS header allowlist aligned with `x-pikar-persona`, `x-user-id`, and `user-id`.
- Carry forward or extend the existing test coverage that asserts those headers remain allowed.
- Avoid touching this area unless a frontend request path proves another header is required.

**Files:**
- `app/fast_api_app.py`
- `tests/unit/test_product_truth_guards.py`
- `frontend/src/services/api.ts`

## 2. Route Protected Frontend Pages Through Authenticated API Helpers
**Goal:** close FE-02 and the authenticated portion of FE-03.

**Tasks:**
- Replace raw `fetch()` calls in `frontend/src/app/departments/page.tsx` with an authenticated service/helper path.
- If needed, add a small dedicated departments service module rather than repeating request setup inline.
- Audit approval-related UI surfaces and split them into:
  - public token approval link flow that remains unauthenticated
  - authenticated pending-approval or dashboard flows that must use `fetchWithAuth()`
- Align backend department/approval routes that sit on these UI paths so their auth model and response shape match the frontend usage.

**Files:**
- `frontend/src/app/departments/page.tsx`
- `frontend/src/app/approval/[token]/page.tsx`
- `frontend/src/services/api.ts`
- optional `frontend/src/services/departments.ts`
- `app/routers/departments.py`
- `app/routers/approvals.py`

## 3. Remove Direct Browser Supabase Access From Initiative Detail
**Goal:** close FE-05 by making the frontend consume the backend's normalized initiative contract.

**Tasks:**
- Refactor `frontend/src/app/dashboard/initiatives/[id]/page.tsx` to read initiative detail through `frontend/src/services/initiatives.ts` instead of direct Supabase `.from('initiatives')` calls.
- Route initiative updates/deletes and journey-input persistence through backend API helpers or add the missing typed endpoints needed for those operations.
- Ensure the page can rely on top-level fields such as `goal`, `success_criteria`, `owner_agents`, `primary_workflow`, `current_phase`, `verification_status`, and `trust_summary`.
- Preserve the metadata payload for backward compatibility, but stop making it the only source of truth for rendered operational data.

**Files:**
- `frontend/src/app/dashboard/initiatives/[id]/page.tsx`
- `frontend/src/services/initiatives.ts`
- `app/routers/initiatives.py`
- `app/services/initiative_service.py`
- `app/services/initiative_operational_state.py`

## 4. Align Workflow Types and SSE Contracts
**Goal:** close FE-04 and FE-06 together because both live on the workflow execution path.

**Tasks:**
- Update `frontend/src/services/workflows.ts` interfaces so they match `WorkflowExecutionResponse` / `WorkflowHistoryItem` from `app/routers/workflows.py`.
- Remove unsafe casts in the active/completed workflow pages and let components consume the stronger types directly.
- Add heartbeat/keepalive support on the backend workflow SSE endpoint, including proxy-safe headers if needed.
- Update the frontend SSE parser to ignore keepalive frames/comments cleanly and continue handling status/error events.
- Review the other FastAPI SSE path in `app/fast_api_app.py` for the same proxy-timeout weakness and align behavior if it is part of the user-facing surface.

**Files:**
- `frontend/src/services/workflows.ts`
- `frontend/src/app/dashboard/workflows/active/page.tsx`
- `frontend/src/app/dashboard/workflows/completed/page.tsx`
- `frontend/src/components/workflows/WorkflowStepTimeline.tsx`
- `app/routers/workflows.py`
- `app/fast_api_app.py`

## 5. Verification
**Backend checks:**
- `uv run pytest tests/unit/test_product_truth_guards.py -q`
- `uv run pytest tests/unit/test_initiative_operational_state.py -q`
- add/update targeted workflow SSE or approval/department route tests as needed

**Frontend checks:**
- `npm run test -- src/__tests__/services/api.test.ts --run`
- `npm run test -- src/__tests__/services/initiatives.test.ts --run`
- add/update targeted tests for departments/authenticated fetch usage and workflow/SSE typing behavior
- `npm run build`

**Manual/contract checks:**
- confirm Departments page sends authenticated requests and no longer 401s
- confirm initiative detail renders normalized top-level operational fields without relying on raw metadata unpacking
- confirm workflow active view stays connected through idle periods and tolerates keepalive frames
- confirm public token approval links still work without requiring a logged-in session
