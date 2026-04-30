---
phase: 83-document-upload-bypass
plan: 01
subsystem: testing
tags: [vitest, jsdom, react-testing-library, test-harness, chat]

# Dependency graph
requires: []
provides:
  - "renderChatInterface(opts) helper that pre-mocks all 11 module-scope hooks in ChatInterface.tsx (useAgentChat, useFileUpload, useTextToSpeech, usePresence, useRealtimeSession, useSessionControl, useSessionMap, useSpeechRecognition, useVoiceSession, usePersona, plus supabase/client.createClient)"
  - "Override surface for uploadFile, messages, isStreaming, addMessage, sendMessage"
  - "getFetchSpy() returning the active vi.spyOn(global, 'fetch') instance with a benign 200 default"
  - "jsdom polyfills for scrollIntoView and matchMedia inside the harness"
affects: [Plan 02 (will consume harness for 5 component-level behavior tests), any future ChatInterface tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-scope vi.mock + per-call vi.mocked().mockReturnValue() for component-level harnesses"
    - "Test harness module pattern: factory + override surface + helper accessors (getFetchSpy)"

key-files:
  created:
    - frontend/src/components/chat/__test-utils__/chatHarness.ts
    - frontend/src/components/chat/__test-utils__/chatHarness.test.tsx
  modified: []

key-decisions:
  - "Mocks installed at module scope with vi.mock; per-render reset via vi.mocked(...).mockReturnValue inside renderChatInterface()"
  - "Hook return shapes copied verbatim from each hook's TypeScript signature to avoid TypeError-on-render drift"
  - "Polyfilled jsdom gaps (scrollIntoView, matchMedia) inside the harness rather than in vitest.config.mts to keep the polyfill scoped to ChatInterface tests"
  - "Pre-existing failure in ChatInterface.test.tsx (4 tests, useSessionControl provider error) deferred to Plan 02 — vi.mock is per-file so the harness cannot fix tests in another file without that file importing the harness"

patterns-established:
  - "Module-scope vi.mock pattern: all hook mocks declared at top of harness module, hoisted by vitest into every importing test file"
  - "Override factory pattern: defaultX() functions return benign return-shape objects, callers provide partial overrides via opts"
  - "Fetch spy lifecycle: install per render (mockRestore previous), expose via getFetchSpy() helper for assertions"

requirements-completed: [HOTFIX-01]

# Metrics
duration: 7 min
completed: 2026-04-30
---

# Phase 83 Plan 01: Test Harness Summary

**Reusable chatHarness module that pre-mocks all 11 module-scope hooks in `ChatInterface.tsx` and exposes a `renderChatInterface(opts)` helper for component-level behavior tests, unblocking Plan 02's HOTFIX-01 verification suite.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-30T17:46:45Z
- **Completed:** 2026-04-30T17:53:46Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2

## Accomplishments

- Built `frontend/src/components/chat/__test-utils__/chatHarness.ts` (~290 lines) that mocks all 11 module-scope hooks called by `ChatInterface.tsx`, plus the `@/lib/supabase/client` module
- Per-test override surface (`RenderChatOptions`) covers the two values Plan 02 needs to control: `uploadFile` (return value of `useFileUpload().uploadFile`) and the global `fetch` spy
- Re-exposed `addMessage` and `sendMessage` from the useAgentChat mock so behavior tests can assert on agent-chat callbacks without redoing the inline mock
- Polyfilled the two jsdom gaps `ChatInterface.tsx` runs into on first render: `Element.prototype.scrollIntoView` and `window.matchMedia`
- 4-test smoke suite (`chatHarness.test.tsx`) covers: smoke render, uploadFile override, addMessage/sendMessage exposure, fetch spy default + access

## Task Commits

TDD cycle produced two atomic commits:

1. **RED — `test(83-01): add failing test for chatHarness module`** — `e10e9805`
2. **GREEN — `feat(83-01): implement chatHarness with module-scope hook mocks`** — `4f327b8f`

No REFACTOR commit needed — implementation is at single-purpose minimum.

## Mocked Hooks (Module-Scope)

The harness installs `vi.mock(...)` at module scope (vitest hoists these into every importing test file at compile time). Each mock returns the destructure shape `ChatInterface.tsx` actually consumes:

| # | Hook | Module | Destructured fields |
|---|------|--------|---------------------|
| 1 | `useAgentChat` | `@/hooks/useAgentChat` | `messages, sendMessage, isStreaming, addMessage, toggleWidgetMinimized, isLoadingHistory, pinWidget, sessionId, getSessionId, stopGeneration` |
| 2 | `useFileUpload` | `@/hooks/useFileUpload` | `uploadFile, uploadFileToVault, isUploading, uploadError` |
| 3 | `useTextToSpeech` | `@/hooks/useTextToSpeech` | `speak, stop, isSpeaking, isSupported` |
| 4 | `usePresence` | `@/hooks/usePresence` | `presenceState, onlineUsers` |
| 5 | `useRealtimeSession` | `@/hooks/useRealtimeSession` | (side-effect only — returns undefined) |
| 6 | `useSpeechRecognition` | `@/hooks/useSpeechRecognition` | `isRecording, isTranscribing, toggleRecording, startRecording, stopRecording, transcript, transcriptVersion, interimTranscript, error, isSupported, clearTranscript` |
| 7 | `useVoiceSession` | `@/hooks/useVoiceSession` | `isConnected, isAgentSpeaking, agentTranscript, userTranscript, transcriptTurns, error, remainingSeconds, isWrappingUp, isTimedOut, connect, disconnect` |
| 8 | `useSessionControl` | `@/contexts/SessionControlContext` | `visibleSessionId, setVisibleSessionId, sessionRestored, config, createNewChat, selectChat, deleteChat, clearAllChats, refreshSessions, updateSessionTitle, updateSessionPreview, addSessionOptimistic` |
| 9 | `useSessionMap` | `@/contexts/SessionMapContext` | `activeSessions, addActiveSession, removeActiveSession, updateSessionState, getActiveSessionRef, sessions, setSessions, isLoadingSessions, setIsLoadingSessions` |
| 10 | `usePersona` | `@/contexts/PersonaContext` | `persona, setPersona, isLoading, userId, userEmail, agentName` |
| 11 | `createClient` | `@/lib/supabase/client` | chainable stub: `from().select().eq()`, `auth.{getUser,getSession,onAuthStateChange}`, `channel().on().subscribe()`, `removeChannel` |

## Override Surface — `RenderChatOptions`

```ts
export interface RenderChatOptions {
  uploadFile?: ReturnType<typeof vi.fn>   // override useFileUpload().uploadFile
  messages?: unknown[]                    // override useAgentChat().messages
  isStreaming?: boolean                   // override useAgentChat().isStreaming
  addMessage?: ReturnType<typeof vi.fn>   // override useAgentChat().addMessage
  sendMessage?: ReturnType<typeof vi.fn>  // override useAgentChat().sendMessage
}
```

`renderChatInterface(opts)` returns the standard `RenderResult` from `@testing-library/react`, augmented with `{ addMessage, sendMessage, uploadFile }` — the exact `vi.fn()` instances the component receives — so behavior tests can call `expect(addMessage).toHaveBeenCalledWith(...)` directly.

A separate top-level `getFetchSpy()` returns the currently-installed `vi.spyOn(global, 'fetch')` instance for assertions like `expect(getFetchSpy()).not.toHaveBeenCalledWith(expect.stringContaining('/api/upload/smart'), expect.anything())`.

## Files Created/Modified

- `frontend/src/components/chat/__test-utils__/chatHarness.ts` — Reusable test harness; renderChatInterface(opts) helper, getFetchSpy(), 11 module-scope hook mocks, Supabase client stub, jsdom polyfills.
- `frontend/src/components/chat/__test-utils__/chatHarness.test.tsx` — 4-test smoke suite proving the harness contract (smoke render, uploadFile override, agent-chat callback exposure, fetch spy access).

## Decisions Made

- **vi.mock at module scope, per-render mockReturnValue:** Each call to `renderChatInterface(...)` re-resolves every hook's return value, so test order is irrelevant and overrides are honored on the per-test path.
- **Hook return shapes copied verbatim from each hook's source TypeScript signature:** Avoids the failure mode where a hand-rolled mock omits a field that ChatInterface destructures (e.g. `voiceSession.transcriptTurns`), producing a confusing TypeError at render time. Each `defaultX()` factory in `chatHarness.ts` mirrors the exact destructure used in `ChatInterface.tsx`.
- **jsdom polyfills inside the harness rather than vitest.config.mts:** Keeps the polyfill scoped to ChatInterface tests; other test files in the repo do not need scrollIntoView or matchMedia polyfills, so installing them globally would be unnecessary.
- **Per-render fetch spy reinstall:** `mockRestore()` previous spy + new `vi.spyOn` ensures each test starts with a clean call history, preventing cross-test contamination on the global object.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Added `window.matchMedia` polyfill to the harness**
- **Found during:** Task 1 GREEN phase — first run of harness tests
- **Issue:** ChatInterface.tsx:196 calls `window.matchMedia('(max-width: 768px)')` in a `useEffect` to detect mobile viewport, but jsdom does not implement `matchMedia`. Render crashed with `TypeError: window.matchMedia is not a function`.
- **Fix:** Added a benign `matchMedia` stub inside `renderChatInterface()` (returns `{ matches: false, addEventListener, removeEventListener, ... }`). The polyfill is installed only if `window.matchMedia` is not already a function, so it does not clobber a real implementation in environments that have one.
- **Files modified:** `frontend/src/components/chat/__test-utils__/chatHarness.ts`
- **Verification:** Re-running harness tests turned 4 failures into 4 GREEN passes.
- **Committed in:** `4f327b8f` (GREEN commit, part of the same atomic implementation)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Polyfill is purely additive jsdom shim; necessary for any test that renders ChatInterface in jsdom. No scope creep.

## Issues Encountered

### Pre-existing failure in `ChatInterface.test.tsx` — deferred to Plan 02

Running the plan's combined verification command (`npx vitest run chatHarness.test.tsx ChatInterface.test.tsx`) revealed that all 4 tests in `ChatInterface.test.tsx` fail at render time with `Error: useSessionControl must be used within a SessionControlProvider`.

**Root cause:** `ChatInterface.tsx` was modified after `ChatInterface.test.tsx` was written to add 11 module-scope hooks; the existing test only mocks `useAgentChat`. Re-running the test on `main` (no Plan 01 changes) reproduces the same 4 failures — this is pre-existing drift, not caused by Plan 01.

**Why not fixed in Plan 01:** The plan explicitly forbids modifying `ChatInterface.test.tsx` ("DO NOT modify ChatInterface.tsx or ChatInterface.test.tsx in this plan — those are Plan 02's scope"). Vitest hoists `vi.mock` calls per-file, so the harness's mocks installed inside `chatHarness.test.tsx` do NOT propagate to `ChatInterface.test.tsx`. The harness cannot fix nor regress this test from a different file.

**Mitigation:** Documented in `.planning/phases/83-document-upload-bypass/deferred-items.md`. Plan 02's first task should refactor `ChatInterface.test.tsx` to import `renderChatInterface` from the harness; once that lands, all 4 existing tests will pass automatically because the harness installs every required hook stub.

**Why this still satisfies Plan 01's success criteria:** The harness itself is fully functional (4/4 harness tests green) and Plan 02 can `import { renderChatInterface } from './__test-utils__/chatHarness'` to write its 5 behavior tests with zero per-test hook re-mocking — the actual success criterion of this plan.

## Verification Results

| Check | Status | Evidence |
|-------|--------|----------|
| `cd frontend && npx vitest run src/components/chat/__test-utils__/chatHarness.test.tsx` | PASS | 4/4 tests green in ~370ms |
| `cd frontend && npx tsc --noEmit -p tsconfig.json 2>&1 \| grep chatHarness` | PASS | No errors mention chatHarness |
| `cd frontend && npx eslint src/components/chat/__test-utils__/chatHarness.{ts,test.tsx}` | PASS | Zero lint errors |
| Combined: harness + existing ChatInterface tests | PARTIAL | Harness 4/4 green; existing ChatInterface.test.tsx 0/4 green — pre-existing failure documented in deferred-items.md, scheduled for Plan 02 |

## QA Flag — Future Maintenance

- **Harness uses `Response`** (jsdom polyfill) for the default fetch implementation. If `vitest.config.mts` ever changes the test environment from `jsdom` to `node`, the global `Response` constructor will not be available — the harness will need an explicit polyfill or replacement (e.g. a `Response`-shaped object literal).
- **If `ChatInterface.tsx` adds a new module-scope hook**, the harness MUST be updated in tandem (add the `vi.mock`, add a `defaultX()` factory, wire it into `renderChatInterface`). Symptom of forgetting: behavior tests will fail with `Cannot read properties of undefined` from inside the destructure on first render.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 02 (Wave 1) is unblocked.** Plan 02 can now `import { renderChatInterface, getFetchSpy } from './__test-utils__/chatHarness'` and author its 5 component-level behavior tests for HOTFIX-01.
- **Pre-existing breakage in `ChatInterface.test.tsx`** is documented in `deferred-items.md`. Plan 02's first task should adopt the harness inside `ChatInterface.test.tsx`, which fixes all 4 existing tests and unblocks the plan's verify gate that was originally written assuming those tests passed.

## Self-Check: PASSED

- `frontend/src/components/chat/__test-utils__/chatHarness.ts` — exists on disk
- `frontend/src/components/chat/__test-utils__/chatHarness.test.tsx` — exists on disk
- Commit `e10e9805` (test RED) — present in `git log`
- Commit `4f327b8f` (feat GREEN) — present in `git log`

---
*Phase: 83-document-upload-bypass*
*Completed: 2026-04-30*
