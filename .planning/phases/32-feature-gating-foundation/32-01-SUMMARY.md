---
phase: 32-feature-gating-foundation
plan: "01"
subsystem: ui
tags: [feature-gating, persona, react, typescript, nextjs, tailwind]

# Dependency graph
requires: []
provides:
  - "featureGating.ts — single source of truth for all persona tier access decisions"
  - "useFeatureGate hook — React hook returning allowed/currentTier/requiredTier/isLoading"
  - "UpgradePrompt component — soft-gating UI in page/sidebar/card variants"
affects:
  - 32-02-frontend-wiring
  - 32-03-backend-middleware
  - any future plan gating sidebar items, pages, or API routes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TIER_ORDER index comparison for persona hierarchy (TIER_ORDER.indexOf(userTier) >= TIER_ORDER.indexOf(minTier))"
    - "Route-based FeatureKey naming (matches sidebar href slugs)"
    - "Soft gating — UpgradePrompt links to /dashboard/billing, never to payment flow"
    - "Shimmer-first loading — UpgradePrompt renders shimmer while persona loads"

key-files:
  created:
    - frontend/src/config/featureGating.ts
    - frontend/src/hooks/useFeatureGate.ts
    - frontend/src/components/ui/UpgradePrompt.tsx
  modified: []

key-decisions:
  - "Single config file (featureGating.ts) is the exclusive source of truth; billing page FEATURE_ROWS will import from it in a follow-up plan"
  - "Route-path-based FeatureKey identifiers (e.g., 'workflows', 'sales') make sidebar and page integration direct lookups"
  - "getFeatureKeyForRoute sorts by route length descending so more-specific routes win (e.g., /dashboard/workflows/custom matches custom-workflows before workflows)"
  - "UpgradePrompt is soft-only — CTA is always 'View Plans' linking to /dashboard/billing, no Stripe references"
  - "TierBadge uses existing PERSONA_INFO gradient colors from onboarding.ts to maintain visual consistency"

patterns-established:
  - "Feature gate check: import useFeatureGate, destructure allowed, render <UpgradePrompt featureKey=... variant=...> if !allowed"
  - "Config-layer purity: featureGating.ts has zero React/Next imports — safe for server-side middleware use"

requirements-completed: [GATE-03, GATE-04]

# Metrics
duration: 9min
completed: "2026-04-03"
---

# Phase 32 Plan 01: Feature Gating Foundation Summary

**Centralized tier-to-feature access config (featureGating.ts) with useFeatureGate React hook and three-variant UpgradePrompt component — the contract layer that Plans 02 and 03 build against.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-03T00:54:47Z
- **Completed:** 2026-04-03T01:04:00Z
- **Tasks:** 2
- **Files modified:** 3 created, 0 modified

## Accomplishments

- Created `featureGating.ts` as the single source of truth for all 8 gated features across 4 persona tiers, with helpers for tier comparison, route lookup, and gated-route map
- Implemented `useFeatureGate` hook that wraps `usePersona()` context and returns `{ allowed, currentTier, requiredTier, isLoading, featureLabel }` for any FeatureKey
- Built `UpgradePrompt` component with page/sidebar/card variants, shimmer loading state, and TierBadge using persona gradient colors from `PERSONA_INFO`
- Verified all plan assertions: `isFeatureAllowed('workflows', 'solopreneur') === false`, `isFeatureAllowed('workflows', 'startup') === true`, `isFeatureAllowed('compliance', 'startup') === false`, `isFeatureAllowed('compliance', 'sme') === true`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create centralized feature gating config** - `6fc9b30` (feat)
2. **Task 2: Create UpgradePrompt component and useFeatureGate hook** - `267ea21` (feat)

## Files Created/Modified

- `frontend/src/config/featureGating.ts` — PersonaTier, TIER_ORDER, FeatureKey, FEATURE_ACCESS record, isFeatureAllowed, getRequiredTier, getFeatureKeyForRoute, getGatedRoutes
- `frontend/src/hooks/useFeatureGate.ts` — React hook combining usePersona() with gating config
- `frontend/src/components/ui/UpgradePrompt.tsx` — Soft-gating UI component with page/sidebar/card variants and shimmer loading

## Decisions Made

- `featureGating.ts` intentionally has zero React/Next.js imports so it is safe to import from both client components and server-side middleware (Plan 03 will use it in Next.js middleware)
- `getFeatureKeyForRoute` sorts entries by route string length descending so `/dashboard/workflows/custom` correctly resolves to `custom-workflows` before `workflows`
- UpgradePrompt page variant uses `min-h-[60vh]` rather than `min-h-screen` so it composes inside existing persona shell layouts without overflowing
- `TierBadge` uses `bg-gradient-to-r` with `PERSONA_INFO[tier].color` to reuse the existing gradient strings from `onboarding.ts` (`from-orange-500 to-amber-500`, etc.)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

The plan's `<verify>` command (`npx tsc --noEmit src/config/featureGating.ts`) produces false positives when passing individual files because tsconfig path aliases and jsx transform are not applied per-file. Verified instead using `npx tsc --noEmit --skipLibCheck` at project root, which confirmed zero errors in all three new files. Pre-existing errors from `@types/dom-webcodecs` version conflict in node_modules are unrelated to this plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 (frontend wiring) can now import `FEATURE_ACCESS`, `FeatureKey`, and `UpgradePrompt` to gate sidebar nav items and page routes
- Plan 03 (backend middleware) can import `getGatedRoutes()` and `isFeatureAllowed()` from `featureGating.ts` for server-side enforcement
- Billing page (`frontend/src/app/dashboard/billing/page.tsx`) FEATURE_ROWS remain manually maintained — a follow-up plan should have the billing page import from `featureGating.ts` directly to eliminate duplication

---
*Phase: 32-feature-gating-foundation*
*Completed: 2026-04-03*
