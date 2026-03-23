---
phase: 12-agent-config-feature-flags
plan: 02
subsystem: admin-agent-config
tags: [admin-panel, agent-config, feature-flags, autonomy-permissions, runtime-injection, tdd]
one_liner: "10 AdminAgent config tools + 11 REST endpoints for agent config/flags/permissions + async runner factory with live DB instruction injection"

dependency_graph:
  requires:
    - "12-01 (agent_config_service, admin_agent_configs table, admin_feature_flags table)"
    - "07-foundation (AdminAgent singleton, create_admin_agent factory, per-request runner pattern)"
    - "11-external-integrations (integrations.py tool pattern, autonomy enforcement pattern)"
  provides:
    - "10 config-domain tools callable from AdminAgent chat"
    - "11 REST endpoints at /admin/config/* for frontend config page (Plan 03)"
    - "Runtime instruction injection: admin edits take effect on next chat message"
  affects:
    - "app/routers/admin/chat.py (runner factory now async, uses factory not singleton)"
    - "app/agents/admin/agent.py (10 new tools, updated instructions, instruction_override param)"
    - "app/routers/admin/__init__.py (config router wired)"
    - "app/routers/admin/audit.py (pre-existing async bug fixed)"

tech_stack:
  added: []
  patterns:
    - "TDD (RED-GREEN) for both tasks"
    - "Autonomy gate pattern (check_autonomy before each tool, confirm-tier returns requires_confirmation)"
    - "Service delegation pattern (tools import and delegate to agent_config_service)"
    - "Runtime instruction injection via create_admin_agent(instruction_override=...) from DB"
    - "Async runner factory pattern (await _make_admin_runner() instead of sync call)"

key_files:
  created:
    - path: "app/agents/admin/tools/config.py"
      description: "10 AdminAgent config tools with autonomy enforcement (6 auto, 4 confirm)"
    - path: "app/routers/admin/config.py"
      description: "11 REST endpoints at /admin/config/* for agent config CRUD, flags, permissions, MCP"
    - path: "tests/unit/admin/test_config_tools.py"
      description: "20 tool unit tests (autonomy gates, success paths, SKIL-07/08)"
    - path: "tests/unit/admin/test_config_api.py"
      description: "17 API endpoint tests (auth, CRUD shapes, injection 422, runner wiring)"
  modified:
    - path: "app/agents/admin/tools/__init__.py"
      description: "Added 10 config tools to imports and __all__"
    - path: "app/agents/admin/agent.py"
      description: "Added 10 config tools to singleton + factory tools lists; updated ADMIN_AGENT_INSTRUCTION with Phase 12 section + SKIL-07/08 blocks; added instruction_override param to create_admin_agent()"
    - path: "app/routers/admin/__init__.py"
      description: "Wired config router with admin-config tag"
    - path: "app/routers/admin/chat.py"
      description: "_make_admin_runner() changed to async; now fetches live instructions from DB before each request via get_agent_config('admin')"
    - path: "app/routers/admin/audit.py"
      description: "Fixed pre-existing bug: _resolve_admin_emails was sync def with await inside; corrected to async def"

decisions:
  - "_make_admin_runner() made async (not a new module-level coroutine) — keeps the import pattern clean while allowing DB fetch before agent creation"
  - "instruction_override guard checks for 'Default instructions for' sentinel to distinguish placeholder rows from real edits — consistent with service layer decision from Plan 01"
  - "create_admin_agent() falls back to ADMIN_AGENT_INSTRUCTION constant when instruction_override is None — singleton behavior unchanged, only per-request factory path uses DB"
  - "get_agent_config_from_service alias in chat.py module scope — enables clean patch target for unit tests without patching inside a nested try block"
  - "config router mounted with tags=['admin-config'] — separates Swagger docs from main admin tag"
  - "audit.py _resolve_admin_emails async fix: pre-existing SyntaxError (await in sync def) blocked __init__.py import; fixed inline per Rule 1"

metrics:
  duration: "18 min"
  completed_date: "2026-03-23"
  tasks_completed: 2
  files_created: 4
  files_modified: 5
  tests_added: 37
---

# Phase 12 Plan 02: AdminAgent Config Tools + REST API Summary

10 AdminAgent config tools + 11 REST endpoints for agent config/flags/permissions + async runner factory with live DB instruction injection.

## What Was Built

### Task 1: AdminAgent Config Tools (10 tools)

`app/agents/admin/tools/config.py` implements 10 tools following the `integrations.py` pattern:

**6 auto-tier tools (read-only):**
- `get_agent_config(agent_name)` — delegates to `agent_config_service.get_agent_config()`
- `get_config_history(agent_name, limit)` — delegates to service, returns newest-first
- `get_feature_flags()` — queries `admin_feature_flags` directly
- `get_autonomy_permissions(category)` — queries `admin_agent_permissions`
- `assess_config_impact(agent_name)` (SKIL-07) — WorkflowRegistry + 7-day telemetry, risk assessment
- `recommend_config_rollback(agent_name)` (SKIL-08) — pre/post stats comparison, >5% drop triggers recommend

**4 confirm-tier tools (require confirmation_token):**
- `update_agent_config(agent_name, new_instructions, token)` — injection validation via service
- `rollback_agent_config(history_id, agent_name, token)` — delegates to service rollback
- `toggle_feature_flag(flag_key, enabled, token)` — delegates to service `set_flag()`
- `update_autonomy_permission(action_name, new_level, token)` — validates level in frozenset, updates DB

All tools wired into both `admin_agent` singleton and `create_admin_agent()` factory. `ADMIN_AGENT_INSTRUCTION` updated with Phase 12 section listing all tools plus SKIL-07/08 reasoning blocks.

### Task 2: REST API + Runtime Instruction Injection

`app/routers/admin/config.py` provides 11 endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | /config/agents | List all configs (no full instructions) |
| GET | /config/agents/{name} | Full config with instructions (404 on miss) |
| POST | /config/agents/{name}/preview-diff | Unified diff without saving |
| PUT | /config/agents/{name} | Save instructions (422 on injection) |
| GET | /config/agents/{name}/history | Version history |
| POST | /config/agents/{name}/rollback | Restore previous version |
| GET | /config/flags | List all feature flags |
| PUT | /config/flags/{key} | Toggle flag |
| GET | /config/permissions | List all autonomy tiers |
| PUT | /config/permissions/{action} | Update autonomy tier (422 on invalid) |
| GET | /config/mcp-endpoints | MCP endpoint configs (read-only) |

**CRITICAL runtime injection wiring (addresses RESEARCH.md Pitfall 1):**

`_make_admin_runner()` in `chat.py` is now `async def`. Before each chat request it:
1. Calls `get_agent_config_from_service("admin")` to read live DB instructions
2. If the row exists and does not contain the placeholder sentinel, passes `instruction_override=config["current_instructions"]` to `create_admin_agent()`
3. Falls back to hardcoded `ADMIN_AGENT_INSTRUCTION` constant on any DB failure

This means admin-edited instructions take effect on the very next chat message without a redeploy.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `_resolve_admin_emails` async syntax error in audit.py**
- **Found during:** Task 2 (import chain from `__init__.py` triggered the error)
- **Issue:** `_resolve_admin_emails` was defined as `def` (sync) but contained `await asyncio.gather(...)` inside — a Python `SyntaxError` that blocked the entire `app.routers.admin` package import
- **Fix:** Changed `def _resolve_admin_emails` to `async def _resolve_admin_emails` and added `await` at the call site
- **Files modified:** `app/routers/admin/audit.py`
- **Commit:** 413610f

## Self-Check: PASSED

All created files verified on disk. Both task commits verified in git log.

| Check | Result |
|-------|--------|
| app/agents/admin/tools/config.py | FOUND |
| app/routers/admin/config.py | FOUND |
| tests/unit/admin/test_config_tools.py | FOUND |
| tests/unit/admin/test_config_api.py | FOUND |
| .planning/phases/12-agent-config-feature-flags/12-02-SUMMARY.md | FOUND |
| Commit 5baf788 (Task 1 — config tools) | FOUND |
| Commit 413610f (Task 2 — REST API + injection wiring) | FOUND |
| 37 tests pass | PASSED |
