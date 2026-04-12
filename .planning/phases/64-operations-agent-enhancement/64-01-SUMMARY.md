---
phase: 64-operations-agent-enhancement
plan: "01"
subsystem: operations-agent
tags: [operations, workflow, bottleneck-detection, analytics, tdd]
dependency_graph:
  requires:
    - supabase tables workflow_steps, workflow_executions
    - app/services/base_service.py (BaseService)
  provides:
    - app/services/workflow_bottleneck_service.py (WorkflowBottleneckService, analyze_bottlenecks)
    - app/agents/tools/ops_tools.py (OPS_ANALYSIS_TOOLS)
  affects:
    - app/agents/operations/agent.py (OPERATIONS_AGENT_TOOLS, OPERATIONS_AGENT_INSTRUCTION)
tech_stack:
  added: []
  patterns:
    - "Sync ADK tool wrapper around async service (asyncio.get_event_loop pattern)"
    - "Python-side aggregation of Supabase PostgREST data (no GROUP BY support)"
    - "TDD: RED test commit → GREEN service commit → Task 2 commit"
key_files:
  created:
    - app/services/workflow_bottleneck_service.py
    - app/agents/tools/ops_tools.py
    - tests/unit/services/test_workflow_bottleneck_service.py
  modified:
    - app/agents/operations/agent.py
decisions:
  - "[Phase 64-01]: Python-side step aggregation instead of SQL GROUP BY — Supabase PostgREST does not support aggregation queries; fetch raw rows and group in Python"
  - "[Phase 64-01]: Four independent bottleneck thresholds — slow (>24h avg), failing (>20%), approval-blocked (>48h avg + >30% waiting_approval), outlier (max >1 week) — each generates its own recommendation type"
  - "[Phase 64-01]: Severity tiers: slow steps >48h and failing steps >40% are 'high'; all others are 'medium'; sort high-first then by avg_duration descending"
  - "[Phase 64-01]: _fetch_steps_and_executions isolated as a patchable async method so unit tests can mock data without a live Supabase connection"
metrics:
  duration: "12min"
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_changed: 4
---

# Phase 64 Plan 01: Workflow Bottleneck Detection — Summary

**One-liner:** Workflow bottleneck detection service querying workflow_steps/workflow_executions with per-step duration aggregation, four threshold-based flags, and plain-English recommendations wired as Operations Agent tools.

## What Was Built

### WorkflowBottleneckService (`app/services/workflow_bottleneck_service.py`)

Queries `workflow_executions` filtered by `user_id` and date window, then fetches all `workflow_steps` for those executions. Aggregates in Python (Supabase PostgREST lacks GROUP BY):

- **Per-step stats:** `avg_duration_hours`, `max_duration_hours`, `execution_count`, `failure_count`, `failure_rate`, `approval_wait_count`, `approval_wait_rate`, `is_bottleneck`
- **Bottleneck flags:** slow (`avg > 24h`), failing (`failure_rate > 20%`), approval-blocked (`avg > 48h` AND `approval_wait_rate > 30%`)
- **Recommendations:** Plain-English with specific numbers (e.g., "Content Approval averages 3.2 days — consider adding reminders or parallel tracks.")
- **Outlier detection:** `max_duration > 7 days` generates an outlier recommendation
- **Health summary:** `get_workflow_health_summary` returns `completion_rate`, `avg_execution_hours`, `top_bottlenecks` (up to 3)
- **Module convenience:** `analyze_bottlenecks(user_id, days)` at module level

### OPS_ANALYSIS_TOOLS (`app/agents/tools/ops_tools.py`)

Two sync ADK tool wrappers following the `inventory.py` pattern:

- `analyze_workflow_bottlenecks(user_id, days=30)` — full step-level analysis
- `get_workflow_health(user_id)` — quick health overview

### Operations Agent (`app/agents/operations/agent.py`)

- `OPS_ANALYSIS_TOOLS` imported and added to `OPERATIONS_AGENT_TOOLS`
- `OPERATIONS_AGENT_INSTRUCTION` updated with guidance on when to use each tool and how to present results conversationally

## Tests

19 unit tests covering all bottleneck thresholds, recommendation content, health summary aggregation, edge cases (empty executions, missing timestamps), and the module-level convenience function. All pass.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files exist
- `app/services/workflow_bottleneck_service.py` — created
- `app/agents/tools/ops_tools.py` — created
- `app/agents/operations/agent.py` — modified
- `tests/unit/services/test_workflow_bottleneck_service.py` — created

### Commits exist
- `f8aa3b0d` — test(64-01): add failing tests for WorkflowBottleneckService
- `6539bcd1` — feat(64-01): implement WorkflowBottleneckService with bottleneck detection
- `9d707212` — feat(64-01): create ops_tools and wire OPS_ANALYSIS_TOOLS into Operations Agent

## Self-Check: PASSED
