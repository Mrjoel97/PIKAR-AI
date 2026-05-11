-- supabase/migrations/20260511120100_department_tasks_goal.sql
--
-- Agent Operating Model — Foundation 2/7
-- department_tasks gains a freeform goal text field. Mirrors the
-- initiative_checklist_items.goal column so TaskContract.goal can be
-- hydrated from either source identically.

ALTER TABLE public.department_tasks
    ADD COLUMN IF NOT EXISTS goal TEXT;
