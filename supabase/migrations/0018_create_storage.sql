-- Migration: 0018_create_storage.sql
-- Description: Setup Storage Buckets and Media Assets table.

-- 1. Create Storage Buckets
-- Note: 'storage.buckets' is a system table in Supabase.
-- We use INSERT ... ON CONFLICT to avoid errors if they already exist.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('brand-assets', 'brand-assets', true, 52428800, '{image/*,video/*,application/pdf}'), -- 50MB limit
    ('user-content', 'user-content', false, 52428800, '{image/*,video/*,application/pdf}')
ON CONFLICT (id) DO UPDATE SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;


-- 2. Create Media Assets Table
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    bucket_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT, -- MIME type e.g. 'image/png'
    category TEXT, -- 'brand_logo', 'poster', 'explainer_video', etc.
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_media_assets_user_id ON media_assets(user_id);
CREATE INDEX idx_media_assets_bucket_id ON media_assets(bucket_id);
CREATE INDEX idx_media_assets_category ON media_assets(category);

-- RLS for media_assets table
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own media assets" ON media_assets
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS for Storage Buckets (storage.objects)
-- Policy: Users can upload/select/update/delete their own files in 'brand-assets' and 'user-content'
-- Note: Supabase Storage RLS is handled on the `storage.objects` table.

CREATE POLICY "Users receive access to their own folder in brand-assets" ON storage.objects
    FOR ALL
    TO authenticated
    USING ( bucket_id = 'brand-assets' AND (storage.foldername(name))[1] = auth.uid()::text )
    WITH CHECK ( bucket_id = 'brand-assets' AND (storage.foldername(name))[1] = auth.uid()::text );

CREATE POLICY "Users receive access to their own folder in user-content" ON storage.objects
    FOR ALL
    TO authenticated
    USING ( bucket_id = 'user-content' AND (storage.foldername(name))[1] = auth.uid()::text )
    WITH CHECK ( bucket_id = 'user-content' AND (storage.foldername(name))[1] = auth.uid()::text );
