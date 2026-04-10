---
phase: 60-financial-agent-enhancement
plan: "04"
subsystem: financial-agent
tags: [forecasting, scenario-modeling, what-if, regression, degraded-tool-replacement]
dependency_graph:
  requires: [60-01, 60-02]
  provides: [ForecastService, ScenarioModelingService, run_financial_scenario, generate_financial_forecast]
  affects: [app/agents/tools/registry.py, app/agents/tools/degraded_tools.py]
tech_stack:
  added: [weighted-linear-regression]
  patterns: [lazy-db-imports, module-level-convenience-functions]
key_files:
  created:
    - app/services/forecast_service.py
    - app/services/scenario_modeling_service.py
    - tests/unit/services/test_forecast_service.py
    - tests/unit/services/test_scenario_modeling_service.py
  modified:
    - app/agents/financial/tools.py
    - app/agents/financial/agent.py
    - app/agents/tools/registry.py
    - app/agents/tools/degraded_tools.py
decisions:
  - Lazy DB imports (no BaseService inheritance) for both ForecastService and ScenarioModelingService to enable unit testing without Supabase client chain
  - Module-level helper functions (_get_baseline_forecast, _get_cash_position) in scenario service for clean test mocking
  - Weighted linear regression with recent_weight=2.0 for high-confidence forecasts; equal weight (1.0) for medium-confidence
metrics:
  duration: 15min
  completed: "2026-04-10T11:46:06Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 16
  files_changed: 8
---

# Phase 60 Plan 04: Scenario Modeling & Forecast Replacement Summary

Weighted-regression forecasting service and what-if scenario modeling with 5 scenario types, replacing degraded generate_forecast with real data-driven implementation.

## What Was Built

### ForecastService (`app/services/forecast_service.py`)
- `get_monthly_history()`: Aggregates financial_records by month into revenue/expenses buckets
- `generate_forecast()`: Projects revenue and expenses using weighted linear regression
  - < 3 months data: flat average projection, confidence=low
  - 3-5 months data: simple linear regression, confidence=medium
  - 6+ months data: weighted linear regression (recent months weighted 2x), confidence=high
- Revenue and expenses clamped to >= 0 in projections
- Returns structured forecast with monthly projections, confidence, methodology, currency

### ScenarioModelingService (`app/services/scenario_modeling_service.py`)
- `run_scenario()`: Applies what-if parameters on top of baseline forecast
- Supported scenario types:
  - `hire`: Add count * salary_per_person to monthly expenses
  - `new_expense`: Add flat monthly cost
  - `lose_customers_pct`: Reduce revenue by percentage
  - `price_increase_pct`: Increase revenue by percentage
  - `revenue_change_pct`: General revenue adjustment
- Tracks cumulative cash position from starting cash
- Detects months_until_negative and generates warnings
- Produces human-readable summary string
- Returns baseline vs projected comparison for side-by-side display

### Agent Integration
- `run_financial_scenario()` tool: Translates scenario_type/count/amount/percentage into scenario dict
- `generate_financial_forecast()` tool: Wraps ForecastService for agent use
- Both tools added to FINANCIAL_AGENT_TOOLS
- Agent instructions added: SCENARIO MODELING and FINANCIAL FORECASTING sections

### Degraded Tool Replacement (FIN-06)
- Registry entries `generate_forecast` and `create_forecast` now point to `_real_generate_forecast` / `_real_create_forecast`
- Real implementation calls ForecastService with user context
- Degraded functions in degraded_tools.py marked as DEPRECATED (not deleted for backward compat)

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 5ddf48f7 | test(60-04): add failing tests for forecast and scenario modeling services |
| 2 | ecda53bd | feat(60-04): add ForecastService and ScenarioModelingService with tests |
| 3 | 85b16380 | feat(60-04): wire scenario modeling and forecast tools to financial agent |

## Test Results

16 tests passing:
- 7 forecast tests: sufficient data, growing/declining trends, limited data, metadata, clamping
- 9 scenario tests: hire, revenue change, new expense, baseline, data points, cumulative cash, negative cash warning, price increase, summary

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy DB imports instead of BaseService inheritance**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Importing BaseService triggers full Supabase client chain (supabase._async), blocking test collection
- **Fix:** ForecastService and ScenarioModelingService use lazy imports inside methods instead of extending BaseService. Follows same pattern as ExpenseCategorizationService from 60-02.
- **Files modified:** app/services/forecast_service.py, app/services/scenario_modeling_service.py

**2. [Rule 3 - Blocking] Module-level helper functions for scenario mocking**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Patching lazy class factories inside scenario service was not intercepted by unittest.mock
- **Fix:** Extracted _get_baseline_forecast() and _get_cash_position() as patchable module-level async functions
- **Files modified:** app/services/scenario_modeling_service.py, tests/unit/services/test_scenario_modeling_service.py

## Self-Check: PASSED

All 4 created files verified on disk. All 3 commit hashes verified in git log.
