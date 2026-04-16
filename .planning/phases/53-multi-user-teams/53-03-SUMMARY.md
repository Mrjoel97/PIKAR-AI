---
phase: 53-multi-user-teams
plan: "03"
subsystem: teams-ui
tags: [team-settings, invites, pending-invites, rbac, resend-email]

requires:
  - phase: 53-multi-user-teams
    provides: "Invite email route + pending invite backend APIs from 53-01"

provides:
  - Team settings page at /dashboard/settings/team with admin invite controls and shared member list
  - Email-based invite form with Admin/Member selector and toast feedback
  - Pending invites UI with resend/revoke actions and expiry countdowns

affects:
  - frontend/src/components/team/InviteLinkGenerator.tsx
  - frontend/src/components/team/PendingInvitesList.tsx
  - frontend/src/app/dashboard/settings/team/page.tsx
  - frontend/src/components/layout/sidebarNav.ts
  - frontend/src/app/api/teams/invite/route.ts

tech-stack:
  added: []
  patterns:
    - "refreshKey callback from invite form to pending invites list for deterministic refetch"
    - "resend flow uses backend token refresh first, then Next.js invite API for email delivery"
    - "admin-only navigation entry with PermissionGate-hidden invite controls for direct-link member access"

requirements-completed: [TEAM-01, TEAM-03]

duration: 37min
completed: 2026-04-10
---

# Phase 53 Plan 03: Team Settings UI + Pending Invite Management Summary

Implemented the full team settings management surface under `/dashboard/settings/team`, including email invite send, pending invite lifecycle actions, and member visibility controls.

## Accomplishments

- Replaced the old link-generator invite component with an email-first invite form (`email + Admin/Member role + Send Invite`) wired to `POST /api/teams/invite`.
- Added `PendingInvitesList` with loading and empty states, role badges, sent date, expiry countdown, resend, and revoke actions.
- Implemented resend delivery without duplicate invite creation by:
  - rotating token via `POST /teams/invites/{id}/resend`
  - reusing the refreshed token in `POST /api/teams/invite` for email send
- Created new `Team Settings` page at `/dashboard/settings/team` with:
  - admin-only invite + pending sections (via `PermissionGate require="manage-team" fallback="hide"`)
  - shared member list visible to all roles
  - updated role reference card (Admin, Member)
- Added admin-only `Team Settings` entry in sidebar navigation.

## Verification

- `npx tsc -p . --noEmit` (frontend) passed.

## Deviations From Plan

- Extended `POST /api/teams/invite` to accept resend payload fields (`inviteToken`, `inviteExpiresAt`, `inviteId`) so pending-invite resends can deliver email using the refreshed token from backend without creating duplicate invites.
- Added optional `viewer` role handling in the same route for legacy pending invites still stored with viewer role.

## Next Phase Readiness

- 53-04 can focus on the public `/invite/[token]` acceptance surface and final role alignment while reusing the new settings page and pending-invite UX.

## Self-Check: PASSED

Frontend TypeScript compilation passed after integrating new team settings route, invite form, pending invite list, and sidebar navigation updates.
