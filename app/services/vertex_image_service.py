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

"""Vertex AI image generation service."""

import base64
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

VERTEX_IMAGE_MODEL_PRIMARY = os.getenv(
    "VERTEX_IMAGE_MODEL_PRIMARY", "imagen-4.0-fast-generate-001"
)
VERTEX_IMAGE_MODEL_FALLBACK = os.getenv(
    "VERTEX_IMAGE_MODEL_FALLBACK", "imagen-4.0-generate-001"
)


def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    style_hint: str | None = None,
    number_of_images: int = 1,
) -> dict[str, Any]:
    """Generate image(s) using Vertex Imagen models."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        return {
            "success": False,
            "error": "GOOGLE_CLOUD_PROJECT not set",
            "image_bytes_base64": None,
            "mime_type": None,
            "model_used": None,
        }

    full_prompt = f"{prompt}. {style_hint}" if style_hint else prompt
    last_error: str | None = None

    for model_id in [VERTEX_IMAGE_MODEL_PRIMARY, VERTEX_IMAGE_MODEL_FALLBACK]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(vertexai=True, project=project, location=location)
            response = client.models.generate_images(
                model=model_id,
                prompt=full_prompt,
                config=types.GenerateImagesConfig(
                    aspect_ratio=aspect_ratio,
                    number_of_images=min(max(1, number_of_images), 4),
                ),
            )
            images = getattr(response, "generated_images", None) or []
            if not images:
                raise ValueError("No images in response")

            first = images[0]
            image_obj = getattr(first, "image", first)
            raw_bytes = getattr(image_obj, "image_bytes", None)
            if not raw_bytes and hasattr(image_obj, "_image_bytes"):
                raw_bytes = image_obj._image_bytes
            if not raw_bytes:
                raise ValueError("Image has no bytes")

            mime_type = getattr(first, "mime_type", None) or "image/png"
            return {
                "success": True,
                "image_bytes_base64": base64.b64encode(raw_bytes).decode("utf-8"),
                "mime_type": mime_type,
                "model_used": model_id,
                "count": len(images),
            }
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Vertex image model %s failed: %s", model_id, exc)

    return {
        "success": False,
        "error": last_error or "Image generation failed with configured Vertex models",
        "image_bytes_base64": None,
        "mime_type": None,
        "model_used": None,
    }
