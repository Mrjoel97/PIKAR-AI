---
phase: 37-sme-department-coordination
plan: "03"
subsystem: frontend
tags: [nextjs, react, typescript, departments, task-handoffs, health-indicators, ux]

# Dependency graph
requires:
  - phase: 37-sme-department-coordination
    plan: "01"
    provides: POST /departments/tasks, GET /departments/{id}/tasks, PATCH /departments/tasks/{id}/status, GET /departments/health endpoints
provides:
  - /departments/[deptId] detail page with KPI cards, health indicator, inbound/outbound task tabs
  - Task creation form for cross-department handoffs
  - Health badges (green/yellow/red) on departments list page
  - Clickable department names linking to detail pages
affects:
  - All personas who access the /departments route
  - SME users creating and managing cross-department task handoffs

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Next.js async params via useEffect + Promise.then (Next.js 15 pattern)
    - Lazy-load tab data with outboundLoaded flag to avoid redundant fetches
    - Non-blocking health fetch with .catch fallback to empty array on list page
    - Status action buttons inline in task cards (no separate action menu)

key-files:
  created:
    - frontend/src/app/departments/[deptId]/page.tsx
  modified:
    - frontend/src/services/departments.ts
    - frontend/src/app/departments/page.tsx

key-decisions:
  - "Async params resolved via useEffect+Promise.then for Next.js 15 compatibility (params is now a Promise)"
  - "Health fetch on departments list page is non-blocking — falls back to empty array so list still loads if health endpoint is slow"
  - "Create task form embedded inline in detail page (not a separate route) — matches existing modal patterns in the codebase"
  - "Outbound tasks lazily loaded on tab switch with a loaded-flag to prevent redundant API calls on re-renders"

patterns-established:
  - "Health badge pattern: HEALTH_CONFIG map with dot/text/bg/gradient per status — reusable for other health-bearing entities"
  - "Task card with inline status action button (Start/Complete) — avoids dropdowns for simple 3-state transitions"

requirements-completed: [DEPT-01, DEPT-02]

# Metrics
duration: 5min
completed: 2026-04-03
---

# Phase 37 Plan 03: SME Department Frontend Summary

**Department detail page with health indicator, 4 KPI cards, inbound/outbound task tabs, inline task creation form, and health badges on the departments list — consuming the Plan 01 API endpoints**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T23:06:45Z
- **Completed:** 2026-04-03T23:11:31Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Extended `frontend/src/services/departments.ts` with 4 new API functions (`getDepartmentTasks`, `createDepartmentTask`, `updateDepartmentTaskStatus`, `getDepartmentHealth`) and 3 new TypeScript interfaces (`DepartmentTask`, `DepartmentHealthSummary`, `CreateDepartmentTaskParams`)
- Created `/departments/[deptId]/page.tsx` (665 lines): health indicator badge, 4 KPI MetricCards (Active Tasks, Completed 30d, Completion Rate, Health Status), inbound/outbound task tabs, task cards with from/to department names, priority badge, status badge, overdue due date highlighting, Start/Complete action buttons
- Inline Create Handoff Task form: target department selector (excluding current), priority dropdown, due date input, success/error feedback, auto-closes after creation
- Updated `departments/page.tsx` OverviewTab to fetch health in parallel with department list, show green/yellow/red health dot + label + active task count per department, and make department names clickable `Link` components to `/departments/[id]`

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend departments service and create department detail page** - `ebd7b72` (feat)
2. **Task 2: Add health badges and department detail navigation to departments list** - `f0b0c9a` (feat)

## Files Created/Modified

- `frontend/src/app/departments/[deptId]/page.tsx` — Department detail page (665 lines): health badge, KPIs, inbound/outbound task tabs, task cards with status actions, inline create form
- `frontend/src/services/departments.ts` — Added DepartmentTask, DepartmentHealthSummary, CreateDepartmentTaskParams interfaces + getDepartmentTasks, createDepartmentTask, updateDepartmentTaskStatus, getDepartmentHealth functions (201 lines total)
- `frontend/src/app/departments/page.tsx` — Added getDepartmentHealth fetch, healthData state, OverviewTab health badges (health dot + label + active count), department name Link navigation (518 lines total)

## Decisions Made

- **Next.js 15 async params**: `params` in Next.js 15 App Router is a `Promise<{deptId: string}>`. Resolved via `useEffect` + `params.then()` rather than `use(params)` to keep the component compatible with the existing `'use client'` pattern in the codebase.
- **Non-blocking health fetch on list page**: The `getDepartmentHealth()` call on the list page uses `.catch(() => [])` so a slow or erroring health endpoint never blocks the department list from rendering. Health badges simply don't appear if the fetch fails.
- **Inline form over modal**: The task creation form is inline (toggled by a button) rather than a full modal overlay — consistent with the codebase's pattern of inline expandable forms and avoids adding a modal library dependency.
- **Outbound tasks lazily loaded**: Outbound tasks are only fetched when the user clicks the "Outbound Tasks" tab, with an `outboundLoaded` flag preventing redundant re-fetches on subsequent renders.

## Deviations from Plan

None — plan executed exactly as written. The task creation form was already included in Task 1 (the detail page) as specified by the plan structure, and Task 2 focused exclusively on the departments list page updates.

## Self-Check: PASSED

- FOUND: frontend/src/app/departments/[deptId]/page.tsx (665 lines, >= 100 min_lines)
- FOUND: frontend/src/services/departments.ts exports: createDepartmentTask, getDepartmentTasks, updateDepartmentTaskStatus, getDepartmentHealth (4/4)
- FOUND: frontend/src/app/departments/page.tsx contains: health_status (via healthStatus), getDepartmentHealth, Link to /departments/
- FOUND: commit ebd7b72
- FOUND: commit f0b0c9a
- VERIFIED: detail page contains getDepartmentTasks, getDepartmentHealth, healthStatus (3 matches >= 3)
- VERIFIED: list page contains getDepartmentHealth, healthStatus, Link/departments (3 matches >= 2)

---
*Phase: 37-sme-department-coordination*
*Completed: 2026-04-03*
