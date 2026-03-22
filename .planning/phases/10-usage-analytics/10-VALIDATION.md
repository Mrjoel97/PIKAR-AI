---
phase: 10
slug: usage-analytics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), manual browser (frontend) |
| **Config file** | `pyproject.toml` (backend) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_analytics*.py -x -q` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/test_analytics*.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | ANLT-01,02 | unit | `uv run pytest tests/unit/admin/test_analytics_service.py` | W0 | pending |
| 10-02-01 | 02 | 2 | ANLT-01,02,04,05 | unit | `uv run pytest tests/unit/admin/test_analytics_api.py` | W0 | pending |
| 10-03-01 | 03 | 3 | ANLT-01,02,04,05 | manual | Browser: analytics dashboard | N/A | pending |

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_analytics_service.py` — stubs for aggregation service
- [ ] `tests/unit/admin/test_analytics_api.py` — stubs for analytics API

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DAU/MAU charts render | ANLT-01 | Visual chart rendering | Navigate to /admin/analytics, verify line charts show data |
| Agent effectiveness bars | ANLT-02 | Visual chart rendering | Verify horizontal bar chart for all 10 agents |
| Feature usage breakdown | ANLT-04 | Visual table/chart | Verify feature categories shown with counts |
| Config status card | ANLT-05 | Visual rendering | Verify feature flag count and last config change |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
