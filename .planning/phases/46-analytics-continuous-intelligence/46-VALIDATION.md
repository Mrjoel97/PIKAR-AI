---
phase: 46
slug: analytics-continuous-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/unit/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 0 | XDATA-01–06 | unit | `uv run pytest tests/unit/test_external_db_service.py -x` | ❌ W0 | ⬜ pending |
| 46-01-02 | 01 | 0 | CAL-01–04 | unit | `uv run pytest tests/unit/test_calendar_tools.py -x` | ❌ W0 | ⬜ pending |
| 46-01-03 | 01 | 0 | INTEL-01–05 | unit | `uv run pytest tests/unit/test_monitoring_job_service.py -x` | ❌ W0 | ⬜ pending |
| 46-02-xx | 02 | 1 | XDATA-01–06 | unit | `uv run pytest tests/unit/test_external_db_service.py tests/unit/tools/test_external_db_tools.py -x` | ❌ W0 | ⬜ pending |
| 46-03-xx | 03 | 1 | CAL-01–04 | unit | `uv run pytest tests/unit/test_calendar_tools.py -x` | ❌ W0 | ⬜ pending |
| 46-04-xx | 04 | 2 | INTEL-01–05 | unit | `uv run pytest tests/unit/test_monitoring_job_service.py tests/unit/test_scheduled_endpoints.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_external_db_service.py` — stubs for XDATA-01 through XDATA-06
- [ ] `tests/unit/tools/test_external_db_tools.py` — stubs for XDATA-04, XDATA-05
- [ ] `tests/unit/test_calendar_tools.py` — stubs for CAL-01 through CAL-04
- [ ] `tests/unit/test_monitoring_job_service.py` — stubs for INTEL-01, INTEL-03, INTEL-04, INTEL-05
- [ ] `tests/unit/test_scheduled_endpoints.py` — stubs for INTEL-02

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| External PostgreSQL connection from config UI | XDATA-01 | Requires live DB + frontend interaction | Connect a test PG database from config page, verify test-connection passes |
| BigQuery connection from config UI | XDATA-02 | Requires live BigQuery project + OAuth | Connect BigQuery from config page, verify schema listing works |
| Calendar free/busy with external attendees | CAL-01 | Requires Google Calendar permissions | Check free/busy for a meeting with external attendee, verify fallback when no access |
| Monitoring alert delivery to Slack/Teams | INTEL-05 | Requires live notification channels | Create a monitoring job, trigger significant change, verify alert in Slack/Teams |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
