---
phase: 17
slug: creative-questioning
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-21
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest 4.0.18 (frontend) |
| **Config file** | `pytest.ini` (backend), `frontend/scripts/run-vitest.mjs` (frontend) |
| **Quick run command** | `uv run pytest tests/unit/app_builder/ -x` |
| **Full suite command** | `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app_builder/ -x`
- **After every plan wave:** Run `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | FLOW-01 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py -x` | W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | FLOW-01 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py -x` | W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | BLDR-04 | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/GsdProgressBar.test.tsx` | W0 | ⬜ pending |
| 17-02-02 | 02 | 2 | FLOW-01, BLDR-04 | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/QuestioningWizard.test.tsx` | W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/app_builder/test_app_builder_router.py` — covers FLOW-01 (router unit tests with mocked Supabase client)
- [ ] `frontend/src/__tests__/components/GsdProgressBar.test.tsx` — covers BLDR-04 (stage rendering, active highlight)
- [ ] `frontend/src/__tests__/components/QuestioningWizard.test.tsx` — covers FLOW-01 wizard step logic

*Existing pytest + vitest infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Choice cards render visually with correct styling | FLOW-01 | Visual design quality | Open /app-builder/new, verify cards are styled, clickable, and responsive |
| Progress bar stage transitions animate smoothly | BLDR-04 | Animation quality | Complete questioning flow, verify progress bar updates with visual feedback |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
