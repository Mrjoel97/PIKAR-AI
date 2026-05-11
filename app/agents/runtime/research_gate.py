# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Research-completion gate per spec section 7.

The gate blocks all non-research tool calls until the research run for a
given (task_contract_id, agent_id) is marked complete. Set of allowed
research tool IDs is the canonical ``RESEARCH_TOOL_IDS`` frozenset below.

Public API (consumed by :mod:`app.agents.runtime.lifecycle` callbacks):

* :data:`RESEARCH_TOOL_IDS` — the five allow-listed tool IDs.
* :func:`open_gate` — insert an ``agent_research_runs`` row (status='open').
* :func:`is_open` — True if an open/in_progress run exists for the pair.
* :func:`record_tool_result` — append a research tool's raw result.
* :func:`check_coverage` — LLM coverage check; returns ResearchResult or None.
* :func:`close_gate` — persist a complete ResearchResult and stamp completed_at.

The module owns all Supabase access through the async helper
:func:`_get_supabase`, which mirrors the pattern used in
:mod:`app.agents.runtime.persona_gate` so unit tests can monkey-patch the
client with an :class:`unittest.mock.AsyncMock` shaped wrapper.

The coverage LLM is Gemini 2.5 Flash by default (overridable via the
``RESEARCH_COVERAGE_LLM_MODEL`` env var). Failures fall through gracefully
unless the run's iteration budget is exhausted, at which point a
:class:`ResearchGateError` is raised so callers can surface a forced-
completion warning to the workspace.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.agents.runtime.types import ResearchGateError, ResearchResult
from app.skills.registry import AgentID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task 46 — research tool allow-set
# ---------------------------------------------------------------------------


RESEARCH_TOOL_IDS: frozenset[str] = frozenset(
    {
        "deep_research",
        "tavily_search",
        "firecrawl_scrape",
        "google_search",
        "quick_research",
    }
)


# ---------------------------------------------------------------------------
# Coverage LLM configuration
# ---------------------------------------------------------------------------


COVERAGE_LLM_MODEL = os.getenv("RESEARCH_COVERAGE_LLM_MODEL", "gemini-2.5-flash")
COVERAGE_LLM_TIMEOUT_S = float(os.getenv("RESEARCH_COVERAGE_LLM_TIMEOUT_S", "20.0"))


# ---------------------------------------------------------------------------
# Supabase indirection (matches app/agents/runtime/persona_gate.py)
# ---------------------------------------------------------------------------


async def _get_supabase() -> Any:
    """Return the async service-role Supabase client.

    Indirection so tests can monkey-patch the client with a MagicMock.
    Imported lazily to avoid triggering Supabase initialization at module
    import time.
    """
    from app.services.supabase_client import get_async_client

    return await get_async_client()


# ---------------------------------------------------------------------------
# Task 47 — open_gate
# ---------------------------------------------------------------------------


async def open_gate(
    *,
    task_contract_id: UUID,
    contract_source: str,
    agent_id: AgentID,
    initial_query: str,
    user_id: UUID | None = None,
) -> UUID:
    """Insert an ``agent_research_runs`` row (status='open') and return run_id.

    Args:
        task_contract_id: UUID of the TaskContract the run is bound to.
        contract_source: Logical source of the contract — e.g.
            ``"initiative_step"`` or ``"department_task"``.
        agent_id: AgentID of the agent that opened the run.
        initial_query: The first-pass research query (free text).
        user_id: Optional auth.users id for RLS scoping.

    Returns:
        UUID of the newly-inserted ``agent_research_runs`` row.

    Raises:
        ResearchGateError: If the insert response carries no row.
    """
    client = await _get_supabase()
    payload: dict[str, Any] = {
        "task_contract_id": str(task_contract_id),
        "task_contract_source": contract_source,
        "agent_id": agent_id.value,
        "query": initial_query,
        "status": "open",
        "iterations": 0,
    }
    if user_id is not None:
        payload["user_id"] = str(user_id)

    response = await client.table("agent_research_runs").insert(payload).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        raise ResearchGateError(
            f"open_gate insert returned no row for contract {task_contract_id}"
        )
    run_id = UUID(rows[0]["id"])
    logger.info(
        "research_gate opened",
        extra={
            "run_id": str(run_id),
            "task_contract_id": str(task_contract_id),
            "agent_id": agent_id.value,
        },
    )
    return run_id


# ---------------------------------------------------------------------------
# Task 48 — is_open
# ---------------------------------------------------------------------------


async def is_open(*, task_contract_id: UUID, agent_id: AgentID) -> bool:
    """Return True if an open/in_progress research run exists for this pair.

    A run counts as "blocking" while its status is ``open`` or
    ``in_progress``; ``complete`` and ``failed`` are terminal.
    """
    client = await _get_supabase()
    response = (
        await client.table("agent_research_runs")
        .select("id, status")
        .eq("task_contract_id", str(task_contract_id))
        .eq("agent_id", agent_id.value)
        .in_("status", ["open", "in_progress"])
        .limit(1)
        .execute()
    )
    return bool(getattr(response, "data", None))


# ---------------------------------------------------------------------------
# Task 49 + Task 71 — record_tool_result
# ---------------------------------------------------------------------------


async def record_tool_result(
    *,
    run_id: UUID,
    tool_id: str,
    raw_result: dict,
) -> None:
    """Append a research tool's raw result to the run's ``result`` JSONB.

    Increments ``iterations`` by one and flips ``status`` to ``in_progress``.
    Refuses non-research tool IDs and refuses to write to runs already in a
    terminal state.

    Raises:
        ResearchGateError: If ``tool_id`` is not in :data:`RESEARCH_TOOL_IDS`,
            if the run does not exist, or if the run is already
            ``complete``/``failed``.
    """
    if tool_id not in RESEARCH_TOOL_IDS:
        raise ResearchGateError(
            f"record_tool_result called with non-research tool_id={tool_id!r}"
        )
    client = await _get_supabase()
    row_resp = (
        await client.table("agent_research_runs")
        .select("result, iterations, status")
        .eq("id", str(run_id))
        .single()
        .execute()
    )
    data = getattr(row_resp, "data", None)
    if not data:
        raise ResearchGateError(f"run_id {run_id} not found")
    row = data[0] if isinstance(data, list) else data
    status = row.get("status")
    if status in ("complete", "failed"):
        raise ResearchGateError(
            f"cannot record tool result on closed run {run_id} "
            f"(status={status})"
        )

    existing = row.get("result") or {}
    raw_results = list(existing.get("raw_results") or [])
    raw_results.append({"tool_id": tool_id, "data": raw_result})
    merged = {**existing, "raw_results": raw_results}
    new_iter = int(row.get("iterations") or 0) + 1
    await (
        client.table("agent_research_runs")
        .update({"result": merged, "iterations": new_iter, "status": "in_progress"})
        .eq("id", str(run_id))
        .execute()
    )


# ---------------------------------------------------------------------------
# Task 50 — coverage prompt + JSON parser
# ---------------------------------------------------------------------------


def _strip_code_fence(text: str) -> str:
    """Strip ``\\`\\`\\`json ... \\`\\`\\``` or ``\\`\\`\\` ... \\`\\`\\``` fences."""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


def _parse_coverage_json(text: str) -> ResearchResult | None:
    """Parse a JSON coverage response into a ResearchResult.

    Returns ``None`` when the text isn't valid JSON, isn't an object, or
    fails :class:`ResearchResult` validation. The caller decides whether to
    retry or raise based on iteration budget.
    """
    try:
        parsed = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    try:
        return ResearchResult.model_validate(parsed)
    except Exception:
        logger.warning("research coverage JSON failed ResearchResult validation")
        return None


def _build_coverage_prompt(
    success_criteria: list[str], raw_results: list[dict]
) -> str:
    """Compose the coverage-check prompt for the coverage LLM."""
    criteria_block = "\n".join(f"- {c}" for c in success_criteria) or "- (none)"
    raw_blob = json.dumps(raw_results, ensure_ascii=False)[:8000]
    return (
        "You are auditing whether research findings cover a set of success "
        "criteria.\n\n"
        "SUCCESS CRITERIA:\n"
        f"{criteria_block}\n\n"
        "RAW RESEARCH RESULTS (tool outputs):\n"
        f"{raw_blob}\n\n"
        "Produce a JSON object with these keys exactly:\n"
        '  "summary" (200-400 word synthesis of what is known)\n'
        '  "sources": list of {"url","title","key_claim","retrieved_at"}\n'
        '  "contradictions": list of strings\n'
        '  "coverage_assessment": "complete" or "partial"\n'
        '  "missing_information": list of unanswered criteria\n\n'
        "Return ONLY the JSON object. Coverage is 'complete' only when every "
        "success criterion is directly addressed by at least one source."
    )


# ---------------------------------------------------------------------------
# Task 51 + 52 — check_coverage
# ---------------------------------------------------------------------------


async def _call_coverage_llm(prompt: str) -> str | None:
    """Low-temperature Gemini Flash call. Returns text or None on failure.

    Wrapped so unit tests can monkey-patch it without touching real Gemini.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.warning("google.genai not available; research coverage LLM skipped")
        return None
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=COVERAGE_LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=2048
                ),
            ),
            timeout=COVERAGE_LLM_TIMEOUT_S,
        )
        text = (getattr(response, "text", None) or "").strip()
        return text or None
    except asyncio.TimeoutError:
        logger.warning("research coverage LLM timed out after %ss", COVERAGE_LLM_TIMEOUT_S)
        return None
    except Exception as exc:
        logger.warning("research coverage LLM call failed: %s", exc)
        return None


async def _load_run(run_id: UUID) -> dict:
    """Load a single ``agent_research_runs`` row by id.

    Returns the row dict (not wrapped). Raises :class:`ResearchGateError`
    if the row is missing.
    """
    client = await _get_supabase()
    resp = (
        await client.table("agent_research_runs")
        .select("id, result, iterations")
        .eq("id", str(run_id))
        .single()
        .execute()
    )
    data = getattr(resp, "data", None)
    if not data:
        raise ResearchGateError(f"run_id {run_id} not found")
    return data[0] if isinstance(data, list) else data


async def check_coverage(
    *,
    run_id: UUID,
    success_criteria: list[str],
    max_iterations: int,
) -> ResearchResult | None:
    """Run an LLM coverage check.

    Returns a :class:`ResearchResult` if the LLM judges coverage complete,
    ``None`` if it judges coverage partial and the iteration budget still
    has room, and raises :class:`ResearchGateError` when the iteration
    budget is exhausted without a complete coverage assessment (or when
    the LLM call itself failed and the budget is exhausted).
    """
    row = await _load_run(run_id)
    raw_results = list((row.get("result") or {}).get("raw_results") or [])
    iterations = int(row.get("iterations") or 0)

    prompt = _build_coverage_prompt(success_criteria, raw_results)
    text = await _call_coverage_llm(prompt)
    if not text:
        if iterations >= max_iterations:
            raise ResearchGateError(
                f"research run {run_id} exhausted {max_iterations} iterations "
                "with no successful coverage LLM call"
            )
        return None

    result = _parse_coverage_json(text)
    if result is None:
        if iterations >= max_iterations:
            raise ResearchGateError(
                f"research run {run_id} exhausted {max_iterations} iterations "
                "with unparseable coverage output"
            )
        return None

    if result.coverage_assessment == "complete":
        return result

    if iterations >= max_iterations:
        raise ResearchGateError(
            f"research run {run_id} exhausted {max_iterations} iterations; "
            f"missing: {result.missing_information}"
        )
    return None


# ---------------------------------------------------------------------------
# Task 53 — close_gate
# ---------------------------------------------------------------------------


async def close_gate(*, run_id: UUID, result: ResearchResult) -> None:
    """Persist the validated ResearchResult and mark the run complete."""
    client = await _get_supabase()
    payload = {
        "status": "complete",
        "result": result.model_dump(mode="json"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    await (
        client.table("agent_research_runs")
        .update(payload)
        .eq("id", str(run_id))
        .execute()
    )
    logger.info("research_gate closed", extra={"run_id": str(run_id)})


__all__ = [
    "RESEARCH_TOOL_IDS",
    "ResearchGateError",
    "ResearchResult",
    "check_coverage",
    "close_gate",
    "is_open",
    "open_gate",
    "record_tool_result",
]
