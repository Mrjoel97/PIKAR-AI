---
phase: 13-interactive-impersonation
plan: 02
subsystem: backend
tags: [admin-agent, user-intelligence, impersonation, tdd, skil-03, skil-04]
dependency_graph:
  requires:
    - 13-01 (impersonation_service, admin_impersonation_sessions table, activate_impersonation permission seed)
  provides:
    - users_intelligence.py (get_at_risk_users, get_user_support_context)
    - impersonate_user upgraded to interactive session mode
    - AdminAgent with 44 tools + SKIL-03/SKIL-04 instructions
  affects:
    - app/agents/admin/tools/users.py
    - app/agents/admin/agent.py
    - tests/unit/admin/test_user_tools.py
tech_stack:
  added: []
  patterns:
    - TDD (RED→GREEN per task)
    - Service-role Supabase client + execute_async for all DB reads
    - Module-level IntegrationProxyService import for clean patch targets
    - asyncio.to_thread for synchronous Supabase auth.admin calls
    - Python-side aggregation for event counting (acceptable at admin query scale, per Phase 10 decision)
    - Direct _check_autonomy patch in tests (avoids leaking Supabase env into autonomy mock)
key_files:
  created:
    - app/agents/admin/tools/users_intelligence.py
    - tests/unit/admin/test_user_intelligence_tools.py
  modified:
    - app/agents/admin/tools/users.py
    - app/agents/admin/agent.py
    - tests/unit/admin/test_user_tools.py
decisions:
  - "IntegrationProxyService imported at module level (not lazy inside function) — enables clean patch target at app.agents.admin.tools.users_intelligence.IntegrationProxyService without create=True"
  - "get_at_risk_users filters users where prior_count==0 to avoid division-by-zero and meaningless 100% decline — only users with measurable prior activity are flagged"
  - "Action name changed from impersonate_user to activate_impersonation — matches admin_agent_permissions seed row added in Plan 01 migration"
  - "test_impersonate_user_confirm_tier updated to patch _check_autonomy directly — pre-existing patch architecture in test_user_tools.py cannot reach _autonomy.py's supabase_client via the tools.users mock path"
  - "E402 lint fix: moved _check_autonomy import from mid-file to top of imports in users.py — pre-existing style issue surfaced by ruff during plan"
  - "AdminAgent tool count is 44 (not 41 as estimated) — pre-existing baseline already had 42 tools; plan estimate was off by 3"
metrics:
  duration: "24 min"
  completed: "2026-03-23"
  tasks_completed: 2
  files_created: 2
  files_modified: 3
  tests_added: 10
---

# Phase 13 Plan 02: User Intelligence Tools + Interactive Impersonation Summary

**One-liner:** AdminAgent user intelligence layer with SKIL-03 at-risk detection (declining usage + login + Stripe billing), SKIL-04 support playbooks, and impersonate_user upgraded from read-only URL to interactive 30-minute session via create_impersonation_session.

## What Was Built

### `app/agents/admin/tools/users_intelligence.py` (new)

**Tool 1: `get_at_risk_users(threshold_days_inactive=7)`** (SKIL-03)
- Queries `sessions` table for distinct users active in the last 28 days
- Per user: counts `session_events` in current 14-day window vs prior 14-day window; flags >50% decline
- Fetches `last_sign_in_at` via `asyncio.to_thread(client.auth.admin.get_user_by_id, uid)`
- Filters to users whose last login exceeds `threshold_days_inactive` days
- Attempts Stripe billing status via `IntegrationProxyService().call("stripe", ...)` — degrades to `"unknown (Stripe not configured)"` on any exception
- Returns `{"at_risk_users": [...], "criteria": {...}}` with per-user: user_id, email, last_sign_in_at, activity_decline_pct, billing_status, risk_factors

**Tool 2: `get_user_support_context(user_id)`** (SKIL-04)
- Fetches last 10 session_events for usage summary (message count last 7 days, last activity)
- Queries `session_events` with `event_type='tool_error'` in last 48h for error patterns
- Counter-aggregates errors by (agent_name, error_type) — returns sorted by frequency
- Fetches `user_executive_agents` for persona and onboarding_completed
- Builds `suggested_steps` list based on error rate, zero-activity, and onboarding state
- Includes `allow_listed_actions` from `IMPERSONATION_ALLOWED_PATHS` so AdminAgent knows safe endpoints

### `app/agents/admin/tools/users.py` (upgraded)

**`impersonate_user` tool (Phase 13 upgrade):**
- Changed autonomy action name from `"impersonate_user"` to `"activate_impersonation"` (matches Plan 01 permission seed)
- On auto tier: calls `create_impersonation_session(admin_user_id=None, target_user_id=user_id)`
- Calls `log_admin_action` with `source="impersonation"` and `impersonation_session_id=session["id"]`
- Returns `{"impersonation_url": ..., "mode": "interactive", "session_id": ..., "expires_at": ...}`
- Confirm tier message updated to describe 30-minute interactive session
- Moved `_check_autonomy` import to module top (fixed pre-existing E402 lint)

### `app/agents/admin/agent.py` (upgraded)

- Added imports for `get_at_risk_users`, `get_user_support_context`
- Both tools registered in `admin_agent` singleton and `create_admin_agent()` factory (with `# Phase 13: user intelligence` comment block)
- Available tools line updated: `Phase 9+13` listing now includes `get_at_risk_users, get_user_support_context`
- Added **SKIL-03 section** with 5-step at-risk user presentation pattern (watch list, activity decline, billing flag, Stripe suggestion, concrete outreach)
- Added **SKIL-04 section** with 4-step support brief pattern (usage, errors, troubleshooting, allow-list enforcement)

## Tests

| File | Tests | Result |
|------|-------|--------|
| test_user_intelligence_tools.py | 8 | PASS |
| test_user_tools.py (impersonate) | 2 | PASS |
| **New tests total** | **10** | **10/10** |

**Pre-existing failures** (5 in test_user_tools.py, unrelated to Phase 13):
- `test_suspend_user_confirm_tier`, `test_unsuspend_user_confirm_tier`, `test_change_persona_confirm_tier`, `test_blocked_tool_returns_error_suspend`, `test_blocked_tool_returns_error_list_users`
- Root cause: `_autonomy.py` imports `supabase_client.get_service_client`; tests patch `tools.users.get_service_client` — different module. The autonomy check falls through with "defaulting to auto" warning. Pre-existing before Plan 01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IntegrationProxyService lazy import not patchable**
- **Found during:** Task 1 (TDD GREEN debugging)
- **Issue:** `from app.services.integration_proxy import IntegrationProxyService` was inside the function body, so `app.agents.admin.tools.users_intelligence.IntegrationProxyService` didn't exist as a module attribute — `patch()` raised AttributeError
- **Fix:** Moved import to module level; removed duplicate lazy import from function body
- **Files modified:** app/agents/admin/tools/users_intelligence.py
- **Commit:** bf7fbb5

**2. [Rule 1 - Bug] E402 lint: `_check_autonomy` import mid-file in users.py**
- **Found during:** Task 2 (ruff check)
- **Issue:** The `_check_autonomy` import in users.py was placed after a comment block rather than at the top of imports, causing E402 violation
- **Fix:** Moved import to top of import block
- **Files modified:** app/agents/admin/tools/users.py
- **Commit:** ba498e9

**3. [Rule 1 - Bug] test_impersonate_user_confirm_tier test needed updating**
- **Found during:** Task 2 (test run after impersonate_user upgrade)
- **Issue:** Test patched `tools.users.get_service_client` which doesn't reach `_autonomy.py`'s client; also asserted `action == "impersonate_user"` but the action name was changed to `"activate_impersonation"`
- **Fix:** Test now patches `_check_autonomy` directly with a confirm-gate dict; asserts `action == "activate_impersonation"` and that description contains "interactive". Added `test_impersonate_user_auto_tier_interactive_session` to verify Phase 13 auto-tier path
- **Files modified:** tests/unit/admin/test_user_tools.py
- **Commit:** ba498e9

### Tool Count Deviation

Plan estimated 38 existing + 3 new = 41 tools. Actual count: 42 pre-existing + 2 new = 44 tools. The plan counted 38 as baseline (from an earlier admin state); the actual singleton had 42 by the time Plan 02 executed. Both new tools (`get_at_risk_users`, `get_user_support_context`) are registered correctly.

## Pre-existing Failures (Out of Scope)

- `tests/unit/admin/test_user_tools.py` — 5 confirm/blocked tier tests failing due to `_autonomy.py` supabase_client patch architecture mismatch. Confirmed pre-existing via `git stash` verification.
- `tests/unit/admin/test_analytics_tools.py::test_get_usage_stats_blocked_returns_error` — also pre-existing (noted in Plan 01 SUMMARY).

## Self-Check: PASSED

Files created:
- FOUND: app/agents/admin/tools/users_intelligence.py
- FOUND: tests/unit/admin/test_user_intelligence_tools.py

Commits:
- FOUND: bf7fbb5 (feat(13-02): user intelligence tools)
- FOUND: ba498e9 (feat(13-02): upgrade impersonate_user to interactive sessions + register intelligence tools)
