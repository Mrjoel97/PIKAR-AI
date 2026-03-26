---
phase: 28-persona-agent-equalization
plan: 01
subsystem: agents
tags: [persona, policy-registry, prompt-fragments, agent-routing, equalization]

# Dependency graph
requires: []
provides:
  - "ALL_AGENT_NAMES constant in policy_registry.py for universal agent access"
  - "Equalized preferred_agents across all 4 personas (12 agents each)"
  - "Inclusive prompt injection wording (All specialized agents)"
  - "7 equalization tests proving equal access, preserved behavioral tuning, unchanged rate limits"
affects: [persona-runtime, agent-routing, executive-agent]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Persona differentiates behavior (routing priorities, prompt fragments) not availability"
    - "ALL_AGENT_NAMES as single source of truth for agent access"

key-files:
  created:
    - tests/unit/test_persona_equalization.py
  modified:
    - app/personas/policy_registry.py
    - app/personas/prompt_fragments.py
    - tests/unit/test_persona_policy_registry.py

key-decisions:
  - "ALL_AGENT_NAMES constant defined in policy_registry.py (not prompt_fragments.py) to keep policy data co-located"
  - "Prompt wording changed to 'All specialized agents (route based on routing priorities below)' to prevent LLM from interpreting a long agent list as restrictive"
  - "preferred_agents field kept on PersonaPolicy dataclass for backward compatibility even though all personas now share the same value"

patterns-established:
  - "Persona = behavioral tuning, not access restriction: routing priorities and prompt fragments differ, but agent list is universal"
  - "Rate limits (10/30/60/120 per minute) are the only hard persona differentiator"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-03-27
---

# Phase 28 Plan 01: Persona Agent Equalization Summary

**Equalized preferred_agents across all 4 personas to include all 12 canonical agents, changing prompt injection from restrictive subset to inclusive "All specialized agents" wording**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-26T21:35:40Z
- **Completed:** 2026-03-26T21:43:21Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- All 4 personas (solopreneur, startup, SME, enterprise) now have identical preferred_agents containing all 12 agent names
- Prompt injection changed from restrictive "Preferred agents: X, Y" to inclusive "All specialized agents (route based on routing priorities below)"
- 7 new equalization tests proving: identical access, all canonical agents present, solopreneur includes previously missing agents, inclusive prompt wording, differing routing priorities, behavioral fragments preserved for all 12x4 combinations, rate limits unchanged
- Zero regressions across 18 tests (7 new equalization + 4 existing policy registry + 3 personalization injection + 4 integration template routing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Equalize preferred_agents and update prompt injection**
   - `4c35a5d` (test) - TDD RED: failing equalization tests
   - `8f64eed` (feat) - TDD GREEN: equalized agent access + inclusive prompt wording
2. **Task 2: Write equalization test suite and update existing test** - `95aaeeb` (test)

## Files Created/Modified
- `app/personas/policy_registry.py` - Added ALL_AGENT_NAMES constant, replaced per-persona agent subsets with universal list
- `app/personas/prompt_fragments.py` - Changed prompt line from "Preferred agents: X, Y" to "Available agents: All specialized agents"
- `tests/unit/test_persona_equalization.py` - 7 new tests proving equalization invariants
- `tests/unit/test_persona_policy_registry.py` - Updated 2 assertions for 12+ agents

## Decisions Made
- ALL_AGENT_NAMES defined in policy_registry.py (co-located with policy data) rather than prompt_fragments.py
- Prompt wording uses "All specialized agents (route based on routing priorities below)" to avoid LLM interpreting a 12-agent list as restrictive
- PersonaPolicy.preferred_agents field retained for backward compatibility; all 4 personas now share the same tuple value

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Agent access equalized; all personas can route to all 12 agent types
- Behavioral tuning (routing priorities, per-agent fragments, deliverable shapes) preserved and tested
- Rate limits remain the sole hard differentiator between personas
- Ready for Phase 28 Plan 02 (if any) or next phase

## Self-Check: PASSED

- All 5 files verified present on disk
- All 3 commit hashes verified in git log (4c35a5d, 8f64eed, 95aaeeb)

---
*Phase: 28-persona-agent-equalization*
*Completed: 2026-03-27*
