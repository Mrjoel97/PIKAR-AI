-- Data I/O & Document Generation: bucket, column mappings, brand logo support
-- Phase 40-01: Foundation for CSV import/export and document generation

-- ============================================================================
-- csv_column_mappings: persisted AI-suggested column mappings per user per table
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.csv_column_mappings (
    id          uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    table_name  text        NOT NULL,
    mapping     jsonb       NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_csv_column_mappings_user_table
        UNIQUE (user_id, table_name)
);

CREATE INDEX IF NOT EXISTS idx_csv_column_mappings_user
    ON public.csv_column_mappings (user_id);

-- RLS policies
ALTER TABLE public.csv_column_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own column mappings"
    ON public.csv_column_mappings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own column mappings"
    ON public.csv_column_mappings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own column mappings"
    ON public.csv_column_mappings FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own column mappings"
    ON public.csv_column_mappings FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for admin operations
CREATE POLICY "Service role full access on csv_column_mappings"
    ON public.csv_column_mappings FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- updated_at trigger (reuses function from integration_infrastructure migration)
CREATE TRIGGER set_csv_column_mappings_updated_at
    BEFORE UPDATE ON public.csv_column_mappings
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- ============================================================================
-- generated-documents Storage bucket (private)
-- ============================================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('generated-documents', 'generated-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies: authenticated users can upload/read their own files
-- Path convention: {user_id}/exports/... and {user_id}/documents/...
CREATE POLICY "Users can upload own generated documents"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'generated-documents'
        AND auth.role() = 'authenticated'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can read own generated documents"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'generated-documents'
        AND auth.role() = 'authenticated'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can delete own generated documents"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'generated-documents'
        AND auth.role() = 'authenticated'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Service role can manage all generated documents (for cleanup jobs)
CREATE POLICY "Service role full access on generated-documents"
    ON storage.objects FOR ALL
    USING (
        bucket_id = 'generated-documents'
        AND auth.role() = 'service_role'
    )
    WITH CHECK (
        bucket_id = 'generated-documents'
        AND auth.role() = 'service_role'
    );

-- ============================================================================
-- brand_profiles: add logo_url column for branded PDF generation
-- ============================================================================
ALTER TABLE public.brand_profiles
    ADD COLUMN IF NOT EXISTS logo_url text;
