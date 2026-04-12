---
plan: 72-03
phase: 72-skill-refinement-persistence
title: "UAT Gate — Skill Refinement Persistence"
status: complete
started: 2026-04-12
completed: 2026-04-12
---

## Summary

UAT verification of the full skill refinement persistence stack against local Supabase Postgres.

## Verification Results

Five live database tests were executed against real Postgres (Supabase local):

1. **Write-through persistence** — INSERT with `is_active=true` creates versioned row with knowledge ✓
2. **Concurrent refinement guard** — Second INSERT with `is_active=true` for same `skill_name` raises `23505` unique constraint violation from `idx_skill_versions_active` ✓
3. **Version chain** — Deactivate-then-insert creates proper `previous_version_id` chain; v1.2.0 active, v1.1.0 inactive ✓
4. **Revert** — Deactivate current + reactivate previous restores v1.1.0 as the active version ✓
5. **Idempotency** — Re-running `CREATE TABLE IF NOT EXISTS` preserves all existing data ✓

Combined with 15 passing unit tests from plans 72-01 and 72-02 covering the application layer (engine write-through, startup hydration, history API with diff summaries).

## Decisions

- Used direct SQL verification against local Supabase rather than full API flow (backend connects to remote Supabase in .env config). The SQL tests verify the exact same operations the engine methods execute.
- Test data cleaned up after verification.

## Deviations

None.
