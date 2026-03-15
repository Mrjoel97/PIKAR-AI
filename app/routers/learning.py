"""Learning router — courses catalog and user progress tracking."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["Learning"])


class CourseResponse(BaseModel):
    """Response model for a learning course."""

    id: str
    title: str
    description: Optional[str] = None
    category: str
    difficulty: str
    duration_minutes: int
    lessons_count: int
    thumbnail_gradient: Optional[str] = None
    is_recommended: bool
    sort_order: int
    created_at: str


class ProgressResponse(BaseModel):
    """Response model for learning progress."""

    id: str
    user_id: str
    course_id: str
    progress_percent: float
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: str
    learning_courses: Optional[CourseResponse] = None


class UpdateProgressRequest(BaseModel):
    """Request body for updating progress."""

    progress_percent: float


@router.get("/courses", response_model=List[CourseResponse])
@limiter.limit(get_user_persona_limit)
async def list_courses(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    category: Optional[str] = None,
) -> List[dict]:
    """List available learning courses."""
    supabase = get_service_client()
    query = supabase.table("learning_courses").select("*").order("sort_order")
    if category:
        query = query.eq("category", category)
    response = query.execute()
    return response.data or []


@router.get("/progress", response_model=List[ProgressResponse])
@limiter.limit(get_user_persona_limit)
async def get_progress(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> List[dict]:
    """Get learning progress for the current user."""
    supabase = get_service_client()
    response = (
        supabase.table("learning_progress")
        .select("*, learning_courses(*)")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data or []


@router.post("/progress/{course_id}/start", response_model=ProgressResponse, status_code=201)
@limiter.limit(get_user_persona_limit)
async def start_course(
    request: Request,
    course_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Start a course (create progress record)."""
    supabase = get_service_client()

    # Check course exists
    course_check = supabase.table("learning_courses").select("id").eq("id", course_id).execute()
    if not course_check.data:
        raise HTTPException(status_code=404, detail="Course not found")

    # Upsert progress (handles re-starting)
    response = (
        supabase.table("learning_progress")
        .upsert(
            {
                "user_id": user_id,
                "course_id": course_id,
                "status": "in_progress",
                "progress_percent": 0,
                "started_at": "now()",
            },
            on_conflict="user_id,course_id",
        )
        .execute()
    )
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to start course")


@router.patch("/progress/{course_id}", response_model=ProgressResponse)
@limiter.limit(get_user_persona_limit)
async def update_progress(
    request: Request,
    course_id: str,
    body: UpdateProgressRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Update learning progress for a course."""
    supabase = get_service_client()

    update_data = {"progress_percent": body.progress_percent}
    if body.progress_percent >= 100:
        update_data["status"] = "completed"
        update_data["completed_at"] = "now()"
    elif body.progress_percent > 0:
        update_data["status"] = "in_progress"

    response = (
        supabase.table("learning_progress")
        .update(update_data)
        .eq("user_id", user_id)
        .eq("course_id", course_id)
        .execute()
    )
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=404, detail="Progress record not found")
