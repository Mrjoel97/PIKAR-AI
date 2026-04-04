---
phase: 42
slug: crm-email-automation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/unit/test_hubspot_service.py tests/unit/test_email_sequence.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | CRM-01..06 | unit | `uv run pytest tests/unit/test_hubspot_service.py -x -q` | ❌ W0 | ⬜ pending |
| 42-02-01 | 02 | 1 | EMAIL-01..05 | unit | `uv run pytest tests/unit/test_email_sequence.py -x -q` | ❌ W0 | ⬜ pending |
| 42-03-01 | 03 | 2 | CRM-04,05 EMAIL-06 | unit | `uv run pytest tests/unit/test_hubspot_service.py tests/unit/test_email_sequence.py -x -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/unit/test_hubspot_service.py` — stubs for contact sync, deal sync, conflict resolution, webhook processing
- [ ] `tests/unit/test_email_sequence.py` — stubs for sequence CRUD, enrollment, scheduling, tracking, bounce protection

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HubSpot OAuth connect | CRM-01 | Requires real HubSpot account | Connect HubSpot from /dashboard/configuration, verify contacts sync |
| Bidirectional sync | CRM-02 | Requires real HubSpot + Pikar data | Update contact in Pikar, verify change appears in HubSpot within seconds |
| Email open tracking | EMAIL-03 | Requires real email client | Send test sequence, open email, verify tracking event recorded |
| Bounce auto-pause | EMAIL-04 | Requires bounce simulation | Trigger >5% bounce rate, verify sequences auto-pause with notification |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
