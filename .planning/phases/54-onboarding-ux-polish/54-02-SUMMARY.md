---
phase: 54-onboarding-ux-polish
plan: "02"
subsystem: google-workspace-credential-persistence
tags: [google-oauth, auth-callback, integrations, gmail, calendar, configuration]

requires: [54-01]

provides:
  - Canonical backend Google Workspace credential sync and truthful status contract
  - Server-side Supabase callback sync so Google provider tokens are persisted without exposing them to browser code
  - Shared Google credential resolver for foreground tools and background briefing/triage consumers
  - Frontend reconnect UX that reflects reusable stored auth rather than optimistic identity-only checks

affects:
  - app/services/google_workspace_auth_service.py
  - app/routers/configuration.py
  - app/routers/briefing.py
  - app/integrations/google/client.py
  - app/agents/tools/calendar_tool.py
  - app/agents/tools/gmail.py
  - app/agents/tools/gmail_inbox.py
  - app/agents/tools/docs.py
  - app/agents/tools/forms.py
  - app/agents/tools/google_sheets.py
  - app/agents/tools/briefing_tools.py
  - app/services/briefing_digest_service.py
  - app/services/email_triage_worker.py
  - frontend/src/app/auth/callback/route.ts
  - frontend/src/app/api/configuration/google-workspace-status/route.ts
  - frontend/src/app/dashboard/configuration/page.tsx
  - frontend/src/__tests__/services/google-workspace-status.test.ts
  - tests/unit/app/test_google_workspace_auth_service.py

tech-stack:
  added: []
  patterns:
    - "canonical Google Workspace credentials stored in integration_credentials under a dedicated provider key"
    - "callback-time backend sync uses the Supabase session JWT server-side and never exposes provider tokens to frontend JS"
    - "Google runtime credential resolution prefers canonical storage, falls back to controlled legacy sources, and forces refresh-capable credentials for stored sessions"
    - "configuration status reflects reusable stored auth and surfaces reconnect guidance when only identity or partial tokens exist"

requirements-completed: [UX-02]

completed: 2026-04-11
---

# Phase 54 Plan 02: Google Workspace Credential Persistence Summary

Completed the second slice of Phase 54 by making Google Workspace connection state real, reusable, and truthful across callback, runtime, and configuration UX.

## Accomplishments

- Added `app/services/google_workspace_auth_service.py` as the canonical Google Workspace auth service to:
  - persist encrypted Google Workspace credentials into `integration_credentials`
  - preserve an existing refresh token when a later sync only returns a new access token
  - resolve Google credentials from canonical storage first, then controlled legacy fallbacks
  - report a truthful connection contract for the configuration UI
- Updated `app/routers/configuration.py` to:
  - expose truthful `GET /configuration/google-workspace-status`
  - add authenticated `POST /configuration/google-workspace/sync`
  - return reconnect-specific state instead of treating Google identity presence as equivalent to a usable Workspace connection
- Updated `frontend/src/app/auth/callback/route.ts` so successful Supabase OAuth callback exchange now:
  - resolves provider tokens on the server
  - calls the backend sync endpoint with the Supabase session JWT
  - logs sync failures without breaking the successful auth redirect flow
- Extended `app/integrations/google/client.py` with shared stored-credential resolution helpers so later-session Google actions can rebuild refresh-capable credentials from backend-owned state
- Updated the Google tool and briefing paths to use the shared resolver rather than depending only on `tool_context.state` session tokens:
  - calendar
  - Gmail send/inbox
  - Docs
  - Forms
  - Sheets
  - briefing draft approval
  - digest sending
  - email triage worker refresh-token lookup
  - briefing router draft-send path
- Updated `frontend/src/app/dashboard/configuration/page.tsx` and the Next API proxy route so the UI now shows:
  - connected only when reusable stored auth exists
  - reconnect guidance when only identity or partial token state exists
  - a secure “Continue with Google” / reconnect CTA instead of telling the user to sign out manually
- Added focused backend and frontend regression tests for:
  - sync persistence behavior
  - truthful status semantics
  - callback-time backend sync contract
  - authenticated status route passthrough

## Verification

- `uv run pytest tests/unit/app/test_google_workspace_auth_service.py -x` passed
- `uv run pytest tests/unit/test_calendar_tools.py tests/unit/test_gmail_inbox_tools.py tests/unit/test_briefing_tools.py tests/unit/test_email_triage_worker.py -x` passed
- `cd frontend && npm run test -- src/__tests__/services/google-workspace-status.test.ts` passed
- `cd frontend && npx tsc -p . --noEmit` passed

## Deviations From Plan

- The real credential reuse seam extended into `app/routers/briefing.py` and the Next.js status proxy route, so both were added to the actual execution scope to keep briefing send paths and configuration status aligned with the new canonical contract.
- Compatibility fallback was retained for legacy Google token storage (`user_google_tokens`, RPC refresh token lookup, `user_oauth_tokens`) so existing users are not broken while the canonical `integration_credentials` path becomes the new source of truth.

## Next Phase Readiness

- Phase 54 remains in progress
- The next live gap is `54-03-PLAN.md`: dashboard empty-state polish sweep

## Self-Check: PASSED

Google Workspace auth is now persisted through a backend-owned path, status only reports connected when the app can actually reuse the credentials later, and both interactive Google tools and background email flows verified against the shared resolver path.
