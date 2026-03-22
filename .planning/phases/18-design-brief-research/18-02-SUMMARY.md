---
phase: 18-design-brief-research
plan: 02
subsystem: ui
tags: [react, nextjs, sse, vitest, tailwind, app-builder]

# Dependency graph
requires:
  - phase: 17-creative-questioning
    provides: GsdProgressBar component, AppProject types, app-builder service patterns, vitest test setup
  - phase: 18-design-brief-research
    plan: 01
    provides: Backend SSE /research endpoint, /approve-brief endpoint, PATCH /stage endpoint

provides:
  - DesignBriefCard: editable color palette, typography, spacing, raw markdown preview
  - SitemapCard: editable page list with sections and device target checkboxes
  - BuildPlanView: phase/dependency visualization with screen chips
  - [projectId]/layout.tsx: server component fetching project stage dynamically for GsdProgressBar
  - [projectId]/research/page.tsx: SSE-driven research page with progress animation, approve flow
  - startResearch() SSE service function using fetch ReadableStream (supports Authorization header)
  - approveBrief() service function posting design system + sitemap to backend
  - DesignBrief, SitemapPage, BuildPlanPhase, ResearchEvent TypeScript interfaces

affects:
  - 18-03 and beyond (building phase UI will consume AppProject.build_plan and design_system fields)
  - Any future app-builder page under [projectId]/ inherits the dynamic progress bar layout

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SSE via fetch ReadableStream (not EventSource) to support Authorization header on POST requests
    - Next.js 15+ server component [projectId]/layout with awaited params Promise
    - TDD: RED (test scaffolds) committed before GREEN (implementation)
    - Native DOM assertions in vitest (element.disabled, not jest-dom toBeDisabled)
    - Framer-motion mocked in tests to avoid animation overhead

key-files:
  created:
    - frontend/src/app/app-builder/[projectId]/layout.tsx
    - frontend/src/app/app-builder/[projectId]/page.tsx
    - frontend/src/app/app-builder/[projectId]/research/page.tsx
    - frontend/src/components/app-builder/DesignBriefCard.tsx
    - frontend/src/components/app-builder/SitemapCard.tsx
    - frontend/src/components/app-builder/BuildPlanView.tsx
    - frontend/src/__tests__/components/DesignBriefCard.test.tsx
    - frontend/src/__tests__/components/ResearchPage.test.tsx
  modified:
    - frontend/src/types/app-builder.ts
    - frontend/src/services/app-builder.ts
    - frontend/src/app/app-builder/layout.tsx
    - frontend/src/app/app-builder/new/page.tsx

key-decisions:
  - "18-02: [projectId]/layout.tsx is a server component that fetches project stage with cache:no-store — always fresh stage for GsdProgressBar, no client JS needed"
  - "18-02: Approve button rendered (but disabled) even during research — enables test access via getByRole('button', {name:/approve/i})"
  - "18-02: startResearch uses fetch ReadableStream not EventSource — only way to send Authorization header on SSE POST"
  - "18-02: Root app-builder layout stripped to plain wrapper — progress bar moved to [projectId]/layout (dynamic) and new/page.tsx (hardcoded questioning)"

patterns-established:
  - "SSE ReadableStream pattern: POST + getReader() + decoder + buffer splitting on '\\n\\n'"
  - "Server component layout with awaited params: params: Promise<{ projectId: string }> then await params"
  - "TDD RED commit first, then GREEN commit — two separate commits per TDD task cycle"

requirements-completed: [FLOW-02, FLOW-03, FLOW-04]

# Metrics
duration: 15min
completed: 2026-03-22
---

# Phase 18 Plan 02: Design Brief Research Frontend Summary

**SSE-driven research page with live progress animation, editable DesignBriefCard + SitemapCard, explicit approve flow, BuildPlanView, and dynamic GsdProgressBar reading project stage from API**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-22T02:02:00Z
- **Completed:** 2026-03-22T02:16:47Z
- **Tasks:** 2 (TDD task + implementation task)
- **Files modified:** 12

## Accomplishments

- Research page streams SSE events (searching, synthesizing, saving, ready) with framer-motion step transitions and pulsing animation
- DesignBriefCard provides editable color swatches with hex inputs, typography font fields, spacing, and a raw DESIGN.md textarea
- SitemapCard provides editable page list with sections (comma-separated) and device target checkboxes
- Approve button is disabled during research and calls approveBrief() on click — approval is never automatic
- BuildPlanView renders after approval showing phases, screen chips, and dependency labels
- GsdProgressBar reads project stage dynamically in [projectId]/layout.tsx (server component)
- All 7 vitest tests pass (3 DesignBriefCard + 4 ResearchPage) with zero regressions in the 223-test baseline

## Task Commits

Each task was committed atomically:

1. **Task 1: Types, service functions, and test scaffolds (RED)** - `64bb7c5` (test)
2. **Task 2: Dynamic progress bar layout and research page with editable cards (GREEN)** - `d38b027` (feat)

## Files Created/Modified

- `frontend/src/types/app-builder.ts` — Added DesignBrief, SitemapPage, BuildPlanPhase, ResearchEvent interfaces; extended AppProject with design_system, sitemap, build_plan optional fields
- `frontend/src/services/app-builder.ts` — Added startResearch() SSE stream function and approveBrief() function
- `frontend/src/app/app-builder/layout.tsx` — Stripped to plain wrapper (GsdProgressBar moved out)
- `frontend/src/app/app-builder/new/page.tsx` — Added GsdProgressBar hardcoded to 'questioning'
- `frontend/src/app/app-builder/[projectId]/layout.tsx` — Server component: fetches project stage, renders dynamic GsdProgressBar
- `frontend/src/app/app-builder/[projectId]/page.tsx` — Client redirect to /research sub-page
- `frontend/src/app/app-builder/[projectId]/research/page.tsx` — Full research page with SSE progress, editable cards, approve button, build plan
- `frontend/src/components/app-builder/DesignBriefCard.tsx` — Editable design system card (134 lines)
- `frontend/src/components/app-builder/SitemapCard.tsx` — Editable sitemap card with device target checkboxes (102 lines)
- `frontend/src/components/app-builder/BuildPlanView.tsx` — Build plan phase/dependency view (59 lines)
- `frontend/src/__tests__/components/DesignBriefCard.test.tsx` — 3 unit tests (color swatches, typography, onChange)
- `frontend/src/__tests__/components/ResearchPage.test.tsx` — 4 unit tests (progress, ready state, approve, disabled)

## Decisions Made

- **[projectId]/layout.tsx as server component:** Fetches project stage with `cache: 'no-store'` for always-fresh GsdProgressBar. Falls back to 'research' on errors — no auth needed server-side for this read.
- **Approve button always rendered during research (disabled):** Keeps the button accessible in tests via `getByRole('button', {name:/approve/})` without needing to check for its absence.
- **fetch ReadableStream for SSE:** EventSource does not support Authorization headers or POST methods. fetch + ReadableStream + TextDecoder is the only correct approach.
- **Root layout stripped:** Cleaner separation — each sub-layout owns its progress bar context.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — baseline had 15 pre-existing test failures (unrelated to app-builder); my changes introduced zero additional failures.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Research frontend complete: users can see SSE progress, edit brief + sitemap, approve to lock design system
- Backend endpoints from 18-01 (POST /research, POST /approve-brief) are consumed by this page
- Phase 18-03 (building phase UI) can consume AppProject.build_plan and design_system fields now present in types
- The [projectId]/layout.tsx pattern is established for all future project sub-pages

---
*Phase: 18-design-brief-research*
*Completed: 2026-03-22*

## Self-Check: PASSED

All 11 required artifact files found. Key service patterns (startResearch, approveBrief, GsdProgressBar, DesignBriefCard) confirmed present. Commits 64bb7c5 and d38b027 verified. All min_lines requirements met (research/page.tsx=189, DesignBriefCard=134, SitemapCard=102, BuildPlanView=59, test=43).
