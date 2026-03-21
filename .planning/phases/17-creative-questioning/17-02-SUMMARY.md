---
phase: 17-creative-questioning
plan: "02"
subsystem: ui
tags: [react, nextjs, framer-motion, vitest, tailwind, app-builder, tdd, wizard, progress-bar]

# Dependency graph
requires:
  - phase: 17-creative-questioning
    provides: FastAPI router (POST /app-builder/projects, GET /app-builder/projects/{id}, PATCH /app-builder/projects/{id}/stage)
  - phase: 16-foundation
    provides: app_projects and build_sessions DB schema with GSD stage CHECK constraints

provides:
  - GsdProgressBar component (7-stage sticky progress bar; completed/current/future visual states)
  - QuestioningWizard component (5-step choice-card wizard with framer-motion transitions; auto-advance + free-text final step)
  - QuestionStep component (choice-card grid, 2-col sm / 3-col md, indigo selected state)
  - /app-builder layout (sticky GsdProgressBar always visible)
  - /app-builder/new page (QuestioningWizard rendered centered)
  - frontend/src/types/app-builder.ts (GSD_STAGES const, GsdStage type, AppProject interface, QUESTIONS array)
  - frontend/src/services/app-builder.ts (createProject, getProject, advanceStage authenticated fetch wrappers)
  - 9 vitest unit tests (4 GsdProgressBar + 5 QuestioningWizard) all GREEN

affects:
  - 17-creative-questioning (plan 03+ — AI agent integration, brief generation)
  - 18-research (QuestioningWizard creative_brief JSONB feeds research agent)
  - All phases 18-23 that share the /app-builder layout with the GsdProgressBar

# Tech tracking
tech-stack:
  added: []
  patterns:
    - AnimatePresence mode="wait" + motion.div key={step} for x-slide step transitions in wizards
    - Lucide icon map (Record<string, React.ElementType>) to resolve icon strings from const array at render time
    - vitest native DOM assertion (.disabled property) instead of jest-dom toBeDisabled() — no @testing-library/jest-dom setup in this project

key-files:
  created:
    - frontend/src/types/app-builder.ts
    - frontend/src/services/app-builder.ts
    - frontend/src/components/app-builder/GsdProgressBar.tsx
    - frontend/src/components/app-builder/QuestionStep.tsx
    - frontend/src/components/app-builder/QuestioningWizard.tsx
    - frontend/src/app/app-builder/layout.tsx
    - frontend/src/app/app-builder/new/page.tsx
    - frontend/src/__tests__/components/GsdProgressBar.test.tsx
    - frontend/src/__tests__/components/QuestioningWizard.test.tsx
  modified: []

key-decisions:
  - "toBeDisabled() is a jest-dom matcher not available in this vitest setup — use (btn as HTMLButtonElement).disabled === true for native DOM check"
  - "GsdProgressBar stage hardcoded to 'questioning' in layout for Phase 17 — dynamic stage via context or URL-derived prop deferred to Phase 18+ when projects have IDs in the route"
  - "QuestioningWizard: auto-advance fires on steps 0-3 (choice cards), not step 4 (name) — isFinalStep guard controls this distinction"

patterns-established:
  - "Lucide icon map pattern: Record<string, React.ElementType> keyed by icon string name from const array, resolved at render time with ?? fallback"
  - "Wizard step navigation: useState step index + AnimatePresence key={step} for declarative transitions — no explicit animation state machine needed"
  - "Native DOM assertions in vitest: use element.property (e.g. .disabled) not jest-dom matchers when @testing-library/jest-dom is not configured"

requirements-completed:
  - FLOW-01
  - BLDR-04

# Metrics
duration: 15min
completed: 2026-03-21
---

# Phase 17 Plan 02: Creative Questioning Wizard Summary

**5-step creative questioning wizard with choice-card auto-advance, framer-motion transitions, and 7-stage GSD progress bar embedded in /app-builder layout**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-21T21:45:00Z
- **Completed:** 2026-03-21T21:58:00Z
- **Tasks:** 2 (TDD: RED scaffold + GREEN implementation)
- **Files modified:** 9 (created)

## Accomplishments

- Created `GsdProgressBar` — sticky 7-segment horizontal bar driven by `currentStage` prop; completed stages show green+Check icon; current stage shows indigo+ring; future stages show slate/muted; renders stage banner "STAGE N OF 7 — LABEL"
- Created `QuestioningWizard` — 5-step wizard that accumulates answers in local state; steps 0-3 auto-advance on choice card click via framer-motion AnimatePresence; step 4 renders a free-text name input and "Start Building" submit button; calls `createProject()` then `router.push(/app-builder/{id})`
- Wired `/app-builder/layout.tsx` with sticky `GsdProgressBar` at top and `/app-builder/new/page.tsx` rendering the wizard centered; all 9 vitest tests GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Types, service, and test scaffolds** - `32d65c8` (test — RED state; types + services + test files)
2. **Task 2: GsdProgressBar, QuestioningWizard, layout, and new-project page** - `f042bc6` (feat — GREEN, all 9 tests pass)

_Note: TDD tasks — test commit first (RED), then implementation commit (GREEN)._

## Files Created/Modified

- `frontend/src/types/app-builder.ts` — GSD_STAGES const (7 entries), GsdStage type, AppProject interface, QUESTIONS array (5 questions, exact order, choices as specified)
- `frontend/src/services/app-builder.ts` — createProject(), getProject(), advanceStage() authenticated fetch wrappers using Supabase session token
- `frontend/src/components/app-builder/GsdProgressBar.tsx` — 7-stage progress bar, aria-current="step" on current, aria-label="{label} complete" on Check icons
- `frontend/src/components/app-builder/QuestionStep.tsx` — choice-card grid, 2-col/3-col responsive, indigo selected state
- `frontend/src/components/app-builder/QuestioningWizard.tsx` — 5-step wizard, framer-motion transitions, back button, loading/error states
- `frontend/src/app/app-builder/layout.tsx` — Server Component with sticky GsdProgressBar
- `frontend/src/app/app-builder/new/page.tsx` — Client Component rendering QuestioningWizard
- `frontend/src/__tests__/components/GsdProgressBar.test.tsx` — 4 tests for progress bar rendering
- `frontend/src/__tests__/components/QuestioningWizard.test.tsx` — 5 tests for wizard behavior

## Decisions Made

- Hardcoded `currentStage="questioning"` in layout — dynamic stage (read from project data) deferred to Phase 18 when projects have IDs in the route path
- Used native DOM `.disabled` property check in tests instead of `toBeDisabled()` — `@testing-library/jest-dom` is not configured in this project's vitest setup

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `toBeDisabled()` is a jest-dom matcher not available in vitest without @testing-library/jest-dom setup**
- **Found during:** Task 2 verification (running tests GREEN)
- **Issue:** The test committed in Task 1 (RED) used `expect(submitBtn).toBeDisabled()` — this throws "Invalid Chai property: toBeDisabled" because the vitest config (vitest.config.mts) has no setup file importing jest-dom matchers
- **Fix:** Changed to `expect((submitBtn as HTMLButtonElement).disabled).toBe(true)` — native DOM property, always available in jsdom environment
- **Files modified:** `frontend/src/__tests__/components/QuestioningWizard.test.tsx`
- **Verification:** All 9 tests pass GREEN after fix
- **Committed in:** `f042bc6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Fix necessary for correctness; no scope creep. The button IS disabled in the DOM (verified via rendered HTML in error output); the assertion method was wrong, not the component.

## Issues Encountered

- Git bash had transient fatal errors (add_item mount failure) on first ~15 attempts — resolved by retrying; no data loss or file corruption.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `/app-builder/new` page is live and renders the full 5-step wizard
- `createProject()` calls `POST /app-builder/projects` (Phase 17-01 endpoint) with `{title, creative_brief}` JSONB
- `GsdProgressBar` is in the layout, will be enhanced in Phase 18+ to read dynamic stage from project data
- `QUESTIONS` array and `creative_brief` structure are the input contract for Phase 18 research agent

---
*Phase: 17-creative-questioning*
*Completed: 2026-03-21*
