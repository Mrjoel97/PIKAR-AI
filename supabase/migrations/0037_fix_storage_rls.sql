-- Migration: 0037_fix_storage_rls.sql
-- Description: Fix RLS policy for knowledge-vault to allow 'media/USER_ID/*' paths used by media tools.

DROP POLICY IF EXISTS "Users can access their own files in knowledge-vault" ON storage.objects;

CREATE POLICY "Users can access their own files in knowledge-vault" ON storage.objects
    FOR ALL
    TO authenticated
    USING (
        bucket_id = 'knowledge-vault' AND (
            split_part(name, '/', 1) = auth.uid()::text 
            OR 
            ( split_part(name, '/', 1) = 'media' AND split_part(name, '/', 2) = auth.uid()::text )
        )
    )
    WITH CHECK (
        bucket_id = 'knowledge-vault' AND (
            split_part(name, '/', 1) = auth.uid()::text 
            OR 
            ( split_part(name, '/', 1) = 'media' AND split_part(name, '/', 2) = auth.uid()::text )
        )
    );

