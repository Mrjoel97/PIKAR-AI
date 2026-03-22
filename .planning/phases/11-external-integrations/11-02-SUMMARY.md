---
phase: 11-external-integrations
plan: "02"
subsystem: admin-agent
tags: [integration-tools, adminagent, sentry, posthog, github, autonomy, budget, tdd]
dependency_graph:
  requires: ["11-01"]
  provides: ["admin-integration-tools", "skil-01-cross-service-diagnostics", "skil-02-trend-detection"]
  affects: ["app/agents/admin/agent.py", "app/agents/admin/tools/__init__.py"]
tech_stack:
  added: []
  patterns:
    - "_check_autonomy() self-contained per-module pattern (per analytics.py and users.py)"
    - "_get_integration_config() shared helper returning tuple or error dict"
    - "IntegrationProxyService.call() with fetch_fn injection for clean mocking"
    - "check_session_budget() fails-open on Redis unavailability"
key_files:
  created:
    - app/agents/admin/tools/integrations.py
    - tests/unit/admin/test_integration_tools.py
  modified:
    - app/agents/admin/tools/__init__.py
    - app/agents/admin/agent.py
decisions:
  - "base_url returned from _get_integration_config but ignored by tools (prefixed _base_url) — tools pass config dict to fetch_fn which reads base_url directly from config"
  - "_DEFAULT_SESSION_ID='admin' placeholder for Phase 13 real session IDs — per plan spec"
  - "fetch_fn injected into IntegrationProxyService.call() from integration_proxy.py private helpers — matches actual call signature from Plan 01"
  - "All 6 tools are auto tier — no confirm/blocked variants needed for read-only proxy operations"
metrics:
  duration: "10 min"
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 4
requirements_satisfied: [INTG-01, INTG-02, INTG-03, INTG-04, INTG-06, SKIL-01, SKIL-02]
---

# Phase 11 Plan 02: AdminAgent Integration Tools Summary

**One-liner:** 6 read-only AdminAgent tools (Sentry, PostHog, GitHub) with autonomy enforcement, budget gating, and SKIL-01/SKIL-02 cross-service diagnostic reasoning added to ADMIN_AGENT_INSTRUCTION.

## What Was Built

### Task 1: 6 Integration Tools with TDD Tests

`app/agents/admin/tools/integrations.py` — 6 async AdminAgent tools following the established analytics.py pattern:

| Tool | Provider | Operation | Params |
|---|---|---|---|
| `sentry_get_issues` | sentry | get_issues | limit |
| `sentry_get_issue_detail` | sentry | get_issue_detail | issue_id |
| `posthog_query_events` | posthog | get_events | limit |
| `posthog_get_insights` | posthog | get_insights | — |
| `github_list_prs` | github | get_prs | state |
| `github_get_pr_status` | github | get_pr_status | pr_number |

Each tool follows the same 4-step guard pattern:
1. `_check_autonomy()` — queries `admin_agent_permissions`, returns error/confirm dict or None
2. `_get_integration_config()` — fetches from `admin_integrations`, validates is_active, guards NULL key, decrypts
3. `check_session_budget()` — Redis-backed per-session call budget (fails open on Redis unavailable)
4. `IntegrationProxyService.call()` — cache-check → fetch_fn → cache-set with provider TTL

`tests/unit/admin/test_integration_tools.py` — 10 tests covering all 6 tools with full mock isolation:
- Happy path for each tool verifying correct provider/operation/params
- Blocked autonomy tier (proxy never called)
- Missing integration row (no-config error)
- Budget exhausted (proxy never called)
- NULL api_key_encrypted guard (decrypt never called)

### Task 2: AdminAgent Registration and Diagnostic Skills

`app/agents/admin/tools/__init__.py` — Added imports and `__all__` entries for all 6 integration tools (alphabetical order).

`app/agents/admin/agent.py` — Three changes:
- Import block for integration tools added after analytics imports
- All 6 tools added to both `admin_agent` singleton (24 total tools) and `create_admin_agent()` factory with `# Phase 11: external integrations` comment
- `ADMIN_AGENT_INSTRUCTION` extended with three new sections:
  - **External Integration Tools (Phase 11)** — usage guidance, API key privacy note
  - **Cross-Service Diagnostic Reasoning (SKIL-01)** — 4-step correlation workflow, 5 reasoning patterns, confidence levels
  - **Response Time Degradation Trend Detection (SKIL-02)** — 7-day baseline comparison, 50%/100% thresholds, proactive alerting, 4 degradation patterns

## Verification Results

```
uv run pytest tests/unit/admin/test_integration_tools.py -x -v
→ 10 passed in 3.99s

uv run ruff check app/agents/admin/tools/integrations.py app/agents/admin/agent.py
→ All checks passed!

Singleton tools (24): check_system_health, get_api_health_summary, ...
  sentry_get_issues, sentry_get_issue_detail, posthog_query_events,
  posthog_get_insights, github_list_prs, github_get_pr_status
→ Assertion passed: 22+ tools, sentry and github present

SKIL-01 and SKIL-02 sections present in ADMIN_AGENT_INSTRUCTION
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `base_url` unused variable in all 6 tool unpack assignments**
- **Found during:** Task 1 lint (ruff RUF059)
- **Issue:** `_get_integration_config()` returns a 3-tuple including `base_url`, but tools pass the `config` dict directly to `fetch_fn` which reads `base_url` from config internally — the unpacked `base_url` variable was never used
- **Fix:** Renamed to `_base_url` in all 6 tool functions to satisfy ruff RUF059
- **Files modified:** `app/agents/admin/tools/integrations.py`
- **Commit:** 76ae0fb (included in Task 1 commit after lint fix)

**2. [Rule 3 - Blocking] `IntegrationProxyService.call()` requires `fetch_fn` keyword arg**
- **Found during:** Task 1 implementation — plan described `IntegrationProxyService.call(provider, operation, api_key, config, params)` but actual signature from Plan 01 adds required `fetch_fn` callable
- **Fix:** Each tool passes the corresponding private fetch function from `integration_proxy.py` as `fetch_fn` (`_fetch_sentry_issues`, `_fetch_sentry_issue_detail`, etc.)
- **Files modified:** `app/agents/admin/tools/integrations.py`

## Commits

| Hash | Message |
|---|---|
| `76ae0fb` | feat(11-02): create 6 AdminAgent integration tools with tests |
| `23af07c` | feat(11-02): register integration tools in AdminAgent and add SKIL-01/02 |

## Self-Check: PASSED

| Item | Status |
|---|---|
| `app/agents/admin/tools/integrations.py` | FOUND |
| `tests/unit/admin/test_integration_tools.py` | FOUND |
| `app/agents/admin/tools/__init__.py` | FOUND |
| `app/agents/admin/agent.py` | FOUND |
| Commit `76ae0fb` | FOUND |
| Commit `23af07c` | FOUND |
