-- Migration: 0003_complete_schema.sql
-- Description: Add missing tables for core services (Initiatives, Campaigns, Recruitment, CRM, Compliance)
-- Following supabase-best-practices:
-- - rls-always-enable: Enabled on all new tables
-- - rls-explicit-auth-check: Using auth.uid()
-- - rls-add-indexes: Added indexes on user_id and other query cols

-- 1. INITIATIVES (StrategicPlanningAgent)
CREATE TABLE initiatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'draft',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE initiatives ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own initiatives" ON initiatives
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_initiatives_user_id ON initiatives(user_id);
CREATE INDEX idx_initiatives_status ON initiatives(status);


-- 2. CAMPAIGNS (MarketingAutomationAgent)
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    campaign_type TEXT NOT NULL,
    target_audience TEXT,
    schedule_start TIMESTAMPTZ,
    status TEXT DEFAULT 'draft',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own campaigns" ON campaigns
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);


-- 3. RECRUITMENT_JOBS (HRRecruitmentAgent)
CREATE TABLE recruitment_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    department TEXT,
    description TEXT,
    requirements TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE recruitment_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own jobs" ON recruitment_jobs
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_recruitment_jobs_user_id ON recruitment_jobs(user_id);


-- 4. RECRUITMENT_CANDIDATES (HRRecruitmentAgent)
CREATE TABLE recruitment_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES recruitment_jobs(id) ON DELETE CASCADE,
    -- Denormalizing user_id for easier RLS, technically redundant but safer/faster
    user_id UUID NOT NULL REFERENCES auth.users(id), 
    name TEXT NOT NULL,
    email TEXT,
    resume_url TEXT,
    status TEXT DEFAULT 'applied',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE recruitment_candidates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own candidates" ON recruitment_candidates
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_candidates_job_id ON recruitment_candidates(job_id);
CREATE INDEX idx_candidates_user_id ON recruitment_candidates(user_id);


-- 5. SUPPORT_TICKETS (CustomerSupportAgent)
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id), -- Owner of the ticket system (the business)
    subject TEXT NOT NULL,
    description TEXT,
    customer_email TEXT,
    priority TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'new',
    assigned_to TEXT,
    resolution TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own tickets" ON support_tickets
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_tickets_user_id ON support_tickets(user_id);
CREATE INDEX idx_tickets_status ON support_tickets(status);


-- 6. COMPLIANCE_AUDITS (ComplianceRiskAgent)
CREATE TABLE compliance_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    scope TEXT,
    auditor TEXT,
    scheduled_date TIMESTAMPTZ,
    status TEXT DEFAULT 'scheduled',
    findings TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE compliance_audits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own audits" ON compliance_audits
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_audits_user_id ON compliance_audits(user_id);


-- 7. COMPLIANCE_RISKS (ComplianceRiskAgent)
CREATE TABLE compliance_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT,
    mitigation_plan TEXT,
    owner TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE compliance_risks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own risks" ON compliance_risks
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_risks_user_id ON compliance_risks(user_id);


-- 8. USER_EXECUTIVE_AGENTS (UserOnboardingService)
CREATE TABLE user_executive_agents (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    agent_name TEXT,
    business_context JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    system_prompt_override TEXT,
    onboarding_completed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE user_executive_agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own agent config" ON user_executive_agents
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- 9. MCP_AUDIT_LOGS (Missing table referenced in RLS)
CREATE TABLE mcp_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    agent_id UUID,
    tool_name TEXT NOT NULL,
    arguments JSONB,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE mcp_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own audit logs" ON mcp_audit_logs
    FOR SELECT
    USING (auth.uid() = user_id);

-- No INSERT policy for users (server-side only)
CREATE INDEX idx_mcp_audit_logs_user_id ON mcp_audit_logs(user_id);
