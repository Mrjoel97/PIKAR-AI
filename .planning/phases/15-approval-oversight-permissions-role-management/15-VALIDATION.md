---
phase: 15
slug: approval-oversight-permissions-role-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_governance_tools.py -x` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/test_governance_tools.py -x`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | ROLE-01 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_create_admin_account -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | ROLE-02 | unit | `uv run pytest tests/unit/admin/test_role_access.py::test_junior_admin_write_blocked -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | ROLE-03 | unit | `uv run pytest tests/unit/admin/test_role_access.py::test_senior_admin_no_role_management -x` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | ROLE-04 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_update_role_permissions -x` | ❌ W0 | ⬜ pending |
| 15-01-05 | 01 | 1 | APPR-01 | unit | `uv run pytest tests/unit/admin/test_approval_api.py::test_list_all_approvals -x` | ❌ W0 | ⬜ pending |
| 15-01-06 | 01 | 1 | APPR-02 | unit | `uv run pytest tests/unit/admin/test_approval_api.py::test_override_approval -x` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | SKIL-12 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_recommend_autonomy_tier -x` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | SKIL-13 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_generate_compliance_report -x` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | SKIL-14 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_suggest_role_permissions -x` | ❌ W0 | ⬜ pending |
| 15-02-04 | 02 | 1 | SKIL-15 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_generate_daily_digest -x` | ❌ W0 | ⬜ pending |
| 15-02-05 | 02 | 1 | SKIL-16 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_classify_and_escalate -x` | ❌ W0 | ⬜ pending |
| 15-02-06 | 02 | 1 | ASST-02 | unit | `uv run pytest tests/unit/admin/test_governance_tools.py::test_admin_agent_tool_count -x` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | APPR-01 | visual | `cd frontend && npx tsc --noEmit --pretty` | ✅ | ⬜ pending |
| 15-03-02 | 03 | 2 | ROLE-04 | visual | `cd frontend && npx tsc --noEmit --pretty` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_governance_tools.py` — stubs for 5 governance tools + role CRUD + tool count
- [ ] `tests/unit/admin/test_approval_api.py` — stubs for admin approval endpoints
- [ ] `tests/unit/admin/test_role_access.py` — stubs for role-based access enforcement

*Existing `tests/unit/admin/conftest.py` covers shared fixtures — no new conftest needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Approvals page renders filterable table | APPR-01 | Visual layout verification | Navigate to /admin/approvals, verify table with filters |
| Settings page tabs render correctly | ROLE-04 | Visual layout verification | Navigate to /admin/settings, verify 3 tabs |
| Role assignment dropdown works | ROLE-01 | Interactive UI | Assign junior_admin role, verify persistence |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
