# Plan: Phase 1 - Milestone 1 (Core Reliability & Infrastructure)

**Objective:** Standardize workflow execution and resolve architectural debt.

## 1. Migration Reconciliation (Task 1.1)
**Problem:** Numerical collisions (0037, 0053, 0054) and mixed naming formats (sequential vs timestamped).
**Strategy:**
- Rename colliding numeric migrations to a consistent, non-overlapping sequential sequence (0001-0060).
- For all new migrations going forward (2026*), ensure they are applied *after* the consolidated sequential baseline.
- Create a `scripts/verify/check_migrations.py` to detect prefix collisions during CI.

## 2. Deterministic Argument Mapping (Task 1.2)
**Problem:** `app/workflows/worker.py` uses a broad `**sys_context` and a `TypeError` fallback, making tool calls fragile and non-deterministic.
**Strategy:**
- Introduce a `ToolRegistry` that stores not just the function, but its `Pydantic` input model.
- Update `execute_step` to:
    1. Look up the tool in the registry.
    2. Extract relevant keys from `sys_context` (Workflow Initial Context + previous step outputs).
    3. Validate the extracted data against the tool's `input_schema`.
    4. Call the tool with strictly validated arguments.
- **Files to modify:** `app/workflows/worker.py`, `app/agents/tools/registry.py` (or equivalent).

## 3. Unified Worker Logic (Task 1.3)
**Problem:** Runtime behavior is split across `engine.py` (orchestration) and `worker.py` (execution), causing inconsistency.
**Strategy:**
- Move `execute_step` logic from `worker.py` into a shared `app/workflows/step_executor.py`.
- Both `WorkflowEngine` (for synchronous/immediate steps) and `WorkflowWorker` (for asynchronous/queued steps) will use the same `StepExecutor` class.
- Ensure state updates (completed_at, output_data) are handled identically regardless of the caller.

## 4. Redis Circuit Breakers (Task 1.4)
**Problem:** If Redis fails, the application might hang or crash during cache lookups.
**Strategy:**
- Wrap Redis calls in `app/services/cache.py` with a simple circuit breaker (e.g., `pycircuitbreaker` or a custom decorator).
- If Redis is down, the breaker should open and immediately fall back to the "Cache-Aside" direct database query.
- Add a `health/cache` endpoint check to monitor the breaker state.

## Verification Plan (Milestone 1)
- **Migrations:** Run `supabase migration list` to verify a clean, sequential order.
- **Arg Mapping:** Create a test workflow with a tool that has a strict Pydantic schema (e.g., `mcp_web_search`). Verify that it fails *before* execution if arguments are missing.
- **Unified Logic:** Run the same workflow via `engine.py` (direct) and `worker.py` (background). Verify identical `output_data` and `metadata` in the database.
- **Redis:** Manually stop the Redis container and verify the application still functions (with a slight latency increase) via `GET /health/cache`.
