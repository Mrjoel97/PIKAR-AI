---
phase: 61-content-agent-enhancement
plan: 02
subsystem: agents
tags: [content-agent, scheduling, content-calendar, platform-timing, adk]

# Dependency graph
requires:
  - phase: 61-content-agent-enhancement
    provides: "Content agent with simple_create_content fast path (61-01)"
provides:
  - "suggest_and_schedule_content tool with suggestion and scheduling modes"
  - "Platform-specific optimal posting time recommendations"
  - "ContentCalendarService integration for one-click scheduling"
  - "POST-CREATION SCHEDULING instruction in Content Director"
affects: [content-agent, content-calendar]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Lazy DB imports for scheduling service testability", "Platform timing lookup tables for deterministic recommendations"]

key-files:
  created:
    - tests/unit/test_suggest_schedule_tool.py
  modified:
    - app/agents/content/tools.py
    - app/agents/content/agent.py

key-decisions:
  - "Pre-computed platform timing lookup tables instead of parsing PLATFORM_GUIDELINES strings at runtime for determinism and testability"
  - "Extractable _today() helper for date mocking in tests without patching datetime globally"
  - "Search starts from tomorrow (today + 1) to avoid same-day scheduling"

patterns-established:
  - "Two-mode tool pattern: schedule=False for suggestion, schedule=True for action -- agent calls twice to give user confirmation control"

requirements-completed: [CONTENT-02]

# Metrics
duration: 9min
completed: 2026-04-10
---

# Phase 61 Plan 02: Schedule Suggestion Tool Summary

**Auto-schedule suggestion tool that recommends optimal posting times per platform and one-click schedules via ContentCalendarService**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-10T12:06:41Z
- **Completed:** 2026-04-10T12:15:49Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- suggest_and_schedule_content tool with dual suggestion/scheduling modes
- Platform-specific optimal timing using PLATFORM_GUIDELINES data (Instagram, LinkedIn, TikTok, YouTube, Twitter, Facebook)
- Content type mapping from agent types (social_post, blog_intro, etc.) to calendar types (social, blog, etc.)
- Content Director instruction updated to always suggest scheduling after content creation
- 6 unit tests covering both modes, platform-specific timing, defaults, and type mapping

## Task Commits

Each task was committed atomically:

1. **Task 1: Create suggest_and_schedule_content tool with tests (TDD)** - `4bf89152` (feat)
2. **Task 2: Wire scheduling tool into Content Director** - `10d14b88` (feat, bundled with 61-01 agent wiring)

## Files Created/Modified
- `app/agents/content/tools.py` - Added suggest_and_schedule_content tool, _compute_optimal_timing, _map_content_type, platform timing lookup tables
- `app/agents/content/agent.py` - Import + tool registration + POST-CREATION SCHEDULING instruction section
- `tests/unit/test_suggest_schedule_tool.py` - 6 unit tests for suggestion mode, scheduling mode, platform timing, defaults, type mapping

## Decisions Made
- Pre-computed platform timing lookup tables (_PLATFORM_FIRST_TIME dict) for deterministic, testable behavior instead of runtime string parsing of PLATFORM_GUIDELINES
- Extracted _today() helper function for clean date mocking in tests without patching datetime.date globally
- Search starts from tomorrow to avoid scheduling content for same day
- Two-mode tool pattern (schedule=False then schedule=True) gives users explicit confirmation before calendar entry creation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Task 2 agent.py changes were bundled into the 61-01 agent wiring commit due to concurrent file modification timing; changes are correctly present in commit 10d14b88

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Content agent now has both fast-path creation (61-01) and post-creation scheduling (61-02)
- Ready for 61-03 (next content agent enhancement plan)
- ContentCalendarService integration is tested and wired

## Self-Check: PASSED

All files verified present, all commits verified in git log.

---
*Phase: 61-content-agent-enhancement*
*Completed: 2026-04-10*
