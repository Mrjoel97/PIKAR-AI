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

"""Vertex AI image generation service (Imagen 4 + Gemini image fallback).

Does not require Canva MCP. Users can generate images directly via the agent.
"""

import base64
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

VERTEX_IMAGE_MODEL_PRIMARY = os.getenv("VERTEX_IMAGE_MODEL_PRIMARY", "imagen-4.0-generate-001")
VERTEX_IMAGE_MODEL_FALLBACK = os.getenv("VERTEX_IMAGE_MODEL_FALLBACK", "imagen-3.0-generate-002")


def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    style_hint: str | None = None,
    number_of_images: int = 1,
) -> dict[str, Any]:
    """Generate image(s) using Vertex AI (Imagen 4 primary, fallback to Imagen 3).

    No Canva MCP required. Uses same GCP/Vertex credentials as the rest of the app.

    Args:
        prompt: Text description for image generation.
        aspect_ratio: One of "1:1", "3:4", "4:3", "16:9", "9:16".
        style_hint: Optional style hint (e.g. "vibrant", "minimal") appended to prompt.
        number_of_images: 1–4.

    Returns:
        Dict with:
          - success: bool
          - image_bytes_base64: str (first image) or list of base64 strings
          - mime_type: str (e.g. image/png)
          - model_used: str (primary or fallback)
          - error: str (if success is False)
    """
    full_prompt = f"{prompt}. {style_hint}" if style_hint else prompt
    models_to_try = [VERTEX_IMAGE_MODEL_PRIMARY, VERTEX_IMAGE_MODEL_FALLBACK]

    for model_id in models_to_try:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            config = types.GenerateImagesConfig(
                aspect_ratio=aspect_ratio,
                number_of_images=min(max(1, number_of_images), 4),
            )
            response = client.models.generate_images(
                model=model_id,
                prompt=full_prompt,
                config=config,
            )
            if not response or not getattr(response, "generated_images", None):
                raise ValueError("No images in response")

            images = response.generated_images
            first = images[0]
            img_obj = getattr(first, "image", first)
            raw_bytes = getattr(img_obj, "image_bytes", None)
            if not raw_bytes and hasattr(img_obj, "_image_bytes"):
                raw_bytes = img_obj._image_bytes
            if not raw_bytes:
                raise ValueError("Image has no bytes")

            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            mime = getattr(first, "mime_type", None) or "image/png"

            return {
                "success": True,
                "image_bytes_base64": b64,
                "mime_type": mime,
                "model_used": model_id,
                "count": len(images),
            }
        except Exception as e:
            logger.warning(f"Vertex image model {model_id} failed: {e}")
            continue

    return {
        "success": False,
        "error": "Image generation failed with primary and fallback models",
        "image_bytes_base64": None,
        "mime_type": None,
        "model_used": None,
    }
