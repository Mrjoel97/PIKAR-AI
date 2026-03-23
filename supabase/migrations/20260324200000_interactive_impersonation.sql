-- Interactive Impersonation Sessions
-- Tracks active admin impersonation sessions for audit, allow-list enforcement,
-- and notification suppression. Phase 13, Plan 01.

-- ─── Table ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.admin_impersonation_sessions (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- target_user_id uses plain UUID (no FK to auth.users) — matches app_projects pattern
    -- from 16-01 decision: simplifies service-role testing and avoids cascade complexity.
    target_user_id   uuid        NOT NULL,
    is_active        boolean     NOT NULL DEFAULT true,
    expires_at       timestamptz NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    ended_at         timestamptz
);

-- Index optimised for the notification suppression query:
--   SELECT ... WHERE target_user_id = $1 AND is_active = true AND expires_at > now()
CREATE INDEX IF NOT EXISTS idx_impersonation_sessions_target_active
    ON public.admin_impersonation_sessions (target_user_id, is_active, expires_at DESC);

-- ─── RLS ──────────────────────────────────────────────────────────────────────
ALTER TABLE public.admin_impersonation_sessions ENABLE ROW LEVEL SECURITY;

-- All access is via service-role client (bypasses RLS) — no user-facing policies needed.

-- ─── admin_agent_permissions seed ─────────────────────────────────────────────
-- Seed three permission rows for user-management tools introduced in Phase 13.
-- ON CONFLICT DO NOTHING keeps migrations idempotent.
INSERT INTO public.admin_agent_permissions
    (resource, action, autonomy_tier, risk_level, description)
VALUES
    (
        'users',
        'activate_impersonation',
        'confirm',
        'medium',
        'Start an interactive impersonation session as a target user — requires super-admin.'
    ),
    (
        'users',
        'get_at_risk_users',
        'auto',
        'low',
        'List users with anomalous activity patterns that may need intervention.'
    ),
    (
        'users',
        'get_user_support_context',
        'auto',
        'low',
        'Retrieve recent support context (actions, errors) for a specific user.'
    )
ON CONFLICT (resource, action) DO NOTHING;
