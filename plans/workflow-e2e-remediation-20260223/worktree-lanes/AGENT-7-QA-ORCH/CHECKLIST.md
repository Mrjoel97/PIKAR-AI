# AGENT-7-QA-ORCH Worktree Execution Checklist

- Lane type: `qa-orchestration`
- Focus: Evidence consolidation, browser subset validation, exhaustive reruns, and regression gatekeeping.
- Suggested worktree path: `.tmp/codex-parallel/worktrees/wt-agent-7-qa-orch`
- Suggested branch name: `workflow-e2e/agent-7-qa-orch`
- Depends on: `AGENT-1-GATES, AGENT-2-INTEGRATIONS, AGENT-3-DEGRADED-A, AGENT-4-DEGRADED-B, AGENT-5-AUTONOMOUS-A, AGENT-6-AUTONOMOUS-B`

## Worktree Setup

```bash
git worktree add .tmp/codex-parallel/worktrees/wt-agent-7-qa-orch -b workflow-e2e/agent-7-qa-orch main
cd .tmp/codex-parallel/worktrees/wt-agent-7-qa-orch
```

## Pre-Flight Checklist

- [ ] Pull latest `main` and confirm no unresolved conflicts in the worktree.
- [ ] Confirm `AGENT-0-INFRA` prerequisites required for this lane are merged/deployed in the target E2E environment.
- [ ] Confirm strict E2E env flags are set as expected (`WORKFLOW_STRICT_TOOL_RESOLUTION`, `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD`, `WORKFLOW_ALLOW_FALLBACK_SIMULATION=0`, readiness gate decision).
- [ ] Confirm dedicated test user/token strategy and rate-limit pacing are ready for batch verification.
- [ ] Create or confirm lane evidence directory (logs, screenshots, API traces, test outputs).

## QA / Orchestration Scope

- [ ] Maintain merge candidate matrix across AGENT-1..AGENT-6 and track integration conflicts.
- [ ] Run browser subset for workflow start modal, active execution view, and approval flow.
- [ ] Run exhaustive workflow + journey audit rerun with per-item polling enabled after lane merges.
- [ ] Publish final evidence pack and delta report versus `workflow-journey-e2e-audit-20260222` baseline.

## Deliverables (Lane)

- [ ] Browser subset validation results documented for workflow start + approval flows.
- [ ] Exhaustive rerun with per-item polling completed and diffed against baseline audit.
- [ ] Consolidated evidence package and final pass/fail matrix published.

## Commit / PR Handoff

- [ ] Branch rebased or merged with current `main` (or merge train branch) before final validation.
- [ ] Tests run and results recorded in milestone tracker.
- [ ] Evidence refs included for each completed milestone/workflow.
- [ ] Known risks and deferred items listed explicitly.
- [ ] Ready-for-merge status marked in `MILESTONES.md` and `milestones.csv`.

