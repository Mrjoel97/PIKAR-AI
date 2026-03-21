---
phase: 09-user-management
plan: 04
subsystem: ui
tags: [react, nextjs, context, impersonation, admin, session-timer, tailwind]

requires:
  - phase: 09-user-management-01
    provides: GET /admin/users/{id} endpoint returning user profile data
  - phase: 07-foundation
    provides: require_admin middleware, admin layout, AdminSidebar

provides:
  - ImpersonationContext with target user data, PersonaContext override, 30-min session timer
  - ImpersonationBanner: non-dismissible sticky banner with countdown timer and exit button
  - /admin/impersonate/[userId] page with read-only user view
  - Exported raw PersonaContext for future context override use

affects: [09-03, 13-interactive-impersonation, USER-03]

tech-stack:
  added: []
  patterns:
    - sessionStorage-persisted session timer pattern (pikar:impersonate:{userId}:start key)
    - PersonaContext.Provider override via raw context export for impersonation
    - Countdown effect with setInterval that auto-redirects on expiry
    - Two-layer context wrapping: ImpersonationContext.Provider > PersonaContext.Provider

key-files:
  created:
    - frontend/src/contexts/ImpersonationContext.tsx
    - frontend/src/components/admin/ImpersonationBanner.tsx
    - frontend/src/app/(admin)/impersonate/[userId]/page.tsx
  modified:
    - frontend/src/contexts/PersonaContext.tsx

key-decisions:
  - "Export raw PersonaContext (not PersonaProvider) so ImpersonationProvider can supply static override values to usePersona() callers"
  - "sessionStorage key pikar:impersonate:{userId}:start persists timer across admin navigation within same session"
  - "ImpersonationBanner background transitions amber-600 -> red-600 when <5 min remain as visual urgency cue"
  - "Impersonation page renders inside (admin) layout — AdminSidebar intentionally visible for admin context awareness"
  - "Phase 9 establishes read-only view foundation; full interactive persona layout rendering deferred to Phase 13"

patterns-established:
  - "PersonaContext raw export + static override pattern: export { PersonaContext } then wrap with <PersonaContext.Provider value={staticValues}> in impersonation tree"
  - "Session timer with sessionStorage persistence: check existing key on mount, reuse if <30min old, create new otherwise"

requirements-completed: [USER-03]

duration: 7min
completed: 2026-03-21
---

# Phase 9 Plan 04: User Management — Impersonation View Summary

**ImpersonationContext with PersonaContext override, non-dismissible amber banner with 30-min sessionStorage-persisted countdown, and read-only impersonation view page at /admin/impersonate/[userId]**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-21T19:04:51Z
- **Completed:** 2026-03-21T19:11:07Z
- **Tasks:** 2 of 3 (Task 3 is checkpoint:human-verify — awaiting manual verification)
- **Files modified:** 4

## Accomplishments

- `ImpersonationProvider` overrides `PersonaContext` with target user's static data so any child calling `usePersona()` receives the target user's values — foundation for Phase 13 interactive impersonation
- 30-minute session timer persisted in `sessionStorage` (key: `pikar:impersonate:{userId}:start`) — survives navigation within impersonation view, auto-redirects to `/admin/users` on expiry
- `ImpersonationBanner` is sticky top-0 z-9999, non-dismissible — amber-600 background, red-600 warning when <5 minutes remain; shows target email, persona, MM:SS countdown, Exit button
- `/admin/impersonate/[userId]` fetches target user from `GET /admin/users/{id}`, shows loading skeleton, error state with 2s auto-redirect, then renders full impersonation view
- `PersonaContext` raw export added to enable override pattern for future consumers

## Task Commits

Each task was committed atomically:

1. **Task 1: ImpersonationContext and ImpersonationBanner components** - `6ef2820` (feat)
2. **Task 2: Impersonation view page** - `3d31c04` (feat)

**Plan metadata:** (pending final metadata commit)

## Files Created/Modified

- `frontend/src/contexts/ImpersonationContext.tsx` — ImpersonationProvider (30-min timer, PersonaContext override, exitImpersonation), useImpersonation hook
- `frontend/src/components/admin/ImpersonationBanner.tsx` — Non-dismissible sticky banner with MM:SS countdown and exit button; amber/red visual urgency
- `frontend/src/app/(admin)/impersonate/[userId]/page.tsx` — Impersonation view page: fetches user, loading skeleton, error redirect, ImpersonationProvider + ImpersonationBanner + read-only user card
- `frontend/src/contexts/PersonaContext.tsx` — Added `export { PersonaContext }` at bottom for raw context access

## Decisions Made

- Exported raw `PersonaContext` (not `PersonaProvider`) — the impersonation use case requires supplying fully static values without Supabase subscriptions; `PersonaContext.Provider` with static values is the correct pattern
- Session timer persisted in `sessionStorage` with key `pikar:impersonate:{userId}:start` — allows admin to navigate within the impersonation view without resetting the 30-minute clock
- `ImpersonationBanner` background changes amber → red when <5 min remain — clear urgency signal without interrupting the admin's work
- Impersonation page intentionally renders inside `(admin)` layout (AdminSidebar visible) — admin always knows they are in admin mode; Phase 13 may change this for deeper simulation

## Deviations from Plan

None — plan executed exactly as written. All types, component structure, and behavior match the plan specification.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 13 (interactive impersonation) can now import `ImpersonationProvider` and use the established `PersonaContext` override pattern to render actual persona layouts with the target user's data
- `/admin/users/[id]` (from Plan 09-03) should include a "View as User" button linking to `/admin/impersonate/{userId}` — this is the entry point from the user detail page

---
*Phase: 09-user-management*
*Completed: 2026-03-21*
