---
phase: 88-chat-and-workspace-persistence
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/contexts/SessionControlContext.tsx
  - frontend/src/contexts/__tests__/SessionControlContext.test.tsx
  - frontend/src/components/chat/__test-utils__/chatHarness.ts
  - frontend/src/components/chat/ChatInterface.test.tsx
autonomous: true
requirements:
  - HOTFIX-06
must_haves:
  truths:
    - "After sending a message and reloading, the same session_id is restored from localStorage `pikar_current_session_id` and the chat history is visible in the panel"
    - "Workspace artifacts re-query Supabase `workspace_items` keyed on the restored session_id and re-render the same items that were present before reload"
    - "Calling `createNewChat()` clears `pikar_current_session_id` from localStorage (or replaces it with the new id) and the workspace clears its rendered items"
    - "Chat history list (`/dashboard/history` and the in-panel dropdown) shows all sessions returned by `GET /sessions` with title + preview + updatedAt"
    - "Opening the same session in a second browser tab does not corrupt either tab — the second tab's localStorage write fires a `storage` event, the first tab observes it and updates `visibleSessionIdRaw` to match (last-write-wins) without throwing or stranding workspace items keyed on the old id"
  artifacts:
    - path: "frontend/src/contexts/SessionControlContext.tsx"
      provides: "`storage` event listener on window that calls setVisibleSessionIdRaw when another browser tab updates `pikar_current_session_id` for the same origin"
      contains: "addEventListener('storage'"
    - path: "frontend/src/contexts/__tests__/SessionControlContext.test.tsx"
      provides: "Vitest behavior tests for the cross-tab `storage` listener — fires a synthetic StorageEvent and asserts visibleSessionId updates"
      contains: "storage event"
    - path: "frontend/src/components/chat/__test-utils__/chatHarness.ts"
      provides: "Extended `useSessionControl` mock that exposes `visibleSessionId`, `setVisibleSessionId`, `sessionRestored` so persistence-related tests can drive the harness"
      contains: "visibleSessionId"
    - path: "frontend/src/components/chat/ChatInterface.test.tsx"
      provides: "Reload-restore behavior test — renders with `initialSessionId` from a seeded localStorage value, asserts useAgentChat receives that id"
      contains: "restores session from localStorage"
  key_links:
    - from: "SessionControlContext.tsx visibleSessionId state"
      to: "localStorage `pikar_current_session_id`"
      via: "useLayoutEffect read on mount + setVisibleSessionId write on every change (already shipped) + new `storage` event listener for cross-tab sync"
      pattern: "addEventListener\\(.storage."
    - from: "PersonaDashboardLayout.tsx sessionRestored gate"
      to: "ChatInterface initialSessionId prop"
      via: "useChatSession().currentSessionId aliased from useSessionControl().visibleSessionId — already shipped, verify only"
      pattern: "initialSessionId=\\{effectiveSessionId\\}"
    - from: "ActiveWorkspace.tsx loadWorkspaceState"
      to: "supabase workspace_items keyed on session_id"
      via: "currentSessionId useEffect dependency triggers re-query — already shipped, verify only"
      pattern: "\\.eq\\('session_id', currentSessionId\\)"
---

<objective>
Reconcile the chat-history-on-reload persistence work that shipped in commit `c8da1d99` (2026-04-27) without a corresponding GSD plan. Adds the missing piece: cross-browser-tab safety via a `storage` event listener (success criterion 4 of the ROADMAP). Adds vitest behavior coverage for the four already-shipped truths so the persistence guarantee is regression-proof.

Purpose: HOTFIX-06 production hotfix bug 6/7. The persistence work is live in production and demonstrably correct via manual testing, but it has zero automated test coverage and one open gap (cross-tab sync). This plan closes both — the gap with one new `useEffect` block of ~12 lines, and the coverage with 5 focused behavior tests using the existing chatHarness pattern from Phase 83.

Output: ~12 production lines added in `SessionControlContext.tsx` (new `useEffect` for `storage` event listener); ~80 lines of new tests across two test files; harness extension for `useSessionControl` mock; one retroactive SUMMARY.md documenting the four shipped truths with line-number anchors so future readers understand what `c8da1d99` accomplished.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

# Source under modification
@frontend/src/contexts/SessionControlContext.tsx
@frontend/src/components/chat/__test-utils__/chatHarness.ts
@frontend/src/components/chat/ChatInterface.test.tsx

# Reference (DO NOT modify in this plan)
@frontend/src/contexts/SessionMapContext.tsx
@frontend/src/contexts/ChatSessionContext.tsx
@frontend/src/components/dashboard/PersonaDashboardLayout.tsx
@frontend/src/components/dashboard/ActiveWorkspace.tsx
@frontend/src/hooks/useAgentChat.ts

<interfaces>
<!-- Already-shipped persistence (commit c8da1d99). Executor should NOT re-implement these. -->

From `frontend/src/contexts/SessionControlContext.tsx` (current HEAD):
```typescript
// Line 26 — module-scope constant
const STORAGE_KEY = 'pikar_current_session_id'

// Lines 129-139 — restore on mount (synchronous, before paint)
useLayoutEffect(() => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      setVisibleSessionIdRaw(stored)
    }
  } catch {
    // localStorage may be unavailable (SSR, privacy mode, etc.)
  }
  setSessionRestored(true)
}, [])

// Lines 144-155 — persist on every change
const setVisibleSessionId = useCallback((id: string | null) => {
  setVisibleSessionIdRaw(id)
  try {
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, id)
    }
  } catch {
    // localStorage may be unavailable
  }
}, [])
```

From `frontend/src/components/dashboard/PersonaDashboardLayout.tsx:224` — gate logic:
```tsx
{sessionRestored ? (
  <ChatInterface
    initialSessionId={effectiveSessionId}
    // ...
  />
) : (
  <div>Loading chat…</div>
)}
```

From `frontend/src/components/dashboard/ActiveWorkspace.tsx:317-355` — workspace queries on `currentSessionId`:
```typescript
const { data: rows, error } = await supabase
  .from('workspace_items')
  .select('*')
  .eq('user_id', authUser.id)
  .eq('session_id', currentSessionId)  // <-- restored value flows here
  .order('created_at', { ascending: true });
```

<!-- Existing chatHarness mock shape (frontend/src/components/chat/__test-utils__/chatHarness.ts:70-72). -->
<!-- Currently: `useSessionControl: vi.fn()` — returns undefined by default; consumers MUST provide a mockReturnValue per render. -->
<!-- Plan 88-01 extends the harness so persistence tests can seed `visibleSessionId` declaratively. -->

```typescript
vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: vi.fn(),
}))
```

<!-- The `storage` event API (MDN reference, no code change required to use): -->
<!-- StorageEvent fires on `window` ONLY in OTHER tabs/windows of the same origin when localStorage is mutated. -->
<!-- It does NOT fire in the tab that performed the write — that tab is responsible for its own state. -->
<!-- Properties: event.key (string|null), event.newValue (string|null), event.oldValue (string|null), event.storageArea. -->
```typescript
window.addEventListener('storage', (e: StorageEvent) => {
  if (e.key !== STORAGE_KEY) return  // ignore unrelated keys
  if (e.storageArea !== window.localStorage) return  // ignore sessionStorage events
  // e.newValue is the new value (null if cleared)
  // Update local React state (do NOT write back to localStorage — would loop forever)
})
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend chatHarness mock + RED behavior tests for shipped persistence truths</name>
  <files>frontend/src/components/chat/__test-utils__/chatHarness.ts, frontend/src/components/chat/ChatInterface.test.tsx, frontend/src/contexts/__tests__/SessionControlContext.test.tsx</files>
  <behavior>
    Five behavior tests covering ROADMAP success criteria 1, 2, 3, 5, and the new criterion 4 (cross-tab safety). Tests 1-3 should GREEN immediately (the production code already shipped). Test 4 (cross-tab) should RED — the listener does not exist yet. Test 5 (history list) should GREEN.

    - **Test 1 — "restores session_id from localStorage on mount"** (file: SessionControlContext.test.tsx). Render the SessionControlProvider after seeding `localStorage.setItem('pikar_current_session_id', 'session-test-restore-123')`. Use a child consumer that calls `useSessionControl()` and renders `visibleSessionId` into the DOM. Assert the rendered text is `session-test-restore-123` after `await waitFor(...)`. Maps to HOTFIX-06.1.

    - **Test 2 — "persists session_id to localStorage on change"** (file: SessionControlContext.test.tsx). Render provider with empty localStorage. Use a child consumer that calls `setVisibleSessionId('session-new-456')` from a button click. Assert `localStorage.getItem('pikar_current_session_id') === 'session-new-456'` after the click. Maps to HOTFIX-06.1 + .3 (the persist mechanism).

    - **Test 3 — "createNewChat replaces stored session_id"** (file: SessionControlContext.test.tsx). Render provider after seeding `pikar_current_session_id='session-old-789'`. Click a button that calls `createNewChat()`. Assert `localStorage.getItem('pikar_current_session_id')` is now a fresh `session-<timestamp>-<rand>` (does NOT match `session-old-789`, DOES match `/^session-\d+-[a-z0-9]+$/`). Maps to HOTFIX-06.3.

    - **Test 4 — "cross-tab storage event updates visibleSessionId"** (file: SessionControlContext.test.tsx). Render provider after seeding `pikar_current_session_id='session-tab-A'`. Use a child consumer that renders `visibleSessionId` into the DOM. Fire a synthetic `StorageEvent` (jsdom does not fire it from `localStorage.setItem` in the same window — it MUST be dispatched manually):
      ```typescript
      const event = new StorageEvent('storage', {
        key: 'pikar_current_session_id',
        newValue: 'session-tab-B',
        oldValue: 'session-tab-A',
        storageArea: window.localStorage,
      });
      window.dispatchEvent(event);
      ```
      Assert the rendered text becomes `session-tab-B` after `await waitFor(...)`. **THIS TEST WILL RED in Task 1** — the listener does not exist yet. It turns GREEN after Task 2.

    - **Test 5 — "reload-restore: ChatInterface receives restored sessionId via initialSessionId"** (file: ChatInterface.test.tsx, in a new describe block "ChatInterface — persistence (HOTFIX-06)"). Use the chatHarness with the new `useSessionControl` mock returning `{ visibleSessionId: 'session-restore-555', setVisibleSessionId: vi.fn(), sessionRestored: true, config: DEFAULT_SESSION_CONFIG, createNewChat: vi.fn(), selectChat: vi.fn(), deleteChat: vi.fn().mockResolvedValue(undefined), clearAllChats: vi.fn().mockResolvedValue(undefined), refreshSessions: vi.fn().mockResolvedValue(undefined), updateSessionTitle: vi.fn().mockResolvedValue(undefined), updateSessionPreview: vi.fn().mockResolvedValue(undefined), addSessionOptimistic: vi.fn() }`. Pass `initialSessionId="session-restore-555"` to `<ChatInterface />`. Assert that the `useAgentChat` mock was called with first argument equal to `'session-restore-555'`. Maps to HOTFIX-06.1 (component-level wiring).
  </behavior>
  <action>
    1. **Read** `frontend/src/components/chat/__test-utils__/chatHarness.ts` in full (it's ~250 lines from Phase 83). Locate the existing `vi.mock('@/contexts/SessionControlContext', ...)` block at lines 70-72 and the harness factory `renderChatInterface(opts)` near the end of the file.

    2. **Extend the harness mock** for `useSessionControl`. Add a `sessionControl` field to `RenderChatOptions` (the existing options interface) and a default object inside `renderChatInterface`:
       ```typescript
       // Top of file, after imports
       import type { SessionConfig } from '@/types/session'
       import { DEFAULT_SESSION_CONFIG } from '@/types/session'

       // Add to RenderChatOptions interface:
       sessionControl?: Partial<{
         visibleSessionId: string | null
         setVisibleSessionId: (id: string | null) => void
         sessionRestored: boolean
         config: SessionConfig
         createNewChat: () => string
         selectChat: (id: string) => void
         deleteChat: (id: string) => Promise<void>
         clearAllChats: () => Promise<void>
         refreshSessions: () => Promise<void>
         updateSessionTitle: (id: string, t: string) => Promise<void>
         updateSessionPreview: (id: string, p: string) => Promise<void>
         addSessionOptimistic: (s: unknown) => void
       }>
       ```

       Inside `renderChatInterface`, before the existing `(useSessionControl as ReturnType<typeof vi.fn>).mockReturnValue(...)` (or add it if not present), build the default:
       ```typescript
       const defaultSessionControl = {
         visibleSessionId: null,
         setVisibleSessionId: vi.fn(),
         sessionRestored: true,
         config: DEFAULT_SESSION_CONFIG,
         createNewChat: vi.fn(() => 'session-mock-new'),
         selectChat: vi.fn(),
         deleteChat: vi.fn().mockResolvedValue(undefined),
         clearAllChats: vi.fn().mockResolvedValue(undefined),
         refreshSessions: vi.fn().mockResolvedValue(undefined),
         updateSessionTitle: vi.fn().mockResolvedValue(undefined),
         updateSessionPreview: vi.fn().mockResolvedValue(undefined),
         addSessionOptimistic: vi.fn(),
       }
       ;(useSessionControl as ReturnType<typeof vi.fn>).mockReturnValue({
         ...defaultSessionControl,
         ...opts.sessionControl,
       })
       ```
       If a `useSessionControl` `mockReturnValue` already exists (it should, from Phase 83's harness work), merge into it rather than duplicating. Read the current state first and adapt.

    3. **Create** `frontend/src/contexts/__tests__/SessionControlContext.test.tsx` (NEW file). Existing `frontend/src/contexts/__tests__/SubscriptionContext.test.tsx` is the style reference — read it first to match imports, jsdom polyfills, supabase client mocking, and the renderHook+wrapper pattern.

       Key gotchas to handle in the new test file:
       - `SessionControlProvider` requires `SessionMapProvider` as a parent (it calls `useSessionMap()` at line 105-111). Wrap in both: `<SessionMapProvider><SessionControlProvider>{children}</SessionControlProvider></SessionMapProvider>`.
       - The provider calls `supabase.auth.getUser()` and `listUserSessions()` on mount. Mock them: `vi.mock('@/lib/supabase/client', () => ({ createClient: vi.fn(() => ({ auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'test-user' } } }) }, from: vi.fn() })) }))` and `vi.mock('@/services/sessions', () => ({ listUserSessions: vi.fn().mockResolvedValue({ sessions: [] }) }))`.
       - Each test must `localStorage.clear()` in `beforeEach` to avoid bleed between tests.

       Then write Tests 1-4 from <behavior>. Use `@testing-library/react`'s `render` with a small consumer component:
       ```tsx
       function Consumer() {
         const ctx = useSessionControl()
         return (
           <div>
             <span data-testid="vsid">{ctx.visibleSessionId ?? 'null'}</span>
             <button data-testid="set" onClick={() => ctx.setVisibleSessionId('session-new-456')}>set</button>
             <button data-testid="new" onClick={() => ctx.createNewChat()}>new</button>
           </div>
         )
       }
       ```

    4. **Add Test 5 to `ChatInterface.test.tsx`** under a new describe block: `describe('ChatInterface — persistence (HOTFIX-06)', () => { ... })` at the bottom of the file (after the existing HOTFIX-01 describe block). Use the harness's new `sessionControl` option:
       ```typescript
       import { renderChatInterface } from './__test-utils__/chatHarness'
       import { useAgentChat } from '@/hooks/useAgentChat'  // already mocked module-scope by harness

       it('forwards initialSessionId from props to useAgentChat', () => {
         renderChatInterface({
           initialSessionId: 'session-restore-555',
           sessionControl: { visibleSessionId: 'session-restore-555' },
         })
         expect(useAgentChat).toHaveBeenCalled()
         const firstCallArgs = (useAgentChat as ReturnType<typeof vi.fn>).mock.calls[0]
         // useAgentChat accepts either (sessionId: string) or (options: UseAgentChatOptions)
         const arg = firstCallArgs[0]
         if (typeof arg === 'string') {
           expect(arg).toBe('session-restore-555')
         } else {
           expect(arg.initialSessionId).toBe('session-restore-555')
         }
       })
       ```
       Confirm the harness already accepts `initialSessionId` as a top-level option. If not, add it: read the existing `renderChatInterface` signature first.

    5. **Run the new tests in isolation**:
       ```bash
       cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx
       cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "persistence (HOTFIX-06)"
       ```
       Expected results:
       - Tests 1, 2, 3, 5: **GREEN** (production code already shipped in c8da1d99)
       - Test 4 (cross-tab storage event): **RED** (listener does not exist yet — that's Task 2)

       If Tests 1, 2, 3, or 5 are RED, debug — the production code shipped, so a RED here means a test setup bug, not a regression. Do NOT modify production code in this task; that is Task 2's job.

    6. **Commit RED state**:
       ```bash
       git add frontend/src/components/chat/__test-utils__/chatHarness.ts \
               frontend/src/contexts/__tests__/SessionControlContext.test.tsx \
               frontend/src/components/chat/ChatInterface.test.tsx
       git commit -m "test(88-01): add behavior coverage for shipped persistence + RED cross-tab test (HOTFIX-06)"
       ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx src/components/chat/ChatInterface.test.tsx -t "persistence|HOTFIX-06|storage event"</automated>
  </verify>
  <done>
    Harness extended with `sessionControl` option and a default object covering all 12 fields of `SessionControlContextValue`. New file `SessionControlContext.test.tsx` exists with 4 tests; Tests 1-3 GREEN, Test 4 RED. New describe block in `ChatInterface.test.tsx` with Test 5 GREEN. RED commit exists with message `test(88-01): add behavior coverage for shipped persistence + RED cross-tab test (HOTFIX-06)`. Existing 9 tests in ChatInterface.test.tsx (4 pre-Phase-83 + 5 HOTFIX-01) still pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add `storage` event listener for cross-browser-tab safety (HOTFIX-06.4)</name>
  <files>frontend/src/contexts/SessionControlContext.tsx</files>
  <behavior>
    Test 4 from Task 1 (currently RED) must turn GREEN after this task. After this task:
    - Tab A holds `visibleSessionId === 'session-tab-A'`. Tab B (same origin) writes `localStorage.setItem('pikar_current_session_id', 'session-tab-B')`. Within one render tick, Tab A's `visibleSessionId` updates to `'session-tab-B'` without throwing.
    - The listener does NOT cause an infinite loop — it does NOT call `localStorage.setItem` from inside the handler.
    - The listener is removed on unmount (no leak across hot-reloads).
    - When a tab clears the key (logout, e.g. `localStorage.removeItem(STORAGE_KEY)`), the other tab's `visibleSessionId` becomes `null`.
  </behavior>
  <action>
    Open `frontend/src/contexts/SessionControlContext.tsx`. Locate the existing `useLayoutEffect` block at lines 129-139 (the localStorage restore-on-mount). Add a new `useEffect` block IMMEDIATELY AFTER it (before the `setVisibleSessionId` callback at line 144):

    ```typescript
    // ------------------------------------------------------------------
    // Cross-browser-tab sync — HOTFIX-06 success criterion 4
    //
    // The `storage` event fires on `window` in OTHER same-origin tabs ONLY
    // when localStorage is mutated. Last-write-wins is acceptable per the
    // ROADMAP — we just need to keep this tab's React state in sync with
    // localStorage so the workspace and chat panel re-query for the new
    // session_id rather than displaying stale data keyed on the old one.
    //
    // Do NOT call `setVisibleSessionId` (the persisting setter) from this
    // handler — it would write to localStorage and risk a feedback loop.
    // Use the raw setter so we update React state without touching storage.
    // ------------------------------------------------------------------
    useEffect(() => {
      const handleStorage = (e: StorageEvent) => {
        if (e.key !== STORAGE_KEY) return
        if (e.storageArea !== window.localStorage) return
        // e.newValue is null when the key is removed (e.g. logout in other tab)
        setVisibleSessionIdRaw(e.newValue)
      }
      window.addEventListener('storage', handleStorage)
      return () => window.removeEventListener('storage', handleStorage)
    }, [])
    ```

    **Why a separate `useEffect` and not added to the existing `useLayoutEffect`:** the layout effect fires synchronously before paint exactly once on mount; we want the storage listener attached at any time after mount. Splitting them keeps each effect's job clear. The dependency array is `[]` because `setVisibleSessionIdRaw` is the React setState dispatcher (stable identity guaranteed by React) and `STORAGE_KEY` is a module constant.

    **Verify TypeScript happiness:**
    ```bash
    cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep SessionControlContext | head -10
    ```
    Expect no new errors.

    **Run the failing test (Test 4):**
    ```bash
    cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx -t "storage event"
    ```
    Must turn GREEN.

    **Run all four tests in the new file:**
    ```bash
    cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx
    ```
    All 4 GREEN.

    **Commit GREEN:**
    ```bash
    git add frontend/src/contexts/SessionControlContext.tsx
    git commit -m "fix(88-01): cross-tab session_id sync via storage event listener (HOTFIX-06.4)"
    ```

    **DO NOT add a BroadcastChannel** — the ROADMAP explicitly lists BroadcastChannel as out of scope, and the `storage` event covers last-write-wins for free with zero new browser API surface. Document the BroadcastChannel deferral in the SUMMARY.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx</automated>
  </verify>
  <done>
    New `useEffect` block (~12 lines) added to `SessionControlContext.tsx` immediately after the existing layout-effect restore block. All 4 tests in `SessionControlContext.test.tsx` GREEN. Test 5 in `ChatInterface.test.tsx` still GREEN. Pre-existing 9 tests in `ChatInterface.test.tsx` still GREEN. `npx tsc --noEmit` reports no new errors on this file. GREEN commit exists with message `fix(88-01): cross-tab session_id sync via storage event listener (HOTFIX-06.4)`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full vitest + lint pass + retroactive SUMMARY for shipped c8da1d99 work</name>
  <files>.planning/phases/88-chat-and-workspace-persistence/88-01-persistence-reconciliation-SUMMARY.md</files>
  <action>
    1. **Run the full frontend test suite**: `cd frontend && npm test`. Must be GREEN. (Pre-existing failure noted in STATE.md was resolved at end of Phase 83 — confirm by checking the failure list.)

    2. **Lint check**: `cd frontend && npm run lint`. No new warnings on `SessionControlContext.tsx`, `chatHarness.ts`, `ChatInterface.test.tsx`, or `SessionControlContext.test.tsx`.

    3. **TypeScript safety**: `cd frontend && npx tsc --noEmit -p tsconfig.json`. No errors anywhere mentioning the four modified files.

    4. **Backend impact check**: This plan touches ZERO backend files. `make test` is intentionally NOT in the verification chain. PR reviewers do not need to run backend tests for this plan.

    5. **Manual UAT script** (not run in this task — captured in SUMMARY for the phase gate UAT review):
       - Open the app in Chrome Tab A. Send a message in any persona dashboard. Note the session_id (visible in the URL or the workspace via dev-tools `localStorage.getItem('pikar_current_session_id')`).
       - Hard-refresh Tab A. Verify the same session loads — chat history visible, last agent response present, workspace items restored.
       - Open the app in Chrome Tab B (new tab, same origin). It should pick up the same session_id from localStorage and show the same chat + workspace.
       - In Tab B, click "New Chat" (the `+` icon in the chat panel header). Tab B now shows a fresh session.
       - Switch back to Tab A. Within ~1 second (the time it takes for the storage event to propagate and React to re-render), Tab A's `visibleSessionId` should match Tab B's new session. Workspace re-queries, history dropdown still lists both sessions.
       - Stop the backend (`docker compose stop backend`). Refresh either tab. The localStorage restore still works (it doesn't depend on the backend), but `refreshSessions` will silently fail in `console.error`. The chat interface should still mount without throwing.

    6. **Write retroactive SUMMARY**: Document what shipped in c8da1d99 and what was added in this plan. Use the path in <files> above. The SUMMARY is the only place this work has a planning-tool record — be thorough.

    SUMMARY content requirements:
    - **What shipped pre-plan (c8da1d99, 2026-04-27):** STORAGE_KEY constant; useLayoutEffect restore block (lines 129-139); setVisibleSessionId persist wrapper (lines 144-155); GET /sessions endpoint + listUserSessions service; refreshSessions rewritten to use it. Cite line numbers as anchors.
    - **What this plan added:** storage event listener (~12 lines in SessionControlContext.tsx); 4 behavior tests in new file SessionControlContext.test.tsx; 1 behavior test in ChatInterface.test.tsx ("persistence (HOTFIX-06)" describe block); chatHarness `sessionControl` option extension.
    - **Truth-to-code map** (each of the 5 must_haves.truths to its source line range, for ROADMAP traceability).
    - **Out-of-scope items deliberately deferred:** BroadcastChannel (storage event sufficient for last-write-wins), pikar_open_tab_ids (handled by Plan 88-02), tab-strip UI (handled by Plan 88-03).
    - **Manual UAT script** (the 6-step script from action #5).
    - **PR-reviewer note:** Frontend-only plan. No backend changes. Backend `make test` is not in the verification chain.
  </action>
  <verify>
    <automated>cd frontend && npm test && cd frontend && npm run lint</automated>
  </verify>
  <done>
    Full vitest suite GREEN. Frontend lint clean. TypeScript compile clean. SUMMARY.md exists at `.planning/phases/88-chat-and-workspace-persistence/88-01-persistence-reconciliation-SUMMARY.md` documenting the c8da1d99 reconciliation, the new storage-event listener, and the manual UAT script. PR-reviewer note included.
  </done>
</task>

</tasks>

<verification>
**Per-task automated verification:**

| Task | Command | Maps To |
|------|---------|---------|
| 1 (RED) | `cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx -t "storage event"` (must FAIL) | HOTFIX-06.4 RED gate |
| 2 (GREEN) | `cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx` (must PASS, all 4) | HOTFIX-06.4 GREEN gate |
| 3 (Suite) | `cd frontend && npm test` (must PASS) and `cd frontend && npm run lint` (must be clean) | Phase gate |

**Behavior assertions covering ROADMAP success criteria 1-5:**
1. Test 1 (restores from localStorage) → criterion 1 (chat session restored)
2. Test 5 (initialSessionId forwarded to useAgentChat) → criterion 1 (chat history surfaced)
3. (No new test — visual workspace verification is in the manual UAT script) → criterion 2
4. Test 3 (createNewChat replaces stored id) → criterion 3 (new chat resets)
5. Test 4 (storage event updates visibleSessionId) → criterion 4 (cross-tab safety) — **the new gap closed by this plan**
6. (covered by existing /sessions service tests + manual UAT) → criterion 5 (history list)
</verification>

<success_criteria>
- ROADMAP success criteria 1, 2, 3, 5 are now covered by automated tests AND a manual UAT script (was: zero automated coverage prior to this plan).
- ROADMAP success criterion 4 (cross-tab safety) is implemented and verified — the only previously-open criterion in this part of the phase.
- Production code delta is minimal: ~12 lines added in `SessionControlContext.tsx`, zero deletions.
- Test code delta: ~80 lines across 2 test files plus harness extension (~30 lines in chatHarness.ts).
- No backend files touched; no Python tests need to run.
- A retroactive SUMMARY.md gives the GSD planning system a record of the c8da1d99 work that previously had none.
</success_criteria>

<output>
After completion, create `.planning/phases/88-chat-and-workspace-persistence/88-01-persistence-reconciliation-SUMMARY.md` documenting:
1. **What shipped pre-plan (c8da1d99):** STORAGE_KEY constant + restore + persist + /sessions endpoint, with line-number anchors.
2. **What this plan added:** storage event listener + 5 behavior tests + harness extension.
3. **Truth-to-code map:** each of the 5 must_haves.truths to source line range.
4. **Out-of-scope deferrals:** BroadcastChannel, openTabIds (Plan 02), TabStrip UI (Plan 03).
5. **Manual UAT script (6 steps):** Tab A reload, Tab A+B same session, Tab B new chat, cross-tab observation, backend offline.
6. **PR-reviewer note:** Frontend-only plan; backend tests not required.
</output>
</content>
</invoke>