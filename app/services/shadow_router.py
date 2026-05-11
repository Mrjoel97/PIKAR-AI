# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shadow-traffic router helpers for W3 Section B (B-Alpha-Plus).

This module provides the building blocks for shadowing a primary agent
variant against a candidate variant and persisting their divergence into
``public.agent_shadow_diffs`` for offline review.

The surface is intentionally functional (not a class) — each helper is
independently composable from the FastAPI run_sse hook that wires shadow
traffic. See ``project_agent_operating_model_w1.md`` (memory) for the
design decisions resolved before implementation.

Key contracts:
    * ``compute_divergence`` is a pure function over normalized inputs;
      it does not touch I/O.
    * ``should_shadow`` is a cheap, defensive sampler; non-int inputs do
      not crash callers.
    * ``write_shadow_diff`` is fire-and-forget from the caller's view —
      it swallows every exception and logs a warning. It MUST NEVER raise.
    * ``fire_and_forget_diff_write`` schedules the write via
      ``asyncio.create_task`` so the caller can keep going.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ShadowOutput:
    """Captured final output of a single agent variant for a turn.

    Attributes:
        text: User-facing rendered text.
        tool_calls: List of ``{"tool_id": str, "args": dict}`` records.
        artifacts: List of ``{"kind": str, "content_id": str}`` records.
            Additional fields are tolerated and ignored by the divergence
            computation.
        latency_ms: Wall-clock duration from request start to last event.
    """

    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)
    latency_ms: int | None = None


@dataclass
class Divergence:
    """Comparison result between a primary and candidate :class:`ShadowOutput`.

    Attributes:
        score: Overall divergence in ``[0.0, 1.0]``; the max of the three
            dimension scores. ``0.0`` means identical, ``1.0`` means fully
            divergent.
        kind: One of ``"identical"``, ``"text"``, ``"tool_calls"``,
            ``"artifacts"``, or ``"multiple"``.
        text_score: Jaccard distance over normalized text tokens.
        tool_calls_score: Jaccard distance over tool-call signatures.
        artifacts_score: Jaccard distance over ``(kind, content_id)`` tuples.
    """

    score: float
    kind: str
    text_score: float
    tool_calls_score: float
    artifacts_score: float


# ---------------------------------------------------------------------------
# Divergence
# ---------------------------------------------------------------------------

# A dimension counts as "agreed" if its score is below this threshold.
# Float noise from set arithmetic stays nowhere near 0.05, but if we
# upgrade to embedding-based similarity later the threshold becomes
# load-bearing.
_AGREEMENT_THRESHOLD = 0.05

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, drop tokens of length < 2."""
    if not text:
        return set()
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) >= 2}


def _jaccard_distance(a: set[Any], b: set[Any]) -> float:
    """Return Jaccard distance ``1 - intersection/union``. Empty sets -> 0.0."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return 1.0 - (len(a & b) / len(union))


def _tool_call_signatures(calls: list[dict]) -> set[tuple[str, str]]:
    """Project tool calls onto stable ``(tool_id, sorted-json-args)`` keys."""
    signatures: set[tuple[str, str]] = set()
    for call in calls or []:
        tool_id = str(call.get("tool_id", ""))
        args = call.get("args", {}) or {}
        try:
            args_key = json.dumps(args, sort_keys=True, default=str)
        except (TypeError, ValueError):
            # Last-ditch fallback for un-serializable arg payloads; we
            # would rather record *something* than crash divergence.
            args_key = repr(args)
        signatures.add((tool_id, args_key))
    return signatures


def _artifact_signatures(artifacts: list[dict]) -> set[tuple[str, str]]:
    """Project artifacts onto stable ``(kind, content_id)`` keys."""
    signatures: set[tuple[str, str]] = set()
    for art in artifacts or []:
        kind = str(art.get("kind", ""))
        content_id = str(art.get("content_id", art.get("id", "")))
        signatures.add((kind, content_id))
    return signatures


def _classify_kind(
    text_score: float,
    tool_calls_score: float,
    artifacts_score: float,
) -> str:
    """Map per-dimension scores to the discriminated ``kind`` label."""
    disagreements: list[str] = []
    if text_score >= _AGREEMENT_THRESHOLD:
        disagreements.append("text")
    if tool_calls_score >= _AGREEMENT_THRESHOLD:
        disagreements.append("tool_calls")
    if artifacts_score >= _AGREEMENT_THRESHOLD:
        disagreements.append("artifacts")

    if not disagreements:
        return "identical"
    if len(disagreements) == 1:
        return disagreements[0]
    return "multiple"


def compute_divergence(primary: ShadowOutput, candidate: ShadowOutput) -> Divergence:
    """Compute a :class:`Divergence` between two :class:`ShadowOutput` values.

    Uses simple set-based Jaccard distance across three dimensions
    (text tokens, tool-call signatures, artifact identifiers). The
    overall score is the max of the three dimension scores; ``kind``
    summarizes which dimension(s) disagreed.

    Args:
        primary: The primary variant's output.
        candidate: The candidate variant's output.

    Returns:
        A :class:`Divergence` instance.
    """
    text_score = _jaccard_distance(_tokenize(primary.text), _tokenize(candidate.text))
    tool_calls_score = _jaccard_distance(
        _tool_call_signatures(primary.tool_calls),
        _tool_call_signatures(candidate.tool_calls),
    )
    artifacts_score = _jaccard_distance(
        _artifact_signatures(primary.artifacts),
        _artifact_signatures(candidate.artifacts),
    )

    overall = max(text_score, tool_calls_score, artifacts_score)
    kind = _classify_kind(text_score, tool_calls_score, artifacts_score)

    return Divergence(
        score=overall,
        kind=kind,
        text_score=text_score,
        tool_calls_score=tool_calls_score,
        artifacts_score=artifacts_score,
    )


# ---------------------------------------------------------------------------
# Traffic sampling
# ---------------------------------------------------------------------------


def should_shadow(percent: int) -> bool:
    """Return True for ``random.randint(0, 99) < percent``.

    Defensive against bad input — non-int inputs return ``False`` and
    out-of-range percents are clamped to ``[0, 100]``.

    Args:
        percent: Desired shadow rate in ``[0, 100]``.

    Returns:
        Whether this call should shadow the request.
    """
    if not isinstance(percent, int) or isinstance(percent, bool):
        # bool is a subclass of int; we explicitly reject it because
        # ``True``/``False`` would otherwise be treated as 1/0 and quietly
        # work, masking caller bugs.
        if isinstance(percent, bool):
            # Allow bool through as int after all? No — caller should pass
            # int. Reject to match spec.
            return False
        return False

    clamped = max(0, min(100, percent))
    if clamped <= 0:
        return False
    if clamped >= 100:
        return True
    return random.randint(0, 99) < clamped


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _get_supabase() -> Any:
    """Return the async Supabase client (or a coroutine producing one).

    Tests monkeypatch this to a sync ``lambda`` returning a ``MagicMock``;
    production hits ``get_async_client()`` which is itself a coroutine.
    Both shapes are handled by :func:`_resolve_supabase`.
    """
    from app.services.supabase_client import get_async_client

    return get_async_client()


async def _resolve_supabase() -> Any:
    """Resolve ``_get_supabase()`` whether sync- or coroutine-returning."""
    candidate = _get_supabase()
    if inspect.iscoroutine(candidate):
        return await candidate
    return candidate


def _build_record(
    *,
    agent_id: str,
    primary_variant: str,
    candidate_variant: str,
    primary: ShadowOutput,
    candidate: ShadowOutput,
    divergence: Divergence,
    user_id: UUID | None,
    request_id: UUID | None,
) -> dict[str, Any]:
    """Assemble the insertable row for ``agent_shadow_diffs``."""
    record: dict[str, Any] = {
        "agent_id": agent_id,
        "primary_variant": primary_variant,
        "candidate_variant": candidate_variant,
        "primary_text": primary.text,
        "candidate_text": candidate.text,
        "primary_tool_calls": list(primary.tool_calls or []),
        "candidate_tool_calls": list(candidate.tool_calls or []),
        "primary_artifacts": list(primary.artifacts or []),
        "candidate_artifacts": list(candidate.artifacts or []),
        "divergence_score": float(divergence.score),
        "divergence_kind": divergence.kind,
        "primary_latency_ms": primary.latency_ms,
        "candidate_latency_ms": candidate.latency_ms,
    }
    if user_id is not None:
        record["user_id"] = str(user_id)
    if request_id is not None:
        record["request_id"] = str(request_id)
    return record


async def write_shadow_diff(
    *,
    agent_id: str,
    primary_variant: str,
    candidate_variant: str,
    primary: ShadowOutput,
    candidate: ShadowOutput,
    divergence: Divergence,
    user_id: UUID | None = None,
    request_id: UUID | None = None,
) -> None:
    """Insert one row into ``public.agent_shadow_diffs``.

    Swallows every exception (network, schema, serialization) and logs a
    warning. The caller MUST be able to treat this as fire-and-forget.

    Args:
        agent_id: TEXT id of the shadowed agent (e.g. ``"executive"``).
        primary_variant: Name of the primary build path (e.g. ``"legacy"``).
        candidate_variant: Name of the candidate build path
            (e.g. ``"manifest"``).
        primary: The primary variant's :class:`ShadowOutput`.
        candidate: The candidate variant's :class:`ShadowOutput`.
        divergence: Pre-computed :class:`Divergence` between the two.
        user_id: Optional user UUID for ``auth.users(id)`` FK.
        request_id: Optional correlation UUID for the original turn.
    """
    try:
        client = await _resolve_supabase()
        record = _build_record(
            agent_id=agent_id,
            primary_variant=primary_variant,
            candidate_variant=candidate_variant,
            primary=primary,
            candidate=candidate,
            divergence=divergence,
            user_id=user_id,
            request_id=request_id,
        )
        await client.table("agent_shadow_diffs").insert(record).execute()
    except Exception as exc:
        logger.warning("[shadow_router] write_shadow_diff failed: %s", exc)


def fire_and_forget_diff_write(
    *,
    agent_id: str,
    primary_variant: str,
    candidate_variant: str,
    primary: ShadowOutput,
    candidate: ShadowOutput,
    divergence: Divergence,
    user_id: UUID | None = None,
    request_id: UUID | None = None,
) -> asyncio.Task[None]:
    """Schedule :func:`write_shadow_diff` on the current event loop.

    Returns the resulting :class:`asyncio.Task` so callers can hold a
    reference (asyncio garbage-collects orphan tasks) or cancel during
    shutdown. The task itself never raises because
    :func:`write_shadow_diff` swallows exceptions internally.

    Args:
        agent_id: See :func:`write_shadow_diff`.
        primary_variant: See :func:`write_shadow_diff`.
        candidate_variant: See :func:`write_shadow_diff`.
        primary: See :func:`write_shadow_diff`.
        candidate: See :func:`write_shadow_diff`.
        divergence: See :func:`write_shadow_diff`.
        user_id: See :func:`write_shadow_diff`.
        request_id: See :func:`write_shadow_diff`.

    Returns:
        The created :class:`asyncio.Task`.
    """
    return asyncio.create_task(
        write_shadow_diff(
            agent_id=agent_id,
            primary_variant=primary_variant,
            candidate_variant=candidate_variant,
            primary=primary,
            candidate=candidate,
            divergence=divergence,
            user_id=user_id,
            request_id=request_id,
        )
    )
