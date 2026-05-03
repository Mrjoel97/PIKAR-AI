---
phase: 84-voice-gate-deadlock-fix
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/useVoiceSession.ts
  - frontend/__tests__/hooks/useVoiceSession.test.ts
  - .planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md
autonomous: true
requirements:
  - HOTFIX-02

must_haves:
  truths:
    - "After the agent's intro greeting completes, the user can speak and the audio reaches the server (verified via input_transcription in production logs and a vitest spec asserting forwardInputChunk emits an 'audio' WebSocket frame for a 0.05-RMS chunk after onended fires)."
    - "Within ~1s of the user pausing for silence_duration_ms (700ms server-side), the model produces an audio response — because sub-noise-floor chunks (RMS < VOICE_NOISE_FLOOR_RMS, default 0.003) are dropped before float32ToPcm16 so server VAD finally observes clean silence."
    - "A full ≥4-turn conversation completes end-to-end with no stuck silence — verified by a vitest spec that loops agent-audio + onended + user-speech + turn_complete four times and asserts the gate opens/closes correctly each cycle."
    - "ARCHITECTURAL INVARIANT: the half-duplex gate at useVoiceSession.ts:886 remains exactly `if (isPlayingRef.current && !remoteTurnCompleteRef.current) return;`. The noise-floor cutoff is implemented as a SEPARATE filter immediately AFTER that gate and BEFORE float32ToPcm16 — NOT as a modification to gate conditions. SC4 (multi-condition gate adding playbackQueueRef.length / pendingTurnDelayRef / lastRemoteActivityAtRef tail) is EXPLICITLY REJECTED per 84-RESEARCH.md §Q5 and a guard-rail test in this plan asserts the gate stays narrow."
  artifacts:
    - path: "frontend/src/hooks/useVoiceSession.ts"
      provides: "Noise-floor RMS cutoff inside forwardInputChunk + VOICE_NOISE_FLOOR_RMS module-scope constant with NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS env override"
      contains: "VOICE_NOISE_FLOOR_RMS"
    - path: "frontend/__tests__/hooks/useVoiceSession.test.ts"
      provides: "Five new vitest specs covering SC1, SC2, SC3, mid-utterance regression, and SC4-rejection guard-rail"
      contains: "drops sub-noise-floor chunks"
    - path: ".planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md"
      provides: "Manual UAT checklist (quiet/noisy/mid-utterance/whisper) + production-log assertion pattern"
      contains: "4-turn conversation"
  key_links:
    - from: "frontend/src/hooks/useVoiceSession.ts forwardInputChunk"
      to: "the existing half-duplex gate at line 886 + the new RMS cutoff"
      via: "RMS check executes immediately after the gate (line 888) and before float32ToPcm16 (was line 889)"
      pattern: "rms < VOICE_NOISE_FLOOR_RMS"
    - from: "frontend/__tests__/hooks/useVoiceSession.test.ts"
      to: "MockWebSocket.send and MockAudioBufferSourceNode.onended"
      via: "Existing scaffolding — push Float32Array chunks of varying RMS through the captured onaudioprocess handler and assert ws.send call shape"
      pattern: "ws.send.*\\\"type\\\":\\\"audio\\\""
---

<objective>
Fix the brain-dump voice deadlock (HOTFIX-02) by adding a ~10-LOC noise-floor RMS cutoff inside `forwardInputChunk` so the Gemini Live server-side VAD observes `silence_duration_ms` of clean silence after the user pauses, allowing it to close the user's turn and trigger the model response.

Purpose: Phase 84-RESEARCH.md (HIGH confidence) traced the symptom "intro plays, user speech transcribes, agent never replies" to a server-side cause: continuous mic forwarding of ambient noise + AEC residue means Gemini Live's `automatic_activity_detection` (silence_duration_ms=700) never sees clean silence at user pauses, so `input_transcription` fires forever but `model_turn` never does. The smallest correct fix is a noise FLOOR (NOT local VAD, NOT a wider gate) that drops literal sub-speech ambient before transmission. SC4 in the roadmap proposes a multi-condition gate widening — research demonstrates this would NOT fix the bug (all four SC4 conditions evaluate FALSE during the user's pause) AND would re-introduce the mid-utterance suppression regression fixed by commit 86b0bc20 on 2026-04-29. SC4 is therefore EXPLICITLY REJECTED in this plan; SC1, SC2, and SC3 are the binding success criteria.

Output:
- Modified `frontend/src/hooks/useVoiceSession.ts` (~10 LOC added: 1 constant + 6-line RMS check + comment block)
- Extended `frontend/__tests__/hooks/useVoiceSession.test.ts` (5 new specs)
- New `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` (manual checklist)
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/84-voice-gate-deadlock-fix/84-RESEARCH.md
@.planning/phases/84-voice-gate-deadlock-fix/84-VALIDATION.md

@frontend/src/hooks/useVoiceSession.ts
@frontend/__tests__/hooks/useVoiceSession.test.ts

<sc4_rejection_summary>
**SC4 (multi-condition gate) is REJECTED.** Per `84-RESEARCH.md` §Q5, SC4 widens the gate at the agent→user boundary; the actual deadlock is at the user→agent boundary. At the failure point, all four SC4 conditions (`isPlayingRef`, `playbackQueueRef.length > 0`, `pendingTurnDelayRef`, `lastRemoteActivityAtRef` within tail window) evaluate FALSE — the gate is already open. SC4 verbatim would also re-introduce the mid-utterance re-latch bug fixed by commit 86b0bc20 (2026-04-29).

This plan implements the SAME fix for SC1+SC2+SC3 via a DIFFERENT mechanism: a noise-floor RMS cutoff (not a gate modification). Test 5 below is a guard-rail that fails if anyone widens the gate later. PR reviewers should read `84-RESEARCH.md` §Q5 + this block before requesting SC4 verbatim.
</sc4_rejection_summary>

<interfaces>
<!-- Existing contracts the executor will use directly. Extracted from useVoiceSession.ts and the test file. No codebase exploration needed beyond these. -->

From `frontend/src/hooks/useVoiceSession.ts` (line 79, module-scope constants block — add new constant immediately after this line):
```ts
const REMOTE_TURN_ACTIVITY_TAIL_MS = 650;
```

From `frontend/src/hooks/useVoiceSession.ts` (lines 843–897, `forwardInputChunk` definition — DO NOT alter the existing gate; insert the RMS check between line 888 `}` and line 889 `const pcm16 = ...`):
```ts
const forwardInputChunk = (inputData: Float32Array) => {
    if (ws.readyState !== WebSocket.OPEN) return;
    if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
    }
    // ... long comment block (lines 851–885) explaining the narrow gate ...
    if (isPlayingRef.current && !remoteTurnCompleteRef.current) {
        return;
    }
    // <-- INSERT RMS CHECK HERE (between the gate's closing brace and float32ToPcm16) -->
    const pcm16 = float32ToPcm16(inputData, ctx.sampleRate, MIC_SAMPLE_RATE);
    const uint8 = new Uint8Array(pcm16.buffer);
    let binary = '';
    for (let i = 0; i < uint8.length; i++) {
        binary += String.fromCharCode(uint8[i]);
    }
    const base64 = btoa(binary);
    ws.send(JSON.stringify({ type: 'audio', data: base64 }));
};
```

From `frontend/__tests__/hooks/useVoiceSession.test.ts` (existing scaffolding the new tests build on):
- `MockWebSocket` with `send: vi.fn()` and a manual `simulateMessage(data)` helper
- `MockAudioContext` with `createScriptProcessor`-style hookup; the harness captures the registered `onaudioprocess` callback so tests can synthesise Float32Array input chunks
- `MockAudioBufferSourceNode.autoFinish = true` causes `onended` to fire on the next microtask after `start()` — used to drive intro-playback completion
- `drainPlaybackQueue` exported from the hook for deterministic test sequencing
- Pattern for new tests: `renderHook(() => useVoiceSession(...))`, `await act(async () => { ... })`, capture `ws.send` calls, push Float32Arrays through the captured `onaudioprocess`, assert `ws.send` shape with `expect.objectContaining({ type: 'audio' })` after JSON.parse
</interfaces>

<noise_floor_design_constraint>
The cutoff is a noise FLOOR, NOT local VAD. This nuance is load-bearing:

- **Threshold (0.003 RMS)** is far below any human speech (conversational ~0.03–0.1, whispered voiced segments ~0.005). Real speech ALWAYS passes.
- **It does not detect speech start/end** — it only zeros out chunks mathematically indistinguishable from silence (electronic noise floor, HVAC hum, AEC residue).
- **The previous local-VAD removed at threshold 0.0012** was attempting to gate speech onset; that goal is different and remains forbidden per the architectural memo.
- **Server-side VAD remains the sole arbiter of speech vs. silence** — this cutoff just gives it the clean silence it requires.

The block comment in Task 2's diff MUST state these four points so future maintainers don't conflate this with the prohibited local-VAD pattern.
</noise_floor_design_constraint>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Add 5 failing vitest specs to useVoiceSession.test.ts + draft 84-MANUAL-UAT.md</name>
  <files>frontend/__tests__/hooks/useVoiceSession.test.ts, .planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md</files>
  <behavior>
  Add the 5 specs from `84-RESEARCH.md` § Validation Architecture (test names match VALIDATION.md per-task table 84-01-01 .. 84-01-05). All 5 MUST FAIL initially because the noise-floor cutoff does not yet exist in `useVoiceSession.ts`.

  - Test 1 (`forwards user speech (RMS > floor) after intro onended fires`) — drives ws→ready→intro chunk→`MockAudioBufferSourceNode.autoFinish` queueMicrotask→`onended`. After playback ends, push a Float32Array of ~0.05 RMS through the captured onaudioprocess. Assert `ws.send` was called with a JSON payload of shape `{type:'audio', data: <base64>}`. **Currently passes** (no cutoff today) but will continue passing after the fix — included for SC1 coverage.
  - Test 2 (`drops sub-noise-floor chunks so server VAD can close the turn`) — same setup; after intro, push Float32Array of ~0.001 RMS (sub-floor ambient). Assert NO `ws.send({type:'audio', ...})` for that chunk. Then push 0.05 RMS → assert sent. Then 0.001 → assert NOT sent. **MUST FAIL today** because everything currently forwards.
  - Test 3 (`completes a 4-turn conversation cycle without permanent gating`) — loop 4 times: drive agent audio chunk(s) + `onended`; push user speech (0.05 RMS); manually emit `turn_complete` via `simulateMessage`. Verify on each iteration `isPlayingRef` toggles correctly and the gate opens/closes on schedule (assert by checking that user-speech chunks ARE sent post-onended each cycle). May currently pass, but locks the regression contract.
  - Test 4 (`stale remote activity does not suppress mic during user speech`) — drive intro → onended. Push user speech (0.05 RMS, asserted sent). Simulate a stray `transcript` server event (which bumps `lastRemoteActivityAtRef` — would have re-latched the SC4 wider gate). Push more user speech. Assert it WAS sent. This guards against accidental SC4-style re-introduction.
  - Test 5 (`keeps the half-duplex gate narrow (does not check queue/pending/tail)`) — manually arrange a state where `playbackQueueRef.length > 0` AND `pendingTurnDelayRef !== null` AND `lastRemoteActivityAtRef` is recent, BUT `isPlayingRef === false`. Push 0.05 RMS user chunk. Assert it WAS sent. (If a future PR widens the gate per SC4 verbatim, the chunk would be suppressed and this test fails — surfacing the architectural disagreement.) **MUST PASS today** (gate is already narrow); included as a guard-rail for future PRs.

  Use existing test scaffolding only. Do not introduce new mocks. If a ref is not directly accessible from outside the hook, exercise the equivalent observable behavior (e.g., for Test 5, drive the state via real handlers — push agent chunks without flushing onended, then push user speech — rather than mutating refs directly).

  Also create `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` containing the manual checklist verbatim from `84-VALIDATION.md` § Manual-Only Verifications (quiet 4-turn, noisy 4-turn, mid-utterance non-suppression, whisper, production-log assertion). Header: `# Phase 84 — Manual UAT Checklist`. Reference `84-VALIDATION.md` as the source of truth for sampling discipline.

  Commit message: `test(84-01): add 5 failing specs for HOTFIX-02 noise-floor cutoff (RED) + manual UAT checklist`
  </behavior>
  <action>
  1. Open `frontend/__tests__/hooks/useVoiceSession.test.ts`. Locate the existing `describe('useVoiceSession', ...)` block (or top-level `describe`).
  2. Add a nested `describe('noise-floor cutoff (HOTFIX-02)', () => { ... })` containing the 5 specs above. Use `it()` titles that match the VALIDATION.md per-task table EXACTLY (so `npx vitest run -t "<title fragment>"` from VALIDATION.md filters to a single test):
     - `forwards user speech (RMS > floor) after intro onended fires`
     - `drops sub-noise-floor chunks so server VAD can close the turn`
     - `completes a 4-turn conversation cycle without permanent gating`
     - `stale remote activity does not suppress mic during user speech`
     - `keeps the half-duplex gate narrow (does not check queue/pending/tail)`
  3. Use the existing `MockWebSocket`, `MockAudioContext`, `MockAudioBufferSourceNode`, and `drainPlaybackQueue` exports. Do not modify the harness itself unless absolutely required — if you must, document why in the test file.
  4. RMS-shape helpers: write a tiny in-test helper `makeFloat32ChunkAtRMS(rms: number, length = 128): Float32Array` that fills the array with constant `rms` (sign-alternating to keep average zero so RMS == |value|). 128 samples matches the AudioWorklet block size noted in 84-RESEARCH.md § Risks #4.
  5. Run `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` and confirm Test 2 (and ideally Test 4) FAIL with messages indicating the sub-floor chunk WAS forwarded. Tests 1, 3, 5 may pass or fail depending on existing behavior — that's fine; they lock contracts going into Task 2.
  6. Create `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` with the 5-row checklist from `84-VALIDATION.md` § Manual-Only Verifications. Each row: a checkbox `- [ ]`, the behavior description, the requirement ID, and the test instructions verbatim.
  7. Stage both files and commit using the exact message specified in `<behavior>`. Do NOT run `npm run lint` yet — Task 2 will run it after the implementation lands so lint output reflects the final state.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "drops sub-noise-floor chunks"</automated>
  </verify>
  <done>
  - `frontend/__tests__/hooks/useVoiceSession.test.ts` contains 5 new `it(...)` specs with exact titles matching VALIDATION.md table rows 84-01-01..05.
  - At least Test 2 (`drops sub-noise-floor chunks so server VAD can close the turn`) FAILS with a clear assertion message about the sub-floor chunk being forwarded.
  - `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` exists with the 5-row manual checklist.
  - One git commit with the message above; both files staged together.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Implement noise-floor cutoff in useVoiceSession.ts; turn all 5 specs green; lint clean</name>
  <files>frontend/src/hooks/useVoiceSession.ts</files>
  <behavior>
  Add a module-scope `VOICE_NOISE_FLOOR_RMS` constant with `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS` env override defaulting to `0.003`, and insert the 6-line RMS check inside `forwardInputChunk` IMMEDIATELY AFTER the existing gate at line 886-888 and BEFORE the `float32ToPcm16` call at line 889. Run vitest until all 5 Task-1 specs pass. Run `cd frontend && npm run lint` and fix any new lint issues.

  After fix lands:
  - Test 2 transitions RED → GREEN.
  - Tests 1, 3, 4, 5 remain GREEN (or transition GREEN if any were failing).
  - Half-duplex gate text at line 886-888 remains EXACTLY `if (isPlayingRef.current && !remoteTurnCompleteRef.current) { return; }` — no SC4 widening.

  Commit message: `fix(84-01): implement noise-floor RMS cutoff for HOTFIX-02 (GREEN)`
  </behavior>
  <action>
  1. Open `frontend/src/hooks/useVoiceSession.ts`. Add a new module-scope constant immediately AFTER line 79 (`const REMOTE_TURN_ACTIVITY_TAIL_MS = 650;`) and BEFORE line 80 (`const MIC_CAPTURE_WORKLET_PATH`):

     ```ts
     // Noise-floor RMS cutoff. Drops chunks whose RMS is below this value
     // BEFORE they're encoded and forwarded to the server. This is NOT
     // local VAD: the threshold is far below any human speech (whispered
     // ~0.005, conversational ~0.03+), so real voice ALWAYS passes. Its
     // sole purpose is to give Gemini Live's server-side automatic
     // activity detection (silence_duration_ms in voice_session.py) clean
     // silence after the user pauses — without this, ambient noise + AEC
     // residue keeps the user's turn open server-side and the model
     // never produces a response (see 84-RESEARCH.md § Q3, Q4).
     //
     // Crucially, this is NOT a modification of the half-duplex gate at
     // L886. SC4's proposed multi-condition gate is REJECTED — see
     // 84-RESEARCH.md § Q5. The gate stays narrow; this is a separate,
     // earlier filter on chunk content (energy), not on session state.
     //
     // Tunable via NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS env (string parsed
     // to Number; falsy/NaN falls back to 0.003).
     const VOICE_NOISE_FLOOR_RMS = (() => {
         const raw = process.env.NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS;
         const parsed = raw ? Number(raw) : NaN;
         return Number.isFinite(parsed) && parsed > 0 ? parsed : 0.003;
     })();
     ```

  2. Inside `forwardInputChunk` (definition begins line 843), insert the RMS check between the closing `}` of the gate (line 888) and the `const pcm16 = ...` line (currently 889). The insertion is exactly:

     ```ts
             // Noise-floor cutoff. See VOICE_NOISE_FLOOR_RMS comment at top
             // of file. Computes RMS of the incoming Float32 block; drops
             // pure background so the server VAD can see silence_duration_ms
             // of clean silence after the user pauses. Real speech always
             // exceeds this threshold by 10x+.
             let sumSq = 0;
             for (let i = 0; i < inputData.length; i++) {
                 const s = inputData[i];
                 sumSq += s * s;
             }
             const rms = Math.sqrt(sumSq / inputData.length);
             if (rms < VOICE_NOISE_FLOOR_RMS) {
                 return;
             }
     ```

     Indentation must match the surrounding 4-space style of the file.

  3. DO NOT alter line 886-888 (the half-duplex gate). The gate must remain `if (isPlayingRef.current && !remoteTurnCompleteRef.current) { return; }`.

  4. Run `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` and confirm all 5 noise-floor specs pass. If any still fail, debug — DO NOT widen the gate or alter the threshold materially. (If Test 5 fails, you've accidentally widened the gate; revert and re-read 84-RESEARCH.md § Q5.)

  5. Run `cd frontend && npm run lint`. Fix any new ruff/eslint findings introduced by the change (likely none — the inserted block is plain TS with no new imports). Do NOT auto-format unrelated lines.

  6. Stage `frontend/src/hooks/useVoiceSession.ts` and commit using the exact message specified in `<behavior>`.

  7. Update `.planning/STATE.md` and `.planning/ROADMAP.md` per the project's existing pattern: append "84-voice-gate-deadlock-fix P01" row to the velocity table in STATE.md (with task count and file count); update ROADMAP.md Phase 84 section's `**Plans:**` line to `1/1 plans complete` and replace the `[ ] TBD` plan list bullet with `[x] 84-01-noise-floor-cutoff-PLAN.md — Add noise-floor RMS cutoff in useVoiceSession.ts; reject SC4 (HOTFIX-02)`. Add a Decisions bullet under "Phase 84-voice-gate-deadlock-fix" with the SC4-rejection rationale and the threshold choice (0.003 RMS, env-overridable).

  8. Write `.planning/phases/84-voice-gate-deadlock-fix/84-01-noise-floor-cutoff-SUMMARY.md` per `~/.claude/get-shit-done/templates/summary.md`. Include a prominent **SC4 Rejection Rationale** section quoting `84-RESEARCH.md` §Q5 and noting this plan satisfies SC1+SC2+SC3 via the noise-floor cutoff. Memory-update breadcrumb: list the file `~/.claude/projects/C--Users-expert-documents-pka-pikar-ai/memory/project_voice_brain_dump_architecture.md` with the proposed amendment (currently asserts "no local VAD" — clarify the noise-floor exception). The amendment itself is OUT OF SCOPE for this plan; flag it as a follow-up only.

  9. Stage STATE.md, ROADMAP.md, and the SUMMARY together in a third commit: `docs(84-01): update STATE/ROADMAP + SUMMARY (SC4 rejected; noise-floor implemented)`.
  </action>
  <verify>
    <automated>cd frontend &amp;&amp; npx vitest run __tests__/hooks/useVoiceSession.test.ts</automated>
  </verify>
  <done>
  - `frontend/src/hooks/useVoiceSession.ts` contains the `VOICE_NOISE_FLOOR_RMS` constant near line 80 and the RMS cutoff block inside `forwardInputChunk` between the existing gate and `float32ToPcm16`.
  - Half-duplex gate at line 886-888 (post-insert: line numbers shift) remains EXACTLY `if (isPlayingRef.current && !remoteTurnCompleteRef.current) { return; }` — no widening.
  - All 5 specs in `frontend/__tests__/hooks/useVoiceSession.test.ts` § "noise-floor cutoff (HOTFIX-02)" PASS.
  - `cd frontend && npm run lint` exits 0.
  - `.planning/STATE.md` velocity table appended with the 84-voice-gate-deadlock-fix P01 row; Decisions section gains an SC4-rejection bullet.
  - `.planning/ROADMAP.md` Phase 84 section shows `1/1 plans complete` and the plan list shows `[x] 84-01-noise-floor-cutoff-PLAN.md`.
  - `.planning/phases/84-voice-gate-deadlock-fix/84-01-noise-floor-cutoff-SUMMARY.md` exists with the SC4-rejection rationale section.
  - Three git commits land in order: RED (Task 1), GREEN (this task's code commit), and docs (this task's STATE/ROADMAP/SUMMARY commit).
  </done>
</task>

</tasks>

<verification>
**Per VALIDATION.md per-task table:**
- 84-01-01 (SC1): `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "forwards user speech .* after intro onended"` — green
- 84-01-02 (SC2): `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "drops sub-noise-floor chunks"` — green
- 84-01-03 (SC3): `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "completes a 4-turn conversation cycle"` — green
- 84-01-04 (regression): `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "stale remote activity does not suppress mic"` — green
- 84-01-05 (SC4 rejected): `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "keeps the half-duplex gate narrow"` — green

**Wave-level:**
- `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` — entire file green
- `cd frontend && npm run lint` — exits 0

**Manual UAT (post-deploy, NOT a CI gate but required before milestone close — see 84-MANUAL-UAT.md):**
- 4-turn conversation in quiet room: each agent reply within ~1.5s of pause
- 4-turn conversation in noisy room: each reply within ~2s of pause
- 8+ second mid-utterance: mic NEVER cut off
- Whisper turn: transcribed and replied to
- Production log spot-check: pattern `input_transcription → turn_complete → model_turn → turn_complete → input_transcription` (alternating, NOT `input_transcription × N` with no `model_turn`)
</verification>

<success_criteria>
- HOTFIX-02 SC1 satisfied: user audio reaches server after intro greeting (vitest spec + manual UAT).
- HOTFIX-02 SC2 satisfied: model produces audio response within ~1s of user pause (manual UAT; vitest verifies the mechanism — sub-floor chunks dropped — that enables it).
- HOTFIX-02 SC3 satisfied: 4-turn conversation completes with no stuck silence (vitest spec for the gate behavior; manual UAT for end-to-end Gemini Live session).
- HOTFIX-02 SC4 EXPLICITLY REJECTED: half-duplex gate remains narrow; guard-rail test 5 fails CI if future PRs widen it.
- 5 vitest specs green; full vitest file green; `npm run lint` exits 0.
- STATE.md / ROADMAP.md / SUMMARY.md updated; SC4 rejection rationale recorded in SUMMARY.
- Three git commits land cleanly (RED, GREEN, docs).
</success_criteria>

<output>
After completion:
1. `.planning/phases/84-voice-gate-deadlock-fix/84-01-noise-floor-cutoff-SUMMARY.md` exists with the SC4-rejection rationale section, threshold-choice justification (0.003 RMS, env-overridable via `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS`), and a memory-update breadcrumb pointing to `~/.claude/projects/C--Users-expert-documents-pka-pikar-ai/memory/project_voice_brain_dump_architecture.md` flagging the "no local VAD" rule needs nuance for the noise-floor exception. The memory amendment itself is a follow-up, not part of this plan.
2. `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` exists for QA to run post-deploy.
3. `.planning/STATE.md` velocity table updated; Decisions section records the SC4 rejection as a project decision.
4. `.planning/ROADMAP.md` Phase 84 marked `1/1 plans complete`.
</output>
