-- Ad Management: Phase 4
-- Ad campaigns, ad creatives, spend tracking, ROAS metrics

-- =============================================================================
-- 1. Ad Campaigns (platform-specific ad campaign tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('google_ads', 'meta_ads')),
    platform_campaign_id TEXT,
    -- platform_campaign_id: External ID from Google Ads or Meta Ads API
    name TEXT NOT NULL,
    ad_type TEXT NOT NULL DEFAULT 'search' CHECK (ad_type IN (
        'search', 'display', 'video', 'shopping', 'performance_max',
        'feed', 'stories', 'reels', 'carousel', 'collection'
    )),
    objective TEXT DEFAULT 'conversions' CHECK (objective IN (
        'awareness', 'traffic', 'engagement', 'leads', 'conversions', 'sales'
    )),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft', 'pending_review', 'active', 'paused', 'completed', 'rejected'
    )),
    targeting JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- targeting: { locations[], age_min, age_max, genders[], interests[], keywords[], audiences[], placements[] }
    bid_strategy TEXT DEFAULT 'manual_cpc' CHECK (bid_strategy IN (
        'manual_cpc', 'maximize_clicks', 'maximize_conversions', 'target_cpa',
        'target_roas', 'maximize_conversion_value', 'lowest_cost', 'cost_cap', 'bid_cap'
    )),
    bid_amount DECIMAL(10, 2),
    -- bid_amount: CPC/CPA/ROAS target depending on bid_strategy
    daily_budget DECIMAL(10, 2),
    total_budget DECIMAL(10, 2),
    currency TEXT NOT NULL DEFAULT 'USD',
    start_date DATE,
    end_date DATE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- metadata: { ad_group_id, ad_set_id, pixel_id, conversion_actions[], audience_id, persona_id }
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ad_campaigns_user ON ad_campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_ad_campaigns_campaign ON ad_campaigns(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ad_campaigns_platform ON ad_campaigns(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_ad_campaigns_status ON ad_campaigns(user_id, status);

ALTER TABLE ad_campaigns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ad_campaigns_select_own" ON ad_campaigns
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "ad_campaigns_insert_own" ON ad_campaigns
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "ad_campaigns_update_own" ON ad_campaigns
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "ad_campaigns_delete_own" ON ad_campaigns
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "ad_campaigns_service_role" ON ad_campaigns
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER ad_campaigns_updated_at
    BEFORE UPDATE ON ad_campaigns
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);


-- =============================================================================
-- 2. Ad Creatives (creative assets linked to ad campaigns)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ad_creatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ad_campaign_id UUID NOT NULL REFERENCES ad_campaigns(id) ON DELETE CASCADE,
    platform_creative_id TEXT,
    name TEXT NOT NULL,
    creative_type TEXT NOT NULL DEFAULT 'image' CHECK (creative_type IN (
        'image', 'video', 'carousel', 'responsive', 'html5', 'text_only'
    )),
    headline TEXT,
    description TEXT,
    call_to_action TEXT,
    -- call_to_action: 'Learn More', 'Shop Now', 'Sign Up', 'Get Offer', etc.
    primary_text TEXT,
    -- primary_text: Main ad copy (Facebook/Instagram primary text)
    destination_url TEXT,
    display_url TEXT,
    media_urls TEXT[] DEFAULT '{}',
    -- media_urls: URLs to images/videos used in the creative
    thumbnail_url TEXT,
    specs JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- specs: { width, height, aspect_ratio, file_format, file_size_kb, duration_seconds }
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft', 'pending_review', 'approved', 'active', 'paused', 'rejected'
    )),
    ab_variant TEXT,
    -- ab_variant: 'A', 'B', 'C' — for split testing
    performance JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- performance: { impressions, clicks, ctr, conversions, cost, cpc, cpa }
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ad_creatives_user ON ad_creatives(user_id);
CREATE INDEX IF NOT EXISTS idx_ad_creatives_campaign ON ad_creatives(ad_campaign_id);
CREATE INDEX IF NOT EXISTS idx_ad_creatives_status ON ad_creatives(user_id, status);

ALTER TABLE ad_creatives ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ad_creatives_select_own" ON ad_creatives
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "ad_creatives_insert_own" ON ad_creatives
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "ad_creatives_update_own" ON ad_creatives
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "ad_creatives_delete_own" ON ad_creatives
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "ad_creatives_service_role" ON ad_creatives
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER ad_creatives_updated_at
    BEFORE UPDATE ON ad_creatives
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);


-- =============================================================================
-- 3. Ad Spend Tracking (daily spend + metrics per ad campaign)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ad_spend_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ad_campaign_id UUID NOT NULL REFERENCES ad_campaigns(id) ON DELETE CASCADE,
    tracking_date DATE NOT NULL,
    spend DECIMAL(10, 2) NOT NULL DEFAULT 0,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    conversion_value DECIMAL(10, 2) NOT NULL DEFAULT 0,
    -- conversion_value: Revenue attributed to this day's ad spend
    ctr DECIMAL(5, 4) DEFAULT 0,
    cpc DECIMAL(10, 2) DEFAULT 0,
    cpa DECIMAL(10, 2) DEFAULT 0,
    roas DECIMAL(10, 2) DEFAULT 0,
    -- roas: conversion_value / spend
    currency TEXT NOT NULL DEFAULT 'USD',
    platform_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- platform_data: Raw metrics from platform API
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ad_spend_campaign_date
    ON ad_spend_tracking(ad_campaign_id, tracking_date);
CREATE INDEX IF NOT EXISTS idx_ad_spend_user_date
    ON ad_spend_tracking(user_id, tracking_date);

ALTER TABLE ad_spend_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ad_spend_tracking_select_own" ON ad_spend_tracking
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "ad_spend_tracking_insert_own" ON ad_spend_tracking
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "ad_spend_tracking_update_own" ON ad_spend_tracking
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "ad_spend_tracking_service_role" ON ad_spend_tracking
    FOR ALL USING (auth.role() = 'service_role');
