-- Migration: 20260316000000_data_deletion.sql
-- Description: Data deletion tracking table and delete_user_account() stored procedure
--              for GDPR compliance and Facebook data deletion callback support.

-- ============================================================================
-- 1. TRACKING TABLE — records all deletion requests (Facebook callback + self-service)
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_deletion_requests (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    platform          TEXT        NOT NULL DEFAULT 'self'
                                  CHECK (platform IN ('facebook', 'self')),
    facebook_user_id  TEXT,
    status            TEXT        NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending', 'completed', 'failed')),
    confirmation_code TEXT        NOT NULL,
    requested_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ,
    error_detail      TEXT
);

CREATE INDEX IF NOT EXISTS idx_ddr_user_id ON data_deletion_requests(user_id);

-- Confirmation code must be unique — used as capability token for status lookup
CREATE UNIQUE INDEX IF NOT EXISTS idx_ddr_conf_code ON data_deletion_requests(confirmation_code);

-- Prevent duplicate Facebook deletion requests (idempotency guard against concurrent callbacks)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ddr_facebook_unique
    ON data_deletion_requests(facebook_user_id, platform)
    WHERE facebook_user_id IS NOT NULL AND status IN ('pending', 'completed');

-- RLS: deny all public/authenticated access — backend uses service_role client only
ALTER TABLE data_deletion_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access" ON data_deletion_requests
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);


-- ============================================================================
-- 2. ACCOUNT DELETION STORED PROCEDURE
-- ============================================================================
-- Explicitly deletes rows from ALL tables that reference auth.users(id) without
-- ON DELETE CASCADE, then removes auth.users row which cascades to the rest.
--
-- Tables with REFERENCES auth.users(id) but NO ON DELETE CASCADE will RESTRICT
-- the deletion if rows exist. We must delete from them first.
--
-- Runs as SECURITY DEFINER so it executes with owner privileges (bypasses RLS).
-- Only service_role can call it (see GRANT below).

CREATE OR REPLACE FUNCTION delete_user_account(p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
BEGIN
    -- ================================================================
    -- GROUP 1: Tables with NO FK at all on user_id (orphan risk)
    -- ================================================================

    -- connected_accounts: user_id UUID NOT NULL, no FK constraint
    DELETE FROM connected_accounts WHERE user_id = p_user_id;

    -- business_health_scores: user_id UUID, no FK constraint
    DELETE FROM business_health_scores WHERE user_id = p_user_id;

    -- finance_assumptions_ledger: user_id UUID, no FK constraint
    DELETE FROM finance_assumptions_ledger WHERE user_id = p_user_id;

    -- user_mcp_integrations: user_id TEXT NOT NULL, no FK constraint
    DELETE FROM user_mcp_integrations WHERE user_id = p_user_id::text;

    -- ================================================================
    -- GROUP 2: Tables from 0001_initial_schema.sql
    -- (REFERENCES auth.users(id) with NO ON DELETE CASCADE — defaults to RESTRICT)
    -- ================================================================

    -- agent_knowledge -> agents(id) ON DELETE CASCADE, but agents itself is RESTRICT
    DELETE FROM agent_knowledge WHERE user_id = p_user_id;
    DELETE FROM embeddings WHERE user_id = p_user_id;
    DELETE FROM ai_jobs WHERE user_id = p_user_id;
    DELETE FROM agents WHERE user_id = p_user_id;

    -- ================================================================
    -- GROUP 3: Tables from 0003_complete_schema.sql
    -- (REFERENCES auth.users(id) with NO ON DELETE CASCADE — defaults to RESTRICT)
    -- ================================================================

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

    -- ================================================================
    -- GROUP 4: Tables from other numbered migrations (RESTRICT)
    -- ================================================================

    -- 0004_a2a_tasks.sql
    DELETE FROM a2a_tasks WHERE user_id = p_user_id;

    -- 0005_sessions.sql
    DELETE FROM sessions WHERE user_id = p_user_id;

    -- 0007_workflow_steps.sql — workflow_executions/steps
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

    -- 0036_media_assets_payments.sql (payment tables)
    DELETE FROM payment_transactions WHERE user_id = p_user_id;
    DELETE FROM payment_links WHERE user_id = p_user_id;

    -- 0046_user_reports_table.sql
    DELETE FROM user_reports WHERE user_id = p_user_id;

    -- ================================================================
    -- GROUP 5: Timestamp-based migrations (verify CASCADE status)
    -- Some of these DO have CASCADE; deleting explicitly is safe either way.
    -- ================================================================

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

    -- CRM / monitoring tables
    DELETE FROM contacts_crm WHERE user_id = p_user_id;
    DELETE FROM follow_up_rules WHERE user_id = p_user_id;
    DELETE FROM monitored_competitors WHERE user_id = p_user_id;

    -- ================================================================
    -- Mark pending deletion requests as completed (audit trail)
    -- Uses ON DELETE SET NULL so the row survives auth.users removal.
    -- ================================================================
    UPDATE data_deletion_requests
       SET status       = 'completed',
           completed_at = now()
     WHERE user_id = p_user_id
       AND status  = 'pending';

    -- ================================================================
    -- Final step: delete from auth.users
    -- Any remaining tables with ON DELETE CASCADE will be cleaned up
    -- automatically by PostgreSQL. Tables without CASCADE have already
    -- been handled above.
    -- ================================================================
    DELETE FROM auth.users WHERE id = p_user_id;
END;
$$;

-- Only service_role can execute this function
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM authenticated;
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM anon;
GRANT  EXECUTE ON FUNCTION delete_user_account(UUID) TO service_role;
