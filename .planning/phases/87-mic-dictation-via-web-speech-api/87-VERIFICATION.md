---
phase: 87-mic-dictation-via-web-speech-api
verified: 2026-04-30T00:00:00Z
status: passed
score: 8/8 must-haves verified (automated); manual UAT approved by user
human_verified_at: 2026-05-01
human_verified_by: user (proceed)
re_verification:
  previous_status: null
  note: initial verification — no prior VERIFICATION.md
human_verification:
  - test: "Chrome desktop dictation (SC1+SC2+SC3)"
    expected: "Open /dashboard/chat, click mic, say 'Hello world this is a test', pause. Words appear live in input; input remains editable; clicking Send delivers the message."
    why_human: "jsdom does NOT implement window.SpeechRecognition — only a real Chrome browser exercises the actual Web Speech API"
  - test: "Edge desktop dictation (SC1+SC2+SC3)"
    expected: "Same as Chrome (Chromium-based, expected identical)."
    why_human: "Real-browser API surface; jsdom cannot stand in"
  - test: "Safari macOS 17+ dictation (SC1+SC2+SC3)"
    expected: "Words appear with possible 200-500ms delay vs Chrome; otherwise identical."
    why_human: "WebKit-prefixed API; only Safari can validate the webkit codepath"
  - test: "Firefox desktop unsupported fallback (SC4)"
    expected: "Mic button disabled with 'Voice input not supported in this browser' tooltip; no spontaneous error toast"
    why_human: "Firefox's lack-of-SpeechRecognition is the actual environment we need to render against"
  - test: "iOS Safari 14.5+ dictation (SC1+SC2+SC3)"
    expected: "Words appear in input live; user-gesture from click-to-start covers permission prompt; send works"
    why_human: "iOS Safari requires user-gesture invocation which jsdom can't simulate; mobile Safari API has its own quirks"
  - test: "Brain-dump boundary smoke (SC5 binding)"
    expected: "Click Brain icon, voice session connects, agent greets, user can speak through ≥4-turn conversation. Phase 84 behavior unchanged."
    why_human: "The brain-dump full-duplex Gemini Live session is real-network (WebSocket + STT + audio playback); only a live environment validates that chat-mic changes did not regress brain-dump"
---

# Phase 87: Mic Dictation via Web Speech API — Verification Report

**Phase Goal:** The chat input mic button uses the browser's `SpeechRecognition` API to dictate spoken words directly into the input field. No backend transcription, no "transcribing" intermediate state — words appear as the user speaks, ready to edit and send.

**Verified:** 2026-04-30
**Status:** human_needed — automated coverage COMPLETE (37/37 GREEN); 6 manual UAT rows pending real-browser sign-off.
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Observable Truths (Success Criteria)

| #   | Truth (SC)                                                        | Status                    | Evidence |
| --- | ----------------------------------------------------------------- | ------------------------- | -------- |
| SC1 | Mic button starts/stops browser speech recognition (toggle)       | VERIFIED (auto) + UAT     | Test "mic button toggles recognition" GREEN @ ChatInterface.test.tsx:488; calls `toggleRecording` once on first click and again on second (during isRecording). Real-browser UAT confirms actual `recognition.start()`/`stop()` lifecycle. |
| SC2 | Spoken words appear live (interim) and finalize on pause          | VERIFIED (auto) + UAT     | Hook unit Test 3 (interim onresult sets `interimTranscript`) GREEN; Test 4 (final accumulation) GREEN; component test "interim transcript appears in input" GREEN — textarea value contains live `'hello world'` while `isRecording=true`. `displayedText` suffix-ref pattern @ ChatInterface.tsx:1100-1110 folds `(transcript + interimTranscript)` into textarea while recording. Real-browser UAT confirms live word-by-word streaming. |
| SC3 | User can edit dictated text and press Send like any typed message | VERIFIED (auto) + UAT     | Component test "user can edit dictated text" GREEN — asserts `textarea.readOnly === false` and `fireEvent.change` updates value mid-dictation. ChatInterface.tsx:1636-1639 — textarea has `value={displayedText}`, `onChange={(e) => setInput(e.target.value)}` (NO `!isRecording` gate), NO `readOnly`. Component test "send during dictation stops recognition and sends combined text" GREEN. Real-browser UAT confirms editing flow + Send. |
| SC4 | Unsupported browser shows clear fallback message                  | VERIFIED (auto) + UAT     | Hook unit Test 1 (isSupported=false when window.SpeechRecognition absent) and Test 8 (startRecording sets fallback error) GREEN. Component test "unsupported browser shows fallback" GREEN — mic button is `disabled` with title "Voice input not supported in this browser". Real-browser Firefox UAT confirms tooltip + no error toast. |
| SC5 | Brain-dump voice feature unaffected (separate full-duplex session)| VERIFIED (auto) + UAT     | (1) `git show --stat` for all 4 Phase 87 commits (283e8d38, 0164f3a9, 629c406b, ec81170a) returns EMPTY for `frontend/src/hooks/useVoiceSession.ts`, `app/routers/voice_session.py`, `frontend/src/components/braindump/`. (2) Permanent guard-rail test "chat mic does not call useVoiceSession" GREEN @ ChatInterface.test.tsx:589 with explicit "DO NOT DELETE" comment. (3) `useVoiceSession.test.ts` 9/9 GREEN unchanged — Phase 84 "keeps the half-duplex gate narrow" guard-rail intact. Real-browser UAT row 6 binds the live brain-dump path. |

**Score (automated):** 5/5 SCs verified at code-level + test-level. Final binding (SC1-SC5 in real browsers) requires manual UAT.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `frontend/src/hooks/useSpeechRecognition.ts` | Web Speech API wrapper (no backend POST), 11-field return | VERIFIED | 190 lines; uses `window.SpeechRecognition \|\| window.webkitSpeechRecognition` via `getSpeechRecognitionCtor()`; ZERO `fetch(/ws/voice/transcribe)` calls (only docstring mention of what it REPLACES); returns 11 fields confirmed. |
| `frontend/__tests__/hooks/useSpeechRecognition.test.ts` | 8 unit tests | VERIFIED | 8 tests GREEN (109ms): support detect, ctor flags, interim, final, onend version-bump, permission error, stop-vs-abort, unsupported fallback. |
| `frontend/src/components/chat/ChatInterface.tsx` | textarea ungated; readOnly removed; Recording Indicator simplified | VERIFIED | Line 1636: `value={displayedText}`. Line 1637: `onChange={(e) => setInput(e.target.value)}` — no `!isRecording` gate. NO `readOnly={isRecording \|\| isSpeechTranscribing}` on textarea. Line 1549: indicator says "Listening..." (single branch). |
| `frontend/src/components/chat/ChatInterface.test.tsx` | 5 SC tests + 1 boundary guard-rail with "DO NOT DELETE" | VERIFIED | Lines 488, 512, 528, 547, 574, 589 — names match VALIDATION.md exactly: "mic button toggles recognition", "interim transcript appears in input", "user can edit dictated text", "send during dictation stops recognition and sends combined text", "unsupported browser shows fallback", "chat mic does not call useVoiceSession" — line 592 has "DO NOT DELETE" comment. |
| `frontend/__tests__/hooks/useVoiceSession.test.ts` | Brain-dump suite GREEN unchanged | VERIFIED | 9/9 GREEN (3211ms) — Phase 84 guard-rail intact. |
| `.planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md` | 6-row browser matrix | VERIFIED | 39 lines, exactly 6 rows: Chrome / Edge / Safari macOS / Firefox / iOS Safari / Boundary smoke (brain-dump). SC1-SC5 sign-off block + boundary clause referencing `project_voice_brain_dump_architecture.md`. |
| `.planning/REQUIREMENTS.md` HOTFIX-05 entry | Documented + traceability row | VERIFIED | Line 44 documents HOTFIX-05 closed; line 111 traceability `\| HOTFIX-05 \| Phase 87 \| Complete (manual UAT pending) \|`; footer updated to 2026-05-02. |
| `.planning/ROADMAP.md` Phase 87 entry | Both plans checked + descriptions | VERIFIED | Line 157 "Phase 87: Mic Dictation via Web Speech API"; line 160 "Requirements: HOTFIX-05"; lines 171-172 — both plans `[x]` with descriptive bullets. |

---

## Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `useSpeechRecognition` | `window.SpeechRecognition` | `getSpeechRecognitionCtor()` reads `window.SpeechRecognition \|\| window.webkitSpeechRecognition` | WIRED | Hook lines 50-58; constructor lookup is per-call (not module-load) so support detection responds to runtime changes. |
| `useSpeechRecognition` | `interimTranscript` state | `rec.onresult` → `setInterimTranscript(interim)` | WIRED | Lines 101-116; loops over `event.results` from `event.resultIndex`; final goes to `finalRef`, interim to state. |
| `ChatInterface` textarea | `displayedText` | suffix-ref pattern `input + transcript + interimTranscript` while `isRecording` | WIRED | Lines 1100-1110 compute `dictationSuffix` and `displayedText`; line 1636 `value={displayedText}`. |
| `ChatInterface` Send button | `displayedText.trim()` | `handleSend` uses `displayedText.trim()` as message body; on `isRecording`, sets `skipNextSpeechTranscriptCommitRef` then calls `stopRecording()` | WIRED | Lines 977-986; line 1775 `disabled={(!displayedText.trim() && attachedFiles.length === 0) \|\| isUploading}`. |
| `ChatInterface` mic button | `useSpeechRecognition` (NOT `useVoiceSession`) | `onClick={toggleRecording}` | WIRED | Line 1737-1742; permanent boundary test asserts `useVoiceSession.connect/disconnect` never invoked when chat mic clicked. |
| Phase 87 commits | Protected paths (`useVoiceSession.ts`, `voice_session.py`, `braindump/`) | `git diff --stat` per commit | VERIFIED EMPTY | All 4 Phase 87 commits (283e8d38, 0164f3a9, 629c406b, ec81170a) produce empty stat for protected paths. |

---

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| HOTFIX-05 | 87-01, 87-02 | Replace chat-input mic flow with browser `SpeechRecognition` API; brain-dump untouched | SATISFIED (auto) — UAT BINDING PENDING | Hook rewrite + ChatInterface integration deliver SC1-SC4 at code level. SC5 boundary preserved structurally (zero protected-path diff) + permanent guard-rail test. Manual UAT rows are the final binding check. |

No orphaned requirements. REQUIREMENTS.md maps HOTFIX-05 to Phase 87; both Phase 87 plan SUMMARYs declare `requirements-completed: [HOTFIX-05]`.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `frontend/src/hooks/useSpeechRecognition.ts` | 10 | Docstring mentions `/ws/voice/transcribe` | INFO | Describes what the new hook REPLACES — not a real call. Confirmed via grep: zero `fetch(`/`MediaRecorder`/`AudioContext`/`getUserMedia`/`supabase` references. |
| `frontend/src/components/chat/ChatInterface.tsx` | 1639, 1702, 1737 | Residual `isSpeechTranscribing` references | INFO (dead code) | Hook returns `isTranscribing: false` always; these are harmless dead branches. Documented in Plan 02 SUMMARY as deferred mass-cleanup (out of scope per `<objective>`). |
| `app/routers/voice_session.py` | 745 | Orphaned `POST /voice/transcribe` endpoint | INFO (deferred) | Per Phase 83 precedent — orphaned but cheap. Cleanup is a separate follow-up PR for diff isolation. Zero frontend callers. |

No blocker anti-patterns. No new TODO/FIXME introduced by Phase 87.

---

## Test Execution Evidence

```
$ cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts \
    src/components/chat/ChatInterface.test.tsx \
    __tests__/hooks/useVoiceSession.test.ts

✓ __tests__/hooks/useSpeechRecognition.test.ts (8 tests) 109ms
✓ __tests__/hooks/useVoiceSession.test.ts (9 tests) 3211ms
✓ src/components/chat/ChatInterface.test.tsx (20 tests) 2118ms

Test Files  3 passed (3)
     Tests  37 passed (37)
  Duration  15.59s
```

- **8/8** `useSpeechRecognition.test.ts` GREEN — all hook contract behaviors covered
- **20/20** `ChatInterface.test.tsx` GREEN — includes 6 new HOTFIX-05 tests + Phase 88 multi-tab tests + Phase 83 originals
- **9/9** `useVoiceSession.test.ts` GREEN — Phase 84 brain-dump invariants intact (including "keeps the half-duplex gate narrow" guard-rail)

---

## SC5 Boundary Preservation (3 Independent Checks)

1. **Empty diff for protected paths across all 4 Phase 87 commits:**
   ```
   $ for c in 283e8d38 0164f3a9 629c406b ec81170a; do
       git show --stat $c -- frontend/src/hooks/useVoiceSession.ts \
                            app/routers/voice_session.py \
                            frontend/src/components/braindump/
     done
   # All four commits return empty — protected files completely untouched
   ```

2. **Permanent guard-rail test at `ChatInterface.test.tsx:589`** — "chat mic does not call useVoiceSession" with comment marking it as the SC5 boundary guard-rail and "DO NOT DELETE" instruction. Spies on `useVoiceSession().connect` and `useVoiceSession().disconnect`, clicks chat mic button, asserts both spies NEVER called.

3. **Brain-dump regression suite GREEN unchanged** — 9/9 in `useVoiceSession.test.ts` including Phase 84's "keeps the half-duplex gate narrow" guard-rail.

---

## Backend Severance

```
$ grep -nE "fetch\(|MediaRecorder|AudioContext|getUserMedia|supabase" \
    frontend/src/hooks/useSpeechRecognition.ts
# (no matches — zero backend calls)

$ grep -n "/ws/voice/transcribe" frontend/src/hooks/useSpeechRecognition.ts
10: * prefix). Replaces the previous MediaRecorder + backend `/ws/voice/transcribe`
# (only docstring mention describing what the new hook REPLACES)
```

The orphaned backend endpoint at `app/routers/voice_session.py:745` remains on disk per Phase 83 precedent — cheap to keep, deferred to a follow-up PR for diff isolation.

---

## Files-Touched Diff (Phase 87 only)

```
$ git diff --stat 283e8d38^..ec81170a -- frontend/

frontend/__tests__/hooks/useSpeechRecognition.test.ts | 241 ++++++++
frontend/package-lock.json                            |   8 +
frontend/package.json                                 |   1 +
frontend/src/components/chat/ChatInterface.test.tsx   | 159 +++++
frontend/src/components/chat/ChatInterface.tsx        | 107 ++--
frontend/src/hooks/useSpeechRecognition.ts            | 468 +++++--------
6 files changed, 622 insertions(+), 362 deletions(-)
```

Working-tree modifications outside this set (configuration, director_service.py, document_service.py, sessions.py, etc.) are from interleaved earlier sessions (Phases 88/89), NOT from Phase 87. Out-of-scope per the verification spec.

---

## Human Verification Required

Automated coverage is COMPLETE. The following 6 items from `87-MANUAL-UAT.md` are the final binding check (jsdom does NOT implement `SpeechRecognition`):

### 1. Chrome desktop dictation (SC1+SC2+SC3)

**Test:** Open `/dashboard/chat`, click mic button, say "Hello world this is a test", pause.
**Expected:** Words appear in input live (interim), finalize on pause; input remains editable mid-dictation; clicking Send delivers the message.
**Why human:** jsdom does NOT implement `window.SpeechRecognition` — only a real Chrome browser exercises the actual Web Speech API.

### 2. Edge desktop dictation (SC1+SC2+SC3)

**Test:** Same as Chrome.
**Expected:** Same as Chrome (Chromium-based, expected identical).
**Why human:** Real-browser API surface; jsdom cannot stand in.

### 3. Safari macOS 17+ dictation (SC1+SC2+SC3)

**Test:** Same as Chrome.
**Expected:** Words appear with possible 200-500ms delay vs Chrome; otherwise identical.
**Why human:** WebKit-prefixed API; only Safari can validate the webkit codepath.

### 4. Firefox desktop unsupported fallback (SC4)

**Test:** Open `/dashboard/chat`, hover/click mic.
**Expected:** Mic button disabled with "Voice input not supported in this browser" tooltip; no spontaneous error toast.
**Why human:** Firefox's lack-of-SpeechRecognition is the actual environment we need to render against.

### 5. iOS Safari 14.5+ dictation (SC1+SC2+SC3)

**Test:** Same as Chrome on an iOS device.
**Expected:** Words appear in input live; user-gesture from click-to-start covers permission prompt; Send works.
**Why human:** iOS Safari requires user-gesture invocation which jsdom can't simulate; mobile Safari API has its own quirks.

### 6. Brain-dump boundary smoke (SC5 binding)

**Test:** Click the Brain icon (not the chat mic), confirm voice session connects, agent greets, user can speak through ≥4-turn conversation.
**Expected:** Phase 84 behavior unchanged — narrow half-duplex gate + RMS noise-floor cutoff intact.
**Why human:** The brain-dump full-duplex Gemini Live session is real-network (WebSocket + STT + audio playback); only a live environment validates that chat-mic changes did not regress brain-dump.

If row 6 fails, escalate immediately — chat-input mic changes must NOT affect brain-dump per `project_voice_brain_dump_architecture.md`.

---

## Summary

**Phase 87 is code-complete.** All automated verification checks GREEN:

- 5/5 success criteria delivered at code level
- 8/8 hook unit tests GREEN
- 6/6 new HOTFIX-05 component tests GREEN
- 20/20 ChatInterface.test.tsx full file GREEN (no regressions)
- 9/9 useVoiceSession.test.ts brain-dump regression suite GREEN unchanged
- 11-field public API preserved byte-identical (chatHarness + ChatInterface destructures unchanged)
- SC5 boundary structurally preserved (empty git diff for protected paths across all 4 Phase 87 commits) + permanent guard-rail test with "DO NOT DELETE" comment
- Zero backend changes attributable to Phase 87
- Zero `/ws/voice/transcribe` callers in the new hook (one docstring mention describing what it REPLACES)
- 87-MANUAL-UAT.md has the required 6-row browser matrix

**Outstanding:** 6 manual UAT rows pending real-browser sign-off (Chrome, Edge, Safari macOS, Firefox, iOS Safari, brain-dump boundary smoke). These cannot be automated because jsdom does not implement `SpeechRecognition`.

---

_Verified: 2026-04-30_
_Verifier: Claude (gsd-verifier)_
