---
phase: 69-admin-research-enhancement
plan: "01"
subsystem: admin-agent
tags: [admin, diagnosis, feature-adoption, telemetry, tdd]
dependency_graph:
  requires:
    - app/agents/admin/tools/_autonomy.py
    - app/services/base_service.py (AdminService)
    - app/services/supabase.py (get_service_client)
    - app/services/supabase_async.py (execute_async)
    - DB tables: user_mcp_integrations, api_health_checks, ad_budget_caps, governance_approvals, tool_telemetry
  provides:
    - app/agents/admin/tools/diagnosis.py (diagnose_user_problem)
    - app/services/feature_adoption_service.py (FeatureAdoptionService)
    - app/agents/admin/tools/adoption.py (get_feature_adoption)
  affects:
    - app/agents/admin/agent.py (AdminAgent singleton + factory, 61 → 63 tools)
tech_stack:
  added: []
  patterns:
    - asyncio.gather for parallel diagnostic checks
    - AdminService inheritance for service-role DB access (bypassing RLS)
    - Autonomy gate via _check_autonomy before every tool
    - Python-side grouping over tool_telemetry rows (PostgREST has no GROUP BY)
    - patch.dict(os.environ) for AdminService unit test isolation
key_files:
  created:
    - app/agents/admin/tools/diagnosis.py
    - app/services/feature_adoption_service.py
    - app/agents/admin/tools/adoption.py
    - tests/unit/admin/test_diagnosis_tool.py
    - tests/unit/admin/test_adoption_tool.py
  modified:
    - app/agents/admin/agent.py
decisions:
  - "asyncio.gather runs all four diagnostic checks in parallel — OAuth, health, budget, approvals never block each other"
  - "Health check uses .neq('status','healthy') so only degraded/unhealthy endpoints are returned; test mocks pass empty rows for the all-clear case"
  - "FeatureAdoptionService omits unique_users from per-user compute_adoption results — only meaningful for platform-wide aggregation"
  - "Python-side grouping in FeatureAdoptionService consistent with Phase 64-01 pattern (PostgREST has no GROUP BY)"
  - "patch.dict(os.environ) with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY sentinel values allows AdminService instantiation in unit tests without live DB"
  - "defaultdict(lambda: {'tools': defaultdict(lambda: {'count': 0, 'users': set()})}) for in-memory grouping — avoids any DB aggregation dependency"
metrics:
  duration: "15min"
  completed: "2026-04-13"
  tasks_completed: 2
  files_changed: 6
---

# Phase 69 Plan 01: Admin Self-Diagnosis and Feature Adoption Summary

One-liner: Parallel 4-signal user problem diagnostic with plain-English summary, plus per-agent tool usage adoption metrics backed by tool_telemetry grouping.

## What Was Built

### Task 1 — diagnose_user_problem + get_feature_adoption + FeatureAdoptionService (TDD)

**diagnose_user_problem(user_id)**
- Runs four async checks in parallel via `asyncio.gather`:
  1. `user_mcp_integrations` — flags inactive OAuth connections
  2. `api_health_checks` — flags non-healthy endpoints (`.neq("status","healthy")`)
  3. `ad_budget_caps` — flags rows where `current_spend_usd >= monthly_cap_usd`
  4. `governance_approvals` — flags rows where `status="pending"`
- Each check returns a list of typed issue dicts: `{category, severity, details, recommended_action}`
- `_build_summary()` generates a human-readable `plain_english_summary` — "All systems look good..." or "I found N issue(s)..." with bullet actions
- Returns `{user_id, issues, all_clear, plain_english_summary}` or error dict from autonomy gate

**FeatureAdoptionService(AdminService)**
- Queries `tool_telemetry` for last N days, optionally filtered by `user_id`
- Python-side grouping: `defaultdict` by `(agent_name, tool_name)` with call counts and user sets
- Produces per-agent entries: `agent_name`, `unique_tools_used`, `total_calls`, `top_tools` (top 5), `unique_users` (platform-wide only)
- Returns `{agent_adoption, total_agents_active, total_unique_tools, period_days}`

**get_feature_adoption(days, user_id)**
- Thin wrapper: autonomy gate → `FeatureAdoptionService().compute_adoption()`

### Task 2 — Wire into AdminAgent

- Added two imports to `agent.py` (targeted edit, parallel-safe)
- Added both tools to singleton `tools=[...]` and `create_admin_agent()` factory under `# Phase 69: self-diagnosis and feature adoption` comment
- Appended two instruction sections to `ADMIN_AGENT_INSTRUCTION`: "User Problem Diagnosis (Phase 69)" and "Feature Adoption Metrics (Phase 69)"
- AdminAgent now has 63 tools (up from 61)

## Test Results

14 unit tests, all passing:

| Test | Coverage |
|------|----------|
| test_diagnose_integration_issues | OAuth inactive providers → integration_issues |
| test_diagnose_platform_health_issues | Degraded API endpoints → platform_health_issues |
| test_diagnose_budget_cap_exceeded | Spend >= cap → budget_cap_exceeded with platform/amounts |
| test_diagnose_pending_approvals | Pending governance rows → pending_approvals with count |
| test_diagnose_all_clear | No issues → all_clear=True, empty issues list |
| test_diagnose_plain_english_summary_with_issues | Summary mentions issue count, no raw JSON |
| test_diagnose_plain_english_summary_all_clear | "All systems look good" when no issues |
| test_diagnose_autonomy_blocked | Blocked gate → error dict, no issues key |
| test_get_feature_adoption_structure | Returns agent_adoption with all required fields |
| test_get_feature_adoption_user_filter | user_id forwarded to service.compute_adoption |
| test_get_feature_adoption_platform_wide | Platform-wide includes unique_users per entry |
| test_get_feature_adoption_autonomy_blocked | Blocked gate → error dict |
| test_feature_adoption_service_grouping | AdminAgent row = 3 calls, 2 tools correctly grouped |
| test_feature_adoption_service_user_filter | Per-user result omits unique_users key |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test all_clear case had mismatched mock data**
- **Found during:** Task 1, GREEN phase
- **Issue:** test_diagnose_all_clear passed `health_rows=[{"status":"healthy"}]` as mock return value. Production code queries `.neq("status","healthy")` which returns no rows for a healthy endpoint — the mock bypasses the filter so the "healthy" row was being returned and flagged as an issue
- **Fix:** Updated test to pass `health_rows=[]` (reflecting what `.neq("status","healthy")` would return in reality). Added comment explaining the filter semantics
- **Files modified:** tests/unit/admin/test_diagnosis_tool.py

**2. [Rule 2 - Missing critical functionality] AdminService requires SUPABASE_URL in test**
- **Found during:** Task 1, FeatureAdoptionService unit tests
- **Issue:** `FeatureAdoptionService()` inherits `AdminService.__init__()` which raises `ValueError` when `SUPABASE_URL` env var is absent (as in test environment)
- **Fix:** Added `patch.dict(os.environ, {"SUPABASE_URL": "http://localhost", "SUPABASE_SERVICE_ROLE_KEY": "test-key"})` to the two service-level tests
- **Files modified:** tests/unit/admin/test_adoption_tool.py

**3. [Rule 1 - Bug] Lint: line too long in diagnosis.py docstring**
- **Found during:** Task 2 lint check
- **Issue:** Docstring line `- ``issues``: list of issue dicts (category, severity, details, recommended_action)` exceeded 88-char line limit (E501)
- **Fix:** Wrapped the line; linter subsequently normalized it back to single line (both forms pass)
- **Files modified:** app/agents/admin/tools/diagnosis.py

## Self-Check: PASSED

Files exist:
- app/agents/admin/tools/diagnosis.py — FOUND
- app/services/feature_adoption_service.py — FOUND
- app/agents/admin/tools/adoption.py — FOUND
- tests/unit/admin/test_diagnosis_tool.py — FOUND
- tests/unit/admin/test_adoption_tool.py — FOUND

Commits:
- a4f88e55 — feat(69-01): add diagnose_user_problem, get_feature_adoption tools and FeatureAdoptionService
- 38ff087f — feat(69-01): wire diagnose_user_problem and get_feature_adoption into AdminAgent

AdminAgent tool count: 63 (verified via python -c import check)
All 14 tests: PASSED
Lint: PASSED (0 errors on all 3 new source files)
