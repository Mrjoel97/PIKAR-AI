-- =============================================================================
-- Phase 15 Plan 01: Approval Oversight, Role-Based Access Control
--
-- Creates:
--   1. admin_role_permissions — per-role section access control table
--   2. user_id column on approval_requests — for efficient admin cross-user queries
--   3. Default role permission seeds for all 4 admin roles
--   4. admin_agent_permissions seeds for 8 new Phase 15 tools
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. admin_role_permissions table
--    Controls what each admin role can do per UI section.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.admin_role_permissions (
    role             text NOT NULL
                         CHECK (role IN ('junior_admin', 'senior_admin', 'admin', 'super_admin')),
    section          text NOT NULL
                         CHECK (section IN (
                             'users', 'monitoring', 'analytics', 'approvals',
                             'config', 'knowledge', 'billing', 'integrations',
                             'settings', 'audit_log'
                         )),
    allowed_actions  text[] NOT NULL DEFAULT '{read}',
    PRIMARY KEY (role, section)
);

ALTER TABLE public.admin_role_permissions ENABLE ROW LEVEL SECURITY;
-- All access is via service-role client (bypasses RLS) — no user-facing policies needed.

-- -----------------------------------------------------------------------------
-- 2. Add user_id to approval_requests for efficient admin cross-user queries
-- -----------------------------------------------------------------------------
ALTER TABLE public.approval_requests
    ADD COLUMN IF NOT EXISTS user_id uuid;

CREATE INDEX IF NOT EXISTS idx_approval_requests_user_id
    ON public.approval_requests (user_id);

-- Backfill: extract requester_user_id from payload JSONB for existing rows
UPDATE public.approval_requests
SET user_id = (payload->>'requester_user_id')::uuid
WHERE user_id IS NULL
  AND payload->>'requester_user_id' IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 3. Seed default role permissions
--    junior_admin  — read only across all sections
--    senior_admin  — read+write everywhere, except settings (read only)
--    admin         — read+write+manage everywhere, except settings (read+write)
--    super_admin   — read+write+manage everywhere
-- -----------------------------------------------------------------------------

-- junior_admin: read only on all 10 sections
INSERT INTO public.admin_role_permissions (role, section, allowed_actions)
VALUES
    ('junior_admin', 'users',        '{read}'),
    ('junior_admin', 'monitoring',   '{read}'),
    ('junior_admin', 'analytics',    '{read}'),
    ('junior_admin', 'approvals',    '{read}'),
    ('junior_admin', 'config',       '{read}'),
    ('junior_admin', 'knowledge',    '{read}'),
    ('junior_admin', 'billing',      '{read}'),
    ('junior_admin', 'integrations', '{read}'),
    ('junior_admin', 'settings',     '{read}'),
    ('junior_admin', 'audit_log',    '{read}')
ON CONFLICT (role, section) DO NOTHING;

-- senior_admin: read+write on all sections, settings is read only
INSERT INTO public.admin_role_permissions (role, section, allowed_actions)
VALUES
    ('senior_admin', 'users',        '{read,write}'),
    ('senior_admin', 'monitoring',   '{read,write}'),
    ('senior_admin', 'analytics',    '{read,write}'),
    ('senior_admin', 'approvals',    '{read,write}'),
    ('senior_admin', 'config',       '{read,write}'),
    ('senior_admin', 'knowledge',    '{read,write}'),
    ('senior_admin', 'billing',      '{read,write}'),
    ('senior_admin', 'integrations', '{read,write}'),
    ('senior_admin', 'settings',     '{read}'),
    ('senior_admin', 'audit_log',    '{read,write}')
ON CONFLICT (role, section) DO NOTHING;

-- admin: read+write+manage on all sections, settings is read+write
INSERT INTO public.admin_role_permissions (role, section, allowed_actions)
VALUES
    ('admin', 'users',        '{read,write,manage}'),
    ('admin', 'monitoring',   '{read,write,manage}'),
    ('admin', 'analytics',    '{read,write,manage}'),
    ('admin', 'approvals',    '{read,write,manage}'),
    ('admin', 'config',       '{read,write,manage}'),
    ('admin', 'knowledge',    '{read,write,manage}'),
    ('admin', 'billing',      '{read,write,manage}'),
    ('admin', 'integrations', '{read,write,manage}'),
    ('admin', 'settings',     '{read,write}'),
    ('admin', 'audit_log',    '{read,write,manage}')
ON CONFLICT (role, section) DO NOTHING;

-- super_admin: read+write+manage on all sections including settings
INSERT INTO public.admin_role_permissions (role, section, allowed_actions)
VALUES
    ('super_admin', 'users',        '{read,write,manage}'),
    ('super_admin', 'monitoring',   '{read,write,manage}'),
    ('super_admin', 'analytics',    '{read,write,manage}'),
    ('super_admin', 'approvals',    '{read,write,manage}'),
    ('super_admin', 'config',       '{read,write,manage}'),
    ('super_admin', 'knowledge',    '{read,write,manage}'),
    ('super_admin', 'billing',      '{read,write,manage}'),
    ('super_admin', 'integrations', '{read,write,manage}'),
    ('super_admin', 'settings',     '{read,write,manage}'),
    ('super_admin', 'audit_log',    '{read,write,manage}')
ON CONFLICT (role, section) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 4. Seed admin_agent_permissions for 8 new Phase 15 tools
-- -----------------------------------------------------------------------------
INSERT INTO public.admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('approvals', 'recommend_autonomy_tier',   'auto',    'low',    'Analyse tool usage patterns and recommend an autonomy tier adjustment'),
    ('approvals', 'generate_compliance_report','auto',    'low',    'Generate a compliance report summarising admin actions over a time window'),
    ('approvals', 'suggest_role_permissions',  'auto',    'low',    'Suggest per-section permission changes for an admin role based on usage'),
    ('approvals', 'generate_daily_digest',     'auto',    'low',    'Produce a daily digest of pending approvals and governance alerts'),
    ('approvals', 'classify_and_escalate',     'confirm', 'medium', 'Classify an approval request risk level and escalate to a senior admin'),
    ('approvals', 'list_all_approvals',        'auto',    'low',    'List all pending approval requests across all users'),
    ('approvals', 'override_approval',         'confirm', 'high',   'Admin override to approve or reject any pending approval request'),
    ('approvals', 'manage_admin_role',         'confirm', 'high',   'Create, update, or delete an admin role assignment for a user')
ON CONFLICT (action_category, action_name) DO NOTHING;
