-- =============================================================================
-- Phase 16: App Builder Schema Foundation
-- Creates the five App Builder tables, indexes, RLS policies, triggers, and
-- the stitch-assets Storage bucket.
--
-- Tables:
--   1. app_projects
--   2. app_screens
--   3. screen_variants
--   4. design_systems
--   5. build_sessions
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. app_projects
-- Top-level project record; owns all screens, design systems, and sessions.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,  -- ownership enforced via RLS, no FK to auth.users (simplifies testing)
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'generating', 'ready', 'exported')),
    stage           TEXT NOT NULL DEFAULT 'questioning'
                    CHECK (stage IN ('questioning', 'research', 'brief', 'building', 'verifying', 'shipping', 'done')),
    creative_brief  JSONB DEFAULT '{}',
    design_system   JSONB DEFAULT '{}',
    sitemap         JSONB DEFAULT '[]',
    build_plan      JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_projects_user_id ON app_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_app_projects_status  ON app_projects(status);

-- ---------------------------------------------------------------------------
-- 2. app_screens
-- Individual screens/pages within a project. Ordered by order_index.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_screens (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID NOT NULL REFERENCES app_projects(id) ON DELETE CASCADE,
    user_id           UUID NOT NULL,  -- ownership enforced via RLS
    name              TEXT NOT NULL,
    page_type         TEXT NOT NULL DEFAULT 'page',
    device_type       TEXT NOT NULL DEFAULT 'DESKTOP'
                      CHECK (device_type IN ('DESKTOP', 'MOBILE', 'TABLET')),
    order_index       INTEGER NOT NULL DEFAULT 0,
    approved          BOOLEAN NOT NULL DEFAULT false,
    stitch_project_id TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_screens_project_id ON app_screens(project_id);
CREATE INDEX IF NOT EXISTS idx_app_screens_user_id    ON app_screens(user_id);

-- ---------------------------------------------------------------------------
-- 3. screen_variants
-- Multiple generated variants per screen. is_selected marks the active one.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS screen_variants (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id        UUID NOT NULL REFERENCES app_screens(id) ON DELETE CASCADE,
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    variant_index    INTEGER NOT NULL DEFAULT 0,
    stitch_screen_id TEXT,
    html_url         TEXT,     -- permanent Supabase Storage URL
    screenshot_url   TEXT,     -- permanent Supabase Storage URL
    prompt_used      TEXT,
    is_selected      BOOLEAN NOT NULL DEFAULT false,
    iteration        INTEGER NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_screen_variants_screen_id ON screen_variants(screen_id);
CREATE INDEX IF NOT EXISTS idx_screen_variants_user_id   ON screen_variants(user_id);

-- ---------------------------------------------------------------------------
-- 4. design_systems
-- Captured design tokens per project. Locked after user approval.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS design_systems (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID NOT NULL REFERENCES app_projects(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL,  -- ownership enforced via RLS
    name         TEXT NOT NULL DEFAULT 'Default',
    colors       JSONB DEFAULT '{}',
    typography   JSONB DEFAULT '{}',
    spacing      JSONB DEFAULT '{}',
    components   JSONB DEFAULT '{}',
    locked       BOOLEAN NOT NULL DEFAULT false,
    raw_markdown TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_design_systems_project_id ON design_systems(project_id);

-- ---------------------------------------------------------------------------
-- 5. build_sessions
-- Tracks the multi-stage conversation state for building a project.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS build_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES app_projects(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL,  -- ownership enforced via RLS
    stage       TEXT NOT NULL DEFAULT 'questioning',
    state       JSONB DEFAULT '{}',
    messages    JSONB DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_build_sessions_project_id ON build_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_build_sessions_user_id    ON build_sessions(user_id);

-- ---------------------------------------------------------------------------
-- 6. updated_at triggers
-- Reuse existing public.update_updated_at_column() (created in 0007, patched in 0027).
-- Do NOT redefine the function.
-- ---------------------------------------------------------------------------
CREATE TRIGGER update_app_projects_updated_at
    BEFORE UPDATE ON app_projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_app_screens_updated_at
    BEFORE UPDATE ON app_screens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_design_systems_updated_at
    BEFORE UPDATE ON design_systems
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_build_sessions_updated_at
    BEFORE UPDATE ON build_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- 7. Row Level Security
-- Each table: SELECT/UPDATE/DELETE USING auth.uid() = user_id
--             INSERT WITH CHECK auth.uid() = user_id
-- screen_variants uses auth.uid() = user_id as well.
-- ---------------------------------------------------------------------------

-- app_projects
ALTER TABLE app_projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "app_projects_user_select" ON app_projects
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "app_projects_user_insert" ON app_projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "app_projects_user_update" ON app_projects
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "app_projects_user_delete" ON app_projects
    FOR DELETE USING (auth.uid() = user_id);

-- app_screens
ALTER TABLE app_screens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "app_screens_user_select" ON app_screens
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "app_screens_user_insert" ON app_screens
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "app_screens_user_update" ON app_screens
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "app_screens_user_delete" ON app_screens
    FOR DELETE USING (auth.uid() = user_id);

-- screen_variants
ALTER TABLE screen_variants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "screen_variants_user_select" ON screen_variants
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "screen_variants_user_insert" ON screen_variants
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "screen_variants_user_update" ON screen_variants
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "screen_variants_user_delete" ON screen_variants
    FOR DELETE USING (auth.uid() = user_id);

-- design_systems
ALTER TABLE design_systems ENABLE ROW LEVEL SECURITY;

CREATE POLICY "design_systems_user_select" ON design_systems
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "design_systems_user_insert" ON design_systems
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "design_systems_user_update" ON design_systems
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "design_systems_user_delete" ON design_systems
    FOR DELETE USING (auth.uid() = user_id);

-- build_sessions
ALTER TABLE build_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "build_sessions_user_select" ON build_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "build_sessions_user_insert" ON build_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "build_sessions_user_update" ON build_sessions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "build_sessions_user_delete" ON build_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- 8. Storage bucket: stitch-assets
-- Public bucket for HTML previews, screenshots, and exported ZIPs.
-- Max 50 MB per file; restricted to web-safe MIME types.
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'stitch-assets',
    'stitch-assets',
    true,
    52428800,
    ARRAY['text/html', 'image/png', 'image/jpeg', 'image/webp', 'application/zip']
)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS: allow public reads, authenticated user writes
CREATE POLICY "stitch_assets_public_read" ON storage.objects
    FOR SELECT USING (bucket_id = 'stitch-assets');

CREATE POLICY "stitch_assets_user_insert" ON storage.objects
    FOR INSERT WITH CHECK (bucket_id = 'stitch-assets' AND auth.role() = 'authenticated');

CREATE POLICY "stitch_assets_user_update" ON storage.objects
    FOR UPDATE USING (bucket_id = 'stitch-assets' AND auth.uid()::text = (storage.foldername(name))[1]);
