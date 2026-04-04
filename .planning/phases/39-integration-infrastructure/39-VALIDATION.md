---
phase: 39
slug: integration-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `uv run pytest tests/unit/test_integration_infrastructure.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 1 | INFRA-01,02 | unit | `uv run pytest tests/unit/test_integration_credentials.py -x -q` | ❌ W0 | ⬜ pending |
| 39-01-02 | 01 | 1 | INFRA-03,07 | unit | `uv run pytest tests/unit/test_integration_manager.py -x -q` | ❌ W0 | ⬜ pending |
| 39-02-01 | 02 | 1 | INFRA-04,05,06 | unit | `uv run pytest tests/unit/test_webhook_service.py -x -q` | ❌ W0 | ⬜ pending |
| 39-03-01 | 03 | 2 | INFRA-08 | unit | `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_integration_credentials.py` — stubs for credential CRUD + encryption
- [ ] `tests/unit/test_integration_manager.py` — stubs for token refresh + sync state
- [ ] `tests/unit/test_webhook_service.py` — stubs for inbound verify + outbound delivery

*Test files created as part of TDD tasks within each plan.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth popup flow | INFRA-01 | Requires browser + external provider | Open /dashboard/configuration, click Connect on a provider, verify popup opens to correct auth URL |
| Frontend status display | INFRA-08 | Visual rendering | Open /dashboard/configuration, verify category cards show green/gray/red dots per provider |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
