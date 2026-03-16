# Phase 4 Summary: Frontend-Backend Alignment

## Outcome

Completed the Phase 4 frontend-backend alignment plan. Protected frontend pages now route through shared API helpers, initiative detail consumes the backend's normalized contract, workflow execution views use aligned TypeScript types and heartbeat-safe SSE, and the approval surface now explicitly preserves the public token link while keeping authenticated approval/dashboard actions on authenticated helpers.

## What Changed

- Preserved the existing CORS/header contract in `app/fast_api_app.py` and kept `x-pikar-persona`, `x-user-id`, and `user-id` as the browser-facing header truth.
- Routed protected frontend pages through shared service helpers instead of page-level request setup:
  - added `frontend/src/services/departments.ts`
  - expanded `frontend/src/services/initiatives.ts`
  - added `frontend/src/services/approvals.ts`
  - extended `frontend/src/services/api.ts` with a shared public-fetch path alongside the authenticated helper path
- Repaired the departments and approval integration seams:
  - `frontend/src/app/departments/page.tsx` now uses authenticated helpers
  - `frontend/src/app/approval/[token]/page.tsx` now uses a dedicated public approvals service instead of inline raw `fetch()` calls
  - `app/routers/departments.py` and `app/routers/approvals.py` now use `execute_async()` on active UI paths
- Removed direct browser Supabase access from `frontend/src/app/dashboard/initiatives/[id]/page.tsx` and aligned it to the backend initiative contract via typed service calls and backend endpoints in `app/routers/initiatives.py`.
- Aligned workflow contract and SSE behavior across:
  - `frontend/src/services/workflows.ts`
  - `frontend/src/components/workflows/WorkflowExecutionCard.tsx`
  - `frontend/src/components/workflows/WorkflowStepTimeline.tsx`
  - `frontend/src/app/dashboard/workflows/active/page.tsx`
  - `frontend/src/app/dashboard/workflows/completed/page.tsx`
  - `app/routers/workflows.py`
  - `app/fast_api_app.py`
- Hardened workflow streaming with proxy-safe SSE headers, initial connection comments, and keepalive comments so idle Cloud Run/proxy windows do not silently sever user-facing streams.

## Verification

Passed checks:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_initiative_operational_state.py tests/integration/test_workflow_policy_endpoints.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/test_product_truth_guards.py -q`
- `uv run python -` with `py_compile.compile(...)` for:
  - `app/routers/departments.py`
  - `app/routers/initiatives.py`
  - `app/routers/workflows.py`
  - `app/routers/approvals.py`
  - `app/fast_api_app.py`
- `npm run test -- src/__tests__/services/api.test.ts --run`
- `npm run build`

Notes:
- The approval requirement is satisfied by the real product split: `/approval/[token]` remains a public token-gated page, while authenticated approval actions stay on authenticated dashboard/workflow request paths.
- Sandboxed pytest and frontend verification remain environment-sensitive on this workstation, so some checks required unrestricted runs.

## Follow-up

- Phase 5 planning should focus on the security hardening slice next.
- Refresh `uv.lock` in an environment with full `uv lock` support.
- Upgrade the local Supabase CLI so future database verification can stay on the supported local command path.
