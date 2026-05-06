-- =============================================================================
-- Restore six Phase 7-15 admin tables that were registered as applied in
-- supabase_migrations.schema_migrations but never actually created in the
-- public schema. Diagnosed 2026-05-06 after /admin/analytics/aggregate hit
-- PGRST205 ("Could not find the table 'public.admin_analytics_daily' in the
-- schema cache"). Cross-checking via `supabase inspect db table-stats --linked`
-- showed six expected admin tables missing despite their source migrations
-- appearing in the applied list.
--
-- Likely cause: 2026-04-27 Cloud Run / Supabase migration from project b484
-- back to pikar-ai-project (see project_cloud_run_migration.md memory)
-- copied the schema_migrations registry but didn't bring all schema with it.
--
-- Tables restored (one CREATE TABLE per source migration):
--   - admin_analytics_daily          (20260321700000_analytics_summary_tables.sql)
--   - admin_agent_stats_daily        (20260321700000_analytics_summary_tables.sql)
--   - admin_agent_configs            (20260323000000_agent_config_feature_flags.sql)
--   - admin_feature_flags            (20260323000000_agent_config_feature_flags.sql)
--   - admin_knowledge_entries        (20260323100000_admin_knowledge_base.sql)
--   - admin_impersonation_sessions   (20260324200000_interactive_impersonation.sql)
--
-- Plus the ancillary objects from those originals that are also schema-level
-- (function + storage bucket) so they're consistent with the table presence.
--
-- All statements are idempotent (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF
-- NOT EXISTS, CREATE OR REPLACE FUNCTION, INSERT ... ON CONFLICT DO NOTHING)
-- so this migration is safe regardless of whether any of the listed objects
-- already exist on the target database. SQL is copied verbatim from the
-- originals -- no schema changes -- so re-applying the originals (e.g. via
-- `migration repair --status reverted` + `db push`) is also safe.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- From 20260321700000_analytics_summary_tables.sql -- Phase 10 Usage Analytics
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS admin_analytics_daily (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date   date        NOT NULL UNIQUE,
    dau         integer     NOT NULL DEFAULT 0,
    mau         integer     NOT NULL DEFAULT 0,
    messages    integer     NOT NULL DEFAULT 0,
    workflows   integer     NOT NULL DEFAULT 0,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_analytics_daily_stat_date
    ON admin_analytics_daily (stat_date DESC);

ALTER TABLE admin_analytics_daily ENABLE ROW LEVEL SECURITY;


CREATE TABLE IF NOT EXISTS admin_agent_stats_daily (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_date       date        NOT NULL,
    agent_name      text        NOT NULL,
    success_count   integer     NOT NULL DEFAULT 0,
    error_count     integer     NOT NULL DEFAULT 0,
    timeout_count   integer     NOT NULL DEFAULT 0,
    avg_duration_ms numeric(10, 2),
    total_calls     integer     NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (stat_date, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_admin_agent_stats_daily_date
    ON admin_agent_stats_daily (stat_date DESC, agent_name);

ALTER TABLE admin_agent_stats_daily ENABLE ROW LEVEL SECURITY;


-- ---------------------------------------------------------------------------
-- From 20260323000000_agent_config_feature_flags.sql -- Phase 12 Agent Config
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

CREATE TABLE IF NOT EXISTS admin_feature_flags (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_key    text        NOT NULL UNIQUE,
    is_enabled  boolean     NOT NULL DEFAULT false,
    description text,
    updated_by  uuid        REFERENCES auth.users(id),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE admin_agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_feature_flags ENABLE ROW LEVEL SECURITY;

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

INSERT INTO admin_feature_flags (flag_key, is_enabled, description)
VALUES
    ('workflow_kill_switch',    false, 'Hard stop for all workflow starts'),
    ('workflow_canary_enabled', false, 'Limit workflow execution to canary user list'),
    ('workflow_canary_user_ids',false, 'Whether canary user ID list is active (list managed in env var)')
ON CONFLICT (flag_key) DO NOTHING;


-- ---------------------------------------------------------------------------
-- From 20260323100000_admin_knowledge_base.sql -- Phase 12.1 Knowledge Base
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS admin_knowledge_entries (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename           text        NOT NULL,
    file_type          text        NOT NULL,
    mime_type          text,
    file_path          text,
    agent_scope        text,
    uploaded_by        text        NOT NULL,
    status             text        NOT NULL DEFAULT 'processing',
    chunk_count        integer     NOT NULL DEFAULT 0,
    embedding_ids      text[]      NOT NULL DEFAULT '{}',
    file_size_bytes    bigint,
    error_message      text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS admin_knowledge_entries_agent_scope_idx
    ON admin_knowledge_entries (agent_scope);
CREATE INDEX IF NOT EXISTS admin_knowledge_entries_status_idx
    ON admin_knowledge_entries (status);
CREATE INDEX IF NOT EXISTS admin_knowledge_entries_file_type_idx
    ON admin_knowledge_entries (file_type);

ALTER TABLE admin_knowledge_entries ENABLE ROW LEVEL SECURITY;

-- Note: explicitly schema-qualify the pgvector type. The original migration
-- (20260323100000) used bare `vector(768)`, which works only when `extensions`
-- is in the active search_path. Recent Supabase platform defaults tightened
-- the search_path during migration apply, so we qualify here to keep the
-- function creation independent of session search_path config.
CREATE OR REPLACE FUNCTION match_system_knowledge(
    query_embedding  extensions.vector(768),
    match_threshold  float  DEFAULT 0.5,
    match_count      int    DEFAULT 5,
    filter_agent_scope text DEFAULT NULL
)
RETURNS TABLE (
    id          uuid,
    content     text,
    metadata    jsonb,
    similarity  float
)
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content,
        e.metadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    WHERE
        e.metadata->>'scope' = 'system'
        AND (
            filter_agent_scope IS NULL
            OR e.metadata->>'agent_scope' IS NULL
            OR e.metadata->>'agent_scope' = filter_agent_scope
        )
        AND 1 - (e.embedding <=> query_embedding) >= match_threshold
    ORDER BY e.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('admin-knowledge', 'admin-knowledge', false, 104857600)
ON CONFLICT (id) DO NOTHING;


-- ---------------------------------------------------------------------------
-- From 20260324200000_interactive_impersonation.sql -- Phase 13 Impersonation
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.admin_impersonation_sessions (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    target_user_id   uuid        NOT NULL,
    is_active        boolean     NOT NULL DEFAULT true,
    expires_at       timestamptz NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    ended_at         timestamptz
);

CREATE INDEX IF NOT EXISTS idx_impersonation_sessions_target_active
    ON public.admin_impersonation_sessions (target_user_id, is_active, expires_at DESC);

ALTER TABLE public.admin_impersonation_sessions ENABLE ROW LEVEL SECURITY;
