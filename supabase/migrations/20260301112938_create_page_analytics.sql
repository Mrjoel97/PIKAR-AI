-- ============================================================
-- Landing Page Analytics: page views, events, and visitor tracking
-- Run this migration in Supabase SQL Editor
-- ============================================================

CREATE TABLE public.page_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Page identification
    page_id UUID,  -- references landing_pages if exists
    page_url TEXT NOT NULL,
    page_title TEXT,
    
    -- Event info
    event_type TEXT NOT NULL DEFAULT 'pageview',  -- pageview, click, scroll, form_submit, cta_click
    event_label TEXT,  -- e.g. "hero_cta", "pricing_scroll"
    
    -- Visitor info (anonymous)
    visitor_id TEXT NOT NULL,      -- hashed fingerprint, no PII
    session_id TEXT,               -- group events in one visit
    
    -- Traffic source
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    
    -- Device info
    user_agent TEXT,
    device_type TEXT,  -- desktop, mobile, tablet
    country TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for fast queries
CREATE INDEX idx_page_analytics_user ON public.page_analytics(user_id);
CREATE INDEX idx_page_analytics_page ON public.page_analytics(page_id);
CREATE INDEX idx_page_analytics_created ON public.page_analytics(user_id, created_at DESC);
CREATE INDEX idx_page_analytics_event ON public.page_analytics(user_id, event_type);
CREATE INDEX idx_page_analytics_visitor ON public.page_analytics(visitor_id, created_at DESC);

-- RLS
ALTER TABLE public.page_analytics ENABLE ROW LEVEL SECURITY;

-- Users can read their own analytics
CREATE POLICY page_analytics_select ON public.page_analytics
    FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()));

-- Insert allowed for both authenticated users and the anon role (tracking pixel)
CREATE POLICY page_analytics_insert_auth ON public.page_analytics
    FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()));

-- Anon insert for tracking pixel (must specify user_id in payload)
CREATE POLICY page_analytics_insert_anon ON public.page_analytics
    FOR INSERT TO anon
    WITH CHECK (true);
