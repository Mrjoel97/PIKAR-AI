-- Migration: 0018_create_storage.sql
-- Description: Setup Storage Buckets and Media Assets table.

-- 0. Create Storage Buckets when the Supabase storage system tables are available.
DO $$
BEGIN
    IF to_regclass('storage.buckets') IS NULL OR to_regclass('storage.objects') IS NULL THEN
        RAISE NOTICE 'Supabase storage system tables are unavailable. Skipping bucket and storage policy setup in 0018_create_storage.sql.';
    ELSE
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES 
            ('brand-assets', 'brand-assets', true, 52428800, '{image/*,video/*,application/pdf}'),
            ('user-content', 'user-content', false, 52428800, '{image/*,video/*,application/pdf}')
        ON CONFLICT (id) DO UPDATE SET 
            public = EXCLUDED.public,
            file_size_limit = EXCLUDED.file_size_limit,
            allowed_mime_types = EXCLUDED.allowed_mime_types;
    END IF;
END $$;

-- 1. Create Media Assets Table
CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    bucket_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT,
    category TEXT,
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_media_assets_user_id ON media_assets(user_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_bucket_id ON media_assets(bucket_id);
CREATE INDEX IF NOT EXISTS idx_media_assets_category ON media_assets(category);

ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can CRUD their own media assets" ON media_assets;
CREATE POLICY "Users can CRUD their own media assets" ON media_assets
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 2. Storage RLS for Storage Buckets (storage.objects)
DO $$
BEGIN
    IF to_regclass('storage.objects') IS NULL THEN
        RAISE NOTICE 'Supabase storage.objects is unavailable. Skipping storage policies in 0018_create_storage.sql.';
    ELSE
        DROP POLICY IF EXISTS "Users receive access to their own folder in brand-assets" ON storage.objects;
        CREATE POLICY "Users receive access to their own folder in brand-assets" ON storage.objects
            FOR ALL
            TO authenticated
            USING ( bucket_id = 'brand-assets' AND split_part(name, '/', 1) = auth.uid()::text )
            WITH CHECK ( bucket_id = 'brand-assets' AND split_part(name, '/', 1) = auth.uid()::text );

        DROP POLICY IF EXISTS "Users receive access to their own folder in user-content" ON storage.objects;
        CREATE POLICY "Users receive access to their own folder in user-content" ON storage.objects
            FOR ALL
            TO authenticated
            USING ( bucket_id = 'user-content' AND split_part(name, '/', 1) = auth.uid()::text )
            WITH CHECK ( bucket_id = 'user-content' AND split_part(name, '/', 1) = auth.uid()::text );
    END IF;
END $$;