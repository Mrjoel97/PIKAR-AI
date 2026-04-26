# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Media Generation Tools.

This module provides tools for generating images and videos using Vertex AI and other services,
independent of Canva integration.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()

# Duration routing: Veo supports ~4-8s; longer videos use DirectorService up to 3 minutes.
VEO_MAX_DURATION_SECONDS = int(os.getenv("VEO_MAX_DURATION_SECONDS", "8"))
DIRECTOR_MAX_DURATION_SECONDS = int(os.getenv("DIRECTOR_MAX_DURATION_SECONDS", "180"))


def _should_use_director_pipeline(_prompt: str, duration_seconds: int) -> bool:
    """Route anything longer than a single Veo clip through the Director pipeline."""
    return VEO_MAX_DURATION_SECONDS < duration_seconds <= DIRECTOR_MAX_DURATION_SECONDS


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


def _get_request_scope() -> dict[str, str | None]:
    from app.services.request_context import (
        get_current_session_id,
        get_current_workflow_execution_id,
    )

    return {
        "session_id": get_current_session_id(),
        "workflow_execution_id": get_current_workflow_execution_id(),
    }


async def _register_media_contract(
    *,
    user_id: str | None,
    asset_id: str,
    asset_type: str,
    title: str,
    prompt: str,
    file_url: str | None,
    workspace_mode: str = "focus",
    source: str = "agent_media_tool",
    thumbnail_url: str | None = None,
    editable_url: str | None = None,
    platform_profile: str | None = None,
    widget_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scope = _get_request_scope()
    if not user_id:
        return {**scope, "workspace_mode": workspace_mode}

    from app.services.content_bundle_service import ContentBundleService

    service = ContentBundleService()
    return await service.register_media_output(
        user_id=user_id,
        asset_id=asset_id,
        asset_type=asset_type,
        title=title,
        prompt=prompt,
        file_url=file_url,
        thumbnail_url=thumbnail_url,
        editable_url=editable_url,
        source=source,
        workspace_mode=workspace_mode,
        session_id=scope.get("session_id"),
        workflow_execution_id=scope.get("workflow_execution_id"),
        platform_profile=platform_profile,
        widget_type=widget_type or asset_type,
        metadata=metadata,
    )


def _attach_contract_to_widget(
    widget: dict[str, Any],
    contract: dict[str, Any],
    *,
    extra_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    widget_copy = dict(widget)
    data = dict(widget_copy.get("data") or {})
    data.update(
        {
            key: value
            for key, value in {
                "bundle_id": contract.get("bundle_id"),
                "deliverable_id": contract.get("deliverable_id"),
                "workspace_item_id": contract.get("workspace_item_id"),
                "session_id": contract.get("session_id"),
                "workflow_execution_id": contract.get("workflow_execution_id"),
            }.items()
            if value is not None
        }
    )
    if extra_data:
        data.update(
            {key: value for key, value in extra_data.items() if value is not None}
        )
    widget_copy["data"] = data

    workspace = dict(widget_copy.get("workspace") or {})
    workspace.update(
        {
            key: value
            for key, value in {
                "mode": contract.get("workspace_mode")
                or workspace.get("mode")
                or "focus",
                "bundleId": contract.get("bundle_id"),
                "deliverableId": contract.get("deliverable_id"),
                "workspaceItemId": contract.get("workspace_item_id"),
                "sessionId": contract.get("session_id"),
                "workflowExecutionId": contract.get("workflow_execution_id"),
            }.items()
            if value is not None
        }
    )
    widget_copy["workspace"] = workspace
    return widget_copy


def _schedule_best_effort_task(coro: Any, label: str) -> None:
    """Run non-critical async work without blocking the user-facing response."""

    async def _runner() -> None:
        try:
            await coro
        except Exception as exc:
            logger.warning("Background task failed (%s): %s", label, exc)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    task = loop.create_task(_runner())
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def _build_video_storage_fallback(
    *,
    user_id: str | None,
    asset_id: str,
    prompt: str,
    duration: int,
    source: str,
    video_bytes: bytes,
    fallback_video_url: str | None,
    model_used: str | None,
) -> dict[str, Any]:
    """Return the best available video result when storage or signing fails."""
    title = (prompt[:80] + "…") if len(prompt) > 80 else prompt

    if fallback_video_url:
        widget = {
            "type": "video",
            "title": "Generated video",
            "data": {
                "videoUrl": fallback_video_url,
                "title": title,
                "asset_id": asset_id,
                "caption": prompt,
            },
            "dismissible": True,
            "expandable": True,
        }
        contract = await _register_media_contract(
            user_id=user_id,
            asset_id=asset_id,
            asset_type="video",
            title=title,
            prompt=prompt,
            file_url=fallback_video_url,
            source=f"{source}-storage-fallback",
            metadata={
                "source": source,
                "duration": duration,
                "model_used": model_used,
                "storage_failed": True,
            },
        )
        return _attach_contract_to_widget(widget, contract)

    return {
        "success": True,
        "video_bytes": video_bytes,
        "video_url": None,
        "model_used": model_used or source,
        "user_message": "Video generated, but storage failed. Returning the unstored result.",
    }


async def generate_image(
    prompt: str,
    style: str = "vibrant",
    dimensions: dict[str, int] | None = None,
    user_id: str | None = None,
    art_direction_id: str = "",
) -> dict[str, Any]:
    """Generate an AI image using Vertex (Gemini 2.5 Flash Image + fallback).

    Users can create images directly via the agent. Result is stored in Knowledge Vault
    media and shown in the image widget.

    Args:
        prompt: Description of the image.
        style: Visual style (vibrant, minimal, tech, organic, bold, surreal, professional).
        dimensions: Optional dict with width/height.
        user_id: User ID for storage (optional, falls back to context).
        art_direction_id: Optional art direction contract ID for visual consistency.

    Returns:
        Widget definition with image data.
    """
    from app.services.request_context import get_current_user_id

    user_id = user_id or get_current_user_id()
    request_scope = _get_request_scope()

    # Apply art direction contract if provided
    art_direction_modifier = ""
    if art_direction_id and user_id:
        try:
            from app.agents.tools.art_direction import (
                build_art_direction_prompt_modifier,
                get_art_direction,
            )

            ad_result = await get_art_direction(art_direction_id, user_id)
            if ad_result.get("success") and ad_result.get("contract"):
                contract = ad_result["contract"]
                art_direction_modifier = build_art_direction_prompt_modifier(contract)
                # Override style preset if art direction specifies one
                ad_style = contract.get("image_style_preset", "")
                if ad_style and ad_style in STYLE_PRESETS:
                    style = ad_style
        except Exception as exc:
            logger.debug("Art direction enrichment skipped: %s", exc)

    style_modifier = STYLE_PRESETS.get(style, STYLE_PRESETS["vibrant"])
    enhanced_prompt = prompt.strip() or prompt
    if art_direction_modifier:
        enhanced_prompt = f"{enhanced_prompt} | {art_direction_modifier}"

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
            signed = supabase.storage.from_(bucket_id).create_signed_url(
                storage_path, 3600
            )
            file_url = (
                signed.get("signedURL") or signed.get("signedUrl")
                if isinstance(signed, dict)
                else None
            )
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
                    "session_id": request_scope.get("session_id"),
                    "workflow_execution_id": request_scope.get("workflow_execution_id"),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            supabase.table("media_assets").insert(row).execute()
        except Exception as e:
            logger.warning(f"Failed to save to media_assets: {e}")

        try:
            from app.rag.knowledge_vault import ingest_document_content

            ingest_content = f"Generated image: {title}. Prompt: {prompt}. Asset ID: {asset_id}. Stored in Knowledge Vault media."
            _schedule_best_effort_task(
                ingest_document_content(
                    content=ingest_content,
                    title=f"Image: {title}",
                    document_type="media",
                    user_id=user_id,
                    metadata={"asset_id": asset_id, "asset_type": "image"},
                ),
                f"image-ingest:{asset_id}",
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
    contract = await _register_media_contract(
        user_id=user_id,
        asset_id=asset_id,
        asset_type="image",
        title=title,
        prompt=prompt,
        file_url=file_url or image_url,
        source="generate_image",
        metadata={"style": style, "model_used": result.get("model_used")},
    )
    return _attach_contract_to_widget(widget, contract)


async def generate_video(
    prompt: str,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    user_id: str | None = None,
    art_direction_id: str = "",
) -> dict[str, Any]:
    """Generate video using Vertex Veo or the multi-scene Director pipeline.

    Store in Knowledge Vault media; return video widget.
    For durations longer than a single Veo clip, DirectorService assembles a longer video.

    Args:
        prompt: Description of the video content.
        duration_seconds: Video length in seconds.
        aspect_ratio: Aspect ratio (e.g., "16:9", "9:16").
        user_id: Optional user ID.
        art_direction_id: Optional art direction contract ID for visual consistency.
    """
    from app.services.remotion_render_service import (
        REMOTION_RENDER_ENABLED,
        render_scenes_to_mp4,
    )
    from app.services.request_context import get_current_user_id

    user_id = user_id or get_current_user_id()
    request_scope = _get_request_scope()

    # Apply art direction contract if provided
    if art_direction_id and user_id:
        try:
            from app.agents.tools.art_direction import (
                build_art_direction_prompt_modifier,
                get_art_direction,
            )

            ad_result = await get_art_direction(art_direction_id, user_id)
            if ad_result.get("success") and ad_result.get("contract"):
                contract = ad_result["contract"]
                modifier = build_art_direction_prompt_modifier(contract)
                if modifier:
                    prompt = f"{prompt.strip()} | {modifier}"
                # Apply aspect ratio from art direction if not explicitly set
                ad_ratio = contract.get("aspect_ratio", "")
                if ad_ratio and aspect_ratio == "16:9":  # Only override default
                    aspect_ratio = ad_ratio
        except Exception as exc:
            logger.debug("Video art direction enrichment skipped: %s", exc)

    if duration_seconds > DIRECTOR_MAX_DURATION_SECONDS:
        return {
            "success": False,
            "error": f"Maximum video duration is {DIRECTOR_MAX_DURATION_SECONDS} seconds (3 minutes). Requested: {duration_seconds}s.",
            "user_message": "Videos can be up to 3 minutes long. Please request a shorter duration.",
        }

    duration_normalized = (
        max(4, min(DIRECTOR_MAX_DURATION_SECONDS, int(duration_seconds)))
        if duration_seconds
        else 6
    )

    if _should_use_director_pipeline(prompt, duration_normalized):
        return await create_pro_video(
            prompt=prompt,
            user_id=user_id,
            duration_seconds=duration_normalized,
        )

    supabase = _get_supabase_client()

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
                supabase,
                user_id,
                asset_id,
                video_bytes,
                prompt,
                duration_normalized,
                "server-side remotion",
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

    # Keep the Veo prompt lean so request prep stays fast and predictable.
    enhanced_prompt = prompt.strip() or prompt

    # Offload blocking Veo call to thread
    result = await asyncio.to_thread(
        vertex_generate,
        prompt=enhanced_prompt,
        duration_seconds=veo_duration,
        aspect_ratio=aspect_ratio,
        number_of_videos=1,
    )

    if not result.get("success"):
        logger.warning(
            f"Veo generation failed: {result.get('error')}. Attempting Remotion fallback..."
        )

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
                    image_url=image_url,
                )

            # Run in executor to avoid blocking event loop
            mp4_bytes, asset_id = await loop.run_in_executor(None, blocking_render)

            if mp4_bytes and asset_id:
                # If we have supabase context, save it as a widget
                if user_id and supabase:
                    return await _save_and_return_video_widget(
                        supabase,
                        user_id,
                        asset_id,
                        mp4_bytes,
                        prompt,
                        duration_normalized,
                        "fallback-remotion",
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
                "Video generation is not configured (missing Vertex project). "
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
            supabase,
            user_id,
            asset_id,
            video_bytes,
            prompt,
            duration_normalized,
            "vertex veo",
            fallback_video_url=video_url,
            model_used=result.get("model_used"),
        )

    if video_bytes:
        return {
            "success": True,
            "video_bytes": video_bytes,
            "video_url": None,
            "model_used": result.get("model_used"),
            "user_message": "Video generated using Vertex Veo.",
        }

    # Fallback if we only have URL and no bytes (unlikely for current implementation but safe)
    if video_url:
        if user_id and supabase:
            try:
                supabase.table("media_assets").upsert(
                    {
                        "id": asset_id,
                        "user_id": user_id,
                        "bucket_id": "external-generated",
                        "asset_type": "video",
                        "title": (prompt[:80] + "…") if len(prompt) > 80 else prompt,
                        "filename": f"{asset_id}.mp4",
                        "file_path": f"external/{asset_id}.mp4",
                        "file_url": video_url,
                        "file_type": "video/mp4",
                        "category": "generated",
                        "metadata": {
                            "prompt": prompt,
                            "source": "vertex veo url",
                            "duration": duration_normalized,
                            "session_id": request_scope.get("session_id"),
                            "workflow_execution_id": request_scope.get(
                                "workflow_execution_id"
                            ),
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                    on_conflict="id",
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to save URL-only video to media_assets: {e}")

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
        contract = await _register_media_contract(
            user_id=user_id,
            asset_id=asset_id,
            asset_type="video",
            title=(prompt[:80] + "…") if len(prompt) > 80 else prompt,
            prompt=prompt,
            file_url=video_url,
            source="generate_video_url_fallback",
            metadata={"source": "vertex veo url", "duration": duration_normalized},
        )
        return _attach_contract_to_widget(widget, contract)

    return {
        "success": False,
        "error": "Video processing failed",
        "user_message": "Video processing failed. Please try again.",
        "prompt": prompt,
    }


async def _save_and_return_video_widget(
    supabase,
    user_id,
    asset_id,
    video_bytes,
    prompt,
    duration,
    source,
    fallback_video_url: str | None = None,
    model_used: str | None = None,
):
    """Helper to save video to storage/db and return widget."""
    request_scope = _get_request_scope()
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
            logger.warning(
                f"Video storage upload failed (attempt {attempt + 1}/3): {e}"
            )
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                logger.warning(
                    "Video storage failed after generation; returning fallback result"
                )
                return await _build_video_storage_fallback(
                    user_id=user_id,
                    asset_id=asset_id,
                    prompt=prompt,
                    duration=duration,
                    source=source,
                    video_bytes=video_bytes,
                    fallback_video_url=fallback_video_url,
                    model_used=model_used,
                )

    if upload_success:
        try:
            signed = await asyncio.to_thread(
                supabase.storage.from_(bucket_id).create_signed_url, storage_path, 3600
            )
            file_url = (
                signed.get("signedURL") or signed.get("signedUrl")
                if isinstance(signed, dict)
                else None
            )
        except Exception as e:
            logger.warning(f"Video URL signing failed: {e}")
            return await _build_video_storage_fallback(
                user_id=user_id,
                asset_id=asset_id,
                prompt=prompt,
                duration=duration,
                source=source,
                video_bytes=video_bytes,
                fallback_video_url=fallback_video_url,
                model_used=model_used,
            )

    if file_url:
        try:
            supabase.table("media_assets").insert(
                {
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
                    "metadata": {
                        "prompt": prompt,
                        "source": source,
                        "duration": duration,
                        "session_id": request_scope.get("session_id"),
                        "workflow_execution_id": request_scope.get(
                            "workflow_execution_id"
                        ),
                    },
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="id",
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to save video to media_assets: {e}")

        try:
            from app.rag.knowledge_vault import ingest_document_content

            ingest_content = f"Generated video: {title}. Prompt: {prompt}. Asset ID: {asset_id}. Stored in Knowledge Vault media."
            _schedule_best_effort_task(
                ingest_document_content(
                    content=ingest_content,
                    title=f"Video: {title}",
                    document_type="media",
                    user_id=user_id,
                    metadata={"asset_id": asset_id, "asset_type": "video"},
                ),
                f"video-ingest:{asset_id}",
            )
        except Exception as e:
            logger.warning(f"Knowledge vault ingest for video failed: {e}")

        widget = {
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
        contract = await _register_media_contract(
            user_id=user_id,
            asset_id=asset_id,
            asset_type="video",
            title=title,
            prompt=prompt,
            file_url=file_url,
            source=source,
            metadata={"source": source, "duration": duration},
        )
        return _attach_contract_to_widget(widget, contract)

    return await _build_video_storage_fallback(
        user_id=user_id,
        asset_id=asset_id,
        prompt=prompt,
        duration=duration,
        source=source,
        video_bytes=video_bytes,
        fallback_video_url=fallback_video_url,
        model_used=model_used,
    )


async def list_media_assets(
    user_id: str,
    asset_type: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
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
    user_id: str | None = None,
    duration_seconds: int = 30,
) -> dict[str, Any]:
    """Create a high-quality, multi-scene video using AI Director (Veo 3 + Remotion).

    Use this tool when the user asks for a "pro" video, a "long" video, a "story", or a video with multiple scenes.
    This process takes longer (1-3 minutes) but produces a much higher quality result with transitions and narrative.

    Args:
        prompt: Description of the video content, style, and narrative.
        user_id: User ID (optional).
        duration_seconds: Requested video duration, capped at 3 minutes.
    """
    from app.services.director_service import DirectorService
    from app.services.request_context import get_current_user_id

    user_id = user_id or get_current_user_id()
    if not user_id:
        return {"success": False, "error": "User ID required"}

    target_duration_seconds = max(
        4, min(DIRECTOR_MAX_DURATION_SECONDS, int(duration_seconds or 30))
    )

    def _director_failure_details() -> dict[str, Any] | None:
        failed_event = next(
            (
                event
                for event in reversed(progress_events)
                if str(event.get("stage") or "").strip().lower() == "failed"
            ),
            None,
        )
        if not failed_event:
            return None

        payload = (
            failed_event.get("payload")
            if isinstance(failed_event.get("payload"), dict)
            else {}
        )
        reason = str(payload.get("reason") or "director_failed").strip() or "director_failed"
        user_message = "I started the director process, but it failed before the final video was ready."
        if reason == "storyboard_generation_failed":
            user_message = "I started the director process, but the storyboard step failed."
        elif reason == "empty_storyboard":
            user_message = "I started the director process, but the storyboard came back with no scenes."
        elif reason == "scene_generation_timeout":
            user_message = "I started the director process, but scene generation timed out."
        elif reason == "all_scenes_failed":
            user_message = "I started the director process, but every scene asset failed to generate."
        elif reason == "remotion_render_failed":
            backend = str(payload.get("render_backend") or "").strip().lower()
            backend_label = "FFmpeg" if backend == "ffmpeg" else "Remotion"
            user_message = (
                f"I started the director process, and the scene assembly finished, "
                f"but the final {backend_label} render failed."
            )
        elif reason == "upload_failed":
            user_message = "I started the director process, and the final video rendered, but uploading it failed."
        elif reason == "final_upload_failed":
            user_message = "I started the director process, and the final video was created, but returning the uploaded file failed."

        return {
            "reason": reason,
            "payload": payload,
            "user_message": user_message,
        }

    try:
        director = DirectorService()
        progress_events = []

        async def _progress_callback(stage: str, payload: dict[str, Any]):
            progress_events.append({"stage": stage, "payload": payload})
            try:
                from app.services.request_context import emit_progress_update

                await emit_progress_update(stage, payload)
            except (ConnectionError, TimeoutError):
                # Live progress is best-effort and should not break generation.
                pass

        result_payload = await director.create_pro_video(
            prompt,
            user_id,
            progress_callback=_progress_callback,
            return_metadata=True,
            target_duration_seconds=target_duration_seconds,
        )

        if not result_payload:
            failure = _director_failure_details()
            return {
                "success": False,
                "error": (
                    failure["reason"]
                    if failure
                    else "Pro video creation failed during generation."
                ),
                "user_message": (
                    failure["user_message"]
                    if failure
                    else "I started the director process, but it failed before the final video was ready."
                ),
                "progress": progress_events,
                **(
                    {
                        "failure_reason": failure["reason"],
                        "failure_payload": failure["payload"],
                    }
                    if failure
                    else {}
                ),
            }

        video_url = (
            result_payload.get("video_url")
            if isinstance(result_payload, dict)
            else result_payload
        )
        asset_id = (
            result_payload.get("asset_id") if isinstance(result_payload, dict) else None
        )
        storyboard_captions = (
            result_payload.get("storyboard_captions")
            if isinstance(result_payload, dict)
            else None
        )
        if not video_url:
            return {
                "success": False,
                "error": "Pro video creation produced no output.",
                "progress": progress_events,
            }

        contract = await _register_media_contract(
            user_id=user_id,
            asset_id=asset_id or str(uuid.uuid4()),
            asset_type="video",
            title=(prompt[:80] + "…") if len(prompt) > 80 else prompt,
            prompt=prompt,
            file_url=video_url,
            source="director_service",
            metadata={
                "source": "director_service",
                "storyboard_captions": storyboard_captions or [],
                "duration": target_duration_seconds,
            },
        )
        widget = {
            "type": "video",
            "title": "Pro Video",
            "data": {
                "videoUrl": video_url,
                "title": prompt[:50],
                "caption": "Generated with AI Director (Veo + Remotion)",
                "asset_id": asset_id,
                "durationSeconds": target_duration_seconds,
                "progress": progress_events,
                "storyboard_captions": storyboard_captions or [],
            },
            "dismissible": True,
            "expandable": True,
        }
        return _attach_contract_to_widget(widget, contract)

    except Exception as e:
        logger.error(f"Pro video creation error: {e}")
        return {"success": False, "error": str(e)}


async def generate_images(
    prompts: list[str],
    style: str = "vibrant",
    dimensions: dict[str, int] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Generate multiple AI images concurrently.

    Args:
        prompts: List of image descriptions (max 10).
        style: Visual style for all images.
        dimensions: Optional shared dimensions.
        user_id: User ID for storage.

    Returns:
        Dict with list of widget definitions.
    """
    if not prompts:
        return {"success": False, "error": "No prompts provided"}

    # Cap at 10 to prevent abuse
    prompts = prompts[:10]

    # Generate all images concurrently
    tasks = [
        generate_image(prompt=p, style=style, dimensions=dimensions, user_id=user_id)
        for p in prompts
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    widgets = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append({"index": i, "prompt": prompts[i], "error": str(result)})
        elif isinstance(result, dict) and result.get("type") == "image":
            widgets.append(result)
        elif isinstance(result, dict) and result.get("success") is False:
            errors.append(
                {
                    "index": i,
                    "prompt": prompts[i],
                    "error": result.get("error", "Unknown"),
                }
            )
        else:
            widgets.append(result)

    return {
        "success": len(widgets) > 0,
        "widgets": widgets,
        "count": len(widgets),
        "errors": errors if errors else None,
        "user_message": f"Generated {len(widgets)} image{'s' if len(widgets) != 1 else ''}"
        + (f" ({len(errors)} failed)" if errors else ""),
    }


async def generate_videos(
    prompts: list[str],
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Generate multiple videos. Runs sequentially to avoid Veo rate limits.

    Args:
        prompts: List of video descriptions (max 5).
        duration_seconds: Duration per video.
        aspect_ratio: Aspect ratio.
        user_id: User ID.

    Returns:
        Dict with list of widget definitions.
    """
    if not prompts:
        return {"success": False, "error": "No prompts provided"}

    prompts = prompts[:5]  # Cap at 5 for videos (more expensive)

    widgets = []
    errors = []
    for i, p in enumerate(prompts):
        try:
            result = await generate_video(
                prompt=p,
                duration_seconds=duration_seconds,
                aspect_ratio=aspect_ratio,
                user_id=user_id,
            )
            if isinstance(result, dict) and result.get("type") == "video":
                widgets.append(result)
            elif isinstance(result, dict) and result.get("success") is False:
                errors.append(
                    {"index": i, "prompt": p, "error": result.get("error", "Unknown")}
                )
            else:
                widgets.append(result)
        except Exception as e:
            errors.append({"index": i, "prompt": p, "error": str(e)})

    return {
        "success": len(widgets) > 0,
        "widgets": widgets,
        "count": len(widgets),
        "errors": errors if errors else None,
        "user_message": f"Generated {len(widgets)} video{'s' if len(widgets) != 1 else ''}"
        + (f" ({len(errors)} failed)" if errors else ""),
    }


MEDIA_TOOLS = [
    generate_image,
    generate_images,
    generate_video,
    generate_videos,
    list_media_assets,
    create_pro_video,
]
