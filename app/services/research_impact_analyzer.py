# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

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
            return {
                "success": True,
                "domains": {},
                "message": "No interactions in window",
            }

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

    positive_count = sum(
        1 for i in feedback_given if i.get("user_feedback") == "positive"
    )
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
        "FIN": "financial",
        "CON": "content",
        "STR": "strategic",
        "SAL": "sales",
        "MKT": "marketing",
        "OPS": "operations",
        "HR": "hr",
        "CMP": "compliance",
        "CUS": "customer_support",
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
            recommendations.append(
                {
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
                }
            )
        elif delta <= SKIP_RESEARCH_DELTA_THRESHOLD:
            recommendations.append(
                {
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
                }
            )

    return recommendations
