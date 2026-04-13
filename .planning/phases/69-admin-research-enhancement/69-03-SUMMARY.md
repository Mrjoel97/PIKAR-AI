---
phase: 69-admin-research-enhancement
plan: 03
subsystem: api
tags: [research-agent, persona, synthesis, monitoring, adk, gemini]

# Dependency graph
requires:
  - phase: 69-02
    provides: billing cost projection alerts on AdminAgent
provides:
  - format_synthesis_for_persona tool — 4 persona-specific output formats for research synthesis
  - Updated RESEARCH_AGENT_INSTRUCTION with persona-aware synthesis and monitoring subscription guidance
  - PERSONA_SYNTHESIZER_TOOLS registered on ResearchAgent alongside existing MONITORING_TOOLS
affects:
  - research-agent
  - executive-agent
  - any agent phase that consumes research synthesis output

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Persona dispatch table with frozenset for O(1) persona validation
    - Helper function decomposition (_build_summary, _build_citations, _build_recommendations) shared across all 4 formatters
    - Graceful no-findings fallback with suggested follow-up queries for all personas
    - Pre-existing E501 violations in multi-line instruction strings are not introduced by this phase

key-files:
  created:
    - app/agents/research/tools/persona_synthesizer.py
    - tests/unit/test_persona_synthesizer.py
    - tests/unit/test_monitoring_subscriptions.py
  modified:
    - app/agents/research/instructions.py
    - app/agents/research/agent.py

key-decisions:
  - "format_synthesis_for_persona defaults to startup (not solopreneur) as the balanced middle ground for unknown/None persona"
  - "admin persona falls back to startup — admin is not a research consumer"
  - "Enterprise executive_summary is a full paragraph built from top-3 findings; solopreneur gets max 5 bullets from top-5 findings"
  - "Confidence label thresholds: >=0.75=high, >=0.50=medium, <0.50=low"
  - "No-findings fallback returns no_findings=True plus suggested follow-up queries for all 4 personas"
  - "Instruction sections added as plain Markdown inside the triple-quoted string — consistent with existing instruction style"

patterns-established:
  - "Persona dispatch: validate with frozenset, fallback to 'startup', dispatch to private _format_X helper"
  - "Per-persona formatters are private helpers (_format_solopreneur, _format_startup, etc.) — only format_synthesis_for_persona is public"
  - "Action item extraction uses keyword heuristics (not LLM) for determinism and testability — consistent with Phase 64-01, 66, 67-03 patterns"

requirements-completed: [RESEARCH-01, RESEARCH-02]

# Metrics
duration: 21min
completed: 2026-04-13
---

# Phase 69 Plan 03: Persona-Aware Research Synthesis and Conversational Monitoring Subscriptions Summary

**format_synthesis_for_persona tool delivers 4 distinct output formats (solopreneur bullets, startup recommendations, SME structured report, enterprise executive briefing) and RESEARCH_AGENT_INSTRUCTION now guides conversational monitoring subscription setup**

## Performance

- **Duration:** 21 min
- **Started:** 2026-04-13T13:35:49Z
- **Completed:** 2026-04-13T13:56:49Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `format_synthesis_for_persona` with 4 persona-specific output shapes: solopreneur (max 5 bullets + action items + categorical confidence), startup (source-attributed findings + prioritised recommendations + confidence dict), SME (source URLs + data quality assessment + estimated impact), enterprise (full methodology + numbered citations + risk assessment + appendix)
- Graceful no-findings fallback for all 4 personas returns `no_findings: True` plus `follow_up_queries` — never crashes or returns raw empty dicts
- Updated `RESEARCH_AGENT_INSTRUCTION` with two new sections: Persona-Aware Synthesis (when/how to call `format_synthesis_for_persona`) and Conversational Monitoring Subscriptions (6-step guided flow + quick-setup shortcuts)
- Wired `PERSONA_SYNTHESIZER_TOOLS` into `RESEARCH_AGENT_TOOLS` — ResearchAgent now has 13 tools total
- 19 tests across 2 files: 12 functional tests for the synthesizer, 7 wiring tests confirming tool registration and instruction content

## Task Commits

1. **Task 1: Create persona_synthesizer tool (TDD)** — `01b2b09f` (feat)
2. **Task 2: Wire tool + update instructions** — `8882f69c` (feat)

## Files Created/Modified

- `app/agents/research/tools/persona_synthesizer.py` — format_synthesis_for_persona + 4 private formatters + PERSONA_SYNTHESIZER_TOOLS export
- `tests/unit/test_persona_synthesizer.py` — 12 functional tests covering all 4 personas, fallbacks, empty findings, and export
- `tests/unit/test_monitoring_subscriptions.py` — 7 wiring tests confirming tool registration, instruction content, and singleton load
- `app/agents/research/instructions.py` — Added Persona-Aware Synthesis and Conversational Monitoring Subscriptions sections
- `app/agents/research/agent.py` — Added PERSONA_SYNTHESIZER_TOOLS import and list entry

## Decisions Made

- Defaulted unknown/None persona to `startup` — the balanced middle ground between conciseness (solopreneur) and formality (enterprise)
- `admin` persona falls back to startup — admins are platform operators, not research consumers
- Confidence label thresholds: >=0.75=high, >=0.50=medium, <0.50=low — categorical labels for solopreneur, numeric dict for startup/sme/enterprise
- Enterprise executive_summary is a paragraph; solopreneur `key_findings` is a flat list capped at 5 — clear differentiation between briefing styles
- Action item extraction and recommendation prioritization use keyword heuristics (not LLM) — consistent with Phase 64-01, 66, 67-03 patterns for determinism and testability
- No-findings fallback includes `suggested_queries` / `follow_up_queries` so agents can guide users to refine queries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeError in `_build_executive_summary`**
- **Found during:** Task 1 GREEN phase (test_enterprise_format_has_required_keys)
- **Issue:** Generator expression `" ".join(f.get("text")[:300].split(".")[:2] + ["."] for f in top)` produced `list found, str expected` TypeError — `join` received a generator of lists, not strings
- **Fix:** Replaced with explicit loop building snippet strings per finding, then joining
- **Files modified:** `app/agents/research/tools/persona_synthesizer.py`
- **Verification:** All 12 persona synthesizer tests pass after fix
- **Committed in:** `01b2b09f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** Bug fix necessary for correctness, caught by TDD RED/GREEN cycle. No scope creep.

## Issues Encountered

- `git stash` during lint investigation unintentionally reverted working-copy changes to `instructions.py` and `agent.py` (stash pop blocked by uv.lock conflict). Changes were re-applied from memory and all tests re-confirmed before the Task 2 commit.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- ResearchAgent now delivers persona-tailored research output — consumers (ExecutiveAgent, other agents) can pass persona strings to get appropriately formatted intelligence
- Monitoring subscription instructions are in place; functional monitoring requires `create_monitoring_job` connectivity (MonitoringJobService + DB)
- Phase 69-04 (if planned) can build on this persona foundation to inject persona detection from `user_executive_agents` table into the synthesis call

---
*Phase: 69-admin-research-enhancement*
*Completed: 2026-04-13*
