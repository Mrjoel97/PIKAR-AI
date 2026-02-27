"""Canva Media Creation MCP Tool.

Provides media creation capabilities including:
- Canva design creation and access
- AI image generation using nano-banana skill
- Video creation using remotion skill
- Social media graphic generation
"""

import os
import uuid
import logging
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timezone

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
        content: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a design using Canva API.
        
        Args:
            design_type: Type of design (instagram_post, facebook_post, etc.)
            title: Design title
            content: Design content (text, images, etc.)
            
        Returns:
            Design details and edit URL
        """
        if not self.is_canva_configured():
            return {"error": "Canva not configured. Please add your CANVA_API_KEY."}
        
        import httpx
        
        dimensions = self.DESIGN_TYPES.get(design_type, {"width": 1080, "height": 1080})
        
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
                        "title": title,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "design_id": data.get("design", {}).get("id"),
                        "edit_url": data.get("design", {}).get("urls", {}).get("edit_url"),
                        "view_url": data.get("design", {}).get("urls", {}).get("view_url"),
                        "title": title,
                        "dimensions": dimensions,
                    }
                else:
                    return {"error": f"Canva API error: {response.text}"}
                    
        except Exception as e:
            logger.error(f"Canva design creation failed: {e}")
            return {"error": str(e)}
    
    def _dimensions_to_aspect_ratio(self, dimensions: Optional[Dict[str, int]]) -> str:
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
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            
            image_prompt = f"Social media graphic for {platform}. Content theme: {text[:100]}"
            image_result = await generate_image(
                prompt=image_prompt,
                style=style,
                dimensions=dimensions,
                user_id=user_id,
            )
            result["image"] = image_result
        
        return result


# Singleton instance
_canva_tool: Optional[CanvaMCPTool] = None


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
    platform: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
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
    scenes: List[Dict[str, Any]],
    duration: int = 30,
    style: str = "modern",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a programmatic (scene-based) video using Remotion.
    
    Generates Remotion composition code for multi-scene or template-style videos.
    For "one prompt → one MP4" (user says "create a 30 second video about X"),
    prefer create_video_with_veo: the backend uses VEO 3 for short clips and
    server-side Remotion for longer durations, returning a single playable MP4.
    Use create_video when you need explicit scene list and Remotion structure.
    """
    from app.services.request_context import get_current_user_id
    from app.services.remotion_render_service import render_programmatic_video
    from app.agents.tools.media import _save_and_return_video_widget, _get_supabase_client
    import asyncio
    import uuid

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
        remotion_scenes.append({
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
            ] if text else [],
            "transition": {"type": "fade", "durationFrames": 15},
        })

    props = {
        "scenes": remotion_scenes,
        "fps": fps,
        "durationInFrames": duration_frames,
        "bgMusicVolume": 0.35,
        "voiceoverVolume": 1.0,
    }

    try:
        mp4_bytes, asset_id = await asyncio.to_thread(
            render_programmatic_video,
            props,
            user_id
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
                supabase, user_id, asset_id or str(uuid.uuid4()), mp4_bytes, title, duration, "programmatic-remotion"
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
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
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
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
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
    media_type: Optional[str] = None,
) -> Dict[str, Any]:
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
    storyboard_captions: Optional[List[str]] = None,
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

    lines: List[str] = []
    if normalized_platform == "linkedin":
        lines.append(f"New campaign concept: {hook}")
        lines.append(f"We built this short-form ad {style_phrase} from a storyboard-to-video pipeline.")
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
) -> Dict[str, Any]:
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
    user_id: Optional[str] = None,
    auto_publish: bool = False,
    nano_banana_mode: str = "always",
) -> Dict[str, Any]:
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
            "error": "Content pipeline failed during video generation."
        }

    if isinstance(pipeline_result, dict):
        video_url = pipeline_result.get("video_url")
        storyboard_captions = pipeline_result.get("storyboard_captions") or []
        generated_scenes = pipeline_result.get("scenes") or []
    else:
        video_url = pipeline_result
        storyboard_captions = []
        generated_scenes = []

    if not video_url:
        return {
            "success": False,
            "error": "Content pipeline failed during video generation."
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
        user_message = (
            "Content pipeline completed, but social posting failed. Video and drafted caption are ready to post manually."
        )
    else:
        user_message = "Content pipeline completed successfully. Video and drafted social caption are ready."

    return {
        "success": True,
        "video_url": video_url,
        "storyboard_captions": storyboard_captions,
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
# Export for Agent Registration
# ============================================================================

CANVA_TOOLS = [
    create_image,
    create_video,
    create_video_with_veo,
    create_social_graphic,
    list_media,
    execute_content_pipeline,
]

CANVA_TOOLS_MAP = {
    "create_image": create_image,
    "create_video": create_video,
    "create_video_with_veo": create_video_with_veo,
    "create_social_graphic": create_social_graphic,
    "list_media": list_media,
    "execute_content_pipeline": execute_content_pipeline,
}
