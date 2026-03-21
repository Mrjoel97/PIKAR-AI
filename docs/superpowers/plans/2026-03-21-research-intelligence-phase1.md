# Research Intelligence System — Phase 1: Knowledge Graph Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the knowledge graph schema in Supabase and add a `graph_read()` tool to all 10 specialized agents so they can query structured intelligence with sub-second cached lookups.

**Architecture:** 7 new Supabase tables (kg_entities, kg_aliases, kg_edges, kg_findings, kg_research_log, kg_watch_topics, kg_domain_budgets) with RLS policies, indexes, and updated_at triggers. A new `graph_read()` ADK tool queries the graph via Supabase with Redis caching (using existing circuit breaker). A new `graph_service.py` encapsulates all graph read/write logic. The tool is added to every specialized agent's tool list.

**Tech Stack:** Supabase (PostgreSQL + pgvector), Redis (existing cache layer), Python async, Google ADK tool pattern

**Spec:** `docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md`

---

## File Structure

```
NEW FILES:
  supabase/migrations/20260321500000_knowledge_graph.sql    — All 7 kg_* tables + RLS + indexes
  app/services/graph_service.py                              — Knowledge graph read/write service
  app/agents/tools/graph_tools.py                            — graph_read() ADK tool + GRAPH_TOOLS export
  app/agents/research/__init__.py                            — Package init (empty for now)
  app/agents/research/config.py                              — Domain freshness thresholds + config
  tests/unit/test_graph_service.py                           — Graph service unit tests
  tests/unit/test_graph_tools.py                             — Graph tool unit tests
  tests/integration/test_knowledge_graph_migration.py        — Migration verification test

MODIFIED FILES:
  app/services/cache.py                                      — Add get_generic/set_generic methods
  app/agents/specialized_agents.py                           — Add GRAPH_TOOLS import
  app/agents/financial/agent.py                              — Add graph_read to tools
  app/agents/content/agent.py                                — Add graph_read to tools
  app/agents/strategic/agent.py                              — Add graph_read to tools
  app/agents/sales/agent.py                                  — Add graph_read to tools
  app/agents/marketing/agent.py                              — Add graph_read to tools
  app/agents/operations/agent.py                             — Add graph_read to tools
  app/agents/hr/agent.py                                     — Add graph_read to tools
  app/agents/compliance/agent.py                             — Add graph_read to tools
  app/agents/customer_support/agent.py                       — Add graph_read to tools
  app/agents/data/agent.py                                   — Add graph_read to tools
```

---

## Task 1: Supabase Migration — Knowledge Graph Tables

**Files:**
- Create: `supabase/migrations/20260321500000_knowledge_graph.sql`

- [ ] **Step 1: Create the migration file with all 7 tables**

```sql
-- Knowledge Graph Schema for Research Intelligence System
-- Spec: docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md

-- Ensure pgvector extension is available
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1. kg_entities — Graph nodes
-- ============================================================
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

    CONSTRAINT uq_kg_entity UNIQUE (canonical_name, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_kg_entities_name_type
    ON kg_entities (canonical_name, entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_domains
    ON kg_entities USING GIN (domains);
CREATE INDEX IF NOT EXISTS idx_kg_entities_freshness
    ON kg_entities (freshness_at);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type
    ON kg_entities (entity_type);
-- HNSW index for semantic entity search (requires pgvector 0.5+)
CREATE INDEX IF NOT EXISTS idx_kg_entities_embedding
    ON kg_entities USING hnsw (embedding vector_cosine_ops);

CREATE TRIGGER update_kg_entities_updated_at
    BEFORE UPDATE ON kg_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_entities ENABLE ROW LEVEL SECURITY;

-- Global read access (shared graph), service_role for writes
CREATE POLICY "kg_entities_select_all" ON kg_entities
    FOR SELECT USING (true);
CREATE POLICY "kg_entities_service_role_insert" ON kg_entities
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_entities_service_role_update" ON kg_entities
    FOR UPDATE USING (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_entities_service_role_delete" ON kg_entities
    FOR DELETE USING (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 2. kg_aliases — Entity resolution
-- ============================================================
CREATE TABLE IF NOT EXISTS kg_aliases (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id   UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    alias       TEXT NOT NULL,
    source      TEXT,
    confidence  FLOAT NOT NULL DEFAULT 1.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_kg_alias UNIQUE (alias, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_kg_aliases_alias
    ON kg_aliases (alias);
CREATE INDEX IF NOT EXISTS idx_kg_aliases_entity_id
    ON kg_aliases (entity_id);

CREATE TRIGGER update_kg_aliases_updated_at
    BEFORE UPDATE ON kg_aliases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_aliases_select_all" ON kg_aliases
    FOR SELECT USING (true);
CREATE POLICY "kg_aliases_service_role_insert" ON kg_aliases
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_aliases_service_role_update" ON kg_aliases
    FOR UPDATE USING (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_aliases_service_role_delete" ON kg_aliases
    FOR DELETE USING (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 3. kg_edges — Relationships between entities
-- ============================================================
CREATE TABLE IF NOT EXISTS kg_edges (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_id     UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    relationship  TEXT NOT NULL,
    domain        TEXT NOT NULL,
    confidence    FLOAT NOT NULL DEFAULT 0.8,
    evidence      JSONB NOT NULL DEFAULT '{}',
    source_url    TEXT,
    freshness_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_kg_edge UNIQUE (source_id, target_id, relationship, domain)
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_source_domain
    ON kg_edges (source_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target_domain
    ON kg_edges (target_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_edges_freshness
    ON kg_edges (freshness_at);

CREATE TRIGGER update_kg_edges_updated_at
    BEFORE UPDATE ON kg_edges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_edges_select_all" ON kg_edges
    FOR SELECT USING (true);
CREATE POLICY "kg_edges_service_role_insert" ON kg_edges
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_edges_service_role_update" ON kg_edges
    FOR UPDATE USING (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_edges_service_role_delete" ON kg_edges
    FOR DELETE USING (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 4. kg_findings — Research findings attached to entities/edges
-- ============================================================
CREATE TABLE IF NOT EXISTS kg_findings (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id     UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    edge_id       UUID REFERENCES kg_edges(id) ON DELETE CASCADE,
    domain        TEXT NOT NULL,
    finding_text  TEXT NOT NULL,
    confidence    FLOAT NOT NULL DEFAULT 0.5,
    sources       JSONB NOT NULL DEFAULT '[]',
    contradicts   JSONB NOT NULL DEFAULT '[]',
    embedding     VECTOR(768),
    freshness_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_finding_anchor
        CHECK (entity_id IS NOT NULL OR edge_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_kg_findings_entity_domain
    ON kg_findings (entity_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_findings_edge_domain
    ON kg_findings (edge_id, domain);
CREATE INDEX IF NOT EXISTS idx_kg_findings_freshness
    ON kg_findings (freshness_at);
CREATE INDEX IF NOT EXISTS idx_kg_findings_domain
    ON kg_findings (domain);
-- HNSW index for semantic finding search (requires pgvector 0.5+)
CREATE INDEX IF NOT EXISTS idx_kg_findings_embedding
    ON kg_findings USING hnsw (embedding vector_cosine_ops);

CREATE TRIGGER update_kg_findings_updated_at
    BEFORE UPDATE ON kg_findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_findings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_findings_select_all" ON kg_findings
    FOR SELECT USING (true);
CREATE POLICY "kg_findings_service_role_insert" ON kg_findings
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_findings_service_role_update" ON kg_findings
    FOR UPDATE USING (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_findings_service_role_delete" ON kg_findings
    FOR DELETE USING (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 5. kg_research_log — Cost tracking + audit trail
-- ============================================================
CREATE TABLE IF NOT EXISTS kg_research_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain          TEXT NOT NULL,
    query           TEXT NOT NULL,
    depth           TEXT NOT NULL DEFAULT 'quick'
                    CHECK (depth IN ('quick', 'standard', 'deep')),
    tracks_run      INT NOT NULL DEFAULT 1,
    searches_used   INT NOT NULL DEFAULT 0,
    scrapes_used    INT NOT NULL DEFAULT 0,
    cost_usd        DECIMAL(10,4) NOT NULL DEFAULT 0,
    findings_count  INT NOT NULL DEFAULT 0,
    graph_updates   INT NOT NULL DEFAULT 0,
    triggered_by    TEXT NOT NULL DEFAULT 'agent_request'
                    CHECK (triggered_by IN (
                        'agent_request', 'scheduled', 'event', 'user_initiated'
                    )),
    requesting_agent TEXT,
    user_id         UUID,
    duration_ms     INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kg_research_log_domain_created
    ON kg_research_log (domain, created_at);
CREATE INDEX IF NOT EXISTS idx_kg_research_log_triggered
    ON kg_research_log (triggered_by, created_at);

CREATE TRIGGER update_kg_research_log_updated_at
    BEFORE UPDATE ON kg_research_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_research_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_research_log_select_all" ON kg_research_log
    FOR SELECT USING (true);
CREATE POLICY "kg_research_log_service_role_insert" ON kg_research_log
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 6. kg_watch_topics — Admin-managed watch topics
-- ============================================================
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

    CONSTRAINT uq_kg_watch_topic UNIQUE (domain, topic)
);

CREATE INDEX IF NOT EXISTS idx_kg_watch_topics_domain_active
    ON kg_watch_topics (domain, is_active);

CREATE TRIGGER update_kg_watch_topics_updated_at
    BEFORE UPDATE ON kg_watch_topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_watch_topics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_watch_topics_select_all" ON kg_watch_topics
    FOR SELECT USING (true);
CREATE POLICY "kg_watch_topics_service_role_insert" ON kg_watch_topics
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_watch_topics_service_role_update" ON kg_watch_topics
    FOR UPDATE USING (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_watch_topics_service_role_delete" ON kg_watch_topics
    FOR DELETE USING (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 7. kg_domain_budgets — Per-domain budget configuration
-- ============================================================
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
    ON kg_domain_budgets (domain);

CREATE TRIGGER update_kg_domain_budgets_updated_at
    BEFORE UPDATE ON kg_domain_budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE kg_domain_budgets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kg_domain_budgets_select_all" ON kg_domain_budgets
    FOR SELECT USING (true);
CREATE POLICY "kg_domain_budgets_service_role_insert" ON kg_domain_budgets
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role'
    );
CREATE POLICY "kg_domain_budgets_service_role_update" ON kg_domain_budgets
    FOR UPDATE USING (
        auth.role() = 'service_role'
    );

-- ============================================================
-- 8. Seed default domain budgets
-- ============================================================
INSERT INTO kg_domain_budgets (domain, monthly_budget, schedule_cron) VALUES
    ('financial',        80.00,  '0 6 * * *'),         -- daily
    ('marketing',        60.00,  '0 6 * * 1,3,5'),     -- mon/wed/fri
    ('sales',            50.00,  '0 6 * * 1,4'),       -- mon/thu
    ('compliance',       45.00,  '0 6 * * 1'),         -- monday
    ('customer_support', 40.00,  '0 6 * * 2,5'),       -- tue/fri
    ('strategic',        40.00,  '0 6 * * 2,5'),       -- tue/fri
    ('content',          30.00,  '0 6 * * 3'),         -- wednesday
    ('operations',       30.00,  '0 6 * * 5'),         -- friday
    ('hr',               30.00,  '0 6 * * 1'),         -- biweekly (app logic)
    ('data',             30.00,  '0 6 * * 4')          -- thursday
ON CONFLICT (domain) DO NOTHING;

-- ============================================================
-- 9. RPC function for semantic entity search
-- ============================================================
CREATE OR REPLACE FUNCTION match_kg_entities(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.55,
    filter_domains TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    canonical_name TEXT,
    entity_type TEXT,
    domains TEXT[],
    properties JSONB,
    source_count INT,
    freshness_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.canonical_name,
        e.entity_type,
        e.domains,
        e.properties,
        e.source_count,
        e.freshness_at,
        (1 - (e.embedding <=> query_embedding))::FLOAT AS similarity
    FROM kg_entities e
    WHERE
        e.embedding IS NOT NULL
        AND (1 - (e.embedding <=> query_embedding)) > match_threshold
        AND (filter_domains IS NULL OR e.domains && filter_domains)
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

- [ ] **Step 2: Verify migration file syntax**

Run: `head -20 supabase/migrations/20260321500000_knowledge_graph.sql`
Expected: File exists, first lines show the comment header and CREATE TABLE

- [ ] **Step 3: Apply migration to local Supabase**

Run: `supabase db push --local`
Expected: Migration applies successfully with no errors

- [ ] **Step 4: Verify tables exist**

Run: `supabase db reset --local` (if push fails, reset rebuilds from all migrations)
Then verify: `psql -h localhost -p 54322 -U postgres -d postgres -c "\dt kg_*"`
Expected: 7 tables listed (kg_entities, kg_aliases, kg_edges, kg_findings, kg_research_log, kg_watch_topics, kg_domain_budgets)

- [ ] **Step 5: Verify seed data**

Run: `psql -h localhost -p 54322 -U postgres -d postgres -c "SELECT domain, monthly_budget, schedule_cron FROM kg_domain_budgets ORDER BY monthly_budget DESC"`
Expected: 10 rows with financial at $80, marketing at $60, etc.

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/20260321500000_knowledge_graph.sql
git commit -m "feat(research): add knowledge graph schema — 7 tables with RLS, indexes, seed data"
```

---

## Task 2: Domain Freshness Config

**Files:**
- Create: `app/agents/research/__init__.py`
- Create: `app/agents/research/config.py`

- [ ] **Step 1: Create package init**

```python
# app/agents/research/__init__.py
"""Research Intelligence System — Knowledge graph and multi-track research."""
```

- [ ] **Step 2: Write failing test for config**

Create `tests/unit/test_research_config.py`:

```python
"""Tests for research domain configuration."""


def test_domain_freshness_has_all_domains():
    """All 10 agent domains must have freshness config."""
    from app.agents.research.config import DOMAIN_FRESHNESS

    expected_domains = {
        "financial", "marketing", "compliance", "sales", "strategic",
        "operations", "hr", "customer_support", "data", "content",
    }
    assert set(DOMAIN_FRESHNESS.keys()) == expected_domains


def test_domain_freshness_values_are_valid():
    """Each domain config must have default_hours, critical_hours, expiry_days."""
    from app.agents.research.config import DOMAIN_FRESHNESS

    for domain, config in DOMAIN_FRESHNESS.items():
        assert "default_hours" in config, f"{domain} missing default_hours"
        assert "critical_hours" in config, f"{domain} missing critical_hours"
        assert "expiry_days" in config, f"{domain} missing expiry_days"
        assert config["critical_hours"] < config["default_hours"], (
            f"{domain}: critical_hours must be < default_hours"
        )
        assert config["default_hours"] < config["expiry_days"] * 24, (
            f"{domain}: default_hours must be < expiry_days in hours"
        )


def test_cache_ttl_for_domain():
    """Cache TTL helper returns correct seconds."""
    from app.agents.research.config import get_cache_ttl_seconds

    ttl = get_cache_ttl_seconds("financial")
    assert ttl == 4 * 3600  # 4 hours in seconds

    ttl = get_cache_ttl_seconds("hr")
    assert ttl == 48 * 3600  # 48 hours in seconds


def test_cache_ttl_unknown_domain_returns_default():
    """Unknown domain returns 24-hour default TTL."""
    from app.agents.research.config import get_cache_ttl_seconds

    ttl = get_cache_ttl_seconds("nonexistent_domain")
    assert ttl == 24 * 3600
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_research_config.py -v`
Expected: FAIL with ModuleNotFoundError or ImportError

- [ ] **Step 4: Write config implementation**

```python
# app/agents/research/config.py
"""Domain-specific configuration for the Research Intelligence System.

Defines freshness thresholds, cache TTLs, and research depth parameters
per agent domain. These values drive the adaptive router and continuous
intelligence scheduler.
"""

from __future__ import annotations

DOMAIN_FRESHNESS: dict[str, dict[str, int | float]] = {
    "financial":        {"default_hours": 4,   "critical_hours": 1,   "expiry_days": 7},
    "marketing":        {"default_hours": 12,  "critical_hours": 4,   "expiry_days": 14},
    "compliance":       {"default_hours": 24,  "critical_hours": 2,   "expiry_days": 30},
    "sales":            {"default_hours": 8,   "critical_hours": 2,   "expiry_days": 7},
    "strategic":        {"default_hours": 12,  "critical_hours": 4,   "expiry_days": 14},
    "operations":       {"default_hours": 24,  "critical_hours": 8,   "expiry_days": 30},
    "hr":               {"default_hours": 48,  "critical_hours": 24,  "expiry_days": 60},
    "customer_support": {"default_hours": 8,   "critical_hours": 2,   "expiry_days": 7},
    "data":             {"default_hours": 12,  "critical_hours": 4,   "expiry_days": 14},
    "content":          {"default_hours": 24,  "critical_hours": 8,   "expiry_days": 30},
}

DEFAULT_FRESHNESS_HOURS = 24


def get_cache_ttl_seconds(domain: str) -> int:
    """Return Redis cache TTL in seconds for a domain's graph_read results.

    Uses the domain's default_hours freshness threshold. Unknown domains
    get a 24-hour default.

    Args:
        domain: Agent domain name (e.g., 'financial', 'hr').

    Returns:
        Cache TTL in seconds.
    """
    config = DOMAIN_FRESHNESS.get(domain)
    if config is None:
        return DEFAULT_FRESHNESS_HOURS * 3600
    return int(config["default_hours"] * 3600)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_research_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/agents/research/__init__.py app/agents/research/config.py tests/unit/test_research_config.py
git commit -m "feat(research): add domain freshness config with cache TTL helpers"
```

---

## Task 3: Graph Service — Read Operations

**Files:**
- Create: `app/services/graph_service.py`
- Create: `tests/unit/test_graph_service.py`

- [ ] **Step 1: Write failing tests for graph_read_entity**

Create `tests/unit/test_graph_service.py`:

```python
"""Tests for the Knowledge Graph service."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.graph_service import GraphService

# Note: tests patch at the method level (_query_by_name, _get_findings, etc.)
# rather than mocking Supabase call chains, for resilience against query refactors.


def _run(coro):
    """Run async code in sync tests."""
    return asyncio.run(coro)


def _mock_supabase():
    """Create a mock Supabase client."""
    client = MagicMock()
    return client


def _mock_cache_service(hit_value=None):
    """Create a mock cache service with optional cache hit."""
    cache = MagicMock()
    if hit_value is not None:
        from app.services.cache import CacheResult
        cache.get_generic = AsyncMock(return_value=CacheResult.hit(hit_value))
    else:
        from app.services.cache import CacheResult
        cache.get_generic = AsyncMock(return_value=CacheResult.miss())
    cache.set_generic = AsyncMock(return_value=True)
    return cache


def test_query_entity_by_name_returns_entity():
    """Exact name match returns entity with findings and relationships."""
    mock_supabase = _mock_supabase()

    entity_data = [{
        "id": "entity-uuid-1",
        "canonical_name": "South African Reserve Bank",
        "entity_type": "institution",
        "domains": ["financial", "compliance"],
        "properties": {"abbreviation": "SARB"},
        "source_count": 14,
        "freshness_at": "2026-03-21T12:00:00Z",
    }]
    findings_data = [{
        "id": "finding-uuid-1",
        "finding_text": "SARB cut repo rate to 7.75%",
        "confidence": 0.95,
        "sources": [{"url": "https://reuters.com/...", "title": "SARB cuts rate"}],
        "freshness_at": "2026-03-21T12:00:00Z",
    }]
    edges_data = [{
        "id": "edge-uuid-1",
        "relationship": "sets_rate",
        "target_name": "Repo Rate",
        "confidence": 0.95,
        "evidence": {"current": "7.75%"},
    }]

    service = GraphService(supabase_client=mock_supabase)

    # Patch at the method level for more resilient tests
    with patch.object(service, "_query_by_name", new_callable=AsyncMock, return_value=entity_data[0]):
        with patch.object(service, "_get_findings", new_callable=AsyncMock, return_value=findings_data):
            with patch.object(service, "_get_relationships", new_callable=AsyncMock, return_value=edges_data):
                result = _run(service.query_entity(
                    query="South African Reserve Bank",
                    domain="financial",
                ))

    assert result["found"] is True
    assert result["entity"]["canonical_name"] == "South African Reserve Bank"
    assert len(result["findings"]) >= 1
    assert result["findings"][0]["finding_text"] == "SARB cut repo rate to 7.75%"


def test_query_entity_not_found_returns_empty():
    """Non-existent entity returns found=False."""
    mock_supabase = _mock_supabase()
    service = GraphService(supabase_client=mock_supabase)

    with patch.object(service, "_query_by_name", new_callable=AsyncMock, return_value=None):
        with patch.object(service, "_query_by_alias", new_callable=AsyncMock, return_value=None):
            result = _run(service.query_entity(query="NonexistentEntity", domain="financial"))

    assert result["found"] is False
    assert result["entity"] is None
    assert result["findings"] == []


def test_query_entity_checks_aliases():
    """Entity lookup falls through to alias table when exact match fails."""
    mock_supabase = _mock_supabase()

    # First query (exact match) returns nothing
    empty_response = MagicMock()
    empty_response.data = []

    # Alias query returns a match
    alias_response = MagicMock()
    alias_response.data = [{"entity_id": "entity-uuid-1"}]

    # Entity by ID returns data
    entity_response = MagicMock()
    entity_response.data = [{
        "id": "entity-uuid-1",
        "canonical_name": "South African Reserve Bank",
        "entity_type": "institution",
        "domains": ["financial"],
        "properties": {},
        "source_count": 5,
        "freshness_at": "2026-03-21T12:00:00Z",
    }]

    service = GraphService(supabase_client=mock_supabase)

    # We test that the alias path is attempted
    with patch.object(service, "_query_by_name", new_callable=AsyncMock, return_value=None):
        with patch.object(service, "_query_by_alias", new_callable=AsyncMock, return_value={
            "id": "entity-uuid-1",
            "canonical_name": "South African Reserve Bank",
            "entity_type": "institution",
            "domains": ["financial"],
            "properties": {},
            "source_count": 5,
            "freshness_at": "2026-03-21T12:00:00Z",
        }):
            with patch.object(service, "_get_findings", new_callable=AsyncMock, return_value=[]):
                with patch.object(service, "_get_relationships", new_callable=AsyncMock, return_value=[]):
                    result = _run(service.query_entity(query="SARB", domain="financial"))

    assert result["found"] is True
    assert result["entity"]["canonical_name"] == "South African Reserve Bank"


def test_check_freshness_returns_stale():
    """Freshness check correctly identifies stale data."""
    from datetime import datetime, timedelta, timezone

    from app.services.graph_service import GraphService

    stale_time = (datetime.now(tz=timezone.utc) - timedelta(hours=10)).isoformat()
    assert GraphService.is_stale(stale_time, threshold_hours=4) is True


def test_check_freshness_returns_fresh():
    """Freshness check correctly identifies fresh data."""
    from datetime import datetime, timedelta, timezone

    from app.services.graph_service import GraphService

    fresh_time = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    assert GraphService.is_stale(fresh_time, threshold_hours=4) is False


def test_query_entity_error_returns_graceful_empty():
    """Database errors return graceful empty result, not exception."""
    mock_supabase = _mock_supabase()
    mock_supabase.table.side_effect = Exception("Connection refused")

    service = GraphService(supabase_client=mock_supabase)
    result = _run(service.query_entity(query="anything", domain="financial"))

    assert result["found"] is False
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_graph_service.py -v`
Expected: FAIL with ImportError (GraphService doesn't exist yet)

- [ ] **Step 3: Write GraphService implementation**

```python
# app/services/graph_service.py
"""Knowledge Graph service for reading and writing structured intelligence.

Provides query methods for entities, relationships, and findings in the
knowledge graph. Handles entity resolution (exact match → alias → semantic)
and freshness checking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class GraphService:
    """Service for querying the knowledge graph stored in Supabase."""

    def __init__(self, supabase_client: Any) -> None:
        """Initialize with a Supabase client.

        Args:
            supabase_client: Supabase client instance (sync or async).
        """
        self._db = supabase_client

    async def query_entity(
        self,
        query: str,
        domain: str,
        include_findings: bool = True,
        include_relationships: bool = True,
        findings_limit: int = 10,
    ) -> dict[str, Any]:
        """Query the knowledge graph for an entity and its context.

        Resolution order: exact canonical_name → alias → (semantic in Phase 2).

        Args:
            query: Entity name or alias to search for.
            domain: Domain to scope findings and relationships.
            include_findings: Whether to fetch related findings.
            include_relationships: Whether to fetch related edges.
            findings_limit: Max findings to return.

        Returns:
            Dict with keys: found, entity, findings, relationships, error.
        """
        try:
            # Step 1: Try exact name match
            entity = await self._query_by_name(query)

            # Step 2: Try alias match
            if entity is None:
                entity = await self._query_by_alias(query)

            if entity is None:
                return {
                    "found": False,
                    "entity": None,
                    "findings": [],
                    "relationships": [],
                    "query": query,
                    "domain": domain,
                }

            findings = []
            relationships = []

            if include_findings:
                findings = await self._get_findings(
                    entity_id=entity["id"],
                    domain=domain,
                    limit=findings_limit,
                )

            if include_relationships:
                relationships = await self._get_relationships(
                    entity_id=entity["id"],
                    domain=domain,
                )

            return {
                "found": True,
                "entity": entity,
                "findings": findings,
                "relationships": relationships,
                "query": query,
                "domain": domain,
            }

        except Exception as e:
            logger.error("Graph query error for '%s' in %s: %s", query, domain, e)
            return {
                "found": False,
                "entity": None,
                "findings": [],
                "relationships": [],
                "query": query,
                "domain": domain,
                "error": str(e),
            }

    async def _query_by_name(self, name: str) -> dict[str, Any] | None:
        """Find entity by exact canonical_name match (case-insensitive)."""
        response = (
            self._db.table("kg_entities")
            .select("*")
            .ilike("canonical_name", name)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None

    async def _query_by_alias(self, alias: str) -> dict[str, Any] | None:
        """Find entity via alias table (case-insensitive)."""
        alias_response = (
            self._db.table("kg_aliases")
            .select("entity_id")
            .ilike("alias", alias)
            .execute()
        )
        if not alias_response.data:
            return None

        entity_id = alias_response.data[0]["entity_id"]
        entity_response = (
            self._db.table("kg_entities")
            .select("*")
            .eq("id", entity_id)
            .execute()
        )
        if entity_response.data:
            return entity_response.data[0]
        return None

    async def _get_findings(
        self,
        entity_id: str,
        domain: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get findings for an entity in a specific domain."""
        response = (
            self._db.table("kg_findings")
            .select("id, finding_text, confidence, sources, contradicts, freshness_at")
            .eq("entity_id", entity_id)
            .eq("domain", domain)
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    async def _get_relationships(
        self,
        entity_id: str,
        domain: str,
    ) -> list[dict[str, Any]]:
        """Get edges from an entity in a specific domain, with target names."""
        response = (
            self._db.table("kg_edges")
            .select("id, relationship, target_id, confidence, evidence, source_url")
            .eq("source_id", entity_id)
            .eq("domain", domain)
            .execute()
        )
        edges = response.data or []
        if not edges:
            return []

        # Batch-resolve target names (avoid N+1 queries)
        target_ids = list({edge["target_id"] for edge in edges})
        targets_resp = (
            self._db.table("kg_entities")
            .select("id, canonical_name")
            .in_("id", target_ids)
            .execute()
        )
        target_map = {
            t["id"]: t["canonical_name"]
            for t in (targets_resp.data or [])
        }
        for edge in edges:
            edge["target_name"] = target_map.get(edge["target_id"], "Unknown")

        return edges

    @staticmethod
    def is_stale(freshness_at: str, threshold_hours: float) -> bool:
        """Check if a timestamp is older than the threshold.

        Args:
            freshness_at: ISO format timestamp string.
            threshold_hours: Maximum age in hours before data is stale.

        Returns:
            True if the data is stale (older than threshold).
        """
        if not freshness_at:
            return True
        try:
            ts = datetime.fromisoformat(freshness_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(tz=timezone.utc) - ts).total_seconds() / 3600
            return age_hours > threshold_hours
        except (ValueError, TypeError):
            return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_graph_service.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/graph_service.py tests/unit/test_graph_service.py
git commit -m "feat(research): add GraphService with entity query, alias resolution, freshness check"
```

---

## Task 3.5: Add Generic Cache Methods to CacheService

**Files:**
- Modify: `app/services/cache.py`

The existing `CacheService` only has domain-specific methods (`get_user_config`, `set_user_config`, etc.). The graph_read tool needs generic get/set methods. Add these following the existing method pattern with `@with_circuit_breaker`.

- [ ] **Step 1: Add `get_generic` and `set_generic` to CacheService**

Add these methods to `app/services/cache.py` inside the `CacheService` class, after the existing `set_user_persona` method:

```python
@with_circuit_breaker
async def get_generic(self, key: str) -> CacheResult:
    """Get a value from cache by arbitrary key.

    Args:
        key: Cache key string.

    Returns:
        CacheResult with the cached value (parsed from JSON) or miss/error.
    """
    raw = await self._redis.get(key)
    if raw is None:
        await self._redis.incr("stats:misses")
        return CacheResult.miss()
    await self._redis.incr("stats:hits")
    try:
        return CacheResult.hit(json.loads(raw))
    except (json.JSONDecodeError, TypeError):
        return CacheResult.hit(raw)

@with_circuit_breaker
async def set_generic(self, key: str, value: Any, ttl: int = 3600) -> bool:
    """Set a value in cache with arbitrary key and TTL.

    Args:
        key: Cache key string.
        value: Value to cache (will be JSON serialized).
        ttl: Time-to-live in seconds (default 1 hour).

    Returns:
        True if set successfully.
    """
    serialized = json.dumps(value, default=str)
    await self._redis.set(key, serialized, ex=ttl)
    return True
```

Also add `import json` and `from typing import Any` to the imports at the top of `cache.py` if not already present.

- [ ] **Step 2: Verify existing tests still pass**

Run: `uv run pytest tests/test_cache_service.py -v`
Expected: All existing tests PASS (new methods don't break anything)

- [ ] **Step 3: Commit**

```bash
git add app/services/cache.py
git commit -m "feat(cache): add generic get/set methods for knowledge graph caching"
```

---

## Task 4: graph_read ADK Tool

**Files:**
- Create: `app/agents/tools/graph_tools.py`
- Create: `tests/unit/test_graph_tools.py`

- [ ] **Step 1: Write failing test for graph_read tool**

Create `tests/unit/test_graph_tools.py`:

```python
"""Tests for graph_read ADK tool."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    """Run async code in sync tests."""
    return asyncio.run(coro)


def test_graph_read_returns_findings_for_known_entity():
    """graph_read returns formatted findings when entity exists in graph."""
    from app.agents.tools.graph_tools import graph_read

    mock_result = {
        "found": True,
        "entity": {
            "canonical_name": "South African Reserve Bank",
            "entity_type": "institution",
            "domains": ["financial"],
            "properties": {"abbreviation": "SARB"},
        },
        "findings": [
            {
                "finding_text": "SARB cut repo rate to 7.75%",
                "confidence": 0.95,
                "sources": [{"url": "https://reuters.com", "title": "SARB"}],
                "freshness_at": "2026-03-21T12:00:00Z",
            }
        ],
        "relationships": [
            {
                "relationship": "sets_rate",
                "target_name": "Repo Rate",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.agents.tools.graph_tools._get_cached_or_query", new_callable=AsyncMock, return_value=mock_result):
        result = graph_read(
            query="South African Reserve Bank",
            domain="financial",
        )

    assert result["success"] is True
    assert result["found"] is True
    assert "SARB cut repo rate" in result["findings"][0]["finding_text"]


def test_graph_read_returns_not_found():
    """graph_read returns success=True but found=False for unknown entities."""
    from app.agents.tools.graph_tools import graph_read

    mock_result = {
        "found": False,
        "entity": None,
        "findings": [],
        "relationships": [],
    }

    with patch("app.agents.tools.graph_tools._get_cached_or_query", new_callable=AsyncMock, return_value=mock_result):
        result = graph_read(query="Nonexistent Corp", domain="financial")

    assert result["success"] is True
    assert result["found"] is False
    assert result["findings"] == []


def test_graph_read_handles_errors_gracefully():
    """graph_read returns success=False on unexpected errors."""
    from app.agents.tools.graph_tools import graph_read

    with patch("app.agents.tools.graph_tools._get_cached_or_query", new_callable=AsyncMock, side_effect=Exception("DB down")):
        result = graph_read(query="anything", domain="financial")

    assert result["success"] is False
    assert "error" in result


def test_graph_tools_exports_list():
    """GRAPH_TOOLS list is exported for agent registration."""
    from app.agents.tools.graph_tools import GRAPH_TOOLS

    assert isinstance(GRAPH_TOOLS, list)
    assert len(GRAPH_TOOLS) == 1
    assert GRAPH_TOOLS[0].__name__ == "graph_read"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_graph_tools.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write graph_read tool implementation**

```python
# app/agents/tools/graph_tools.py
"""Knowledge Graph read tool for ADK agents.

Provides graph_read() — a lightweight synchronous tool added to every
specialized agent that queries the knowledge graph with Redis caching.
No Research Agent involvement; direct Supabase queries only.

Uses synchronous Supabase client (matching existing tool patterns like
briefing_tools.py, invoicing.py). Cache operations use the new
get_generic/set_generic methods on CacheService.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def graph_read(
    query: str,
    domain: str,
    freshness_hours: int | None = None,
) -> dict[str, Any]:
    """Read structured intelligence from the knowledge graph.

    Queries the knowledge graph for entities, their relationships, and
    recent findings. Uses Redis caching for sub-second repeated lookups.
    If the graph has no data for the query, returns found=False.

    This tool does NOT trigger live research. It only reads what is
    already in the graph. For fresh research, delegate to the Research Agent.

    Args:
        query: Entity name, topic, or search term to look up.
        domain: Agent domain for scoping results (e.g., 'financial', 'marketing').
        freshness_hours: Optional override for cache TTL in hours.

    Returns:
        Dictionary with success, found, entity, findings, relationships, and
        optional staleness warning.
    """
    try:
        result = _get_cached_or_query(query, domain, freshness_hours)
    except Exception as e:
        logger.error("graph_read error: %s", e)
        return {
            "success": False,
            "found": False,
            "error": str(e),
            "query": query,
            "domain": domain,
        }

    # Check if data is stale and add warning
    if result.get("found") and result.get("entity"):
        from app.agents.research.config import DOMAIN_FRESHNESS
        from app.services.graph_service import GraphService

        threshold = DOMAIN_FRESHNESS.get(domain, {}).get("default_hours", 24)
        freshness_at = result["entity"].get("freshness_at", "")
        if GraphService.is_stale(freshness_at, threshold):
            result["staleness_warning"] = (
                f"Data is older than {threshold}h threshold for {domain} domain. "
                "Consider delegating to Research Agent for fresh data."
            )

    return {
        "success": True,
        **result,
    }


def _get_cached_or_query(
    query: str,
    domain: str,
    freshness_hours: int | None = None,
) -> dict[str, Any]:
    """Check Redis cache first, then query Supabase synchronously.

    Cache key: kg:read:{domain}:{sha256(query_lower)}
    Cache TTL: domain-specific from config.
    """
    import asyncio

    from app.agents.research.config import get_cache_ttl_seconds
    from app.services.cache import get_cache_service

    cache_key = _make_cache_key(query, domain)
    cache = get_cache_service()

    # Try cache first (cache methods are async, use run_until_complete)
    try:
        loop = asyncio.get_event_loop()
        cached = loop.run_until_complete(cache.get_generic(cache_key))
        if cached.found and cached.value is not None:
            logger.debug("graph_read cache hit: %s", cache_key)
            return cached.value
    except Exception:
        # Cache miss or error — fall through to DB
        pass

    # Query database (Supabase client is synchronous)
    from app.services.graph_service import GraphService

    try:
        from app.services.supabase_client import get_supabase_client

        client = get_supabase_client()
    except Exception:
        return {
            "found": False,
            "entity": None,
            "findings": [],
            "relationships": [],
            "query": query,
            "domain": domain,
            "error": "Database unavailable",
        }

    service = GraphService(supabase_client=client)
    result = service.query_entity_sync(query=query, domain=domain)

    # Cache the result (async, best-effort)
    ttl = (freshness_hours * 3600) if freshness_hours else get_cache_ttl_seconds(domain)
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cache.set_generic(cache_key, result, ttl=ttl))
    except Exception:
        pass  # Cache write failure is non-critical

    return result


def _make_cache_key(query: str, domain: str) -> str:
    """Generate cache key for graph_read queries.

    Args:
        query: Search query string.
        domain: Agent domain.

    Returns:
        Cache key string like 'kg:read:financial:a1b2c3...'.
    """
    query_hash = hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
    return f"kg:read:{domain}:{query_hash}"


# Export for agent tool registration
GRAPH_TOOLS = [graph_read]
```

**Note:** `GraphService` needs a `query_entity_sync` method that wraps the async `query_entity` for use in sync tool context. Add this to the `GraphService` class in Task 3:

```python
def query_entity_sync(self, **kwargs) -> dict[str, Any]:
    """Synchronous wrapper for query_entity (for use in ADK tools)."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.query_entity(**kwargs))
    except RuntimeError:
        return asyncio.run(self.query_entity(**kwargs))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_graph_tools.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/graph_tools.py tests/unit/test_graph_tools.py
git commit -m "feat(research): add graph_read ADK tool with Redis caching"
```

---

## Task 5: Wire graph_read Into All Specialized Agents

**Files:**
- Modify: `app/agents/financial/agent.py` (and all 9 other agent files)

This task adds `GRAPH_TOOLS` to each agent's tool list. The pattern is identical for all 10 agents: import the tools list and spread it into the agent's existing tools.

- [ ] **Step 1: Identify the exact tool list in each agent**

Run for each agent to find their tool list variable name:
```bash
grep -n "tools=" app/agents/financial/agent.py | head -5
grep -n "tools=" app/agents/content/agent.py | head -5
grep -n "tools=" app/agents/strategic/agent.py | head -5
grep -n "tools=" app/agents/sales/agent.py | head -5
grep -n "tools=" app/agents/marketing/agent.py | head -5
grep -n "tools=" app/agents/operations/agent.py | head -5
grep -n "tools=" app/agents/hr/agent.py | head -5
grep -n "tools=" app/agents/compliance/agent.py | head -5
grep -n "tools=" app/agents/customer_support/agent.py | head -5
grep -n "tools=" app/agents/data/agent.py | head -5
```

Each agent uses a `*_AGENT_TOOLS` list variable (e.g., `FINANCIAL_AGENT_TOOLS`). The tool list is defined at module level and passed to the Agent constructor.

- [ ] **Step 2: Add GRAPH_TOOLS import and extend each agent's tool list**

For each of the 10 agent files, add the import and extend the tools list. The pattern for each file:

```python
# Add to imports section:
from app.agents.tools.graph_tools import GRAPH_TOOLS

# Find the *_AGENT_TOOLS list definition and append:
# Before:
FINANCIAL_AGENT_TOOLS = [tool_a, tool_b, ...]
# After:
FINANCIAL_AGENT_TOOLS = [tool_a, tool_b, ..., *GRAPH_TOOLS]
```

Apply this to all 10 files:
- `app/agents/financial/agent.py` — has `FINANCIAL_AGENT_TOOLS` list
- `app/agents/content/agent.py` — **SPECIAL CASE:** No `CONTENT_AGENT_TOOLS` variable. Content agent inlines `sanitize_tools([...])` directly in the `create_content_agent()` factory and singleton constructor. Add `*GRAPH_TOOLS` inside the inline tool list in both the singleton creation and the factory function's `sanitize_tools([...])` call.
- `app/agents/strategic/agent.py` — has `STRATEGIC_AGENT_TOOLS` list
- `app/agents/sales/agent.py` — has `SALES_AGENT_TOOLS` list
- `app/agents/marketing/agent.py` — has `MARKETING_AGENT_TOOLS` list
- `app/agents/operations/agent.py` — has `OPERATIONS_AGENT_TOOLS` list
- `app/agents/hr/agent.py` — has `HR_AGENT_TOOLS` list
- `app/agents/compliance/agent.py` — has `COMPLIANCE_AGENT_TOOLS` list
- `app/agents/customer_support/agent.py` — has `CUSTOMER_SUPPORT_AGENT_TOOLS` list
- `app/agents/data/agent.py` — has `DATA_AGENT_TOOLS` list

- [ ] **Step 3: Verify no import errors**

Run: `uv run python -c "from app.agents.specialized_agents import SPECIALIZED_AGENTS; print(f'{len(SPECIALIZED_AGENTS)} agents loaded')"`
Expected: `10 agents loaded` with no import errors

- [ ] **Step 4: Verify graph_read is in each agent's tool list**

Run: `uv run python -c "
from app.agents.specialized_agents import SPECIALIZED_AGENTS
for agent in SPECIALIZED_AGENTS:
    tools = [t.__name__ if callable(t) else str(t) for t in (agent.tools or [])]
    has_graph = 'graph_read' in tools
    print(f'{agent.name}: graph_read={has_graph}')
"`
Expected: All 10 agents show `graph_read=True`

- [ ] **Step 5: Commit**

```bash
git add app/agents/financial/agent.py app/agents/content/agent.py app/agents/strategic/agent.py app/agents/sales/agent.py app/agents/marketing/agent.py app/agents/operations/agent.py app/agents/hr/agent.py app/agents/compliance/agent.py app/agents/customer_support/agent.py app/agents/data/agent.py
git commit -m "feat(research): wire graph_read tool into all 10 specialized agents"
```

---

## Task 6: Integration Test — Full Stack Verification

**Files:**
- Create: `tests/integration/test_knowledge_graph_migration.py`

- [ ] **Step 1: Write integration test that verifies the full graph read path**

```python
"""Integration tests for the knowledge graph schema and read path.

These tests verify:
1. Migration created all 7 kg_* tables
2. Data can be inserted and queried via GraphService
3. Entity resolution works (exact + alias)
4. Freshness checking works correctly
5. Domain budget seed data exists

Requires: local Supabase running (supabase start).
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import asyncio
import os

import pytest

# Skip entire module if no local Supabase
pytestmark = pytest.mark.integration


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def supabase_client():
    """Get Supabase client for integration tests."""
    try:
        from app.services.supabase_client import get_supabase_client
        return get_supabase_client()
    except Exception:
        pytest.skip("Supabase not available")


def test_kg_tables_exist(supabase_client):
    """All 7 kg_* tables should exist after migration."""
    tables = [
        "kg_entities", "kg_aliases", "kg_edges", "kg_findings",
        "kg_research_log", "kg_watch_topics", "kg_domain_budgets",
    ]
    for table in tables:
        response = supabase_client.table(table).select("*").limit(1).execute()
        # No exception means table exists
        assert response is not None, f"Table {table} should exist"


def test_domain_budgets_seeded(supabase_client):
    """Default domain budgets should be seeded."""
    response = supabase_client.table("kg_domain_budgets").select("domain").execute()
    domains = {row["domain"] for row in response.data}
    assert "financial" in domains
    assert "marketing" in domains
    assert len(domains) == 10


def test_insert_and_query_entity(supabase_client):
    """Can insert an entity and query it back via GraphService."""
    from app.services.graph_service import GraphService

    # Insert test entity
    test_entity = {
        "canonical_name": "Test Corp Integration",
        "entity_type": "company",
        "domains": ["financial"],
        "properties": {"industry": "tech"},
    }
    insert_resp = supabase_client.table("kg_entities").insert(test_entity).execute()
    assert insert_resp.data, "Insert should succeed"
    entity_id = insert_resp.data[0]["id"]

    try:
        # Query via GraphService
        service = GraphService(supabase_client=supabase_client)
        result = _run(service.query_entity(
            query="Test Corp Integration",
            domain="financial",
        ))
        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Test Corp Integration"
    finally:
        # Cleanup
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_alias_resolution(supabase_client):
    """Can resolve entity via alias."""
    from app.services.graph_service import GraphService

    # Insert entity + alias
    entity_resp = supabase_client.table("kg_entities").insert({
        "canonical_name": "Integration Test Bank",
        "entity_type": "institution",
        "domains": ["financial"],
    }).execute()
    entity_id = entity_resp.data[0]["id"]

    alias_resp = supabase_client.table("kg_aliases").insert({
        "entity_id": entity_id,
        "alias": "ITB",
        "source": "test",
    }).execute()

    try:
        service = GraphService(supabase_client=supabase_client)
        result = _run(service.query_entity(query="ITB", domain="financial"))
        assert result["found"] is True
        assert result["entity"]["canonical_name"] == "Integration Test Bank"
    finally:
        supabase_client.table("kg_aliases").delete().eq("entity_id", entity_id).execute()
        supabase_client.table("kg_entities").delete().eq("id", entity_id).execute()


def test_match_kg_entities_rpc(supabase_client):
    """Semantic search RPC function should exist and be callable."""
    # Call with a zero vector — should return empty (no entities have embeddings yet)
    zero_embedding = [0.0] * 768
    response = supabase_client.rpc("match_kg_entities", {
        "query_embedding": zero_embedding,
        "match_count": 5,
        "match_threshold": 0.1,
    }).execute()
    # Function exists and returns (possibly empty) results
    assert isinstance(response.data, list)
```

- [ ] **Step 2: Run integration tests (requires local Supabase)**

Run: `uv run pytest tests/integration/test_knowledge_graph_migration.py -v -m integration`
Expected: All 5 tests PASS (or skip if Supabase not running)

- [ ] **Step 3: Run full test suite to verify no regressions**

Run: `uv run pytest tests/ -v --ignore=tests/integration -x`
Expected: All existing tests still pass

- [ ] **Step 4: Run linter**

Run: `uv run ruff check app/agents/research/ app/services/graph_service.py app/agents/tools/graph_tools.py --fix && uv run ruff format app/agents/research/ app/services/graph_service.py app/agents/tools/graph_tools.py`
Expected: No errors or auto-fixed

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_knowledge_graph_migration.py
git commit -m "test(research): add integration tests for knowledge graph schema and read path"
```

---

## Phase 1 Completion Checklist

After all 6 tasks are done, verify:

- [ ] 7 `kg_*` tables exist in local Supabase with RLS policies and indexes
- [ ] 10 default domain budgets are seeded
- [ ] `match_kg_entities` RPC function works for semantic search
- [ ] `GraphService.query_entity()` resolves entities by name and alias
- [ ] `GraphService.is_stale()` correctly checks freshness
- [ ] `graph_read()` tool works with Redis caching
- [ ] All 10 specialized agents have `graph_read` in their tool list
- [ ] All existing tests still pass
- [ ] Linter passes

**Next phase:** Phase 2 — Research Agent (query planner, track runners, synthesizer, graph writer). This will be a separate plan document.
