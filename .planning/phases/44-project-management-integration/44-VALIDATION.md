---
phase: 44
slug: project-management-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/unit/services/test_pm_integration.py -x -q` |
| **Full suite command** | `uv run pytest tests/unit/services/test_pm_integration.py tests/unit/tools/test_pm_tools.py -v` |
| **Estimated runtime** | ~12 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/services/test_pm_integration.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/unit/services/test_pm_integration.py tests/unit/tools/test_pm_tools.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 12 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | PM-01, PM-02 | unit | `uv run pytest tests/unit/services/test_pm_integration.py -k "linear_service or asana_service"` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 1 | PM-03, PM-04 | unit | `uv run pytest tests/unit/services/test_pm_integration.py -k "sync_service or status_mapping"` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 1 | PM-03 | unit | `uv run pytest tests/unit/services/test_pm_integration.py -k "webhook"` | ❌ W0 | ⬜ pending |
| 44-02-02 | 02 | 1 | PM-03 | unit | `uv run pytest tests/unit/services/test_pm_integration.py -k "initial_sync"` | ❌ W0 | ⬜ pending |
| 44-03-01 | 03 | 2 | PM-05 | unit | `uv run pytest tests/unit/tools/test_pm_tools.py -k "agent_tools"` | ❌ W0 | ⬜ pending |
| 44-03-02 | 03 | 2 | PM-01, PM-02 | manual | Frontend verification | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/services/test_pm_integration.py` — stubs for PM-01 through PM-04
- [ ] `tests/unit/tools/test_pm_tools.py` — stubs for PM-05
- [ ] Fixtures: mock httpx transport for Linear GraphQL + Asana REST responses

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth popup flow for Linear/Asana | PM-01, PM-02 | Requires browser interaction with consent screens | Open configuration → Click Connect on Linear card → Complete OAuth → Verify connected status |
| Project picker UI | PM-03 | Frontend form interaction | Connect Linear → Verify project list appears → Select projects → Save → Verify sync starts |
| Status mapping UI | PM-04 | Frontend dropdown interaction | Open Linear card → Verify default mappings shown → Change one → Save → Verify persisted |

*All backend logic has automated verification; manual items are frontend UX flows.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 12s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
