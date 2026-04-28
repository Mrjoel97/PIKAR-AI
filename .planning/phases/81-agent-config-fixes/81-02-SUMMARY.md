---
phase: 81-agent-config-fixes
plan: "02"
subsystem: agents
tags: [agents, instructions, error-handling, escalation, skills-registry, self-improvement]
dependency_graph:
  requires: [81-01]
  provides: [sales-escalation, ops-escalation, compliance-escalation, cs-escalation, reporting-all-blocks, research-all-blocks]
  affects:
    - app/agents/sales/agent.py
    - app/agents/operations/agent.py
    - app/agents/compliance/agent.py
    - app/agents/customer_support/agent.py
    - app/agents/reporting/agent.py
    - app/agents/research/instructions.py
tech_stack:
  added: []
  patterns: [shared_instructions blocks appended to all agent instruction strings]
key_files:
  created: []
  modified:
    - app/agents/sales/agent.py
    - app/agents/operations/agent.py
    - app/agents/compliance/agent.py
    - app/agents/customer_support/agent.py
    - app/agents/reporting/agent.py
    - app/agents/research/instructions.py
decisions:
  - "Reporting agent keeps legacy use_skill/list_available_skills from enhanced_tools alongside new instruction blocks — no tool changes needed"
  - "Research agent instructions.py converted from plain string to concatenated expression to allow block appending"
  - "Research agent tool list not modified — skill tools referenced in instructions will be wired in a future phase"
metrics:
  duration_minutes: 7
  completed_date: "2026-04-27"
  tasks_completed: 2
  files_modified: 6
---

# Phase 81 Plan 02: Agent Instruction Alignment Summary

Added missing shared instruction blocks (error/escalation, skills registry, self-improvement) to six agents, giving all 10 agents in the fleet consistent behavioral alignment with the established Financial/Strategic/Content pattern.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add error/escalation instructions to Sales, Operations, Compliance, CS agents | a414366a | app/agents/sales/agent.py, app/agents/operations/agent.py, app/agents/compliance/agent.py, app/agents/customer_support/agent.py |
| 2 | Add all three shared instruction blocks to Reporting and Research agents | 556cca9c | app/agents/reporting/agent.py, app/agents/research/instructions.py |

## What Was Built

**Task 1 — Escalation instructions for four agents:**

All four agents already had SKILLS_REGISTRY_INSTRUCTIONS and SELF_IMPROVEMENT_INSTRUCTIONS. Only `get_error_and_escalation_instructions` was missing.

- `app/agents/sales/agent.py`: Added `get_error_and_escalation_instructions` to the import from `shared_instructions` and appended the call with Sales-specific domain rules (escalate to legal/compliance for contracts, financial for pricing)
- `app/agents/operations/agent.py`: Same pattern — escalate to compliance for regulatory process changes, financial for budget decisions beyond authority
- `app/agents/compliance/agent.py`: Same pattern — escalate to external counsel for novel interpretations, financial for impact quantification
- `app/agents/customer_support/agent.py`: Same pattern — escalate to compliance for privacy requests (GDPR/CCPA), financial for refunds beyond policy

**Task 2 — All three blocks for Reporting and Research:**

- `app/agents/reporting/agent.py`: Expanded import from single `CONVERSATION_MEMORY_INSTRUCTIONS` to all four symbols; appended SKILLS_REGISTRY_INSTRUCTIONS, SELF_IMPROVEMENT_INSTRUCTIONS, and escalation block (escalate to financial for report interpretation, ops for workflow data)
- `app/agents/research/instructions.py`: Added import block for the three shared instruction symbols; converted `RESEARCH_AGENT_INSTRUCTION` from a plain triple-quoted string to a concatenated expression ending with skills registry, self-improvement, and escalation block (escalate to compliance for regulated research, cap confidence threshold at 50%)

## Verification

```
Escalation block in all 6 agents:       6/6  (grep -l count)
Skills registry in Reporting+Research:  2/2
Self-improvement in Reporting+Research: 2/2
Agent unit tests:                       20 passed in 7.84s
```

## Decisions Made

1. Reporting agent keeps legacy `use_skill`/`list_available_skills` from `enhanced_tools` alongside the new instruction blocks — both reference the same underlying skill system. No tool changes needed.
2. Research `instructions.py` converted from plain string assignment to a parenthesized concatenation — the only safe way to append multiple instruction blocks without modifying the instruction text body.
3. Research agent tool list (`app/agents/research/agent.py`) was not modified — the skills/self-improve tools referenced in the new instruction blocks will be wired in a future phase, consistent with the plan's note.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `app/agents/sales/agent.py` — exists, 2x `get_error_and_escalation_instructions` (import + call)
- `app/agents/operations/agent.py` — exists, 2x `get_error_and_escalation_instructions`
- `app/agents/compliance/agent.py` — exists, 2x `get_error_and_escalation_instructions`
- `app/agents/customer_support/agent.py` — exists, 2x `get_error_and_escalation_instructions`
- `app/agents/reporting/agent.py` — exists, SKILLS_REGISTRY + SELF_IMPROVEMENT + escalation
- `app/agents/research/instructions.py` — exists, SKILLS_REGISTRY + SELF_IMPROVEMENT + escalation
- Commit a414366a — exists (Task 1)
- Commit 556cca9c — exists (Task 2)
