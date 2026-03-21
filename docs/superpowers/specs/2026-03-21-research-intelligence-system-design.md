# Research Intelligence System — Design Spec

**Date:** 2026-03-21
**Status:** Approved
**Priority:** High — Research is the core differentiator for keeping agent intelligence current

## Problem Statement

Pikar-AI's current research capability (`DeepResearchTool` in `app/agents/tools/deep_research.py`) supports multiple research types (deep, quick, market, competitor), generates 3 sequential search queries, scrapes concurrently via `asyncio.gather` with up to 10-15 sources, and includes contradiction detection and confidence scoring. It is a capable single-session research pipeline.

However, it lacks the architectural properties needed for an AI executive system making business-critical recommendations:
- **No persistent knowledge graph** — research results are stored as flat embeddings in the Knowledge Vault but not as structured entities with relationships, freshness tracking, or cross-domain linking
- **No continuous intelligence** — research only happens when explicitly requested; the system has no background refresh or staleness awareness
- **No cross-validation across independent research tracks** — queries run sequentially within a single pipeline rather than as parallel independent tracks that a synthesizer cross-references
- **No adaptive depth** — every research request gets the same pipeline regardless of query importance or existing graph coverage
- **No integration with self-improvement** — research outcomes are not tracked against agent performance, so the system cannot learn which domains benefit most from research

The system needs to evolve into a GSD-style multi-track parallel research architecture with a persistent knowledge graph, continuous intelligence, and a self-improvement flywheel — so every agent gets smarter over time without code changes.

## Goals

1. **Agent-backing research (Priority B):** Every agent automatically researches before making important recommendations, with adaptive depth based on query importance
2. **Continuous intelligence (Priority C):** Background research keeps the knowledge graph fresh per domain cadence + event-driven urgency triggers
3. **User-initiated research (Priority A):** Users can request comprehensive research and receive multi-track, cross-validated reports with citations
4. **Self-improvement flywheel:** Research system and self-improvement system enhance each other — gaps trigger research, research outcomes refine agent behavior
5. **Admin visibility:** Full cost tracking, graph exploration, and scheduler management in the admin panel (not user-facing)

## Non-Goals

- Replacing the existing Knowledge Vault (embeddings table) — the graph supplements it
- Building a dedicated graph database (Neo4j) — Supabase tables with recursive CTEs are sufficient
- Real-time streaming data feeds (e.g., live stock tickers) — the system refreshes on cadence, not real-time
- User-facing research dashboard — cost/graph management is admin-only

## Architecture Overview

### Approach: Research Agent (New ADK Agent)

The codebase currently has 12 agents: 10 specialized domain agents (financial, content, strategic, sales, marketing, operations, hr, compliance, customer_support, data) registered in `SPECIALIZED_AGENTS` list in `specialized_agents.py`, plus admin and reporting agents. The Research Agent becomes the 13th agent.

Unlike admin/reporting which are standalone, the Research Agent is added to the `SPECIALIZED_AGENTS` list so that the ExecutiveAgent can route to it via ADK's native `sub_agents` routing — the same mechanism used for all domain agents. The Research Agent owns the knowledge graph, search pipeline, and continuous intelligence scheduler.

### Agent Invocation Mechanism

Agents interact with the research system at two levels:

1. **`graph_read()` tool (direct, no routing)** — Added to every agent's tool list. Queries the knowledge graph directly via Supabase. Sub-second, no API cost, no inter-agent communication. Used for cached lookups. If data is stale, emits a `stale_entity_accessed` event for background refresh but still returns the stale data immediately.

2. **Research Agent delegation (via ExecutiveAgent routing)** — When an agent needs fresh research (graph data is stale or missing and the query is important), it delegates to the Research Agent through the normal ExecutiveAgent `sub_agents` routing. The agent includes the query, domain context, and requested depth. The Research Agent runs the full pipeline and returns structured findings. This follows the same pattern as e.g. financial agent delegating to compliance agent for regulatory context.

```
Financial Agent                Marketing Agent              Compliance Agent
     |                              |                            |
     +------ "research this" -------+----------------------------+
                                    |
                          +---------------------+
                          |   RESEARCH AGENT    |
                          |                     |
                          | - Query Planner     |
                          | - Track Runners     |
                          | - Synthesizer       |
                          | - Graph Manager     |
                          | - Freshness Loop    |
                          | - Cost Tracker      |
                          +---------------------+
                                    |
                    +-------------------------------+
                    |   FEDERATED KNOWLEDGE GRAPH    |
                    |  (Supabase — 5 new tables)    |
                    +-------------------------------+
```

Every existing agent also gets a lightweight `graph_read()` tool for fast cached lookups that bypass the Research Agent entirely. `graph_read()` uses the existing Redis cache layer (`app/services/cache.py` with circuit breaker) for response caching:
- **Cache key**: `kg:read:{domain}:{sha256(query)}`
- **Cache TTL**: matches domain freshness threshold (e.g., 4 hours for financial, 48 hours for HR)
- **Cache invalidation**: when the Research Agent updates entities/findings for a domain, it invalidates all `kg:read:{domain}:*` keys
- **Circuit breaker**: if Redis is down, `graph_read()` falls back to direct Supabase query (same as existing cache.py pattern)
- **Cache coherence**: since the Research Agent is the only writer, and it invalidates on write, all 10+ agents reading the same entity get consistent data

## Section 1: Research Agent — Internal Architecture

### File Structure

```
app/agents/research/
  agent.py              # create_research_agent() factory
  instructions.py       # Research methodology + domain awareness
  subagents.py          # Track runners (parallel research workers)
  tools/
    query_planner.py      # Decompose question into sub-queries
    track_runner.py       # Execute one research track (search + scrape)
    synthesizer.py        # Cross-validate findings across tracks
    graph_manager.py      # Read/write knowledge graph
    freshness_checker.py  # Check if graph data is fresh enough
    cost_tracker.py       # Log API spend per domain
  config.py             # Domain-specific settings (freshness thresholds, track counts)
```

### Research Flow

When an agent requests research:

1. **Freshness Check** — Query the knowledge graph for existing data on the topic. If data is fresh (within domain-specific threshold), return immediately from graph (< 1 second, no API cost).

2. **Adaptive Depth Decision** — Heuristics (refined by self-improvement skills) determine depth:
   - Domain priority (financial = HIGH, HR = LOW)
   - Query complexity (multi-entity = deeper)
   - Time since last research on topic
   - Budget remaining for domain this month
   - Depth levels: QUICK (1 search, no scrape), STANDARD (3 tracks, top 3 scrapes), DEEP (5 tracks, top 5 scrapes + contrarian analysis)

3. **Query Decomposition** — Break the original question into focused sub-queries, one per track. Track types (GSD-inspired):
   - **Primary** — Direct answer to the query (GSD: FEATURES.md)
   - **Context** — Background/conditions around the topic (GSD: ARCHITECTURE.md)
   - **Contrarian** — Opposing views, alternative data, edge cases (GSD: PITFALLS.md)
   - **Impact** — Practical implications for the user (GSD: SUMMARY.md)
   - **Risk** — Uncertainty factors, what could go wrong (GSD: PITFALLS.md)
   - **Historical** — Trend data, how this has changed over time (GSD: STACK.md)

4. **Parallel Track Execution** — All tracks run concurrently via async tasks. Each track: Tavily search → score results → Firecrawl scrape top URLs → extract findings.

5. **Synthesis** — Cross-validate facts across tracks. Identify agreements (HIGH confidence), contradictions (flagged with reason), and gaps. Score source authority per finding. Calculate overall confidence.

6. **Graph Update** — Upsert entities and edges, attach findings with citations and freshness timestamps, embed chunks for semantic retrieval, log cost to kg_research_log.

### Confidence Scoring (Enhanced)

This replaces the existing single-pipeline formula in `deep_research.py` (which weights source_score 0.4, scrape_score 0.25, search_health 0.2, scrape_health 0.15 with a flat 0.08 contradiction penalty). The new formula is designed for multi-track research where cross-track agreement is the strongest quality signal:

```
track_agreement = (findings confirmed across 2+ tracks) / total_findings
source_quality  = avg(tavily_score) across all tracks
freshness       = max(0.0, 1.0 - (hours_since_newest_source / 168))  # decays over 1 week, floored at 0
contradiction_penalty = min(1.0, contradictions_found * 0.05)  # capped at 1.0

confidence = (
    track_agreement   * 0.35 +
    source_quality    * 0.30 +
    freshness         * 0.20 +
    (1.0 - contradiction_penalty) * 0.15
)
```

For QUICK research (single track), `track_agreement` defaults to 0.5 (neutral) since cross-validation is not possible.

## Section 2: Federated Knowledge Graph Schema

### Tables

Five new tables in Supabase, alongside the existing `embeddings` table:

**`kg_entities`** — Graph nodes (companies, people, regulations, markets, topics, metrics, countries, technologies, institutions)
- `id` UUID PK
- `canonical_name` TEXT NOT NULL
- `entity_type` TEXT NOT NULL
- `domains` TEXT[] (e.g., ['financial', 'compliance'])
- `properties` JSONB (flexible key-value per entity type)
- `embedding` VECTOR(768) (for semantic entity search)
- `source_count` INT (how many sources confirm this entity)
- `freshness_at` TIMESTAMPTZ
- UNIQUE(canonical_name, entity_type)

**`kg_aliases`** — Entity resolution (multiple names map to one entity)
- `id` UUID PK
- `entity_id` UUID FK → kg_entities
- `alias` TEXT
- `source` TEXT
- `confidence` FLOAT
- UNIQUE(alias, entity_id)

**`kg_edges`** — Relationships between entities
- `id` UUID PK
- `source_id` UUID FK → kg_entities
- `target_id` UUID FK → kg_entities
- `relationship` TEXT (sets_rate, regulates, competes_with, operates_in, etc.)
- `domain` TEXT
- `confidence` FLOAT
- `evidence` JSONB
- `source_url` TEXT
- `freshness_at` TIMESTAMPTZ
- UNIQUE(source_id, target_id, relationship, domain)

**`kg_findings`** — Research findings attached to entities or edges
- `id` UUID PK
- `entity_id` UUID FK → kg_entities (nullable)
- `edge_id` UUID FK → kg_edges (nullable)
- `domain` TEXT NOT NULL
- `finding_text` TEXT NOT NULL
- `confidence` FLOAT
- `sources` JSONB (array of {url, title, retrieved_at, score})
- `contradicts` JSONB (array of {finding_id, reason})
- `embedding` VECTOR(768)
- `freshness_at` TIMESTAMPTZ
- `expires_at` TIMESTAMPTZ (domain-specific TTL)
- CHECK(entity_id IS NOT NULL OR edge_id IS NOT NULL)

**`kg_research_log`** — Cost tracking and audit trail (powers admin dashboard)
- `id` UUID PK
- `domain` TEXT NOT NULL
- `query` TEXT NOT NULL
- `depth` TEXT (quick, standard, deep)
- `tracks_run` INT
- `searches_used` INT
- `scrapes_used` INT
- `cost_usd` DECIMAL(10,4)
- `findings_count` INT
- `graph_updates` INT
- `triggered_by` TEXT (agent_request, scheduled, event, user_initiated)
- `requesting_agent` TEXT
- `user_id` UUID
- `duration_ms` INT
- `created_at` TIMESTAMPTZ DEFAULT now() NOT NULL
- `updated_at` TIMESTAMPTZ DEFAULT now() NOT NULL

### RLS Policies and Indexes

All `kg_*` tables will include:
- RLS enabled with service_role bypass (matching existing pattern in `20260318000000_self_improvement.sql`)
- `created_at` and `updated_at` columns with DEFAULT now()
- Indexes on foreign keys and frequently queried columns:
  - `kg_entities`: index on `(canonical_name, entity_type)`, GIN index on `domains`, HNSW index on `embedding`
  - `kg_aliases`: index on `(alias)` for fast entity resolution lookups
  - `kg_edges`: index on `(source_id, domain)`, index on `(target_id, domain)`
  - `kg_findings`: index on `(entity_id, domain)`, index on `(edge_id, domain)`, index on `(freshness_at)`, HNSW index on `embedding`
  - `kg_research_log`: index on `(domain, created_at)`, index on `(triggered_by, created_at)`
  - `kg_watch_topics`: index on `(domain, is_active)`
  - `kg_domain_budgets`: index on `(domain)`

### Multi-Tenancy

The knowledge graph is a **shared global graph** — entities and findings are not scoped to individual users. This is intentional: market data, competitor intelligence, and regulatory information are the same regardless of which user asks. The `kg_research_log` table includes a `user_id` column to track who triggered research, but the graph data itself is shared. If per-tenant isolation is needed in the future, `kg_findings` can be extended with a `user_id` column and RLS policies.

### Migration Strategy

All schema changes require Supabase migrations in `supabase/migrations/`:
- Phase 1 migration: creates all 7 `kg_*` tables (entities, aliases, edges, findings, research_log, watch_topics, domain_budgets) with RLS policies and indexes
- Phase 3 migration: ALTERs `interaction_logs` to add research tracking columns (`research_used`, `research_depth`, `research_job_id`, `graph_entities_hit`, `graph_freshness_avg`). The `research_job_id` FK requires `kg_research_log` to exist first, so this runs after Phase 1.

### Domain-Wide Findings

Findings that don't attach to a specific entity (e.g., "AI regulation is accelerating globally") are stored by creating a topic-type entity in `kg_entities` (entity_type='topic', canonical_name='AI regulation trends') and attaching the finding to it. This avoids needing a special "free-floating" finding pattern.

### Entity Resolution

When research encounters a name:
1. Exact match on `kg_entities.canonical_name` → resolved
2. Exact match on `kg_aliases.alias` → resolved to entity_id
3. Semantic search on entity embedding → similarity > 0.75: same entity (add alias automatically), 0.55-0.75: candidate match (add alias with confidence < 1.0, log for admin review), < 0.55: new entity. Threshold is lower than typical semantic search (0.85) because entity names like "SARB" vs "South African Reserve Bank" have very different embeddings despite being the same entity — the alias table + exact matching handles most cases, semantic search is the fallback

### Freshness Thresholds Per Domain

| Domain | Default (hours) | Critical (hours) | Expiry (days) |
|--------|----------------|-------------------|---------------|
| Financial | 4 | 1 | 7 |
| Marketing | 12 | 4 | 14 |
| Compliance | 24 | 2 | 30 |
| Sales | 8 | 2 | 7 |
| Strategic | 12 | 4 | 14 |
| Operations | 24 | 8 | 30 |
| HR | 48 | 24 | 60 |
| Customer | 8 | 2 | 7 |
| Data | 12 | 4 | 14 |
| Content | 24 | 8 | 30 |

### Relationship to Existing Knowledge Vault

The knowledge graph does NOT replace the existing `embeddings` table:
- **Knowledge Vault** (existing): Stores raw research reports, brain dumps, documents as chunked embeddings. Query pattern: "Find content similar to this text."
- **Knowledge Graph** (new): Stores structured entities, relationships, and scored findings. Query pattern: "What do we know about X? How does X relate to Y?"

Research results are written to BOTH: Knowledge Vault gets the full report as chunks (backward compatible), Knowledge Graph gets extracted entities, edges, and findings (new structured intelligence).

## Section 3: Continuous Intelligence — Scheduler + Event System

### Hybrid Model

Two engines working together:
- **Scheduler**: Maintains baseline freshness per domain on a configurable cadence
- **Event Bus**: Triggers immediate research when important events occur

### Domain Schedules (Default, Admin-Configurable)

| Domain | Cadence | Rationale |
|--------|---------|-----------|
| Financial | Daily | Markets move fast |
| Marketing | 3x/week (Mon/Wed/Fri) | Campaign cycles |
| Sales | 2x/week (Mon/Thu) | Pipeline cadence |
| Compliance | Weekly (Monday) | Regulations change slowly |
| Customer | 2x/week (Tue/Fri) | Support trends |
| Strategic | 2x/week (Tue/Fri) | Competitive landscape |
| Content | Weekly (Wednesday) | Content trends |
| Operations | Weekly (Friday) | Process changes |
| HR | Biweekly (Monday) | Policy changes are rare |
| Data | Weekly (Thursday) | Tool/platform updates |

### Scheduled Research Job Flow

When a scheduled job fires:
1. Find stale high-value entities in this domain (ordered by source_count — most-referenced first)
2. Check domain-specific watch topics (admin-configurable per deployment)
3. Check self-improvement coverage gaps for this domain
4. Build prioritized, deduplicated research queue
5. Execute research within domain budget ceiling

### Watch Topics

Admin-managed topics per domain that the scheduler always keeps fresh. Stored in `kg_watch_topics` table, editable via admin panel. Examples:
- Financial: "SARB interest rate", "ZAR/USD exchange rate", "JSE performance"
- Compliance: "POPIA enforcement actions", "GDPR latest rulings", "AI regulation updates"
- Marketing: "competitor brand campaigns", "social media algorithm changes"

### Event Bus

Uses **Redis Streams** (new capability built on existing Redis infrastructure). Redis Streams is chosen over Redis pub/sub because Streams provide message persistence and consumer groups — if the intelligence worker is temporarily down, messages queue up and are processed when it restarts (pub/sub is fire-and-forget and would lose messages). The Redis instance is already running; Streams is a built-in Redis data structure requiring no new infrastructure.

Six event trigger types:

1. **coverage_gap_detected** — Self-improvement identifies knowledge gap → deep research on gap topic
2. **low_confidence_response** — Agent answers with confidence < 0.5 → standard research
3. **stale_entity_accessed** — graph_read returns expired data → quick refresh (return stale data immediately, refresh in background)
4. **user_feedback_negative** — User flags response as wrong → deep research to correct graph
5. **external_webhook** — News API, regulatory feed, market alert → domain-specific deep research
6. **cross_domain_signal** — Entity updated in one domain, stale in others → refresh affected domains

### Dedup and Rate Protection

| Event Type | Dedup Window | Rationale |
|-----------|-------------|-----------|
| coverage_gap | 24 hours | Same gap researched once/day max |
| low_confidence | 4 hours | Same topic refreshed once per 4h |
| stale_access | 1 hour | Quick refresh at most hourly |
| user_feedback | 1 hour | User corrections get fast response |
| external_webhook | 2 hours | External signals deduped per 2h |
| cross_domain | 8 hours | Cross-domain propagation is slower |

Global limits: max 3 concurrent research jobs, event queue max 50 (drop low-priority when exceeded).

### Background Worker

Runs as a separate service (same codebase, different entrypoint):

```yaml
# Docker Compose addition
services:
  intelligence-worker:
    build: .
    command: uv run python -m app.services.intelligence_worker
    depends_on: [redis]
    environment:
      WORKER_MODE: intelligence
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health/worker"]
      interval: 30s
      timeout: 10s
      retries: 3
```

The worker exposes a lightweight health endpoint at port 8001 for Docker healthcheck and admin panel worker status display.

## Section 4: Admin Panel — Cost Dashboard + Research Management

### Location

New "Research Intelligence" section in the v3.0 Admin Panel. NOT visible to regular users.

### Four Tabs

**Tab 1: Overview**
- KPI cards: Research jobs today, graph size (entities/edges/findings), freshness score (% of entities within threshold), cost MTD vs budget
- Domain health table: per-domain freshness bar, finding count, last research timestamp
- Recent events feed: last 20 events with trigger type, domain, topic

**Tab 2: Costs**
- Monthly budget bar (spend vs ceiling with projection)
- Cost breakdown by service (Tavily, Firecrawl, embeddings, Supabase)
- Cost breakdown by trigger type (agent-backing, scheduled, event-driven, user-initiated)
- Cost by domain table (budget, spent, searches, scrapes, avg depth)
- Daily cost trend chart (last 14 days)

**Tab 3: Graph Explorer**
- Entity search (semantic + exact)
- Entity detail view: properties, aliases, relationships, recent findings, contradictions
- Actions: Force Refresh, Edit Entity, Merge With, Delete

**Tab 4: Scheduler Management**
- Domain schedule table (cadence, next run, status, toggle on/off)
- Watch topics CRUD per domain (add/edit/remove topics with priority)
- Event bus status (queue depth, active research count, events processed/deduped/dropped today)
- Budget controls (per-domain ceiling, alert threshold, auto-pause toggle, fallback mode)
- Research history log with CSV export

### Additional Tables

**`kg_watch_topics`** — Admin-managed watch topics
- id, domain, topic, priority (critical/high/medium/low), is_active, last_researched_at, created_by, created_at, updated_at
- UNIQUE(domain, topic)

**`kg_domain_budgets`** — Budget configuration per domain
- id, domain (UNIQUE), monthly_budget, alert_threshold (default 0.8), auto_pause (default true), schedule_cron, schedule_tz, is_active, created_at, updated_at

### API Endpoints

```
GET    /admin/research/overview
GET    /admin/research/costs
GET    /admin/research/costs/daily
GET    /admin/research/graph/stats
GET    /admin/research/graph/entity/:id
POST   /admin/research/graph/search
POST   /admin/research/graph/refresh
DELETE /admin/research/graph/entity/:id
GET    /admin/research/scheduler
PUT    /admin/research/scheduler/:domain
GET    /admin/research/watch-topics
POST   /admin/research/watch-topics
PUT    /admin/research/watch-topics/:id
DELETE /admin/research/watch-topics/:id
GET    /admin/research/budgets
PUT    /admin/research/budgets/:domain
GET    /admin/research/events
GET    /admin/research/history
GET    /admin/research/history/export
```

## Section 5: Self-Improvement Flywheel Integration

### Connection 1: Self-Improvement → Research

When the existing self-improvement evaluation loop detects a coverage gap, it emits a research event via the event bus. The Research Agent receives the event and runs deep research on the gap topic, updating the knowledge graph. The next time an agent encounters a similar query, graph_read returns fresh data.

### Connection 2: Research → Self-Improvement

Every agent interaction is tagged with research metadata (new columns on interaction_logs, added via Phase 3 migration):
- `research_used` BOOLEAN DEFAULT false
- `research_depth` TEXT DEFAULT 'none' ('none', 'cache', 'quick', 'standard', 'deep')
- `research_job_id` UUID FK → kg_research_log (nullable)
- `graph_entities_hit` INT DEFAULT 0
- `graph_freshness_avg` FLOAT (nullable)

Note: The self-improvement system's `coverage_gaps` table uses `resolved_by_skill` (not `resolved_by`) per the schema in `20260318000000_self_improvement.sql`. The research event emission code must use this exact column name when checking for unresolved gaps.

The self-improvement evaluation loop now compares scores between research-backed and non-research responses, per domain and per query type. When evidence shows research significantly improves a query type, it generates a skill like "pre_research_investment_queries" that tells the adaptive router to always research before those queries. When evidence shows research doesn't help (e.g., HR policy questions), it generates a "skip_research" skill that saves API budget.

### Adaptive Router Component

The adaptive router is a module at `app/agents/research/tools/adaptive_router.py` that determines research depth for each incoming query. It exposes a single function:

```python
async def determine_research_depth(
    query: str,
    domain: str,
    agent_id: str,
    graph_freshness: float | None,  # hours since last relevant graph data
) -> ResearchDepth:  # enum: CACHE_ONLY, QUICK, STANDARD, DEEP
```

Decision logic (in priority order):
1. If agent has a `skip_research_*` skill for this query type → CACHE_ONLY
2. If agent has a `pre_research_*` skill for this query type → use skill's recommended depth
3. If graph has fresh data (within domain threshold) → CACHE_ONLY
4. If domain budget is exhausted → CACHE_ONLY (fallback mode)
5. Heuristic scoring: domain priority + query complexity + staleness → QUICK/STANDARD/DEEP

The router reads agent skills from the `agent_skills` table at decision time, so self-improvement-generated skills take effect immediately without code changes.

### Flywheel Health (Admin Panel Addition)

Added to the Overview tab:
- Research impact table: per-domain comparison of with-research vs without-research avg scores, delta, and status (HIGH/MED/LOW/SKIP)
- Generated research skills list (from self-improvement)
- Coverage gap → resolution metrics (gaps detected, research triggered, gaps resolved, avg resolution time)

## Cost Estimates

### Monthly Totals by Scenario

| Scenario | Searches | Scrapes | Est. Cost |
|----------|----------|---------|-----------|
| Early stage (few users) | ~3K | ~1.5K | $80 – $150/mo |
| Growth (moderate usage) | ~14K | ~6K | $200 – $435/mo |
| Scale (500+ interactions/day) | ~40K | ~15K | $600 – $1,200/mo |

### Built-In Cost Controls
- Dedup windows per event type (1-24 hours)
- Domain budget ceilings with auto-pause
- Smart scrape gating (only scrape URLs above relevance threshold)
- Budget alert at configurable threshold (default 80%)
- Fallback to graph-only mode when budget exhausted

## Build Phases

| Phase | Scope | Dependency |
|-------|-------|-----------|
| Phase 1 | Knowledge Graph schema + `graph_read` tool on all agents | Foundation — everything reads/writes the graph |
| Phase 2 | Research Agent (query planner + track runners + synthesizer + graph writer) | Phase 1 — needs graph to write to |
| Phase 3 | Adaptive router + interaction_log extension | Phase 2 — needs Research Agent operational |
| Phase 4 | Continuous Intelligence (scheduler + event bus + worker) | Phase 2 — needs Research Agent to execute jobs |
| Phase 5 | Self-improvement flywheel integration | Phases 3+4 — needs research metadata + event bus |
| Phase 6 | Admin panel (cost dashboard + graph explorer + scheduler management) | Phase 4 — needs data to display |

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph storage | Supabase (new tables) | No new infrastructure, team already knows it, recursive CTEs handle graph queries |
| Agent pattern | 13th ADK agent (added to SPECIALIZED_AGENTS) | Follows existing factory pattern, routable via ExecutiveAgent, gets own self-improvement loop |
| Event bus | Redis Streams | Already running Redis, Streams provide message persistence + consumer groups (pub/sub would lose messages if worker is down) |
| Background worker | Separate Docker service, same codebase | Clean process isolation, shared code, independent scaling |
| Embedding model | text-embedding-004 (768 dims) | Already used in Knowledge Vault, consistent dimensions |
| Search API | Tavily (existing) | Already integrated, good AI-powered ranking |
| Scrape API | Firecrawl (existing) | Already integrated, handles JS rendering |
| Cost approach | Quality-first with budget guardrails | Fresh data is the product differentiator, but with admin-controlled ceilings |
