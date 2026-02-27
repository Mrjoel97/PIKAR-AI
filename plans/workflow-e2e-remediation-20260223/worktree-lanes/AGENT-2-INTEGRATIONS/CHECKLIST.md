# AGENT-2-INTEGRATIONS Worktree Execution Checklist

- Lane type: `integration-dependent`
- Focus: Sandbox integration credentialing, strict-mode integration behavior, and contract validation.
- Suggested worktree path: `.tmp/codex-parallel/worktrees/wt-agent-2-integrations`
- Suggested branch name: `workflow-e2e/agent-2-integrations`
- Depends on: `AGENT-0-INFRA`

## Worktree Setup

```bash
git worktree add .tmp/codex-parallel/worktrees/wt-agent-2-integrations -b workflow-e2e/agent-2-integrations main
cd .tmp/codex-parallel/worktrees/wt-agent-2-integrations
```

## Pre-Flight Checklist

- [ ] Pull latest `main` and confirm no unresolved conflicts in the worktree.
- [ ] Confirm `AGENT-0-INFRA` prerequisites required for this lane are merged/deployed in the target E2E environment.
- [ ] Confirm strict E2E env flags are set as expected (`WORKFLOW_STRICT_TOOL_RESOLUTION`, `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD`, `WORKFLOW_ALLOW_FALLBACK_SIMULATION=0`, readiness gate decision).
- [ ] Confirm dedicated test user/token strategy and rate-limit pacing are ready for batch verification.
- [ ] Create or confirm lane evidence directory (logs, screenshots, API traces, test outputs).

## Assigned Workflows (11)

| Workflow | Category | Priority | Journey Impact | Audit Start | Audit Status |
|---|---|---|---:|---:|---|
| Account Renewal | sales | P1 | 3 | 200 | PARTIAL_START_ONLY |
| Analytics Implementation | data | P1 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Benefits Enrollment | hr | P1 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Dashboard Creation | data | P1 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Data Pipeline Setup | data | P1 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Feature Development | product | P1 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Influencer Outreach | marketing | P1 | 1 | 200 | PARTIAL_START_ONLY |
| Payroll Processing | hr | P1 | 1 | 200 | PARTIAL_START_ONLY |
| Deal Closing | sales | P1 | 0 | 200 | PARTIAL_START_ONLY |
| Machine Learning Pipeline | data | P1 | 0 | 429 | BLOCKED_ENV_CONFIG |
| Sales Training | sales | P1 | 0 | 200 | PARTIAL_START_ONLY |

## Execution Checklist (Lane-Level)

- [ ] Implement lane-specific fixes in small commits grouped by shared code path (tools/engine/router/frontend/tests).
- [ ] For each workflow, execute the per-workflow tasklist from `workflow_tasklist_68.csv` and capture evidence refs.
- [ ] Run targeted tests after each shared-code change before continuing to the next workflow cluster.
- [ ] Maintain a running lane changelog (files touched, behavior changes, risks, open follow-ups).
- [ ] Update milestone tracker statuses and evidence links continuously (not at the end).

## Deliverables (Lane)

- [ ] Sandbox credentials and connection checks for assigned workflows documented and validated.
- [ ] Strict-mode no-simulation behavior proven for critical integration steps.
- [ ] Integration contract tests/fixtures added or updated.

## Commit / PR Handoff

- [ ] Branch rebased or merged with current `main` (or merge train branch) before final validation.
- [ ] Tests run and results recorded in milestone tracker.
- [ ] Evidence refs included for each completed milestone/workflow.
- [ ] Known risks and deferred items listed explicitly.
- [ ] Ready-for-merge status marked in `MILESTONES.md` and `milestones.csv`.

