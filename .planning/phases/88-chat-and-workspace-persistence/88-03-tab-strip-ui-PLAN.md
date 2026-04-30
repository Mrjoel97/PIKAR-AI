---
phase: 88-chat-and-workspace-persistence
plan: 03
type: execute
wave: 3
depends_on:
  - "88-02"
files_modified:
  - frontend/src/components/chat/TabStrip.tsx
  - frontend/src/components/chat/TabStrip.test.tsx
  - frontend/src/components/chat/ChatInterface.tsx
  - frontend/src/components/chat/__test-utils__/chatHarness.ts
  - frontend/src/components/chat/ChatInterface.test.tsx
autonomous: true
requirements:
  - FEATURE-MULTI-SESSION-TABS
must_haves:
  truths:
    - "ChatInterface header renders a horizontal TabStrip (one pill per id in openTabIds) instead of a bare `+` icon"
    - "Each tab pill shows a label derived from the matching ChatSession (sessions[].title with preview fallback) and a close `×` button"
    - "Clicking a pill switches the visible tab — calls openTab(id) which updates visibleSessionId and the workspace re-queries on the new id"
    - "Clicking the `×` on a pill calls closeTab(id) — pill disappears, list re-orders, last-tab fallback creates a fresh chat"
    - "Trailing `+` button after the last pill creates a fresh tab via createNewChat (preserves the existing onNewChat affordance, just with better discoverability)"
    - "When openTabIds.length >= tabCap, the trailing `+` is disabled (greyed) AND clicking it shows a transient inline message — no thrown error reaches the user"
    - "Active tab pill has visually distinct styling (teal background, bold label) so the user knows which one they're viewing"
    - "The tiny `+` icon previously at ChatInterface.tsx:~1167 is removed — the TabStrip's trailing `+` is the canonical new-chat affordance"
  artifacts:
    - path: "frontend/src/components/chat/TabStrip.tsx"
      provides: "Stateless TabStrip presentation component — receives tabs, activeId, cap, callbacks via props; renders pills + trailing + button"
      contains: "export function TabStrip"
      min_lines: 80
    - path: "frontend/src/components/chat/TabStrip.test.tsx"
      provides: "Vitest behavior tests for TabStrip — render, click switches, close removes, cap disables +, active styling"
      contains: "TabStrip"
    - path: "frontend/src/components/chat/ChatInterface.tsx"
      provides: "Header now renders <TabStrip /> wired to useSessionControl + useSessionMap; old `+` button removed"
      contains: "<TabStrip"
  key_links:
    - from: "ChatInterface.tsx header"
      to: "<TabStrip /> component"
      via: "props: tabs (derived from openTabIds + sessions), activeId (visibleSessionId), cap (tabCap), onSwitch (openTab), onClose (closeTab), onNew (createNewChat)"
      pattern: "<TabStrip"
    - from: "TabStrip onSwitch handler"
      to: "openTab(id) from useSessionControl"
      via: "passed via prop; openTab handles the existing addActiveSession + setVisibleSessionId chain"
      pattern: "onSwitch=\\{openTab\\}"
    - from: "TabStrip onClose handler"
      to: "closeTab(id) from useSessionControl"
      via: "passed via prop; closeTab handles list removal + activeSessions cleanup + last-tab fallback"
      pattern: "onClose=\\{closeTab\\}"
    - from: "Workspace coupling (verification only — already wired)"
      to: "ActiveWorkspace re-queries on currentSessionId change"
      via: "openTab calls setVisibleSessionId, which propagates to PersonaDashboardLayout's currentSessionId, which is the dependency in ActiveWorkspace.tsx:357-359 useEffect"
      pattern: "useEffect\\(\\(\\) => \\{[^}]*\\}, \\[currentSessionId\\]\\)"
---

<objective>
Render the multi-session tab UI in `ChatInterface.tsx` header. Plan 02 built the state machine; this plan builds the visual layer that consumes it. Replaces the existing tiny `+` icon (at line ~1167) with a horizontal TabStrip showing one pill per open tab plus a trailing `+` button.

Workspace coupling (criterion 8) is a verification-only concern in this plan — it's already wired through `ActiveWorkspace.tsx:357-359`'s `useEffect(..., [currentSessionId])`. We add a behavior test to lock that wiring in place against future regressions.

Purpose: FEATURE-MULTI-SESSION-TABS — the discoverable surface. Without this UI, the state from Plan 02 is invisible to users.

Output: New file `TabStrip.tsx` (~120 lines, stateless presentation), new file `TabStrip.test.tsx` (~150 lines, 6 behavior tests), edits to `ChatInterface.tsx` (replace ~10 lines of header markup, remove the old `+` button), harness extension for `useSessionMap.sessions` so ChatInterface tests can seed tab labels, one new ChatInterface integration test confirming TabStrip → workspace coupling.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/88-chat-and-workspace-persistence/88-02-tab-state-SUMMARY.md

# Source under modification
@frontend/src/components/chat/ChatInterface.tsx
@frontend/src/components/chat/__test-utils__/chatHarness.ts
@frontend/src/components/chat/ChatInterface.test.tsx

# Reference (DO NOT modify in this plan)
@frontend/src/contexts/SessionControlContext.tsx
@frontend/src/contexts/SessionMapContext.tsx
@frontend/src/components/dashboard/PersonaDashboardLayout.tsx
@frontend/src/components/dashboard/ActiveWorkspace.tsx

<interfaces>
<!-- TabStrip props contract — define here so the executor implements against a known shape. -->

```typescript
// frontend/src/components/chat/TabStrip.tsx (NEW)
export interface TabStripTab {
  id: string             // session_id
  label: string          // session.title or first-line of session.preview, truncated to ~24 chars
  isActive: boolean      // true when id === activeId
}

export interface TabStripProps {
  tabs: TabStripTab[]
  activeId: string | null
  cap: number
  /** Called when user clicks a pill (not the close X). */
  onSwitch: (id: string) => void
  /** Called when user clicks the X on a pill. Implementer guarantees last-tab fallback. */
  onClose: (id: string) => void
  /** Called when user clicks the trailing + button. Disabled when tabs.length >= cap. */
  onNew: () => void
  /** Optional className passthrough for layout containers. */
  className?: string
}

export function TabStrip(props: TabStripProps): JSX.Element
```

<!-- ChatInterface header location to modify (frontend/src/components/chat/ChatInterface.tsx:1143-1173) -->
<!-- The TabStrip replaces the `<button onClick={onNewChat}>` block at lines 1167-1173. -->
<!-- The Clock (history) and MoreVertical (more options) icons stay at lines 1175-1290. -->

```tsx
// CURRENT header at line 1143-1173:
<div className="bg-slate-50/60 p-2 border-b border-slate-100/80 flex items-center gap-2">
  <div className="w-6 h-6 rounded-full ...">{agentName?.charAt(0).toUpperCase() ?? <Bot />}</div>
  <div className="flex-1">
    <h3>{agentName || 'Pikar AI'}</h3>
    <p>{agentName ? 'Personal Agent' : 'Executive Assistant & Orchestrator'}</p>
  </div>
  {onlineUsers.length > 1 && (<div>...{onlineUsers.length} online</div>)}
  <div className="flex items-center gap-1">
    <button onClick={onNewChat} title="New Chat"><Plus size={14} /></button>  {/* <-- DELETE this block */}
    <div ref={historyRef}>...history dropdown...</div>
    <div ref={moreOptionsRef}>...more options dropdown...</div>
  </div>
</div>

// AFTER this plan: TabStrip lives BELOW the existing header bar (so it has full width
// and the agent identity stays in its own row). Two-row header.
<div className="border-b border-slate-100/80">
  <div className="bg-slate-50/60 p-2 flex items-center gap-2">
    <div className="w-6 h-6 rounded-full ...">...</div>
    <div className="flex-1">...</div>
    {onlineUsers.length > 1 && (<div>...</div>)}
    <div className="flex items-center gap-1">
      {/* + button REMOVED — replaced by TabStrip's trailing + */}
      <div ref={historyRef}>...history dropdown...</div>
      <div ref={moreOptionsRef}>...more options dropdown...</div>
    </div>
  </div>
  <TabStrip
    tabs={tabs}
    activeId={visibleSessionId}
    cap={tabCap}
    onSwitch={openTab}
    onClose={closeTab}
    onNew={onNewChat ?? (() => {})}
  />
</div>
```

<!-- ChatSession lookup for tab labels (frontend/src/contexts/SessionMapContext.tsx:23-29) -->
```typescript
export interface ChatSession {
  id: string
  title: string
  preview?: string
  createdAt: string
  updatedAt: string
}
```

<!-- New consumers from useSessionControl (added in Plan 88-02): -->
```typescript
const {
  visibleSessionId,
  openTabIds,
  tabCap,
  openTab,
  closeTab,
} = useSessionControl()
const { sessions } = useSessionMap()
```

<!-- Existing harness (frontend/src/components/chat/__test-utils__/chatHarness.ts:74-76) -->
<!-- useSessionMap is already mocked module-scope. After Plan 88-01 the harness has a `sessionControl` option; -->
<!-- this plan adds an analogous `sessionMap` option for sessions[] lookup. -->
```typescript
vi.mock('@/contexts/SessionMapContext', () => ({
  useSessionMap: vi.fn(),
}))
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create TabStrip.tsx + RED behavior tests</name>
  <files>frontend/src/components/chat/TabStrip.tsx, frontend/src/components/chat/TabStrip.test.tsx</files>
  <behavior>
    The TabStrip component is a stateless presentation component — it receives all data and callbacks via props and emits no internal state. This makes it trivially unit-testable without context wrapping.

    6 tests, all RED initially because `TabStrip.tsx` does not exist yet:

    - **Test 1 — "renders one pill per tab"**: pass `tabs=[{id:'a',label:'Alpha',isActive:false},{id:'b',label:'Beta',isActive:true}]`; assert both labels render. Maps to feature criterion 6 (visible tabs).

    - **Test 2 — "active pill has distinct styling"**: assert the pill with `isActive:true` has a class containing `bg-teal` (or whatever the active style picks). Use `screen.getByText('Beta').closest('button')` and inspect className. Maps to criterion (locked decision: active styling).

    - **Test 3 — "clicking a pill calls onSwitch"**: pass `onSwitch=vi.fn()`; click the 'Alpha' pill (not on its X — on the label area); assert `onSwitch` called once with `'a'`. Maps to criterion 8 (tab switch).

    - **Test 4 — "clicking the × calls onClose"**: pass `onClose=vi.fn()`; click the close X next to 'Alpha'; assert `onClose` called once with `'a'`. The click MUST NOT also fire onSwitch (use stopPropagation in the close handler). Maps to criterion 10.

    - **Test 5 — "trailing + button calls onNew"**: pass `onNew=vi.fn()`, `cap=8`, `tabs.length === 2`; assert a `+` button is rendered, click it, assert `onNew` called once. Maps to criterion 11 (TabStrip's + supersedes the old `+` icon).

    - **Test 6 — "trailing + is disabled at cap"**: pass `cap=2`, `tabs.length === 2`; assert the `+` button is rendered with `disabled={true}` (or `aria-disabled="true"`); click it; assert `onNew` was NOT called. Maps to criterion 6 (cap enforcement at the UI layer — Plan 04 will add the toast).
  </behavior>
  <action>
    1. **Create `frontend/src/components/chat/TabStrip.tsx`** with the props contract defined in <interfaces>. Implementation should be stateless — no useState, no useEffect. Use Tailwind classes consistent with the rest of the codebase (read the existing chat header at `ChatInterface.tsx:1143-1173` for the design vocabulary: `text-xs`, `text-slate-700`, `bg-teal-50`, `rounded-md`, `transition-colors`).

       Reference structure (do not copy verbatim — adapt to the codebase's conventions):
       ```tsx
       'use client'

       import React from 'react'
       import { X, Plus } from 'lucide-react'

       export interface TabStripTab {
         id: string
         label: string
         isActive: boolean
       }

       export interface TabStripProps {
         tabs: TabStripTab[]
         activeId: string | null
         cap: number
         onSwitch: (id: string) => void
         onClose: (id: string) => void
         onNew: () => void
         className?: string
       }

       export function TabStrip({
         tabs,
         activeId,
         cap,
         onSwitch,
         onClose,
         onNew,
         className,
       }: TabStripProps) {
         const atCap = tabs.length >= cap

         return (
           <div
             role="tablist"
             aria-label="Open chat sessions"
             className={`flex items-center gap-1 px-2 py-1 bg-slate-50/40 overflow-x-auto ${className ?? ''}`}
           >
             {tabs.map((tab) => (
               <div
                 key={tab.id}
                 role="tab"
                 aria-selected={tab.isActive}
                 className={`group flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors max-w-[160px] flex-shrink-0 ${
                   tab.isActive
                     ? 'bg-teal-50 text-teal-700 font-semibold border border-teal-200'
                     : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                 }`}
               >
                 <button
                   data-testid={`tab-pill-${tab.id}`}
                   onClick={() => onSwitch(tab.id)}
                   className="flex-1 truncate text-left cursor-pointer"
                   title={tab.label}
                 >
                   {tab.label}
                 </button>
                 <button
                   data-testid={`tab-close-${tab.id}`}
                   onClick={(e) => {
                     e.stopPropagation()
                     onClose(tab.id)
                   }}
                   className="opacity-0 group-hover:opacity-100 hover:bg-red-100 hover:text-red-600 rounded p-0.5 transition-opacity"
                   aria-label={`Close ${tab.label}`}
                 >
                   <X size={10} />
                 </button>
               </div>
             ))}

             <button
               data-testid="tab-new"
               onClick={atCap ? undefined : onNew}
               disabled={atCap}
               className={`flex items-center justify-center p-1 rounded-md transition-colors flex-shrink-0 ${
                 atCap
                   ? 'text-slate-300 cursor-not-allowed'
                   : 'text-slate-500 hover:text-teal-600 hover:bg-slate-100'
               }`}
               aria-label={atCap ? `Tab cap reached (${cap})` : 'New chat'}
               title={atCap ? `Tab cap reached (${cap}). Close a tab to open a new one.` : 'New chat'}
             >
               <Plus size={14} />
             </button>
           </div>
         )
       }
       ```

       **Why opacity-0 group-hover for the close X:** mirrors VS Code / Chrome / Firefox tab UX — close X reveals on hover, doesn't clutter the at-rest state. If accessibility requires always-visible (some users prefer this), the `aria-label` is still announced by screen readers.

       **Why disabled vs aria-disabled:** the `<button disabled>` HTML attribute handles the click-suppression natively and screen readers announce it correctly. We also keep the `aria-label` informative.

    2. **Create `frontend/src/components/chat/TabStrip.test.tsx`**. This component is stateless — no harness or context wrapping required. Use plain `@testing-library/react` `render`:

       ```tsx
       import { describe, it, expect, vi } from 'vitest'
       import { render, screen, fireEvent } from '@testing-library/react'
       import { TabStrip, type TabStripTab } from './TabStrip'

       const baseTabs: TabStripTab[] = [
         { id: 'a', label: 'Alpha', isActive: false },
         { id: 'b', label: 'Beta', isActive: true },
       ]

       describe('TabStrip — multi-session tabs (FEATURE-MULTI-SESSION-TABS)', () => {
         it('renders one pill per tab', () => {
           render(<TabStrip tabs={baseTabs} activeId="b" cap={5} onSwitch={vi.fn()} onClose={vi.fn()} onNew={vi.fn()} />)
           expect(screen.getByText('Alpha')).toBeTruthy()
           expect(screen.getByText('Beta')).toBeTruthy()
         })

         it('active pill has distinct styling', () => {
           render(<TabStrip tabs={baseTabs} activeId="b" cap={5} onSwitch={vi.fn()} onClose={vi.fn()} onNew={vi.fn()} />)
           const activeButton = screen.getByText('Beta').closest('[role="tab"]') as HTMLElement
           expect(activeButton.className).toMatch(/bg-teal/)
           expect(activeButton.getAttribute('aria-selected')).toBe('true')
           const inactiveButton = screen.getByText('Alpha').closest('[role="tab"]') as HTMLElement
           expect(inactiveButton.getAttribute('aria-selected')).toBe('false')
         })

         it('clicking a pill calls onSwitch with the id', () => {
           const onSwitch = vi.fn()
           render(<TabStrip tabs={baseTabs} activeId="b" cap={5} onSwitch={onSwitch} onClose={vi.fn()} onNew={vi.fn()} />)
           fireEvent.click(screen.getByTestId('tab-pill-a'))
           expect(onSwitch).toHaveBeenCalledTimes(1)
           expect(onSwitch).toHaveBeenCalledWith('a')
         })

         it('clicking the × calls onClose with the id (and not onSwitch)', () => {
           const onSwitch = vi.fn()
           const onClose = vi.fn()
           render(<TabStrip tabs={baseTabs} activeId="b" cap={5} onSwitch={onSwitch} onClose={onClose} onNew={vi.fn()} />)
           fireEvent.click(screen.getByTestId('tab-close-a'))
           expect(onClose).toHaveBeenCalledTimes(1)
           expect(onClose).toHaveBeenCalledWith('a')
           expect(onSwitch).not.toHaveBeenCalled()
         })

         it('trailing + button calls onNew when below cap', () => {
           const onNew = vi.fn()
           render(<TabStrip tabs={baseTabs} activeId="b" cap={5} onSwitch={vi.fn()} onClose={vi.fn()} onNew={onNew} />)
           const newButton = screen.getByTestId('tab-new')
           expect((newButton as HTMLButtonElement).disabled).toBe(false)
           fireEvent.click(newButton)
           expect(onNew).toHaveBeenCalledTimes(1)
         })

         it('trailing + is disabled at cap and does not fire onNew', () => {
           const onNew = vi.fn()
           render(<TabStrip tabs={baseTabs} activeId="b" cap={2} onSwitch={vi.fn()} onClose={vi.fn()} onNew={onNew} />)
           const newButton = screen.getByTestId('tab-new') as HTMLButtonElement
           expect(newButton.disabled).toBe(true)
           fireEvent.click(newButton)
           expect(onNew).not.toHaveBeenCalled()
         })
       })
       ```

    3. **Run the tests:**
       ```bash
       cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx
       ```
       All 6 must GREEN immediately — the component is created in this same task. The "RED" terminology is technically misapplied here because component-creation and test-creation happen together; that's intentional for stateless presentation components where there's nothing to wire incrementally. The TDD discipline that matters here is: **assertions are written from the props contract, not after seeing the rendered output**.

    4. **Lint + tsc:**
       ```bash
       cd frontend && npx eslint src/components/chat/TabStrip.tsx src/components/chat/TabStrip.test.tsx
       cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep TabStrip
       ```
       Both clean.

    5. **Commit:**
       ```bash
       git add frontend/src/components/chat/TabStrip.tsx frontend/src/components/chat/TabStrip.test.tsx
       git commit -m "feat(88-03): add TabStrip presentation component + 6 behavior tests (FEATURE-MULTI-SESSION-TABS)"
       ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx</automated>
  </verify>
  <done>
    `TabStrip.tsx` created with stateless props contract matching <interfaces>. `TabStrip.test.tsx` created with 6 tests, all GREEN. Lint + tsc clean. Commit message: `feat(88-03): add TabStrip presentation component + 6 behavior tests (FEATURE-MULTI-SESSION-TABS)`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire TabStrip into ChatInterface header + remove legacy `+` button</name>
  <files>frontend/src/components/chat/ChatInterface.tsx, frontend/src/components/chat/__test-utils__/chatHarness.ts, frontend/src/components/chat/ChatInterface.test.tsx</files>
  <behavior>
    After this task:
    - `ChatInterface` renders `<TabStrip />` below the existing agent-identity header bar.
    - The legacy `+` button at line ~1167 is REMOVED.
    - `tabs` prop is computed from `openTabIds` × `sessions[]` lookup (with a fallback label for ids not yet in `sessions[]`, e.g. brand-new chats).
    - `activeId` is `visibleSessionId`.
    - `onSwitch={openTab}`, `onClose={closeTab}`, `onNew={onNewChat ?? createNewChat}`.

    New ChatInterface tests in the existing test file:
    - **Test 7 (HOTFIX-06 describe block)**: render harness with `sessionControl: { openTabIds: ['s1','s2'], visibleSessionId: 's2', tabCap: 5 }` and `sessionMap: { sessions: [{id:'s1',title:'First chat',createdAt:'',updatedAt:''},{id:'s2',title:'Second chat',createdAt:'',updatedAt:''}] }`; assert both 'First chat' and 'Second chat' labels appear AND that the legacy `+` icon (queryable as `screen.queryByTitle('New Chat')` from the old button) is GONE. Maps to criteria 6, 11.
    - **Test 8 (HOTFIX-06 describe block)**: render same setup; click the 'First chat' pill via `screen.getByTestId('tab-pill-s1')`; assert `openTab` mock from sessionControl was called with `'s1'`. Maps to criterion 8.
  </behavior>
  <action>
    **Step 1 — Extend chatHarness.ts** to mock `useSessionMap` with a default `sessions` array and accept a `sessionMap` override:
    ```typescript
    // Add to RenderChatOptions
    sessionMap?: Partial<{
      sessions: ChatSession[]
      activeSessions: Map<string, unknown>
      addActiveSession: (id: string, init?: unknown) => void
      removeActiveSession: (id: string) => void
      updateSessionState: (id: string, updates: unknown) => void
      getActiveSessionRef: (id: string) => null
      isLoadingSessions: boolean
      setSessions: (s: unknown) => void
      setIsLoadingSessions: (b: boolean) => void
    }>

    // Inside renderChatInterface, add the mock setup (analogous to sessionControl from Plan 01):
    const defaultSessionMap = {
      sessions: [],
      activeSessions: new Map(),
      addActiveSession: vi.fn(),
      removeActiveSession: vi.fn(),
      updateSessionState: vi.fn(),
      getActiveSessionRef: vi.fn(() => null),
      isLoadingSessions: false,
      setSessions: vi.fn(),
      setIsLoadingSessions: vi.fn(),
    }
    ;(useSessionMap as ReturnType<typeof vi.fn>).mockReturnValue({
      ...defaultSessionMap,
      ...opts.sessionMap,
    })
    ```

    Also extend the `sessionControl` default object (added in Plan 01 Task 1) to include the new tab fields:
    ```typescript
    const defaultSessionControl = {
      // ... existing fields ...
      openTabIds: [] as string[],
      tabCap: 5,
      openTab: vi.fn(),
      closeTab: vi.fn(),
    }
    ```

    **Step 2 — Edit `frontend/src/components/chat/ChatInterface.tsx`.**

    **2a — Add the import** at the top with the other component imports:
    ```typescript
    import { TabStrip, type TabStripTab } from './TabStrip'
    ```

    **2b — Pull the new fields from useSessionControl + useSessionMap.** Locate the existing `useSessionControl()` call (search for `const { visibleSessionId } = useSessionControl()` or similar — currently used for `visibleSessionId`). Update it:
    ```typescript
    const { visibleSessionId, openTabIds, tabCap, openTab, closeTab } = useSessionControl()
    const { sessions } = useSessionMap()
    ```

    **2c — Compute the `tabs` prop** with `useMemo` near the top of the component body (after the hook calls):
    ```typescript
    const tabs: TabStripTab[] = useMemo(() => {
      return openTabIds.map((id) => {
        const session = sessions.find((s) => s.id === id)
        const rawLabel = session?.title?.trim() || session?.preview?.trim() || ''
        const label = rawLabel
          ? rawLabel.length > 24
            ? rawLabel.slice(0, 24) + '…'
            : rawLabel
          : 'New chat'
        return {
          id,
          label,
          isActive: id === visibleSessionId,
        }
      })
    }, [openTabIds, sessions, visibleSessionId])
    ```

    **Why "New chat" fallback:** when the user clicks `+` to create a fresh session, `openTabIds` updates immediately (push-based) but `sessions[]` doesn't update until the next `refreshSessions()` round-trip (after the first message is sent and the title is computed server-side, ~2-8 seconds later). The fallback ensures the new pill renders with a sensible label during that gap.

    **2d — Replace the header markup at lines 1143-1292.** This is a structural edit. Read the existing block first; the diff is:
    - Wrap the existing `<div className="bg-slate-50/60 p-2 border-b border-slate-100/80 flex items-center gap-2">` and the action-icon row in a parent container that holds both the agent-identity row AND the new TabStrip.
    - DELETE the `<button onClick={onNewChat} title="New Chat"><Plus size={14} /></button>` block at lines 1167-1173 (the legacy `+`).
    - INSERT `<TabStrip ... />` AFTER the agent-identity row, BEFORE the messages area.

    Resulting structure:
    ```tsx
    {/* Header */}
    <div className="border-b border-slate-100/80">
      <div className="bg-slate-50/60 p-2 flex items-center gap-2">
        <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-teal-500 to-cyan-500 flex items-center justify-center text-white font-bold text-xs shadow-lg shadow-teal-500/20">
          {agentName ? agentName.charAt(0).toUpperCase() : <Bot size={14} />}
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-sm text-slate-800 font-outfit leading-tight">
            {agentName || 'Pikar AI'}
          </h3>
          <p className="text-[10px] text-slate-500 leading-tight block mt-0.5">
            {agentName ? 'Personal Agent' : 'Executive Assistant & Orchestrator'}
          </p>
        </div>
        {/* Online users indicator */}
        {onlineUsers.length > 1 && (
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>{onlineUsers.length} online</span>
          </div>
        )}

        {/* Header Action Icons — note: legacy + button DELETED here */}
        <div className="flex items-center gap-1">
          {/* Chat History Dropdown — UNCHANGED */}
          <div ref={historyRef} className="relative">...</div>
          {/* More Options Dropdown — UNCHANGED */}
          <div ref={moreOptionsRef} className="relative">...</div>
        </div>
      </div>

      {/* TabStrip — new in Plan 88-03 */}
      <TabStrip
        tabs={tabs}
        activeId={visibleSessionId}
        cap={tabCap}
        onSwitch={openTab}
        onClose={closeTab}
        onNew={onNewChat ?? (() => { void 0 })}
      />
    </div>
    ```

    **DO NOT delete:** The history dropdown (`historyRef`) and more-options dropdown (`moreOptionsRef`) — they stay intact at the right edge of the agent-identity row.

    **DO NOT modify:** the messages area (lines 1303-1318) or the input area (lines 1320+).

    **2e — Audit `onNewChat` prop binding.** It comes from `PersonaDashboardLayout.tsx:232` which passes `createNewChat` from `useChatSession()`. Plan 02 updated `createNewChat` to push into `openTabIds` already, so the wiring works without change. Confirm by reading line 232 — `onNewChat={createNewChat}`. No edits to PersonaDashboardLayout in this plan.

    **Step 3 — Add the two integration tests** to `ChatInterface.test.tsx` under the existing `describe('ChatInterface — persistence (HOTFIX-06)', ...)` block from Plan 01:

    ```typescript
    it('renders TabStrip pills from openTabIds × sessions', () => {
      renderChatInterface({
        sessionControl: {
          openTabIds: ['s1', 's2'],
          visibleSessionId: 's2',
          tabCap: 5,
        },
        sessionMap: {
          sessions: [
            { id: 's1', title: 'First chat', createdAt: '', updatedAt: '' },
            { id: 's2', title: 'Second chat', createdAt: '', updatedAt: '' },
          ],
        },
      })
      expect(screen.getByText('First chat')).toBeTruthy()
      expect(screen.getByText('Second chat')).toBeTruthy()
      // The legacy + icon (the small one in the header action row) is gone:
      expect(screen.queryByTitle('New Chat')).toBeNull()
      // The TabStrip + button still exists at the end of the strip:
      expect(screen.getByTestId('tab-new')).toBeTruthy()
    })

    it('clicking a TabStrip pill calls openTab', () => {
      const openTab = vi.fn()
      renderChatInterface({
        sessionControl: {
          openTabIds: ['s1', 's2'],
          visibleSessionId: 's2',
          openTab,
          tabCap: 5,
        },
        sessionMap: {
          sessions: [
            { id: 's1', title: 'First chat', createdAt: '', updatedAt: '' },
            { id: 's2', title: 'Second chat', createdAt: '', updatedAt: '' },
          ],
        },
      })
      fireEvent.click(screen.getByTestId('tab-pill-s1'))
      expect(openTab).toHaveBeenCalledTimes(1)
      expect(openTab).toHaveBeenCalledWith('s1')
    })
    ```

    **Step 4 — Run all tests:**
    ```bash
    cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx src/components/chat/ChatInterface.test.tsx
    ```
    All tests must GREEN: 6 TabStrip tests + (4 pre-Phase-83 + 5 HOTFIX-01 + 1 from Plan 88-01 + 2 new from this task) ChatInterface tests = 18 total.

    **Step 5 — Lint + tsc:**
    ```bash
    cd frontend && npx eslint src/components/chat/ChatInterface.tsx src/components/chat/__test-utils__/chatHarness.ts
    cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E "ChatInterface|chatHarness"
    ```
    Both clean.

    **Step 6 — Commit:**
    ```bash
    git add frontend/src/components/chat/ChatInterface.tsx \
            frontend/src/components/chat/__test-utils__/chatHarness.ts \
            frontend/src/components/chat/ChatInterface.test.tsx
    git commit -m "feat(88-03): wire TabStrip into ChatInterface header, remove legacy + (FEATURE-MULTI-SESSION-TABS)"
    ```
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx src/components/chat/ChatInterface.test.tsx</automated>
  </verify>
  <done>
    `ChatInterface.tsx` header restructured into a two-row layout: agent-identity row + TabStrip row. Legacy `+` button at line ~1167 deleted. `tabs` derived via useMemo from `openTabIds × sessions`. Harness extended with `sessionMap` option and tab fields in the `sessionControl` default. 2 new ChatInterface tests pass. All 18 tests across the two files GREEN. Lint + tsc clean. Commit message: `feat(88-03): wire TabStrip into ChatInterface header, remove legacy + (FEATURE-MULTI-SESSION-TABS)`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Workspace coupling verification + UAT script + SUMMARY</name>
  <files>.planning/phases/88-chat-and-workspace-persistence/88-03-tab-strip-ui-SUMMARY.md</files>
  <action>
    1. **Verify workspace coupling — criterion 8** is wired correctly. The wiring already exists at `ActiveWorkspace.tsx:357-359`:
       ```typescript
       useEffect(() => {
         loadWorkspaceState()
       }, [loadWorkspaceState])
       ```
       and at line 361-366:
       ```typescript
       useEffect(() => {
         setActivity(null)
         setWorkspaceItems([])
         setActiveItemId(null)
         setLayoutMode('focus')
       }, [currentSessionId])
       ```
       The `currentSessionId` flows from `useChatSession().currentSessionId` → which is `useSessionControl().visibleSessionId` (per `ChatSessionContext.tsx:33`) → which `openTab()` updates via `setVisibleSessionId()` (Plan 02). So clicking a TabStrip pill triggers: `openTab(id)` → `setVisibleSessionId(id)` → `currentSessionId` change in PersonaDashboardLayout → `ActiveWorkspace`'s currentSessionId useEffect fires → workspace re-queries Supabase keyed on the new id.

       **No code change needed in this task — verification is the deliverable.** Document the chain in the SUMMARY so future readers can audit it without re-tracing.

    2. **Full frontend suite**: `cd frontend && npm test`. Must be GREEN.

    3. **Lint**: `cd frontend && npm run lint`. No new warnings.

    4. **TypeScript**: `cd frontend && npx tsc --noEmit -p tsconfig.json`. Clean.

    5. **Manual UAT script** (record in SUMMARY):
       - Open the app. Send a message (e.g. "Hello"). Note the new session_id in `localStorage.pikar_open_tab_ids`.
       - Click the TabStrip's trailing `+`. A new pill appears (label "New chat" until first message). Workspace clears (no items).
       - Send a different message in the new tab (e.g. "What's the weather?"). The pill label updates to a truncated version of the message after a few seconds (when refreshSessions completes).
       - Click the FIRST tab. The chat panel scrolls back to "Hello" / its agent response. The workspace re-queries and shows whatever items the first session created (or empty if none).
       - Click the second tab. Workspace swaps again — back to whatever items the second session has. **No stale items from the first session appear** — that's criterion 8.
       - Open chat history dropdown (Clock icon). Click an older session. Confirm a new pill appears for it (selectChat → openTab delegation from Plan 02).
       - Click `+` repeatedly until 5 pills are open. The 6th `+` click is greyed out (disabled). Tooltip shows "Tab cap reached (5). Close a tab to open a new one."
       - Click the `×` on one pill. Pill disappears. If it was the visible tab, the next-most-recent tab becomes visible. Workspace re-queries.
       - Close all tabs one by one. The last close should auto-create a fresh tab — chat panel never goes empty.

    6. **Write SUMMARY.md** at the path in <files>. Cover:
       - **Component added:** TabStrip.tsx — stateless presentation, ~120 lines.
       - **Component edited:** ChatInterface.tsx — header restructured to two rows, legacy `+` deleted (~10 lines net change).
       - **Harness extended:** chatHarness.ts — new `sessionMap` option, `sessionControl` defaults extended with tab fields.
       - **Tests added:** 6 TabStrip behavior tests, 2 ChatInterface integration tests.
       - **Workspace coupling chain documented** (the 4-link chain from openTab → ActiveWorkspace re-query). This is criterion 8's verification — no new code needed; the wiring shipped before this plan.
       - **Truth-to-code map:** 8 truths from must_haves to source line ranges.
       - **Out-of-scope deferrals:** streaming-tab indicator (Plan 04), max-tab toast in production (Plan 04 — current behavior is just a disabled button + tooltip), drag-to-reorder (out of phase).
       - **Locked-decision honored:** active-tab styling via teal-50 bg + teal-200 border + bold; close-X reveal on hover (VS Code pattern).
       - **PR-reviewer note:** Frontend-only plan; backend tests not required.
       - **Executor halt criteria (WARNING 4):** Halt and notify if any single task's vitest run exceeds 5 minutes wall-clock OR any single task's diff exceeds 15 files. The plan modifies 5 files across two layers (component + integration); defensive halts protect quality.
       - **Manual UAT script** (the 9-step script from action #5).
  </action>
  <verify>
    <automated>cd frontend && npm test && cd frontend && npm run lint</automated>
  </verify>
  <done>
    Full vitest suite GREEN. Frontend lint clean. TypeScript compile clean. SUMMARY.md exists at `.planning/phases/88-chat-and-workspace-persistence/88-03-tab-strip-ui-SUMMARY.md` with workspace-coupling chain documented (criterion 8 traced through 4 source locations) and 9-step manual UAT script.
  </done>
</task>

</tasks>

<verification>
**Per-task automated verification:**

| Task | Command | Maps To |
|------|---------|---------|
| 1 (TabStrip unit) | `cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx` (6 PASS) | Component contract |
| 2 (Integration) | `cd frontend && npx vitest run src/components/chat/TabStrip.test.tsx src/components/chat/ChatInterface.test.tsx` (all PASS) | Wiring |
| 3 (Suite) | `cd frontend && npm test` + `npm run lint` | Phase gate |

**Behavior assertions covering FEATURE-MULTI-SESSION-TABS criteria 6, 8, 11:**
- Test 1 (TabStrip renders pills) → criterion 6 (visible tabs)
- Test 7 (ChatInterface renders TabStrip + legacy + gone) → criterion 11 (TabStrip supersedes `+`)
- Test 8 (clicking pill → openTab → setVisibleSessionId → workspace re-queries) → criterion 8 (workspace follows tab) — chain verified through ActiveWorkspace.tsx existing useEffect
- Tests 5+6 (TabStrip cap behavior) → criterion 6 (cap enforcement at UI)

Criterion 9 (streaming indicator) is intentionally NOT covered here — it requires `useBackgroundStream`'s session activity which Plan 04 wires into TabStrip pill styling.
</verification>

<success_criteria>
- TabStrip is a stateless, prop-driven component testable without context wrapping.
- ChatInterface header is restructured into a two-row layout — agent identity + TabStrip.
- The tiny `+` icon at line ~1167 is deleted; the TabStrip's trailing `+` is the canonical new-chat affordance.
- Tab labels gracefully degrade: session.title > session.preview > "New chat" fallback.
- Active-tab styling visually distinguishes the visible tab (teal background + bold).
- Workspace coupling (criterion 8) is verified through documentation of the existing wiring — no new code needed.
- Cap-at-UI is shown via `disabled` button + descriptive tooltip; the actual toast is Plan 04.
</success_criteria>

<output>
After completion, create `.planning/phases/88-chat-and-workspace-persistence/88-03-tab-strip-ui-SUMMARY.md` documenting:
1. **Component added:** TabStrip.tsx (stateless presentation, ~120 lines).
2. **Component edited:** ChatInterface.tsx (header restructured to two-row layout; legacy `+` deleted).
3. **Harness extension:** sessionMap option + tab fields in sessionControl defaults.
4. **Tests added:** 6 TabStrip + 2 ChatInterface integration = 8 total.
5. **Workspace coupling chain:** openTab → setVisibleSessionId → currentSessionId in PersonaDashboardLayout → ActiveWorkspace useEffect re-query (line refs).
6. **Truth-to-code map** for 8 truths.
7. **Out-of-scope deferrals:** streaming indicator (04), max-tab toast (04), drag-reorder (out of phase).
8. **Locked-decision honored:** teal active styling, hover-reveal close X.
9. **PR-reviewer note:** Frontend-only.
10. **Manual UAT script** (9 steps).
</output>
</content>
</invoke>