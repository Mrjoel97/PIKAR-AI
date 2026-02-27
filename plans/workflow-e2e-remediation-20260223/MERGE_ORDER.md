# Merge Order (AGENT-1 .. AGENT-7)

This merge order assumes **AGENT-0-INFRA** changes are completed and deployed first (not included in this packet set).

## Preconditions (Must Be True Before Merging AGENT-1..AGENT-6)
- `BACKEND_API_URL` configured in edge-function runtime and backend callback path reachable.
- `WORKFLOW_SERVICE_SECRET` configured consistently for service-auth `/workflows/execute-step`.
- Strict E2E flags agreed and applied in the target validation environment.
- Test user persona / pacing strategy prevents `429` distortion in batch verification.

## Recommended Merge Train
1. `AGENT-2-INTEGRATIONS`
2. `AGENT-1-GATES`
3. `AGENT-3-DEGRADED-A`
4. `AGENT-4-DEGRADED-B`
5. `AGENT-5-AUTONOMOUS-A`
6. `AGENT-6-AUTONOMOUS-B`
7. `AGENT-7-QA-ORCH` (docs/evidence/final rerun results, after code lanes)

## Why This Order
- Integration and approval path changes tend to affect shared engine/router/tooling behavior and should land before broad workflow-specific fixes.
- Degraded-path hardening can change shared fallback/strict-mode behavior and should settle before autonomous completion tuning.
- QA/Orchestration lane should merge last to avoid stale evidence and rerun outputs.

## Worktree Naming / Branch Conventions
| Lane | Worktree Path | Branch |
|---|---|---|
| AGENT-1-GATES | `.tmp/codex-parallel/worktrees/wt-agent-1-gates` | `workflow-e2e/agent-1-gates` |
| AGENT-2-INTEGRATIONS | `.tmp/codex-parallel/worktrees/wt-agent-2-integrations` | `workflow-e2e/agent-2-integrations` |
| AGENT-3-DEGRADED-A | `.tmp/codex-parallel/worktrees/wt-agent-3-degraded-a` | `workflow-e2e/agent-3-degraded-a` |
| AGENT-4-DEGRADED-B | `.tmp/codex-parallel/worktrees/wt-agent-4-degraded-b` | `workflow-e2e/agent-4-degraded-b` |
| AGENT-5-AUTONOMOUS-A | `.tmp/codex-parallel/worktrees/wt-agent-5-autonomous-a` | `workflow-e2e/agent-5-autonomous-a` |
| AGENT-6-AUTONOMOUS-B | `.tmp/codex-parallel/worktrees/wt-agent-6-autonomous-b` | `workflow-e2e/agent-6-autonomous-b` |
| AGENT-7-QA-ORCH | `.tmp/codex-parallel/worktrees/wt-agent-7-qa-orch` | `workflow-e2e/agent-7-qa-orch` |

## Merge Gates (Per Lane)
- `M99` in the lane `MILESTONES.md` is `done`.
- Lane checklist `CHECKLIST.md` commit/PR handoff section is complete.
- Tests and evidence refs are attached in `milestones.csv` / `MILESTONES.md`.
- Rebase/merge with current `main` and rerun lane smoke tests before merge.

## Final Program Gate
- After AGENT-1..AGENT-6 merge, AGENT-7 runs the exhaustive workflow/journey audit with per-item polling enabled and browser subset checks, then publishes final pass/fail evidence.
