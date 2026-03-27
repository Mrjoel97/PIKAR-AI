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

"""Embedding service for generating vector embeddings using Google GenAI."""

import logging
import os
import time
from pathlib import Path
from typing import Any

try:
    from google import genai
except Exception:  # pragma: no cover - import guard
    genai = None

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = 768
EMBEDDING_TASK_TYPE = os.getenv("EMBEDDING_TASK_TYPE", "RETRIEVAL_DOCUMENT")

_client = None
_client_disabled_reason: str | None = None


def _vertex_enabled() -> bool:
    vertex_flag = (os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    has_project = bool((os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip())
    has_credentials = bool((os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip())
    running_on_cloud = bool((os.getenv("K_SERVICE") or "").strip())
    return has_project and (vertex_flag or has_credentials or running_on_cloud)


def _resolve_vertex_credentials() -> None:
    credentials_path = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if credentials_path and not os.path.isabs(credentials_path):
        project_root = Path(__file__).resolve().parent.parent.parent
        resolved = (
            project_root / credentials_path.replace("\\", "/").lstrip("./")
        ).resolve()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)


def _summarize_exception(error: Exception) -> str:
    return " ".join(str(error).split())[:280]


def _classify_permanent_error(error: Exception) -> str | None:
    message = str(error).upper()
    if "BILLING_DISABLED" in message:
        return "vertex_billing_disabled"
    if "API KEY NOT VALID" in message or "INVALID API KEY" in message:
        return "invalid_api_key"
    if "UNAUTHENTICATED" in message:
        return "authentication_failed"
    if "INSUFFICIENT AUTHENTICATION SCOPES" in message:
        return "insufficient_auth_scopes"
    if "PERMISSION_DENIED" in message:
        return "permission_denied"
    return None


def _disable_embeddings(reason: str, message: str) -> None:
    global _client, _client_disabled_reason
    _client = None
    if _client_disabled_reason == reason:
        return
    _client_disabled_reason = reason
    logger.warning(message)


def _handle_embedding_failure(error: Exception, operation: str) -> None:
    permanent_reason = _classify_permanent_error(error)
    if permanent_reason == "vertex_billing_disabled":
        _disable_embeddings(
            permanent_reason,
            "Vertex AI embeddings are configured, but billing is disabled for the Google Cloud project. Embeddings will fallback to zeros until billing is enabled and the app restarts.",
        )
        return
    if permanent_reason == "invalid_api_key":
        _disable_embeddings(
            permanent_reason,
            "The configured Google AI API key is invalid. Embeddings will fallback to zeros until the key is fixed and the app restarts.",
        )
        return
    if permanent_reason in {
        "authentication_failed",
        "insufficient_auth_scopes",
        "permission_denied",
    }:
        _disable_embeddings(
            permanent_reason,
            f"{operation} disabled due to a Google AI authentication or permission error: {_summarize_exception(error)}. Embeddings will fallback to zeros until the configuration is fixed and the app restarts.",
        )
        return
    logger.warning("%s failed: %s", operation, _summarize_exception(error))


def _create_client():
    if _vertex_enabled():
        project = (os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
        location = (os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1").strip()
        if not project:
            logger.warning(
                "Vertex AI embedding mode requested but GOOGLE_CLOUD_PROJECT is not set. Embeddings will fallback to zeros."
            )
            return None
        _resolve_vertex_credentials()
        logger.info(
            "[embeddings] initializing Vertex AI client for project=%s location=%s",
            project,
            location,
        )
        return genai.Client(vertexai=True, project=project, location=location)

    api_key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        logger.warning(
            "No Google AI embedding credentials configured. Set Vertex AI env vars or GOOGLE_API_KEY. Embeddings will fallback to zeros."
        )
        return None

    logger.info("[embeddings] initializing Gemini Developer API client")
    return genai.Client(api_key=api_key)


def _get_client():
    global _client
    if genai is None:
        logger.warning("google.genai not available. Embeddings will fallback to zeros.")
        return None
    if _client_disabled_reason:
        return None
    if _client is None:
        _client = _create_client()
    return _client


def _extract_values(embedding_obj: Any) -> list[float] | None:
    if embedding_obj is None:
        return None
    if hasattr(embedding_obj, "values"):
        return list(embedding_obj.values)
    if isinstance(embedding_obj, dict) and "values" in embedding_obj:
        return list(embedding_obj["values"])
    return None


def _build_embed_params(contents: Any) -> dict:
    params: dict[str, Any] = {"model": EMBEDDING_MODEL, "contents": contents}
    config: dict[str, Any] = {}
    if EMBEDDING_TASK_TYPE:
        config["taskType"] = EMBEDDING_TASK_TYPE
    if config:
        params["config"] = config
    return params


def get_embedding_health() -> dict:
    client = _get_client()
    if client is None:
        return {
            "status": "unhealthy",
            "reason": _client_disabled_reason
            or "missing_google_genai_or_embedding_credentials",
        }
    start = time.perf_counter()
    try:
        response = client.models.embed_content(**_build_embed_params("health check"))
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    except Exception as e:
        _handle_embedding_failure(e, "Embedding health check")
        return {
            "status": "unhealthy",
            "reason": _client_disabled_reason
            or f"embed_failed: {_summarize_exception(e)}",
        }
    embedding = getattr(response, "embedding", None)
    values = _extract_values(embedding)
    if values and len(values) == EMBEDDING_DIMENSION:
        return {
            "status": "healthy",
            "model": EMBEDDING_MODEL,
            "dimension": len(values),
            "latency_ms": elapsed_ms,
        }
    return {"status": "unhealthy", "reason": "unexpected_embedding_shape"}


def generate_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMENSION
    client = _get_client()
    if client is None:
        return [0.0] * EMBEDDING_DIMENSION
    start = time.perf_counter()
    try:
        response = client.models.embed_content(**_build_embed_params(text))
    except Exception as e:
        _handle_embedding_failure(e, "Embedding request")
        return [0.0] * EMBEDDING_DIMENSION
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    embedding = getattr(response, "embedding", None)
    if embedding is not None:
        values = _extract_values(embedding)
        if values:
            logger.info(
                f"[embeddings] single latency_ms={elapsed_ms} model={EMBEDDING_MODEL} task_type={EMBEDDING_TASK_TYPE}"
            )
            return values
    embeddings = getattr(response, "embeddings", None) or []
    if embeddings:
        values = _extract_values(embeddings[0])
        if values:
            logger.info(
                f"[embeddings] single latency_ms={elapsed_ms} model={EMBEDDING_MODEL} task_type={EMBEDDING_TASK_TYPE}"
            )
            return values
    return [0.0] * EMBEDDING_DIMENSION


def generate_embeddings_batch(
    texts: list[str], batch_size: int = 5
) -> list[list[float]]:
    if not texts:
        return []
    client = _get_client()
    if client is None:
        return [[0.0] * EMBEDDING_DIMENSION for _ in texts]
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = [t if t and t.strip() else " " for t in texts[i : i + batch_size]]
        start = time.perf_counter()
        try:
            response = client.models.embed_content(**_build_embed_params(batch))
        except Exception as e:
            _handle_embedding_failure(e, "Embedding batch")
            all_embeddings.extend([[0.0] * EMBEDDING_DIMENSION for _ in batch])
            if _client_disabled_reason:
                remaining = len(texts) - len(all_embeddings)
                if remaining > 0:
                    all_embeddings.extend(
                        [[0.0] * EMBEDDING_DIMENSION for _ in range(remaining)]
                    )
                return all_embeddings
            continue
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        embeddings = getattr(response, "embeddings", None) or []
        for item in embeddings:
            values = _extract_values(item)
            all_embeddings.append(values if values else [0.0] * EMBEDDING_DIMENSION)
        while len(all_embeddings) < i + len(batch):
            all_embeddings.append([0.0] * EMBEDDING_DIMENSION)
        logger.info(
            f"[embeddings] batch latency_ms={elapsed_ms} size={len(batch)} model={EMBEDDING_MODEL} task_type={EMBEDDING_TASK_TYPE}"
        )
    return all_embeddings
