---
phase: 71-engine-runtime-fixes
plan: 01
subsystem: services
tags: [async, gemini, genai, event-bus, telemetry, self-improvement]

# Dependency graph
requires: []
provides:
  - "Non-blocking async Gemini client in SelfImprovementEngine"
  - "Correct await-based event bus emit in identify_improvements"
  - "Telemetry metrics (cycle_duration_ms, gemini_call_latency_ms, actions_executed_total) on improvement cycle"
affects: [72-feedback-loop, 73-scheduled-cycles]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "client.aio.models.generate_content for non-blocking async Gemini usage"
    - "Per-call latency tracking via time.perf_counter with instance attribute accumulation"
    - "Structured logger.info with metric fields for observability pipeline pickup"

key-files:
  created:
    - tests/unit/test_self_improvement_engine.py
  modified:
    - app/services/self_improvement_engine.py

key-decisions:
  - "Accumulate gemini latency on instance attribute (_total_gemini_latency_ms) rather than passing through return values -- simpler API surface"
  - "Use getattr with default for _total_gemini_latency_ms accumulation to be safe if called outside run_improvement_cycle"

patterns-established:
  - "google.genai async pattern: client.aio.models.generate_content instead of sync client.models.generate_content"
  - "_patch_genai context manager for test mocking -- patches both sys.modules and the google package attribute"

requirements-completed: [FIX-01, FIX-02, FIX-05]

# Metrics
duration: 7min
completed: 2026-04-12
---

# Phase 71 Plan 01: Self-Improvement Engine Runtime Fixes Summary

**Async Gemini client, corrected event bus await, and cycle telemetry instrumentation for SelfImprovementEngine**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-12T04:14:13Z
- **Completed:** 2026-04-12T04:21:14Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- FIX-01: Replaced blocking sync `client.models.generate_content` with async `client.aio.models.generate_content` so FastAPI event loop is never blocked during Gemini calls
- FIX-02: Replaced `asyncio.get_event_loop().run_until_complete(bus.emit(...))` with direct `await bus.emit(...)` eliminating the RuntimeError crash in identify_improvements
- FIX-05: Added three telemetry metrics to run_improvement_cycle return dict: cycle_duration_ms, gemini_call_latency_ms, actions_executed_total
- Added structured logger.info line for observability pipeline consumption
- 5 unit tests covering all three fixes with proper mocking patterns

## Task Commits

Each task was committed atomically (TDD flow):

1. **Task 1 RED: Failing tests** - `2438062a` (test)
2. **Task 1 GREEN: Implementation + passing tests** - `8aac8b5c` (feat)

## Files Created/Modified
- `app/services/self_improvement_engine.py` - Async Gemini client, fixed event bus emit, telemetry instrumentation
- `tests/unit/test_self_improvement_engine.py` - 5 pytest-asyncio tests covering FIX-01, FIX-02, FIX-05

## Decisions Made
- Accumulate Gemini latency on instance attribute (`_total_gemini_latency_ms`) rather than threading through return values -- keeps the internal API simpler
- Used `getattr(self, "_total_gemini_latency_ms", 0.0)` in `_generate_with_gemini` for safe accumulation when called outside `run_improvement_cycle`
- Created `_patch_genai` context manager in tests to properly handle conftest's google.genai module mock by patching both sys.modules and the google package attribute

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- conftest.py mocks `google.genai` as a bare `types.ModuleType` without `Client`; `patch.dict(sys.modules)` alone was insufficient because `import google.genai` resolves via the google package attribute. Solved with a custom `_patch_genai` context manager that patches both `sys.modules["google.genai"]` and `google.genai` attribute on the package.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SelfImprovementEngine is now safe for async execution in production FastAPI
- Telemetry metrics are available for observability dashboards
- Ready for Phase 72 (feedback loop) and Phase 73 (scheduled cycles) which build on this engine

## Self-Check: PASSED

- [x] app/services/self_improvement_engine.py exists
- [x] tests/unit/test_self_improvement_engine.py exists
- [x] .planning/phases/71-engine-runtime-fixes/71-01-SUMMARY.md exists
- [x] Commit 2438062a (RED tests) exists
- [x] Commit 8aac8b5c (GREEN implementation) exists

---
*Phase: 71-engine-runtime-fixes*
*Completed: 2026-04-12*
