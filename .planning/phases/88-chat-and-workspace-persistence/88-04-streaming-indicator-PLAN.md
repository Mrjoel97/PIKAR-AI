---
phase: 88-chat-and-workspace-persistence
plan: 04
type: execute
wave: 4
depends_on:
  - "88-03"
files_modified:
  - frontend/src/components/chat/TabStrip.tsx
  - frontend/src/components/chat/TabStrip.test.tsx
  - frontend/src/components/chat/ChatInterface.tsx
  - frontend/src/components/chat/ChatInterface.test.tsx
  - frontend/src/contexts/SessionControlContext.tsx
autonomous: true
requirements:
  - FEATURE-MULTI-SESSION-TABS
must_haves:
  truths:
    - "A non-active tab whose `activeSessions[id].status === 'streaming'` displays a small animated dot (teal, pulsing) on its pill"
    - "When a non-active streaming session emits a final message and transitions to `idle`, the dot becomes a static 'unread' badge until the user clicks the tab"
    - "Clicking the streaming/unread tab clears the indicator. Click -> openTab -> setVisibleSessionId(id); the pre-shipped useEffect at ChatInterface.tsx:785-792 (keyed on visibleSessionId) then clears hasUnread via updateSessionState. Plan 88-04 does NOT add a duplicate clear in handleTabSwitch -- the existing wiring is sufficient (defense-in-depth NOT needed)."
    - "Attempting to open a tab when at cap surfaces a `sonner` toast: 'Tab limit reached ({cap}). Close a tab to open a new one.' — no thrown error reaches the user"
    - "The active tab NEVER shows a streaming dot or unread badge — by definition the user is watching it"
    - "TabStrip exposes an `indicators: Record<string, 'streaming' | 'unread' | 'none'>` prop so the upstream wiring (ChatInterface) decides what each tab's state is — keeps TabStrip stateless and unit-testable"
  artifacts:
    - path: "frontend/src/components/chat/TabStrip.tsx"
      provides: "New `indicators` prop + dot/badge rendering on non-active tabs; renders nothing for the active tab"
      contains: "indicators"
    - path: "frontend/src/components/chat/TabStrip.test.tsx"
      provides: "3 new tests covering streaming dot, unread badge, active-tab clear"
      contains: "indicators"
    - path: "frontend/src/components/chat/ChatInterface.tsx"
      provides: "indicators map computed from useSessionMap().activeSessions; max-tab catch-and-toast wrapper around onNewChat"
      contains: "indicators"
    - path: "frontend/src/components/chat/ChatInterface.test.tsx"
      provides: "2 new tests: cap-toast firing + indicator wiring through ChatInterface → TabStrip"
      contains: "Tab limit reached"
  key_links:
    - from: "ChatInterface indicators useMemo"
      to: "useSessionMap().activeSessions"
      via: "for each id in openTabIds: lookup session.status + session.hasUnread; emit 'streaming' | 'unread' | 'none'; force 'none' when id === visibleSessionId"
      pattern: "activeSessions\\.get\\("
    - from: "TabStrip onNew handler"
      to: "sonner toast.error('Tab limit reached...')"
      via: "ChatInterface wraps onNewChat with try/catch on TabCapReachedError; on catch, shows toast"
      pattern: "TabCapReachedError"
    - from: "Active tab click"
      to: "updateSessionState(id, { hasUnread: false }) via existing useEffect at ChatInterface.tsx:785-792"
      via: "openTab updates visibleSessionId; the pre-shipped useEffect (Phase 83) keyed on visibleSessionId already runs updateSessionState({ hasUnread: false }). Plan 88-04 does NOT add a duplicate clear in handleTabSwitch."
      pattern: "hasUnread: false"
---

<objective>
Polish the multi-session tab feature with the two remaining ROADMAP success criteria for Phase 88:

- **Criterion 9** — non-active tabs that are streaming or recently finished show an indicator (animated dot for streaming, static badge for unread).
- **User-facing cap message** — when the user hits the tab cap, a `sonner` toast surfaces the limit cleanly. (Plan 03 left this as a `disabled` button + tooltip; Plan 04 adds the toast for explicit feedback when the user clicks the disabled state OR when `selectChat` from the history dropdown hits the cap.)

Purpose: FEATURE-MULTI-SESSION-TABS — the polish that turns "the feature works" into "the feature feels finished." Without these indicators, users miss the fact that a background tab finished streaming. Without the cap toast, the cap silently rejects without explaining why.

Output: ~30 lines added in `TabStrip.tsx` (indicators prop + dot/badge JSX), ~30 lines added in `ChatInterface.tsx` (indicators useMemo + cap-toast wrapper), 5 new behavior tests across two test files.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/88-chat-and-workspace-persistence/88-03-tab-strip-ui-SUMMARY.md

# Source under modification
@frontend/src/components/chat/TabStrip.tsx
@frontend/src/components/chat/TabStrip.test.tsx
@frontend/src/components/chat/ChatInterface.tsx
@frontend/src/components/chat/ChatInterface.test.tsx

# Reference (DO NOT modify in this plan)
@frontend/src/contexts/SessionMapContext.tsx
@frontend/src/contexts/SessionControlContext.tsx
@frontend/src/types/session.ts
@frontend/src/hooks/useBackgroundStream.ts

<interfaces>
<!-- ActiveSessionState already has the fields we need (frontend/src/types/session.ts:7-24) -->
```typescript
export type SessionStatus = 'idle' | 'streaming' | 'error' | 'interrupted'

export interface ActiveSessionState {
  sessionId: string
  messages: Message[]
  status: SessionStatus
  abortController: AbortController | null
  hasUnread: boolean       // <-- ALREADY EXISTS — this plan starts setting it from the indicator wiring
  lastUpdatedAt: number
  // ...
}
```

<!-- useSessionMap exposes activeSessions (Map<string, ActiveSessionState>) -->
<!-- (frontend/src/contexts/SessionMapContext.tsx:35-36) -->
```typescript
activeSessions: Map<string, ActiveSessionState>
updateSessionState: (sessionId: string, updates: Partial<ActiveSessionState>) => void
```

<!-- TabStrip extension contract -->
```typescript
// New prop on TabStripProps (added to existing interface):
indicators?: Record<string, 'streaming' | 'unread' | 'none'>
// Default to 'none' when prop is absent or id not in map.
```

<!-- TabCapReachedError export (from Plan 88-02) — re-imported in ChatInterface for the cap-toast wrapper -->
```typescript
import { TabCapReachedError } from '@/contexts/SessionControlContext'
```

<!-- sonner toast usage pattern (existing codebase convention, e.g. WorkflowBuilder.tsx:180) -->
```typescript
import { toast } from 'sonner'
toast.error('Tab limit reached (5). Close a tab to open a new one.')
```

<!-- useBackgroundStream sets status:'streaming' on startStream (line 156-160) and status:'idle' on stopStream (line 106-109). -->
<!-- It does NOT currently set hasUnread when a non-visible session finishes. Plan 04 adds this hook in -->
<!-- ChatInterface (NOT in useBackgroundStream — keeping the hook unchanged is safer; the wiring lives at the consumer). -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend TabStrip with indicators prop + RED tests</name>
  <files>frontend/src/components/chat/TabStrip.tsx, frontend/src/components/chat/TabStrip.test.tsx</files>
  <behavior>
    3 new tests in `TabStrip.test.tsx`. ALL RED until the component is updated within this same task (then GREEN — the component edits and the tests are atomic):

    - **Test 7 — "renders streaming dot on non-active streaming tab"**: pass `tabs=[{id:'a',label:'A',isActive:false},{id:'b',label:'B',isActive:true}]`, `indicators={a:'streaming'}`; assert a streaming-dot element is rendered inside the 'A' pill (queryable via `screen.getByTestId('tab-indicator-a')`) AND that `screen.queryByTestId('tab-indicator-b')` returns null (active tab never shows indicator). Maps to criterion 9.

    - **Test 8 — "renders unread badge on non-active recently-finished tab"**: pass `indicators={a:'unread'}`; assert the indicator element has different styling than streaming (e.g. solid teal dot, not pulsing). Use className substring check: streaming includes `animate-pulse`, unread does NOT.

    - **Test 9 — "indicators absent or 'none' renders no indicator element"**: pass `indicators={a:'none'}`; assert `screen.queryByTestId('tab-indicator-a')` is null. Same with `indicators={}` (omitted).
  </behavior>
  <action>
    1. **Edit `frontend/src/components/chat/TabStrip.tsx`** — extend the interface and rendering:

       **Step 1a — Add to `TabStripProps`:**
       ```typescript
       export interface TabStripProps {
         tabs: TabStripTab[]
         activeId: string | null
         cap: number
         onSwitch: (id: string) => void
         onClose: (id: string) => void
         onNew: () => void
         className?: string
         /**
          * Per-tab activity state. Keys are session ids; values describe what
          * the tab pill should display when NOT active. The active tab never
          * shows an indicator regardless of this map.
          *  - 'streaming' → animated pulsing dot (background SSE active).
          *  - 'unread' → solid dot (recent finish, not yet viewed).
          *  - 'none' or absent → no indicator.
          */
         indicators?: Record<string, 'streaming' | 'unread' | 'none'>
       }
       ```

       **Step 1b — Inside the tabs.map() rendering, before the close X button, add the indicator JSX:**
       ```tsx
       {(() => {
         if (tab.isActive) return null  // active tab never shows indicator
         const state = indicators?.[tab.id] ?? 'none'
         if (state === 'none') return null
         const dotClass = state === 'streaming'
           ? 'w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse'
           : 'w-1.5 h-1.5 rounded-full bg-teal-500'
         return (
           <span
             data-testid={`tab-indicator-${tab.id}`}
             className={dotClass}
             aria-label={state === 'streaming' ? 'Streaming' : 'New activity'}
             role="status"
           />
         )
       })()}
       ```
       Place this between the label `<button>` and the close `<button>` so visual order is: `[label] [indicator] [×]`.

       **Step 1c — Destructure `indicators` from props** at the top of the function:
       ```typescript
       export function TabStrip({
         tabs,
         activeId,
         cap,
         onSwitch,
         onClose,
         onNew,
         className,
         indicators,
       }: TabStripProps) {
       ```

    2. **Add 3 tests to `frontend/src/components/chat/TabStrip.test.tsx`** at the bottom of the existing describe block (or in a new sub-describe `indicators`):

       ```typescript
       describe('TabStrip — indicators (FEATURE-MULTI-SESSION-TABS criterion 9)', () => {
         it('renders streaming dot on non-active streaming tab', () => {
           render(
             <TabStrip
               tabs={baseTabs}
               activeId="b"
               cap={5}
               onSwitch={vi.fn()}
               onClose={vi.fn()}
               onNew={vi.fn()}
               indicators={{ a: 'streaming' }}
             />,
           )
           const dot = screen.getByTestId('tab-indicator-a')
           expect(dot).toBeTruthy()
           expect(dot.className).toMatch(/animate-pulse/)
           // Active tab b: no indicator regardless
           expect(screen.queryByTestId('tab-indicator-b')).toBeNull()
         })

         it('renders solid badge on non-active unread tab (no pulse)', () => {
           render(
             <TabStrip
               tabs={baseTabs}
               activeId="b"
               cap={5}
               onSwitch={vi.fn()}
               onClose={vi.fn()}
               onNew={vi.fn()}
               indicators={{ a: 'unread' }}
             />,
           )
           const dot = screen.getByTestId('tab-indicator-a')
           expect(dot).toBeTruthy()
           expect(dot.className).not.toMatch(/animate-pulse/)
         })

         it('renders no indicator when state is none or absent', () => {
           const { rerender } = render(
             <TabStrip
               tabs={baseTabs}
               activeId="b"
               cap={5}
               onSwitch={vi.fn()}
               onClose={vi.fn()}
               onNew={vi.fn()}
               indicators={{ a: 'none' }}
             />,
           )
           expect(screen.queryByTestId('tab-indicator-a')).toBeNull()

           rerender(
             <TabStrip
               tabs={baseTabs}
               activeId="b"
               cap={5}
               onSwitch={vi.fn()}
               onClose={vi.fn()}
               onNew={vi.fn()}
             />,
           )
           expect(screen.queryByTestId('tab-indicator-a')).toBeNull()
         })
       })
       ```

    3. **Run tests:**
       ```bash
       cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx
       ```
       All 9 tests GREEN (6 from Plan 03 + 3 new).

    4. **Lint + tsc:**
       ```bash
       cd frontend && npx eslint src/components/chat/TabStrip.tsx src/components/chat/TabStrip.test.tsx
       cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep TabStrip
       ```
       Both clean.

    5. **Commit:**
       ```bash
       git add frontend/src/components/chat/TabStrip.tsx frontend/src/components/chat/TabStrip.test.tsx
       git commit -m "feat(88-04): TabStrip indicators prop for streaming/unread dots (FEATURE-MULTI-SESSION-TABS)"
       ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx</automated>
  </verify>
  <done>
    TabStrip extended with `indicators` prop. 3 new tests GREEN. All 9 TabStrip tests GREEN. Active tab never shows indicator regardless of map content. Streaming uses `animate-pulse`, unread does not. Lint + tsc clean. Commit message: `feat(88-04): TabStrip indicators prop for streaming/unread dots (FEATURE-MULTI-SESSION-TABS)`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire indicators in ChatInterface + max-tab toast + RED tests</name>
  <files>frontend/src/components/chat/ChatInterface.tsx, frontend/src/components/chat/ChatInterface.test.tsx</files>
  <behavior>
    After this task:
    - `ChatInterface` computes `indicators: Record<string, 'streaming'|'unread'|'none'>` from `activeSessions` and `openTabIds`. Rule: active tab → 'none'; status === 'streaming' → 'streaming'; hasUnread === true (and not streaming) → 'unread'; otherwise 'none'.
    - When the user clicks the trailing `+` while at cap, the `disabled` button doesn't fire (Plan 03 already covered that). The new behavior: the SAME error path also fires from `selectChat` calls that hit the cap (e.g. opening a 6th session from the history dropdown). ChatInterface wraps `selectChat` (or its handler chain) with a try/catch that surfaces a `sonner` toast on `TabCapReachedError`.
    - When the user clicks an unread/streaming tab, the click clears `hasUnread` for that session via `updateSessionState(id, { hasUnread: false })`.

    2 new tests in `ChatInterface.test.tsx`:

    - **Test 9 (HOTFIX-06 / FEATURE describe)**: render harness with `sessionMap.activeSessions = new Map([['s1', { sessionId:'s1', messages:[], status:'streaming', hasUnread:false, abortController:null, lastUpdatedAt:Date.now(), scrollTop:-1, rawWidgets:[], pendingActions:[] }]])`, `sessionControl.openTabIds=['s1','s2']`, `visibleSessionId='s2'`, sessions=[…both]; assert `screen.getByTestId('tab-indicator-s1')` exists with `animate-pulse`; assert `screen.queryByTestId('tab-indicator-s2')` is null.

    - **Test 10**: mock `sonner` (`vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() } }))`); render harness with `sessionControl.tabCap=2`, `openTabIds=['s1','s2']`. Programmatically invoke the cap-fail path. The cleanest way to do this from a test is to override `sessionControl.openTab` to be a function that throws `TabCapReachedError`, then trigger an action that calls `selectChat` (e.g. open the history dropdown and click an entry). Since the harness mocks `useSessionControl`, any wrapper logic in ChatInterface that catches and toasts is testable. **Specific assertion**: import the mocked toast and assert `toast.error` was called with a message matching `/Tab limit reached.*2/`. Maps to locked decision "max-tab toast".
  </behavior>
  <action>
    **Step 1 — Edit `frontend/src/components/chat/ChatInterface.tsx`.**

    **1a — Add the sonner import** at the top with other imports:
    ```typescript
    import { toast } from 'sonner'
    import { TabCapReachedError } from '@/contexts/SessionControlContext'
    ```

    **1b — Pull `activeSessions` from useSessionMap** (extending the existing destructure from Plan 88-03). Note we do NOT need `updateSessionState` here — the existing useEffect at `ChatInterface.tsx:785-792` already clears `hasUnread` whenever `visibleSessionId` changes, so this plan does not introduce a duplicate clear:
    ```typescript
    const { sessions, activeSessions } = useSessionMap()
    ```

    **1c — Compute the `indicators` map.** Place this `useMemo` near the existing `tabs` useMemo:
    ```typescript
    const indicators = useMemo<Record<string, 'streaming' | 'unread' | 'none'>>(() => {
      const result: Record<string, 'streaming' | 'unread' | 'none'> = {}
      for (const id of openTabIds) {
        if (id === visibleSessionId) {
          result[id] = 'none'
          continue
        }
        const session = activeSessions.get(id)
        if (!session) {
          result[id] = 'none'
          continue
        }
        if (session.status === 'streaming') {
          result[id] = 'streaming'
        } else if (session.hasUnread) {
          result[id] = 'unread'
        } else {
          result[id] = 'none'
        }
      }
      return result
    }, [openTabIds, visibleSessionId, activeSessions])
    ```

    **1d — Wrap `openTab` calls with cap-error toast handling.** The TabStrip's `onSwitch` and `onNew` props need to be safe-wrappers that catch `TabCapReachedError`. Add right after `indicators`:
    ```typescript
    const handleTabSwitch = useCallback(
      (id: string) => {
        try {
          openTab(id)
          // NOTE: hasUnread is already cleared by the existing useEffect at
          // ChatInterface.tsx:785-792 (keyed on `visibleSessionId`). When openTab
          // updates visibleSessionId, that effect fires and runs
          //   updateSessionState(visibleSessionId, { hasUnread: false, lastUpdatedAt: Date.now() })
          // We intentionally do NOT call updateSessionState here — that would be
          // a duplicate. Documented in 88-04-SUMMARY.md under "Indicator clear path".
        } catch (err) {
          if (err instanceof TabCapReachedError) {
            toast.error(`Tab limit reached (${err.cap}). Close a tab to open a new one.`)
          } else {
            throw err
          }
        }
      },
      [openTab],
    )

    const handleTabNew = useCallback(() => {
      // The TabStrip already disables the + button when at cap (Plan 03), so this
      // path normally won't fire at cap. But selectChat from the history dropdown
      // can still hit the cap — that path uses the same SessionControl.selectChat
      // which already catches internally (Plan 02 Task 3 step 7). The toast there
      // currently only console.warns; this plan upgrades it to a sonner toast by
      // wrapping the onNewChat prop too.
      try {
        if (onNewChat) {
          onNewChat()
        }
      } catch (err) {
        if (err instanceof TabCapReachedError) {
          toast.error(`Tab limit reached (${err.cap}). Close a tab to open a new one.`)
        } else {
          throw err
        }
      }
    }, [onNewChat])
    ```

    **1e — Update the `<TabStrip />` JSX from Plan 03** to use the new wrappers and pass `indicators`:
    ```tsx
    <TabStrip
      tabs={tabs}
      activeId={visibleSessionId}
      cap={tabCap}
      onSwitch={handleTabSwitch}
      onClose={closeTab}
      onNew={handleTabNew}
      indicators={indicators}
    />
    ```

    **1f — Upgrade `selectChat` cap handling.** SessionControlContext's `selectChat` (rewritten in Plan 02 Task 3 step 7) currently does `console.warn` on cap. We can ALSO upgrade that to a sonner toast for the history-dropdown path. **DO NOT** edit `SessionControlContext.tsx` to import sonner (that adds a UI dependency to the context layer — wrong direction). Instead: ChatInterface's `onSelectChat` prop is bound to `selectChat` from PersonaDashboardLayout. Wrap the dropdown click handler in ChatInterface to use the same try/catch.

    Locate the chat history dropdown click handler at line ~1202:
    ```tsx
    onClick={() => {
      onSelectChat?.(chat.id);
      setIsHistoryOpen(false);
    }}
    ```

    Replace with:
    ```tsx
    onClick={() => {
      try {
        onSelectChat?.(chat.id);
      } catch (err) {
        if (err instanceof TabCapReachedError) {
          toast.error(`Tab limit reached (${err.cap}). Close a tab to open a new one.`)
        } else {
          throw err
        }
      }
      setIsHistoryOpen(false);
    }}
    ```

    **However**, `onSelectChat` ultimately calls `selectChat` from useSessionControl, which (Plan 02 Task 3 step 7) already catches internally. To make the catch in this layer effective, we need to update `selectChat` in `SessionControlContext.tsx` to RETHROW the TabCapReachedError instead of swallowing with console.warn. This is a small Plan 02 amendment:

    **1f-amendment — Edit `SessionControlContext.tsx` selectChat (Plan 02 Task 3 step 7):**
    ```typescript
    const selectChat = useCallback(
      (sessionId: string) => {
        // Always rethrow TabCapReachedError so UI layer (Plan 04) can decide
        // how to surface it (sonner toast). Other errors propagate unchanged.
        openTab(sessionId)
      },
      [openTab],
    )
    ```
    The earlier `try/catch` with console.warn is removed entirely. Cap-rejection is now uniformly handled at the UI layer.

    **Step 2 — Add 2 tests to `ChatInterface.test.tsx`** in the existing FEATURE-MULTI-SESSION-TABS describe (or extend the "persistence (HOTFIX-06)" block — pick whichever describe makes more sense; the existing tests from Plan 03 are likely in the persistence block; add a new sibling describe `'ChatInterface — multi-session tabs polish (FEATURE-MULTI-SESSION-TABS)'` for clarity):

    ```typescript
    // Mock sonner at module scope (vi.mock hoists)
    vi.mock('sonner', () => ({
      toast: {
        error: vi.fn(),
        success: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
      },
    }))

    import { toast } from 'sonner'

    describe('ChatInterface — multi-session tabs polish (FEATURE-MULTI-SESSION-TABS)', () => {
      beforeEach(() => {
        vi.mocked(toast.error).mockClear()
      })

      it('renders streaming indicator on non-active streaming tab', () => {
        const streamingSession = {
          sessionId: 's1',
          messages: [],
          status: 'streaming' as const,
          abortController: null,
          hasUnread: false,
          lastUpdatedAt: Date.now(),
          scrollTop: -1,
          rawWidgets: [],
          pendingActions: [],
        }
        renderChatInterface({
          sessionControl: {
            openTabIds: ['s1', 's2'],
            visibleSessionId: 's2',
            tabCap: 5,
          },
          sessionMap: {
            sessions: [
              { id: 's1', title: 'Streaming chat', createdAt: '', updatedAt: '' },
              { id: 's2', title: 'Visible chat', createdAt: '', updatedAt: '' },
            ],
            activeSessions: new Map([['s1', streamingSession]]),
          },
        })
        const dot = screen.getByTestId('tab-indicator-s1')
        expect(dot).toBeTruthy()
        expect(dot.className).toMatch(/animate-pulse/)
        expect(screen.queryByTestId('tab-indicator-s2')).toBeNull()
      })

      it('shows sonner toast when openTab throws TabCapReachedError', () => {
        const openTab = vi.fn(() => {
          throw new TabCapReachedError(2)
        })
        renderChatInterface({
          sessionControl: {
            openTabIds: ['s1', 's2'],
            visibleSessionId: 's2',
            tabCap: 2,
            openTab,
          },
          sessionMap: {
            sessions: [
              { id: 's1', title: 'A', createdAt: '', updatedAt: '' },
              { id: 's2', title: 'B', createdAt: '', updatedAt: '' },
            ],
          },
        })
        // Click a different tab pill — handleTabSwitch wraps openTab, which throws.
        // The wrapper should catch and call toast.error.
        fireEvent.click(screen.getByTestId('tab-pill-s1'))
        expect(openTab).toHaveBeenCalledTimes(1)
        expect(toast.error).toHaveBeenCalledTimes(1)
        expect(vi.mocked(toast.error).mock.calls[0][0]).toMatch(/Tab limit reached \(2\)/)
      })
    })
    ```

    **Step 3 — Run all tests:**
    ```bash
    cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx src/components/chat/ChatInterface.test.tsx src/contexts/__tests__/SessionControlContext.test.tsx
    ```
    All tests GREEN. The Plan 02 SessionControlContext tests should still pass — the only change in `selectChat` is removing the try/catch (the underlying tests don't depend on it being caught silently).

    **Step 4 — Lint + tsc:**
    ```bash
    cd frontend && npx eslint src/components/chat/ChatInterface.tsx
    cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E "ChatInterface|SessionControlContext"
    ```
    Both clean.

    **Step 5 — Commit:**
    ```bash
    git add frontend/src/components/chat/ChatInterface.tsx \
            frontend/src/components/chat/ChatInterface.test.tsx \
            frontend/src/contexts/SessionControlContext.tsx
    git commit -m "feat(88-04): tab indicators wiring + sonner cap toast (FEATURE-MULTI-SESSION-TABS criteria 9 + cap UX)"
    ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx src/components/chat/ChatInterface.test.tsx src/contexts/__tests__/SessionControlContext.test.tsx</automated>
  </verify>
  <done>
    `indicators` useMemo computed in ChatInterface from activeSessions + visibleSessionId. `handleTabSwitch` wraps openTab with try/catch and clears hasUnread on click. `handleTabNew` wraps onNewChat with try/catch. Chat history dropdown click handler catches TabCapReachedError. SessionControlContext.tsx selectChat simplified — rethrows instead of console.warn. 2 new ChatInterface tests GREEN. All TabStrip tests still GREEN. All Plan 02 SessionControlContext tests still GREEN. Lint + tsc clean. Commit message: `feat(88-04): tab indicators wiring + sonner cap toast (FEATURE-MULTI-SESSION-TABS criteria 9 + cap UX)`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full vitest + lint pass + UAT script + final phase SUMMARY</name>
  <files>.planning/phases/88-chat-and-workspace-persistence/88-04-streaming-indicator-SUMMARY.md</files>
  <action>
    1. **Full frontend suite**: `cd frontend && npm test`. Must be GREEN. Aggregate test count after this phase: ~28+ Phase 88 tests across 4 test files (~9 TabStrip + ~5 SessionControlContext (4 from Plan 01 + 8 from Plan 02 + edits) + ~10 ChatInterface for Phase 88 + 9 from Phase 83 = ~32 chat-area tests total).

    2. **Lint**: `cd frontend && npm run lint`. No new warnings.

    3. **TypeScript**: `cd frontend && npx tsc --noEmit -p tsconfig.json`. Clean.

    4. **Backend impact**: ZERO backend files touched across all of Phase 88. `make test` is intentionally NOT in the verification chain. Document this clearly in the SUMMARY for PR reviewers.

    5. **End-to-end manual UAT script** for Phase 88 as a whole (covers all 11 ROADMAP success criteria):

       **Setup:**
       - `docker compose up -d` (backend + redis)
       - `cd frontend && npm run dev`
       - Open Chrome, navigate to `http://localhost:3000`, sign in.

       **Criteria 1, 2, 3 (Plan 88-01) — Persistence:**
       - Send a message in any persona. Note the session_id via dev-tools `localStorage.pikar_current_session_id`.
       - Click the workspace canvas to confirm any items render. Note the items.
       - Hard-refresh (Ctrl+F5). Confirm: same chat history visible, last agent response present, workspace re-renders the same items. ✅ criteria 1, 2.
       - Click `+` (the TabStrip's trailing + from Plan 03). Confirm: new session_id in `pikar_current_session_id`, workspace clears (no items). ✅ criterion 3.

       **Criterion 4 (Plan 88-01) — Cross-tab safety:**
       - Open a SECOND Chrome tab, sign-in already cached, navigate to the same URL. Confirm: same session restored.
       - In Tab B, click `+` (new chat). Confirm Tab B's URL/storage shows the new session.
       - Switch back to Tab A. Within ~1 second, confirm Tab A's `visibleSessionId` updates to match Tab B's new session (storage event listener firing). Workspace re-queries. ✅ criterion 4.

       **Criterion 5 (Plan 88-01) — History list:**
       - Click the Clock icon (chat history dropdown). Confirm: list shows all past sessions with title + preview + timestamp. ✅ criterion 5.

       **Criteria 6, 7, 11 (Plans 88-02, 88-03) — Multi-tab + persistence + + supersession:**
       - Open ~3 tabs by clicking `+` repeatedly (each becomes a new pill). Confirm `pikar_open_tab_ids` in dev-tools is `["session-...","session-...","session-..."]`.
       - Refresh the page. Confirm all 3 tabs restore as pills. ✅ criterion 7.
       - Confirm 3 tabs visible as pills in the TabStrip (✅ criterion 6).
       - Confirm there is NO standalone `+` icon at the right edge of the agent-identity row (the legacy one is gone). The only `+` is the TabStrip's trailing one. ✅ criterion 11.
       - Open ~5 tabs total (free tier). The 6th `+` click → toast: "Tab limit reached (5). Close a tab to open a new one." ✅ cap UX.

       **Criterion 8 (Plan 88-03) — Tab switch swaps workspace:**
       - With multiple tabs open, click each tab pill. Confirm each click swaps BOTH the chat view AND the workspace items. No workspace items leak between tabs (a session-2 item must NOT appear when session-1 is active). ✅ criterion 8.

       **Criterion 9 (Plan 88-04) — Streaming/unread indicator:**
       - With Tab A visible, click into Tab B. Send a message in Tab B. Click back to Tab A.
       - In Tab A's view, watch Tab B's pill: while Tab B is streaming, the pill should show a pulsing teal dot.
       - Wait for Tab B's stream to complete. The dot transitions to a solid (non-pulsing) badge. ✅ criterion 9.
       - Click Tab B. Confirm the indicator clears (the click sets hasUnread:false and Tab B becomes active so its `'none'` lookup wins).

       **Criterion 10 (Plan 88-02 + 88-03) — Close tab semantics:**
       - Click `×` on any non-last pill. Confirm: pill removed, the underlying session is NOT deleted (open chat history dropdown — it's still listed there).
       - Reopen the closed session via the dropdown. Confirm a new pill appears.
       - Close ALL tabs one by one. The last close should auto-create a fresh empty tab — chat panel never goes blank. ✅ criterion 10 + locked decision.

       **Failure paths:**
       - Stop the backend (`docker compose stop backend`). Refresh page. Confirm: localStorage restore still works (frontend-only), `refreshSessions` silently fails in console, but the chat panel mounts with the previously visible session and the open tabs intact. No crash.

    6. **Write final phase SUMMARY** at the path in <files>. This is Plan 04's SUMMARY. The phase-level recap (which the orchestrator will surface) should also note that all 11 criteria are now verified.

       SUMMARY content:
       - **What this plan added:** TabStrip indicators prop, ChatInterface indicators useMemo + handleTabSwitch/handleTabNew wrappers, sonner cap toast, history-dropdown error handling, SessionControlContext.selectChat simplified to rethrow.
       - **Indicator clear path (WARNING 3 documentation):** `handleTabSwitch` does NOT call `updateSessionState({ hasUnread: false })`. The pre-shipped useEffect at `ChatInterface.tsx:785-792` (added in Phase 83, keyed on `visibleSessionId`) handles unread clearing. When the user clicks a non-active tab, `handleTabSwitch` calls `openTab(id)` which calls `setVisibleSessionId(id)`; the visibleSessionId-keyed useEffect then runs `updateSessionState(visibleSessionId, { hasUnread: false, lastUpdatedAt: Date.now() })`. Plan 88-04 leverages the existing wiring rather than introducing a defense-in-depth duplicate.
       - **Executor halt criteria (WARNING 4):** Halt and notify if any single task's vitest run exceeds 5 minutes wall-clock OR any single task's diff exceeds 15 files. The plan is dense (4-5 files modified across two layers).
       - **Tests added:** 3 TabStrip + 2 ChatInterface = 5 new tests.
       - **End-to-end manual UAT script** (the script from action #5).
       - **Phase 88 success-criteria coverage matrix:**
         | Criterion | Plan | Coverage |
         |-----------|------|----------|
         | 1. Reload restores chat | 88-01 | Test 1, 5 (auto) + manual UAT |
         | 2. Workspace restores | 88-01 | Manual UAT (already shipped wiring) |
         | 3. New chat resets | 88-01 | Test 3 (auto) + manual UAT |
         | 4. Cross-tab safety | 88-01 | Test 4 (auto) + manual UAT |
         | 5. History list | 88-01 | Manual UAT (existing /sessions tests cover the data layer) |
         | 6. Multi-tab open | 88-02, 88-03 | Tests 6, 7, 10 (auto) + manual UAT |
         | 7. Tabs persist | 88-02 | Tests 9, 14 (auto) + manual UAT |
         | 8. Tab switch swaps workspace | 88-03 | Test 8 (chain documented) + manual UAT |
         | 9. Streaming indicator | 88-04 | Tests 7, 8, 9 (TabStrip) + Test 9 (ChatInterface) (auto) + manual UAT |
         | 10. Close tab keeps session | 88-02, 88-03 | Tests 11, 13 (auto) + manual UAT |
         | 11. TabStrip supersedes + icon | 88-03 | Test 7 (auto) + manual UAT |
       - **Production code delta total for Phase 88:** ~12 lines storage listener (88-01), ~80 lines tab state (88-02), ~120 lines TabStrip + ~10 lines ChatInterface header restructure (88-03), ~30 lines indicators wiring + ~15 lines toasts (88-04). **~270 lines added; near-zero subtractions.** Single-feature, easy to revert if needed.
       - **PR-reviewer note:** Phase 88 is FRONTEND-ONLY. Zero backend Python files touched. Backend `make test` is not in the verification chain.
       - **Out-of-scope items deferred to future phases (per locked decisions):** drag-to-reorder, mobile tab UI, BroadcastChannel cross-tab sync (storage event covers it), side-by-side workspace split.
  </action>
  <verify>
    <automated>cd frontend && npm test && cd frontend && npm run lint</automated>
  </verify>
  <done>
    Full vitest suite GREEN. Frontend lint clean. TypeScript compile clean. SUMMARY.md exists at `.planning/phases/88-chat-and-workspace-persistence/88-04-streaming-indicator-SUMMARY.md` with the full 11-criteria coverage matrix and end-to-end manual UAT script. Phase 88 ROADMAP success criteria are all verified.
  </done>
</task>

</tasks>

<verification>
**Per-task automated verification:**

| Task | Command | Maps To |
|------|---------|---------|
| 1 (TabStrip indicators) | `cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx` (9 PASS) | Criterion 9 component layer |
| 2 (Wiring + toast) | `cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx src/components/chat/ChatInterface.test.tsx src/contexts/__tests__/SessionControlContext.test.tsx` (all PASS) | Criterion 9 + cap UX |
| 3 (Suite) | `cd frontend && npm test` + `npm run lint` | Phase gate |

**Behavior assertions covering FEATURE-MULTI-SESSION-TABS criterion 9 + cap UX:**
- TabStrip Test 7 (streaming dot) → criterion 9 streaming case
- TabStrip Test 8 (unread badge) → criterion 9 finished-but-unviewed case
- TabStrip Test 9 (no indicator when 'none') → criterion 9 negative case
- ChatInterface Test 9 (streaming wiring through useMemo + activeSessions) → criterion 9 integration
- ChatInterface Test 10 (sonner cap toast) → cap UX (locked decision)

This plan completes Phase 88's automated coverage. Criteria 1-3 + 5 (Plan 88-01) and criterion 8 (Plan 88-03) round out the 11-criteria matrix when combined with the manual UAT script in this plan's SUMMARY.
</verification>

<success_criteria>
- TabStrip's `indicators` prop renders pulsing dot for streaming, solid dot for unread, nothing for active or 'none'.
- ChatInterface computes `indicators` from `activeSessions` × `openTabIds` × `visibleSessionId` — active tab forced to 'none'.
- Clicking a tab clears `hasUnread` for that session via `updateSessionState`.
- Hitting the tab cap surfaces a `sonner` toast (`toast.error('Tab limit reached (N). Close a tab to open a new one.')`) — both from the TabStrip `+` flow AND the chat-history-dropdown selectChat flow.
- `SessionControlContext.selectChat` no longer console.warns on cap — it rethrows so the UI layer can decide presentation.
- All 11 ROADMAP success criteria for Phase 88 are now achievable end-to-end through the test suite + manual UAT script combo.
- Total Phase 88 production-code footprint: ~270 lines added, ~5 lines deleted (the legacy `+` button + the console.warn line in selectChat).
</success_criteria>

<output>
After completion, create `.planning/phases/88-chat-and-workspace-persistence/88-04-streaming-indicator-SUMMARY.md` documenting:
1. **What this plan added:** TabStrip indicators prop, ChatInterface indicators useMemo + handleTabSwitch/handleTabNew, sonner cap toast, history-dropdown error catch, SessionControlContext.selectChat rethrow.
2. **Tests added:** 3 TabStrip + 2 ChatInterface = 5 total.
3. **Phase 88 success-criteria coverage matrix** (all 11 criteria mapped to plans + tests + manual UAT).
4. **End-to-end manual UAT script** covering all 11 criteria across all 4 plans.
5. **Phase 88 production-code footprint:** ~270 lines added (12+80+130+45 across 4 plans), ~5 lines deleted. Frontend-only.
6. **PR-reviewer note:** Frontend-only phase; no backend Python changes; backend tests not required.
7. **Out-of-scope deferrals:** drag-reorder, mobile tab UI, BroadcastChannel, workspace split.
</output>
</content>
</invoke>