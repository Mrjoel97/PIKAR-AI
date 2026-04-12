---
phase: 72-skill-refinement-persistence
plan: 01
subsystem: self-improvement-engine
tags: [persistence, skill-versions, revert, supabase, TDD]
dependency_graph:
  requires: [improvement_actions table]
  provides: [skill_versions table, DB-backed skill revert]
  affects: [app/services/self_improvement_engine.py]
tech_stack:
  added: []
  patterns: [transactional write-through, DB-backed revert, unique partial index]
key_files:
  created:
    - supabase/migrations/20260412100000_skill_versions.sql
    - tests/unit/test_skill_version_persistence.py
  modified:
    - app/services/self_improvement_engine.py
decisions:
  - DB failures in write-through are caught so in-memory updates still happen as fallback
  - Unique partial index enforces exactly one active version per skill_name
  - Revert reads previous_version_id chain rather than scanning by created_at
metrics:
  duration: 8min
  completed: 2026-04-12
---

# Phase 72 Plan 01: Skill Version Persistence Summary

Supabase skill_versions table with unique partial index, transactional write-through in _execute_skill_refined, and DB-backed revert in _attempt_revert

## What Was Done

### Task 1: Create skill_versions migration and write-through tests (TDD RED)
- **Commit:** `076666b6`
- Created `supabase/migrations/20260412100000_skill_versions.sql` with:
  - `skill_versions` table (id, skill_name, version, knowledge, previous_version_id, source_action_id, created_by, created_at, is_active, metadata)
  - Unique partial index `idx_skill_versions_active` on `(skill_name) WHERE is_active = true` enforcing one active version per skill
  - Supporting indexes for name+recency and active lookups
  - RLS policies (authenticated read, service_role full access) with idempotent DO $$ guards
- Created `tests/unit/test_skill_version_persistence.py` with 6 tests (5 RED, 1 already passing)

### Task 2: Wire write-through and revert into SelfImprovementEngine (GREEN)
- **Commit:** `7287374f`
- Modified `_execute_skill_refined` to:
  1. Query skill_versions for the current active row
  2. Deactivate previous active version (is_active=False)
  3. Insert new version with is_active=True, previous_version_id, source_action_id, metadata
  4. Then update in-memory registry (existing behavior preserved)
  5. Return new_version_id in result dict
- Modified `_attempt_revert` for `skill_refined` action type to:
  1. Find current active version from skill_versions
  2. Load previous version via previous_version_id
  3. Deactivate current, activate previous in DB
  4. Restore skill.knowledge and skill.version in registry
  5. Gracefully handle no-previous-version edge case
- All DB operations wrapped in try/except -- failures log warnings, in-memory fallback preserved

## Verification

- 6 new persistence tests pass (write-through insert, deactivation, previous_version_id, revert DB ops, revert in-memory, no-previous graceful)
- 5 existing SelfImprovementEngine tests still pass
- Ruff lint clean on all modified files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion operator precedence**
- **Found during:** Task 1 -> Task 2 transition (GREEN phase)
- **Issue:** Test assertion used `"x" in (a or b if cond else c)` which evaluates with wrong operator precedence
- **Fix:** Extracted `_get_op_name()` and `_has_op()` helper functions for reliable op_name extraction from mock call args
- **Files modified:** tests/unit/test_skill_version_persistence.py
- **Commit:** 7287374f

## Self-Check: PASSED
