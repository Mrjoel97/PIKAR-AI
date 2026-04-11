---
phase: 62-sales-agent-enhancement
plan: "02"
subsystem: sales-agent
tags: [pipeline-health, lead-attribution, crm, hubspot, utm-tracking]
dependency_graph:
  requires: [hubspot_tools, contacts-table, hubspot_deals-table]
  provides: [get_pipeline_recommendations, get_lead_attribution, PIPELINE_DASHBOARD_TOOLS]
  affects: [sales_agent, pipeline_health, lead_source_attribution]
tech_stack:
  added: []
  patterns: [lazy-import-for-testability, admin-service-mock-pattern, tdd-red-green]
key_files:
  created:
    - app/agents/tools/pipeline_dashboard.py
    - supabase/migrations/20260409620200_lead_source_attribution.sql
    - tests/unit/test_pipeline_dashboard.py
  modified:
    - app/agents/sales/agent.py
decisions:
  - "Lazy imports inside tool functions (not module-level) to avoid app.agents.__init__ chain in tests"
  - "Patch app.services.base_service.AdminService (source) not the tool module for test isolation"
  - "Classify at-risk by early-stage + close_date within 14 days OR amount < 50% of pipeline avg"
  - "Prefer last_activity_at over updated_at for staleness detection when column is populated"
  - "Migration NOT applied to live DB — committed as SQL artifact only per plan instructions"
metrics:
  duration: 15min
  completed: "2026-04-11"
  tasks: 3
  files: 4
requirements_satisfied: [SALES-02, SALES-04]
---

# Phase 62 Plan 02: Pipeline Health Dashboard & Lead Attribution Summary

Pipeline health classification and lead source attribution tools giving the Sales Agent actionable deal recommendations and UTM-linked contact attribution.

## What Was Built

### Tool 1: `get_pipeline_recommendations`

Queries `hubspot_deals` for all user deals and classifies each into five buckets:

- **stalled** — no activity (`last_activity_at` or `updated_at`) for >= `days_stalled_threshold` days (default 14), stage not closed
- **at_risk** — early stage + close date within 14 days, OR deal amount < 50% of pipeline average
- **healthy** — active open deals not matching stalled/at_risk
- **won** — stage contains closedwon/won
- **lost** — stage contains closedlost/lost

Stalled deals generate three recommended actions: re-engagement email, limited-time discount offer, manager escalation. At-risk deals generate: urgent review call, competitive comparison, extended trial offer.

Returns `pipeline_health` (grouped deal lists), `recommendations` (action items with priority), and `summary` (counts and total value).

### Tool 2: `get_lead_attribution`

Queries `contacts` created within `period_days` (default 90) and groups by `source` enum, computing per-source count and conversion rate (lifecycle_stage == 'customer'). When `utm_source` data is present, also produces a `by_campaign` breakdown keyed by UTM source.

Returns `attribution.by_source`, `attribution.by_campaign`, totals, and overall conversion rate.

### Migration: `20260409620200_lead_source_attribution.sql`

Idempotent SQL migration (NOT applied to live DB) that:
- Adds `ad_campaign` and `email_campaign` values to `contact_source` enum
- Adds `campaign_id UUID`, `utm_source TEXT`, `utm_medium TEXT`, `utm_campaign TEXT` to `contacts`
- Adds `last_activity_at TIMESTAMPTZ` to `hubspot_deals`
- Creates `idx_contacts_campaign` and `idx_contacts_utm` partial indexes

### Sales Agent Wiring

Added `PIPELINE_DASHBOARD_TOOLS` import and list entry after `HUBSPOT_TOOLS` in `SALES_AGENT_TOOLS`. Added two instruction blocks to `SALES_AGENT_INSTRUCTION`:

- **PIPELINE HEALTH DASHBOARD** — directs agent to use `get_pipeline_recommendations` with kanban and table widgets
- **LEAD SOURCE ATTRIBUTION** — directs agent to use `get_lead_attribution` for ROI and channel analysis

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test patch strategy required AdminService mock**
- **Found during:** Task 2 GREEN phase
- **Issue:** `execute_async` patch alone insufficient — `AdminService()` constructor raises `ValueError` when `SUPABASE_URL` is absent in test env. Lazy-import pattern means `app.agents.__init__` is triggered by `from app.agents.tools.pipeline_dashboard import ...` inside tests via `app.agents` package `__init__.py`.
- **Fix:** Added `_ADMIN_SERVICE_PATCH = "app.services.base_service.AdminService"` to all tests that call the two tools. All imports kept function-scoped (not module-level) to avoid the full `app.agents` chain. Updated `_make_admin_mock()` helper returns chained query builder mock.
- **Files modified:** `tests/unit/test_pipeline_dashboard.py`

**2. [Rule 3 - Blocking] Supabase async not available in system Python**
- **Found during:** Task 2 RED phase
- **Issue:** `python` (system Python 3.14) doesn't have `supabase._async` — tests required `uv run pytest` to use the project venv (Python 3.12 + full deps).
- **Fix:** Switched all test invocations to `C:/Users/expert/.local/bin/uv.cmd run pytest`. No code change required.

## Test Coverage

All 8 tests pass via `uv run pytest tests/unit/test_pipeline_dashboard.py`:

| Test | Coverage |
|------|----------|
| `test_returns_grouped_by_status` | Groups 4 deals into stalled/healthy/won/lost correctly |
| `test_stalled_deals_get_reengagement_recommendations` | 3 re-engagement actions on 20-day inactive deal |
| `test_at_risk_deals_get_escalation_recommendations` | 3 escalation actions on deal closing in 7 days |
| `test_no_user_id_returns_error` (recommendations) | Returns `{"error": ..., "success": False}` |
| `test_returns_source_breakdown_with_counts_and_conversion` | Source counts, converted, conversion_rate correct |
| `test_attribution_includes_campaign_detail_when_utm_available` | `by_campaign` populated when utm_source present |
| `test_no_user_id_returns_error` (attribution) | Returns `{"error": ..., "success": False}` |
| `test_tools_list_exports_both_functions` | PIPELINE_DASHBOARD_TOOLS has exactly 2 entries |

## Commits

| Hash | Description |
|------|-------------|
| `681132c4` | chore(62-02): add lead source attribution migration |
| `7bc0d385` | test(62-02): add failing tests for pipeline dashboard and lead attribution |
| `06932774` | feat(62-02): implement pipeline dashboard and lead attribution tools |
| `bef2e0e3` | feat(62-02): wire PIPELINE_DASHBOARD_TOOLS into Sales Agent |

## Self-Check: PASSED
