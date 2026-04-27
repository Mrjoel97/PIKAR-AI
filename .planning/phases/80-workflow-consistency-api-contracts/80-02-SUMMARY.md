---
phase: 80-workflow-consistency-api-contracts
plan: 02
subsystem: api
tags: [openapi, typescript, codegen, ci, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 80-workflow-consistency-api-contracts
    provides: Plan 01 workflow execution idempotency and atomic triggers
provides:
  - OpenAPI-to-TypeScript codegen pipeline (no server required)
  - Committed baseline api.generated.ts from FastAPI OpenAPI spec (22,884 lines)
  - CI job that fails on generated type drift
  - workflows.ts imports from generated types for WorkflowTemplate, StartWorkflowResponse, WorkflowStep
affects:
  - Any frontend service file migration to generated types (follow same pattern)
  - Backend router changes that affect OpenAPI schema (CI will catch drift)

# Tech tracking
tech-stack:
  added: [openapi-typescript@7.13.0]
  patterns:
    - Export FastAPI OpenAPI schema via uv (no server needed) then pipe through openapi-typescript
    - Windows .cmd wrapper handled by spawnSync+shell:true with temp Python script file to avoid quoting issues
    - from __future__ import annotations removed from router files to allow Pydantic TypeAdapter to resolve annotations at schema generation time

key-files:
  created:
    - frontend/scripts/generate-api-types.mjs
    - frontend/src/types/api.generated.ts
  modified:
    - frontend/package.json (added openapi-typescript devDependency + generate:types script)
    - frontend/src/services/workflows.ts (import from generated types)
    - .github/workflows/ci.yml (api-types-check job)
    - .gitignore (frontend/.openapi-schema.json exclusion)
    - app/routers/**/*.py (34 files: removed from __future__ import annotations)

key-decisions:
  - "OpenAPI schema exported via uv run python without server; temp .py file avoids shell quoting issues on Windows"
  - "from __future__ import annotations removed from all 34 app/routers/**/*.py files — deferred annotation evaluation prevents Pydantic TypeAdapter from resolving ForwardRefs during schema generation"
  - "WorkflowExecution and WorkflowExecutionDetails kept hand-maintained — backend returns execution as {[key: string]: unknown} in OpenAPI spec, not a typed Pydantic model"
  - "WorkflowTrigger and all trigger types kept hand-maintained — no named Pydantic schemas exposed for triggers in OpenAPI spec"

patterns-established:
  - "Pattern: import type { components } from '@/types/api.generated' then use components['schemas']['ModelName'] for type aliasing"
  - "Pattern: TODO(ARCH-04) comment on hand-maintained types to track which backend schemas need to be promoted to named Pydantic models"

requirements-completed: [ARCH-04]

# Metrics
duration: 50min
completed: 2026-04-27
---

# Phase 80 Plan 02: Workflow Consistency & API Contracts — OpenAPI Codegen Summary

**OpenAPI-to-TypeScript codegen via uv+openapi-typescript with CI drift check; 3 workflow types now sourced from 22,884-line generated schema**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-04-27T12:20:00Z
- **Completed:** 2026-04-27T13:10:00Z
- **Tasks:** 2
- **Files modified:** 43 (34 router files + 4 core files + package.json + package-lock.json + .gitignore + api.generated.ts)

## Accomplishments

- Codegen script exports FastAPI OpenAPI schema without running the server (uv run python) and pipes through openapi-typescript to produce frontend/src/types/api.generated.ts (22,884 lines)
- CI job `api-types-check` added to ci.yml; runs generate:types and fails with actionable error if committed types drift from freshly generated ones
- 3 hand-maintained workflow types replaced with generated aliases: WorkflowTemplate → WorkflowTemplateResponse, StartWorkflowResponse (exact match), WorkflowStep → WorkflowHistoryItem
- TypeScript type check (`tsc --noEmit`) passes with zero errors after migration

## Task Commits

1. **Task 1: Set up openapi-typescript tooling, generate types, add CI check** - `e8c2b00e` (feat)
2. **Task 2: Replace hand-maintained workflow types with generated imports** - `ed048eb7` (feat)

## Files Created/Modified

- `frontend/scripts/generate-api-types.mjs` - Codegen script: exports OpenAPI schema via uv, runs openapi-typescript, handles Windows .cmd wrappers via spawnSync+shell+temp Python file
- `frontend/src/types/api.generated.ts` - 22,884-line auto-generated TypeScript types from FastAPI OpenAPI spec
- `frontend/package.json` - openapi-typescript@7.13.0 devDependency, generate:types script
- `frontend/package-lock.json` - Lockfile updated
- `frontend/src/services/workflows.ts` - WorkflowTemplate, StartWorkflowResponse, WorkflowStep now from generated types; remaining types kept with TODO(ARCH-04) comments
- `.github/workflows/ci.yml` - api-types-check job added (parallel with existing gates)
- `.gitignore` - frontend/.openapi-schema.json excluded
- `app/routers/**/*.py` (34 files) - `from __future__ import annotations` removed to fix Pydantic TypeAdapter ForwardRef resolution

## Decisions Made

- **Script temp file for Python code**: On Windows, passing multi-word strings through shell quoting to `uv run python -c "..."` breaks. Writing Python code to a temp `.py` file and invoking `uv run python tempfile.py` avoids this.
- **spawnSync + shell:true on Windows**: Node's execFileSync cannot directly execute `.cmd` files; spawnSync with shell:true lets the OS shell resolve uv.cmd/npx.cmd correctly.
- **WorkflowExecution kept hand-maintained**: The backend's OpenAPI spec exposes `execution` in WorkflowExecutionResponse as `{[key: string]: unknown}` (no named Pydantic model). The typed hand-maintained interface is more useful; alignment deferred to backend work.
- **WorkflowTrigger types kept hand-maintained**: No named Pydantic schemas for triggers appear in the spec (likely unregistered body/response types). All get TODO(ARCH-04) comments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed `from __future__ import annotations` from 34 router files to fix Pydantic TypeAdapter ForwardRef errors**
- **Found during:** Task 1 (running generate:types script)
- **Issue:** FastAPI + Pydantic cannot resolve `ForwardRef('PersonaBody')`, `ForwardRef('StreamingResponse')`, `ForwardRef('CreateDepartmentTaskRequest')`, etc. when `from __future__ import annotations` defers all annotation evaluation in router files. `app.openapi()` raises `PydanticUserError: TypeAdapter is not fully defined`.
- **Fix:** Removed `from __future__ import annotations` from all 34 affected files under `app/routers/`. Python 3.10+ supports `X | Y` union syntax natively; these files don't require the import.
- **Files modified:** 34 files across `app/routers/` and `app/routers/admin/`
- **Verification:** `uv run python -c 'from app.fast_api_app import app; app.openapi()'` succeeds and produces 22,884-line schema
- **Committed in:** `e8c2b00e` (Task 1 commit)

**2. [Rule 1 - Bug] Updated generate-api-types.mjs to handle Windows .cmd wrappers**
- **Found during:** Task 1 (running generate:types on Windows dev machine)
- **Issue:** `execFileSync('uv', ...)` raises `EINVAL` on Windows because uv is installed as `uv.cmd` (a Windows Command Script) that cannot be directly executed by Node's execFileSync. The `-c` argument also broke through shell quoting.
- **Fix:** Switched to `spawnSync('uv', args, { shell: true })` on Windows; write Python code to a temp `.py` file to avoid shell quoting issues with multi-word `-c` arguments.
- **Files modified:** `frontend/scripts/generate-api-types.mjs`
- **Verification:** `node frontend/scripts/generate-api-types.mjs` succeeds on Windows; Linux CI uses `shell: false` path.
- **Committed in:** `e8c2b00e` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2x Rule 1 - Bug)
**Impact on plan:** Both fixes required for the plan to function. The router annotation fix is a genuine bug in the app (Pydantic fails at schema generation time). The Windows fix is an environment compatibility issue. No scope creep.

## Issues Encountered

- uv not on PATH in bash shell (only in PowerShell/cmd on this Windows machine). All Node.js and Python invocations ran via `powershell.exe -Command` for consistency.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pattern established: other service files (approvals.ts, briefing.ts, initiatives.ts) can follow the same `import type { components }` pattern when migrating to generated types
- CI now fails automatically when backend schema changes without updating committed types
- Backend work needed to promote WorkflowExecution and WorkflowTrigger Pydantic models to named schemas (TODO(ARCH-04) tags added as breadcrumbs)

---
*Phase: 80-workflow-consistency-api-contracts*
*Completed: 2026-04-27*
