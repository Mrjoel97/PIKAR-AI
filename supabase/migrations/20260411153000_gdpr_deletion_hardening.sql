-- Migration: 20260411153000_gdpr_deletion_hardening.sql
-- Description: GDPR-02 / GDPR-03 hardening pass for delete_user_account().
--
-- The original March 2026 migration (20260316000000_data_deletion.sql) was
-- written before a number of user-linked tables were added, and before the
-- enterprise governance subsystem was introduced.  This migration refreshes
-- the stored procedure to:
--
--   1. DELETE rows from every user-linked table not already covered by an
--      ON DELETE CASCADE foreign key (or added after the original migration).
--
--   2. ANONYMIZE governance_audit_log rows instead of deleting them.
--      These rows represent approved workflow actions and must survive for
--      audit purposes.  The actor's identity (user_id, ip_address) is removed
--      by setting user_id to a sentinel UUID (DELETED_USER_PLACEHOLDER) and
--      ip_address to NULL.  The action_type, resource_type, resource_id, and
--      details columns are preserved — they describe *what happened*, not *who
--      did it*.
--
--   3. Preserve the data_deletion_requests audit row (ON DELETE SET NULL on
--      user_id means the row survives auth.users deletion automatically).
--
-- The sentinel UUID used for anonymization:
--   '00000000-0000-0000-0000-000000000000'
-- Any governance viewer that looks up this UUID in auth.admin will receive
-- a "not found" response rather than crashing, which is safe.

-- Sentinel UUID used to replace deleted user references in audit tables
-- that must survive account deletion (governance_audit_log).
DO $$
BEGIN
    -- No-op: we just document the sentinel UUID here for readability.
    -- The actual replacement happens inside delete_user_account() below.
    NULL;
END;
$$;

CREATE OR REPLACE FUNCTION delete_user_account(p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    _sentinel_uuid UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    -- ====================================================================
    -- STEP 0: Anonymize governance/history tables that must survive.
    --
    -- governance_audit_log rows preserve action trails for compliance;
    -- the actor's identity is removed so no PII persists.
    -- approval_chains also stores user_id without FK — delete those.
    -- ====================================================================

    -- governance_audit_log: anonymize actor identity, preserve action trail
    UPDATE governance_audit_log
       SET user_id    = _sentinel_uuid,
           ip_address = NULL
     WHERE user_id = p_user_id;

    -- approval_chain_steps cascade from approval_chains via ON DELETE CASCADE
    DELETE FROM approval_chains WHERE user_id = p_user_id;

    -- ====================================================================
    -- GROUP 1: Tables with NO FK at all on user_id (orphan risk)
    -- ====================================================================

    -- connected_accounts: user_id UUID NOT NULL, no FK constraint
    DELETE FROM connected_accounts WHERE user_id = p_user_id;

    -- business_health_scores: user_id UUID, no FK constraint
    DELETE FROM business_health_scores WHERE user_id = p_user_id;

    -- finance_assumptions_ledger: user_id UUID, no FK constraint
    DELETE FROM finance_assumptions_ledger WHERE user_id = p_user_id;

    -- user_mcp_integrations: user_id TEXT NOT NULL, no FK constraint
    DELETE FROM user_mcp_integrations WHERE user_id = p_user_id::text;

    -- onboarding_drip_emails: user_id UUID NOT NULL, no FK constraint
    DELETE FROM onboarding_drip_emails WHERE user_id = p_user_id;

    -- onboarding_checklist: user_id UUID NOT NULL, no FK constraint
    DELETE FROM onboarding_checklist WHERE user_id = p_user_id;

    -- app_projects: user_id UUID NOT NULL, no FK (ownership via RLS)
    -- app_screens and build_sessions cascade from app_projects ON DELETE CASCADE
    DELETE FROM app_projects WHERE user_id = p_user_id;

    -- metric_baselines: user_id UUID NOT NULL, no FK constraint
    DELETE FROM metric_baselines WHERE user_id = p_user_id;

    -- ====================================================================
    -- GROUP 2: Tables from 0001_initial_schema.sql
    -- (REFERENCES auth.users(id) with NO ON DELETE CASCADE — defaults to RESTRICT)
    -- ====================================================================

    -- agent_knowledge -> agents(id) ON DELETE CASCADE, but agents itself is RESTRICT
    DELETE FROM agent_knowledge WHERE user_id = p_user_id;
    DELETE FROM embeddings WHERE user_id = p_user_id;
    DELETE FROM ai_jobs WHERE user_id = p_user_id;
    DELETE FROM agents WHERE user_id = p_user_id;

    -- ====================================================================
    -- GROUP 3: Tables from 0003_complete_schema.sql (RESTRICT)
    -- ====================================================================

    -- recruitment_candidates references recruitment_jobs(id) CASCADE
    DELETE FROM recruitment_candidates WHERE user_id = p_user_id;
    DELETE FROM recruitment_jobs WHERE user_id = p_user_id;

    -- compliance
    DELETE FROM compliance_risks WHERE user_id = p_user_id;
    DELETE FROM compliance_audits WHERE user_id = p_user_id;

    -- core operational tables
    DELETE FROM campaigns WHERE user_id = p_user_id;
    DELETE FROM user_executive_agents WHERE user_id = p_user_id;
    DELETE FROM mcp_audit_logs WHERE user_id = p_user_id;

    -- initiatives chain: events -> items -> checklists -> initiatives
    DELETE FROM initiative_checklist_item_events WHERE user_id = p_user_id;
    DELETE FROM initiative_checklist_items WHERE user_id = p_user_id;
    DELETE FROM initiative_checklist_items WHERE owner_user_id = p_user_id;
    DELETE FROM initiatives WHERE user_id = p_user_id;

    -- ====================================================================
    -- GROUP 4: Tables from other numbered migrations (RESTRICT)
    -- ====================================================================

    -- 0004_a2a_tasks.sql
    DELETE FROM a2a_tasks WHERE user_id = p_user_id;

    -- 0005_sessions.sql
    DELETE FROM sessions WHERE user_id = p_user_id;

    -- 0007_workflow_steps.sql
    DELETE FROM workflow_executions WHERE user_id = p_user_id;

    -- 0008_commerce_schema.sql
    DELETE FROM products WHERE user_id = p_user_id;
    DELETE FROM orders WHERE user_id = p_user_id;
    DELETE FROM invoices WHERE user_id = p_user_id;

    -- 0012_approval_requests.sql
    DELETE FROM approval_requests WHERE user_id = p_user_id;

    -- 0013_departments.sql
    DELETE FROM departments WHERE user_id = p_user_id;

    -- 0014/0035_landing_pages.sql
    DELETE FROM landing_pages WHERE user_id = p_user_id;

    -- 0018_create_storage.sql
    DELETE FROM media_assets WHERE user_id = p_user_id;

    -- 0026_user_workflows.sql
    DELETE FROM user_workflows WHERE user_id = p_user_id;

    -- 0030_create_users_profile.sql (PK = user_id, RESTRICT)
    DELETE FROM users_profile WHERE user_id = p_user_id;

    -- 0033_knowledge_vault_tables.sql
    DELETE FROM vault_documents WHERE user_id = p_user_id;

    -- 0034_user_configurations.sql
    DELETE FROM user_configurations WHERE user_id = p_user_id;

    -- 0036_media_assets_payments.sql
    DELETE FROM payment_transactions WHERE user_id = p_user_id;
    DELETE FROM payment_links WHERE user_id = p_user_id;

    -- 0046_user_reports_table.sql
    DELETE FROM user_reports WHERE user_id = p_user_id;

    -- ====================================================================
    -- GROUP 5: Timestamp-based migrations added before March 2026
    -- ====================================================================

    DELETE FROM briefing_runs WHERE user_id = p_user_id;
    DELETE FROM user_memory_facts WHERE user_id = p_user_id;
    DELETE FROM memory_episodes WHERE user_id = p_user_id;
    DELETE FROM skill_usage_log WHERE user_id = p_user_id;
    DELETE FROM financial_records WHERE user_id = p_user_id;
    DELETE FROM analytics_events WHERE user_id = p_user_id;
    DELETE FROM analytics_reports WHERE user_id = p_user_id;
    DELETE FROM user_activity_log WHERE user_id = p_user_id;
    DELETE FROM custom_skills WHERE user_id = p_user_id;
    DELETE FROM support_tickets WHERE user_id = p_user_id;
    DELETE FROM learning_progress WHERE user_id = p_user_id;
    DELETE FROM community_comments WHERE user_id = p_user_id;
    DELETE FROM community_upvotes WHERE user_id = p_user_id;
    DELETE FROM community_posts WHERE user_id = p_user_id;
    DELETE FROM content_bundle_deliverables WHERE user_id = p_user_id;
    DELETE FROM content_bundles WHERE user_id = p_user_id;
    DELETE FROM workspace_items WHERE user_id = p_user_id;
    DELETE FROM page_analytics WHERE user_id = p_user_id;

    -- CRM / monitoring
    DELETE FROM contacts_crm WHERE user_id = p_user_id;
    DELETE FROM follow_up_rules WHERE user_id = p_user_id;
    DELETE FROM monitored_competitors WHERE user_id = p_user_id;

    -- ====================================================================
    -- GROUP 6: Tables added AFTER the original March 2026 deletion migration
    --          (post-20260316 timestamp migrations)
    -- ====================================================================

    -- 20260317 braindump_sessions (ON DELETE CASCADE — explicit is safe)
    DELETE FROM braindump_sessions WHERE user_id = p_user_id;

    -- 20260318 self_improvement
    DELETE FROM interaction_logs WHERE user_id = p_user_id;
    DELETE FROM coverage_gaps WHERE user_id = p_user_id;

    -- 20260318 marketing_content_tools (CASCADE, explicit safe)
    DELETE FROM blog_posts WHERE user_id = p_user_id;
    DELETE FROM content_calendar WHERE user_id = p_user_id;
    DELETE FROM email_templates WHERE user_id = p_user_id;

    -- 20260318 campaign_orchestrator (CASCADE, explicit safe)
    DELETE FROM marketing_audiences WHERE user_id = p_user_id;
    DELETE FROM marketing_personas WHERE user_id = p_user_id;
    DELETE FROM campaign_phases WHERE user_id = p_user_id;

    -- 20260318 ad_management (CASCADE, explicit safe)
    DELETE FROM ad_campaigns WHERE user_id = p_user_id;

    -- 20260319 email_triage (CASCADE, explicit safe)
    DELETE FROM email_triage WHERE user_id = p_user_id;

    -- 20260319 user_briefing_preferences (CASCADE, explicit safe)
    DELETE FROM user_briefing_preferences WHERE user_id = p_user_id;

    -- 20260320 social_analytics / brand_monitors (CASCADE, explicit safe)
    DELETE FROM brand_monitors WHERE user_id = p_user_id;
    DELETE FROM social_analytics_cache WHERE user_id = p_user_id;

    -- 20260321 brand_profiles (CASCADE, explicit safe)
    DELETE FROM brand_profiles WHERE user_id = p_user_id;

    -- 20260321 admin_panel: user_roles (CASCADE, explicit safe)
    DELETE FROM user_roles WHERE user_id = p_user_id;
    DELETE FROM admin_chat_sessions WHERE admin_user_id = p_user_id;

    -- 20260321 app_builder: screen_variants (CASCADE, explicit safe)
    DELETE FROM screen_variants WHERE user_id = p_user_id;

    -- 20260324 subscriptions (REFERENCES auth.users(id) no CASCADE — RESTRICT)
    DELETE FROM subscriptions WHERE user_id = p_user_id;

    -- 20260403 teams_rbac: workspace_members (CASCADE, explicit safe)
    --   workspaces.owner_id ON DELETE CASCADE — whole workspace deleted automatically
    DELETE FROM workspace_members WHERE user_id = p_user_id;

    -- 20260404 integration_infrastructure (CASCADE, explicit safe)
    DELETE FROM integration_credentials WHERE user_id = p_user_id;
    DELETE FROM integration_sync_state WHERE user_id = p_user_id;

    -- 20260404 data_io_documents (CASCADE, explicit safe)
    DELETE FROM csv_column_mappings WHERE user_id = p_user_id;

    -- 20260405 ad_budget_caps (CASCADE, explicit safe)
    DELETE FROM ad_budget_caps WHERE user_id = p_user_id;

    -- 20260405 pm_integration (CASCADE, explicit safe)
    DELETE FROM synced_tasks WHERE user_id = p_user_id;
    DELETE FROM pm_status_mappings WHERE user_id = p_user_id;

    -- 20260405 notification_rules (CASCADE, explicit safe)
    DELETE FROM notification_rules WHERE user_id = p_user_id;
    DELETE FROM notification_channel_config WHERE user_id = p_user_id;

    -- 20260406 external_db_monitoring (CASCADE, explicit safe)
    DELETE FROM monitoring_jobs WHERE user_id = p_user_id;

    -- 20260410 unified_action_history (CASCADE, explicit safe)
    DELETE FROM unified_action_history WHERE user_id = p_user_id;

    -- 20260410 decision_journal (CASCADE, explicit safe)
    DELETE FROM decision_journal WHERE user_id = p_user_id;

    -- 20260410 proactive_alerts (CASCADE, explicit safe)
    DELETE FROM proactive_alert_log WHERE user_id = p_user_id;

    -- 20260410 financial_health_score (CASCADE, explicit safe)
    DELETE FROM financial_health_snapshots WHERE user_id = p_user_id;

    -- ====================================================================
    -- Mark pending deletion requests as completed (audit trail).
    -- data_deletion_requests.user_id has ON DELETE SET NULL so the row
    -- survives the auth.users deletion below.
    -- ====================================================================
    UPDATE data_deletion_requests
       SET status       = 'completed',
           completed_at = now()
     WHERE user_id = p_user_id
       AND status  = 'pending';

    -- ====================================================================
    -- Final step: delete from auth.users.
    -- Any remaining tables with ON DELETE CASCADE are cleaned up
    -- automatically by PostgreSQL.
    -- ====================================================================
    DELETE FROM auth.users WHERE id = p_user_id;
END;
$$;

-- Grant policy unchanged: only service_role may execute this function.
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM authenticated;
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM anon;
GRANT  EXECUTE ON FUNCTION delete_user_account(UUID) TO service_role;
