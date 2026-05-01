---
phase: 88-chat-and-workspace-persistence
plan: 02
subsystem: frontend/contexts/session
tags: [feature-multi-session-tabs, openTabIds, tabCap, localStorage, vitest, tier-derived-cap]
requires:
  - phase: 88-01-persistence-reconciliation
    provides: SessionControlContext base, harness with sessionControl override, behavior test scaffold
provides:
  - openTabIds state + localStorage persistence under `pikar_open_tab_ids`
  - openTab/closeTab callbacks (idempotent add, cap-throw, last-tab fallback to createNewChat)
  - TabCapReachedError exported error class with `cap` property
  - Tier-derived tabCap (free=5, paid=8) pushed from useChatSession() into provider state
  - setTabCap exposed on SessionControlContext for the consumer-side override pattern
  - selectChat rewritten to delegate to openTab so history-dropdown clicks produce tab pills
  - createNewChat updated to seed new id into openTabIds
affects:
  - 88-03-tab-strip-ui (consumes openTabIds, openTab, closeTab, tabCap to render the TabStrip)
  - 88-04-streaming-indicator (consumes per-tab streaming state + max-tab toast)

tech-stack:
  added: []
  patterns:
    - "Consumer-side provider override: useChatSession() (in dashboard tree where SubscriptionProvider is mounted) reads tier and pushes tier-derived cap into root-tree provider via setTabCap"
    - "Closure-captured state for synchronous error path: openTab reads openTabIds from render closure for the cap-check rather than throwing inside a setState updater (avoids React internal re-run surprises)"
    - "Idempotent setOpenTabIds updaters: prev.includes(id) ? prev : [...prev, id] keeps duplicate-add a no-op without external pre-check"

key-files:
  created:
    - .planning/phases/88-chat-and-workspace-persistence/88-02-tab-state-SUMMARY.md
  modified:
    - frontend/src/contexts/SessionControlContext.tsx (interface +5 fields, +TabCapReachedError export, +TAB_CAP_FREE/PAID exports, +openTabIds restore/persist, +openTab/closeTab implementations, selectChat→openTab delegation, createNewChat openTabIds-seed; ~165 LOC added)
    - frontend/src/contexts/ChatSessionContext.tsx (useSubscription import, useEffect that pushes tier-derived cap via setTabCap, tabCap re-export uses desiredCap; ~30 LOC added)
    - frontend/src/contexts/__tests__/SessionControlContext.test.tsx (Tests 6-14 added; SessionMapContext mock at module scope so removeActiveSession/addActiveSession are observable; TabConsumer + clickOpen/clickClose helpers; ~265 LOC added)

key-decisions:
  - "Consumer-side override pattern for the tier-derived cap: SessionControlProvider lives at root layout (above SubscriptionProvider at dashboard layout); calling useSubscription() in the provider would throw, so useChatSession() reads tier and pushes cap into provider state"
  - "Cap throw is synchronous (NOT inside setOpenTabIds updater): React may re-run updaters during reconciliation, and a throw inside the updater can fire from an unexpected stack frame; we read openTabIds from the render closure for the pre-check"
  - "Cap floor for non-dashboard consumers: provider defaults to TAB_CAP_FREE = 5, which is the safe value for any future consumer outside the dashboard tree (e.g., admin panel, settings) where SubscriptionProvider isn't mounted"
  - "createNewChat skips cap-check: it is the LAST-RESORT fallback when closeTab empties the list, so it must always succeed even when stale localStorage had >= cap ids"
  - "Closure-captured nextOpenTabIds in closeTab: computed from openTabIds (current render's closure) BEFORE setOpenTabIds is called, so the promotion/fallback logic uses a deterministic value rather than racing with React's batched state update"

patterns-established:
  - "Pattern A — Consumer-side override: a hook called only inside a sub-tree (here useChatSession in dashboard) reads context only available there (useSubscription) and pushes derived state into a parent provider via setter. Lets the parent provider mount at a higher tree depth than its data source."
  - "Pattern B — Closure-vs-updater for synchronous error paths: when a setState callback path needs to throw to the original caller, read state from the render closure for the precondition check and throw before calling the setter; do NOT throw inside the updater function itself."

requirements-completed:
  - FEATURE-MULTI-SESSION-TABS

# Metrics
duration: 22min
completed: 2026-05-01
---

# Phase 88 Plan 02: Tab State Summary

**openTabIds + openTab/closeTab + tier-derived tabCap (5 free / 8 paid) + TabCapReachedError + localStorage persistence — the data layer for FEATURE-MULTI-SESSION-TABS, ready for Plan 03's TabStrip UI.**

## Performance

- **Duration:** 22 min (resumption only — Tasks 1+2 had been completed by a previous executor session before a rate-limit interrupt)
- **Started (resumption):** 2026-05-01T00:28:07Z
- **Completed:** 2026-05-01T00:50:26Z
- **Tasks (this resumption):** 2 (Task 3 GREEN wiring + Task 4 tier-derived cap + suite)
- **Tasks (cumulative for plan):** 4
- **Files modified (this resumption):** 2 (SessionControlContext.tsx, ChatSessionContext.tsx)
- **Files modified (cumulative):** 3 (also __tests__/SessionControlContext.test.tsx from Task 2)

## Accomplishments

- All 9 new vitest tests (Tests 6-14, GREEN gate) pass: openTab adds + idempotent + makes-visible + persists, cap throws TabCapReachedError, closeTab removes + promotes last-opened + auto-createNewChat-on-last-close, openTabIds restored from localStorage.
- All 4 Plan-01 persistence tests still GREEN (no regression).
- All 10 ChatInterface.test.tsx tests still GREEN (no regression).
- TypeScript clean for both modified contexts (SessionControlContext.tsx, ChatSessionContext.tsx).
- ESLint: zero new findings introduced; the 3 pre-existing warnings/error in SessionControlContext.tsx (sessions, setConfig, any in catch) are documented in Plan 01's deferred-issues note.
- Provider-tree mismatch resolved cleanly: useSubscription() is called only inside useChatSession() (dashboard tree), pushed into provider state via setTabCap.

## Task Commits

Each task was committed atomically:

1. **Task 1: Stub interface + TabCapReachedError export** — `d960b5a2` (feat)
2. **Task 2: RED tests for openTab/closeTab/persistence/cap** — `3155fed9` (test)
3. **Task 3: Wire openTab/closeTab/persist + GREEN gate** — `d0f46c36` (feat)
4. **Task 4: Tier-derived tab cap via useChatSession** — `6e1ac6df` (feat)

**Plan metadata commit:** (final) `docs(88-02): complete tab-state plan`

## Files Created/Modified

- `frontend/src/contexts/SessionControlContext.tsx` — interface extended with `openTabIds`, `tabCap`, `setTabCap`, `openTab`, `closeTab`; `TabCapReachedError` exported (lines 39-43); `TAB_CAP_FREE`/`TAB_CAP_PAID` exported (lines 28-31); restore-on-mount useLayoutEffect (lines 192-209); persist-on-change useEffect (lines 213-225); openTab implementation (lines 317-341); closeTab implementation (lines 363-394); selectChat delegates to openTab with TabCapReachedError catch (lines 405-418); createNewChat seeds new id into openTabIds (lines 296-303).
- `frontend/src/contexts/ChatSessionContext.tsx` — `useSubscription` import (line 14); `TAB_CAP_FREE`/`TAB_CAP_PAID` imports from SessionControlContext (lines 11-13); useChatSession reads tier, pushes desired cap via `useEffect(() => ctrl.setTabCap(desiredCap), [...])` (lines 49-58); returned `tabCap` is `desiredCap` (line 78), not `ctrl.tabCap`.
- `frontend/src/contexts/__tests__/SessionControlContext.test.tsx` — Tests 6-14 (9 new vitest cases) inside a new `'multi-session tabs (FEATURE-MULTI-SESSION-TABS)'` describe block; module-scope mock of `@/contexts/SessionMapContext` so `removeActiveSession`/`addActiveSession` are observable spies; `TabConsumer` component + `clickOpen`/`clickClose`/`readOpenTabIds` helpers.

## Decisions Made

1. **Consumer-side provider override (the provider-tree-mismatch fix)** — `SessionControlProvider` is mounted at the root layout (above `SubscriptionProvider` at the dashboard layout). Calling `useSubscription()` inside the provider would throw `useSubscription must be used within a <SubscriptionProvider>`. We solved this by exposing `setTabCap` on the context, defaulting `tabCap` to `TAB_CAP_FREE = 5` in the provider, and letting `useChatSession()` (which only ever runs inside the dashboard tree) read the tier and push the derived cap into provider state via `useEffect`. Dashboard consumers see the tier-aware cap; non-dashboard consumers (theoretical / future) get the safe `5` default.
2. **Cap throw is synchronous, OUTSIDE the setState updater** — Initial implementation threw inside the `setOpenTabIds((prev) => …)` updater. React 18+ may re-run updaters during reconciliation, and the throw fired from an unexpected stack frame (Test 10 caught the bug — error escaped the test consumer's try/catch). Refactored to read `openTabIds` from the render's closure for the cap-precondition and throw BEFORE calling `setOpenTabIds`. This is the documented React pattern for synchronous error propagation from event handlers.
3. **Closure-captured `nextOpenTabIds` in `closeTab`** — Initial implementation read the next array via the updater's `prev` and stored it in a let-binding. Tests 11-13 caught the timing bug (the let was still empty when the post-setState logic referenced it). Refactored to compute `nextOpenTabIds = openTabIds.filter(...)` from the render closure before calling the setter, so the promotion/fallback logic sees a deterministic value.
4. **`createNewChat` skips cap-check** — `createNewChat` is the last-resort fallback path triggered by `closeTab` when the list empties. Even if stale localStorage somehow had >= cap ids, we MUST be able to seed a fresh tab. The next user-initiated `openTab` enforces the cap normally.
5. **`TAB_CAP_FREE` / `TAB_CAP_PAID` exported as named constants** — keeps the magic numbers central in `SessionControlContext.tsx`. `ChatSessionContext` imports both rather than re-typing literals.

## Truth-to-Code Map

For ROADMAP traceability — each `must_haves.truths` item from the PLAN.md frontmatter to its source line range and test.

| # | Truth | Source line range | Test |
| --- | --- | --- | --- |
| 1 | "openTabIds is a string[] of session ids… persisted to localStorage key `pikar_open_tab_ids` and restored on mount" | `SessionControlContext.tsx:27` (key), `:171` (state), `:192-209` (restore), `:213-225` (persist) | Tests 9, 14 |
| 2 | "openTab(sessionId) adds the id to openTabIds (idempotent)… sets it as visibleSessionId; calling openTab when at the cap is rejected with a thrown TabCapReachedError" | `SessionControlContext.tsx:317-341` (openTab impl), `:39-43` (error class) | Tests 6, 7, 8, 10 |
| 3 | "closeTab(sessionId) removes the id from openTabIds AND from the in-memory activeSessions map; if the closed tab was the visible one, the next remaining tab becomes visible (last-opened wins); closing the LAST tab triggers createNewChat()" | `SessionControlContext.tsx:363-394` (closeTab impl), `:296-303` (createNewChat fallback path) | Tests 11, 12, 13 |
| 4 | "closeTab does NOT delete the session from Supabase — sessions remain in /sessions list" | `SessionControlContext.tsx:363-394` (no Supabase calls in closeTab; only `removeActiveSession` map cleanup) | Reviewed by code inspection — closeTab body has no `supabase.from('sessions').delete(...)` |
| 5 | "Tab cap is derived from the user's subscription tier via useSubscription called inside useChatSession() (NOT inside SessionControlProvider)… free → 5 tabs, all paid tiers → 8 tabs. Provider defaults tabCap to TAB_CAP_FREE=5 via useState; useChatSession() pushes the tier-derived value via setTabCap from a useEffect on tier change" | `SessionControlContext.tsx:172` (provider state default), `:78` (setTabCap on interface); `ChatSessionContext.tsx:14` (useSubscription import), `:49-58` (tier read + setTabCap useEffect), `:78` (returned tabCap = desiredCap) | Test 10 (provider-level cap=5 enforcement) |
| 6 | "Selecting a chat from the history dropdown via selectChat(id) auto-opens it as a tab (calls openTab internally)" | `SessionControlContext.tsx:405-418` (selectChat delegates to openTab with TabCapReachedError catch) | Manual UAT step 5 below |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cap throw refactored from setState updater to synchronous-before-setter**
- **Found during:** Task 3 verification (Test 10 fell through the consumer's try/catch)
- **Issue:** The initial `openTab` implementation threw `TabCapReachedError` inside the `setOpenTabIds((prev) => …)` updater function. React 18+ may re-run updaters during reconciliation; in our test the throw fired from a `basicStateReducer → updateReducerImpl → useState` stack inside `SessionControlProvider`'s render path, not from the consumer's onClick handler. The test consumer's `try { ctx.openTab(id) } catch (err) { onError?.(err) }` couldn't catch it.
- **Fix:** Refactored `openTab` to (a) check `openTabIds.includes(sessionId)` from the render closure and return-early-with-make-visible if duplicate, (b) check `openTabIds.length >= tabCap` from the closure and `throw new TabCapReachedError(tabCap)` synchronously BEFORE calling `setOpenTabIds`. The setter call uses an idempotent updater `(prev) => prev.includes(id) ? prev : [...prev, id]`.
- **Files modified:** `frontend/src/contexts/SessionControlContext.tsx` (lines 317-341)
- **Verification:** Test 10 now GREEN — `capturedError instanceof TabCapReachedError` and `capturedError.cap === 5` both pass; `readOpenTabIds()` is unchanged after the cap rejection.
- **Committed in:** `d0f46c36` (Task 3 GREEN commit)

**2. [Rule 1 - Bug] `closeTab` next-state computed from closure (not from setState updater)**
- **Found during:** Task 3 verification (Tests 11, 12, 13 all read empty `nextOpenTabIds`)
- **Issue:** Initial implementation set `let nextOpenTabIds: string[] = []` then called `setOpenTabIds((prev) => { nextOpenTabIds = prev.filter(...); return nextOpenTabIds })`. React batches state updates — at the time the post-setState logic (`removeActiveSession`, promotion, `createNewChat` fallback) read `nextOpenTabIds`, the updater had not yet run. The variable was still `[]`. Test 11 saw `removeActiveSessionMock` not called (early-return guard tripped), Test 12 saw the promotion not happen, Test 13 saw `createNewChat` not called.
- **Fix:** Compute `nextOpenTabIds = openTabIds.filter((id) => id !== sessionId)` from the render closure FIRST, then call `setOpenTabIds(nextOpenTabIds)` with the precomputed array. The post-setState logic now references the deterministic closure value.
- **Files modified:** `frontend/src/contexts/SessionControlContext.tsx` (lines 363-394)
- **Verification:** Tests 11, 12, 13 all GREEN.
- **Committed in:** `d0f46c36` (Task 3 GREEN commit, same commit as Fix 1)

---

**Total deviations:** 2 auto-fixed (2 Rule-1 bugs in initial Task-3 implementation, both caught by the Task-2 RED tests turning GREEN as designed by TDD)
**Impact on plan:** Both fixes were corrections to my initial Task-3 wiring, NOT scope additions. The TDD RED gates from Task 2 caught both bugs immediately, validating the plan's test-first design. Final implementation matches the plan's documented behavior 1:1.

## Issues Encountered

- Initial `openTab` implementation threw inside the setState updater (anti-pattern caught by Test 10). Refactored to throw synchronously before the setter — see Deviation 1.
- Initial `closeTab` implementation computed `nextOpenTabIds` inside the setState updater and read it post-call (timing bug caught by Tests 11, 12, 13). Refactored to compute from render closure — see Deviation 2.
- The previous executor session was interrupted by a rate-limit AFTER Tasks 1 and 2 had committed (`d960b5a2`, `3155fed9`). Resumption verified Tests 6-14 were RED before starting Task 3, then drove them to GREEN. Resumption protocol worked exactly as designed.

## Out-of-Scope Deferrals

| Deferred item | Reason |
| --- | --- |
| TabStrip UI component + ChatInterface header restructure | Plan 88-03 (Tab Strip UI) handles this. This plan ships only the data layer. |
| Per-tab streaming/unread indicators + sonner cap toast | Plan 88-04 (Streaming Indicator) handles this. The TabStrip onClick handler will catch `TabCapReachedError` from `openTab` and surface the toast. |
| Drag-to-reorder tabs | Out of phase entirely. |
| Cross-tab sync for `pikar_open_tab_ids` | Not required by ROADMAP; the closeTab→createNewChat sequence transiently writes `[]` then `[newId]` between the two `setOpenTabIds` updaters. Acceptable today because `pikar_open_tab_ids` does NOT have a `storage` event listener (only `pikar_current_session_id` does — Plan 88-01 scope). If a future phase adds cross-tab sync for open tabs, the writes need to be unified (e.g., `flushSync`, a single combined reducer, or a debounced effect). |
| Behavior test for tier-derived cap=8 (paid) | Test 10 covers cap=5 (free / provider default). The paid cap=8 path is exercised only inside `useChatSession()`, which is harder to test in isolation because it requires `<SubscriptionProvider>`. Tested via the Manual UAT script (step 6 below). |

## Manual UAT Script (for phase gate)

Run after merging into a deploy preview. Open browser dev-tools → Application → Local Storage → origin.

1. **Free tier baseline.** Sign in as a free user. Send a message in any persona. Observe `pikar_current_session_id` (existing) and `pikar_open_tab_ids` (new) both populated. Type `JSON.parse(localStorage.getItem('pikar_open_tab_ids'))` in the console → returns an array of 1 string.
2. **Open tabs from the `+` icon.** Click the `+` icon (existing button at `ChatInterface.tsx:1167` — Plan 03 will replace this with a TabStrip; for Plan 02 verification this suffices). Observe a fresh session id appended to `pikar_open_tab_ids` (NOT replaced — appended).
3. **Open tabs from the history dropdown.** From the chat history dropdown (Clock icon), select an older session. Observe its id appended to `pikar_open_tab_ids` (selectChat → openTab delegation).
4. **Free-tier cap.** Repeat step 2/3 until 5 tabs are open. The 6th attempt via the `+` icon — Plan 03 will surface a toast; for Plan 02 the cap rejection is observable only via the browser console as `[SessionControl] selectChat hit tab cap: Tab cap reached (5)…`.
5. **Last-tab fallback.** Close 4 tabs via the upcoming TabStrip (or by manually calling `useSessionControl().closeTab('id')` from the React DevTools). Close the 5th — observe `pikar_open_tab_ids` ends as `[newId]` where `newId` matches `/^session-\d+-[a-z0-9]+$/` (createNewChat seeded). Chat panel never empties.
6. **Paid-tier cap.** Sign in as a solopreneur/startup/sme/enterprise user. Open 5 tabs (free-tier cap). The 6th, 7th, and 8th tabs should open successfully (paid cap = 8). The 9th attempt should hit the cap. Observe `useChatSession().tabCap === 8` in the React DevTools.
7. **Reload persistence.** Refresh the browser. Confirm `pikar_open_tab_ids` is restored unchanged. The chat panel still shows whichever tab was visible before the reload (per Plan 88-01's `pikar_current_session_id` restore).

## PR-Reviewer Note

**Frontend-only plan.** No backend Python files touched. `make test` is intentionally not in the verification chain — backend reviewers do not need to run it for this PR.

## Next Phase Readiness

- **Plan 88-03 (Tab Strip UI):** Ready. Plan 03 consumes `useChatSession().openTabIds`, `tabCap`, `openTab`, `closeTab` to render the tab strip. The interface contract documented in this plan's `<interfaces>` block is the API Plan 03 codes against.
- **Plan 88-04 (Streaming Indicator):** Ready. Plan 04's max-tab toast lives in TabStrip's onClick handler — it catches `TabCapReachedError` thrown by `openTab` and renders a sonner toast.

## Self-Check: PASSED

- [x] `frontend/src/contexts/SessionControlContext.tsx` modified with new behavior — verified via `git show d0f46c36 --stat` (1 file, +165/-16 LOC)
- [x] `frontend/src/contexts/ChatSessionContext.tsx` modified with useSubscription override — verified via `git show 6e1ac6df --stat` (1 file, +30/-4 LOC)
- [x] Commit `d960b5a2` (Task 1 stub) exists — verified via `git log --oneline`
- [x] Commit `3155fed9` (Task 2 RED) exists — verified via `git log --oneline`
- [x] Commit `d0f46c36` (Task 3 GREEN) exists — verified via `git log --oneline`
- [x] Commit `6e1ac6df` (Task 4 tier-derived cap) exists — verified via `git log --oneline`
- [x] All 13 SessionControlContext.test.tsx tests GREEN (4 from Plan 01 + 9 from Plan 02) — verified
- [x] All 10 ChatInterface.test.tsx tests GREEN (no regression) — verified
- [x] TypeScript compile clean for the 2 modified context files — verified via `npx tsc --noEmit -p tsconfig.json | grep -E "SessionControlContext|ChatSessionContext"` (no output)
- [x] No NEW lint findings introduced (3 pre-existing warnings/error in SessionControlContext.tsx documented in Plan 01)
- [x] Full frontend test suite: 514 passed / 49 failed — failure count IDENTICAL to Plan 01 baseline (the 49 pre-existing failures in unrelated components: PersonaView, CalendarWidget, InitiativeDashboard, KanbanWidget, RevenueChart, LandingDemo, ProtectedRoute). Zero new failures introduced by this plan.
