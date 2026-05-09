---
phase: 102-google-workspace-credential-bridge
plan: 03
type: execute
wave: 3
depends_on: [102-01, 102-02]
files_modified:
  - frontend/src/app/dashboard/configuration/page.tsx
  - frontend/src/services/integrations.ts
  - frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx
autonomous: true
requirements: [WORKSPACE-01]

must_haves:
  truths:
    - "When the user is NOT connected to Google Workspace, the configuration page shows a 'Connect Google Workspace' button (not the legacy 'sign out and sign back in' instructions)"
    - "Clicking 'Connect Google Workspace' opens a popup window at /api/integrations/google_workspace/authorize with width=600, height=700"
    - "When the popup posts {type: 'oauth-callback', provider: 'google_workspace', success: true}, the parent re-fetches /api/configuration/google-workspace-status within 2s and the UI flips to the connected branch"
    - "When the user IS connected, a 'Disconnect' button is visible; clicking it routes to DELETE /api/configuration/google-workspace (the GoogleWorkspaceAuthService path) so the backend revoke runs"
    - "After successful disconnect, the UI flips back to the disconnected branch within 2s"
  artifacts:
    - path: "frontend/src/app/dashboard/configuration/page.tsx"
      provides: "Replaced Google Workspace section (lines 3690-3748): connect button drives handleConnectIntegration('google_workspace'); disconnect button calls disconnectGoogleWorkspace; postMessage listener re-fetches workspace status when provider==='google_workspace'"
      contains: "google_workspace"
    - path: "frontend/src/services/integrations.ts"
      provides: "disconnectGoogleWorkspace() helper that hits DELETE /api/configuration/google-workspace (NOT the generic /integrations/{provider} path)"
      contains: "disconnectGoogleWorkspace"
    - path: "frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx"
      provides: "Vitest module covering: button renders when disconnected, click opens correct popup URL, postMessage triggers status refresh, disconnect calls correct endpoint"
      contains: "google_workspace"
  key_links:
    - from: "frontend/src/app/dashboard/configuration/page.tsx (Connect button)"
      to: "/api/integrations/google_workspace/authorize"
      via: "handleConnectIntegration('google_workspace') -> window.open popup"
      pattern: "handleConnectIntegration\\(.google_workspace.\\)"
    - from: "frontend/src/app/dashboard/configuration/page.tsx (postMessage listener at lines 3008-3034)"
      to: "/api/configuration/google-workspace-status (re-fetch on success)"
      via: "extended handleOAuthMessage branch when provider === 'google_workspace'"
      pattern: "google_workspace.*google-workspace-status"
    - from: "frontend/src/app/dashboard/configuration/page.tsx (Disconnect button)"
      to: "DELETE /api/configuration/google-workspace"
      via: "disconnectGoogleWorkspace from services/integrations.ts"
      pattern: "disconnectGoogleWorkspace"
---

<objective>
Replace the legacy "sign out and sign back in" Google Workspace section in the configuration page with a real OAuth connect button and a working disconnect button. After this plan, end-users can connect their Google Workspace account from inside the app (popup OAuth -> postMessage -> status refresh) and disconnect with a confirmed revoke at Google.

This plan depends on Plan 102-01 (the `google_workspace` entry in `PROVIDER_REGISTRY` makes `/api/integrations/google_workspace/authorize` route correctly) and Plan 102-02 (the disconnect endpoint at `/api/configuration/google-workspace` revokes via the modified `GoogleWorkspaceAuthService.disconnect`).

Purpose: Satisfies WORKSPACE-01 (in-app Connect Google Workspace card with popup OAuth + postMessage). Closes the user-facing gap where today the only "fix" for a missing token was to sign out of Pikar AI and re-authenticate via Supabase Auth's Google identity — opaque, frustrating, and doesn't grant the per-tool scopes Phase 102 needs.

Output: Modified `frontend/src/app/dashboard/configuration/page.tsx` Google Workspace section with conditional connect/disconnect UI; new `disconnectGoogleWorkspace` helper in `services/integrations.ts` pointing at `/api/configuration/google-workspace`; vitest unit test pinning the four observable truths.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/102-google-workspace-credential-bridge/102-CONTEXT.md
@.planning/phases/102-google-workspace-credential-bridge/102-RESEARCH.md
@.planning/phases/102-google-workspace-credential-bridge/102-01-provider-registry-and-bridge-PLAN.md
@.planning/phases/102-google-workspace-credential-bridge/102-02-token-refresh-and-disconnect-revoke-PLAN.md
@frontend/src/app/dashboard/configuration/page.tsx
@frontend/src/services/integrations.ts

<interfaces>
<!-- Key contracts the executor needs. Extracted from the codebase. -->

From frontend/src/app/dashboard/configuration/page.tsx:

```typescript
// Lines 102-108 — existing GoogleWorkspaceStatus interface (DO NOT change)
interface GoogleWorkspaceStatus {
    connected: boolean;
    accountName?: string;
    scopes?: string[];
    expiresAt?: string | null;
    lastSync?: string | null;
}

// Lines 3008-3034 — existing handleOAuthMessage listener
// Already calls refreshIntegrationStatus() when an oauth-callback message arrives.
// EXTEND IT: when event.data.provider === 'google_workspace', also re-fetch
// /api/configuration/google-workspace-status and call setGoogleWorkspace(...).

// Lines 3211-3226 — existing handleConnectIntegration
const handleConnectIntegration = (providerKey: string) => {
    const popup = window.open(
        `/api/integrations/${providerKey}/authorize`,
        'oauth-popup',
        'width=600,height=700,scrollbars=yes',
    );
    // ... existing focus/error handling ...
};

// Lines 3690-3748 — CURRENT Google Workspace section (REPLACE)
// Connected branch (3699-3733): shows account name, scopes, last sync, etc.
// Disconnected branch (3734-3747): says "sign out and sign back in" — REPLACE
// with a proper Connect button.
```

From frontend/src/services/integrations.ts (existing):

```typescript
// Generic helper, currently used for all integrations:
export async function disconnectIntegration(provider: string): Promise<void> {
    const r = await fetch(`/api/integrations/${provider}`, { method: 'DELETE' });
    if (!r.ok) throw new Error(`Failed to disconnect ${provider}`);
}

// NEW helper to add (Google Workspace needs the dedicated endpoint that
// runs revoke before delete):
export async function disconnectGoogleWorkspace(): Promise<void> {
    const r = await fetch('/api/configuration/google-workspace', { method: 'DELETE' });
    if (!r.ok) throw new Error('Failed to disconnect Google Workspace');
}
```

Backend endpoint shapes (from RESEARCH section §WORKSPACE-05):
- `GET /api/configuration/google-workspace-status` -> returns GoogleWorkspaceStatus
- `DELETE /api/configuration/google-workspace` -> calls GoogleWorkspaceAuthService.disconnect (which 102-02 modifies to revoke)
- `GET /api/integrations/google_workspace/authorize` -> generic OAuth router; redirects to Google consent. Already routed by 102-01 once `google_workspace` is in PROVIDER_REGISTRY.

Test framework (existing or to be set up):
- Vitest is preferred per Next.js 16 / React 19 stack. Verify `frontend/vitest.config.ts` exists; if not, may need to create it. Check `frontend/package.json` `test` script.
- Existing vitest test file pattern: search for `__tests__` directories in frontend/src.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add failing vitest test for Connect/Disconnect card</name>
  <files>frontend/src/app/dashboard/configuration/__tests__/ConfigurationPage.test.tsx</files>
  <behavior>
    Create a new vitest test file (or extend an existing one in the configuration directory). ALL tests must FAIL initially.

    Add a test class / describe block `describe('Google Workspace integration card', ...)` with 5 tests:

    - **shows Connect button when disconnected**: render `<ConfigurationPage />` with mocked initial status `{ googleWorkspace: { connected: false } }`. Assert a button with text matching `/connect google workspace/i` is in the document. Assert NO text matching `/sign out and sign back in/i` (legacy copy must be gone).

    - **clicking Connect opens popup at correct URL**: same setup. Mock `window.open` with `vi.spyOn(window, 'open').mockReturnValue(...)`. Click the button. Assert `window.open` was called once with first arg matching `/\/api\/integrations\/google_workspace\/authorize/`, second arg `'oauth-popup'`, third arg containing `'width=600'` and `'height=700'`.

    - **postMessage triggers re-fetch of workspace status**: same setup, mock `fetch` so `/api/configuration/google-workspace-status` returns `{ connected: true, accountName: "user@example.com" }`. Dispatch `window.postMessage({type: 'oauth-callback', provider: 'google_workspace', success: true}, '*')`. `await waitFor(() => expect(screen.getByText(/user@example.com/i)).toBeInTheDocument(), { timeout: 2500 })`. The UI must flip to the connected branch.

    - **shows Disconnect button when connected**: render with `{ googleWorkspace: { connected: true, accountName: 'user@example.com' } }`. Assert a Disconnect button is present. Assert no Connect button.

    - **clicking Disconnect calls correct endpoint**: same setup. Mock `fetch` and assert that clicking Disconnect triggers `fetch('/api/configuration/google-workspace', { method: 'DELETE' })` (the dedicated path, NOT `/api/integrations/google_workspace`). After the response resolves, the UI flips to the disconnected branch.

    Total: 5 tests.

    Run `cd frontend && npm test -- ConfigurationPage` — ALL must FAIL with assertion errors (or test-runner-not-set-up errors that the executor must resolve as part of Task 1).

    Commit message: `test(102-03): add failing vitest tests for Google Workspace connect/disconnect card (WORKSPACE-01)`.
  </behavior>
  <action>
    First check if vitest is already set up:
    ```bash
    cd frontend && cat package.json | grep -E "test|vitest" && ls vitest.config.* 2>/dev/null
    ```

    If vitest is NOT set up, the executor MUST set it up minimally:
    - Add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` to devDependencies (`npm i -D`).
    - Create `frontend/vitest.config.ts` with `environment: 'jsdom'`, `setupFiles: ['./vitest.setup.ts']`.
    - Create `frontend/vitest.setup.ts` importing `@testing-library/jest-dom`.
    - Add `"test": "vitest run"` to `package.json` `scripts`.
    - Document the setup in the SUMMARY.

    If vitest IS set up, just create the test file in the existing pattern.

    Test file shape:
    ```typescript
    import { describe, it, expect, vi, beforeEach } from 'vitest';
    import { render, screen, waitFor, fireEvent } from '@testing-library/react';
    import ConfigurationPage from '../page';

    // Mock the data-fetching hook(s) that ConfigurationPage uses on mount so
    // the test controls initial googleWorkspace state. Verify the hook name
    // by reading page.tsx — likely `useEffect` with a fetch call to
    // /api/configuration/google-workspace-status. Mock global.fetch.

    describe('Google Workspace integration card', () => {
        beforeEach(() => {
            vi.resetAllMocks();
        });
        // ... 5 tests as specified ...
    });
    ```

    Verify all tests FAIL because the page.tsx still has the legacy "sign out and sign back in" copy and no `disconnectGoogleWorkspace` helper exists.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm test -- ConfigurationPage 2>&amp;1 | tail -30</automated>
  </verify>
  <done>
    5 new vitest tests exist; all FAIL with assertion errors. Vitest is configured (either pre-existing or newly added with config files committed). Commit `test(102-03): add failing vitest tests for Google Workspace connect/disconnect card (WORKSPACE-01)` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add disconnectGoogleWorkspace helper to services/integrations.ts</name>
  <files>frontend/src/services/integrations.ts</files>
  <behavior>
    Add a new exported async function `disconnectGoogleWorkspace` that hits the dedicated `/api/configuration/google-workspace` endpoint (NOT the generic `/api/integrations/{provider}` path).

    ```typescript
    /**
     * Disconnect Google Workspace via the dedicated configuration endpoint so
     * the backend revoke (Phase 102, WORKSPACE-05) runs before deleting the row.
     * Calling the generic `/api/integrations/{provider}` DELETE path would skip
     * the revoke step.
     */
    export async function disconnectGoogleWorkspace(): Promise<void> {
        const r = await fetch('/api/configuration/google-workspace', { method: 'DELETE' });
        if (!r.ok) {
            throw new Error(`Failed to disconnect Google Workspace (status ${r.status})`);
        }
    }
    ```

    Place after the existing `disconnectIntegration` function (or wherever the existing disconnect helpers live — read the file first to confirm location and TypeScript style).

    The generic `disconnectIntegration` function is NOT removed — other providers continue to use it. Only the Google Workspace path is special-cased.

    Run `cd frontend && npm test -- ConfigurationPage` — the **clicking Disconnect calls correct endpoint** test should now pass once Task 3 wires the button to this function.

    Commit message: `feat(102-03): add disconnectGoogleWorkspace helper for revoke-then-delete path`.
  </behavior>
  <action>
    Read `frontend/src/services/integrations.ts` first to confirm the existing pattern (export style, error handling, TypeScript settings). Match the existing style.

    Add the new function. Do NOT modify `disconnectIntegration` (other providers still use it).

    Run `cd frontend && npm run lint` (or whatever the project's frontend lint command is — check `package.json` scripts) to ensure no TypeScript / ESLint errors.

    Commit. The test for this specific helper (`clicking Disconnect calls correct endpoint`) will not GREEN until Task 3 wires the page to the helper, but the file change is committed independently for traceability.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm run lint -- --max-warnings 0 src/services/integrations.ts 2>&amp;1 | tail -10 || cd frontend &amp;&amp; npx tsc --noEmit 2>&amp;1 | tail -10</automated>
  </verify>
  <done>
    `disconnectGoogleWorkspace` is exported from `frontend/src/services/integrations.ts`. TypeScript compilation clean. ESLint (or the project's lint runner) clean. Commit `feat(102-03): add disconnectGoogleWorkspace helper for revoke-then-delete path` lands.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Replace legacy Google Workspace section with Connect/Disconnect UI</name>
  <files>frontend/src/app/dashboard/configuration/page.tsx</files>
  <behavior>
    After this task, all 5 vitest tests from Task 1 are GREEN.

    Three changes inside `frontend/src/app/dashboard/configuration/page.tsx`:

    **Change A: Add the import** (top of file, with other service imports):

    ```typescript
    import { disconnectGoogleWorkspace } from '@/services/integrations';
    ```

    **Change B: Extend the `handleOAuthMessage` listener** (currently lines 3008-3034). After the existing `refreshIntegrationStatus()` call, add:

    ```typescript
    if (event.data?.provider === 'google_workspace' && event.data?.success) {
        // Re-fetch the dedicated google-workspace-status endpoint so the
        // GoogleWorkspaceStatus state updates within 2s of OAuth completion.
        try {
            const r = await fetch('/api/configuration/google-workspace-status');
            if (r.ok) {
                const status = await r.json();
                setGoogleWorkspace(status);
            }
        } catch (err) {
            console.warn('Failed to refresh Google Workspace status', err);
        }
    }
    ```

    Read the existing listener to determine whether it's already async; if not, mark it async (only this one method) so the `await` is valid.

    **Change C: Replace the Google Workspace section at lines 3690-3748.** The connected branch (lines 3699-3733) is **mostly preserved** — only add a Disconnect button at the bottom. The disconnected branch (lines 3734-3747) is **completely replaced** with a Connect button.

    ```tsx
    {googleWorkspace?.connected ? (
        <div className="space-y-4">
            {/* PRESERVE the existing connected branch UI here:
                accountName, scopes list, lastSync timestamp, etc. */}
            {/* ... existing connected UI ... */}
            <button
                onClick={async () => {
                    if (!confirm('Disconnect Google Workspace? This will revoke access at Google.')) return;
                    setDisconnectingProvider('google_workspace');
                    try {
                        await disconnectGoogleWorkspace();
                        // Re-fetch status to flip UI back to disconnected branch
                        const r = await fetch('/api/configuration/google-workspace-status');
                        if (r.ok) {
                            setGoogleWorkspace(await r.json());
                        }
                    } catch (err) {
                        alert(`Failed to disconnect: ${err instanceof Error ? err.message : err}`);
                    } finally {
                        setDisconnectingProvider(null);
                    }
                }}
                disabled={disconnectingProvider === 'google_workspace'}
                className="text-sm text-red-600 hover:text-red-700"
            >
                {disconnectingProvider === 'google_workspace' ? 'Disconnecting...' : 'Disconnect'}
            </button>
        </div>
    ) : (
        <div className="text-center py-8">
            {/* ... icon + heading ... */}
            <h3 className="text-lg font-semibold mb-2">Connect Google Workspace</h3>
            <p className="text-sm text-gray-600 mb-4">
                Authorize Pikar AI to create Docs, Sheets, Calendar events,
                Forms, and send Gmail on your behalf.
            </p>
            <button
                onClick={() => handleConnectIntegration('google_workspace')}
                className="mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
                <Plug className="inline w-4 h-4 mr-2" />
                Connect Google Workspace
            </button>
        </div>
    )}
    ```

    The legacy "sign out and sign back in" copy MUST be removed.

    Verify state setter `setDisconnectingProvider` and `setGoogleWorkspace` already exist in the component (per RESEARCH §WORKSPACE-01 the state already exists). If not, add the missing `useState` hook for `disconnectingProvider`. The `Plug` icon comes from lucide-react and is likely already imported elsewhere in this file — verify the import.

    Run `cd frontend && npm test -- ConfigurationPage` — all 5 tests GREEN.

    Run `cd frontend && npm run lint` and `cd frontend && npx tsc --noEmit` — clean.

    Commit message: `feat(102-03): in-app Google Workspace connect/disconnect card with revoke (WORKSPACE-01)`.
  </behavior>
  <action>
    Read the relevant sections of page.tsx FIRST to confirm:
    1. Line numbers for the Google Workspace section (RESEARCH says 3690-3748 — verify)
    2. Whether `handleOAuthMessage` is already async
    3. Whether `setDisconnectingProvider` state and setter exist
    4. Whether `setGoogleWorkspace` setter exists
    5. Whether `Plug` icon is already imported from `lucide-react`
    6. Whether `googleWorkspace` state shape matches `GoogleWorkspaceStatus` interface

    Adjust the implementation as needed to match the actual component structure. The `space-y-4`, `text-red-600`, etc. classes are placeholders — match the existing Tailwind class style used elsewhere in the file.

    Make the three changes (import, listener extension, section replacement). Preserve the existing connected-branch UI (account name, scopes list, last sync) — only add the Disconnect button at the end of that branch.

    Verify all 5 vitest tests GREEN. Verify lint + tsc clean.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npm test -- ConfigurationPage 2>&amp;1 | tail -20 &amp;&amp; cd frontend &amp;&amp; npx tsc --noEmit 2>&amp;1 | tail -10</automated>
  </verify>
  <done>
    5/5 vitest tests in ConfigurationPage.test.tsx GREEN. The legacy "sign out and sign back in" copy is gone from page.tsx. Connect button drives `handleConnectIntegration('google_workspace')`. Disconnect button calls `disconnectGoogleWorkspace`. postMessage listener re-fetches the dedicated workspace-status endpoint. TypeScript compilation and lint clean. Commit `feat(102-03): in-app Google Workspace connect/disconnect card with revoke (WORKSPACE-01)` lands.
  </done>
</task>

</tasks>

<verification>
End-to-end (per-task): see each `<verify>` block.

Plan-level: `cd frontend && npm test -- ConfigurationPage` -> all 5 vitest tests GREEN. `cd frontend && npm run lint && npx tsc --noEmit` -> clean.

**Phase-gate manual smoke (this is the load-bearing manual test for Phase 102):**

1. Set `GOOGLE_WORKSPACE_CLIENT_ID`, `GOOGLE_WORKSPACE_CLIENT_SECRET`, `GOOGLE_WORKSPACE_REDIRECT_URI` in `.env`. Run `make local-backend` and `cd frontend && npm run dev`.
2. Log in as a fresh test user (no existing Google identity in Supabase Auth).
3. Visit `/dashboard/configuration`. Confirm "Connect Google Workspace" button (NOT "sign out and sign back in").
4. Click button. Verify popup opens at `/api/integrations/google_workspace/authorize` and Google consent screen shows the 8 scopes.
5. Approve. Popup closes. Within 2s the UI flips to connected with the user's email shown.
6. Inspect `integration_credentials` table: row exists for the test user with `provider='google_workspace'`, encrypted `access_token` and `refresh_token`.
7. Send a chat message: "Create a Google Doc titled 'Phase 102 smoke test' with body 'Hello world'". Confirm doc URL appears in chat. Open the URL — doc exists in the test user's Drive.
8. Click Disconnect. Confirm dialog. UI flips back to "Connect Google Workspace" within 2s. Inspect `integration_credentials` — row gone. Inspect server logs — see the `oauth2.googleapis.com/revoke` POST.
9. Send the same chat message again. Expect "Google authentication required for document features" error (not stale 401).
</verification>

<success_criteria>
- `frontend/src/app/dashboard/configuration/page.tsx` no longer contains the legacy "sign out and sign back in" copy.
- The disconnected branch shows a "Connect Google Workspace" button driving `handleConnectIntegration('google_workspace')`.
- The connected branch shows a "Disconnect" button driving `disconnectGoogleWorkspace`.
- The `handleOAuthMessage` listener re-fetches `/api/configuration/google-workspace-status` when `event.data.provider === 'google_workspace'`.
- `frontend/src/services/integrations.ts` exports `disconnectGoogleWorkspace` that hits `DELETE /api/configuration/google-workspace`.
- All 5 vitest tests GREEN.
- `npx tsc --noEmit` and lint clean.
- Phase-gate manual smoke passes (deferred to UAT).
</success_criteria>

<output>
After completion, create `.planning/phases/102-google-workspace-credential-bridge/102-03-frontend-connect-disconnect-card-SUMMARY.md` documenting:
- Exact line numbers of the replaced section in page.tsx (RESEARCH said 3690-3748 — confirm or correct)
- Whether vitest was pre-configured or had to be set up (and what config files were added)
- Whether `Plug` icon, `setDisconnectingProvider`, `setGoogleWorkspace`, and `googleWorkspace` state were pre-existing or had to be added
- Test count delta (existing N -> existing N + 5 GREEN)
- Manual smoke test checklist with actual results from at least one connect/disconnect cycle
- Any deviations from this plan (e.g. component structure differs from RESEARCH expectations)
</output>
