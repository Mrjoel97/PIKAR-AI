-- ============================================================
-- Production Hardening Migration
-- Fixes: RLS, indexes, cascades, unique constraints
-- ============================================================

-- ==================== RLS POLICIES ====================

-- 1. teams table — CRITICAL: no RLS
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access_teams" ON teams FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "users_read_own_teams" ON teams FOR SELECT USING (
    auth.uid()::text = ANY(
        SELECT tm.user_id::text FROM team_members tm WHERE tm.team_id = teams.id
    )
);

-- 2. user_integrations — CRITICAL: no RLS, exposes API credentials
ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access_integrations" ON user_integrations FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "users_select_own_integrations" ON user_integrations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_insert_own_integrations" ON user_integrations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_update_own_integrations" ON user_integrations FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "users_delete_own_integrations" ON user_integrations FOR DELETE USING (auth.uid() = user_id);

-- 3. braindump_sessions — HIGH: no user isolation
ALTER TABLE braindump_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access_braindump" ON braindump_sessions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "users_access_own_braindumps" ON braindump_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_create_own_braindumps" ON braindump_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_delete_own_braindumps" ON braindump_sessions FOR DELETE USING (auth.uid() = user_id);

-- 4. community_posts — MEDIUM: public read, own write
ALTER TABLE community_posts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access_posts" ON community_posts FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "anyone_read_posts" ON community_posts FOR SELECT USING (true);
CREATE POLICY "users_insert_own_posts" ON community_posts FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_update_own_posts" ON community_posts FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "users_delete_own_posts" ON community_posts FOR DELETE USING (auth.uid() = user_id);

-- 5. community_comments — MEDIUM: public read, own write
ALTER TABLE community_comments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access_comments" ON community_comments FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "anyone_read_comments" ON community_comments FOR SELECT USING (true);
CREATE POLICY "users_insert_own_comments" ON community_comments FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_update_own_comments" ON community_comments FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "users_delete_own_comments" ON community_comments FOR DELETE USING (auth.uid() = user_id);

-- ==================== UNIQUE CONSTRAINTS ====================

-- 6. api_credentials — CRITICAL: prevent duplicate provider per user
ALTER TABLE api_credentials ADD CONSTRAINT IF NOT EXISTS api_credentials_user_provider_unique UNIQUE (user_id, provider);

-- 7. community_upvotes — HIGH: prevent multiple upvotes
ALTER TABLE community_upvotes ADD CONSTRAINT IF NOT EXISTS community_upvotes_user_post_unique UNIQUE (user_id, post_id);

-- ==================== CASCADE FIXES ====================
-- Use DO blocks so they don't fail if constraints don't exist or have different names

-- 8-10. Critical cascades
DO $$ BEGIN
    ALTER TABLE team_members DROP CONSTRAINT IF EXISTS team_members_team_id_fkey;
    ALTER TABLE team_members ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE workflows DROP CONSTRAINT IF EXISTS workflows_user_id_fkey;
    ALTER TABLE workflows ADD CONSTRAINT workflows_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE scheduled_tasks DROP CONSTRAINT IF EXISTS scheduled_tasks_workflow_id_fkey;
    ALTER TABLE scheduled_tasks ADD CONSTRAINT scheduled_tasks_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

-- 11-17. High priority cascades
DO $$ BEGIN
    ALTER TABLE campaign_phases DROP CONSTRAINT IF EXISTS campaign_phases_campaign_id_fkey;
    ALTER TABLE campaign_phases ADD CONSTRAINT campaign_phases_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE campaign_phases DROP CONSTRAINT IF EXISTS campaign_phases_approval_request_id_fkey;
    ALTER TABLE campaign_phases ADD CONSTRAINT campaign_phases_approval_request_id_fkey FOREIGN KEY (approval_request_id) REFERENCES approval_requests(id) ON DELETE SET NULL;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE brand_mentions DROP CONSTRAINT IF EXISTS brand_mentions_monitor_id_fkey;
    ALTER TABLE brand_mentions ADD CONSTRAINT brand_mentions_monitor_id_fkey FOREIGN KEY (monitor_id) REFERENCES brand_monitors(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE community_comments DROP CONSTRAINT IF EXISTS community_comments_post_id_fkey;
    ALTER TABLE community_comments ADD CONSTRAINT community_comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE community_upvotes DROP CONSTRAINT IF EXISTS community_upvotes_post_id_fkey;
    ALTER TABLE community_upvotes ADD CONSTRAINT community_upvotes_post_id_fkey FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE learning_progress DROP CONSTRAINT IF EXISTS learning_progress_user_id_fkey;
    ALTER TABLE learning_progress ADD CONSTRAINT learning_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE improvement_actions DROP CONSTRAINT IF EXISTS improvement_actions_user_id_fkey;
    ALTER TABLE improvement_actions ADD CONSTRAINT improvement_actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE coverage_gaps DROP CONSTRAINT IF EXISTS coverage_gaps_user_id_fkey;
    ALTER TABLE coverage_gaps ADD CONSTRAINT coverage_gaps_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
EXCEPTION WHEN others THEN NULL;
END $$;

-- ==================== INDEXES ====================

-- 18. workflows
CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON workflows(user_id);

-- 19. scheduled_tasks
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_workflow_id ON scheduled_tasks(workflow_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user_status ON scheduled_tasks(user_id, status);

-- 20. campaigns
CREATE INDEX IF NOT EXISTS idx_campaigns_user_created ON campaigns(user_id, created_at DESC);

-- 21. landing_pages
CREATE INDEX IF NOT EXISTS idx_landing_pages_user_created ON landing_pages(user_id, created_at DESC);

-- 22. form_submissions
CREATE INDEX IF NOT EXISTS idx_form_submissions_page_created ON form_submissions(page_id, created_at DESC);

-- 23. department tables
CREATE INDEX IF NOT EXISTS idx_department_decision_logs_dept_created ON department_decision_logs(department_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inter_dept_requests_from_status ON inter_dept_requests(from_department_id, status);
CREATE INDEX IF NOT EXISTS idx_inter_dept_requests_to_status ON inter_dept_requests(to_department_id, status);
CREATE INDEX IF NOT EXISTS idx_proactive_triggers_dept_active ON proactive_triggers(department_id, is_active);

-- 24. brand tables
CREATE INDEX IF NOT EXISTS idx_brand_monitors_user_active ON brand_monitors(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_brand_mentions_source_created ON brand_mentions(source, created_at DESC);

-- 25. community tables
CREATE INDEX IF NOT EXISTS idx_community_posts_user_created ON community_posts(user_id, created_at DESC);

-- 26. learning + skills
CREATE INDEX IF NOT EXISTS idx_learning_progress_user_course ON learning_progress(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_skill_scores_user_category ON skill_scores(user_id, category);

-- 27. interaction_logs
CREATE INDEX IF NOT EXISTS idx_interaction_logs_user_type ON interaction_logs(user_id, interaction_type);

-- 28. support_tickets
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_created ON support_tickets(user_id, created_at DESC);
