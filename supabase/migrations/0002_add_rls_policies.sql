-- Migration: 0002_add_rls_policies.sql
-- Description: Add Row Level Security policies to unprotected tables
-- Following supabase-best-practices skill guidelines:
-- - rls-always-enable: Always enable RLS on public schema tables
-- - rls-wrap-functions-select: Wrap auth functions with (SELECT ...) for performance
-- - rls-add-indexes: Add indexes on columns used in RLS policies
-- - rls-specify-roles: Specify roles with TO authenticated clause
-- - rls-explicit-auth-check: Use explicit auth.uid() checks

-- =============================================================================
-- 1. AGENTS TABLE - RLS Policies
-- System agents are shared (read-only), user agents are private
-- =============================================================================

ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Users can view system agents and their own agents
CREATE POLICY "agents_select_policy" ON agents
    FOR SELECT
    TO authenticated
    USING (
        is_system = true 
        OR (SELECT auth.uid()) = user_id
    );

-- Users can only insert their own agents
CREATE POLICY "agents_insert_policy" ON agents
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id AND is_system = false);

-- Users can only update their own non-system agents
CREATE POLICY "agents_update_policy" ON agents
    FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id AND is_system = false)
    WITH CHECK ((SELECT auth.uid()) = user_id AND is_system = false);

-- Users can only delete their own non-system agents
CREATE POLICY "agents_delete_policy" ON agents
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id AND is_system = false);

-- Index for RLS performance (per rls-add-indexes rule)
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);
CREATE INDEX IF NOT EXISTS idx_agents_is_system ON agents(is_system);

-- =============================================================================
-- 2. AGENT_KNOWLEDGE TABLE - RLS Policies
-- Users can only access their own agent knowledge
-- =============================================================================

ALTER TABLE agent_knowledge ENABLE ROW LEVEL SECURITY;

-- Users can view their own agent knowledge
CREATE POLICY "agent_knowledge_select_policy" ON agent_knowledge
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Users can insert their own agent knowledge
CREATE POLICY "agent_knowledge_insert_policy" ON agent_knowledge
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can update their own agent knowledge
CREATE POLICY "agent_knowledge_update_policy" ON agent_knowledge
    FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can delete their own agent knowledge
CREATE POLICY "agent_knowledge_delete_policy" ON agent_knowledge
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Index for RLS performance
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_user_id ON agent_knowledge(user_id);

-- =============================================================================
-- 3. EMBEDDINGS TABLE - RLS Policies
-- Users can only access their own embeddings
-- =============================================================================

ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Users can view their own embeddings
CREATE POLICY "embeddings_select_policy" ON embeddings
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Users can insert their own embeddings
CREATE POLICY "embeddings_insert_policy" ON embeddings
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can update their own embeddings
CREATE POLICY "embeddings_update_policy" ON embeddings
    FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can delete their own embeddings
CREATE POLICY "embeddings_delete_policy" ON embeddings
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Index for RLS performance
CREATE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id);

-- =============================================================================
-- 4. AI_JOBS TABLE - RLS Policies
-- Users can only access their own AI jobs
-- =============================================================================

ALTER TABLE ai_jobs ENABLE ROW LEVEL SECURITY;

-- Users can view their own AI jobs
CREATE POLICY "ai_jobs_select_policy" ON ai_jobs
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Users can insert their own AI jobs
CREATE POLICY "ai_jobs_insert_policy" ON ai_jobs
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can update their own AI jobs
CREATE POLICY "ai_jobs_update_policy" ON ai_jobs
    FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- Users can delete their own AI jobs
CREATE POLICY "ai_jobs_delete_policy" ON ai_jobs
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Index for RLS performance
CREATE INDEX IF NOT EXISTS idx_ai_jobs_user_id ON ai_jobs(user_id);

-- =============================================================================
-- 5. MCP_AUDIT_LOGS TABLE - RLS Policies
-- Users can only view their own audit logs (read-only for compliance)
-- =============================================================================

ALTER TABLE mcp_audit_logs ENABLE ROW LEVEL SECURITY;

-- Users can only view their own audit logs
CREATE POLICY "mcp_audit_logs_select_policy" ON mcp_audit_logs
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Only service role can insert audit logs (server-side only)
-- No INSERT policy for authenticated users - logs are created by backend

-- Audit logs should not be updatable or deletable by users
-- No UPDATE or DELETE policies - maintains audit trail integrity

-- Index already exists: idx_mcp_audit_logs_user_id

-- =============================================================================
-- VERIFICATION QUERIES (Run after migration to verify)
-- =============================================================================
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- AND tablename IN ('agents', 'agent_knowledge', 'embeddings', 'ai_jobs', 'mcp_audit_logs');
--
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE tablename IN ('agents', 'agent_knowledge', 'embeddings', 'ai_jobs', 'mcp_audit_logs');

