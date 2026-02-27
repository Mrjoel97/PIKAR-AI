# AGENT-4-DEGRADED-B Worktree Execution Checklist

- Lane type: `degraded-simulation-prone`
- Focus: Eliminate critical degraded/simulation fallback paths and prove strict-mode completion/gating.
- Suggested worktree path: `.tmp/codex-parallel/worktrees/wt-agent-4-degraded-b`
- Suggested branch name: `workflow-e2e/agent-4-degraded-b`
- Depends on: `AGENT-0-INFRA`

## Worktree Setup

```bash
git worktree add .tmp/codex-parallel/worktrees/wt-agent-4-degraded-b -b workflow-e2e/agent-4-degraded-b main
cd .tmp/codex-parallel/worktrees/wt-agent-4-degraded-b
```

## Pre-Flight Checklist

- [ ] Pull latest `main` and confirm no unresolved conflicts in the worktree.
- [ ] Confirm `AGENT-0-INFRA` prerequisites required for this lane are merged/deployed in the target E2E environment.
- [ ] Confirm strict E2E env flags are set as expected (`WORKFLOW_STRICT_TOOL_RESOLUTION`, `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD`, `WORKFLOW_ALLOW_FALLBACK_SIMULATION=0`, readiness gate decision).
- [ ] Confirm dedicated test user/token strategy and rate-limit pacing are ready for batch verification.
- [ ] Create or confirm lane evidence directory (logs, screenshots, API traces, test outputs).

## Assigned Workflows (13)

| Workflow | Category | Priority | Journey Impact | Audit Start | Audit Status |
|---|---|---|---:|---:|---|
| Contract Review | legal | P1 | 7 | 429 | BLOCKED_ENV_CONFIG |
| Recruitment Pipeline | hr | P1 | 4 | 200 | PARTIAL_START_ONLY |
| Budget Planning | finance | P2 | 2 | 429 | BLOCKED_ENV_CONFIG |
| Pipeline Review | sales | P2 | 2 | 429 | BLOCKED_ENV_CONFIG |
| Cash Flow Management | finance | P2 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Data Governance Audit | data | P2 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Incident Investigation | legal | P2 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Office Move/Expansion | operations | P2 | 1 | 200 | PARTIAL_START_ONLY |
| Tax Filing Prep | finance | P2 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Beta Testing Program | product | P2 | 0 | 429 | BLOCKED_ENV_CONFIG |
| Expense Reimbursement | finance | P2 | 0 | 429 | BLOCKED_ENV_CONFIG |
| Invoice Processing | finance | P2 | 0 | 429 | BLOCKED_ENV_CONFIG |
| Offboarding | hr | P2 | 0 | 200 | PARTIAL_START_ONLY |

## Execution Checklist (Lane-Level)

- [ ] Implement lane-specific fixes in small commits grouped by shared code path (tools/engine/router/frontend/tests).
- [ ] For each workflow, execute the per-workflow tasklist from `workflow_tasklist_68.csv` and capture evidence refs.
- [ ] Run targeted tests after each shared-code change before continuing to the next workflow cluster.
- [ ] Maintain a running lane changelog (files touched, behavior changes, risks, open follow-ups).
- [ ] Update milestone tracker statuses and evidence links continuously (not at the end).

## Deliverables (Lane)

- [ ] Critical degraded paths identified and replaced/hardened for assigned workflows.
- [ ] Strict-mode runs complete or gate explicitly with no critical fallback simulation.
- [ ] Regression tests prevent fallback on critical steps.

## Commit / PR Handoff

- [ ] Branch rebased or merged with current `main` (or merge train branch) before final validation.
- [ ] Tests run and results recorded in milestone tracker.
- [ ] Evidence refs included for each completed milestone/workflow.
- [ ] Known risks and deferred items listed explicitly.
- [ ] Ready-for-merge status marked in `MILESTONES.md` and `milestones.csv`.

