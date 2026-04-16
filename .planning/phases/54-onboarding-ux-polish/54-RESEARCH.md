# Phase 54: Onboarding & UX Polish - Research

**Researched:** 2026-04-11
**Status:** Complete

## Research Question

What is the lowest-risk way to complete the v7 signup-to-first-use experience without drifting outside the existing GSD roadmap or reopening already-stable auth work?

## Findings

### 1. The current onboarding flow is feature-rich, but the final handoff is broken

- The conversational onboarding flow already captures:
  - agent name
  - business discovery messages
  - persona extraction
  - preferences
  - selected first action
- `OnboardingTransition.tsx` already submits onboarding data and completes onboarding successfully.
- The break happens **after** completion:
  - it redirects to `/dashboard/command-center?initialPrompt=...`
  - command center hides chat via `showChat={false}`
  - `PersonaDashboardLayout.tsx` does not read `initialPrompt` from the URL anyway
- Result: the selected first action does not reliably become the user’s first live chat message.

### 2. Checklist actions are only half-wired on command center

- `OnboardingChecklist.tsx` can pass a prompt upward through `onActionClick`.
- `PersonaDashboardLayout.tsx` stores that prompt in `initialChatPrompt`.
- That works only when the page actually renders chat.
- On command center, the chat panel is hidden, so the checklist can mark progress without moving the user into an actionable conversation.

### 3. Google Workspace status is currently optimistic, not authoritative

- `frontend/src/services/auth.ts` correctly asks Google for Gmail and Calendar scopes.
- `frontend/src/app/auth/callback/route.ts` exchanges the auth code for a Supabase session, but no backend sync path currently persists provider tokens as a canonical Google Workspace credential record.
- `app/routers/configuration.py` reports “Google Workspace connected” if the user has a Google identity in Supabase Auth.
- That status does **not** prove:
  - a usable refresh token exists
  - the access token was persisted for later use
  - background jobs or later agent actions can still access Gmail/Calendar

### 4. Google credential consumption is fragmented

- Foreground Google tools expect live `tool_context.state["google_provider_token"]` and `tool_context.state["google_refresh_token"]`.
- Background consumers read legacy storage paths:
  - `user_google_tokens`
  - `user_oauth_tokens`
  - in other integrations, `integration_credentials`
- Code search did not find a single canonical sync path that writes Google sign-in credentials after the normal Supabase auth callback.
- The lowest-risk fix is to introduce a canonical backend Google Workspace credential service, sync into it from the auth callback, and allow existing consumers to migrate onto it with controlled compatibility fallbacks.

### 5. Empty-state infrastructure already exists, so Phase 54 should be a polish sweep, not a redesign

- Shared component: `frontend/src/components/ui/EmptyState.tsx`
- Persona/widget configuration: `personaEmptyStates.ts`
- Many pages already have decent empty states.
- Remaining gaps are concentrated in dashboard pages that still use:
  - raw “No data available” text
  - passive no-data labels with no CTA
  - empty summaries that do not tell the user what to do next

## Recommended Phase Split

### Plan 01: Onboarding-to-first-chat completion

- Create one shared chat-launch helper
- Route onboarding completion and command-center checklist actions into a chat-enabled surface
- Teach `PersonaDashboardLayout` to honor a sanitized `initialPrompt`
- Add frontend regression tests for launch URL and prompt extraction behavior

### Plan 02: Google Workspace credential persistence + verified status

- Add a canonical backend Google Workspace credential sync/resolution path
- Sync provider tokens after Supabase auth callback in a server-only flow
- Update backend status to reflect usable stored access, not only Google identity presence
- Let Google tools/background services resolve stored credentials without forcing re-auth

### Plan 03: Dashboard empty-state polish sweep

- Reuse the shared empty-state component
- Upgrade the main zero-data dashboard pages that still rely on passive placeholders
- Add CTAs that route users toward chat, workflow setup, or data connection

## Validation Architecture

Phase 54 needs a mixed frontend/backend validation strategy:

- **Frontend:** Vitest coverage for onboarding launch helpers and representative empty-state rendering
- **Backend:** pytest coverage for canonical Google Workspace credential sync and retrieval behavior
- **Type safety:** `npx tsc -p . --noEmit`
- **Manual:** one real signup/onboarding/first-chat pass and one real Google OAuth follow-up action pass

## Risks and Pitfalls

### Pitfall 1: Fixing only the route but not the prompt parser

Sending the user to a chat-enabled page is not enough if the target layout still ignores `initialPrompt`.

### Pitfall 2: Declaring Google Workspace “connected” without refresh-capable persistence

This would keep the UX green while background or later-session Google actions still fail.

### Pitfall 3: Migrating Google consumers too aggressively

There are multiple legacy token lookup paths. A compatibility layer is safer than a flag day rewrite.

### Pitfall 4: Replacing page copy without actionable CTA wiring

A prettier “No data yet” message still misses the Phase 54 requirement if the user has no obvious next action.

## Conclusion

Phase 54 should be executed in three plans:

1. Fix the onboarding launch path first
2. Make Google Workspace persistence truthful and reusable
3. Sweep the remaining dashboard empty states into a consistent, actionable UX

That order closes the clearest first-use break immediately while keeping the larger Google persistence work inside the same v7 phase.

---

*Phase: 54-onboarding-ux-polish*
*Research completed: 2026-04-11*
