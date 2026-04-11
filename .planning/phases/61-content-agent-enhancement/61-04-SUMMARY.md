---
phase: 61-content-agent-enhancement
plan: "04"
subsystem: api
tags: [content, analytics, social, engagement, suggestions, heuristic]

# Dependency graph
requires:
  - phase: 61-02
    provides: ContentCalendarService with published item tracking and status lifecycle
provides:
  - ContentPerformanceService with get_published_content, fetch_engagement_for_item, generate_suggestions, compute_aggregate_metrics, get_performance_summary
  - get_content_performance tool in content/tools.py
  - CONTENT PERFORMANCE FEEDBACK LOOP instruction block in Content Director
affects:
  - 61-content-agent-enhancement
  - content-agent
  - social-analytics

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level callable stub (not class import) for lazy-loadable dependencies that need patch-friendly test mocking
    - Heuristic suggestion engine with priority ordering (high/medium/low) and 5-suggestion cap

key-files:
  created:
    - app/services/content_performance_service.py
    - tests/unit/test_content_performance_service.py
  modified:
    - app/agents/content/tools.py
    - app/agents/content/agent.py

key-decisions:
  - "Module-level ContentCalendarService is a lazy factory function (not a class import) — avoids Supabase chain at import time while remaining patch-friendly for tests"
  - "get_social_analytics re-exported at module level from lazy wrapper so tests can patch app.services.content_performance_service.get_social_analytics"
  - "Three heuristic suggestion rules shipped: low engagement rate (<2%), high likes/low shares ratio (>10x), platform outperformance (>=2x ratio) — covers the plan's main patterns without ML"

patterns-established:
  - "Lazy callable pattern: module-level function that does the lazy import and returns a service instance — compatible with @patch without triggering the full import chain"
  - "Performance feedback loop wiring: service -> tool function -> agent instruction section -> factory tools list"

requirements-completed:
  - CONTENT-04

# Metrics
duration: 20min
completed: 2026-04-11
---

# Phase 61 Plan 04: Content Performance Feedback Loop Summary

**Heuristic engagement feedback loop for published content: ContentPerformanceService fetches engagement from social_analytics, generates actionable improvement suggestions, surfaced via get_content_performance tool in Content Director**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-11T13:23:31Z
- **Completed:** 2026-04-11T13:43:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- ContentPerformanceService with full pipeline: fetch published calendar items, retrieve per-post engagement metrics from social_analytics, compute aggregate totals/averages, generate heuristic suggestions, return structured summary
- Three suggestion rules: low overall engagement rate (<2% triggers "high" priority), high likes but low shares (>10x ratio triggers shareability CTA suggestion), platform outperformance (>=2x engagement ratio triggers channel focus suggestion)
- get_content_performance async tool wired into Content Director with CONTENT PERFORMANCE FEEDBACK LOOP instruction block covering when to surface data and how to connect it to future content strategy
- 7 unit tests covering all plan scenarios — all pass in test environment without Supabase/Redis dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: ContentPerformanceService with performance fetching and suggestion generation** - `e5ddb0ab` (feat)
2. **Task 2: get_content_performance tool and Content Director wiring** - `b8bd4c5f` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `app/services/content_performance_service.py` - ContentPerformanceService: get_published_content, fetch_engagement_for_item, generate_suggestions, compute_aggregate_metrics, get_performance_summary
- `tests/unit/test_content_performance_service.py` - 7 unit tests covering all six plan scenarios
- `app/agents/content/tools.py` - Added get_content_performance async tool function
- `app/agents/content/agent.py` - Imported get_content_performance, added CONTENT PERFORMANCE FEEDBACK LOOP instruction section, added tool to create_content_agent() factory

## Decisions Made
- Module-level `ContentCalendarService` is implemented as a lazy factory function rather than a class import — this avoids pulling the Supabase chain at import time (which broke test collection in this Python environment) while keeping the name patchable via `@patch("app.services.content_performance_service.ContentCalendarService")`
- `get_social_analytics` re-exported at module level from the `_get_social_analytics` lazy wrapper so tests can patch at `app.services.content_performance_service.get_social_analytics` without importing the social analytics module chain
- Three suggestion rules shipped (engagement, shareability, platform) covering the plan's main heuristic patterns — timing and format rules were not implemented as the data shape (post timestamps, media type) is not present in the current calendar item schema

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed module-level ContentCalendarService import breaking test collection**
- **Found during:** Task 1 (TDD RED phase — tests failed to collect)
- **Issue:** Prior code had `from app.services.content_calendar_service import ContentCalendarService` at module level (line 48), which triggered the full Supabase async client chain (`supabase._async`) — a module not available in the lightweight test Python environment. Tests failed at collection with `ModuleNotFoundError: No module named 'supabase._async'`
- **Fix:** Converted module-level class import to a lazy factory function `ContentCalendarService()` that defers the real import inside the function body. This matches the `get_social_analytics` pattern already used in the same file and preserves the patch path
- **Files modified:** `app/services/content_performance_service.py`
- **Verification:** All 7 tests now collect and pass; `ruff check` passes on the service file
- **Committed in:** `e5ddb0ab` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug fix)
**Impact on plan:** Necessary correctness fix. The lazy import pattern is the established project convention for services with heavy dependency chains. No scope creep.

## Issues Encountered
- Pre-existing `RUF013` lint errors in `app/agents/content/tools.py` (implicit Optional in `update_content`, `list_content`) and `app/agents/content/agent.py` (`create_content_agent` `output_key` parameter) — these are out-of-scope pre-existing issues. Logged here, not fixed.

## User Setup Required
None - no external service configuration required. ContentPerformanceService reads from existing social_analytics integration when post IDs are present in published calendar item metadata.

## Next Phase Readiness
- Content performance feedback loop complete — Content Director can now report engagement metrics and improvement suggestions for published content
- Phase 61 content agent enhancement series is complete across 4 plans (01: simple create, 02: scheduling, 03: brand voice, 04: performance feedback)
- Pre-existing `RUF013` implicit Optional issues in content/tools.py and content/agent.py are candidates for cleanup in Phase 70 (Degraded Tool Cleanup)

---
*Phase: 61-content-agent-enhancement*
*Completed: 2026-04-11*
