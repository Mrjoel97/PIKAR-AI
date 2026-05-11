-- supabase/migrations/20260511120000_initiative_checklist_items_goal_owner.sql
--
-- Agent Operating Model — Foundation 1/7
-- Extends initiative_checklist_items so each step carries its own goal
-- and an explicit agent owner. Required input for TaskContract hydration
-- (see app/agents/runtime/step_runtime.py).

ALTER TABLE public.initiative_checklist_items
    ADD COLUMN IF NOT EXISTS goal TEXT;

ALTER TABLE public.initiative_checklist_items
    ADD COLUMN IF NOT EXISTS assigned_agent_id TEXT;

CREATE INDEX IF NOT EXISTS idx_initiative_checklist_items_assigned_agent
    ON public.initiative_checklist_items (assigned_agent_id)
    WHERE assigned_agent_id IS NOT NULL;
