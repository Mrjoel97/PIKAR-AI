-- supabase/migrations/20260511120050_restore_department_tasks.sql
--
-- Agent Operating Model — Restore prerequisite (department_tasks)
--
-- Mirrors the pattern in 20260506190000_restore_missing_admin_tables.sql:
-- 20260403400000_department_tasks.sql was recorded as applied in
-- supabase_migrations.schema_migrations but the table never materialised on
-- remote (likely casualty of the 2026-04-27 b484 → pikar-ai-project move per
-- project_cloud_run_migration.md memory).
--
-- The 7 Section A agent-operating-model migrations 20260511120100..120200
-- depend on this table existing. This restore brings the table + indexes +
-- RLS policies back. Trigger + view from the original are deferred — they
-- depend on _governance_set_updated_at which may also be missing, and
-- neither is load-bearing for the agent runtime work.
--
-- All statements are idempotent so re-applying the original 20260403400000
-- (e.g. via migration repair --status reverted + db push) remains safe.

CREATE TABLE IF NOT EXISTS public.department_tasks (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT        NOT NULL,
    description         TEXT,
    from_department_id  UUID        NOT NULL REFERENCES public.departments(id),
    to_department_id    UUID        NOT NULL REFERENCES public.departments(id),
    created_by          UUID        NOT NULL,
    assigned_to         UUID,
    status              TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority            TEXT        NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    due_date            TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    metadata            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dept_tasks_to_dept_status
    ON public.department_tasks (to_department_id, status)
    WHERE status IN ('pending', 'in_progress');

CREATE INDEX IF NOT EXISTS idx_dept_tasks_from_dept
    ON public.department_tasks (from_department_id);

CREATE INDEX IF NOT EXISTS idx_dept_tasks_created_by
    ON public.department_tasks (created_by);

CREATE INDEX IF NOT EXISTS idx_dept_tasks_due_date
    ON public.department_tasks (due_date)
    WHERE status IN ('pending', 'in_progress');

ALTER TABLE public.department_tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read department tasks"
    ON public.department_tasks;
CREATE POLICY "Authenticated users can read department tasks"
    ON public.department_tasks
    FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Service role full access"
    ON public.department_tasks;
CREATE POLICY "Service role full access"
    ON public.department_tasks
    FOR ALL
    USING (auth.role() = 'service_role');
