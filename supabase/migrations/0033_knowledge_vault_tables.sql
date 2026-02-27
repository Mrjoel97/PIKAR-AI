-- Migration: 0033_knowledge_vault_tables.sql
-- Description: Create tables and storage for Knowledge Vault feature

-- 1. Create knowledge-vault storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('knowledge-vault', 'knowledge-vault', false, 52428800, '{application/pdf,text/*,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,image/*,video/*,audio/*}')
ON CONFLICT (id) DO UPDATE SET 
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. Create vault_documents table for tracking uploaded documents
CREATE TABLE IF NOT EXISTS vault_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    size_bytes BIGINT,
    category TEXT,
    is_processed BOOLEAN DEFAULT false,
    embedding_count INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for vault_documents
CREATE INDEX IF NOT EXISTS idx_vault_documents_user_id ON vault_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_vault_documents_created_at ON vault_documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_documents_is_processed ON vault_documents(is_processed);

-- RLS for vault_documents
ALTER TABLE vault_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can CRUD their own vault documents" ON vault_documents;
CREATE POLICY "Users can CRUD their own vault documents" ON vault_documents
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 3. Create agent_google_docs table for tracking agent-created Google Docs
CREATE TABLE IF NOT EXISTS agent_google_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id TEXT,
    doc_id TEXT NOT NULL, -- Google Doc ID
    title TEXT NOT NULL,
    doc_url TEXT NOT NULL,
    doc_type TEXT, -- 'report', 'document', 'spreadsheet', etc.
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for agent_google_docs
CREATE INDEX IF NOT EXISTS idx_agent_google_docs_user_id ON agent_google_docs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_google_docs_created_at ON agent_google_docs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_google_docs_agent_id ON agent_google_docs(agent_id);

-- RLS for agent_google_docs
ALTER TABLE agent_google_docs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own agent Google Docs" ON agent_google_docs;
CREATE POLICY "Users can view their own agent Google Docs" ON agent_google_docs
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can insert agent Google Docs" ON agent_google_docs;
CREATE POLICY "Service role can insert agent Google Docs" ON agent_google_docs
    FOR INSERT
    WITH CHECK (true);

-- 4. Storage RLS for knowledge-vault bucket
DROP POLICY IF EXISTS "Users can access their own files in knowledge-vault" ON storage.objects;
CREATE POLICY "Users can access their own files in knowledge-vault" ON storage.objects
    FOR ALL
    TO authenticated
    USING ( bucket_id = 'knowledge-vault' AND (storage.foldername(name))[1] = auth.uid()::text )
    WITH CHECK ( bucket_id = 'knowledge-vault' AND (storage.foldername(name))[1] = auth.uid()::text );

-- 5. Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_vault_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vault_documents_updated_at ON vault_documents;
CREATE TRIGGER vault_documents_updated_at
    BEFORE UPDATE ON vault_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_vault_documents_updated_at();
