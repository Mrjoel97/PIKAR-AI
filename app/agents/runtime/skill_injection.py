# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Semantic skill matching + prompt injection for ``before_agent_callback``.

The matcher reuses ``app.skills.skill_embeddings`` (the warmed in-memory
cosine cache backing :meth:`SkillsRegistry.semantic_search`) so no new
vector infrastructure ships here. The output is a markdown block that
:mod:`app.agents.runtime.lifecycle` prepends to the agent's instruction.

Filter chain (applied to ``skills_registry.semantic_search`` candidates):

1. ``score >= effective similarity_floor``;
2. ``agent.agent_id`` is in ``skill.agent_ids`` (or skill targets all agents
   via an empty list);
3. ``skill.name`` is allowed by ``ops.skills.allowed_ids`` — supports
   ``"*"`` wildcard or glob-style prefix patterns like ``"finance:*"``.

Public API (consumed by ``lifecycle.before_agent`` once Section B lands):

- :func:`match_and_inject` — returns the markdown ``Relevant skills``
  block (empty string if no candidates clear the gates).
- :func:`build_consult_applicable_skills_tool` — factory returning a
  mid-turn tool an agent can call when scope shifts; result mirrors the
  block plus structured metadata.
- :func:`_matches_any` — exported for unit tests and reuse by callers
  needing to pin the allowed-ids glob semantics.

Direct-mode exclusion: callers can pass ``skip_direct_mode=True`` plus
``mode="direct"`` to suppress injection, or set
``ops.skills.injection.skip_direct_mode = True`` on the agent's
operations config. Default is to inject for both modes.
"""

from __future__ import annotations

import fnmatch
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from opentelemetry import trace

from app.skills.registry import Skill, skills_registry

logger = logging.getLogger(__name__)

# Module-level tracer. ``opentelemetry.trace.get_tracer`` is contract-safe
# whether or not a TracerProvider has been configured globally — when no
# provider is set it returns a no-op tracer, so importing this module never
# fails and production calls never raise from a missing telemetry stack.
# Tests patch ``_tracer`` to capture span attributes (see
# ``test_skill_injection.py::_FakeTracer``).
_tracer = trace.get_tracer(__name__)


def _embeddings_warmed() -> bool:
    """Indirection over :func:`app.skills.skill_embeddings.is_warmed`.

    The runtime calls this once per turn to decide whether the semantic
    path or the keyword fallback should run. Defined as a thin wrapper so
    tests can monkeypatch the decision without reaching into another
    module's globals.
    """
    try:
        from app.skills.skill_embeddings import is_warmed

        return bool(is_warmed())
    except Exception:
        return False


if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.runtime.types import DirectRequest, TaskContract

    # PikarBaseAgent is referenced as a string to avoid a circular import
    # at runtime; we don't actually import it here.


__all__ = [
    "SkillMatch",
    "build_consult_applicable_skills_tool",
    "consult_applicable_skills_factory",
    "match_and_inject",
]


@dataclass
class SkillMatch:
    """A scored skill candidate returned by the matcher."""

    score: float
    skill: Skill


# ---------------------------------------------------------------------------
# Glob helpers
# ---------------------------------------------------------------------------


def _matches_any(skill_name: str, patterns: list[str]) -> bool:
    """Return ``True`` if ``skill_name`` matches any glob pattern in ``patterns``.

    Empty pattern list denies everything (callers wanting "allow all"
    should pass ``["*"]`` — this matches ``operations.yaml``'s default).
    """
    if not patterns:
        return False
    if "*" in patterns:
        return True
    return any(fnmatch.fnmatchcase(skill_name, p) for p in patterns)


# ---------------------------------------------------------------------------
# Keyword fallback (W3 A3-lite)
# ---------------------------------------------------------------------------


def _keyword_match_skills(
    query: str,
    skills: list[Skill],
    *,
    allowed: list[str],
    top_k: int,
) -> list[SkillMatch]:
    """Substring fallback used when the embedding cache is cold.

    Splits ``query`` into >2-char tokens, scores each candidate skill by
    the fraction of tokens that appear (lowercased substring match) in
    the skill's name + description + knowledge_summary, and returns the
    top-K matches whose score clears 0.65 (the default similarity floor).

    Score formula: ``0.65 + 0.30 * (hits / total_tokens)`` — keeps the
    fallback's scores in the ``[0.65, 0.95]`` band so they don't claim
    higher confidence than semantic matches (which can reach 1.0).

    Agent scope filtering (``skill.agent_ids``) is the caller's job —
    pass ``skills`` already scoped via ``skills_registry.get_by_agent_id``.
    """
    query_tokens = {t for t in query.lower().split() if len(t) > 2}
    if not query_tokens:
        return []

    matches: list[SkillMatch] = []
    for skill in skills:
        if not _matches_any(skill.name, allowed):
            continue
        haystack = " ".join(
            (
                skill.name,
                getattr(skill, "description", "") or "",
                getattr(skill, "knowledge_summary", "") or "",
            )
        ).lower()
        hits = sum(1 for token in query_tokens if token in haystack)
        if hits == 0:
            continue
        score = 0.65 + 0.30 * (hits / len(query_tokens))
        matches.append(SkillMatch(score=score, skill=skill))

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:top_k]


# ---------------------------------------------------------------------------
# Render helper
# ---------------------------------------------------------------------------


def _render_section(matches: list[SkillMatch]) -> str:
    """Render matched skills as a markdown ``## Relevant skills`` block.

    Returns an empty string when ``matches`` is empty so callers can
    unconditionally concatenate the result onto an instruction.
    """
    if not matches:
        return ""

    lines: list[str] = ["## Relevant skills", ""]
    for m in matches:
        summary = (m.skill.knowledge_summary or "").strip()
        description = (m.skill.description or "").strip()
        lines.append(
            f"- **{m.skill.name}** (score {m.score:.2f}, {m.skill.category}): "
            f"{description}"
        )
        if summary and summary != description:
            lines.append(f"  - {summary}")
    lines.append("")
    lines.append("Call `use_skill(name)` for the full guidance when needed.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query extraction
# ---------------------------------------------------------------------------


def _extract_query(request: Any) -> str:
    """Pull the user-facing text off a :class:`TaskContract` or :class:`DirectRequest`.

    ``TaskContract`` exposes ``goal``; ``DirectRequest`` exposes
    ``message``. ``MagicMock`` instances expose both — accept either.
    """
    text = getattr(request, "goal", None) or getattr(request, "message", None) or ""
    if not isinstance(text, str):
        return ""
    return text.strip()


# ---------------------------------------------------------------------------
# Core matcher
# ---------------------------------------------------------------------------


async def match_and_inject(
    request: TaskContract | DirectRequest,
    agent: Any,
    *,
    top_k: int | None = None,
    similarity_floor: float | None = None,
    mode: str | None = None,
    skip_direct_mode: bool | None = None,
) -> str:
    """Return a markdown ``Relevant skills`` block for the given request.

    Args:
        request: The :class:`TaskContract` (initiative mode) or
            :class:`DirectRequest` (direct mode) describing the turn.
        agent: The owning :class:`PikarBaseAgent` (typed as :class:`Any` to
            avoid a circular import). Must expose ``agent_id`` and
            ``ops.skills.{allowed_ids,injection.top_k,injection.similarity_floor}``.
        top_k: Override the per-agent ``ops.skills.injection.top_k``.
        similarity_floor: Override the per-agent ``similarity_floor``.
        mode: ``"direct"`` or ``"initiative"``. Used together with
            ``skip_direct_mode`` to suppress injection for direct turns.
        skip_direct_mode: When ``True`` and ``mode == "direct"``, returns
            the empty string without consulting the registry. Falls back
            to ``agent.ops.skills.injection.skip_direct_mode`` when ``None``.

    Returns:
        The rendered markdown block, or an empty string when no skills
        clear the threshold (or when direct-mode skipping kicks in).
    """
    with _tracer.start_as_current_span("pikar.skill_injection.match") as span:
        # Baseline attributes — set first so they're always present on the
        # span even if an early return fires.
        agent_id_value = getattr(getattr(agent, "agent_id", None), "value", None)
        span.set_attribute(
            "pikar.agent_id",
            str(agent_id_value) if agent_id_value is not None else "",
        )
        span.set_attribute("pikar.mode", mode or "unknown")

        # --- direct-mode exclusion -----------------------------------------
        injection_cfg = getattr(getattr(agent, "ops", None), "skills", None)
        injection_cfg = getattr(injection_cfg, "injection", None)
        eff_skip_direct = (
            skip_direct_mode
            if skip_direct_mode is not None
            else bool(getattr(injection_cfg, "skip_direct_mode", False))
        )
        if mode == "direct" and eff_skip_direct:
            span.set_attribute("pikar.skipped", "direct_mode")
            return ""

        # --- effective config (caller overrides win) ------------------------
        eff_top_k = (
            top_k if top_k is not None else int(getattr(injection_cfg, "top_k", 5) or 5)
        )
        eff_floor = (
            similarity_floor
            if similarity_floor is not None
            else float(getattr(injection_cfg, "similarity_floor", 0.65) or 0.65)
        )
        span.set_attribute("pikar.top_k", eff_top_k)
        span.set_attribute("pikar.similarity_floor", eff_floor)

        # --- query extraction ----------------------------------------------
        query = _extract_query(request)
        span.set_attribute("pikar.query_len", len(query))
        if not query:
            span.set_attribute("pikar.skipped", "empty_query")
            return ""

        allowed = list(
            getattr(getattr(agent, "ops", None), "skills", None).allowed_ids
            if getattr(getattr(agent, "ops", None), "skills", None) is not None
            and getattr(getattr(agent.ops, "skills", None), "allowed_ids", None)
            is not None
            else ["*"]
        )
        agent_id = getattr(agent, "agent_id", None)

        # --- matcher routing ------------------------------------------------
        # In production the embedding cache is warmed at startup and the
        # semantic path runs. In dev/test environments without Vertex
        # credentials ``is_warmed()`` stays False, so we fall back to a
        # substring matcher to keep skill injection useful locally.
        if not _embeddings_warmed():
            span.set_attribute("pikar.matcher", "keyword_fallback")
            try:
                scoped = skills_registry.get_by_agent_id(agent_id) if agent_id else []
            except Exception as exc:
                span.set_attribute("pikar.error", str(exc)[:200])
                logger.debug("[skill_injection] get_by_agent_id failed: %s", exc)
                return ""
            span.set_attribute("pikar.candidate_count", len(scoped))
            keyword_matches = _keyword_match_skills(
                query=query,
                skills=scoped,
                allowed=allowed,
                top_k=eff_top_k,
            )
            span.set_attribute("pikar.matched_count", len(keyword_matches))
            return _render_section(keyword_matches)

        span.set_attribute("pikar.matcher", "semantic")

        # --- candidate retrieval (over-fetch so allowed_ids post-filter
        #     does not under-count) ---------------------------------------
        try:
            candidates = skills_registry.semantic_search(
                query=query,
                agent_id=agent_id,
                limit=max(eff_top_k * 3, eff_top_k),
                threshold=eff_floor,
            )
        except Exception as exc:
            span.set_attribute("pikar.error", str(exc)[:200])
            logger.debug("[skill_injection] semantic_search failed: %s", exc)
            return ""

        span.set_attribute("pikar.candidate_count", len(candidates))
        if not candidates:
            span.set_attribute("pikar.matched_count", 0)
            return ""

        matches: list[SkillMatch] = []
        for candidate in candidates:
            score = float(candidate.get("score", 0.0))
            skill = candidate.get("skill")
            if skill is None:
                continue
            if score < eff_floor:
                continue
            # empty agent_ids list means available to all agents
            skill_agents = getattr(skill, "agent_ids", None) or []
            if skill_agents and agent_id not in skill_agents:
                continue
            if not _matches_any(skill.name, allowed):
                continue
            matches.append(SkillMatch(score=score, skill=skill))
            if len(matches) >= eff_top_k:
                break

        span.set_attribute("pikar.matched_count", len(matches))
        return _render_section(matches)


# ---------------------------------------------------------------------------
# Mid-turn tool factory
# ---------------------------------------------------------------------------


def build_consult_applicable_skills_tool(agent: Any) -> Callable[..., Any]:
    """Return an agent-callable tool that re-runs skill matching mid-turn.

    Useful when a user's scope shifts after the initial injection — the
    agent can call ``consult_applicable_skills("new task description")``
    to refresh its set of relevant skills without escalating to a full
    new turn.

    Returns a tuple of ``(success, agent_id, skills_block)`` packed in a
    dict so the caller can decide where to slot the block into its next
    reasoning step (vs. us mutating system state).
    """
    # Local import — avoids any chance of a runtime cycle with types.py.
    from uuid import uuid4

    from app.agents.runtime.types import DirectRequest

    async def consult_applicable_skills(task: str) -> dict[str, Any]:
        """Re-match this agent's skills against ``task`` and return a block."""
        try:
            # Build a synthetic DirectRequest just to feed `_extract_query`.
            # Fields beyond ``message`` are unused by the matcher but
            # required by the frozen dataclass; we synthesize defaults.
            req = DirectRequest(
                user_id=_safe_uuid(getattr(agent, "user_id", None)) or uuid4(),
                agent_id=getattr(agent, "agent_id", None),
                persona_id=str(getattr(agent, "persona_id", "") or ""),
                message=task,
                session_id=None,
            )
            block = await match_and_inject(req, agent)
            agent_id = getattr(agent, "agent_id", None)
            return {
                "success": True,
                "agent_id": getattr(agent_id, "value", str(agent_id)),
                "skills_block": block,
            }
        except Exception as exc:
            logger.warning(
                "[skill_injection] consult_applicable_skills failed: %s", exc
            )
            return {"success": False, "error": str(exc)}

    consult_applicable_skills.__name__ = "consult_applicable_skills"
    consult_applicable_skills.__doc__ = (
        "Re-match this agent's skills against a task description and "
        "return a markdown 'Relevant skills' block (empty string if no "
        "skills clear the configured similarity floor)."
    )
    return consult_applicable_skills


def _safe_uuid(value: Any) -> UUID | None:
    """Return ``value`` if it's already a UUID, else attempt to parse it."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            return None
    return None


# Public alias matching the controller-prompt naming convention.
consult_applicable_skills_factory = build_consult_applicable_skills_tool
