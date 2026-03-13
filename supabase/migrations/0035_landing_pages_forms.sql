-- ============================================================================
-- Landing Pages and Forms Tables
-- ============================================================================
-- Created: 2025-02-10
-- Description: Tables for landing page management, form handling, and lead capture
-- ============================================================================

-- Landing Pages table
CREATE TABLE IF NOT EXISTS landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    html_content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backfill missing landing page columns when an older table already exists
ALTER TABLE landing_pages ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE landing_pages ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE landing_pages ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT FALSE;
ALTER TABLE landing_pages ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

UPDATE landing_pages
SET slug = CONCAT('page-', SUBSTRING(id::text, 1, 8))
WHERE slug IS NULL OR slug = '';

ALTER TABLE landing_pages ALTER COLUMN slug SET NOT NULL;

-- Unique slug per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_landing_pages_user_slug 
ON landing_pages(user_id, slug);

-- Index for published pages
CREATE INDEX IF NOT EXISTS idx_landing_pages_published 
ON landing_pages(published) WHERE published = TRUE;

-- Landing Forms table
CREATE TABLE IF NOT EXISTS landing_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    page_id UUID REFERENCES landing_pages(id) ON DELETE CASCADE,
    form_name TEXT NOT NULL,
    fields JSONB NOT NULL DEFAULT '[]',
    webhook_url TEXT,
    email_notification TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_landing_forms_user 
ON landing_forms(user_id);

CREATE INDEX IF NOT EXISTS idx_landing_forms_page 
ON landing_forms(page_id);

-- Form Submissions table
CREATE TABLE IF NOT EXISTS form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID NOT NULL REFERENCES landing_forms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    page_id UUID REFERENCES landing_pages(id) ON DELETE SET NULL,
    data JSONB NOT NULL DEFAULT '{}',
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_form_submissions_form 
ON form_submissions(form_id);

CREATE INDEX IF NOT EXISTS idx_form_submissions_user 
ON form_submissions(user_id);

CREATE INDEX IF NOT EXISTS idx_form_submissions_created 
ON form_submissions(created_at DESC);

-- ============================================================================
-- Row Level Security
-- ============================================================================

ALTER TABLE landing_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE landing_forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_submissions ENABLE ROW LEVEL SECURITY;

-- Landing Pages policies
DROP POLICY IF EXISTS "Users can view their own landing pages" ON landing_pages;
CREATE POLICY "Users can view their own landing pages"
ON landing_pages FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create their own landing pages" ON landing_pages;
CREATE POLICY "Users can create their own landing pages"
ON landing_pages FOR INSERT
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own landing pages" ON landing_pages;
CREATE POLICY "Users can update their own landing pages"
ON landing_pages FOR UPDATE
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own landing pages" ON landing_pages;
CREATE POLICY "Users can delete their own landing pages"
ON landing_pages FOR DELETE
USING (auth.uid() = user_id);

-- Public can view published pages
DROP POLICY IF EXISTS "Anyone can view published landing pages" ON landing_pages;
CREATE POLICY "Anyone can view published landing pages"
ON landing_pages FOR SELECT
USING (published = TRUE);

-- Service role full access
DROP POLICY IF EXISTS "Service role has full access to landing_pages" ON landing_pages;
CREATE POLICY "Service role has full access to landing_pages"
ON landing_pages FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Landing Forms policies
DROP POLICY IF EXISTS "Users can manage their own forms" ON landing_forms;
CREATE POLICY "Users can manage their own forms"
ON landing_forms FOR ALL
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to landing_forms" ON landing_forms;
CREATE POLICY "Service role has full access to landing_forms"
ON landing_forms FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Form Submissions policies
DROP POLICY IF EXISTS "Users can view submissions to their forms" ON form_submissions;
CREATE POLICY "Users can view submissions to their forms"
ON form_submissions FOR SELECT
USING (auth.uid() = user_id);

-- Allow public form submissions (anyone can submit)
DROP POLICY IF EXISTS "Anyone can submit forms" ON form_submissions;
CREATE POLICY "Anyone can submit forms"
ON form_submissions FOR INSERT
WITH CHECK (TRUE);

DROP POLICY IF EXISTS "Service role has full access to form_submissions" ON form_submissions;
CREATE POLICY "Service role has full access to form_submissions"
ON form_submissions FOR ALL
USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- ============================================================================
-- Updated At Trigger
-- ============================================================================

CREATE OR REPLACE FUNCTION update_landing_pages_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_landing_pages_updated_at ON landing_pages;
CREATE TRIGGER trigger_landing_pages_updated_at
BEFORE UPDATE ON landing_pages
FOR EACH ROW
EXECUTE FUNCTION update_landing_pages_updated_at();
