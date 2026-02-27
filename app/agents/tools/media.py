"""Media Generation Tools.

This module provides tools for generating images and videos using Vertex AI and other services,
independent of Canva integration.
"""

import os
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Duration routing: Veo supports ~4-8s; longer videos use server-side Remotion when enabled.
VEO_MAX_DURATION_SECONDS = int(os.getenv("VEO_MAX_DURATION_SECONDS", "8"))
DIRECTOR_MIN_DURATION_SECONDS = int(os.getenv("DIRECTOR_MIN_DURATION_SECONDS", "20"))


def _should_use_director_pipeline(prompt: str, duration_seconds: int) -> bool:
    """Route long-form or narrative requests through DirectorService."""
    # Disabled to prevent 30-minute sequential video generations. 
    # DirectorService should be explicitly called via `create_pro_video` instead.
    return False

# Style presets for image generation
STYLE_PRESETS = {
    "vibrant": "vibrant colors, high saturation, energetic, modern",
    "minimal": "minimalist, clean lines, subtle colors, elegant",
    "tech": "futuristic, digital, glowing elements, dark background",
    "organic": "natural, earthy tones, flowing shapes, organic textures",
    "bold": "bold colors, strong contrast, impactful, attention-grabbing",
    "surreal": "surrealistic, dreamlike, floating elements, artistic",
    "professional": "corporate, clean, trustworthy, business-appropriate",
}

# Image dimensions to aspect ratio mapping
IMAGE_DIMENSIONS = {
    "instagram_post": {"width": 1080, "height": 1080, "ratio": "1:1"},
    "instagram_story": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "facebook_post": {"width": 1200, "height": 630, "ratio": "16:9"},
    "twitter_post": {"width": 1600, "height": 900, "ratio": "16:9"},
    "linkedin_post": {"width": 1200, "height": 627, "ratio": "16:9"},
    "tiktok_video": {"width": 1080, "height": 1920, "ratio": "9:16"},
    "youtube_thumbnail": {"width": 1280, "height": 720, "ratio": "16:9"},
    "presentation": {"width": 1920, "height": 1080, "ratio": "16:9"},
}


def _get_supabase_client():
    """Get Supabase client from centralized service."""
    try:
        from app.services.supabase import get_service_client
        return get_service_client()
    except (ImportError, ConnectionError):
        return None


async def generate_image(
    prompt: str,
    style: str = "vibrant",
    dimensions: Optional[Dict[str, int]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate an AI image using Vertex (Imagen 4 + fallback).
    
    Users can create images directly via the agent. Result is stored in Knowledge Vault
    media and shown in the image widget.
    
    Args:
        prompt: Description of the image.
        style: Visual style (vibrant, minimal, tech, organic, bold, surreal, professional).
        dimensions: Optional dict with width/height.
        user_id: User ID for storage (optional, falls back to context).
        
    Returns:
        Widget definition with image data.
    """
    from app.services.request_context import get_current_user_id
    user_id = user_id or get_current_user_id()
    
    style_modifier = STYLE_PRESETS.get(style, STYLE_PRESETS["vibrant"])
    enhanced_prompt = f"{prompt}. Style: {style_modifier}. High-fidelity, artistic, professional quality."
    
    # Determine aspect ratio
    aspect_ratio = "1:1"
    if dimensions:
        w = dimensions.get("width", 1080)
        h = dimensions.get("height", 1080)
        if w > h and w / h >= 1.5:
            aspect_ratio = "16:9"
        elif h > w and h / w >= 1.5:
            aspect_ratio = "9:16"
        elif w > h:
            aspect_ratio = "4:3"
        elif h > w:
            aspect_ratio = "3:4"

    try:
        from app.services.vertex_image_service import generate_image as vertex_generate

        # Offload blocking Vertex call to thread
        result = await asyncio.to_thread(
            vertex_generate,
            prompt=enhanced_prompt,
            aspect_ratio=aspect_ratio,
            style_hint=style_modifier,
            number_of_images=1,
        )
    except Exception as e:
        logger.error(f"Vertex image generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "prompt": enhanced_prompt,
        }

    if not result.get("success") or not result.get("image_bytes_base64"):
        return {
            "success": False,
            "error": result.get("error", "Image generation failed"),
            "prompt": enhanced_prompt,
        }

    import base64
    b64 = result["image_bytes_base64"]
    raw_bytes = base64.b64decode(b64)
    mime = result.get("mime_type") or "image/png"
    data_url = f"data:{mime};base64,{b64}"
    asset_id = str(uuid.uuid4())
    title = (prompt[:80] + "…") if len(prompt) > 80 else prompt
    file_path = None
    file_url = None
    bucket_id = "knowledge-vault"
    supabase = _get_supabase_client()

    # Store in Knowledge Vault media (media_assets) and optionally upload to storage
    if user_id and supabase:
        try:
            storage_path = f"media/{user_id}/{asset_id}.png"
            supabase.storage.from_(bucket_id).upload(
                storage_path,
                raw_bytes,
                {"content-type": mime},
            )
            file_path = storage_path
            signed = supabase.storage.from_(bucket_id).create_signed_url(storage_path, 3600)
            file_url = signed.get("signedURL") or signed.get("signedUrl") if isinstance(signed, dict) else None
        except Exception as e:
            logger.warning(f"Storage upload failed, using data URL only: {e}")

        try:
            row = {
                "id": asset_id,
                "user_id": user_id,
                "bucket_id": bucket_id,
                "asset_type": "image",
                "title": title,
                "filename": f"{asset_id}.png",
                "file_path": file_path or f"media/{user_id}/{asset_id}.png",
                "file_url": file_url,
                "file_type": mime,
                "category": "generated",
                "size_bytes": len(raw_bytes),
                "metadata": {
                    "prompt": enhanced_prompt,
                    "style": style,
                    "model_used": result.get("model_used"),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            supabase.table("media_assets").insert(row).execute()
        except Exception as e:
            logger.warning(f"Failed to save to media_assets: {e}")

        try:
            from app.rag.knowledge_vault import ingest_document_content
            ingest_content = f"Generated image: {title}. Prompt: {prompt}. Asset ID: {asset_id}. Stored in Knowledge Vault media."
            await ingest_document_content(
                content=ingest_content,
                title=f"Image: {title}",
                document_type="media",
                user_id=user_id,
                metadata={"asset_id": asset_id, "asset_type": "image"},
            )
        except Exception as e:
            logger.warning(f"Knowledge vault ingest for image failed: {e}")

    # Return image widget so frontend shows the image (required for all users)
    image_url = file_url or data_url
    widget = {
        "type": "image",
        "title": "Generated image",
        "data": {
            "imageUrl": image_url,
            "prompt": prompt,
            "asset_id": asset_id,
            "caption": title,
        },
        "dismissible": True,
        "expandable": True,
    }
    return widget


async def generate_video(
    prompt: str,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate video using Vertex Veo or server-side Remotion.
    
    Store in Knowledge Vault media; return video widget.
    For durations longer than 8 seconds, server-side Remotion is used when enabled.
    """
    from app.services.request_context import get_current_user_id
    from app.services.remotion_render_service import REMOTION_RENDER_ENABLED, render_scenes_to_mp4
    
    user_id = user_id or get_current_user_id()
    duration_normalized = max(4, min(180, int(duration_seconds))) if duration_seconds else 6
    supabase = _get_supabase_client()

    if _should_use_director_pipeline(prompt, duration_normalized):
        return await create_pro_video(prompt=prompt, user_id=user_id)

    # Long duration and Remotion enabled → use Remotion only (skip Veo to avoid API limits).
    use_remotion_only = (
        duration_normalized > VEO_MAX_DURATION_SECONDS and REMOTION_RENDER_ENABLED
    )
    
    if use_remotion_only:
        # Server-side Remotion Render
        video_bytes, asset_id = await asyncio.to_thread(
            render_scenes_to_mp4, prompt, duration_normalized, user_id or ""
        )
        
        if video_bytes and asset_id and user_id and supabase:
            return await _save_and_return_video_widget(
                supabase, user_id, asset_id, video_bytes, prompt, duration_normalized, "server-side remotion"
            )
            
        # Remotion render failed
        return {
            "success": False,
            "error": "Long video render failed.",
            "user_message": "Video creation for that duration didn't complete. Try again or use a shorter duration.",
            "prompt": prompt,
        }

    # Use Vertex Veo
    from app.services.vertex_video_service import generate_video as vertex_generate
    veo_duration = min(VEO_MAX_DURATION_SECONDS, max(4, duration_normalized))
    
    # Enhance prompt for video if it's too simple
    enhanced_prompt = prompt
    if len(prompt.split()) < 10:
        enhanced_prompt = f"{prompt}, cinematic, high quality, 4k, detailed, photorealistic"
    
    # Offload blocking Veo call to thread
    result = await asyncio.to_thread(
        vertex_generate,
        prompt=enhanced_prompt,
        duration_seconds=veo_duration,
        aspect_ratio=aspect_ratio,
        number_of_videos=1,
    )
    
    if not result.get("success"):
        logger.warning(f"Veo generation failed: {result.get('error')}. Attempting Remotion fallback...")
        
        # Fallback logic: Try to generate an image first for the background
        image_url = None
        try:
            logger.info("Generating background image for Remotion fallback...")
            img_result = await generate_image(prompt=prompt, user_id=user_id)
            if img_result and "data" in img_result and "imageUrl" in img_result["data"]:
                image_url = img_result["data"]["imageUrl"]
                logger.info("Background image generated successfully.")
        except Exception as e:
            logger.warning(f"Failed to generate background image for fallback: {e}")

        try:
             from app.services import remotion_render_service
             loop = asyncio.get_running_loop()
             
             def blocking_render():
                 return remotion_render_service.render_scenes_to_mp4(
                     prompt=prompt,
                     duration_seconds=duration_normalized,
                     user_id=user_id or "system_fallback",
                     image_url=image_url
                 )
             
             # Run in executor to avoid blocking event loop
             mp4_bytes, asset_id = await loop.run_in_executor(None, blocking_render)
             
             if mp4_bytes and asset_id:
                 # If we have supabase context, save it as a widget
                 if user_id and supabase:
                     return await _save_and_return_video_widget(
                        supabase, user_id, asset_id, mp4_bytes, prompt, duration_normalized, "fallback-remotion"
                     )
                 
                 # Otherwise return raw success
                 return {
                     "success": True,
                     "video_bytes": mp4_bytes,
                     "video_url": None, 
                     "model_used": "remotion-render",
                     "user_message": "Video generated using Remotion (Veo unavailable).",
                 }
             else:
                 # Both failed
                 return {
                     "success": False,
                     "error": f"Veo failed ({result.get('error')}) and Remotion failed (no output)",
                     "user_message": f"Unable to generate video. Veo Error: {result.get('error')}. Remotion Error: No output.",
                 }
                 
        except Exception as e:
            logger.warning(f"Remotion fallback failed: {e}")
            
        # Final failure return if fallback failed exception
        veo_error = result.get("error") or ""
        if "GOOGLE_CLOUD_PROJECT not set" in veo_error:
            user_message = (
                "Video generation is not configured (missing project). "
                "Please contact support or try again later."
            )
        else:
            user_message = f"Video generation unavailable. Veo Error: {veo_error}"
        return {
            "success": False,
            "error": "Video generation failed.",
            "user_message": user_message,
            "prompt": prompt,
        }


    # Veo Success
    video_bytes = result.get("video_bytes")
    video_url = result.get("video_url")
    
    if not video_bytes and not video_url:
        return {
            "success": False,
            "error": "No video output",
            "user_message": "Video generation produced no output. Please try again.",
            "prompt": prompt,
        }

    asset_id = str(uuid.uuid4())
    
    if user_id and supabase and video_bytes:
        return await _save_and_return_video_widget(
            supabase, user_id, asset_id, video_bytes, prompt, duration_normalized, "vertex veo"
        )
    
    # Fallback if we only have URL and no bytes (unlikely for current implementation but safe)
    if video_url:
         widget = {
            "type": "video",
            "title": "Generated video",
            "data": {
                "videoUrl": video_url,
                "title": prompt[:50],
                "asset_id": asset_id,
                "caption": prompt,
            },
            "dismissible": True,
            "expandable": True,
        }
         return widget

    return {
        "success": False,
        "error": "Video processing failed",
        "user_message": "Video processing failed. Please try again.",
        "prompt": prompt,
    }


async def _save_and_return_video_widget(
    supabase, user_id, asset_id, video_bytes, prompt, duration, source
):
    """Helper to save video to storage/db and return widget."""
    title = (prompt[:80] + "…") if len(prompt) > 80 else prompt
    bucket_id = "knowledge-vault"
    storage_path = f"media/{user_id}/{asset_id}.mp4"
    file_url = None
    
    upload_success = False
    for attempt in range(3):
        try:
            await asyncio.to_thread(
                supabase.storage.from_(bucket_id).upload,
                storage_path,
                video_bytes,
                {"content-type": "video/mp4"},
            )
            upload_success = True
            break
        except Exception as e:
            logger.warning(f"Video storage upload failed (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                return {"success": False, "error": "Failed to store generated video"}

    if upload_success:
        try:
            signed = await asyncio.to_thread(
                supabase.storage.from_(bucket_id).create_signed_url,
                storage_path, 
                3600
            )
            file_url = signed.get("signedURL") or signed.get("signedUrl") if isinstance(signed, dict) else None
        except Exception as e:
            logger.warning(f"Video URL signing failed: {e}")
            return {"success": False, "error": "Failed to generate video URL"}

    if file_url:
        try:
            supabase.table("media_assets").insert({
                "id": asset_id,
                "user_id": user_id,
                "bucket_id": bucket_id,
                "asset_type": "video",
                "title": title,
                "filename": f"{asset_id}.mp4",
                "file_path": storage_path,
                "file_url": file_url,
                "file_type": "video/mp4",
                "category": "generated",
                "size_bytes": len(video_bytes),
                "metadata": {"prompt": prompt, "source": source, "duration": duration},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save video to media_assets: {e}")

        try:
            from app.rag.knowledge_vault import ingest_document_content
            ingest_content = f"Generated video: {title}. Prompt: {prompt}. Asset ID: {asset_id}. Stored in Knowledge Vault media."
            await ingest_document_content(
                content=ingest_content,
                title=f"Video: {title}",
                document_type="media",
                user_id=user_id,
                metadata={"asset_id": asset_id, "asset_type": "video"},
            )
        except Exception as e:
            logger.warning(f"Knowledge vault ingest for video failed: {e}")

        return {
            "type": "video",
            "title": "Generated video",
            "data": {
                "videoUrl": file_url,
                "title": title,
                "asset_id": asset_id,
                "caption": prompt,
            },
            "dismissible": True,
            "expandable": True,
        }
    
    return {"success": False, "error": "Final video URL generation failed"}


async def list_media_assets(
    user_id: str,
    asset_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """List user's media assets from Knowledge Vault."""
    supabase = _get_supabase_client()
    if not supabase:
        return {"error": "Database not configured"}
    
    try:
        query = supabase.table("media_assets").select("*").eq("user_id", user_id)
        
        if asset_type:
            query = query.eq("asset_type", asset_type)
        
        result = query.order("created_at", desc=True).limit(limit).execute()
        
        return {
            "success": True,
            "assets": result.data,
            "count": len(result.data),
        }
        
    except Exception as e:
        logger.error(f"Failed to list media: {e}")
        return {"error": str(e)}

async def create_pro_video(
    prompt: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a high-quality, multi-scene video using AI Director (Veo 3 + Remotion).
    
    Use this tool when the user asks for a "pro" video, a "long" video, a "story", or a video with multiple scenes.
    This process takes longer (1-3 minutes) but produces a much higher quality result with transitions and narrative.
    
    Args:
        prompt: Description of the video content, style, and narrative.
        user_id: User ID (optional).
    """
    from app.services.request_context import get_current_user_id
    from app.services.director_service import DirectorService
    
    user_id = user_id or get_current_user_id()
    if not user_id:
        return {"success": False, "error": "User ID required"}

    try:
        director = DirectorService()
        progress_events = []

        async def _progress_callback(stage: str, payload: Dict[str, Any]):
            progress_events.append({"stage": stage, "payload": payload})
            try:
                from app.services.request_context import emit_progress_update

                await emit_progress_update(stage, payload)
            except (ConnectionError, TimeoutError):
                # Live progress is best-effort and should not break generation.
                pass

        video_url = await director.create_pro_video(prompt, user_id, progress_callback=_progress_callback)
        
        if not video_url:
            return {
                "success": False, 
                "error": "Pro video creation failed during generation.",
                "user_message": "I started the director process, but something went wrong generating the scenes.",
                "progress": progress_events,
            }
            
        # Return video widget
        return {
            "type": "video",
            "title": "Pro Video",
            "data": {
                "videoUrl": video_url,
                "title": prompt[:50],
                "caption": "Generated with AI Director (Veo + Remotion)",
                "asset_id": str(uuid.uuid4()), # Partial ID since real one is in URL
                "progress": progress_events,
            },
            "dismissible": True,
            "expandable": True,
        }
            
    except Exception as e:
        logger.error(f"Pro video creation error: {e}")
        return {"success": False, "error": str(e)}

MEDIA_TOOLS = [generate_image, generate_video, list_media_assets, create_pro_video]
