---
phase: 07-foundation
plan: 04
subsystem: ui
tags: [nextjs, react, typescript, supabase, sse, fetchEventSource, tailwind, lucide-react]

# Dependency graph
requires:
  - phase: 07-01
    provides: "require_admin dependency, GET /admin/check-access endpoint, admin_audit_log table"
  - phase: 07-03
    provides: "POST /admin/chat/stream SSE endpoint, GET /admin/chat/sessions, GET /admin/chat/history"
provides:
  - "(admin) route group with server-side AdminGuard in layout.tsx"
  - "AdminSidebar with 10 nav items in dark theme"
  - "useAdminChat hook with SSE streaming, session persistence, confirmation state"
  - "AdminChatPanel collapsible bottom-right chat panel"
  - "ConfirmationCard with risk-level colour-coding and double-click protection"
  - "Audit log viewer at /admin/audit-log with source/date filters and pagination"
affects: [07-05, 07-06, 07-07, 07-08, 07-09, 07-10, 07-11, 07-12, 07-13, 07-14, 07-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server component AdminGuard: layout.tsx fetches /admin/check-access server-side — non-admins redirected before any React renders"
    - "Client component chat panel imported into server layout (Next.js handles boundary transparently)"
    - "Single-use confirmation token: cleared from pendingConfirmation immediately on Confirm click, button disabled to prevent replay"
    - "SSE streaming via fetchEventSource with onopen/onmessage/onerror handlers mirroring useAgentChat pattern"

key-files:
  created:
    - frontend/src/app/(admin)/layout.tsx
    - frontend/src/app/(admin)/page.tsx
    - frontend/src/app/(admin)/audit-log/page.tsx
    - frontend/src/components/admin/AdminSidebar.tsx
    - frontend/src/components/admin/AdminChatPanel.tsx
    - frontend/src/components/admin/ConfirmationCard.tsx
    - frontend/src/components/admin/adminNav.ts
    - frontend/src/hooks/useAdminChat.ts
  modified: []

key-decisions:
  - "AdminGuard is server-side only: layout.tsx calls /admin/check-access with Bearer token — redirect happens before client bundle loads, no UI flash possible"
  - "Chat panel streams to /admin/chat/stream (07-03 endpoint), not the main /a2a/app/run_sse"
  - "ConfirmationCard double-click protection: local clicked state disables button immediately on first click, independent of isProcessing prop"
  - "Audit log uses client-side fetch (not server component) to support filter/pagination interactions without full page reload"

patterns-established:
  - "Admin dark theme: bg-gray-900/bg-gray-950 base, indigo-600 accent, all admin components consistently dark"
  - "Admin route group: (admin)/ prefix isolates admin pages; layout.tsx is the single access gate"
  - "useAdminChat mirrors useAgentChat structure but strips widget/workspace concerns — admin-specific simpler interface"

requirements-completed: [ASST-01, ASST-04, ASST-06, AUDT-03, AUTH-05]

# Metrics
duration: 7min
completed: 2026-03-21
---

# Phase 7 Plan 04: Admin Frontend Shell Summary

**Server-side AdminGuard layout + dark sidebar + SSE chat panel with confirmation card + audit log viewer — complete admin frontend shell**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-21T11:37:38Z
- **Completed:** 2026-03-21T11:44:41Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Admin route group `(admin)/` with server-side access guard in `layout.tsx` — non-admins redirected to `/dashboard` before any React renders, eliminating UI flash
- Dark-theme AdminSidebar with 10 navigation items and active-route highlighting via `usePathname`; `useAdminChat` hook mirroring `useAgentChat` pattern with SSE streaming, session persistence, and single-use confirmation token state
- ConfirmationCard with risk-level colour-coding (red/amber/green) and double-click protection; AdminChatPanel collapsible bottom-right panel with auto-scroll; audit log page with source/date filters and prev/next pagination

## Task Commits

Each task was committed atomically:

1. **Task 1: Admin layout + AdminGuard + sidebar + navigation** - `af4771a` (feat)
2. **Task 2: useAdminChat hook + AdminChatPanel + ConfirmationCard + audit log page** - `627ba3b` (feat)

## Files Created/Modified

- `frontend/src/app/(admin)/layout.tsx` — Server component: session check, /admin/check-access fetch, redirect guard, renders AdminSidebar + main + AdminChatPanel
- `frontend/src/app/(admin)/page.tsx` — Admin overview page with 6 placeholder status cards
- `frontend/src/app/(admin)/audit-log/page.tsx` — Client component: audit trail table with source/date-range filters and prev/next pagination
- `frontend/src/components/admin/AdminSidebar.tsx` — Dark-theme sidebar, 10 nav items, active highlighting, admin email display, back-to-dashboard link
- `frontend/src/components/admin/AdminChatPanel.tsx` — Collapsible bottom-right chat panel, SSE messages, ConfirmationCard inline rendering, auto-scroll
- `frontend/src/components/admin/ConfirmationCard.tsx` — Amber-bordered confirmation card, risk-level badge + button colours, single-click protection with spinner
- `frontend/src/components/admin/adminNav.ts` — ADMIN_NAV_ITEMS array with 10 items and Lucide icons
- `frontend/src/hooks/useAdminChat.ts` — SSE hook: sendMessage, confirmAction, rejectAction, loadHistory, loadSessions, pendingConfirmation state

## Decisions Made

- AdminGuard is pure server-side: `layout.tsx` calls `/admin/check-access` with Bearer token before rendering any children — redirect happens before client bundle loads, eliminating UI flash risk
- Chat panel targets `/admin/chat/stream` (Plan 03 endpoint) rather than the main A2A endpoint — admin chat is a separate concern with different session model
- ConfirmationCard tracks a local `clicked` boolean that disables the button immediately on first click, independent of the async `isConfirming` prop, providing instant UI feedback and preventing replay
- Audit log is a `'use client'` component to support interactive filters and pagination without full page reloads

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. TypeScript compiled cleanly on first pass for both tasks.

## User Setup Required

None - no external service configuration required. The admin frontend connects to backend endpoints already built in Plans 01 and 03.

## Next Phase Readiness

- Complete admin frontend shell is ready for Plan 05 (Wave 2 completion)
- All pages beyond Overview and Audit Log show placeholder content — subsequent plans (08+) will populate them
- AdminChatPanel is wired to `/admin/chat/stream` — requires Plan 03's backend to be running for live testing
- The `(admin)/` route group acts as the single entry point for all future admin pages; simply add pages under `frontend/src/app/(admin)/`

---
*Phase: 07-foundation*
*Completed: 2026-03-21*

## Self-Check: PASSED

All 8 created files confirmed on disk. Both task commits (af4771a, 627ba3b) confirmed in git log.
