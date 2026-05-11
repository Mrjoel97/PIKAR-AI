-- supabase/migrations/20260511120300_agent_research_runs.sql
--
-- Agent Operating Model — Foundation 4/7
-- Tracks each research session opened by an agent for a TaskContract.
-- The research-completion gate (app/agents/runtime/research_gate.py)
-- blocks non-research tool calls until the row reaches status='complete'.

CREATE TABLE IF NOT EXISTS public.agent_research_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_contract_id UUID,
    task_contract_source TEXT,
    agent_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('open','in_progress','complete','failed')),
    result JSONB,
    iterations INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_arr_contract
    ON public.agent_research_runs (task_contract_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_arr_agent
    ON public.agent_research_runs (agent_id, created_at DESC);

ALTER TABLE public.agent_research_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_research_runs_owner_all"
    ON public.agent_research_runs;
CREATE POLICY "agent_research_runs_owner_all"
    ON public.agent_research_runs
    FOR ALL
    USING (user_id IS NULL OR auth.uid() = user_id)
    WITH CHECK (user_id IS NULL OR auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.agent_research_runs TO authenticated;
