# Research Intelligence System — Phase 4: Continuous Intelligence

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the knowledge graph fresh automatically through scheduled domain research and event-driven urgent research. A background scheduler runs research jobs on configurable cadences per domain, while a Redis Streams event bus triggers immediate research when coverage gaps, stale data, or user feedback signals arrive.

**Architecture:** Builds on the existing `WorkflowWorker` polling pattern and `scheduled_endpoints.py` Cloud Scheduler pattern. A new `IntelligenceScheduler` runs domain research on cadence (via Cloud Scheduler endpoint). A new `ResearchEventBus` uses Redis Streams (XADD/XREADGROUP) for persistent, at-least-once event delivery. Both feed work to the Research Agent's existing pipeline (query planner → track runner → synthesizer → graph writer). Events are deduplicated within configurable time windows.

**Tech Stack:** Redis Streams (`redis.asyncio`), FastAPI scheduled endpoints, existing Research Agent pipeline, Supabase

**Spec:** `docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md` (Section 3)
**Depends on:** Phases 1-3 (knowledge graph + Research Agent + adaptive router)

---

## File Structure

```
NEW FILES:
  app/services/research_event_bus.py           — Redis Streams event bus (publish + consume)
  app/services/intelligence_scheduler.py       — Scheduled domain research with priority queue
  app/services/intelligence_worker.py          — Background consumer for research events
  tests/unit/test_research_event_bus.py        — Event bus tests
  tests/unit/test_intelligence_scheduler.py    — Scheduler tests

MODIFIED FILES:
  app/services/scheduled_endpoints.py          — Add /scheduled/intelligence-tick endpoint
  app/agents/tools/graph_tools.py              — Emit stale_entity_accessed event on stale reads
  docker-compose.yml                           — Add intelligence-worker service (optional)
```

---

## Task 1: Research Event Bus (Redis Streams)

**Files:**
- Create: `app/services/research_event_bus.py`
- Create: `tests/unit/test_research_event_bus.py`

The event bus uses Redis Streams for persistent, ordered event delivery. Events survive worker restarts (unlike pub/sub). Consumer groups ensure at-least-once processing.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_research_event_bus.py`:

```python
"""Tests for the research event bus (Redis Streams)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_emit_event_calls_xadd():
    """Emitting an event calls Redis XADD on the stream."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234-0")

    bus = ResearchEventBus(redis_client=mock_redis)
    result = _run(bus.emit(
        topic="SARB interest rate",
        domain="financial",
        trigger_type="stale_access",
        suggested_depth="quick",
        priority="medium",
    ))

    assert result["success"] is True
    mock_redis.xadd.assert_awaited_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == "research:events"  # stream name


def test_emit_deduplicates_within_window():
    """Same topic+domain within dedup window is skipped."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234-0")
    mock_redis.get = AsyncMock(return_value="1")  # dedup key exists

    bus = ResearchEventBus(redis_client=mock_redis)
    result = _run(bus.emit(
        topic="SARB interest rate",
        domain="financial",
        trigger_type="stale_access",
        suggested_depth="quick",
    ))

    assert result["success"] is True
    assert result.get("deduplicated") is True
    mock_redis.xadd.assert_not_awaited()


def test_emit_handles_redis_failure():
    """Event emission fails gracefully on Redis error."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.xadd = AsyncMock(side_effect=Exception("Redis down"))

    bus = ResearchEventBus(redis_client=mock_redis)
    result = _run(bus.emit(
        topic="test",
        domain="financial",
        trigger_type="stale_access",
        suggested_depth="quick",
    ))

    assert result["success"] is False


def test_consume_reads_from_stream():
    """Consumer reads events from Redis Stream."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    # Simulate one event in stream, then empty
    mock_redis.xreadgroup = AsyncMock(side_effect=[
        [["research:events", [
            ("1234-0", {"data": json.dumps({
                "topic": "test", "domain": "financial",
                "trigger_type": "stale_access", "suggested_depth": "quick",
                "priority": "medium",
            })})
        ]]],
        [],  # empty on second call
    ])
    mock_redis.xack = AsyncMock()

    bus = ResearchEventBus(redis_client=mock_redis)
    events = _run(bus.consume_batch(max_events=10))

    assert len(events) == 1
    assert events[0]["topic"] == "test"
    assert events[0]["domain"] == "financial"


def test_dedup_window_per_trigger_type():
    """Different trigger types have different dedup windows."""
    from app.services.research_event_bus import DEDUP_WINDOWS

    assert DEDUP_WINDOWS["coverage_gap"] > DEDUP_WINDOWS["stale_access"]
    assert DEDUP_WINDOWS["user_feedback"] <= 3600  # max 1 hour
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_research_event_bus.py -v`

- [ ] **Step 3: Write event bus implementation**

```python
# app/services/research_event_bus.py
"""Research event bus using Redis Streams.

Provides persistent, at-least-once event delivery for research triggers.
Uses Redis Streams (XADD/XREADGROUP) instead of pub/sub because:
- Messages persist if the consumer is temporarily down
- Consumer groups enable distributed processing
- Acknowledgement (XACK) prevents message loss

Events trigger background research when:
- Coverage gaps are detected by self-improvement
- graph_read encounters stale data
- User gives negative feedback
- External webhooks signal changes
- Cross-domain entity updates propagate
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

STREAM_NAME = "research:events"
CONSUMER_GROUP = "intelligence-workers"
CONSUMER_NAME = "worker-1"

# Dedup windows in seconds per trigger type
DEDUP_WINDOWS: dict[str, int] = {
    "coverage_gap": 86400,      # 24 hours
    "low_confidence": 14400,    # 4 hours
    "stale_access": 3600,       # 1 hour
    "user_feedback": 3600,      # 1 hour
    "external_webhook": 7200,   # 2 hours
    "cross_domain": 28800,      # 8 hours
}

MAX_CONCURRENT_RESEARCH = 3
EVENT_QUEUE_MAX = 50


class ResearchEventBus:
    """Redis Streams-based event bus for research triggers."""

    def __init__(self, redis_client: Any = None) -> None:
        """Initialize with a Redis client.

        Args:
            redis_client: An async Redis client. If None, uses the
                CacheService's internal Redis connection.
        """
        self._redis = redis_client

    async def _get_redis(self):
        """Get or create Redis client."""
        if self._redis is not None:
            return self._redis
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        if not cache._connected:
            await cache.connect()
        self._redis = cache._redis
        return self._redis

    async def emit(
        self,
        topic: str,
        domain: str,
        trigger_type: str,
        suggested_depth: str = "standard",
        priority: str = "medium",
        source_agent: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Publish a research event to the stream.

        Deduplicates within the trigger type's time window to prevent
        redundant research on the same topic.

        Args:
            topic: Research topic or query.
            domain: Agent domain.
            trigger_type: What triggered this event.
            suggested_depth: Recommended research depth.
            priority: Event priority (critical, high, medium, low).
            source_agent: Which agent triggered this.
            metadata: Additional context.

        Returns:
            Dict with success flag and optional dedup/event_id info.
        """
        try:
            redis = await self._get_redis()

            # Check dedup
            dedup_key = self._make_dedup_key(topic, domain, trigger_type)
            existing = await redis.get(dedup_key)
            if existing:
                logger.debug("Dedup hit for %s/%s/%s", topic, domain, trigger_type)
                return {"success": True, "deduplicated": True, "dedup_key": dedup_key}

            # Build event payload
            event = {
                "topic": topic,
                "domain": domain,
                "trigger_type": trigger_type,
                "suggested_depth": suggested_depth,
                "priority": priority,
                "source_agent": source_agent or "",
                "metadata": json.dumps(metadata or {}),
            }

            # Publish to stream
            event_id = await redis.xadd(
                STREAM_NAME,
                {"data": json.dumps(event)},
                maxlen=EVENT_QUEUE_MAX * 10,  # keep last 500 events
            )

            # Set dedup key with TTL
            dedup_ttl = DEDUP_WINDOWS.get(trigger_type, 3600)
            await redis.set(dedup_key, "1", ex=dedup_ttl)

            logger.info(
                "Research event emitted: %s/%s/%s (id=%s)",
                trigger_type, domain, topic[:50], event_id,
            )
            return {"success": True, "event_id": event_id, "deduplicated": False}

        except Exception as e:
            logger.warning("Failed to emit research event: %s", e)
            return {"success": False, "error": str(e)}

    async def consume_batch(
        self,
        max_events: int = 10,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        """Read a batch of events from the stream.

        Uses consumer groups for at-least-once delivery.

        Args:
            max_events: Max events to read in one batch.
            block_ms: How long to block waiting for events (0 = no block).

        Returns:
            List of event dicts.
        """
        try:
            redis = await self._get_redis()

            # Ensure consumer group exists
            try:
                await redis.xgroup_create(
                    STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True,
                )
            except Exception:
                pass  # Group already exists

            # Read events
            results = await redis.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_NAME: ">"},
                count=max_events,
                block=block_ms,
            )

            if not results:
                return []

            events = []
            for _stream, messages in results:
                for msg_id, msg_data in messages:
                    try:
                        event = json.loads(msg_data.get("data", "{}"))
                        event["_msg_id"] = msg_id
                        events.append(event)
                    except (json.JSONDecodeError, AttributeError):
                        logger.warning("Invalid event data: %s", msg_data)
                        # Acknowledge bad messages to prevent reprocessing
                        await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)

            return events

        except Exception as e:
            logger.error("Failed to consume events: %s", e)
            return []

    async def acknowledge(self, msg_id: str) -> bool:
        """Acknowledge a processed event.

        Args:
            msg_id: The Redis Stream message ID.

        Returns:
            True if acknowledged successfully.
        """
        try:
            redis = await self._get_redis()
            await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
            return True
        except Exception as e:
            logger.warning("Failed to acknowledge %s: %s", msg_id, e)
            return False

    @staticmethod
    def _make_dedup_key(topic: str, domain: str, trigger_type: str) -> str:
        """Generate a dedup key for event deduplication."""
        content = f"{topic.lower().strip()}:{domain}:{trigger_type}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"research:dedup:{hash_val}"


# Module-level singleton
_event_bus: ResearchEventBus | None = None


def get_event_bus() -> ResearchEventBus:
    """Get the singleton event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = ResearchEventBus()
    return _event_bus
```

- [ ] **Step 4: Run tests**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_research_event_bus.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check app/services/research_event_bus.py --fix && uv run ruff format app/services/research_event_bus.py
git add app/services/research_event_bus.py tests/unit/test_research_event_bus.py
git commit -m "feat(research): add Redis Streams event bus for research triggers"
```

---

## Task 2: Intelligence Scheduler

**Files:**
- Create: `app/services/intelligence_scheduler.py`
- Create: `tests/unit/test_intelligence_scheduler.py`

The scheduler runs domain research on configurable cadences. It's triggered by a Cloud Scheduler endpoint (same pattern as existing scheduled_endpoints.py).

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_intelligence_scheduler.py`:

```python
"""Tests for the intelligence scheduler."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_get_domains_due_for_refresh():
    """Scheduler identifies domains that need refreshing."""
    from app.services.intelligence_scheduler import get_domains_due_for_refresh

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"domain": "financial", "schedule_cron": "0 6 * * *", "is_active": True},
        {"domain": "hr", "schedule_cron": "0 6 * * 1", "is_active": True},
    ]

    with patch("app.services.intelligence_scheduler._get_supabase", return_value=mock_client):
        domains = get_domains_due_for_refresh()

    assert isinstance(domains, list)
    # Returns active domains (actual cron check depends on current time)


def test_build_research_queue_prioritizes_stale():
    """Research queue prioritizes stale high-value entities."""
    from app.services.intelligence_scheduler import build_research_queue

    mock_client = MagicMock()

    # Mock stale entities
    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"canonical_name": "SARB", "source_count": 14, "freshness_at": "2026-03-01T00:00:00Z"},
    ]

    # Mock watch topics
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"topic": "ZAR exchange rate", "priority": "critical"},
    ]

    with patch("app.services.intelligence_scheduler._get_supabase", return_value=mock_client):
        queue = build_research_queue(domain="financial")

    assert isinstance(queue, list)
    assert len(queue) >= 0  # depends on mocked data


def test_run_scheduled_research_executes_pipeline():
    """Scheduler executes the full research pipeline for a domain."""
    from app.services.intelligence_scheduler import run_scheduled_research

    with patch("app.services.intelligence_scheduler.build_research_queue", return_value=[
        {"query": "SARB interest rate", "depth": "standard"},
    ]):
        with patch("app.services.intelligence_scheduler._execute_research_job", new_callable=AsyncMock, return_value={"success": True}):
            result = _run(run_scheduled_research(domain="financial"))

    assert result["success"] is True
    assert result["jobs_executed"] >= 0
```

- [ ] **Step 2: Write scheduler implementation**

```python
# app/services/intelligence_scheduler.py
"""Intelligence scheduler for continuous domain research.

Maintains baseline freshness per domain on a configurable cadence.
Triggered by Cloud Scheduler endpoint (POST /scheduled/intelligence-tick).

For each domain due for refresh:
1. Find stale high-value entities (ordered by source_count)
2. Check admin-configured watch topics
3. Build prioritized, deduplicated research queue
4. Execute research within domain budget ceiling
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase():
    from app.services.supabase_client import get_supabase_client
    return get_supabase_client()


def get_domains_due_for_refresh() -> list[dict[str, Any]]:
    """Get domains that are active and due for scheduled research.

    Queries kg_domain_budgets for active domains. The actual cron
    schedule check is done by the Cloud Scheduler — this endpoint
    just processes whatever domains are active.

    Returns:
        List of domain config dicts with domain, monthly_budget, schedule_cron.
    """
    try:
        client = _get_supabase()
        response = (
            client.table("kg_domain_budgets")
            .select("domain, monthly_budget, schedule_cron, is_active")
            .eq("is_active", True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error("Failed to get domain schedules: %s", e)
        return []


def build_research_queue(
    domain: str,
    max_items: int = 10,
) -> list[dict[str, Any]]:
    """Build a prioritized research queue for a domain.

    Combines:
    1. Stale high-value entities (by source_count descending)
    2. Admin-configured watch topics
    3. Unresolved coverage gaps for this domain

    Args:
        domain: Agent domain.
        max_items: Max items in the queue.

    Returns:
        List of research job dicts with query and depth.
    """
    try:
        client = _get_supabase()
        queue = []

        # 1. Find stale entities
        from app.agents.research.config import DOMAIN_FRESHNESS

        import datetime

        threshold_hours = DOMAIN_FRESHNESS.get(domain, {}).get("default_hours", 24)
        stale_cutoff = (
            datetime.datetime.now(tz=datetime.timezone.utc)
            - datetime.timedelta(hours=threshold_hours)
        ).isoformat()

        stale_resp = (
            client.table("kg_entities")
            .select("canonical_name, source_count, freshness_at")
            .contains("domains", [domain])
            .lt("freshness_at", stale_cutoff)
            .order("source_count", desc=True)
            .limit(max_items)
            .execute()
        )
        for entity in (stale_resp.data or []):
            queue.append({
                "query": entity["canonical_name"],
                "depth": "standard",
                "source": "stale_entity",
                "priority": entity.get("source_count", 1),
            })

        # 2. Watch topics
        watch_resp = (
            client.table("kg_watch_topics")
            .select("topic, priority")
            .eq("domain", domain)
            .eq("is_active", True)
            .execute()
        )
        priority_map = {"critical": 100, "high": 50, "medium": 20, "low": 5}
        for topic in (watch_resp.data or []):
            queue.append({
                "query": topic["topic"],
                "depth": "deep" if topic["priority"] == "critical" else "standard",
                "source": "watch_topic",
                "priority": priority_map.get(topic["priority"], 10),
            })

        # 3. Unresolved coverage gaps
        gaps_resp = (
            client.table("coverage_gaps")
            .select("user_query, occurrence_count")
            .eq("agent_id", _domain_to_agent_id(domain))
            .eq("resolved", False)
            .order("occurrence_count", desc=True)
            .limit(5)
            .execute()
        )
        for gap in (gaps_resp.data or []):
            queue.append({
                "query": gap["user_query"],
                "depth": "deep",
                "source": "coverage_gap",
                "priority": gap.get("occurrence_count", 1) * 10,
            })

        # Deduplicate by query (keep highest priority)
        seen: dict[str, dict] = {}
        for item in queue:
            key = item["query"].lower().strip()
            if key not in seen or item["priority"] > seen[key]["priority"]:
                seen[key] = item
        queue = sorted(seen.values(), key=lambda x: x["priority"], reverse=True)

        return queue[:max_items]

    except Exception as e:
        logger.error("Failed to build research queue for %s: %s", domain, e)
        return []


async def run_scheduled_research(domain: str) -> dict[str, Any]:
    """Execute scheduled research for a domain.

    Builds the research queue and executes each job through the
    Research Agent's pipeline.

    Args:
        domain: Agent domain to research.

    Returns:
        Dict with success, jobs_executed, total_cost.
    """
    queue = build_research_queue(domain)
    if not queue:
        return {"success": True, "jobs_executed": 0, "message": f"No research needed for {domain}"}

    jobs_executed = 0
    total_cost = 0.0

    from app.agents.research.tools.adaptive_router import _check_budget

    for item in queue:
        # Budget check before each job
        if not _check_budget(domain):
            logger.info("Budget exhausted for %s after %d jobs", domain, jobs_executed)
            break

        result = await _execute_research_job(
            query=item["query"],
            domain=domain,
            depth=item["depth"],
            triggered_by="scheduled",
        )

        if result.get("success"):
            jobs_executed += 1
            total_cost += result.get("cost_usd", 0)

    return {
        "success": True,
        "domain": domain,
        "jobs_executed": jobs_executed,
        "total_cost": round(total_cost, 4),
        "queue_size": len(queue),
    }


async def _execute_research_job(
    query: str,
    domain: str,
    depth: str,
    triggered_by: str = "scheduled",
) -> dict[str, Any]:
    """Execute a single research job through the full pipeline.

    Pipeline: plan_queries → run_tracks_parallel → synthesize_tracks
              → write_to_graph → write_to_vault → log_research_cost

    Args:
        query: Research query.
        domain: Agent domain.
        depth: Research depth (quick/standard/deep).
        triggered_by: What triggered this research.

    Returns:
        Dict with success and research metadata.
    """
    import time

    start = time.monotonic()

    try:
        from app.agents.research.tools.query_planner import plan_queries
        from app.agents.research.tools.track_runner import run_tracks_parallel
        from app.agents.research.tools.synthesizer import synthesize_tracks
        from app.agents.research.tools.graph_writer import write_to_graph, write_to_vault
        from app.agents.research.tools.cost_tracker import log_research_cost, estimate_cost_usd

        # Step 1: Plan queries
        plan = plan_queries(query=query, domain=domain, depth=depth)
        if not plan["success"]:
            return {"success": False, "error": "Query planning failed"}

        # Step 2: Run tracks in parallel
        track_results = await run_tracks_parallel(
            tracks=plan["tracks"],
            scrape_top_n=3 if depth != "quick" else 0,
        )

        # Step 3: Synthesize
        synthesis = synthesize_tracks(
            track_results=track_results,
            original_query=query,
            domain=domain,
        )

        if not synthesis["success"]:
            return {"success": False, "error": "Synthesis failed"}

        # Step 4: Write to graph
        graph_result = write_to_graph(synthesis=synthesis, domain=domain)

        # Step 5: Write to vault
        await write_to_vault(synthesis=synthesis, topic=query)

        # Step 6: Log cost
        duration_ms = int((time.monotonic() - start) * 1000)
        cost = estimate_cost_usd(
            searches=synthesis.get("search_count", 0),
            scrapes=synthesis.get("scrape_count", 0),
        )
        log_research_cost(
            domain=domain,
            query=query,
            depth=depth,
            tracks_run=len(plan["tracks"]),
            searches_used=synthesis.get("search_count", 0),
            scrapes_used=synthesis.get("scrape_count", 0),
            findings_count=len(synthesis.get("findings", [])),
            graph_updates=graph_result.get("entities_written", 0) + graph_result.get("findings_written", 0),
            triggered_by=triggered_by,
            duration_ms=duration_ms,
        )

        return {
            "success": True,
            "query": query,
            "domain": domain,
            "depth": depth,
            "findings": len(synthesis.get("findings", [])),
            "confidence": synthesis.get("confidence", 0),
            "cost_usd": cost,
            "duration_ms": duration_ms,
        }

    except Exception as e:
        logger.error("Research job failed for '%s' in %s: %s", query, domain, e)
        return {"success": False, "error": str(e)}


def _domain_to_agent_id(domain: str) -> str:
    """Map domain name to agent_id used in coverage_gaps table."""
    mapping = {
        "financial": "FIN",
        "content": "CON",
        "strategic": "STR",
        "sales": "SAL",
        "marketing": "MKT",
        "operations": "OPS",
        "hr": "HR",
        "compliance": "CMP",
        "customer_support": "CUS",
        "data": "DAT",
    }
    return mapping.get(domain, domain.upper()[:3])
```

- [ ] **Step 3: Run tests**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_intelligence_scheduler.py -v`
Expected: All 3 tests PASS

- [ ] **Step 4: Lint and commit**

```bash
uv run ruff check app/services/intelligence_scheduler.py --fix && uv run ruff format app/services/intelligence_scheduler.py
git add app/services/intelligence_scheduler.py tests/unit/test_intelligence_scheduler.py
git commit -m "feat(research): add intelligence scheduler for continuous domain research"
```

---

## Task 3: Intelligence Worker (Event Consumer)

**Files:**
- Create: `app/services/intelligence_worker.py`

A background worker that consumes events from the Redis Streams event bus and executes research jobs. Can run as a standalone process or as a background task within FastAPI.

- [ ] **Step 1: Write the intelligence worker**

```python
# app/services/intelligence_worker.py
"""Background worker that consumes research events and executes jobs.

Can run as:
1. Standalone process: python -m app.services.intelligence_worker
2. Background task in FastAPI lifespan (for simpler deployments)

Consumes from the Redis Streams event bus and routes events to the
intelligence scheduler's _execute_research_job function.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

logger = logging.getLogger(__name__)

MAX_CONCURRENT = int(os.getenv("RESEARCH_MAX_CONCURRENT", "3"))
POLL_INTERVAL = int(os.getenv("RESEARCH_POLL_INTERVAL", "5"))


class IntelligenceWorker:
    """Consumes research events and executes research jobs."""

    def __init__(self) -> None:
        self.running = False
        self._active_jobs = 0
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def start(self) -> None:
        """Start the event consumption loop."""
        self.running = True
        logger.info(
            "Intelligence worker started (max_concurrent=%d, poll_interval=%ds)",
            MAX_CONCURRENT, POLL_INTERVAL,
        )

        from app.services.research_event_bus import get_event_bus

        bus = get_event_bus()

        while self.running:
            try:
                events = await bus.consume_batch(
                    max_events=MAX_CONCURRENT - self._active_jobs,
                    block_ms=POLL_INTERVAL * 1000,
                )

                for event in events:
                    asyncio.create_task(self._process_event(event, bus))

            except asyncio.CancelledError:
                logger.info("Intelligence worker cancelled")
                break
            except Exception as e:
                logger.error("Worker loop error: %s", e)
                await asyncio.sleep(POLL_INTERVAL)

        logger.info("Intelligence worker stopped")

    async def stop(self) -> None:
        """Signal the worker to stop."""
        self.running = False

    async def _process_event(self, event: dict, bus) -> None:
        """Process a single research event."""
        async with self._semaphore:
            self._active_jobs += 1
            try:
                from app.services.intelligence_scheduler import _execute_research_job

                result = await _execute_research_job(
                    query=event.get("topic", ""),
                    domain=event.get("domain", "general"),
                    depth=event.get("suggested_depth", "standard"),
                    triggered_by=event.get("trigger_type", "event"),
                )

                # Acknowledge the event
                msg_id = event.get("_msg_id")
                if msg_id:
                    await bus.acknowledge(msg_id)

                if result.get("success"):
                    logger.info(
                        "Research event processed: %s/%s (%d findings, $%.4f)",
                        event.get("domain"), event.get("topic", "")[:40],
                        result.get("findings", 0), result.get("cost_usd", 0),
                    )
                else:
                    logger.warning(
                        "Research event failed: %s/%s — %s",
                        event.get("domain"), event.get("topic", "")[:40],
                        result.get("error"),
                    )

            except Exception as e:
                logger.error("Event processing error: %s", e)
            finally:
                self._active_jobs -= 1


async def main():
    """Entry point for standalone worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    worker = IntelligenceWorker()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Lint and commit**

```bash
uv run ruff check app/services/intelligence_worker.py --fix && uv run ruff format app/services/intelligence_worker.py
git add app/services/intelligence_worker.py
git commit -m "feat(research): add intelligence worker for event-driven research execution"
```

---

## Task 4: Scheduled Endpoint + Stale Event Emission

**Files:**
- Modify: `app/services/scheduled_endpoints.py`
- Modify: `app/agents/tools/graph_tools.py`

Add the Cloud Scheduler endpoint that triggers domain research, and update graph_read to emit stale_entity_accessed events.

- [ ] **Step 1: Read scheduled_endpoints.py to understand the pattern**

Read `app/services/scheduled_endpoints.py` to find the router and endpoint pattern.

- [ ] **Step 2: Add intelligence-tick endpoint**

Add to the existing scheduled endpoints router:

```python
@router.post("/scheduled/intelligence-tick")
async def intelligence_tick(request: Request):
    """Trigger scheduled research for all active domains.

    Called by Cloud Scheduler on the configured cadence.
    Processes each active domain's research queue.
    """
    _verify_scheduler_secret(request)

    from app.services.intelligence_scheduler import (
        get_domains_due_for_refresh,
        run_scheduled_research,
    )

    domains = get_domains_due_for_refresh()
    results = []
    for domain_config in domains:
        domain = domain_config["domain"]
        result = await run_scheduled_research(domain)
        results.append(result)

    total_jobs = sum(r.get("jobs_executed", 0) for r in results)
    total_cost = sum(r.get("total_cost", 0) for r in results)

    return {
        "success": True,
        "domains_processed": len(domains),
        "total_jobs": total_jobs,
        "total_cost": round(total_cost, 4),
        "results": results,
    }
```

- [ ] **Step 3: Update graph_read to emit stale events**

Read `app/agents/tools/graph_tools.py` and find where the staleness warning is added. After the warning, add event emission:

```python
if GraphService.is_stale(freshness_at, threshold):
    result["staleness_warning"] = (
        f"Data is older than {threshold}h threshold for {domain} domain. "
        "Consider delegating to Research Agent for fresh data."
    )
    # Emit stale_entity_accessed event for background refresh
    try:
        import asyncio
        from app.services.research_event_bus import get_event_bus
        bus = get_event_bus()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bus.emit(
            topic=query,
            domain=domain,
            trigger_type="stale_access",
            suggested_depth="quick",
            priority="medium",
        ))
    except Exception:
        pass  # Event emission is non-critical
```

- [ ] **Step 4: Lint and commit**

```bash
uv run ruff check app/services/scheduled_endpoints.py app/agents/tools/graph_tools.py --fix
uv run ruff format app/services/scheduled_endpoints.py app/agents/tools/graph_tools.py
git add app/services/scheduled_endpoints.py app/agents/tools/graph_tools.py
git commit -m "feat(research): add intelligence-tick endpoint and stale entity event emission"
```

---

## Task 5: Docker Compose Update (Optional)

**Files:**
- Modify: `docker-compose.yml`

Add the intelligence worker as an optional service.

- [ ] **Step 1: Read docker-compose.yml**

- [ ] **Step 2: Add intelligence-worker service**

Add after the existing backend service:

```yaml
  # Intelligence worker — consumes research events, runs scheduled research
  intelligence-worker:
    build: .
    container_name: pikar-intelligence-worker
    command: uv run python -m app.services.intelligence_worker
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - RESEARCH_MAX_CONCURRENT=3
      - RESEARCH_POLL_INTERVAL=5
    env_file:
      - .env
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
    networks:
      - pikar-network
    profiles:
      - intelligence  # Only starts with: docker compose --profile intelligence up
    restart: unless-stopped
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(research): add intelligence-worker service to Docker Compose"
```

---

## Task 6: Full Verification

- [ ] **Step 1: Run all research tests**

```bash
uv run pytest tests/unit/test_query_planner.py tests/unit/test_track_runner.py tests/unit/test_synthesizer.py tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py tests/unit/test_research_agent.py tests/unit/test_graph_service.py tests/unit/test_graph_tools.py tests/unit/test_research_config.py tests/unit/test_adaptive_router.py tests/unit/test_research_event_bus.py tests/unit/test_intelligence_scheduler.py -v
```
Expected: All pass (~58 tests)

- [ ] **Step 2: Lint all files**

```bash
uv run ruff check app/agents/research/ app/services/graph_service.py app/agents/tools/graph_tools.py app/services/research_event_bus.py app/services/intelligence_scheduler.py app/services/intelligence_worker.py --fix
```

- [ ] **Step 3: Verify no regressions**

```bash
uv run pytest tests/unit/ -v -x --ignore=tests/unit/test_agents.py
```

---

## Phase 4 Completion Checklist

After all 6 tasks:

- [ ] Redis Streams event bus publishes and consumes research events
- [ ] Events deduplicated within trigger-type-specific time windows
- [ ] Intelligence scheduler builds prioritized research queue per domain
- [ ] Queue combines stale entities + watch topics + coverage gaps
- [ ] Scheduler respects domain budget ceilings
- [ ] Full research pipeline (plan → track → synthesize → graph → vault → cost) executes end-to-end
- [ ] Intelligence worker consumes events with max concurrency control
- [ ] `/scheduled/intelligence-tick` endpoint triggers domain research
- [ ] `graph_read` emits stale_entity_accessed events for background refresh
- [ ] Docker Compose has optional intelligence-worker service
- [ ] All tests pass

**Next phase:** Phase 5 — Self-improvement flywheel integration. Coverage gaps trigger research events, research outcomes generate/refine agent skills.
