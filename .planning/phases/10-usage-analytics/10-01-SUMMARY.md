---
phase: 10-usage-analytics
plan: 01
subsystem: database
tags: [supabase, postgresql, analytics, aggregation, python, fastapi]

# Dependency graph
requires:
  - phase: 07-foundation
    provides: admin_agent_permissions table and RLS patterns for admin tables
  - phase: 08-health-monitoring
    provides: agent_telemetry table used as aggregation source
depends_on: []
provides:
  - admin_analytics_daily table (stat_date UNIQUE, DAU/MAU/messages/workflows columns)
  - admin_agent_stats_daily table ((stat_date, agent_name) UNIQUE, success/error/timeout/avg_duration columns)
  - run_daily_aggregation() async function in app/services/analytics_aggregator.py
  - 4 analytics tool permission rows in admin_agent_permissions
affects:
  - 10-02 (analytics API router — reads admin_analytics_daily, admin_agent_stats_daily)
  - 10-03 (analytics dashboard frontend — drives chart data shape)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pre-aggregated summary tables to avoid scanning large event tables on dashboard load
    - Python-side GROUP BY aggregation (avoids Supabase RPC for agent stats grouping)
    - _extract_count() dual-mode: reads data[0]["count"] or falls back to len(data)
    - Query all source tables before upserts (consistent execute_async call ordering for testability)

key-files:
  created:
    - supabase/migrations/20260321700000_analytics_summary_tables.sql
    - app/services/analytics_aggregator.py
    - tests/unit/admin/test_analytics_service.py
  modified: []

key-decisions:
  - "10-01: Agent telemetry queried before analytics daily upsert — consistent execute_async call ordering makes mock-based tests reliable without positional fragility"
  - "10-01: Python-side aggregation for agent stats — Supabase Python client cannot express GROUP BY + FILTER in one call; aggregating in Python avoids RPC and is readable"
  - "10-01: _extract_count() supports both count-dict result shape and raw row list — handles both Supabase count responses and raw row fetches transparently"
  - "10-01: admin_analytics_daily uses DAU/MAU computed from sessions.updated_at, not auth.users — sessions.user_id is TEXT not UUID, no JOIN needed"

patterns-established:
  - "Analytics tables: RLS enabled, no policies (service-role-only), matching all Phase 7 admin tables"
  - "Idempotent aggregation: upsert with on_conflict=stat_date (or stat_date,agent_name) means re-running for same date overwrites not duplicates"
  - "TDD ordering: write failing tests establishing call contract, then implement to match — call ordering matters for positional mock dispatch"

requirements-completed: [ANLT-01, ANLT-02]

# Metrics
duration: 25min
completed: 2026-03-22
---

# Phase 10 Plan 01: Analytics Data Foundation Summary

**Pre-aggregated admin_analytics_daily and admin_agent_stats_daily tables with idempotent nightly aggregation service computing DAU/MAU/messages/workflows from Supabase event tables**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-22T01:58:59Z
- **Completed:** 2026-03-22T02:23:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- SQL migration creating two summary tables with correct constraints, indexes, RLS, and 4 analytics permission seed rows
- `run_daily_aggregation()` service computing DAU (distinct sessions), MAU (30-day trailing), message count, workflow count, and per-agent stats from agent_telemetry
- 6 unit tests (TDD RED/GREEN) covering return shape, value correctness, per-agent upserts, empty table handling, idempotency, and default-to-yesterday date behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Create analytics summary table migration** - `e734147` (feat)
2. **Task 2: TDD RED — failing tests** - `8bb018a` (test)
3. **Task 2: TDD GREEN — aggregation service implementation** - `4d91335` (feat)

## Files Created/Modified

- `supabase/migrations/20260321700000_analytics_summary_tables.sql` — Two summary tables with UNIQUE constraints, DESC indexes, RLS enabled, and 4 permission seed rows
- `app/services/analytics_aggregator.py` — `run_daily_aggregation()` async function with `_extract_count()` helper
- `tests/unit/admin/test_analytics_service.py` — 6 pytest-asyncio tests covering all behavior contracts

## Decisions Made

- **Python-side aggregation for agent stats:** Supabase Python client cannot express `GROUP BY agent_name WITH COUNT FILTER` in a single fluent call. Fetching raw rows and aggregating in Python avoids needing an RPC and keeps the code readable. Acceptable volume at daily batch scale.
- **Query order — agent_telemetry before upserts:** Execute all source queries first, then upserts. This makes the `execute_async` call sequence consistent and mock-positional tests reliable without brittle counting.
- **`_extract_count()` dual-mode:** Handles both `[{"count": N}]` (Supabase `.select("count")` response) and raw row lists (`len(data)`). Allows the same pattern whether using count-select or fetching all rows.
- **`ON CONFLICT (action_category, action_name)` for permissions:** The `admin_agent_permissions` UNIQUE constraint from Phase 7 is on `(action_category, action_name)` — not just `action_name`. Plan spec had `ON CONFLICT (action_name)` which would have failed. Fixed to match the established schema constraint.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ON CONFLICT clause for admin_agent_permissions seed**
- **Found during:** Task 1 (migration creation)
- **Issue:** Plan specified `ON CONFLICT (action_name) DO NOTHING` but the Phase 7 migration established `UNIQUE (action_category, action_name)` — single-column conflict would cause a constraint error
- **Fix:** Changed to `ON CONFLICT (action_category, action_name) DO NOTHING` matching the actual unique constraint
- **Files modified:** `supabase/migrations/20260321700000_analytics_summary_tables.sql`
- **Verification:** Matches established pattern in `20260321600000_user_management_permissions.sql`
- **Committed in:** `e734147` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed execute_async call ordering to match test contract**
- **Found during:** Task 2 GREEN phase
- **Issue:** Initial implementation upserted `admin_analytics_daily` (call 5) before querying `agent_telemetry` (call 6). Tests dispatch mock results positionally by call count, so agent_telemetry data landed in the upsert slot, producing `agent_name='unknown'`
- **Fix:** Moved agent_telemetry query before the analytics daily upsert — all source queries first, then all upserts
- **Files modified:** `app/services/analytics_aggregator.py`
- **Verification:** All 6 tests pass after reorder
- **Committed in:** `4d91335` (Task 2 feat commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- `uv` not on PATH in bash shell — used `cmd //c "uv run ..."` workaround for all Python/test commands. Standard on this Windows dev environment.

## User Setup Required

None — no external service configuration required. Migration will be applied via `supabase db push` as part of standard deployment.

## Next Phase Readiness

- `admin_analytics_daily` and `admin_agent_stats_daily` tables ready to receive aggregation data
- `run_daily_aggregation()` ready to be wired into a scheduled endpoint (Phase 10-02)
- Analytics API router (10-02) can now query these summary tables for fast dashboard reads
- No blockers

---
*Phase: 10-usage-analytics*
*Completed: 2026-03-22*
