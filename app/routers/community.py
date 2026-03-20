"""Community router — posts, comments, and upvotes for community forum."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/community", tags=["Community"])


class CreatePostRequest(BaseModel):
    """Request body for creating a community post."""

    title: str
    body: str
    category: str | None = "general"
    tags: list[str] | None = None


class PostResponse(BaseModel):
    """Response model for a community post."""

    id: str
    user_id: str
    author_name: str
    title: str
    body: str
    category: str
    tags: list[str]
    upvotes: int
    reply_count: int
    is_pinned: bool
    created_at: str
    updated_at: str


class CommentResponse(BaseModel):
    """Response model for a community comment."""

    id: str
    post_id: str
    user_id: str
    author_name: str
    body: str
    upvotes: int
    created_at: str


class CreateCommentRequest(BaseModel):
    """Request body for creating a comment."""

    body: str


class UpvoteResponse(BaseModel):
    """Response model for upvote toggle."""

    upvoted: bool
    upvotes: int


@router.get("/posts", response_model=list[PostResponse])
@limiter.limit(get_user_persona_limit)
async def list_posts(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    category: str | None = None,
    sort: Literal["recent", "popular"] = "recent",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """List community posts with optional filters."""
    supabase = get_service_client()
    query = supabase.table("community_posts").select("*")
    if category:
        query = query.eq("category", category)
    if sort == "popular":
        query = query.order("upvotes", desc=True)
    else:
        query = query.order("created_at", desc=True)
    query = query.range(offset, offset + limit - 1)
    response = query.execute()
    return response.data or []


@router.post("/posts", response_model=PostResponse, status_code=201)
@limiter.limit(get_user_persona_limit)
async def create_post(
    request: Request,
    body: CreatePostRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Create a new community post."""
    supabase = get_service_client()

    # Get author name from user profile
    profile = (
        supabase.table("users_profile").select("full_name").eq("id", user_id).execute()
    )
    author_name = profile.data[0]["full_name"] if profile.data else "Anonymous"

    response = (
        supabase.table("community_posts")
        .insert(
            {
                "user_id": user_id,
                "author_name": author_name,
                "title": body.title,
                "body": body.body,
                "category": body.category or "general",
                "tags": body.tags or [],
            }
        )
        .execute()
    )
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to create post")


@router.get("/posts/{post_id}")
@limiter.limit(get_user_persona_limit)
async def get_post(
    request: Request,
    post_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Get a single post with its comments."""
    supabase = get_service_client()

    post_resp = (
        supabase.table("community_posts").select("*").eq("id", post_id).execute()
    )
    if not post_resp.data:
        raise HTTPException(status_code=404, detail="Post not found")

    comments_resp = (
        supabase.table("community_comments")
        .select("*")
        .eq("post_id", post_id)
        .order("created_at")
        .execute()
    )

    return {
        "post": post_resp.data[0],
        "comments": comments_resp.data or [],
    }


@router.post(
    "/posts/{post_id}/comments", response_model=CommentResponse, status_code=201
)
@limiter.limit(get_user_persona_limit)
async def add_comment(
    request: Request,
    post_id: str,
    body: CreateCommentRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Add a comment to a post."""
    supabase = get_service_client()

    # Verify post exists
    post_check = (
        supabase.table("community_posts").select("id").eq("id", post_id).execute()
    )
    if not post_check.data:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get author name
    profile = (
        supabase.table("users_profile").select("full_name").eq("id", user_id).execute()
    )
    author_name = profile.data[0]["full_name"] if profile.data else "Anonymous"

    response = (
        supabase.table("community_comments")
        .insert(
            {
                "post_id": post_id,
                "user_id": user_id,
                "author_name": author_name,
                "body": body.body,
            }
        )
        .execute()
    )
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to add comment")


@router.post("/posts/{post_id}/upvote", response_model=UpvoteResponse)
@limiter.limit(get_user_persona_limit)
async def toggle_upvote(
    request: Request,
    post_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Toggle upvote on a post."""
    supabase = get_service_client()

    # Check if already upvoted
    existing = (
        supabase.table("community_upvotes")
        .select("user_id")
        .eq("user_id", user_id)
        .eq("post_id", post_id)
        .execute()
    )

    if existing.data:
        # Remove upvote
        supabase.table("community_upvotes").delete().eq("user_id", user_id).eq(
            "post_id", post_id
        ).execute()
        # Decrement count
        post = (
            supabase.table("community_posts")
            .select("upvotes")
            .eq("id", post_id)
            .execute()
        )
        new_count = max(0, (post.data[0]["upvotes"] if post.data else 1) - 1)
        supabase.table("community_posts").update({"upvotes": new_count}).eq(
            "id", post_id
        ).execute()
        return {"upvoted": False, "upvotes": new_count}
    else:
        # Add upvote
        supabase.table("community_upvotes").insert(
            {"user_id": user_id, "post_id": post_id}
        ).execute()
        # Increment count
        post = (
            supabase.table("community_posts")
            .select("upvotes")
            .eq("id", post_id)
            .execute()
        )
        new_count = (post.data[0]["upvotes"] if post.data else 0) + 1
        supabase.table("community_posts").update({"upvotes": new_count}).eq(
            "id", post_id
        ).execute()
        return {"upvoted": True, "upvotes": new_count}
