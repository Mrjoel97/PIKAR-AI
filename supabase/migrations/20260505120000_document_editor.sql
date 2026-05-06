-- supabase/migrations/20260505120000_document_editor.sql

-- moddatetime is required for the updated_at trigger below; idempotent.
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE IF NOT EXISTS document_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL UNIQUE,
    doc_class TEXT NOT NULL CHECK (doc_class IN
        ('report','spreadsheet','presentation','word','google_doc','google_sheet')),
    source JSONB,
    extracted_text TEXT,
    extracted_at TIMESTAMPTZ,
    forked_from_upload BOOLEAN NOT NULL DEFAULT false,
    binary_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_sources_user ON document_sources(user_id);

CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document_sources(document_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_snapshot JSONB NOT NULL,
    binary_url TEXT NOT NULL,
    diff_summary TEXT,
    created_by TEXT NOT NULL CHECK (created_by IN ('agent','user','system')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_versions_doc ON document_versions(document_id, created_at DESC);

ALTER TABLE document_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see their own document sources"
    ON document_sources FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert their own document sources"
    ON document_sources FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update their own document sources"
    ON document_sources FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users delete their own document sources"
    ON document_sources FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "Service role full access on document_sources"
    ON document_sources FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Users see their own document versions"
    ON document_versions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert their own document versions"
    ON document_versions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access on document_versions"
    ON document_versions FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER document_sources_updated_at
    BEFORE UPDATE ON document_sources
    FOR EACH ROW EXECUTE FUNCTION extensions.moddatetime(updated_at);
