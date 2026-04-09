---
phase: 52-persona-feature-gating
plan: "02"
subsystem: frontend
tags: [feature-gating, upgrade-prompt, sidebar, modal, 403-interception]
dependency_graph:
  requires: []
  provides: [upgrade-gate-modal, 403-upgrade-interception, locked-nav-items]
  affects: [frontend/src/components/layout/PremiumShell.tsx, frontend/src/services/api.ts]
tech_stack:
  added: []
  patterns:
    - Custom DOM event bus (pikar:upgrade-gate) for decoupled 403 → modal communication
    - Lock icon + button-override pattern for gated nav items
    - try/catch useSubscription mirroring established usePersona pattern
key_files:
  created:
    - frontend/src/components/layout/UpgradeGateModal.tsx
    - frontend/__tests__/components/UpgradeGateModal.test.tsx
  modified:
    - frontend/src/services/api.ts
    - frontend/src/components/layout/sidebarNav.ts
    - frontend/src/components/layout/PremiumShell.tsx
decisions:
  - "Used custom DOM event (window.dispatchEvent) rather than global state manager for 403→modal bridge; keeps api.ts free of React dependencies"
  - "Routing to /dashboard/billing for CTA rather than hardcoding price IDs; upgrade flow completes on billing page"
  - "Locked nav items render as <button> instead of <Link> to prevent navigation; preserves accessibility semantics"
  - "NavItem typed with NavItemProps interface; sidebarNav.ts exports NavItem interface for downstream type safety"
metrics:
  duration: "11 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_modified: 5
requirements_satisfied: [GATE-01]
---

# Phase 52 Plan 02: Upgrade Gate Modal and Locked Nav Items Summary

Frontend upgrade prompt experience: reusable UpgradeGateModal triggered by 403 API responses and locked sidebar nav clicks, with tier-conditional CTA and custom event bus for decoupled wiring.

## What Was Built

### UpgradeGateModal component (`frontend/src/components/layout/UpgradeGateModal.tsx`)

A `'use client'` React component (90 lines) that:
- Accepts `isOpen`, `onClose`, `feature`, `currentTier`, `requiredTier` props
- Looks up feature label/description from `FEATURE_ACCESS` in featureGating.ts; falls back to raw feature string
- Renders centered modal overlay with Lock icon, tier badge, and conditional CTA:
  - `requiredTier === 'enterprise'` → "Contact us" button
  - Otherwise → "Upgrade to {tier}" button
- Both CTAs link to `/dashboard/billing`
- "Maybe later" dismiss button and backdrop click also close the modal
- Uses `data-testid="upgrade-gate-backdrop"` for test accessibility

### 403 interception in `api.ts`

Added to `fetchApiInternal`, after getting a non-retryable response:
- Checks `response.status === 403`, clones the response with `response.clone()` (body not consumed)
- Parses JSON body; if `body.detail.feature` present, dispatches `CustomEvent('pikar:upgrade-gate', { detail })`
- Exports `UpgradeGateEvent` interface, `UPGRADE_GATE_EVENT` constant, `dispatchUpgradeGate` helper

### Locked sidebar nav (`sidebarNav.ts`)

- Added `NavItem` interface with optional `featureKey?: FeatureKey` property
- Tagged 5 nav items with feature keys: Approvals (`approvals`), Finance (`finance-forecasting`), Sales Pipeline (`sales`), Compliance (`compliance`), Reports (`reports`)
- Items without a featureKey remain ungated (Command Center, Content, Workspace, Vault, Community, etc.)

### PremiumShell integration (`PremiumShell.tsx`)

- Imports `UpgradeGateModal`, `UPGRADE_GATE_EVENT`, `isFeatureAllowed`, `FEATURE_ACCESS`, `useSubscription`
- Resolves `userTier` via `useSubscription()` in a try/catch (mirrors existing `usePersona` pattern); defaults to `'solopreneur'`; treats `'free'` as `'solopreneur'`
- `useEffect` listens for `pikar:upgrade-gate` window events and sets `upgradeGate` state
- NavItem rendering: checks `isFeatureAllowed(item.featureKey, userTier)`; if locked, renders subtle Lock icon and wires `onLockedClick` → `setUpgradeGate`
- Updated `NavItem` component to accept `locked` and `onLockedClick` props; renders as `<button>` when locked (no navigation), `<Link>` otherwise
- `UpgradeGateModal` mounted at bottom of layout tree, controlled by `upgradeGate` state

### Tests (`frontend/__tests__/components/UpgradeGateModal.test.tsx`)

7 tests (all passing):
1. Renders feature name, description, tier badge, and CTA
2. "Upgrade to {tier}" CTA for non-enterprise required tiers
3. "Contact us" CTA for enterprise gates
4. onClose fires on "Maybe later" click
5. Does not render when `isOpen=false`
6. onClose fires on backdrop click
7. Falls back to raw feature string for unknown feature keys

## Verification

- `npx vitest run __tests__/components/UpgradeGateModal.test.tsx` — 7/7 passed
- `npx tsc --noEmit` — exit 0, no type errors

## Deviations from Plan

None — plan executed exactly as written. Minor adjustment: test assertion used `/Compliance Suite/i` regex instead of exact string `'Compliance Suite'` because the heading renders "Unlock Compliance Suite" (the component prepends "Unlock" to the label). This is correct behaviour, not a defect.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `frontend/src/components/layout/UpgradeGateModal.tsx` | FOUND |
| `frontend/__tests__/components/UpgradeGateModal.test.tsx` | FOUND |
| Commit `a051c175` (test RED) | FOUND |
| Commit `b2168ff4` (feat GREEN) | FOUND |
| Commit `d53c7657` (feat Task 2) | FOUND |
