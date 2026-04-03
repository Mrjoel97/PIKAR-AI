---
phase: 33-backend-persona-awareness
plan: "01"
subsystem: api
tags: [personas, agents, prompt-engineering, behavioral-instructions, python]

# Dependency graph
requires:
  - phase: 29-persona-system
    provides: PersonaPolicy model, policy_registry, prompt_fragments pipeline
  - phase: 32-feature-gating
    provides: persona-aware request context
provides:
  - Concrete behavioral directives for all 4 personas x 12 agents (48 combinations)
  - get_behavioral_instructions() function automatically wired into every agent system prompt
  - BEHAVIORAL STYLE DIRECTIVES block appended to build_persona_policy_block() output
affects:
  - 34-computed-kpis
  - 35-teams-rbac
  - 36-enterprise-governance
  - 37-sme-dept-coordination

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Behavioral instructions as separate module (not scattered across 11 agent files)"
    - "Circular import prevention: behavioral_instructions.py inlines its own alias table"
    - "TDD RED/GREEN flow for behavioral contract testing"

key-files:
  created:
    - app/personas/behavioral_instructions.py
    - tests/unit/test_persona_behavioral_instructions.py
  modified:
    - app/personas/prompt_fragments.py
    - app/personas/__init__.py
    - tests/unit/test_personalization_prompt_injection.py

key-decisions:
  - "Behavioral instructions live in a single module (behavioral_instructions.py), not inside 11 agent files — maintainability over co-location"
  - "Circular import resolved by inlining _resolve_agent() + _AGENT_ALIASES in behavioral_instructions.py instead of importing from prompt_fragments.py"
  - "Behavioral blocks injected after HOW TO ADAPT section in build_persona_policy_block() — zero changes needed in context_extractor.py or user_agent_factory.py"

patterns-established:
  - "Persona behavioral directives pattern: each block is 4-6 concrete sentences of communication rules, not metadata"
  - "Module-level alias table pattern: modules that need agent resolution but would create circular imports maintain their own local alias copy"

requirements-completed: [PERS-01, PERS-02]

# Metrics
duration: 14min
completed: 2026-04-03
---

# Phase 33 Plan 01: Backend Persona Awareness Summary

**Persona behavioral instruction matrix: 48 concrete communication-style directives (4 personas x 12 agents) automatically injected into every agent system prompt via the existing callback pipeline**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-03T13:51:34Z
- **Completed:** 2026-04-03T14:05:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `app/personas/behavioral_instructions.py` with 48 distinct behavioral directive blocks covering every persona-agent combination — solopreneur gets "write like a sharp adviser texting a busy founder", enterprise gets "Use professional, executive-ready language throughout"
- Integrated behavioral instructions into the existing `build_persona_policy_block()` pipeline with 3 lines of code — no changes to `context_extractor.py` or `user_agent_factory.py` because they already call the pipeline
- Wrote 20 tests covering all behavioral specification requirements including word-overlap < 50% for solopreneur vs enterprise across all 12 agents, verified all 33 persona tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create persona behavioral instructions module with tests** - `36c2868` (feat)
2. **Task 2: Integrate behavioral instructions into persona policy block pipeline** - `5707187` (feat)

_Note: Task 1 used TDD — tests written first (RED), then implementation (GREEN)._

## Files Created/Modified

- `app/personas/behavioral_instructions.py` - 48-combination behavioral instruction matrix with `get_behavioral_instructions()` function; inlines `_resolve_agent()` and `_AGENT_ALIASES` to avoid circular import with `prompt_fragments.py`
- `tests/unit/test_persona_behavioral_instructions.py` - 20 tests (8 behavior specs + 12 parametrized overlap tests) verifying all combinations, None handling, and material differentiation
- `app/personas/prompt_fragments.py` - Added import and 4-line integration block after HOW TO ADAPT section in `build_persona_policy_block()`
- `app/personas/__init__.py` - Added `get_behavioral_instructions` import and `__all__` export
- `tests/unit/test_personalization_prompt_injection.py` - Added `BEHAVIORAL STYLE DIRECTIVES` assertions to two existing integration tests

## Decisions Made

- **Single module for all behavioral directives** — kept instructions in `behavioral_instructions.py` rather than distributed across 11 agent files. This makes future persona edits a single-file change.
- **Circular import resolved by inlining alias table** — `behavioral_instructions.py` maintains its own `_AGENT_ALIASES` dict and `_resolve_agent()` function to avoid importing from `prompt_fragments.py` (which would create a cycle). A comment in the code notes to keep the two tables in sync.
- **Zero downstream changes** — behavioral instructions slot into the existing callback pipeline at the `build_persona_policy_block()` level. `context_extractor.py` and `user_agent_factory.py` pick them up automatically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed word "portfolio" from solopreneur financial instructions to satisfy test assertion**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** The solopreneur FinancialAnalysisAgent instruction used "portfolio theory" in a negation context ("do not introduce portfolio theory"), but the test asserted the word "portfolio" must not appear at all
- **Fix:** Replaced the negation phrasing with "Never introduce investor-grade financial frameworks or quarterly board-level analysis" — same intent, no forbidden word
- **Files modified:** `app/personas/behavioral_instructions.py`
- **Verification:** `test_solopreneur_financial_agent_contains_cash_flow` passes
- **Committed in:** `36c2868` (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed circular import between behavioral_instructions.py and prompt_fragments.py**
- **Found during:** Task 2 (integration)
- **Issue:** `behavioral_instructions.py` imported `resolve_agent_name` from `prompt_fragments.py`, while `prompt_fragments.py` now imported `get_behavioral_instructions` from `behavioral_instructions.py` — Python raised `ImportError: cannot import name 'get_behavioral_instructions' from partially initialized module`
- **Fix:** Removed the `prompt_fragments` import from `behavioral_instructions.py` and inlined a local `_resolve_agent()` with its own `_AGENT_ALIASES` copy
- **Files modified:** `app/personas/behavioral_instructions.py`
- **Verification:** All 33 persona tests pass; import chain resolves cleanly
- **Committed in:** `5707187` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 content fix, 1 Rule 3 blocking import fix)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- `uv` command not in bash PATH on this Windows environment — resolved by using `.venv/Scripts/pytest.exe` and `.venv/Scripts/ruff.exe` directly. All quality gates executed successfully.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Behavioral instructions are live in every agent system prompt via the existing callback pipeline
- 33-02 (if planned) can build on `get_behavioral_instructions()` from the public `app.personas` package API
- 34-computed-kpis can reference behavioral instruction patterns when shaping persona-aware KPI outputs
- No blockers

---
*Phase: 33-backend-persona-awareness*
*Completed: 2026-04-03*
