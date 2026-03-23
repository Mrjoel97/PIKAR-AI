---
phase: 21-multi-page-builder
plan: "03"
subsystem: ui
tags: [react, nextjs, typescript, vitest, testing-library, sse, app-builder]

# Dependency graph
requires:
  - phase: 21-01
    provides: multi_page_service.py, build_all_pages generator, NavLinkRewriter
  - phase: 21-02
    provides: POST /app-builder/projects/{id}/build-all (SSE), GET /app-builder/projects/{id}/screens, PATCH /app-builder/projects/{id}/sitemap
provides:
  - MultiPageEvent type and AppScreen.selected_html_url in app-builder.ts types
  - buildAllPages, listProjectScreens, updateSitemap service functions in app-builder.ts
  - SitemapCard extended with removePage (delete button) and movePage (up/down arrows, disabled at boundaries)
  - MultiPageProgress component for per-page build progress visualization
  - Verifying page at /app-builder/[projectId]/verifying with tab-based iframe preview per page
  - BuildingPage with "Build All Pages" button, multi-page SSE flow, SitemapCard onChange wired to updateSitemap
  - "Review All Pages" button navigating to verifying stage after build completes
affects:
  - 21-04 (shipping phase, will use advanceStage('shipping'))
  - 22-shipping (verifying page navigates there on Approve & Ship)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SSE ReadableStream consumer (fetch + buffer + split on \n\n) reused from generateScreen for buildAllPages
    - Local accumulator pattern for multi-page SSE events (same as generateScreen/iterateScreen stale-closure guard)
    - iframe key={screen.id} forces remount on tab switch (Phase 19 pattern)
    - SitemapCard onChange triggers async backend persist (fire-and-forget, non-fatal)

key-files:
  created:
    - frontend/src/components/app-builder/MultiPageProgress.tsx
    - frontend/src/app/app-builder/[projectId]/verifying/page.tsx
    - frontend/src/__tests__/components/SitemapEditor.test.tsx
    - frontend/src/__tests__/components/VerifyingPage.test.tsx
  modified:
    - frontend/src/types/app-builder.ts
    - frontend/src/services/app-builder.ts
    - frontend/src/components/app-builder/SitemapCard.tsx
    - frontend/src/app/app-builder/[projectId]/building/page.tsx

key-decisions:
  - "21-03: SitemapCard onChange wired to updateSitemap with fire-and-forget — local state updates immediately, backend sync is non-fatal to preserve UX responsiveness"
  - "21-03: 'Build All Pages' button shown only when sitemap has 2+ pages and no screens yet — avoids collision with single-screen generation flow"
  - "21-03: MultiPageProgress uses local accumulator pattern copied from handleGenerateScreen — avoids stale-state closure during streaming"
  - "21-03: VerifyingPage uses iframe key={screen.id} for forced remount on tab switch — reuses Phase 19 established pattern"
  - "21-03: SitemapCard readOnly=true during isBuildingAll — prevents sitemap mutations while multi-page build is streaming"

patterns-established:
  - "Multi-page SSE: page_started sets 'building', page_complete sets 'complete', build_complete sets flag and shows 'Review All Pages'"
  - "SitemapCard reorder/remove: onChange callback triggers updateSitemap PATCH immediately; parent always holds truth"

requirements-completed: [PAGE-04, FLOW-06]

# Metrics
duration: 19min
completed: 2026-03-23
---

# Phase 21 Plan 03: Multi-Page Builder Frontend Summary

**Tab-based verifying page, per-page SSE progress, and SitemapCard reorder/remove with backend persistence — completing the multi-page builder frontend for PAGE-04 and FLOW-06**

## Performance

- **Duration:** 19 min
- **Started:** 2026-03-23T03:54:50Z
- **Completed:** 2026-03-23T04:13:20Z
- **Tasks:** 2
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments

- SitemapCard extended with per-row up/down reorder arrows and delete button (disabled at boundaries and when readOnly or only 1 page), wired to PATCH /sitemap via updateSitemap
- MultiPageProgress component renders horizontal per-page status indicators (grey/indigo-pulsing/green) with current page text
- Verifying page at /app-builder/[projectId]/verifying with tab switcher, iframe preview per page (key-forced remount on switch), "Back to Building" and "Approve & Ship" actions
- BuildingPage gains "Build All Pages" button (2+ page sitemap, no screens yet), multi-page SSE flow with MultiPageProgress, and "Review All Pages" after build completes
- 11 tests across SitemapEditor (8) and VerifyingPage (3), all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Types, services, SitemapCard reorder+remove, MultiPageProgress** - `dc19acc` (feat, TDD green)
2. **Task 2: Verifying page and BuildingPage multi-page integration** - `51f0af9` (feat)

## Files Created/Modified

- `frontend/src/types/app-builder.ts` — Added MultiPageEvent interface and selected_html_url to AppScreen
- `frontend/src/services/app-builder.ts` — Added buildAllPages (SSE), listProjectScreens (GET /screens), updateSitemap (PATCH /sitemap)
- `frontend/src/components/app-builder/SitemapCard.tsx` — Added removePage with delete button, movePage with up/down arrows (disabled at boundaries)
- `frontend/src/components/app-builder/MultiPageProgress.tsx` — New: per-page status bar (pending/building/complete) with current page label
- `frontend/src/app/app-builder/[projectId]/verifying/page.tsx` — New: tab-based multi-page review with iframe preview and Approve & Ship
- `frontend/src/app/app-builder/[projectId]/building/page.tsx` — Extended: SitemapCard with onChange persistence, Build All Pages flow, MultiPageProgress, Review All Pages
- `frontend/src/__tests__/components/SitemapEditor.test.tsx` — New: 8 tests (TDD) for removePage and movePage behaviors
- `frontend/src/__tests__/components/VerifyingPage.test.tsx` — New: 3 tests for tab rendering, tab switching, Approve & Ship button

## Decisions Made

- SitemapCard onChange uses fire-and-forget updateSitemap — local state updates immediately so reorder/remove feels instant; backend sync failure is logged but non-fatal
- "Build All Pages" button only visible when sitemap.length >= 2 and variants.length === 0 — prevents confusion with single-screen generation flow that already works
- MultiPageProgress uses the same local accumulator pattern as handleGenerateScreen — this is the established stale-closure guard in this codebase (documented in STATE.md decisions for Phase 20)
- SitemapCard set to readOnly=true while isBuildingAll — prevents mid-build sitemap mutations that would invalidate the in-flight build
- iframe key={screen.id} forces remount when switching tabs — reuses Phase 19 established pattern for stale iframe prevention

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `uv` binary not accessible in bash PATH on this Windows dev environment — backend tests skipped for this frontend-only plan. No Python files were changed in Plan 21-03; backend app_builder tests remain green from Plans 21-01/02.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All PAGE-04 and FLOW-06 frontend requirements complete
- Verifying page navigates to /app-builder/[projectId]/shipping on approve — Phase 22 (shipping) will create that page
- Multi-page builder frontend fully functional; backend endpoints from Plans 21-01/02 are live
- Phase 21 (all 3 plans) complete: multi-page service, router endpoints, and frontend UI

---
*Phase: 21-multi-page-builder*
*Completed: 2026-03-23*
