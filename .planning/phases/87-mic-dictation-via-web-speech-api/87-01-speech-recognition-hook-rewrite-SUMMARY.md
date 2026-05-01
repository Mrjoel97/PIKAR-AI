---
phase: 87-mic-dictation-via-web-speech-api
plan: 01
subsystem: ui
tags: [speech-recognition, web-speech-api, react-hooks, vitest, tdd, hotfix]

requires:
  - phase: 84-voice-gate-deadlock-fix
    provides: useVoiceSession boundary (separate hook, separate WebSocket route, zero cross-imports)
  - phase: 83-document-upload-bypass
    provides: chatHarness pattern (vi.mock with stable 11-field return shape)
provides:
  - Web Speech API wrapper hook (`useSpeechRecognition`) with interim + final result streaming
  - 8-test vitest unit suite mocking `window.SpeechRecognition` via class-based fake constructor
  - `@types/dom-speech-recognition` typings (zero `as any` casts in production code)
  - Public 11-field return shape preserved — drop-in compatible with existing chatHarness mock and ChatInterface destructure
affects:
  - 87-02-chat-interface-integration (consumes the new hook; owns textarea readOnly removal, suffix-ref live-streaming, mid-dictation send, SC1-SC5 component tests)

tech-stack:
  added:
    - "@types/dom-speech-recognition@^0.0.10 (devDependency, types-only, zero runtime cost)"
  patterns:
    - "Per-call constructor lookup (NOT module-load capture) so tests can swap window.SpeechRecognition between renders without vi.resetModules"
    - "stop() vs abort() discipline: stop() flushes interim into final via onend; abort() silent for unmount cleanup to prevent phantom transcriptVersion bumps"
    - "Class-based test fake with static onCreate hook — satisfies typeof SpeechRecognition constructor signature without no-this-alias lint violation"
    - "ERROR_MESSAGES lookup table for friendly user-actionable copy (permission, no-speech, audio-capture, network)"

key-files:
  created:
    - "frontend/__tests__/hooks/useSpeechRecognition.test.ts (241 lines, 8 tests)"
  modified:
    - "frontend/src/hooks/useSpeechRecognition.ts (190 lines; full rewrite from 373-line MediaRecorder + backend POST wrapper)"
    - "frontend/package.json (added @types/dom-speech-recognition devDep)"
    - "frontend/package-lock.json (regenerated for dep install)"

key-decisions:
  - "Constructor lookup inside startRecording (per-call) instead of module-load — required for Test 1's swap-between-renders pattern"
  - "isSupported is a useState initialized at hook construction (NOT a derived value re-evaluated each render) — prevents flicker; Test 1 verifies both supported and unsupported cases via separate renderHook calls"
  - "isTranscribing field retained but always returns false — back-compat with ChatInterface's 6 references (now dead branches but harmless); Plan 02 simplifies them"
  - "Cleanup useEffect calls abort() (silent), NOT stop(); stop() would fire onend with finalRef content and bump transcriptVersion AFTER unmount, causing phantom append-to-input on next mount"
  - "stopRecording uses recognition.stop() (NOT abort) so any in-progress interim flushes to final via onend — supports 'click Send mid-dictation includes the in-progress phrase' UX wired by Plan 02"
  - "Class-based test fake (FakeRec class with static onCreate) chosen over function-style constructor — eliminates no-this-alias lint error AND keeps the constructor signature compatible with the typeof SpeechRecognition assignment"
  - "Window-property type lookup via `as unknown as { SpeechRecognition?: typeof SpeechRecognition; webkitSpeechRecognition?: typeof SpeechRecognition }` — necessary because @types/dom-speech-recognition declares globals as `declare var`, not as Window-interface augmentations"
  - "Backend `/ws/voice/transcribe` route at app/routers/voice_session.py:745-783 left on disk per Phase 83 precedent — orphaned but cheap, cleanup deferred to follow-up PR for diff isolation"

patterns-established:
  - "Per-call window-API lookup for testability: read window.X inside the function that needs it, not at module scope, so vitest can install/uninstall mocks between renders"
  - "Class-based test fake constructor pattern: a class with public mutable fields + vi.fn() spies + static onCreate hook satisfies `typeof SomeWebAPI` assignments with strict ESLint rules"

requirements-completed: [HOTFIX-05]

duration: 31 min
completed: 2026-05-01
---

# Phase 87 Plan 01: Speech Recognition Hook Rewrite Summary

**Web Speech API wrapper hook (`useSpeechRecognition`) replacing the 373-line MediaRecorder + backend POST flow with a 190-line client-side `window.SpeechRecognition` consumer — interim + final results stream live, zero `/ws/voice/transcribe` round-trip, public 11-field return shape preserved byte-identical for chatHarness and ChatInterface compatibility.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-05-01T13:29:08Z
- **Completed:** 2026-05-01T13:59:46Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- HOTFIX-05 hook layer shipped: `useSpeechRecognition` wraps `window.SpeechRecognition` directly; no backend transcription POST, no MediaRecorder, no AudioContext, no Supabase auth
- 8/8 unit tests GREEN covering: support detection (Test 1), constructor flags (Test 2), interim onresult (Test 3), final accumulation (Test 4), onend version-bump semantics (Test 5), permission-denied error (Test 6), stop-vs-abort discipline (Test 7), unsupported-environment fallback (Test 8)
- 14/14 existing ChatInterface.test.tsx tests GREEN — chatHarness mock and ChatInterface destructure remained valid because the public 11-field return shape was preserved
- 9/9 existing useVoiceSession.test.ts tests GREEN — Phase 84 half-duplex gate invariant intact; brain-dump path completely untouched
- TypeScript strict-mode compile clean on the new hook (`@types/dom-speech-recognition` provides typed `SpeechRecognition`, `SpeechRecognitionEvent`, `SpeechRecognitionErrorEvent`)
- ESLint clean on both the hook and its test suite (zero violations after class-based fake refactor)
- Zero modifications to `useVoiceSession.ts`, `voice_session.py`, or `components/braindump/` — SC5 boundary structurally protected, verified via `git diff --stat HEAD~2 HEAD -- ...` returning empty

## Task Commits

Each task was committed atomically following the TDD red-green-refactor cycle:

1. **Task 1 (RED): Failing unit suite + types install** — `283e8d38` (test)
   - Authored 8 RED tests in `frontend/__tests__/hooks/useSpeechRecognition.test.ts` mocking `window.SpeechRecognition` with a fake constructor
   - Installed `@types/dom-speech-recognition@^0.0.10` in frontend devDependencies
   - Confirmed RED: 7/8 tests fail against the legacy MediaRecorder hook (Test 1 passed by happenstance because the legacy hook returns `isSupported=true` based on MediaRecorder presence, not `window.SpeechRecognition`)

2. **Task 2 (GREEN): Hook rewrite + test class refactor** — `0164f3a9` (refactor)
   - Replaced the 373-line backend wrapper with a 190-line Web Speech API hook
   - Refactored test fake from function-based `FakeCtor` to class-based `FakeRec` with `static onCreate(instance)` to eliminate `@typescript-eslint/no-this-alias` lint
   - All 8 unit tests GREEN; ChatInterface.test.tsx (14 tests) and useVoiceSession.test.ts (9 tests) GREEN unchanged
   - Tightened TypeScript widening: `(window as unknown as { SpeechRecognition?: typeof SpeechRecognition; webkitSpeechRecognition?: typeof SpeechRecognition })` — narrow, intentional, lint-clean

_Note: This is a TDD plan — produces RED commit then GREEN commit, no separate REFACTOR. Test refactor was rolled into the GREEN commit since it was driven by lint feedback during GREEN execution._

## Files Created/Modified

- `frontend/src/hooks/useSpeechRecognition.ts` — Full rewrite. 190 lines. Web Speech API wrapper. `'use client'` directive. Imports only `react` (useState, useRef, useCallback, useEffect). Exports the same `UseSpeechRecognitionReturn` interface (11 fields). Constructor lookup via `getSpeechRecognitionCtor()` reads `window.SpeechRecognition || window.webkitSpeechRecognition` on every call. Event handlers: `onresult` (accumulates final to `finalRef`, sets interim to state), `onerror` (maps to friendly message via `ERROR_MESSAGES` table), `onend` (bumps `versionRef` only when `finalRef.current.trim()` is non-empty, clears interim, releases `recognitionRef`). Cleanup `useEffect` calls `abort()` (silent) so unmount never bumps `transcriptVersion`.

- `frontend/__tests__/hooks/useSpeechRecognition.test.ts` — New unit suite. 241 lines. 8 tests. `// @vitest-environment jsdom` header + Pikar copyright. Class-based `FakeRec` test fake with `static onCreate` hook to record the latest instance. Helpers: `installFakeSpeechRecognition`, `uninstallSpeechRecognition`, `fireResult(transcript, isFinal)`, `fireError(code)`, `fireEnd()`. Each test wraps state changes in `act(...)` from `@testing-library/react`.

- `frontend/package.json` — Added `"@types/dom-speech-recognition": "^0.0.10"` to devDependencies.

- `frontend/package-lock.json` — Regenerated by `npm install -D` (no other lockfile churn).

## Decisions Made

- **Per-call constructor lookup over module-load capture** — The reference skeleton in 87-RESEARCH.md captured the constructor at module load; this implementation reads it inside `getSpeechRecognitionCtor()` on every call. Rationale: Test 1 must verify both supported and unsupported cases by toggling `window.SpeechRecognition` between separate `renderHook` invocations. Module-load capture would cache stale state across the toggle and require `vi.resetModules`, complicating test setup. Per-call lookup is one extra property read per `startRecording` call — negligible cost.

- **`isSupported` initialized via `useState(() => ...)` lazy initializer, NOT recomputed each render** — Once a hook is mounted, the support detection result is fixed. Re-evaluating per render would risk flicker if the test or app mutated `window` mid-lifecycle. Captured at mount only.

- **`isTranscribing` always returns `false`** — The Web Speech API has no async transcription step (recognition fires `onend` synchronously), so the field is semantically dead in the new implementation. Kept as a public field to preserve the 11-field destructure contract; ChatInterface's 6 references to `isSpeechTranscribing` become harmless dead branches that Plan 02 will clean up.

- **Cleanup uses `abort()` not `stop()`** — `stop()` would flush in-progress interim to final and fire `onend`, which would bump `transcriptVersion`. After unmount, that bump has no observer — but on the NEXT mount of a new instance, the consumer's `transcriptVersion` effect would see a stale-looking transcript and append to input. `abort()` is silent (no `onend`), preventing this race.

- **`stopRecording` uses `stop()` (NOT `abort()`)** — Opposite discipline from cleanup. The user explicitly clicked stop or pressed Send mid-dictation; we WANT the in-progress interim to flush to final and trigger the version bump so the consumer effect appends the words to the input field. This is the load-bearing piece of "click Send mid-dictation includes the in-progress phrase" UX that Plan 02 wires up.

- **Class-based test fake (Refactor during GREEN)** — Original RED used `function FakeCtor(this: FakeRec) { ... }` which triggered `@typescript-eslint/no-this-alias` on `latest = this`. Refactored to `class FakeRec { static onCreate(instance) { latest = instance } constructor() { FakeRec.onCreate(this) } }`. Static method indirection satisfies the lint rule without changing the constructor's runtime signature.

- **Window-property cast via `as unknown as { ... }`** — `@types/dom-speech-recognition` declares `SpeechRecognition` and `webkitSpeechRecognition` as `declare var` globals, NOT as `Window` interface augmentations. Direct `window.SpeechRecognition` doesn't type-check. Intersection types like `Window & { webkitSpeechRecognition?: ... }` strip the global declarations. Solution: cast to a narrow lookup-only shape with `as unknown as { SpeechRecognition?: typeof SpeechRecognition; webkitSpeechRecognition?: typeof SpeechRecognition }`. Single, narrow, documented.

- **Backend `/ws/voice/transcribe` route NOT deleted** — Mirrors Phase 83's smart-upload disposition. The route at `app/routers/voice_session.py:745-783` is now orphaned (zero frontend callers), but cheap to keep on disk. Deletion deferred to a follow-up PR for diff isolation per the plan's `<objective>` instructions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 1 used `rerender()` after `unmount()` causing "Cannot update an unmounted root" React error**
- **Found during:** Task 2 GREEN — running unit suite revealed Test 1 still failing despite all production code being correct
- **Issue:** The original Test 1 called `rerender()` from the FIRST `renderHook` after that root had been unmounted, to reinstall the fake constructor for `afterEach` idempotency. React's `Cannot update an unmounted root` error.
- **Fix:** Replaced the trailing `rerender()` with a separate `unmount()` call on the second `renderHook`. The `afterEach` block already handles cleanup via `uninstallSpeechRecognition()`.
- **Files modified:** `frontend/__tests__/hooks/useSpeechRecognition.test.ts`
- **Verification:** Test 1 passes 7→8 → all 8 tests GREEN
- **Committed in:** `0164f3a9` (rolled into GREEN commit since the bug surfaced during GREEN verification)

**2. [Rule 1 - Bug] Test fake used function-with-`this:`-parameter constructor pattern, triggering `no-this-alias` lint**
- **Found during:** Task 2 GREEN — `npx eslint __tests__/hooks/useSpeechRecognition.test.ts` flagged 3 errors: 2 × `no-explicit-any` on event-handler types, 1 × `no-this-alias` on `latest = this` inside the function-style constructor
- **Issue:** The `function FakeCtor(this: FakeRec) { ... latest = this }` pattern from the plan's reference skeleton violated strict-ESLint house rules
- **Fix:** Refactored to a `class FakeRec` with typed event-handler fields (`(event: FakeResultEvent) => void` instead of `(event: any) => void`) and a `static onCreate(instance: FakeRec)` method invoked from the constructor as `FakeRec.onCreate(this)`. The static-method indirection avoids the `latest = this` aliasing pattern. Defined `FakeResultEvent` and `FakeErrorEvent` interfaces to type the event payloads.
- **Files modified:** `frontend/__tests__/hooks/useSpeechRecognition.test.ts`
- **Verification:** `npx eslint` returns zero errors; all 8 tests still GREEN
- **Committed in:** `0164f3a9` (GREEN commit — refactoring driven by lint feedback during GREEN, not a separate REFACTOR commit)

**3. [Rule 1 - Bug] Initial `(window as Window & { webkitSpeechRecognition?: ... })` cast caused `Property 'SpeechRecognition' does not exist on type 'Window & WindowWithWebkit'` TS error**
- **Found during:** Task 2 GREEN — `npx tsc --noEmit` flagged the type lookup at line 53
- **Issue:** `@types/dom-speech-recognition` declares `SpeechRecognition` and `webkitSpeechRecognition` as `declare var` globals, NOT as `Window` interface augmentations. The intersection-type cast `Window & WindowWithWebkit` resolves the global declarations to no-op augmentations and TS complains the property doesn't exist on the resulting type.
- **Fix:** Replaced the intersection-type cast with `(window as unknown as { SpeechRecognition?: typeof SpeechRecognition; webkitSpeechRecognition?: typeof SpeechRecognition })`. Narrow lookup-only shape; widens through `unknown` once. Documented why in the JSDoc comment on `getSpeechRecognitionCtor`.
- **Files modified:** `frontend/src/hooks/useSpeechRecognition.ts`
- **Verification:** `npx tsc --noEmit` returns no errors on the file; all 8 tests still GREEN
- **Committed in:** `0164f3a9` (GREEN commit)

---

**Total deviations:** 3 auto-fixed (3 × Rule 1 — Bug)
**Impact on plan:** All three were minor implementation details discovered during GREEN verification. None changed plan scope, none crossed the SC5 boundary, none affected the public 11-field interface. Two were test-quality fixes (lint + React lifecycle); one was a TS strict-mode interaction with `@types/dom-speech-recognition`. All resolved in <10 min and rolled into the GREEN commit.

## Issues Encountered

None — all three deviations above were straightforward Rule 1 fixes during the standard TDD GREEN verification loop.

## Authentication Gates

None — this plan is purely a frontend code change with no backend or external service interaction.

## User Setup Required

None — no external service configuration. The new hook runs entirely in-browser using the user's existing microphone permission grant. Manual UAT (Plan 02 owns the `87-MANUAL-UAT.md` scaffold) will exercise the actual `SpeechRecognition` API across Chrome/Edge/Safari/Firefox/iOS Safari.

## Verification Evidence

| Gate | Command | Result |
|------|---------|--------|
| Hook unit suite | `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts` | **8/8 GREEN** (293ms) |
| ChatInterface regression | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` | **14/14 GREEN** (2348ms) |
| Brain-dump regression (SC5 smoke) | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` | **9/9 GREEN** (3177ms) — including Phase 84 "keeps the half-duplex gate narrow" guard-rail |
| Combined suite | `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts` | **31/31 GREEN** |
| Backend severance | `grep -nE "fetch\|MediaRecorder\|AudioContext\|getUserMedia\|/ws/voice\|transcribeBlob\|supabase" frontend/src/hooks/useSpeechRecognition.ts` | Zero code matches (one docstring mention of "MediaRecorder + backend `/ws/voice/transcribe`" describing what the hook REPLACES) |
| Public interface invariant | Public-field grep on hook | All 11 fields declared in `UseSpeechRecognitionReturn` AND returned from `useSpeechRecognition()` |
| TypeScript compile | `cd frontend && npx tsc --noEmit` | Zero errors in `useSpeechRecognition.ts`, `chatHarness.ts`, or `ChatInterface.tsx` |
| ESLint | `cd frontend && npx eslint src/hooks/useSpeechRecognition.ts __tests__/hooks/useSpeechRecognition.test.ts` | Zero errors / zero warnings |
| SC5 boundary | `git diff --stat HEAD~2 HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/` | **Empty** — protected files completely untouched across both task commits |

## Hand-off to Plan 02

The hook layer is ready. Plan 02 (`87-02-chat-interface-integration`) owns:

- Removing the textarea `readOnly` and onChange-gate at `ChatInterface.tsx:1604,1607` (load-bearing for SC3)
- Replacing the transcript-version effect at `ChatInterface.tsx:355-365` with the suffix-ref live-streaming pattern (load-bearing for SC2 — words appear as they're spoken)
- Loosening Enter and Send-button disabled checks to allow mid-dictation send (calls `stopRecording()` on send to flush interim into final)
- Simplifying the recording-indicator copy at `ChatInterface.tsx:1502-1530` (drop the `isSpeechTranscribing` branch — always false now)
- Adding 5 new component tests (SC1-SC5) in `ChatInterface.test.tsx` using the existing `renderChatInterface` harness with per-test mock overrides
- Adding 1 new boundary guard-rail test ("chat mic does not call useVoiceSession") that fails CI if the two paths are ever wired together
- Authoring `87-MANUAL-UAT.md` with the 6-row browser matrix from 87-VALIDATION.md
- Sign-off on SC1-SC5 by hand against `make local-backend` + `cd frontend && npm run dev`

## Deferred Items

- **Backend `POST /voice/transcribe` route at `app/routers/voice_session.py:745-783` stays on disk.** Zero frontend callers after this plan, but cheap to keep. Mirrors Phase 83's smart-upload backend disposition. Cleanup is a separate follow-up PR for diff isolation.
- **`isSpeechTranscribing` dead branches in `ChatInterface.tsx`** (6 references). The new hook returns `isTranscribing: false` always, so all 6 branches are dead code. Plan 02 simplifies them as part of the integration work.

## Next Phase Readiness

- Plan 02 is unblocked. Hook contract verified via 31 passing tests across 3 suites.
- The chatHarness mock at `chatHarness.ts:334-348` continues to satisfy ChatInterface's destructure — no harness changes needed for Plan 02 to land its component tests.
- SC5 boundary is structurally guaranteed (zero cross-imports between `useSpeechRecognition` and `useVoiceSession`) AND verifiable via `git diff` — Plan 02 must preserve this invariant.

---
*Phase: 87-mic-dictation-via-web-speech-api*
*Completed: 2026-05-01*
