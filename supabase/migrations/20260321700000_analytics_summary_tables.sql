-- =============================================================================
-- Phase 10: Usage Analytics — pre-aggregated summary tables
--
-- Creates two summary tables for the analytics dashboard:
--   1. admin_analytics_daily — DAU, MAU, messages, workflows per day
--   2. admin_agent_stats_daily — per-agent success/error/timeout/duration per day
--
-- RLS is enabled on both tables with no policies → service-role-only access,
-- matching the pattern established by all Phase 7 admin tables.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. admin_analytics_daily
-- One row per calendar date. Populated nightly by analytics_aggregator.py.
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

-- Speed up dashboard time-series queries (newest first)
CREATE INDEX IF NOT EXISTS idx_admin_analytics_daily_stat_date
    ON admin_analytics_daily (stat_date DESC);

ALTER TABLE admin_analytics_daily ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- 2. admin_agent_stats_daily
-- One row per (date, agent_name). Populated nightly by analytics_aggregator.py.
-- ---------------------------------------------------------------------------
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

-- Speed up per-agent time-series queries
CREATE INDEX IF NOT EXISTS idx_admin_agent_stats_daily_date
    ON admin_agent_stats_daily (stat_date DESC, agent_name);

ALTER TABLE admin_agent_stats_daily ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- admin_agent_permissions seed rows for analytics tools
-- Matches UNIQUE (action_category, action_name) constraint from Phase 7.
-- ---------------------------------------------------------------------------
INSERT INTO admin_agent_permissions (action_name, action_category, autonomy_level, description)
VALUES
    ('get_usage_stats',        'analytics', 'auto', 'View usage statistics (DAU, MAU, messages, workflows)'),
    ('get_agent_effectiveness', 'analytics', 'auto', 'View per-agent effectiveness metrics'),
    ('get_engagement_report',  'analytics', 'auto', 'View feature usage and engagement report'),
    ('generate_report',        'analytics', 'auto', 'Generate analytics summary report')
ON CONFLICT (action_category, action_name) DO NOTHING;
