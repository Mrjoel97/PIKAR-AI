---
phase: 8
slug: health-monitoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend — if configured) |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `uv run pytest tests/unit/admin/ -x -q` |
| **Full suite command** | `uv run pytest tests/unit/admin/ tests/integration/admin/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ tests/integration/admin/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | HLTH-01, HLTH-06 | unit | `uv run pytest tests/unit/admin/test_health_checker.py -v` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | HLTH-02 | unit | `uv run pytest tests/unit/admin/test_scheduled_health.py -v` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | HLTH-03 | unit | `uv run pytest tests/unit/admin/test_incident_manager.py -v` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | HLTH-04 | unit | `uv run pytest tests/unit/admin/test_monitoring_api.py -v` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 2 | HLTH-04, HLTH-05 | manual | Browser verification | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_health_checker.py` — stubs for HLTH-01, HLTH-06
- [ ] `tests/unit/admin/test_scheduled_health.py` — stubs for HLTH-02
- [ ] `tests/unit/admin/test_incident_manager.py` — stubs for HLTH-03
- [ ] `tests/unit/admin/test_monitoring_api.py` — stubs for HLTH-04
- [ ] `npm install recharts` — recharts not currently in frontend

*Existing pytest + admin conftest from Phase 7 covers shared fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sparkline charts render with recent data | HLTH-04 | Visual rendering in browser | Open `/admin/monitoring`, verify sparklines show data points |
| Stale-data warning banner appears | HLTH-05 | Time-based visual check | Stop scheduler, wait >5 min, verify banner appears |
| Status card turns green on recovery | HLTH-03 | End-to-end with real endpoints | Take endpoint down, verify red; bring back, verify green |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
