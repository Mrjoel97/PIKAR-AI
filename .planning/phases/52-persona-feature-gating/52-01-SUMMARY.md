---
phase: 52-persona-feature-gating
plan: "01"
subsystem: agents
tags: [personas, adk, gemini, supabase, behavioral-instructions, prompt-engineering]

requires:
  - phase: 50-billing
    provides: subscriptions table with tier and is_active columns
  - phase: 52-persona-feature-gating
    provides: prompt_fragments.build_persona_policy_block, behavioral_instructions module

provides:
  - Subscription-first persona resolution (subscriptions.tier beats profile.persona)
  - All 10 specialized agent factories accept optional persona parameter
  - ExecutiveAgent construction supports persona-aware prompt composition
  - Persona behavioral instructions injected at factory-creation time

affects: [52-02, 52-03, app/agent.py, app/agents/specialized_agents.py]

tech-stack:
  added: []
  patterns:
    - "Subscription-first resolution: subscriptions.tier > cookie/header > profile.persona > None"
    - "Factory persona injection: persona_block appended to instruction when persona is set, singletons stay generic"
    - "Keyword-only persona=None default preserves all existing callers"

key-files:
  created:
    - tests/unit/app/personas/__init__.py
    - tests/unit/app/personas/test_runtime_subscription.py
  modified:
    - app/personas/runtime.py
    - app/agents/financial/agent.py
    - app/agents/content/agent.py
    - app/agents/strategic/agent.py
    - app/agents/sales/agent.py
    - app/agents/marketing/agent.py
    - app/agents/operations/agent.py
    - app/agents/hr/agent.py
    - app/agents/compliance/agent.py
    - app/agents/customer_support/agent.py
    - app/agents/data/agent.py
    - app/agents/reporting/agent.py
    - app/agent.py

key-decisions:
  - "Import execute_async and get_service_client at module level in runtime.py to enable simple patching in tests"
  - "Singleton agents (SPECIALIZED_AGENTS list) remain persona-agnostic; only factory functions get persona injection"
  - "ExecutiveAgent uses include_routing=True so persona policy block includes routing priorities"
  - "Pre-existing RUF013 lint issues (output_key: str = None) left as-is — out-of-scope pre-existing violations"

patterns-established:
  - "Persona injection pattern: append build_persona_policy_block result to instruction string in factory, not in singleton"
  - "Subscription-first DB lookup: wrapped in try/except to fall through gracefully to profile.persona on error"

requirements-completed: [GATE-02, UX-05]

duration: 18min
completed: "2026-04-09"
---

# Phase 52 Plan 01: Persona Agent Wiring Summary

**Subscription-first persona resolution and factory-level persona injection across all 10 specialized agents and the ExecutiveAgent, using build_persona_policy_block to append tier-specific behavioral instructions at instantiation time**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-09T22:13:41Z
- **Completed:** 2026-04-09T22:32:29Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Updated `resolve_effective_persona` to query `subscriptions.tier` before falling back to `profile.persona`, establishing the subscription as the Phase 50 source of truth for persona
- Added `persona: str | None = None` to all 10 specialized agent factory functions and the ExecutiveAgent builder, each appending `build_persona_policy_block` output when persona is provided
- Written 4 unit tests (TDD) covering the full priority chain: explicit param > cookie/header > subscription > profile > None
- Existing callers without persona continue to work unchanged; singleton agents remain generic

## Task Commits

Each task was committed atomically:

1. **Task 1: Update resolve_effective_persona (TDD)** - `b30d654f` (feat)
2. **Task 2: Wire persona into all agent factories and ExecutiveAgent** - `3d3343e8` (feat)

**Plan metadata:** _(this commit)_ (docs: complete plan)

## Files Created/Modified

- `app/personas/runtime.py` - Added subscription tier check between cookie/header and profile.persona lookup; imported execute_async and get_service_client at module level
- `app/agent.py` - _build_executive_agent, create_executive_agent, create_executive_agent_fallback, _build_fallback_sub_agents all accept and propagate persona
- `app/agents/financial/agent.py` - create_financial_agent gains persona parameter
- `app/agents/content/agent.py` - create_content_agent gains persona parameter
- `app/agents/strategic/agent.py` - create_strategic_agent gains persona parameter
- `app/agents/sales/agent.py` - create_sales_agent gains persona parameter
- `app/agents/marketing/agent.py` - create_marketing_agent gains persona parameter
- `app/agents/operations/agent.py` - create_operations_agent gains persona parameter
- `app/agents/hr/agent.py` - create_hr_agent gains persona parameter
- `app/agents/compliance/agent.py` - create_compliance_agent gains persona parameter
- `app/agents/customer_support/agent.py` - create_customer_support_agent gains persona parameter
- `app/agents/data/agent.py` - create_data_agent gains persona parameter
- `app/agents/reporting/agent.py` - create_data_reporting_agent gains persona parameter
- `tests/unit/app/personas/__init__.py` - New test package
- `tests/unit/app/personas/test_runtime_subscription.py` - 4 tests for subscription-first priority chain

## Decisions Made

- Import `execute_async` and `get_service_client` at module level in `runtime.py` (not inside the try block) so tests can patch them cleanly without `create=True` hacks.
- Singleton agents in `SPECIALIZED_AGENTS` stay persona-agnostic — they are shared across requests and cannot carry per-user state. Only factory-created instances (per-request/workflow) get persona injection.
- `include_routing=True` on the ExecutiveAgent's `build_persona_policy_block` call so the routing priorities from the persona policy are included in the executive system prompt.
- Pre-existing `output_key: str = None` RUF013 violations left untouched — they are out-of-scope pre-existing issues that exist in many files across the codebase.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The TDD flow was clean: tests failed correctly in RED phase (AttributeError on `execute_async` not yet in runtime), and all 4 passed after the implementation was added.

## User Setup Required

None - no external service configuration required. The subscriptions table was established in Phase 50.

## Next Phase Readiness

- All 10 specialized agent factories and ExecutiveAgent are now persona-aware
- `resolve_effective_persona` delivers the subscription tier as the ground truth for persona
- Ready for Phase 52-02 which will call `resolve_effective_persona` at request time and pass persona into `create_executive_agent(persona=...)`
- No blockers

---
*Phase: 52-persona-feature-gating*
*Completed: 2026-04-09*

## Self-Check: PASSED

- app/personas/runtime.py — FOUND
- app/agents/financial/agent.py — FOUND
- tests/unit/app/personas/test_runtime_subscription.py — FOUND
- Commit b30d654f — FOUND
- Commit 3d3343e8 — FOUND
