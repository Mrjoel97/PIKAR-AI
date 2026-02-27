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

"""Embedding service for generating vector embeddings using Gemini API.

Uses Google's text-embedding-004 model (768 dimensions) for semantic search.
This avoids Vertex AI / GCP credential requirements for faster demos.
"""

import os
import time
import logging
from typing import Any

try:
    from google import genai
except Exception:  # pragma: no cover - import guard
    genai = None

logger = logging.getLogger(__name__)

# Model configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = 768
EMBEDDING_TASK_TYPE = os.getenv("EMBEDDING_TASK_TYPE", "RETRIEVAL_DOCUMENT")

# Cache the client instance
_client = None


def _get_client():
    """Get or create the Gemini API client instance."""
    global _client
    if genai is None:
        logger.warning("google.genai not available. Embeddings will fallback to zeros.")
        return None
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set. Embeddings will fallback to zeros.")
            return None
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client: {e}")
            _client = None
    return _client


def _extract_values(embedding_obj: Any) -> list[float] | None:
    """Extract vector values from various embedding response shapes."""
    if embedding_obj is None:
        return None
    # google.genai response objects use .values
    if hasattr(embedding_obj, "values"):
        return list(embedding_obj.values)
    # dict fallback
    if isinstance(embedding_obj, dict) and "values" in embedding_obj:
        return list(embedding_obj["values"])
    return None


def _build_embed_params(contents: Any) -> dict:
    """Build parameters for the Gemini embedding call."""
    params: dict = {
        "model": EMBEDDING_MODEL,
        "contents": contents,
    }
    if EMBEDDING_TASK_TYPE:
        params["task_type"] = EMBEDDING_TASK_TYPE
    return params


def get_embedding_health() -> dict:
    """Health check for embedding availability and latency."""
    client = _get_client()
    if client is None:
        return {
            "status": "unhealthy",
            "reason": "missing_google_genai_or_api_key",
        }

    start = time.perf_counter()
    try:
        response = client.models.embed_content(
            **_build_embed_params("health check")
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    except Exception as e:
        return {
            "status": "unhealthy",
            "reason": f"embed_failed: {e}",
        }

    embedding = getattr(response, "embedding", None)
    values = _extract_values(embedding) if embedding is not None else None
    if not values:
        embeddings = getattr(response, "embeddings", None)
        if embeddings and len(embeddings) > 0:
            values = _extract_values(embeddings[0])

    if not values:
        return {
            "status": "degraded",
            "reason": "no_embedding_values_returned",
            "latency_ms": elapsed_ms,
        }

    non_zero_count = sum(1 for v in values if v != 0.0)
    return {
        "status": "healthy" if non_zero_count > 0 else "degraded",
        "latency_ms": elapsed_ms,
        "dimension": len(values),
        "non_zero_count": non_zero_count,
        "task_type": EMBEDDING_TASK_TYPE,
        "model": EMBEDDING_MODEL,
    }


def generate_embedding(text: str) -> list[float]:
    """Generate a vector embedding for the given text.
    
    Args:
        text: The text to generate an embedding for.
        
    Returns:
        A list of floats representing the 768-dimensional embedding vector.
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * EMBEDDING_DIMENSION
    
    client = _get_client()
    if client is None:
        return [0.0] * EMBEDDING_DIMENSION

    start = time.perf_counter()
    try:
        response = client.models.embed_content(
            **_build_embed_params(text)
        )
    except Exception as e:
        logger.warning(f"Embedding request failed: {e}")
        return [0.0] * EMBEDDING_DIMENSION
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    # Response may include a single embedding or list
    embedding = getattr(response, "embedding", None)
    if embedding is not None:
        values = _extract_values(embedding)
        if values:
            logger.info(f"[embeddings] single latency_ms={elapsed_ms} model={EMBEDDING_MODEL} task_type={EMBEDDING_TASK_TYPE}")
            return values

    embeddings = getattr(response, "embeddings", None)
    if embeddings and len(embeddings) > 0:
        values = _extract_values(embeddings[0])
        if values:
            logger.info(f"[embeddings] single latency_ms={elapsed_ms} model={EMBEDDING_MODEL} task_type={EMBEDDING_TASK_TYPE}")
            return values
    
    return [0.0] * EMBEDDING_DIMENSION


def generate_embeddings_batch(texts: list[str], batch_size: int = 5) -> list[list[float]]:
    """Generate embeddings for multiple texts in batches.
    
    Args:
        texts: List of texts to generate embeddings for.
        batch_size: Number of texts to process per API call (max 5 for Vertex AI).
        
    Returns:
        List of embedding vectors, one per input text.
    """
    if not texts:
        return []
    
    client = _get_client()
    if client is None:
        return [[0.0] * EMBEDDING_DIMENSION for _ in texts]
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Handle empty strings in batch
        batch = [t if t and t.strip() else " " for t in batch]
        
        start = time.perf_counter()
        try:
            response = client.models.embed_content(
                **_build_embed_params(batch)
            )
        except Exception as e:
            logger.warning(f"Embedding batch failed: {e}")
            all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION for _ in batch])
            continue
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        embeddings = getattr(response, "embeddings", None)
        if embeddings:
            for emb in embeddings:
                values = _extract_values(emb)
                all_embeddings.append(values or [0.0] * EMBEDDING_DIMENSION)
        else:
            all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION for _ in batch])
        logger.info(
            f"[embeddings] batch latency_ms={elapsed_ms} size={len(batch)} "
            f"model={EMBEDDING_MODEL} task_type={EMBEDDING_TASK_TYPE}"
        )
    
    return all_embeddings
