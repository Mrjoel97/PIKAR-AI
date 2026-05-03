-- Ensure generated-documents accepts all document export MIME types.
-- This repairs older environments where the bucket was created with only
-- application/json, which blocks PDF/PPTX/XLSX uploads at runtime.

DO $$
BEGIN
    IF to_regclass('storage.buckets') IS NULL THEN
        RAISE NOTICE 'Supabase storage.buckets is unavailable. Skipping generated-documents bucket repair.';
    ELSE
        INSERT INTO storage.buckets (id, name, public, allowed_mime_types)
        VALUES (
            'generated-documents',
            'generated-documents',
            false,
            ARRAY[
                'application/json',
                'application/pdf',
                'application/msword',
                'application/vnd.ms-excel',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/csv',
                'text/csv; charset=utf-8',
                'text/markdown',
                'text/plain'
            ]
        )
        ON CONFLICT (id) DO UPDATE
        SET
            public = EXCLUDED.public,
            allowed_mime_types = EXCLUDED.allowed_mime_types;
    END IF;
END $$;
