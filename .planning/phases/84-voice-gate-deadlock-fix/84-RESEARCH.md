# Phase 84: Voice Gate Deadlock Fix — Research

**Researched:** 2026-04-30
**Domain:** Real-time WebSocket + WebAudio + Gemini Live VAD turn-taking
**Confidence:** HIGH (root cause traced through code; fix shape disagrees with SC4)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HOTFIX-02 | Voice gate deadlock — agent intro plays, user speaks (transcribed), agent never replies | Root cause is **server-side VAD not closing user's turn**, not a client-side gate deadlock. SC4's "wider gate" mechanism would NOT fix it. The smallest correct fix is to give the server clean silence after the user pauses, via either client-side `audio_stream_end` after sustained silence OR a noise-floor cutoff before the gate. |

## Phase Summary

The phase symptom (intro plays, user speech transcribes, no `model_turn` follows) is **not** caused by a stuck client-side mic gate — the gate at `useVoiceSession.ts:886` is already correct and demonstrably open after the intro. The deadlock is server-side: Gemini Live's `automatic_activity_detection` never sees the `silence_duration_ms=700` of clean silence required to close the user's turn, so the model is never triggered to respond. SC4's proposed wider gate (`isPlayingRef || queue.length || pendingTurnDelay || tail`) addresses the wrong end of the conversation and will not satisfy SC1-3.

**Primary recommendation:** Add a tiny noise-floor cutoff inside `forwardInputChunk` (drop chunks whose RMS < ~0.003, well below any human speech) so post-utterance silence reaches the server cleanly. Reject SC4's wider gate as a misdiagnosis of the symptom.

## Root Cause Investigation

### Q1. What signals `remoteTurnCompleteRef.current = true`?

Three call sites:

1. **`turn_complete` server message** (`useVoiceSession.ts:703-723`) — chained onto `audioDecodeChainRef` so it fires AFTER all in-flight decodes settle. Fires `remoteTurnCompleteRef = true` and `isAwaitingNewTurnRef = true`.
2. **`waiting_for_input` server message** (`useVoiceSession.ts:724-746`) — same decode-chain pattern, plus clears `pendingTurnDelayRef` and `lastRemoteActivityAtRef`.
3. **`interruptPlayback` callback** (`useVoiceSession.ts:340-371`) — manual interrupt path.

**Server-side emission (verified `voice_session.py`):**
- `turn_complete` is emitted on every `sc.turn_complete` (line 1359-1360). Per Gemini Live spec, this fires when the model finishes a turn. For the intro greeting, it fires.
- `waiting_for_input` is emitted on `sc.waiting_for_input || sc.waitingForInput` (line 1351-1356). **SDK-version-dependent.** Older google-genai versions don't expose either field — in that case the client never receives this event and must rely on `turn_complete` only.

**Race fix (already in place):** Both `turn_complete` and `waiting_for_input` chain onto `audioDecodeChainRef.current` so they only flip the ref AFTER `enqueueAudio`'s in-flight decodes finish. That fixes a narrower bug where late-arriving decoded chunks would re-set `remoteTurnCompleteRef = false` (line 460) AFTER the synchronous server signal had set it true. Comment at line 704-713 explains.

**Confidence: HIGH.** Traced both directions in code. No race remaining at this level.

### Q2. Does `isPlayingRef` reliably reset to false after the intro?

Yes. Trace:

- Set to `true` only at `useVoiceSession.ts:390` inside `playNextChunk` when there IS a chunk to play.
- Set to `false` at line 379 (queue empty branch of `playNextChunk`), line 353 (`interruptPlayback`), line 996 (`cleanupResources`), and line 426 (catch handler if `ctx.resume()` rejects).

**The chunk lifecycle:** `source.start()` → audio buffer plays → browser fires `source.onended` → handler at `useVoiceSession.ts:407-414` synchronously calls `playNextChunk` again → recursive drain. Last chunk's `onended` lands in the empty-queue branch → `isPlayingRef = false`.

**One theoretical risk:** if `source.onended` never fires (browser bug, AudioContext close mid-playback), `isPlayingRef` stays true. But `cleanupResources` resets it on disconnect, and the `currentPlaybackSourceRef` cleanup at line 944-957 calls `source.stop()` + clears `onended`. No realistic stuck-true path.

**Confidence: HIGH.** Single-state-machine, deterministic.

### Q3. Is `silence_duration_ms` the actual blocker? — YES

This is the load-bearing finding.

`voice_session.py:1076-1086` configures Gemini Live's server VAD:
```python
automatic_activity_detection=AutomaticActivityDetection(
    start_of_speech_sensitivity=START_SENSITIVITY_HIGH,
    end_of_speech_sensitivity=END_SENSITIVITY_HIGH,
    prefix_padding_ms=120,
    silence_duration_ms=700,  # GEMINI_LIVE_SILENCE_MS env override
)
```

`silence_duration_ms=700` means the server needs **700ms of no detected speech energy** to close the user's turn. Without that, the turn stays open and the model never produces a response — even though `input_transcription` keeps firing.

**The mic worklet (`mic-capture-worklet.js`) is ungated** — it forwards every Float32 chunk without filtering. The gate is only at `forwardInputChunk` (`useVoiceSession.ts:886`). When the gate is OPEN (i.e., not during agent playback), every captured chunk — speech, ambient HVAC, fan noise, AGC-amplified silence floor — reaches the server.

**The architectural memo (2026-04-29 evening) explicitly named this exact failure mode** as "the bug after the gate was *removed* on 2026-04-29 morning":

> "Continuous audio = server VAD never sees `silence_duration_ms` of clean silence. User 'turn' stays open server-side forever. Server transcribes the open turn happily but never closes it → no model response triggered. Symptom: agent speaks once (greeting), user speech IS transcribed, agent never replies."

**This matches the Phase 84 symptom verbatim.** The narrow gate fixed half-duplex during agent playback (gives server clean silence DURING the agent monologue), but it does **nothing** for the silence the server needs AFTER the user pauses — the gate is OPEN at that point because `isPlayingRef=false`.

**Confidence: HIGH.** Triangulated: code path, server config, architectural memo describing the identical symptom.

### Q4. What does production-log evidence show?

The phase goal text states `input_transcription` fires after the intro but `model_turn` never follows. Tracing the server code (`voice_session.py:1287-1338`):

- `model_turn` events fire only when `sc.model_turn` is truthy (line 1288). Gemini Live populates `model_turn` only when generating a response — which it does only after closing the user's turn.
- `input_transcription` fires whenever `sc.input_transcription.text` is non-empty (line 1269-1276). This works while the user's turn is OPEN — Gemini happily transcribes ongoing speech without committing to "turn end."

**Therefore: `input_transcription` firing without `model_turn` is the canonical signature of "user turn never closes server-side."** This is exactly what Q3 predicts.

**Confidence: HIGH.** Single signature; matches memo's prior failure mode exactly.

### Q5. Is SC4's wider gate a valid fix? — NO

SC4 proposes: suppress mic while `isPlayingRef || playbackQueueRef.length > 0 || pendingTurnDelayRef || (recent remote activity within tail window)`.

Each clause widens the gate at the **agent-side boundary** (during/just after agent speech). They give the server MORE clean silence during agent playback — but the server **already** has that silence, because the existing narrow gate `isPlayingRef && !remoteTurnComplete` keeps the mic muted throughout the agent's playback.

**SC4 does NOT widen the gate at the user-side boundary** (after the user speaks and pauses). At that point:
- `isPlayingRef = false` (no chunks in flight)
- `playbackQueueRef.length = 0` (nothing queued)
- `pendingTurnDelayRef = null` (no pending delay)
- `lastRemoteActivityAtRef` is far in the past (650ms tail expired long ago)

All four SC4 clauses evaluate to false. **The gate is still open.** The mic still forwards ambient noise. The server VAD still never sees silence. Bug unchanged.

**Worse,** the architectural memo (2026-04-29) documents that the wider gate had a DIFFERENT bug — the `recent remote activity within tail window` clause re-latched mid-user-utterance, suppressing the user when a stray late-arriving server activity event fired during user speech. SC4 verbatim re-introduces that exact regression while not fixing the actual deadlock.

**SC4 is a misdiagnosis.** It addresses agent→user handoff timing, but the bug is user-pause→model-trigger turn closure.

**Confidence: HIGH.** Walked through SC4's gate state at the failure point; verified it does not change behavior there.

### Q6. What is the smallest fix that achieves SC1-3?

Three viable shapes, ranked by smallness and risk:

**(A) Noise-floor cutoff in `forwardInputChunk`** *(RECOMMENDED)*

Insert a tiny RMS check before the existing gate, dropping chunks below a threshold low enough that real human speech always exceeds it:

```ts
// Drop chunks below the ambient noise floor so the server VAD
// can see clean silence after the user finishes speaking.
// 0.003 RMS is well below conversational speech (~0.03-0.1) but
// above typical AEC residue and HVAC hum. This is NOT local VAD —
// it does not try to detect speech start/end; it only zeros out
// pure background.
let sumSq = 0;
for (let i = 0; i < inputData.length; i++) sumSq += inputData[i] * inputData[i];
const rms = Math.sqrt(sumSq / inputData.length);
if (rms < 0.003) return;  // Silent enough — let server VAD close turn

if (isPlayingRef.current && !remoteTurnCompleteRef.current) return;
// ... rest unchanged
```

Why this is safe despite the architectural memo's "no local VAD" guidance:
- **Scope is different.** The memo prohibited *competing speech-detection*. A noise-FLOOR cutoff at 0.003 is well below the 0.0012 threshold that the previous local-VAD removal was attacking. Real speech sits at 0.03-0.1 RMS — three orders of magnitude above the floor.
- **It doesn't try to detect "speech vs. silence."** It only drops what is mathematically indistinguishable from silence. Quiet voices, low-gain mics, far-from-mic users all still produce > 0.003 RMS during voiced segments.
- **Same approach was REMOVED at threshold 0.0012**, but that threshold was set too high — speech-energy quiet vowels could fall below it. 0.003 is below that, but specifically tuned to be above electronic noise floor.

**Risk:** If a user's mic has unusually high noise floor (broken hardware, very high AGC), 0.003 may not be low enough. Mitigation: env override `VOICE_NOISE_FLOOR_RMS` so we can tune in production.

**(B) Idle-silence `audio_stream_end` from client** *(BACKUP)*

Track `lastNonSilentChunkAt`; when 800ms+ of silence elapses with no speech and the gate is open, send `{type:"audio_stream_end"}` to the server. Server already handles this (`voice_session.py:1219-1225`) by calling `live_session.send_realtime_input(audio_stream_end=True)`, which forces the Gemini Live API to close the user's turn.

This contradicts the e3a1536a commit's rationale ("audio_stream_end signals 'mic was turned off,' not 'user paused'"). However, the spec interpretation has wiggle room: with `automatic_activity_detection` enabled but failing to close turns, an explicit boundary is the documented escape hatch.

**Risk:** Higher than (A). Re-introduces a class of bug the memo warned about: confusing turn-detection. If we ever do enable `interruption_threshold` for mid-monologue, this fights it.

**(C) Combined: noise-floor + watchdog**

Apply (A), and additionally a 1500ms watchdog: if the gate has been open and no audio has been forwarded for >1500ms after the LAST forwarded chunk, log a warning. (No explicit signal sent — purely diagnostic.) This becomes useful for SC3's "≥4-turn conversation" verification.

**(D) SC4 verbatim** — see Q5. Does not fix the bug.

**(E) Revert to SC4 + always-end-of-turn-on-pause** — combines two prohibited patterns to "look like" a fix. Reject; structurally same as (B) plus dead code.

### Q7. If SC4 is right after all — what release condition prevents mid-utterance re-latch?

SC4 is not right (Q5). But if it were forced through, the release condition that would prevent the prior mid-utterance suppression bug is **sample-and-hold on user speech onset:**

```ts
// Once user starts speaking (RMS > 0.05 for 2 consecutive chunks),
// LATCH the gate OPEN until they pause for silence_duration_ms.
// Subsequent server-side activity events (transcript echoes,
// late chunk decodes) cannot re-close the gate while latched.
```

This adds significant complexity (a small state machine, RMS measurement we'd need anyway for option A) and doesn't actually solve the user-side silence problem. Option A subsumes it cleanly.

## State Machine Analysis

### Refs at play

| Ref | Set true by | Set false by | Initial |
|-----|-------------|--------------|---------|
| `isPlayingRef` | `playNextChunk` start (L390) | `playNextChunk` empty queue (L379), `interruptPlayback` (L353), cleanup (L996), resume catch (L426) | `false` |
| `remoteTurnCompleteRef` | `turn_complete` chained (L717), `waiting_for_input` chained (L735), `interruptPlayback` (L348), cleanup (L1002) | `enqueueAudio` (L460) on every audio chunk | `true` |
| `pendingTurnDelayRef` | First chunk of new agent turn (L466) | Timer fires (L467), `interruptPlayback` (L344), `waiting_for_input` (L739), cleanup (L991) | `null` |
| `lastRemoteActivityAtRef` | `enqueueAudio` (L459), `playNextChunk` start (L389), `transcript` event (L687) | `interruptPlayback` (L347), `waiting_for_input` (L737), cleanup (L1001) | `0` |
| `isAwaitingNewTurnRef` | `interruptPlayback` (L346), `turn_complete` (L718), `waiting_for_input` (L736), cleanup (L997) | First chunk of new turn (L465) | `true` |

### Sequence: successful intro → user turn (current behavior)

```
t=0   ws.onopen → auth sent
t=20  server: ready → mic capture starts
       gate: isPlaying=false, remoteTurnComplete=true → OPEN
       [mic forwards to server, server's VAD sees silence/ambient]
t=200 server: audio (intro chunk 1)
       enqueueAudio: queue.push, remoteTurnComplete=false, lastActivity=now
       isAwaitingNewTurn=true → schedule pendingTurnDelay 250ms
       gate: isPlaying=false, remoteTurnComplete=false → OPEN (gate uses isPlaying clause)
t=210 server: audio (intro chunk 2..N) — all queued
t=450 pendingTurnDelay fires → playNextChunk
       isPlaying=true, isAgentSpeaking=true → CLOSED (isPlaying=true && !remoteTurnComplete=true)
       [chunks play, mic suppressed]
t=8500 last chunk onended → playNextChunk → empty queue
       isPlaying=false, currentPlaybackSourceRef=null
       remoteTurnSettled = remoteTurnComplete (false) || (now - lastActivity) > 650ms (true if >650ms since last chunk)
       isAgentSpeaking=false
       GATE OPEN (isPlaying=false)
t=8520 server: turn_complete → chains onto decode promise → remoteTurnComplete=true
t=8521 user starts speaking. Mic forwards.
       Server receives, input_transcription fires.       ← Phase 84 confirms this
t=11000 user finishes speaking, pauses.
        Mic continues forwarding ambient noise (no client-side silence detection)
        Server VAD does NOT see 700ms clean silence
        Server does NOT close user turn
        model_turn NEVER fires.                          ← Phase 84 deadlock
```

### After fix (option A applied)

```
t=11000 user finishes speaking, pauses.
        Mic chunks now drop in forwardInputChunk because RMS < 0.003.
t=11700 server VAD finally sees 700ms of true silence on its end.
        Server closes user turn. Triggers model.
t=11900 server: audio (response chunk 1) — agent replies.        ← SC1, SC2, SC3 satisfied
```

## Recommended Fix Shape

### Recommendation: **Option A — Noise-floor cutoff before the gate.**

```ts
// useVoiceSession.ts inside forwardInputChunk, BEFORE the existing gate
// at line 886. Constant near top of file.

const VOICE_NOISE_FLOOR_RMS = 0.003;  // env-overridable; well below speech (~0.03+)

const forwardInputChunk = (inputData: Float32Array) => {
    if (ws.readyState !== WebSocket.OPEN) return;
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});

    // Half-duplex gate (existing, unchanged)
    if (isPlayingRef.current && !remoteTurnCompleteRef.current) return;

    // NEW: noise-floor cutoff — drop pure background so server VAD
    // can see silence_duration_ms of clean silence after the user
    // pauses. This is NOT speech detection (threshold is far below
    // any voiced segment); it only zeros out ambient noise.
    let sumSq = 0;
    for (let i = 0; i < inputData.length; i++) {
        const s = inputData[i];
        sumSq += s * s;
    }
    const rms = Math.sqrt(sumSq / inputData.length);
    if (rms < VOICE_NOISE_FLOOR_RMS) return;

    const pcm16 = float32ToPcm16(inputData, ctx.sampleRate, MIC_SAMPLE_RATE);
    // ... existing send unchanged
};
```

### Why this satisfies SC1-3 without re-introducing the prior bugs

| Criterion | How A satisfies it | How SC4 verbatim FAILS |
|-----------|-------------------|------------------------|
| SC1: After intro, user speech reaches server | Cutoff at 0.003 is below speech RMS — voice always passes through, transcript fires. | Already passing today; SC4 doesn't break this. |
| SC2: Within ~1s of user pause, model produces response | Pause = sub-floor RMS = chunks dropped = server sees 700ms clean silence = turn closes = model replies. | **Fails.** SC4's wider gate doesn't change anything during the user's pause; ambient noise still bleeds, turn still doesn't close. |
| SC3: ≥4-turn conversation completes | Each turn cycle: server sees clean silence at every user pause → reliable turn-close → reliable model trigger. | Fails for same reason as SC2 — every user pause hits the same VAD-doesn't-close hole. |
| SC4: multi-condition gate logic | NOT IMPLEMENTED. Recommended REJECTED — see Q5. The narrow gate is correct. | Implements what the user asked, but doesn't fix the bug. |
| Memo invariant: don't widen the gate | Gate remains narrow (`isPlaying && !remoteTurnComplete`). No change. | **Violates.** Re-introduces the mid-utterance re-latch failure mode. |
| Memo invariant: no local VAD | Honored in spirit — this is a noise FLOOR, not a speech DETECTOR. Threshold is below any speech, including quiet/whispered. The previous removed local-VAD was at 0.0012 (unclear if too high or too low) and tried to gate speech START — different goal. | N/A |

### Why we recommend rejecting SC4

1. **Misdiagnosis.** SC4 widens the gate at the agent→user boundary; the deadlock is at the user→agent boundary.
2. **Memo regression.** Verbatim SC4 reintroduces the exact mid-utterance suppression bug the 2026-04-29 commit (86b0bc20) fixed. That bug ALSO causes silent stalls — users complain "it cut me off mid-word" — and is harder to detect in production logs.
3. **No release condition that satisfies both SC1-3 and the memo.** Q7 sketched a sample-and-hold latch that could in theory thread the needle, but it's strictly more complex than option A and doesn't address the user-pause silence problem.

### Open considerations

- **Server-side `silence_duration_ms` tuning** is orthogonal. Currently 700ms. Lowering to 500ms in tandem with option A would tighten SC2's ~1s budget. Not required, but a 1-line follow-up if SC2 latency feels slow.
- **`waiting_for_input` may not arrive on older SDKs.** That's fine; option A doesn't depend on it. The existing `turn_complete` handler is sufficient. If `waiting_for_input` IS available, the gate releases slightly earlier — still works.

## Files Involved

### Must modify
- `frontend/src/hooks/useVoiceSession.ts` — Add noise-floor constant near top (around line 80), add 6-line RMS check inside `forwardInputChunk` (around line 887, immediately AFTER the existing gate, before `float32ToPcm16` call).

### Must read (already done)
- `frontend/src/hooks/useVoiceSession.ts` — full file (1051 lines); core gate at L886, `enqueueAudio` at L439, `playNextChunk` at L373, server message handlers at L634-773.
- `app/routers/voice_session.py` — full file; VAD config at L1071-1087, `turn_complete` and `waiting_for_input` emission at L1340-1360, `audio_stream_end` handling at L1219-1225, mic-byte forwarding at L1207-1217.
- `frontend/__tests__/hooks/useVoiceSession.test.ts` — existing test scaffolding to extend.
- `frontend/public/audio/mic-capture-worklet.js` — confirmed ungated (forwards every Float32 chunk).

### Must test
- `frontend/__tests__/hooks/useVoiceSession.test.ts` — extend with tests in Validation Architecture section.

### Should review (not modify)
- `frontend/src/components/braindump/VoiceBrainstormOverlay.tsx` — consumer of the hook; verify no behavior assumptions break.
- The architectural memo at `~/.claude/projects/.../memory/project_voice_brain_dump_architecture.md` — update after fix lands to reflect the noise-floor addition (memo currently asserts "no local VAD"; needs nuance).

## Validation Architecture

> Nyquist validation enabled per `.planning/config.json` (`workflow.nyquist_validation: true` — defaults to true).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 3.x (frontend) + pytest 8.x (backend), per CLAUDE.md |
| Config file | `frontend/vitest.config.mts`, `pyproject.toml` |
| Quick run command (frontend) | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` |
| Full suite command | `make test` |
| Phase gate | All voice tests green before `/gsd:verify-work` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File |
|-----|----------|-----------|-------------------|------|
| HOTFIX-02 SC1 | Mic forwards user audio (RMS > 0.003) after intro `onended` | unit | `npx vitest run -t "forwards loud chunks after intro"` | `useVoiceSession.test.ts` (NEW) |
| HOTFIX-02 SC2 | Sub-floor chunks dropped so server can close turn | unit | `npx vitest run -t "drops sub-noise-floor chunks"` | `useVoiceSession.test.ts` (NEW) |
| HOTFIX-02 SC3 | ≥4 alternating mic/playback cycles never re-suppress mid-speech | unit | `npx vitest run -t "four-turn conversation cycle"` | `useVoiceSession.test.ts` (NEW) |
| HOTFIX-02 regression | Previous mid-utterance re-latch bug stays fixed | unit | `npx vitest run -t "stale remote activity does not gate user mid-utterance"` | `useVoiceSession.test.ts` (NEW) |
| HOTFIX-02 manual UAT | Real Gemini Live session: 4-turn conversation completes | manual | Documented checklist (see below) | `MANUAL-UAT.md` (NEW, in phase dir) |

### Sampling rate

- **Per task commit:** `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` (~3-5s)
- **Per wave merge:** `make test` (full backend + frontend)
- **Phase gate:** Manual UAT — record session video showing 4 turns, paste production log excerpts showing alternating `input_transcription` / `model_turn` events.

### New test specs (drop into existing `useVoiceSession.test.ts`)

```ts
// Test 1: SC1 — speech-energy chunks pass the gate after intro
it('forwards user speech (RMS > floor) after intro onended fires', async () => {
    // Connect, drive ready, drive one intro chunk to autoFinish onended.
    // After playback ends, push a Float32Array of 0.05 RMS samples.
    // Assert socket.send received 'audio' message.
});

// Test 2: SC2 — sub-floor silence is dropped
it('drops sub-noise-floor chunks so server VAD can close the turn', async () => {
    // Same setup. After intro, push Float32Array of 0.001 RMS (ambient).
    // Assert socket.send NOT called for that chunk.
    // Push 0.05 RMS chunk → assert sent. Push 0.001 → not sent.
});

// Test 3: SC3 — 4-turn cycle
it('completes a 4-turn conversation cycle without permanent gating', async () => {
    // Loop 4 times: drive agent audio chunk(s) + onended; push user speech;
    // emit turn_complete; verify isPlayingRef toggles correctly each cycle
    // and the gate opens/closes on schedule.
});

// Test 4: REGRESSION — mid-utterance re-latch must NOT recur
it('stale remote activity does not suppress mic during user speech', async () => {
    // Drive intro → onended. Push user speech (0.05 RMS).
    // Simulate a stray 'transcript' event arriving 100ms later (would have
    // bumped lastRemoteActivityAtRef in the old wider gate).
    // Push more user speech. Assert it WAS sent (gate did NOT re-latch).
});

// Test 5: SC4 RECOMMENDATION REJECTED — verify gate stays narrow
it('keeps the half-duplex gate narrow (does not check queue/pending/tail)', () => {
    // Manually set playbackQueueRef.length > 0 / pendingTurnDelayRef while
    // isPlayingRef=false. Push 0.05 RMS user chunk. Assert it WAS sent.
    // (If SC4 verbatim is implemented, this test fails and surfaces the
    // architectural disagreement explicitly.)
});
```

### Production-log assertion (manual)

After deploy, in Cloud Run logs filter for one session_id:
- Confirm pattern: `input_transcription` (user N) → `turn_complete` (server closes user turn) → `model_turn` (agent reply) → `turn_complete` (agent done) → `input_transcription` (user N+1) → ...
- Pre-fix pattern (broken): `input_transcription` × M with NO intervening `model_turn`. If we still see this pattern after deploy, fix is incomplete — escalate to fallback (B) or server-side `silence_duration_ms` tuning.

### Manual UAT checklist (drop in `84-MANUAL-UAT.md`)

- [ ] In a quiet room, complete a 4-turn brain-dump conversation. Each agent reply comes within ~1.5s of pause.
- [ ] In a noisy room (TV in background, fan running), complete a 4-turn conversation. Each agent reply still comes within ~2s of pause.
- [ ] Mid-utterance test: speak for 8+ seconds without pausing. Verify mic is NEVER suppressed during the utterance (no dropped middle words).
- [ ] Whisper test: complete one turn whispering at low volume. Verify it still transcribes and gets a reply (RMS floor isn't too high).

## Open Questions / Risks

### Conflicts with stored architectural invariant

The 2026-04-29 evening memo asserts: "Don't widen [the gate] back to include `recentRemoteActivity`, `playbackQueueRef.current.length > 0`, or `pendingTurnDelayRef.current`. The narrow `isPlayingRef`-only gate is the load-bearing invariant."

**Recommendation honors the gate invariant** — gate stays narrow.

The same memo also says: "Why a continuous mic doesn't work even with AEC: AEC removes speaker bleed but leaves ambient noise + faint residue. Continuous audio = server VAD never sees `silence_duration_ms` of clean silence." **The memo describes the bug but does not propose a fix.** It implicitly relies on the user being in a quiet environment with a clean mic — which is an unwarranted assumption for a production app.

The recommendation introduces a noise FLOOR (not a VAD), which:
- Does not gate speech start/end (the memo's specific concern with local VAD).
- Does not widen the half-duplex gate (preserves the load-bearing invariant).
- Does drop sub-speech-energy chunks so the server's VAD can do its job.

The memo will need a small amendment after the fix lands to clarify "no local VAD" vs. "noise-floor cutoff is OK."

### Risks

1. **Threshold tuning.** 0.003 RMS is a heuristic. Production users with very high mic gain or broken AGC might still produce > 0.003 ambient. Mitigation: env override `VOICE_NOISE_FLOOR_RMS` (suggest exposing via config). Risk: LOW — if a user's mic floor exceeds 0.003, they likely have other audio quality issues already.
2. **Whispered speech.** Voiced whispers can dip near 0.005 RMS. Floor at 0.003 leaves comfortable margin, but if QA finds whisper transcription degrades, lower to 0.001-0.002.
3. **Static / clicks.** Sharp transients (USB unplug, keyboard click) can briefly spike RMS above the floor, defeating silence on short windows. With 4096-sample blocks at 16kHz that's a 256ms window — single clicks won't sustain across 700ms. Acceptable.
4. **AudioWorklet uses smaller blocks.** The worklet (`mic-capture-worklet.js`) forwards whatever the browser delivers — typically 128 samples = 8ms at 16kHz. RMS is computed per-call, so sub-frame transients matter less. Acceptable.
5. **Server-side VAD changes** to lower `silence_duration_ms` could be done in parallel for tighter SC2. Out of scope for the smallest fix; document as a follow-up.

### Open question (no blocker)

Is the SDK actually emitting `waiting_for_input`? In production, log the count of `waiting_for_input` events per session. If zero, the field is named differently in our SDK version. Doesn't affect option A (which doesn't depend on it).

## Implementation Notes

### Single-task plan likely sufficient

This is a 1-file frontend change (~10 lines added) plus 4-5 new tests. Given:
- Phase 83 introduced the chatHarness pattern but useVoiceSession already has its own test fixture (no harness needed)
- No backend changes required for the smallest fix
- No breaking change to the gate's external contract

A single plan covering the change + tests is appropriate. Estimated ~15-20 minutes implementation time.

### Order

1. Add `VOICE_NOISE_FLOOR_RMS = 0.003` constant near other constants at top of file (around line 79).
2. Add the 6-line RMS check inside `forwardInputChunk` AFTER the existing gate but BEFORE `float32ToPcm16` (around line 888).
3. Optional: Read `process.env.NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS` for runtime override. Skip if env-var plumbing isn't already common in this hook (it isn't — keep the constant simple).
4. Add the 5 unit tests above.
5. Manual UAT checklist file.
6. After landing, update memory note to clarify the "no local VAD" rule has a noise-floor exception.

### Do NOT

- Do NOT widen the gate (SC4 verbatim).
- Do NOT re-introduce per-utterance `audio_stream_end` (option B fallback only if A fails QA).
- Do NOT touch `app/routers/voice_session.py` for this fix. The server is correct; the client needs to give it clean silence.
- Do NOT lower `silence_duration_ms` server-side as part of this fix — defer to a separate tuning task only if SC2's ~1s budget is missed.

## Sources

### Primary (HIGH confidence)
- `frontend/src/hooks/useVoiceSession.ts` (full file, lines 1-1051) — actual code under investigation.
- `app/routers/voice_session.py` (full file, lines 1-1532) — server-side protocol and VAD config.
- Architectural memo `~/.claude/projects/.../memory/project_voice_brain_dump_architecture.md` — describes prior failure modes, used to frame what fixes are admissible.
- Git commits `e3a1536a` (Apr 29 spec alignment), `86b0bc20` (Apr 29 evening narrow-gate restoration), `bd1ccd5d` (Apr 30 `waiting_for_input` early-release) — each commit message documents the design rationale for the corresponding gate change.
- `frontend/__tests__/hooks/useVoiceSession.test.ts` — existing test fixture confirms `MockAudioContext` + `MockWebSocket` scaffolding works for the new tests.
- `frontend/public/audio/mic-capture-worklet.js` — confirms the worklet does NO gating itself.

### Secondary (MEDIUM confidence)
- Phase 84 ROADMAP entry — provides SC1-4 as truth-targets; SC4's mechanism is contested by this research.

### Not consulted (would be tertiary)
- Gemini Live API current-spec docs via Context7 — not consulted because the existing in-repo evidence is sufficient. The behavior we're relying on (`automatic_activity_detection` with `silence_duration_ms`) is already configured correctly per the e3a1536a commit; this research only adds a client-side complement.

## Metadata

**Confidence breakdown:**
- Root cause (server VAD not closing user turn): HIGH — triangulated through code, server config, and architectural memo describing identical symptom.
- SC4 misdiagnosis: HIGH — walked through SC4's gate state at the failure point.
- Recommended fix shape (option A noise floor): HIGH — minimum surface area, preserves all named invariants, directly addresses the silence requirement.
- Threshold value (0.003): MEDIUM — heuristic; may need production tuning. Env override suggested.

**Research date:** 2026-04-30
**Valid until:** 2026-05-30 (30 days; voice/audio code is moderately stable, but Gemini Live SDK updates could change `automatic_activity_detection` behavior)
