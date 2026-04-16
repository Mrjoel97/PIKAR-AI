---
phase: 54
slug: onboarding-ux-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + vitest + TypeScript |
| **Config file** | `pyproject.toml`, `frontend/vitest.config.mts`, `frontend/tsconfig.json` |
| **Quick run command** | `uv run pytest tests/unit/app/test_google_workspace_auth_service.py -x && cd frontend && npm run test -- src/__tests__/services/onboarding-launch.test.ts src/__tests__/services/google-workspace-status.test.ts src/__tests__/dashboard/empty-states.test.tsx` |
| **Full suite command** | `uv run pytest tests/unit/app/test_google_workspace_auth_service.py -x && cd frontend && npm run test -- src/__tests__/services/onboarding-launch.test.ts src/__tests__/services/google-workspace-status.test.ts src/__tests__/dashboard/empty-states.test.tsx && npx tsc -p . --noEmit` |
| **Estimated runtime** | ~55 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app/test_google_workspace_auth_service.py -x`
- **After every plan wave:** Run `cd frontend && npm run test -- src/__tests__/services/onboarding-launch.test.ts src/__tests__/services/google-workspace-status.test.ts src/__tests__/dashboard/empty-states.test.tsx`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 55 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 1 | UX-01 | unit | `cd frontend && npm run test -- src/__tests__/services/onboarding-launch.test.ts -t "builds chat-enabled launch urls"` | ❌ W0 | ⬜ pending |
| 54-01-02 | 01 | 1 | UX-01 | unit | `cd frontend && npm run test -- src/__tests__/services/onboarding-launch.test.ts -t "reads initialPrompt once"` | ❌ W0 | ⬜ pending |
| 54-02-01 | 02 | 1 | UX-02 | unit | `uv run pytest tests/unit/app/test_google_workspace_auth_service.py::test_sync_google_workspace_tokens_persists_credentials -x` | ❌ W0 | ⬜ pending |
| 54-02-02 | 02 | 1 | UX-02 | unit | `uv run pytest tests/unit/app/test_google_workspace_auth_service.py::test_status_requires_usable_google_workspace_credentials -x` | ❌ W0 | ⬜ pending |
| 54-02-03 | 02 | 1 | UX-02 | unit | `cd frontend && npm run test -- src/__tests__/services/google-workspace-status.test.ts` | ❌ W0 | ⬜ pending |
| 54-03-01 | 03 | 2 | UX-03 | component | `cd frontend && npm run test -- src/__tests__/dashboard/empty-states.test.tsx` | ❌ W0 | ⬜ pending |
| 54-03-02 | 03 | 2 | UX-03 | typecheck | `cd frontend && npx tsc -p . --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/app/test_google_workspace_auth_service.py` — backend Google Workspace sync/status coverage
- [ ] `frontend/src/__tests__/services/onboarding-launch.test.ts` — onboarding prompt handoff coverage
- [ ] `frontend/src/__tests__/services/google-workspace-status.test.ts` — frontend Google Workspace status/reconnect coverage
- [ ] `frontend/src/__tests__/dashboard/empty-states.test.tsx` — representative zero-data dashboard coverage

*Existing pytest, Vitest, and TypeScript infrastructure already exist. No framework installation work is required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A brand-new user completes onboarding and their selected first action becomes the first live chat message | UX-01 | Requires a real browser flow across auth, onboarding, routing, and chat startup | Sign up with a fresh account, complete conversational onboarding, choose a first action, confirm the app lands on a chat-enabled surface and the selected prompt is sent exactly once |
| Google OAuth survives the callback and a later Gmail/Calendar action works after navigation or refresh | UX-02 | Requires real Supabase OAuth + Google consent + token persistence behavior | Sign in with Google, visit the integrations/configuration surface, confirm connected status, refresh/navigate, then trigger a calendar or Gmail-backed action and confirm it works without reconnecting |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 55s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
