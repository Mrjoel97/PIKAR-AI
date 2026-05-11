# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Direct vs. initiative mode classifier per spec § 9.

Three-tier waterfall:

  1. Explicit override (``/quick``, ``/q``, ``/plan``, ``/initiative``).
  2. Rule heuristics (existing TaskContract, ``@agent`` handoff, initiative
     verb match, short factual-question shortcut).
  3. Persona default (``PersonaPolicy.classifier_default_mode``).
  4. LLM fallback — single Gemini Flash call. Safe default = ``"initiative"``
     so an ambiguous request still gets the full lifecycle (research gate,
     audit, persisted artifacts) rather than a "best-effort" reply.

Spec § 9 invariants enforced here:

  * ``session_has_open_contract=True`` -> initiative, regardless of rules.
  * ``@agent`` mention -> initiative.
  * Explicit override always wins (yes, even over an open contract — the
    user explicitly typed ``/quick`` to break out for one turn).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import ClassifierResult, Mode, PersonaPolicy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants (Task 66)
# ---------------------------------------------------------------------------

DIRECT_VERBS: frozenset[str] = frozenset(
    {
        "what",
        "when",
        "who",
        "where",
        "show",
        "list",
        "find",
        "look",
        "look up",
        "summarize",
        "tell me",
        "fetch",
        "get",
    }
)
"""Words/phrases that strongly signal a single-shot factual ask.

Single-token verbs (``"what"``, ``"show"``, ...) are matched against the first
token of the request. Multi-word entries (``"look up"``, ``"tell me"``) are
matched as a prefix on the full request.
"""

INITIATIVE_VERBS: frozenset[str] = frozenset(
    {
        "plan",
        "build",
        "launch",
        "develop",
        "orchestrate",
        "migrate",
        "run a campaign",
        "execute",
        "strategize",
    }
)
"""Words/phrases that strongly signal a multi-step initiative."""

DIRECT_LENGTH_THRESHOLD: int = 80
"""Max characters for the direct-verb shortcut.

A short ``"what is q3 revenue"`` is direct; a long, nuanced question is
ambiguous and falls through to the LLM tier.
"""

# ---------------------------------------------------------------------------
# LLM tunables (Task 69)
# ---------------------------------------------------------------------------

CLASSIFIER_LLM_MODEL = os.getenv("TASK_ROUTER_LLM_MODEL", "gemini-2.5-flash")
CLASSIFIER_LLM_TIMEOUT_S = float(os.getenv("TASK_ROUTER_LLM_TIMEOUT_S", "8.0"))


# ---------------------------------------------------------------------------
# Override detection (Task 67)
# ---------------------------------------------------------------------------

_OVERRIDE_DIRECT_PREFIXES: tuple[str, ...] = ("/quick", "/q ", "/q\t", "/q\n")
_OVERRIDE_INITIATIVE_PREFIXES: tuple[str, ...] = ("/plan", "/initiative")


def _detect_override(text: str) -> Mode | None:
    """Detect explicit slash overrides per spec § 9.1.

    Recognised prefixes (case-insensitive, leading whitespace tolerated):

      * ``/quick``, ``/q`` -> ``"direct"``
      * ``/plan``, ``/initiative`` -> ``"initiative"``

    Returns ``None`` when no override is present so the caller can fall
    through to the next tier.
    """
    if not text:
        return None
    stripped = text.strip().lower()
    if not stripped:
        return None
    # /q must be a standalone token (so "/query" doesn't accidentally match).
    if stripped == "/q" or stripped.startswith(_OVERRIDE_DIRECT_PREFIXES):
        return "direct"
    if stripped.startswith(_OVERRIDE_INITIATIVE_PREFIXES):
        return "initiative"
    return None


# ---------------------------------------------------------------------------
# Rule heuristics (Task 68)
# ---------------------------------------------------------------------------

_AT_AGENT_RE = re.compile(r"(^|\s)@[a-z][a-z0-9_\-]*", re.IGNORECASE)
_INITIATIVE_ID_RE = re.compile(r"\binitiative[_\- ]?id\b", re.IGNORECASE)


def _apply_rules(text: str, *, session_has_open_contract: bool) -> Mode | None:
    """Apply rule heuristics per spec § 9.2. First conclusive answer wins.

    Order:

      1. Existing TaskContract on session -> ``"initiative"``.
      2. Initiative verb (or phrase like ``"run a campaign"``) -> ``"initiative"``.
      3. ``@agent`` handoff or explicit ``initiative_id`` -> ``"initiative"``.
      4. Direct verb at start of message AND length < threshold -> ``"direct"``.
      5. Otherwise ``None`` (caller falls through to persona default / LLM).
    """
    if session_has_open_contract:
        return "initiative"

    normalized = (text or "").strip().lower()
    if not normalized:
        return None

    # Initiative verbs — substring match catches multi-word phrases like
    # "run a campaign" naturally.
    for verb in INITIATIVE_VERBS:
        # Word-boundary match for single-word verbs to avoid e.g. "plant" -> plan;
        # substring match for phrases (spec gives "run a campaign" verbatim).
        if " " in verb:
            if verb in normalized:
                return "initiative"
        else:
            if re.search(rf"\b{re.escape(verb)}\b", normalized):
                return "initiative"

    # @agent handoff or explicit initiative id.
    if _AT_AGENT_RE.search(normalized):
        return "initiative"
    if _INITIATIVE_ID_RE.search(normalized):
        return "initiative"

    # Short factual question — first token (single-word direct verb) or
    # multi-word direct prefix, AND length under threshold.
    tokens = normalized.split()
    first_token = tokens[0] if tokens else ""
    if first_token in DIRECT_VERBS and len(normalized) < DIRECT_LENGTH_THRESHOLD:
        return "direct"
    for direct_prefix in DIRECT_VERBS:
        if " " in direct_prefix and normalized.startswith(direct_prefix):
            if len(normalized) < DIRECT_LENGTH_THRESHOLD:
                return "direct"

    return None


# ---------------------------------------------------------------------------
# LLM fallback (Task 69)
# ---------------------------------------------------------------------------


def _strip_code_fence(text: str) -> str:
    """Strip leading ```json fences so ``json.loads`` accepts the payload."""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


async def _call_classifier_llm(prompt: str) -> str | None:
    """Single low-latency Gemini Flash call. Returns text or ``None`` on failure.

    Isolated as a module-level coroutine so unit tests can monkeypatch it
    with ``AsyncMock`` without reaching into ``google.genai``.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        logger.warning("google.genai not available; task_router LLM tier skipped")
        return None
    try:
        client = genai.Client()
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=CLASSIFIER_LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=256,
                ),
            ),
            timeout=CLASSIFIER_LLM_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "task_router LLM call timed out after %.1fs", CLASSIFIER_LLM_TIMEOUT_S
        )
        return None
    except Exception as exc:
        logger.warning("task_router LLM call failed: %s", exc)
        return None
    raw = (getattr(response, "text", None) or "").strip()
    return raw or None


def _build_classifier_prompt(text: str) -> str:
    """Compose the Flash prompt. Strict JSON contract simplifies parsing."""
    return (
        "Classify a user request as 'direct' (single fact/action, no plan needed) "
        "or 'initiative' (multi-step work requiring research, audit, and follow-up).\n\n"
        f"REQUEST: {text}\n\n"
        'Return ONLY JSON: {"mode":"direct"|"initiative","confidence":<0..1>,'
        '"reasoning":"<short>"}.'
    )


def _safe_default(reasoning: str) -> ClassifierResult:
    """Produce the safe-default (initiative, zero confidence) result.

    Used when the LLM is unavailable or returns garbage. Initiative is the
    *safe* fallback — it costs a research run, but it never drops a real
    initiative request on the floor.
    """
    return ClassifierResult(
        mode="initiative",
        confidence=0.0,
        reasoning=reasoning,
        signal="llm",
    )


async def _llm_classify(text: str) -> ClassifierResult:
    """Run the LLM fallback tier. Defaults to ``"initiative"`` on any failure."""
    raw = await _call_classifier_llm(_build_classifier_prompt(text))
    if not raw:
        return _safe_default("LLM unavailable; defaulted to initiative")
    try:
        parsed = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        return _safe_default("LLM output unparseable; defaulted to initiative")
    if not isinstance(parsed, dict):
        return _safe_default("LLM output not a JSON object; defaulted to initiative")

    mode_raw = str(parsed.get("mode", "")).strip().lower()
    if mode_raw not in ("direct", "initiative"):
        mode_raw = "initiative"
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    reasoning = str(parsed.get("reasoning", "") or "")[:240]
    return ClassifierResult(
        mode=mode_raw,  # type: ignore[arg-type]
        confidence=confidence,
        reasoning=reasoning,
        signal="llm",
    )


# ---------------------------------------------------------------------------
# Public waterfall (Task 70)
# ---------------------------------------------------------------------------


async def classify(
    request_text: str,
    *,
    ops: OperationsConfig,
    persona_policy: PersonaPolicy,
    session_has_open_contract: bool,
) -> ClassifierResult:
    """Three-tier waterfall classifier per spec § 9.

    Order:

      1. Explicit override (``/quick``, ``/q``, ``/plan``, ``/initiative``).
      2. Rule heuristics (verbs + length + open contract + ``@agent``).
      3. Persona default (``persona_policy.classifier_default_mode``).
      4. LLM fallback (with ops ``last_resort_default`` applied only when the
         LLM itself was unavailable / unparseable).

    Args:
        request_text: The raw user message.
        ops: Per-agent ``operations.yaml`` config — only ``ops.routing`` is
            consulted here, but the full config is passed for future
            extensions (e.g. ops-level overrides).
        persona_policy: Resolved per-(user, persona) policy. Its
            ``classifier_default_mode`` short-circuits the LLM tier.
        session_has_open_contract: ``True`` when the session already has an
            open ``TaskContract`` — forces initiative mode unless the user
            explicitly typed ``/quick``.

    Returns:
        :class:`ClassifierResult` whose ``signal`` records which tier
        produced the decision (``override``, ``rule``, ``persona_default``
        — surfaced via ``signal="rule"`` for spec compliance — or ``llm``).
    """
    # Tier 1: explicit override always wins.
    override = _detect_override(request_text)
    if override is not None:
        return ClassifierResult(
            mode=override,
            confidence=1.0,
            reasoning="explicit /quick or /plan prefix",
            signal="override",
        )

    # Tier 2: rule heuristics.
    rule = _apply_rules(
        request_text,
        session_has_open_contract=session_has_open_contract,
    )
    if rule is not None:
        return ClassifierResult(
            mode=rule,
            confidence=0.9,
            reasoning="rule heuristic match",
            signal="rule",
        )

    # Tier 3: persona default.
    persona_default = persona_policy.classifier_default_mode
    if persona_default in ("direct", "initiative"):
        return ClassifierResult(
            mode=persona_default,  # type: ignore[arg-type]
            confidence=0.5,
            reasoning=f"persona '{persona_policy.persona_id}' default",
            signal="persona_default",
        )

    # Tier 4: LLM fallback.
    result = await _llm_classify(request_text)
    # If the LLM was unavailable, honour ops.routing.last_resort_default so
    # cautious agents bias toward direct (cheap) while bold agents stay on
    # initiative (thorough). We *only* override on zero confidence so a
    # successful LLM verdict is respected.
    if result.confidence == 0.0 and ops.routing.last_resort_default in (
        "direct",
        "initiative",
    ):
        result = result.model_copy(
            update={
                "mode": ops.routing.last_resort_default,
                "reasoning": (
                    f"LLM unavailable; applied ops.routing.last_resort_default="
                    f"{ops.routing.last_resort_default}"
                ),
            }
        )
    return result


__all__ = [
    "CLASSIFIER_LLM_MODEL",
    "CLASSIFIER_LLM_TIMEOUT_S",
    "DIRECT_LENGTH_THRESHOLD",
    "DIRECT_VERBS",
    "INITIATIVE_VERBS",
    "_apply_rules",
    "_call_classifier_llm",
    "_detect_override",
    "_llm_classify",
    "classify",
]
