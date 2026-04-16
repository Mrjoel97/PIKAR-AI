---
phase: 53-multi-user-teams
plan: "04"
subsystem: invite-acceptance
tags: [invite-flow, auth-return, role-alignment, teams, public-route]

requires:
  - phase: 53-multi-user-teams
    provides: "Invite email route, pending invites UI, and RBAC member management foundation"

provides:
  - Public invite acceptance route at /invite/[token] for logged-in and logged-out users
  - Auth returnUrl handling across login, signup, and OAuth callback for invite continuation
  - Admin/Member-only role vocabulary in role controls and team dashboard reference
  - Legacy /dashboard/team/join compatibility redirect for already-sent invite links

affects:
  - frontend/src/app/invite/[token]/page.tsx
  - frontend/src/app/api/teams/invite-details/route.ts
  - frontend/src/app/dashboard/team/join/page.tsx
  - frontend/src/components/team/RoleDropdown.tsx
  - frontend/src/app/dashboard/team/page.tsx
  - frontend/src/services/auth.ts
  - frontend/src/app/auth/login/LoginPage.tsx
  - frontend/src/app/auth/signup/SignupPage.tsx
  - frontend/src/app/auth/callback/route.ts
  - frontend/src/app/api/teams/invite/route.ts
  - app/routers/teams.py

tech-stack:
  added: []
  patterns:
    - "public invite metadata resolved through a small Next.js service-role route instead of anonymous cross-table joins"
    - "auth returnUrl propagated through email/password login, signup, and Google OAuth callback"
    - "legacy viewer roles normalized to Member vocabulary in UI while backend schema remains admin/editor/viewer compatible"

requirements-completed: [TEAM-02, TEAM-03]

duration: 22min
completed: 2026-04-10
---

# Phase 53 Plan 04: Public Invite Flow + Final Role Alignment Summary

Completed the public invite acceptance flow and finalized the Admin/Member role vocabulary across the team surface.

## Accomplishments

- Added public invite page at `/invite/[token]` that:
  - loads invite metadata before acceptance
  - supports logged-in immediate acceptance
  - supports logged-out login/signup prompts with invite email prefill
  - refreshes workspace context after join and redirects to `/dashboard`
- Added `GET /api/teams/invite-details` so the public invite page can safely show workspace name, role, inviter name, and expiry without anonymous RLS join issues
- Updated auth helpers and auth pages so `returnUrl` is preserved through:
  - email/password login
  - signup
  - Google OAuth callback
- Replaced the old `/dashboard/team/join?token=...` page with a compatibility redirect to `/invite/{token}` so previously-sent invite emails still work
- Updated role management UI to Admin/Member only and aligned the team dashboard role reference card to the same two-role model
- Fixed owner badge rendering on the team dashboard by resolving the real workspace owner ID instead of passing an empty placeholder
- Switched newly-generated invite links to `/invite/{token}` in both the Next.js invite email route and backend share URL generation

## Verification

- `npx tsc -p . --noEmit` (frontend) passed
- `uv run python -c "from app.routers.teams import router; print('Imports OK')"` passed
- Browser validation on `2026-04-10` loaded `/invite/test-token` in Playwright and confirmed the public invite page renders for logged-out users
- Fixed a post-completion route bug in `frontend/src/app/invite/[token]/page.tsx` by switching token resolution to `useParams()`, restoring correct auth continuation links (`/auth/login?returnUrl=%2Finvite%2F{token}` and `/auth/signup?returnUrl=%2Finvite%2F{token}`)
- Browser validation remains blocked from true end-to-end acceptance in the current local environment because:
  - `frontend/.env` does not include `SUPABASE_SERVICE_ROLE_KEY`, so `GET /api/teams/invite-details` returns `500 Server configuration error`
  - the configured Supabase project `rbdowedrdhtlbngapexj` does not currently contain `workspaces`, `workspace_members`, or `workspace_invites`, so even with the frontend env fixed the team invite backend cannot complete against this database yet

## Deviations From Plan

- Added auth continuation support in login, signup, auth callback, and shared auth helpers because the planned public invite page could not resume correctly after authentication without it
- Added a dedicated public invite metadata route because anonymous frontend reads could access `workspace_invites` but not workspace names through RLS-protected joins
- Updated the legacy join route to redirect to `/invite/{token}` so pre-53-04 invite emails remain valid
- Applied a post-completion compatibility fix for Next.js 16 dynamic route params after browser validation exposed `params.token` resolving to `undefined` in the client page

## Next Phase Readiness

- Phase 53 is now complete end-to-end
- The next GSD anchor is Phase 54 planning for onboarding and UX polish

## Self-Check: PASSED

Frontend TypeScript compilation passed, and the backend teams router import check succeeded after the invite URL change.
