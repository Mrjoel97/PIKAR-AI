"""Canva Media Creation MCP Tool.

Provides media creation capabilities including:
- Canva design creation and access
- AI image generation using nano-banana skill
- Video creation using remotion skill
- Social media graphic generation
"""

import asyncio
import logging
import os
import uuid
from typing import Any

from app.mcp.security.audit_logger import log_mcp_call
from app.mcp.security.external_call_guard import protect_text_payload

logger = logging.getLogger(__name__)

# Canva API configuration
CANVA_API_KEY = os.getenv("CANVA_API_KEY", "")
CANVA_API_BASE = "https://api.canva.com/rest/v1"

# Duration routing: Veo supports ~4-8s; longer videos use server-side Remotion when enabled.
VEO_MAX_DURATION_SECONDS = int(os.getenv("VEO_MAX_DURATION_SECONDS", "8"))


class CanvaMCPTool:
    """Canva MCP Tool for media creation and management."""

    # Supported design types
    DESIGN_TYPES = {
        "instagram_post": {"width": 1080, "height": 1080},
        "instagram_story": {"width": 1080, "height": 1920},
        "facebook_post": {"width": 1200, "height": 630},
        "twitter_post": {"width": 1600, "height": 900},
        "linkedin_post": {"width": 1200, "height": 627},
        "tiktok_video": {"width": 1080, "height": 1920},
        "youtube_thumbnail": {"width": 1280, "height": 720},
        "presentation": {"width": 1920, "height": 1080},
        "banner": {"width": 1920, "height": 600},
        "logo": {"width": 500, "height": 500},
    }

    # Style presets for nano-banana
    NANO_BANANA_STYLES = {
        "vibrant": "vibrant colors, high saturation, energetic, modern",
        "minimal": "minimalist, clean lines, subtle colors, elegant",
        "tech": "futuristic, digital, glowing elements, dark background",
        "organic": "natural, earthy tones, flowing shapes, organic textures",
        "bold": "bold colors, strong contrast, impactful, attention-grabbing",
        "surreal": "surrealistic, dreamlike, floating elements, artistic",
        "professional": "corporate, clean, trustworthy, business-appropriate",
    }

    def __init__(self):
        self._supabase = None

    @property
    def supabase(self):
        """Get Supabase client for storage."""
        if self._supabase is None:
            try:
                from app.services.supabase import get_service_client

                self._supabase = get_service_client()
            except Exception as e:
                logger.warning(f"Failed to get Supabase client: {e}")
        return self._supabase

    def is_canva_configured(self) -> bool:
        """Check if Canva API is configured."""
        return bool(CANVA_API_KEY and len(CANVA_API_KEY) > 10)

    async def create_design_with_canva(
        self,
        design_type: str,
        title: str,
        content: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a design using Canva API."""
        if not self.is_canva_configured():
            return {"error": "Canva not configured. Please add your CANVA_API_KEY."}

        import httpx

        dimensions = self.DESIGN_TYPES.get(design_type, {"width": 1080, "height": 1080})
        title_guard = protect_text_payload(title, field_name="design_title")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CANVA_API_BASE}/designs",
                    headers={
                        "Authorization": f"Bearer {CANVA_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "design_type": {
                            "width": dimensions["width"],
                            "height": dimensions["height"],
                        },
                        "title": title_guard.outbound_value,
                    },
                    timeout=30.0,
                )

            if response.status_code == 200:
                data = response.json()
                log_mcp_call(
                    tool_name="canva_create_design",
                    query_sanitized=title_guard.audit_value,
                    success=True,
                    response_status="success",
                    metadata={**title_guard.metadata, "design_type": design_type},
                )
                return {
                    "success": True,
                    "design_id": data.get("design", {}).get("id"),
                    "edit_url": data.get("design", {}).get("urls", {}).get("edit_url"),
                    "view_url": data.get("design", {}).get("urls", {}).get("view_url"),
                    "title": title_guard.outbound_value,
                    "dimensions": dimensions,
                }

            error_message = f"Canva API error: {response.text}"
            log_mcp_call(
                tool_name="canva_create_design",
                query_sanitized=title_guard.audit_value,
                success=False,
                response_status="error",
                error_message=error_message,
                metadata={
                    **title_guard.metadata,
                    "design_type": design_type,
                    "status_code": response.status_code,
                },
            )
            return {"error": error_message}

        except Exception as e:
            logger.error(f"Canva design creation failed: {e}")
            log_mcp_call(
                tool_name="canva_create_design",
                query_sanitized=title_guard.audit_value,
                success=False,
                response_status="error",
                error_message=str(e),
                metadata={**title_guard.metadata, "design_type": design_type},
            )
            return {"error": str(e)}

    def _dimensions_to_aspect_ratio(self, dimensions: dict[str, int] | None) -> str:
        """Map width/height to Vertex aspect ratio."""
        if not dimensions:
            return "1:1"
        w = dimensions.get("width") or 1080
        h = dimensions.get("height") or 1080
        if w == h:
            return "1:1"
        if w > h:
            if w / h >= 1.7:
                return "16:9"
            return "4:3"
        if h / w >= 1.7:
            return "9:16"
        return "3:4"

    async def generate_social_post(
        self,
        platform: str,
        text: str,
        style: str = "vibrant",
        include_image: bool = True,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a complete social media post with image.

        Args:
            platform: Target platform (instagram, facebook, twitter, linkedin, tiktok)
            text: Post text/caption
            style: Visual style for the image
            include_image: Whether to generate an accompanying image
            user_id: User ID for storage

        Returns:
            Complete social post with image spec
        """
        design_type_map = {
            "instagram": "instagram_post",
            "facebook": "facebook_post",
            "twitter": "twitter_post",
            "linkedin": "linkedin_post",
            "tiktok": "tiktok_video",
        }

        design_type = design_type_map.get(platform, "instagram_post")
        dimensions = self.DESIGN_TYPES.get(design_type, {"width": 1080, "height": 1080})

        result = {
            "success": True,
            "platform": platform,
            "text": text,
            "dimensions": dimensions,
        }

        if include_image:
            # Use the new decoupled media generation tool
            from app.agents.tools.media import generate_image

            image_prompt = (
                f"Social media graphic for {platform}. Content theme: {text[:100]}"
            )
            image_result = await generate_image(
                prompt=image_prompt,
                style=style,
                dimensions=dimensions,
                user_id=user_id,
            )
            result["image"] = image_result

        return result


# Singleton instance
_canva_tool: CanvaMCPTool | None = None


def get_canva_tool() -> CanvaMCPTool:
    """Get singleton Canva tool instance."""
    global _canva_tool
    if _canva_tool is None:
        _canva_tool = CanvaMCPTool()
    return _canva_tool


# ============================================================================
# Agent Tool Functions
# ============================================================================


async def create_image(
    prompt: str,
    style: str = "vibrant",
    platform: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create an AI-generated image using Imagen with nano-banana style presets.

    Use for high-quality images: marketing, social media, infographics, hero visuals.
    Generation uses Vertex Imagen (Imagen 4/3) with nano-banana style presets; apply
    the nano-banana skill (vibrancy, cohesion, prompting strategy) for best quality.
    Image is saved to the user's Knowledge Vault → Media Files.

    Args:
        prompt: Description of the image to create (for infographics, describe sections and content).
        style: Visual style (vibrant, minimal, tech, organic, bold, surreal, professional)
        platform: Target platform for sizing (instagram, facebook, twitter, etc.)
        user_id: Optional; if not provided, the current request user is used for saving to their vault.

    Returns:
        Image widget (imageUrl, asset_id) or error.
    """
    from app.agents.tools import media

    dimensions = None
    if platform:
        design_type_map = {
            "instagram": "instagram_post",
            "facebook": "facebook_post",
            "twitter": "twitter_post",
            "linkedin": "linkedin_post",
        }
        design_type = design_type_map.get(platform, "instagram_post")
        # Access DESIGN_TYPES from the class directly or instance
        dimensions = CanvaMCPTool.DESIGN_TYPES.get(design_type)

    return await media.generate_image(
        prompt=prompt,
        style=style,
        dimensions=dimensions,
        user_id=user_id,
    )


async def create_video(
    title: str,
    scenes: list[dict[str, Any]],
    duration: int = 30,
    style: str = "modern",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create a programmatic (scene-based) video using Remotion.

    Generates Remotion composition code for multi-scene or template-style videos.
    For "one prompt → one MP4" (user says "create a 30 second video about X"),
    prefer create_video_with_veo: the backend uses VEO 3 for short clips and
    server-side Remotion for longer durations, returning a single playable MP4.
    Use create_video when you need explicit scene list and Remotion structure.
    """
    from app.agents.tools.media import (
        _get_supabase_client,
        _save_and_return_video_widget,
    )
    from app.services.remotion_render_service import render_programmatic_video
    from app.services.request_context import get_current_user_id

    user_id = user_id or get_current_user_id()
    if not user_id:
        return {"success": False, "error": "User ID required"}

    # Construct props for Remotion
    fps = 30
    duration_frames = max(1, duration * fps)

    # Normalize scenes
    remotion_scenes = []
    for s in scenes:
        scene_duration = int(s.get("duration", 4))
        text = str(s.get("text", "") or s.get("description", ""))
        remotion_scenes.append(
            {
                "text": text,
                "duration": scene_duration,
                "imageUrl": s.get("image_url", ""),
                "videoUrl": s.get("video_url", ""),
                "voiceoverUrl": s.get("voiceover_url", ""),
                "captions": [
                    {
                        "text": text,
                        "startFrame": 0,
                        "endFrame": max(1, scene_duration * fps - 1),
                    }
                ]
                if text
                else [],
                "transition": {"type": "fade", "durationFrames": 15},
            }
        )

    props = {
        "scenes": remotion_scenes,
        "fps": fps,
        "durationInFrames": duration_frames,
        "bgMusicVolume": 0.35,
        "voiceoverVolume": 1.0,
    }

    try:
        mp4_bytes, asset_id = await asyncio.to_thread(
            render_programmatic_video, props, user_id
        )
        if not mp4_bytes:
            return {
                "success": False,
                "error": "Remotion render failed",
                "user_message": "Programmatic video rendering failed.",
            }

        supabase = _get_supabase_client()
        if supabase:
            return await _save_and_return_video_widget(
                supabase,
                user_id,
                asset_id or str(uuid.uuid4()),
                mp4_bytes,
                title,
                duration,
                "programmatic-remotion",
            )

        return {
            "success": True,
            "video_bytes": mp4_bytes,
            "user_message": "Programmatic video generated successfully.",
        }
    except Exception as e:
        logger.error(f"Programmatic video creation error: {e}")
        return {"success": False, "error": str(e)}


async def create_video_with_veo(
    prompt: str,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create a video from a text prompt; uses VEO 3 or server-side Remotion by duration.

    Pass duration_seconds (e.g. 10, 15, 28, 30, 60, 180). For durations longer than
    8 seconds, the backend uses server-side Remotion when REMOTION_RENDER_ENABLED=1,
    so the user receives one MP4 without hitting VEO API limits. For ≤8 s, VEO 3 is
    used with Remotion fallback on failure. Video is stored in Knowledge Vault →
    Media Files and shown in chat/workspace; user can view and download. Use for any
    user request to create a video from a prompt.
    """
    from app.agents.tools import media

    return await media.generate_video(
        prompt=prompt,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        user_id=user_id,
    )


async def create_social_graphic(
    platform: str,
    caption: str,
    style: str = "vibrant",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create a social media post with graphic.

    Generates both the caption and an accompanying image
    optimized for the target platform.

    Args:
        platform: Target platform (instagram, facebook, twitter, linkedin, tiktok)
        caption: Post caption/text
        style: Visual style for the graphic
        user_id: User ID for saving

    Returns:
        Complete social post with image specification
    """
    tool = get_canva_tool()

    return await tool.generate_social_post(
        platform=platform,
        text=caption,
        style=style,
        include_image=True,
        user_id=user_id,
    )


async def list_media(
    user_id: str,
    media_type: str | None = None,
) -> dict[str, Any]:
    """List user's media library.

    Retrieves all media assets created by the user including
    images, videos, and design specifications.

    Args:
        user_id: User ID
        media_type: Filter by type (image_spec, video_spec, design)

    Returns:
        List of media assets
    """
    from app.agents.tools import media

    return await media.list_media_assets(
        user_id=user_id,
        asset_type=media_type,
    )


def _normalize_social_platform(platform: str) -> str:
    value = str(platform or "instagram").strip().lower()
    aliases = {
        "x": "twitter",
        "ig": "instagram",
        "fb": "facebook",
    }
    return aliases.get(value, value or "instagram")


def _draft_social_video_caption(
    prompt: str,
    platform: str,
    storyboard_captions: list[str] | None = None,
    nano_banana_mode: str = "always",
) -> str:
    """Draft a platform-tailored social caption using storyboard scene captions."""
    normalized_platform = _normalize_social_platform(platform)
    captions = [str(c).strip() for c in (storyboard_captions or []) if str(c).strip()]
    hook = captions[0] if captions else prompt.strip()
    highlights = captions[1:4]

    cta_map = {
        "instagram": "Comment your favorite scene and DM us if you want this look for your next campaign.",
        "twitter": "Reply with your favorite frame and repost if you want more creative breakdowns.",
        "linkedin": "Comment if you'd like a breakdown of the storyboard-to-video workflow behind this concept.",
        "facebook": "Drop a comment with the scene you want us to turn into the next ad concept.",
        "tiktok": "Comment 'PART 2' if you want the behind-the-scenes prompt stack.",
    }
    hashtag_map = {
        "instagram": "#NanoBanana #AIVideo #CreativeAds #BrandStorytelling #MotionDesign",
        "twitter": "#AIVideo #CreativeAds #Marketing #MotionDesign",
        "linkedin": "#AIVideo #CreativeStrategy #BrandMarketing #ContentOps",
        "facebook": "#AIVideo #BrandAd #CreativeMarketing",
        "tiktok": "#AIVideo #CreativeTok #BrandAd #MotionDesign",
    }

    mode = str(nano_banana_mode or "always").strip().lower()
    style_phrase = (
        "with vibrant Nano Banana 3D visuals"
        if mode not in {"off", "none", "false", "disable"}
        else "with premium cinematic visuals"
    )

    lines: list[str] = []
    if normalized_platform == "linkedin":
        lines.append(f"New campaign concept: {hook}")
        lines.append(
            f"We built this short-form ad {style_phrase} from a storyboard-to-video pipeline."
        )
    else:
        lines.append(hook)
        lines.append(f"A high-converting social ad concept {style_phrase}.")

    if highlights:
        lines.append("Highlights: " + " | ".join(highlights))

    lines.append(cta_map.get(normalized_platform, cta_map["instagram"]))
    lines.append(hashtag_map.get(normalized_platform, hashtag_map["instagram"]))
    return "\n\n".join(lines)


async def _publish_video_to_social_if_requested(
    *,
    auto_publish: bool,
    user_id: str,
    platform: str,
    caption: str,
    video_url: str,
) -> dict[str, Any]:
    """Attempt social posting only when explicitly enabled."""
    if not auto_publish:
        return {
            "attempted": False,
            "success": False,
            "message": "Draft only. Set auto_publish=True to attempt social posting.",
        }

    try:
        from app.social.publisher import get_social_publisher

        publisher = get_social_publisher()
        result = await publisher.post_with_media(
            user_id=user_id,
            platform=_normalize_social_platform(platform),
            content=caption,
            media_urls=[video_url],
        )
    except Exception as exc:
        logger.warning("Auto-publish failed before completion: %s", exc)
        return {"attempted": True, "success": False, "error": str(exc)}

    if isinstance(result, dict):
        return {"attempted": True, "success": bool(result.get("success")), **result}
    return {"attempted": True, "success": False, "error": "Unexpected publish response"}


async def execute_content_pipeline(
    prompt: str,
    platform: str = "instagram",
    user_id: str | None = None,
    auto_publish: bool = False,
    nano_banana_mode: str = "always",
) -> dict[str, Any]:
    """Execute the full Content Creation Pipeline.

    Orchestrates Storyboarding (Gemini) -> Base Images (Imagen) ->
    Video Clips (Veo) -> Composition (Remotion) -> Social Copy generation.
    Highly applies the Nano Banana styling (vibrant, surreal, cohesive 3D render).

    Args:
        prompt: Description of the video or ad to create.
        platform: Target platform for the social copy.
        user_id: User ID.
        auto_publish: If True, attempt to post the final video to a connected social account.
        nano_banana_mode: "always" (default), "auto", or "off" style injection.

    Returns:
        Complete video and social post.
    """
    from app.services.director_service import DirectorService
    from app.services.request_context import get_current_user_id

    user_id = user_id or get_current_user_id()
    if not user_id:
        return {"success": False, "error": "User ID required"}

    platform = _normalize_social_platform(platform)
    director = DirectorService()

    # Run pipeline
    pipeline_result = await director.create_pro_video(
        prompt,
        user_id,
        return_metadata=True,
        nano_banana_mode=nano_banana_mode,
    )

    if not pipeline_result:
        return {
            "success": False,
            "error": "Content pipeline failed during video generation.",
        }

    if isinstance(pipeline_result, dict):
        video_url = pipeline_result.get("video_url")
        asset_id = pipeline_result.get("asset_id")
        storyboard_captions = pipeline_result.get("storyboard_captions") or []
        generated_scenes = pipeline_result.get("scenes") or []
    else:
        video_url = pipeline_result
        asset_id = None
        storyboard_captions = []
        generated_scenes = []

    if not video_url:
        return {
            "success": False,
            "error": "Content pipeline failed during video generation.",
        }

    # Generate social copy
    tool = get_canva_tool()
    drafted_caption = _draft_social_video_caption(
        prompt=prompt,
        platform=platform,
        storyboard_captions=storyboard_captions,
        nano_banana_mode=nano_banana_mode,
    )
    post_result = await tool.generate_social_post(
        platform=platform,
        text=drafted_caption,
        style="vibrant",
        include_image=False,
        user_id=user_id,
    )

    publish_result = await _publish_video_to_social_if_requested(
        auto_publish=auto_publish,
        user_id=user_id,
        platform=platform,
        caption=drafted_caption,
        video_url=video_url,
    )

    if publish_result.get("attempted") and publish_result.get("success"):
        user_message = "Content pipeline completed and the video was posted to your connected social account."
    elif publish_result.get("attempted"):
        user_message = "Content pipeline completed, but social posting failed. Video and drafted caption are ready to post manually."
    else:
        user_message = "Content pipeline completed successfully. Video and drafted social caption are ready."

    content_contract = {}
    if asset_id:
        try:
            from app.services.content_bundle_service import ContentBundleService

            bundle_service = ContentBundleService()
            content_contract = await bundle_service.register_media_output(
                user_id=user_id,
                asset_id=asset_id,
                asset_type="video",
                title=(prompt[:80] + "…") if len(prompt) > 80 else prompt,
                prompt=prompt,
                file_url=video_url,
                source="canva_content_pipeline",
                workspace_mode="focus",
                platform_profile=platform,
                widget_type="video",
                metadata={
                    "platform": platform,
                    "storyboard_captions": storyboard_captions,
                    "nano_banana_mode": nano_banana_mode,
                    "scene_count": len(generated_scenes),
                },
            )
        except Exception as exc:
            logger.warning("Failed to register content pipeline contract: %s", exc)

    return {
        "success": True,
        "video_url": video_url,
        "asset_id": asset_id,
        "storyboard_captions": storyboard_captions,
        "content_contract": content_contract,
        "pipeline": {
            "scene_count": len(generated_scenes),
            "storyboard_captions": storyboard_captions,
            "nano_banana_mode": nano_banana_mode,
        },
        "social_post": post_result,
        "publish_result": publish_result,
        "user_message": user_message,
    }


# ============================================================================
async def create_product_photoshoot_bundle(
    product_name: str,
    brand_style: str = "vibrant",
    shot_count: int = 3,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Create a reusable photoshoot bundle brief for product content production."""
    normalized_count = max(1, min(int(shot_count or 3), 8))
    shots = []
    for idx in range(normalized_count):
        shot_number = idx + 1
        shots.append(
            {
                "name": f"Shot {shot_number}",
                "prompt": f"{product_name} product photography, {brand_style} style, hero composition {shot_number}",
                "aspect_ratio": "1:1" if shot_number == 1 else "4:5",
            }
        )

    return {
        "success": True,
        "product_name": product_name,
        "brand_style": brand_style,
        "shot_count": normalized_count,
        "bundle": {
            "hero_asset": shots[0],
            "shots": shots,
            "user_id": user_id,
        },
    }


async def get_media_deliverable_templates() -> dict[str, Any]:
    """Return built-in media deliverable templates for the content pipeline."""
    templates = [
        {
            "name": "product_photoshoot_bundle",
            "title": "Product Photoshoot Bundle",
            "description": "Hero, detail, and lifestyle shot prompts for a product launch.",
        },
        {
            "name": "social_video_pipeline",
            "title": "Social Video Pipeline",
            "description": "Storyboard, video generation, caption drafting, and publish handoff.",
        },
        {
            "name": "launch_graphics_pack",
            "title": "Launch Graphics Pack",
            "description": "Reusable post, story, and banner deliverables for launches.",
        },
    ]
    return {"success": True, "templates": templates, "count": len(templates)}


# Export for Agent Registration
# ============================================================================

CANVA_TOOLS = [
    create_image,
    create_video,
    create_video_with_veo,
    create_social_graphic,
    list_media,
    execute_content_pipeline,
    create_product_photoshoot_bundle,
    get_media_deliverable_templates,
]

CANVA_TOOLS_MAP = {
    "create_image": create_image,
    "create_video": create_video,
    "create_video_with_veo": create_video_with_veo,
    "create_social_graphic": create_social_graphic,
    "list_media": list_media,
    "execute_content_pipeline": execute_content_pipeline,
    "create_product_photoshoot_bundle": create_product_photoshoot_bundle,
    "get_media_deliverable_templates": get_media_deliverable_templates,
}
