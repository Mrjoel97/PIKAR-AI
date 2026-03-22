-- Extend interaction_logs with research tracking columns
-- Used by the self-improvement system to compare research-backed vs non-research responses
-- Spec: docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md (Section 5)

-- Add research tracking columns
ALTER TABLE interaction_logs
    ADD COLUMN IF NOT EXISTS research_used BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS research_depth TEXT DEFAULT 'none'
        CHECK (research_depth IN ('none', 'cache', 'quick', 'standard', 'deep')),
    ADD COLUMN IF NOT EXISTS research_job_id UUID REFERENCES kg_research_log(id),
    ADD COLUMN IF NOT EXISTS graph_entities_hit INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS graph_freshness_avg REAL;

-- Index for self-improvement research analysis queries
-- Covers: "compare scores for research_used=true vs false, grouped by agent_id"
CREATE INDEX IF NOT EXISTS idx_interaction_logs_research
    ON interaction_logs (agent_id, research_used, research_depth, created_at);

-- Comment for documentation
COMMENT ON COLUMN interaction_logs.research_used IS 'Whether research backed this response';
COMMENT ON COLUMN interaction_logs.research_depth IS 'Depth of research: none, cache, quick, standard, deep';
COMMENT ON COLUMN interaction_logs.research_job_id IS 'FK to kg_research_log for cost correlation';
COMMENT ON COLUMN interaction_logs.graph_entities_hit IS 'Number of knowledge graph entities that contributed';
COMMENT ON COLUMN interaction_logs.graph_freshness_avg IS 'Average age in hours of graph data used';
