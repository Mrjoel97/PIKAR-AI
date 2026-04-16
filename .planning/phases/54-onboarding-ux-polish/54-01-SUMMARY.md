---
phase: 54-onboarding-ux-polish
plan: "01"
subsystem: onboarding-first-chat-handoff
tags: [onboarding, chat-launch, dashboard, persona, session]

requires: []

provides:
  - Shared onboarding/chat launch helper for persona routes and dashboard prompt parsing
  - Post-onboarding redirect into a chat-enabled persona surface instead of hidden-chat command center
  - Fresh-session launch behavior so onboarding, initiative, and checklist prompts are not swallowed by restored chat history
  - One-shot dashboard launch param cleanup that preserves unrelated query state

affects:
  - frontend/src/lib/onboarding/navigation.ts
  - frontend/src/app/onboarding/components/OnboardingTransition.tsx
  - frontend/src/app/onboarding/processing/page.tsx
  - frontend/src/components/dashboard/PersonaDashboardLayout.tsx
  - frontend/src/components/chat/ChatInterface.tsx
  - frontend/src/__tests__/services/onboarding-launch.test.ts

tech-stack:
  added: []
  patterns:
    - "shared onboarding launch helper builds and parses sanitized initialPrompt persona routes"
    - "prompt launches always create a fresh chat session before auto-send so restored history cannot consume the handoff"
    - "dashboard launch params are stripped after capture while preserving unrelated query state"

requirements-completed: [UX-01]

completed: 2026-04-11
---

# Phase 54 Plan 01: Onboarding-to-First-Chat Summary

Completed the first slice of Phase 54 by making the signup and checklist handoff land in a real live chat flow.

## Accomplishments

- Added `frontend/src/lib/onboarding/navigation.ts` to centralize:
  - persona chat launch route building
  - post-onboarding fallback routing
  - dashboard launch prompt extraction for `initialPrompt`, initiative, journey, and braindump flows
  - launch-param cleanup that preserves unrelated query state
- Updated `OnboardingTransition.tsx` so onboarding completion now routes to `/{persona}?initialPrompt=...` instead of `/dashboard/command-center`
- Updated the legacy onboarding processing page so its fallback destination is also chat-enabled (`/{persona}` or `/dashboard/workspace`)
- Reworked `PersonaDashboardLayout.tsx` so launch prompts:
  - are parsed through the shared helper
  - create a fresh chat session before sending
  - redirect hidden-chat command-center launches onto a chat-enabled persona route
  - clear launch params after capture to avoid replay on refresh
- Fixed `ChatInterface.tsx` so an initial prompt can auto-send into a fresh session that only contains the default welcome message
- Added focused frontend regression coverage for launch URL building, prompt extraction, braindump/journey launches, and launch-param cleanup

## Verification

- `cd frontend && npm run test -- src/__tests__/services/onboarding-launch.test.ts` passed
- `cd frontend && npx tsc -p . --noEmit` passed

## Deviations From Plan

- The core launch bug extended into `frontend/src/components/chat/ChatInterface.tsx`, because the existing auto-send logic treated a welcome-only session as non-empty and therefore blocked all initial prompts. That file was added to the actual execution scope to close the handoff end to end.
- Command-center checklist behavior was fixed through the shared dashboard layout launch path instead of editing `OnboardingChecklist.tsx` or `command-center/page.tsx` directly.

## Next Phase Readiness

- Phase 54 remains in progress
- The next live gap is `54-02-PLAN.md`: Google Workspace credential persistence and truthful reconnect/status UX

## Self-Check: PASSED

Onboarding, checklist, initiative, and braindump prompt launches now share one chat-first handoff path, and the core route/session behavior verified with frontend Vitest plus TypeScript compilation.
