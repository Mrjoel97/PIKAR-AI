"""Skill embedding cache for semantic search.

Pre-computes text embeddings for all skills at startup and caches them
in-memory for fast cosine-similarity lookups.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# In-memory embedding cache: skill_name -> embedding vector
_embedding_cache: dict[str, list[float]] = {}


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
