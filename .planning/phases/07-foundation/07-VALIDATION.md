---
phase: 7
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), manual browser (frontend) |
| **Config file** | `pyproject.toml` (backend), N/A (frontend) |
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
| 7-01-01 | 01 | 1 | AUTH-01..05 | unit | `uv run pytest tests/unit/admin/test_admin_auth.py` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | AUTH-01..05 | integration | `uv run pytest tests/integration/admin/test_admin_guard.py` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | AUDT-01..04 | unit | `uv run pytest tests/unit/admin/test_audit.py` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 1 | AUDT-02 | unit | `uv run pytest tests/unit/admin/test_encryption.py` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 2 | ASST-01..06 | unit | `uv run pytest tests/unit/admin/test_admin_agent.py` | ❌ W0 | ⬜ pending |
| 7-03-02 | 03 | 2 | ASST-03,05,06 | unit | `uv run pytest tests/unit/admin/test_autonomy.py` | ❌ W0 | ⬜ pending |
| 7-03-03 | 03 | 2 | ASST-06 | unit | `uv run pytest tests/unit/admin/test_confirmation.py` | ❌ W0 | ⬜ pending |
| 7-04-01 | 04 | 2 | AUTH-03,05 | manual | Browser test: non-admin redirect | N/A | ⬜ pending |
| 7-04-02 | 04 | 2 | ASST-01 | manual | Browser test: SSE chat streaming | N/A | ⬜ pending |
| 7-04-03 | 04 | 2 | AUDT-03 | manual | Browser test: audit log viewer | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/__init__.py` — package init
- [ ] `tests/unit/admin/conftest.py` — shared fixtures (mock Supabase, mock Redis, mock ADK)
- [ ] `tests/unit/admin/test_admin_auth.py` — stubs for AUTH-01..05
- [ ] `tests/unit/admin/test_audit.py` — stubs for AUDT-01..04
- [ ] `tests/unit/admin/test_encryption.py` — stubs for AUDT-02 (Fernet)
- [ ] `tests/unit/admin/test_admin_agent.py` — stubs for ASST-01..06
- [ ] `tests/unit/admin/test_autonomy.py` — stubs for ASST-03,05
- [ ] `tests/unit/admin/test_confirmation.py` — stubs for ASST-06
- [ ] `tests/integration/admin/__init__.py` — package init
- [ ] `tests/integration/admin/test_admin_guard.py` — stubs for AUTH integration

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-admin redirect | AUTH-03, AUTH-05 | Requires browser session + Supabase auth state | 1. Login as non-admin user 2. Navigate to /admin 3. Verify redirect to /dashboard with toast |
| SSE chat streaming | ASST-01 | Real-time SSE rendering in browser | 1. Login as admin 2. Open admin panel 3. Type question 4. Verify streamed response |
| Chat persistence | ASST-06 | Browser refresh behavior | 1. Send a message 2. Refresh browser 3. Verify chat history reloads |
| Confirm card UX | ASST-03 | Interactive button click flow | 1. Ask agent to perform a confirm-tier action 2. Verify card renders 3. Click Confirm 4. Verify execution |
| Audit log viewer | AUDT-03 | UI filter/pagination | 1. Perform various admin actions 2. Navigate to audit log 3. Verify entries with correct source tags |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
