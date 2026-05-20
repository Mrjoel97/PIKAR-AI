BEGIN;
CREATE INDEX IF NOT EXISTS idx_kg_findings_embedding_semantic
    ON kg_findings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
ANALYZE kg_findings;
COMMIT;
