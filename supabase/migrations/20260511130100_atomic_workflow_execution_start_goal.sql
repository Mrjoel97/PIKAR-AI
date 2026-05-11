-- Migration: Add p_goal parameter to start_workflow_execution_atomic RPC
-- Purpose: Allow callers to persist an optional free-text goal alongside the
--          new execution row.  p_goal is appended as the last parameter so all
--          existing callers that omit it continue to work without modification.
--
-- This is a CREATE OR REPLACE of the original function defined in
-- 20260426200000_atomic_workflow_execution_start.sql.  The original file is
-- left untouched; only the live Postgres function definition is replaced.

CREATE OR REPLACE FUNCTION start_workflow_execution_atomic(
    p_user_id          UUID,
    p_template_id      UUID,
    p_template_version INT     DEFAULT NULL,
    p_started_by       UUID    DEFAULT NULL,
    p_run_source       TEXT    DEFAULT 'user_ui',
    p_name             TEXT    DEFAULT 'Workflow Execution',
    p_context          JSONB   DEFAULT '{}'::jsonb,
    p_max_concurrent   INT     DEFAULT 3,
    p_goal             TEXT    DEFAULT NULL
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
            goal,
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
            p_goal,
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
        goal,
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
        p_goal,
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

-- Revoke old 8-arg signature grants and re-grant the new 9-arg signature.
-- The old overload is implicitly replaced because PostgreSQL identifies
-- functions by name + argument types; adding a parameter changes the signature.
GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT
) TO authenticated;

GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT
) TO service_role;
