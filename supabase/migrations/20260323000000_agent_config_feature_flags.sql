-- =============================================================================
-- Phase 12: Agent Config & Feature Flags
-- Creates admin_agent_configs and admin_feature_flags tables.
-- Seeds agent config rows, feature flag rows, and config-domain permission rows.
--
-- Tables created:
--   1. admin_agent_configs  — one row per specialized agent, stores instructions + version
--   2. admin_feature_flags  — key/value flag store with Redis caching layer
--
-- Seeds:
--   - admin_agent_configs: 10 rows (one per specialized agent)
--   - admin_feature_flags: 3 rows (workflow kill switch + canary flags)
--   - admin_agent_permissions: 10 new config-domain rows
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. admin_agent_configs
-- One row per agent name. Stores the active instruction set and version counter.
-- updated_by is nullable to support automated/system updates (monitoring_loop).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_agent_configs (
    id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name           text        NOT NULL UNIQUE,
    current_instructions text        NOT NULL,
    version              integer     NOT NULL DEFAULT 1,
    updated_by           uuid        REFERENCES auth.users(id),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    created_at           timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 2. admin_feature_flags
-- Key/value feature flag store. Redis caches reads for 60 s.
-- updated_by is nullable to support automated flag changes.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_feature_flags (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_key    text        NOT NULL UNIQUE,
    is_enabled  boolean     NOT NULL DEFAULT false,
    description text,
    updated_by  uuid        REFERENCES auth.users(id),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Enable RLS on both new tables.
-- No policies defined: anon access is denied by default.
-- All access goes through the service-role client (bypasses RLS).
-- ---------------------------------------------------------------------------
ALTER TABLE admin_agent_configs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_feature_flags  ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- Seed: admin_agent_configs
-- 10 rows, one per specialized agent. Placeholder instructions are used;
-- the service layer falls back to the Python-defined instruction constant
-- when it detects the placeholder text.
-- ---------------------------------------------------------------------------
INSERT INTO admin_agent_configs (agent_name, current_instructions)
VALUES
    ('financial',        'Default instructions for financial agent. Edit via admin panel to customize.'),
    ('content',          'Default instructions for content agent. Edit via admin panel to customize.'),
    ('strategic',        'Default instructions for strategic agent. Edit via admin panel to customize.'),
    ('sales',            'Default instructions for sales agent. Edit via admin panel to customize.'),
    ('marketing',        'Default instructions for marketing agent. Edit via admin panel to customize.'),
    ('operations',       'Default instructions for operations agent. Edit via admin panel to customize.'),
    ('hr',               'Default instructions for hr agent. Edit via admin panel to customize.'),
    ('compliance',       'Default instructions for compliance agent. Edit via admin panel to customize.'),
    ('customer_support', 'Default instructions for customer_support agent. Edit via admin panel to customize.'),
    ('data',             'Default instructions for data agent. Edit via admin panel to customize.')
ON CONFLICT (agent_name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Seed: admin_feature_flags
-- Mirrors the three env-var feature flags defined in app/services/feature_flags.py.
-- is_enabled defaults to false; the service reads Redis first, then this table.
-- ---------------------------------------------------------------------------
INSERT INTO admin_feature_flags (flag_key, is_enabled, description)
VALUES
    ('workflow_kill_switch',    false, 'Hard stop for all workflow starts'),
    ('workflow_canary_enabled', false, 'Limit workflow execution to canary user list'),
    ('workflow_canary_user_ids',false, 'Whether canary user ID list is active (list managed in env var)')
ON CONFLICT (flag_key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Seed: admin_agent_permissions (config domain)
-- 10 new config-domain rows for the AdminAgent config tools.
-- Uses ON CONFLICT DO NOTHING to avoid collision with existing seeds.
-- ---------------------------------------------------------------------------
INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('config', 'get_agent_config',          'auto',    'low',    'Read current agent instructions and version'),
    ('config', 'update_agent_config',        'confirm', 'medium', 'Update agent instructions (injection-validated)'),
    ('config', 'get_config_history',         'auto',    'low',    'View configuration change history'),
    ('config', 'rollback_agent_config',      'confirm', 'medium', 'Restore previous agent instruction version'),
    ('config', 'get_feature_flags',          'auto',    'low',    'List all feature flags with status'),
    ('config', 'toggle_feature_flag',        'confirm', 'medium', 'Enable or disable a feature flag'),
    ('config', 'get_autonomy_permissions',   'auto',    'low',    'List all autonomy tier assignments'),
    ('config', 'update_autonomy_permission', 'confirm', 'high',   'Change autonomy tier for an admin action'),
    ('config', 'assess_config_impact',       'auto',    'low',    'Assess workflow impact of agent config change'),
    ('config', 'recommend_config_rollback',  'auto',    'low',    'Analyze whether config rollback is recommended')
ON CONFLICT (action_category, action_name) DO NOTHING;
