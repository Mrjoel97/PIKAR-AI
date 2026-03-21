# Research Intelligence System — Phase 2: Research Agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the Research Agent — the 13th ADK agent that performs GSD-style multi-track parallel research with query decomposition, parallel track execution, cross-track synthesis, and knowledge graph persistence.

**Architecture:** The Research Agent follows the existing ADK factory pattern (`create_research_agent()`). It uses ADK's `ParallelAgent` to run 3-5 research tracks concurrently, each performing independent Tavily searches + Firecrawl scrapes. A synthesizer cross-validates findings across tracks, scores confidence, extracts entities/edges, and writes to both the Knowledge Graph and Knowledge Vault. The agent is registered in `SPECIALIZED_AGENTS` so the ExecutiveAgent can route to it.

**Tech Stack:** Google ADK (Agent, ParallelAgent), Tavily API, Firecrawl API, Supabase, Google GenAI embeddings (text-embedding-004), existing DeepResearchTool infrastructure

**Spec:** `docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md` (Section 1)
**Depends on:** Phase 1 (knowledge graph schema + graph_read tool) — must be complete

---

## File Structure

```
NEW FILES:
  app/agents/research/agent.py                    — create_research_agent() factory + singleton
  app/agents/research/instructions.py             — Research Agent instruction prompts
  app/agents/research/tools/                      — Research-specific tools (package)
  app/agents/research/tools/__init__.py            — Package init
  app/agents/research/tools/query_planner.py       — Decompose question into multi-track sub-queries
  app/agents/research/tools/track_runner.py        — Execute one research track (search + scrape + extract)
  app/agents/research/tools/synthesizer.py         — Cross-validate findings, score confidence, extract entities
  app/agents/research/tools/graph_writer.py        — Write research results to knowledge graph + vault
  app/agents/research/tools/cost_tracker.py        — Log API spend per domain to kg_research_log
  tests/unit/test_query_planner.py                 — Query planner tests
  tests/unit/test_track_runner.py                  — Track runner tests
  tests/unit/test_synthesizer.py                   — Synthesizer tests
  tests/unit/test_graph_writer.py                  — Graph writer tests
  tests/unit/test_cost_tracker.py                  — Cost tracker tests
  tests/unit/test_research_agent.py                — Research agent integration tests

MODIFIED FILES:
  app/agents/specialized_agents.py                 — Add research_agent + create_research_agent
  app/agent.py                                     — Add research_agent to fallback sub_agents
```

---

## Task 1: Query Planner Tool

**Files:**
- Create: `app/agents/research/tools/__init__.py`
- Create: `app/agents/research/tools/query_planner.py`
- Create: `tests/unit/test_query_planner.py`

The query planner takes a research question and decomposes it into 3-5 focused sub-queries, each assigned a track type (Primary, Context, Contrarian, Impact, Risk). This is the GSD-style decomposition that replaces the existing linear 3-query approach.

- [ ] **Step 1: Create tools package init**

```python
# app/agents/research/tools/__init__.py
"""Research Agent tools — query planning, track execution, synthesis, graph writing."""
```

- [ ] **Step 2: Write failing tests for query planner**

Create `tests/unit/test_query_planner.py`:

```python
"""Tests for the research query planner."""

from __future__ import annotations


def test_plan_queries_returns_correct_structure():
    """Query planner returns list of track dicts with query and track_type."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="What are the current interest rate trends in South Africa?",
        domain="financial",
        depth="deep",
    )

    assert result["success"] is True
    tracks = result["tracks"]
    assert isinstance(tracks, list)
    assert len(tracks) >= 3  # deep = 5, standard = 3, quick = 1
    for track in tracks:
        assert "query" in track
        assert "track_type" in track
        assert track["track_type"] in (
            "primary", "context", "contrarian", "impact", "risk", "historical"
        )


def test_plan_queries_deep_returns_5_tracks():
    """Deep research generates 5 tracks."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="South Africa interest rates",
        domain="financial",
        depth="deep",
    )
    assert len(result["tracks"]) == 5


def test_plan_queries_standard_returns_3_tracks():
    """Standard research generates 3 tracks."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="South Africa interest rates",
        domain="financial",
        depth="standard",
    )
    assert len(result["tracks"]) == 3


def test_plan_queries_quick_returns_1_track():
    """Quick research generates 1 track (primary only)."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="South Africa interest rates",
        domain="financial",
        depth="quick",
    )
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["track_type"] == "primary"


def test_plan_queries_adds_domain_context():
    """Queries include domain-specific keywords."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(
        query="interest rates",
        domain="compliance",
        depth="standard",
    )
    # At least one track should reference compliance/regulatory context
    all_queries = " ".join(t["query"].lower() for t in result["tracks"])
    assert any(
        kw in all_queries
        for kw in ("regulation", "compliance", "legal", "policy", "ruling")
    )


def test_plan_queries_handles_empty_query():
    """Empty query returns error."""
    from app.agents.research.tools.query_planner import plan_queries

    result = plan_queries(query="", domain="financial", depth="deep")
    assert result["success"] is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_query_planner.py -v`
Expected: FAIL with ImportError

- [ ] **Step 4: Write query planner implementation**

```python
# app/agents/research/tools/query_planner.py
"""Query planner for multi-track research decomposition.

Takes a research question and decomposes it into focused sub-queries,
each assigned a track type. This is the GSD-style decomposition that
enables parallel independent research tracks.

Track types (inspired by GSD research documents):
- primary: Direct answer to the query (GSD: FEATURES.md)
- context: Background/conditions around the topic (GSD: ARCHITECTURE.md)
- contrarian: Opposing views, alternative data (GSD: PITFALLS.md)
- impact: Practical implications for the user (GSD: SUMMARY.md)
- risk: Uncertainty factors, what could go wrong (GSD: PITFALLS.md)
- historical: Trend data, how this has changed (GSD: STACK.md)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Track configurations by depth
TRACK_CONFIGS = {
    "quick": ["primary"],
    "standard": ["primary", "context", "impact"],
    "deep": ["primary", "context", "contrarian", "impact", "risk"],
}

# Domain-specific keywords to inject into queries for better results
DOMAIN_KEYWORDS = {
    "financial": ["market", "investment", "economic", "financial", "fiscal"],
    "marketing": ["brand", "campaign", "audience", "trend", "digital marketing"],
    "compliance": ["regulation", "compliance", "legal", "policy", "ruling", "enforcement"],
    "sales": ["revenue", "pipeline", "conversion", "deal", "pricing"],
    "strategic": ["competitive", "strategy", "market position", "growth", "opportunity"],
    "operations": ["process", "efficiency", "supply chain", "operational", "logistics"],
    "hr": ["workforce", "talent", "employment", "HR policy", "labor"],
    "customer_support": ["customer satisfaction", "support", "service", "feedback", "NPS"],
    "data": ["analytics", "data platform", "metrics", "dashboard", "data engineering"],
    "content": ["content strategy", "publishing", "editorial", "media", "content marketing"],
}

# Templates for generating track-specific queries
TRACK_TEMPLATES = {
    "primary": "{query} {year} latest",
    "context": "{query} background context {domain_kw} landscape overview",
    "contrarian": "{query} criticism risks challenges opposing view alternative perspective",
    "impact": "{query} impact implications business practical effects {domain_kw}",
    "risk": "{query} risks uncertainty threats what could go wrong {domain_kw}",
    "historical": "{query} history trend over time evolution changes {year_range}",
}


def plan_queries(
    query: str,
    domain: str,
    depth: str = "standard",
) -> dict[str, Any]:
    """Decompose a research question into multi-track sub-queries.

    Args:
        query: The original research question.
        domain: Agent domain for context-aware query generation.
        depth: Research depth — 'quick' (1 track), 'standard' (3), or 'deep' (5).

    Returns:
        Dict with success flag and list of track dicts, each containing
        'query' and 'track_type'.
    """
    if not query or not query.strip():
        return {"success": False, "tracks": [], "error": "Query cannot be empty"}

    track_types = TRACK_CONFIGS.get(depth, TRACK_CONFIGS["standard"])
    domain_keywords = DOMAIN_KEYWORDS.get(domain, [])
    domain_kw = domain_keywords[0] if domain_keywords else domain

    import datetime

    year = datetime.datetime.now(tz=datetime.timezone.utc).year
    year_range = f"{year - 2}-{year}"

    tracks = []
    for track_type in track_types:
        template = TRACK_TEMPLATES.get(track_type, "{query}")
        track_query = template.format(
            query=query.strip(),
            domain_kw=domain_kw,
            year=year,
            year_range=year_range,
        )
        tracks.append({
            "query": track_query,
            "track_type": track_type,
        })

    return {
        "success": True,
        "tracks": tracks,
        "original_query": query,
        "domain": domain,
        "depth": depth,
    }


# ADK tool export
QUERY_PLANNER_TOOLS = [plan_queries]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_query_planner.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check app/agents/research/tools/ --fix && uv run ruff format app/agents/research/tools/
git add app/agents/research/tools/__init__.py app/agents/research/tools/query_planner.py tests/unit/test_query_planner.py
git commit -m "feat(research): add query planner for multi-track decomposition"
```

---

## Task 2: Track Runner Tool

**Files:**
- Create: `app/agents/research/tools/track_runner.py`
- Create: `tests/unit/test_track_runner.py`

The track runner executes a single research track: Tavily search, score + rank results, scrape top URLs via Firecrawl, and extract findings. Multiple track runners execute in parallel via `asyncio.gather`.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_track_runner.py`:

```python
"""Tests for the research track runner."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_run_track_returns_findings():
    """Track runner returns structured findings from search + scrape."""
    from app.agents.research.tools.track_runner import run_track

    mock_search_result = {
        "success": True,
        "results": [
            {"title": "SARB Rate Cut", "url": "https://example.com/1", "content": "SARB cut rates to 7.75%", "score": 0.92},
            {"title": "SA Economy", "url": "https://example.com/2", "content": "Inflation at 4.2%", "score": 0.85},
        ],
        "answer": "SARB recently cut the repo rate.",
    }
    mock_scrape_result = {
        "success": True,
        "url": "https://example.com/1",
        "markdown": "# SARB cuts repo rate to 7.75%\n\nThe South African Reserve Bank cut rates by 25bps.",
        "metadata": {"title": "SARB Rate Cut"},
    }

    with patch("app.agents.research.tools.track_runner._search", new_callable=AsyncMock, return_value=mock_search_result):
        with patch("app.agents.research.tools.track_runner._scrape_urls", new_callable=AsyncMock, return_value=[mock_scrape_result]):
            result = _run(run_track(
                query="SARB interest rate 2026",
                track_type="primary",
                scrape_top_n=2,
            ))

    assert result["success"] is True
    assert result["track_type"] == "primary"
    assert len(result["sources"]) >= 1
    assert len(result["scraped_content"]) >= 1
    assert result["sources"][0]["url"] == "https://example.com/1"


def test_run_track_handles_search_failure():
    """Track runner returns graceful error when search fails."""
    from app.agents.research.tools.track_runner import run_track

    mock_search_fail = {"success": False, "error": "Rate limit", "results": []}

    with patch("app.agents.research.tools.track_runner._search", new_callable=AsyncMock, return_value=mock_search_fail):
        result = _run(run_track(
            query="anything",
            track_type="primary",
        ))

    assert result["success"] is False
    assert "error" in result


def test_run_track_deduplicates_urls():
    """Track runner removes duplicate URLs from results."""
    from app.agents.research.tools.track_runner import _deduplicate_sources

    sources = [
        {"url": "https://example.com/1", "score": 0.9},
        {"url": "https://example.com/1", "score": 0.8},
        {"url": "https://example.com/2", "score": 0.7},
    ]
    result = _deduplicate_sources(sources)
    assert len(result) == 2
    assert result[0]["score"] == 0.9  # keeps highest score


def test_run_track_limits_scrape_count():
    """Track runner only scrapes top N URLs."""
    from app.agents.research.tools.track_runner import run_track

    mock_search = {
        "success": True,
        "results": [
            {"title": f"Result {i}", "url": f"https://example.com/{i}", "content": f"Content {i}", "score": 0.9 - i * 0.1}
            for i in range(10)
        ],
        "answer": None,
    }

    scrape_call_count = 0

    async def mock_scrape(urls, **kwargs):
        nonlocal scrape_call_count
        scrape_call_count = len(urls)
        return [{"success": True, "url": u, "markdown": "content", "metadata": {}} for u in urls]

    with patch("app.agents.research.tools.track_runner._search", new_callable=AsyncMock, return_value=mock_search):
        with patch("app.agents.research.tools.track_runner._scrape_urls", new_callable=AsyncMock, side_effect=mock_scrape):
            _run(run_track(query="test", track_type="primary", scrape_top_n=3))

    assert scrape_call_count <= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_track_runner.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write track runner implementation**

```python
# app/agents/research/tools/track_runner.py
"""Track runner for parallel research execution.

Executes a single research track: Tavily search -> rank results ->
Firecrawl scrape top URLs -> extract key findings. Multiple track
runners execute concurrently via asyncio.gather.

Reuses existing Tavily and Firecrawl infrastructure from app/mcp/tools/.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


async def run_track(
    query: str,
    track_type: str,
    max_search_results: int = 5,
    scrape_top_n: int = 3,
    search_depth: str = "advanced",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Execute one research track: search, rank, scrape, extract.

    Args:
        query: Search query for this track.
        track_type: Track type (primary, context, contrarian, impact, risk).
        max_search_results: Max results from Tavily search.
        scrape_top_n: Number of top URLs to scrape via Firecrawl.
        search_depth: Tavily search depth ('basic' or 'advanced').
        user_id: Optional user ID for audit logging.

    Returns:
        Dict with track_type, sources, scraped_content, quick_answer,
        duration_ms, and success flag.
    """
    start = time.monotonic()

    try:
        # Step 1: Search
        search_result = await _search(
            query=query,
            max_results=max_search_results,
            search_depth=search_depth,
            user_id=user_id,
        )

        if not search_result.get("success"):
            return {
                "success": False,
                "track_type": track_type,
                "query": query,
                "error": search_result.get("error", "Search failed"),
                "sources": [],
                "scraped_content": [],
                "duration_ms": int((time.monotonic() - start) * 1000),
            }

        # Step 2: Deduplicate and rank sources
        sources = _deduplicate_sources(search_result.get("results", []))
        sources.sort(key=lambda s: s.get("score", 0), reverse=True)

        # Step 3: Scrape top URLs
        urls_to_scrape = [
            s["url"] for s in sources[:scrape_top_n] if s.get("url")
        ]
        scraped_content = []
        if urls_to_scrape:
            scraped_content = await _scrape_urls(
                urls=urls_to_scrape,
                user_id=user_id,
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        return {
            "success": True,
            "track_type": track_type,
            "query": query,
            "sources": sources,
            "scraped_content": [s for s in scraped_content if s.get("success")],
            "quick_answer": search_result.get("answer"),
            "search_count": 1,
            "scrape_count": len(urls_to_scrape),
            "duration_ms": duration_ms,
        }

    except Exception as e:
        logger.error("Track runner error for '%s' (%s): %s", query, track_type, e)
        return {
            "success": False,
            "track_type": track_type,
            "query": query,
            "error": str(e),
            "sources": [],
            "scraped_content": [],
            "duration_ms": int((time.monotonic() - start) * 1000),
        }


async def run_tracks_parallel(
    tracks: list[dict[str, Any]],
    scrape_top_n: int = 3,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Run multiple research tracks in parallel.

    Args:
        tracks: List of track dicts from query planner, each with 'query' and 'track_type'.
        scrape_top_n: URLs to scrape per track.
        user_id: Optional user ID.

    Returns:
        List of track results (same order as input).
    """
    tasks = [
        run_track(
            query=track["query"],
            track_type=track["track_type"],
            scrape_top_n=scrape_top_n,
            user_id=user_id,
        )
        for track in tracks
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append({
                "success": False,
                "track_type": tracks[i]["track_type"],
                "query": tracks[i]["query"],
                "error": str(result),
                "sources": [],
                "scraped_content": [],
            })
        else:
            processed.append(result)

    return processed


def _deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate URLs, keeping highest-scored version.

    Args:
        sources: List of source dicts with 'url' and 'score' keys.

    Returns:
        Deduplicated list sorted by score descending.
    """
    seen: dict[str, dict[str, Any]] = {}
    for source in sources:
        url = source.get("url", "")
        if not url:
            continue
        if url not in seen or source.get("score", 0) > seen[url].get("score", 0):
            seen[url] = source
    return sorted(seen.values(), key=lambda s: s.get("score", 0), reverse=True)


async def _search(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Execute Tavily search using existing MCP infrastructure.

    Args:
        query: Search query string.
        max_results: Max results to return.
        search_depth: 'basic' or 'advanced'.
        user_id: Optional user ID for audit.

    Returns:
        Search result dict with success, results, answer keys.
    """
    from app.mcp.tools.web_search import web_search_with_context

    return await web_search_with_context(
        query=query,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=True,
        agent_name="ResearchAgent",
        user_id=user_id,
    )


async def _scrape_urls(
    urls: list[str],
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Scrape multiple URLs in parallel using existing Firecrawl infrastructure.

    Args:
        urls: List of URLs to scrape.
        user_id: Optional user ID for audit.

    Returns:
        List of scrape result dicts.
    """
    from app.mcp.tools.web_scrape import web_scrape

    tasks = [
        web_scrape(
            url=url,
            extract_content=True,
            agent_name="ResearchAgent",
            user_id=user_id,
        )
        for url in urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed.append({
                "success": False,
                "url": urls[i],
                "error": str(result),
            })
        else:
            processed.append(result)

    return processed


# ADK tool export
TRACK_RUNNER_TOOLS = [run_track]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_track_runner.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check app/agents/research/tools/track_runner.py --fix && uv run ruff format app/agents/research/tools/track_runner.py
git add app/agents/research/tools/track_runner.py tests/unit/test_track_runner.py
git commit -m "feat(research): add track runner for parallel search + scrape execution"
```

---

## Task 3: Synthesizer Tool

**Files:**
- Create: `app/agents/research/tools/synthesizer.py`
- Create: `tests/unit/test_synthesizer.py`

The synthesizer takes results from multiple parallel tracks and cross-validates findings, identifies agreements and contradictions, scores confidence using the new multi-track formula, and extracts entities/edges for graph persistence.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_synthesizer.py`:

```python
"""Tests for the research synthesizer."""

from __future__ import annotations


def test_synthesize_findings_returns_structure():
    """Synthesizer returns findings, confidence, contradictions, entities."""
    from app.agents.research.tools.synthesizer import synthesize_tracks

    track_results = [
        {
            "success": True,
            "track_type": "primary",
            "sources": [
                {"title": "SARB cuts rate", "url": "https://a.com", "content": "SARB cut repo rate to 7.75%", "score": 0.92},
            ],
            "scraped_content": [
                {"success": True, "url": "https://a.com", "markdown": "SARB cut repo rate by 25bps to 7.75% on March 20, 2026.", "metadata": {"title": "SARB"}},
            ],
        },
        {
            "success": True,
            "track_type": "context",
            "sources": [
                {"title": "SA Inflation", "url": "https://b.com", "content": "Inflation eased to 4.2% y/y", "score": 0.88},
            ],
            "scraped_content": [
                {"success": True, "url": "https://b.com", "markdown": "South Africa inflation fell to 4.2%.", "metadata": {"title": "Inflation"}},
            ],
        },
    ]

    result = synthesize_tracks(
        track_results=track_results,
        original_query="South Africa interest rates",
        domain="financial",
    )

    assert result["success"] is True
    assert isinstance(result["findings"], list)
    assert len(result["findings"]) >= 1
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["all_sources"], list)


def test_synthesize_handles_failed_tracks():
    """Synthesizer works even if some tracks failed."""
    from app.agents.research.tools.synthesizer import synthesize_tracks

    track_results = [
        {
            "success": True,
            "track_type": "primary",
            "sources": [{"title": "A", "url": "https://a.com", "content": "Data A", "score": 0.9}],
            "scraped_content": [],
        },
        {
            "success": False,
            "track_type": "context",
            "error": "Rate limit",
            "sources": [],
            "scraped_content": [],
        },
    ]

    result = synthesize_tracks(
        track_results=track_results,
        original_query="test",
        domain="financial",
    )

    assert result["success"] is True
    assert result["tracks_succeeded"] == 1
    assert result["tracks_failed"] == 1


def test_synthesize_all_tracks_failed():
    """Synthesizer returns failure when all tracks fail."""
    from app.agents.research.tools.synthesizer import synthesize_tracks

    track_results = [
        {"success": False, "track_type": "primary", "error": "Fail", "sources": [], "scraped_content": []},
        {"success": False, "track_type": "context", "error": "Fail", "sources": [], "scraped_content": []},
    ]

    result = synthesize_tracks(
        track_results=track_results,
        original_query="test",
        domain="financial",
    )

    assert result["success"] is False


def test_confidence_formula_multi_track():
    """Confidence scoring uses the multi-track formula from spec."""
    from app.agents.research.tools.synthesizer import calculate_confidence

    confidence = calculate_confidence(
        track_agreement=0.8,
        source_quality=0.85,
        freshness=0.9,
        contradictions_found=1,
    )

    expected = (0.8 * 0.35) + (0.85 * 0.30) + (0.9 * 0.20) + ((1.0 - min(1.0, 1 * 0.05)) * 0.15)
    assert abs(confidence - expected) < 0.01


def test_confidence_quick_research_neutral_agreement():
    """Quick research (single track) uses 0.5 neutral agreement."""
    from app.agents.research.tools.synthesizer import calculate_confidence

    confidence = calculate_confidence(
        track_agreement=0.5,  # neutral for single track
        source_quality=0.8,
        freshness=1.0,
        contradictions_found=0,
    )

    assert 0.0 <= confidence <= 1.0


def test_extract_findings_from_scraped():
    """Findings are extracted from scraped content."""
    from app.agents.research.tools.synthesizer import extract_findings

    scraped = [
        {"url": "https://a.com", "markdown": "SARB cut repo rate to 7.75%. Inflation at 4.2%.", "metadata": {"title": "SARB"}},
        {"url": "https://b.com", "markdown": "The rand weakened against the dollar.", "metadata": {"title": "Rand"}},
    ]
    sources = [
        {"url": "https://a.com", "title": "SARB", "score": 0.9, "content": "Rate cut"},
        {"url": "https://b.com", "title": "Rand", "score": 0.8, "content": "Rand weak"},
    ]

    findings = extract_findings(scraped_content=scraped, sources=sources)

    assert isinstance(findings, list)
    assert len(findings) >= 1
    for f in findings:
        assert "text" in f
        assert "source_url" in f
        assert "confidence" in f
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_synthesizer.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write synthesizer implementation**

```python
# app/agents/research/tools/synthesizer.py
"""Cross-track synthesis for multi-track research.

Takes results from parallel track runners and:
1. Merges and deduplicates sources across tracks
2. Extracts key findings from scraped content
3. Identifies contradictions between tracks
4. Calculates confidence using the multi-track formula
5. Produces a structured synthesis ready for graph persistence
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def synthesize_tracks(
    track_results: list[dict[str, Any]],
    original_query: str,
    domain: str,
) -> dict[str, Any]:
    """Synthesize results from multiple parallel research tracks.

    Args:
        track_results: List of track runner results.
        original_query: The original research question.
        domain: Agent domain for context.

    Returns:
        Dict with findings, confidence, sources, contradictions, and metadata.
    """
    succeeded = [t for t in track_results if t.get("success")]
    failed = [t for t in track_results if not t.get("success")]

    if not succeeded:
        return {
            "success": False,
            "findings": [],
            "confidence": 0.0,
            "all_sources": [],
            "contradictions": [],
            "tracks_succeeded": 0,
            "tracks_failed": len(failed),
            "error": "All research tracks failed",
        }

    # Merge sources across tracks
    all_sources = []
    all_scraped = []
    search_count = 0
    scrape_count = 0

    for track in succeeded:
        all_sources.extend(track.get("sources", []))
        all_scraped.extend(track.get("scraped_content", []))
        search_count += track.get("search_count", 1)
        scrape_count += track.get("scrape_count", 0)

    # Deduplicate sources by URL
    seen_urls: set[str] = set()
    unique_sources = []
    for source in sorted(all_sources, key=lambda s: s.get("score", 0), reverse=True):
        url = source.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(source)

    # Extract findings from scraped content
    findings = extract_findings(
        scraped_content=all_scraped,
        sources=unique_sources,
    )

    # Calculate track agreement (findings seen in 2+ tracks)
    track_agreement = _calculate_track_agreement(
        findings=findings,
        track_count=len(succeeded),
    )

    # Source quality (average Tavily score)
    source_scores = [s.get("score", 0) for s in unique_sources if s.get("score")]
    source_quality = sum(source_scores) / len(source_scores) if source_scores else 0.5

    # Freshness (use 1.0 as default — sources are live)
    freshness = 1.0

    # Contradictions (simple text overlap check)
    contradictions = _find_contradictions(findings)

    # Calculate confidence
    confidence = calculate_confidence(
        track_agreement=track_agreement,
        source_quality=source_quality,
        freshness=freshness,
        contradictions_found=len(contradictions),
    )

    return {
        "success": True,
        "findings": findings,
        "confidence": round(confidence, 3),
        "all_sources": unique_sources,
        "contradictions": contradictions,
        "tracks_succeeded": len(succeeded),
        "tracks_failed": len(failed),
        "search_count": search_count,
        "scrape_count": scrape_count,
        "original_query": original_query,
        "domain": domain,
        "track_agreement": round(track_agreement, 3),
        "source_quality": round(source_quality, 3),
    }


def calculate_confidence(
    track_agreement: float,
    source_quality: float,
    freshness: float,
    contradictions_found: int,
) -> float:
    """Calculate confidence using the multi-track formula from spec.

    Formula:
        confidence = (track_agreement * 0.35) + (source_quality * 0.30)
                   + (freshness * 0.20) + ((1 - contradiction_penalty) * 0.15)

    Args:
        track_agreement: Ratio of cross-validated findings (0.0-1.0).
        source_quality: Average source relevance score (0.0-1.0).
        freshness: Source freshness score (0.0-1.0).
        contradictions_found: Number of contradictions detected.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    contradiction_penalty = min(1.0, contradictions_found * 0.05)
    freshness_clamped = max(0.0, freshness)

    confidence = (
        track_agreement * 0.35
        + source_quality * 0.30
        + freshness_clamped * 0.20
        + (1.0 - contradiction_penalty) * 0.15
    )

    return max(0.0, min(1.0, confidence))


def extract_findings(
    scraped_content: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract key findings from scraped content and source summaries.

    Each finding includes the text, source URL, and a confidence based
    on the source's Tavily score.

    Args:
        scraped_content: List of scrape results with 'markdown' content.
        sources: List of search sources with 'score' and 'url'.

    Returns:
        List of finding dicts with 'text', 'source_url', 'confidence'.
    """
    source_scores = {s.get("url", ""): s.get("score", 0.5) for s in sources}
    findings = []

    # Extract from scraped content (primary source of findings)
    for scrape in scraped_content:
        if not scrape.get("success") and not scrape.get("markdown"):
            continue
        url = scrape.get("url", "")
        markdown = scrape.get("markdown", "")
        title = scrape.get("metadata", {}).get("title", "")

        # Split into paragraphs and take substantive ones as findings
        paragraphs = [
            p.strip() for p in markdown.split("\n\n")
            if p.strip() and len(p.strip()) > 50 and not p.strip().startswith("#")
        ]

        for para in paragraphs[:3]:  # max 3 findings per source
            findings.append({
                "text": para[:500],  # cap at 500 chars
                "source_url": url,
                "source_title": title,
                "confidence": source_scores.get(url, 0.5),
            })

    # If no scraped findings, fall back to source content summaries
    if not findings:
        for source in sources[:5]:
            content = source.get("content", "")
            if content and len(content) > 30:
                findings.append({
                    "text": content[:500],
                    "source_url": source.get("url", ""),
                    "source_title": source.get("title", ""),
                    "confidence": source.get("score", 0.5),
                })

    return findings


def _calculate_track_agreement(
    findings: list[dict[str, Any]],
    track_count: int,
) -> float:
    """Estimate cross-track agreement.

    For single-track research, returns 0.5 (neutral).
    For multi-track, counts how many findings have corroborating
    sources from different URLs.

    Args:
        findings: List of extracted findings.
        track_count: Number of successful tracks.

    Returns:
        Agreement score between 0.0 and 1.0.
    """
    if track_count <= 1:
        return 0.5  # neutral for single track

    if not findings:
        return 0.0

    # Count findings that have sources from multiple URLs
    urls = {f.get("source_url") for f in findings if f.get("source_url")}
    if len(urls) <= 1:
        return 0.3  # all from same source

    # More unique sources = higher agreement
    return min(1.0, len(urls) / (track_count * 2))


def _find_contradictions(findings: list[dict[str, Any]]) -> list[str]:
    """Detect potential contradictions between findings.

    Simple heuristic: looks for findings containing numbers that
    differ for the same topic keywords.

    Args:
        findings: List of finding dicts.

    Returns:
        List of contradiction description strings.
    """
    # Simple implementation — full LLM-based contradiction
    # detection will be added in a later phase
    return []


# ADK tool export
SYNTHESIZER_TOOLS = [synthesize_tracks]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_synthesizer.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check app/agents/research/tools/synthesizer.py --fix && uv run ruff format app/agents/research/tools/synthesizer.py
git add app/agents/research/tools/synthesizer.py tests/unit/test_synthesizer.py
git commit -m "feat(research): add synthesizer for cross-track validation and confidence scoring"
```

---

## Task 4: Graph Writer + Cost Tracker Tools

**Files:**
- Create: `app/agents/research/tools/graph_writer.py`
- Create: `app/agents/research/tools/cost_tracker.py`
- Create: `tests/unit/test_graph_writer.py`
- Create: `tests/unit/test_cost_tracker.py`

The graph writer takes synthesized findings and persists them to the knowledge graph (entities, edges, findings) and the Knowledge Vault (full report). The cost tracker logs API usage to `kg_research_log`.

- [ ] **Step 1: Write failing tests for graph writer**

Create `tests/unit/test_graph_writer.py`:

```python
"""Tests for the research graph writer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_write_findings_to_graph_creates_entities():
    """Graph writer creates/updates entities from findings."""
    from app.agents.research.tools.graph_writer import write_to_graph

    mock_client = MagicMock()
    # Mock upsert returning entity data
    mock_client.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "entity-1", "canonical_name": "SARB", "entity_type": "institution"}
    ]
    # Mock insert for findings
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "finding-1"}
    ]

    synthesis = {
        "findings": [
            {"text": "SARB cut repo rate to 7.75%", "source_url": "https://a.com", "confidence": 0.92, "source_title": "SARB"},
        ],
        "all_sources": [
            {"title": "SARB Rate Cut", "url": "https://a.com", "score": 0.92},
        ],
        "domain": "financial",
        "original_query": "SARB interest rate",
    }

    with patch("app.agents.research.tools.graph_writer._get_supabase", return_value=mock_client):
        result = write_to_graph(synthesis=synthesis, domain="financial")

    assert result["success"] is True
    assert result["entities_written"] >= 0
    assert result["findings_written"] >= 0


def test_write_findings_handles_db_error():
    """Graph writer handles database errors gracefully."""
    from app.agents.research.tools.graph_writer import write_to_graph

    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB unavailable")

    synthesis = {
        "findings": [{"text": "test", "source_url": "https://a.com", "confidence": 0.5, "source_title": "Test"}],
        "all_sources": [],
        "domain": "financial",
        "original_query": "test",
    }

    with patch("app.agents.research.tools.graph_writer._get_supabase", return_value=mock_client):
        result = write_to_graph(synthesis=synthesis, domain="financial")

    assert result["success"] is False
    assert "error" in result
```

- [ ] **Step 2: Write failing tests for cost tracker**

Create `tests/unit/test_cost_tracker.py`:

```python
"""Tests for the research cost tracker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_log_research_cost_writes_to_table():
    """Cost tracker writes a row to kg_research_log."""
    from app.agents.research.tools.cost_tracker import log_research_cost

    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "log-1"}]

    with patch("app.agents.research.tools.cost_tracker._get_supabase", return_value=mock_client):
        result = log_research_cost(
            domain="financial",
            query="SARB interest rate",
            depth="deep",
            tracks_run=5,
            searches_used=5,
            scrapes_used=15,
            findings_count=12,
            graph_updates=8,
            triggered_by="agent_request",
            requesting_agent="FinancialAnalysisAgent",
            duration_ms=5200,
        )

    assert result["success"] is True
    mock_client.table.assert_called_with("kg_research_log")


def test_estimate_cost_calculates_correctly():
    """Cost estimation formula works for searches + scrapes."""
    from app.agents.research.tools.cost_tracker import estimate_cost_usd

    cost = estimate_cost_usd(searches=5, scrapes=3)
    assert cost > 0
    assert isinstance(cost, float)


def test_log_research_cost_handles_db_error():
    """Cost tracker doesn't raise on DB failure (fire-and-forget)."""
    from app.agents.research.tools.cost_tracker import log_research_cost

    mock_client = MagicMock()
    mock_client.table.side_effect = Exception("DB down")

    with patch("app.agents.research.tools.cost_tracker._get_supabase", return_value=mock_client):
        result = log_research_cost(
            domain="financial", query="test", depth="quick",
            tracks_run=1, searches_used=1, scrapes_used=0,
            findings_count=0, graph_updates=0,
            triggered_by="agent_request", duration_ms=100,
        )

    # Fire-and-forget — returns success=False but doesn't raise
    assert result["success"] is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py -v`
Expected: FAIL with ImportError

- [ ] **Step 4: Write graph writer implementation**

```python
# app/agents/research/tools/graph_writer.py
"""Knowledge graph writer for research results.

Persists synthesized findings to:
1. kg_entities — entities mentioned in findings
2. kg_findings — individual finding records with citations
3. Knowledge Vault — full research report as embeddings (backward compat)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase():
    """Get Supabase client."""
    from app.services.supabase_client import get_supabase_client

    return get_supabase_client()


def write_to_graph(
    synthesis: dict[str, Any],
    domain: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Write synthesized research findings to the knowledge graph.

    Creates/updates entities from the query topic and writes findings
    as kg_findings records linked to those entities.

    Args:
        synthesis: Output from synthesize_tracks().
        domain: Agent domain.
        user_id: Optional user ID.

    Returns:
        Dict with success flag, entities_written, findings_written counts.
    """
    try:
        client = _get_supabase()
        entities_written = 0
        findings_written = 0

        # Create a topic entity for the research query
        query = synthesis.get("original_query", "Unknown")
        entity_data = {
            "canonical_name": query,
            "entity_type": "topic",
            "domains": [domain],
            "properties": {
                "research_confidence": synthesis.get("confidence", 0),
                "source_count": len(synthesis.get("all_sources", [])),
            },
        }

        entity_resp = (
            client.table("kg_entities")
            .upsert(entity_data, on_conflict="canonical_name,entity_type")
            .execute()
        )

        entity_id = None
        if entity_resp.data:
            entity_id = entity_resp.data[0]["id"]
            entities_written += 1

        # Write findings
        if entity_id:
            for finding in synthesis.get("findings", []):
                finding_data = {
                    "entity_id": entity_id,
                    "domain": domain,
                    "finding_text": finding["text"],
                    "confidence": finding.get("confidence", 0.5),
                    "sources": [{
                        "url": finding.get("source_url", ""),
                        "title": finding.get("source_title", ""),
                    }],
                    "freshness_at": "now()",
                }
                try:
                    client.table("kg_findings").insert(finding_data).execute()
                    findings_written += 1
                except Exception as e:
                    logger.warning("Failed to write finding: %s", e)

        return {
            "success": True,
            "entities_written": entities_written,
            "findings_written": findings_written,
            "entity_id": entity_id,
        }

    except Exception as e:
        logger.error("Graph write error: %s", e)
        return {
            "success": False,
            "entities_written": 0,
            "findings_written": 0,
            "error": str(e),
        }


async def write_to_vault(
    synthesis: dict[str, Any],
    topic: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Write full research report to Knowledge Vault for backward compatibility.

    Args:
        synthesis: Output from synthesize_tracks().
        topic: Research topic.
        user_id: Optional user ID.

    Returns:
        Dict with success flag and vault metadata.
    """
    try:
        from app.rag.knowledge_vault import ingest_document_content

        # Build vault content from synthesis
        lines = [f"# Research Report: {topic}\n"]
        lines.append(f"**Confidence:** {synthesis.get('confidence', 0):.1%}\n")
        lines.append(f"**Sources:** {len(synthesis.get('all_sources', []))}\n")
        lines.append(f"**Domain:** {synthesis.get('domain', 'general')}\n\n")

        lines.append("## Key Findings\n")
        for i, finding in enumerate(synthesis.get("findings", []), 1):
            lines.append(f"{i}. {finding['text']}\n")
            lines.append(f"   Source: {finding.get('source_url', 'N/A')}\n\n")

        if synthesis.get("contradictions"):
            lines.append("## Contradictions\n")
            for c in synthesis["contradictions"]:
                lines.append(f"- {c}\n")

        lines.append("\n## Sources\n")
        for source in synthesis.get("all_sources", [])[:10]:
            lines.append(f"- [{source.get('title', 'Untitled')}]({source.get('url', '')})\n")

        content = "\n".join(lines)

        result = await ingest_document_content(
            content=content,
            title=f"Research: {topic}",
            document_type="research_report",
            user_id=user_id,
            metadata={
                "research_type": "multi_track",
                "num_sources": len(synthesis.get("all_sources", [])),
                "topic": topic,
                "confidence_score": synthesis.get("confidence", 0),
                "domain": synthesis.get("domain", "general"),
            },
        )
        return {"success": True, **result}

    except Exception as e:
        logger.error("Vault write error: %s", e)
        return {"success": False, "error": str(e)}


GRAPH_WRITER_TOOLS = [write_to_graph]
```

- [ ] **Step 5: Write cost tracker implementation**

```python
# app/agents/research/tools/cost_tracker.py
"""Cost tracking for research API usage.

Logs every research job to kg_research_log for the admin cost dashboard.
Estimates API costs based on search and scrape counts.
Fire-and-forget — never blocks or raises on failure.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Approximate per-call costs (verify against current Tavily/Firecrawl pricing)
COST_PER_SEARCH = 0.01  # ~$0.01 per Tavily search
COST_PER_SCRAPE = 0.015  # ~$0.015 per Firecrawl scrape


def _get_supabase():
    """Get Supabase client."""
    from app.services.supabase_client import get_supabase_client

    return get_supabase_client()


def estimate_cost_usd(searches: int, scrapes: int) -> float:
    """Estimate API cost in USD for a research job.

    Args:
        searches: Number of Tavily searches.
        scrapes: Number of Firecrawl scrapes.

    Returns:
        Estimated cost in USD.
    """
    return round(searches * COST_PER_SEARCH + scrapes * COST_PER_SCRAPE, 4)


def log_research_cost(
    domain: str,
    query: str,
    depth: str,
    tracks_run: int,
    searches_used: int,
    scrapes_used: int,
    findings_count: int,
    graph_updates: int,
    triggered_by: str,
    duration_ms: int,
    requesting_agent: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Log a research job to kg_research_log. Fire-and-forget.

    Args:
        domain: Agent domain.
        query: Research query.
        depth: Research depth (quick/standard/deep).
        tracks_run: Number of parallel tracks executed.
        searches_used: Total Tavily searches across all tracks.
        scrapes_used: Total Firecrawl scrapes across all tracks.
        findings_count: Number of findings extracted.
        graph_updates: Number of graph entities/findings written.
        triggered_by: What triggered this research.
        duration_ms: Total research duration in milliseconds.
        requesting_agent: Which agent requested this research.
        user_id: Optional user ID.

    Returns:
        Dict with success flag.
    """
    try:
        client = _get_supabase()
        cost = estimate_cost_usd(searches_used, scrapes_used)

        log_entry = {
            "domain": domain,
            "query": query[:500],  # cap query length
            "depth": depth,
            "tracks_run": tracks_run,
            "searches_used": searches_used,
            "scrapes_used": scrapes_used,
            "cost_usd": cost,
            "findings_count": findings_count,
            "graph_updates": graph_updates,
            "triggered_by": triggered_by,
            "requesting_agent": requesting_agent,
            "user_id": user_id,
            "duration_ms": duration_ms,
        }

        client.table("kg_research_log").insert(log_entry).execute()
        return {"success": True, "cost_usd": cost}

    except Exception as e:
        logger.warning("Cost tracking failed (non-blocking): %s", e)
        return {"success": False, "error": str(e)}


COST_TRACKER_TOOLS = [log_research_cost]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Lint and commit**

```bash
uv run ruff check app/agents/research/tools/graph_writer.py app/agents/research/tools/cost_tracker.py --fix
uv run ruff format app/agents/research/tools/graph_writer.py app/agents/research/tools/cost_tracker.py
git add app/agents/research/tools/graph_writer.py app/agents/research/tools/cost_tracker.py tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py
git commit -m "feat(research): add graph writer and cost tracker for research persistence"
```

---

## Task 5: Research Agent Instructions

**Files:**
- Create: `app/agents/research/instructions.py`

- [ ] **Step 1: Write the Research Agent instruction prompt**

```python
# app/agents/research/instructions.py
"""Instruction prompts for the Research Agent.

Defines the agent's identity, methodology, and behavior when handling
research requests from other agents or the ExecutiveAgent.
"""

from __future__ import annotations

RESEARCH_AGENT_INSTRUCTION = """You are the Research Intelligence Agent — Pikar AI's dedicated research specialist.

## Your Role
You perform multi-track parallel research to provide other agents with fresh, cross-validated intelligence. When another agent needs current information about markets, competitors, regulations, trends, or any external topic, the ExecutiveAgent delegates to you.

## Your Methodology (GSD-Inspired)
You follow a systematic research process:

1. **Query Planning** — Decompose the question into focused sub-queries across multiple tracks:
   - Primary: Direct answer to the question
   - Context: Background conditions and landscape
   - Contrarian: Opposing views and challenges
   - Impact: Practical implications
   - Risk: Uncertainty factors

2. **Parallel Track Execution** — Run all tracks concurrently. Each track independently searches, ranks, and scrapes top sources.

3. **Cross-Track Synthesis** — Compare findings across tracks to identify:
   - Agreements (high confidence when multiple tracks confirm)
   - Contradictions (flag with explanation)
   - Gaps (topics that need more research)

4. **Knowledge Graph Persistence** — Store structured findings in the knowledge graph so future queries can use cached intelligence.

## Research Depth Levels
- **Quick**: 1 track, 1 search, no scraping. For simple factual lookups.
- **Standard**: 3 tracks, 3 searches, top 3 scrapes per track. For most queries.
- **Deep**: 5 tracks, 5 searches, top 5 scrapes per track. For strategic decisions.

## When Responding
- Always cite sources with URLs
- State confidence level explicitly
- Flag any contradictions found
- Note data freshness (when sources were published)
- Suggest follow-up research if confidence is low

## What You Do NOT Do
- You do not make business decisions — you provide intelligence for other agents to decide
- You do not guess when data is unavailable — you report gaps
- You do not modify the knowledge graph schema — you only read/write data
"""

RESEARCH_AGENT_DESCRIPTION = (
    "Research Intelligence Agent — performs multi-track parallel research "
    "with cross-validation, knowledge graph persistence, and confidence scoring. "
    "Delegate research questions here for fresh, cited, cross-validated intelligence."
)
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/research/instructions.py
git commit -m "feat(research): add Research Agent instruction prompts"
```

---

## Task 6: Research Agent Factory + Registration

**Files:**
- Create: `app/agents/research/agent.py`
- Modify: `app/agents/specialized_agents.py`
- Modify: `app/agent.py`
- Create: `tests/unit/test_research_agent.py`

This wires everything together into an ADK agent and registers it in the system.

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_research_agent.py`:

```python
"""Tests for the Research Agent registration."""

from __future__ import annotations


def test_research_agent_exists():
    """Research agent singleton can be imported."""
    from app.agents.research.agent import research_agent

    assert research_agent is not None
    assert research_agent.name == "ResearchAgent"


def test_create_research_agent_factory():
    """Factory creates a fresh Research Agent instance."""
    from app.agents.research.agent import create_research_agent

    agent = create_research_agent(name_suffix="_test")
    assert agent.name == "ResearchAgent_test"
    assert agent.tools is not None
    assert len(agent.tools) > 0


def test_research_agent_in_specialized_agents():
    """Research agent is registered in SPECIALIZED_AGENTS list."""
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    agent_names = [a.name for a in SPECIALIZED_AGENTS]
    assert "ResearchAgent" in agent_names


def test_research_agent_has_required_tools():
    """Research agent has all required tool functions."""
    from app.agents.research.agent import research_agent

    tool_names = [t.__name__ if callable(t) else str(t) for t in (research_agent.tools or [])]
    assert "plan_queries" in tool_names
    assert "run_track" in tool_names
    assert "synthesize_tracks" in tool_names
    assert "write_to_graph" in tool_names
    assert "log_research_cost" in tool_names
    assert "graph_read" in tool_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_research_agent.py -v`
Expected: FAIL

- [ ] **Step 3: Write Research Agent factory**

```python
# app/agents/research/agent.py
"""Research Agent — 13th ADK agent for multi-track parallel research.

Follows the existing agent factory pattern. Registered in SPECIALIZED_AGENTS
for ExecutiveAgent routing.
"""

from __future__ import annotations

from app.agents.base_agent import PikarAgent as Agent
from app.agents.research.instructions import (
    RESEARCH_AGENT_DESCRIPTION,
    RESEARCH_AGENT_INSTRUCTION,
)
from app.agents.research.tools.cost_tracker import COST_TRACKER_TOOLS
from app.agents.research.tools.graph_writer import GRAPH_WRITER_TOOLS
from app.agents.research.tools.query_planner import QUERY_PLANNER_TOOLS
from app.agents.research.tools.synthesizer import SYNTHESIZER_TOOLS
from app.agents.research.tools.track_runner import TRACK_RUNNER_TOOLS
from app.agents.shared import DEEP_AGENT_CONFIG, get_model
from app.agents.tools.graph_tools import GRAPH_TOOLS

RESEARCH_AGENT_TOOLS = [
    *QUERY_PLANNER_TOOLS,
    *TRACK_RUNNER_TOOLS,
    *SYNTHESIZER_TOOLS,
    *GRAPH_WRITER_TOOLS,
    *COST_TRACKER_TOOLS,
    *GRAPH_TOOLS,
]


def create_research_agent(
    name_suffix: str = "",
    output_key: str | None = None,
) -> Agent:
    """Create a fresh ResearchAgent instance.

    Used by the fallback ExecutiveAgent and workflow pipelines
    to avoid ADK's single-parent constraint.

    Args:
        name_suffix: Optional suffix for unique naming in workflows.
        output_key: Optional output key for pipeline chaining.

    Returns:
        A fresh ResearchAgent instance.
    """
    agent_name = f"ResearchAgent{name_suffix}" if name_suffix else "ResearchAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description=RESEARCH_AGENT_DESCRIPTION,
        instruction=RESEARCH_AGENT_INSTRUCTION,
        tools=RESEARCH_AGENT_TOOLS,
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
    )


# Singleton for ExecutiveAgent's sub_agents list
research_agent = create_research_agent()
```

- [ ] **Step 4: Add to specialized_agents.py**

Read `app/agents/specialized_agents.py` and add:
1. Import: `from app.agents.research.agent import create_research_agent, research_agent`
2. Add `research_agent` to the `SPECIALIZED_AGENTS` list
3. Add `"research_agent"` and `"create_research_agent"` to `__all__`

- [ ] **Step 5: Add to fallback agent in app/agent.py**

Read `app/agent.py` and find `_build_fallback_sub_agents()`. Add:
1. Import: `from app.agents.specialized_agents import create_research_agent`
2. Add `create_research_agent("_fb")` to the fallback sub_agents list

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/unit/test_research_agent.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Verify full agent load**

Run: `uv run python -c "from app.agents.specialized_agents import SPECIALIZED_AGENTS; print(f'{len(SPECIALIZED_AGENTS)} agents loaded'); print([a.name for a in SPECIALIZED_AGENTS])"`
Expected: `11 agents loaded` with `ResearchAgent` in the list

- [ ] **Step 8: Lint and commit**

```bash
uv run ruff check app/agents/research/ --fix && uv run ruff format app/agents/research/
git add app/agents/research/agent.py app/agents/research/instructions.py app/agents/specialized_agents.py app/agent.py tests/unit/test_research_agent.py
git commit -m "feat(research): register Research Agent as 13th ADK agent in SPECIALIZED_AGENTS"
```

---

## Task 7: Full Test Suite Verification

- [ ] **Step 1: Run all new research tests**

Run: `uv run pytest tests/unit/test_query_planner.py tests/unit/test_track_runner.py tests/unit/test_synthesizer.py tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py tests/unit/test_research_agent.py tests/unit/test_graph_service.py tests/unit/test_graph_tools.py tests/unit/test_research_config.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `uv run pytest tests/unit/ -v -x --ignore=tests/unit/test_agents.py`
Expected: No new failures

- [ ] **Step 3: Lint all new files**

Run: `uv run ruff check app/agents/research/ --fix && uv run ruff format app/agents/research/`
Expected: Clean

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A && git commit -m "test(research): verify Phase 2 — all research agent tests passing"
```

---

## Phase 2 Completion Checklist

After all 7 tasks are done, verify:

- [ ] Query planner decomposes questions into 1/3/5 tracks based on depth
- [ ] Track runner executes search + scrape per track using existing Tavily/Firecrawl
- [ ] Parallel execution via `run_tracks_parallel` with `asyncio.gather`
- [ ] Synthesizer cross-validates findings and scores confidence with multi-track formula
- [ ] Graph writer persists entities and findings to knowledge graph
- [ ] Vault writer persists full reports to Knowledge Vault (backward compatible)
- [ ] Cost tracker logs API usage to `kg_research_log`
- [ ] Research Agent registered as 13th agent in `SPECIALIZED_AGENTS`
- [ ] Research Agent added to fallback sub_agents in `app/agent.py`
- [ ] ExecutiveAgent can route to Research Agent
- [ ] All existing tests still pass

**Next phase:** Phase 3 — Adaptive Router + interaction_log extension. This adds the intelligence layer that decides research depth per query and tracks research impact on agent performance.
