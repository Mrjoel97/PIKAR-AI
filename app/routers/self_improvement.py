"""Self-Improvement API Router.

Dashboard endpoints for viewing skill scores, improvement actions,
coverage gaps, and triggering evaluation cycles.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import limiter, get_user_persona_limit
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
    trend: Optional[str] = None
    score_delta: Optional[float] = None
    created_at: Optional[str] = None


class ImprovementActionResponse(BaseModel):
    id: str
    action_type: str
    skill_name: Optional[str] = None
    agent_id: Optional[str] = None
    trigger_reason: str
    status: str
    effectiveness_before: Optional[float] = None
    effectiveness_after: Optional[float] = None
    created_at: Optional[str] = None


class CoverageGapResponse(BaseModel):
    id: str
    user_query: str
    agent_id: str
    matched_skills: Optional[list] = None
    confidence_score: float
    occurrence_count: int
    resolved: bool
    created_at: Optional[str] = None


class DashboardSummary(BaseModel):
    total_interactions: int
    total_skills_scored: int
    avg_effectiveness: float
    underperformers: int
    high_performers: int
    pending_actions: int
    unresolved_gaps: int


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
        client.table("coverage_gaps")
        .select("id", count="exact")
        .eq("resolved", False),
        op_name="self_improvement_router.dashboard.gaps",
    )

    # Total interactions
    interactions_resp = await execute_async(
        client.table("interaction_logs")
        .select("id", count="exact"),
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
    status: Optional[str] = None,
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
    resolved: Optional[bool] = False,
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
