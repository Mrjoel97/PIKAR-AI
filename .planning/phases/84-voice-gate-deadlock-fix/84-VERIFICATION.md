---
phase: 84-voice-gate-deadlock-fix
verified: 2026-04-30T23:10:00Z
status: passed
score: 4/4 must-haves verified (automated); 5 manual UAT cases approved by user
human_verified_at: 2026-04-30
human_verified_by: user (approved)
re_verification:
  previous_status: none
  notes: "Initial verification — no prior 84-VERIFICATION.md existed."
human_verification:
  - test: "Quiet 4-turn conversation"
    expected: "In a quiet room, complete a 4-turn brain-dump conversation. Each agent reply within ~1.5s of the user pause. No stuck silence, no missed user words, no permanent mic gating."
    why_human: "Requires real Gemini Live server-side VAD + real microphone + real WebAudio AEC. The cutoff math is automated in jsdom but the silence_duration_ms=700 race against ambient is intrinsically a live behavior."
  - test: "Noisy 4-turn conversation"
    expected: "Same as quiet, but with TV/fan running. Each reply within ~2s. If reply NEVER comes, raise NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS to 0.005 or 0.007."
    why_human: "Threshold tuning against real ambient noise spectra cannot be exercised by Float32 fixtures; only live mics expose AGC/noise-floor edge cases."
  - test: "Mid-utterance non-suppression (regression guard)"
    expected: "Speak continuously for 8+ seconds without pausing. Mic NEVER cut off mid-word; no middle-word drops in transcript."
    why_human: "Validates the prior mid-utterance re-latch bug (the one fixed by 86b0bc20) stays fixed against real server activity event timing."
  - test: "Whisper test (threshold not too high)"
    expected: "Complete one turn whispering at low volume. Whisper transcribes and gets a reply."
    why_human: "Confirms the 0.003 floor leaves margin above whispered voiced segments (~0.005 RMS) under real mic conditions."
  - test: "Production-log assertion"
    expected: "After deploy, in Cloud Run logs filter by one session_id. Confirm pattern: input_transcription → turn_complete → model_turn → turn_complete → input_transcription (alternating). NOT input_transcription × N with no model_turn."
    why_human: "Only Cloud Run telemetry on a real Gemini Live session can prove the server-side VAD is now closing user turns."
---

# Phase 84: Voice Gate Deadlock Fix — Verification Report

**Phase Goal (per ROADMAP — note: stale residue from before SC4 rejection):** "The brain-dump voice session is bidirectional — agent greets, user speaks, agent responds, repeat — with no permanent mic gating after the intro."

**Binding Success Criteria (per planner + research):** SC1, SC2, SC3 only. SC4 was EXPLICITLY REJECTED during planning per `84-RESEARCH.md` §Q5; see "SC4 Rejection Verification" section below.

**Verified:** 2026-04-30T23:10:00Z
**Status:** `human_needed`
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Observable Truths (must_haves.truths from PLAN frontmatter)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After the agent's intro greeting completes, the user can speak and the audio reaches the server (verified via input_transcription in production logs and a vitest spec asserting forwardInputChunk emits an 'audio' WebSocket frame for a 0.05-RMS chunk after onended fires) | ✓ VERIFIED (auto) / ? PENDING (live) | Test 1 GREEN — `forwards user speech (RMS > floor) after intro onended fires` (test file L466-482). Production log assertion deferred to manual UAT case 5. |
| 2 | Within ~1s of the user pausing for silence_duration_ms (700ms server-side), the model produces an audio response — because sub-noise-floor chunks (RMS < VOICE_NOISE_FLOOR_RMS, default 0.003) are dropped before float32ToPcm16 so server VAD finally observes clean silence | ✓ VERIFIED (mechanism) / ? PENDING (live latency) | Test 2 GREEN — `drops sub-noise-floor chunks so server VAD can close the turn` (test file L484-507). Sub-floor (0.001) chunks correctly dropped; speech-energy (0.05) chunks pass. Live latency deferred to manual UAT cases 1+2. |
| 3 | A full ≥4-turn conversation completes end-to-end with no stuck silence — verified by a vitest spec that loops agent-audio + onended + user-speech + turn_complete four times and asserts the gate opens/closes correctly each cycle | ✓ VERIFIED (auto) / ? PENDING (live) | Test 3 GREEN — `completes a 4-turn conversation cycle without permanent gating` (test file L509-554). 4 cycles × user-speech + agent-audio + turn_complete; gate releases every cycle. End-to-end live verification deferred to manual UAT case 1. |
| 4 | ARCHITECTURAL INVARIANT: the half-duplex gate at useVoiceSession.ts:909 (post-insert) remains exactly `if (isPlayingRef.current && !remoteTurnCompleteRef.current) return;`. The noise-floor cutoff is implemented as a SEPARATE filter immediately AFTER that gate and BEFORE float32ToPcm16. SC4 is EXPLICITLY REJECTED per 84-RESEARCH.md §Q5 and a guard-rail test asserts the gate stays narrow | ✓ VERIFIED | Gate verbatim at `frontend/src/hooks/useVoiceSession.ts:909` (read confirmed). RMS check inserted at L913-928, BEFORE `float32ToPcm16` at L930. `grep -c "isPlayingRef.current && !remoteTurnCompleteRef.current"` returns `1` — exactly one occurrence. Test 5 GREEN — `keeps the half-duplex gate narrow (does not check queue/pending/tail)` runs in isolation and passes. |

**Score:** 4/4 truths automation-verified. Truths 1-3 each have a corresponding manual UAT case for live verification.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/hooks/useVoiceSession.ts` | Noise-floor RMS cutoff + VOICE_NOISE_FLOOR_RMS module constant with NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS env override | ✓ VERIFIED | Constant at L98-102 (env-overridable IIFE, 0.003 default, NaN/non-positive fallback). Block comment L80-97 matches plan spec. RMS check at L913-928 inside `forwardInputChunk`, AFTER the gate (L909-911), BEFORE `float32ToPcm16` (L930). Indentation 12-space matches surrounding closure block. |
| `frontend/__tests__/hooks/useVoiceSession.test.ts` | 5 new vitest specs (SC1, SC2, SC3, regression, SC4-rejection guard-rail) | ✓ VERIFIED | `describe('noise-floor cutoff (HOTFIX-02)', ...)` at L375 contains all 5 specs (L466, 484, 509, 556, 587). Helpers `makeFloat32ChunkAtRMS` (L383), `driveToPostIntro` (L401), `pushChunk` (L447), `audioSendCount` (L460) wire the harness. Test titles match VALIDATION.md per-task table 84-01-01..05 EXACTLY. |
| `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` | Manual UAT checklist (quiet/noisy/mid-utterance/whisper) + production-log assertion pattern | ✓ VERIFIED | File created. Header `# Phase 84 — Manual UAT Checklist` matches plan. 5 rows: quiet 4-turn (SC1+SC2+SC3), noisy 4-turn (SC2 robustness), mid-utterance non-suppression (memo regression guard), whisper (threshold not too high), production-log assertion. References `84-VALIDATION.md` as source of truth for sampling discipline. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `forwardInputChunk` (useVoiceSession.ts) | existing half-duplex gate at L909 + new RMS cutoff at L913-928 | RMS check executes immediately after the gate (L909-911) and before float32ToPcm16 (L930) | ✓ WIRED | Read confirmed: gate L909, comment block L913-919, sumSq loop L920-924, sqrt L925, threshold compare + return L926-928, float32ToPcm16 L930. Order is: ws-readyState gate → ctx.resume → narrow half-duplex gate → RMS noise floor → encode → send. |
| `useVoiceSession.test.ts` | MockWebSocket.send + MockAudioBufferSourceNode.onended scaffolding | Existing pattern: emit Float32 chunks via captured onaudioprocess, assert ws.send call shape `{type: 'audio', ...}` | ✓ WIRED | `audioSendCount` helper (L460-464) filters `socket.send.mock.calls` for `type: 'audio'` payloads after JSON.parse. `driveToPostIntro` uses `socket.emitMessage` (existing pattern — plan called it `simulateMessage` but executor correctly used the actual harness method per documented executor-prompt allowance). All 5 specs run GREEN. |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|-------------|-------------|--------|----------|
| HOTFIX-02 | 84-01-noise-floor-cutoff-PLAN.md | Voice gate deadlock — agent intro plays, user speaks (transcribed), agent never replies | ✓ SATISFIED (SC1-3 automation) / ? PENDING (live UAT) | All 5 vitest specs GREEN; SC1 mechanism verified via Test 1, SC2 via Test 2, SC3 via Test 3, regression guard via Test 4, SC4-rejection guard-rail via Test 5. Live behavior verification is the manual UAT scope. |

**Note on REQUIREMENTS.md:** HOTFIX-02 is referenced in PLAN frontmatter and ROADMAP entry but is NOT recorded in `.planning/REQUIREMENTS.md`. This is a **pre-existing pattern** — HOTFIX-01 (Phase 83) is also absent from REQUIREMENTS.md. The researcher acknowledged this during planning; treating ROADMAP as the authoritative record per the verification prompt's explicit out-of-scope guidance. **Not flagged as a gap.**

**Orphaned requirements:** None. The single declared requirement (HOTFIX-02) maps cleanly to the single Phase 84 plan.

---

## SC4 Rejection Verification

The verification prompt requires SC4 rejection to be documented in 4 places. Confirmed:

1. **PLAN top section (`84-01-noise-floor-cutoff-PLAN.md`):** ✓ — `<sc4_rejection_summary>` block at L68-72; `<objective>` paragraph names SC4 as "EXPLICITLY REJECTED" (L45).
2. **must_haves truth #4 (PLAN frontmatter):** ✓ — Truth #4 at L20: "SC4 (multi-condition gate adding playbackQueueRef.length / pendingTurnDelayRef / lastRemoteActivityAtRef tail) is EXPLICITLY REJECTED per 84-RESEARCH.md §Q5 and a guard-rail test in this plan asserts the gate stays narrow."
3. **SUMMARY.md SC4 Rejection Rationale section:** ✓ — Dedicated section at L92-122 quotes `84-RESEARCH.md` §Q5 verbatim, names Test 5 as the guard-rail, justifies threshold choice.
4. **ROADMAP.md `**SC4 Status:**` line:** ✓ — Line 114 of `.planning/ROADMAP.md`: "**SC4 Status:** REJECTED during planning — see 84-RESEARCH.md §Q5. Root cause is server-side VAD not closing user turn; SC4 misdiagnoses the boundary. Plan implements a noise-floor RMS cutoff instead, satisfying SC1+SC2+SC3 without widening the gate."

**Plus a 5th anchor (bonus):** `.planning/STATE.md` Decisions section L172 records the rejection as a project-level decision.

**SC4 rejection is consistently documented across all required surfaces.**

---

## Anti-Patterns Scan

Files modified in Phase 84:
- `frontend/src/hooks/useVoiceSession.ts` (constant + RMS cutoff added)
- `frontend/__tests__/hooks/useVoiceSession.test.ts` (5 new tests + helpers)
- `.planning/STATE.md` (velocity + decisions)
- `.planning/ROADMAP.md` (Phase 84 entry updated)
- `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` (created)
- `.planning/phases/84-voice-gate-deadlock-fix/84-01-noise-floor-cutoff-SUMMARY.md` (created)

Anti-pattern detection on changed source: NONE.
- No TODO / FIXME / placeholder / coming-soon markers introduced.
- No empty implementations (`return null`, `return {}`, `=> {}`) introduced.
- No console.log-only handlers introduced.
- No mutation of the architectural invariant (`isPlayingRef.current && !remoteTurnCompleteRef.current` gate text appears EXACTLY once in the file, unchanged).

---

## Memo Invariant Preservation

| Invariant | Source | Status |
|-----------|--------|--------|
| Half-duplex gate text unchanged | Memo 2026-04-29 (post-86b0bc20) | ✓ PRESERVED — gate at L909 reads exactly `if (isPlayingRef.current && !remoteTurnCompleteRef.current) { return; }` |
| Test 5 guard-rail in suite | PLAN truth #4 + SUMMARY decisions | ✓ PRESENT — `keeps the half-duplex gate narrow (does not check queue/pending/tail)` at test file L587-650; runs GREEN in isolation and as part of the file. Implementation arranges multi-condition state (pendingTurnDelayRef set, queue has chunks, recent activity) with isPlayingRef false — proves the gate ignores those clauses. |
| Memory file `project_voice_brain_dump_architecture.md` NOT modified | PLAN scope discipline | ✓ PRESERVED — file mtime is 2026-04-29 18:40 (predates Phase 84 by ~24 hours). Memo amendment is documented as a deferred follow-up in SUMMARY.md L124-130. |
| Backend (`app/routers/voice_session.py`) NOT modified | PLAN scope discipline | ✓ PRESERVED — `git log` for that file shows last touch in commit `bd1ccd5d` (2026-04-30 PRE-Phase-84); Phase 84 commits `57ce02f5` and `4ffabbb7` did not touch it. |

---

## Test Execution Results

```
cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts

✓ __tests__/hooks/useVoiceSession.test.ts (9 tests) 3208ms
   ✓ unlocks mic capture as soon as the server sends waiting_for_input  (pre-existing)
   ✓ forwards user speech (RMS > floor) after intro onended fires       (Test 1 — SC1)
   ✓ drops sub-noise-floor chunks so server VAD can close the turn       (Test 2 — SC2)
   ✓ completes a 4-turn conversation cycle without permanent gating     (Test 3 — SC3)
   ✓ stale remote activity does not suppress mic during user speech     (Test 4 — regression guard)
   ✓ keeps the half-duplex gate narrow (does not check queue/pending/tail) (Test 5 — SC4 guard-rail)
   + 3 other pre-existing tests

Test Files  1 passed (1)
     Tests  9 passed (9)
  Duration  11.64s
```

Test 5 also re-run in isolation: 1 passed, 8 skipped (filter by name) — confirms the guard-rail is independently green.

---

## Goal-Backward Trace (binding = SC1-3)

If a user dropped into the brain-dump voice session today, the code path supports a 4-turn conversation as follows:

1. **Connect** → server emits `ready` → mic capture starts. Gate is OPEN (`isPlayingRef=false`, `remoteTurnComplete=true`).
2. **Server emits intro chunks** → `enqueueAudio` queues them, `pendingTurnDelayRef` schedules `playNextChunk` after 250ms → playback begins → `isPlayingRef=true` → gate CLOSED.
3. **Last intro chunk's `onended` fires** → queue drains → `isPlayingRef=false` → gate releases.
4. **Server emits `turn_complete`** → chains onto decode promise → `remoteTurnCompleteRef=true`. Gate now fully released.
5. **User speaks** → mic chunks arrive at `forwardInputChunk` → ws.readyState OK → narrow gate passes (isPlayingRef=false) → **NEW: RMS check** → speech RMS (~0.05) >> floor (0.003) → chunk encoded and forwarded. **(SC1 satisfied)**
6. **User pauses** → mic worklet keeps emitting Float32 blocks containing only ambient/AEC residue → blocks compute RMS (~0.001 typical) < 0.003 → **dropped before float32ToPcm16**. Server sees actual silence on the wire.
7. **After ~700ms of clean silence**, Gemini Live's server-side `automatic_activity_detection` closes the user's turn → emits `model_turn` → audio response chunks flow back to client. **(SC2 satisfied — within ~1s of pause)**
8. **Cycle repeats** for turns 2-4. Test 3 proves the gate cycles cleanly across 4 iterations. **(SC3 satisfied — automation; live latency requires UAT case 1.)**

The trace is internally consistent. The only step not exercised by automated tests is step 7's actual server-side VAD closure on real audio — that is precisely what manual UAT cases 1+2 and the production-log assertion (case 5) verify.

---

## Why `human_needed` (not `passed`)

All four must-haves are automation-verified. Every SC4-rejection documentation surface is in place. The narrow-gate invariant is preserved. The mechanism that satisfies SC1-3 (sub-floor RMS chunks dropped) is locked into the test suite.

**However, SC1-3 are statements about live Gemini Live behavior:**
- SC1's "audio reaches the server" final proof is `input_transcription` in production logs.
- SC2's "model produces audio response within ~1s" is a real-time latency claim.
- SC3's "≥4-turn conversation completes end-to-end" requires real WebAudio + AEC + server VAD.

The vitest specs prove the **mechanism** (cutoff drops sub-floor, gate stays narrow, gate releases on cycle) but cannot exercise Gemini Live's actual silence-detection against real microphone audio in a jsdom environment. Per the verification prompt and `84-VALIDATION.md` § "Manual-Only Verifications", these must be validated against a deployed environment.

**Manual UAT (`84-MANUAL-UAT.md`) is required before the phase can be closed.** The 5 cases are listed in the `human_verification` frontmatter above and are unchanged from `84-MANUAL-UAT.md`.

---

## Out-of-Scope Items (NOT counted as gaps)

Per the verification prompt's explicit guidance:
- **HOTFIX-02 absent from `.planning/REQUIREMENTS.md`** — pre-existing pattern; HOTFIX-01 also absent. Researcher-acknowledged.
- **Manual UAT not yet completed** — that is the `human_needed` work, not a gap.
- **Repo-wide lint failures in unrelated files** (services/initiatives.ts, services/workflows.ts, remotion scenes) — confirmed pre-existing during Phase 83 verification; the executor logged 161 errors / 134 warnings as out-of-scope in SUMMARY.md L150.
- **Memory amendment deferred** — explicitly flagged as a follow-up in SUMMARY.md L124-130, not a gap.
- **50+ pre-existing test failures in unrelated files** — confirmed pre-existing during Phase 83.

---

## Gaps Summary

**No automated gaps.** All 4 must-haves verified, all 5 vitest specs GREEN, narrow-gate invariant preserved verbatim, SC4 rejection documented in all 4 (5 with STATE.md) required surfaces, memory file untouched, backend untouched, no anti-patterns introduced.

The phase is mechanically complete and architecturally clean. Live verification (5 manual UAT cases in `84-MANUAL-UAT.md`) is the remaining gate.

---

*Verified: 2026-04-30T23:10:00Z*
*Verifier: Claude (gsd-verifier, Opus 4.7 1M)*
