-- =============================================================================
-- Phase 9: User Management — admin_agent_permissions seed rows
--
-- Seeds 6 permission rows for user management tools used by AdminAgent.
-- Autonomy tiers:
--   - list_users / get_user_detail: auto (read-only, low risk)
--   - suspend_user / unsuspend_user / change_user_persona: confirm (mutates user state)
--   - impersonate_user: confirm (sensitive read-only view)
-- =============================================================================

INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('users', 'list_users',           'auto',    'low',    'List and search user accounts'),
    ('users', 'get_user_detail',      'auto',    'low',    'Get full user profile and activity stats'),
    ('users', 'suspend_user',         'confirm', 'medium', 'Temporarily suspend a user account'),
    ('users', 'unsuspend_user',       'confirm', 'medium', 'Re-enable a suspended user account'),
    ('users', 'change_user_persona',  'confirm', 'medium', 'Switch a user persona tier'),
    ('users', 'impersonate_user',     'confirm', 'low',    'Open read-only impersonation view for a user')
ON CONFLICT (action_category, action_name) DO NOTHING;
