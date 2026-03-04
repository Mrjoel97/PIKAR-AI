-- AGENT-MEM-05: canonicalize long-term knowledge storage on vault_documents + embeddings

ALTER TABLE public.vault_documents
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS content_text TEXT,
    ADD COLUMN IF NOT EXISTS document_type TEXT,
    ADD COLUMN IF NOT EXISTS source_type TEXT,
    ADD COLUMN IF NOT EXISTS agent_id TEXT,
    ADD COLUMN IF NOT EXISTS source_url TEXT;

UPDATE public.vault_documents
SET
    title = COALESCE(
        title,
        NULLIF(BTRIM(metadata ->> 'title'), ''),
        filename
    ),
    content_text = COALESCE(
        content_text,
        NULLIF(BTRIM(metadata ->> 'content_text'), ''),
        NULLIF(BTRIM(metadata ->> 'content'), '')
    ),
    document_type = COALESCE(
        document_type,
        NULLIF(BTRIM(metadata ->> 'document_type'), ''),
        CASE
            WHEN COALESCE(category, '') <> '' THEN LOWER(REGEXP_REPLACE(category, '[^a-zA-Z0-9]+', '_', 'g'))
            ELSE 'uploaded_document'
        END
    ),
    source_type = COALESCE(
        source_type,
        NULLIF(BTRIM(metadata ->> 'source_type'), ''),
        'vault_document'
    ),
    agent_id = COALESCE(
        agent_id,
        NULLIF(BTRIM(metadata ->> 'agent_id'), '')
    ),
    source_url = COALESCE(
        source_url,
        NULLIF(BTRIM(metadata ->> 'source_url'), '')
    )
WHERE
    title IS NULL
    OR content_text IS NULL
    OR document_type IS NULL
    OR source_type IS NULL
    OR agent_id IS NULL
    OR source_url IS NULL;

CREATE INDEX IF NOT EXISTS idx_vault_documents_document_type
    ON public.vault_documents(document_type);

CREATE INDEX IF NOT EXISTS idx_vault_documents_agent_id
    ON public.vault_documents(agent_id);

CREATE INDEX IF NOT EXISTS idx_embeddings_source_id
    ON public.embeddings(source_id);

CREATE INDEX IF NOT EXISTS idx_embeddings_source_type
    ON public.embeddings(source_type);

COMMENT ON TABLE public.agent_knowledge IS
    'Deprecated compatibility table. Canonical knowledge storage lives in vault_documents + embeddings.';
