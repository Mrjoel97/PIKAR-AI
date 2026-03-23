---
phase: 12-agent-config-feature-flags
plan: "01"
subsystem: database, api
tags: [supabase, redis, python, feature-flags, prompt-injection, difflib, admin-panel]

requires:
  - phase: 07-foundation
    provides: admin_agent_permissions table, admin_config_history table, get_service_client, execute_async pattern
  - phase: 08-health-monitoring
    provides: get_cache_service/_get_redis pattern for direct Redis access in service modules

provides:
  - admin_agent_configs table with versioned instruction storage (10 agents seeded)
  - admin_feature_flags table with Redis read-through caching
  - agent_config_service.py: 8 exported async functions covering full config CRUD lifecycle
  - Prompt injection validation with 6 regex patterns + 32000-char length guard
  - Unified diff generation for instruction change review
  - 25 unit tests covering all service behaviors

affects:
  - 12-02 (config tools/API — builds directly on these service functions)
  - 12-03 (config frontend — depends on API built in 12-02)

tech-stack:
  added: []
  patterns:
    - "get_cache_service()._get_redis() for direct Redis SETEX/GET in service modules (not CacheResult abstraction)"
    - "_SERVICE_CLIENT_PATCH + _EXECUTE_ASYNC_PATCH both required in unit tests — get_service_client() called directly, execute_async wraps the query builder"
    - "inject/validate before any DB write — save_agent_config runs validate_instruction_content before touching Supabase"
    - "defence-in-depth rollback validation — rollback_agent_config re-validates restored text before calling save_agent_config"

key-files:
  created:
    - supabase/migrations/20260323000000_agent_config_feature_flags.sql
    - app/services/agent_config_service.py
    - tests/unit/admin/test_config_service.py
  modified: []

key-decisions:
  - "Placeholder instruction text in SQL seeds ('Default instructions for {name} agent. Edit via admin panel to customize.') — actual Python instruction constants are too large for SQL; service layer detects placeholder and falls back to Python constant"
  - "get_cache_service()._get_redis() used directly (not CacheService.get_generic) — flag cache needs raw SETEX with explicit 60s TTL, not the abstracted CacheResult pattern"
  - "Both _SERVICE_CLIENT_PATCH and _EXECUTE_ASYNC_PATCH required in all async service tests — get_service_client() is called at function body time, execute_async wraps the query chain"
  - "save_agent_config validates injection before any DB read — fail-fast design avoids unnecessary Supabase round-trips on bad input"
  - "rollback_agent_config re-validates restored text — defence-in-depth per RESEARCH.md Pitfall 5; history rows could contain stale injected content"

patterns-established:
  - "Flag cache key format: admin:feature_flag:{flag_key} with 60s TTL via SETEX"
  - "Config history written on every mutation (set_flag, save_agent_config) with config_type + config_key + previous_value/new_value JSON"

requirements-completed: [CONF-01, CONF-02, CONF-03]

duration: 10min
completed: 2026-03-23
---

# Phase 12 Plan 01: Agent Config & Feature Flags — DB + Service Layer Summary

**SQL migration adds versioned agent instruction storage and Redis-cached feature flags; Python service layer provides diff generation, 6-pattern injection validation, and full CRUD with audit history**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-23T01:20:08Z
- **Completed:** 2026-03-23T01:29:27Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- SQL migration creates `admin_agent_configs` and `admin_feature_flags` tables (RLS enabled), seeds 10 agent config rows, 3 feature flag rows, and 10 config-domain permission rows in `admin_agent_permissions`
- `agent_config_service.py` exports all 8 required functions: `generate_instruction_diff`, `validate_instruction_content`, `get_flag`, `set_flag`, `get_agent_config`, `save_agent_config`, `get_config_history`, `rollback_agent_config`
- 25 unit tests all green — covers cache hit/miss, injection detection, diff generation, save/rollback, and history retrieval

## Task Commits

1. **Task 1: Database migration** — `6ede3ec` (feat)
2. **Task 2: Agent config service + tests** — `6e63c83` (feat)

## Files Created/Modified

- `supabase/migrations/20260323000000_agent_config_feature_flags.sql` — 2 new tables (admin_agent_configs, admin_feature_flags) with RLS + 23 seed rows
- `app/services/agent_config_service.py` — 8 async service functions, injection validation, Redis flag caching
- `tests/unit/admin/test_config_service.py` — 25 unit tests (511 lines) covering all behaviors

## Decisions Made

- Placeholder instruction text in SQL seeds — actual Python instruction constants are too long for SQL; the service layer will fall back to Python-defined constants when it detects the placeholder
- `get_cache_service()._get_redis()` used for direct Redis `SETEX`/`GET` (not the `CacheResult` abstraction) — feature flag caching needs raw TTL control
- Both `_SERVICE_CLIENT_PATCH` and `_EXECUTE_ASYNC_PATCH` required in all unit tests — `get_service_client()` is called at function-body time before `execute_async` is reached
- Fail-fast injection validation in `save_agent_config` — returns violations before any Supabase round-trip
- Defence-in-depth re-validation in `rollback_agent_config` — history rows could contain stale injected content from before validation was enforced

## Deviations from Plan

None — plan executed exactly as written.

The one auto-fix applied during Task 2 testing was an omitted `_SERVICE_CLIENT_PATCH` in unit tests (the plan specified patching `execute_async` but `get_service_client()` is called before `execute_async` in several functions). Fixed inline across all affected tests as a Rule 1 bug fix.

## Issues Encountered

`test_get_flag_cache_miss_reads_db` and related tests initially failed because `get_service_client()` is called directly inside service functions before `execute_async` is invoked. The test patch for `execute_async` alone was insufficient. Added `_SERVICE_CLIENT_PATCH` to all tests that exercise code paths touching Supabase. All 25 tests pass after fix.

## User Setup Required

None — no external service configuration required. Migration will be applied to Supabase when `supabase db push` is next run against the target environment.

## Next Phase Readiness

- `admin_agent_configs` and `admin_feature_flags` tables are defined and ready for Plan 02 (admin tools + API router)
- All 8 service functions are importable and tested — Plan 02 can call them directly from tool implementations
- `admin_agent_permissions` seeded with 10 config-domain rows — autonomy enforcement in Plan 02 tools will work immediately

## Self-Check: PASSED

- FOUND: supabase/migrations/20260323000000_agent_config_feature_flags.sql
- FOUND: app/services/agent_config_service.py
- FOUND: tests/unit/admin/test_config_service.py
- FOUND: .planning/phases/12-agent-config-feature-flags/12-01-SUMMARY.md
- FOUND commit: 6ede3ec (migration)
- FOUND commit: 6e63c83 (service + tests)

---
*Phase: 12-agent-config-feature-flags*
*Completed: 2026-03-23*
