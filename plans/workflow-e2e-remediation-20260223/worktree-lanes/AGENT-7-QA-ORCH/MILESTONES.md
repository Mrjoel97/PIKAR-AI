# AGENT-7-QA-ORCH Milestone Tracker

- Worktree path: `.tmp/codex-parallel/worktrees/wt-agent-7-qa-orch`
- Branch: `workflow-e2e/agent-7-qa-orch`
- Status values: `todo`, `in_progress`, `blocked`, `done`

| Milestone ID | Type | Priority | Status | Scope | Title | Depends On | Evidence Ref | Owner |
|---|---|---|---|---|---|---|---|---|
| M00 | setup | P0 | todo | lane | Worktree created and lane preflight complete | AGENT-1-GATES,AGENT-2-INTEGRATIONS,AGENT-3-DEGRADED-A,AGENT-4-DEGRADED-B,AGENT-5-AUTONOMOUS-A,AGENT-6-AUTONOMOUS-B |  |  |
| M10 | qa | P1 | todo | lane | Browser subset workflow start + approval path validation complete | M00 |  |  |
| M20 | qa | P1 | todo | lane | Exhaustive audit rerun with per-item polling complete | M00 |  |  |
| M30 | qa | P1 | todo | lane | Final diff against baseline audit published | M00 |  |  |
| M99 | handoff | P1 | todo | lane | QA orchestration lane sign-off / release recommendation complete | M30 |  |  |

## Notes

- `M10` After AGENT-1 merge
- `M20` After AGENT-1..AGENT-6 merges + infra
- `M30` Includes workflow/journey deltas and blocker resolution summary
- `M99` Final evidence package and merge report ready
