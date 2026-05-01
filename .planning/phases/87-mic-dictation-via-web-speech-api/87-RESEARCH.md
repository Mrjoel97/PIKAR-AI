# Phase 87: Mic Dictation via Web Speech API — Research

**Researched:** 2026-04-30
**Domain:** Browser Web Speech API (`SpeechRecognition`), React 19 hooks, vitest 4 + jsdom
**Confidence:** HIGH

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HOTFIX-05 | Replace chat-input mic flow with browser `SpeechRecognition` API; interim + final results stream into the input field; brain-dump voice (`useVoiceSession`) untouched | Current `useSpeechRecognition.ts` is a **MediaRecorder + backend POST** wrapper — full rewrite needed. ChatInterface's textarea is currently `readOnly` while recording (`ChatInterface.tsx:1607`); rewrite must remove that gate. Brain-dump path is fully separate (separate hook, separate WebSocket endpoint, no cross-import) — boundary preservation is straightforward. |

## Phase Summary

Rewrite `frontend/src/hooks/useSpeechRecognition.ts` from a MediaRecorder→`/ws/voice/transcribe` backend wrapper into a thin client-side wrapper around `window.SpeechRecognition || window.webkitSpeechRecognition`. Stream interim results into the chat textarea live, finalize on pause, keep the same return-shape so `ChatInterface.tsx` and `chatHarness.ts` don't need restructuring — only the parts that gate the textarea on recording must change.

## Current Implementation

### Chat-input mic flow (the SUBJECT of this phase)

| Location | What it does today |
|----------|-------------------|
| `frontend/src/hooks/useSpeechRecognition.ts:74-372` | Hook records mic via `MediaRecorder`, runs a custom RMS silence detector to auto-stop, POSTs the resulting blob to `${NEXT_PUBLIC_API_URL}/ws/voice/transcribe` with a Supabase bearer token, and returns the final string in `transcript`. **No interim results** — the user sees `"Transcribing..."` while waiting for the round-trip. |
| `frontend/src/hooks/useSpeechRecognition.ts:147` | Calls `POST /ws/voice/transcribe` with FormData (`audio`, `language_code`). Backend returns `{ success, transcript, confidence, error, mime_type }`. |
| `frontend/src/hooks/useSpeechRecognition.ts:50-56` | `recorderSupported()` returns true if `navigator.mediaDevices.getUserMedia` AND `MediaRecorder` exist — drives `isSupported`. |
| `frontend/src/hooks/useSpeechRecognition.ts:24-27` | Auto-stop after 1.4s of silence with RMS threshold 0.02 — proxied as a server-side VAD. |
| `frontend/src/components/chat/ChatInterface.tsx:30,338-349` | Imports `useSpeechRecognition` and destructures all 11 fields: `isRecording, isTranscribing, toggleRecording, startRecording, transcript, transcriptVersion, interimTranscript, error (renamed speechError), isSupported (renamed isSpeechSupported)`. |
| `frontend/src/components/chat/ChatInterface.tsx:355-365` | `useEffect` watching `speechTranscriptVersion`: on each completed transcript bump, either appends to `input` (`setInput(prev => prev ? \`${prev} ${speechTranscript}\` : speechTranscript)`) or auto-sends the message if currently brainstorming. Uses `transcriptVersion` to dedupe. |
| `frontend/src/components/chat/ChatInterface.tsx:1502-1530` | "Recording…" / "Transcribing…" indicator pill above the textarea; renders `speechTranscript` and `interimTranscript` together as a quoted preview while recording. |
| `frontend/src/components/chat/ChatInterface.tsx:1599-1620` | Textarea: `readOnly={isRecording || isSpeechTranscribing}`, `disabled={isUploading || isSpeechTranscribing}`, `onChange={(e) => !isRecording && setInput(e.target.value)}`. **The user is blocked from editing while listening — this contradicts SC3 and must change.** |
| `frontend/src/components/chat/ChatInterface.tsx:1702-1726` | Mic button: `isSpeechSupported` ternary — supported branch wires `onClick={toggleRecording}`, disabled while `isStreaming || isUploading || isSpeechTranscribing || voiceSession.isConnected`; unsupported branch renders a disabled mic with the title "Voice input not supported in this browser". |
| `frontend/src/components/chat/ChatInterface.tsx:1078,1604,1607,1670,1697,1743` | Six places that gate other UI on `isRecording` / `isSpeechTranscribing`. Most are still appropriate (e.g. disable file-attach while listening); the textarea readOnly/disabled and the keyDown gate are the ones that must relax. |

### Backend transcription endpoint (will be DETACHED)

| Location | What it does |
|----------|-------------|
| `app/routers/voice_session.py:745-783` | `POST /voice/transcribe` — accepts an audio upload, calls `speech_to_text_service.transcribe_audio` via `asyncio.to_thread`, returns `{success, transcript, confidence, error, mime_type}`. Only consumer is the current chat-input flow. |
| `app/services/speech_to_text_service.py:259` | Google Cloud STT wrapper — also called by `app/services/knowledge_service.py:390` for vault audio ingestion. Service stays; only the HTTP route's chat-mic consumer goes away. |

**Decision:** the route can stay on disk (no consumers after this phase, but cheap to keep — same pattern as the smart-upload backend route in Phase 83). Mark for follow-up cleanup but do NOT delete in this phase to keep the diff minimal.

### Brain-dump path (the BOUNDARY — MUST NOT TOUCH)

| Location | What it does |
|----------|-------------|
| `frontend/src/hooks/useVoiceSession.ts` | Full-duplex WebSocket session to `voice_session.py` Gemini Live endpoint. 16 kHz PCM mic capture via AudioWorklet, 24 kHz speaker playback, half-duplex `isPlayingRef` gate (Phase 84), RMS noise-floor cutoff at `forwardInputChunk` (Phase 84). Completely independent of `useSpeechRecognition`. |
| `frontend/src/components/chat/ChatInterface.tsx:31,224-258,474,601` | Brain-dump uses `useVoiceSession`, `BrainDumpMenu`, `VoiceBrainstormOverlay` — entirely separate UI affordance from the chat-input mic. The two never co-listen: `BrainDumpMenu` is `disabled` while `isRecording` (chat mic), and the chat mic is `disabled` while `voiceSession.isConnected` (`ChatInterface.tsx:1670,1705`). |
| `app/routers/voice_session.py` (websocket, separate route) | Brain-dump's WebSocket endpoint and its STT internals are unrelated to the HTTP `/voice/transcribe` route. |

**Boundary verification (grep):** `useVoiceSession` and `useSpeechRecognition` have **zero** cross-imports. Confirmed by grep — neither file references the other. The protection for SC5 is structural, not policy.

### Uncommitted changes (do they affect this phase?)

`git diff --stat HEAD -- frontend/src/components/chat/ChatInterface.tsx frontend/src/hooks/useSpeechRecognition.ts` returned empty. The uncommitted changes in `useAgentChat.ts`, `useSessionPreload.ts`, and `lib/sessionHistory.ts` do not touch speech recognition (verified by grep for `speech|recogn|mic` in their diffs — zero matches). **Phase 87 has a clean working surface.**

### Wave 0 test infrastructure (already in place)

| File | Status |
|------|--------|
| `frontend/src/components/chat/__test-utils__/chatHarness.ts:65-67,147,334-348,494-496` | `vi.mock('@/hooks/useSpeechRecognition', ...)` already wired with all 11 fields stubbed. Phase 87 can lean on this directly — no harness changes required if the new hook keeps the same return shape. |
| `frontend/vitest.config.mts` | jsdom, globals=true, `@` alias to `src/` — sufficient for unit + component tests. |
| `frontend/src/components/chat/ChatInterface.test.tsx` | Already imports `renderChatInterface`, includes a "replaces send button with stop button when streaming" test that proves the harness is healthy. |

## Recommended Implementation

### High-level shape

Rewrite `useSpeechRecognition.ts` to:
1. Return the **exact same 11-field public interface** so `ChatInterface.tsx` and `chatHarness.ts` need no destructure-line changes
2. Replace `MediaRecorder + transcribeBlob` with `SpeechRecognition` event-driven streaming
3. Emit interim results via `interimTranscript` field on every `onresult` event
4. Emit a `transcriptVersion` bump when `recognition.onend` fires (or when user presses stop) so the existing append-to-input effect at `ChatInterface.tsx:355-365` still works
5. Detect support via `typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)`
6. **Remove `isTranscribing`** semantically (no async backend) — keep the field for back-compat but always return `false`. This eliminates the "Transcribing…" intermediate state (SC3).

### Hook return-shape contract (UNCHANGED)

```typescript
interface UseSpeechRecognitionReturn {
  isRecording: boolean;          // recognition.start() called and not yet ended
  isSupported: boolean;          // window.SpeechRecognition || webkitSpeechRecognition
  isTranscribing: boolean;       // ALWAYS FALSE in new implementation (kept for back-compat)
  transcript: string;            // accumulated final transcript for current session
  transcriptVersion: number;     // bumps on each finalized session (drives the "append to input" effect)
  interimTranscript: string;     // current interim (non-final) result chunk
  error: string | null;          // friendly error message
  startRecording: () => void;
  stopRecording: () => void;
  toggleRecording: () => void;
  clearTranscript: () => void;
}
```

### TypeScript typings strategy

`SpeechRecognition` is **NOT** in `lib.dom.d.ts` for either Chromium or webkit prefixes. Three options ranked:

| Option | Verdict | Why |
|--------|---------|-----|
| `npm install -D @types/dom-speech-recognition` | **PREFERRED** | Zero project-specific code; types match the W3C draft spec; widely used (~7M weekly downloads). One-line `package.json` add, no production runtime cost (devDep). |
| Custom `frontend/src/types/speech-recognition.d.ts` | Acceptable fallback | Avoids a new dep, ~30 lines of declarations. Use only if `@types/dom-speech-recognition` is rejected for license/policy reasons (it's MIT). |
| `(window as any).SpeechRecognition` | **REJECT** | Project lints with strict TS; `as any` casts are tolerated in some places but will draw review heat in a hook this central. Avoid. |

Recommend: **install `@types/dom-speech-recognition`**. After install, the constructor lookup is:

```typescript
const SpeechRecognitionCtor =
  typeof window === 'undefined'
    ? undefined
    : (window.SpeechRecognition || (window as Window & { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition);
```

The `as` cast is local and narrowly scoped. Once `@types/dom-speech-recognition` is installed, `window.SpeechRecognition` is typed; only the `webkit` prefix needs widening — and only in a single line.

### Core hook skeleton (to be detailed in plan)

```typescript
'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

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
    if (recognitionRef.current) return;

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
        'no-speech': 'No speech detected. Please try again.',
        'audio-capture': 'No microphone found. Please connect a microphone and try again.',
        'network': 'Network error during recognition. Please retry.',
      };
      setError(msgs[event.error] ?? `Voice input failed: ${event.error}`);
      setIsRecording(false);
    };

    rec.onend = () => {
      // Auto-stop on browser-side silence: flush current interim into final, bump version,
      // let the consumer effect append to input.
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
    } catch (err) {
      setError('Could not start voice input. Please try again.');
    }
  }, []);

  const stopRecording = useCallback(() => {
    recognitionRef.current?.stop();
    // onend handles state cleanup
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

  useEffect(() => () => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
  }, []);

  return {
    isRecording,
    isSupported,
    isTranscribing: false,           // legacy field — always false in Web Speech API path
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

### ChatInterface.tsx edits (small, surgical)

1. **Remove `readOnly` and the onChange-gate on the textarea** so the user can edit while dictating (SC3):
   ```diff
   - onChange={(e) => !isRecording && setInput(e.target.value)}
   + onChange={(e) => setInput(e.target.value)}
   - readOnly={isRecording || isSpeechTranscribing}
   ```
   Keep `disabled={isUploading || isSpeechTranscribing}` (isSpeechTranscribing is now always false — keeps the disable on isUploading only, harmless).

2. **Inline the interim transcript into the textarea value** so words appear as they're spoken (SC2). Recommended pattern: replace the existing `useEffect` at `ChatInterface.tsx:355-365` with two coordinated effects:

   - **Live interim effect:** while `isRecording`, append `interimTranscript` to a *display-only* suffix that lives next to `input`. Use a ref to remember the input value at the moment recording started, then render `displayedText = inputAtRecordStart + finalTranscript + interimTranscript`. On stop (transcriptVersion bump), commit `displayedText` to `input` and clear the suffix.

   - **Simpler alternative (LOWER UX quality but smaller diff):** keep the existing transcriptVersion-bump effect; just stream `transcript + interimTranscript` into `setInput` directly on every change while `isRecording`. Risk: races with user typing during dictation. Choose this only if the cleaner pattern is too disruptive for a hotfix.

   Recommendation: cleaner pattern (suffix ref). It's 15 lines and matches the SC2/SC3 contract precisely.

3. **Loosen the `handleKeyDown` gate** at `ChatInterface.tsx:1078` so Enter sends mid-dictation (UX choice — but cleaner: stop recognition on send so the in-progress interim flushes into final before the request goes out):
   ```diff
   - if (e.key === 'Enter' && !e.shiftKey && !isUploading && !isSpeechTranscribing && !isRecording) {
   + if (e.key === 'Enter' && !e.shiftKey && !isUploading) {
        e.preventDefault();
   +    if (isRecording) stopRecording();
        handleSend();
      }
   ```
   Plus same change in `handleSend` button's disabled list (line 1743).

4. **Update the "Recording…" indicator copy** (`ChatInterface.tsx:1502-1530`) — remove the `isSpeechTranscribing` branch entirely (always false now); just render a "Listening…" pill with a stop button while `isRecording`.

5. **Fallback message (SC4):** the unsupported branch at `ChatInterface.tsx:1719-1726` already renders a disabled mic with the title "Voice input not supported in this browser". Improve it by also surfacing a one-line inline message inside `speechError` when the user clicks an unsupported mic OR when `recognitionRef` errors with `not-allowed`. Specifically, `startRecording` already sets that error in the new hook — and the existing `speechError` UI at `ChatInterface.tsx:1533-1537` already renders amber-styled errors. So the fallback story works **for free** if SC4 just means "tell me what to do" via that pill.

### `package.json` edit

Add `@types/dom-speech-recognition` to `devDependencies`:
```bash
cd frontend && npm install -D @types/dom-speech-recognition
```

Pin to a stable version (currently 0.0.6). The package is types-only, zero runtime cost.

## Files Involved

### Must modify

| File | Change |
|------|--------|
| `frontend/src/hooks/useSpeechRecognition.ts` | Full rewrite (≈373 lines → ≈110 lines). Remove MediaRecorder, AudioContext, RMS silence loop, Supabase auth, fetch to `/ws/voice/transcribe`. Replace with `SpeechRecognition` event handlers. Keep the 11-field public interface intact. |
| `frontend/src/components/chat/ChatInterface.tsx` | (a) Remove textarea `readOnly` and onChange-gate (line 1604, 1607); (b) Replace the transcript-version effect (lines 355-365) with suffix-ref live-streaming pattern; (c) Loosen `handleKeyDown` and Send-button disabled checks to allow mid-dictation send (auto-stops recognition on send); (d) Simplify Recording-indicator copy (lines 1502-1530) to drop the Transcribing branch. |
| `frontend/package.json` + `package-lock.json` | Add `@types/dom-speech-recognition` to `devDependencies`. |

### Must read (for context, NOT modify in this phase)

| File | Why |
|------|-----|
| `frontend/src/components/chat/__test-utils__/chatHarness.ts` | `defaultSpeechRecognition()` at lines 334-348 — confirms the 11-field shape that production tests rely on. New hook MUST keep all 11 fields. |
| `frontend/src/components/chat/ChatInterface.test.tsx` | Existing 4 tests at lines 49-93 must still pass. Plan should add new tests in this file (or a sibling) for SC1-SC4. |

### MUST NOT TOUCH (protects SC5)

| File | Why |
|------|-----|
| `frontend/src/hooks/useVoiceSession.ts` | Brain-dump full-duplex session. Phase 84's narrow gate (HOTFIX-02) is the load-bearing invariant — see `project_voice_brain_dump_architecture.md` memory. |
| `app/routers/voice_session.py` (lines 1-744 + WebSocket route) | Brain-dump WebSocket. Only line 745-783 (HTTP `/voice/transcribe`) is in scope, and even that is **left on disk** — only the chat-input frontend caller is removed. |
| `frontend/src/components/braindump/VoiceBrainstormOverlay.tsx` | Brain-dump UI. Independent of chat-input mic. |
| `frontend/__tests__/hooks/useVoiceSession.test.ts` | The Phase 84 guard-rail test ("keeps the half-duplex gate narrow") must continue to pass unchanged. |

### Tests (new, to be added in plan)

| File | Coverage |
|------|----------|
| `frontend/__tests__/hooks/useSpeechRecognition.test.ts` (NEW) | Mock `window.SpeechRecognition` constructor; assert: start sets `isRecording=true`, `onresult` interim chunk updates `interimTranscript`, final chunk appends to `transcript`, `onend` bumps `transcriptVersion`, `onerror` with `not-allowed` sets friendly error, unsupported environment returns `isSupported=false`. |
| `frontend/src/components/chat/ChatInterface.test.tsx` (extend) | Add tests using `renderChatInterface({ /* override speech mock */ })`: (a) clicking the mic button calls `toggleRecording` (SC1); (b) when `interimTranscript='hello'`, the textarea shows `hello` live (SC2); (c) when `transcriptVersion` bumps, the textarea remains editable and the user can backspace (SC3); (d) when `isSpeechSupported=false`, the disabled-mic branch renders with the unsupported tooltip (SC4); (e) **boundary test**: render with `voiceSession.isConnected=true` and assert the mic button is `disabled` AND no chat-mic state was wired into `useVoiceSession` (SC5 guard-rail). |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 4.0.18 + @testing-library/react 16.3.2 (jsdom 27.4.0) |
| Config file | `frontend/vitest.config.mts` |
| Quick run command | `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts src/components/chat/ChatInterface.test.tsx` |
| Full suite command | `cd frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| HOTFIX-05 / SC1 | Mic button click → start/stop recognition | unit + component | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "mic button toggles recognition"` | ❌ Wave 0 — extend existing test file |
| HOTFIX-05 / SC2 | Interim results stream into textarea live | component | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "interim transcript appears in input"` | ❌ Wave 0 |
| HOTFIX-05 / SC3 | User can edit the dictated text and press send normally | component | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "user can edit dictated text"` | ❌ Wave 0 |
| HOTFIX-05 / SC4 | Unsupported browser → fallback message | component | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "unsupported browser shows fallback"` | ❌ Wave 0 |
| HOTFIX-05 / SC5 | Brain-dump voice unaffected (boundary) | regression + guard-rail | `npx vitest run __tests__/hooks/useVoiceSession.test.ts` (existing — must remain green) + new boundary assertion in ChatInterface.test.tsx | Existing useVoiceSession tests already cover; add 1 new guard-rail test |
| HOTFIX-05 / hook unit | Hook responds to `SpeechRecognition` events correctly | unit | `npx vitest run __tests__/hooks/useSpeechRecognition.test.ts` | ❌ Wave 0 — new file |

### Sampling Rate
- **Per task commit:** `npx vitest run __tests__/hooks/useSpeechRecognition.test.ts src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts` (≈8s on the dev box)
- **Per wave merge:** `cd frontend && npm test`
- **Phase gate:** Full suite green + manual UAT below before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/__tests__/hooks/useSpeechRecognition.test.ts` — new unit test file. Mock `window.SpeechRecognition` with a fake constructor that exposes `start`, `stop`, `abort`, and lets the test fire `onresult`/`onerror`/`onend` callbacks.
- [ ] `frontend/src/components/chat/ChatInterface.test.tsx` — extend with 5 new tests (SC1-SC5). The harness already supports per-render override of `useSpeechRecognition` mock.
- [ ] No new framework install needed — vitest 4 + jsdom + @testing-library/react are already configured (Phase 83 chatHarness is the existence proof).
- [ ] Type install: `npm install -D @types/dom-speech-recognition` so the new hook compiles cleanly.

### Manual UAT (REQUIRED — not automatable in jsdom)

jsdom does NOT implement `SpeechRecognition`. Real-browser UAT is mandatory:

| Browser | UAT Steps | Pass Criteria |
|---------|-----------|---------------|
| Chrome desktop | Open `/dashboard/chat`, click mic, say "Hello world this is a test", pause | Words appear in input live; input remains editable; clicking send delivers the message |
| Edge desktop | Same | Same (Chromium-based, expected identical) |
| Safari macOS 17+ | Same | Words appear (with possible 200-500ms delay vs Chrome) |
| Firefox desktop | Click mic | Disabled-mic with "Voice input not supported in this browser" tooltip; OR support-detect goes false and no error toast (whichever the new code chooses — choose disabled tooltip for clarity) |
| iOS Safari 14.5+ | Same as Chrome | Words appear (may require user-gesture; click-to-start covers it) |
| **All browsers — boundary smoke** | Click brain-dump (Brain icon), confirm voice session connects, agent greets, user can speak | No regression in Phase 84 behavior; brain-dump path unchanged |

## Open Questions / Risks

1. **`continuous=true` and Chrome's auto-stop after long silence**
   - Chrome's `SpeechRecognition` ends the session after ~30-60s of silence even with `continuous=true`. The user must click mic again.
   - **Mitigation:** the `onend` handler already bumps `transcriptVersion` so the user's words are flushed to input before the session ends. Acceptable UX — and arguably better than rolling our own keep-alive.

2. **Mid-dictation send UX**
   - If user clicks Send while `isRecording`, do we (a) finish current interim then send, or (b) abort and send what we have?
   - **Recommendation:** (a) — call `recognition.stop()` (NOT `abort()`), which fires `onend` with the final interim flushed. The send happens after `transcriptVersion` bumps, so the message includes the in-progress phrase. Wire this in `handleKeyDown` and `handleSend`.

3. **Race: user types while dictating**
   - Suffix-ref pattern handles this: the live `displayedText` is `input + final + interim`. The user's `setInput` writes only land in `input`; the dictation suffix is appended on render. On stop, the suffix folds into `input`.
   - **Risk:** if the user puts their cursor in the middle of `input` and dictates, the dictated text appears at the end (not at the cursor). This is the standard Google/Dragon dictation behavior — accept it.

4. **Permission denial UX**
   - First click triggers browser permission prompt. If denied, `onerror` fires with `not-allowed`. The new hook surfaces a friendly amber pill via `speechError`.
   - **Risk:** subsequent clicks DON'T re-prompt automatically (browser caches the denial). The error message must tell the user "open browser settings to allow mic access" — already in the recommended `msgs['not-allowed']` copy.

5. **TypeScript strict mode on `webkitSpeechRecognition`**
   - `@types/dom-speech-recognition` covers the standard `SpeechRecognition` constructor. The webkit prefix needs a one-line `as` cast — already shown in the skeleton above.
   - **Confidence:** HIGH — pattern is widely used in TypeScript projects.

6. **iOS Safari user-gesture requirement**
   - iOS Safari requires `recognition.start()` to be called inside a user-gesture handler (button click is fine). Our `onClick={toggleRecording}` already satisfies this.
   - **Risk:** none — the existing UI pattern is correct.

7. **`/voice/transcribe` HTTP endpoint after this phase**
   - Zero callers in the frontend after this phase. The endpoint stays on disk (zero-cost, mirrors Phase 83's smart-upload disposition) — defer cleanup to a follow-up phase to keep this PR's diff focused.

8. **`isTranscribing` legacy field**
   - The new hook returns `isTranscribing: false` always. ChatInterface.tsx has 6 references to `isSpeechTranscribing` — all become dead branches but cause no harm. Keep them on the existing edit; mass-cleanup is out of scope for HOTFIX hygiene.

## Implementation Notes

### Ordering hints

1. **Plan task A — type install + hook rewrite + hook unit test (single PR-sized task)**
   - Install `@types/dom-speech-recognition`
   - Rewrite `useSpeechRecognition.ts`
   - Author `useSpeechRecognition.test.ts` with a mocked `SpeechRecognition` constructor
   - Verify: `npx vitest run __tests__/hooks/useSpeechRecognition.test.ts` GREEN
   - Verify: existing `ChatInterface.test.tsx` GREEN (no behavior tests changed yet)
   - Verify: Phase 84 `useVoiceSession.test.ts` GREEN (boundary smoke)

2. **Plan task B — ChatInterface integration + behavior tests**
   - Edit textarea readOnly/onChange/disabled gates
   - Replace transcriptVersion effect with suffix-ref pattern
   - Loosen Enter and Send-button gates
   - Simplify Recording-indicator copy
   - Add 5 SC1-SC5 component tests
   - Verify: full `frontend && npm test` GREEN

3. **Plan task C — manual UAT scaffold**
   - Create `87-MANUAL-UAT.md` with the 6 browser matrix above
   - Smoke against `make local-backend` + `cd frontend && npm run dev`
   - Sign off SC1-SC5 by hand

### Gotchas

- **vi.mock hoisting:** the chatHarness `vi.mock('@/hooks/useSpeechRecognition', ...)` is already in place. Per-test override: `vi.mocked(useSpeechRecognition).mockReturnValueOnce({...})` after `renderChatInterface` returns. Pattern proven by Phase 88-04 sonner mock.
- **jsdom does not have `SpeechRecognition`:** the unit test must inject a fake constructor onto `window.SpeechRecognition` BEFORE the hook is imported (use a `beforeEach` block). The hook reads the constructor at module load — restructure to read inside `startRecording` if module-load capture causes test ordering issues.
- **Cleanup:** the `useEffect` cleanup must `abort()` (not `stop()`) the recognition — `stop()` would fire `onend` with potentially-finalized interim, causing a phantom `transcriptVersion` bump after unmount. `abort()` is silent.
- **Don't forget `'use client'` directive** at the top of the new hook — it's `useState` + browser API, must be a Client Component module.
- **The textarea's `readOnly` removal is the single biggest UX win** — without it, SC3 is structurally impossible no matter how clean the hook is. Don't skip it.
- **Phase 88 just landed in this same file.** Confirm no merge conflicts with the TabStrip work (lines ~150-200 for tab state, lines ~1140 for tab strip render). The mic edits are at lines 30, 338-365, 1078, 1502-1535, 1599-1620, 1702-1726 — disjoint from Phase 88's changes.

## Sources

### Primary (HIGH confidence)
- `frontend/src/hooks/useSpeechRecognition.ts:1-372` — current implementation (read in full)
- `frontend/src/components/chat/ChatInterface.tsx:30,338-365,1078,1502-1535,1599-1620,1702-1726` — all chat-mic call sites
- `frontend/src/hooks/useVoiceSession.ts:1-80` — brain-dump boundary (verified independent)
- `frontend/src/components/chat/__test-utils__/chatHarness.ts:65-67,147,334-348,494-496` — chatHarness mock contract
- `app/routers/voice_session.py:745-783` — backend `/voice/transcribe` endpoint definition
- `frontend/package.json` — Next.js 16 / React 19.2.3 / vitest 4.0.18 / TS 5.9.3
- `frontend/vitest.config.mts` — jsdom + globals + `@` alias
- `.planning/phases/87-mic-dictation-via-web-speech-api/` (empty — no prior work)

### Secondary (MEDIUM confidence — Web Speech API spec)
- W3C Web Speech API Editor's Draft (the spec for `SpeechRecognition`, `SpeechRecognitionEvent`, `SpeechRecognitionErrorEvent`)
- MDN Web Docs: `SpeechRecognition`, `SpeechRecognition.continuous`, `SpeechRecognition.interimResults`, `SpeechRecognition.onresult`, `SpeechRecognition.onerror`
- caniuse.com: `SpeechRecognition` — Chrome 33+, Edge 79+, Safari 14.1+ (with prefix), Firefox no support, iOS Safari 14.5+

### Tertiary
- Memory `project_voice_brain_dump_architecture.md` — confirms brain-dump architecture and the SC5 boundary
- `.planning/STATE.md` — confirms phases 83-86 complete, no overlapping work

## Metadata

**Confidence breakdown:**
- Current implementation: HIGH — all 6 call sites read directly from source
- Web Speech API behavior: HIGH — well-specified, widely deployed, MDN/W3C-aligned
- Brain-dump boundary: HIGH — grep-verified zero cross-imports between the two hooks
- Test approach: HIGH — chatHarness already supports the override pattern
- TypeScript typings: HIGH — `@types/dom-speech-recognition` is a known good package

**Research date:** 2026-04-30
**Valid until:** 30 days (Web Speech API is stable; project state may shift if Phases 88/89 land changes to ChatInterface.tsx mic region — re-check at plan time)
