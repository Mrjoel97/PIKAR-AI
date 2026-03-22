---
phase: 19-screen-generation
plan: "02"
subsystem: app-builder
tags: [react, nextjs, typescript, tdd, vitest, sse, iframe, framer-motion]
dependency_graph:
  requires:
    - phase: 19-01
      provides: "screen_generation_service, 4 backend endpoints (generate-screen, generate-device-variant, variants, select)"
    - phase: 18-design-brief-research
      provides: "build_plan on AppProject, design_system, startResearch SSE pattern"
  provides:
    - VariantComparisonGrid component (2-3 column grid with indigo ring selection)
    - DevicePreviewFrame component (sandboxed iframe with Desktop/Mobile/Tablet tabs)
    - GenerationProgress component (SSE step progress with framer-motion pulse)
    - BuildingPage at /app-builder/[projectId]/building
    - generateScreen, generateDeviceVariant, getScreenVariants, selectVariant service functions
    - DeviceType, ScreenVariant, GenerationEvent, AppScreen TypeScript interfaces
  affects:
    - Phase 20+ (any phase building on the building page or variant selection flow)
tech-stack:
  added: []
  patterns:
    - TDD red/green for all new frontend components
    - fetch ReadableStream SSE pattern (matches startResearch — Authorization header support)
    - data-testid="generation-progress" for testable async UI state
    - iframe key={htmlUrl} to force remount on URL change (avoids stale iframe)
    - On-demand device variant generation — MOBILE/TABLET triggered only if no cached variant exists
key-files:
  created:
    - frontend/src/components/app-builder/VariantComparisonGrid.tsx
    - frontend/src/components/app-builder/DevicePreviewFrame.tsx
    - frontend/src/components/app-builder/GenerationProgress.tsx
    - frontend/src/app/app-builder/[projectId]/building/page.tsx
    - frontend/src/__tests__/components/VariantComparisonGrid.test.tsx
    - frontend/src/__tests__/components/DevicePreviewFrame.test.tsx
    - frontend/src/__tests__/components/BuildingPage.test.tsx
  modified:
    - frontend/src/types/app-builder.ts
    - frontend/src/services/app-builder.ts
key-decisions:
  - "iframe key={htmlUrl} forces remount on URL change — avoids stale iframe showing old content when variant switches"
  - "On-demand device generation — switching to MOBILE/TABLET checks variants array first; only calls generateDeviceVariant if no cached device variant exists"
  - "GenerationProgress uses data-testid='generation-progress' — framer-motion opacity animation makes text content unreliable for tests; testId is stable"
  - "BuildingPage accumulates variant_generated events into local array before React state update — avoids closure stale-capture during SSE streaming"
  - "Screen sidebar build plan rendered from project.build_plan fetched via getProject() on mount — same data shape as approved brief"
patterns-established:
  - "SSE service function pattern: fetch POST → ReadableStream reader → split on double-newline → JSON.parse data: lines (matches startResearch)"
  - "TDD native DOM assertions: element.disabled property (not jest-dom) — @testing-library/jest-dom not configured in this vitest setup"
requirements-completed: [SCRN-02, SCRN-03, BLDR-02]
duration: 8min
completed: "2026-03-22"
---

# Phase 19 Plan 02: Screen Generation Frontend Summary

Side-by-side variant comparison grid, sandboxed live iframe with Desktop/Mobile/Tablet device switcher, and SSE-driven building page composing all three components into the screen generation workflow.

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-22T14:25:09Z
- **Completed:** 2026-03-22T14:32:49Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 9

## Accomplishments

- VariantComparisonGrid renders 2-3 variant screenshot thumbnails side-by-side with indigo ring selection indicator (SCRN-02)
- DevicePreviewFrame renders a sandboxed iframe with Desktop/Mobile/Tablet tabs and generates device variants on demand (SCRN-03)
- BuildingPage composes GenerationProgress, VariantComparisonGrid, and DevicePreviewFrame into a cohesive SSE-driven generation workflow with build plan sidebar (BLDR-02)
- All 10 new component tests pass; all 7 app-builder component test files pass (26 tests total)

## Task Commits

Each task was committed atomically:

1. **Task 1: Types, service functions, and test scaffolds (RED)** - `421e3fa` (test)
2. **Task 2: Components and building page (GREEN)** - `5b2a1ae` (feat)

## Files Created/Modified

- `frontend/src/types/app-builder.ts` - Added DeviceType, ScreenVariant, GenerationEvent, AppScreen interfaces
- `frontend/src/services/app-builder.ts` - Added generateScreen, generateDeviceVariant, getScreenVariants, selectVariant
- `frontend/src/components/app-builder/VariantComparisonGrid.tsx` - 2-3 column grid with indigo ring selection state
- `frontend/src/components/app-builder/DevicePreviewFrame.tsx` - Sandboxed iframe with 3 device tab buttons (DESKTOP/MOBILE/TABLET dims: 1280/390/768px)
- `frontend/src/components/app-builder/GenerationProgress.tsx` - SSE step progress with framer-motion pulse and progress bar
- `frontend/src/app/app-builder/[projectId]/building/page.tsx` - Full building page: sidebar build plan, SSE generation, variant grid, device preview
- `frontend/src/__tests__/components/VariantComparisonGrid.test.tsx` - 3 tests: render, click select, ring class
- `frontend/src/__tests__/components/DevicePreviewFrame.test.tsx` - 4 tests: iframe src, 3 device tabs, onDeviceChange, sandbox attribute
- `frontend/src/__tests__/components/BuildingPage.test.tsx` - 3 tests: GenerationProgress during generation, VariantComparisonGrid after ready, DevicePreviewFrame iframe src

## Decisions Made

1. **`iframe key={htmlUrl}`** — Forces React to remount the iframe whenever the URL changes. Without this, the iframe keeps showing stale content when a different variant is selected.

2. **On-demand device generation** — Switching to MOBILE or TABLET checks the `variants` array for an existing `device_type` match before calling `generateDeviceVariant`. This avoids redundant Stitch calls when the user tabs back and forth.

3. **`data-testid="generation-progress"` on GenerationProgress** — The framer-motion opacity pulse animation makes the step message text unstable for DOM queries. A stable testId gives BuildingPage tests a reliable hook.

4. **Local accumulator for SSE variants** — The `onEvent` callback captures `accumulated: ScreenVariant[]` in a closure and calls `setVariants([...accumulated])` on each event, avoiding the React stale-state closure problem during streaming.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Building page is functional at `/app-builder/[projectId]/building`
- All screen generation API calls wired up (generate, device variant, list, select)
- Device preview uses permanent Supabase Storage URLs from Plan 01
- Ready for Phase 19 Plan 03 (verifying / export flow) or any downstream phase

## Self-Check: PASSED

- [x] `frontend/src/components/app-builder/VariantComparisonGrid.tsx` — FOUND
- [x] `frontend/src/components/app-builder/DevicePreviewFrame.tsx` — FOUND
- [x] `frontend/src/components/app-builder/GenerationProgress.tsx` — FOUND
- [x] `frontend/src/app/app-builder/[projectId]/building/page.tsx` — FOUND
- [x] `frontend/src/__tests__/components/VariantComparisonGrid.test.tsx` — FOUND
- [x] `frontend/src/__tests__/components/DevicePreviewFrame.test.tsx` — FOUND
- [x] `frontend/src/__tests__/components/BuildingPage.test.tsx` — FOUND
- [x] Commit `421e3fa` (RED tests) — FOUND
- [x] Commit `5b2a1ae` (GREEN implementation) — FOUND
- [x] All 10 component tests pass
- [x] All 7 app-builder component test files pass (26 tests)

---
*Phase: 19-screen-generation*
*Completed: 2026-03-22*
