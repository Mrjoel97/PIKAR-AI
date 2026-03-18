-- Marketing Content Tools: Phase 2
-- Blog posts, content calendar, and email templates

-- Enable moddatetime extension (required for auto-updating updated_at)
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

-- =============================================================================
-- 1. Blog Posts
-- =============================================================================
CREATE TABLE IF NOT EXISTS blog_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    excerpt TEXT,
    seo_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- seo_metadata: { meta_title, meta_description, keywords[], focus_keyword, og_image_url }
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'scheduled', 'published', 'archived')),
    featured_image_url TEXT,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    category TEXT,
    tags TEXT[] DEFAULT '{}',
    word_count INTEGER DEFAULT 0,
    reading_time_minutes INTEGER DEFAULT 0,
    published_at TIMESTAMPTZ,
    scheduled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_blog_posts_user_slug ON blog_posts(user_id, slug);
CREATE INDEX IF NOT EXISTS idx_blog_posts_status ON blog_posts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_blog_posts_campaign ON blog_posts(campaign_id) WHERE campaign_id IS NOT NULL;

ALTER TABLE blog_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blog_posts_select_own" ON blog_posts
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "blog_posts_insert_own" ON blog_posts
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "blog_posts_update_own" ON blog_posts
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "blog_posts_delete_own" ON blog_posts
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "blog_posts_service_role" ON blog_posts
    FOR ALL USING (auth.role() = 'service_role');

-- Auto-update updated_at
CREATE TRIGGER blog_posts_updated_at
    BEFORE UPDATE ON blog_posts
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);


-- =============================================================================
-- 2. Content Calendar
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('blog', 'social', 'email', 'video', 'newsletter', 'ad', 'other')),
    platform TEXT,
    -- platform: twitter, linkedin, facebook, instagram, tiktok, youtube, blog, email, etc.
    scheduled_date DATE NOT NULL,
    scheduled_time TIME,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'in_progress', 'ready', 'scheduled', 'published', 'cancelled')),
    description TEXT,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    blog_post_id UUID REFERENCES blog_posts(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- metadata: { target_audience, cta, hashtags[], utm_params, notes }
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_calendar_user_date ON content_calendar(user_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_content_calendar_status ON content_calendar(user_id, status);
CREATE INDEX IF NOT EXISTS idx_content_calendar_campaign ON content_calendar(campaign_id) WHERE campaign_id IS NOT NULL;

ALTER TABLE content_calendar ENABLE ROW LEVEL SECURITY;

CREATE POLICY "content_calendar_select_own" ON content_calendar
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "content_calendar_insert_own" ON content_calendar
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "content_calendar_update_own" ON content_calendar
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "content_calendar_delete_own" ON content_calendar
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "content_calendar_service_role" ON content_calendar
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER content_calendar_updated_at
    BEFORE UPDATE ON content_calendar
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);


-- =============================================================================
-- 3. Email Templates
-- =============================================================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL DEFAULT '',
    body_text TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general' CHECK (category IN ('welcome', 'nurture', 'promotional', 'transactional', 'newsletter', 're_engagement', 'announcement', 'general')),
    variables TEXT[] DEFAULT '{}',
    -- variables: ['first_name', 'company_name', 'offer_url'] — placeholders in the template
    ab_variants JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- ab_variants: [{ variant_name, subject, body_html, body_text }]
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- metadata: { tone, audience_segment, estimated_read_time, preview_text }
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_email_templates_user_category ON email_templates(user_id, category);
CREATE INDEX IF NOT EXISTS idx_email_templates_status ON email_templates(user_id, status);
CREATE INDEX IF NOT EXISTS idx_email_templates_campaign ON email_templates(campaign_id) WHERE campaign_id IS NOT NULL;

ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "email_templates_select_own" ON email_templates
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "email_templates_insert_own" ON email_templates
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "email_templates_update_own" ON email_templates
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "email_templates_delete_own" ON email_templates
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "email_templates_service_role" ON email_templates
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER email_templates_updated_at
    BEFORE UPDATE ON email_templates
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
