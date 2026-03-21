---
phase: 9
slug: user-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), manual browser (frontend) |
| **Config file** | `pyproject.toml` (backend) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_users*.py -x -q` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/test_users*.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | USER-01..03 | unit | `uv run pytest tests/unit/admin/test_users_api.py` | ❌ W0 | ⬜ pending |
| 9-02-01 | 02 | 1 | USER-05 | unit | `uv run pytest tests/unit/admin/test_user_tools.py` | ❌ W0 | ⬜ pending |
| 9-03-01 | 03 | 2 | USER-01 | manual | Browser: user table with search/filter/pagination | N/A | ⬜ pending |
| 9-03-02 | 03 | 2 | USER-05 | manual | Browser: impersonation view with banner | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `npm install @tanstack/react-table@^8.21.3` — headless table library
- [ ] `tests/unit/admin/test_users_api.py` — stubs for USER-01..03
- [ ] `tests/unit/admin/test_user_tools.py` — stubs for USER-05 agent tools

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| User table search/filter | USER-01 | Server-side pagination + UI interaction | Search by email, filter by persona, verify paginated results |
| Suspend blocks login | USER-02 | Requires real Supabase auth flow | Suspend user, attempt login in incognito, verify blocked |
| Persona switch reflects | USER-03 | Requires user session refresh | Change persona, verify next session shows new persona |
| Impersonation banner | USER-05 | Visual + behavior (non-dismissible, read-only) | Enter impersonation, verify banner stays visible, verify mutations blocked |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
