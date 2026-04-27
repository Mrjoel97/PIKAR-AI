-- Migration: Atomic workflow execution start RPC
-- Purpose: Eliminate the TOCTOU race condition in engine.py where two concurrent
--          Cloud Run replicas could both pass the SELECT COUNT check before either
--          performs the INSERT, allowing duplicate concurrent executions to bypass
--          the MAX_CONCURRENT_EXECUTIONS_PER_USER limit.
--
-- This function atomically combines the count check and the insert in a single
-- Postgres statement, so no two concurrent callers can both pass the limit gate.
--
-- Parameters:
--   p_user_id          UUID   — the user starting the workflow
--   p_template_id      UUID   — the workflow template to execute
--   p_template_version INT    — optional template version (NULL = latest)
--   p_started_by       UUID   — who triggered the start (usually same as p_user_id)
--   p_run_source       TEXT   — origin of the run (default 'user_ui')
--   p_name             TEXT   — display name for the execution record
--   p_context          JSONB  — initial execution context payload
--   p_max_concurrent   INT    — per-user concurrency limit; 0 or negative = no limit
--
-- Returns: SETOF workflow_executions
--   Non-empty set → execution was created successfully (status='pending')
--   Empty set     → concurrent limit was exceeded; caller must return error to user

CREATE OR REPLACE FUNCTION start_workflow_execution_atomic(
    p_user_id          UUID,
    p_template_id      UUID,
    p_template_version INT     DEFAULT NULL,
    p_started_by       UUID    DEFAULT NULL,
    p_run_source       TEXT    DEFAULT 'user_ui',
    p_name             TEXT    DEFAULT 'Workflow Execution',
    p_context          JSONB   DEFAULT '{}'::jsonb,
    p_max_concurrent   INT     DEFAULT 3
)
RETURNS SETOF workflow_executions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_started_by UUID;
BEGIN
    -- Default p_started_by to p_user_id when not provided
    v_started_by := COALESCE(p_started_by, p_user_id);

    -- Branch 1: No concurrency limit (p_max_concurrent <= 0 means unlimited)
    -- Always insert without checking active count.
    IF p_max_concurrent <= 0 THEN
        RETURN QUERY
        INSERT INTO workflow_executions (
            user_id,
            template_id,
            template_version,
            started_by,
            run_source,
            name,
            status,
            current_phase_index,
            current_step_index,
            context
        ) VALUES (
            p_user_id,
            p_template_id,
            p_template_version,
            v_started_by,
            p_run_source,
            p_name,
            'pending',
            0,
            0,
            p_context
        )
        RETURNING *;

        RETURN;
    END IF;

    -- Branch 2: Concurrency limit enabled (p_max_concurrent > 0)
    -- Atomically insert only when the active execution count is below the limit.
    -- The WHERE subquery and INSERT are evaluated as a single statement, eliminating
    -- the TOCTOU window that existed between the old SELECT COUNT and INSERT.
    RETURN QUERY
    INSERT INTO workflow_executions (
        user_id,
        template_id,
        template_version,
        started_by,
        run_source,
        name,
        status,
        current_phase_index,
        current_step_index,
        context
    )
    SELECT
        p_user_id,
        p_template_id,
        p_template_version,
        v_started_by,
        p_run_source,
        p_name,
        'pending',
        0,
        0,
        p_context
    WHERE (
        SELECT COUNT(*)
        FROM workflow_executions
        WHERE user_id = p_user_id
          AND status IN ('pending', 'running', 'paused', 'waiting_approval')
    ) < p_max_concurrent
    RETURNING *;
END;
$$;

-- Grant execution rights to authenticated users and the service role used by the backend
GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT
) TO authenticated;

GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT
) TO service_role;
