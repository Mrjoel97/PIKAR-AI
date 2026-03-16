# Phase 4 Context: Frontend-Backend Alignment

## Why This Phase Exists

Phase 3 removed the worst async blocking inside the service layer, but the user-facing integration seams are still uneven. Several frontend pages bypass the authenticated API helpers or bypass the backend contract entirely, and the workflow SSE path still lacks heartbeat/keepalive protection for Cloud Run.

## Requirement Mapping

- FE-01: CORS headers for `x-pikar-persona`, `x-user-id`, and `user-id`
- FE-02: Departments page uses `fetchWithAuth()` instead of raw `fetch()`
- FE-03: Approval page uses the correct auth model for the actual route shape
- FE-04: Frontend workflow execution types match backend response models
- FE-05: Initiative API responses surface metadata-backed fields where the UI expects them
- FE-06: Workflow SSE stays alive behind Cloud Run / proxy idle timeouts

## What The Audit Found

### Already aligned or mostly aligned

- `app/fast_api_app.py` already includes `x-pikar-persona`, `x-user-id`, and `user-id` in `_cors_allowed_headers`.
- `tests/unit/test_product_truth_guards.py` already asserts those CORS headers are present.
- `app/services/initiative_operational_state.py` already promotes operational-state metadata into top-level initiative fields, and `app/routers/initiatives.py` returns initiatives through `InitiativeService` for list/detail endpoints.

### Concrete gaps

1. Departments frontend is unauthenticated against authenticated endpoints.
   - `frontend/src/app/departments/page.tsx` uses raw `fetch()` for list/toggle/tick.
   - `app/routers/departments.py` requires `get_current_user_id` on those routes, so the page is prone to 401/auth drift.

2. Approval flow needs nuance, not a blind auth retrofit.
   - The only approval UI found is `frontend/src/app/approval/[token]/page.tsx`.
   - `app/routers/approvals.py` treats `/approvals/{token}` and `/approvals/{token}/decision` as public token-gated routes, while `/approvals/pending/list` is the authenticated route.
   - The roadmap wording should be interpreted as “use the correct authenticated helper on authenticated approval flows” and preserve the public magic-link approval page.

3. Initiative detail bypasses the backend contract.
   - `frontend/src/app/dashboard/initiatives/[id]/page.tsx` reads and writes initiatives directly through the browser Supabase client.
   - That bypasses the normalized API response shape from `app/routers/initiatives.py` and `app/services/initiative_operational_state.py`, so FE-05 is only partially realized in practice.

4. Workflow TypeScript types lag behind the backend response model.
   - `frontend/src/services/workflows.ts` defines narrower `WorkflowExecution` / `WorkflowStep` shapes than `app/routers/workflows.py` returns.
   - `WorkflowHistoryItem` on the backend includes optional fields like `phase_index`, `step_index`, `tool_name`, `trust_class`, `verification_status`, `evidence_refs`, and `last_failure_reason`.
   - UI code is compensating with casts in workflow pages/components instead of aligned types.

5. Workflow SSE still has no heartbeat/keepalive strategy.
   - `app/routers/workflows.py` streams status snapshots every two seconds, but does not emit heartbeat frames or proxy-safe SSE headers.
   - `frontend/src/services/workflows.ts` manually parses the stream and does not account for keepalive comments/frames.
   - `app/fast_api_app.py` also exposes another SSE path without heartbeat support, reinforcing that proxy timeout risk is real.

## Files Most Likely In Scope

Backend:
- `app/fast_api_app.py`
- `app/routers/departments.py`
- `app/routers/approvals.py`
- `app/routers/workflows.py`
- `app/routers/initiatives.py`
- `app/services/initiative_operational_state.py`

Frontend:
- `frontend/src/services/api.ts`
- `frontend/src/services/workflows.ts`
- `frontend/src/services/initiatives.ts`
- `frontend/src/app/departments/page.tsx`
- `frontend/src/app/approval/[token]/page.tsx`
- `frontend/src/app/dashboard/initiatives/[id]/page.tsx`
- `frontend/src/app/dashboard/workflows/active/page.tsx`
- `frontend/src/components/workflows/WorkflowStepTimeline.tsx`

Tests likely in scope:
- `tests/unit/test_product_truth_guards.py`
- `tests/unit/test_initiative_operational_state.py`
- `frontend/src/__tests__/services/api.test.ts`
- `frontend/src/__tests__/services/initiatives.test.ts`
- new frontend/workflow/SSE regression coverage as needed

## Planning Notes

- FE-01 should be treated as preserve-and-verify, not as fresh implementation work.
- FE-03 should not force authenticated fetch onto the token approval page; instead, the plan should separate public token approval from authenticated pending-approval UX.
- Prefer routing frontend data access through typed service wrappers and backend API contracts rather than direct browser Supabase mutations on dashboard pages.
- Phase 4 should also clean up backend routes that are now on critical UI paths if they still perform blocking Supabase `.execute()` calls.
