# Phase 84 — Manual UAT Checklist

**Source of truth for sampling discipline:** `84-VALIDATION.md` § Manual-Only Verifications.
**Why manual:** These verifications require real Gemini Live, real WebAudio, real microphone, and real VAD timing — none of which can be exercised in vitest. Run these post-deploy, before closing the milestone. They are NOT a CI gate.

**Pre-flight:** `make local-backend` + `cd frontend && npm run dev`. Open the brain-dump voice overlay. Click voice. Wait for the agent's intro greeting to finish.

---

## Required UAT Cases

- [ ] **Quiet 4-turn conversation** — `HOTFIX-02 SC1+SC2+SC3`
  In a quiet room, complete a 4-turn brain-dump conversation. Each agent reply must come within **~1.5s** of the user pause. Confirm 4 alternating turns with no stuck silence, no missed user words, no permanent mic gating.

- [ ] **Noisy 4-turn conversation** — `HOTFIX-02 SC2 robustness`
  In a noisy room (TV in background, fan running), complete a 4-turn conversation. Each agent reply must come within **~2s** of the user pause. If a reply NEVER comes, the noise-floor threshold is too low — increase via `NEXT_PUBLIC_VOICE_NOISE_FLOOR_RMS` (default `0.003`; try `0.005` or `0.007` next).

- [ ] **Mid-utterance non-suppression (regression guard)** — `Memo regression guard`
  Speak continuously for **8+ seconds without pausing**. Confirm the mic is NEVER cut off mid-word and no middle words are dropped from the transcript. (If SC4 had been implemented as a wider gate, this case would fail — that's the regression we are guarding against.)

- [ ] **Whisper test** — `Threshold not too high`
  Complete one turn whispering at low volume. Confirm the whisper is transcribed and gets a reply. The 0.003 RMS floor leaves margin above whispered voiced segments (~0.005 RMS); if QA finds whisper transcription degrades, lower the threshold to `0.001`–`0.002` via the env override.

- [ ] **Production-log assertion** — `HOTFIX-02 in production`
  After deploy, in Cloud Run logs filter by one `session_id`. Confirm the alternating pattern:
  ```
  input_transcription (user) → turn_complete (server closes user turn)
    → model_turn (agent) → turn_complete (agent done)
    → input_transcription (user) → ...
  ```
  Pre-fix pattern (broken): `input_transcription` × N with **no** intervening `model_turn`. If you still see this pattern after deploy, the fix is incomplete — escalate to fallback (B) `audio_stream_end` from client OR tune `silence_duration_ms` server-side, per `84-RESEARCH.md` § Recommended Fix Shape.

---

## Sign-Off

- **QA tester:** _______
- **Date:** _______
- **Build / commit hash:** _______
- **All 5 cases passed:** ☐ yes ☐ no
- **Notes / failures:** _______

When all 5 boxes are ticked, paste this completed checklist into the Phase 84 verification record before running `/gsd:verify-work 84`.
