-- supabase/migrations/20260511120400_agent_audit_reports.sql
--
-- Agent Operating Model — Foundation 5/7
-- Persists the self-audit report produced at the end of every
-- initiative-mode TaskContract execution. Backs AuditReport in
-- app/agents/runtime/types.py.

CREATE TABLE IF NOT EXISTS public.agent_audit_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    task_contract_id UUID,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    overall_status TEXT NOT NULL
        CHECK (overall_status IN ('pass','fail','partial')),
    per_item JSONB NOT NULL DEFAULT '[]'::jsonb,
    per_criterion JSONB NOT NULL DEFAULT '[]'::jsonb,
    gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    recoverable BOOLEAN NOT NULL,
    next_action TEXT NOT NULL
        CHECK (next_action IN ('submit','retry','escalate')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_aar_contract
    ON public.agent_audit_reports (task_contract_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aar_agent
    ON public.agent_audit_reports (agent_id, created_at DESC);

ALTER TABLE public.agent_audit_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "agent_audit_reports_owner_all"
    ON public.agent_audit_reports;
CREATE POLICY "agent_audit_reports_owner_all"
    ON public.agent_audit_reports
    FOR ALL
    USING (user_id IS NULL OR auth.uid() = user_id)
    WITH CHECK (user_id IS NULL OR auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.agent_audit_reports TO authenticated;
