-- Migration: Social Analytics Cache + Social Listening Tables
-- Supports: social media analytics caching, brand monitoring, and mention tracking.

-- ============================================================
-- 1. Social Analytics Cache
-- Stores periodic snapshots of platform analytics for historical comparison.
-- ============================================================
CREATE TABLE IF NOT EXISTS social_analytics_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN (
        'twitter', 'linkedin', 'facebook', 'instagram', 'tiktok', 'youtube'
    )),
    metric_type TEXT NOT NULL CHECK (metric_type IN ('account', 'post')),
    resource_id TEXT,  -- post/video ID for post-level; NULL for account-level
    metrics JSONB NOT NULL DEFAULT '{}',
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_social_analytics_user_platform
    ON social_analytics_cache(user_id, platform, metric_type);
CREATE INDEX IF NOT EXISTS idx_social_analytics_fetched
    ON social_analytics_cache(fetched_at DESC);

-- ============================================================
-- 2. Brand Monitors
-- Stores active brand/keyword monitoring configurations.
-- ============================================================
CREATE TABLE IF NOT EXISTS brand_monitors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_name TEXT NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    platforms TEXT[] DEFAULT ARRAY['web', 'twitter', 'reddit'],
    is_active BOOLEAN DEFAULT true,
    last_scan_at TIMESTAMPTZ,
    scan_interval_minutes INT DEFAULT 1440,  -- daily by default
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_monitors_user
    ON brand_monitors(user_id, is_active);

-- ============================================================
-- 3. Brand Mentions
-- Stores discovered brand mentions from monitoring scans.
-- ============================================================
CREATE TABLE IF NOT EXISTS brand_mentions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    monitor_id UUID NOT NULL REFERENCES brand_monitors(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('web', 'twitter', 'reddit', 'linkedin', 'facebook', 'instagram')),
    title TEXT,
    content TEXT,
    url TEXT,
    author TEXT,
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral', 'mixed')),
    engagement_score INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    published_at TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_mentions_monitor
    ON brand_mentions(monitor_id, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_brand_mentions_source
    ON brand_mentions(user_id, source, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_brand_mentions_sentiment
    ON brand_mentions(user_id, sentiment);

-- ============================================================
-- 4. Extend connected_accounts platform CHECK (if needed)
-- Add google_search_console and google_analytics as valid platforms.
-- ============================================================
-- Note: If the connected_accounts table uses a CHECK constraint on platform,
-- this ALTER replaces it. If it uses an enum or has no constraint, skip this.
DO $$
BEGIN
    -- Try to drop and recreate the check constraint if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'connected_accounts'
        AND constraint_type = 'CHECK'
        AND constraint_name LIKE '%platform%'
    ) THEN
        EXECUTE (
            SELECT 'ALTER TABLE connected_accounts DROP CONSTRAINT ' || constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'connected_accounts'
            AND constraint_type = 'CHECK'
            AND constraint_name LIKE '%platform%'
            LIMIT 1
        );
        ALTER TABLE connected_accounts ADD CONSTRAINT connected_accounts_platform_check
            CHECK (platform IN (
                'twitter', 'linkedin', 'facebook', 'instagram',
                'tiktok', 'youtube', 'google_search_console', 'google_analytics'
            ));
    END IF;
END $$;

-- ============================================================
-- 5. RLS Policies
-- ============================================================
ALTER TABLE social_analytics_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_monitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_mentions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analytics cache"
    ON social_analytics_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to analytics cache"
    ON social_analytics_cache FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Users can manage own brand monitors"
    ON brand_monitors FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to brand monitors"
    ON brand_monitors FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Users can view own brand mentions"
    ON brand_mentions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to brand mentions"
    ON brand_mentions FOR ALL
    USING (auth.role() = 'service_role');
