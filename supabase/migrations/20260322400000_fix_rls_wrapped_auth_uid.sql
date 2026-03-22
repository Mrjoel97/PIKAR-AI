-- Fix: Wrap auth.uid() in (SELECT ...) for RLS performance
-- Unwrapped auth.uid() is re-evaluated per row, degrading performance on large tables.
-- See: https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select

-- initiatives
DROP POLICY IF EXISTS "Users can CRUD their own initiatives" ON initiatives;
CREATE POLICY "Users can CRUD their own initiatives" ON initiatives
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- campaigns
DROP POLICY IF EXISTS "Users can CRUD their own campaigns" ON campaigns;
CREATE POLICY "Users can CRUD their own campaigns" ON campaigns
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- recruitment_jobs
DROP POLICY IF EXISTS "Users can CRUD their own jobs" ON recruitment_jobs;
CREATE POLICY "Users can CRUD their own jobs" ON recruitment_jobs
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- recruitment_candidates
DROP POLICY IF EXISTS "Users can CRUD their own candidates" ON recruitment_candidates;
CREATE POLICY "Users can CRUD their own candidates" ON recruitment_candidates
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- support_tickets
DROP POLICY IF EXISTS "Users can CRUD their own tickets" ON support_tickets;
CREATE POLICY "Users can CRUD their own tickets" ON support_tickets
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- compliance_audits
DROP POLICY IF EXISTS "Users can CRUD their own audits" ON compliance_audits;
CREATE POLICY "Users can CRUD their own audits" ON compliance_audits
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- compliance_risks
DROP POLICY IF EXISTS "Users can CRUD their own risks" ON compliance_risks;
CREATE POLICY "Users can CRUD their own risks" ON compliance_risks
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

-- user_executive_agents
DROP POLICY IF EXISTS "Users can CRUD their own agent config" ON user_executive_agents;
CREATE POLICY "Users can CRUD their own agent config" ON user_executive_agents
    FOR ALL USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);
