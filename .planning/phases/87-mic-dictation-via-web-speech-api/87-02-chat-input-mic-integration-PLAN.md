---
phase: 87-mic-dictation-via-web-speech-api
plan: 02
type: execute
wave: 2
depends_on: ["87-01"]
files_modified:
  - frontend/src/components/chat/ChatInterface.tsx
  - frontend/src/components/chat/ChatInterface.test.tsx
  - .planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md
autonomous: true
requirements: [HOTFIX-05]

must_haves:
  truths:
    - "SC1: clicking the mic button on the chat input calls useSpeechRecognition().toggleRecording (start when idle, stop when recording)"
    - "SC2: when isRecording=true and interimTranscript='hello', the textarea's displayed value contains 'hello' (interim words appear live as user speaks)"
    - "SC3: while recording, the textarea is editable — onChange fires setInput; readOnly is FALSE; the user can backspace/edit dictated text"
    - "SC3-extension: pressing Enter or clicking Send while recording stops recognition (recognition.stop() flushes interim) and dispatches sendMessage with the combined text"
    - "SC4: when isSpeechSupported=false, the mic button renders disabled with title='Voice input not supported in this browser' and no error toast appears spontaneously"
    - "SC5-boundary: the chat-input mic toggleRecording handler does NOT invoke ANY symbol exported from useVoiceSession (verified by guard-rail test that asserts useVoiceSession's connect/disconnect were never called when only the chat mic is exercised)"
    - "SC5-regression: every test in frontend/__tests__/hooks/useVoiceSession.test.ts remains GREEN unchanged after Plan 02 — the brain-dump path is not modified, including the Phase 84 'keeps the half-duplex gate narrow' guard-rail"
    - "Brain-dump invariant: frontend/src/hooks/useVoiceSession.ts and app/routers/voice_session.py have ZERO line-level diff after this plan's commit"
  artifacts:
    - path: "frontend/src/components/chat/ChatInterface.tsx"
      provides: "Updated mic-input integration: editable textarea during recording, suffix-ref live-streaming of interim, mid-dictation send, simplified indicator copy"
      contains: "interimTranscript"
    - path: "frontend/src/components/chat/ChatInterface.test.tsx"
      provides: "5 SC1-SC5 component tests + 1 SC5 boundary guard-rail, appended to existing test suite"
      contains: "chat mic does not call useVoiceSession"
    - path: ".planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md"
      provides: "6-row browser matrix UAT scaffold (Chrome, Edge, Safari macOS, Firefox, iOS Safari, brain-dump boundary smoke)"
      min_lines: 40
  key_links:
    - from: "frontend/src/components/chat/ChatInterface.tsx textarea"
      to: "user keyboard input"
      via: "onChange={(e) => setInput(e.target.value)} — readOnly removed, onChange-gate removed"
      pattern: "onChange=\\{\\(e\\) => setInput"
    - from: "frontend/src/components/chat/ChatInterface.tsx displayedText computation"
      to: "input + dictation suffix"
      via: "suffix-ref pattern — displayedText = input + (isRecording ? interimTranscript : '')"
      pattern: "displayedText"
    - from: "frontend/src/components/chat/ChatInterface.tsx mic button"
      to: "useSpeechRecognition().toggleRecording"
      via: "onClick={toggleRecording} (already exists, leave in place)"
      pattern: "onClick=\\{toggleRecording\\}"
    - from: "frontend/src/components/chat/ChatInterface.tsx (chat mic flow)"
      to: "frontend/src/hooks/useVoiceSession.ts (brain-dump)"
      via: "ZERO calls — boundary guard-rail test fails CI if any chat-mic handler ever invokes voiceSession.connect/disconnect"
      pattern: "voiceSession\\.(connect|disconnect)"
      negative: true
---

<objective>
Wire the rewritten `useSpeechRecognition` hook from Plan 01 into `ChatInterface.tsx` so dictated words stream live into the input field, the user can edit while dictating, and clicking Send mid-dictation captures the in-progress phrase. Append 5 component tests covering SC1-SC5 plus 1 boundary guard-rail test that fails CI if anyone ever wires the chat-mic flow into the brain-dump session.

**Why this matters (HOTFIX-05 finalization):** Plan 01 makes the hook capable of streaming interim results in real time, but `ChatInterface.tsx` currently sets the textarea to `readOnly` while recording and only appends to `input` once `transcriptVersion` bumps post-recording. SC2 (live interim in input) and SC3 (editability mid-dictation) are structurally impossible without removing the `readOnly` gate and replacing the transcriptVersion-only effect with a suffix-ref live-streaming pattern.

**SC5 boundary protection (locked, non-negotiable):**
- ZERO modifications to `frontend/src/hooks/useVoiceSession.ts` or `app/routers/voice_session.py`.
- ZERO modifications to `frontend/src/components/braindump/*`.
- A new component test asserts the chat-mic flow never invokes any `useVoiceSession` symbol — fails CI if anyone ever wires the two paths together.
- Existing `frontend/__tests__/hooks/useVoiceSession.test.ts` (including Phase 84's "keeps the half-duplex gate narrow" guard-rail) MUST stay GREEN unchanged.

**Scope discipline:**
- This plan is ChatInterface integration + tests + UAT scaffold + STATE/ROADMAP/SUMMARY. Nothing else.
- The orphaned backend `POST /voice/transcribe` route at `app/routers/voice_session.py:745-783` stays on disk (Phase 83 smart-upload precedent — defer cleanup to a follow-up PR).
- The 6 references to `isSpeechTranscribing` in `ChatInterface.tsx` are dead branches after Plan 01 (always false). Simplify the few that improve readability (recording indicator copy); leave the rest as-is. Mass-cleanup is out of scope.

**Output:** SC1-SC5 GREEN in vitest; manual UAT scaffold ready for browser testing; STATE.md, ROADMAP.md, and 87-02-SUMMARY.md updated.
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
@.planning/phases/87-mic-dictation-via-web-speech-api/87-01-speech-recognition-hook-rewrite-PLAN.md
@frontend/src/components/chat/ChatInterface.tsx
@frontend/src/components/chat/ChatInterface.test.tsx
@frontend/src/components/chat/__test-utils__/chatHarness.ts
@frontend/src/hooks/useSpeechRecognition.ts

<interfaces>
<!-- The chatHarness already mocks useSpeechRecognition + useVoiceSession with all expected fields.
     Per-test override pattern (proven by Phase 88-04):
       vi.mocked(useSpeechRecognition).mockReturnValueOnce({ ...defaultShape, isRecording: true, interimTranscript: 'hello' })
     But because chatHarness installs the mock via vi.mocked(...).mockReturnValue inside renderChatInterface(),
     test files override AFTER the render call by re-calling vi.mocked(...).mockReturnValue then triggering a re-render
     OR by overriding BEFORE the render via vi.mocked(...).mockReturnValueOnce — verify which pattern works in practice. -->

```typescript
// chatHarness.defaultSpeechRecognition() — full destructure surface
{
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

// chatHarness.defaultVoiceSession() — full destructure surface (DO NOT TOUCH in this plan)
{
  isConnected: false,
  isAgentSpeaking: false,
  agentTranscript: '',
  userTranscript: '',
  transcriptTurns: [],
  error: null,
  remainingSeconds: null,
  isWrappingUp: false,
  isTimedOut: false,
  connect: vi.fn().mockResolvedValue(undefined),
  disconnect: vi.fn(),
}
```

```typescript
// Existing ChatInterface.tsx anchor lines (PRE-Plan-02):
// Line 339-349: useSpeechRecognition destructure (KEEP unchanged — Plan 01 already preserved the shape)
// Line 355-365: existing transcriptVersion-only effect (REPLACE with suffix-ref live-stream)
// Line 1069: const displayedText = input;  ← MUST become: input + (isRecording ? (interimTranscript_or_speechTranscript-since-record-start) : '')
// Line 1078: handleKeyDown gate (LOOSEN to allow mid-dictation send)
// Line 1502-1530: Recording Indicator JSX (SIMPLIFY — drop Transcribing branch)
// Line 1604: onChange={(e) => !isRecording && setInput(e.target.value)}  ← REMOVE the !isRecording gate
// Line 1607: readOnly={isRecording || isSpeechTranscribing}  ← REMOVE entirely (SC3 load-bearing)
// Line 1702-1726: mic button supported/unsupported branch (KEEP — already SC1+SC4-correct)
// Line 1743: send button disabled list (LOOSEN to allow mid-dictation send)
```
</interfaces>

<surgical_edits>
<!-- The 6 surgical edits to ChatInterface.tsx, in order. Apply with Edit tool, not Write — preserve all surrounding code. -->

**Edit 1 — Replace the transcriptVersion-only effect at lines 355-365 with the suffix-ref live-streaming pattern:**

Current (lines 354-365):
```tsx
  // Append a finished backend transcript once per completed recording.
  useEffect(() => {
    if (!speechTranscript.trim()) return;
    if (speechTranscriptVersion <= handledTranscriptVersionRef.current) return;

    handledTranscriptVersionRef.current = speechTranscriptVersion;
    if (isBrainstorming) {
      sendMessage(speechTranscript, 'collab');
    } else {
      setInput(prev => prev ? `${prev} ${speechTranscript}` : speechTranscript);
    }
  }, [speechTranscript, speechTranscriptVersion, isBrainstorming, sendMessage]);
```

Replacement (preserves the brainstorming auto-send branch and the dedupe via handledTranscriptVersionRef):
```tsx
  // Snapshot of `input` at the moment recording started — used to render
  // a live "input + (final + interim)" suffix during dictation without
  // racing the user's typed input.
  const inputAtRecordStartRef = useRef('');

  // When recording starts, snapshot the current input. When it ends
  // (transcriptVersion bump), commit `input + final` into setInput so the
  // dictated text becomes editable. The interim suffix is purely visual
  // (rendered via displayedText below) and never written to setInput
  // mid-dictation — that avoids fighting the user's keystrokes.
  useEffect(() => {
    if (isRecording) {
      inputAtRecordStartRef.current = input;
    }
    // intentional: only react to the recording-edge, not every input keystroke
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRecording]);

  // On finalization (transcriptVersion bump), commit final transcript.
  useEffect(() => {
    if (!speechTranscript.trim()) return;
    if (speechTranscriptVersion <= handledTranscriptVersionRef.current) return;

    handledTranscriptVersionRef.current = speechTranscriptVersion;
    if (isBrainstorming) {
      sendMessage(speechTranscript, 'collab');
    } else {
      const baseline = inputAtRecordStartRef.current;
      const combined = baseline ? `${baseline} ${speechTranscript}` : speechTranscript;
      setInput(combined);
    }
  }, [speechTranscript, speechTranscriptVersion, isBrainstorming, sendMessage]);
```

**Edit 2 — Replace `const displayedText = input;` at line 1069 with the suffix computation:**

```tsx
  // displayedText folds the live dictation suffix on top of `input` while
  // recording. The textarea reads displayedText as its `value`; setInput
  // only fires from real user keystrokes (textarea onChange) or from the
  // commit-on-stop effect above. This keeps the UI live (SC2) while
  // staying editable (SC3) without races.
  const dictationSuffix = isRecording
    ? [speechTranscript, interimTranscript].filter((s) => s && s.trim()).join(' ')
    : '';
  const displayedText = isRecording && dictationSuffix
    ? (input ? `${input} ${dictationSuffix}` : dictationSuffix)
    : input;
```

**Edit 3 — Loosen `handleKeyDown` at line 1078 to allow mid-dictation Enter, auto-stopping recognition:**

Current:
```tsx
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isUploading && !isSpeechTranscribing && !isRecording) {
      e.preventDefault();
      handleSend();
    }
  };
```

Replacement:
```tsx
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isUploading) {
      e.preventDefault();
      // If dictating, stop recognition so any pending interim flushes into
      // final via onend BEFORE handleSend reads the input. stopRecording
      // calls recognition.stop() (NOT abort), which preserves interim.
      if (isRecording) stopRecording();
      handleSend();
    }
  };
```

Note: `stopRecording` must be added to the destructure on line 339-349. The Plan 01 hook already exports it; check the existing destructure and add `stopRecording` if missing — most likely it IS missing today since the existing flow auto-stops via the silence loop.

**Edit 4 — Simplify the Recording Indicator JSX at lines 1502-1530 (drop the Transcribing branch — isSpeechTranscribing is always false post-Plan-01):**

Current is a 28-line block branching on `isSpeechTranscribing`. Replacement is a 14-line block:

```tsx
            {/* Recording Indicator */}
            {isRecording && (
              <div className="mb-2 flex items-center gap-2 p-2 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="relative flex h-3 w-3">
                    <span className="absolute inline-flex h-full w-full rounded-full animate-ping bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                  </span>
                  <span className="text-sm font-medium text-red-600">Listening...</span>
                </div>
                {(speechTranscript || interimTranscript) && (
                  <span className="text-sm text-red-500 italic truncate flex-1">
                    &ldquo;{[speechTranscript, interimTranscript].filter(Boolean).join(' ')}&rdquo;
                  </span>
                )}
                <button
                  onClick={toggleRecording}
                  className="text-xs text-red-600 hover:text-red-800 font-medium flex-shrink-0 ml-auto"
                >
                  Stop
                </button>
              </div>
            )}
```

**Edit 5 — Remove the `!isRecording` gate on the textarea onChange at line 1604, and remove the `readOnly` prop entirely at line 1607:**

Current:
```tsx
                onChange={(e) => !isRecording && setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isUploading || isSpeechTranscribing}
                readOnly={isRecording || isSpeechTranscribing}
```

Replacement (keep `disabled={isUploading || isSpeechTranscribing}` — isSpeechTranscribing is always false now, so it effectively becomes `disabled={isUploading}`, which is correct):
```tsx
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isUploading || isSpeechTranscribing}
```

**Important:** the `displayedText` from Edit 2 is what the textarea renders via `value={displayedText}`. When the user types mid-dictation, `setInput` updates `input`, the suffix re-derives, and `displayedText` recomputes — no race. The user's keystrokes land in `input`; the dictation suffix is purely visual until the commit-on-stop effect folds it in.

**Edit 6 — Loosen the Send button's disabled list at line 1743 (find the send `<button>` whose disabled list includes `isRecording || isSpeechTranscribing`) so mid-dictation send works the same as Edit 3:**

Likely current pattern:
```tsx
disabled={isStreaming || isUploading || isSpeechTranscribing || /* possibly */ isRecording}
```

Replacement: drop `isRecording` (and `isSpeechTranscribing` if present — always false now). Wrap the onClick to call `stopRecording()` first if `isRecording`:
```tsx
onClick={() => {
  if (isRecording) stopRecording();
  handleSend();
}}
disabled={isStreaming || isUploading}
```

**Confirm exact line via grep at execution time:** `grep -nE "disabled=\\{.*isSpeechTranscribing.*\\}" frontend/src/components/chat/ChatInterface.tsx` will surface every gate. Plan 02 must touch only the SEND-button gate, not the file-attach gate or the file-pill remove-button gate (those should keep `isRecording` to prevent file shenanigans during dictation).
</surgical_edits>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Append 5 SC1-SC5 component tests + 1 boundary guard-rail to ChatInterface.test.tsx; create 87-MANUAL-UAT.md</name>
  <files>frontend/src/components/chat/ChatInterface.test.tsx, .planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md</files>
  <behavior>
    Append a new `describe('ChatInterface — HOTFIX-05 mic dictation', ...)` block to `frontend/src/components/chat/ChatInterface.test.tsx`. Six tests that MUST be RED before Task 2 applies the ChatInterface edits:

    **Test 1 — SC1: "mic button toggles recognition"**
    - Render with `vi.mocked(useSpeechRecognition).mockReturnValueOnce({ ...defaultShape, isSupported: true, toggleRecording: spy })`. Override BEFORE renderChatInterface call.
    - Locate the mic button by `title=/Start voice input/i` (existing). Click it.
    - Assert `spy` was called once.
    - Re-render with `isRecording: true` and `title=/Stop recording/i`; click again; assert spy called again.

    **Test 2 — SC2: "interim transcript appears in input"**
    - Render with `vi.mocked(useSpeechRecognition).mockReturnValueOnce({ ...defaultShape, isSupported: true, isRecording: true, interimTranscript: 'hello world', transcript: '' })`.
    - Locate the textarea by placeholder OR by id="chat-input-text".
    - Assert textarea.value contains 'hello world' (the displayedText computation should fold interim into the displayed value while recording — this is what fails today because `displayedText = input;` ignores interim).

    **Test 3 — SC3: "user can edit dictated text"**
    - Render with `vi.mocked(useSpeechRecognition).mockReturnValueOnce({ ...defaultShape, isSupported: true, isRecording: true, interimTranscript: 'hello' })`.
    - Locate the textarea. Assert it is NOT readOnly (`expect(textarea.readOnly).toBe(false)` — currently true via line 1607).
    - fireEvent.change(textarea, { target: { value: 'edited text' } }). Assert no exception thrown and the change handler did NOT silently swallow (current code's `!isRecording && setInput(...)` swallows changes during recording — without the gate removal, the value rendered post-change won't reflect the typed text because input never updated).

    **Test 4 — SC4: "unsupported browser shows fallback"**
    - Render with `vi.mocked(useSpeechRecognition).mockReturnValueOnce({ ...defaultShape, isSupported: false })`.
    - Locate the disabled mic button by `title=/Voice input not supported in this browser/i`.
    - Assert button.disabled === true.
    - Assert no `screen.queryByText(/error|failed/i)` toast is present.

    **Test 5 — SC5 boundary guard-rail: "chat mic does not call useVoiceSession"**
    - Render normally (any speech-recognition state). Spy on `useVoiceSession`'s connect/disconnect via `vi.mocked(useVoiceSession).mockReturnValue({ ...defaultVoiceSession, connect: connectSpy, disconnect: disconnectSpy })` — set BEFORE renderChatInterface so the chatHarness picks up the override.
    - Click the chat mic button (the one with title /Start voice input/i, NOT the brain-dump Brain icon).
    - Wait microtask tick.
    - Assert `connectSpy` was NEVER called. Assert `disconnectSpy` was NEVER called.
    - This is a permanent guard-rail: if anyone ever wires the chat-mic flow into `useVoiceSession.connect`, this test fails CI. **Comment in the test body explicitly states this is the SC5 boundary guard-rail and must never be deleted.**

    **Test 6 — SC5 regression: brain-dump suite link (NOT a new test, but the focused-run command MUST include it)**
    - This is satisfied by the verify command running `__tests__/hooks/useVoiceSession.test.ts` alongside ChatInterface.test.tsx. No new test code; the existing 7+ tests there must remain GREEN.

    Tests 1, 4 may pass against current code (the mic button onClick already wires toggleRecording from the hook; the unsupported branch already renders correct title text). Tests 2, 3 MUST fail RED. Test 5 likely passes RED (current code doesn't wire chat mic to voiceSession either) but is a permanent invariant — keep it. Document RED status per test in the task notes.

    **87-MANUAL-UAT.md** (new file at `.planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md`) — 6-row browser matrix from 87-RESEARCH.md § Manual UAT:

    | Browser | UAT Steps | Pass Criteria | Result | Tester | Date |
    |---------|-----------|---------------|--------|--------|------|
    | Chrome desktop | … | … | ⬜ pending | | |
    | Edge desktop | … | … | ⬜ pending | | |
    | Safari macOS 17+ | … | … | ⬜ pending | | |
    | Firefox desktop | … | … | ⬜ pending | | |
    | iOS Safari 14.5+ | … | … | ⬜ pending | | |
    | **Boundary smoke (brain-dump)** | … | Phase 84 behavior unchanged | ⬜ pending | | |

    Include a "Sign-off" section at the bottom: SC1, SC2, SC3, SC4, SC5 each with a checkbox to sign off. Steps copied verbatim from 87-RESEARCH.md to avoid drift.
  </behavior>
  <action>
    1. Open `frontend/src/components/chat/ChatInterface.test.tsx`. Append a new `describe('ChatInterface — HOTFIX-05 mic dictation', ...)` block at the end of the file (after the existing HOTFIX-01 block).

    2. Inside the new describe, write the 6 tests described in <behavior>. Use the chatHarness override pattern proven by Phase 88-04:
       ```typescript
       import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'
       import { useVoiceSession } from '@/hooks/useVoiceSession'

       const baseSpeech = {
         isRecording: false, isTranscribing: false, isSupported: true,
         toggleRecording: vi.fn(), startRecording: vi.fn(), stopRecording: vi.fn(),
         transcript: '', transcriptVersion: 0, interimTranscript: '',
         error: null, clearTranscript: vi.fn(),
       }

       it('SC1: mic button toggles recognition', () => {
         const toggleSpy = vi.fn()
         vi.mocked(useSpeechRecognition).mockReturnValueOnce({ ...baseSpeech, toggleRecording: toggleSpy })
         renderChatInterface()
         const micBtn = screen.getByTitle(/Start voice input/i)
         fireEvent.click(micBtn)
         expect(toggleSpy).toHaveBeenCalledTimes(1)
       })
       ```
       *Note:* `mockReturnValueOnce` chained ahead of renderChatInterface works because chatHarness re-installs `vi.mocked(useSpeechRecognition).mockReturnValue(...)` inside renderChatInterface, which is a different mock-stack frame. If `mockReturnValueOnce` doesn't take effect, fall back to overriding via a second `vi.mocked(...).mockReturnValue(...)` AFTER renderChatInterface and re-rendering — document the chosen pattern in your task notes.

    3. Test 5 (SC5 boundary guard-rail) requires a vi.fn() spy on connect+disconnect. Use:
       ```typescript
       const connectSpy = vi.fn().mockResolvedValue(undefined)
       const disconnectSpy = vi.fn()
       vi.mocked(useVoiceSession).mockReturnValueOnce({
         isConnected: false, isAgentSpeaking: false, agentTranscript: '',
         userTranscript: '', transcriptTurns: [], error: null,
         remainingSeconds: null, isWrappingUp: false, isTimedOut: false,
         connect: connectSpy, disconnect: disconnectSpy,
       })
       renderChatInterface()
       fireEvent.click(screen.getByTitle(/Start voice input/i))
       expect(connectSpy).not.toHaveBeenCalled()
       expect(disconnectSpy).not.toHaveBeenCalled()
       ```
       Add a verbose comment at the top of this test:
       ```
       // SC5 boundary guard-rail: this test fails CI if anyone ever wires the
       // chat-input mic flow into useVoiceSession.connect/disconnect. The two
       // paths must remain structurally independent. DO NOT DELETE.
       ```

    4. Run the focused suite — at minimum SC2 + SC3 must be RED:
       ```
       cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "HOTFIX-05"
       ```
       Capture which tests are RED for the SUMMARY.

    5. Create `.planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md` with:
       - Front-matter (`phase: 87`, `slug: mic-dictation-via-web-speech-api`, `type: manual_uat`, `created: 2026-05-01`).
       - The 6-row browser matrix with steps copied verbatim from 87-RESEARCH.md § Manual UAT.
       - SC1-SC5 sign-off section at the bottom (5 checkboxes).
       - Boundary clause: "If brain-dump regresses (Brain icon click no longer connects, or the agent goes silent mid-conversation), STOP and escalate — chat-input mic changes must NOT affect this. Phase 84 behavior is the load-bearing invariant per `project_voice_brain_dump_architecture.md`."

    6. Boundary check: `git diff --stat HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/ frontend/src/hooks/useSpeechRecognition.ts` MUST return empty (we don't touch any of these in Plan 02).
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "HOTFIX-05" 2>&1 | tee /tmp/87-02-task1.log; grep -qE "(failed|FAIL)" /tmp/87-02-task1.log && echo "RED CONFIRMED — Task 2 may proceed" || (echo "EXPECTED RED on SC2/SC3 — investigate before Task 2" && exit 1)</automated>
  </verify>
  <done>
    - 6 new tests appended to `ChatInterface.test.tsx` under `describe('ChatInterface — HOTFIX-05 mic dictation', ...)`.
    - SC2 + SC3 tests RED. SC1, SC4, SC5 may be GREEN already (acceptable — the gates were already correct on those axes).
    - `87-MANUAL-UAT.md` created with 6-row matrix + SC1-SC5 sign-off + brain-dump boundary clause.
    - Zero modifications to SC5-protected files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Apply 6 surgical edits to ChatInterface.tsx; run full suite + lint; update STATE/ROADMAP/SUMMARY</name>
  <files>frontend/src/components/chat/ChatInterface.tsx, .planning/STATE.md, .planning/ROADMAP.md, .planning/phases/87-mic-dictation-via-web-speech-api/87-02-chat-input-mic-integration-SUMMARY.md</files>
  <behavior>
    Apply the 6 surgical edits enumerated in `<context>` § `<surgical_edits>` to `ChatInterface.tsx`, then drive the RED Task-1 tests to GREEN. Edits in order:

    1. Replace transcript-version effect at lines 354-365 with two coordinated effects (record-start snapshot + commit-on-finalize). Adds `inputAtRecordStartRef`.
    2. Replace `const displayedText = input;` (line 1069) with the suffix computation that folds `interimTranscript` while `isRecording`.
    3. Loosen `handleKeyDown` (line 1078) to drop the `!isRecording && !isSpeechTranscribing` clauses; auto-stop recognition before `handleSend()`.
    4. Simplify Recording Indicator JSX (lines 1502-1530) — drop the `isSpeechTranscribing` branch, keep the "Listening…" + Stop button affordance + interim-quote display.
    5. Remove `!isRecording &&` gate from textarea onChange (line 1604) and remove `readOnly={isRecording || isSpeechTranscribing}` prop (line 1607). Keep `disabled={isUploading || isSpeechTranscribing}` — isSpeechTranscribing is dead-code-false post-Plan 01, harmless to leave.
    6. Loosen Send-button disabled list (around line 1743) to drop `isRecording`/`isSpeechTranscribing`; wrap onClick to call `stopRecording()` first if `isRecording`. **Confirm via grep BEFORE editing** to find the SEND button specifically — do NOT touch the file-attach gate or file-pill remove-button gate (those keep isRecording for safety).

    Add `stopRecording` to the destructure on lines 339-349 if missing — it's needed by Edits 3 and 6.

    Behavior after all 6 edits:
    - SC1: clicking mic calls toggleRecording (already worked — preserved).
    - SC2: while isRecording, displayedText folds interim into the textarea value (Edit 2).
    - SC3: while isRecording, textarea is editable; user can backspace; setInput fires from real keystrokes (Edit 5).
    - SC3-extension: pressing Enter or Send mid-dictation auto-stops + sends (Edits 3, 6).
    - SC4: unsupported branch unchanged (already correct).
    - SC5: zero diff in useVoiceSession.ts / voice_session.py / braindump/.

    **All 4 existing ChatInterface tests must stay GREEN.** All 6 new HOTFIX-05 tests must turn GREEN. Plan 88 tests in the same file must stay GREEN. Brain-dump regression suite must stay GREEN.

    **Lint must pass:** `cd frontend && npx eslint src/components/chat/ChatInterface.tsx` returns clean.

    **STATE.md update:** Append a new YAML stanza at the top with `stopped_at: Completed 87-mic-dictation-via-web-speech-api 87-02-chat-input-mic-integration-PLAN.md`, last_updated set to ISO timestamp, and a last_activity line summarizing both plans of Phase 87.

    **ROADMAP.md update:** In the Phase 87 entry, change `**Plans:** 0 plans` to `**Plans:** 2/2 plans complete`, replace the `- [ ] TBD (run /gsd:plan-phase 87 to break down)` line with two `- [x]` entries pointing to 87-01 and 87-02 plans + brief objectives. Append HOTFIX-05 to the Hotfix Requirements section in REQUIREMENTS.md if not already present, then update the Traceability table.

    **SUMMARY.md** (`87-02-chat-input-mic-integration-SUMMARY.md`): the standard execute-plan summary plus a dedicated "SC5 Boundary Preservation" section documenting:
    - Zero line-level diff in `useVoiceSession.ts` and `app/routers/voice_session.py` — verifiable via `git diff HEAD~2..HEAD -- <those paths>` returning empty.
    - The new boundary guard-rail test ("chat mic does not call useVoiceSession") at `ChatInterface.test.tsx` is permanent and will fail CI on any future PR that wires the two paths together.
    - The orphaned backend `POST /voice/transcribe` route stays on disk (Phase 83 precedent) — defer cleanup to a follow-up PR.
  </behavior>
  <action>
    1. **Pre-edit grep to confirm exact line numbers** (the file has had recent edits from Phase 88; line numbers in 87-RESEARCH.md may have drifted by ±5):
       ```
       grep -nE "speechTranscriptVersion|displayedText|handleKeyDown|isSpeechTranscribing|onChange.*setInput|readOnly|isSpeechSupported \\?" frontend/src/components/chat/ChatInterface.tsx | head -30
       ```
       Update each Edit's line numbers in your task notes BEFORE applying via the Edit tool.

    2. **Edit 1** — Replace lines 354-365 effect block. Use the Edit tool with `old_string` matching the existing 11-line useEffect block and `new_string` containing the two new effects + `inputAtRecordStartRef`.

    3. **Edit 2** — Replace `const displayedText = input;` at line ~1069 with the dictationSuffix + displayedText computation.

    4. **Edit 3** — Replace handleKeyDown body. Add `stopRecording` to the destructure on line 339-349 if missing.

    5. **Edit 4** — Replace Recording Indicator JSX block at lines ~1502-1530.

    6. **Edit 5** — Remove the `!isRecording &&` gate on textarea onChange and remove the entire `readOnly={...}` prop line.

    7. **Edit 6** — Confirm the Send button via grep (`grep -nB2 -A4 "handleSend\\b" frontend/src/components/chat/ChatInterface.tsx | head -40`) and apply the disabled-list + onClick edits SPECIFICALLY to the send button. Do NOT touch the file-attach button (Paperclip) or the file-pill remove button (those keep isRecording).

    8. Run the full focused suite — all 6 HOTFIX-05 tests must be GREEN, all existing tests must stay GREEN:
       ```
       cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx
       ```

    9. Run the brain-dump regression suite (SC5 boundary smoke) — must stay GREEN unchanged:
       ```
       cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts
       ```

    10. Run the focused VALIDATION.md command (matches per-task table rows 87-02-01..06):
        ```
        cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts __tests__/hooks/useSpeechRecognition.test.ts
        ```

    11. Run lint:
        ```
        cd frontend && npx eslint src/components/chat/ChatInterface.tsx
        ```

    12. Run the full vitest suite (per-wave gate per VALIDATION.md):
        ```
        cd frontend && npm test
        ```

    13. **Boundary diff invariant check (CRITICAL):**
        ```
        git diff --stat HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/ frontend/src/hooks/useSpeechRecognition.ts frontend/__tests__/hooks/useSpeechRecognition.test.ts frontend/__tests__/hooks/useVoiceSession.test.ts
        ```
        Expected: empty (the only files modified by Plan 02 are ChatInterface.tsx, ChatInterface.test.tsx, .planning/* files, and the SUMMARY).

    14. Update `.planning/STATE.md` — prepend a new YAML stanza:
        ```yaml
        ---
        gsd_state_version: 1.0
        milestone: v10.0
        milestone_name: Platform Hardening & Quality
        status: planning
        stopped_at: Completed 87-mic-dictation-via-web-speech-api 87-02-chat-input-mic-integration-PLAN.md
        last_updated: "<ISO timestamp>"
        last_activity: "<ISO date> — Phase 87 COMPLETE (2/2 plans). 87-01 rewrote useSpeechRecognition.ts as a Web Speech API wrapper (~110 lines, public 11-field shape preserved); 87-02 wired ChatInterface for live interim streaming + editable textarea + mid-dictation send + simplified indicator. 6 new HOTFIX-05 tests GREEN incl. SC5 boundary guard-rail. useVoiceSession.ts and app/routers/voice_session.py UNCHANGED."
        progress:
          total_phases: 15
          completed_phases: 13
          total_plans: <existing+2>
          completed_plans: <existing+2>
        ---
        ```

    15. Update `.planning/ROADMAP.md` — Phase 87 entry: change "Plans: 0 plans" to "Plans: 2/2 plans complete" and replace the placeholder TBD line with:
        ```
        Plans:
        - [x] 87-01-speech-recognition-hook-rewrite-PLAN.md — HOTFIX-05: rewrite useSpeechRecognition.ts as a thin wrapper around window.SpeechRecognition; @types/dom-speech-recognition install; 8 unit tests
        - [x] 87-02-chat-input-mic-integration-PLAN.md — HOTFIX-05: wire ChatInterface for live interim streaming + editable textarea (SC1-SC5) + boundary guard-rail; 87-MANUAL-UAT.md scaffold
        ```
        Append a row to the Progress table: `| 87. Mic Dictation via Web Speech API | v10.0-hotfix | Complete    | <date> | <date> |`.

    16. Update `.planning/REQUIREMENTS.md` — add HOTFIX-05 to the "Hotfix Requirements" section if missing:
        ```
        - [x] **HOTFIX-05** (Phase 87): Chat-input mic button uses browser SpeechRecognition API for in-browser dictation. useSpeechRecognition.ts rewritten as a Web Speech API wrapper (~110 lines, public 11-field shape preserved); ChatInterface.tsx textarea readOnly removed (SC3); displayedText folds interimTranscript live (SC2); mid-dictation Enter/Send auto-stops recognition. SC5 boundary preserved — useVoiceSession.ts and app/routers/voice_session.py unchanged; permanent guard-rail test "chat mic does not call useVoiceSession" added to ChatInterface.test.tsx.
        ```
        Append `| HOTFIX-05 | Phase 87 | Complete |` to the Traceability table.

    17. Create `.planning/phases/87-mic-dictation-via-web-speech-api/87-02-chat-input-mic-integration-SUMMARY.md` following the standard execute-plan summary template, with an additional **SC5 Boundary Preservation** section documenting:
        - Zero line-level diff in `useVoiceSession.ts` (`git log --oneline -p HEAD~2..HEAD -- frontend/src/hooks/useVoiceSession.ts` returns empty patch).
        - Zero line-level diff in `app/routers/voice_session.py`.
        - The boundary guard-rail test exists and is GREEN; it asserts `useVoiceSession.connect`/`disconnect` are never called from chat-mic interactions.
        - The orphaned `POST /voice/transcribe` route is still on disk; cleanup deferred (Phase 83 precedent).
        - Manual UAT in `87-MANUAL-UAT.md` is pending real-browser sign-off across 6 rows; phase is "code complete, manual UAT pending."
  </action>
  <verify>
    <automated>cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts __tests__/hooks/useSpeechRecognition.test.ts</automated>
  </verify>
  <done>
    - 6 surgical edits applied to ChatInterface.tsx; file compiles + lints clean.
    - All 6 HOTFIX-05 tests in ChatInterface.test.tsx GREEN.
    - All existing tests in ChatInterface.test.tsx (Phase 83 HOTFIX-01, Phase 88 multi-tab, original ChatInterface basics) GREEN.
    - All tests in `__tests__/hooks/useVoiceSession.test.ts` GREEN unchanged (Phase 84 boundary smoke incl. "keeps the half-duplex gate narrow" guard-rail).
    - Full vitest suite (`npm test`) GREEN.
    - Lint clean on ChatInterface.tsx.
    - Boundary diff invariant: ZERO modifications to useVoiceSession.ts, voice_session.py, braindump/, useSpeechRecognition.ts (Plan 01 finalized those; Plan 02 only consumes them).
    - STATE.md, ROADMAP.md, REQUIREMENTS.md updated with Phase 87 completion + HOTFIX-05 traceability row.
    - 87-02-SUMMARY.md created with SC5 Boundary Preservation section.
    - 87-MANUAL-UAT.md exists awaiting real-browser sign-off (logged as "code complete, UAT pending" in SUMMARY).
  </done>
</task>

</tasks>

<verification>
**Plan-level gates (run after both tasks):**

1. **Per-task verification table from VALIDATION.md (rows 87-02-01..06):**
   ```
   cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "HOTFIX-05"
   ```
   All 6 SC1-SC5 tests + boundary guard-rail GREEN.

2. **Full ChatInterface.test.tsx (no regression on Phase 83/88 tests):**
   ```
   cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx
   ```

3. **Brain-dump regression smoke (SC5 invariant — VALIDATION.md row 87-02-06):**
   ```
   cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts
   ```
   GREEN unchanged.

4. **useSpeechRecognition unit suite (Plan 01 carry-over verification):**
   ```
   cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts
   ```
   GREEN unchanged.

5. **Full focused suite per VALIDATION.md per-task table:**
   ```
   cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts
   ```

6. **Phase-gate full suite:**
   ```
   cd frontend && npm test
   ```

7. **Lint:**
   ```
   cd frontend && npx eslint src/components/chat/ChatInterface.tsx src/components/chat/ChatInterface.test.tsx
   ```

8. **Boundary diff invariant (zero modifications to SC5-protected files across Plan 01 + Plan 02):**
   ```
   git diff --stat <base-of-phase-87>..HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/
   ```
   Expected: empty.

9. **Manual UAT scaffold present:**
   ```
   test -f .planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md
   ```

10. **STATE/ROADMAP/REQUIREMENTS updated:**
    - STATE.md top stanza references "87-02-chat-input-mic-integration-PLAN.md" complete.
    - ROADMAP.md Phase 87 shows "2/2 plans complete" and progress table row added.
    - REQUIREMENTS.md Hotfix Requirements section includes HOTFIX-05 + Traceability row.
</verification>

<success_criteria>
- [x] **SC1** — Mic button toggles recognition (test 1 GREEN).
- [x] **SC2** — Interim transcript appears in input field live (test 2 GREEN; suffix-ref pattern in displayedText).
- [x] **SC3** — User can edit dictated text and press send (test 3 GREEN; readOnly removed; mid-dictation Enter/Send auto-stops).
- [x] **SC4** — Unsupported browser shows fallback message (test 4 GREEN; existing branch preserved).
- [x] **SC5 — Brain-dump untouched** (test 5 GREEN guard-rail; useVoiceSession.ts & voice_session.py UNCHANGED line-for-line; useVoiceSession.test.ts GREEN).
- [x] All Phase 83 HOTFIX-01 tests, Phase 88 multi-tab tests, and original ChatInterface basics still GREEN.
- [x] Lint clean on ChatInterface.tsx.
- [x] Manual UAT scaffold ready for real-browser sign-off (Phase 87 will be "code complete, UAT pending" until rows are filled).
- [x] STATE/ROADMAP/REQUIREMENTS reflect Phase 87 closure with HOTFIX-05 traceability.
- [x] **Phase 87 SUMMARY documents that the orphaned backend `POST /voice/transcribe` route stays on disk** (deferred to follow-up PR per Phase 83 precedent).

**Out of scope (explicitly deferred):**
- Deleting backend `POST /voice/transcribe` route at `app/routers/voice_session.py:745-783` and the chat-mic-related portion of `speech_to_text_service.py` (the service stays anyway — it's used by `knowledge_service.py` for vault audio). Cleanup is a separate follow-up PR for diff isolation.
- Mass-cleaning the 6 references to `isSpeechTranscribing` in ChatInterface.tsx that are now dead branches (always false). Most are file-attach safety gates that still make sense. Kept as-is.
- Cursor-position-aware dictation insertion (current behavior: append to end, matching Google/Dragon convention — accepted in 87-RESEARCH.md § Open Questions Q3).
</success_criteria>

<output>
After completion:

1. Create `.planning/phases/87-mic-dictation-via-web-speech-api/87-02-chat-input-mic-integration-SUMMARY.md` covering:
   - Files modified (3 production + 3 planning).
   - The 6 surgical edits applied with line-number deltas.
   - The 6 new HOTFIX-05 tests with their RED→GREEN transition.
   - **SC5 Boundary Preservation section** (mandatory) listing:
     - Zero line-level diff in useVoiceSession.ts and app/routers/voice_session.py (verifiable via git diff).
     - The permanent boundary guard-rail test in ChatInterface.test.tsx ("chat mic does not call useVoiceSession").
     - The orphaned `POST /voice/transcribe` route deferred to follow-up.
   - Hand-off note for `/gsd:verify-work`: code complete, manual UAT pending in `87-MANUAL-UAT.md` across 6 browser rows.

2. STATE.md, ROADMAP.md, REQUIREMENTS.md updates as described in Task 2.

3. Phase 87 closure: ready for manual UAT, then `/gsd:verify-work 87` once rows are signed off.
</output>
