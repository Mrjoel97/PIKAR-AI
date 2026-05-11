# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Self-audit primitives per spec § 8.

Deterministic Gemini Flash call (low temperature). Walks every ``todo_item``
and every ``success_criterion`` against the produced artifacts, then:

  * persists the report to ``agent_audit_reports`` (via
    :func:`persist_audit_report`); and
  * appends a compact ``audit_summary`` record to the originating
    ``initiative_checklist_items.evidence`` JSONB (via
    :func:`attach_audit_summary_to_evidence`).

The audit deliberately runs at low temperature with a strict JSON contract
so a downstream caller can reason about pass/fail/partial without prompt
drift. Belt-and-braces enforcement of
``ops.audit.fail_on_any_unmet_criterion`` downgrades an over-generous LLM
"pass" verdict to "fail/retry" whenever any criterion is unmet.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
from typing import Any
from uuid import UUID

from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
)
from app.skills.registry import AgentID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tunables (env-driven, low-temperature defaults)
# ---------------------------------------------------------------------------

AUDIT_LLM_MODEL = os.getenv("AUDIT_LLM_MODEL", "gemini-2.5-flash")
"""Gemini Flash model id used for audits.

Override with ``AUDIT_LLM_MODEL`` if the deployment needs a tighter
fallback (e.g. ``gemini-2.5-flash-lite``).
"""

AUDIT_LLM_TIMEOUT_S = float(os.getenv("AUDIT_LLM_TIMEOUT_S", "25.0"))
"""Per-call timeout for the audit LLM (seconds).

Audits run *after* the producing turn finished, so a longer timeout than
the classifier is acceptable — but we still cap it so a hung call does
not block submission.
"""

AUDIT_LLM_TEMPERATURE = 0.1
"""Low temperature so two runs over the same artifacts agree."""

AUDIT_LLM_MAX_OUTPUT_TOKENS = 2048
"""Plenty of room for ``per_item`` + ``per_criterion`` blocks but bounded."""


# ---------------------------------------------------------------------------
# Prompt builder (Task 54)
# ---------------------------------------------------------------------------


def _serialize_artifacts(artifacts: list[Artifact]) -> str:
    """Serialize artifacts for the prompt — bounded and JSON-safe."""
    safe: list[dict[str, Any]] = []
    for art in artifacts:
        safe.append(
            {
                "kind": art.kind,
                "ref": art.ref,
                "summary": art.summary,
                "payload": art.payload,
            }
        )
    blob = json.dumps(safe, ensure_ascii=False, default=str)
    return blob[:6000]


def _build_audit_prompt(
    *,
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
) -> str:
    """Compose the audit prompt.

    Embeds every ``todo_item`` (title + description) and every
    ``success_criterion`` verbatim so the LLM has the exact contract text
    to audit against. Demands strict JSON output.
    """
    if contract.todo_items:
        todo_block = "\n".join(
            (
                f"- id={item.id} :: {item.title}"
                + (f"\n  desc: {item.description}" if item.description else "")
            )
            for item in contract.todo_items
        )
    else:
        todo_block = "- (no todo items)"

    if contract.success_criteria:
        crit_block = "\n".join(f"- {c}" for c in contract.success_criteria)
    else:
        crit_block = "- (none)"

    artifacts_blob = _serialize_artifacts(artifacts)
    research_blob = (research.summary or "")[:3000]

    return (
        "You are auditing whether produced artifacts satisfy a task contract.\n\n"
        f"GOAL: {contract.goal}\n\n"
        "TODO ITEMS:\n"
        f"{todo_block}\n\n"
        "SUCCESS CRITERIA:\n"
        f"{crit_block}\n\n"
        "RESEARCH SUMMARY:\n"
        f"{research_blob}\n\n"
        f"ARTIFACTS:\n{artifacts_blob}\n\n"
        "Output a JSON object with these keys exactly:\n"
        '  "overall_status": "pass" | "fail" | "partial"\n'
        '  "per_item": [{"item_id","status","evidence_pointers","gaps"}]\n'
        '  "per_criterion": [{"criterion","met","justification"}]\n'
        '  "gaps": list of strings\n'
        '  "recoverable": boolean\n'
        '  "next_action": "submit" | "retry" | "escalate"\n\n'
        "Pass ONLY if every criterion is met and every todo has evidence. "
        "Return ONLY the JSON object — no prose, no code fences."
    )


# ---------------------------------------------------------------------------
# JSON parser (Task 55)
# ---------------------------------------------------------------------------


def _strip_code_fence(text: str) -> str:
    """Strip leading ```json fences so ``json.loads`` accepts the payload."""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


def _parse_audit_json(text: str) -> AuditReport | None:
    """Parse the audit LLM output into an :class:`AuditReport`.

    Returns ``None`` if the payload is not valid JSON, is not a JSON
    object, or fails ``AuditReport`` validation (e.g. invalid status).
    """
    try:
        parsed = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    # Audit LLM is not responsible for policy violations — those are
    # populated by the persona gate later. Default to an empty list so
    # the AuditReport validation doesn't fail on missing keys.
    parsed.setdefault("policy_violations", [])
    try:
        return AuditReport.model_validate(parsed)
    except Exception:
        logger.warning("audit JSON failed AuditReport validation")
        return None


# ---------------------------------------------------------------------------
# Audit LLM client (Task 56)
# ---------------------------------------------------------------------------


def _load_genai() -> tuple[Any, Any] | None:
    """Import ``google.genai`` lazily so tests without the SDK still pass.

    Returns ``None`` if the SDK is unavailable; otherwise returns the
    ``(genai, genai_types)`` tuple.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        return None
    return genai, genai_types


async def _call_audit_llm(prompt: str) -> str | None:
    """Single low-temperature Gemini Flash call. Returns text or ``None``.

    Isolated as a module-level coroutine so unit tests can monkeypatch
    it with ``AsyncMock`` without reaching into ``google.genai``.
    """
    loaded = _load_genai()
    if loaded is None:
        logger.warning("google.genai not available; audit LLM skipped")
        return None
    genai, genai_types = loaded
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=AUDIT_LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=AUDIT_LLM_TEMPERATURE,
                    max_output_tokens=AUDIT_LLM_MAX_OUTPUT_TOKENS,
                ),
            ),
            timeout=AUDIT_LLM_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.warning("audit LLM call timed out after %.1fs", AUDIT_LLM_TIMEOUT_S)
        return None
    except Exception as exc:
        logger.warning("audit LLM call failed: %s", exc)
        return None
    raw = (getattr(response, "text", None) or "").strip()
    return raw or None


# ---------------------------------------------------------------------------
# Public API: audit_against_contract (Task 57 + Task 72)
# ---------------------------------------------------------------------------


def _fallback_fail_report(reason: str) -> AuditReport:
    """Build a conservative fail report when the LLM cannot be trusted."""
    return AuditReport(
        overall_status="fail",
        per_item=[],
        per_criterion=[],
        gaps=[reason],
        policy_violations=[],
        recoverable=False,
        next_action="escalate",
    )


async def audit_against_contract(
    contract: TaskContract,
    artifacts: list[Artifact],
    research: ResearchResult,
    *,
    ops: OperationsConfig,
) -> AuditReport:
    """Deterministic LLM audit of artifacts against todo + success_criteria.

    Honors ``ops.audit.fail_on_any_unmet_criterion`` as belt-and-braces:
    an LLM verdict of ``"pass"`` is downgraded to ``"fail"`` with
    ``next_action="retry"`` whenever any criterion is reported unmet.

    Args:
        contract: The frozen task contract being audited.
        artifacts: Concrete deliverables produced by the agent turn.
        research: The research result that unlocked tool use; included
            in the prompt so the auditor can cross-reference cited claims.
        ops: Per-agent operations config — only ``ops.audit`` is read.

    Returns:
        An :class:`AuditReport`. Never raises — falls back to an
        ``overall_status="fail", next_action="escalate"`` report when the
        LLM is unavailable or produces unparseable output.
    """
    prompt = _build_audit_prompt(
        contract=contract, artifacts=artifacts, research=research
    )
    text = await _call_audit_llm(prompt)
    if not text:
        return _fallback_fail_report("audit LLM unavailable")
    report = _parse_audit_json(text)
    if report is None:
        return _fallback_fail_report("audit LLM output unparseable")

    # Belt-and-braces: enforce fail_on_any_unmet_criterion even if the LLM
    # voted "pass" while flagging an unmet criterion. Spec § 8.
    fail_on_unmet = getattr(ops.audit, "fail_on_any_unmet_criterion", True)
    if fail_on_unmet and any(not c.met for c in report.per_criterion):
        if report.overall_status == "pass":
            report = report.model_copy(
                update={"overall_status": "fail", "next_action": "retry"}
            )

    return report


# ---------------------------------------------------------------------------
# Supabase helpers (Tasks 58 + 59)
# ---------------------------------------------------------------------------


def _get_supabase() -> Any:
    """Return the async Supabase client.

    Production returns a coroutine (the async singleton); tests
    monkeypatch this to a sync lambda returning a ``MagicMock``. Callers
    must use :func:`_resolve_supabase` to handle both shapes.
    """
    from app.services.supabase_client import get_async_client

    return get_async_client()


async def _resolve_supabase() -> Any:
    """Resolve ``_get_supabase()`` whether it is sync or returns a coroutine.

    Tests monkeypatch ``_get_supabase`` with a sync ``lambda`` returning
    a ``MagicMock``; production hits ``get_async_client()`` which is a
    coroutine. Both paths funnel through here so the callers stay clean.
    """
    candidate = _get_supabase()
    if inspect.iscoroutine(candidate):
        return await candidate
    return candidate


async def persist_audit_report(
    report: AuditReport,
    *,
    agent_id: AgentID,
    task_contract_id: UUID,
) -> UUID:
    """Insert an :class:`AuditReport` into ``agent_audit_reports``.

    Args:
        report: The audit report to persist.
        agent_id: The owning agent's ID (stored as TEXT).
        task_contract_id: UUID of the producing task contract.

    Returns:
        The UUID of the newly-inserted row.

    Raises:
        RuntimeError: If the insert returned no row (the Supabase client
            usually raises before this point, but we defend against an
            empty response anyway).
    """
    client = await _resolve_supabase()
    payload = {
        "agent_id": agent_id.value,
        "task_contract_id": str(task_contract_id),
        "overall_status": report.overall_status,
        "per_item": [i.model_dump(mode="json") for i in report.per_item],
        "per_criterion": [c.model_dump(mode="json") for c in report.per_criterion],
        "gaps": list(report.gaps),
        "policy_violations": [
            v.model_dump(mode="json") for v in report.policy_violations
        ],
        "recoverable": report.recoverable,
        "next_action": report.next_action,
    }
    response = await client.table("agent_audit_reports").insert(payload).execute()
    rows = getattr(response, "data", None) or []
    if not rows:
        raise RuntimeError("persist_audit_report insert returned no row")
    return UUID(rows[0]["id"])


async def attach_audit_summary_to_evidence(
    *,
    contract: TaskContract,
    report: AuditReport,
) -> None:
    """Append an ``audit_summary`` record to the checklist item's evidence.

    Only runs for ``contract.source == "initiative_step"`` — direct-mode
    and department-task contracts do not have a corresponding row in
    ``initiative_checklist_items``.

    The existing JSONB array is read, the new summary appended, and the
    full array written back. Concurrent audits on the same checklist
    item are rare in practice (one agent owns one step at a time), but
    the design accepts a last-writer-wins race.
    """
    if contract.source != "initiative_step":
        return

    client = await _resolve_supabase()
    row_resp = (
        await client.table("initiative_checklist_items")
        .select("evidence")
        .eq("id", str(contract.id))
        .single()
        .execute()
    )
    data = getattr(row_resp, "data", None) or {}
    # Supabase ``.single()`` returns a dict; defensive: tolerate a list shape
    # from older fakes that return one-element arrays.
    row = data[0] if isinstance(data, list) and data else data
    existing: list[Any] = []
    if isinstance(row, dict):
        existing = list(row.get("evidence") or [])

    existing.append(
        {
            "kind": "audit_summary",
            "overall_status": report.overall_status,
            "gaps": list(report.gaps),
            "next_action": report.next_action,
        }
    )

    await (
        client.table("initiative_checklist_items")
        .update({"evidence": existing})
        .eq("id", str(contract.id))
        .execute()
    )


__all__ = [
    "AUDIT_LLM_MAX_OUTPUT_TOKENS",
    "AUDIT_LLM_MODEL",
    "AUDIT_LLM_TEMPERATURE",
    "AUDIT_LLM_TIMEOUT_S",
    "attach_audit_summary_to_evidence",
    "audit_against_contract",
    "persist_audit_report",
]
