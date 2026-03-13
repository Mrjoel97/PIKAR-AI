# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Vertex AI Veo video generation service."""

import logging
import os
import time
from typing import Any
logger = logging.getLogger(__name__)

VERTEX_VIDEO_MODEL_PRIMARY = os.getenv("VERTEX_VIDEO_MODEL_PRIMARY", "veo-3.1-fast-generate-preview")
VERTEX_VIDEO_MODEL_FALLBACK = os.getenv("VERTEX_VIDEO_MODEL_FALLBACK", "veo-3.1-generate-preview")
VEO_POLL_INTERVAL = int(os.getenv("VEO_POLL_INTERVAL", "4"))
VEO_POLL_INTERVAL_MIN = int(os.getenv("VEO_POLL_INTERVAL_MIN", "2"))
VEO_POLL_INTERVAL_MAX = int(os.getenv("VEO_POLL_INTERVAL_MAX", "8"))
VEO_POLL_TIMEOUT = int(os.getenv("VEO_POLL_TIMEOUT", "600"))


def generate_video(
    prompt: str,
    *,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    number_of_videos: int = 1,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Generate video using Vertex Veo models."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        return {
            "success": False,
            "video_bytes": None,
            "video_url": None,
            "model_used": None,
            "error": "GOOGLE_CLOUD_PROJECT not set",
        }

    duration = 4 if duration_seconds <= 4 else 6 if duration_seconds <= 6 else 8
    if aspect_ratio not in ("16:9", "9:16"):
        aspect_ratio = "16:9"

    last_error: str | None = None
    for model_id in [VERTEX_VIDEO_MODEL_PRIMARY, VERTEX_VIDEO_MODEL_FALLBACK]:
        try:
            logger.info("Attempting video generation with model: %s", model_id)
            result = _generate_video_with_sdk(
                project=project,
                location=location,
                model_id=model_id,
                prompt=prompt,
                duration_seconds=duration,
                aspect_ratio=aspect_ratio,
                number_of_videos=number_of_videos,
                image_bytes=image_bytes,
            )
            if result.get("success"):
                return result
            last_error = result.get("error")
            logger.warning("Veo model %s failed: %s", model_id, result.get("error"))
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Veo model %s raised exception: %s", model_id, exc)

    return {
        "success": False,
        "video_bytes": None,
        "video_url": None,
        "model_used": None,
        "error": last_error or "Video generation failed with configured Vertex models",
    }


def _infer_image_mime_type(image_bytes: bytes | None) -> str:
    """Infer a best-effort MIME type for image-to-video prompts."""
    if not image_bytes:
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _generate_video_with_sdk(
    project: str,
    location: str,
    model_id: str,
    prompt: str,
    duration_seconds: int,
    aspect_ratio: str,
    number_of_videos: int,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Call Vertex Veo using google-genai SDK."""
    try:
        from google import genai
        from google.genai.types import GenerateVideosConfig, Image
    except ImportError:
        return {
            "success": False,
            "video_bytes": None,
            "video_url": None,
            "model_used": model_id,
            "error": "google-genai SDK not installed",
        }

    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        config = GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            number_of_videos=min(max(1, number_of_videos), 4),
        )

        request_kwargs: dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "config": config,
        }
        if image_bytes:
            request_kwargs["image"] = Image(
                image_bytes=image_bytes,
                mime_type=_infer_image_mime_type(image_bytes),
            )

        operation = client.models.generate_videos(**request_kwargs)

        start_time = time.monotonic()
        poll_interval = min(max(1, VEO_POLL_INTERVAL_MIN, VEO_POLL_INTERVAL), max(1, VEO_POLL_INTERVAL_MAX))
        while not operation.done:
            if time.monotonic() - start_time > VEO_POLL_TIMEOUT:
                return {
                    "success": False,
                    "video_bytes": None,
                    "video_url": None,
                    "model_used": model_id,
                    "error": "Veo operation timed out",
                }
            time.sleep(poll_interval)
            poll_interval = min(max(1, VEO_POLL_INTERVAL_MAX), max(1, int(poll_interval * 1.5)))
            try:
                operation = client.operations.get(operation)
            except Exception as exc:
                logger.warning("Veo polling transient error: %s", exc)

        if not operation.result:
            return {
                "success": False,
                "video_bytes": None,
                "video_url": None,
                "model_used": model_id,
                "error": "Veo operation completed but returned no result",
            }

        generated_videos = getattr(operation.result, "generated_videos", None) or []
        if not generated_videos:
            return {
                "success": False,
                "video_bytes": None,
                "video_url": None,
                "model_used": model_id,
                "error": "Veo result contained no generated_videos",
            }

        video_result = generated_videos[0]
        video_obj = getattr(video_result, "video", None)
        video_url = getattr(video_obj, "uri", None) if video_obj else None
        video_bytes = getattr(video_obj, "video_bytes", None) if video_obj else None

        if not video_bytes and not video_url:
            return {
                "success": False,
                "video_bytes": None,
                "video_url": None,
                "model_used": model_id,
                "error": "Could not extract video bytes or URL from Veo result",
            }

        return {
            "success": True,
            "video_bytes": video_bytes,
            "video_url": video_url,
            "model_used": model_id,
        }
    except Exception as exc:
        logger.error("Veo SDK error: %s", exc)
        return {
            "success": False,
            "video_bytes": None,
            "video_url": None,
            "model_used": model_id,
            "error": str(exc),
        }
