-- =============================================================================
-- Research Intelligence: Knowledge Graph Schema
-- Creates the seven knowledge-graph tables, indexes, RLS policies, triggers,
-- seed data, and the match_kg_entities RPC function.
--
-- Tables:
--   1. kg_entities       — graph nodes (companies, people, topics, etc.)
--   2. kg_aliases         — entity resolution / alternate names
--   3. kg_edges           — typed relationships between entities
--   4. kg_findings        — research findings attached to entities/edges
--   5. kg_research_log    — cost & usage tracking per research run
--   6. kg_watch_topics    — admin-managed monitoring topics
--   7. kg_domain_budgets  — per-domain budget configuration
-- =============================================================================

-- Guard: ensure pgvector is available
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- 1. kg_entities — graph nodes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name  TEXT NOT NULL,
    entity_type     TEXT NOT NULL
                    CHECK (entity_type IN (
                        'company', 'person', 'regulation', 'market',
                        'technology', 'topic', 'metric', 'country',
                        'institution', 'product', 'event'
                    )),
    domains         TEXT[] NOT NULL DEFAULT '{}',
    properties      JSONB NOT NULL DEFAULT '{}',
    embedding       VECTOR(768),
    source_count    INT NOT NULL DEFAULT 1,
    freshness_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_name, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_kg_entities_name_type
    ON kg_entities(canonical_name, entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_domains
    ON kg_entities USING GIN (domains);
CREATE INDEX IF NOT EXISTS idx_kg_entities_freshness
    ON kg_entities(freshness_at);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type
    ON kg_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_embedding
    ON kg_entities USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- 2. kg_aliases — entity resolution / alternate names
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_aliases (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id   UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    alias       TEXT NOT NULL,
    source      TEXT,
    confidence  FLOAT NOT NULL DEFAULT 1.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (alias, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_kg_aliases_alias
    ON kg_aliases(alias);
CREATE INDEX IF NOT EXISTS idx_kg_aliases_entity_id
    ON kg_aliases(entity_id);

-- ---------------------------------------------------------------------------
-- 3. kg_edges — relationships between entities
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    relationship    TEXT NOT NULL,
    domain          TEXT NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.8,
    evidence        JSONB NOT NULL DEFAULT '{}',
    source_url      TEXT,
    freshness_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, target_id, relationship, domain)
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_source_domain
    ON kg_edges(source_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target_domain
    ON kg_edges(target_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_edges_freshness
    ON kg_edges(freshness_at);

-- ---------------------------------------------------------------------------
-- 4. kg_findings — research findings attached to entities or edges
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id       UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    edge_id         UUID REFERENCES kg_edges(id) ON DELETE CASCADE,
    domain          TEXT NOT NULL,
    finding_text    TEXT NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.5,
    sources         JSONB NOT NULL DEFAULT '[]',
    contradicts     JSONB NOT NULL DEFAULT '[]',
    embedding       VECTOR(768),
    freshness_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (entity_id IS NOT NULL OR edge_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_kg_findings_entity_domain
    ON kg_findings(entity_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_findings_edge_domain
    ON kg_findings(edge_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_findings_freshness
    ON kg_findings(freshness_at);
CREATE INDEX IF NOT EXISTS idx_kg_findings_domain
    ON kg_findings(domain);
CREATE INDEX IF NOT EXISTS idx_kg_findings_embedding
    ON kg_findings USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- 5. kg_research_log — cost & usage tracking per research run
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_research_log (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain            TEXT NOT NULL,
    query             TEXT NOT NULL,
    depth             TEXT NOT NULL DEFAULT 'quick'
                      CHECK (depth IN ('quick', 'standard', 'deep')),
    tracks_run        INT NOT NULL DEFAULT 1,
    searches_used     INT NOT NULL DEFAULT 0,
    scrapes_used      INT NOT NULL DEFAULT 0,
    cost_usd          DECIMAL(10,4) NOT NULL DEFAULT 0,
    findings_count    INT NOT NULL DEFAULT 0,
    graph_updates     INT NOT NULL DEFAULT 0,
    triggered_by      TEXT NOT NULL DEFAULT 'agent_request'
                      CHECK (triggered_by IN (
                          'agent_request', 'scheduled', 'event', 'user_initiated'
                      )),
    requesting_agent  TEXT,
    user_id           UUID,
    duration_ms       INT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_research_log_domain_created
    ON kg_research_log(domain, created_at);
CREATE INDEX IF NOT EXISTS idx_kg_research_log_trigger_created
    ON kg_research_log(triggered_by, created_at);

-- ---------------------------------------------------------------------------
-- 6. kg_watch_topics — admin-managed monitoring topics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_watch_topics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain              TEXT NOT NULL,
    topic               TEXT NOT NULL,
    priority            TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    is_active           BOOLEAN NOT NULL DEFAULT true,
    last_researched_at  TIMESTAMPTZ,
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (domain, topic)
);

CREATE INDEX IF NOT EXISTS idx_kg_watch_topics_domain_active
    ON kg_watch_topics(domain, is_active);

-- ---------------------------------------------------------------------------
-- 7. kg_domain_budgets — per-domain budget configuration
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg_domain_budgets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain          TEXT NOT NULL UNIQUE,
    monthly_budget  DECIMAL(10,2) NOT NULL,
    alert_threshold FLOAT NOT NULL DEFAULT 0.8,
    auto_pause      BOOLEAN NOT NULL DEFAULT true,
    schedule_cron   TEXT NOT NULL DEFAULT '0 6 * * 1',
    schedule_tz     TEXT NOT NULL DEFAULT 'Africa/Johannesburg',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_domain_budgets_domain
    ON kg_domain_budgets(domain);

-- ---------------------------------------------------------------------------
-- 8. updated_at triggers
-- Reuse existing public.update_updated_at_column() (created in 0007, patched in 0027).
-- Do NOT redefine the function.
-- ---------------------------------------------------------------------------
CREATE TRIGGER update_kg_entities_updated_at
    BEFORE UPDATE ON kg_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kg_aliases_updated_at
    BEFORE UPDATE ON kg_aliases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kg_edges_updated_at
    BEFORE UPDATE ON kg_edges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kg_findings_updated_at
    BEFORE UPDATE ON kg_findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kg_research_log_updated_at
    BEFORE UPDATE ON kg_research_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kg_watch_topics_updated_at
    BEFORE UPDATE ON kg_watch_topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kg_domain_budgets_updated_at
    BEFORE UPDATE ON kg_domain_budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- 9. Row Level Security
-- All kg_* tables: SELECT open to all authenticated users (shared global graph).
-- Write operations (INSERT / UPDATE / DELETE) restricted to service_role only.
-- ---------------------------------------------------------------------------

-- kg_entities
ALTER TABLE kg_entities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_entities_select" ON kg_entities
    FOR SELECT USING (true);

CREATE POLICY "kg_entities_service_write" ON kg_entities
    FOR ALL USING (auth.role() = 'service_role');

-- kg_aliases
ALTER TABLE kg_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_aliases_select" ON kg_aliases
    FOR SELECT USING (true);

CREATE POLICY "kg_aliases_service_write" ON kg_aliases
    FOR ALL USING (auth.role() = 'service_role');

-- kg_edges
ALTER TABLE kg_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_edges_select" ON kg_edges
    FOR SELECT USING (true);

CREATE POLICY "kg_edges_service_write" ON kg_edges
    FOR ALL USING (auth.role() = 'service_role');

-- kg_findings
ALTER TABLE kg_findings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_findings_select" ON kg_findings
    FOR SELECT USING (true);

CREATE POLICY "kg_findings_service_write" ON kg_findings
    FOR ALL USING (auth.role() = 'service_role');

-- kg_research_log (SELECT for all, INSERT only for service_role)
ALTER TABLE kg_research_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_research_log_select" ON kg_research_log
    FOR SELECT USING (true);

CREATE POLICY "kg_research_log_service_insert" ON kg_research_log
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

-- kg_watch_topics
ALTER TABLE kg_watch_topics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_watch_topics_select" ON kg_watch_topics
    FOR SELECT USING (true);

CREATE POLICY "kg_watch_topics_service_write" ON kg_watch_topics
    FOR ALL USING (auth.role() = 'service_role');

-- kg_domain_budgets
ALTER TABLE kg_domain_budgets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_domain_budgets_select" ON kg_domain_budgets
    FOR SELECT USING (true);

CREATE POLICY "kg_domain_budgets_service_write" ON kg_domain_budgets
    FOR ALL USING (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- 10. Seed default domain budgets
-- ---------------------------------------------------------------------------
INSERT INTO kg_domain_budgets (domain, monthly_budget, schedule_cron) VALUES
    ('financial',        80.00,  '0 6 * * *'),
    ('marketing',        60.00,  '0 6 * * 1,3,5'),
    ('sales',            50.00,  '0 6 * * 1,4'),
    ('compliance',       45.00,  '0 6 * * 1'),
    ('customer_support', 40.00,  '0 6 * * 2,5'),
    ('strategic',        40.00,  '0 6 * * 2,5'),
    ('content',          30.00,  '0 6 * * 3'),
    ('operations',       30.00,  '0 6 * * 5'),
    ('hr',               30.00,  '0 6 * * 1'),
    ('data',             30.00,  '0 6 * * 4')
ON CONFLICT (domain) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 11. RPC: Semantic entity search via cosine similarity
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_kg_entities(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.55,
    filter_domains TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id              UUID,
    canonical_name  TEXT,
    entity_type     TEXT,
    domains         TEXT[],
    properties      JSONB,
    source_count    INT,
    freshness_at    TIMESTAMPTZ,
    similarity      FLOAT
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT
        e.id,
        e.canonical_name,
        e.entity_type,
        e.domains,
        e.properties,
        e.source_count,
        e.freshness_at,
        (1 - (e.embedding <=> query_embedding))::FLOAT AS similarity
    FROM public.kg_entities e
    WHERE e.embedding IS NOT NULL
      AND (1 - (e.embedding <=> query_embedding)) >= match_threshold
      AND (filter_domains IS NULL OR e.domains && filter_domains)
    ORDER BY e.embedding <=> query_embedding
    LIMIT GREATEST(COALESCE(match_count, 10), 1);
$$;

REVOKE ALL ON FUNCTION public.match_kg_entities(vector, integer, float, text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_kg_entities(vector, integer, float, text[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_kg_entities(vector, integer, float, text[]) TO service_role;
