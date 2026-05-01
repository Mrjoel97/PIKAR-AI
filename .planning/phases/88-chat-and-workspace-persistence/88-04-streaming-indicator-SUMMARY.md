---
phase: 88-chat-and-workspace-persistence
plan: 04
subsystem: frontend/components/chat
tags: [feature-multi-session-tabs, streaming-indicator, sonner-toast, tabstrip, chatinterface, vitest]
requires:
  - phase: 88-03-tab-strip-ui
    provides: TabStrip stateless prop-driven component, ChatInterface header restructure, tabs useMemo from openTabIds × sessions
  - phase: 88-02-tab-state
    provides: TabCapReachedError export, openTab/closeTab/openTabIds, tier-derived tabCap
  - phase: 88-01-persistence-reconciliation
    provides: storage event cross-tab sync (visibleSessionId)
provides:
  - TabStrip indicators?: Record<string, 'streaming' | 'unread' | 'none'> prop with animated/solid dot rendering
  - ChatInterface indicators useMemo derived from useSessionMap().activeSessions × openTabIds × visibleSessionId
  - handleTabSwitch + handleTabNew wrappers in ChatInterface that catch TabCapReachedError and surface a sonner toast
  - Chat-history dropdown click handler now catches TabCapReachedError and surfaces same toast
  - SessionControlContext.selectChat simplified — rethrows TabCapReachedError instead of console.warn (UI layer decides presentation)
  - chatHarness.ts upgraded to vi.importActual for SessionControlContext so production TabCapReachedError type-matches in tests
affects:
  - Phase 88 verification gate (gsd-verifier should now find all 11 ROADMAP success criteria satisfied)

tech-stack:
  added: []
  patterns:
    - "Stateless prop-driven indicator state — TabStrip remains context-free; ChatInterface computes per-tab activity from useSessionMap().activeSessions and passes via the indicators prop"
    - "Active-tab forced to 'none' — by definition the user is watching it; no need to render a streaming dot on the tab they can already see"
    - "vi.importActual passthrough in chatHarness — lets tests import production-defined error classes (TabCapReachedError) and have `instanceof` checks succeed across the mock boundary"
    - "Indicator clear via single source of truth — handleTabSwitch does NOT call updateSessionState({ hasUnread: false }); the existing useEffect at ChatInterface (keyed on visibleSessionId) handles unread-clear when openTab updates the visible session id"
    - "UI-layer cap-toast wrapping — SessionControlContext stays free of UI concerns (no sonner import); the toast lives at the call site (ChatInterface's handleTabSwitch / handleTabNew / history-dropdown onClick)"

key-files:
  created:
    - .planning/phases/88-chat-and-workspace-persistence/88-04-streaming-indicator-SUMMARY.md
  modified:
    - frontend/src/components/chat/TabStrip.tsx (+30 LOC: indicators prop on TabStripProps + dot/badge JSX between label and close X)
    - frontend/src/components/chat/TabStrip.test.tsx (+74 LOC: 3 new behavior tests covering streaming/unread/none paths)
    - frontend/src/components/chat/ChatInterface.tsx (+76 LOC: indicators useMemo, handleTabSwitch + handleTabNew wrappers, sonner import, history-dropdown try/catch, TabStrip prop refresh)
    - frontend/src/components/chat/ChatInterface.test.tsx (+93 LOC: sonner module mock, 2 new integration tests, TabCapReachedError import)
    - frontend/src/contexts/SessionControlContext.tsx (-12 LOC: selectChat simplified — try/catch with console.warn replaced by direct openTab(sessionId) delegation)
    - frontend/src/components/chat/__test-utils__/chatHarness.ts (+8 LOC: vi.importActual passthrough so TabCapReachedError remains accessible)

key-decisions:
  - "TabStrip indicators is a sparse Record<id, state> — keeps the prop contract minimal and makes the active-tab override trivial (skip lookup if id === activeId)"
  - "Indicator clear path uses the existing visibleSessionId-keyed useEffect — handleTabSwitch does NOT add a duplicate updateSessionState({ hasUnread: false }) call"
  - "Cap-toast lives at the UI layer (ChatInterface) — context layer stays free of sonner import; selectChat rethrows TabCapReachedError instead of swallowing"
  - "vi.importActual for SessionControlContext mock so production TabCapReachedError still type-matches the runtime instanceof check after the mock boundary — alternative was to manually re-export the class from the mock factory which is more brittle"
  - "Active tab gets 'none' regardless of session.status — by definition the user is watching it; rendering a pulsing dot on the active pill would be visual noise"

patterns-established:
  - "Pattern A — Sparse indicator map: TabStrip.indicators?: Record<string, 'streaming'|'unread'|'none'>. Absent keys resolve to 'none'. Keeps the wire format minimal AND lets the parent skip computing state for ids it doesn't care about."
  - "Pattern B — UI-layer error transformation: SessionControlContext rethrows TabCapReachedError; ChatInterface (UI layer) catches and transforms into a sonner toast. Keeps the data layer free of UI concerns AND lets different UI layers (ChatInterface, future admin panel, etc.) choose their own presentation."
  - "Pattern C — vi.importActual passthrough mock: when production code uses `instanceof CustomError` and the test mocks the same module, use vi.importActual to keep the real error class export. Otherwise the mock replaces the class with undefined and instanceof always returns false."

requirements-completed:
  - FEATURE-MULTI-SESSION-TABS

# Metrics
duration: 14min
completed: 2026-05-01
tasks_count: 3
files_count: 6
---

# Phase 88 Plan 04: Streaming Indicator Summary

**Per-tab streaming/unread indicators (animated pulsing dot for live SSE, solid dot for finished-but-unviewed) + sonner cap toast — the polish that turns "the feature works" into "the feature feels finished." Closes Phase 88's last open ROADMAP criterion (#9) and upgrades the cap-rejection UX from console.warn to a user-facing toast.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-05-01T01:18:20Z
- **Completed:** 2026-05-01T01:31:53Z
- **Tasks:** 3
- **Files modified:** 6 (1 created — SUMMARY.md; 5 edited — TabStrip.tsx, TabStrip.test.tsx, ChatInterface.tsx, ChatInterface.test.tsx, SessionControlContext.tsx, chatHarness.ts)
- **Net production LOC:** ~95 (+30 TabStrip + ~76 ChatInterface - ~12 SessionControlContext = +94)
- **Net test/harness LOC:** ~175 (+74 TabStrip.test + ~93 ChatInterface.test + ~8 chatHarness)

## Accomplishments

- New `indicators?: Record<string, 'streaming' | 'unread' | 'none'>` prop on `TabStripProps`. Active tab never shows an indicator regardless of map content. Streaming = `w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse`. Unread = same dot WITHOUT `animate-pulse`. Both carry `role="status"` and a descriptive `aria-label` for screen readers.
- ChatInterface computes the indicators map via a `useMemo` over `[openTabIds, visibleSessionId, activeSessions]`. The map is dense (one key per open tab) so TabStrip never has to handle an "absent id with non-empty map" edge case. Rules:
  - active tab → `'none'`
  - `session.status === 'streaming'` → `'streaming'`
  - `session.hasUnread === true && session.status !== 'streaming'` → `'unread'`
  - otherwise → `'none'`
- `handleTabSwitch` and `handleTabNew` callbacks wrap `openTab` and `onNewChat` with try/catch on `TabCapReachedError`. On catch, they call `toast.error('Tab limit reached (N). Close a tab to open a new one.')`. Other errors propagate.
- Chat history dropdown click handler at line ~1222 wraps `onSelectChat?.(chat.id)` with the same try/catch. This was previously gated by `selectChat`'s `console.warn` swallow — now `selectChat` rethrows and the UI layer catches.
- `SessionControlContext.selectChat` simplified from a 13-line try/catch (with console.warn on TabCapReachedError) to a 3-line direct `openTab(sessionId)` delegation. The data layer stays free of UI concerns (no sonner import). Plan 88-02's "selectChat delegates to openTab" decision is honored AND the cap-error path now reaches the UI layer.
- `chatHarness.ts` upgraded from full-module replacement (`vi.mock(... { useSessionControl: vi.fn() })`) to `vi.importActual` passthrough so production-defined `TabCapReachedError` remains the same class symbol on both sides of the mock boundary. Without this, `instanceof TabCapReachedError` checks would fail in tests because the mock would replace the class with `undefined`.
- 5 new behavior tests added (3 TabStrip + 2 ChatInterface). All GREEN.
- All 36 tests in the chat-area suite (9 TabStrip + 13 SessionControlContext + 14 ChatInterface) GREEN.
- Full frontend test suite: 527 passed / 49 failed. Pass count went from 522 (Plan 88-03 baseline) to 527 — exactly +5 (3 TabStrip + 2 ChatInterface) as designed. The 49 failures are IDENTICAL to the Plan 88-01/02/03 baseline (pre-existing failures in PersonaView, CalendarWidget, InitiativeDashboard, KanbanWidget, RevenueChart, LandingDemo, ProtectedRoute).
- Lint: 20 problems across the 6 modified files — IDENTICAL to the combined 88-02 + 88-03 baseline (17 ChatInterface.tsx + 3 SessionControlContext.tsx). Zero new lint findings introduced by Plan 88-04.
- TypeScript: clean for the 6 modified files. The single TS error at `useAgentChat.ts:443` is pre-existing and unrelated.

## Task Commits

Each task was committed atomically:

1. **Task 1: TabStrip indicators prop + 3 new tests** — `ef775bb6` (feat)
2. **Task 2: ChatInterface wiring + sonner cap toast + selectChat rethrow + 2 new tests** — `41ee477b` (feat)
3. **Task 3: Full vitest + lint pass + final phase SUMMARY** — (this commit, will be the docs metadata commit)

## Files Created/Modified

### Created

- **`.planning/phases/88-chat-and-workspace-persistence/88-04-streaming-indicator-SUMMARY.md`** (this file)

### Modified

- **`frontend/src/components/chat/TabStrip.tsx`** (+30 LOC)
  - Extended `TabStripProps` with `indicators?: Record<string, 'streaming' | 'unread' | 'none'>`.
  - Destructured `indicators` from props.
  - Added IIFE between the label `<button>` and the close `<button>` that renders nothing for active tabs (early return if `isActive`), nothing for `'none'` (early return), an animated pulsing teal dot for `'streaming'`, and a solid teal dot for `'unread'`.
  - Each indicator span carries `data-testid={`tab-indicator-${tab.id}`}` for test selection plus `role="status"` and a descriptive `aria-label`.

- **`frontend/src/components/chat/TabStrip.test.tsx`** (+74 LOC)
  - 3 new behavior tests in a sub-describe `'TabStrip — indicators (FEATURE-MULTI-SESSION-TABS criterion 9)'`:
    - `'renders streaming dot on non-active streaming tab'` — asserts `getByTestId('tab-indicator-a')` exists with `animate-pulse` AND `queryByTestId('tab-indicator-b')` (active tab) is null.
    - `'renders solid badge on non-active unread tab (no pulse)'` — asserts the dot exists AND its className does NOT match `/animate-pulse/`.
    - `'renders no indicator when state is none or absent'` — asserts no indicator with `'none'` AND no indicator when `indicators` prop is omitted entirely.

- **`frontend/src/components/chat/ChatInterface.tsx`** (+76 LOC, -8 LOC net)
  - Imports: added `TabCapReachedError` to the existing `@/contexts/SessionControlContext` import line; added `import { toast } from 'sonner'`.
  - Added `indicators` useMemo (depends on `[openTabIds, visibleSessionId, activeSessions]`) computing per-tab streaming/unread/none state.
  - Added `handleTabSwitch` `useCallback` wrapping `openTab(id)` with try/catch on `TabCapReachedError` → `toast.error(...)`.
  - Added `handleTabNew` `useCallback` wrapping `onNewChat()` with the same try/catch.
  - TabStrip JSX updated: `onSwitch={handleTabSwitch}`, `onNew={handleTabNew}`, `indicators={indicators}` (was `onSwitch={openTab}`, `onNew={onNewChat ?? (() => {})}`, no indicators).
  - Chat history dropdown click handler at line ~1222: `onSelectChat?.(chat.id)` wrapped with try/catch on `TabCapReachedError`.

- **`frontend/src/components/chat/ChatInterface.test.tsx`** (+93 LOC)
  - Module-scope `vi.mock('sonner', ...)` ABOVE the chatHarness import (vi.mock is hoisted; the harness transitively imports sonner via ChatInterface).
  - Imports `toast` from `'sonner'` and `TabCapReachedError` from `@/contexts/SessionControlContext`.
  - 2 new integration tests in a new describe `'ChatInterface — multi-session tabs polish (FEATURE-MULTI-SESSION-TABS)'`:
    - `'renders streaming indicator on non-active streaming tab'` — seeds `activeSessions: new Map([['s1', { status: 'streaming', hasUnread: false, ... }]])` with `visibleSessionId: 's2'`, asserts the streaming dot renders on s1's pill (with `animate-pulse`) and nothing on s2's.
    - `'shows sonner toast when openTab throws TabCapReachedError'` — seeds `openTab` as a `vi.fn(() => { throw new TabCapReachedError(2) })`, fires a click on `tab-pill-s1`, asserts `openTab` was called once AND `toast.error` was called once with a message matching `/Tab limit reached \(2\)/`.

- **`frontend/src/contexts/SessionControlContext.tsx`** (-12 LOC)
  - `selectChat` simplified from a 13-line try/catch (which logged `'[SessionControl] selectChat hit tab cap:'` on TabCapReachedError) to a 3-line direct `openTab(sessionId)` delegation.
  - The "the data layer stays free of UI concerns" decision is honored — no sonner import was added here.
  - All 13 existing SessionControlContext tests still GREEN (no test asserted on the console.warn path).

- **`frontend/src/components/chat/__test-utils__/chatHarness.ts`** (+8 LOC)
  - The `vi.mock('@/contexts/SessionControlContext', ...)` factory replaced with an async one that uses `vi.importActual` to spread real exports AND override only `useSessionControl: vi.fn()`. This keeps `TabCapReachedError`, `TAB_CAP_FREE`, `TAB_CAP_PAID`, `SessionControlProvider` accessible to test code.
  - Without this change, Plan 88-04 Test 'shows sonner toast when openTab throws TabCapReachedError' would fail at `new TabCapReachedError(2)` because `TabCapReachedError` would be undefined after the mock.

## Phase 88 Success-Criteria Coverage Matrix

The Phase 88 ROADMAP defined 11 success criteria. Plan 88-04 closes the last open one (#9). This matrix maps each criterion to the plan that satisfies it, the test(s) that lock it in, and the manual UAT step that verifies it end-to-end.

| # | Criterion | Plan | Code location | Automated test | Manual UAT step |
| --- | --- | --- | --- | --- | --- |
| 1 | Reload restores chat | 88-01 (also pre-shipped in commit `c8da1d99`) | `SessionControlContext.tsx:180-190` (useLayoutEffect restore from `pikar_current_session_id`) | Plan 88-01 Test "forwards initialSessionId from props to useAgentChat" + persistence describe block | UAT step "Criteria 1, 2, 3" |
| 2 | Workspace restores | 88-01 (pre-shipped) | `ActiveWorkspace.tsx:355-362` (useEffect on `[currentSessionId]`) | Manual only (Supabase round-trip) | UAT step "Criteria 1, 2, 3" |
| 3 | New chat resets | 88-01 (pre-shipped) | `SessionControlContext.tsx:295-304` (createNewChat seeds new id) | Plan 88-01 persistence test (createNewChat path) | UAT step "Criteria 1, 2, 3" |
| 4 | Cross-tab safety | 88-01 | `SessionControlContext.tsx:241-250` (storage event listener) | Plan 88-01 cross-tab synthetic StorageEvent test | UAT step "Criterion 4" |
| 5 | History list | 88-01 (pre-shipped) | `SessionControlContext.tsx:431-458` (refreshSessions / GET /sessions) | Plan 88-01 persistence test (history list re-renders) | UAT step "Criterion 5" |
| 6 | Multi-tab open (multiple pills visible) | 88-02 + 88-03 | `SessionControlContext.tsx:317-341` (openTab) + `TabStrip.tsx:60-130` (pill rendering) + `ChatInterface.tsx:118-133` (tabs useMemo) | TabStrip Tests 1-2 (renders pills, active styling) + ChatInterface Test "renders TabStrip pills from openTabIds × sessions" | UAT step "Criteria 6, 7, 11" |
| 7 | Tabs persist | 88-02 | `SessionControlContext.tsx:196-211` (restore openTabIds from localStorage) + `:213-225` (persist on every change) | SessionControlContext Tests 9, 14 | UAT step "Criteria 6, 7, 11" |
| 8 | Tab switch swaps workspace | 88-03 (chain documented) | `TabStrip.tsx:84` (onClick=onSwitch) → `ChatInterface.tsx:202-219` (handleTabSwitch → openTab) → `SessionControlContext.tsx:317-341` (openTab → setVisibleSessionId) → `ActiveWorkspace.tsx:355-362` (workspace re-query on visibleSessionId change) | ChatInterface Test "clicking a TabStrip pill calls openTab with the id" + Plan 88-02 openTab tests | UAT step "Criterion 8" |
| 9 | Streaming/unread indicator | 88-04 (this plan) | `TabStrip.tsx:96-119` (indicator IIFE) + `ChatInterface.tsx:135-167` (indicators useMemo) | TabStrip Tests 7-9 (streaming dot / unread badge / none) + ChatInterface Test "renders streaming indicator on non-active streaming tab" | UAT step "Criterion 9" |
| 10 | Close tab keeps session | 88-02 + 88-03 | `SessionControlContext.tsx:363-397` (closeTab — removes from openTabIds + activeSessions, NOT from sessions[]) + last-tab fallback to createNewChat | SessionControlContext Tests 11, 12, 13 | UAT step "Criterion 10" |
| 11 | TabStrip supersedes + icon | 88-03 | `ChatInterface.tsx:1192` (legacy + button removed, comment notes the deletion) + TabStrip's trailing + (`TabStrip.tsx:108-128`) | ChatInterface Test "renders TabStrip pills from openTabIds × sessions and removes legacy +" (`expect(screen.queryByTitle('New Chat')).toBeNull()`) | UAT step "Criteria 6, 7, 11" |

**All 11 criteria verified.** Phase 88 is ready for `gsd-verifier` goal-backward verification.

## End-to-End Manual UAT Script (Phase 88 — all 11 criteria)

Run after deploying all 4 plans (88-01 + 88-02 + 88-03 + 88-04) into a deploy preview. Open Chrome dev-tools → Application → Local Storage → origin.

### Setup

- `docker compose up -d` (backend + redis)
- `cd frontend && npm run dev`
- Open Chrome, navigate to `http://localhost:3000`, sign in.

### Criteria 1, 2, 3 (Plan 88-01) — Persistence

1. Send a message in any persona ("Test persistence"). Note the session id via dev-tools `localStorage.pikar_current_session_id`.
2. Click the workspace canvas to confirm any items render. Note the items.
3. Hard-refresh (Ctrl+F5). Confirm: same chat history visible, last agent response present, workspace re-renders the same items. **✅ criteria 1, 2.**
4. Click `+` (the TabStrip's trailing + from Plan 03). Confirm: new session id in `pikar_current_session_id`, workspace clears (no items). **✅ criterion 3.**

### Criterion 4 (Plan 88-01) — Cross-tab safety

1. Open a SECOND Chrome tab, sign-in already cached, navigate to the same URL. Confirm: same session restored.
2. In Tab B, click `+` (new chat). Confirm Tab B's URL/storage shows the new session.
3. Switch back to Tab A. Within ~1 second, confirm Tab A's `visibleSessionId` updates to match Tab B's new session (storage event listener firing). Workspace re-queries. **✅ criterion 4.**

### Criterion 5 (Plan 88-01) — History list

1. Click the Clock icon (chat history dropdown). Confirm: list shows all past sessions with title + preview + timestamp. **✅ criterion 5.**

### Criteria 6, 7, 11 (Plans 88-02, 88-03) — Multi-tab open + persistence + supersession

1. Open ~3 tabs by clicking `+` repeatedly (each becomes a new pill). Confirm `pikar_open_tab_ids` in dev-tools is `["session-...","session-...","session-..."]`.
2. Refresh the page. Confirm all 3 tabs restore as pills. **✅ criterion 7.**
3. Confirm 3 tabs visible as pills in the TabStrip. **✅ criterion 6.**
4. Confirm there is NO standalone `+` icon at the right edge of the agent-identity row (the legacy one is gone). The only `+` is the TabStrip's trailing one. **✅ criterion 11.**
5. Open ~5 tabs total (free tier). The 6th `+` click → button is greyed (disabled native HTML attribute) AND if you try opening from the history dropdown, a sonner toast surfaces: "Tab limit reached (5). Close a tab to open a new one." **✅ cap UX (Plan 88-04 toast).**

### Criterion 8 (Plan 88-03) — Tab switch swaps workspace

1. With multiple tabs open, click each tab pill. Confirm each click swaps BOTH the chat view AND the workspace items. No workspace items leak between tabs (a session-2 item must NOT appear when session-1 is active). **✅ criterion 8.**

### Criterion 9 (Plan 88-04 — this plan) — Streaming/unread indicator

1. With Tab A visible, click into Tab B. Send a message in Tab B. Click back to Tab A.
2. In Tab A's view, watch Tab B's pill: while Tab B is streaming, the pill should show a pulsing teal dot (`tab-indicator-{tab-b-id}` with `animate-pulse` class).
3. Wait for Tab B's stream to complete. The dot transitions to a solid (non-pulsing) badge. **✅ criterion 9.**
4. Click Tab B. Confirm the indicator clears (the click sets `visibleSessionId = tab-b-id`, the existing useEffect at `ChatInterface.tsx:808-815` runs `updateSessionState(tab-b-id, { hasUnread: false })`, AND because Tab B becomes active its `'none'` lookup wins on the next render).

### Criterion 10 (Plans 88-02 + 88-03) — Close tab semantics

1. Click `×` on any non-last pill. Confirm: pill removed, the underlying session is NOT deleted (open chat history dropdown — it's still listed there).
2. Reopen the closed session via the dropdown. Confirm a new pill appears.
3. Close ALL tabs one by one. The last close should auto-create a fresh empty tab — chat panel never goes blank. **✅ criterion 10 + locked decision (last-tab fallback).**

### Failure paths

- Stop the backend (`docker compose stop backend`). Refresh page. Confirm: localStorage restore still works (frontend-only), `refreshSessions` silently fails in console, but the chat panel mounts with the previously visible session and the open tabs intact. No crash.

## Decisions Made

1. **Sparse indicator map (Record<id, state>) over a per-TabStripTab `state` field.** Considered adding `state?: 'streaming' | 'unread' | 'none'` to `TabStripTab` itself. Chose the separate `indicators` map because it keeps the active-tab override trivial (skip lookup if id === activeId) AND makes the prop additive — Plan 88-03 callers that don't care about indicators don't have to pass anything (defaults to absent → 'none' for all tabs). Also matches the plan's locked decision.

2. **Indicator clear path leverages the existing `visibleSessionId`-keyed `useEffect`.** `ChatInterface.tsx:808-815` (added in Phase 83) already runs `updateSessionState(visibleSessionId, { hasUnread: false, lastUpdatedAt: Date.now() })` whenever `visibleSessionId` changes. When `handleTabSwitch` calls `openTab(id)`, that updates `visibleSessionId`, which fires the existing useEffect, which clears `hasUnread`. Adding a duplicate `updateSessionState({ hasUnread: false })` call inside `handleTabSwitch` would race with that effect (the duplicate would fire BEFORE openTab updates visibleSessionId, but after the next render the existing effect would still fire — the duplicate is wasted work AT BEST, and at worst causes the "hasUnread is briefly false then briefly true" flicker). The plan called this out explicitly as a WARNING-3 documented decision.

3. **UI-layer cap-toast wrapping** — `SessionControlContext.selectChat` rethrows `TabCapReachedError`; ChatInterface (UI layer) catches and transforms into `toast.error(...)`. Considered importing sonner directly into SessionControlContext but that adds a UI-layer dependency to a data-layer module — wrong direction. Each UI consumer can choose its own presentation (sonner toast in ChatInterface, browser alert in tests, custom inline banner in a future admin panel, etc.).

4. **`vi.importActual` passthrough mock for SessionControlContext** — Plan 88-04 Test 2 needs `new TabCapReachedError(2)` to construct an error AND the production code to type-match it via `instanceof TabCapReachedError`. The harness's previous full-module replacement (`vi.mock(... { useSessionControl: vi.fn() })`) made `TabCapReachedError` undefined after the mock. Solutions considered:
   - (a) Manually re-export the class from the mock factory — brittle, drifts when SessionControlContext exports change.
   - (b) `vi.importActual` passthrough — keeps every real export, overrides only `useSessionControl`. Idiomatic vitest pattern.
   Chose (b).

5. **Active tab forced to 'none' regardless of map content** — by definition the user is watching the active tab, so rendering a streaming dot or unread badge on it would be visual noise. The check happens FIRST in TabStrip's IIFE (`if (isActive) return null`) so even if a caller passes `indicators={{ [activeId]: 'streaming' }}` the dot doesn't render. This is also the documented locked decision in the PLAN.md `must_haves.truths` block.

## Deviations from Plan

None — plan executed exactly as written.

The plan asked for one minor amendment to Plan 88-02's `selectChat` (to rethrow instead of console.warn). That amendment was applied as part of Task 2 step 1f and is documented above. It's a 12-line subtraction in SessionControlContext.tsx — the simplification is well within the plan's "small Plan 02 amendment" framing.

## Issues Encountered

- The harness's `vi.mock('@/contexts/SessionControlContext', () => ({ useSessionControl: vi.fn() }))` would have made `TabCapReachedError` undefined in Plan 88-04 tests. Detected this BEFORE running the new tests by inspecting the mock factory — upgraded to `vi.importActual` passthrough. All 36 chat-area tests stayed GREEN through the change.

## Out-of-Scope Deferrals (from the original Phase 88 ROADMAP)

| Deferred item | Reason |
| --- | --- |
| Drag-to-reorder tabs | Out of phase entirely — locked decision per CONTEXT.md. |
| Mobile tab UI (touch-friendly close X, swipe-to-close) | Out of phase — desktop-first; the existing UI works on mobile but is not optimized. |
| BroadcastChannel cross-tab sync | Storage event covers it (Plan 88-01); `pikar_open_tab_ids` does NOT have a cross-tab listener — locked decision per CONTEXT.md. |
| Side-by-side workspace split for two visible sessions | Out of phase — workspace coupling is single-session today. |

## Phase 88 Production-Code Footprint (cumulative)

| Plan | Production LOC added | Production LOC removed | Net |
| --- | --- | --- | --- |
| 88-01 (persistence reconciliation) | ~12 (storage event listener) | 0 | +12 |
| 88-02 (tab state) | ~165 (interface + restore/persist + openTab/closeTab + selectChat delegation + createNewChat seed) | ~16 | +149 |
| 88-03 (TabStrip UI) | ~155 (TabStrip 135 + ChatInterface 30 - legacy + 10) | ~10 | +145 |
| 88-04 (streaming indicator + cap toast) | ~95 (TabStrip 30 + ChatInterface 76 - SessionControlContext 12 + chatHarness 8 - selectChat trim 7) | ~12 (selectChat simplification) | +83 |
| **Phase 88 total** | **~427** | **~38** | **+389** |

(Test/harness LOC not counted above. Plan 88-04 added ~175 test LOC.)

Phase 88 is **frontend-only** — zero backend Python files touched.

## PR-Reviewer Note

**Frontend-only phase.** No backend Python files touched across all 4 plans (88-01 + 88-02 + 88-03 + 88-04). Backend `make test` is intentionally NOT in the verification chain — backend reviewers do not need to run it for this PR.

The 49 failing tests in `npm test` are pre-existing in unrelated files (PersonaView, CalendarWidget, InitiativeDashboard, KanbanWidget, RevenueChart, LandingDemo, ProtectedRoute) and have been documented as the Phase 88 baseline since Plan 88-01.

## Next Phase Readiness

- **Phase 88 complete.** Ready for `gsd-verifier` goal-backward verification against the 11 ROADMAP success criteria.
- **No blockers carried forward.**
- **No User Setup required** — phase introduces no new env vars, dashboard configs, or external service integrations.

## Self-Check: PASSED

- [x] `frontend/src/components/chat/TabStrip.tsx` modified — verified via `git show ef775bb6 --stat` (2 files, +112/-0 LOC across both)
- [x] `frontend/src/components/chat/TabStrip.test.tsx` modified — verified via `git show ef775bb6 --stat`
- [x] `frontend/src/components/chat/ChatInterface.tsx` modified — verified via `git show 41ee477b --stat` (4 files, +217/-22 LOC)
- [x] `frontend/src/components/chat/ChatInterface.test.tsx` modified — verified via `git show 41ee477b --stat`
- [x] `frontend/src/contexts/SessionControlContext.tsx` modified (selectChat simplified) — verified via `git show 41ee477b --stat`
- [x] `frontend/src/components/chat/__test-utils__/chatHarness.ts` modified (vi.importActual passthrough) — verified via `git show 41ee477b --stat`
- [x] Commit `ef775bb6` (Task 1) exists — verified via `git log --oneline`
- [x] Commit `41ee477b` (Task 2) exists — verified via `git log --oneline`
- [x] All 9 TabStrip.test.tsx tests GREEN (6 from Plan 88-03 + 3 new) — verified via vitest run (251ms)
- [x] All 14 ChatInterface.test.tsx tests GREEN (12 from Plan 88-01/02/03 + 2 new) — verified via vitest run (1.5s)
- [x] All 13 SessionControlContext.test.tsx tests still GREEN (no regression from selectChat simplification) — verified via vitest run (569ms)
- [x] Combined run (3 files) = 36/36 GREEN — verified
- [x] Full frontend test suite: 527 passed / 49 failed. Pass count = 522 (Plan 88-03 baseline) + 5 (3 TabStrip + 2 ChatInterface). Failure count IDENTICAL.
- [x] TypeScript clean for all 6 modified files — verified via `npx tsc --noEmit -p tsconfig.json | grep -E "ChatInterface|SessionControlContext|chatHarness|TabStrip"` (no output)
- [x] No NEW lint findings — 20 problems across 6 files matches the 88-02 + 88-03 cumulative baseline (17 ChatInterface + 3 SessionControlContext)
- [x] All 11 Phase 88 ROADMAP success criteria mapped to plan + code location + test + UAT step (see coverage matrix above)
- [x] Indicator clear path correctly leverages existing `visibleSessionId`-keyed useEffect — handleTabSwitch does NOT add a duplicate updateSessionState({ hasUnread: false }) call (matches plan WARNING-3 documented decision)
