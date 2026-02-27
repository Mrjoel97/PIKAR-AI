# AGENT-1-GATES Worktree Execution Checklist

- Lane type: `human-gated`
- Focus: Approval-state correctness, `/approve` resume semantics, and frontend approval UX.
- Suggested worktree path: `.tmp/codex-parallel/worktrees/wt-agent-1-gates`
- Suggested branch name: `workflow-e2e/agent-1-gates`
- Depends on: `AGENT-0-INFRA`

## Worktree Setup

```bash
git worktree add .tmp/codex-parallel/worktrees/wt-agent-1-gates -b workflow-e2e/agent-1-gates main
cd .tmp/codex-parallel/worktrees/wt-agent-1-gates
```

## Pre-Flight Checklist

- [ ] Pull latest `main` and confirm no unresolved conflicts in the worktree.
- [ ] Confirm `AGENT-0-INFRA` prerequisites required for this lane are merged/deployed in the target E2E environment.
- [ ] Confirm strict E2E env flags are set as expected (`WORKFLOW_STRICT_TOOL_RESOLUTION`, `WORKFLOW_STRICT_CRITICAL_TOOL_GUARD`, `WORKFLOW_ALLOW_FALLBACK_SIMULATION=0`, readiness gate decision).
- [ ] Confirm dedicated test user/token strategy and rate-limit pacing are ready for batch verification.
- [ ] Create or confirm lane evidence directory (logs, screenshots, API traces, test outputs).

## Assigned Workflows (8)

| Workflow | Category | Priority | Journey Impact | Audit Start | Audit Status |
|---|---|---|---:|---:|---|
| Initiative Framework | strategy | P1 | 4 | 429 | BLOCKED_ENV_CONFIG |
| Competitor Analysis Workflow | strategy | P1 | 3 | 429 | BLOCKED_ENV_CONFIG |
| Lead Generation Workflow | sales | P1 | 3 | 429 | BLOCKED_ENV_CONFIG |
| Product Launch Workflow | strategy | P1 | 3 | 429 | BLOCKED_ENV_CONFIG |
| Social Media Campaign Workflow | marketing | P1 | 2 | 429 | BLOCKED_ENV_CONFIG |
| A/B Testing Workflow | data | P1 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Content Creation Workflow (Extended) | content | P1 | 0 | 429 | BLOCKED_ENV_CONFIG |
| Email Sequence Workflow | marketing | P1 | 0 | 429 | BLOCKED_ENV_CONFIG |

## Execution Checklist (Lane-Level)

- [ ] Implement lane-specific fixes in small commits grouped by shared code path (tools/engine/router/frontend/tests).
- [ ] For each workflow, execute the per-workflow tasklist from `workflow_tasklist_68.csv` and capture evidence refs.
- [ ] Run targeted tests after each shared-code change before continuing to the next workflow cluster.
- [ ] Maintain a running lane changelog (files touched, behavior changes, risks, open follow-ups).
- [ ] Update milestone tracker statuses and evidence links continuously (not at the end).

## Deliverables (Lane)

- [ ] Approval gate path verified for all assigned workflows (API + SSE + persisted history).
- [ ] Frontend approval UI path validated for representative workflows and no desync after approve.
- [ ] Integration tests for approval gating/resume behavior added/updated.

## Commit / PR Handoff

- [ ] Branch rebased or merged with current `main` (or merge train branch) before final validation.
- [ ] Tests run and results recorded in milestone tracker.
- [ ] Evidence refs included for each completed milestone/workflow.
- [ ] Known risks and deferred items listed explicitly.
- [ ] Ready-for-merge status marked in `MILESTONES.md` and `milestones.csv`.

