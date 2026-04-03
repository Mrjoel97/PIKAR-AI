---
phase: 37-sme-department-coordination
plan: "02"
subsystem: api
tags: [routing, agents, department, keyword-detection, prompt-engineering, python]

# Dependency graph
requires:
  - phase: 37-sme-department-coordination
    provides: department_tasks migration and DepartmentTaskService (plan 37-01)
provides:
  - DEPARTMENT_ROUTING dict mapping 10 department types to agent names and keyword patterns
  - detect_department() function with word-boundary-aware keyword matching
  - 22 unit tests covering all 6 core SME departments and edge cases
  - DEPARTMENT-AWARE ROUTING section in ExecutiveAgent instruction
affects:
  - executive agent routing behavior for SME/Enterprise users
  - any future plan that adds department-specific prompt logic

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Word-boundary regex matching for keyword detection (re.compile with \\b anchors)"
    - "Compound keyword tie-breaking: count first, then longest matched keyword length"
    - "DepartmentRoute dataclass for typed routing configuration"

key-files:
  created:
    - app/config/department_routing.py
    - tests/unit/test_department_routing.py
  modified:
    - app/prompts/executive_instruction.txt

key-decisions:
  - "Used word-boundary regex (\\b) instead of plain substring matching to prevent false positives (e.g. 'hr' in 'share')"
  - "Tie-breaking: prefer department with highest keyword match count; on tie, prefer longest matched keyword"
  - "Added compound keyword 'seo strategy' to MARKETING to resolve ambiguity with STRATEGIC 'strategy' keyword"
  - "10 departments total in config (6 core SME + CONTENT, STRATEGIC, SUPPORT, DATA) matching seeded DB values"

patterns-established:
  - "Department routing config lives in app/config/ alongside feature_gating.py"
  - "detect_department returns (dept_type, agent_name) tuple or None — callers must handle None"

requirements-completed: [DEPT-03]

# Metrics
duration: 20min
completed: 2026-04-03
---

# Phase 37 Plan 02: SME Department Routing Config Summary

**Keyword-based department detection with word-boundary regex matching routing queries to 10 specialist agents, plus ExecutiveAgent prompt engineering for automatic SME department delegation**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-03T22:03:00Z
- **Completed:** 2026-04-03T22:23:06Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `app/config/department_routing.py` with `DepartmentRoute` dataclass, `DEPARTMENT_ROUTING` dict (10 departments), and `detect_department()` function
- Implemented word-boundary-aware keyword matching using pre-compiled regex patterns — prevents "hr" matching inside "share" or "their"
- Added 22 unit tests via TDD covering all 6 core SME departments, edge cases (None returns), case insensitivity, partial-word false positives, and tuple format
- Inserted `DEPARTMENT-AWARE ROUTING` section into `app/prompts/executive_instruction.txt` with routing table for 6 departments and 5 routing rules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create department routing config with keyword detection** - `0d2dec6` (feat)
2. **Task 2: Enhance ExecutiveAgent instruction with department routing guidance** - `1ad096b` (feat)

**Plan metadata:** to be added in final commit

_Note: Task 1 used TDD (tests written first, confirmed RED, then implementation made them GREEN)_

## Files Created/Modified

- `app/config/department_routing.py` — DepartmentRoute dataclass, DEPARTMENT_ROUTING dict (10 entries), detect_department() with word-boundary regex matching
- `tests/unit/test_department_routing.py` — 22 unit tests covering all 6 core SME departments plus edge cases
- `app/prompts/executive_instruction.txt` — Added DEPARTMENT-AWARE ROUTING section (22 new lines) between PERSONA-AWARE ROUTING and BEHAVIOR GUIDELINES

## Decisions Made

- **Word-boundary regex over substring**: Used `\b` anchors to prevent "hr" matching inside "share"/"their". Pure `.in` substring matching would cause false positives on short keywords.
- **Tie-breaking strategy**: Count of matched keywords wins first; on a count tie, the department with the longest individual keyword match wins (more specific match preferred). This resolved "seo strategy" ambiguity between MARKETING and STRATEGIC.
- **Compound keyword addition**: Added "seo strategy" and "marketing strategy" to MARKETING keywords so domain-specific compound phrases beat generic single-word matches from other departments.
- **10 departments in config**: Included all 10 department types seeded in the DB (not just the 6 core SME ones) so the config is the single source of truth for all routing decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed tie-breaking logic using actual keyword length instead of regex pattern string length**
- **Found during:** Task 1 (TDD GREEN phase — test_detect_department_marketing_seo failed)
- **Issue:** `_build_patterns` stored only compiled regex objects. The tie-breaker used `len(pattern.pattern)` which measured the full regex string (e.g. `\bseo\b` = 7 chars) rather than the actual keyword length (3), causing "strategy" (8 chars) to win over "seo" (3 chars) when both had 1 match each
- **Fix:** Changed `_build_patterns` return type to `list[tuple[re.Pattern, int]]` storing `(pattern, kw_len)` pairs. Also added "seo strategy" as a compound MARKETING keyword so the phrase scores 2 matches vs STRATEGIC's 1
- **Files modified:** `app/config/department_routing.py`
- **Verification:** `test_detect_department_marketing_seo` and all 22 tests pass
- **Committed in:** `0d2dec6` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for correctness — the routing algorithm would have given wrong results for queries containing both domain-specific and general-purpose keywords. No scope creep.

## Issues Encountered

- `uv` not on PATH in bash shell. Found at `/c/Users/expert/AppData/Roaming/Python/Python313/Scripts/uv.exe` and used the absolute path for all test invocations.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `detect_department()` is importable and tested — ready for use in the ExecutiveAgent tool layer or middleware
- `DEPARTMENT_ROUTING` dict provides the full agent-name mapping needed by any routing logic in future plans
- ExecutiveAgent now has explicit instruction for department-first routing on SME/Enterprise queries
- Phase 37 Plan 03 (if it exists) can reference `app/config/department_routing.py` as the canonical routing authority

## Self-Check: PASSED

- FOUND: app/config/department_routing.py
- FOUND: tests/unit/test_department_routing.py
- FOUND: .planning/phases/37-sme-department-coordination/37-02-SUMMARY.md
- FOUND: commit 0d2dec6
- FOUND: commit 1ad096b

---
*Phase: 37-sme-department-coordination*
*Completed: 2026-04-03*
