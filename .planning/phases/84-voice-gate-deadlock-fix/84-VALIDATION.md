---
phase: 84
slug: voice-gate-deadlock-fix
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-30
sc4_status: rejected
sc4_rejection_reason: "Research traced root cause to server-side VAD not closing user turn on ambient noise. SC4's wider gate addresses agent→user boundary; bug is at user→agent boundary. SC4 verbatim would re-introduce the mid-utterance re-latch bug fixed by commit 86b0bc20 on 2026-04-29."
---

# Phase 84 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: `84-RESEARCH.md` § Validation Architecture.
> **Note:** SC4 is intentionally NOT implemented. SC1–SC3 are the binding success criteria. See research § "Why we recommend rejecting SC4".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (frontend) + Pytest (backend, for completeness — backend untouched in this phase) |
| **Config file** | `frontend/vitest.config.mts` |
| **Quick run command** | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~3–5s quick · ~60–90s full suite |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts`
- **After every plan wave:** Run `make test`
- **Before `/gsd:verify-work`:** Full suite green + manual UAT (4-turn live session) + production-log spot-check
- **Max feedback latency:** ~5 seconds for the focused file run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 84-01-01 | 01 | 0 | HOTFIX-02 SC1 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "forwards user speech .* after intro onended"` | ✅ extend | ⬜ pending |
| 84-01-02 | 01 | 0 | HOTFIX-02 SC2 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "drops sub-noise-floor chunks"` | ✅ extend | ⬜ pending |
| 84-01-03 | 01 | 0 | HOTFIX-02 SC3 | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "completes a 4-turn conversation cycle"` | ✅ extend | ⬜ pending |
| 84-01-04 | 01 | 0 | HOTFIX-02 regression | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "stale remote activity does not suppress mic"` | ✅ extend | ⬜ pending |
| 84-01-05 | 01 | 0 | SC4 explicitly rejected | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts -t "keeps the half-duplex gate narrow"` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Note:** Test 5 is a guard-rail. If a future PR widens the gate (SC4 verbatim), this test fails and surfaces the architectural disagreement explicitly. Keep it.

---

## Wave 0 Requirements

*No new infrastructure needed.* `useVoiceSession.test.ts` already exists at `frontend/__tests__/hooks/useVoiceSession.test.ts` with WS / AudioContext mocks. Extend it with the 5 new specs from research § Validation Architecture.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 4-turn conversation in quiet room | HOTFIX-02 SC1+SC2+SC3 | Real Gemini Live, real WebAudio, real microphone, real VAD timing | (1) `make local-backend` + `cd frontend && npm run dev`. (2) Open brain-dump, click voice. (3) Wait for intro greeting. (4) Speak. Pause. Confirm agent replies within ~1.5s. (5) Repeat 3 more times. Confirm 4 alternating turns with no stuck silence. |
| 4-turn conversation in noisy room | HOTFIX-02 SC2 robustness | Validate noise-floor threshold against real ambient noise | Same as above but with TV/fan background. Each reply within ~2s of pause. If reply NEVER comes, threshold may be too low — increase `VOICE_NOISE_FLOOR_RMS` env (default 0.003). |
| Mid-utterance non-suppression | Memo regression guard | Validates the prior mid-utterance bug stays fixed | Speak continuously for 8+ seconds without pausing. Confirm mic is NEVER cut off mid-word. (If SC4 had been implemented, this would fail.) |
| Whisper test | Threshold not too high | Validates 0.003 floor doesn't suppress quiet speech | Complete one turn whispering at low volume. Confirm it transcribes and gets a reply. |
| Production-log assertion | HOTFIX-02 in production | Cloud Run telemetry confirms server VAD closes turns | After deploy, filter Cloud Run logs by one session_id. Confirm pattern: `input_transcription` (user) → `turn_complete` (server closes turn) → `model_turn` (agent) → `turn_complete` (agent done) → repeat. Pre-fix pattern (broken): `input_transcription` × N with no `model_turn` between. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (none — existing test file extended)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s for quick run
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner & checker confirm coverage)
- [ ] Production-log pattern verified post-deploy

**Approval:** pending
