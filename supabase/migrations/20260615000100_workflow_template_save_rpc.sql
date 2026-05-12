-- Migration: 20260615000100_workflow_template_save_rpc.sql
-- Phase 110-02 (Spec B Phase 2) — RPC layer for template Save + run-time pinning.
--
-- Purpose
-- -------
-- 1. Extend ``start_workflow_execution_atomic`` with a new 10th parameter
--    ``p_template_version_id UUID DEFAULT NULL`` so the engine can pin each
--    new execution row to the workflow_template_versions row that was current
--    at execution start. Adding a parameter changes the function signature,
--    which means ``CREATE OR REPLACE FUNCTION`` alone is rejected by Postgres
--    (it allows replacing only when the argument list is identical). The
--    migration first ``DROP FUNCTION ... CASCADE``s the existing 9-arg
--    signature, then recreates with the new 10-arg signature.
--
--    Caller-audit precondition (run as part of plan execution, not the
--    migration body):
--
--        grep -rn 'start_workflow_execution_atomic' app/ supabase/ tests/
--
--    Confirmed all live callers use named-keyword ``.rpc("start_workflow_execution_atomic", {...})``
--    invocation, NOT positional args. The new ``p_template_version_id`` default
--    of NULL preserves every existing caller's behaviour unchanged.
--
-- 2. Create ``save_workflow_template_version`` — a server-side atomic two-table
--    write that (a) checks the caller's If-Match value against the current
--    version's saved_at, (b) inserts a new immutable row in
--    workflow_template_versions, (c) updates workflow_templates.current_version_id
--    to point at the new version, all inside a single function call so the
--    Python layer never sees a torn write. Returns the new version row or zero
--    rows on If-Match mismatch (the caller translates a zero-row return into
--    an HTTP 412 Precondition Failed).
--
-- Idempotency
-- -----------
-- Every CREATE statement uses an IF NOT EXISTS or CREATE OR REPLACE variant.
-- The DROP FUNCTION is wrapped in IF EXISTS so a clean re-apply is a no-op.
--
-- supabase CLI 2.75 dollar-quote bug
-- ----------------------------------
-- Uses $BODY$ named dollar quotes throughout (NOT bare $$), per the bug noted
-- in Phase 109 + 110-01 SUMMARYs.
--
-- See: .planning/phases/110-workflow-node-editor-editable/110-02-backend-save-load-PLAN.md
--      .planning/phases/110-workflow-node-editor-editable/110-CONTEXT.md
--      .planning/phases/110-workflow-node-editor-editable/110-01-SUMMARY.md

-- ----------------------------------------------------------------------------
-- 1. Drop the existing 9-arg start_workflow_execution_atomic signature.
--    PostgreSQL identifies functions by (name, argument types); replacing
--    one signature with a different argument list requires DROP + CREATE,
--    not CREATE OR REPLACE. CASCADE handles dependent objects in case any
--    views/triggers reference the function (Phase 109 audit showed only
--    Python callers via .rpc(), but CASCADE is defensive).
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT
) CASCADE;

-- ----------------------------------------------------------------------------
-- 2. Recreate start_workflow_execution_atomic with the new 10-arg signature.
--    Body is copied verbatim from 20260511130100_atomic_workflow_execution_start_goal.sql
--    with one change: template_version_id is appended to BOTH the column list
--    AND the VALUES/SELECT clause in both branches (no-limit and concurrency-
--    limited). The legacy template_version INT column continues to be written
--    alongside the new template_version_id UUID column.
--
--    An end-to-end regression test for the existing 9-arg caller shape
--    (omitting p_template_version_id) lives in
--    tests/integration/test_linear_workflow_execution_post_versioning.py —
--    confirms NULL default lets all existing callers keep working unchanged.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION start_workflow_execution_atomic(
    p_user_id              UUID,
    p_template_id          UUID,
    p_template_version     INT     DEFAULT NULL,
    p_started_by           UUID    DEFAULT NULL,
    p_run_source           TEXT    DEFAULT 'user_ui',
    p_name                 TEXT    DEFAULT 'Workflow Execution',
    p_context              JSONB   DEFAULT '{}'::jsonb,
    p_max_concurrent       INT     DEFAULT 3,
    p_goal                 TEXT    DEFAULT NULL,
    p_template_version_id  UUID    DEFAULT NULL    -- NEW (10th param) — Phase 110-02
)
RETURNS SETOF workflow_executions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $BODY$
DECLARE
    v_started_by UUID;
BEGIN
    -- Default p_started_by to p_user_id when not provided
    v_started_by := COALESCE(p_started_by, p_user_id);

    -- Branch 1: No concurrency limit (p_max_concurrent <= 0 means unlimited).
    -- Always insert without checking active count.
    IF p_max_concurrent <= 0 THEN
        RETURN QUERY
        INSERT INTO workflow_executions (
            user_id,
            template_id,
            template_version,
            template_version_id,
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
            p_template_version_id,
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

    -- Branch 2: Concurrency limit enabled (p_max_concurrent > 0).
    -- Atomically insert only when the active execution count is below the
    -- limit. The WHERE subquery and INSERT are evaluated as a single
    -- statement, eliminating the TOCTOU window that existed between the old
    -- SELECT COUNT and INSERT.
    RETURN QUERY
    INSERT INTO workflow_executions (
        user_id,
        template_id,
        template_version,
        template_version_id,
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
        p_template_version_id,
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
$BODY$;

-- Grants for the new 10-arg signature.
GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT, UUID
) TO authenticated;

GRANT EXECUTE ON FUNCTION start_workflow_execution_atomic(
    UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT, UUID
) TO service_role;

-- ----------------------------------------------------------------------------
-- 3. save_workflow_template_version — atomic two-table Save.
--
--    Inputs
--      p_template_id          — which workflow_templates row to save under
--      p_user_id              — auth.uid() of the saving user (NULL only for
--                               system contexts; production always supplies)
--      p_graph_nodes          — JSONB array of node definitions
--      p_graph_edges          — JSONB array of edge definitions
--      p_graph_layout         — JSONB dict of layout positions (nullable)
--      p_comment              — optional Save message (nullable)
--      p_if_match_saved_at    — caller's last-known saved_at for optimistic
--                               locking (NULL = first save / unconditional)
--      p_parent_version_id    — explicit override for the revert flow; when
--                               NULL, defaults to the current version's id so
--                               normal saves chain naturally
--
--    Behaviour
--      - When p_if_match_saved_at is non-NULL and the current version's
--        saved_at differs, returns ZERO rows. The Python caller translates
--        this to HTTP 412 Precondition Failed.
--      - When the check passes (or there is no current version yet), inserts
--        a new workflow_template_versions row with version_number = max+1
--        and updates workflow_templates.current_version_id to point at it.
--      - Returns the newly-inserted version row (SETOF, one row).
--
--    Atomicity
--      Both writes happen inside the single function call body, which runs
--      in an implicit transaction. Either both succeed or neither does.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION save_workflow_template_version(
    p_template_id           UUID,
    p_user_id               UUID,
    p_graph_nodes           JSONB,
    p_graph_edges           JSONB,
    p_graph_layout          JSONB,
    p_comment               TEXT,
    p_if_match_saved_at     TIMESTAMPTZ,
    p_parent_version_id     UUID DEFAULT NULL    -- explicit override for revert flow
)
RETURNS SETOF workflow_template_versions
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $BODY$
DECLARE
    v_current_version  workflow_template_versions%ROWTYPE;
    v_next_number      INT;
    v_new_version      workflow_template_versions%ROWTYPE;
    v_parent_id        UUID;
BEGIN
    -- Load the current version row (or leave v_current_version with NULL
    -- fields if the template has no version yet — e.g. a seed pre-copy or
    -- a row whose Phase 109 graph projection was NULL).
    SELECT wtv.* INTO v_current_version
    FROM workflow_template_versions wtv
    JOIN workflow_templates wt ON wt.current_version_id = wtv.id
    WHERE wt.id = p_template_id;

    -- If-Match check: only enforce when caller supplied a value AND a
    -- current version exists. Skipping the check when the template has no
    -- current_version_id yet lets first-save flow through.
    IF p_if_match_saved_at IS NOT NULL AND v_current_version.saved_at IS NOT NULL THEN
        IF v_current_version.saved_at <> p_if_match_saved_at THEN
            -- Stale write — return no rows; caller translates to HTTP 412.
            RETURN;
        END IF;
    END IF;

    -- Compute next version number monotonically per template.
    SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_next_number
    FROM workflow_template_versions
    WHERE template_id = p_template_id;

    -- Parent: explicit override (for revert flow) OR the current version's id.
    -- When v_current_version is empty (first save), parent is NULL.
    v_parent_id := COALESCE(p_parent_version_id, v_current_version.id);

    -- Insert the new version row.
    INSERT INTO workflow_template_versions (
        template_id,
        version_number,
        parent_version_id,
        graph_nodes,
        graph_edges,
        graph_layout,
        saved_by_user_id,
        comment
    ) VALUES (
        p_template_id,
        v_next_number,
        v_parent_id,
        p_graph_nodes,
        p_graph_edges,
        p_graph_layout,
        p_user_id,
        p_comment
    )
    RETURNING * INTO v_new_version;

    -- Update template's current_version_id pointer + bump updated_at.
    UPDATE workflow_templates
    SET current_version_id = v_new_version.id,
        updated_at = now()
    WHERE id = p_template_id;

    -- Return the new version row to the caller (Python layer reads
    -- saved_at to build the ETag wire format).
    RETURN NEXT v_new_version;
END;
$BODY$;

-- Grants for the save_workflow_template_version function.
GRANT EXECUTE ON FUNCTION save_workflow_template_version(
    UUID, UUID, JSONB, JSONB, JSONB, TEXT, TIMESTAMPTZ, UUID
) TO authenticated;

GRANT EXECUTE ON FUNCTION save_workflow_template_version(
    UUID, UUID, JSONB, JSONB, JSONB, TEXT, TIMESTAMPTZ, UUID
) TO service_role;

-- ----------------------------------------------------------------------------
-- 4. ROLLBACK PROCEDURE (manual; not auto-executed)
--
-- To fully roll back this migration:
--
--   DROP FUNCTION IF EXISTS save_workflow_template_version(
--       UUID, UUID, JSONB, JSONB, JSONB, TEXT, TIMESTAMPTZ, UUID
--   ) CASCADE;
--
--   DROP FUNCTION IF EXISTS start_workflow_execution_atomic(
--       UUID, UUID, INT, UUID, TEXT, TEXT, JSONB, INT, TEXT, UUID
--   ) CASCADE;
--
--   -- Then re-apply 20260511130100_atomic_workflow_execution_start_goal.sql
--   -- to restore the 9-arg signature.
--
-- After Plan 02 ships and all in-flight executions complete, the legacy
-- workflow_executions.template_version INT column can be dropped in a
-- "Phase 110.5" cleanup migration. That cleanup is OUT OF SCOPE here —
-- both the legacy INT column and the new UUID column intentionally
-- coexist after this migration.
