---
phase: 83
slug: document-upload-bypass
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 83 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: `83-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.0.18 (jsdom) + @testing-library/react |
| **Config file** | `frontend/vitest.config.mts` |
| **Quick run command** | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx` |
| **Full suite command** | `cd frontend && npm test` |
| **Estimated runtime** | ~2–5s quick · ~60s full suite |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx`
- **After every plan wave:** Run `cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite green + manual UAT (4 file types) complete
- **Max feedback latency:** ~5 seconds for the focused file run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 83-01-01 | 01 | 0 | HOTFIX-01 (infra) | harness | `cd frontend && npx vitest run src/components/chat/__test-utils__/chatHarness.test.tsx` | ❌ W0 | ⬜ pending |
| 83-01-02 | 01 | 1 | HOTFIX-01.1 | unit (component) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "drop attaches without smart"` | ✅ extend | ⬜ pending |
| 83-01-03 | 01 | 1 | HOTFIX-01.1 | unit (component) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "no detecting content type indicator"` | ✅ extend | ⬜ pending |
| 83-01-04 | 01 | 1 | HOTFIX-01.2 | unit (component) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "send delivers extracted content inline"` | ✅ extend | ⬜ pending |
| 83-01-05 | 01 | 1 | HOTFIX-01.3 | unit (component) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "upload failure renders single system message"` | ✅ extend | ⬜ pending |
| 83-01-06 | 01 | 1 | HOTFIX-01.4 | unit (component) | `cd frontend && npx vitest run src/components/chat/ChatInterface.test.tsx -t "drop does not fetch smart endpoint"` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/components/chat/__test-utils__/chatHarness.ts` — `renderChatInterface(opts)` helper that pre-mocks every hook used at module scope (`useAgentChat`, `useFileUpload`, `usePresence`, `useRealtimeSession`, `useSessionControl`, `useSessionMap`, `useTextToSpeech`, `useSpeechRecognition`, `useVoiceSession`, `usePersona`, plus `supabase/client.createClient`). Required so component-level drop tests can render the full tree without stubbing each hook per test.
- [ ] (Optional) `frontend/src/components/chat/__test-utils__/chatHarness.test.tsx` — minimal smoke test that the harness renders without throwing.

*No framework install needed — Vitest, jsdom, and @testing-library/react already in `frontend/package.json`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drop a real PDF, DOCX, XLSX, and image into chat; pill within ~1s; send; agent reply | HOTFIX-01 (all 4 success criteria) | Real file extraction in backend, real agent SSE response, real-time UI feel ("within 1s") cannot be assessed via jsdom timers alone | (1) `make local-backend` + `cd frontend && npm run dev`. (2) Open chat. (3) Drag-and-drop each of: a small PDF, a DOCX, an XLSX, a JPG/PNG. Confirm: pill renders ≤1s, no "Detecting content type" toast, no spinner. (4) Type a prompt referencing the file and press send. Confirm: agent reply mentions file content (or for image, acknowledges placeholder). (5) Force a backend `/upload` failure (e.g. stop backend, drop file, send) and confirm a single system message appears, no infinite spinner, input becomes usable again. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (chatHarness.ts)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s for quick run
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner & checker confirm coverage)

**Approval:** pending
