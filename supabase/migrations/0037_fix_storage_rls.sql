-- Migration: 0037_fix_storage_rls.sql
-- Description: Fix RLS policy for knowledge-vault to allow 'media/USER_ID/*' paths used by media tools.

DO $$
BEGIN
    IF to_regclass('storage.objects') IS NULL THEN
        RAISE NOTICE 'Supabase storage.objects is unavailable. Skipping knowledge-vault storage RLS update in 0037_fix_storage_rls.sql.';
    ELSE
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
    END IF;
END $$;