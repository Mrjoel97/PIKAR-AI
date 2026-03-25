---
phase: 14-billing-dashboard
plan: "01"
subsystem: admin-billing
tags: [billing, stripe, analytics, admin-agent, tdd]
dependency_graph:
  requires:
    - 13-03 (interactive impersonation — IntegrationProxyService, _check_autonomy patterns)
    - 11-02 (external integrations — _get_integration_config, session budgets)
    - 10-02 (analytics — get_usage_stats, get_agent_effectiveness)
  provides:
    - GET /admin/billing/summary endpoint
    - 7 AdminAgent billing tools (get_billing_metrics, get_plan_distribution, issue_refund, detect_analytics_anomalies, generate_executive_summary, forecast_revenue, assess_refund_risk)
    - Stripe MRR/ARR metrics helpers (_fetch_stripe_metrics, _create_refund_sync)
  affects:
    - app/agents/admin/agent.py (49 → 56 tools)
    - app/agents/admin/tools/__init__.py (__all__ extended)
    - app/services/integration_proxy.py (2 new Stripe helpers)
tech_stack:
  added: []
  patterns:
    - IntegrationProxyService.call() for cached Stripe fetch
    - asyncio.to_thread() for sync Stripe SDK calls (sequential, not gather)
    - statistics.mean/stdev from stdlib for anomaly detection
    - Least-squares linear extrapolation for revenue forecasting
    - Graceful degradation: db_only / no_data / live data_source modes
key_files:
  created:
    - supabase/migrations/20260325000000_billing_permissions.sql
    - app/agents/admin/tools/billing.py
    - app/routers/admin/billing.py
    - tests/unit/admin/test_billing_tools.py
    - tests/unit/admin/test_billing_api.py
  modified:
    - app/services/integration_proxy.py
    - app/agents/admin/tools/__init__.py
    - app/agents/admin/agent.py
    - app/routers/admin/__init__.py
decisions:
  - "log_admin_action imported at module level in billing.py — enables clean patch target in unit tests (same reason as Phase 13 users_intelligence.py pattern)"
  - "get_usage_stats and get_agent_effectiveness imported at module level — deferred imports inside async functions cannot be patched at module scope"
  - "Zero-stddev baseline handled explicitly: any deviation from a perfectly flat baseline is flagged as anomalous (infinite deviation)"
  - "asyncio.to_thread for Stripe refund (not via proxy cache) — refunds must never be cached; Phase 19 pattern: sequential SDK calls"
  - "forecast_revenue uses least-squares slope on monthly MRR buckets derived from subscriptions.created_at — no Stripe API call needed"
  - "assess_refund_risk degrades gracefully when admin_analytics_daily has no user-level data — wraps usage query in try/except"
metrics:
  duration: "17 minutes"
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_created: 5
  files_modified: 4
  tests_added: 17
---

# Phase 14 Plan 01: Billing Dashboard Backend Summary

7 AdminAgent billing tools + GET /admin/billing/summary endpoint backed by IntegrationProxyService Stripe cache and subscriptions DB, with full autonomy enforcement and 17 passing unit tests.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Migration + Stripe fetch helpers + billing tools + tests | 391043b | billing_permissions.sql, integration_proxy.py, billing.py, test_billing_tools.py |
| 2 | Billing API router + AdminAgent registration + API tests | 234c8b8 | routers/admin/billing.py, tools/__init__.py, agent.py, test_billing_api.py |

## What Was Built

### Permission Seed Migration
`supabase/migrations/20260325000000_billing_permissions.sql` — 7 rows in `admin_agent_permissions`: 6 auto-tier tools (billing reads/analytics) and 1 confirm-tier tool (`issue_refund`, high risk).

### Stripe Fetch Helpers (`integration_proxy.py`)
- `_get_stripe_metrics_sync` — iterates Stripe subscriptions with `auto_paging_iter()`, normalizes annual prices to monthly, computes MRR/ARR in dollars
- `_fetch_stripe_metrics` — async wrapper via `asyncio.to_thread`
- `_create_refund_sync` — calls `stripe.Refund.create()` with optional partial amount
- `_fetch_stripe_refund` — async wrapper via `asyncio.to_thread`

### 7 Billing Tools (`app/agents/admin/tools/billing.py`)
All tools enforce autonomy via `_check_autonomy()` before executing:

1. **get_billing_metrics** — live MRR/ARR from Stripe via `IntegrationProxyService.call()` with 5-minute cache
2. **get_plan_distribution** — tier breakdown from `subscriptions` table, zero Stripe API budget
3. **issue_refund** — confirm tier; executes `_create_refund_sync` via `asyncio.to_thread`; logs to `admin_audit_log`
4. **detect_analytics_anomalies** (SKIL-05) — stdlib `statistics.mean/stdev`, flags >2-stddev outliers in DAU/MAU and per-agent success rates; handles zero-variance baseline
5. **generate_executive_summary** (SKIL-06) — narrative text with DAU trend direction, revenue summary, top/bottom agent, anomaly count; degrades if Stripe not configured
6. **forecast_revenue** (SKIL-10) — least-squares linear extrapolation on monthly MRR buckets from subscription history; requires 7+ rows; "medium" confidence for 7-30 points
7. **assess_refund_risk** (SKIL-11) — scores HIGH/MEDIUM/LOW based on tenure_months and usage_level; degrades gracefully if no usage data in `admin_analytics_daily`

### Billing API Router (`app/routers/admin/billing.py`)
`GET /admin/billing/summary` gated by `require_admin`, rate-limited at 120/minute. Returns:
- `mrr`, `arr` from Stripe (or 0 when not configured)
- `churn_rate` (churn_pending / total_active)
- `plan_distribution` list from subscriptions table
- `data_source`: `"live"` (Stripe connected), `"db_only"` (Stripe missing), `"no_data"` (empty table)

### AdminAgent Updates (`app/agents/admin/agent.py`)
- 7 billing tools added to both the singleton and `create_admin_agent()` factory (now 56 total tools, surpassing ASST-02 30+ target)
- New instruction sections: `## Billing Tools (Phase 14)`, `## Analytics Anomaly Detection (SKIL-05)`, `## Executive Summary Generation (SKIL-06)`, `## Revenue Forecasting (SKIL-10)`, `## Refund Risk Assessment (SKIL-11)`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] log_admin_action needed module-level import for test patchability**
- **Found during:** Task 1 — test_issue_refund_executes_after_confirmation
- **Issue:** `log_admin_action` was imported inside the function body; patch target `app.agents.admin.tools.billing.log_admin_action` raised `AttributeError`
- **Fix:** Moved import to module level (same pattern as Phase 13 `users_intelligence.py`)
- **Files modified:** app/agents/admin/tools/billing.py
- **Commit:** 391043b

**2. [Rule 1 - Bug] get_usage_stats / get_agent_effectiveness needed module-level imports**
- **Found during:** Task 1 — test_detect_anomalies_flags_dau
- **Issue:** Deferred imports inside async functions cannot be patched at the module scope used by the test
- **Fix:** Moved both analytics tool imports to module level
- **Files modified:** app/agents/admin/tools/billing.py
- **Commit:** 391043b

**3. [Rule 1 - Bug] Zero-stddev baseline produced false negative in anomaly detection**
- **Found during:** Task 1 — test_detect_anomalies_flags_dau
- **Issue:** When baseline DAU is perfectly constant (stddev=0), the code hit `continue` and never flagged the spike
- **Fix:** Added explicit zero-stddev handler — any deviation from a flat baseline is anomalous (deviation = infinity)
- **Files modified:** app/agents/admin/tools/billing.py
- **Commit:** 391043b

**4. [Rule 1 - Bug] AsyncMock side_effect with unawaited coroutines**
- **Found during:** Task 1 — test_assess_refund_risk_high / _low
- **Issue:** Test used `AsyncMock(return_value=result)()` to create side_effect values; this creates unawaited coroutine objects, not resolved values
- **Fix:** Changed to `AsyncMock(side_effect=[result1, result2])` pattern
- **Files modified:** tests/unit/admin/test_billing_tools.py
- **Commit:** 391043b

**5. [Rule 1 - Bug] Ruff B905 zip() missing strict= parameter**
- **Found during:** Task 2 verification lint run
- **Issue:** `zip(x_vals, mrr_values)` in forecast_revenue lacked explicit `strict=True`
- **Fix:** Added `strict=True`
- **Files modified:** app/agents/admin/tools/billing.py
- **Commit:** 234c8b8

**6. [Rule 1 - Bug] Ruff I001 unsorted imports in billing router**
- **Found during:** Task 2 verification lint run
- **Issue:** Import block formatting not matching ruff's isort expectations
- **Fix:** Split long import line for IntegrationProxyService into multi-line block
- **Files modified:** app/routers/admin/billing.py
- **Commit:** 234c8b8

## Self-Check: PASSED
