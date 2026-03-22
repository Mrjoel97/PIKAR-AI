# Research Intelligence System — Phase 3: Adaptive Router + Interaction Tracking

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the intelligence layer that decides research depth per query (cache-only / quick / standard / deep) and tracks whether research-backed responses perform better — so the self-improvement system can learn which domains benefit from research.

**Architecture:** A new `adaptive_router.py` module determines research depth using a priority-ordered decision chain: self-improvement skills → graph freshness → budget check → heuristic scoring. A Supabase migration extends `interaction_logs` with 5 research tracking columns. The existing `interaction_logger.py` is extended to record research metadata. The Executive Agent instruction is updated to include the Research Agent in its routing guide.

**Tech Stack:** Python, Supabase (ALTER TABLE migration), existing self-improvement engine, existing interaction logger

**Spec:** `docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md` (Section 5: Adaptive Router Component)
**Depends on:** Phase 1 (knowledge graph) + Phase 2 (Research Agent) — must be complete

---

## File Structure

```
NEW FILES:
  supabase/migrations/20260322100000_interaction_logs_research.sql  — ALTER TABLE for research columns
  app/agents/research/tools/adaptive_router.py                      — Depth decision engine
  tests/unit/test_adaptive_router.py                                — Router tests

MODIFIED FILES:
  app/services/interaction_logger.py                                — Add research metadata to log_interaction()
  app/prompts/executive_instruction.txt                             — Add ResearchAgent to routing guide
```

---

## Task 1: Supabase Migration — Interaction Logs Research Columns

**Files:**
- Create: `supabase/migrations/20260322100000_interaction_logs_research.sql`

Adds 5 new columns to the existing `interaction_logs` table for tracking research impact on agent performance.

- [ ] **Step 1: Read the existing interaction_logs migration to understand the table**

Read `supabase/migrations/20260318000000_self_improvement.sql` lines 7-46 to confirm the table structure.

- [ ] **Step 2: Create the migration file**

```sql
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
    ON interaction_logs (agent_id, research_used, research_depth)
    WHERE created_at > now() - INTERVAL '30 days';

-- Comment for documentation
COMMENT ON COLUMN interaction_logs.research_used IS 'Whether research backed this response';
COMMENT ON COLUMN interaction_logs.research_depth IS 'Depth of research: none, cache, quick, standard, deep';
COMMENT ON COLUMN interaction_logs.research_job_id IS 'FK to kg_research_log for cost correlation';
COMMENT ON COLUMN interaction_logs.graph_entities_hit IS 'Number of knowledge graph entities that contributed';
COMMENT ON COLUMN interaction_logs.graph_freshness_avg IS 'Average age in hours of graph data used';
```

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260322100000_interaction_logs_research.sql
git commit -m "feat(research): extend interaction_logs with research tracking columns"
```

---

## Task 2: Adaptive Router

**Files:**
- Create: `app/agents/research/tools/adaptive_router.py`
- Create: `tests/unit/test_adaptive_router.py`

The adaptive router determines research depth for each query using a priority-ordered decision chain.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_adaptive_router.py`:

```python
"""Tests for the adaptive research depth router."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_determine_depth_returns_valid_depth():
    """Router returns a valid ResearchDepth enum value."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="What are interest rates in South Africa?",
        domain="financial",
        agent_id="FIN",
    )

    assert isinstance(result, ResearchDepth)
    assert result in (
        ResearchDepth.CACHE_ONLY,
        ResearchDepth.QUICK,
        ResearchDepth.STANDARD,
        ResearchDepth.DEEP,
    )


def test_fresh_graph_data_returns_cache_only():
    """If graph has fresh data, router returns CACHE_ONLY."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="test query",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=1.0,  # 1 hour old, threshold is 4h for financial
    )

    assert result == ResearchDepth.CACHE_ONLY


def test_stale_graph_data_triggers_research():
    """If graph data is stale, router recommends research."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="What are interest rates in South Africa?",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=10.0,  # 10 hours old, threshold is 4h
    )

    assert result in (ResearchDepth.QUICK, ResearchDepth.STANDARD, ResearchDepth.DEEP)


def test_no_graph_data_triggers_research():
    """If no graph data exists, router recommends research."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    result = determine_depth(
        query="Something never researched before",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=None,  # no data
    )

    assert result != ResearchDepth.CACHE_ONLY


def test_exhausted_budget_returns_cache_only():
    """If domain budget is exhausted, router falls back to CACHE_ONLY."""
    from app.agents.research.tools.adaptive_router import ResearchDepth, determine_depth

    with patch("app.agents.research.tools.adaptive_router._check_budget", return_value=False):
        result = determine_depth(
            query="test",
            domain="financial",
            agent_id="FIN",
            graph_freshness_hours=None,
        )

    assert result == ResearchDepth.CACHE_ONLY


def test_high_priority_domain_gets_deeper_research():
    """Financial domain (high priority) gets deeper research than HR."""
    from app.agents.research.tools.adaptive_router import determine_depth

    financial_depth = determine_depth(
        query="market analysis question",
        domain="financial",
        agent_id="FIN",
        graph_freshness_hours=None,
    )
    hr_depth = determine_depth(
        query="leave policy question",
        domain="hr",
        agent_id="HR",
        graph_freshness_hours=None,
    )

    # Financial should get at least as deep as HR
    assert financial_depth.value >= hr_depth.value


def test_depth_to_string():
    """ResearchDepth enum converts to string for storage."""
    from app.agents.research.tools.adaptive_router import ResearchDepth

    assert ResearchDepth.CACHE_ONLY.name.lower() == "cache_only"
    assert ResearchDepth.DEEP.name.lower() == "deep"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_adaptive_router.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write adaptive router implementation**

```python
# app/agents/research/tools/adaptive_router.py
"""Adaptive research depth router.

Determines the appropriate research depth for each query using a
priority-ordered decision chain:

1. If graph has fresh data → CACHE_ONLY
2. If domain budget exhausted → CACHE_ONLY (fallback)
3. Heuristic scoring based on domain priority + query complexity → depth

In Phase 5, the self-improvement system will generate skills like
"pre_research_investment_queries" and "skip_research_hr_policy" that
override these heuristics. For now, we use domain priority as the
primary signal.
"""

from __future__ import annotations

import enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResearchDepth(enum.IntEnum):
    """Research depth levels, ordered by intensity.

    IntEnum so depths can be compared: DEEP > STANDARD > QUICK > CACHE_ONLY.
    """

    CACHE_ONLY = 0
    QUICK = 1
    STANDARD = 2
    DEEP = 3


# Domain priority scores (higher = more research-intensive)
DOMAIN_PRIORITY: dict[str, float] = {
    "financial": 0.9,
    "compliance": 0.85,
    "strategic": 0.8,
    "sales": 0.7,
    "marketing": 0.7,
    "customer_support": 0.65,
    "data": 0.6,
    "content": 0.5,
    "operations": 0.45,
    "hr": 0.3,
}


def determine_depth(
    query: str,
    domain: str,
    agent_id: str,
    graph_freshness_hours: float | None = None,
) -> ResearchDepth:
    """Determine the appropriate research depth for a query.

    Decision chain (priority order):
    1. If graph data is fresh (within domain threshold) → CACHE_ONLY
    2. If domain budget is exhausted → CACHE_ONLY
    3. Heuristic: domain priority + staleness → QUICK/STANDARD/DEEP

    In Phase 5, self-improvement skills will be checked first:
    - skip_research_* skills → force CACHE_ONLY
    - pre_research_* skills → force minimum depth

    Args:
        query: The research query text.
        domain: Agent domain (e.g., 'financial', 'hr').
        agent_id: Which agent is requesting.
        graph_freshness_hours: Hours since last relevant graph data.
            None means no graph data exists.

    Returns:
        ResearchDepth enum value.
    """
    # Step 1: Check graph freshness
    if graph_freshness_hours is not None:
        from app.agents.research.config import DOMAIN_FRESHNESS

        threshold = DOMAIN_FRESHNESS.get(domain, {}).get("default_hours", 24)
        if graph_freshness_hours <= threshold:
            logger.debug(
                "Graph data fresh (%.1fh <= %dh threshold) for %s — CACHE_ONLY",
                graph_freshness_hours, threshold, domain,
            )
            return ResearchDepth.CACHE_ONLY

    # Step 2: Check budget
    if not _check_budget(domain):
        logger.info("Budget exhausted for %s — falling back to CACHE_ONLY", domain)
        return ResearchDepth.CACHE_ONLY

    # Step 3: Heuristic depth based on domain priority
    priority = DOMAIN_PRIORITY.get(domain, 0.5)

    if priority >= 0.8:
        depth = ResearchDepth.DEEP
    elif priority >= 0.6:
        depth = ResearchDepth.STANDARD
    else:
        depth = ResearchDepth.QUICK

    # Boost depth if no graph data at all (first research on topic)
    if graph_freshness_hours is None and depth.value < ResearchDepth.STANDARD.value:
        depth = ResearchDepth.STANDARD

    logger.debug(
        "Adaptive depth for %s (priority=%.2f, freshness=%s): %s",
        domain, priority, graph_freshness_hours, depth.name,
    )
    return depth


def _check_budget(domain: str) -> bool:
    """Check if the domain has remaining research budget this month.

    Queries kg_domain_budgets and kg_research_log to compare
    spend vs ceiling.

    Args:
        domain: Agent domain.

    Returns:
        True if budget is available, False if exhausted.
    """
    try:
        from app.services.supabase_client import get_supabase_client

        client = get_supabase_client()

        # Get domain budget ceiling
        budget_resp = (
            client.table("kg_domain_budgets")
            .select("monthly_budget, auto_pause, is_active")
            .eq("domain", domain)
            .execute()
        )
        if not budget_resp.data:
            return True  # No budget configured = unlimited
        budget = budget_resp.data[0]
        if not budget.get("is_active"):
            return True  # Inactive = no enforcement

        if not budget.get("auto_pause"):
            return True  # Auto-pause disabled

        ceiling = float(budget["monthly_budget"])

        # Get current month spend
        import datetime

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

        spend_resp = (
            client.table("kg_research_log")
            .select("cost_usd")
            .eq("domain", domain)
            .gte("created_at", month_start)
            .execute()
        )
        total_spend = sum(float(row["cost_usd"]) for row in (spend_resp.data or []))

        return total_spend < ceiling

    except Exception as e:
        logger.warning("Budget check failed for %s (allowing research): %s", domain, e)
        return True  # Fail open — allow research if check fails


# ADK tool export
ADAPTIVE_ROUTER_TOOLS = [determine_depth]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_adaptive_router.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check app/agents/research/tools/adaptive_router.py --fix && uv run ruff format app/agents/research/tools/adaptive_router.py
git add app/agents/research/tools/adaptive_router.py tests/unit/test_adaptive_router.py
git commit -m "feat(research): add adaptive depth router with budget checking"
```

---

## Task 3: Extend Interaction Logger

**Files:**
- Modify: `app/services/interaction_logger.py`

Add research metadata parameters to `log_interaction()` so every agent interaction records whether research was used and at what depth.

- [ ] **Step 1: Read the existing interaction_logger.py**

Read `app/services/interaction_logger.py` to understand the `log_interaction()` method signature and how it builds the insert dict.

- [ ] **Step 2: Extend `log_interaction()` with research parameters**

Add these optional keyword parameters to `log_interaction()`:

```python
async def log_interaction(
    self,
    agent_id: str,
    user_query: str,
    *,
    # ... existing params ...
    agent_response_summary: str | None = None,
    skill_used: str | None = None,
    skill_category: str | None = None,
    session_id: str | None = None,
    response_tokens: int | None = None,
    response_time_ms: int | None = None,
    metadata: dict | None = None,
    # NEW research tracking params:
    research_used: bool = False,
    research_depth: str = "none",
    research_job_id: str | None = None,
    graph_entities_hit: int = 0,
    graph_freshness_avg: float | None = None,
) -> dict | None:
```

In the dict that gets inserted, add:
```python
data = {
    # ... existing fields ...
    "research_used": research_used,
    "research_depth": research_depth,
    "research_job_id": research_job_id,
    "graph_entities_hit": graph_entities_hit,
    "graph_freshness_avg": graph_freshness_avg,
}
```

Only include `research_job_id` and `graph_freshness_avg` in the dict if they are not None (to avoid inserting null UUIDs).

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/ -k "interaction" -v`
Expected: Existing tests still pass (new params have defaults)

- [ ] **Step 4: Lint and commit**

```bash
uv run ruff check app/services/interaction_logger.py --fix && uv run ruff format app/services/interaction_logger.py
git add app/services/interaction_logger.py
git commit -m "feat(research): extend interaction logger with research tracking metadata"
```

---

## Task 4: Update Executive Agent Instruction

**Files:**
- Modify: `app/prompts/executive_instruction.txt`

Add the Research Agent to the ExecutiveAgent's routing guide so it knows when to delegate research queries.

- [ ] **Step 1: Read the executive instruction file**

Read `app/prompts/executive_instruction.txt` to find:
- The "Available Specialists" section (around lines 240-277)
- The "Smart Delegation Guide" matrix
- The delegation rules section

- [ ] **Step 2: Add Research Agent to the specialists list**

In the "Available Specialists" section, add:
```
- ResearchAgent — Research Intelligence specialist. Delegate here for: market intelligence, competitor analysis, regulatory updates, industry trends, any question requiring fresh external data with citations. Uses multi-track parallel research with cross-validation.
```

- [ ] **Step 3: Add Research Agent to the delegation rules**

In the delegation rules section, add a new rule:
```
13. Research queries requiring fresh external data — delegate to ResearchAgent
14. Before giving strategic or financial advice based on external conditions — delegate to ResearchAgent first, then use findings for the specialist's response
```

- [ ] **Step 4: Add to Smart Delegation Guide**

Add a row to the delegation matrix:
```
| External intelligence, market data, competitor info | ResearchAgent | Multi-track research, knowledge graph, citations |
```

- [ ] **Step 5: Commit**

```bash
git add app/prompts/executive_instruction.txt
git commit -m "feat(research): add ResearchAgent to Executive Agent routing guide"
```

---

## Task 5: Wire Adaptive Router Into Research Agent

**Files:**
- Modify: `app/agents/research/agent.py`

Add the adaptive router to the Research Agent's tool list so it can self-determine depth.

- [ ] **Step 1: Read the current agent.py**

Read `app/agents/research/agent.py` to see the current RESEARCH_AGENT_TOOLS list.

- [ ] **Step 2: Add adaptive router import and tools**

```python
from app.agents.research.tools.adaptive_router import ADAPTIVE_ROUTER_TOOLS

RESEARCH_AGENT_TOOLS = [
    *QUERY_PLANNER_TOOLS,
    *TRACK_RUNNER_TOOLS,
    *SYNTHESIZER_TOOLS,
    *GRAPH_WRITER_TOOLS,
    *COST_TRACKER_TOOLS,
    *GRAPH_TOOLS,
    *ADAPTIVE_ROUTER_TOOLS,  # NEW
]
```

- [ ] **Step 3: Run research agent tests**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_research_agent.py -v`
Expected: All pass (new tool adds to the list)

- [ ] **Step 4: Commit**

```bash
git add app/agents/research/agent.py
git commit -m "feat(research): wire adaptive router into Research Agent tools"
```

---

## Task 6: Full Verification

- [ ] **Step 1: Run all research tests**

```bash
uv run pytest tests/unit/test_query_planner.py tests/unit/test_track_runner.py tests/unit/test_synthesizer.py tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py tests/unit/test_research_agent.py tests/unit/test_graph_service.py tests/unit/test_graph_tools.py tests/unit/test_research_config.py tests/unit/test_adaptive_router.py -v
```
Expected: All pass (should be ~50 tests total)

- [ ] **Step 2: Lint all research files**

```bash
uv run ruff check app/agents/research/ app/services/graph_service.py app/agents/tools/graph_tools.py --fix
uv run ruff format app/agents/research/ app/services/graph_service.py app/agents/tools/graph_tools.py
```

- [ ] **Step 3: Verify migration file syntax**

Read `supabase/migrations/20260322100000_interaction_logs_research.sql` to confirm it's valid SQL.

- [ ] **Step 4: Run existing tests for regressions**

```bash
uv run pytest tests/unit/ -v -x --ignore=tests/unit/test_agents.py
```
Expected: No new failures

---

## Phase 3 Completion Checklist

After all 6 tasks are done:

- [ ] `interaction_logs` table has 5 new research tracking columns
- [ ] Adaptive router determines depth: CACHE_ONLY / QUICK / STANDARD / DEEP
- [ ] Router checks graph freshness, budget, and domain priority
- [ ] Budget check queries kg_domain_budgets + kg_research_log
- [ ] Interaction logger records research_used, research_depth, research_job_id, graph_entities_hit, graph_freshness_avg
- [ ] Executive Agent instruction includes ResearchAgent in routing guide
- [ ] Research Agent has adaptive_router in its tool list
- [ ] All existing tests still pass

**Next phase:** Phase 4 — Continuous Intelligence (scheduler + Redis Streams event bus + worker service). This adds background research that keeps the knowledge graph fresh automatically.
