# Phase 109 Deferred Items

## Out-of-Scope Discoveries During Execution

### frontend/src/contexts/PersonaContext.tsx (parallel automation)

During plan 109-01 execution, a parallel git automation modified
`frontend/src/contexts/PersonaContext.tsx` (added `AGENT_NAME_CACHE_KEY`
caching, `agentLoaded` field, 10s timeout + retry delay constants).

Discovered: 2026-05-11 while recovering from a branch-switch.
Disposition: Reverted from plan-109 working tree per
[project_branch_pollution_2026_05_09 memory] — "Parallel GSD automation
drops unrelated commits onto active branches; cherry-pick onto fresh
branch from main before pushing." The PersonaContext changes belong to
whatever feat/agent-operating-model branch the parallel automation is
running on, not this plan.

If the agent-display-name caching work is intended to ship, it should
land on its own branch via its own plan. Plan 109-01 only touches
supabase/migrations/ and tests/integration/.
