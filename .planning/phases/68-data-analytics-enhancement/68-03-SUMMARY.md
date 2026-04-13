---
phase: 68-data-analytics-enhancement
plan: "03"
subsystem: api
tags: [python, supabase, stripe, cohort-analysis, analytics, data-agent]

# Dependency graph
requires:
  - phase: 68-01
    provides: DataQueryService NL query infrastructure and data routing patterns

provides:
  - CohortAnalysisService with retention matrix, LTV by cohort, and churn rate computation
  - cohort_analysis tool on DataAnalysisAgent (SaaS cohort analysis from Stripe financial_records)
  - Real query_analytics tool replacing degraded placeholder (AnalyticsService with grouping)
  - Real query_usage tool replacing degraded placeholder (usage-category events + frequency counts)
  - Registry wired to real implementations for both query_analytics and query_usage

affects:
  - 68-04
  - 70-degraded-tool-cleanup
  - app/agents/data/agent.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - First-transaction-month as SaaS signup cohort proxy (no separate customer table needed)
    - 30-day recency threshold for churn detection from financial_records
    - Lazy LLM import with template fallback in _generate_summary
    - _aggregate_events helper for post-processing events into chart-ready buckets

key-files:
  created:
    - app/services/cohort_analysis_service.py
    - tests/unit/services/test_cohort_analysis_service.py
  modified:
    - app/agents/data/tools.py
    - app/agents/data/agent.py
    - app/agents/tools/degraded_tools.py
    - app/agents/tools/registry.py

key-decisions:
  - "CohortAnalysisService uses financial_records source_id as customer identifier — source_id from Stripe balance transactions uniquely identifies Stripe customers without a separate customer table"
  - "First-transaction month is the signup cohort proxy — avoids dependency on a dedicated subscriptions-for-SaaS-customers table"
  - "30-day recency threshold for churn detection — standard SaaS definition; configurable via method parameter"
  - "query_analytics and query_usage degraded definitions removed from degraded_tools.py — code deleted, not just commented, to eliminate dead code"
  - "Registry for query_analytics/query_usage imports from app.agents.data.tools under real_* alias following Phase 62/63/64/65 pattern"
  - "_aggregate_events is a module-level sync helper (no DB) — pure post-processing of in-memory event list"

patterns-established:
  - "Cohort analysis from transaction records: group by source_id + first transaction month, then build retention/LTV/churn matrices in Python"
  - "Real tool replacing degraded: import as real_X alias, comment out degraded import, update registry entry with phase note"

requirements-completed:
  - DATA-04
  - DATA-05

# Metrics
duration: 21min
completed: "2026-04-13"
---

# Phase 68 Plan 03: Data Analytics Enhancement — Cohort Analysis Summary

**CohortAnalysisService computing retention, LTV, and churn from Stripe financial_records, with real query_analytics and query_usage replacing the last two DATA degraded tools**

## Performance

- **Duration:** 21 min
- **Started:** 2026-04-13T00:39:37Z
- **Completed:** 2026-04-13T01:00:17Z
- **Tasks:** 2 (Task 1 TDD, Task 2 wiring)
- **Files modified:** 6

## Accomplishments

- `CohortAnalysisService` computes retention matrix, average LTV, and churn rate per signup-month cohort from Stripe financial_records with Gemini Flash executive summary and template fallback
- `cohort_analysis` tool wired into `DataAnalysisAgent` with helpful Stripe-connect message when no data found
- `query_analytics` and `query_usage` replaced with real AnalyticsService implementations supporting date filtering, category filtering, and `group_by` aggregation (day/week/month/category/event_name)
- Degraded definitions of `query_analytics` and `query_usage` removed from `degraded_tools.py`; registry entries updated to real implementations following established Phase 62-65 pattern
- 10 unit tests covering all 9 behaviors from plan (retention, LTV, churn, full_analysis, executive_summary)

## Task Commits

1. **RED: Failing tests for CohortAnalysisService** - `8b63cbe5` (test)
2. **GREEN: Implement CohortAnalysisService** - `0c3c9532` (feat)
3. **Task 2: cohort_analysis tool + replace degraded tools** - `6e4b7077` (feat)

## Files Created/Modified

- `app/services/cohort_analysis_service.py` - CohortAnalysisService with compute_cohort_retention, compute_ltv_by_cohort, compute_churn_by_cohort, full_cohort_analysis
- `tests/unit/services/test_cohort_analysis_service.py` - 10 unit tests covering all service methods
- `app/agents/data/tools.py` - Added cohort_analysis, query_analytics, query_usage, and _aggregate_events helper
- `app/agents/data/agent.py` - Imported 3 new tools, added to DATA_AGENT_TOOLS, updated CAPABILITIES and BEHAVIOR instructions
- `app/agents/tools/degraded_tools.py` - Removed query_analytics and query_usage function definitions; removed unused query_events import
- `app/agents/tools/registry.py` - Replaced degraded_query_analytics/degraded_query_usage with real_query_analytics/real_query_usage

## Decisions Made

- **CohortAnalysisService inherits BaseService (not AdminService)** — cohort data is scoped to the authenticated user's own Stripe transactions, not cross-user admin data
- **source_id as customer identifier** — Stripe balance transactions carry source_id uniquely identifying the customer; avoids a separate customer lookup table
- **First-transaction month = signup cohort proxy** — pragmatic SaaS analysis using only what's in financial_records
- **_aggregate_events as sync module-level helper** — pure in-memory post-processing, no DB dependency, easy to test

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_compute_cohort_retention_single_month date logic**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test used `timedelta(days=15)` and `timedelta(days=10)` from now — on April 13, day-15 lands in March and day-10 in April, producing 2 cohorts not 1
- **Fix:** Changed test to use fixed date `datetime(2026, 3, 5)` with +3 day offset, ensuring both customers fall in the same calendar month
- **Files modified:** tests/unit/services/test_cohort_analysis_service.py
- **Verification:** `len(result["cohorts"]) == 1` assertion passes
- **Committed in:** `0c3c9532` (part of GREEN task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test fixture date arithmetic)
**Impact on plan:** Minor test fixture fix only. Service implementation unchanged. No scope creep.

## Issues Encountered

- `test_degraded_tools.py` has a pre-existing `AttributeError` for `create_contact` (removed in Phase 62) — not caused by this plan, logged as deferred pre-existing issue
- `test_kpi_service.py` has 16 pre-existing failures — confirmed via stash test, not caused by this plan

## Next Phase Readiness

- DATA-04 and DATA-05 requirements complete
- `cohort_analysis` tool ready for user-facing SaaS cohort questions in the Data Agent
- `query_analytics` and `query_usage` are real implementations — no `degraded_completed` status returned to agents
- Phase 68-04 (if planned) can build on CohortAnalysisService for additional analytics features

---
*Phase: 68-data-analytics-enhancement*
*Completed: 2026-04-13*
