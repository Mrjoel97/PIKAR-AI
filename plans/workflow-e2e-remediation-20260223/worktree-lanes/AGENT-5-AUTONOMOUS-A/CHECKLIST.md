# AGENT-5-AUTONOMOUS-A Worktree Execution Checklist

- Lane type: `fully autonomous`
- Focus: Deterministic strict-mode completion, output quality, and idempotent retry/cancel behavior.
- Suggested worktree path: `.tmp/codex-parallel/worktrees/wt-agent-5-autonomous-a`
- Suggested branch name: `workflow-e2e/agent-5-autonomous-a`
- Depends on: `AGENT-0-INFRA`

## Worktree Setup

```bash
git worktree add .tmp/codex-parallel/worktrees/wt-agent-5-autonomous-a -b workflow-e2e/agent-5-autonomous-a main
cd .tmp/codex-parallel/worktrees/wt-agent-5-autonomous-a
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
| Strategic Planning Cycle | strategy | P1 | 31 | 429 | BLOCKED_ENV_CONFIG |
| Policy Update | legal | P1 | 9 | 429 | BLOCKED_ENV_CONFIG |
| Partnership Development | strategy | P1 | 4 | 429 | BLOCKED_ENV_CONFIG |
| Customer Onboarding | support | P2 | 3 | 429 | BLOCKED_ENV_CONFIG |
| Financial Reporting | finance | P2 | 3 | 429 | BLOCKED_ENV_CONFIG |
| Knowledge Base Update | support | P2 | 2 | 429 | BLOCKED_ENV_CONFIG |
| SEO Optimization Audit | marketing | P2 | 2 | 200 | PARTIAL_START_ONLY |
| IP Filing | legal | P3 | 1 | 429 | BLOCKED_ENV_CONFIG |
| Product Launch Campaign | marketing | P3 | 1 | 200 | PARTIAL_START_ONLY |
| Market Entry Strategy | strategy | P3 | 0 | 429 | BLOCKED_ENV_CONFIG |
| Support Ticket Resolution | support | P3 | 0 | 429 | BLOCKED_ENV_CONFIG |

## Execution Checklist (Lane-Level)

- [ ] Implement lane-specific fixes in small commits grouped by shared code path (tools/engine/router/frontend/tests).
- [ ] For each workflow, execute the per-workflow tasklist from `workflow_tasklist_68.csv` and capture evidence refs.
- [ ] Run targeted tests after each shared-code change before continuing to the next workflow cluster.
- [ ] Maintain a running lane changelog (files touched, behavior changes, risks, open follow-ups).
- [ ] Update milestone tracker statuses and evidence links continuously (not at the end).

## Deliverables (Lane)

- [ ] Assigned workflows complete in strict mode without human approval unless reclassified.
- [ ] Outcome summaries/history artifacts are useful and persisted.
- [ ] Retry/cancel idempotency assertions covered by tests.

## Commit / PR Handoff

- [ ] Branch rebased or merged with current `main` (or merge train branch) before final validation.
- [ ] Tests run and results recorded in milestone tracker.
- [ ] Evidence refs included for each completed milestone/workflow.
- [ ] Known risks and deferred items listed explicitly.
- [ ] Ready-for-merge status marked in `MILESTONES.md` and `milestones.csv`.

