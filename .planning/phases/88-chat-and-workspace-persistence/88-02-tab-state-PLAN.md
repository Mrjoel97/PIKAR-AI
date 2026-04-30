---
phase: 88-chat-and-workspace-persistence
plan: 02
type: execute
wave: 2
depends_on:
  - "88-01"
files_modified:
  - frontend/src/contexts/SessionControlContext.tsx
  - frontend/src/contexts/ChatSessionContext.tsx
  - frontend/src/contexts/__tests__/SessionControlContext.test.tsx
autonomous: true
requirements:
  - FEATURE-MULTI-SESSION-TABS
must_haves:
  truths:
    - "openTabIds is a string[] of session ids the user has open as tabs, persisted to localStorage key `pikar_open_tab_ids` and restored on mount"
    - "openTab(sessionId) adds the id to openTabIds (idempotent — duplicate add is a no-op) and sets it as visibleSessionId; calling openTab when at the cap is rejected with a thrown TabCapReachedError"
    - "closeTab(sessionId) removes the id from openTabIds AND from the in-memory activeSessions map; if the closed tab was the visible one, the next remaining tab becomes visible (last-opened wins); closing the LAST tab triggers createNewChat() so the chat panel never empties"
    - "closeTab does NOT delete the session from Supabase — sessions remain in /sessions list and the user can reopen via the chat history dropdown"
    - "Tab cap is derived from the user's subscription tier via useSubscription called inside useChatSession() (NOT inside SessionControlProvider — provider tree mismatch): free → 5 tabs, all paid tiers (solopreneur/startup/sme/enterprise) → 8 tabs. Provider defaults tabCap to TAB_CAP_FREE=5 via useState; useChatSession() pushes the tier-derived value via setTabCap from a useEffect on tier change"
    - "Selecting a chat from the history dropdown via selectChat(id) auto-opens it as a tab (calls openTab internally) so the tab strip is always in sync with what the user is viewing"
  artifacts:
    - path: "frontend/src/contexts/SessionControlContext.tsx"
      provides: "openTabIds state + openTab/closeTab callbacks + tier-aware cap + localStorage persistence under `pikar_open_tab_ids`"
      contains: "openTabIds"
      min_lines: 600
    - path: "frontend/src/contexts/ChatSessionContext.tsx"
      provides: "Re-export of openTabIds, openTab, closeTab, tabCap from useChatSession() so consumers (Plan 03 TabStrip, future code) get the unified interface"
      contains: "openTabIds"
    - path: "frontend/src/contexts/__tests__/SessionControlContext.test.tsx"
      provides: "Behavior tests for openTab/closeTab/persistence/cap enforcement (~8 new tests)"
      contains: "openTab"
  key_links:
    - from: "openTab(sessionId)"
      to: "addActiveSession + setVisibleSessionId"
      via: "the existing addActiveSession from SessionMapContext warms the in-memory map; setVisibleSessionId makes the new tab visible AND persists session_id"
      pattern: "addActiveSession\\("
    - from: "closeTab(sessionId)"
      to: "removeActiveSession + setOpenTabIds + (conditional) createNewChat"
      via: "removes from both the openTabIds list and the activeSessions map; if list becomes empty, calls createNewChat to seed a fresh tab"
      pattern: "removeActiveSession\\("
    - from: "selectChat(sessionId)"
      to: "openTab(sessionId)"
      via: "selectChat is rewritten to delegate to openTab so opening from the history dropdown produces a new tab pill (existing setVisibleSessionId-only behavior is replaced)"
      pattern: "openTab\\(sessionId\\)"
    - from: "tier from useSubscription"
      to: "tabCap derivation"
      via: "useMemo (tier === 'free' ? 5 : 8); not a hook in the inner provider — provider already lives under SubscriptionProvider in app/layout.tsx"
      pattern: "tier === 'free'"
---

<objective>
Build the in-memory and persistent state machinery for multi-session tabs. Pure state plan — no UI, no rendering. Plan 03 will consume this state to render the tab strip in `ChatInterface.tsx`.

Adds three pieces to `SessionControlContext`:
1. `openTabIds: string[]` state, persisted to localStorage key `pikar_open_tab_ids`.
2. `openTab(sessionId)` and `closeTab(sessionId)` callbacks with cap enforcement and last-tab fallback.
3. Tier-aware `tabCap` (free=5, paid=8) sourced from `useSubscription()`.

Re-exports the new fields through `useChatSession()` so the existing consumer pattern continues to work.

Purpose: FEATURE-MULTI-SESSION-TABS — the data layer. Splits cleanly from the UI layer (Plan 03) so logic and rendering are testable and reviewable in isolation, matching the project's established pattern of context/UI separation (see `SessionMapContext` ↔ `ChatInterface`).

Output: ~80 lines added in `SessionControlContext.tsx` (state + restore + persist + 2 callbacks + cap derivation); ~10 lines added in `ChatSessionContext.tsx` (re-export); ~8 new vitest tests in the existing `SessionControlContext.test.tsx` from Plan 01; one new module-scope export `TabCapReachedError`.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/88-chat-and-workspace-persistence/88-01-persistence-reconciliation-SUMMARY.md

# Source under modification
@frontend/src/contexts/SessionControlContext.tsx
@frontend/src/contexts/ChatSessionContext.tsx
@frontend/src/contexts/__tests__/SessionControlContext.test.tsx

# Reference (DO NOT modify in this plan)
@frontend/src/contexts/SessionMapContext.tsx
@frontend/src/contexts/SubscriptionContext.tsx
@frontend/src/types/session.ts

<interfaces>
<!-- Existing context value shape (frontend/src/contexts/SessionControlContext.tsx:32-47) -->

```typescript
interface SessionControlContextValue {
  visibleSessionId: string | null
  setVisibleSessionId: (id: string | null) => void
  sessionRestored: boolean
  config: SessionConfig

  createNewChat: () => string
  selectChat: (sessionId: string) => void

  deleteChat: (sessionId: string) => Promise<void>
  clearAllChats: () => Promise<void>
  refreshSessions: () => Promise<void>
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>
  updateSessionPreview: (sessionId: string, preview: string) => Promise<void>
  addSessionOptimistic: (session: ChatSession) => void
}
```

<!-- New shape after Plan 02 — additions only, no breaking changes to existing fields -->

```typescript
interface SessionControlContextValue {
  // ... all existing fields unchanged ...

  // NEW for FEATURE-MULTI-SESSION-TABS:
  openTabIds: string[]
  tabCap: number
  openTab: (sessionId: string) => void  // throws TabCapReachedError if at cap
  closeTab: (sessionId: string) => void
}

// Module-scope export (also new):
export class TabCapReachedError extends Error {
  constructor(public cap: number) {
    super(`Tab cap reached (${cap}). Close a tab before opening a new one.`)
    this.name = 'TabCapReachedError'
  }
}
```

<!-- useChatSession() re-export (frontend/src/contexts/ChatSessionContext.tsx:29-50) -->
<!-- After Plan 02 it must include the four new fields -->

```typescript
export function useChatSession() {
  const map = useSessionMap()
  const ctrl = useSessionControl()
  return {
    // ... all existing fields ...

    // NEW:
    openTabIds: ctrl.openTabIds,
    tabCap: ctrl.tabCap,
    openTab: ctrl.openTab,
    closeTab: ctrl.closeTab,
  }
}
```

<!-- Existing SessionMapContext methods used by closeTab/openTab -->
<!-- (frontend/src/contexts/SessionMapContext.tsx:39-51) -->
```typescript
addActiveSession: (sessionId: string, initialOverrides?: Partial<ActiveSessionState>) => void  // no-op if already present
removeActiveSession: (sessionId: string) => void  // cleans up the ref map too
```

<!-- Tier source (frontend/src/contexts/SubscriptionContext.tsx:14, 75) -->
```typescript
export type PikarTier = 'free' | 'solopreneur' | 'startup' | 'sme' | 'enterprise'
const tier: PikarTier = subscription?.is_active ? subscription.tier : 'free'
```
<!-- SubscriptionProvider is already mounted above SessionControlProvider in app/layout.tsx — confirm with grep before adding the useSubscription import. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Define openTabIds + tabCap state and the TabCapReachedError export (interface contracts first)</name>
  <files>frontend/src/contexts/SessionControlContext.tsx, frontend/src/contexts/ChatSessionContext.tsx</files>
  <behavior>
    No tests run yet — this task only defines the shape. Verification is TypeScript compile + lint pass. Tests come in Task 2 (RED) and Task 3 (GREEN).

    After this task:
    - `SessionControlContextValue` includes the four new fields with correct types.
    - `TabCapReachedError` is exported as a named export from `SessionControlContext.tsx`.
    - `useChatSession()` re-exports the four new fields.
    - The module compiles. The four new methods/fields are stubs (return empty array, no-op functions, cap=5) — they will be wired in Task 3.

    Stub bodies for this task only:
    ```typescript
    const [openTabIds, setOpenTabIds] = useState<string[]>([])
    const tabCap = 5  // stub — proper tier derivation in Task 3
    const openTab = useCallback((sessionId: string) => { /* TODO Task 3 */ }, [])
    const closeTab = useCallback((sessionId: string) => { /* TODO Task 3 */ }, [])
    ```
  </behavior>
  <action>
    1. **Provider tree note (do NOT call `useSubscription()` inside `SessionControlProvider`).**

       Verified provider locations:
       - `SessionControlProvider` is mounted at the **root layout** (`frontend/src/app/layout.tsx:86-100`).
       - `SubscriptionProvider` is mounted at the **dashboard layout** (`frontend/src/app/dashboard/layout.tsx`), which is a CHILD of the root.

       Calling `useSubscription()` inside `SessionControlProvider` would throw "must be used within a `<SubscriptionProvider>`" — its `useContext` returns null at the root tree depth. **DO NOT add `useSubscription()` to `SessionControlProvider`.**

       **Contingency (a) — Read tier inside `useChatSession()`:** Keep `tabCap` as plain state inside `SessionControlProvider` defaulted to `TAB_CAP_FREE = 5` (the safe default for non-dashboard consumers). Inside `useChatSession()` in `ChatSessionContext.tsx` (which IS used only inside the dashboard tree where `SubscriptionProvider` is mounted), call `useSubscription()` and OVERRIDE `tabCap` in the returned object with the tier-derived value. Plan 03/04 already consume `tabCap` via `useChatSession()`/`useSessionControl()` — this approach gives:
       - Dashboard-tree consumers (where `SubscriptionProvider` is available) → tier-derived cap (5 free / 8 paid).
       - Non-dashboard-tree consumers (theoretical future use) → safe default `TAB_CAP_FREE = 5`.
       - `SessionControlProvider` itself remains mountable at the root with no Subscription dependency.

       This task (Task 1) does NOT add `useSubscription()` anywhere — it only sets up the stub state. Task 3 wires the tier override INSIDE `useChatSession()` (not inside `SessionControlProvider`). Test 10 mocks `useSubscription()` at the `useChatSession()` consumer site, not inside the SessionControlProvider tree.

    2. **Edit `frontend/src/contexts/SessionControlContext.tsx`:**

       **Step 2a — Add the new module-scope constant and error class** at the top, near the existing `STORAGE_KEY` (line 26):
       ```typescript
       const STORAGE_KEY = 'pikar_current_session_id'
       const OPEN_TABS_STORAGE_KEY = 'pikar_open_tab_ids'  // NEW
       const TAB_CAP_FREE = 5                              // NEW
       const TAB_CAP_PAID = 8                              // NEW
       const AGENTS_APP_NAME = 'agents'

       // NEW — exported error class for callers to catch when at cap
       export class TabCapReachedError extends Error {
         constructor(public cap: number) {
           super(`Tab cap reached (${cap}). Close a tab before opening a new one.`)
           this.name = 'TabCapReachedError'
         }
       }
       ```

       **Step 2b — Extend the `SessionControlContextValue` interface** (line 32):
       ```typescript
       interface SessionControlContextValue {
         visibleSessionId: string | null
         setVisibleSessionId: (id: string | null) => void
         sessionRestored: boolean
         config: SessionConfig

         createNewChat: () => string
         selectChat: (sessionId: string) => void

         deleteChat: (sessionId: string) => Promise<void>
         clearAllChats: () => Promise<void>
         refreshSessions: () => Promise<void>
         updateSessionTitle: (sessionId: string, title: string) => Promise<void>
         updateSessionPreview: (sessionId: string, preview: string) => Promise<void>
         addSessionOptimistic: (session: ChatSession) => void

         // NEW — multi-session tab support (FEATURE-MULTI-SESSION-TABS)
         openTabIds: string[]
         tabCap: number
         setTabCap: (cap: number) => void  // pushed by useChatSession() with tier-derived value
         openTab: (sessionId: string) => void  // throws TabCapReachedError if at cap
         closeTab: (sessionId: string) => void
       }
       ```

       **Step 2c — Add stub state inside `SessionControlProvider`** (after the existing `useState` calls near line 116-121):
       ```typescript
       const [visibleSessionId, setVisibleSessionIdRaw] = useState<string | null>(null)
       const [sessionRestored, setSessionRestored] = useState(false)
       const [config, setConfig] = useState<SessionConfig>(DEFAULT_SESSION_CONFIG)
       const [userId, setUserId] = useState<string | null>(null)

       // NEW — multi-session tab state (proper restore/persist/wiring in Task 3)
       const [openTabIds, setOpenTabIds] = useState<string[]>([])
       // tabCap is useState so useChatSession() can push tier-derived value via setTabCap.
       // Default = TAB_CAP_FREE (5). DO NOT call useSubscription() here — provider tree mismatch.
       const [tabCap, setTabCap] = useState<number>(TAB_CAP_FREE)
       const openTab = useCallback((_sessionId: string) => {
         // STUB — Task 3 implements
       }, [])
       const closeTab = useCallback((_sessionId: string) => {
         // STUB — Task 3 implements
       }, [])
       ```

       **Step 2d — Add the five new fields to the memoized context value** (around line 471-500):
       ```typescript
       const value = useMemo<SessionControlContextValue>(
         () => ({
           visibleSessionId,
           setVisibleSessionId,
           sessionRestored,
           config,
           createNewChat,
           selectChat,
           deleteChat,
           clearAllChats,
           refreshSessions,
           updateSessionTitle,
           updateSessionPreview,
           addSessionOptimistic,
           // NEW
           openTabIds,
           tabCap,
           setTabCap,
           openTab,
           closeTab,
         }),
         [
           visibleSessionId,
           setVisibleSessionId,
           sessionRestored,
           config,
           createNewChat,
           selectChat,
           deleteChat,
           clearAllChats,
           refreshSessions,
           updateSessionTitle,
           updateSessionPreview,
           addSessionOptimistic,
           // NEW deps
           openTabIds,
           tabCap,
           setTabCap,
           openTab,
           closeTab,
         ],
       )
       ```

    3. **Edit `frontend/src/contexts/ChatSessionContext.tsx`** (line 29-50). Add the four new fields to the returned object. **For this task (the stub task), pass through `ctrl.tabCap` directly.** Task 3 Step 2 will replace this with a tier-derived override using `useSubscription()` — but we need the stubs to compile cleanly first.
       ```typescript
       export function useChatSession() {
         const map = useSessionMap()
         const ctrl = useSessionControl()
         return {
           currentSessionId: ctrl.visibleSessionId,
           setCurrentSessionId: ctrl.setVisibleSessionId,
           sessionRestored: ctrl.sessionRestored,
           sessions: map.sessions,
           isLoadingSessions: map.isLoadingSessions,
           createNewChat: ctrl.createNewChat,
           selectChat: ctrl.selectChat,
           deleteChat: ctrl.deleteChat,
           clearAllChats: ctrl.clearAllChats,
           refreshSessions: ctrl.refreshSessions,
           updateSessionTitle: ctrl.updateSessionTitle,
           updateSessionPreview: ctrl.updateSessionPreview,
           addSessionOptimistic: ctrl.addSessionOptimistic,
           goToHistoryPage: () => {
             window.location.href = '/dashboard/history'
           },
           // NEW
           openTabIds: ctrl.openTabIds,
           tabCap: ctrl.tabCap,
           openTab: ctrl.openTab,
           closeTab: ctrl.closeTab,
         }
       }
       ```

    4. **TypeScript check:**
       ```bash
       cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E "SessionControlContext|ChatSessionContext" | head -20
       ```
       Must report zero errors on these two files.

    5. **Lint check:**
       ```bash
       cd frontend && npx eslint src/contexts/SessionControlContext.tsx src/contexts/ChatSessionContext.tsx
       ```
       Should be clean. The `_sessionId` unused-arg in the stubs is intentional — eslint-disable per-line if necessary, or use `void _sessionId` to suppress.

    6. **Run existing tests** to confirm no regression:
       ```bash
       cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx
       ```
       The 4 tests from Plan 01 should still GREEN. (The harness stub from Plan 01 only mocks specific fields; the new ones are unused by those tests so they pass through fine.)

    7. **Commit (interface-only, no behavior):**
       ```bash
       git add frontend/src/contexts/SessionControlContext.tsx frontend/src/contexts/ChatSessionContext.tsx
       git commit -m "feat(88-02): tab state interface + TabCapReachedError stub (FEATURE-MULTI-SESSION-TABS)"
       ```

    **DO NOT** wire `useSubscription()` inside `SessionControlContext.tsx` — neither in this task nor in Task 3. The tier-derived override lives in `useChatSession()` (Task 3 Step 2 below). Keeping the stub at `TAB_CAP_FREE` inside `SessionControlProvider` lets Task 2 write tests against a known-constant cap and respects the provider tree (root layout has no `SubscriptionProvider`).
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E "SessionControlContext|ChatSessionContext"</automated>
  </verify>
  <done>
    `SessionControlContextValue` extended with 4 new fields. `TabCapReachedError` exported. Stubs in place. `useChatSession()` re-exports the new fields. TypeScript compile clean for the two modified files. Pre-Plan-01 4 vitest tests still GREEN. Commit message: `feat(88-02): tab state interface + TabCapReachedError stub (FEATURE-MULTI-SESSION-TABS)`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: RED behavior tests for openTab/closeTab/persistence/cap enforcement</name>
  <files>frontend/src/contexts/__tests__/SessionControlContext.test.tsx</files>
  <behavior>
    8 new tests added to the existing test file from Plan 01. ALL 8 should RED because Task 1 left the methods as stubs. They turn GREEN in Task 3.

    - **Test 6 — "openTab adds id to openTabIds"**: render provider; click a button that calls `openTab('session-A')`; assert the consumer reads `openTabIds === ['session-A']`. Maps to feature criteria 6, 8.

    - **Test 7 — "openTab is idempotent on duplicate"**: render; openTab('session-A') twice; assert `openTabIds === ['session-A']` (length 1, not 2).

    - **Test 8 — "openTab makes the session visible"**: render; openTab('session-X'); assert `visibleSessionId === 'session-X'` AND `localStorage.getItem('pikar_current_session_id') === 'session-X'` (proves it goes through the existing setVisibleSessionId persisting setter).

    - **Test 9 — "openTab persists openTabIds to localStorage"**: render; openTab('session-A'); openTab('session-B'); assert `JSON.parse(localStorage.getItem('pikar_open_tab_ids') || '[]') === ['session-A', 'session-B']` (deep equal).

    - **Test 10 — "openTab at cap throws TabCapReachedError"**: render the SessionControlProvider directly (NOT through `useChatSession()`); openTab 5 times with distinct ids ('session-1'..'session-5'); attempt to openTab('session-6'); assert it throws `TabCapReachedError` with `error.cap === 5`. Use `expect(() => act(() => openTab('session-6'))).toThrow(TabCapReachedError)` pattern.

      **Mocking site note (BLOCKER 1 fix):** `useSubscription()` is NOT called inside `SessionControlProvider` (provider tree mismatch — `SubscriptionProvider` is at `/dashboard/layout.tsx`, child of root). The provider's `tabCap` is a plain `useState` defaulting to `TAB_CAP_FREE = 5`, so this test runs without ANY `useSubscription` mock. The tier-derived override happens inside `useChatSession()` (Task 3 Step 2) — when adding a separate test that exercises tier-derived cap (e.g., paid=8), mock `useSubscription()` at the `useChatSession()` consumer site, NOT inside this provider-only test. Maps to feature criterion 6 (cap 5 free).

    - **Test 11 — "closeTab removes id from openTabIds and activeSessions"**: render; openTab('session-A'); openTab('session-B'); closeTab('session-A'); assert `openTabIds === ['session-B']` AND that `removeActiveSession` mock from `SessionMapContext` was called with `'session-A'`. Maps to criterion 10.

    - **Test 12 — "closeTab on visible tab promotes the next remaining tab"**: render; openTab('session-A'); openTab('session-B'); openTab('session-C') (visible is 'session-C' after step 3); closeTab('session-C'); assert `visibleSessionId === 'session-B'` (the most-recently-opened remaining tab — i.e. `openTabIds[openTabIds.length - 1]` after the splice). Maps to criterion 8.

    - **Test 13 — "closeTab on the last remaining tab triggers createNewChat"**: render; openTab('session-only'); closeTab('session-only'); assert: `openTabIds.length === 1` (not 0 — because createNewChat opened a fresh tab); `openTabIds[0] !== 'session-only'`; `openTabIds[0]` matches `/^session-\d+-[a-z0-9]+$/`. **Plus explicit final-localStorage assertion** (BLOCKER 2 fix): after the closeTab→createNewChat sequence, `expect(JSON.parse(localStorage.getItem(OPEN_TABS_STORAGE_KEY) || '[]')).toEqual([newId])` where `newId = openTabIds[0]` (the createNewChat-generated id). This locks in the final localStorage state and proves the transient `[]` write between updaters is fully recovered. Maps to feature criterion 10 + locked decision "auto-open a fresh new chat".

      **Transient-write note (record in SUMMARY):** The closeTab→createNewChat sequence transiently writes `[]` to `pikar_open_tab_ids` between the two `setOpenTabIds` updaters, then writes `[newId]`. The transient empty-array write is acceptable today because **`pikar_open_tab_ids` does NOT have a cross-tab `storage` event listener** (only `pikar_current_session_id` has one — see Plan 88-01). If a future phase adds cross-tab sync for `pikar_open_tab_ids`, the writes need to be unified (e.g., via `flushSync`, a single combined reducer, or a debounced effect that watches the array reference and writes once per render commit).

    - **Test 14 — "openTabIds restored from localStorage on mount"**: seed `localStorage.setItem('pikar_open_tab_ids', '["session-restore-1","session-restore-2"]')` BEFORE rendering; mount provider; assert openTabIds is `['session-restore-1', 'session-restore-2']`. Maps to criterion 7.
  </behavior>
  <action>
    1. **Open the existing test file** `frontend/src/contexts/__tests__/SessionControlContext.test.tsx` (created in Plan 01). Confirm the existing 4 tests still pass before adding new ones.

    2. **Add a new describe block** at the bottom of the file:
       ```typescript
       describe('SessionControlContext — multi-session tabs (FEATURE-MULTI-SESSION-TABS)', () => {
         beforeEach(() => {
           localStorage.clear()
           vi.clearAllMocks()
         })
         // Tests 6-14 below
       })
       ```

    3. **Update the consumer test component** to expose the new fields. The existing `Consumer` from Plan 01 only reads `visibleSessionId`. Extend it (in this describe block, scoped via a local component definition):
       ```tsx
       function TabConsumer({ onError }: { onError?: (e: unknown) => void }) {
         const ctx = useSessionControl()
         return (
           <div>
             <span data-testid="vsid">{ctx.visibleSessionId ?? 'null'}</span>
             <span data-testid="tabs">{JSON.stringify(ctx.openTabIds)}</span>
             <span data-testid="cap">{ctx.tabCap}</span>
             <button data-testid="open" onClick={(e) => {
               const id = (e.currentTarget as HTMLButtonElement).dataset.id!
               try { ctx.openTab(id) } catch (err) { onError?.(err) }
             }} />
             <button data-testid="close" onClick={(e) => {
               const id = (e.currentTarget as HTMLButtonElement).dataset.id!
               ctx.closeTab(id)
             }} />
           </div>
         )
       }

       function clickOpen(id: string) {
         const btn = screen.getByTestId('open') as HTMLButtonElement
         btn.dataset.id = id
         fireEvent.click(btn)
       }
       function clickClose(id: string) {
         const btn = screen.getByTestId('close') as HTMLButtonElement
         btn.dataset.id = id
         fireEvent.click(btn)
       }
       ```

    4. **Mock `removeActiveSession`** at module scope so Test 11 can assert it was called. The existing `SessionControlContext` calls `removeActiveSession` from `useSessionMap()` — the test must wrap in `<SessionMapProvider>`. Either:
       - **Option A (preferred):** spy on the real `SessionMapProvider`'s removeActiveSession via the actual context — render with the real provider, capture a ref to its return value via a sibling consumer, then `vi.spyOn(...)` on the captured method.
       - **Option B (simpler):** mock the entire `SessionMapContext` module: `vi.mock('@/contexts/SessionMapContext', () => ({ useSessionMap: vi.fn(() => ({ addActiveSession: vi.fn(), removeActiveSession: vi.fn(), sessions: [], setSessions: vi.fn(), isLoadingSessions: false, setIsLoadingSessions: vi.fn(), updateSessionState: vi.fn(), getActiveSessionRef: vi.fn(() => null), activeSessions: new Map() })), SessionMapProvider: ({ children }: { children: React.ReactNode }) => children }))` — capture the spy via the mock implementation. Pick **Option B** for simpler test setup; document the choice in a comment.

       Implementation:
       ```typescript
       const removeActiveSessionMock = vi.fn()
       const addActiveSessionMock = vi.fn()
       vi.mock('@/contexts/SessionMapContext', async () => {
         const actual = await vi.importActual<typeof import('@/contexts/SessionMapContext')>('@/contexts/SessionMapContext')
         return {
           ...actual,
           useSessionMap: () => ({
             activeSessions: new Map(),
             addActiveSession: addActiveSessionMock,
             removeActiveSession: removeActiveSessionMock,
             updateSessionState: vi.fn(),
             getActiveSessionRef: vi.fn(() => null),
             sessions: [],
             setSessions: vi.fn(),
             isLoadingSessions: false,
             setIsLoadingSessions: vi.fn(),
           }),
         }
       })
       ```
       (Top of test file, NOT inside the describe block — vi.mock hoists.)

    5. **Write Tests 6-14** per the <behavior> spec. Use `act()` from `@testing-library/react` around button clicks that update state.

    6. **Run the new tests**:
       ```bash
       cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx -t "multi-session tabs"
       ```
       **All 9 tests MUST RED** (8 from this task + the existing failure flow). Specifically:
       - Tests 6-9 fail because `openTab` is a no-op stub — `openTabIds` stays `[]`.
       - Test 10 fails because `openTab` doesn't throw.
       - Tests 11-13 fail because `closeTab` is a no-op stub.
       - Test 14 fails because there's no localStorage restore for `pikar_open_tab_ids` yet.

       Plan 01's 4 tests must still GREEN.

    7. **Commit RED**:
       ```bash
       git add frontend/src/contexts/__tests__/SessionControlContext.test.tsx
       git commit -m "test(88-02): RED tests for openTab/closeTab/persistence/cap (FEATURE-MULTI-SESSION-TABS)"
       ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx -t "multi-session tabs"</automated>
  </verify>
  <done>
    8 new tests in describe `SessionControlContext — multi-session tabs (FEATURE-MULTI-SESSION-TABS)`. `removeActiveSession`/`addActiveSession` mocked at module scope so closeTab/openTab can be observed. All 8 tests RED. Plan 01's 4 tests still GREEN. RED commit message: `test(88-02): RED tests for openTab/closeTab/persistence/cap (FEATURE-MULTI-SESSION-TABS)`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire openTab/closeTab/persistence/tier-derived cap (GREEN)</name>
  <files>frontend/src/contexts/SessionControlContext.tsx</files>
  <behavior>
    All 8 RED tests from Task 2 turn GREEN. Plan 01's 4 tests stay GREEN. New behavior:
    - `openTabIds` restored from localStorage on mount (alongside the existing `pikar_current_session_id` restore from Plan 01).
    - `openTabIds` persisted on every change.
    - `openTab(id)` adds to list (idempotent), warms `activeSessions` via `addActiveSession`, makes visible via `setVisibleSessionId`, throws `TabCapReachedError` when at cap.
    - `closeTab(id)` removes from list, calls `removeActiveSession`, promotes the most-recently-opened remaining tab to visible if the closed tab was visible, calls `createNewChat()` if the closed tab was the only one.
    - `tabCap` defaults to `TAB_CAP_FREE = 5` inside `SessionControlProvider` (no `useSubscription()` call there — provider tree mismatch). The tier-derived override (free=5 / paid=8) is applied INSIDE `useChatSession()` in `ChatSessionContext.tsx`, which only runs in the dashboard tree where `SubscriptionProvider` is mounted.
    - `selectChat(id)` is rewritten to delegate to `openTab(id)` so opening from the history dropdown produces a tab pill.
  </behavior>
  <action>
    Edit `frontend/src/contexts/SessionControlContext.tsx` AND `frontend/src/contexts/ChatSessionContext.tsx` IN THIS ORDER:

    **Step 1 — Inside `SessionControlProvider` (in `SessionControlContext.tsx`), keep `tabCap` as the safe default.** Replace the stub `const tabCap = TAB_CAP_FREE` (the constant from Task 1) with a `useState` so consumers see a referentially stable value. **DO NOT import or call `useSubscription()` here** — the provider lives at the root layout (`app/layout.tsx:86-100`), above `SubscriptionProvider` (mounted at `app/dashboard/layout.tsx`). Calling `useSubscription()` here would throw at render time.
    ```typescript
    // Provider-side default: safe for all consumers (root + dashboard trees).
    // The dashboard tree gets a tier-derived override via useChatSession() — see Step 2.
    const tabCap = TAB_CAP_FREE
    ```
    Note: keep this as a plain `const` (NOT `useState`) — the value never changes inside the provider. The override happens at the consumer site. The four exported context value fields (`openTabIds`, `tabCap`, `openTab`, `closeTab`) still appear in `useMemo` deps as before.

    **Step 2 — In `ChatSessionContext.tsx`'s `useChatSession()` hook, override `tabCap` with the tier-derived value.** This hook is invoked only in the dashboard tree where `SubscriptionProvider` IS mounted, so `useSubscription()` is safe here.

    Add the import at the top of `ChatSessionContext.tsx`:
    ```typescript
    import { useSubscription } from './SubscriptionContext'
    ```

    Then update `useChatSession()`:
    ```typescript
    export function useChatSession() {
      const map = useSessionMap()
      const ctrl = useSessionControl()
      // Tier-derived tab cap override. SessionControlProvider lives at the root
      // layout (above SubscriptionProvider), so it can't call useSubscription()
      // itself — this hook is called inside the dashboard tree where
      // SubscriptionProvider is mounted, so the override is safe here.
      const { tier } = useSubscription()
      const tabCap = tier === 'free' ? 5 : 8  // TAB_CAP_FREE / TAB_CAP_PAID
      return {
        // ... all existing fields ...
        openTabIds: ctrl.openTabIds,
        tabCap,                          // <-- override, NOT ctrl.tabCap
        openTab: ctrl.openTab,
        closeTab: ctrl.closeTab,
      }
    }
    ```

    **Why this approach:** non-dashboard consumers (theoretical or future) get the safe `TAB_CAP_FREE = 5` default from `useSessionControl()`. Dashboard consumers get the tier-aware cap from `useChatSession()`. `openTab`'s cap-check inside `SessionControlProvider` reads `tabCap` from local state, which is always `TAB_CAP_FREE` — meaning the cap-check enforcement is the floor (5), not the dashboard ceiling (8). This is conservative-correct: a dashboard user on a paid tier with `useChatSession().tabCap === 8` who reaches 5 tabs will hit the provider-level cap and `openTab` will throw `TabCapReachedError(5)`.

    **HOWEVER, that's a problem for paid-tier users (criterion 6 says paid=8).** To fix this without moving providers, we expose a setter for `tabCap` from the provider AND have `useChatSession()` push the tier-derived cap into provider state via `useEffect`:

    Update Step 1 — make `tabCap` a `useState` after all (overriding what's said above):
    ```typescript
    // SessionControlContext.tsx
    const [tabCap, setTabCap] = useState<number>(TAB_CAP_FREE)
    ```

    Add `setTabCap` to the context value (and the `SessionControlContextValue` interface) so `useChatSession()` can push the tier-derived value:
    ```typescript
    // Interface addition
    setTabCap: (cap: number) => void
    ```

    Update `useChatSession()` to sync the cap on tier change:
    ```typescript
    // ChatSessionContext.tsx
    export function useChatSession() {
      const map = useSessionMap()
      const ctrl = useSessionControl()
      const { tier } = useSubscription()
      const desiredCap = tier === 'free' ? 5 : 8

      // Push the tier-derived cap into the provider so openTab's cap-check
      // sees the right number. This runs inside the dashboard tree only;
      // non-dashboard consumers (none today) keep the TAB_CAP_FREE default.
      useEffect(() => {
        ctrl.setTabCap(desiredCap)
      }, [desiredCap, ctrl.setTabCap])

      return {
        // ... existing fields ...
        openTabIds: ctrl.openTabIds,
        tabCap: desiredCap,             // expose desired cap directly
        openTab: ctrl.openTab,
        closeTab: ctrl.closeTab,
      }
    }
    ```

    Add `useEffect` and `useSubscription` imports to `ChatSessionContext.tsx`. The `setTabCap` field is added to `SessionControlContextValue` and to the memoized context value (don't forget to expose it in Step 8 of the Task 3 actions list — currently the `useChatSession()` re-export in the file does NOT expose `setTabCap`; it's used only by `useChatSession()` internally to keep provider state in sync).

    **Why useMemo dep stability:** `setTabCap` is a React setState dispatcher (stable identity). The cap value flows through `useState` so all `useCallback`/`useMemo` deps that already reference `tabCap` (notably `openTab`'s cap-check) update correctly when `setTabCap` is called.

    **Step 3 — Add openTabIds restore on mount.** Place this `useLayoutEffect` IMMEDIATELY AFTER the existing one for `pikar_current_session_id` (which lives at lines 129-139 in the post-Plan-01 file):
    ```typescript
    // Restore open tab list from localStorage (FEATURE-MULTI-SESSION-TABS)
    useLayoutEffect(() => {
      try {
        const stored = localStorage.getItem(OPEN_TABS_STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          if (Array.isArray(parsed) && parsed.every((x) => typeof x === 'string')) {
            setOpenTabIds(parsed)
          }
        }
      } catch {
        // localStorage unavailable or JSON malformed — start with empty list
      }
    }, [])
    ```

    **Step 4 — Add openTabIds persist on every change.** Place this `useEffect` (NOT useLayoutEffect — paint-blocking is unnecessary for writes):
    ```typescript
    // Persist open tab list to localStorage on every change
    useEffect(() => {
      try {
        if (openTabIds.length === 0) {
          localStorage.removeItem(OPEN_TABS_STORAGE_KEY)
        } else {
          localStorage.setItem(OPEN_TABS_STORAGE_KEY, JSON.stringify(openTabIds))
        }
      } catch {
        // localStorage unavailable
      }
    }, [openTabIds])
    ```

    **Step 5 — Replace the `openTab` stub with the real implementation.** Locate the stub `const openTab = useCallback(...)` and replace with:
    ```typescript
    const openTab = useCallback(
      (sessionId: string) => {
        // Idempotent: if already open, just make it visible and return
        let alreadyOpen = false
        setOpenTabIds((prev) => {
          if (prev.includes(sessionId)) {
            alreadyOpen = true
            return prev
          }
          if (prev.length >= tabCap) {
            // Throw synchronously — DO NOT call setOpenTabIds with a value that hits the cap.
            // The throw exits this updater; the state setter has already returned `prev`
            // unchanged, so no state mutation happens. The throw bubbles to the caller.
            throw new TabCapReachedError(tabCap)
          }
          return [...prev, sessionId]
        })
        // Warm the active session map (no-op if already present)
        addActiveSession(sessionId)
        // Make this tab visible (also persists pikar_current_session_id)
        setVisibleSessionId(sessionId)
      },
      [tabCap, addActiveSession, setVisibleSessionId],
    )
    ```

    **Why we throw inside the setOpenTabIds updater:** React calls the updater synchronously, and a throw inside an updater bubbles up to the caller while leaving prior state untouched. Tested in React 18+. If future React behavior changes, the test (Test 10) will catch the regression.

    **Step 6 — Replace the `closeTab` stub:**
    ```typescript
    const closeTab = useCallback(
      (sessionId: string) => {
        let nextOpenTabIds: string[] = []
        let wasVisible = false
        setOpenTabIds((prev) => {
          if (!prev.includes(sessionId)) return prev  // no-op if not open
          nextOpenTabIds = prev.filter((id) => id !== sessionId)
          return nextOpenTabIds
        })
        // Read visibleSessionId via state — closure captures the current render's value
        // which is exactly what we want (the user closed the visible tab if these match).
        wasVisible = visibleSessionId === sessionId

        // Remove from in-memory map. This is safe even if the map doesn't have the entry.
        removeActiveSession(sessionId)

        if (wasVisible) {
          if (nextOpenTabIds.length === 0) {
            // Last tab closed — auto-open a fresh chat (locked decision in CONTEXT)
            createNewChat()
          } else {
            // Promote the most-recently-opened remaining tab.
            const promoted = nextOpenTabIds[nextOpenTabIds.length - 1]
            setVisibleSessionId(promoted)
          }
        }
      },
      [visibleSessionId, removeActiveSession, setVisibleSessionId, createNewChat],
    )
    ```

    **Step 7 — Rewrite `selectChat`** (existing at lines 186-191) to delegate to `openTab`:
    ```typescript
    const selectChat = useCallback(
      (sessionId: string) => {
        try {
          openTab(sessionId)
        } catch (err) {
          if (err instanceof TabCapReachedError) {
            // Surface the error to the caller — Plan 03 TabStrip + Plan 04 toast
            // will render a user-facing message. For now, log so manual UAT shows
            // it cleanly in the browser console.
            console.warn('[SessionControl] selectChat hit tab cap:', err.message)
          } else {
            throw err
          }
        }
      },
      [openTab],
    )
    ```

    **Step 8 — DO NOT modify `createNewChat`.** It already calls `addActiveSession` and `setVisibleSessionId`. **However**, we need it to also push the new id into `openTabIds`. Update it (line 176-181):
    ```typescript
    const createNewChat = useCallback((): string => {
      const newId = generateSessionId()
      addActiveSession(newId, { skipHistoryRestore: true })
      setOpenTabIds((prev) => {
        if (prev.includes(newId)) return prev  // never going to happen, but be safe
        // No cap check here — createNewChat is the LAST-RESORT fallback when closeTab
        // empties the list; we MUST be able to seed a fresh tab even if the user
        // somehow had >=cap stale ids in localStorage. The next user-initiated
        // openTab will hit the cap normally.
        return [...prev, newId]
      })
      setVisibleSessionId(newId)
      return newId
    }, [addActiveSession, setVisibleSessionId])
    ```

    **Step 9 — Run all 12 tests** (4 from Plan 01 + 8 from Task 2):
    ```bash
    cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx
    ```
    All 12 must GREEN.

    **Step 10 — Run the chat panel tests** to confirm no regression in component-level wiring:
    ```bash
    cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx
    ```
    All 10+ tests still GREEN (4 pre-Phase-83 + 5 HOTFIX-01 + 1 HOTFIX-06 from Plan 01).

    **Step 11 — Lint + tsc:**
    ```bash
    cd frontend && npx eslint src/contexts/SessionControlContext.tsx
    cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep SessionControlContext
    ```
    Both clean.

    **Step 12 — Commit GREEN:**
    ```bash
    git add frontend/src/contexts/SessionControlContext.tsx frontend/src/contexts/ChatSessionContext.tsx
    git commit -m "feat(88-02): wire openTab/closeTab/persist/tier-cap (FEATURE-MULTI-SESSION-TABS)"
    ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx src/components/chat/ChatInterface.test.tsx</automated>
  </verify>
  <done>
    All 12 tests in SessionControlContext.test.tsx GREEN (4 from Plan 01 + 8 from this plan). All 10+ ChatInterface.test.tsx tests still GREEN. `selectChat` rewritten to delegate to `openTab`. `createNewChat` updated to push into `openTabIds`. `tabCap` lives as `useState` in `SessionControlProvider` (default 5); `useSubscription` is called ONLY inside `useChatSession()` in `ChatSessionContext.tsx` and pushes the tier-derived cap into the provider via `setTabCap`. Lint + tsc clean. GREEN commit message: `feat(88-02): wire openTab/closeTab/persist/tier-cap (FEATURE-MULTI-SESSION-TABS)`.
  </done>
</task>

<task type="auto">
  <name>Task 4: Full vitest + lint pass + SUMMARY</name>
  <files>.planning/phases/88-chat-and-workspace-persistence/88-02-tab-state-SUMMARY.md</files>
  <action>
    1. **Full frontend suite**: `cd frontend && npm test`. Must be GREEN.

    2. **Lint**: `cd frontend && npm run lint`. No new warnings.

    3. **TypeScript**: `cd frontend && npx tsc --noEmit -p tsconfig.json`. Clean for the 3 modified files.

    4. **Manual UAT script** (record in SUMMARY for the phase gate):
       - Open browser dev-tools console. Watch `localStorage`.
       - Send a message in any persona. Observe `pikar_current_session_id` (existing) and `pikar_open_tab_ids` (new) both populated.
       - In the dev-tools console, type `JSON.parse(localStorage.getItem('pikar_open_tab_ids'))`. Should return an array of 1 string.
       - Click the `+` icon (existing button at ChatInterface.tsx:1167 — Plan 03 will replace this with a TabStrip but for Plan 02 verification it suffices). Observe a fresh session id added to `pikar_open_tab_ids`.
       - From the chat history dropdown (Clock icon), select an older session. Observe its id appended to `pikar_open_tab_ids` (NOT replacing — adding).
       - Repeat until 5 tabs are open (free tier). The 6th attempt via the `+` icon — Plan 03 will surface a toast; for Plan 02 the cap rejection is observable only via the browser console (`[SessionControl] selectChat hit tab cap...`).
       - Refresh the browser. Confirm `pikar_open_tab_ids` is restored unchanged. The chat panel still shows whichever tab was visible.

    5. **Write SUMMARY.md** at the path in <files>. Cover:
       - **State machine added:** openTabIds, tabCap (useState in provider), setTabCap, openTab, closeTab.
       - **Persistence:** new localStorage key `pikar_open_tab_ids` (JSON-encoded string[]).
       - **Tier derivation (provider-tree mismatch fix):** Provider defaults `tabCap` to `TAB_CAP_FREE = 5`. `useChatSession()` (called only inside dashboard tree where `SubscriptionProvider` is mounted) reads tier and pushes `setTabCap(tier === 'free' ? 5 : 8)` via `useEffect`. NO `useSubscription()` call inside `SessionControlContext.tsx` — that would throw because `SubscriptionProvider` lives at `/dashboard/layout.tsx`, a child of the root layout where `SessionControlProvider` is mounted.
       - **Transient-write note:** The closeTab→createNewChat sequence transiently writes `[]` to `pikar_open_tab_ids` between the two `setOpenTabIds` updaters, then `[newId]`. This is acceptable today because `pikar_open_tab_ids` does NOT have a cross-tab `storage` event listener (only `pikar_current_session_id` has one — Plan 88-01 scope). If a future phase adds cross-tab sync for open tabs, the writes need to be unified (e.g., `flushSync` or a single combined reducer).
       - **selectChat rewrite:** now delegates to openTab — opening from history dropdown produces a tab.
       - **createNewChat update:** seeds the new id into openTabIds.
       - **Truth-to-code map:** each of the 6 must_haves.truths to source line range.
       - **Out-of-scope deferrals:** TabStrip UI rendering (Plan 03), streaming-tab indicator (Plan 04), max-tab toast (Plan 04, will live in TabStrip onClick handler), drag-to-reorder (out of phase entirely).
       - **PR-reviewer note:** Frontend-only plan; backend tests not required.
       - **Executor halt criteria (WARNING 4):** Halt and notify if any single task's vitest run exceeds 5 minutes wall-clock OR any single task's diff exceeds 15 files. The plan is dense; defensive halts protect quality.
       - **Manual UAT script** (the 7-step script above).
  </action>
  <verify>
    <automated>cd frontend && npm test && cd frontend && npm run lint</automated>
  </verify>
  <done>
    Full vitest suite GREEN. Frontend lint clean. TypeScript compile clean. SUMMARY.md exists at `.planning/phases/88-chat-and-workspace-persistence/88-02-tab-state-SUMMARY.md`. Manual UAT script captured for phase gate review.
  </done>
</task>

</tasks>

<verification>
**Per-task automated verification:**

| Task | Command | Maps To |
|------|---------|---------|
| 1 (Stub) | `cd frontend && npx tsc --noEmit -p tsconfig.json` (no errors on the 2 files) | Interface contract |
| 2 (RED) | `cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx -t "multi-session tabs"` (all 8 FAIL) | RED gate |
| 3 (GREEN) | `cd frontend && npx vitest run src/contexts/__tests__/SessionControlContext.test.tsx` (all 12 PASS) | GREEN gate |
| 4 (Suite) | `cd frontend && npm test` + `npm run lint` | Phase gate |

**Behavior assertions covering FEATURE-MULTI-SESSION-TABS criteria 6, 7, 10:**
- Tests 6, 7, 8 → criterion 6 (concurrent tabs)
- Tests 9, 14 → criterion 7 (persist via pikar_open_tab_ids)
- Tests 11, 12, 13 → criterion 10 (close removes from open set + activeSessions, NOT from DB)
- Test 10 → cap enforcement (locked decision: 5 free / 8 paid)

Criteria 8 (tab switching swaps workspace), 9 (streaming indicator), 11 (TabStrip supersedes `+` icon) are intentionally NOT covered here — they require the TabStrip UI from Plan 03.
</verification>

<success_criteria>
- All 12 vitest tests in `SessionControlContext.test.tsx` pass (4 from Plan 01 + 8 from Plan 02).
- `useChatSession()` exposes `openTabIds`, `tabCap`, `openTab`, `closeTab` so Plan 03 can consume them with no further context plumbing.
- localStorage round-trip for `pikar_open_tab_ids` works across reload.
- Cap enforcement is a thrown `TabCapReachedError` with `error.cap` available for the caller (Plan 03 TabStrip will catch and toast).
- Closing the last open tab auto-creates a fresh chat — never leaves the chat panel empty (locked decision honored).
- `selectChat` rewrite means existing history-dropdown clicks produce tab pills automatically — Plan 03 doesn't need to change the dropdown handler.
</success_criteria>

<output>
After completion, create `.planning/phases/88-chat-and-workspace-persistence/88-02-tab-state-SUMMARY.md` documenting:
1. **State machine added:** openTabIds, tabCap, openTab, closeTab, TabCapReachedError.
2. **Persistence key added:** `pikar_open_tab_ids` (JSON-encoded string[]).
3. **Tier derivation:** useSubscription.tier → 5 (free) / 8 (paid).
4. **selectChat behavior change:** now creates a tab pill (delegates to openTab).
5. **createNewChat behavior change:** now appends new id to openTabIds.
6. **Truth-to-code map** (6 truths to line ranges).
7. **Out-of-scope deferrals:** TabStrip UI (Plan 03), streaming indicator (Plan 04), max-tab toast (Plan 04).
8. **PR-reviewer note:** Frontend-only; backend tests not required.
9. **Manual UAT script** (7 steps via dev-tools localStorage observation).
</output>
</content>
</invoke>