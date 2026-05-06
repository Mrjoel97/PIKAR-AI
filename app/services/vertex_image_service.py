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
``response_modalities=["IMAGE"]``. The deprecated Imagen ``generate_images``
endpoint is no longer called.

Concurrency and retry
---------------------
Image generation has tight per-minute quotas on Vertex AI (much tighter than
text embeddings). To avoid burst 429s when callers fan out — e.g.,
``media.generate_images`` running ``asyncio.gather`` over many prompts, or
``director_service`` generating per-scene assets — this module:

- Gates all calls through a process-wide ``threading.Semaphore`` sized by
  ``VERTEX_IMAGE_CONCURRENCY`` (default 2). Concurrent callers wait rather
  than firing in parallel and tripping quota together. Threading-level
  semaphore is correct because the function is sync and runs in worker
  threads via ``asyncio.to_thread`` from async callers.
- Retries retryable errors (RESOURCE_EXHAUSTED / 429, UNAVAILABLE / 503,
  DEADLINE_EXCEEDED / 504) with exponential backoff + jitter, governed by
  ``VERTEX_IMAGE_MAX_RETRIES`` and ``VERTEX_IMAGE_BASE_BACKOFF_S``.
- Honors a server-supplied ``retry_delay`` from the SDK exception when
  present, falling back to exponential backoff otherwise.
- Fails fast on permanent errors (PERMISSION_DENIED, INVALID_ARGUMENT,
  NOT_FOUND, etc.) so callers see real failures immediately instead of
  burning retry budget on something that won't recover.
"""

import base64
import logging
import os
import random
import re
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

VERTEX_IMAGE_MODEL_PRIMARY = os.getenv(
    "VERTEX_IMAGE_MODEL_PRIMARY", "gemini-2.5-flash-image"
)
# Optional alternate model. Only honored when different from PRIMARY — the
# previous default had both pointing at ``gemini-2.5-flash-image``, making
# the fallback loop a no-op that doubled quota burn on every failure.
VERTEX_IMAGE_MODEL_FALLBACK = os.getenv(
    "VERTEX_IMAGE_MODEL_FALLBACK", "gemini-2.5-flash-image"
)

VERTEX_IMAGE_MAX_RETRIES = max(0, int(os.getenv("VERTEX_IMAGE_MAX_RETRIES", "3")))
VERTEX_IMAGE_BASE_BACKOFF_S = max(
    0.1, float(os.getenv("VERTEX_IMAGE_BASE_BACKOFF_S", "2.0"))
)
VERTEX_IMAGE_MAX_BACKOFF_S = max(
    1.0, float(os.getenv("VERTEX_IMAGE_MAX_BACKOFF_S", "30.0"))
)
VERTEX_IMAGE_CONCURRENCY = max(1, int(os.getenv("VERTEX_IMAGE_CONCURRENCY", "2")))

_concurrency_semaphore = threading.Semaphore(VERTEX_IMAGE_CONCURRENCY)

# Tokens that mark transient errors worth retrying. Surrounding spaces guard
# against false matches on substrings inside other words/numbers.
_RETRYABLE_TOKENS = (
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
    " 429 ",
    " 503 ",
    " 504 ",
)
_PERMANENT_TOKENS = (
    "PERMISSION_DENIED",
    "UNAUTHENTICATED",
    "INVALID_ARGUMENT",
    "NOT_FOUND",
    "FAILED_PRECONDITION",
    " 400 ",
    " 401 ",
    " 403 ",
    " 404 ",
)

_RETRY_AFTER_RE = re.compile(
    r"retry[^a-z0-9]{0,3}after[^0-9]{0,8}([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE
)


def _classify(exc: Exception) -> str:
    """Classify an exception as ``"retryable"``, ``"permanent"``, or ``"unknown"``."""
    msg = f" {str(exc).upper()} "
    for tok in _PERMANENT_TOKENS:
        if tok in msg:
            return "permanent"
    for tok in _RETRYABLE_TOKENS:
        if tok in msg:
            return "retryable"
    return "unknown"


def _extract_retry_after_seconds(exc: Exception) -> float | None:
    """Pull a ``retry-after`` hint from the exception if the SDK provided one."""
    delay = getattr(exc, "retry_delay", None)
    if delay is not None:
        try:
            return float(delay)
        except (TypeError, ValueError):
            pass
    match = _RETRY_AFTER_RE.search(str(exc))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _backoff_seconds(attempt: int, exc: Exception | None) -> float:
    """Compute backoff for attempt ``n`` (0-indexed). Honors retry-after if present."""
    server_hint = _extract_retry_after_seconds(exc) if exc is not None else None
    if server_hint is not None and server_hint > 0:
        return min(server_hint + random.uniform(0, 0.5), VERTEX_IMAGE_MAX_BACKOFF_S)
    base = VERTEX_IMAGE_BASE_BACKOFF_S * (2**attempt)
    jitter = random.uniform(0, VERTEX_IMAGE_BASE_BACKOFF_S)
    return min(base + jitter, VERTEX_IMAGE_MAX_BACKOFF_S)


def _models_to_try() -> list[str]:
    """Return ordered model list, deduplicated.

    If ``VERTEX_IMAGE_MODEL_FALLBACK`` equals PRIMARY (the default), only the
    primary is tried — the legacy fallback loop in that case was a no-op that
    doubled quota burn on every failure.
    """
    if (
        VERTEX_IMAGE_MODEL_FALLBACK
        and VERTEX_IMAGE_MODEL_FALLBACK != VERTEX_IMAGE_MODEL_PRIMARY
    ):
        return [VERTEX_IMAGE_MODEL_PRIMARY, VERTEX_IMAGE_MODEL_FALLBACK]
    return [VERTEX_IMAGE_MODEL_PRIMARY]


def _call_vertex(
    *,
    model_id: str,
    project: str,
    location: str,
    prompt: str,
    aspect_ratio: str,
    candidate_count: int,
) -> dict[str, Any]:
    """One Vertex ``generate_content`` call for image(s). Raises on any error.

    Collects image parts across all candidates (Gemini may split a multi-image
    response across candidates) and across all parts within each candidate.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            candidate_count=candidate_count,
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
        ),
    )

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError("No candidates in response")

    image_parts = []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for p in parts:
            if getattr(p, "inline_data", None) is not None:
                image_parts.append(p)

    if not image_parts:
        raise ValueError("No image parts in response")

    base64_list: list[str] = []
    mime_type: str | None = None
    for part in image_parts:
        raw_bytes = part.inline_data.data
        if not raw_bytes:
            continue
        if mime_type is None:
            mime_type = part.inline_data.mime_type or "image/png"
        base64_list.append(base64.b64encode(raw_bytes).decode("utf-8"))

    if not base64_list:
        raise ValueError("Image parts had no bytes")

    return {
        "success": True,
        # Back-compat: single-image callers keep reading the first image.
        "image_bytes_base64": base64_list[0],
        # New: plural form populated when number_of_images > 1.
        "image_bytes_base64_list": base64_list,
        "mime_type": mime_type or "image/png",
        "model_used": model_id,
        "count": len(base64_list),
    }


def generate_image(
    prompt: str,
    *,
    aspect_ratio: str = "1:1",
    style_hint: str | None = None,
    number_of_images: int = 1,
) -> dict[str, Any]:
    """Generate image(s) using Gemini image-capable models on Vertex AI.

    Adds retry-with-backoff on transient errors (429/503/504) and gates
    concurrent callers through a process-wide semaphore so fan-outs don't
    burst the per-minute quota in lockstep.

    Args:
        prompt: Image description.
        aspect_ratio: Aspect ratio passed to ``ImageConfig``.
        style_hint: Optional style modifier appended to the prompt.
        number_of_images: ``candidate_count`` passed to Vertex; the response
            may return up to this many images split across candidates.

    Returns:
        Dict with ``success`` flag, the first image's bytes (base64) under
        ``image_bytes_base64`` for back-compat, and the full list under
        ``image_bytes_base64_list``. Shape matches the legacy contract on
        failure (with an empty list).
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        return {
            "success": False,
            "error": "GOOGLE_CLOUD_PROJECT not set",
            "image_bytes_base64": None,
            "image_bytes_base64_list": [],
            "mime_type": None,
            "model_used": None,
        }

    full_prompt = f"{prompt}. {style_hint}" if style_hint else prompt
    requested = max(1, int(number_of_images or 1))
    last_error: str | None = None
    models = _models_to_try()

    with _concurrency_semaphore:
        for model_id in models:
            for attempt in range(VERTEX_IMAGE_MAX_RETRIES + 1):
                try:
                    return _call_vertex(
                        model_id=model_id,
                        project=project,
                        location=location,
                        prompt=full_prompt,
                        aspect_ratio=aspect_ratio,
                        candidate_count=requested,
                    )
                except Exception as exc:
                    last_error = str(exc)
                    classification = _classify(exc)

                    if classification == "permanent":
                        logger.warning(
                            "Vertex image model %s permanent failure: %s",
                            model_id,
                            exc,
                        )
                        break

                    if attempt >= VERTEX_IMAGE_MAX_RETRIES:
                        logger.warning(
                            "Vertex image model %s exhausted %d attempts: %s",
                            model_id,
                            VERTEX_IMAGE_MAX_RETRIES + 1,
                            exc,
                        )
                        break

                    # Unknown errors get exactly one retry — protect against
                    # transient SDK/parsing glitches without burning the full
                    # budget on a real bug.
                    if classification == "unknown" and attempt >= 1:
                        logger.warning(
                            "Vertex image model %s unknown error after retry: %s",
                            model_id,
                            exc,
                        )
                        break

                    sleep_s = _backoff_seconds(attempt, exc)
                    logger.warning(
                        "Vertex image model %s %s (attempt %d/%d), backing off %.2fs",
                        model_id,
                        classification,
                        attempt + 1,
                        VERTEX_IMAGE_MAX_RETRIES + 1,
                        sleep_s,
                    )
                    time.sleep(sleep_s)

    return {
        "success": False,
        "error": last_error or "Image generation failed",
        "image_bytes_base64": None,
        "image_bytes_base64_list": [],
        "mime_type": None,
        "model_used": None,
    }
