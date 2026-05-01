---
phase: 87-mic-dictation-via-web-speech-api
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/useSpeechRecognition.ts
  - frontend/__tests__/hooks/useSpeechRecognition.test.ts
  - frontend/package.json
  - frontend/package-lock.json
autonomous: true
requirements: [HOTFIX-05]

must_haves:
  truths:
    - "Hook reports isSupported=true when window.SpeechRecognition exists, false when undefined (jsdom)"
    - "startRecording() instantiates a SpeechRecognition with continuous=true, interimResults=true and sets isRecording=true"
    - "Firing onresult with an interim result updates interimTranscript without bumping transcriptVersion"
    - "Firing onresult with a final result accumulates into transcript and is preserved across subsequent interim chunks"
    - "Firing onend bumps transcriptVersion (only when finalRef has content) and clears interimTranscript and isRecording"
    - "onerror with 'not-allowed' surfaces a user-actionable permission-denied message via the error field"
    - "stopRecording() calls recognition.stop() (not abort) so any pending interim flushes into final via onend"
    - "Hook public 11-field return shape is identical to the previous backend wrapper (chatHarness.ts and ChatInterface.tsx destructure unchanged)"
    - "isTranscribing always returns false in the new implementation (kept for back-compat — eliminates intermediate 'Transcribing...' state)"
  artifacts:
    - path: "frontend/src/hooks/useSpeechRecognition.ts"
      provides: "Web Speech API wrapper hook (full rewrite of the MediaRecorder backend wrapper)"
      contains: "window.SpeechRecognition"
      min_lines: 90
    - path: "frontend/__tests__/hooks/useSpeechRecognition.test.ts"
      provides: "Vitest unit suite covering start/stop/interim/final/error/unsupported paths"
      min_lines: 120
    - path: "frontend/package.json"
      provides: "@types/dom-speech-recognition added to devDependencies"
      contains: "@types/dom-speech-recognition"
  key_links:
    - from: "frontend/src/hooks/useSpeechRecognition.ts"
      to: "window.SpeechRecognition || webkitSpeechRecognition"
      via: "constructor lookup at module scope (or first invocation of startRecording)"
      pattern: "window\\.SpeechRecognition"
    - from: "frontend/src/hooks/useSpeechRecognition.ts"
      to: "(no fetch call to /ws/voice/transcribe)"
      via: "REMOVAL — backend transcription path is severed; verifiable by absence of the URL"
      pattern: "voice/transcribe"
      negative: true
    - from: "frontend/src/components/chat/__test-utils__/chatHarness.ts"
      to: "frontend/src/hooks/useSpeechRecognition.ts"
      via: "vi.mock import — public interface UseSpeechRecognitionReturn must remain identical so existing harness compiles unchanged"
      pattern: "useSpeechRecognition"
---

<objective>
Replace the backend-transcription `useSpeechRecognition` hook with a thin client-side wrapper around `window.SpeechRecognition` (the Web Speech API), keeping the public 11-field return shape byte-identical so `chatHarness.ts` and `ChatInterface.tsx` need zero destructure changes downstream.

**Why this matters (HOTFIX-05):** the chat-input mic currently records to a Blob, posts it to `/ws/voice/transcribe`, and shows a "Transcribing..." spinner while the round-trip resolves — there are no interim results, the user can't edit the input while the mic is on, and the round-trip routinely fails. The Web Speech API runs in-browser, streams interim results in real time, and the user can edit and send like any typed message. SC1-SC4 of the phase goal are structurally impossible without this rewrite.

**Scope discipline:**
- This plan delivers the hook + its unit suite + the TypeScript typings install. **Nothing else.**
- Plan 02 owns the `ChatInterface.tsx` integration (textarea gates, suffix-ref live-streaming, Enter/Send loosening, indicator copy, 5 component tests, manual-UAT scaffold).
- Plan 02 also owns the SC5 boundary guard-rail test ("chat mic does not call useVoiceSession").
- **MUST NOT TOUCH:** `frontend/src/hooks/useVoiceSession.ts`, `app/routers/voice_session.py`, `frontend/src/components/braindump/*`. SC5 forbids it. Researcher grep-verified zero cross-imports — keep it that way.
- **DEFERRED (do NOT delete in this phase):** the orphaned backend `POST /voice/transcribe` route at `app/routers/voice_session.py:745-783`. Mirrors Phase 83's smart-upload backend disposition — leave on disk; cleanup is a separate follow-up PR for diff isolation.

**Output:** A drop-in replacement hook that compiles with strict TypeScript, passes its own unit suite, and leaves all existing chatHarness-using component tests GREEN unchanged.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/87-mic-dictation-via-web-speech-api/87-RESEARCH.md
@.planning/phases/87-mic-dictation-via-web-speech-api/87-VALIDATION.md
@frontend/src/hooks/useSpeechRecognition.ts
@frontend/src/components/chat/__test-utils__/chatHarness.ts
@frontend/__tests__/hooks/useVoiceSession.test.ts

<interfaces>
<!-- Public return shape that MUST remain identical. chatHarness.defaultSpeechRecognition() and ChatInterface.tsx:339-349 both destructure these 11 fields. Change ANY name and CI breaks. -->

```typescript
// frontend/src/hooks/useSpeechRecognition.ts (the contract)
interface UseSpeechRecognitionReturn {
  isRecording: boolean;          // recognition.start() called and not yet ended
  isSupported: boolean;          // window.SpeechRecognition || webkitSpeechRecognition exists
  isTranscribing: boolean;       // ALWAYS FALSE in Web Speech API path (kept for back-compat)
  transcript: string;            // accumulated final transcript for current session
  transcriptVersion: number;     // bumps on each finalized session (drives ChatInterface append-to-input effect)
  interimTranscript: string;     // current interim (non-final) result chunk
  error: string | null;          // friendly error message
  startRecording: () => void;
  stopRecording: () => void;
  toggleRecording: () => void;
  clearTranscript: () => void;
}
```

```typescript
// frontend/src/components/chat/__test-utils__/chatHarness.ts:334-348 (existing — DO NOT MODIFY)
function defaultSpeechRecognition() {
  return {
    isRecording: false,
    isTranscribing: false,
    toggleRecording: vi.fn(),
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    transcript: '',
    transcriptVersion: 0,
    interimTranscript: '',
    error: null,
    isSupported: false,
    clearTranscript: vi.fn(),
  }
}
```

```typescript
// frontend/src/components/chat/ChatInterface.tsx:339-349 (existing — DO NOT MODIFY in this plan)
const {
  isRecording,
  isTranscribing: isSpeechTranscribing,
  toggleRecording,
  startRecording,
  transcript: speechTranscript,
  transcriptVersion: speechTranscriptVersion,
  interimTranscript,
  error: speechError,
  isSupported: isSpeechSupported
} = useSpeechRecognition();
```
</interfaces>

<reference_skeleton>
<!-- The recommended hook implementation from 87-RESEARCH.md § Recommended Implementation. Treat this as the spec, not a strict template — strict-TS compile + unit-test GREEN are the actual gates. -->

```typescript
'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

interface UseSpeechRecognitionReturn { /* …11 fields above… */ }

// Module-load constructor lookup. SSR-safe via the typeof window guard.
const SpeechRecognitionCtor =
  typeof window === 'undefined'
    ? undefined
    : (window.SpeechRecognition ||
       (window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition);

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [transcriptVersion, setTranscriptVersion] = useState(0);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const finalRef = useRef('');
  const versionRef = useRef(0);

  const isSupported = !!SpeechRecognitionCtor;

  const startRecording = useCallback(() => {
    if (!SpeechRecognitionCtor) {
      setError('Voice input is not supported in this browser. Please type your message.');
      return;
    }
    if (recognitionRef.current) return;          // already running

    finalRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    setError(null);

    const rec = new SpeechRecognitionCtor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = navigator.language || 'en-US';

    rec.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalRef.current += (finalRef.current ? ' ' : '') + result[0].transcript.trim();
        } else {
          interim += result[0].transcript;
        }
      }
      setTranscript(finalRef.current);
      setInterimTranscript(interim);
    };

    rec.onerror = (event: SpeechRecognitionErrorEvent) => {
      const msgs: Record<string, string> = {
        'not-allowed': 'Microphone permission denied. Please allow access in your browser settings.',
        'no-speech':   'No speech detected. Please try again.',
        'audio-capture': 'No microphone found. Please connect a microphone and try again.',
        'network':     'Network error during recognition. Please retry.',
      };
      setError(msgs[event.error] ?? `Voice input failed: ${event.error}`);
      setIsRecording(false);
    };

    rec.onend = () => {
      // Auto-stop on browser-side silence: bump version IF we have final content,
      // so the consumer effect appends to input. interim is dropped (already streamed live).
      if (finalRef.current.trim()) {
        versionRef.current += 1;
        setTranscriptVersion(versionRef.current);
      }
      setInterimTranscript('');
      setIsRecording(false);
      recognitionRef.current = null;
    };

    try {
      rec.start();
      recognitionRef.current = rec;
      setIsRecording(true);
    } catch {
      setError('Could not start voice input. Please try again.');
    }
  }, []);

  const stopRecording = useCallback(() => {
    recognitionRef.current?.stop();   // NOT abort() — stop flushes interim into final via onend
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecording) stopRecording();
    else startRecording();
  }, [isRecording, startRecording, stopRecording]);

  const clearTranscript = useCallback(() => {
    finalRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    setError(null);
  }, []);

  // Cleanup: abort (silent — does NOT fire onend) so unmount never produces a phantom transcriptVersion bump.
  useEffect(() => () => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
  }, []);

  return {
    isRecording,
    isSupported,
    isTranscribing: false,
    transcript,
    transcriptVersion,
    interimTranscript,
    error,
    startRecording,
    stopRecording,
    toggleRecording,
    clearTranscript,
  };
}
```
</reference_skeleton>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Install @types/dom-speech-recognition + author useSpeechRecognition unit suite</name>
  <files>frontend/__tests__/hooks/useSpeechRecognition.test.ts, frontend/package.json, frontend/package-lock.json</files>
  <behavior>
    The unit suite mocks `window.SpeechRecognition` with a tiny fake constructor exposing `start`, `stop`, `abort`, plus `_fireResult({ transcript, isFinal })`, `_fireError(code)`, `_fireEnd()` test helpers attached to the latest instance. Every test installs the fake on `window` in `beforeEach` and removes it in `afterEach`.

    Tests (all 8 MUST be RED at end of this task — current backend-wrapper hook does not consult window.SpeechRecognition at all):

    1. `isSupported reflects window.SpeechRecognition presence`:
       - With `window.SpeechRecognition = FakeCtor`, hook returns isSupported=true.
       - Re-render with `delete window.SpeechRecognition` and `delete window.webkitSpeechRecognition` — hook returns isSupported=false (note: depending on whether the constructor is captured at module load or in startRecording, this test may need a `vi.resetModules()` between cases. Document the chosen capture site in the GREEN task.)

    2. `startRecording instantiates SpeechRecognition with continuous + interimResults`:
       - act(() => result.current.startRecording())
       - The latest fake instance has `continuous === true && interimResults === true`.
       - result.current.isRecording === true.

    3. `interim onresult updates interimTranscript without bumping transcriptVersion`:
       - Start, fire onresult with `{ transcript: 'hello', isFinal: false }`.
       - result.current.interimTranscript === 'hello'.
       - result.current.transcriptVersion === 0.
       - result.current.transcript === '' (no final yet).

    4. `final onresult accumulates into transcript`:
       - Start, fire onresult with `{ transcript: 'hello world', isFinal: true }`.
       - result.current.transcript === 'hello world'.
       - Subsequent interim onresult with `{ transcript: 'and goodb', isFinal: false }` leaves transcript === 'hello world' and sets interimTranscript === 'and goodb'.

    5. `onend bumps transcriptVersion when finalRef has content`:
       - Start, fire final onresult, fire onend.
       - result.current.transcriptVersion === 1.
       - result.current.isRecording === false.
       - result.current.interimTranscript === ''.
       - Calling stopRecording before any final → onend bumps version 0→0 (no bump when finalRef is empty).

    6. `onerror with not-allowed surfaces friendly permission message`:
       - Start, fire onerror({ error: 'not-allowed' }).
       - result.current.error matches /microphone permission|allow access/i.
       - result.current.isRecording === false.

    7. `stopRecording calls recognition.stop (not abort)`:
       - Start, then act(() => result.current.stopRecording()).
       - The fake instance's `stop` was called once; `abort` was NOT called.

    8. `unsupported environment: startRecording sets a fallback error and does not throw`:
       - With both `window.SpeechRecognition` and `window.webkitSpeechRecognition` undefined.
       - result.current.isSupported === false.
       - act(() => result.current.startRecording()) → result.current.error matches /not supported|please type/i.
       - result.current.isRecording stays false.

    Tooling:
    - `npm install -D @types/dom-speech-recognition` inside `frontend/`. Pin to `^0.0.6` (or whatever npm resolves — package is types-only).
    - File goes at `frontend/__tests__/hooks/useSpeechRecognition.test.ts` — same directory as `useVoiceSession.test.ts`. Add `// @vitest-environment jsdom` and `// Copyright (c) 2024-2026 Pikar AI…` header to match house style.
    - Use `@testing-library/react`'s `renderHook` (re-exported from `@testing-library/react` 16.x).

    Why RED: the current `useSpeechRecognition.ts` is a MediaRecorder + fetch wrapper; none of the tests above can pass against it. Run the suite at end of this task and confirm RED before handing to Task 2.
  </behavior>
  <action>
    1. From the repo root, run `cd frontend && npm install -D @types/dom-speech-recognition` (this updates both package.json and package-lock.json — commit BOTH).

    2. Create `frontend/__tests__/hooks/useSpeechRecognition.test.ts` with the 8 tests described in <behavior> above. The fake SpeechRecognition constructor pattern:

    ```typescript
    type FakeRec = {
      continuous: boolean
      interimResults: boolean
      lang: string
      onresult: ((e: any) => void) | null
      onerror: ((e: any) => void) | null
      onend: (() => void) | null
      start: ReturnType<typeof vi.fn>
      stop: ReturnType<typeof vi.fn>
      abort: ReturnType<typeof vi.fn>
    }
    let latest: FakeRec | null = null
    function FakeCtor(this: FakeRec) {
      this.continuous = false
      this.interimResults = false
      this.lang = ''
      this.onresult = null
      this.onerror = null
      this.onend = null
      this.start = vi.fn()
      this.stop = vi.fn()
      this.abort = vi.fn()
      latest = this
    }
    // beforeEach: (window as any).SpeechRecognition = FakeCtor as unknown as typeof SpeechRecognition
    // afterEach:  delete (window as any).SpeechRecognition; delete (window as any).webkitSpeechRecognition; latest = null
    ```

    3. Helpers: `fireResult(transcript, isFinal)` → `latest!.onresult!({ resultIndex: 0, results: [{ 0: { transcript }, isFinal, length: 1 }] })`. Wrap in `act(...)` for React state updates.

    4. Run `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts`. Expect RED on at minimum tests 2-7 (the current hook does not consult window.SpeechRecognition at all). Capture the failing output in your task notes for the SUMMARY.

    5. **Do NOT modify `useSpeechRecognition.ts` in this task.** Hand the RED suite to Task 2.

    6. **Boundary check:** `git diff --stat HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/` MUST return empty (no SC5-protected files modified).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts 2>&1 | tee /tmp/87-01-task1.log; grep -qE "(failed|FAIL)" /tmp/87-01-task1.log && echo "RED CONFIRMED — Task 2 may proceed" || (echo "EXPECTED RED, GOT GREEN — investigate before Task 2" && exit 1)</automated>
  </verify>
  <done>
    - `frontend/package.json` devDependencies include `@types/dom-speech-recognition`.
    - `frontend/package-lock.json` reflects the install (no other lockfile churn).
    - `frontend/__tests__/hooks/useSpeechRecognition.test.ts` exists with 8 named tests covering supported/unsupported, start, interim, final, onend, onerror, stop-vs-abort.
    - Vitest run is RED (≥6 of 8 tests failing) — output captured for SUMMARY.
    - `git diff` shows zero modifications to `useVoiceSession.ts` / `voice_session.py` / `braindump/`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Rewrite useSpeechRecognition.ts against window.SpeechRecognition</name>
  <files>frontend/src/hooks/useSpeechRecognition.ts</files>
  <behavior>
    Replace the entire file contents (~373 lines → ~110 lines) with a Web Speech API wrapper matching the <reference_skeleton> in `<context>` above. The public 11-field return shape MUST be byte-identical to the existing exports — `chatHarness.ts:334-348` and `ChatInterface.tsx:339-349` rely on this contract.

    Behavioral requirements (drive the GREEN of Task 1's RED suite):

    - **Module-load OR first-call constructor capture:** capture `window.SpeechRecognition || webkitSpeechRecognition` once. Module-load is simpler; first-call inside `startRecording` is more test-friendly (lets `delete window.SpeechRecognition` mid-suite re-flip support detection without `vi.resetModules`). Choose first-call inside startRecording — Task 1's test 1 needs it. Set `isSupported` from a `useState` initialized via `typeof window !== 'undefined' && !!(window.SpeechRecognition || (window as any).webkitSpeechRecognition)` so the value is reactive at hook-instantiation time.

    - **Strict TS without `as any` proliferation:** with `@types/dom-speech-recognition` installed, `window.SpeechRecognition` is typed. The webkit prefix needs a single narrow cast: `(window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition`.

    - **isTranscribing always returns false** — kept as a public field for back-compat. `ChatInterface.tsx` has 6 references to `isSpeechTranscribing`; they become dead branches but cause no harm. Plan 02 will simplify them as part of integration.

    - **Cleanup uses `abort()`, NOT `stop()`** — `stop()` would fire `onend` and bump `transcriptVersion` after unmount, causing a phantom append-to-input on the next mount. `abort()` is silent.

    - **stopRecording uses `recognition.stop()`** — flushes interim into final via the engine's `onend`, supporting "click Send mid-dictation includes the in-progress phrase" UX (Plan 02 wires this).

    - **Permission-denied message must be user-actionable.** Use the exact `msgs` table from the skeleton. The amber pill at `ChatInterface.tsx:1533-1537` already renders `speechError` — Plan 02 keeps it.

    - **No fetch to any backend transcription endpoint.** Verifiable post-rewrite via `grep -n "voice/transcribe\|transcribeBlob\|MediaRecorder\|AudioContext\|getUserMedia" frontend/src/hooks/useSpeechRecognition.ts` returning ZERO matches.

    - **'use client' directive** at the top — uses useState + browser API, must be a Client Component module.

    - **Lint MUST pass** — `cd frontend && npm run lint -- src/hooks/useSpeechRecognition.ts` returns clean. Project lints with strict ESLint; resolve any warnings before commit.

    - **Existing chatHarness-using tests MUST stay GREEN.** The only file outside Plan 01's scope that imports `useSpeechRecognition` directly (vs. the harness mock) is none — the harness mock IS the production-test surface. Run `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` to confirm zero regressions in the existing 4+ tests of that file.

    - **Brain-dump regression suite MUST stay GREEN.** Run `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` to confirm Phase 84's "keeps the half-duplex gate narrow" guard-rail and all other useVoiceSession tests still pass.
  </behavior>
  <action>
    1. Open `frontend/src/hooks/useSpeechRecognition.ts` and replace the ENTIRE file with the implementation from the <reference_skeleton> in `<context>`. Adjust the constructor capture site to live inside `startRecording` (read `(typeof window !== 'undefined' && (window.SpeechRecognition || (window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition)) || undefined`) so Task 1 test 1 passes without `vi.resetModules`.

    2. Initialize `isSupported` via `useState(() => typeof window !== 'undefined' && !!(window.SpeechRecognition || (window as any).webkitSpeechRecognition))`. Acceptable to use a single narrow `as any` here OR the typed `Window & { webkitSpeechRecognition?: ... }` cast — both lint clean.

    3. Run the unit suite from Task 1 — must go GREEN on all 8:
       ```
       cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts
       ```

    4. Run the existing ChatInterface suite to confirm no regressions (the chatHarness mock, not the production hook, is what those tests exercise — they should remain GREEN since the public 11-field shape is unchanged):
       ```
       cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx
       ```

    5. Run the brain-dump regression suite (SC5 boundary smoke):
       ```
       cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts
       ```

    6. Run lint specifically on the rewritten file:
       ```
       cd frontend && npx eslint src/hooks/useSpeechRecognition.ts
       ```

    7. Verify the backend-wrapper code is fully gone:
       ```
       grep -nE "voice/transcribe|transcribeBlob|MediaRecorder|AudioContext|getUserMedia" frontend/src/hooks/useSpeechRecognition.ts
       ```
       Expected: zero matches.

    8. Verify the public interface unchanged (smoke):
       ```
       grep -nE "^\s*(isRecording|isSupported|isTranscribing|transcript|transcriptVersion|interimTranscript|error|startRecording|stopRecording|toggleRecording|clearTranscript)" frontend/src/hooks/useSpeechRecognition.ts | wc -l
       ```
       Expected: ≥11 (one declaration line per public field minimum, more are fine).

    9. **Boundary check:** `git diff --stat HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/` MUST return empty.

    10. Stage the four files (`frontend/src/hooks/useSpeechRecognition.ts`, `frontend/__tests__/hooks/useSpeechRecognition.test.ts`, `frontend/package.json`, `frontend/package-lock.json`) for commit by execute-plan's commit step.
  </action>
  <verify>
    <automated>cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts</automated>
  </verify>
  <done>
    - `frontend/src/hooks/useSpeechRecognition.ts` is a Web Speech API wrapper, ~110 lines, no MediaRecorder / AudioContext / fetch / Supabase imports.
    - All 8 tests in `__tests__/hooks/useSpeechRecognition.test.ts` GREEN.
    - All 4 existing tests in `src/components/chat/ChatInterface.test.tsx` GREEN (the chatHarness mock keeps them stable).
    - All tests in `__tests__/hooks/useVoiceSession.test.ts` GREEN (Phase 84 boundary smoke).
    - `npx eslint src/hooks/useSpeechRecognition.ts` clean.
    - `grep "voice/transcribe\|MediaRecorder" useSpeechRecognition.ts` returns zero matches.
    - `git diff` shows zero modifications to `useVoiceSession.ts` / `voice_session.py` / `braindump/`.
  </done>
</task>

</tasks>

<verification>
**Plan-level gates (run after both tasks):**

1. **Hook unit suite:** `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts` — ALL 8 tests GREEN.

2. **ChatInterface suite (existing 4+ tests, no regression):** `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` — GREEN. Plan 02 will ADD 5 new tests; this plan must not break the existing ones.

3. **Brain-dump regression (SC5 boundary smoke):** `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` — ALL tests GREEN. Phase 84's "keeps the half-duplex gate narrow" guard-rail in particular MUST stay GREEN.

4. **Boundary diff invariant:** `git diff --stat HEAD~1..HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/` MUST be empty after this plan's commit.

5. **Backend-wrapper severance:** `grep -nE "voice/transcribe|MediaRecorder|AudioContext|getUserMedia|transcribeBlob" frontend/src/hooks/useSpeechRecognition.ts` returns ZERO matches.

6. **Public interface invariant:** chatHarness.ts compiles unchanged. `cd frontend && npx tsc --noEmit -p .` (or whatever project tsc config) reports zero errors.

7. **Lint:** `cd frontend && npx eslint src/hooks/useSpeechRecognition.ts __tests__/hooks/useSpeechRecognition.test.ts` clean.
</verification>

<success_criteria>
- [x] HOTFIX-05 sub-goal: chat-input mic hook wraps `window.SpeechRecognition`, not a backend POST.
- [x] Public 11-field return shape unchanged (downstream destructures untouched).
- [x] Strict-TS compile clean via `@types/dom-speech-recognition`.
- [x] 8 unit tests in `useSpeechRecognition.test.ts` GREEN.
- [x] Existing ChatInterface and useVoiceSession suites GREEN unchanged.
- [x] Zero modifications to `useVoiceSession.ts`, `voice_session.py`, `braindump/`.
- [x] No fetch to `/ws/voice/transcribe` and no MediaRecorder/AudioContext code in the new hook.

**Out of scope for this plan (delivered by Plan 02):**
- Removing the textarea `readOnly`/onChange-gate at `ChatInterface.tsx:1604,1607` (load-bearing for SC3).
- Replacing the transcript-version effect at `ChatInterface.tsx:355-365` with the suffix-ref live-streaming pattern (load-bearing for SC2).
- Loosening Enter/Send gates to allow mid-dictation send.
- Simplifying the recording-indicator copy at `ChatInterface.tsx:1502-1530` (drop the Transcribing branch).
- 5 new component tests (SC1-SC5) + 1 boundary guard-rail test ("chat mic does not call useVoiceSession").
- `87-MANUAL-UAT.md` 6-row browser matrix.
- STATE/ROADMAP/SUMMARY updates.
</success_criteria>

<output>
After completion, create `.planning/phases/87-mic-dictation-via-web-speech-api/87-01-speech-recognition-hook-rewrite-SUMMARY.md` documenting:
- Files modified (4) + line counts (≈110 in hook, ≈150 in test).
- The 8 unit tests with their RED→GREEN transition evidence.
- Confirmation that chatHarness.ts and ChatInterface.tsx required ZERO destructure changes (the public interface invariant held).
- Confirmation of zero diff in the SC5-protected files.
- The constructor-capture decision (first-call inside startRecording vs module-load) and rationale.
- Hand-off note for Plan 02: the hook is ready; Plan 02 owns the ChatInterface integration + SC1-SC5 component tests + boundary guard-rail + manual UAT.
- Deferred item: orphaned backend `POST /voice/transcribe` route stays on disk (Phase 83 precedent).
</output>
