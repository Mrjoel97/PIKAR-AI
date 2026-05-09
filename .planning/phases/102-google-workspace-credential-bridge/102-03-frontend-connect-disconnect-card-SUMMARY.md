---
phase: 102-google-workspace-credential-bridge
plan: 03
subsystem: frontend
tags: [google-workspace, oauth, configuration, vitest, frontend]
requirements: [WORKSPACE-01]
status: complete
completed: 2026-05-09
duration_minutes: 35
tasks_completed: 3
tests_added: 5
tests_passing: 5
files_modified:
  - frontend/src/app/dashboard/configuration/page.tsx
  - frontend/src/services/integrations.ts
files_created:
  - frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx
commits:
  - e647a910 test(102-03): add failing vitest tests for Google Workspace connect/disconnect card (WORKSPACE-01)
  - 0a18280d feat(102-03): add disconnectGoogleWorkspace helper for revoke-then-delete path
  - 071d2f6d feat(102-03): in-app Google Workspace connect/disconnect card with revoke (WORKSPACE-01) [merged into a docs(107-02) commit by a parallel agent — see Deviations §3]
dependency_graph:
  requires:
    - WORKSPACE-02 (PROVIDER_REGISTRY entry — Plan 102-01) — needed so /api/integrations/google_workspace/authorize routes correctly
    - WORKSPACE-05 (DELETE /api/configuration/google-workspace revoke — Plan 102-02) — needed so the disconnect button revokes at Google
  provides:
    - In-app Connect Google Workspace button (popup OAuth)
    - In-app Disconnect Google Workspace button (revoke-then-delete)
    - postMessage-driven status refresh of the dedicated googleWorkspace state slice
  affects:
    - frontend/src/app/dashboard/configuration/page.tsx (Google Workspace section + handleOAuthMessage listener)
    - frontend/src/services/integrations.ts (disconnectGoogleWorkspace helper)
key-decisions:
  - Used a dedicated disconnectGoogleWorkspace helper (not the generic disconnectProvider) because Google Workspace MUST go through /api/configuration/google-workspace to trigger the GoogleWorkspaceAuthService.disconnect revoke step shipped in 102-02
  - Used plain `fetch` for both /api/configuration/google-workspace-status and /api/configuration/google-workspace because the Next.js API proxy already forwards the user's session cookie (matches the pre-existing pattern in this file at lines 2883 and 3001)
  - Made handleOAuthMessage `async` so the inline await on /api/configuration/google-workspace-status is valid (the legacy fire-and-forget refreshIntegrationStatus call still runs synchronously first)
  - Mocked @/services/integrations entirely in the test (instead of vi.importActual + override) because vi.resetAllMocks in beforeEach was wiping the resolved-value implementations and crashing the page on render
---

# Phase 102 Plan 03: Frontend Connect/Disconnect Card Summary

**One-liner:** Replaced the legacy "sign out and sign back in" Google Workspace section in `/dashboard/configuration` with a real popup-OAuth Connect button and a revoke-aware Disconnect button, wiring the postMessage callback to re-fetch the dedicated `googleWorkspace` state slice.

## What changed

### A. New service helper — `frontend/src/services/integrations.ts`

Added `disconnectGoogleWorkspace()` that hits `DELETE /api/configuration/google-workspace` (the dedicated GoogleWorkspaceAuthService path that revokes at Google before deleting the local row). The generic `disconnectProvider()` is unchanged — other providers continue using `/integrations/{provider}`.

### B. Configuration page — `frontend/src/app/dashboard/configuration/page.tsx`

Three edits:

1. **Import** — added `disconnectGoogleWorkspace` to the existing import from `@/services/integrations`.
2. **handleOAuthMessage listener** (was lines 3008-3034, now ~3008-3056) — kept as a `useEffect` but the inner function is now `async`. After the existing `refreshIntegrationStatus()` call, when `event.data.provider === 'google_workspace' && event.data.success`, the listener also re-fetches `/api/configuration/google-workspace-status` and calls `setGoogleWorkspace(...)`. This is necessary because the dedicated `googleWorkspace` state slice (set on line 2789) is NOT covered by `refreshIntegrationStatus` (which only re-fetches `fetchIntegrationStatus()` for the generic-providers list).
3. **Google Workspace section** (was lines 3690-3748, now ~3713-3845):
   - The connected branch is preserved as-is (account email, features grid, "How to use" hint) and now appends a Disconnect button that calls `disconnectGoogleWorkspace()`, shows a `window.confirm` warning, then re-fetches `/api/configuration/google-workspace-status` to flip the UI back to the disconnected branch. The button uses the existing `Unlink` lucide icon and the existing `disconnectingProvider` state for the busy flag.
   - The disconnected branch is fully rewritten: the legacy "sign out and sign back in" copy is gone; in its place is a Connect Google Workspace button with the existing `Plug` lucide icon that drives `handleConnectIntegration('google_workspace')` -> popup at `/api/integrations/google_workspace/authorize` (routed by 102-01).

### C. Vitest — `frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx`

New file. 5 tests:

1. `shows Connect button (and no legacy "sign out" copy) when disconnected` — finds button by role+name `/connect google workspace/i` and asserts no `/sign out and sign back in/i` text remains.
2. `clicking Connect opens popup at /api/integrations/google_workspace/authorize` — spies on `window.open`, asserts URL matches `\/api\/integrations\/google_workspace\/authorize`, target `'oauth-popup'`, features contain `width=600` and `height=700`.
3. `postMessage triggers re-fetch of workspace status and flips UI to connected` — initial fetch returns `{connected:false}`, then dispatches `oauth-callback` postMessage with `provider:'google_workspace', success:true`; second fetch returns `{connected:true, email:'user@example.com',...}`; `waitFor` finds the email in the DOM.
4. `shows Disconnect button when connected (and no Connect button)` — initial fetch returns `{connected:true}`; asserts `/disconnect/i` button present and Connect button absent.
5. `clicking Disconnect calls DELETE /api/configuration/google-workspace and flips UI back` — clicks Disconnect, asserts a `fetch` call with method DELETE to `/api/configuration/google-workspace` (NOT to `/api/integrations/google_workspace`), then `waitFor` flips UI back to the disconnected branch.

## Verification

### Pre-existing infrastructure confirmed (no setup needed)

- **Vitest** was already configured with `frontend/vitest.config.mts`, `frontend/scripts/run-vitest.mjs`, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom` in devDependencies. No new config files were added.
- **`disconnectingProvider` state** (line 2800), **`setGoogleWorkspace` setter** (line 2789), and **`googleWorkspace` state** (line 2789) all already existed in the component.
- **`Plug` icon** (line 39) and **`Unlink` icon** (line 25) were already imported from `lucide-react`.
- **GoogleWorkspaceStatus interface** at line 102 has shape `{ connected, email?, provider?, features[], message }` — slightly different from what the plan's RESEARCH section described (the plan said `{ connected, accountName?, scopes?, expiresAt?, lastSync? }`), but the implementation matches the actual interface.

### Test results

- **Before Task 3:** 5/5 tests fail with assertion errors (RED, as required by TDD).
- **After Task 3:** 5/5 tests pass (GREEN). Run time ~5 s.

### TypeScript / lint

- `npx tsc --noEmit -p frontend` reports zero errors in `page.tsx`, `integrations.ts`, and the new test file. (One unrelated pre-existing error remains in `RecentWidgets.tsx` — out of scope.)
- `npx eslint` on the three modified files reports zero errors (some pre-existing warnings in `page.tsx` are unchanged: 4 unused-var warnings and 1 unused-import warning that were already there before this plan).

### Plan-level success criteria

| Criterion | Status |
| --- | --- |
| Legacy "sign out and sign back in" copy removed from page.tsx | Done (`grep` returns no match) |
| Disconnected branch shows "Connect Google Workspace" button | Done (line 3841) |
| Connect button drives `handleConnectIntegration('google_workspace')` | Done |
| Connected branch shows Disconnect button | Done |
| Disconnect button drives `disconnectGoogleWorkspace` (NOT generic helper) | Done |
| `handleOAuthMessage` re-fetches `/api/configuration/google-workspace-status` for `provider==='google_workspace'` | Done |
| `disconnectGoogleWorkspace` exported from `services/integrations.ts` and hits `DELETE /api/configuration/google-workspace` | Done |
| 5 new vitest tests GREEN | Done |
| `tsc --noEmit` and lint clean (for files touched) | Done |

## Manual smoke test (deferred to UAT)

Per the plan's `<verification>` section, the load-bearing manual test for Phase 102 is to run the local backend + frontend, log in as a fresh user, click the new Connect button, complete the Google consent flow, verify the popup `postMessage` flips the UI to connected, send a chat to create a Google Doc, then click Disconnect and verify the row is gone from `integration_credentials` and the `oauth2.googleapis.com/revoke` POST shows in server logs. **This was not run during plan execution** because no `GOOGLE_WORKSPACE_CLIENT_ID/SECRET/REDIRECT_URI` are configured in the local `.env` and provisioning a Google OAuth client is a tenant-admin step. The vitest suite pins all 5 observable truths from the plan's `must_haves.truths` list, so the manual smoke is now a confirmation step rather than a discovery step.

## Deviations from Plan

1. **[Rule 3 — Blocking issue] Test framework mock-reset trap.** The plan's stub test scaffold used `vi.resetAllMocks()` in `beforeEach`. That call resets the resolved-value implementations of the `vi.mock('@/services/integrations', ...)` factory mocks — when the page then calls `fetchProviders()`, it gets `undefined`, and the JSX render crashes at `integrationProviders.length` because `setIntegrationProviders(undefined)` ran. Fixed by switching to `vi.clearAllMocks()` (clears call history but preserves implementations from the factory). Documented in the test file's `beforeEach` comment.

2. **[Rule 1 — Bug] Pre-existing `useState<IntegrationProvider[]>([])` was crashing on the test render.** Same root cause as #1 — once mocks were stable the issue went away. No production-code fix required.

3. **[External — race with parallel executor] Task 3 commit hash hijacked by a parallel agent.** While I was running `git add` + `git commit` for Task 3 (`feat(102-03): in-app Google Workspace connect/disconnect card with revoke (WORKSPACE-01)`), a parallel agent (Plan 107-02) ran a `git add` over the same staging area and committed everything together as `071d2f6d docs(107-02): complete Facebook Page token capture plan summary`. My Task 3 file changes are present in commit `071d2f6d`'s tree (verified via `git show --stat 071d2f6d` — page.tsx +117 lines, ConfigurationPage.test.tsx +/-41 lines), but the commit message is misleading. The phase-fence stayed honored (no backend Python touched on my side); this is purely a commit-hash bookkeeping artifact. Tasks 1 and 2 commits (`e647a910`, `0a18280d`) are correctly attributed.

4. **[Plan-vs-actual] `GoogleWorkspaceStatus` interface fields differ from RESEARCH.** The plan's `<interfaces>` block listed `accountName`, `scopes[]`, `expiresAt`, `lastSync`. The actual interface at `page.tsx:102` has `email`, `provider`, `features[]`, `message`. The vitest tests assert against the real interface (e.g. `email: 'user@example.com'`, `features: ['Docs']`) so this discrepancy did not change behavior; it just means the plan's RESEARCH was slightly stale. No backend change required — the existing `/api/configuration/google-workspace-status` endpoint already returns the actual shape.

5. **[Co-tenancy fence] No backend touches.** Per the orchestrator's instructions, this plan stayed entirely in `frontend/src/`. Plans 104-02 and 107-02 (running in parallel) own `app/social/publisher.py` and `app/social/connector.py`. No files outside `frontend/src/` were modified by this plan.

## Self-Check: PASSED

- File `frontend/src/app/dashboard/configuration/page.tsx`: FOUND
- File `frontend/src/services/integrations.ts`: FOUND
- File `frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx`: FOUND
- Commit `e647a910` (test): FOUND
- Commit `0a18280d` (helper): FOUND
- Commit `071d2f6d` (page UI; merged with parallel agent — see Deviations §3): FOUND in tree
- 5/5 vitest tests GREEN
- `grep "sign out and sign back in" frontend/src/app/dashboard/configuration/page.tsx` returns nothing
