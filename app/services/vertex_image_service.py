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
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Vertex AI image generation service.

Uses Gemini 2.5 Flash Image via ``generate_content`` with
``response_modalities=["IMAGE"]``.  The deprecated Imagen
``generate_images`` endpoint is no longer called.
"""

import base64
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

VERTEX_IMAGE_MODEL_PRIMARY = os.getenv(
    "VERTEX_IMAGE_MODEL_PRIMARY", "gemini-2.5-flash-image"
)
# Fallback defaults to the same GA image-capable model so the retry loop acts
# as a transient-error retry. The previous default ("gemini-2.5-flash-preview-0514")
# was a May 2024 preview that has since been retired on Vertex AI and would
# return 404 on every call. Override via env if a real alternate is configured.
VERTEX_IMAGE_MODEL_FALLBACK = os.getenv(
    "VERTEX_IMAGE_MODEL_FALLBACK", "gemini-2.5-flash-image"
)


def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    style_hint: str | None = None,
    number_of_images: int = 1,
) -> dict[str, Any]:
    """Generate image(s) using Gemini image-capable models on Vertex AI."""
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
            response = client.models.generate_content(
                model=model_id,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    ),
                ),
            )

            # Extract image parts from response candidates
            candidates = getattr(response, "candidates", None) or []
            if not candidates:
                raise ValueError("No candidates in response")

            parts = getattr(candidates[0], "content", None)
            parts = getattr(parts, "parts", None) or []

            image_parts = [
                p for p in parts if getattr(p, "inline_data", None) is not None
            ]
            if not image_parts:
                raise ValueError("No image parts in response")

            first = image_parts[0]
            raw_bytes = first.inline_data.data
            if not raw_bytes:
                raise ValueError("Image part has no bytes")

            mime_type = first.inline_data.mime_type or "image/png"
            return {
                "success": True,
                "image_bytes_base64": base64.b64encode(raw_bytes).decode("utf-8"),
                "mime_type": mime_type,
                "model_used": model_id,
                "count": len(image_parts),
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
