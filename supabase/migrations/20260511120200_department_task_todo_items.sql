-- supabase/migrations/20260511120200_department_task_todo_items.sql
--
-- Agent Operating Model — Foundation 3/7
-- Per-task to-do list for department_tasks. Mirrors the structure of
-- initiative_checklist_items so the TaskContract hydration code can
-- treat both sources symmetrically. status enum matches TodoItem in
-- app/agents/runtime/types.py exactly.

CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS public.department_task_todo_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES public.department_tasks(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','in_progress','completed','blocked','skipped')),
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dttd_task_sort
    ON public.department_task_todo_items (task_id, sort_order);

DROP TRIGGER IF EXISTS department_task_todo_items_updated_at
    ON public.department_task_todo_items;
CREATE TRIGGER department_task_todo_items_updated_at
    BEFORE UPDATE ON public.department_task_todo_items
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);

ALTER TABLE public.department_task_todo_items ENABLE ROW LEVEL SECURITY;

-- RLS mirrors department_tasks: users can read/write todo rows iff they
-- can read/write the parent task. Re-using the parent's owner check.
DROP POLICY IF EXISTS "dttd_owner_select" ON public.department_task_todo_items;
CREATE POLICY "dttd_owner_select" ON public.department_task_todo_items
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.department_tasks t
            WHERE t.id = task_id AND t.created_by = auth.uid()
        )
    );

DROP POLICY IF EXISTS "dttd_owner_modify" ON public.department_task_todo_items;
CREATE POLICY "dttd_owner_modify" ON public.department_task_todo_items
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.department_tasks t
            WHERE t.id = task_id AND t.created_by = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.department_tasks t
            WHERE t.id = task_id AND t.created_by = auth.uid()
        )
    );

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.department_task_todo_items TO authenticated;
