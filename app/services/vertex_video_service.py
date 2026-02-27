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

"""Vertex AI Veo video generation service (primary + fallback).

Video storage and in-app playback are required for all users.
Uses predictLongRunning API; polls until complete then returns video bytes or GCS URI.
"""

import base64
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

VERTEX_VIDEO_MODEL_PRIMARY = os.getenv("VERTEX_VIDEO_MODEL_PRIMARY", "veo-3.1-generate-001")
VERTEX_VIDEO_MODEL_FALLBACK = os.getenv("VERTEX_VIDEO_MODEL_FALLBACK", "veo-3.0-generate-001")
VEO_POLL_INTERVAL = int(os.getenv("VEO_POLL_INTERVAL", "15"))
VEO_POLL_INTERVAL_MIN = int(os.getenv("VEO_POLL_INTERVAL_MIN", "2"))
VEO_POLL_INTERVAL_MAX = int(os.getenv("VEO_POLL_INTERVAL_MAX", "10"))
VEO_POLL_TIMEOUT = int(os.getenv("VEO_POLL_TIMEOUT", "600"))  # 10 min max wait


def generate_video(
    prompt: str,
    *,
    duration_seconds: int = 6,
    aspect_ratio: str = "16:9",
    number_of_videos: int = 1,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Generate video using Vertex AI Veo (Veo 3 primary, Veo 3.0 fallback).

    Uses the google-genai SDK to submit the job, poll until complete,
    then returns video bytes or storage URI. Requires Vertex AI and a project
    with Veo enabled.

    Args:
        prompt: Text prompt for video generation.
        duration_seconds: 4, 6, or 8 (Veo 3).
        aspect_ratio: "16:9" or "9:16".
        number_of_videos: 1–4.
        image_bytes: Optional image bytes to animate (Image-to-Video).

    Returns:
        Dict with:
          - success: bool
          - video_bytes: bytes | None
          - video_url: str | None (GCS or signed URL if storage_uri was set)
          - model_used: str | None
          - error: str (if success is False)
    """
    models_to_try = [VERTEX_VIDEO_MODEL_PRIMARY, VERTEX_VIDEO_MODEL_FALLBACK]
    
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

    # Veo 3 supports 4, 6, 8 seconds. Clamp to nearest valid.
    duration = 8
    if duration_seconds <= 4:
        duration = 4
    elif duration_seconds <= 6:
        duration = 6
    else:
        duration = 8

    # Ensure aspect ratio is valid
    if aspect_ratio not in ("16:9", "9:16"):
        aspect_ratio = "16:9"

    for model_id in models_to_try:
        try:
            logger.info(f"Attempting video generation with model: {model_id}")
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
            
            logger.warning(f"Veo model {model_id} failed: {result.get('error')}")
            continue
        except Exception as e:
            logger.warning(f"Veo model {model_id} raised exception: {e}")
            continue
            
    return {
        "success": False,
        "video_bytes": None,
        "video_url": None,
        "model_used": None,
        "error": "Video generation failed with primary and fallback models",
    }


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
        # Import inside function to avoid hard dependency if SDK not installed
        from google import genai
        from google.genai.types import GenerateVideosConfig, Part
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
        
        # Veo 3 supports audio generation
        generate_audio = True if "veo-3" in model_id or "veo-3.1" in model_id else False

        config = GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            generate_audio=generate_audio,
             # We let it return base64 by default (no output_gcs_uri) unless configured otherwise
            # If we need GCS, we can add output_gcs_uri="gs://..."
        )

        # Prepare payload: if we have an image, pass image + prompt text
        payload = prompt
        if image_bytes:
            # We must use proper Part types or dicts for the new SDK
            payload = [
                Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ]

        logger.info(f"Submitting Veo job to {model_id}...")
        operation = client.models.generate_videos(
            model=model_id,
            prompt=payload,
            config=config,
        )
        
        logger.info(f"Veo operation started: {operation.name if hasattr(operation, 'name') else 'unknown'}")

        # Poll until done (adaptive backoff lowers completion latency for short jobs)
        start_time = time.monotonic()
        poll_interval = min(
            max(1, VEO_POLL_INTERVAL_MIN, VEO_POLL_INTERVAL),
            max(1, VEO_POLL_INTERVAL_MAX),
        )
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
            poll_interval = min(
                max(1, VEO_POLL_INTERVAL_MAX),
                max(1, int(poll_interval * 1.5)),
            )
            try:
                operation = client.operations.get(operation)
            except Exception as e:
                 # If polling fails transiently, log and retry
                 logger.warning(f"Veo polling transient error: {e}")
        
        if not operation.result:
             return {
                "success": False,
                "video_bytes": None,
                "video_url": None,
                "model_used": model_id,
                "error": "Veo operation completed but returned no result",
            }

        # Check for generated videos
        if not hasattr(operation.result, 'generated_videos') or not operation.result.generated_videos:
             return {
                "success": False,
                "video_bytes": None,
                "video_url": None,
                "model_used": model_id,
                "error": "Veo result contained no generated_videos",
            }
        
        # Get the first video
        video_result = operation.result.generated_videos[0]
        
        video_bytes = None
        video_url = None
        
        if hasattr(video_result, 'video') and hasattr(video_result.video, 'uri'):
             video_url = video_result.video.uri
        
        # Accessing bytes might differ based on SDK version or response mode
        # If no URI was provided in config, it often returns bytes in the response object 
        # but the SDK structures it typically as a GCS URI if configured or base64 in the raw response
        # Let's check if the SDK object exposes bytes directly
        
        # Inspecting the SDK types, generated_videos[0].video usually has uri.
        # If output_gcs_uri was NOT set, where is the content?
        # The new SDK might wrap the bytes.
        
        # Fallback to inspecting raw response if needed, but let's try standard attribute access first.
        # Based on the documentation: "If a Cloud Storage bucket isn't provided, base64-encoded video bytes are returned in the response."
        
        # From SDK source/docs for Veo 3:
        # generated_videos[0].video.video_bytes might exist if inline.
        
        if hasattr(video_result, 'video') and hasattr(video_result.video, 'video_bytes'):
             video_bytes = video_result.video.video_bytes
        
        # If bytes are not directly on the object, we might need to look at the raw proto/dict
        if not video_bytes and not video_url:
             # Try to find base64 in the raw result if accessible
             # This is a best-effort if the high-level object doesn't expose it easily
             pass

        if video_url and not video_bytes:
             # We have a GCS URI. If we didn't provide one, it might be a temporary one?
             # Actually docs say "If a Cloud Storage bucket isn't provided, base64-encoded video bytes are returned".
             # So we expect bytes.
             pass
             
        # If we still don't have bytes but have a result object, let's try to assume it worked 
        # and maybe the bytes are available via `bytes_base64_encoded` if we dump it.
        # But for now, let's return what we have.
        
        if not video_bytes and not video_url:
              # Last ditch: check if 'bytes_base64_encoded' is in the raw prediction if we can access it
              # simplified: return success=False if we absolutely strictly need bytes/url
              # But let's log the result object to help debug
              logger.info(f"Veo Result Object: {operation.result}")
              return {
                "success": False, 
                "error": "Could not extract video bytes or URL from Veo result",
                "model_used": model_id
              }

        return {
            "success": True,
            "video_bytes": video_bytes,
            "video_url": video_url,
            "model_used": model_id,
        }

    except Exception as e:
        logger.error(f"Veo SDK error: {e}")
        return {
            "success": False,
            "video_bytes": None,
            "video_url": None,
            "model_used": model_id,
            "error": str(e),
        }
