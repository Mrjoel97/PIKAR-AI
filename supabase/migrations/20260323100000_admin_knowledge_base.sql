-- =============================================================================
-- Phase 12.1: Agent Knowledge Base
-- Creates admin_knowledge_entries tracking table, match_system_knowledge RPC,
-- admin-knowledge storage bucket, and permission seeds.
--
-- Tables created:
--   1. admin_knowledge_entries — one row per uploaded file, tracks status + embeddings
--
-- RPC created:
--   1. match_system_knowledge — cosine similarity search over system-scoped embeddings
--
-- Seeds:
--   - storage.buckets: admin-knowledge (private, 100MB limit)
--   - admin_agent_permissions: 8 knowledge-domain rows
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. admin_knowledge_entries
-- One row per uploaded file. Tracks processing status, chunk count, and
-- embedding IDs for the background video transcription pipeline.
-- agent_scope=null means globally available to all agents.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_knowledge_entries (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename           text        NOT NULL,
    file_type          text        NOT NULL,   -- document | image | video
    mime_type          text,
    file_path          text,
    agent_scope        text,                   -- null = global; agent name = agent-specific
    uploaded_by        text        NOT NULL,
    status             text        NOT NULL DEFAULT 'processing',  -- processing | completed | failed
    chunk_count        integer     NOT NULL DEFAULT 0,
    embedding_ids      text[]      NOT NULL DEFAULT '{}',
    file_size_bytes    bigint,
    error_message      text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS admin_knowledge_entries_agent_scope_idx
    ON admin_knowledge_entries (agent_scope);

CREATE INDEX IF NOT EXISTS admin_knowledge_entries_status_idx
    ON admin_knowledge_entries (status);

CREATE INDEX IF NOT EXISTS admin_knowledge_entries_file_type_idx
    ON admin_knowledge_entries (file_type);

-- ---------------------------------------------------------------------------
-- Enable RLS on admin_knowledge_entries.
-- No policies defined: anon access is denied by default.
-- All access goes through the service-role client (bypasses RLS).
-- ---------------------------------------------------------------------------
ALTER TABLE admin_knowledge_entries ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- 2. match_system_knowledge RPC
-- Performs cosine similarity search over the EXISTING embeddings table,
-- filtering to rows where metadata->>'scope' = 'system'.
-- When filter_agent_scope is provided, also narrows to entries that are
-- global (agent_scope IS NULL) OR match the requested agent.
-- IMPORTANT: Does NOT modify the existing match_embeddings function.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_system_knowledge(
    query_embedding  vector(768),
    match_threshold  float  DEFAULT 0.5,
    match_count      int    DEFAULT 5,
    filter_agent_scope text DEFAULT NULL
)
RETURNS TABLE (
    id          uuid,
    content     text,
    metadata    jsonb,
    similarity  float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content,
        e.metadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    WHERE
        e.metadata->>'scope' = 'system'
        AND (
            filter_agent_scope IS NULL
            OR e.metadata->>'agent_scope' IS NULL
            OR e.metadata->>'agent_scope' = filter_agent_scope
        )
        AND 1 - (e.embedding <=> query_embedding) >= match_threshold
    ORDER BY e.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- ---------------------------------------------------------------------------
-- 3. Storage bucket: admin-knowledge
-- Private bucket for admin-uploaded training files (documents, images, videos).
-- 100 MB per-file limit (104857600 bytes).
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('admin-knowledge', 'admin-knowledge', false, 104857600)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Seed: admin_agent_permissions (knowledge domain)
-- 8 rows for knowledge management tools.
-- upload_knowledge and delete_knowledge_entry require explicit confirmation.
-- All read/search operations are auto tier.
-- ---------------------------------------------------------------------------
INSERT INTO admin_agent_permissions (action_category, action_name, autonomy_level, risk_level, description)
VALUES
    ('knowledge', 'upload_knowledge',              'confirm', 'high',   'Upload a document, image, or video to the agent knowledge base'),
    ('knowledge', 'list_knowledge_entries',        'auto',    'low',    'List knowledge base entries with optional agent scope filter'),
    ('knowledge', 'search_knowledge',              'auto',    'low',    'Semantic search over system-scoped knowledge embeddings'),
    ('knowledge', 'delete_knowledge_entry',        'confirm', 'medium', 'Delete a knowledge base entry and its associated embeddings'),
    ('knowledge', 'get_knowledge_stats',           'auto',    'low',    'Get aggregated knowledge base statistics by agent scope'),
    ('knowledge', 'check_knowledge_duplicate',     'auto',    'low',    'Check whether a file with the same name already exists'),
    ('knowledge', 'validate_knowledge_relevance',  'auto',    'low',    'Assess relevance of uploaded content for a specific agent'),
    ('knowledge', 'recommend_chunking_strategy',   'auto',    'low',    'Recommend optimal chunking parameters for a given document type')
ON CONFLICT (action_category, action_name) DO NOTHING;
