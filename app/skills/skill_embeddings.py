# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Skill embedding cache for semantic search.

Pre-computes text embeddings for all skills at startup and caches them
in-memory for fast cosine-similarity lookups.
"""

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# In-memory embedding cache: skill_name -> embedding vector
_embedding_cache: dict[str, list[float]] = {}


def _parse_bool_env(value: str | None) -> bool | None:
    """Parse a boolean environment variable, if present."""
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def startup_warmup_enabled() -> bool:
    """Return whether eager skill-embedding warmup should run in this process."""
    explicit = _parse_bool_env(os.getenv("SKILL_EMBEDDING_WARMUP_ENABLED"))
    if explicit is not None:
        return explicit

    # Default to disabled on Cloud Run to avoid replica startup storms.
    return not bool((os.getenv("K_SERVICE") or "").strip())


def warmup_skill_embeddings(skills: list[Any]) -> int:
    """Pre-compute embeddings for all skills at startup.

    Args:
        skills: List of Skill objects with name and description.

    Returns:
        Number of skills successfully embedded.
    """
    from app.rag.embedding_service import generate_embeddings_batch

    if not skills:
        return 0

    texts = [f"{s.name}: {s.description}" for s in skills]
    try:
        embeddings = generate_embeddings_batch(texts)
    except Exception as e:
        logger.warning("Skill embedding warmup failed: %s", e)
        return 0

    count = 0
    for skill, emb in zip(skills, embeddings):
        # Only cache non-zero embeddings
        if emb and any(v != 0.0 for v in emb):
            _embedding_cache[skill.name] = emb
            count += 1
    logger.info("[skill_embeddings] Warmed %d/%d skill embeddings", count, len(skills))
    return count


def get_skill_embedding(skill_name: str) -> list[float] | None:
    """Get cached embedding for a skill."""
    return _embedding_cache.get(skill_name)


def add_skill_embedding(skill_name: str, description: str) -> bool:
    """Add a single skill embedding to the cache (e.g. for newly registered skills).

    Args:
        skill_name: Name of the skill.
        description: The description text to embed.

    Returns:
        True if successfully cached.
    """
    from app.rag.embedding_service import generate_embedding

    try:
        emb = generate_embedding(f"{skill_name}: {description}")
        if emb and any(v != 0.0 for v in emb):
            _embedding_cache[skill_name] = emb
            return True
    except Exception as e:
        logger.warning("Failed to embed skill '%s': %s", skill_name, e)
    return False


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors without numpy dependency."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def is_warmed() -> bool:
    """Check if embeddings have been warmed up."""
    return len(_embedding_cache) > 0


# ---------------------------------------------------------------------------
# Async wrappers & search
# ---------------------------------------------------------------------------


async def build_index() -> int:
    """Async build of the in-memory embedding index at startup.

    Fetches all registered skills from the SkillsRegistry, then offloads
    the synchronous ``warmup_skill_embeddings`` call to a thread so the
    event loop is never blocked.

    Returns:
        Number of skills successfully embedded.
    """
    from app.skills.registry import skills_registry

    skills = skills_registry.list_all()
    if not skills:
        logger.info("[skill_embeddings] No skills registered — skipping build_index")
        return 0

    count = await asyncio.to_thread(warmup_skill_embeddings, skills)
    logger.info("[skill_embeddings] build_index complete — %d embeddings cached", count)
    return count


async def add_skill_embedding_async(skill_name: str, description: str) -> bool:
    """Async wrapper around :func:`add_skill_embedding`.

    Offloads the synchronous embedding generation to a thread.

    Args:
        skill_name: Name of the skill.
        description: The description text to embed.

    Returns:
        True if successfully cached.
    """
    return await asyncio.to_thread(add_skill_embedding, skill_name, description)


def search_similar(
    query_text: str, limit: int = 5
) -> list[tuple[str, float]]:
    """Search the embedding cache for skills most similar to *query_text*.

    This is a **synchronous** helper.  Callers on the async path should use
    :func:`search_similar_async` which wraps this in ``asyncio.to_thread``.

    Args:
        query_text: Natural-language query to embed and compare.
        limit: Maximum number of results to return.

    Returns:
        List of ``(skill_name, cosine_score)`` tuples sorted descending by
        similarity.  Returns ``[]`` when the cache is cold or the query
        embedding is all zeros.
    """
    if not _embedding_cache:
        return []

    from app.rag.embedding_service import generate_embedding

    query_emb = generate_embedding(query_text)
    if not query_emb or all(v == 0.0 for v in query_emb):
        return []

    scored: list[tuple[str, float]] = []
    for skill_name, cached_emb in _embedding_cache.items():
        score = cosine_similarity(query_emb, cached_emb)
        scored.append((skill_name, score))

    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:limit]


async def search_similar_async(
    query_text: str, limit: int = 5
) -> list[tuple[str, float]]:
    """Async wrapper around :func:`search_similar`.

    Offloads the synchronous embedding + cosine computation to a thread.
    """
    return await asyncio.to_thread(search_similar, query_text, limit)
