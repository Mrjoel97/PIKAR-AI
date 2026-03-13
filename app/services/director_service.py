import asyncio
import json
import logging
import math
import os
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from google import genai
from google.genai.types import GenerateContentConfig

from app.services import audio_music_service
from app.services import remotion_render_service
from app.services import vertex_image_service
from app.services import vertex_video_service
from app.services import voiceover_service
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

# Constants
ASSET_BUCKET = "generated-assets"
VIDEO_BUCKET = "generated-videos"
STORYBOARD_MODEL = "gemini-2.0-flash-001"
DIRECTOR_MAX_DURATION_SECONDS = int(os.getenv("DIRECTOR_MAX_DURATION_SECONDS", "180"))


def _normalize_target_duration_seconds(value: Any) -> int:
    """Clamp the requested long-video duration to the supported range."""
    try:
        duration = int(value)
    except (TypeError, ValueError):
        duration = 30
    return max(4, min(DIRECTOR_MAX_DURATION_SECONDS, duration))


def _target_scene_count(target_duration_seconds: int) -> int:
    """Aim for the fewest scenes that can still hit the requested duration."""
    duration = _normalize_target_duration_seconds(target_duration_seconds)
    return max(3, math.ceil(duration / 8))


def _target_veo_scene_budget(target_duration_seconds: int, scene_count: int) -> int:
    """Cap Veo usage for longer videos so asset generation stays tractable."""
    if scene_count <= 0:
        return 0
    duration = _normalize_target_duration_seconds(target_duration_seconds)
    if duration >= 60:
        return min(scene_count, 2)
    return min(scene_count, 3)


def _spread_scene_indices(scene_count: int, selected_count: int) -> List[int]:
    """Pick stable anchor indices spread across the storyboard."""
    if scene_count <= 0 or selected_count <= 0:
        return []
    if selected_count >= scene_count:
        return list(range(scene_count))
    if selected_count == 1:
        return [0]

    indices: List[int] = []
    for step in range(selected_count):
        candidate = round(step * (scene_count - 1) / (selected_count - 1))
        while candidate in indices and candidate < scene_count - 1:
            candidate += 1
        while candidate in indices and candidate > 0:
            candidate -= 1
        if candidate not in indices:
            indices.append(candidate)
    return sorted(indices)


def _apply_render_type_budget(
    scenes: List[Dict[str, Any]],
    *,
    target_duration_seconds: int,
) -> List[Dict[str, Any]]:
    """Normalize storyboard media mix so long videos use fewer Veo scenes."""
    if not scenes:
        return scenes

    scene_count = len(scenes)
    duration = _normalize_target_duration_seconds(target_duration_seconds)
    if duration < 60:
        return scenes
    veo_budget = _target_veo_scene_budget(target_duration_seconds, scene_count)
    requested_veo_indices = [
        index for index, scene in enumerate(scenes) if str(scene.get("render_type") or "").strip().lower() == "veo"
    ]

    selected_indices: List[int] = []
    if requested_veo_indices:
        keep_positions = _spread_scene_indices(len(requested_veo_indices), veo_budget)
        selected_indices.extend(requested_veo_indices[position] for position in keep_positions)
    else:
        selected_indices.extend(_spread_scene_indices(scene_count, veo_budget))

    selected_set = set(selected_indices)
    for index, scene in enumerate(scenes):
        scene["render_type"] = "veo" if index in selected_set else "imagen"

    return scenes


def _clamp_scene_duration(value: Any) -> int:
    """Clamp to Veo-supported scene duration buckets."""
    try:
        duration = int(value)
    except (TypeError, ValueError):
        duration = 4
    if duration <= 4:
        return 4
    if duration <= 6:
        return 6
    return 8


def _normalize_nano_banana_mode(value: Any) -> str:
    """Normalize style injection mode for storyboard prompting."""
    mode = str(value or "always").strip().lower()
    if mode in {"always", "on", "true", "force"}:
        return "always"
    if mode in {"auto", "agent", "adaptive"}:
        return "auto"
    if mode in {"off", "none", "false", "disable"}:
        return "off"
    return "always"


def _extract_storyboard_captions(storyboard: Dict[str, Any] | None) -> List[str]:
    """Return non-empty scene captions in storyboard order."""
    scenes = storyboard.get("scenes", []) if isinstance(storyboard, dict) else []
    captions: List[str] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        text = str(scene.get("text") or "").strip()
        if text:
            captions.append(text)
    return captions


def _build_storyboard_system_prompt(nano_banana_mode: str, target_duration_seconds: int = 30) -> str:
    """Build the Gemini storyboard system prompt with configurable style guidance."""
    mode = _normalize_nano_banana_mode(nano_banana_mode)
    target_duration_seconds = _normalize_target_duration_seconds(target_duration_seconds)

    if mode == "off":
        style_requirement = """
Style Requirement:
Use a polished cinematic commercial aesthetic appropriate to the product and audience.
Do not force surreal or stylized 3D elements unless the user explicitly asks for them.
"""
    elif mode == "auto":
        style_requirement = """
Adaptive Style Requirement ("Nano Banana" when appropriate):
Decide whether the subject benefits from a vibrant, surreal, cohesive 3D render aesthetic.
If appropriate, explicitly apply "Nano Banana" cues such as Octane render, Unreal Engine 5 aesthetic,
high saturation, deep contrast, glassmorphism, abstract shapes, dreamlike floating elements.
If not appropriate, keep the style premium and cinematic while remaining visually coherent.
"""
    else:
        style_requirement = """
Crucial Style Requirement ("Nano Banana"):
All scene descriptions MUST explicitly dictate a highly vibrant, surreal, and cohesive 3D render style.
Use keywords like: "Octane render", "Unreal Engine 5 aesthetic", "high saturation", "deep contrast",
"abstract shapes", "glassmorphism", "dreamlike", and "floating elements".
"""

    target_scenes = _target_scene_count(target_duration_seconds)
    veo_budget = _target_veo_scene_budget(target_duration_seconds, target_scenes)
    hybrid_rule = (
        f'- HYBRID ASSEMBLY CRITICAL RULE: Use render_type "veo" for ONLY {veo_budget} high-impact scene(s), and set every other scene to "imagen".\n'
    )
    if target_duration_seconds >= 60:
        hybrid_rule += (
            '- For 60-second or longer videos, prioritize the opening hook and the final payoff/CTA for Veo motion.\n'
        )
    speed_requirement = ""
    if target_duration_seconds >= 60:
        speed_requirement = (
            "- Speed Priority: prefer 8-second scenes unless a shorter beat is truly necessary.\n"
            "- Keep the scene count as low as possible while still covering the full requested runtime.\n"
            "- Favor static image-backed coverage for the middle beats so generation finishes faster.\n"
        )

    return f"""
You are a world-class film director, cinematographer, and 3D technical artist.
Create a detailed storyboard for a short promotional video based on the user's prompt.
The video needs to be roughly {target_duration_seconds} seconds long.
Return ONLY valid JSON.

{style_requirement}

Structure:
{{
  "mood": "cinematic, vibrant, surreal, highly detailed 3D render",
  "scenes": [
    {{
      "description": "A visually rich scene description, emphasizing style, lighting, and cinematic motion cues.",
      "text": "On-screen caption",
      "duration": 6,
      "render_type": "veo"
    }}
  ]
}}

Rules:
- Aim for approximately {target_scenes} scenes.
- Scene duration must be 4, 6, or 8 seconds.
{hybrid_rule}- Descriptions should be extremely visual and production-ready (camera movement, lighting, composition).
- Ensure the scenes feel cohesive across the full ad.
{speed_requirement}"""



class DirectorService:
    def __init__(self):
        self.max_concurrency = int(os.getenv("DIRECTOR_MAX_CONCURRENCY", "4"))
        self.scene_timeout_seconds = int(os.getenv("DIRECTOR_SCENE_TIMEOUT_SECONDS", "240"))
        self.total_timeout_seconds = int(os.getenv("DIRECTOR_TOTAL_TIMEOUT_SECONDS", "1200"))
        self.enable_image_fallback = (
            os.getenv("DIRECTOR_ENABLE_IMAGE_FALLBACK", "1").strip().lower() in {"1", "true", "yes"}
        )
        self.fps = max(12, min(30, int(os.getenv("DIRECTOR_RENDER_FPS", "30"))))
        self.long_render_backend = str(os.getenv("DIRECTOR_LONG_RENDER_BACKEND", "auto") or "auto").strip().lower()
        self.fast_render_min_duration_seconds = int(os.getenv("DIRECTOR_FAST_RENDER_MIN_DURATION_SECONDS", "60"))

        self.supabase = get_service_client()
        if os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "1":
            self.client = genai.Client(
                vertexai=True,
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
        else:
            self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    async def _emit_progress(
        self,
        callback: Callable[[str, Dict[str, Any]], Awaitable[None] | None] | None,
        stage: str,
        payload: Dict[str, Any] | None = None,
    ) -> None:
        if callback is None:
            return
        data = payload or {}
        try:
            maybe_coro = callback(stage, data)
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
        except Exception as exc:
            logger.debug("Progress callback failed at stage=%s: %s", stage, exc)

    async def create_pro_video(
        self,
        prompt: str,
        user_id: str,
        progress_callback: Callable[[str, Dict[str, Any]], Awaitable[None] | None] | None = None,
        *,
        return_metadata: bool = False,
        nano_banana_mode: str = "always",
        target_duration_seconds: int = 30,
    ) -> Optional[str] | Dict[str, Any]:
        """
        Orchestrates professional multi-scene video creation:
        1) Storyboard generation
        2) Parallel scene generation (video first, image fallback)
        3) Remotion assembly
        4) Final upload
        """
        target_duration_seconds = _normalize_target_duration_seconds(target_duration_seconds)
        logger.info("Starting Pro Video creation for user=%s", user_id)
        await self._emit_progress(
            progress_callback,
            "planning_started",
            {"target_duration_seconds": target_duration_seconds},
        )

        storyboard = await self._generate_storyboard(
            prompt, nano_banana_mode=nano_banana_mode, target_duration_seconds=target_duration_seconds
        )
        if not storyboard:
            logger.error("Failed to generate storyboard")
            await self._emit_progress(progress_callback, "failed", {"reason": "storyboard_generation_failed"})
            return None

        scenes = storyboard.get("scenes", [])
        storyboard_captions = _extract_storyboard_captions(storyboard)
        if not scenes:
            logger.error("Storyboard has no scenes")
            await self._emit_progress(progress_callback, "failed", {"reason": "empty_storyboard"})
            return None
        logger.info("Generated storyboard with %s scenes", len(scenes))
        await self._emit_progress(
            progress_callback,
            "planning_done",
            {
                "scene_count": len(scenes),
                "storyboard_captions": storyboard_captions,
                "nano_banana_mode": _normalize_nano_banana_mode(nano_banana_mode),
                "target_duration_seconds": target_duration_seconds,
            },
        )

        semaphore = asyncio.Semaphore(max(1, self.max_concurrency))
        mood = storyboard.get("mood")

        async def process_with_limit(index: int, scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await asyncio.wait_for(
                    self._process_scene(index, scene, user_id),
                    timeout=self.scene_timeout_seconds,
                )

        tasks = [process_with_limit(index, scene) for index, scene in enumerate(scenes)]
        try:
            processed_scenes = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.total_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error("Director pipeline timed out while generating scenes")
            await self._emit_progress(progress_callback, "failed", {"reason": "scene_generation_timeout"})
            return None

        valid_scenes: List[Dict[str, Any]] = []
        for result in processed_scenes:
            if isinstance(result, Exception):
                logger.warning("Scene generation raised exception: %s", result)
                continue
            if result is not None:
                valid_scenes.append(result)

        if not valid_scenes:
            logger.error("All scene generations failed")
            await self._emit_progress(progress_callback, "failed", {"reason": "all_scenes_failed"})
            return None

        valid_scenes.sort(key=lambda scene: scene["index"])
        await self._emit_progress(progress_callback, "assets_done", {"scene_count": len(valid_scenes)})

        renderer = self._select_renderer_backend(
            total_duration_seconds=target_duration_seconds,
            scene_count=len(valid_scenes),
        )
        render_scenes, total_duration_frames = self._build_render_scenes(valid_scenes, renderer=renderer)

        bg_music_url = audio_music_service.select_background_music_url(mood)
        props = {
            "scenes": render_scenes,
            "fps": self.fps,
            "durationInFrames": max(1, total_duration_frames),
            "bgMusicUrl": bg_music_url,
            "bgMusicVolume": 0.35,
            "voiceoverVolume": 1.0,
        }

        logger.info("Rendering final composition with %s...", "ffmpeg" if renderer == "ffmpeg" else "Remotion")
        await self._emit_progress(
            progress_callback,
            "rendering_started",
            {"duration_frames": props["durationInFrames"], "render_backend": renderer},
        )
        render_fn = (
            remotion_render_service.render_programmatic_video_ffmpeg
            if renderer == "ffmpeg"
            else remotion_render_service.render_programmatic_video
        )
        mp4_bytes, asset_id = await asyncio.to_thread(
            render_fn,
            props,
            user_id,
        )
        if not mp4_bytes:
            logger.error("%s rendering failed", "FFmpeg" if renderer == "ffmpeg" else "Remotion")
            remotion_diagnostics = remotion_render_service.get_last_render_diagnostics()
            failure_payload: Dict[str, Any] = {"reason": "remotion_render_failed", "render_backend": renderer}
            if remotion_diagnostics:
                failure_payload["remotion_diagnostics"] = remotion_diagnostics
            await self._emit_progress(progress_callback, "failed", failure_payload)
            return None

        path = f"{user_id}/{asset_id}.mp4"
        
        upload_success = False
        for attempt in range(3):
            try:
                await asyncio.to_thread(
                    self.supabase.storage.from_(VIDEO_BUCKET).upload,
                    path,
                    mp4_bytes,
                    {"content-type": "video/mp4"},
                )
                upload_success = True
                break
            except Exception as e:
                logger.warning(f"Remotion video upload failed (attempt {attempt+1}/3): {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        
        if not upload_success:
            logger.error("Failed to upload final Remotion composition")
            await self._emit_progress(progress_callback, "failed", {"reason": "upload_failed"})
            return None

        try:
            public_url = await asyncio.to_thread(
                self.supabase.storage.from_(VIDEO_BUCKET).get_public_url, path
            )
            from app.services.request_context import (
                get_current_session_id,
                get_current_workflow_execution_id,
            )

            session_id = get_current_session_id()
            workflow_execution_id = get_current_workflow_execution_id()
            media_metadata = {
                "prompt": prompt,
                "source": "director_service",
                "storyboard_captions": storyboard_captions,
                "scene_count": len(valid_scenes),
                "nano_banana_mode": _normalize_nano_banana_mode(nano_banana_mode),
                "session_id": session_id,
                "workflow_execution_id": workflow_execution_id,
            }
            try:
                self.supabase.table("media_assets").upsert(
                    {
                        "id": asset_id,
                        "user_id": user_id,
                        "bucket_id": VIDEO_BUCKET,
                        "asset_type": "video",
                        "title": (prompt[:80] + "…") if len(prompt) > 80 else prompt,
                        "filename": f"{asset_id}.mp4",
                        "file_path": path,
                        "file_url": public_url,
                        "file_type": "video/mp4",
                        "category": "generated",
                        "size_bytes": len(mp4_bytes),
                        "metadata": media_metadata,
                    },
                    on_conflict="id",
                ).execute()
            except Exception as exc:
                logger.warning("Failed to save director output to media_assets: %s", exc)

            try:
                from app.rag.knowledge_vault import ingest_document_content

                await ingest_document_content(
                    content=f"Generated pro video: {prompt}. Asset ID: {asset_id}.",
                    title=f"Video: {(prompt[:80] + '…') if len(prompt) > 80 else prompt}",
                    document_type="media",
                    user_id=user_id,
                    metadata={"asset_id": asset_id, "asset_type": "video", **media_metadata},
                )
            except Exception as exc:
                logger.warning("Knowledge vault ingest for director video failed: %s", exc)

            logger.info("Pro Video created successfully: %s", public_url)
            result_payload: Dict[str, Any] = {
                "asset_id": asset_id,
                "storage_path": path,
                "video_url": public_url,
                "storyboard": storyboard,
                "storyboard_captions": storyboard_captions,
                "mood": mood,
                "scenes": valid_scenes,
                "render_backend": renderer,
                "nano_banana_mode": media_metadata["nano_banana_mode"],
                "session_id": session_id,
                "workflow_execution_id": workflow_execution_id,
            }
            await self._emit_progress(
                progress_callback,
                "completed",
                {
                    "asset_id": asset_id,
                    "video_url": public_url,
                    "storyboard_captions": storyboard_captions,
                    "scene_count": len(valid_scenes),
                    "render_backend": renderer,
                    "nano_banana_mode": result_payload["nano_banana_mode"],
                },
            )
            if return_metadata:
                return result_payload
            return public_url
        except Exception as exc:
            logger.error("Failed to upload final video: %s", exc)
            await self._emit_progress(progress_callback, "failed", {"reason": "final_upload_failed", "error": str(exc)})
            return None

    def _build_render_scenes(
        self,
        valid_scenes: List[Dict[str, Any]],
        *,
        renderer: str,
    ) -> tuple[List[Dict[str, Any]], int]:
        render_scenes: List[Dict[str, Any]] = []
        total_duration_frames = 0
        for scene in valid_scenes:
            duration = _clamp_scene_duration(scene.get("duration", 4))
            total_duration_frames += int(duration * self.fps)
            render_scene: Dict[str, Any] = {
                "text": scene.get("text", ""),
                "duration": duration,
                "videoUrl": scene.get("video_url"),
                "imageUrl": scene.get("image_url"),
                "voiceoverUrl": scene.get("voiceover_url"),
            }
            if renderer == "ffmpeg":
                render_scene.update(
                    {
                        "videoBytes": scene.get("video_bytes"),
                        "imageBytes": scene.get("image_bytes"),
                        "voiceoverBytes": scene.get("voiceover_bytes"),
                        "voiceoverMimeType": scene.get("voiceover_mime_type"),
                    }
                )
            else:
                render_scene.update(
                    {
                        "captions": [
                            {
                                "text": scene.get("text", ""),
                                "startFrame": 0,
                                "endFrame": max(1, int(duration * self.fps) - 1),
                            }
                        ]
                        if scene.get("text")
                        else [],
                        "transition": {"type": "fade", "durationFrames": 15},
                    }
                )
            render_scenes.append(render_scene)
        return render_scenes, total_duration_frames

    def _select_renderer_backend(self, *, total_duration_seconds: int, scene_count: int) -> str:
        backend = self.long_render_backend
        if backend in {"ffmpeg", "remotion"}:
            return backend
        if scene_count > 1 and total_duration_seconds >= self.fast_render_min_duration_seconds:
            return "ffmpeg"
        return "remotion"

    async def _generate_storyboard(self, prompt: str, nano_banana_mode: str = "always", target_duration_seconds: int = 30) -> Optional[Dict[str, Any]]:
        """Use Gemini to create and normalize a structured storyboard."""
        system_prompt = _build_storyboard_system_prompt(nano_banana_mode, target_duration_seconds)
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=STORYBOARD_MODEL,
                contents=[system_prompt, f"User Prompt: {prompt}"],
                config=GenerateContentConfig(response_mime_type="application/json"),
            )
            raw_storyboard = json.loads(response.text)
            return self._normalize_storyboard(raw_storyboard, prompt, target_duration_seconds=target_duration_seconds)
        except Exception as exc:
            logger.error("Storyboard generation failed: %s", exc)
            return None

    def _normalize_storyboard(
        self, storyboard: Dict[str, Any], prompt: str, *, target_duration_seconds: int = 30
    ) -> Dict[str, Any]:
        """Normalize model output to a resilient storyboard contract."""
        mood = str(storyboard.get("mood") or storyboard.get("audio_mood") or "cinematic")
        raw_scenes = storyboard.get("scenes") or []

        normalized_scenes: List[Dict[str, Any]] = []
        for item in raw_scenes:
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or item.get("desc") or "").strip()
            text = str(item.get("text") or "").strip()
            if not description:
                description = f"Cinematic scene inspired by: {prompt}"
            normalized_scenes.append(
                {
                    "description": description,
                    "text": text,
                    "duration": _clamp_scene_duration(item.get("duration", 4)),
                    **(
                        {"render_type": str(item.get("render_type") or "").strip().lower()}
                        if str(item.get("render_type") or "").strip().lower() in {"veo", "imagen"}
                        else {}
                    ),
                }
            )

        if not normalized_scenes:
            normalized_scenes = [
                {
                    "description": f"Cinematic establishing shot inspired by: {prompt}",
                    "text": "",
                    "duration": 4,
                    "render_type": "veo",
                }
            ]

        normalized_scenes = _apply_render_type_budget(
            normalized_scenes,
            target_duration_seconds=target_duration_seconds,
        )

        return {"mood": mood, "scenes": normalized_scenes}

    async def _generate_image_asset_for_scene(
        self,
        *,
        description: str,
        user_id: str,
        style_hint: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[bytes]]:
        """Generate and upload a scene image, returning its public URL and raw bytes."""
        request_kwargs: Dict[str, Any] = {
            "prompt": description or "cinematic background",
            "aspect_ratio": "16:9",
            "number_of_images": 1,
        }
        if style_hint:
            request_kwargs["style_hint"] = style_hint

        image_result = await asyncio.to_thread(
            vertex_image_service.generate_image,
            **request_kwargs,
        )
        image_b64 = image_result.get("image_bytes_base64") if isinstance(image_result, dict) else None
        if not image_b64:
            return None, None

        import base64

        image_bytes = base64.b64decode(image_b64)
        filename = f"img_{uuid.uuid4()}.png"
        path = f"{user_id}/assets/{filename}"
        await asyncio.to_thread(
            self.supabase.storage.from_(ASSET_BUCKET).upload,
            path,
            image_bytes,
            {"content-type": "image/png"},
        )
        image_url = self.supabase.storage.from_(ASSET_BUCKET).get_public_url(path)
        return image_url, image_bytes

    async def _process_scene(self, index: int, scene: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        """Generate assets for a single scene with Veo-first animation and optional image fallback."""
        description = str(scene.get("description") or "").strip()
        text = str(scene.get("text") or "").strip()
        duration = _clamp_scene_duration(scene.get("duration", 4))
        render_type = str(scene.get("render_type") or "veo").strip().lower()

        try:
            image_url: Optional[str] = None

            if render_type == "imagen":
                logger.info("Generating static image for scene %s", index)
                image_url, image_bytes = await self._generate_image_asset_for_scene(
                    description=description,
                    user_id=user_id,
                )
                if not image_url:
                    logger.warning("Imagen scene generation failed for %s", index)
                    return None
                voiceover_url, voiceover_bytes, voiceover_mime_type = await self._generate_voiceover_asset_for_scene(user_id, text)
                return {
                    "index": index,
                    "text": text,
                    "duration": duration,
                    "video_url": None,
                    "video_bytes": None,
                    "image_url": image_url,
                    "image_bytes": image_bytes,
                    "voiceover_url": voiceover_url,
                    "voiceover_bytes": voiceover_bytes,
                    "voiceover_mime_type": voiceover_mime_type,
                    "description": description,
                }

            logger.info("Animating scene %s with Veo 3", index)
            result = await asyncio.to_thread(
                vertex_video_service.generate_video,
                prompt=description,
                duration_seconds=duration,
                aspect_ratio="16:9",
                number_of_videos=1,
            )

            if result.get("success"):
                video_bytes = result.get("video_bytes")
                video_url = result.get("video_url")

                if video_bytes:
                    filename = f"{uuid.uuid4()}.mp4"
                    path = f"{user_id}/assets/{filename}"
                    await asyncio.to_thread(
                        self.supabase.storage.from_(ASSET_BUCKET).upload,
                        path,
                        video_bytes,
                        {"content-type": "video/mp4"},
                    )
                    public_url = self.supabase.storage.from_(ASSET_BUCKET).get_public_url(path)
                    voiceover_url, voiceover_bytes, voiceover_mime_type = await self._generate_voiceover_asset_for_scene(user_id, text)
                    return {
                        "index": index,
                        "text": text,
                        "duration": duration,
                        "video_url": public_url,
                        "video_bytes": video_bytes,
                        "image_url": image_url,
                        "image_bytes": None,
                        "voiceover_url": voiceover_url,
                        "voiceover_bytes": voiceover_bytes,
                        "voiceover_mime_type": voiceover_mime_type,
                        "description": description,
                    }

                if video_url:
                    # Keep direct URL path so we do not drop otherwise valid Veo output.
                    voiceover_url, voiceover_bytes, voiceover_mime_type = await self._generate_voiceover_asset_for_scene(user_id, text)
                    return {
                        "index": index,
                        "text": text,
                        "duration": duration,
                        "video_url": video_url,
                        "video_bytes": None,
                        "image_url": image_url,
                        "image_bytes": None,
                        "voiceover_url": voiceover_url,
                        "voiceover_bytes": voiceover_bytes,
                        "voiceover_mime_type": voiceover_mime_type,
                        "description": description,
                    }

            logger.warning("Veo scene generation failed for %s: %s", index, result.get("error"))
        except Exception as exc:
            logger.warning("Veo scene generation exception for %s: %s", index, exc)

        if not self.enable_image_fallback:
            return None

        try:
            logger.warning("Falling back to static image for scene %s", index)
            image_url, image_bytes = await self._generate_image_asset_for_scene(
                description=description,
                user_id=user_id,
                style_hint="cinematic",
            )
            if not image_url:
                return None
            voiceover_url, voiceover_bytes, voiceover_mime_type = await self._generate_voiceover_asset_for_scene(user_id, text)
            return {
                "index": index,
                "text": text,
                "duration": duration,
                "video_url": None,
                "video_bytes": None,
                "image_url": image_url,
                "image_bytes": image_bytes,
                "voiceover_url": voiceover_url,
                "voiceover_bytes": voiceover_bytes,
                "voiceover_mime_type": voiceover_mime_type,
                "description": description,
            }
        except Exception as exc:
            logger.warning("Image fallback failed for scene %s: %s", index, exc)
            return None

    async def _generate_voiceover_asset_for_scene(
        self,
        user_id: str,
        text: str,
    ) -> tuple[Optional[str], Optional[bytes], Optional[str]]:
        """Generate scene voiceover and keep raw audio bytes for local assembly."""
        if not text.strip():
            return None, None, None
        result = await asyncio.to_thread(
            voiceover_service.synthesize_speech,
            text,
        )
        audio_bytes = result.get("audio_bytes")
        mime_type = result.get("mime_type") or "audio/mpeg"
        if not result.get("success") or not audio_bytes:
            return None, None, None
        try:
            filename = f"{uuid.uuid4()}.mp3"
            path = f"{user_id}/assets/{filename}"
            await asyncio.to_thread(
                self.supabase.storage.from_(ASSET_BUCKET).upload,
                path,
                audio_bytes,
                {"content-type": mime_type},
            )
            return self.supabase.storage.from_(ASSET_BUCKET).get_public_url(path), audio_bytes, mime_type
        except Exception as exc:
            logger.warning("Voiceover upload failed: %s", exc)
            return None, audio_bytes, mime_type

    async def _generate_voiceover_for_scene(self, user_id: str, text: str) -> Optional[str]:
        voiceover_url, _audio_bytes, _mime_type = await self._generate_voiceover_asset_for_scene(user_id, text)
        return voiceover_url





