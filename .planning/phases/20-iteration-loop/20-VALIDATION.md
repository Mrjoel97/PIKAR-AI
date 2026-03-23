---
phase: 20
slug: iteration-loop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.4.2 |
| **Framework (frontend)** | vitest |
| **Backend config** | `pyproject.toml` |
| **Frontend config** | `frontend/vitest.config.*` |
| **Quick run command** | `uv run pytest tests/unit/app_builder/test_iteration_service.py -x -v` |
| **Full suite command** | `uv run pytest tests/unit/app_builder/ -x -v && cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/app_builder/test_iteration_service.py -x -v`
- **After every plan wave:** Run `uv run pytest tests/unit/app_builder/ -x -v && cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | ITER-01 | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_edit_yields_correct_events -x` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | ITER-01 | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_edit_screens_called_with_array -x` | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 1 | ITER-02 | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_design_system_injected_when_locked -x` | ❌ W0 | ⬜ pending |
| 20-01-04 | 01 | 1 | ITER-02 | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_no_injection_when_unlocked -x` | ❌ W0 | ⬜ pending |
| 20-01-05 | 01 | 1 | ITER-03 | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_iteration_number_incremented -x` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 1 | ITER-01 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_iterate_screen_sse -x` | ❌ W0 | ⬜ pending |
| 20-02-02 | 02 | 1 | ITER-03 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_screen_history_ordered -x` | ❌ W0 | ⬜ pending |
| 20-02-03 | 02 | 1 | ITER-03 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_rollback_selects_variant -x` | ❌ W0 | ⬜ pending |
| 20-02-04 | 02 | 1 | ITER-04 | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_approve_screen -x` | ❌ W0 | ⬜ pending |
| 20-03-01 | 03 | 2 | FLOW-05 | unit | `cd frontend && npx vitest run src/__tests__/components/IterationPanel.test.tsx` | ❌ W0 | ⬜ pending |
| 20-03-02 | 03 | 2 | ITER-04 | unit | `cd frontend && npx vitest run src/__tests__/components/ApprovalCheckpointCard.test.tsx` | ❌ W0 | ⬜ pending |
| 20-03-03 | 03 | 2 | ITER-03 | unit | `cd frontend && npx vitest run src/__tests__/components/VersionHistoryPanel.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/app_builder/test_iteration_service.py` — stubs for ITER-01, ITER-02, ITER-03
- [ ] `tests/unit/app_builder/test_app_builder_router.py` — extend with iterate, approve, history, rollback tests
- [ ] `frontend/src/__tests__/components/IterationPanel.test.tsx` — stubs for FLOW-05
- [ ] `frontend/src/__tests__/components/ApprovalCheckpointCard.test.tsx` — stubs for ITER-04
- [ ] `frontend/src/__tests__/components/VersionHistoryPanel.test.tsx` — stubs for ITER-03 UI

*Existing infrastructure covers framework installs — no new framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Stitch edit_screens call returns updated HTML | ITER-01 | Requires Stitch MCP subprocess + API key | Start backend, navigate to building page, request edit, confirm preview updates |
| iframe preview updates after edit | FLOW-05 | Browser rendering in iframe | Visually confirm iframe shows new HTML after edit completes |
| Design system visual consistency | ITER-02 | Visual comparison across screens | Generate 2+ screens with locked design system, compare colors/fonts/spacing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
