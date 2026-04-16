# Phase 54: Onboarding & UX Polish - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 54 closes the remaining user-facing readiness gaps between account creation and confident day-one use:

1. **Signup-to-first-chat completion** — a new user must be able to sign up, finish onboarding, land on a chat-enabled surface, and have their selected “first action” actually launch into the first live conversation.
2. **Google Workspace credential persistence** — Google OAuth must persist usable credentials after auth callback so Gmail and Calendar flows still work on later actions, not only during the fresh session exchange.
3. **Dashboard empty-state polish** — the remaining zero-data dashboard surfaces must show intentional empty states with a suggested next action instead of raw placeholder copy or passive “no data” text.

**Out of scope for Phase 54**:
- Load, SSE isolation, or concurrency work planned for Phase 55
- GDPR export/deletion or Knowledge Vault hardening planned for Phase 56
- Replacing Supabase Auth or redesigning the entire auth stack
- Broad dashboard redesign unrelated to onboarding, Google Workspace, or empty-state clarity
- Shipping brand-new product features beyond the scoped UX fixes

</domain>

<decisions>
## Implementation Decisions

### Execution Order

- **Fix the onboarding-to-first-chat handoff first.** It is the clearest user-facing break in the current v7 journey and the safest Phase 54 entry point.
- **Keep Phase 54 inside the main GSD roadmap.** No extracted side plan or detached tracking system.

### Onboarding Launch Behavior

- **Post-onboarding actions must land on a chat-enabled route.** A selected first action is only complete if the user can immediately see the live chat surface that will execute it.
- **Prompt handoff should be handled through one shared helper.** Avoid duplicating route-building and prompt-extraction logic across onboarding, checklist, and dashboard shells.
- **Query-delivered prompts must be consumed once.** Initial launch prompts should be read, passed to chat, and then cleared from the URL so refreshes do not replay them.

### Google Workspace Security Boundary

- **Do not expose Google OAuth tokens in browser-visible code.** Session token synchronization should happen in server-only or backend-owned execution paths.
- **“Connected” must mean usable credentials are stored.** The status UI must not report success based only on a Google identity being present in Supabase Auth.
- **Use one canonical backend credential resolution path.** Google tools and background jobs should stop depending on multiple disconnected token tables.

### Empty State UX

- **Reuse the existing empty-state design language.** Prefer extending `frontend/src/components/ui/EmptyState.tsx` or equivalent shared patterns over inventing per-page one-offs.
- **Every targeted empty state needs a suggested next action.** “No data” without an obvious next move does not satisfy Phase 54.

### Claude's Discretion

The executor may decide without re-asking:
- Whether the chat-enabled onboarding handoff lands on a persona route or workspace route, provided chat is visible and prompt handoff works
- The exact helper/module names used to centralize onboarding launch behavior
- Whether Google Workspace compatibility reads should temporarily fall back to legacy tables during migration, provided the new canonical path is clear
- Which representative dashboard pages are upgraded in Plan 03, provided the main user-facing zero-data surfaces are covered

</decisions>

<specifics>
## Specific Ideas

- A dedicated onboarding launch helper can standardize both “where should we send the user?” and “what prompt should chat receive?”
- The Supabase auth callback route is a strong place to sync Google provider tokens to the backend because it already runs server-side after `exchangeCodeForSession`.
- The empty-state sweep should prioritize dashboard pages that currently show plain text placeholders without CTA guidance.

</specifics>

<code_context>
## Existing Code Insights

### Onboarding and First Chat

- `frontend/src/app/onboarding/components/OnboardingTransition.tsx` currently redirects to `/dashboard/command-center?initialPrompt=...`.
- `frontend/src/app/dashboard/command-center/page.tsx` renders `PersonaDashboardLayout` with `showChat={false}`, so the chat surface is intentionally hidden there.
- `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` computes launch prompts from `context`, `initiativeId`, `braindump_id`, and related params, but it does **not** currently read the `initialPrompt` query parameter.
- `frontend/src/components/dashboard/OnboardingChecklist.tsx` can queue prompts through `onActionClick`, but on command-center the hidden chat panel means those prompts do not become an immediate conversation.

### Google Workspace

- `frontend/src/services/auth.ts` requests Gmail and Calendar scopes during `signInWithGoogle`.
- `frontend/src/app/auth/callback/route.ts` exchanges the Supabase code for a session and redirects, but does not currently persist Google provider tokens through a backend-owned sync path.
- `app/routers/configuration.py` reports Google Workspace status by checking whether the user has a Google identity in Supabase Auth, not whether usable stored credentials exist.
- Backend consumers currently read Google credentials from multiple places:
  - live tool context state (`google_provider_token`, `google_refresh_token`)
  - `user_google_tokens`
  - `user_oauth_tokens`
  - `integration_credentials`
- Code search did not reveal a canonical write path that syncs Google auth callback tokens into those backend persistence tables after normal user sign-in.

### Empty States

- Shared empty-state infrastructure already exists in `frontend/src/components/ui/EmptyState.tsx`.
- Persona/widget empty-state config also exists in `frontend/src/components/personas/personaEmptyStates.ts` and `frontend/src/components/widgets/PersonaEmptyState.tsx`.
- Several dashboard pages still rely on raw placeholder copy such as “No data available”, “No pending approval chains”, or passive no-data text without a CTA.

</code_context>

<deferred>
## Deferred Ideas

- Full browser/manual OAuth seam testing belongs to Phase 55
- Any Google Workspace scope expansion beyond Gmail + Calendar persistence
- A global dashboard-wide empty-state registry beyond what Phase 54 needs to finish v7 cleanly

</deferred>

---

*Phase: 54-onboarding-ux-polish*
*Context gathered: 2026-04-11*
