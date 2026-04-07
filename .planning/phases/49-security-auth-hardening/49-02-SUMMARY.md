---
phase: 49-security-auth-hardening
plan: 02
subsystem: ui
tags: [react, react-19, error-boundary, nextjs-app-router, vitest, testing-library, tailwind]

# Dependency graph
requires:
  - phase: 49-security-auth-hardening
    provides: existing global-error.tsx and route-segment error.tsx (only catch root/segment-level errors, not arbitrary client crashes)
provides:
  - Reusable layout-level React class error boundary at frontend/src/components/errors/RootErrorBoundary.tsx
  - Two-layer wiring (root layout + personas layout) so a single broken client widget never blanks the screen
  - resetKeys auto-reset pattern via componentDidUpdate (pathname-keyed at the personas layer)
  - Vitest + Testing Library coverage pattern for class-component error boundaries
affects:
  - 51-observability-baseline (OBS-01 Sentry — wires Sentry.captureException inside componentDidCatch at the existing TODO marker)
  - Any future plan adding a layout-level boundary for nested routes (apps, admin, etc.)

# Tech tracking
tech-stack:
  added: []  # No new dependencies — uses existing react, lucide-react, vitest
  patterns:
    - "Layout-level error boundary as outermost wrapper inside <body>"
    - "Per-route-group boundary with resetKeys=[pathname] for auto-reset on navigation"
    - "TODO marker pattern for cross-phase integration points (Sentry hook in componentDidCatch)"
    - "Class-component error boundary because React 19 still has no first-party useErrorBoundary hook"

key-files:
  created:
    - frontend/src/components/errors/RootErrorBoundary.tsx
    - frontend/__tests__/RootErrorBoundary.test.tsx
    - .planning/phases/49-security-auth-hardening/deferred-items.md
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/app/(personas)/layout.tsx

key-decisions:
  - "New components/errors/ directory instead of promoting DashboardErrorBoundary — root needs neutral fallback styling, dashboard one is grid-specific"
  - "Two boundary instances (root + personas) instead of one — crash in a persona's dashboard resets at the persona layer preserving providers; crash in providers themselves resets at the root layer"
  - "resetKeys via componentDidUpdate shallow-compares prevProps vs this.props arrays (length + index-by-index) — no third-party react-error-boundary dep"
  - "fallbackTitle 'This page hit a snag' on the inner persona boundary visually distinguishes per-persona crashes from outer ones"
  - "Pathname passed as resetKey at the personas layer — navigating between personas auto-clears a stale fallback without requiring a Try again click"
  - "componentDidCatch logs (error, errorInfo.componentStack) signature is locked-in so Phase 51 OBS-01 can drop Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } }) at the marked TODO"
  - "DashboardErrorBoundary.tsx left untouched — still useful for granular in-grid widget protection"
  - "Existing app/error.tsx and app/global-error.tsx left untouched — they remain as additional safety-net layers (route segment + root layout level)"

patterns-established:
  - "Layout boundaries: every route group with its own dashboard surface should wrap children in RootErrorBoundary with resetKeys=[pathname] when implemented as a client layout"
  - "Test pattern for boundaries: Thrower component with shouldThrow prop, vi.spyOn(console, 'error').mockImplementation, rerender() to flip flag for retry/reset assertions"
  - "Inline TODO(phase-XX REQ-ID) comments mark cross-phase integration hooks so future plans can grep for their phase ID"

requirements-completed: [AUTH-02]

# Metrics
duration: 6min
completed: 2026-04-07
---

# Phase 49 Plan 02: Layout-Level RootErrorBoundary Summary

**React 19 class error boundary wired into root and personas layouts so a single throwing client component renders fallback UI instead of blanking the entire React tree, with pathname-keyed auto-reset on persona navigation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-07T00:45:31Z
- **Completed:** 2026-04-07T00:51:37Z
- **Tasks:** 2 (TDD: 1 RED + 1 GREEN + 1 wiring)
- **Files modified:** 5 (2 created, 2 modified, 1 deferred-items log)

## Accomplishments

- New `RootErrorBoundary` class component in `frontend/src/components/errors/` with `getDerivedStateFromError`, `componentDidCatch`, `componentDidUpdate` (resetKeys), and `handleRetry`
- Root layout (`app/layout.tsx`) wraps the entire provider tree in `<RootErrorBoundary>` — providers and all descendants are now caught
- Personas layout (`app/(personas)/layout.tsx`) converted to a client component and wraps persona routes in `<RootErrorBoundary resetKeys={[pathname]} fallbackTitle="This page hit a snag">`
- 7 Vitest cases passing, all driven RED → GREEN
- Existing `error.tsx`, `global-error.tsx`, `DashboardErrorBoundary.tsx` untouched — they remain as additional safety-net layers
- AUTH-02 requirement closed

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): add failing RootErrorBoundary tests** — `424ca2a` (test)
2. **Task 1 (GREEN): implement RootErrorBoundary class component** — `7a395cb` (feat)
3. **Task 2: wire RootErrorBoundary into root and personas layouts** — `61f31a7` (feat)

**Plan metadata commit:** added separately with SUMMARY/STATE/ROADMAP updates.

## Files Created/Modified

### Created
- `frontend/src/components/errors/RootErrorBoundary.tsx` — Reusable React 19 class error boundary with resetKeys auto-reset, Try again button, Go to Dashboard fallback link, and `console.error` instrumentation that Phase 51 will replace with `Sentry.captureException`
- `frontend/__tests__/RootErrorBoundary.test.tsx` — 7 Vitest + Testing Library cases covering happy path, fallback rendering, retry button behaviour, fallback link href, console.error logging signature, and resetKeys auto-reset
- `.planning/phases/49-security-auth-hardening/deferred-items.md` — Logs out-of-scope pre-existing frontend lint debt (287 problems in unrelated files) for a future cleanup plan

### Modified
- `frontend/src/app/layout.tsx` — Imports `RootErrorBoundary` and wraps the entire provider tree (`PersonaProvider` → `SessionMapProvider` → `SessionControlProvider` → children + Toaster + CookieConsent) in a single outermost boundary inside `<body>`
- `frontend/src/app/(personas)/layout.tsx` — Converted from server component to client (`'use client'`), now imports `usePathname` and `RootErrorBoundary`, wraps persona route children with `resetKeys={[pathname]}` so the boundary auto-resets on navigation between personas

## Decisions Made

1. **Brand-new boundary in `components/errors/`** — chose not to promote `DashboardErrorBoundary` because the dashboard one ships dashboard-specific gradient/shadow styling. The new layout-level fallback is intentionally neutral (matches existing `app/error.tsx` palette).
2. **Two boundary layers, not one** — root layout boundary catches provider-level crashes; personas layout boundary creates a per-persona reset point so a crash in one persona's grid does not unmount the providers above it.
3. **Class component, not third-party `react-error-boundary`** — React 19 still has no first-party `useErrorBoundary` hook. Adding a dependency for ~30 lines of class component would be wasteful.
4. **`resetKeys` via shallow array compare in `componentDidUpdate`** — same algorithm `react-error-boundary` uses, no dep needed.
5. **Pathname as resetKey at personas layer** — passing `[pathname]` from `usePathname()` means navigation between persona routes auto-clears any stale fallback without requiring the user to click "Try again".
6. **`componentDidCatch` signature is locked-in for Phase 51** — `(error: Error, errorInfo: ErrorInfo)` matches what Sentry's `captureException(error, { extra: { componentStack: errorInfo.componentStack } })` expects. Phase 51 OBS-01 just drops one line at the marked TODO.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Existing `(personas)/layout.tsx` was a server component**

- **Found during:** Task 2 (wiring layouts)
- **Issue:** The plan's task 2 snippet uses `usePathname` and `'use client'`, but the file as-shipped was a server component returning `<section>{children}</section>`. The plan correctly anticipated this in its NOTE clause ("If it currently has a server component shape (no 'use client'), preserve any provider/composition logic and only wrap the rendered children").
- **Fix:** Converted the file to a client component, preserved the existing `<section>` wrapper element, and inserted `<RootErrorBoundary>` between `<section>` and `{children}`.
- **Files modified:** `frontend/src/app/(personas)/layout.tsx`
- **Verification:** Lint passes on the modified file with `--max-warnings=0`; all 7 tests still pass after the wiring; existing structure preserved.
- **Committed in:** `61f31a7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — anticipated by the plan note).
**Impact on plan:** Zero scope creep. The plan's NOTE clause already authorized this conversion.

## Issues Encountered

**Pre-existing frontend lint debt — 287 problems in unrelated files**

`cd frontend && npm run lint -- --max-warnings=0` reports 147 errors and 140 warnings across `src/services/`, `src/hooks/`, and other unrelated areas. None touch files modified by this plan. Per the SCOPE BOUNDARY rule (only fix issues directly caused by current task changes) these are NOT addressed here. All four files created/modified by 49-02 lint clean individually with `--max-warnings=0`. Logged in `.planning/phases/49-security-auth-hardening/deferred-items.md` for a future dedicated cleanup plan.

## User Setup Required

None — no external service configuration required. This is a pure frontend code change.

## Phase 51 Integration Hand-off (OBS-01 Sentry)

When OBS-01 lands the Sentry SDK, the boundary already has the integration point marked:

```tsx
componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
  // Log the full component stack so it can be diagnosed in browser DevTools.
  // In production this is also the Sentry hook point (Phase 51 OBS-01).
  console.error(
    'RootErrorBoundary caught an error:',
    error,
    errorInfo.componentStack,
  );
}
```

Phase 51's drop-in:

```tsx
componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
  console.error(
    'RootErrorBoundary caught an error:',
    error,
    errorInfo.componentStack,
  );
  Sentry.captureException(error, {
    extra: { componentStack: errorInfo.componentStack },
  });
}
```

The signature `(error: Error, errorInfo: ErrorInfo)` is intentional so Sentry's `extra` payload receives the component stack directly. Boundary placement is also already documented:
- Outermost: `frontend/src/app/layout.tsx` (catches provider crashes)
- Per-persona: `frontend/src/app/(personas)/layout.tsx` (catches dashboard crashes)
- Future route groups can copy the personas layout pattern.

## Next Phase Readiness

- AUTH-02 closed; layout-level boundary coverage in place.
- `DashboardErrorBoundary` still available for in-grid widget use cases.
- Sentry integration point is a one-line drop-in for Phase 51.
- Phase 49 wave 1 plan 49-02 complete — ready for next plan in execution order.

---
*Phase: 49-security-auth-hardening*
*Completed: 2026-04-07*

## Self-Check: PASSED

- frontend/src/components/errors/RootErrorBoundary.tsx — FOUND
- frontend/__tests__/RootErrorBoundary.test.tsx — FOUND
- frontend/src/app/layout.tsx — FOUND (modified, RootErrorBoundary wired)
- frontend/src/app/(personas)/layout.tsx — FOUND (modified, RootErrorBoundary wired with resetKeys)
- .planning/phases/49-security-auth-hardening/deferred-items.md — FOUND
- Commit 424ca2a (test RED) — FOUND
- Commit 7a395cb (feat GREEN) — FOUND
- Commit 61f31a7 (feat layout wiring) — FOUND
- 7/7 Vitest cases pass (verified twice)
- Zero lint warnings on the four files modified by this plan
- Existing error.tsx, global-error.tsx, DashboardErrorBoundary.tsx untouched (verified via git status)
