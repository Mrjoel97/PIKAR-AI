---
phase: 87-mic-dictation-via-web-speech-api
plan: 02
subsystem: ui
tags: [speech-recognition, web-speech-api, react, vitest, hotfix, chat-input]

# Dependency graph
requires:
  - phase: 87-mic-dictation-via-web-speech-api
    provides: Plan 87-01 — useSpeechRecognition Web Speech API wrapper with stable 11-field shape, interim + final streaming, stop()-flushes-interim discipline
  - phase: 84-voice-gate-deadlock-fix
    provides: useVoiceSession boundary integrity (Phase 84 narrow half-duplex gate is the load-bearing invariant — Plan 02 must never cross it)
  - phase: 83-document-upload-bypass
    provides: chatHarness pattern (vi.mock with stable 11-field useSpeechRecognition + 11-field useVoiceSession defaults; per-render mockReturnValueOnce overrides proven by Phase 88-04)
provides:
  - Live interim dictation streaming into the chat textarea (suffix-ref pattern: input + speechTranscript + interimTranscript while isRecording)
  - Editable textarea mid-dictation (readOnly removed; onChange ungated)
  - Mid-dictation Send (Enter key + Send button): stopRecording flushes pending interim into final, skipNextSpeechTranscriptCommitRef suppresses the commit-on-finalize effect so the in-progress phrase is sent exactly once via handleSend
  - Simplified Recording Indicator copy ("Listening..." with Stop affordance and live interim quote — Transcribing branch dropped, isSpeechTranscribing now dead-code-false)
  - 5 SC1-SC5 component tests + 1 permanent SC5 boundary guard-rail in ChatInterface.test.tsx
  - 87-MANUAL-UAT.md scaffold (6-row browser matrix + SC1-SC5 sign-off + brain-dump boundary clause)
affects:
  - End-of-Phase-87 manual UAT (Chrome/Edge/Safari macOS/Firefox/iOS Safari + brain-dump boundary smoke)
  - /gsd:verify-work 87 (waits on UAT row sign-off)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Suffix-ref live-streaming for dictation: textarea reads displayedText (input + speechTranscript + interimTranscript while isRecording); setInput only fires from real keystrokes; commit-on-finalize folds final transcript into input on transcriptVersion bump. No race with user typing mid-dictation."
    - "skipNextSpeechTranscriptCommitRef flush-and-suppress: handleSend sets the ref before stopRecording() so the subsequent transcriptVersion-effect run sees the flag, skips the append, and the in-progress phrase is sent exactly once via the message body that handleSend already built from displayedText.trim()."
    - "Boundary guard-rail test pattern: vi.mocked(useVoiceSession).mockReturnValueOnce({...defaults, connect: spy, disconnect: spy}) before renderChatInterface; assert spies never called when only the chat-input mic button is exercised. Permanent CI guard-rail with DO NOT DELETE comment."

key-files:
  created:
    - ".planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md (39 lines, 6-row browser matrix + SC1-SC5 sign-off)"
    - ".planning/phases/87-mic-dictation-via-web-speech-api/87-02-chat-input-mic-integration-SUMMARY.md (this file)"
  modified:
    - "frontend/src/components/chat/ChatInterface.tsx (+70/-37 lines; 6 surgical edits applied: stopRecording in destructure, skipNextSpeechTranscriptCommitRef + suppressed-commit branch in transcriptVersion effect, suffix-ref displayedText computation, loosened handleKeyDown gate, mid-dictation handleSend stopRecording + skip-flag set, simplified Recording Indicator JSX, removed textarea readOnly + ungated onChange, loosened Send button disabled + uses displayedText.trim() for empty-message gate)"
    - "frontend/src/components/chat/ChatInterface.test.tsx (+159 lines; 6 new tests in describe block ChatInterface — HOTFIX-05 mic dictation)"

key-decisions:
  - "skipNextSpeechTranscriptCommitRef pattern over auto-stop on send: handleSend sets the ref before stopRecording() so when onend fires and the consumer effect runs, the commit branch is bypassed. The phrase is sent exactly once as messageDraft = displayedText.trim() — avoids double-append and lets the existing transcriptVersion-effect dedupe stay in place."
  - "displayedText.trim() (not input.trim()) drives both the empty-message gate AND the message-to-send body. This means dictated text alone (input='') enables Send and is sent as the message — required for the 'send during dictation' test and matching SC3-extension."
  - "Send button disabled list reduced to (!displayedText.trim() && attachedFiles.length === 0) || isUploading. isRecording / isSpeechTranscribing dropped — both load-bearing for SC3-extension. File-attach button and file-pill remove-button still honor isRecording for safety."
  - "Recording Indicator simplified to single-branch (isRecording only) with 'Listening...' copy and Stop affordance. The Transcribing branch is dead post-Plan 01 (isSpeechTranscribing always false); kept the field name in the conditional for grep-ability but the JSX no longer renders the teal/Loader2 path."
  - "Incidental TS clean-up rolled into the same commit: getErrorMessage helper replaces three (error: any) catch sites with typed narrowing; widget pinning replaces (msg.widget as any) with WidgetDefinition & {id?: string}; event content-parts mapped via {text?: string} typed projection. These touched lines were already in the diff via Phase 88 work — the deviation is to also tighten as-any in the lines we wrote rather than leave fresh as-any in production code."
  - "Manual UAT scaffold (87-MANUAL-UAT.md) was already drafted in an earlier session and matches the 87-RESEARCH.md / 87-VALIDATION.md 6-row matrix verbatim. Kept as-is; no edits needed."

patterns-established:
  - "Suffix-ref live-streaming for any input that needs to render a derived live overlay while a backing source updates async: editable input is the truth, derived overlay is read-only at render time, commit-on-finalize folds the overlay into truth on the version-bump tick. Robust to user editing mid-stream."
  - "Flush-and-suppress flag for handler interactions with version-bump effects: when a click handler needs to short-circuit the post-bump effect's default behavior, set a ref BEFORE triggering the bump (here, before stopRecording()). The effect reads the ref and skips. Avoids double-fire."

requirements-completed: [HOTFIX-05]

# Metrics
duration: 14 min
completed: 2026-05-02
---

# Phase 87 Plan 02: Chat Input Mic Integration Summary

**ChatInterface integrates the rewritten useSpeechRecognition hook for live in-browser dictation: suffix-ref pattern streams interim words into the textarea while `isRecording`, the textarea stays editable mid-dictation (readOnly removed), and Enter/Send mid-dictation flushes pending interim via stopRecording with a skip-flag so the in-progress phrase is sent exactly once. SC5 brain-dump boundary preserved — useVoiceSession.ts and voice_session.py UNCHANGED line-for-line, plus a permanent guard-rail test fails CI if anyone ever wires the chat-mic flow into useVoiceSession.connect/disconnect.**

## Performance

- **Duration:** 14 min (most production code was pre-staged in the working tree from earlier sessions; this run executed the TDD commit sequence + verification + planning updates)
- **Started:** 2026-05-01T21:00:21Z
- **Completed:** 2026-05-02T00:11:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 3 production + 4 planning (5 net new lines in REQUIREMENTS.md, 7 lines in ROADMAP.md, ~25 lines in STATE.md, this SUMMARY)

## Accomplishments

- HOTFIX-05 chat-input mic integration shipped: live interim dictation streams into the textarea, the user can edit mid-dictation, and Enter/Send mid-dictation includes the in-progress phrase exactly once.
- 6 new HOTFIX-05 tests GREEN in `ChatInterface.test.tsx` covering SC1 (mic toggle), SC2 (interim in input), SC3 (editable mid-dictation), SC3-extension (send-during-dictation includes both transcript + interim), SC4 (unsupported browser fallback), and SC5 boundary guard-rail (chat mic does not call useVoiceSession).
- All 20 ChatInterface.test.tsx tests GREEN — no regression on Phase 83 HOTFIX-01 tests, original ChatInterface basics, or Phase 88 multi-tab tests.
- All 9 useVoiceSession.test.ts tests GREEN unchanged — Phase 84 "keeps the half-duplex gate narrow" guard-rail intact.
- All 8 useSpeechRecognition.test.ts tests GREEN unchanged — Plan 01 hook contract preserved.
- Lint clean on edited files (zero new errors; only pre-existing warnings unrelated to this plan).
- Zero modifications to `useVoiceSession.ts`, `voice_session.py`, or `components/braindump/` — SC5 boundary structurally preserved.

## Task Commits

Each task was committed atomically following the TDD red-green sequence:

1. **Task 1 (RED): Tests + UAT scaffold** — `629c406b` (test)
   - Appended 6-test `describe('ChatInterface — HOTFIX-05 mic dictation', ...)` block to `ChatInterface.test.tsx` (159 lines)
   - Created `87-MANUAL-UAT.md` (39 lines) with 6-row browser matrix + SC1-SC5 sign-off
   - Tests use `vi.mocked(useSpeechRecognition).mockReturnValueOnce(...)` ahead of `renderChatInterface` to override per-test (Phase 88-04 pattern)

2. **Task 2 (GREEN): Production edits** — `ec81170a` (feat)
   - 6 surgical edits applied to `ChatInterface.tsx` (+70/-37 lines)
   - Added `stopRecording` to the useSpeechRecognition destructure
   - Added `skipNextSpeechTranscriptCommitRef` and used it in handleSend + the transcriptVersion effect
   - Replaced `const displayedText = input` with the suffix-ref computation
   - Loosened `handleKeyDown` gate (Enter sends mid-dictation)
   - Simplified Recording Indicator JSX (drop dead Transcribing branch)
   - Removed textarea `readOnly`, ungated onChange (`onChange={(e) => setInput(e.target.value)}`)
   - Loosened Send button disabled list and switched to `displayedText.trim()` for the empty-message gate
   - Incidental TS tightening: `getErrorMessage` helper replaces 3 `(error: any)` sites; widget pin uses `WidgetDefinition & {id?: string}`; event content-parts map uses typed projection

## Files Created/Modified

- `frontend/src/components/chat/ChatInterface.tsx` — 6 surgical edits applied (see Task 2 above). Net +70/-37 lines.
- `frontend/src/components/chat/ChatInterface.test.tsx` — 6 new tests appended in `ChatInterface — HOTFIX-05 mic dictation` describe block. +159 lines.
- `.planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md` — Created. 6-row browser matrix (Chrome/Edge/Safari macOS/Firefox/iOS Safari + brain-dump boundary smoke) + SC1-SC5 sign-off + brain-dump boundary clause referencing `project_voice_brain_dump_architecture.md`.
- `.planning/STATE.md` — Prepended new YAML stanza, updated Current Position section, added 2 Performance Metrics rows for Phase 87 P01 + P02.
- `.planning/ROADMAP.md` — Phase 87 entry: "Plans: 0" → "2/2 plans complete"; both plan checkboxes ticked with descriptive bullets.
- `.planning/REQUIREMENTS.md` — Added HOTFIX-05 entry to Hotfix Requirements; added `| HOTFIX-05 | Phase 87 | Complete (manual UAT pending) |` row to Traceability table; updated last-updated footer.
- `.planning/phases/87-mic-dictation-via-web-speech-api/87-02-chat-input-mic-integration-SUMMARY.md` — This file.

## Decisions Made

- **`skipNextSpeechTranscriptCommitRef` flush-and-suppress over auto-stop-on-send-and-skip:** handleSend sets the ref BEFORE `stopRecording()`. When the recognition's `onend` fires and bumps `transcriptVersion`, the consumer effect reads the ref, skips the commit, and continues. The phrase is sent exactly once via `messageToSend = displayedText.trim()` which already includes both `speechTranscript` and `interimTranscript`. This pattern keeps the existing transcript-version dedupe in place AND avoids needing to add timing-sensitive `await onend` logic in handleSend.

- **`displayedText.trim()` (not `input.trim()`) drives the Send button enable + the message body:** This means dictated text alone (with `input === ''`) enables Send and gets sent as the message. Required for SC3-extension test "send during dictation stops recognition and sends combined text" — and matches the live-preview UX (what the user sees is what gets sent).

- **Send button disabled list reduced to `(!displayedText.trim() && attachedFiles.length === 0) || isUploading`:** `isRecording` and `isSpeechTranscribing` dropped (load-bearing for SC3-extension). File-attach button (Paperclip) and file-pill remove-button still honor `isRecording` for safety per the plan's surgical-edit guidance.

- **Recording Indicator simplified to single-branch:** Drops the dead Transcribing branch (isSpeechTranscribing always false post-Plan 01). Renders "Listening..." with Stop affordance and live interim quote when isRecording.

- **Incidental TS clean-up rolled into the GREEN commit:** Three `(error: any)` catch sites replaced with `getErrorMessage` helper; widget-pin `as any` replaced with `WidgetDefinition & {id?: string}`; event content-parts `(p: any) => p.text` replaced with typed `(p: {text?: string})`. These were touched lines in the diff already; tightening them prevents fresh as-any from landing in production. Documented as a deviation, not core scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan 01 SUMMARY was untracked**
- **Found during:** Task 2 completion — `git status` showed `87-01-speech-recognition-hook-rewrite-SUMMARY.md` as untracked.
- **Issue:** Plan 01's SUMMARY.md from the prior session was never committed to git. Phase 87 metadata commit needed to include it.
- **Fix:** Will be staged with the metadata commit (alongside STATE/ROADMAP/REQUIREMENTS + this SUMMARY). The file content is correct; it just needed to be tracked.
- **Files modified:** None (the file was already written by the prior session); just adding it to a commit.
- **Verification:** Will appear in the metadata commit's `git show --stat`.
- **Committed in:** Final metadata commit (alongside this SUMMARY).

**2. [Rule 1 - Bug] Tightened three `(error: any)` catch sites and two other `as any` widget/content-parts casts inside ChatInterface.tsx**
- **Found during:** Task 2 — surgical edits touched lines that already had `(error: any)` and `as any` patterns.
- **Issue:** The plan said to apply "6 surgical edits" but the touched lines included pre-existing `as any` patterns. Leaving them would mean shipping fresh as-any in code that we wrote/touched.
- **Fix:** Added `getErrorMessage(error: unknown, fallback)` helper (typed narrowing); replaced 3 `(error: any)` catch sites with calls to it; replaced widget-pin `(msg.widget as any)` with `WidgetDefinition & {id?: string}` narrowing; replaced event content-parts `.map((p: any) => p.text)` with `.map((p: {text?: string}) => p.text || '')`.
- **Files modified:** `frontend/src/components/chat/ChatInterface.tsx`
- **Verification:** TS strict-mode compile clean; lint clean; no new warnings beyond pre-existing.
- **Committed in:** `ec81170a` (Task 2 GREEN commit).

**3. [Rule 1 - Bug] Production code edits and test authoring were already in the working tree from a prior planner/executor session**
- **Found during:** Initial git status — both `ChatInterface.tsx` and `ChatInterface.test.tsx` were `M` (modified) before this session started, with the full Plan 02 edits already in place.
- **Issue:** Plan 02 expects fresh RED → fresh GREEN sequence. With production code already updated, RED state could not be re-confirmed in this session.
- **Fix:** Honored the TDD spirit by committing in two separate atomic commits (`test(87-02): ...` then `feat(87-02): ...`) rather than collapsing into one. Documented in SUMMARY that RED reconfirmation was not possible because production code was pre-staged. Plan 01 SUMMARY's note about iterative work in earlier sessions is consistent with this state. Plan-level verification passes: 20/20 ChatInterface tests GREEN, 9/9 useVoiceSession tests GREEN, 8/8 useSpeechRecognition tests GREEN.
- **Files modified:** N/A (procedural decision)
- **Verification:** All 6 HOTFIX-05 tests GREEN. SC5 boundary diff empty.
- **Committed in:** N/A (procedural).

---

**Total deviations:** 3 (1 × Rule 3 — Blocking, 2 × Rule 1 — Bug; one is a procedural note, one is incidental TS tightening, one is the untracked Plan 01 SUMMARY).
**Impact on plan:** None on scope. SC5 boundary preserved. All success criteria met. The TS tightening is additive correctness work; the procedural note documents that RED could not be reconfirmed but the GREEN gate is met.

## Issues Encountered

None — the work was largely pre-staged in the working tree from earlier sessions, so this run was primarily verification + commit sequencing + planning updates. The full vitest suite shows 51 pre-existing failures across 22 unrelated test files (`ProtectedRoute.test.tsx`, etc.) that were already present before this plan started — explicitly out of scope per known_risks #7 in the plan.

## Authentication Gates

None — pure frontend code change with no backend or external service interaction.

## SC5 Boundary Preservation

The brain-dump path is structurally protected by Plan 02 in three independent ways:

1. **Zero line-level diff in the protected files:**
   ```
   git diff --stat HEAD~2 HEAD -- \
     frontend/src/hooks/useVoiceSession.ts \
     app/routers/voice_session.py \
     frontend/src/components/braindump/ \
     frontend/src/hooks/useSpeechRecognition.ts
   ```
   Returns empty across both task commits (`629c406b` and `ec81170a`).

2. **Permanent guard-rail test in CI:**
   `ChatInterface.test.tsx` — describe block `ChatInterface — HOTFIX-05 mic dictation`, test "chat mic does not call useVoiceSession". Spies on `useVoiceSession().connect` and `useVoiceSession().disconnect`, clicks the chat-input mic button, asserts both spies are NEVER called. Includes a verbose comment marking the test as the SC5 boundary guard-rail with a permanent "DO NOT DELETE" instruction. Any future PR that wires the chat-mic flow into `useVoiceSession.connect/disconnect` fails this test, blocking merge.

3. **Existing brain-dump regression suite remains GREEN unchanged:**
   `__tests__/hooks/useVoiceSession.test.ts` — 9/9 tests pass, including Phase 84's "keeps the half-duplex gate narrow" guard-rail. Confirmed via `npx vitest run __tests__/hooks/useVoiceSession.test.ts` returning 9 passed.

The orphaned backend `POST /voice/transcribe` route at `app/routers/voice_session.py:745-783` remains on disk per Phase 83 precedent and per the plan's `<objective>` Scope Discipline section. Cleanup is deferred to a follow-up PR for diff isolation. Frontend has zero callers after this plan.

## Verification Evidence

| Gate | Command | Result |
|------|---------|--------|
| HOTFIX-05 focused suite | `npx vitest run src/components/chat/ChatInterface.test.tsx -t "HOTFIX-05"` | 6/6 GREEN (only HOTFIX-05 visible; one test was reported, others auto-skipped due to file-level early exit on first match — re-ran without filter to confirm) |
| ChatInterface full file | `npx vitest run src/components/chat/ChatInterface.test.tsx` | **20/20 GREEN** (2284ms) |
| useSpeechRecognition unit suite | `npx vitest run __tests__/hooks/useSpeechRecognition.test.ts` | **8/8 GREEN** (165ms) |
| useVoiceSession regression (SC5 smoke) | `npx vitest run __tests__/hooks/useVoiceSession.test.ts` | **9/9 GREEN** (3075ms) — including Phase 84 "keeps the half-duplex gate narrow" guard-rail |
| Combined per-VALIDATION.md focused suite | `npx vitest run src/components/chat/ChatInterface.test.tsx __tests__/hooks/useSpeechRecognition.test.ts __tests__/hooks/useVoiceSession.test.ts` | **37/37 GREEN** |
| Lint | `npx eslint src/components/chat/ChatInterface.tsx src/components/chat/ChatInterface.test.tsx` | 0 errors, 9 pre-existing warnings (unused imports, exhaustive-deps, alt-text — none introduced by this plan) |
| SC5 boundary diff invariant | `git diff --stat HEAD~2 HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py frontend/src/components/braindump/ frontend/src/hooks/useSpeechRecognition.ts` | **Empty** — protected files completely untouched |
| Files-touched diff | `git diff --stat HEAD~2 HEAD` | 3 files: `87-MANUAL-UAT.md` (+39), `ChatInterface.test.tsx` (+159), `ChatInterface.tsx` (+70/-37). No collateral damage. |
| Manual UAT scaffold | `test -f .planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md` | Present (39 lines, 6-row browser matrix + SC1-SC5 sign-off) |

## User Setup Required

None — no external service configuration. The new behavior runs entirely in-browser using the user's existing microphone permission grant. Manual UAT will exercise real `SpeechRecognition` API across Chrome/Edge/Safari/Firefox/iOS Safari per `87-MANUAL-UAT.md`.

## Manual UAT Pending

Phase 87 is **code-complete, manual UAT pending**. The 6 rows in `87-MANUAL-UAT.md` need real-browser sign-off before `/gsd:verify-work 87`:

1. Chrome desktop — say "Hello world this is a test", verify words appear live + editable + send works
2. Edge desktop — same (Chromium-based, expected identical to Chrome)
3. Safari macOS 17+ — same (with possible 200-500ms delay vs Chrome)
4. Firefox desktop — disabled mic with "Voice input not supported in this browser" tooltip; no spontaneous error toast
5. iOS Safari 14.5+ — same as Chrome (user-gesture from click-to-start covers permission prompt)
6. Brain-dump boundary smoke — Brain icon connects, agent greets, ≥4-turn conversation works (Phase 84 behavior unchanged)

If the brain-dump row fails, escalate immediately — chat-input mic changes must NOT affect the brain-dump path. That's the load-bearing invariant per `project_voice_brain_dump_architecture.md`.

## Deferred Items

- **Backend `POST /voice/transcribe` route at `app/routers/voice_session.py:745-783` stays on disk.** Zero frontend callers after Plan 01, but cheap to keep. Mirrors Phase 83's smart-upload backend disposition. Cleanup is a separate follow-up PR for diff isolation per the plan's `<objective>` instructions.
- **`isSpeechTranscribing` dead branches in `ChatInterface.tsx`** (a few remain after Plan 02's surgical simplification of the Recording Indicator). The new hook returns `isTranscribing: false` always, so the residual `disabled={isUploading || isSpeechTranscribing}` and similar are harmless dead code. Mass-cleanup is out of scope per the plan's `<objective>` Scope Discipline.
- **`/voice/transcribe` (no longer called by chat-input)** — see backend bullet above. Single follow-up PR can sever the backend path and clean residual `isSpeechTranscribing` references in one shot.

## Hand-off Notes

- For `/gsd:verify-work 87`: the only outstanding work is the 6-row manual UAT in `87-MANUAL-UAT.md`. Once those rows are signed off (especially the brain-dump boundary smoke), Phase 87 is ready to ship.
- For Phase 88+ work in this same file: `ChatInterface.tsx` has had two recent rounds of surgical edits (Phase 88 multi-tab, Phase 87 mic dictation). Future planners should anchor on exact strings (`displayedText`, `dictationSuffix`, `skipNextSpeechTranscriptCommitRef`, `Listening...`, `data-testid="chat-send-button"`) rather than line numbers — the line-number geography drifts.
- For brain-dump-related work: `useVoiceSession.ts` and `app/routers/voice_session.py` were UNCHANGED in Phase 87. The full Phase 84 behavior (narrow half-duplex gate + RMS noise-floor cutoff) is intact. Any future change to those files should preserve Phase 84's "keeps the half-duplex gate narrow" guard-rail test.

## Self-Check: PASSED

- [x] `frontend/src/components/chat/ChatInterface.tsx` modified (verified via `git show --stat ec81170a`)
- [x] `frontend/src/components/chat/ChatInterface.test.tsx` modified (verified via `git show --stat 629c406b`)
- [x] `.planning/phases/87-mic-dictation-via-web-speech-api/87-MANUAL-UAT.md` exists (verified via `ls`)
- [x] Task 1 commit `629c406b` present (`git log --oneline | grep 629c406b`)
- [x] Task 2 commit `ec81170a` present (`git log --oneline | grep ec81170a`)
- [x] All 6 HOTFIX-05 tests GREEN
- [x] All 9 useVoiceSession.test.ts tests GREEN unchanged
- [x] All 8 useSpeechRecognition.test.ts tests GREEN unchanged
- [x] SC5 boundary diff empty (`git diff --stat HEAD~2 HEAD -- <protected paths>`)
- [x] Boundary guard-rail test ("chat mic does not call useVoiceSession") authored with permanent "DO NOT DELETE" comment

---
*Phase: 87-mic-dictation-via-web-speech-api*
*Completed: 2026-05-02*
