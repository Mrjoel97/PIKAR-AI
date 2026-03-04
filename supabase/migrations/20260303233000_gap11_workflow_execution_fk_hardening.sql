-- GAP-11 relational integrity hardening:
-- 1) Snapshot orphaned workflow executions for audit.
-- 2) Remove orphaned rows that block FK creation.
-- 3) Add and validate forward FK constraints.

CREATE TABLE IF NOT EXISTS public.workflow_execution_orphan_audit (
    execution_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    started_by UUID,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    execution_payload JSONB NOT NULL
);

ALTER TABLE public.workflow_execution_orphan_audit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages workflow execution orphan audit" ON public.workflow_execution_orphan_audit;
CREATE POLICY "Service role manages workflow execution orphan audit"
ON public.workflow_execution_orphan_audit FOR ALL TO service_role
USING (true)
WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_user_id
ON public.workflow_executions(user_id);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_started_by
ON public.workflow_executions(started_by);

WITH orphaned AS (
    SELECT
        we.id,
        we.user_id,
        we.started_by,
        we.status,
        to_jsonb(we) AS payload
    FROM public.workflow_executions we
    LEFT JOIN auth.users au
        ON au.id = we.user_id
    WHERE au.id IS NULL
)
INSERT INTO public.workflow_execution_orphan_audit (
    execution_id,
    user_id,
    started_by,
    status,
    reason,
    execution_payload
)
SELECT
    orphaned.id,
    orphaned.user_id,
    orphaned.started_by,
    orphaned.status,
    'orphan_user_id_pre_fk_cleanup',
    orphaned.payload
FROM orphaned
ON CONFLICT (execution_id) DO NOTHING;

DELETE FROM public.workflow_executions we
WHERE EXISTS (
    SELECT 1
    FROM public.workflow_execution_orphan_audit oa
    WHERE oa.execution_id = we.id
      AND oa.reason = 'orphan_user_id_pre_fk_cleanup'
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'workflow_executions_user_id_fkey'
    ) THEN
        ALTER TABLE public.workflow_executions
        ADD CONSTRAINT workflow_executions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES auth.users(id)
        ON DELETE CASCADE
        NOT VALID;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'workflow_executions_started_by_fkey'
    ) THEN
        ALTER TABLE public.workflow_executions
        ADD CONSTRAINT workflow_executions_started_by_fkey
        FOREIGN KEY (started_by)
        REFERENCES auth.users(id)
        ON DELETE SET NULL
        NOT VALID;
    END IF;
END $$;

ALTER TABLE public.workflow_executions
VALIDATE CONSTRAINT workflow_executions_user_id_fkey;

ALTER TABLE public.workflow_executions
VALIDATE CONSTRAINT workflow_executions_started_by_fkey;
