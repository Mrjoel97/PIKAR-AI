-- Fix RLS for knowledge-vault bucket: path is media/{user_id}/{filename}
-- so the second segment (index 2 in 1-based PostgreSQL) is the user_id, not the first.
DROP POLICY IF EXISTS "Users can access their own files in knowledge-vault" ON storage.objects;
CREATE POLICY "Users can access their own files in knowledge-vault" ON storage.objects
    FOR ALL
    TO authenticated
    USING ( bucket_id = 'knowledge-vault' AND (storage.foldername(name))[2] = auth.uid()::text )
    WITH CHECK ( bucket_id = 'knowledge-vault' AND (storage.foldername(name))[2] = auth.uid()::text );
