"""Art Direction Tools — Visual contracts for consistent creative output.

Provides tools to create and retrieve art direction contracts that define
the visual identity for a content pipeline run. Both image generation
(generate_image) and video generation (create_video_with_veo) can read
these contracts to ensure visual consistency across all assets.
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


async def create_art_direction(
    mood: str = "",
    color_palette: list[str] | None = None,
    lighting_style: str = "",
    composition_rules: str = "",
    typography: str = "",
    reference_styles: list[str] | None = None,
    image_style_preset: str = "",
    aspect_ratio: str = "",
    visual_energy: str = "",
    texture_and_finish: str = "",
    brand_elements: str = "",
    do_not_include: list[str] | None = None,
    brief_id: str = "",
    concept_id: str = "",
    notes: str = "",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create an art direction contract that defines the visual identity for a content pipeline.

    This contract ensures visual consistency across ALL generated assets (images, videos,
    graphics) in a campaign or content run. Once created, pass the art_direction_id to
    generate_image() or create_video_with_veo() to apply these visual parameters automatically.

    Use this AFTER selecting a creative concept and BEFORE generating any visual assets.

    Args:
        mood: Overall visual mood (e.g., "warm and inviting", "dark and cinematic", "bright and playful").
        color_palette: List of hex colors or color descriptions (e.g., ["#FF6B35", "#004E89", "warm gold"]).
        lighting_style: Lighting approach (e.g., "golden hour", "studio lighting", "neon glow", "natural daylight").
        composition_rules: Framing and layout guidelines (e.g., "rule of thirds", "centered subject", "negative space heavy").
        typography: Font/text style guidance (e.g., "bold sans-serif", "handwritten script", "minimal mono").
        reference_styles: Style references (e.g., ["Wes Anderson symmetry", "Apple product photography", "lo-fi analog"]).
        image_style_preset: Preferred Imagen style preset (vibrant, minimal, tech, organic, bold, surreal, professional).
        aspect_ratio: Default aspect ratio (e.g., "16:9", "9:16", "1:1", "4:3").
        visual_energy: Energy level (e.g., "calm and serene", "high energy kinetic", "contemplative").
        texture_and_finish: Surface quality (e.g., "matte and clean", "grainy film stock", "glossy and polished").
        brand_elements: Brand-specific visual elements to include (e.g., "logo watermark bottom-right", "brand gradient overlay").
        do_not_include: Visual elements to explicitly avoid (e.g., ["stock photo people", "generic office backgrounds"]).
        brief_id: Link to the creative brief this art direction serves.
        concept_id: Link to the selected creative concept.
        notes: Free-form art direction notes.
        user_id: Optional user ID override.

    Returns:
        Dict with the art direction contract and its ID for pipeline use.
    """
    user_id = user_id or _get_request_user_id()
    art_direction_id = str(uuid.uuid4())

    contract = {
        "id": art_direction_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "brief_id": brief_id or None,
        "concept_id": concept_id or None,

        # Visual parameters
        "mood": mood,
        "color_palette": color_palette or [],
        "lighting_style": lighting_style,
        "composition_rules": composition_rules,
        "typography": typography,
        "reference_styles": reference_styles or [],
        "image_style_preset": image_style_preset or "vibrant",
        "aspect_ratio": aspect_ratio,
        "visual_energy": visual_energy,
        "texture_and_finish": texture_and_finish,
        "brand_elements": brand_elements,
        "do_not_include": do_not_include or [],
        "notes": notes,
    }

    # Enrich from brand profile if available
    if user_id:
        try:
            supabase = _get_supabase_client()
            if supabase:
                result = (
                    supabase.table("brand_profiles")
                    .select("visual_style, preferred_image_style")
                    .eq("user_id", user_id)
                    .eq("is_default", True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    profile = result.data[0]
                    vs = profile.get("visual_style", {})
                    if isinstance(vs, dict):
                        # Only fill in empty fields from brand profile
                        if not contract["color_palette"] and vs.get("color_palette"):
                            contract["color_palette"] = vs["color_palette"]
                        if not contract["mood"] and vs.get("mood"):
                            contract["mood"] = vs["mood"]
                        if not contract["lighting_style"] and vs.get("lighting_style"):
                            contract["lighting_style"] = vs["lighting_style"]
                        if not contract["composition_rules"] and vs.get("composition_rules"):
                            contract["composition_rules"] = vs["composition_rules"]
                        if not contract["typography"] and vs.get("typography"):
                            contract["typography"] = vs["typography"]
                        if not contract["reference_styles"] and vs.get("reference_styles"):
                            contract["reference_styles"] = vs["reference_styles"]
                    pref_style = profile.get("preferred_image_style", "")
                    if not image_style_preset and pref_style:
                        contract["image_style_preset"] = pref_style
        except Exception as exc:
            logger.debug("Brand visual enrichment skipped: %s", exc)

    # Save to Knowledge Vault
    if user_id:
        supabase = _get_supabase_client()
        if supabase:
            try:
                supabase.table("knowledge_vault").insert({
                    "id": art_direction_id,
                    "user_id": user_id,
                    "title": f"Art Direction: {mood or 'Custom'} — {', '.join(contract['color_palette'][:3]) or 'palette TBD'}",
                    "content": json.dumps(contract, default=str),
                    "document_type": "art_direction",
                    "metadata": {
                        "pipeline_stage": "art_direction",
                        "brief_id": brief_id or None,
                        "concept_id": concept_id or None,
                        "style_preset": contract["image_style_preset"],
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            except Exception as exc:
                logger.warning("Failed to save art direction to Knowledge Vault: %s", exc)

    return {
        "success": True,
        "art_direction_id": art_direction_id,
        "contract": contract,
        "message": (
            "Art direction contract created. Pass art_direction_id to generate_image() "
            "or create_video_with_veo() to apply this visual identity to all generated assets.\n\n"
            f"Art Direction ID: {art_direction_id}"
        ),
        "next_step": "generate_assets_with_art_direction",
    }


async def get_art_direction(
    art_direction_id: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve a saved art direction contract by ID.

    Args:
        art_direction_id: The UUID of the art direction contract.
        user_id: Optional user ID override.

    Returns:
        The full art direction contract data.
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
            .eq("id", art_direction_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if result.data:
            content = result.data.get("content", "{}")
            contract = json.loads(content) if isinstance(content, str) else content
            return {
                "success": True,
                "contract": contract,
                "art_direction_id": art_direction_id,
            }

        return {"success": False, "error": f"Art direction {art_direction_id} not found."}

    except Exception as e:
        logger.error("Failed to retrieve art direction: %s", e)
        return {"success": False, "error": str(e)}


def build_art_direction_prompt_modifier(contract: dict[str, Any]) -> str:
    """Build a prompt modifier string from an art direction contract.

    This is used by generate_image() and create_video_with_veo() to inject
    visual parameters into the generation prompt.

    Args:
        contract: The art direction contract dict.

    Returns:
        String to append to generation prompts for visual consistency.
    """
    if not contract:
        return ""

    parts = []

    mood = contract.get("mood", "")
    if mood:
        parts.append(f"Mood: {mood}")

    colors = contract.get("color_palette", [])
    if colors:
        parts.append(f"Color palette: {', '.join(str(c) for c in colors)}")

    lighting = contract.get("lighting_style", "")
    if lighting:
        parts.append(f"Lighting: {lighting}")

    composition = contract.get("composition_rules", "")
    if composition:
        parts.append(f"Composition: {composition}")

    energy = contract.get("visual_energy", "")
    if energy:
        parts.append(f"Energy: {energy}")

    texture = contract.get("texture_and_finish", "")
    if texture:
        parts.append(f"Texture: {texture}")

    refs = contract.get("reference_styles", [])
    if refs:
        parts.append(f"Style references: {', '.join(refs)}")

    brand_elements = contract.get("brand_elements", "")
    if brand_elements:
        parts.append(f"Brand elements: {brand_elements}")

    do_not = contract.get("do_not_include", [])
    if do_not:
        parts.append(f"Avoid: {', '.join(do_not)}")

    notes = contract.get("notes", "")
    if notes:
        parts.append(f"Notes: {notes}")

    if not parts:
        return ""

    return " | ".join(parts)


# Exported tools list
ART_DIRECTION_TOOLS = [
    create_art_direction,
    get_art_direction,
]
