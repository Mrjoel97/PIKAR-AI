---
phase: 88-chat-and-workspace-persistence
plan: 01
subsystem: frontend/contexts/session
tags: [hotfix-06, persistence, localStorage, cross-tab, vitest, retroactive]
requires:
  - frontend/src/contexts/SessionMapContext.tsx (Provider parent)
  - frontend/src/services/sessions.ts (listUserSessions — shipped pre-plan)
  - frontend/src/lib/supabase/client.ts (auth.getUser)
provides:
  - cross-tab session_id sync via window 'storage' event listener (~12 LOC)
  - regression-proof behavior coverage for shipped persistence (commit c8da1d99)
  - extended chatHarness with sessionControl override + initialSessionId prop forwarding
affects:
  - frontend/src/contexts/SessionControlContext.tsx (production: +24 LOC, 0 deletions)
  - frontend/src/components/chat/__test-utils__/chatHarness.ts (test infra: +37 LOC)
  - frontend/src/contexts/__tests__/SessionControlContext.test.tsx (NEW: 4 tests, 192 LOC)
  - frontend/src/components/chat/ChatInterface.test.tsx (+25 LOC, 1 new describe block, 1 new test)
tech-stack:
  added: []
  patterns:
    - Window-level event listener with stable cleanup (addEventListener/removeEventListener pair)
    - Raw setState dispatcher (setVisibleSessionIdRaw) used inside storage handler to avoid persist loop
    - Synthetic StorageEvent dispatch in jsdom for cross-tab sync coverage (jsdom does NOT fire storage from same-window setItem per the spec)
key-files:
  created:
    - frontend/src/contexts/__tests__/SessionControlContext.test.tsx
    - .planning/phases/88-chat-and-workspace-persistence/88-01-persistence-reconciliation-SUMMARY.md
  modified:
    - frontend/src/contexts/SessionControlContext.tsx (lines 141-163: new storage useEffect)
    - frontend/src/components/chat/__test-utils__/chatHarness.ts (SessionControlOverrides interface, defaultSessionControl(overrides), initialSessionId prop forwarding)
    - frontend/src/components/chat/ChatInterface.test.tsx (new describe 'persistence (HOTFIX-06)')
decisions:
  - Use 'storage' event over BroadcastChannel — last-write-wins is acceptable per ROADMAP; storage event has zero new browser API surface
  - setVisibleSessionIdRaw (not setVisibleSessionId) inside the listener — the persisting setter would re-write localStorage and risk a feedback loop
  - Listener as a separate useEffect (not added to the existing useLayoutEffect) — layout effect runs synchronously before paint exactly once on mount; storage listener attaches at any time and unmounts cleanly
  - Synthetic StorageEvent dispatch for the cross-tab test — jsdom does not fire storage from same-window setItem, matching the W3C spec (storage fires only in OTHER same-origin tabs)
  - Pre-existing 'config fetch' tests in __tests__/contexts/SessionControlContext.test.tsx left untouched — they expect /configuration/session-config but the production code intentionally defers that endpoint (comment at line 170-171 of SessionControlContext.tsx)
metrics:
  duration_minutes: 18
  tasks: 3
  files_touched: 4
  production_loc_added: 24
  test_loc_added: ~225
  completed: "2026-04-30T20:52:21Z"
---

# Phase 88 Plan 01: Persistence Reconciliation Summary

Closed the cross-tab safety gap (ROADMAP success criterion 4) for the chat-history-on-reload persistence work that shipped retroactively in commit `c8da1d99` (2026-04-27); added 5 vitest behavior tests so the four already-shipped truths are now regression-proof.

## What Shipped Pre-Plan (commit c8da1d99, 2026-04-27)

The bulk of HOTFIX-06 was implemented and merged before any GSD plan existed. This SUMMARY is the canonical planning-tool record of that work.

| Truth (ROADMAP SC) | Source | Lines |
| --- | --- | --- |
| 1. Reload restores `session_id` from localStorage | `frontend/src/contexts/SessionControlContext.tsx` | 26 (STORAGE_KEY constant), 129-139 (`useLayoutEffect` restore-on-mount) |
| 1. Restored id flows into `<ChatInterface initialSessionId>` | `frontend/src/components/dashboard/PersonaDashboardLayout.tsx` | 224 (`<ChatInterface initialSessionId={effectiveSessionId} />` gated on `sessionRestored`) |
| 2. Workspace re-queries Supabase on session change | `frontend/src/components/dashboard/ActiveWorkspace.tsx` | 317-355 (`.eq('session_id', currentSessionId)` query inside `loadWorkspaceState`) |
| 3. `createNewChat()` replaces stored id | `frontend/src/contexts/SessionControlContext.tsx` | 144-155 (`setVisibleSessionId` persists; null clears storage), 176-181 (`createNewChat` calls it) |
| 5. History list shows all server sessions | `frontend/src/services/sessions.ts` (`listUserSessions`), `app/routers/sessions.py` (`GET /sessions` endpoint) | service: full file; router: existing |

## What This Plan Added

### Production code (`SessionControlContext.tsx`, +24 LOC, 0 deletions)

**Cross-browser-tab sync** — new `useEffect` block at lines 141-163. The `storage` event fires on `window` in OTHER same-origin tabs ONLY when localStorage mutates; we mirror the new value into React state via the raw setState dispatcher (so we do NOT re-write localStorage and risk a feedback loop). Cleanup tears down the listener on unmount to prevent leaks across hot-reloads.

```typescript
useEffect(() => {
  const handleStorage = (e: StorageEvent) => {
    if (e.key !== STORAGE_KEY) return
    if (e.storageArea !== window.localStorage) return
    setVisibleSessionIdRaw(e.newValue)
  }
  window.addEventListener('storage', handleStorage)
  return () => window.removeEventListener('storage', handleStorage)
}, [])
```

### Test infrastructure (`chatHarness.ts`, +37 LOC)

- New `SessionControlOverrides` interface
- `defaultSessionControl(overrides?)` accepts per-test overrides and merges over the harness default
- `RenderChatOptions.initialSessionId` is now forwarded into `<ChatInterface initialSessionId={...} />`
- Existing `defaultSessionControl().config = {}` upgraded to `DEFAULT_SESSION_CONFIG` from `@/types/session` (was a benign placeholder)

### Behavior tests

| # | Test | File | Maps to |
| --- | --- | --- | --- |
| 1 | restores session_id from localStorage on mount | `frontend/src/contexts/__tests__/SessionControlContext.test.tsx` | SC-1 |
| 2 | persists session_id to localStorage on change | same | SC-1, SC-3 |
| 3 | createNewChat replaces stored session_id | same | SC-3 |
| 4 | cross-tab storage event updates visibleSessionId | same | **SC-4 (the gap closed by this plan)** |
| 5 | forwards initialSessionId from props to useAgentChat | `frontend/src/components/chat/ChatInterface.test.tsx` (new describe block 'ChatInterface — persistence (HOTFIX-06)') | SC-1 (component-level wiring) |

Test 4 was RED at end of Task 1 (the listener did not exist yet) and turned GREEN after Task 2's production change. Tests 1-3 and 5 were GREEN immediately because the production code already shipped in `c8da1d99`.

## Truth-to-Code Map

For ROADMAP traceability — each `must_haves.truths` item to its source.

| Truth | Source line range | Test |
| --- | --- | --- |
| "After sending a message and reloading, the same session_id is restored from localStorage `pikar_current_session_id`…" | `SessionControlContext.tsx:26,129-139` + `PersonaDashboardLayout.tsx:224` | Tests 1, 5 |
| "Workspace artifacts re-query Supabase `workspace_items` keyed on the restored session_id…" | `ActiveWorkspace.tsx:317-355` | Manual UAT (no automated coverage — workspace is a higher-level integration concern) |
| "Calling `createNewChat()` clears `pikar_current_session_id` from localStorage (or replaces it with the new id)…" | `SessionControlContext.tsx:144-155,176-181` | Tests 2, 3 |
| "Chat history list (`/dashboard/history` and the in-panel dropdown) shows all sessions returned by `GET /sessions`…" | `services/sessions.ts:listUserSessions` + `SessionControlContext.tsx:202-229` (`refreshSessions`) | Manual UAT (covered by existing /sessions service tests + history-list dropdown behavior) |
| "Opening the same session in a second browser tab does not corrupt either tab — the second tab's localStorage write fires a `storage` event, the first tab observes it…" | `SessionControlContext.tsx:141-163` (NEW in this plan) | Test 4 |

## Out-of-Scope Deferrals

| Deferred item | Reason |
| --- | --- |
| `BroadcastChannel('pikar_session')` | The `storage` event covers last-write-wins for free with zero new browser API surface; the ROADMAP explicitly lists BroadcastChannel as out of scope. |
| `pikar_open_tab_ids` localStorage key + tier-aware cap | Plan 88-02 (Tab State) handles this. |
| TabStrip UI component + ChatInterface header restructure | Plan 88-03 (Tab Strip UI) handles this. |
| Per-tab streaming/unread indicators + sonner cap toast | Plan 88-04 (Streaming Indicator) handles this. |
| Workspace artifact behavior test for SC-2 | Workspace is a higher-level integration concern — covered by manual UAT (step 2 below); a future plan can add `ActiveWorkspace.test.tsx` if regressions surface. |

## Manual UAT Script (for phase gate)

Run after deploying the storage-listener change. The persistence work itself ships in `c8da1d99` and has been live in production since 2026-04-27.

1. Open the app in Chrome **Tab A**. Send a message in any persona dashboard. Note the `session_id` (DevTools → Application → Local Storage → `pikar_current_session_id`).
2. Hard-refresh **Tab A**. Verify the same session loads — chat history visible, last agent response present, workspace items restored.
3. Open the app in Chrome **Tab B** (new tab, same origin). It should pick up the same `session_id` from localStorage and show the same chat + workspace.
4. In **Tab B**, click "New Chat" (the `+` icon in the chat panel header). Tab B now shows a fresh session.
5. Switch back to **Tab A**. Within ~1 second (the time it takes for the storage event to propagate and React to re-render), Tab A's `visibleSessionId` should match Tab B's new session. Workspace re-queries; history dropdown still lists both sessions.
6. Stop the backend (`docker compose stop backend`). Refresh either tab. The localStorage restore still works (it doesn't depend on the backend), but `refreshSessions` will silently fail with `console.error`. The chat interface should still mount without throwing.

## PR-Reviewer Note

**Frontend-only plan.** No backend Python files touched. `make test` is intentionally not in the verification chain — backend reviewers do not need to run it for this PR.

## Per-Task Commits

| Task | Hash | Message |
| --- | --- | --- |
| 1 (RED) | `611bc60a` | `test(88-01): add behavior coverage for shipped persistence + RED cross-tab test (HOTFIX-06)` |
| 2 (GREEN) | `08f7162b` | `fix(88-01): cross-tab session_id sync via storage event listener (HOTFIX-06.4)` |
| 3 (Docs) | (this commit) | `docs(88-01): complete persistence-reconciliation plan` |

## Deviations from Plan

None — plan executed exactly as written. Test 4 RED in Task 1 → GREEN after Task 2 was the planned TDD cycle.

## Deferred Issues (out-of-scope, pre-existing)

- 49 pre-existing test failures in the global `npm test` run (auth pages, dashboard layout, persona switchers, `__tests__/contexts/SessionControlContext.test.tsx` config-fetch suite, etc.) are NOT caused by this plan and live outside its scope. The four files this plan touches (and the new SessionControlContext.test.tsx) all pass cleanly: 18/18 GREEN.
- 3 pre-existing lint findings in `SessionControlContext.tsx` (lines 108 unused `sessions`, 120 unused `setConfig`, 457 `any` in catch) are NOT in our newly added code and predate this plan. Our +24 LOC are lint-clean.

## Self-Check: PASSED

- [x] `frontend/src/contexts/SessionControlContext.tsx` modified (+24 LOC) — verified via `git show 08f7162b --stat`
- [x] `frontend/src/contexts/__tests__/SessionControlContext.test.tsx` created — file exists at the expected path
- [x] `frontend/src/components/chat/__test-utils__/chatHarness.ts` extended — `SessionControlOverrides`, `initialSessionId` forwarding present
- [x] `frontend/src/components/chat/ChatInterface.test.tsx` has new `'persistence (HOTFIX-06)'` describe block with 1 test
- [x] Commit `611bc60a` exists (Task 1 RED) — verified
- [x] Commit `08f7162b` exists (Task 2 GREEN) — verified
- [x] All 4 SessionControlContext.test.tsx tests GREEN
- [x] All 10 ChatInterface.test.tsx tests GREEN (4 pre-Phase-83 + 5 HOTFIX-01 + 1 HOTFIX-06)
- [x] No new TypeScript errors introduced
- [x] No new lint findings introduced
