---
phase: 81-agent-config-fixes
plan: "01"
subsystem: agents
tags: [agents, configuration, model-upgrade, token-ceiling]
dependency_graph:
  requires: []
  provides: [sales-pro-model, deep-config-hr, deep-config-ops, deep-config-cs]
  affects: [app/agents/sales/agent.py, app/agents/hr/agent.py, app/agents/operations/agent.py, app/agents/customer_support/agent.py]
tech_stack:
  added: []
  patterns: [DEEP_AGENT_CONFIG for long-form domain agents]
key_files:
  created: []
  modified:
    - app/agents/sales/agent.py
    - app/agents/hr/agent.py
    - app/agents/operations/agent.py
    - app/agents/customer_support/agent.py
decisions:
  - "Sales uses get_model() (Pro) + DEEP_AGENT_CONFIG — only the LeadScoringAgent sub-agent was already on Pro; the parent agent was incorrectly on Flash"
  - "HR/Ops/CS keep get_routing_model() (Pro) — only ROUTING_AGENT_CONFIG (1024 tokens) replaced by DEEP_AGENT_CONFIG (4096 tokens)"
  - "Operations retains get_fast_model() import for ConfigurationAgent sub-agent — not removed"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-27"
  tasks_completed: 2
  files_modified: 4
---

# Phase 81 Plan 01: Agent Config Fixes Summary

Sales agent upgraded from Gemini Flash to Pro with DEEP_AGENT_CONFIG; HR, Operations, and Customer Support token ceilings raised from 1024 to 4096 via DEEP_AGENT_CONFIG.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Upgrade Sales agent model from Flash to Pro with DEEP_AGENT_CONFIG | 478b0376 | app/agents/sales/agent.py |
| 2 | Upgrade HR, Operations, and Customer Support token ceilings to DEEP_AGENT_CONFIG | 03b7b60e | app/agents/hr/agent.py, app/agents/operations/agent.py, app/agents/customer_support/agent.py |

## What Was Built

**Task 1 — Sales agent upgrade:**
- Replaced `get_fast_model()` with `get_model()` on both the singleton and factory instances
- Replaced `FAST_AGENT_CONFIG` (2048 tokens) with `DEEP_AGENT_CONFIG` (4096 tokens) on both instances
- Removed `FAST_AGENT_CONFIG` and `get_fast_model` from the import line entirely
- The `LeadScoringAgent` sub-agent was already using `get_model()` correctly — no change needed there

**Task 2 — HR/Ops/CS token ceiling raise:**
- Replaced `ROUTING_AGENT_CONFIG` (1024 tokens) with `DEEP_AGENT_CONFIG` (4096 tokens) in singleton and factory for all three agents
- Model getter (`get_routing_model()`) left unchanged in all three — only the content generation config is updated
- Operations agent retains `get_fast_model` import because the `ConfigurationAgent` sub-agent still uses it

## Verification

```
Sales: generate_content_config=DEEP_AGENT_CONFIG occurrences: 2  (expected 2)
Sales: FAST_AGENT_CONFIG occurrences: 0  (expected 0)
HR:    generate_content_config=DEEP_AGENT_CONFIG occurrences: 2  (expected 2)
OPS:   generate_content_config=DEEP_AGENT_CONFIG occurrences: 2  (expected 2)
CS:    generate_content_config=DEEP_AGENT_CONFIG occurrences: 2  (expected 2)
ROUTING_AGENT_CONFIG across all 3 files: 0  (expected 0)
```

Agent unit tests: 20 passed in 45s.

## Decisions Made

1. Sales uses `get_model()` (Pro) + `DEEP_AGENT_CONFIG` — the parent SalesIntelligenceAgent handles complex deal analysis and proposal generation, requiring Pro-level reasoning. The sub-agent `LeadScoringAgent` was already on Pro.
2. HR/Ops/CS keep `get_routing_model()` (Pro with failover) — the model is already correct, only the token ceiling is raised to prevent silent truncation of job descriptions, SOPs, and customer emails.
3. Operations retains `get_fast_model` import — used by `ConfigurationAgent` sub-agent; removing it would break that sub-agent.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `app/agents/sales/agent.py` — verified: 2x DEEP_AGENT_CONFIG, 0x FAST
- `app/agents/hr/agent.py` — verified: 2x DEEP_AGENT_CONFIG, 0x ROUTING
- `app/agents/operations/agent.py` — verified: 2x DEEP_AGENT_CONFIG, 0x ROUTING
- `app/agents/customer_support/agent.py` — verified: 2x DEEP_AGENT_CONFIG, 0x ROUTING
- Commit 478b0376 — exists (Task 1)
- Commit 03b7b60e — exists (Task 2)
