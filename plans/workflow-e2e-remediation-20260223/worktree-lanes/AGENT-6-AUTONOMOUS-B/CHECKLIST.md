# AGENT-6-AUTONOMOUS-B Worktree Execution Checklist

- Lane type: `fully autonomous`
- Focus: Deterministic strict-mode completion, output quality, and idempotent retry/cancel behavior.
- Suggested worktree path: `.tmp/codex-parallel/worktrees/wt-agent-6-autonomous-b`
- Suggested branch name: `workflow-e2e/agent-6-autonomous-b`
- Depends on: `AGENT-0-INFRA`

## Worktree Setup

```bash
git worktree add .tmp/codex-parallel/worktrees/wt-agent-6-autonomous-b -b workflow-e2e/agent-6-autonomous-b main
cd .tmp/codex-parallel/worktrees/wt-agent-6-autonomous-b
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
| Content Creation Workflow | marketing | P1 | 13 | 429 | BLOCKED_ENV_CONFIG |
| GDPR Compliance Audit | legal | P1 | 4 | 429 | BLOCKED_ENV_CONFIG |
| Roadmap Planning | product | P1 | 4 | 429 | BLOCKED_ENV_CONFIG |
| Email Nurture Sequence | marketing | P2 | 3 | 200 | PARTIAL_START_ONLY |
| Win/Loss Analysis | sales | P2 | 3 | 429 | BLOCKED_ENV_CONFIG |
| Performance Review | hr | P2 | 2 | 200 | PARTIAL_START_ONLY |
| Social Media Calendar | marketing | P2 | 2 | 200 | PARTIAL_START_ONLY |
| Outbound Prospecting | sales | P3 | 1 | 200 | PARTIAL_START_ONLY |
| Webinar Hosting | marketing | P3 | 1 | 200 | PARTIAL_START_ONLY |
| Quarterly Business Review (QBR) | strategy | P3 | 0 | 429 | BLOCKED_ENV_CONFIG |
| User Research Sprint | product | P3 | 0 | 429 | BLOCKED_ENV_CONFIG |

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

