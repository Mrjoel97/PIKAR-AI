"""Creative Brief & Concept Exploration Tools.

Provides tools for structured creative planning:
- generate_creative_brief(): Transforms a vague idea into a structured brief
- explore_concepts(): Generates 3 competing creative directions from a brief
- get_creative_brief(): Retrieves a saved brief by ID

These tools implement the "plan before creating" pattern inspired by
professional creative workflows, ensuring all content generation starts
with clear objectives and explored options.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase_client():
    """Get Supabase client from centralized service."""
    try:
        from app.services.supabase import get_service_client

        return get_service_client()
    except (ImportError, ConnectionError):
        return None


def _get_request_user_id() -> str | None:
    """Get the current user ID from the request context."""
    try:
        from app.services.request_context import get_current_user_id

        return get_current_user_id()
    except (ImportError, AttributeError):
        return None


async def generate_creative_brief(
    idea: str,
    goal: str = "",
    target_platform: str = "",
    content_type: str = "",
    additional_context: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Transform a vague idea into a structured creative brief.

    This is the first step in the creative pipeline. It takes a rough idea
    and produces a comprehensive brief that guides all downstream content
    generation (video, image, copy). The brief is stored in Knowledge Vault
    for reference throughout the pipeline.

    Use this BEFORE delegating to VideoDirector, GraphicDesigner, or Copywriter
    to ensure all sub-agents work from the same structured plan.

    Args:
        idea: The raw creative idea or request (e.g., "make a TikTok about our new product launch").
        goal: What the content should achieve (e.g., "drive awareness", "generate leads").
        target_platform: Primary platform (e.g., "Instagram", "TikTok", "YouTube", "LinkedIn").
        content_type: Desired format (e.g., "video ad", "carousel", "blog post", "full campaign").
        additional_context: Any extra details — brand info, product details, audience notes.
        user_id: Optional user ID override.

    Returns:
        Structured creative brief with all fields needed for content generation.
    """
    user_id = user_id or _get_request_user_id()
    brief_id = str(uuid.uuid4())

    # Build the brief structure from the input
    brief = {
        "id": brief_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",

        # Core brief fields
        "original_idea": idea,
        "goal": goal or "Not specified — infer from the idea and context",
        "target_platform": target_platform or "Not specified — recommend based on content type",
        "content_type": content_type or "Not specified — recommend based on the idea",

        # Structured planning fields (to be filled by the agent)
        "objective": "",
        "target_audience": "",
        "key_messages": [],
        "tone_and_voice": "",
        "visual_direction": "",
        "call_to_action": "",
        "success_criteria": [],
        "constraints": [],
        "deliverables": [],
        "additional_context": additional_context,

        # Pipeline tracking
        "pipeline_stage": "brief",
        "selected_concept_id": None,
    }

    # Load brand profile for context enrichment
    brand_context = ""
    if user_id:
        try:
            from app.agents.tools.brand_profile import format_brand_context_block

            supabase = _get_supabase_client()
            if supabase:
                result = (
                    supabase.table("brand_profiles")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("is_default", True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    profile = result.data[0]
                    brand_context = format_brand_context_block(profile)

                    # Auto-populate brief fields from brand profile
                    if not brief["target_audience"] and profile.get("audience_description"):
                        brief["target_audience"] = profile["audience_description"]
                    if not brief["tone_and_voice"] and profile.get("voice_tone"):
                        brief["tone_and_voice"] = profile["voice_tone"]
                    if not brief["visual_direction"] and profile.get("visual_style"):
                        vs = profile["visual_style"]
                        if isinstance(vs, dict) and vs.get("mood"):
                            brief["visual_direction"] = vs["mood"]
        except Exception as exc:
            logger.debug("Brand profile enrichment skipped: %s", exc)

    # Save to Knowledge Vault for pipeline continuity
    if user_id:
        supabase = _get_supabase_client()
        if supabase:
            try:
                supabase.table("knowledge_vault").insert({
                    "id": brief_id,
                    "user_id": user_id,
                    "title": f"Creative Brief: {idea[:80]}",
                    "content": json.dumps(brief, default=str),
                    "document_type": "creative_brief",
                    "metadata": {
                        "pipeline_stage": "brief",
                        "content_type": content_type,
                        "platform": target_platform,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            except Exception as exc:
                logger.warning("Failed to save brief to Knowledge Vault: %s", exc)

    return {
        "success": True,
        "brief": brief,
        "brief_id": brief_id,
        "brand_context": brand_context,
        "message": (
            "Creative brief generated. Review the structured plan above, then:\n"
            "1. Fill in any empty fields based on the idea and context\n"
            "2. Use explore_concepts() to generate 3 creative directions\n"
            "3. Select a concept and delegate to the appropriate sub-agent"
        ),
        "next_step": "explore_concepts",
    }


async def explore_concepts(
    brief_id: str = "",
    idea: str = "",
    goal: str = "",
    target_audience: str = "",
    tone: str = "",
    platform: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Generate 3 competing creative concepts from a brief or idea.

    Each concept offers a different angle, hook, and visual approach.
    This divergent thinking step ensures the best creative direction is
    chosen before committing to expensive generation (video, images).

    Can be called with a brief_id (to load a saved brief) or with
    individual fields for a quick exploration.

    Args:
        brief_id: ID of a saved creative brief to expand into concepts.
        idea: The creative idea (used if no brief_id provided).
        goal: Content objective.
        target_audience: Who the content is for.
        tone: Desired voice/tone.
        platform: Target platform.
        user_id: Optional user ID override.

    Returns:
        Dict with 3 concept options, each with hook, angle, visual mood, and rationale.
    """
    user_id = user_id or _get_request_user_id()

    # Load brief if ID provided
    brief_data = {}
    if brief_id and user_id:
        supabase = _get_supabase_client()
        if supabase:
            try:
                result = (
                    supabase.table("knowledge_vault")
                    .select("content")
                    .eq("id", brief_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
                if result.data:
                    content = result.data.get("content", "{}")
                    brief_data = json.loads(content) if isinstance(content, str) else content
            except Exception as exc:
                logger.warning("Failed to load brief %s: %s", brief_id, exc)

    # Use brief data or fallback to direct params
    effective_idea = brief_data.get("original_idea") or idea
    effective_goal = brief_data.get("goal") or goal
    effective_audience = brief_data.get("target_audience") or target_audience
    effective_tone = brief_data.get("tone_and_voice") or tone
    effective_platform = brief_data.get("target_platform") or platform

    if not effective_idea:
        return {
            "success": False,
            "error": "No idea or brief_id provided. Provide either a creative idea or a brief ID.",
        }

    # Generate 3 concept structures for the agent to flesh out
    concepts = [
        {
            "concept_id": str(uuid.uuid4()),
            "number": 1,
            "name": "Concept A — The Direct Hit",
            "angle": "",
            "hook": "",
            "visual_mood": "",
            "narrative_arc": "",
            "key_scenes_or_elements": [],
            "cta": "",
            "rationale": "",
            "best_for": "Driving immediate action and clear messaging",
        },
        {
            "concept_id": str(uuid.uuid4()),
            "number": 2,
            "name": "Concept B — The Story",
            "angle": "",
            "hook": "",
            "visual_mood": "",
            "narrative_arc": "",
            "key_scenes_or_elements": [],
            "cta": "",
            "rationale": "",
            "best_for": "Emotional connection and brand recall",
        },
        {
            "concept_id": str(uuid.uuid4()),
            "number": 3,
            "name": "Concept C — The Disruptor",
            "angle": "",
            "hook": "",
            "visual_mood": "",
            "narrative_arc": "",
            "key_scenes_or_elements": [],
            "cta": "",
            "rationale": "",
            "best_for": "Virality and standing out from competitors",
        },
    ]

    # Save concepts to Knowledge Vault
    concepts_id = str(uuid.uuid4())
    if user_id:
        supabase = _get_supabase_client()
        if supabase:
            try:
                supabase.table("knowledge_vault").insert({
                    "id": concepts_id,
                    "user_id": user_id,
                    "title": f"Creative Concepts: {effective_idea[:60]}",
                    "content": json.dumps({
                        "brief_id": brief_id or None,
                        "idea": effective_idea,
                        "goal": effective_goal,
                        "audience": effective_audience,
                        "tone": effective_tone,
                        "platform": effective_platform,
                        "concepts": concepts,
                    }, default=str),
                    "document_type": "creative_concepts",
                    "metadata": {
                        "pipeline_stage": "concepts",
                        "brief_id": brief_id or None,
                        "concept_count": 3,
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            except Exception as exc:
                logger.warning("Failed to save concepts to Knowledge Vault: %s", exc)

    return {
        "success": True,
        "concepts_id": concepts_id,
        "brief_id": brief_id or None,
        "context": {
            "idea": effective_idea,
            "goal": effective_goal,
            "audience": effective_audience,
            "tone": effective_tone,
            "platform": effective_platform,
        },
        "concepts": concepts,
        "message": (
            "3 concept templates generated. For each concept, fill in:\n"
            "- **angle**: The unique perspective or approach\n"
            "- **hook**: The opening line/visual that grabs attention\n"
            "- **visual_mood**: Color, lighting, energy, style\n"
            "- **narrative_arc**: Beginning → middle → end structure\n"
            "- **key_scenes_or_elements**: Specific shots/visuals/copy elements\n"
            "- **cta**: Call to action\n"
            "- **rationale**: Why this concept works for the goal\n\n"
            "Then recommend one concept to the user, or ask them to choose."
        ),
        "next_step": "select_concept_and_delegate",
    }


async def get_creative_brief(
    brief_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve a saved creative brief by ID.

    Args:
        brief_id: The UUID of the creative brief.
        user_id: Optional user ID override.

    Returns:
        The full creative brief data.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        result = (
            supabase.table("knowledge_vault")
            .select("*")
            .eq("id", brief_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if result.data:
            content = result.data.get("content", "{}")
            brief = json.loads(content) if isinstance(content, str) else content
            return {
                "success": True,
                "brief": brief,
                "brief_id": brief_id,
                "document_type": result.data.get("document_type"),
            }

        return {"success": False, "error": f"Brief {brief_id} not found."}

    except Exception as e:
        logger.error("Failed to retrieve brief: %s", e)
        return {"success": False, "error": str(e)}


# Exported tools list
CREATIVE_BRIEF_TOOLS = [
    generate_creative_brief,
    explore_concepts,
    get_creative_brief,
]
