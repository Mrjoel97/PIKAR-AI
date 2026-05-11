-- supabase/migrations/20260511120500_agent_task_executions.sql
--
-- Agent Operating Model — Foundation 6/7
-- Layer-1 operational history: one row per TaskContract execution
-- (or stateful direct-mode turn). FKs reach the research and audit
-- tables. gin_trgm on goal enables similarity search at retrieval time.

CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;

CREATE TABLE IF NOT EXISTS public.agent_task_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    persona_id TEXT,
    mode TEXT NOT NULL DEFAULT 'initiative'
        CHECK (mode IN ('direct','initiative')),
    classifier_signal TEXT
        CHECK (classifier_signal IS NULL OR classifier_signal IN ('override','rule','llm')),
    contract_id UUID,
    contract_source TEXT
        CHECK (contract_source IS NULL OR contract_source IN ('initiative_step','department_task','direct_request')),
    initiative_id UUID,
    goal TEXT,
    todo_snapshot JSONB,
    status TEXT NOT NULL
        CHECK (status IN ('running','submitted','escalated','failed')),
    research_run_id UUID REFERENCES public.agent_research_runs(id) ON DELETE SET NULL,
    audit_report_id UUID REFERENCES public.agent_audit_reports(id) ON DELETE SET NULL,
    vault_document_id UUID,
    artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    outcome_summary TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ate_user_agent
    ON public.agent_task_executions (user_id, agent_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ate_initiative
    ON public.agent_task_executions (initiative_id, started_at DESC)
    WHERE initiative_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ate_goal_trgm
    ON public.agent_task_executions USING gin (goal public.gin_trgm_ops);

ALTER TABLE public.agent_task_executions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_task_executions_owner_all"
    ON public.agent_task_executions;
CREATE POLICY "agent_task_executions_owner_all"
    ON public.agent_task_executions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.agent_task_executions TO authenticated;
