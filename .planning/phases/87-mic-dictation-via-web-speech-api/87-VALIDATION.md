---
phase: 87
slug: mic-dictation-via-web-speech-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-01
boundary_protection: brain_dump_voice_untouched
boundary_rationale: "SC5 explicitly excludes useVoiceSession.ts and app/routers/voice_session.py. Researcher grep-verified zero cross-imports between useSpeechRecognition (chat input) and useVoiceSession (brain-dump WebSocket session)."
---

# Phase 87 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: `87-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.0.18 + @testing-library/react 16.3.2 (jsdom 27.4.0) |
| **Config file** | `frontend/vitest.config.mts` |
| **Quick run command** | `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts src/components/chat/ChatInterface.test.tsx __tests__/hooks/useVoiceSession.test.ts` |
| **Full suite command** | `cd frontend && npm test` |
| **Estimated runtime** | ~8s focused · ~60–90s full suite |

---

## Sampling Rate

- **After every task commit:** Run focused command above (includes useSpeechRecognition + ChatInterface + brain-dump regression in one go)
- **After every plan wave:** `cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite green + manual UAT across Chrome/Edge/Safari/Firefox/iOS Safari + brain-dump boundary smoke
- **Max feedback latency:** ~10 seconds for the focused run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 87-01-01 | 01 | 0 | Hook unit (full coverage) | unit | `cd frontend && npx vitest run __tests__/hooks/useSpeechRecognition.test.ts` | ❌ W0 | ⬜ pending |
| 87-02-01 | 02 | 1 | HOTFIX-05 SC1 | component | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "mic button toggles recognition"` | ✅ extend | ⬜ pending |
| 87-02-02 | 02 | 1 | HOTFIX-05 SC2 | component | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "interim transcript appears in input"` | ✅ extend | ⬜ pending |
| 87-02-03 | 02 | 1 | HOTFIX-05 SC3 | component | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "user can edit dictated text"` | ✅ extend | ⬜ pending |
| 87-02-04 | 02 | 1 | HOTFIX-05 SC4 | component | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "unsupported browser shows fallback"` | ✅ extend | ⬜ pending |
| 87-02-05 | 02 | 1 | HOTFIX-05 SC5 (boundary guard-rail) | component | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "chat mic does not call useVoiceSession"` | ✅ extend | ⬜ pending |
| 87-02-06 | 02 | 1 | HOTFIX-05 SC5 (regression) | unit | `cd frontend && npx vitest run __tests__/hooks/useVoiceSession.test.ts` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Note:** Test 5 (`chat mic does not call useVoiceSession`) is a **guard-rail**. It asserts the chat input mic button never invokes any `useVoiceSession` symbol — fails CI if anyone ever wires the two paths together. Keep it permanently. Test 6 is the existing brain-dump suite (Phase 84) which must remain GREEN unchanged.

---

## Wave 0 Requirements

- [ ] `frontend/__tests__/hooks/useSpeechRecognition.test.ts` — NEW unit test file. Mock `window.SpeechRecognition` with a fake constructor exposing `start`, `stop`, `abort`, and methods to fire `onresult`/`onerror`/`onend` callbacks. Tests: start emits `isRecording=true`; results append; stop flushes interim; permission-denied error path; unsupported-browser path (when `window.SpeechRecognition` is undefined).
- [ ] `npm install -D @types/dom-speech-recognition` — TypeScript typings for the SpeechRecognition API.

*No framework install — Vitest 4 + jsdom + @testing-library/react already configured.*

---

## Manual-Only Verifications

> jsdom does NOT implement `SpeechRecognition`. Real-browser UAT is mandatory.

| Browser | UAT Steps | Pass Criteria |
|---------|-----------|---------------|
| Chrome desktop | Open `/dashboard/chat`, click mic, say "Hello world this is a test", pause | Words appear in input live; input remains editable; clicking send delivers the message |
| Edge desktop | Same | Same (Chromium-based, expected identical to Chrome) |
| Safari macOS 17+ | Same | Words appear (with possible 200–500ms delay vs Chrome) |
| Firefox desktop | Click mic | Mic disabled with "Voice input not supported in this browser" tooltip; no error toast |
| iOS Safari 14.5+ | Same as Chrome | Words appear (user-gesture from click-to-start covers permission requirement) |
| **Boundary smoke** | Click brain-dump (Brain icon), confirm voice session connects, agent greets, user can speak, ≥4-turn conversation | **Phase 84 behavior unchanged** — brain-dump path completely untouched. If brain-dump regresses, escalate; chat-input mic changes must NOT affect this |

Log results to `87-MANUAL-UAT.md` (created during execution).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`useSpeechRecognition.test.ts` + types install)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s for focused run
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner & checker confirm coverage)
- [ ] Manual UAT executed across all 5 browsers + boundary smoke logged
- [ ] Brain-dump regression suite (`useVoiceSession.test.ts`) GREEN throughout
- [ ] `useVoiceSession.ts` and `app/routers/voice_session.py` UNCHANGED post-execution (verifiable via `git diff HEAD -- frontend/src/hooks/useVoiceSession.ts app/routers/voice_session.py`)

**Approval:** pending
