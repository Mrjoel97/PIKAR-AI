---
phase: 14
slug: billing-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `uv run pytest tests/unit/admin/test_billing_tools.py -x` |
| **Full suite command** | `uv run pytest tests/unit/admin/ -x` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/admin/test_billing_tools.py -x`
- **After every plan wave:** Run `uv run pytest tests/unit/admin/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | ANLT-03 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_get_billing_metrics_returns_data -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | ANLT-03 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_get_plan_distribution_returns_tiers -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | ANLT-03 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_issue_refund_requires_confirmation -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | ANLT-03 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_issue_refund_executes_after_confirmation -x` | ❌ W0 | ⬜ pending |
| 14-01-05 | 01 | 1 | SKIL-05 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_detect_anomalies_flags_dau -x` | ❌ W0 | ⬜ pending |
| 14-01-06 | 01 | 1 | SKIL-05 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_detect_anomalies_no_flag_stable -x` | ❌ W0 | ⬜ pending |
| 14-01-07 | 01 | 1 | SKIL-06 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_generate_executive_summary_returns_text -x` | ❌ W0 | ⬜ pending |
| 14-01-08 | 01 | 1 | SKIL-10 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_forecast_revenue_projects_trend -x` | ❌ W0 | ⬜ pending |
| 14-01-09 | 01 | 1 | SKIL-10 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_forecast_revenue_insufficient_data -x` | ❌ W0 | ⬜ pending |
| 14-01-10 | 01 | 1 | SKIL-11 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_assess_refund_risk_high -x` | ❌ W0 | ⬜ pending |
| 14-01-11 | 01 | 1 | SKIL-11 | unit | `uv run pytest tests/unit/admin/test_billing_tools.py::test_assess_refund_risk_low -x` | ❌ W0 | ⬜ pending |
| 14-01-12 | 01 | 1 | ANLT-03 | unit | `uv run pytest tests/unit/admin/test_billing_api.py::test_billing_summary_returns_200 -x` | ❌ W0 | ⬜ pending |
| 14-01-13 | 01 | 1 | ANLT-03 | unit | `uv run pytest tests/unit/admin/test_billing_api.py::test_billing_summary_no_stripe -x` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | ANLT-03 | visual | `cd frontend && npx tsc --noEmit --pretty` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/admin/test_billing_tools.py` — stubs for all 8 billing tools (ANLT-03, SKIL-05, SKIL-06, SKIL-10, SKIL-11)
- [ ] `tests/unit/admin/test_billing_api.py` — stubs for GET /admin/billing/summary endpoint

*Existing `tests/unit/admin/conftest.py` covers shared fixtures — no new conftest needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Billing dashboard UI renders KPI cards + charts | ANLT-03 | Visual/layout verification | Navigate to /admin/billing, verify MRR/ARR/churn cards and plan distribution chart render |
| Refund confirmation card appears in admin chat | ANLT-03 | Chat UI interaction | Ask AdminAgent to issue a refund, verify confirmation card renders |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
