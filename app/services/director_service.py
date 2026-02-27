import asyncio
import json
import logging
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

    target_scenes = max(3, target_duration_seconds // 6)

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
- HYBRID ASSEMBLY CRITICAL RULE: You MUST select exactly 3 to 5 scenes as high-impact key moments (e.g., the strong intro hook, the climax, or the call-to-action). Set `"render_type": "veo"` for ONLY these scenes.
- All other scenes MUST have `"render_type": "imagen"`. Do NOT set more than 5 scenes as "veo".
- Descriptions should be extremely visual and production-ready (camera movement, lighting, composition).
- Ensure the scenes feel cohesive across the full ad.
"""



class DirectorService:
    def __init__(self):
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.max_concurrency = int(os.getenv("DIRECTOR_MAX_CONCURRENCY", "3"))
        self.scene_timeout_seconds = int(os.getenv("DIRECTOR_SCENE_TIMEOUT_SECONDS", "240"))
        self.total_timeout_seconds = int(os.getenv("DIRECTOR_TOTAL_TIMEOUT_SECONDS", "1200"))
        self.enable_image_fallback = (
            os.getenv("DIRECTOR_ENABLE_IMAGE_FALLBACK", "1").strip().lower() in {"1", "true", "yes"}
        )
        self.fps = 30

        self.supabase = get_service_client()
        self.client = genai.Client(vertexai=True, project=self.project, location=self.location)

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
        logger.info("Starting Pro Video creation for user=%s", user_id)
        await self._emit_progress(progress_callback, "planning_started")

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

        remotion_scenes: List[Dict[str, Any]] = []
        total_duration_frames = 0
        for scene in valid_scenes:
            duration = _clamp_scene_duration(scene.get("duration", 4))
            total_duration_frames += int(duration * self.fps)
            remotion_scene = {
                "text": scene.get("text", ""),
                "duration": duration,
                "videoUrl": scene.get("video_url"),
                "imageUrl": scene.get("image_url"),
                "voiceoverUrl": scene.get("voiceover_url"),
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
            remotion_scenes.append(remotion_scene)

        bg_music_url = audio_music_service.select_background_music_url(mood)
        props = {
            "scenes": remotion_scenes,
            "fps": self.fps,
            "durationInFrames": max(1, total_duration_frames),
            "bgMusicUrl": bg_music_url,
            "bgMusicVolume": 0.35,
            "voiceoverVolume": 1.0,
        }

        logger.info("Rendering final composition with Remotion...")
        await self._emit_progress(progress_callback, "rendering_started", {"duration_frames": props["durationInFrames"]})
        mp4_bytes, asset_id = await asyncio.to_thread(
            remotion_render_service.render_programmatic_video,
            props,
            user_id,
        )
        if not mp4_bytes:
            logger.error("Remotion rendering failed")
            await self._emit_progress(progress_callback, "failed", {"reason": "remotion_render_failed"})
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
            logger.info("Pro Video created successfully: %s", public_url)
            result_payload: Dict[str, Any] = {
                "video_url": public_url,
                "storyboard": storyboard,
                "storyboard_captions": storyboard_captions,
                "mood": mood,
                "scenes": valid_scenes,
                "nano_banana_mode": _normalize_nano_banana_mode(nano_banana_mode),
            }
            await self._emit_progress(
                progress_callback,
                "completed",
                {
                    "video_url": public_url,
                    "storyboard_captions": storyboard_captions,
                    "scene_count": len(valid_scenes),
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
            return self._normalize_storyboard(raw_storyboard, prompt)
        except Exception as exc:
            logger.error("Storyboard generation failed: %s", exc)
            return None

    def _normalize_storyboard(self, storyboard: Dict[str, Any], prompt: str) -> Dict[str, Any]:
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

        # Ensure render_type is populated
        for i, scene in enumerate(normalized_scenes):
            if "render_type" not in scene:
                scene["render_type"] = "veo" if i < 3 else "imagen"

        return {"mood": mood, "scenes": normalized_scenes}

    async def _process_scene(self, index: int, scene: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        """Generate assets for a single scene (Imagen -> Veo -> upload, with image fallback)."""
        description = str(scene.get("description") or "").strip()
        text = str(scene.get("text") or "").strip()
        duration = _clamp_scene_duration(scene.get("duration", 4))

        try:
            logger.info("Generating base image for scene %s", index)
            image_result = await asyncio.to_thread(
                vertex_image_service.generate_image,
                prompt=description,
                aspect_ratio="16:9",
                number_of_images=1,
            )

            image_url = None
            image_bytes = None
            if image_result.get("success"):
                b64 = image_result.get("image_bytes_base64")
                if b64:
                    import base64
                    image_bytes = base64.b64decode(b64)
                    
                    filename = f"img_{uuid.uuid4()}.png"
                    path = f"{user_id}/assets/{filename}"
                    await asyncio.to_thread(
                        self.supabase.storage.from_(ASSET_BUCKET).upload,
                        path,
                        image_bytes,
                        {"content-type": "image/png"},
                    )
                    image_url = self.supabase.storage.from_(ASSET_BUCKET).get_public_url(path)
                    logger.info("Base image generated: %s", image_url)

            if scene.get("render_type") == "imagen":
                logger.info("Scene %s is imagen-only; skipping Veo 3 animation", index)
                voiceover_url = await self._generate_voiceover_for_scene(user_id, text)
                return {
                    "index": index,
                    "text": text,
                    "duration": duration,
                    "video_url": None,
                    "image_url": image_url,
                    "voiceover_url": voiceover_url,
                    "description": description,
                }

            logger.info("Animating scene %s with Veo 3", index)
            result = await asyncio.to_thread(
                vertex_video_service.generate_video,
                prompt=description,
                duration_seconds=duration,
                aspect_ratio="16:9",
                number_of_videos=1,
                image_bytes=image_bytes,
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
                    voiceover_url = await self._generate_voiceover_for_scene(user_id, text)
                    return {
                        "index": index,
                        "text": text,
                        "duration": duration,
                        "video_url": public_url,
                        "image_url": image_url,
                        "voiceover_url": voiceover_url,
                        "description": description,
                    }

                if video_url:
                    # Keep direct URL path so we do not drop otherwise valid Veo output.
                    voiceover_url = await self._generate_voiceover_for_scene(user_id, text)
                    return {
                        "index": index,
                        "text": text,
                        "duration": duration,
                        "video_url": video_url,
                        "image_url": image_url,
                        "voiceover_url": voiceover_url,
                        "description": description,
                    }

            if image_url and self.enable_image_fallback:
                logger.warning("Veo failed, falling back to static image for scene %s", index)
                voiceover_url = await self._generate_voiceover_for_scene(user_id, text)
                return {
                    "index": index,
                    "text": text,
                    "duration": duration,
                    "video_url": None,
                    "image_url": image_url,
                    "voiceover_url": voiceover_url,
                    "description": description,
                }

            logger.warning("Veo scene generation failed for %s: %s", index, result.get("error"))
        except Exception as exc:
            logger.warning("Veo scene generation exception for %s: %s", index, exc)

        if not self.enable_image_fallback:
            return None

        try:
            image_result = await asyncio.to_thread(
                vertex_image_service.generate_image,
                prompt=description or "cinematic background",
                aspect_ratio="16:9",
                style_hint="cinematic",
                number_of_images=1,
            )
            image_b64 = image_result.get("image_bytes_base64") if isinstance(image_result, dict) else None
            if not image_b64:
                return None

            # image_b64 is already base64 string.
            import base64

            raw_bytes = base64.b64decode(image_b64)
            filename = f"{uuid.uuid4()}.png"
            path = f"{user_id}/assets/{filename}"
            await asyncio.to_thread(
                self.supabase.storage.from_(ASSET_BUCKET).upload,
                path,
                raw_bytes,
                {"content-type": "image/png"},
            )
            public_url = self.supabase.storage.from_(ASSET_BUCKET).get_public_url(path)
            voiceover_url = await self._generate_voiceover_for_scene(user_id, text)
            return {
                "index": index,
                "text": text,
                "duration": duration,
                "image_url": public_url,
                "voiceover_url": voiceover_url,
                "description": description,
            }
        except Exception as exc:
            logger.warning("Image fallback failed for scene %s: %s", index, exc)
            return None

    async def _generate_voiceover_for_scene(self, user_id: str, text: str) -> Optional[str]:
        """Generate and upload scene voiceover; gracefully no-op on failure."""
        if not text.strip():
            return None
        result = await asyncio.to_thread(
            voiceover_service.synthesize_speech,
            text,
        )
        if not result.get("success") or not result.get("audio_bytes"):
            return None
        try:
            filename = f"{uuid.uuid4()}.mp3"
            path = f"{user_id}/assets/{filename}"
            await asyncio.to_thread(
                self.supabase.storage.from_(ASSET_BUCKET).upload,
                path,
                result["audio_bytes"],
                {"content-type": result.get("mime_type") or "audio/mpeg"},
            )
            return self.supabase.storage.from_(ASSET_BUCKET).get_public_url(path)
        except Exception as exc:
            logger.warning("Voiceover upload failed: %s", exc)
            return None
