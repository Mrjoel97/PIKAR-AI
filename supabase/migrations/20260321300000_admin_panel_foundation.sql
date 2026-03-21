-- =============================================================================
-- Phase 7: Admin Panel Foundation
-- Creates all 9 admin tables, is_admin() SECURITY DEFINER function, RLS, and
-- seeds admin_agent_permissions with default autonomy tiers.
--
-- Tables:
--   1. user_roles
--   2. admin_agent_permissions
--   3. admin_chat_sessions
--   4. admin_chat_messages
--   5. admin_audit_log
--   6. admin_config_history
--   7. admin_integrations
--   8. api_health_checks
--   9. api_incidents
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. user_roles
-- Stores admin role assignments per user. Unique per user (one row per user).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_roles (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role        text NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user', 'junior_admin', 'senior_admin', 'admin', 'super_admin')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

-- ---------------------------------------------------------------------------
-- is_admin(user_id_param uuid) -> boolean
-- SECURITY DEFINER so it runs as the table owner regardless of caller RLS.
-- Returns TRUE if the user has any admin-level role.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION is_admin(user_id_param uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM user_roles
        WHERE user_id = user_id_param
          AND role IN ('admin', 'super_admin', 'senior_admin', 'junior_admin')
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- 2. admin_agent_permissions
-- Defines autonomy tiers for each AdminAgent tool action.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_agent_permissions (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    action_category  text NOT NULL,
    action_name      text NOT NULL,
    autonomy_level   text NOT NULL DEFAULT 'auto'
                         CHECK (autonomy_level IN ('auto', 'confirm', 'blocked')),
    risk_level       text,
    description      text,
    UNIQUE (action_category, action_name)
);

-- ---------------------------------------------------------------------------
-- 3. admin_chat_sessions
-- Persists AdminAgent chat sessions so admins can resume conversations.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_chat_sessions (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id  uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title          text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 4. admin_chat_messages
-- Individual messages within an AdminAgent chat session.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_chat_messages (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  uuid NOT NULL REFERENCES admin_chat_sessions(id) ON DELETE CASCADE,
    role        text NOT NULL,
    content     text NOT NULL,
    metadata    jsonb NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 5. admin_audit_log
-- Immutable audit trail of all admin actions.
-- admin_user_id is NULLABLE to support monitoring_loop source (no human actor).
-- impersonation_session_id is schema-ready for Phase 13 (AUDT-04) — not used in Phase 7.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id            uuid REFERENCES auth.users(id),  -- nullable: monitoring_loop
    action                   text NOT NULL,
    target_type              text,
    target_id                text,
    details                  jsonb NOT NULL DEFAULT '{}',
    source                   text NOT NULL
                                 CHECK (source IN ('manual', 'ai_agent', 'impersonation', 'monitoring_loop')),
    impersonation_session_id uuid,  -- Phase 13 (AUDT-04): not populated in Phase 7
    created_at               timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 6. admin_config_history
-- Tracks configuration changes made through the admin panel.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_config_history (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    config_type     text NOT NULL,
    config_key      text NOT NULL,
    previous_value  jsonb,
    new_value       jsonb,
    changed_by      uuid REFERENCES auth.users(id),
    change_source   text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 7. admin_integrations
-- Stores external integration credentials (API keys encrypted with Fernet).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_integrations (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider          text NOT NULL UNIQUE,
    api_key_encrypted text,
    base_url          text,
    config            jsonb NOT NULL DEFAULT '{}',
    is_active         boolean NOT NULL DEFAULT false,
    health_status     text NOT NULL DEFAULT 'unknown',
    updated_by        uuid REFERENCES auth.users(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 8. api_health_checks
-- Point-in-time health check results for monitored endpoints.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_health_checks (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint         text NOT NULL,
    category         text,
    status           text NOT NULL,
    response_time_ms integer,
    status_code      integer,
    error_message    text,
    metadata         jsonb NOT NULL DEFAULT '{}',
    checked_at       timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 9. api_incidents
-- Incident records for API degradation or outage events.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_incidents (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint                    text NOT NULL,
    category                    text,
    incident_type               text,
    started_at                  timestamptz NOT NULL DEFAULT now(),
    resolved_at                 timestamptz,
    auto_remediation_attempted  boolean NOT NULL DEFAULT false,
    remediation_action          text,
    remediation_result          text,
    details                     jsonb NOT NULL DEFAULT '{}',
    created_at                  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Enable RLS on all 9 admin tables
-- No policies defined: anon access is denied by default.
-- All access goes through the service-role client (bypasses RLS).
-- ---------------------------------------------------------------------------
ALTER TABLE user_roles              ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_agent_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_chat_sessions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_chat_messages     ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log         ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_config_history    ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_integrations      ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_health_checks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_incidents           ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- Seed: admin_agent_permissions defaults
-- Reads = auto, writes = confirm, destructive = blocked
-- ---------------------------------------------------------------------------
INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('monitoring', 'check_system_health', 'auto',    'low',          'Read system health status across all platform services'),
    ('users',      'suspend_user',        'confirm', 'medium',       'Temporarily suspend a user account'),
    ('users',      'delete_user',         'blocked', 'destructive',  'Permanently delete a user account and all associated data'),
    ('config',     'update_config',       'confirm', 'medium',       'Update a platform configuration setting')
ON CONFLICT (action_category, action_name) DO NOTHING;
