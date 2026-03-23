---
phase: 13
slug: interactive-impersonation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_impersonation_service.py tests/unit/admin/test_user_intelligence_tools.py -x` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -x` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/test_impersonation_service.py tests/unit/admin/test_user_intelligence_tools.py -x`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | USER-04 | unit | `uv run pytest tests/unit/admin/test_impersonation_service.py::test_create_session -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | USER-04 | unit | `uv run pytest tests/unit/admin/test_impersonation_service.py::test_session_expiry -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | AUDT-04 | unit | `uv run pytest tests/unit/admin/test_impersonation_service.py::test_audit_tagging -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | USER-04 | unit | `uv run pytest tests/unit/admin/test_impersonation_service.py::test_validate_allow_list -x` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 2 | SKIL-03 | unit | `uv run pytest tests/unit/admin/test_user_intelligence_tools.py::test_identify_at_risk_users -x` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 2 | SKIL-04 | unit | `uv run pytest tests/unit/admin/test_user_intelligence_tools.py::test_support_playbook -x` | ❌ W0 | ⬜ pending |
| 13-02-03 | 02 | 2 | USER-04 | unit | `uv run pytest tests/unit/admin/test_user_intelligence_tools.py::test_activate_impersonation_confirm -x` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 3 | USER-04 | tsc | `cd frontend && npx tsc --noEmit --pretty 2>&1 \| grep -i "impersonat"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_impersonation_service.py` — covers USER-04 (session CRUD, expiry, allow-list), AUDT-04 (audit tagging)
- [ ] `tests/unit/admin/test_user_intelligence_tools.py` — covers SKIL-03, SKIL-04, USER-04 (activate tool)

*Existing infrastructure in `tests/unit/admin/conftest.py` with mock_supabase_client and admin_user_dict fixtures covers all new test files — no framework changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Banner turns red in interactive mode | USER-04 | Browser UI | Activate impersonation, verify banner is red and non-dismissible |
| Session auto-expires after 30 min | USER-04 | Timing + UI | Activate, wait or set timer low, verify session ends and banner disappears |
| Blocked endpoint shows rejection | USER-04 | Browser UI | In impersonation mode, attempt non-allowed action, verify rejection message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
