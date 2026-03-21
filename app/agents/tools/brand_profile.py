"""Brand Profile Tools — Persistent brand DNA for creative agents.

Provides tools to create, retrieve, and update brand profiles that define
a user's creative identity (voice, visual style, audience, platform rules).
All creative agents read the active brand profile before generating content,
ensuring consistent output across video, image, and copy generation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Session state key where the active brand profile is cached for the current session
BRAND_PROFILE_STATE_KEY = "_active_brand_profile"


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


async def get_brand_profile(
    user_id: str | None = None,
    brand_profile_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve the active brand profile for the current user.

    Returns the user's brand DNA including voice/tone, visual style, audience,
    platform rules, and content guardrails. Creative agents use this to maintain
    consistent brand identity across all generated content.

    If no profile exists, returns a helpful message prompting the user to create one.

    Args:
        user_id: Optional user ID override. Falls back to request context.
        brand_profile_id: Optional specific profile ID. If omitted, returns the default profile.

    Returns:
        Dict with the brand profile data or an empty-state message.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {
            "success": False,
            "error": "No user context available. Cannot retrieve brand profile.",
        }

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        if brand_profile_id:
            result = (
                supabase.table("brand_profiles")
                .select("*")
                .eq("id", brand_profile_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )
        else:
            # Try default profile first, then fall back to most recent
            result = (
                supabase.table("brand_profiles")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_default", True)
                .limit(1)
                .execute()
            )
            if not result.data:
                result = (
                    supabase.table("brand_profiles")
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

        if result.data:
            profile = result.data[0] if isinstance(result.data, list) else result.data
            return {
                "success": True,
                "profile": profile,
                "brand_name": profile.get("brand_name", ""),
                "voice_tone": profile.get("voice_tone", ""),
                "visual_style": profile.get("visual_style", {}),
                "audience_description": profile.get("audience_description", ""),
                "platform_rules": profile.get("platform_rules", {}),
                "content_rules": profile.get("content_rules", []),
            }

        return {
            "success": True,
            "profile": None,
            "message": (
                "No brand profile found. You can create one with update_brand_profile() "
                "to ensure all creative output matches your brand identity. "
                "Tell me about your brand — name, tone, visual style, target audience — "
                "and I'll set it up."
            ),
        }

    except Exception as e:
        logger.error("Failed to retrieve brand profile: %s", e)
        return {"success": False, "error": str(e)}


async def update_brand_profile(
    brand_name: str = "",
    voice_tone: str = "",
    voice_personality: list[str] | None = None,
    voice_examples: str = "",
    tagline: str = "",
    brand_description: str = "",
    visual_style: dict[str, Any] | None = None,
    audience_description: str = "",
    audience_demographics: str = "",
    audience_psychographics: str = "",
    platform_rules: dict[str, Any] | None = None,
    content_rules: list[str] | None = None,
    forbidden_terms: list[str] | None = None,
    required_disclosures: list[str] | None = None,
    preferred_image_style: str = "",
    preferred_video_style: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create or update the user's brand profile (Brand DNA).

    This defines the creative identity used by all content generation agents.
    Only provided fields are updated; omitted fields retain their current values.
    If no profile exists, a new one is created as the default.

    Args:
        brand_name: Company or brand name (e.g., "TechNova").
        voice_tone: Overall tone (e.g., "bold and conversational", "professional", "edgy").
        voice_personality: Personality traits list (e.g., ["witty", "authoritative", "warm"]).
        voice_examples: Example sentences showing the brand voice in action.
        tagline: Brand tagline or slogan.
        brand_description: Brief description of what the brand does.
        visual_style: Dict with keys like color_palette, mood, lighting_style,
            composition_rules, typography, reference_styles.
        audience_description: Who the content is for (e.g., "Gen Z creators on TikTok").
        audience_demographics: Age, location, income, etc.
        audience_psychographics: Values, interests, behaviors.
        platform_rules: Per-platform rules dict (e.g., {"instagram": {"tone": "casual"}}).
        content_rules: List of content guardrails (e.g., ["Always include CTA"]).
        forbidden_terms: Words/phrases to never use.
        required_disclosures: Required disclaimers or disclosures.
        preferred_image_style: Default image style preset (vibrant, minimal, tech, etc.).
        preferred_video_style: Default video style description.
        user_id: Optional user ID override.

    Returns:
        Dict with the created/updated brand profile.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {
            "success": False,
            "error": "No user context available. Cannot update brand profile.",
        }

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    # Build the update payload — only include provided (non-empty) fields
    update_data: dict[str, Any] = {}
    if brand_name:
        update_data["brand_name"] = brand_name
    if voice_tone:
        update_data["voice_tone"] = voice_tone
    if voice_personality is not None:
        update_data["voice_personality"] = voice_personality
    if voice_examples:
        update_data["voice_examples"] = voice_examples
    if tagline:
        update_data["tagline"] = tagline
    if brand_description:
        update_data["brand_description"] = brand_description
    if visual_style is not None:
        update_data["visual_style"] = visual_style
    if audience_description:
        update_data["audience_description"] = audience_description
    if audience_demographics:
        update_data["audience_demographics"] = audience_demographics
    if audience_psychographics:
        update_data["audience_psychographics"] = audience_psychographics
    if platform_rules is not None:
        update_data["platform_rules"] = platform_rules
    if content_rules is not None:
        update_data["content_rules"] = content_rules
    if forbidden_terms is not None:
        update_data["forbidden_terms"] = forbidden_terms
    if required_disclosures is not None:
        update_data["required_disclosures"] = required_disclosures
    if preferred_image_style:
        update_data["preferred_image_style"] = preferred_image_style
    if preferred_video_style:
        update_data["preferred_video_style"] = preferred_video_style

    if not update_data:
        return {
            "success": False,
            "error": "No fields provided to update. Please provide at least one brand attribute.",
        }

    try:
        # Check if a profile already exists
        existing = (
            supabase.table("brand_profiles")
            .select("id")
            .eq("user_id", user_id)
            .eq("is_default", True)
            .limit(1)
            .execute()
        )

        if existing.data:
            # Update existing default profile
            profile_id = existing.data[0]["id"]
            result = (
                supabase.table("brand_profiles")
                .update(update_data)
                .eq("id", profile_id)
                .execute()
            )
            action = "updated"
        else:
            # Create new default profile
            update_data["user_id"] = user_id
            update_data["is_default"] = True
            if not update_data.get("brand_name"):
                update_data["brand_name"] = "My Brand"
            result = supabase.table("brand_profiles").insert(update_data).execute()
            action = "created"

        profile = result.data[0] if result.data else update_data

        return {
            "success": True,
            "action": action,
            "profile": profile,
            "message": (
                f"Brand profile {action} successfully. "
                f"All creative agents will now use this brand identity when generating content."
            ),
        }

    except Exception as e:
        logger.error("Failed to update brand profile: %s", e)
        return {"success": False, "error": str(e)}


async def list_brand_profiles(
    user_id: str | None = None,
) -> dict[str, Any]:
    """List all brand profiles for the current user.

    Useful when the user manages multiple brands or wants to switch between profiles.

    Args:
        user_id: Optional user ID override.

    Returns:
        Dict with list of brand profiles.
    """
    user_id = user_id or _get_request_user_id()
    if not user_id:
        return {"success": False, "error": "No user context available."}

    supabase = _get_supabase_client()
    if not supabase:
        return {"success": False, "error": "Database not configured."}

    try:
        result = (
            supabase.table("brand_profiles")
            .select(
                "id, brand_name, tagline, voice_tone, is_default, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .order("is_default", desc=True)
            .order("updated_at", desc=True)
            .execute()
        )

        return {
            "success": True,
            "profiles": result.data or [],
            "count": len(result.data or []),
        }

    except Exception as e:
        logger.error("Failed to list brand profiles: %s", e)
        return {"success": False, "error": str(e)}


def format_brand_context_block(profile: dict[str, Any]) -> str:
    """Format a brand profile into an instruction block for agent injection.

    This is called by the context_memory_before_model_callback to inject
    brand DNA into the system prompt of creative agents.

    Args:
        profile: The brand profile dict from Supabase.

    Returns:
        Formatted string for system prompt injection.
    """
    if not profile:
        return ""

    lines = ["\n[BRAND DNA — apply this identity to ALL creative output]"]

    brand_name = profile.get("brand_name", "")
    if brand_name:
        lines.append(f"Brand: {brand_name}")
    tagline = profile.get("tagline", "")
    if tagline:
        lines.append(f"Tagline: {tagline}")
    description = profile.get("brand_description", "")
    if description:
        lines.append(f"About: {description}")

    # Voice
    voice_tone = profile.get("voice_tone", "")
    if voice_tone:
        lines.append(f"Voice Tone: {voice_tone}")
    personality = profile.get("voice_personality", [])
    if personality:
        lines.append(f"Personality Traits: {', '.join(personality)}")
    voice_examples = profile.get("voice_examples", "")
    if voice_examples:
        lines.append(f"Voice Examples: {voice_examples}")

    # Visual
    visual = profile.get("visual_style", {})
    if isinstance(visual, dict) and any(visual.values()):
        lines.append("Visual Direction:")
        for key, value in visual.items():
            if value:
                label = key.replace("_", " ").title()
                if isinstance(value, list):
                    lines.append(f"  - {label}: {', '.join(str(v) for v in value)}")
                else:
                    lines.append(f"  - {label}: {value}")

    # Audience
    audience = profile.get("audience_description", "")
    if audience:
        lines.append(f"Target Audience: {audience}")
    demographics = profile.get("audience_demographics", "")
    if demographics:
        lines.append(f"Demographics: {demographics}")
    psychographics = profile.get("audience_psychographics", "")
    if psychographics:
        lines.append(f"Psychographics: {psychographics}")

    # Platform rules
    platform_rules = profile.get("platform_rules", {})
    if isinstance(platform_rules, dict) and platform_rules:
        lines.append("Platform-Specific Rules:")
        for platform, rules in platform_rules.items():
            if isinstance(rules, dict):
                rule_str = ", ".join(f"{k}: {v}" for k, v in rules.items())
                lines.append(f"  - {platform}: {rule_str}")
            else:
                lines.append(f"  - {platform}: {rules}")

    # Content guardrails
    content_rules = profile.get("content_rules", [])
    if content_rules:
        lines.append("Content Rules:")
        for rule in content_rules:
            lines.append(f"  - {rule}")

    forbidden = profile.get("forbidden_terms", [])
    if forbidden:
        lines.append(f"Never Use: {', '.join(forbidden)}")

    disclosures = profile.get("required_disclosures", [])
    if disclosures:
        lines.append("Required Disclosures:")
        for disc in disclosures:
            lines.append(f"  - {disc}")

    # Preferred styles
    img_style = profile.get("preferred_image_style", "")
    if img_style:
        lines.append(f"Default Image Style: {img_style}")
    vid_style = profile.get("preferred_video_style", "")
    if vid_style:
        lines.append(f"Default Video Style: {vid_style}")

    lines.append("[END BRAND DNA]\n")
    return "\n".join(lines)


# Exported tools list
BRAND_PROFILE_TOOLS = [
    get_brand_profile,
    update_brand_profile,
    list_brand_profiles,
]
