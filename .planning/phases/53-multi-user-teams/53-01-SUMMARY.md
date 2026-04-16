---
phase: 53-multi-user-teams
plan: "01"
subsystem: teams
tags: [team-invites, resend, pending-invites, resend-email, rbac]

requires:
  - phase: 49-security-auth-hardening
    provides: "Workspace/team RBAC foundation and invite acceptance route"

provides:
  - Branded team invite email template and authenticated Next.js invite-delivery route
  - invited_email persistence on workspace_invites with admin-compatible invite roles
  - Pending invite listing, revoke, and resend backend endpoints with governance logging

affects:
  - frontend/emails/team-invite.tsx
  - frontend/src/app/api/teams/invite/route.ts
  - app/services/workspace_service.py
  - app/routers/teams.py
  - supabase/migrations/20260409200000_invite_email_field.sql

tech-stack:
  added: []
  patterns:
    - "Server-side invite bridge route: Supabase session access_token forwarded from Next.js API route to backend /teams endpoints"
    - "Best-effort inviter-name enrichment for pending invites via user_profiles lookups"
    - "Invite acceptance email keeps the working /dashboard/team/join token path live until 53-04 lands public /invite/[token]"

key-files:
  created:
    - frontend/emails/team-invite.tsx
    - frontend/src/app/api/teams/invite/route.ts
    - supabase/migrations/20260409200000_invite_email_field.sql
  modified:
    - app/services/workspace_service.py
    - app/routers/teams.py

key-decisions:
  - "Expanded workspace_invites role constraint to include admin so the new Admin/Member UX can coexist with legacy editor/viewer invite callers"
  - "Mapped frontend Member invites to backend editor while preserving legacy viewer support for the older share-link generator"
  - "Used the current /dashboard/team/join acceptance URL in invite emails to avoid dead links before 53-04 ships the public invite page"

patterns-established:
  - "Governance audit actions invite.revoked and invite.resent for pending-invite lifecycle changes"
  - "Pending invite resend regenerates token + expiry in the backend and returns the refreshed invite payload for downstream email delivery"

requirements-completed: [TEAM-01, TEAM-02]

duration: 43min
completed: 2026-04-10
---

# Phase 53 Plan 01: Invite Email Delivery + Pending Invites Backend Summary

**Branded team-invite email flow plus backend pending-invite management for Phase 53.**

## Performance

- **Duration:** 43 min
- **Completed:** 2026-04-10T13:58:52Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added a Pikar AI branded invite email template that includes inviter name, workspace name, role, and accept CTA
- Added `POST /api/teams/invite` in Next.js to validate email input, forward the authenticated session to the backend, create the invite, and send the Resend email
- Added `invited_email` persistence on `workspace_invites` and expanded the invite-role constraint to allow admin invites alongside legacy editor/viewer callers
- Added backend pending-invite listing, revoke, and resend operations plus governance audit events for revoke/resend actions
- Preserved a working acceptance path by keeping invite emails pointed at the existing `/dashboard/team/join?token=...` route until the public `/invite/[token]` page lands in 53-04

## Verification

- `uv run ruff check app/services/workspace_service.py app/routers/teams.py --select E --select W --select F --select I`
- `uv run python -c "from app.services.workspace_service import WorkspaceService; from app.routers.teams import router; print('Imports OK')"`
- `npx tsc -p . --noEmit`

## Deviations From Plan

- The email CTA uses the current authenticated invite-acceptance route (`/dashboard/team/join?token=...`) instead of the planned public `/invite/[token]` route so invites remain functional before 53-04 is implemented.

## Next Phase Readiness

- 53-03 can now build the email-based invite form and pending-invites UI directly against the new backend/API surface
- 53-04 can swap the email acceptance URL over to the public `/invite/[token]` route without revisiting backend invite storage

## Self-Check: PASSED

Ruff passed, the frontend TypeScript project compiled, and backend imports succeeded after rerunning outside the sandbox.

---
*Phase: 53-multi-user-teams*
*Completed: 2026-04-10*
