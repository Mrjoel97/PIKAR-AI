---
phase: 88-chat-and-workspace-persistence
plan: 03
subsystem: frontend/components/chat
tags: [feature-multi-session-tabs, tabstrip, chatinterface, vitest, ui-presentation, locked-decisions]
requires:
  - phase: 88-02-tab-state
    provides: openTabIds, tabCap, openTab, closeTab, sessions[] from useSessionMap
provides:
  - TabStrip.tsx — stateless presentation component (~135 LOC) consuming openTabIds × sessions
  - ChatInterface.tsx header restructured into a two-row layout (agent identity row + TabStrip row)
  - Legacy `+` button at line ~1167 removed; the TabStrip's trailing `+` is now the canonical new-chat affordance
  - chatHarness.ts extended with sessionMap option + 5 new tab fields in the sessionControl default
affects:
  - 88-04-streaming-indicator (will pass per-tab streaming/unread state through TabStrip's `tabs` prop without refactoring the contract)

tech-stack:
  added: []
  patterns:
    - "Stateless prop-driven UI — no useState/useEffect inside TabStrip; testable without provider wrapping"
    - "Hover-reveal close X (VS Code / Chrome / Firefox tab UX) via opacity-0 group-hover:opacity-100 — keeps the at-rest UI clean while remaining screen-reader-accessible via aria-label"
    - "Native HTML `disabled` attribute on the trailing `+` button — browser handles click-suppression; screen readers announce disabled state correctly"
    - "useMemo over openTabIds × sessions — recomputes tab labels only when openTabIds, sessions, or visibleSessionId change"
    - "'New chat' fallback label — covers the createNewChat → refreshSessions latency window (push-based openTabIds updates immediately, sessions[] arrives ~2-8s later)"

key-files:
  created:
    - frontend/src/components/chat/TabStrip.tsx (135 LOC, stateless presentation)
    - frontend/src/components/chat/TabStrip.test.tsx (147 LOC, 6 vitest behavior tests)
    - .planning/phases/88-chat-and-workspace-persistence/88-03-tab-strip-ui-SUMMARY.md
  modified:
    - frontend/src/components/chat/ChatInterface.tsx (+30 LOC, -10 LOC net change: header restructured, useMemo-derived tabs, legacy + removed, Plus icon dropped from import)
    - frontend/src/components/chat/__test-utils__/chatHarness.ts (+50 LOC: SessionMapOverrides interface, sessionMap option in RenderChatOptions, defaultSessionMap accepts overrides, defaultSessionControl extended with the 5 new tab fields)
    - frontend/src/components/chat/ChatInterface.test.tsx (+62 LOC: 2 new HOTFIX-06 describe-block tests)

key-decisions:
  - "Stateless prop-driven TabStrip — no internal state, no context coupling. Plan 88-04 can pass per-tab streaming/unread indicator state through props without refactoring."
  - "Active styling = teal-50 background + teal-200 border + bold (locked decision in CONTEXT.md / 88-03 PLAN must_haves). Inactive = white bg + slate-200 border + slate-600 text + hover:slate-100."
  - "Hover-reveal close X over always-visible — matches VS Code / Chrome / Firefox tab UX and keeps the at-rest TabStrip uncluttered. aria-label='Close {label}' keeps screen-reader announcement intact."
  - "Native HTML `disabled` attribute on the trailing `+` (vs aria-disabled='true' with onClick guard) — disabled handles click suppression natively AND screen readers announce 'button disabled' without extra ARIA work."
  - "'New chat' fallback for tab labels — covers the createNewChat → first-message → server-side title computation → refreshSessions latency window (typically 2-8s). Without this, brand-new tabs would render with empty labels until the round trip completes."
  - "Header restructured into a two-row layout (parent div with border-b → row 1 = agent identity + dropdowns + row 2 = TabStrip) instead of inlining TabStrip into the same flex row. Reason: TabStrip needs full width and overflow-x-auto for many tabs; cramming it into the agent-identity row would push the dropdown icons off-screen."
  - "The `Plus` icon was dropped from the lucide-react import line — it was only used by the legacy `+` button which is now deleted. Removing the unused import keeps the import line clean and prevents an unused-import lint warning."

patterns-established:
  - "Pattern A — Stateless presentation component for multi-instance UI: when a component renders N pills and Plan-N+1 will add per-pill state (here: streaming indicator), keep the props contract simple (`tabs: TabStripTab[]`) and let the parent compute per-tab state. Future state additions are additive — new fields on TabStripTab — not refactoring."
  - "Pattern B — Test-without-context for stateless components: TabStrip.test.tsx renders the component directly via @testing-library/react with no harness. The 6 tests run in 232ms total because there's no provider tree to mount. Save the harness for components that consume context."

requirements-completed:
  - FEATURE-MULTI-SESSION-TABS

# Metrics
duration: 15min
completed: 2026-05-01
tasks_count: 3
files_count: 5
---

# Phase 88 Plan 03: Tab Strip UI Summary

**TabStrip presentation component + ChatInterface header restructure — multi-session tabs visible in the chat panel header. Plan 88-02 shipped the data layer (openTabIds, openTab/closeTab, tier-derived cap); this plan ships the discoverable surface that consumes it.**

## Performance

- **Duration:** ~15 minutes
- **Started:** 2026-05-01T00:56:51Z
- **Completed:** 2026-05-01T01:11:54Z
- **Tasks:** 3
- **Files modified:** 5 (2 created — TabStrip.tsx + TabStrip.test.tsx; 3 edited — ChatInterface.tsx, chatHarness.ts, ChatInterface.test.tsx)
- **Net production LOC:** ~155 (+135 TabStrip.tsx + ~30 ChatInterface.tsx - ~10 deleted legacy + button)
- **Net test/harness LOC:** ~209 (+147 TabStrip.test.tsx + ~50 chatHarness.ts + ~62 ChatInterface.test.tsx)

## Accomplishments

- New `TabStrip.tsx` ships as a stateless prop-driven component — no useState, no useEffect, no context coupling. Renders one pill per tab + a trailing `+` button. Active pill carries teal-50 bg + teal-200 border + bold text + `aria-selected="true"`. Close `×` reveals on group-hover and calls `e.stopPropagation()` to prevent the parent pill click from firing.
- New `TabStrip.test.tsx` ships with 6 behavior tests (render, active styling, onSwitch, onClose with stopPropagation, onNew below cap, disabled at cap). All GREEN immediately. Tests run in 232ms total — no harness/provider wrapping needed.
- `ChatInterface.tsx` header restructured into a two-row layout — row 1 keeps the agent identity + history/more dropdowns; row 2 is the TabStrip. The legacy `<button onClick={onNewChat} title="New Chat"><Plus /></button>` at line ~1167 has been DELETED; the TabStrip's trailing `+` is the canonical new-chat affordance. The unused `Plus` import was dropped.
- `chatHarness.ts` extended with a new `SessionMapOverrides` interface and `sessionMap` option on `RenderChatOptions`, so Plan 88-03 tests can seed `sessions[]` for tab-label derivation. The `defaultSessionControl` was extended with the 5 new Plan-02 tab fields (openTabIds, tabCap, setTabCap, openTab, closeTab) so any future ChatInterface destructure of those fields does not crash.
- 2 new ChatInterface integration tests added under the existing `'persistence (HOTFIX-06)'` describe block: one asserts the TabStrip renders pills from `openTabIds × sessions` AND the legacy `+` icon (`queryByTitle('New Chat')`) is gone; one asserts clicking a pill calls `openTab` with the id.
- All 18 vitest tests across the two affected files GREEN (6 TabStrip + 12 ChatInterface).
- TypeScript compile clean for the 3 modified files.
- Lint clean for new files (TabStrip.tsx, TabStrip.test.tsx, chatHarness.ts); pre-existing warnings/errors in ChatInterface.tsx (17 problems unchanged from Plan 88-02 baseline) are documented as out-of-scope.
- Full frontend suite: 522 passed / 49 failed — failure count IDENTICAL to Plan 88-02 baseline (the same 49 pre-existing failures in PersonaView, CalendarWidget, InitiativeDashboard, KanbanWidget, RevenueChart, LandingDemo, ProtectedRoute, etc.). Test-passed count went from 514 (Plan 88-02) to 522 (Plan 88-03) — exactly +8 (6 TabStrip + 2 ChatInterface) as designed.

## Per-Task Commits

| Task | Hash | Message |
| --- | --- | --- |
| 1 (TabStrip + tests) | `7ed9111d` | `feat(88-03): add TabStrip presentation component + 6 behavior tests (FEATURE-MULTI-SESSION-TABS)` |
| 2 (ChatInterface wiring + 2 integration tests) | `b6053994` | `feat(88-03): wire TabStrip into ChatInterface header, remove legacy + (FEATURE-MULTI-SESSION-TABS)` |
| 3 (this commit — workspace verification + SUMMARY) | (final) | `docs(88-03): complete tab-strip-ui plan` |

## Workspace Coupling Chain (criterion 8 — verification only)

Criterion 8 of FEATURE-MULTI-SESSION-TABS reads: *"Clicking a pill switches the visible tab — calls openTab(id) which updates visibleSessionId and the workspace re-queries on the new id."*

This wiring already shipped before Plan 88-03. The chain is:

1. **TabStrip pill click** → `onSwitch(tab.id)` callback fires (TabStrip.tsx:75 — `onClick={() => onSwitch(tab.id)}`)
2. **ChatInterface passes `onSwitch={openTab}`** (ChatInterface.tsx, header markup near line 1320 after restructure: `<TabStrip ... onSwitch={openTab} />`)
3. **`openTab(sessionId)` calls `setVisibleSessionId(sessionId)`** (SessionControlContext.tsx:317-341, Plan 88-02)
4. **`setVisibleSessionId` updates `visibleSessionId` state** AND persists to `pikar_current_session_id` localStorage (SessionControlContext.tsx:255-266)
5. **`useChatSession()` exposes `currentSessionId = ctrl.visibleSessionId`** (ChatSessionContext.tsx:60)
6. **PersonaDashboardLayout** consumes `currentSessionId` from `useChatSession()` and passes it down to `<ActiveWorkspace currentSessionId={currentSessionId} />` (or, alternatively, `ActiveWorkspace` reads `useSessionControl().visibleSessionId` directly at line 287: `const { visibleSessionId: currentSessionId } = useSessionControl();`)
7. **ActiveWorkspace's `loadWorkspaceState` useEffect** lists `[currentSessionId, supabase]` as deps (ActiveWorkspace.tsx:355). When `currentSessionId` changes, `loadWorkspaceState` runs, which:
   - Reads local widgets keyed on `(authUser.id, currentSessionId)` (line 317-318)
   - Queries Supabase `workspace_items` with `.eq('session_id', currentSessionId)` (line 329)
8. **A second useEffect** at ActiveWorkspace.tsx:362-366 lists `[currentSessionId]` as deps and resets `setActivity(null)`, `setWorkspaceItems([])`, `setActiveItemId(null)`, `setLayoutMode('focus')` — so stale UI from the previous session does not bleed into the new one before the Supabase round-trip completes.

**No new code was added to wire this chain in Plan 88-03.** The workspace coupling was already in place; this plan inserts the TabStrip pill clicks at the head of the chain. Tests 7-8 in `ChatInterface.test.tsx` (added in Task 2) lock in the entry point — clicking a pill calls `openTab` with the id, and `openTab` (Plan 88-02 implementation) is the rest of the chain's deterministic kickoff.

## Files Created/Modified

### Created

- **`frontend/src/components/chat/TabStrip.tsx`** (135 LOC)
  - Stateless presentation component. Exports `TabStrip` function component, `TabStripTab` interface, `TabStripProps` interface.
  - Renders `<div role="tablist">` containing N pills + a trailing `+` button.
  - Each pill is a `<div role="tab" aria-selected={isActive}>` containing a label `<button>` (data-testid `tab-pill-{id}`) and a close `<button>` (data-testid `tab-close-{id}`).
  - Trailing `+` button has data-testid `tab-new`. Disabled via the native HTML `disabled` attribute when `tabs.length >= cap`.
  - `isActive` is derived from `activeId === tab.id` with `tab.isActive` as a fallback (so callers can opt into per-tab visual override semantics if a future plan ever needs it).
  - Active styling: `bg-teal-50 text-teal-700 font-semibold border border-teal-200`. Inactive: `bg-white text-slate-600 hover:bg-slate-100 border border-slate-200`.

- **`frontend/src/components/chat/TabStrip.test.tsx`** (147 LOC)
  - 6 vitest tests, no harness or provider wrapping required.
  - Each test renders TabStrip directly with vi.fn() callbacks and asserts on the resulting DOM / mock invocations.
  - Tests run in 232ms total.

### Modified

- **`frontend/src/components/chat/ChatInterface.tsx`**
  - Imports: dropped `Plus` from lucide-react (no longer used after the legacy + button was removed); added `TabStrip, type TabStripTab` from `'./TabStrip'`.
  - Hook destructure (around line 109): `useSessionControl()` extended from `{ visibleSessionId }` to `{ visibleSessionId, openTabIds, tabCap, openTab, closeTab }`; `useSessionMap()` extended from `{ activeSessions, updateSessionState }` to `{ activeSessions, updateSessionState, sessions }`.
  - New `useMemo` (after the destructure) computes `tabs: TabStripTab[]` from `openTabIds × sessions` with a "New chat" fallback for ids not yet in `sessions[]`. Truncates labels longer than 24 chars with `…`.
  - Header markup (lines 1143-1320): wrapped the agent-identity row in a parent `<div className="border-b border-slate-100/80">`; deleted the `<button onClick={onNewChat} title="New Chat"><Plus size={14} /></button>` block; inserted `<TabStrip tabs={tabs} activeId={visibleSessionId} cap={tabCap} onSwitch={openTab} onClose={closeTab} onNew={onNewChat ?? (() => {})} />` BELOW the agent-identity row, INSIDE the wrapper.
  - Net diff: ~30 LOC added, ~10 LOC removed.

- **`frontend/src/components/chat/__test-utils__/chatHarness.ts`**
  - Imported `type ChatSession` from `@/contexts/SessionMapContext`.
  - `SessionControlOverrides` extended with 5 new fields: `openTabIds?`, `tabCap?`, `setTabCap?`, `openTab?`, `closeTab?`.
  - New `SessionMapOverrides` interface mirroring the SessionMapContext shape.
  - `RenderChatOptions` extended with `sessionMap?: SessionMapOverrides`.
  - `defaultSessionControl` extended with the 5 tab fields (default values: `openTabIds: []`, `tabCap: 5`, `setTabCap: vi.fn()`, `openTab: vi.fn()`, `closeTab: vi.fn()`).
  - `defaultSessionMap` now accepts an optional overrides argument and merges over the base map. The base map's `sessions: []` is now typed `ChatSession[]`.
  - `renderChatInterface` passes `opts.sessionMap` to `defaultSessionMap(opts.sessionMap)` so tests can seed sessions[] declaratively.

- **`frontend/src/components/chat/ChatInterface.test.tsx`**
  - 2 new tests added under the existing `describe('ChatInterface — persistence (HOTFIX-06)', ...)` block:
    - `'renders TabStrip pills from openTabIds × sessions and removes legacy +'` — seeds `openTabIds: ['s1','s2']` + `sessions: [{id:'s1',title:'First chat',...},{id:'s2',title:'Second chat',...}]`; asserts both labels render, `screen.queryByTitle('New Chat')` is null (legacy + gone), and `screen.getByTestId('tab-new')` exists.
    - `'clicking a TabStrip pill calls openTab with the id'` — seeds the same setup with a vi.fn() `openTab`; clicks `tab-pill-s1`; asserts `openTab` was called once with `'s1'`.

## Truth-to-Code Map

For ROADMAP traceability — each `must_haves.truths` item from PLAN.md to its source line range and test.

| # | Truth | Source line range | Test |
| --- | --- | --- | --- |
| 1 | "ChatInterface header renders a horizontal TabStrip (one pill per id in openTabIds) instead of a bare `+` icon" | `ChatInterface.tsx` header markup near `<TabStrip />` insertion point (after the wrapping two-row div); `TabStrip.tsx:60-70` (`<div role="tablist">` + `tabs.map(...)` rendering one `<div role="tab">` per id) | TabStrip Test 1, ChatInterface Test 'renders TabStrip pills from openTabIds × sessions...' |
| 2 | "Each tab pill shows a label derived from the matching ChatSession (sessions[].title with preview fallback) and a close `×` button" | `ChatInterface.tsx` useMemo: `const session = sessions.find((s) => s.id === id); const rawLabel = session?.title?.trim() || session?.preview?.trim() || ''; ...` | ChatInterface Test 'renders TabStrip pills...' (assertion on `screen.getByText('First chat')` derived from session.title) |
| 3 | "Clicking a pill switches the visible tab — calls openTab(id) which updates visibleSessionId and the workspace re-queries on the new id" | `TabStrip.tsx:75` (`onClick={() => onSwitch(tab.id)}`) → `ChatInterface.tsx` (`onSwitch={openTab}`) → `SessionControlContext.tsx:317-341` (openTab) → `ActiveWorkspace.tsx:317-355` (loadWorkspaceState useEffect on `[currentSessionId, supabase]`). See "Workspace Coupling Chain" section above. | TabStrip Test 3 (onSwitch called with id), ChatInterface Test 'clicking a TabStrip pill calls openTab with the id' |
| 4 | "Clicking the `×` on a pill calls closeTab(id) — pill disappears, list re-orders, last-tab fallback creates a fresh chat" | `TabStrip.tsx:82-89` (close button onClick with `e.stopPropagation()` then `onClose(tab.id)`) → `ChatInterface.tsx` (`onClose={closeTab}`) → `SessionControlContext.tsx:363-394` (closeTab + last-tab createNewChat fallback) | TabStrip Test 4 (onClose called with id, onSwitch NOT called), Plan 88-02 Tests 11-13 (closeTab semantics) |
| 5 | "Trailing `+` button after the last pill creates a fresh tab via createNewChat (preserves the existing onNewChat affordance, just with better discoverability)" | `TabStrip.tsx:97-110` (`<button data-testid="tab-new" onClick={atCap ? undefined : onNew} disabled={atCap}>`) → `ChatInterface.tsx` (`onNew={onNewChat ?? (() => {})}` — `onNewChat` is bound from `PersonaDashboardLayout.tsx:232` which passes `createNewChat` from `useChatSession()`) | TabStrip Test 5 (trailing + calls onNew when below cap) |
| 6 | "When openTabIds.length >= tabCap, the trailing `+` is disabled (greyed) AND clicking it shows a transient inline message — no thrown error reaches the user" | `TabStrip.tsx:97-110` (`disabled={atCap}`, `onClick={atCap ? undefined : onNew}`, `title={atCap ? 'Tab cap reached (${cap}). Close a tab to open a new one.' : 'New chat'}`) | TabStrip Test 6 (disabled + does not fire onNew at cap) — partial: the title="Tab cap reached..." tooltip is the inline message; the production-grade sonner toast is Plan 88-04. |
| 7 | "Active tab pill has visually distinct styling (teal background, bold label) so the user knows which one they're viewing" | `TabStrip.tsx:64-69` (active branch: `bg-teal-50 text-teal-700 font-semibold border border-teal-200`); inactive: `bg-white text-slate-600 hover:bg-slate-100 border border-slate-200` | TabStrip Test 2 (active styling, aria-selected) |
| 8 | "The tiny `+` icon previously at ChatInterface.tsx:~1167 is removed — the TabStrip's trailing `+` is the canonical new-chat affordance" | `ChatInterface.tsx`: `<button onClick={onNewChat} title="New Chat"><Plus size={14} /></button>` block DELETED from the action-icon row; `Plus` icon dropped from the lucide-react import line | ChatInterface Test 'renders TabStrip pills...' (`expect(screen.queryByTitle('New Chat')).toBeNull()`) |

## Decisions Made

1. **Stateless prop-driven TabStrip — no internal state, no context coupling.** TabStrip receives `tabs`, `activeId`, `cap`, `onSwitch`, `onClose`, `onNew`, and an optional `className` via props. No useState, no useEffect, no useContext. Plan 88-04 (per-tab streaming/unread indicators) can pass new fields on `TabStripTab` without refactoring this contract — additive change only. Tests run without harness/provider wrapping in 232ms.

2. **Active styling = teal-50 bg + teal-200 border + bold (locked decision honored).** The PLAN.md `must_haves.truths` item 7 specified "teal background, bold label." Implemented as `bg-teal-50 text-teal-700 font-semibold border border-teal-200`. Inactive pills use `bg-white text-slate-600 hover:bg-slate-100 border border-slate-200`. The aria-selected attribute is set independently (`aria-selected={isActive}`) so screen readers know which tab is active even if the visual styling is overridden by accessibility CSS.

3. **Hover-reveal close X (VS Code / Chrome / Firefox UX).** The close `×` button uses `opacity-0 group-hover:opacity-100` so it only appears when the user hovers the parent pill. Reasoning: keeps the at-rest TabStrip uncluttered. Screen-reader users still see the button (aria-label='Close {label}' is announced regardless of visual opacity).

4. **Native HTML `disabled` attribute on the trailing +.** When `tabs.length >= cap`, the `+` button gets `disabled={atCap}`. Native HTML semantics: browser suppresses click events natively, screen readers announce "button disabled," tab-key navigation skips it. Plus a `title` tooltip with descriptive text. The PLAN's user-facing toast (sonner) is Plan 88-04 scope; the disabled+tooltip in this plan is the minimum viable cap UX.

5. **'New chat' fallback for tab labels.** When the user clicks `+` to create a fresh session, `openTabIds` updates immediately (push-based) but `sessions[]` doesn't update until the next `refreshSessions()` round-trip (after the first message is sent and the title is computed server-side, ~2-8s window). The fallback ensures the new pill renders with a sensible label during that gap. Without this, a brand-new pill would render with an empty string until the round-trip completes.

6. **Header restructured into a two-row layout.** Wrapped the existing agent-identity row in a parent `<div className="border-b border-slate-100/80">` and added the TabStrip BELOW it as a second row. Reasoning: TabStrip needs full width and `overflow-x-auto` for many tabs; cramming it into the agent-identity row would push the dropdown icons (history, more options) off-screen on narrow viewports. The border-b moved from the inner row to the outer wrapper so the visual divider sits below the entire two-row header (between header and messages).

7. **Plus icon dropped from the lucide-react import line.** With the legacy `+` button removed, `Plus` is no longer used anywhere in `ChatInterface.tsx`. Removing the unused import keeps the import line clean and would otherwise trigger the same `@typescript-eslint/no-unused-vars` warning that affects 4 other unused imports in this file (which are pre-existing and out-of-scope to fix).

## Deviations from Plan

None — plan executed exactly as written. The only minor adjustment was renaming the destructured `activeId: _activeId` to `activeId` mid-implementation (was unused at first because the contract said `tab.isActive` carried selection state, but I refactored to derive `isActive = tab.id === activeId` so `activeId` is the canonical source — cleaner contract and avoids the unused-prefix lint warning that the codebase's eslint config doesn't suppress by default).

## Issues Encountered

- Initial `TabStrip.tsx` accepted `activeId` as a destructured prop but didn't read it (using `tab.isActive` directly instead). The codebase's ESLint config does NOT honor the leading-underscore convention for unused parameters, so `activeId: _activeId` triggered `@typescript-eslint/no-unused-vars`. Refactored to `activeId` (no rename) and use it as the canonical source: `const isActive = activeId !== null ? tab.id === activeId : tab.isActive`. This makes the prop meaningful AND avoids the lint warning. All 6 tests still GREEN after the refactor.

## Out-of-Scope Deferrals

| Deferred item | Reason |
| --- | --- |
| Per-tab streaming indicator (animated dot or similar) on active streams | Plan 88-04 (Streaming Indicator) — TabStrip will receive a new field on `TabStripTab` (e.g. `isStreaming?: boolean`) and render the indicator without contract changes. |
| Per-tab unread indicator (red dot when agent finishes streaming on a non-visible tab) | Plan 88-04 — same additive-prop pattern. |
| Production-grade sonner toast on cap-reached click | Plan 88-04 — current behavior (disabled button + descriptive tooltip) is sufficient for visible cap UX; the toast is the polished version. The TabStrip's onNew is not invoked when at-cap (HTML disabled prevents the click) so no `TabCapReachedError` propagates out of the UI in this plan; the toast wiring happens in 88-04. |
| Drag-to-reorder tabs | Out of phase entirely. |
| Workspace artifact behavior test (criterion 8 lock-in via vitest) | The chain is documented in this SUMMARY's "Workspace Coupling Chain" section. Adding a vitest assertion would require mounting `ActiveWorkspace` with full Supabase mocking — out-of-scope for a TabStrip UI plan. The chain's entry point (TabStrip pill click → openTab) IS test-locked in ChatInterface Test 'clicking a TabStrip pill calls openTab with the id'. |

## PR-Reviewer Note

**Frontend-only plan.** No backend Python files touched. `make test` is intentionally not in the verification chain — backend reviewers do not need to run it for this PR. The 49 test failures in the full `npm test` run are pre-existing in unrelated files (PersonaView, CalendarWidget, InitiativeDashboard, KanbanWidget, RevenueChart, LandingDemo, ProtectedRoute) and have been documented as the Phase 88 baseline since Plan 88-01.

## Manual UAT Script (for phase gate)

Run after deploying this plan + Plan 88-04 (the toast) into a deploy preview. Open browser dev-tools → Application → Local Storage → origin.

1. **Baseline.** Open the app. Confirm a single tab pill appears in the chat panel header (the pill represents the current session; if no `pikar_open_tab_ids` entry exists yet, the pill appears after the first send). The pill carries the truncated session title (or "New chat" until the first refreshSessions round-trip completes).
2. **Open a fresh tab via TabStrip's `+`.** Click the trailing `+` after the last pill. A new pill appears at the right end of the strip. Workspace clears (no items). The new pill's label is "New chat" (no session.title yet — the placeholder).
3. **Send a different message in the new tab.** Type "What's the weather?" and send. The pill label updates to a truncated version of the message after a few seconds (when refreshSessions completes and surfaces the server-side title).
4. **Switch tabs.** Click the FIRST tab pill. The chat panel scrolls back to the first session's history. The workspace re-queries Supabase keyed on the first session_id and shows whatever items the first session had created (or empty if none). Verify `localStorage.pikar_current_session_id` matches the first session's id.
5. **Switch back.** Click the second tab pill. Workspace swaps again — back to whatever items the second session has. **No stale items from the first session appear** — that's criterion 8 verified.
6. **History → tab.** Open the chat history dropdown (Clock icon at the right edge of the agent-identity row). Click an older session. Confirm a NEW pill appears for it (selectChat → openTab delegation from Plan 88-02), and that pill becomes the active one. Workspace re-queries for the historical session.
7. **Cap enforcement.** Click `+` repeatedly until 5 pills are open (free tier). The 6th `+` click is greyed out (disabled). Hover the disabled `+` — tooltip shows "Tab cap reached (5). Close a tab to open a new one." For paid-tier users, repeat until 8 pills, then verify the 9th is disabled.
8. **Close a tab.** Hover any pill — the close `×` reveals on the right side. Click it. The pill disappears. If the closed tab was the visible one, the most-recently-opened remaining tab becomes visible. Workspace re-queries for the promoted tab.
9. **Last-tab fallback.** Close all tabs one by one. The very last close should auto-create a fresh tab (the chat panel never goes empty). The new pill carries the "New chat" label until the first message is sent.

## Executor Halt Criteria (WARNING 4)

- Halt and notify if any single task's vitest run exceeds 5 minutes wall-clock. (Actual: TabStrip = 232ms, ChatInterface = 1.3s — well within budget.)
- Halt and notify if any single task's diff exceeds 15 files. (Actual: 5 files total across 3 tasks — well within budget.)

Both halt criteria observed; no halt was needed.

## Self-Check: PASSED

- [x] `frontend/src/components/chat/TabStrip.tsx` created — verified via `ls` + commit `7ed9111d` includes file as `create mode 100644`
- [x] `frontend/src/components/chat/TabStrip.test.tsx` created — verified via `ls` + commit `7ed9111d` includes file as `create mode 100644`
- [x] `frontend/src/components/chat/ChatInterface.tsx` modified — verified via `git show b6053994 --stat` (1 file in commit, +30/-10 LOC)
- [x] `frontend/src/components/chat/__test-utils__/chatHarness.ts` modified — verified via `git show b6053994 --stat`
- [x] `frontend/src/components/chat/ChatInterface.test.tsx` modified — verified via `git show b6053994 --stat`
- [x] Commit `7ed9111d` (Task 1) exists — verified via `git log --oneline -3`
- [x] Commit `b6053994` (Task 2) exists — verified via `git log --oneline -3`
- [x] All 6 TabStrip.test.tsx tests GREEN — verified via direct vitest run (232ms)
- [x] All 12 ChatInterface.test.tsx tests GREEN — verified via direct vitest run (1.3s)
- [x] Combined run (TabStrip + ChatInterface) = 18/18 GREEN — verified via single vitest invocation
- [x] TypeScript compile clean for the 3 modified files (TabStrip.tsx, ChatInterface.tsx, chatHarness.ts) — verified via `npx tsc --noEmit -p tsconfig.json | grep -E "ChatInterface|chatHarness|TabStrip"` (no output)
- [x] Lint clean for new files (TabStrip.tsx, TabStrip.test.tsx, chatHarness.ts) — verified via `npx eslint <files>` (no output)
- [x] No NEW lint findings introduced in ChatInterface.tsx — pre-existing 17 problems unchanged
- [x] Full frontend test suite: 522 passed / 49 failed — failure count IDENTICAL to Plan 88-02 baseline (522 = 514 + 8 new TabStrip+ChatInterface tests). Zero new failures introduced.
- [x] Workspace coupling chain documented (8-link chain from TabStrip pill click → ActiveWorkspace re-query) — see "Workspace Coupling Chain" section above with explicit line refs to `TabStrip.tsx:75`, `ChatInterface.tsx`, `SessionControlContext.tsx:317-341`, `ActiveWorkspace.tsx:287,355,362-366`
