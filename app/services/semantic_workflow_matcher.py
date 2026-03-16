"""Semantic Workflow Matcher (D2).

Matches user activity patterns against workflow templates using
embedding similarity, suggesting the most relevant workflows.
"""

import logging
from typing import Any

from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


async def match_workflows_for_user(
    user_id: str,
    limit: int = 5,
    min_similarity: float = 0.4,
) -> list[dict[str, Any]]:
    """Analyze recent user activity and suggest matching workflow templates."""
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()

        response = await execute_async(
            client.table("user_activity_log")
            .select("action, details")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(50),
            op_name="semantic_workflow_matcher.activity_log",
        )
        logs = response.data if response.data else []
        if len(logs) < 3:
            return []

        actions = [f"{log['action']}: {log.get('details', '')}" for log in logs[:20]]
        activity_summary = "; ".join(actions)

        from app.rag.embedding_service import generate_embedding

        query_embedding = generate_embedding(activity_summary[:500])
        if not query_embedding:
            return []

        wf_response = await execute_async(
            client.table("workflow_templates")
            .select("name, description, category")
            .eq("lifecycle_status", "published"),
            op_name="semantic_workflow_matcher.templates",
        )
        templates = wf_response.data if wf_response.data else []
        if not templates:
            return []

        from app.rag.embedding_service import generate_embeddings_batch
        from app.skills.skill_embeddings import cosine_similarity

        template_texts = [
            f"{t['name']}: {t.get('description', '')} [{t.get('category', '')}]"
            for t in templates
        ]
        template_embeddings = generate_embeddings_batch(template_texts)

        results = []
        for template, emb in zip(templates, template_embeddings):
            if emb and any(v != 0.0 for v in emb):
                score = cosine_similarity(query_embedding, emb)
                if score >= min_similarity:
                    results.append(
                        {
                            "workflow_name": template["name"],
                            "description": template.get("description", ""),
                            "category": template.get("category", ""),
                            "score": round(score, 3),
                        }
                    )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    except Exception as e:
        logger.error("Semantic workflow matching failed for user %s: %s", user_id, e)
        return []


async def get_journey_quality_metrics(user_id: str) -> dict[str, Any]:
    """D3: Compute journey quality metrics from phase transition history."""
    try:
        from app.services.supabase import get_service_client

        client = get_service_client()
        response = await execute_async(
            client.table("initiative_phase_history")
            .select("from_phase, to_phase, duration_seconds, transitioned_at")
            .eq("user_id", user_id)
            .order("transitioned_at", desc=True),
            op_name="semantic_workflow_matcher.phase_history",
        )
        transitions = response.data if response.data else []

        if not transitions:
            return {
                "total_transitions": 0,
                "avg_time_per_phase": {},
                "phases_reached": {},
                "completion_rate": 0.0,
            }

        phase_durations: dict[str, list[int]] = {}
        phase_counts: dict[str, int] = {}
        completed_count = 0

        for t in transitions:
            to_phase = t.get("to_phase", "")
            from_phase = t.get("from_phase", "")
            phase_counts[to_phase] = phase_counts.get(to_phase, 0) + 1

            duration = t.get("duration_seconds")
            if duration and from_phase:
                phase_durations.setdefault(from_phase, []).append(duration)

            if to_phase == "completed" or to_phase == "scale":
                completed_count += 1

        avg_time = {
            phase: round(sum(durs) / len(durs) / 3600, 1)
            for phase, durs in phase_durations.items()
            if durs
        }

        total_initiatives = phase_counts.get("validation", 0) + phase_counts.get("ideation", 0)
        rate = (completed_count / total_initiatives * 100) if total_initiatives > 0 else 0.0

        return {
            "total_transitions": len(transitions),
            "avg_hours_per_phase": avg_time,
            "phases_reached": phase_counts,
            "completion_rate": round(rate, 1),
        }
    except Exception as e:
        logger.error("Journey quality metrics failed for user %s: %s", user_id, e)
        return {"error": str(e)}
