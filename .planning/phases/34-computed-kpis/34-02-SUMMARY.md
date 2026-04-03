---
phase: 34-computed-kpis
plan: "02"
subsystem: ui
tags: [react, nextjs, kpi, persona, hooks, components, frontend]

# Dependency graph
requires:
  - phase: 34-computed-kpis/34-01
    provides: GET /kpis/persona endpoint returning {persona, kpis:[{label,value,unit}]}
provides:
  - useKpis React hook fetching /kpis/persona with loading/error states
  - KpiBar shared component rendering label+value pills for all 4 persona shells
  - All 4 persona shell headers showing real computed KPI values from the backend
affects: [35-teams-rbac, 36-enterprise-governance, 37-sme-dept-coordination]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useKpis hook: cancellation guard via cancelled flag prevents state updates after unmount"
    - "KpiBar: pure presentational component, all data from hook — no internal state or effects"
    - "Case-insensitive label matching between config.kpiLabels and API response"

key-files:
  created:
    - frontend/src/hooks/useKpis.ts
    - frontend/src/components/personas/KpiBar.tsx
  modified:
    - frontend/src/components/personas/SolopreneurShell.tsx
    - frontend/src/components/personas/StartupShell.tsx
    - frontend/src/components/personas/SmeShell.tsx
    - frontend/src/components/personas/EnterpriseShell.tsx

key-decisions:
  - "KpiBar is purely presentational — useKpis hook owns all fetch logic, shells own the data, KpiBar only renders"
  - "Case-insensitive label matching handles any capitalisation differences between config and API response"
  - "Cancellation guard in useKpis prevents setState after unmount for shell components that unmount on persona switch"
  - "No refetch interval — KPIs refresh on shell mount (page navigation), satisfying the 60s freshness requirement"

patterns-established:
  - "KPI display pattern: useKpis() at shell level, pass kpis+isLoading down to KpiBar — no prop drilling beyond one level"
  - "animate-pulse on loading indicator span, not the whole pill — keeps pill size stable during load"

requirements-completed: [KPI-01, KPI-02, KPI-03, KPI-04, KPI-05]

# Metrics
duration: 4min
completed: 2026-04-03
---

# Phase 34 Plan 02: Computed KPIs Frontend Summary

**useKpis hook + KpiBar component wiring all 4 persona shell headers to display real computed KPI values (label+value pills) fetched from /kpis/persona with loading dots and dash fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-03T15:40:28Z
- **Completed:** 2026-04-03T15:43:49Z
- **Tasks:** 2 (Task 3 is human-verify checkpoint — pending user verification)
- **Files modified:** 6

## Accomplishments
- useKpis hook with cancellation guard, typed KpiItem/KpiData interfaces, error boundary returning empty array on failure
- KpiBar purely presentational component: loading state (animate-pulse dots), value state (bold value), empty state (mdash dash)
- All 4 shell headers (Solopreneur, Startup, SME, Enterprise) converted from label-only pills to label+value pills

## Task Commits

Each task was committed atomically:

1. **Task 1: Create useKpis hook and KpiBar component** - `9f414ec` (feat)
2. **Task 2: Update all 4 persona shells to use KpiBar with live data** - `846125f` (feat)

## Files Created/Modified
- `frontend/src/hooks/useKpis.ts` - Custom hook fetching /kpis/persona, returns KpiItem[], isLoading, error
- `frontend/src/components/personas/KpiBar.tsx` - Shared pill renderer with loading/empty/value states
- `frontend/src/components/personas/SolopreneurShell.tsx` - KpiBar integrated, static pills removed
- `frontend/src/components/personas/StartupShell.tsx` - KpiBar integrated, static pills removed
- `frontend/src/components/personas/SmeShell.tsx` - KpiBar integrated, static pills removed
- `frontend/src/components/personas/EnterpriseShell.tsx` - KpiBar integrated, static pills removed

## Decisions Made
- KpiBar is purely presentational — useKpis hook owns all fetch logic, making KpiBar reusable without side effects
- Case-insensitive label matching (`.toLowerCase()`) handles any capitalisation differences between personaShellConfig and API response labels without needing strict alignment
- Cancellation guard (`cancelled = true` in cleanup) prevents React state updates on unmounted components when user switches personas quickly
- No polling interval added — shell remounts on page navigation, satisfying the stated 60-second freshness requirement

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — uses the existing /kpis/persona endpoint from Plan 34-01. No new environment variables or services required.

## Next Phase Readiness
- All 4 persona shell headers now display live computed KPI values
- Task 3 (human-verify checkpoint) pending — user must confirm visual correctness in browser
- After verification: Phase 35 (Teams & RBAC) is the next planned phase
- KPI display pattern established — future phases can add new KPI types without changing shell structure

---
*Phase: 34-computed-kpis*
*Completed: 2026-04-03*
