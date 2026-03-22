# Research Intelligence System — Phase 5: Self-Improvement Flywheel Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the research system with the self-improvement engine to create the intelligence flywheel: coverage gaps trigger research events, and research-backed response scores feed back into skill generation (creating "pre_research_*" and "skip_research_*" skills that tune the adaptive router).

**Architecture:** Two integration points. (1) Self-improvement → Research: extend the self-improvement engine's gap identification to emit research events via the event bus when coverage gaps are found. (2) Research → Self-improvement: add a research impact analyzer that compares scores of research-backed vs non-research interactions per domain/query type, and generates skill recommendations when the delta is significant.

**Tech Stack:** Existing self-improvement engine, existing event bus, existing interaction logger, Supabase

**Spec:** `docs/superpowers/specs/2026-03-21-research-intelligence-system-design.md` (Section 5)
**Depends on:** Phases 1-4

---

## File Structure

```
NEW FILES:
  app/services/research_impact_analyzer.py     — Compare research vs non-research scores, generate skill recommendations
  tests/unit/test_research_impact_analyzer.py  — Analyzer tests

MODIFIED FILES:
  app/services/self_improvement_engine.py      — Emit research events on coverage gap detection
```

---

## Task 1: Coverage Gap → Research Event Integration

**Files:**
- Modify: `app/services/self_improvement_engine.py`

When the self-improvement engine identifies a coverage gap, emit a research event to trigger background research on that topic.

- [ ] **Step 1: Read self_improvement_engine.py**

Read the file to find:
- The `identify_improvements()` method (around lines 164-329)
- Where coverage gaps are identified and processed
- The gap processing loop that creates "skill_created" actions

- [ ] **Step 2: Add event emission after gap identification**

Find the section in `identify_improvements()` where unresolved gaps are processed (the loop that creates improvement actions for gaps). After the gap is identified but before the action is created, add event emission:

```python
# Emit research event for each unresolved gap
try:
    from app.services.research_event_bus import get_event_bus
    import asyncio

    bus = get_event_bus()
    # Map agent_id back to domain for the event
    domain = self._agent_id_to_domain(gap.get("agent_id", ""))

    asyncio.get_event_loop().run_until_complete(bus.emit(
        topic=gap.get("user_query", ""),
        domain=domain,
        trigger_type="coverage_gap",
        suggested_depth="deep",
        priority="high",
        source_agent=gap.get("agent_id"),
        metadata={"gap_id": gap.get("id"), "occurrence_count": gap.get("occurrence_count", 1)},
    ))
except Exception as e:
    logger.debug("Research event emission for gap failed (non-blocking): %s", e)
```

Also add this helper method to the class:

```python
def _agent_id_to_domain(self, agent_id: str) -> str:
    """Map agent_id back to domain name for research events."""
    mapping = {
        "FIN": "financial", "CON": "content", "STR": "strategic",
        "SAL": "sales", "MKT": "marketing", "OPS": "operations",
        "HR": "hr", "CMP": "compliance", "CUS": "customer_support",
        "DAT": "data", "EXEC": "strategic",
    }
    return mapping.get(agent_id, "strategic")
```

- [ ] **Step 3: Run existing self-improvement tests to verify no regressions**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/ -k "self_improvement or improvement" -v --no-header 2>&1 | tail -20`

- [ ] **Step 4: Lint and commit**

```bash
uv run ruff check app/services/self_improvement_engine.py --fix && uv run ruff format app/services/self_improvement_engine.py
git add app/services/self_improvement_engine.py
git commit -m "feat(research): emit research events on coverage gap detection"
```

---

## Task 2: Research Impact Analyzer

**Files:**
- Create: `app/services/research_impact_analyzer.py`
- Create: `tests/unit/test_research_impact_analyzer.py`

The analyzer compares scores of research-backed interactions vs non-research interactions per domain. When it finds a significant delta, it generates skill recommendations.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_research_impact_analyzer.py`:

```python
"""Tests for the research impact analyzer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_analyze_research_impact_returns_structure():
    """Analyzer returns per-domain impact comparison."""
    from app.services.research_impact_analyzer import analyze_research_impact

    mock_client = MagicMock()

    # Mock interaction_logs with research tracking
    mock_client.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
        {"agent_id": "FIN", "research_used": True, "research_depth": "standard",
         "user_feedback": "positive", "task_completed": True, "was_escalated": False, "had_followup": False},
        {"agent_id": "FIN", "research_used": True, "research_depth": "deep",
         "user_feedback": "positive", "task_completed": True, "was_escalated": False, "had_followup": False},
        {"agent_id": "FIN", "research_used": False, "research_depth": "none",
         "user_feedback": "negative", "task_completed": False, "was_escalated": True, "had_followup": True},
        {"agent_id": "FIN", "research_used": False, "research_depth": "none",
         "user_feedback": "neutral", "task_completed": True, "was_escalated": False, "had_followup": False},
        {"agent_id": "HR", "research_used": True, "research_depth": "quick",
         "user_feedback": "neutral", "task_completed": True, "was_escalated": False, "had_followup": False},
        {"agent_id": "HR", "research_used": False, "research_depth": "none",
         "user_feedback": "neutral", "task_completed": True, "was_escalated": False, "had_followup": False},
    ]

    with patch("app.services.research_impact_analyzer._get_supabase", return_value=mock_client):
        result = analyze_research_impact(days=30)

    assert result["success"] is True
    assert "domains" in result
    assert "FIN" in result["domains"]
    assert "with_research" in result["domains"]["FIN"]
    assert "without_research" in result["domains"]["FIN"]


def test_generate_skill_recommendations_high_delta():
    """High delta (research helps a lot) generates pre_research skill."""
    from app.services.research_impact_analyzer import generate_skill_recommendations

    domain_impacts = {
        "FIN": {
            "with_research": {"score": 0.87, "count": 20},
            "without_research": {"score": 0.52, "count": 30},
            "delta": 0.35,
        },
    }

    recommendations = generate_skill_recommendations(domain_impacts)

    assert len(recommendations) >= 1
    assert any(r["type"] == "pre_research" for r in recommendations)
    assert any("FIN" in r.get("agent_id", "") or "financial" in r.get("domain", "") for r in recommendations)


def test_generate_skill_recommendations_low_delta():
    """Low delta (research doesn't help) generates skip_research skill."""
    from app.services.research_impact_analyzer import generate_skill_recommendations

    domain_impacts = {
        "HR": {
            "with_research": {"score": 0.60, "count": 10},
            "without_research": {"score": 0.58, "count": 15},
            "delta": 0.02,
        },
    }

    recommendations = generate_skill_recommendations(domain_impacts)

    assert len(recommendations) >= 1
    assert any(r["type"] == "skip_research" for r in recommendations)


def test_generate_skill_recommendations_insufficient_data():
    """Not enough data (< min_count) generates no recommendations."""
    from app.services.research_impact_analyzer import generate_skill_recommendations

    domain_impacts = {
        "FIN": {
            "with_research": {"score": 0.90, "count": 2},  # too few
            "without_research": {"score": 0.50, "count": 3},
            "delta": 0.40,
        },
    }

    recommendations = generate_skill_recommendations(domain_impacts, min_count=5)

    assert len(recommendations) == 0


def test_compute_effectiveness_score():
    """Effectiveness score matches self-improvement formula."""
    from app.services.research_impact_analyzer import compute_effectiveness_score

    interactions = [
        {"user_feedback": "positive", "task_completed": True, "was_escalated": False, "had_followup": False},
        {"user_feedback": "positive", "task_completed": True, "was_escalated": False, "had_followup": False},
        {"user_feedback": "negative", "task_completed": False, "was_escalated": True, "had_followup": True},
    ]

    score = compute_effectiveness_score(interactions)

    assert 0.0 <= score <= 1.0
    # 2/3 positive, 2/3 completed, 1/3 escalated, 1/3 retry
    # = 0.35*0.667 + 0.30*0.667 + 0.20*(1-0.333) + 0.15*(1-0.333)
    # ≈ 0.234 + 0.200 + 0.133 + 0.100 = 0.667
    assert 0.6 <= score <= 0.7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_research_impact_analyzer.py -v`

- [ ] **Step 3: Write the analyzer implementation**

```python
# app/services/research_impact_analyzer.py
"""Research impact analyzer — compares research-backed vs non-research scores.

Feeds into the self-improvement flywheel by identifying:
1. Domains where research significantly improves scores → generate "pre_research_*" skills
2. Domains where research doesn't help → generate "skip_research_*" skills
3. Optimal depth per domain based on score correlation

Uses the same weighted effectiveness formula as the self-improvement engine
(W_POSITIVE=0.35, W_COMPLETION=0.30, W_ESCALATION=0.20, W_RETRY=0.15).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Same weights as self-improvement engine
_W_POSITIVE = 0.35
_W_COMPLETION = 0.30
_W_ESCALATION = 0.20
_W_RETRY = 0.15

# Thresholds for skill generation
PRE_RESEARCH_DELTA_THRESHOLD = 0.15  # research helps 15%+ → always research
SKIP_RESEARCH_DELTA_THRESHOLD = 0.05  # research helps < 5% → skip research


def _get_supabase():
    from app.services.supabase_client import get_supabase_client
    return get_supabase_client()


def analyze_research_impact(days: int = 30) -> dict[str, Any]:
    """Compare research-backed vs non-research interaction scores by domain.

    Args:
        days: Analysis window in days.

    Returns:
        Dict with per-domain impact comparison.
    """
    try:
        client = _get_supabase()
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

        # Fetch interactions with research tracking columns
        response = (
            client.table("interaction_logs")
            .select(
                "agent_id, research_used, research_depth, "
                "user_feedback, task_completed, was_escalated, had_followup"
            )
            .gte("created_at", cutoff)
            .execute()
        )

        interactions = response.data or []
        if not interactions:
            return {"success": True, "domains": {}, "message": "No interactions in window"}

        # Group by agent_id, then split by research_used
        domains: dict[str, dict] = {}
        for interaction in interactions:
            agent_id = interaction.get("agent_id", "UNKNOWN")
            research_used = interaction.get("research_used", False)

            if agent_id not in domains:
                domains[agent_id] = {"with_research": [], "without_research": []}

            if research_used:
                domains[agent_id]["with_research"].append(interaction)
            else:
                domains[agent_id]["without_research"].append(interaction)

        # Compute scores per domain
        domain_impacts = {}
        for agent_id, groups in domains.items():
            with_score = compute_effectiveness_score(groups["with_research"])
            without_score = compute_effectiveness_score(groups["without_research"])

            domain_impacts[agent_id] = {
                "with_research": {
                    "score": round(with_score, 3),
                    "count": len(groups["with_research"]),
                },
                "without_research": {
                    "score": round(without_score, 3),
                    "count": len(groups["without_research"]),
                },
                "delta": round(with_score - without_score, 3),
            }

        return {"success": True, "domains": domain_impacts}

    except Exception as e:
        logger.error("Research impact analysis failed: %s", e)
        return {"success": False, "domains": {}, "error": str(e)}


def compute_effectiveness_score(interactions: list[dict]) -> float:
    """Compute effectiveness using the self-improvement weighted formula.

    Formula: 0.35*positive_rate + 0.30*completion_rate
             + 0.20*(1-escalation_rate) + 0.15*(1-retry_rate)

    Args:
        interactions: List of interaction dicts with feedback/completion fields.

    Returns:
        Effectiveness score between 0.0 and 1.0.
    """
    if not interactions:
        return 0.5  # neutral when no data

    total = len(interactions)
    feedback_given = [i for i in interactions if i.get("user_feedback") is not None]
    feedback_count = len(feedback_given) or 1  # avoid division by zero

    positive_count = sum(1 for i in feedback_given if i.get("user_feedback") == "positive")
    completed_count = sum(1 for i in interactions if i.get("task_completed"))
    escalated_count = sum(1 for i in interactions if i.get("was_escalated"))
    followup_count = sum(1 for i in interactions if i.get("had_followup"))

    positive_rate = positive_count / feedback_count
    completion_rate = completed_count / total
    escalation_rate = escalated_count / total
    retry_rate = followup_count / total

    return (
        _W_POSITIVE * positive_rate
        + _W_COMPLETION * completion_rate
        + _W_ESCALATION * (1.0 - escalation_rate)
        + _W_RETRY * (1.0 - retry_rate)
    )


def generate_skill_recommendations(
    domain_impacts: dict[str, dict],
    min_count: int = 5,
) -> list[dict[str, Any]]:
    """Generate skill recommendations based on research impact analysis.

    When research significantly improves a domain → pre_research skill.
    When research doesn't help → skip_research skill.

    Args:
        domain_impacts: Output from analyze_research_impact()["domains"].
        min_count: Minimum interactions required per group for recommendation.

    Returns:
        List of skill recommendation dicts.
    """
    recommendations = []

    agent_id_to_domain = {
        "FIN": "financial", "CON": "content", "STR": "strategic",
        "SAL": "sales", "MKT": "marketing", "OPS": "operations",
        "HR": "hr", "CMP": "compliance", "CUS": "customer_support",
        "DAT": "data",
    }

    for agent_id, impact in domain_impacts.items():
        with_count = impact.get("with_research", {}).get("count", 0)
        without_count = impact.get("without_research", {}).get("count", 0)
        delta = impact.get("delta", 0)

        # Need enough data in both groups
        if with_count < min_count or without_count < min_count:
            continue

        domain = agent_id_to_domain.get(agent_id, agent_id.lower())
        with_score = impact["with_research"]["score"]
        without_score = impact["without_research"]["score"]

        if delta >= PRE_RESEARCH_DELTA_THRESHOLD:
            recommendations.append({
                "type": "pre_research",
                "agent_id": agent_id,
                "domain": domain,
                "skill_name": f"pre_research_{domain}_queries",
                "description": (
                    f"Always run research before answering {domain} queries. "
                    f"Research-backed responses score {delta:.0%} higher "
                    f"({with_score:.2f} vs {without_score:.2f})."
                ),
                "recommended_depth": "standard" if delta < 0.25 else "deep",
                "confidence": min(1.0, (with_count + without_count) / 50),
            })
        elif delta <= SKIP_RESEARCH_DELTA_THRESHOLD:
            recommendations.append({
                "type": "skip_research",
                "agent_id": agent_id,
                "domain": domain,
                "skill_name": f"skip_research_{domain}_queries",
                "description": (
                    f"Skip live research for {domain} queries — use graph cache only. "
                    f"Research adds no significant improvement "
                    f"(delta={delta:.0%}, {with_score:.2f} vs {without_score:.2f})."
                ),
                "confidence": min(1.0, (with_count + without_count) / 50),
            })

    return recommendations
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `"C:\Users\expert\.local\bin\uv.cmd" run pytest tests/unit/test_research_impact_analyzer.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check app/services/research_impact_analyzer.py --fix && uv run ruff format app/services/research_impact_analyzer.py
git add app/services/research_impact_analyzer.py tests/unit/test_research_impact_analyzer.py
git commit -m "feat(research): add research impact analyzer for flywheel skill generation"
```

---

## Task 3: Full Verification

- [ ] **Step 1: Run all research tests**

```bash
uv run pytest tests/unit/test_query_planner.py tests/unit/test_track_runner.py tests/unit/test_synthesizer.py tests/unit/test_graph_writer.py tests/unit/test_cost_tracker.py tests/unit/test_research_agent.py tests/unit/test_graph_service.py tests/unit/test_graph_tools.py tests/unit/test_research_config.py tests/unit/test_adaptive_router.py tests/unit/test_research_event_bus.py tests/unit/test_intelligence_scheduler.py tests/unit/test_research_impact_analyzer.py -v
```
Expected: All pass (~63 tests)

- [ ] **Step 2: Lint all files**

```bash
uv run ruff check app/agents/research/ app/services/graph_service.py app/agents/tools/graph_tools.py app/services/research_event_bus.py app/services/intelligence_scheduler.py app/services/intelligence_worker.py app/services/research_impact_analyzer.py --fix
```

---

## Phase 5 Completion Checklist

- [ ] Self-improvement engine emits research events when coverage gaps are detected
- [ ] Research impact analyzer compares research vs non-research scores per domain
- [ ] Analyzer generates "pre_research_*" recommendations when delta > 15%
- [ ] Analyzer generates "skip_research_*" recommendations when delta < 5%
- [ ] Effectiveness scoring uses same weighted formula as self-improvement engine
- [ ] All tests pass

**Next phase:** Phase 6 — Admin panel (cost dashboard, graph explorer, scheduler management)
