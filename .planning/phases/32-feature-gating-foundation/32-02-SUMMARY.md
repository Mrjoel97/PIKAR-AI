---
phase: 32-feature-gating-foundation
plan: "02"
subsystem: ui
tags: [feature-gating, sidebar, navigation, react, typescript, nextjs, tailwind]

# Dependency graph
requires:
  - "32-01 — featureGating.ts, useFeatureGate hook, UpgradePrompt component"
provides:
  - "Sidebar with lock icons on gated nav items and inline upgrade popover"
  - "GatedPage wrapper component — shows UpgradePrompt or children based on feature access"
affects:
  - 32-03-backend-middleware
  - any future page that needs to display gated content

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GatedPage wrapper: import, wrap JSX return — zero page-internal changes"
    - "Sidebar gating: getFeatureKeyForRoute lookup per nav item, button replaces Link for locked items"
    - "Click-outside overlay via fixed inset-0 div dismisses sidebar upgrade popover"

key-files:
  created:
    - frontend/src/components/dashboard/GatedPage.tsx
  modified:
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/app/dashboard/reports/page.tsx
    - frontend/src/app/dashboard/approvals/page.tsx
    - frontend/src/app/dashboard/sales/page.tsx
    - frontend/src/app/dashboard/compliance/page.tsx
    - frontend/src/app/dashboard/workflows/templates/page.tsx

key-decisions:
  - "GatedPage renders its own PremiumShell when denied or loading — avoids double-shell when wrapping pages that also contain PremiumShell (outer GatedPage intercepts first)"
  - "Workflows root page.tsx is a server-side redirect to /templates — GatedPage applied to /templates (the real landing page) rather than the redirect stub"
  - "Sidebar uses lockedFeaturePopover state (FeatureKey | null) to show one popover at a time; click-outside fixed overlay dismisses cleanly"
  - "When persona is null (loading), all sidebar items render as normal Links — no lock icons shown until tier is confirmed"

requirements-completed: [GATE-01]

# Metrics
duration: 11min
completed: "2026-04-03"
---

# Phase 32 Plan 02: Frontend Gating Wiring Summary

**Sidebar lock icons + click-to-upgrade popover for unauthorized nav items, plus GatedPage wrapper applied to five gated dashboard pages — solopreneur users see UpgradePrompt instead of page content for all startup/SME/enterprise features.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-03T13:00:56Z
- **Completed:** 2026-04-03T13:11:51Z
- **Tasks:** 2
- **Files modified:** 1 created, 6 modified

## Accomplishments

- Modified `Sidebar.tsx` to call `getFeatureKeyForRoute` per nav item and render a locked `<button>` (with `Lock` icon, `opacity-60`) instead of `<Link>` for unauthorized features
- Clicking a locked item opens a sidebar-variant `UpgradePrompt` in an absolute popover to the right of the sidebar; click-outside overlay dismisses it
- All ungated items, the approval badge, `SessionList`, and `RecentWidgets` are completely unchanged
- Created `GatedPage` wrapper component with three states: shimmer (loading), UpgradePrompt page variant (denied), or children (allowed)
- Applied `GatedPage` to: reports, approvals, sales, compliance, workflows/templates pages with minimal two-line changes each (import + wrap)

## Task Commits

1. **Task 1: Add lock icons and gating to sidebar navigation** — `395101b` (feat)
2. **Task 2: Create GatedPage wrapper and apply to gated dashboard pages** — `1442053` (feat)

## Files Created/Modified

- `frontend/src/components/layout/Sidebar.tsx` — imports Lock, getFeatureKeyForRoute, isFeatureAllowed, UpgradePrompt; adds lockedFeaturePopover state; renders locked buttons with Lock icon for gated items
- `frontend/src/components/dashboard/GatedPage.tsx` — client wrapper: useFeatureGate → shimmer | UpgradePrompt(page) | children
- `frontend/src/app/dashboard/reports/page.tsx` — wrapped with GatedPage featureKey="reports"
- `frontend/src/app/dashboard/approvals/page.tsx` — wrapped with GatedPage featureKey="approvals"
- `frontend/src/app/dashboard/sales/page.tsx` — wrapped with GatedPage featureKey="sales"
- `frontend/src/app/dashboard/compliance/page.tsx` — wrapped with GatedPage featureKey="compliance"
- `frontend/src/app/dashboard/workflows/templates/page.tsx` — wrapped with GatedPage featureKey="workflows"

## Decisions Made

- `GatedPage` wraps outside `DashboardErrorBoundary` and `PremiumShell` — when the gate denies access it renders its own PremiumShell so the user still gets the standard shell chrome. The inner PremiumShell only renders when `gate.allowed === true`.
- Workflows root `page.tsx` does a server-side `redirect('/dashboard/workflows/templates')` and cannot be a client component. GatedPage was applied to `workflows/templates/page.tsx` (the real content landing) instead. Direct URL access to `/dashboard/workflows/templates` is now gated.
- Sidebar popover uses `position: absolute; left: 100%` so it opens to the right of the sidebar, not obscuring navigation items below.

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing out-of-scope item logged to `deferred-items.md`:
- `workflows/templates/page.tsx` line 94: pre-existing direct `startWorkflow` call (validator recommends `start()` from "workflow/api") — predates this plan, not caused by plan 02 changes.

## User Setup Required

None.

## Next Phase Readiness

- Plan 03 (backend middleware) already completed (`feat(32-03)` commits visible in git log) and can rely on the same `featureGating.ts` contract
- Billing page (`/dashboard/billing`) is the UpgradePrompt CTA destination — it remains manually maintained; a follow-up plan should have it import from `featureGating.ts` directly

---
*Phase: 32-feature-gating-foundation*
*Completed: 2026-04-03*
