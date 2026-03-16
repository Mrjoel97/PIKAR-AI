-- Fix RLS for knowledge-vault bucket: path is media/{user_id}/{filename}
-- so the second segment (index 2 in 1-based PostgreSQL) is the user_id, not the first.
DO $$
BEGIN
    IF to_regclass('storage.objects') IS NULL THEN
        RAISE NOTICE 'Supabase storage.objects is unavailable. Skipping knowledge-vault storage RLS update in 0049_fix_knowledge_vault_storage_rls.sql.';
    ELSE
        DROP POLICY IF EXISTS "Users can access their own files in knowledge-vault" ON storage.objects;
        CREATE POLICY "Users can access their own files in knowledge-vault" ON storage.objects
            FOR ALL
            TO authenticated
            USING ( bucket_id = 'knowledge-vault' AND split_part(name, '/', 2) = auth.uid()::text )
            WITH CHECK ( bucket_id = 'knowledge-vault' AND split_part(name, '/', 2) = auth.uid()::text );
    END IF;
END $$;