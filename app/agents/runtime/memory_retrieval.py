# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Layer-3 memory retrieval for the agent runtime.

Runs alongside skill injection inside ``before_agent_callback``. Returns
a markdown ``## Prior work`` block prepended to the agent prompt so the
agent starts the turn with summaries of its own prior reports on
similar goals.

The retrieval pipeline is:

  1. Extract a query string from the incoming :class:`TaskContract`
     (``.goal``) or :class:`DirectRequest` (``.message``). Empty query
     short-circuits with an empty string.
  2. Call :func:`app.services.knowledge_service.search_system_knowledge`
     with the agent scope (``agent.agent_id.value``) and an over-fetch
     of ``2 * top_k`` so we have enough headroom for the two re-ranking
     passes below.
  3. Filter rows where ``metadata.kind != "agent_report"`` (the vault
     may surface other doc kinds — admin training, transcripts — and
     those are not the prior-work we want).
  4. Re-rank in two passes: first a small recency boost (recent reports
     beat slightly more-similar older ones, but a large similarity gap
     still wins), then same-initiative rows are bubbled to the top
     (initiative continuity always wins, with recency order preserved
     inside each partition).
  5. Truncate to ``top_k`` and render as markdown.

Failures inside this module never break the turn — exceptions are
logged at DEBUG and the function returns ``""`` (i.e. no prior-work
section).

Bound to Tasks 25, 26, 40 of the agent operating model W1+W2 plan.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.services.knowledge_service import search_system_knowledge

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - import only for type-checkers
    from app.agents.base_agent import PikarBaseAgent
    from app.agents.runtime.types import DirectRequest, TaskContract


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_SNIPPET_CHARS = 400
"""Max characters per result snippet rendered into the prior-work block."""

_DEFAULT_TOP_K = 4
"""Fallback top-K when an agent has no ``memory.retrieval_top_k`` configured."""

_OVERFETCH_MULTIPLIER = 2
"""Fetch this many extra rows from the vault so re-ranking has headroom."""

_RECENCY_WINDOW_DAYS = 30
"""Window over which the recency boost decays linearly to zero."""

_RECENCY_MAX_BOOST = 0.05
"""Maximum similarity bump awarded to a brand-new (today) report.

Tuned to be smaller than the natural gap between a strong and a weak
match so recency only flips order between rows that are otherwise
close — never overrides a clearly more-relevant older report.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, limit: int = _MAX_SNIPPET_CHARS) -> str:
    """Trim ``text`` to ``limit`` chars, appending an ellipsis if cut."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _extract_query_and_initiative(
    request: Any,
) -> tuple[str, str | None]:
    """Return ``(query, initiative_id)`` for either a TaskContract or DirectRequest.

    Uses duck-typing rather than ``isinstance`` so the runtime is robust to
    future request variants and so tests can pass plain MagicMocks.
    """
    goal = getattr(request, "goal", None)
    message = getattr(request, "message", None)
    initiative_id = getattr(request, "initiative_id", None)
    query = (goal or message or "").strip()
    return query, initiative_id


def _prioritize_same_initiative(
    rows: list[dict[str, Any]],
    initiative_id: Any,
) -> list[dict[str, Any]]:
    """Stable-partition ``rows`` so same-initiative entries come first.

    Comparison is on the *string form* of ``initiative_id`` so UUIDs and
    plain strings hash the same way. The relative order inside each
    partition is preserved, so callers that already sorted by similarity
    keep that order within each group.
    """
    if not initiative_id:
        return list(rows or [])
    target = str(initiative_id)
    same: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for r in rows or []:
        meta = r.get("metadata") or {}
        row_init = meta.get("initiative_id")
        if row_init is not None and str(row_init) == target:
            same.append(r)
        else:
            other.append(r)
    return same + other


def _parse_iso(ts: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp from the vault metadata.

    Accepts both ``...Z`` and ``...+00:00`` forms. Returns ``None`` for
    anything we cannot parse — the caller treats that as "no recency
    signal" instead of raising.
    """
    if not ts or not isinstance(ts, str):
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _apply_recency_boost(
    rows: list[dict[str, Any]],
    *,
    boost_window_days: int = _RECENCY_WINDOW_DAYS,
    max_boost: float = _RECENCY_MAX_BOOST,
) -> list[dict[str, Any]]:
    """Re-rank rows by ``similarity + recency_boost`` and return the new order.

    The boost decays linearly from ``max_boost`` at "now" to ``0`` at
    ``boost_window_days`` ago, and stays at zero beyond the window.
    Rows missing a parseable ``metadata.created_at`` receive no boost.

    The sort is stable on the original input index so two rows with
    identical scores keep their incoming order — i.e. the caller's
    similarity-then-initiative ordering is preserved on ties.
    """
    now = datetime.now(tz=timezone.utc)
    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, r in enumerate(rows or []):
        try:
            sim = float(r.get("similarity", 0.0) or 0.0)
        except (TypeError, ValueError):
            sim = 0.0
        meta = r.get("metadata") or {}
        ts = _parse_iso(meta.get("created_at"))
        boost = 0.0
        if ts is not None:
            age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
            if age_days <= boost_window_days:
                boost = max_boost * (1.0 - age_days / boost_window_days)
        scored.append((sim + boost, idx, r))

    # Sort: higher score first; on tie, lower original index first (stable).
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]


def _render_prior_work(results: list[dict[str, Any]]) -> str:
    """Render retrieved reports as a markdown ``## Prior work`` block.

    Empty/None inputs return ``""`` so callers can safely concatenate the
    result without conditional checks.
    """
    if not results:
        return ""
    lines: list[str] = [
        "## Prior work (your past reports on similar goals)",
        "",
    ]
    for r in results:
        meta = r.get("metadata") or {}
        goal = meta.get("goal") or "(no goal recorded)"
        try:
            sim = float(r.get("similarity", 0.0) or 0.0)
        except (TypeError, ValueError):
            sim = 0.0
        initiative = meta.get("initiative_id") or "—"
        snippet = _truncate(r.get("content", ""))
        lines.append(f"- **{goal}** (similarity {sim:.2f}, initiative `{initiative}`)")
        if snippet:
            lines.append(f"  > {snippet}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def retrieve_relevant_history(
    request: TaskContract | DirectRequest,
    agent: PikarBaseAgent,
    *,
    top_k: int | None = None,
) -> str:
    """Return a markdown ``Prior work`` block, or ``""`` if nothing relevant.

    The function never raises: vault failures, empty results, missing
    metadata all collapse to an empty string. Callers can concatenate
    the result into the system prompt unconditionally.

    Args:
        request: Either a :class:`TaskContract` (initiative mode) or
            a :class:`DirectRequest` (direct mode). The query is taken
            from ``.goal`` first, falling back to ``.message``.
        agent: The :class:`PikarBaseAgent` running the turn. Used for
            ``agent.agent_id.value`` (vault scope) and
            ``agent.ops.memory.retrieval_top_k`` (truncation target).
        top_k: Optional override for the agent's configured top-K. Useful
            for one-off retrievals (compaction, audit reflection, etc.).

    Returns:
        Markdown string starting with ``## Prior work``, or ``""`` when
        there is no query, no matches, or the vault call failed.
    """
    # Resolve effective top-K (caller override > agent config > default).
    if top_k is not None:
        eff_top_k = int(top_k)
    else:
        memory_cfg = getattr(getattr(agent, "ops", None), "memory", None)
        configured = getattr(memory_cfg, "retrieval_top_k", _DEFAULT_TOP_K)
        try:
            eff_top_k = int(configured) if configured is not None else _DEFAULT_TOP_K
        except (TypeError, ValueError):
            eff_top_k = _DEFAULT_TOP_K

    query, initiative_id = _extract_query_and_initiative(request)
    if not query:
        return ""

    # Always over-fetch so both the initiative-priority pass and the
    # recency boost have a candidate pool to re-order before we
    # truncate to eff_top_k.
    fetch_k = eff_top_k * _OVERFETCH_MULTIPLIER

    # Resolve the agent scope string (AgentID is a str-Enum, so .value).
    agent_scope: str | None = None
    raw_id = getattr(agent, "agent_id", None)
    if raw_id is not None:
        agent_scope = getattr(raw_id, "value", None) or str(raw_id)

    try:
        rows = await search_system_knowledge(
            query=query,
            agent_name=agent_scope,
            top_k=fetch_k,
        )
    except Exception as exc:
        logger.debug("[memory_retrieval] vault search failed: %s", exc)
        return ""

    # Filter to agent_report kind. If a row has no `kind`, default to
    # "agent_report" so older vault rows (pre-classification) are not
    # silently dropped.
    rows = [
        r
        for r in (rows or [])
        if (r.get("metadata") or {}).get("kind", "agent_report") == "agent_report"
    ]
    if not rows:
        return ""

    # Re-rank in two passes:
    #   1. Recency boost first — surfaces fresh reports over slightly more
    #      similar stale ones, but keeps a wide similarity gap winning.
    #   2. Initiative continuity second — same-initiative rows are bubbled
    #      to the top *after* the recency pass, so they always lead the
    #      block even if their raw similarity is lower. Inside each
    #      partition, the recency ordering is preserved.
    rows = _apply_recency_boost(rows)
    rows = _prioritize_same_initiative(rows, initiative_id)

    return _render_prior_work(rows[:eff_top_k])


__all__ = [
    "_apply_recency_boost",
    "_prioritize_same_initiative",
    "_render_prior_work",
    "retrieve_relevant_history",
]
