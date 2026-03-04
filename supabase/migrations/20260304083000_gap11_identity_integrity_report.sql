-- GAP-11: identity-integrity report for workflow execution foreign-key hardening.
-- This function powers rollout verification and recurring observability checks.

CREATE OR REPLACE FUNCTION public.workflow_execution_identity_report()
RETURNS TABLE (
    checked_at TIMESTAMPTZ,
    workflow_execution_rows BIGINT,
    orphan_user_id_rows BIGINT,
    orphan_started_by_rows BIGINT,
    orphan_audit_rows BIGINT,
    user_fk_present BOOLEAN,
    user_fk_validated BOOLEAN,
    started_by_fk_present BOOLEAN,
    started_by_fk_validated BOOLEAN
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, auth, pg_catalog
AS $$
WITH fk_state AS (
    SELECT
        conname,
        convalidated
    FROM pg_catalog.pg_constraint
    WHERE conrelid = 'public.workflow_executions'::regclass
      AND conname IN (
          'workflow_executions_user_id_fkey',
          'workflow_executions_started_by_fkey'
      )
)
SELECT
    now() AS checked_at,
    (SELECT count(*) FROM public.workflow_executions) AS workflow_execution_rows,
    (
        SELECT count(*)
        FROM public.workflow_executions we
        LEFT JOIN auth.users au ON au.id = we.user_id
        WHERE au.id IS NULL
    ) AS orphan_user_id_rows,
    (
        SELECT count(*)
        FROM public.workflow_executions we
        LEFT JOIN auth.users au ON au.id = we.started_by
        WHERE we.started_by IS NOT NULL
          AND au.id IS NULL
    ) AS orphan_started_by_rows,
    (
        SELECT count(*)
        FROM public.workflow_execution_orphan_audit
    ) AS orphan_audit_rows,
    COALESCE(
        (SELECT true FROM fk_state WHERE conname = 'workflow_executions_user_id_fkey'),
        false
    ) AS user_fk_present,
    COALESCE(
        (SELECT convalidated FROM fk_state WHERE conname = 'workflow_executions_user_id_fkey'),
        false
    ) AS user_fk_validated,
    COALESCE(
        (SELECT true FROM fk_state WHERE conname = 'workflow_executions_started_by_fkey'),
        false
    ) AS started_by_fk_present,
    COALESCE(
        (SELECT convalidated FROM fk_state WHERE conname = 'workflow_executions_started_by_fkey'),
        false
    ) AS started_by_fk_validated;
$$;

COMMENT ON FUNCTION public.workflow_execution_identity_report() IS
'GAP-11 integrity report for workflow_executions user identity FKs and orphan counts.';

REVOKE ALL ON FUNCTION public.workflow_execution_identity_report() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.workflow_execution_identity_report() TO service_role;
