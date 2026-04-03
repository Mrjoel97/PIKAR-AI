# Deferred Items — Phase 32

## Pre-existing Issues (Out of Scope)

### 1. [Workflow API Pattern] workflows/templates/page.tsx line 94
- **Found during:** Plan 02, Task 2
- **Issue:** `startWorkflow` is called directly rather than via `start()` from "workflow/api"
- **Scope:** Pre-existing pattern, not caused by plan 02 changes
- **Recommended fix:** Replace direct `startWorkflow` call with `start()` from "workflow/api" to register the run and get a runId
- **Files:** `frontend/src/app/dashboard/workflows/templates/page.tsx`
