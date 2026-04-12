# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Self-Improvement API Router.

Dashboard endpoints for viewing skill scores, improvement actions,
coverage gaps, and triggering evaluation cycles.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/self-improvement", tags=["Self-Improvement"])


# ============================================================================
# Response Models
# ============================================================================


class SkillScoreResponse(BaseModel):
    skill_name: str
    effectiveness_score: float
    total_uses: int
    positive_rate: float
    completion_rate: float
    escalation_rate: float
    retry_rate: float
    trend: str | None = None
    score_delta: float | None = None
    created_at: str | None = None


class ImprovementActionResponse(BaseModel):
    id: str
    action_type: str
    skill_name: str | None = None
    agent_id: str | None = None
    trigger_reason: str
    status: str
    effectiveness_before: float | None = None
    effectiveness_after: float | None = None
    created_at: str | None = None


class CoverageGapResponse(BaseModel):
    id: str
    user_query: str
    agent_id: str
    matched_skills: list | None = None
    confidence_score: float
    occurrence_count: int
    resolved: bool
    created_at: str | None = None


class DashboardSummary(BaseModel):
    total_interactions: int
    total_skills_scored: int
    avg_effectiveness: float
    underperformers: int
    high_performers: int
    pending_actions: int
    unresolved_gaps: int


class SkillVersionResponse(BaseModel):
    """A single skill version entry in the history chain."""

    id: str
    skill_name: str
    version: str
    knowledge_preview: str  # First 200 chars of knowledge
    previous_version_id: str | None = None
    source_action_id: str | None = None
    created_by: str
    created_at: str
    is_active: bool
    diff_summary: (
        str  # e.g. "Knowledge changed from 450 to 1200 chars; version 1.0.0 -> 1.0.2"
    )


class FeedbackRequest(BaseModel):
    """Request body for the user-feedback endpoint."""

    rating: Literal["positive", "negative", "neutral"]


class CycleRequest(BaseModel):
    auto_execute: bool = False
    days: int = 7


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/dashboard")
@limiter.limit(get_user_persona_limit)
async def get_dashboard_summary(
    request: Request,
    days: int = 7,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Aggregate dashboard summary for the self-improvement system."""
    client = get_service_client()

    # Skill scores
    scores_resp = await execute_async(
        client.table("skill_scores")
        .select("effectiveness_score, total_uses, trend")
        .order("created_at", desc=True)
        .limit(200),
        op_name="self_improvement_router.dashboard.scores",
    )
    scores = scores_resp.data or []

    # Deduplicate to latest per skill
    seen = set()
    unique_scores = []
    for s in scores:
        name = s.get("skill_name", "")
        if name not in seen:
            seen.add(name)
            unique_scores.append(s)

    avg_eff = 0.0
    if unique_scores:
        avg_eff = round(
            sum(s["effectiveness_score"] for s in unique_scores) / len(unique_scores), 3
        )

    underperformers = sum(1 for s in unique_scores if s["effectiveness_score"] < 0.4)
    high_performers = sum(1 for s in unique_scores if s["effectiveness_score"] >= 0.8)

    # Pending actions
    actions_resp = await execute_async(
        client.table("improvement_actions")
        .select("id", count="exact")
        .eq("status", "pending"),
        op_name="self_improvement_router.dashboard.actions",
    )

    # Unresolved gaps
    gaps_resp = await execute_async(
        client.table("coverage_gaps").select("id", count="exact").eq("resolved", False),
        op_name="self_improvement_router.dashboard.gaps",
    )

    # Total interactions
    interactions_resp = await execute_async(
        client.table("interaction_logs").select("id", count="exact"),
        op_name="self_improvement_router.dashboard.interactions",
    )

    return DashboardSummary(
        total_interactions=interactions_resp.count or 0,
        total_skills_scored=len(unique_scores),
        avg_effectiveness=avg_eff,
        underperformers=underperformers,
        high_performers=high_performers,
        pending_actions=actions_resp.count or 0,
        unresolved_gaps=gaps_resp.count or 0,
    )


@router.get("/scores")
@limiter.limit(get_user_persona_limit)
async def get_skill_scores(
    request: Request,
    limit: int = 50,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Get latest skill effectiveness scores."""
    client = get_service_client()
    resp = await execute_async(
        client.table("skill_scores")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit),
        op_name="self_improvement_router.scores",
    )
    return {"scores": resp.data or []}


@router.get("/actions")
@limiter.limit(get_user_persona_limit)
async def get_improvement_actions(
    request: Request,
    status: str | None = None,
    limit: int = 50,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Get improvement actions, optionally filtered by status."""
    client = get_service_client()
    query = client.table("improvement_actions").select("*")
    if status:
        query = query.eq("status", status)
    resp = await execute_async(
        query.order("created_at", desc=True).limit(limit),
        op_name="self_improvement_router.actions",
    )
    return {"actions": resp.data or []}


@router.get("/gaps")
@limiter.limit(get_user_persona_limit)
async def get_coverage_gaps(
    request: Request,
    resolved: bool | None = False,
    limit: int = 50,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Get coverage gaps, defaults to unresolved."""
    client = get_service_client()
    query = client.table("coverage_gaps").select("*")
    if resolved is not None:
        query = query.eq("resolved", resolved)
    resp = await execute_async(
        query.order("occurrence_count", desc=True).limit(limit),
        op_name="self_improvement_router.gaps",
    )
    return {"gaps": resp.data or []}


@router.post("/run-cycle")
@limiter.limit("2/minute")
async def trigger_improvement_cycle(
    request: Request,
    body: CycleRequest,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Trigger an improvement evaluation cycle."""
    from app.services.self_improvement_engine import SelfImprovementEngine

    engine = SelfImprovementEngine()
    result = await engine.run_improvement_cycle(
        auto_execute=body.auto_execute,
        days=body.days,
    )
    return {"success": True, "result": result}


@router.get("/skills/{name}/history")
@limiter.limit(get_user_persona_limit)
async def get_skill_version_history(
    request: Request,
    name: str,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Get the full version chain for a skill, newest first.

    Returns an ordered list of versions with diff summaries describing
    what changed between consecutive versions.
    """
    client = get_service_client()
    resp = await execute_async(
        client.table("skill_versions")
        .select("*")
        .eq("skill_name", name)
        .order("created_at", desc=True),
        op_name="self_improvement_router.skill_history",
    )
    rows = resp.data or []

    # Build a lookup by id for computing diff summaries
    by_id: dict[str, dict] = {r["id"]: r for r in rows}

    versions: list[dict] = []
    for row in rows:
        knowledge = row.get("knowledge") or ""
        prev_id = row.get("previous_version_id")

        # Compute diff summary
        if prev_id and prev_id in by_id:
            prev_row = by_id[prev_id]
            prev_knowledge = prev_row.get("knowledge") or ""
            prev_ver = prev_row.get("version", "?")
            cur_ver = row.get("version", "?")
            diff_summary = (
                f"Knowledge changed from {len(prev_knowledge)} to {len(knowledge)} chars; "
                f"version {prev_ver} -> {cur_ver}"
            )
        else:
            diff_summary = "Initial version"

        versions.append(
            SkillVersionResponse(
                id=str(row["id"]),
                skill_name=row["skill_name"],
                version=row.get("version", ""),
                knowledge_preview=knowledge[:200],
                previous_version_id=str(prev_id) if prev_id else None,
                source_action_id=str(row["source_action_id"])
                if row.get("source_action_id")
                else None,
                created_by=row.get("created_by", "unknown"),
                created_at=str(row.get("created_at", "")),
                is_active=row.get("is_active", False),
                diff_summary=diff_summary,
            ).model_dump()
        )

    return {
        "skill_name": name,
        "versions": versions,
        "total": len(versions),
    }


@router.post("/interactions/{interaction_id}/feedback")
@limiter.limit("10/minute")
async def submit_interaction_feedback(
    request: Request,
    interaction_id: str,
    body: FeedbackRequest,
    _current_user_id: str = Depends(get_current_user_id),
):
    """Record user feedback on a previously-logged interaction.

    Args:
        interaction_id: UUID of the interaction_logs row to update.
        body: Request body containing the rating (positive/negative/neutral).

    Returns:
        Confirmation with the interaction_id.
    """
    from app.services.interaction_logger import interaction_logger

    await interaction_logger.record_feedback(
        interaction_id=interaction_id,
        feedback=body.rating,
    )
    return {"success": True, "interaction_id": interaction_id}
