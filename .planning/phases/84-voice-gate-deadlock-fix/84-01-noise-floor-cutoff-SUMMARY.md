---
phase: 84-voice-gate-deadlock-fix
plan: 01
subsystem: voice
tags: [voice, gemini-live, vad, websocket, audio, rms, noise-floor, hotfix]

# Dependency graph
requires:
  - phase: 84-voice-gate-deadlock-fix
    provides: 84-RESEARCH.md (HIGH-confidence root-cause trace) + 84-VALIDATION.md (per-task verify map)
provides:
  - "Client-side noise-floor RMS cutoff inside forwardInputChunk so Gemini Live server-side VAD can close user turns on pauses (default 0.003 RMS, env-overridable)"
  - "5 vitest specs locking SC1/SC2/SC3 contracts plus a regression guard and an SC4-rejection guard-rail"
  - "Manual UAT checklist (84-MANUAL-UAT.md) for post-deploy verification of quiet/noisy/mid-utterance/whisper cases plus production-log alternation pattern"
  - "Documented architectural rejection of SC4 (multi-condition gate widening) with rationale chained to the prior mid-utterance re-latch regression fixed by 86b0bc20"
affects: [85-render-sse-timeout, 86-document-generation-skills-exposure, voice-architecture-memo]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RMS energy cutoff as a noise FLOOR (not local VAD) — additive filter on chunk content placed AFTER the half-duplex session-state gate, BEFORE encode/transmit"
    - "Env-overridable runtime constant via process.env with safe parse (Number.isFinite + > 0 fallback)"
    - "TDD plan: 5 specs in nested describe; helper-driven post-intro state setup (driveToPostIntro) reused across cases"
    - "SC4-rejection guard-rail test: arranges multi-condition state where SC4 verbatim would close the gate but isPlayingRef === false, then asserts user speech passes — fails CI if anyone widens the gate later"

key-files:
  created:
    - .planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md
    - .planning/phases/84-voice-gate-deadlock-fix/84-01-noise-floor-cutoff-SUMMARY.md
  modified:
    - frontend/src/hooks/useVoiceSession.ts
    - frontend/__tests__/hooks/useVoiceSession.test.ts
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "REJECTED SC4 (multi-condition gate widening) — root cause is server-side VAD not closing user turn, not a client-side gate deadlock. SC4 addresses agent→user boundary; deadlock is at user→agent boundary."
  - "Implemented noise-floor RMS cutoff (0.003 default) as a SEPARATE filter AFTER the half-duplex gate, NOT as a gate modification — preserves the load-bearing narrow-gate invariant"
  - "Threshold 0.003 RMS chosen to leave ~10x margin above whispered voiced segments (~0.005) while sitting above electronic noise floor and AEC residue; runtime override via NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS"

patterns-established:
  - "Noise-floor cutoff as architectural exception to 'no local VAD' rule: a noise floor that drops sub-speech-energy chunks is admissible because it is NOT speech detection; threshold is far below any voiced segment"
  - "Plan-level guard-rail tests for explicitly-rejected design alternatives — Test 5 fails CI if a future PR widens the half-duplex gate per SC4 verbatim"

requirements-completed:
  - HOTFIX-02

# Metrics
duration: 7 min
completed: 2026-04-30
---

# Phase 84 Plan 01: Voice Gate Deadlock Noise-Floor Cutoff Summary

**Added a 21-line client-side RMS noise-floor cutoff to `useVoiceSession.forwardInputChunk` (constant + comment + 6-line check) that drops sub-speech-energy mic chunks before transmit, so Gemini Live's server-side automatic activity detection can finally observe `silence_duration_ms=700` of clean silence after the user pauses and trigger the model turn — fixing the brain-dump voice deadlock without widening the half-duplex gate.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-30T19:52:15Z
- **Completed:** 2026-04-30T19:59:37Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 4 (2 source + STATE + ROADMAP)
- **Files created:** 2 (84-MANUAL-UAT.md + this SUMMARY.md)

## Accomplishments

- Identified, documented, and rejected SC4 (multi-condition gate widening) as a misdiagnosis — preserving the narrow-gate invariant that fixes mid-utterance suppression (commit 86b0bc20).
- Implemented the smallest correct fix (~21 LOC) per `84-RESEARCH.md` § Recommended Fix Shape: a noise-floor RMS cutoff that gives the server clean silence at user pauses without modifying the half-duplex gate.
- Added 5 vitest specs to `useVoiceSession.test.ts` covering SC1, SC2, SC3, the prior mid-utterance regression, and an SC4-rejection guard-rail.
- All 9 tests in the file pass (5 new + 4 pre-existing). Sub-floor (0.001 RMS) chunks correctly drop; speech-energy (0.05 RMS) chunks pass; the gate stays narrow.
- Authored `84-MANUAL-UAT.md` so QA can verify the fix end-to-end on real Gemini Live (quiet 4-turn, noisy 4-turn, mid-utterance non-suppression, whisper, production-log alternation pattern).

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): 5 failing specs + manual UAT checklist** — `57ce02f5` (test)
2. **Task 2 (GREEN): noise-floor cutoff implementation** — `4ffabbb7` (fix)

**Plan metadata:** _committed by orchestrator after this SUMMARY lands._

## Files Created/Modified

- `frontend/src/hooks/useVoiceSession.ts` — Added `VOICE_NOISE_FLOOR_RMS` module-scope constant (env-overridable, default 0.003) immediately after `REMOTE_TURN_ACTIVITY_TAIL_MS`. Inserted a 14-line RMS check (block comment + sumSq loop + sqrt + threshold compare + early return) inside `forwardInputChunk`, positioned IMMEDIATELY AFTER the existing half-duplex gate and IMMEDIATELY BEFORE the `float32ToPcm16` call. The gate text itself is **unchanged**.
- `frontend/__tests__/hooks/useVoiceSession.test.ts` — Added a nested `describe('noise-floor cutoff (HOTFIX-02)')` block with 5 specs and two helpers (`makeFloat32ChunkAtRMS`, `driveToPostIntro`) plus a `pushChunk`/`audioSendCount` pair for assertion ergonomics.
- `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` — Created. 5-row manual checklist mirroring `84-VALIDATION.md` § Manual-Only Verifications.
- `.planning/STATE.md` — Velocity table appended; SC4-rejection decision recorded; advance-plan + record-metric run.
- `.planning/ROADMAP.md` — Phase 84 plans block updated to `1/1 plans complete`; plan checkbox flipped.

## SC4 Rejection Rationale

**This is a documented quality-gate requirement of this plan. Read this section before requesting an SC4-style fix in any future PR.**

The Phase 84 ROADMAP success criterion 4 (SC4) reads:

> The mic gate is restored to multi-condition logic: suppress only while `isPlayingRef || playbackQueueRef.length > 0 || pendingTurnDelayRef || (recent remote activity within tail window)`.

`84-RESEARCH.md` §Q5 traces precisely why SC4 verbatim would NOT fix HOTFIX-02 and would re-introduce a regression:

> SC4 proposes: suppress mic while `isPlayingRef || playbackQueueRef.length > 0 || pendingTurnDelayRef || (recent remote activity within tail window)`.
>
> Each clause widens the gate at the **agent-side boundary** (during/just after agent speech). They give the server MORE clean silence during agent playback — but the server **already** has that silence, because the existing narrow gate `isPlayingRef && !remoteTurnComplete` keeps the mic muted throughout the agent's playback.
>
> **SC4 does NOT widen the gate at the user-side boundary** (after the user speaks and pauses). At that point:
> - `isPlayingRef = false` (no chunks in flight)
> - `playbackQueueRef.length = 0` (nothing queued)
> - `pendingTurnDelayRef = null` (no pending delay)
> - `lastRemoteActivityAtRef` is far in the past (650ms tail expired long ago)
>
> All four SC4 clauses evaluate to false. **The gate is still open.** The mic still forwards ambient noise. The server VAD still never sees silence. Bug unchanged.
>
> **Worse,** the architectural memo (2026-04-29) documents that the wider gate had a DIFFERENT bug — the `recent remote activity within tail window` clause re-latched mid-user-utterance, suppressing the user when a stray late-arriving server activity event fired during user speech. SC4 verbatim re-introduces that exact regression while not fixing the actual deadlock.
>
> **SC4 is a misdiagnosis.** It addresses agent→user handoff timing, but the bug is user-pause→model-trigger turn closure.

This plan therefore satisfies SC1, SC2, and SC3 via a different mechanism — a noise-floor RMS cutoff that drops sub-speech-energy chunks before transmit. The half-duplex gate stays narrow and unchanged.

**Test 5 (`keeps the half-duplex gate narrow (does not check queue/pending/tail)`) is a guard-rail.** It fails CI if a future PR widens the gate per SC4 verbatim — surfacing the architectural disagreement explicitly. Do not delete it.

**Threshold choice:** 0.003 RMS is below any voiced human speech (whispered voiced segments ~0.005, conversational ~0.03+, three orders of magnitude above the floor) but above electronic noise floor, HVAC hum, and AEC residue. Tunable via `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS` env. If production users with very high mic gain still surface deadlocks, raise the threshold (try 0.005 first); if whisper transcription degrades, lower it (try 0.001-0.002).

## Memory-Update Breadcrumb (deferred follow-up)

The memory file `~/.claude/projects/C--Users-expert-documents-pka-pikar-ai/memory/project_voice_brain_dump_architecture.md` currently asserts a "no local VAD" invariant (intentionally — the previous removed local-VAD at threshold 0.0012 attempted to gate speech START, which is the prohibited pattern). The noise-floor cutoff is a different beast: it does NOT detect speech start/end; it only zeros out chunks mathematically indistinguishable from silence. The memo needs a small amendment clarifying:

> "No local VAD" still holds — the client never decides "this is speech" vs. "this is silence." A noise-FLOOR cutoff at 0.003 RMS (below any voiced segment, including quiet whispers) IS admissible: it drops sub-speech-energy ambient/AEC residue so server-side VAD can do its job. Threshold is env-overridable via `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS`.

**The memo amendment itself is OUT OF SCOPE for this plan** (per the plan's own scope discipline: bundling a memory-file edit here would violate per-plan boundaries). Flag it as a follow-up for the next voice-architecture-touching session.

## Decisions Made

- **REJECTED SC4 (multi-condition gate widening).** Misdiagnosis: SC4 widens at agent→user boundary; deadlock is at user→agent boundary. Verbatim SC4 also re-introduces the mid-utterance re-latch bug fixed by 86b0bc20.
- **Implemented noise-floor cutoff (option A from 84-RESEARCH.md).** ~21 LOC: 1 module-scope constant + block comment + 6-line RMS check inserted AFTER the existing gate and BEFORE float32ToPcm16. Half-duplex gate text unchanged.
- **Threshold = 0.003 RMS, env-overridable via `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS`.** Margin above whisper-voiced (~0.005), well below conversational (~0.03+), above electronic noise floor.
- **Test 5 kept as guard-rail** even after GREEN — fails CI if a future PR widens the gate. NOT to be deleted.
- **Memory-file amendment deferred to a follow-up** to preserve scope discipline.

## Deviations from Plan

None - plan executed exactly as written.

The plan's `<interfaces>` block referenced a `simulateMessage(data)` helper, but the existing test harness uses `emitMessage(payload)` (which JSON-stringifies the payload). The plan's `<known_risks>` block in the executor prompt explicitly flagged this exact discrepancy — used the existing pattern as instructed. Not a true deviation since the prompt anticipated the mismatch.

## Issues Encountered

None. RED phase produced exactly the expected single failure (Test 2: sub-floor chunk forwarded). GREEN phase turned all 5 new specs green on the first run. Lint scoped to touched files surfaces only pre-existing warnings (`_stream` underscore-prefix and the `cleanupResources` exhaustive-deps warning) that predate this plan.

The repo-wide `npm run lint` reports 161 errors / 134 warnings — these are all in unrelated files (`services/initiatives.ts`, `services/workflows.ts`, `services/widgetDisplay.ts`, `remotion/OAuthDemo/scenes/*`). Per scope-boundary rule, those are pre-existing and out of scope for this hotfix; logged for awareness only.

## User Setup Required

None - no external service configuration required. Optional env override `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS` is documented in the source comment but not required for the default behavior.

## Next Phase Readiness

**Phase 85 (Render SSE Timeout) is unblocked.** Phase 84 hotfix landed; SC1+SC2+SC3 are satisfied programmatically by the 5-spec test suite, and `84-MANUAL-UAT.md` is the post-deploy verification gate. The narrow-gate invariant remains intact; the SC4-rejection guard-rail (Test 5) protects future PRs from accidentally widening it.

**Open follow-ups (not blockers for Phase 85):**
1. Memory-file amendment (`project_voice_brain_dump_architecture.md`) clarifying the "no local VAD" rule has a noise-floor exception — handle in next voice-architecture-touching session.
2. If post-deploy production logs still show `input_transcription` × N with no `model_turn`, escalate to fallback (B) `audio_stream_end` per-utterance from client OR tune `silence_duration_ms` server-side. Both are documented in `84-RESEARCH.md` § Recommended Fix Shape.
3. Manual UAT (5 cases in `84-MANUAL-UAT.md`) must pass before `/gsd:verify-work 84` can close the phase.

## Self-Check: PASSED

- `frontend/src/hooks/useVoiceSession.ts` — FOUND (modified)
- `frontend/__tests__/hooks/useVoiceSession.test.ts` — FOUND (modified)
- `.planning/phases/84-voice-gate-deadlock-fix/84-MANUAL-UAT.md` — FOUND (created)
- `.planning/phases/84-voice-gate-deadlock-fix/84-01-noise-floor-cutoff-SUMMARY.md` — FOUND (this file)
- Commit `57ce02f5` (test RED) — FOUND in `git log`
- Commit `4ffabbb7` (fix GREEN) — FOUND in `git log`
- Half-duplex gate at useVoiceSession.ts L909 — verified via grep, text remains EXACTLY `if (isPlayingRef.current && !remoteTurnCompleteRef.current)`
- Memory file `project_voice_brain_dump_architecture.md` — NOT modified (per scope discipline)
- Vitest run on touched file — 9/9 PASSED (5 new + 4 pre-existing)

---
*Phase: 84-voice-gate-deadlock-fix*
*Completed: 2026-04-30*
