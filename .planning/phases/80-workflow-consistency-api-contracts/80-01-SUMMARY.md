---
phase: 80-workflow-consistency-api-contracts
plan: "01"
subsystem: workflows
tags: [atomicity, concurrency, race-condition, postgres-rpc, toctou]
dependency_graph:
  requires: []
  provides: [atomic-workflow-start-rpc]
  affects: [app/workflows/engine.py, supabase/migrations]
tech_stack:
  added: []
  patterns: [postgres-insert-select-where, security-definer-rpc, rpc-over-insert]
key_files:
  created:
    - supabase/migrations/20260426200000_atomic_workflow_execution_start.sql
    - tests/unit/test_atomic_workflow_start.py
  modified:
    - app/workflows/engine.py
    - tests/unit/test_workflow_engine_readiness_gate.py
decisions:
  - "Atomic INSERT...SELECT...WHERE replaces SELECT COUNT + INSERT to eliminate TOCTOU race at DB level"
  - "p_max_concurrent=0 treated as unlimited — SQL function uses IF branch to skip count check entirely"
  - "On limit exceeded, a follow-up SELECT COUNT is used only for the error message — not for gating"
  - "SECURITY DEFINER + SET search_path=public used so RPC works through authenticated+service_role"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-27"
  tasks_completed: 2
  files_changed: 4
requirements_satisfied: [ARCH-03]
---

# Phase 80 Plan 01: Atomic Workflow Execution Start Summary

**One-liner:** Postgres RPC `start_workflow_execution_atomic` replaces SELECT COUNT + INSERT TOCTOU race with a single atomic statement, preventing duplicate concurrent workflow executions across Cloud Run replicas.

## What Was Built

The `start_workflow` method in `app/workflows/engine.py` previously used a two-step pattern:

1. `SELECT COUNT(*) ... WHERE status IN (active_statuses)` — check if under limit
2. `INSERT INTO workflow_executions ...` — create the execution row

Between steps 1 and 2, two Cloud Run instances handling simultaneous requests for the same user could both pass the count check before either inserts, allowing both to proceed past the `MAX_CONCURRENT_EXECUTIONS_PER_USER` limit.

The fix replaces both steps with a single `client.rpc("start_workflow_execution_atomic", params).execute()` call. The Postgres function uses an atomic `INSERT ... SELECT ... WHERE (COUNT(*) < limit) RETURNING *` pattern — if no row is returned, the limit was exceeded at the moment of the insert attempt, with no race window.

## Tasks Completed

### Task 1: SQL Migration + TDD Tests
**Commits:** `751a4678` (RED), `7e84715b` (GREEN)

Created `supabase/migrations/20260426200000_atomic_workflow_execution_start.sql` with:
- `start_workflow_execution_atomic` Postgres function, `RETURNS SETOF workflow_executions`
- Branch 1 (`p_max_concurrent <= 0`): plain INSERT, no count check — unlimited mode
- Branch 2 (`p_max_concurrent > 0`): atomic `INSERT ... SELECT ... WHERE COUNT < limit RETURNING *`
- `SECURITY DEFINER` + `SET search_path = public`
- GRANT EXECUTE to `authenticated` and `service_role`

Created `tests/unit/test_atomic_workflow_start.py` with 5 tests:
- Success path: RPC called with correct params, execution_id extracted
- Limit exceeded: RPC returns empty, error dict with correct shape returned
- Error shape completeness: all 4 required fields present and correct types
- Zero-limit bypass: `p_max_concurrent=0` passed through to RPC
- No SELECT COUNT before RPC: old TOCTOU pattern is gone

### Task 2: Replace engine.py SELECT+INSERT with RPC
**Commit:** `7e84715b`

Removed the `if MAX_CONCURRENT_EXECUTIONS_PER_USER > 0:` block (SELECT COUNT + limit check) and the separate `client.table("workflow_executions").insert(execution_data).execute()`. Replaced with:

```python
res_exec = await client.rpc("start_workflow_execution_atomic", rpc_params).execute()
if not res_exec.data:
    # fetch count for error message only (not for gating)
    ...
    return {"error": ..., "error_code": "concurrent_execution_limit", ...}
execution_id = res_exec.data[0]["id"]
```

The error response shape `{error, error_code, active_count, limit}` is fully preserved for frontend callers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated _FakeDb in readiness gate tests to support rpc()**
- **Found during:** Task 2 verification (regression run)
- **Issue:** `test_workflow_engine_readiness_gate.py` uses `_FakeDb` which had `table()` and `insert()` but no `rpc()`. After engine.py switched to RPC, 3 of 5 readiness gate tests hit `AttributeError: '_FakeDb' object has no attribute 'rpc'`.
- **Fix:** Added `_FakeRpcQuery` class and `rpc()` method to `_FakeDb` that records params in `execution_inserts` and returns a fake pending execution row.
- **Files modified:** `tests/unit/test_workflow_engine_readiness_gate.py`
- **Commit:** `7e84715b`

### Pre-existing Issues (Out of Scope)

Two F841 lint errors (`client` assigned but unused) exist at lines 1267 and 1469 of `engine.py` in unrelated methods (`_advance_workflow_step`, `_trigger_workflow_advancement`). These pre-date this plan and are logged to deferred items.

## Verification Results

| Check | Result |
|---|---|
| `pytest test_atomic_workflow_start.py` | 5 passed |
| `pytest test_workflow_execution_contracts.py` | 3 passed |
| `pytest test_workflow_engine_readiness_gate.py` | 5 passed |
| All workflow unit tests | 67 passed |
| `grep start_workflow_execution_atomic engine.py` | 1 match |
| Migration file exists | Yes |
| SQL has atomic INSERT...WHERE subquery | Yes |
| SQL has p_max_concurrent<=0 branch | Yes |
| Error response shape preserved | Yes |

## Self-Check

Files created/modified:
- `supabase/migrations/20260426200000_atomic_workflow_execution_start.sql` — FOUND
- `app/workflows/engine.py` — FOUND (modified)
- `tests/unit/test_atomic_workflow_start.py` — FOUND
- `tests/unit/test_workflow_engine_readiness_gate.py` — FOUND (modified)

Commits:
- `751a4678` — FOUND (RED tests)
- `7e84715b` — FOUND (implementation + GREEN)

## Self-Check: PASSED
