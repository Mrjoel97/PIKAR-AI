# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Persona policy enforcement per spec § 13.

This module is the runtime gate for persona-scoped policy decisions. It is
called from ``PikarBaseAgent.before_tool_callback`` (and indirectly from
``task_router`` for the classifier default mode).

Public surface (covers W1+W2 plan tasks 60-65 and the wildcard regression
in task 73):

* :func:`load_persona_policy` - DB-first lookup against ``persona_policies``;
  falls back to defaults derived from :mod:`app.personas.policy_registry`
  when no row exists or the row fails Pydantic validation.
* :func:`check_tool_allowed` - allow-list takes precedence over deny-list
  (spec § 13); wildcard allow-list still respects deny-list.
* :func:`check_action_threshold` - gates ``financial_action`` and
  ``external_send`` tool kinds; consumes an approval token when present.
* :func:`apply_prompt_fragments` - renders the per-persona policy fragments
  as a deterministic markdown block.
* :func:`record_violation` - appends a :class:`PolicyViolation` to the
  audit report's ``policy_violations`` list so enforcement is visible.

The module intentionally avoids importing heavy runtime modules at top level
(``app.services.confirmation_tokens``, the Supabase client) so unit tests
can patch the indirection helpers with synchronous mocks.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.runtime.types import (
    ActionThresholds,
    PersonaPolicy,
    PersonaPolicyError,
    PolicyViolation,
    RateLimits,
)
from app.personas.policy_registry import get_persona_policy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults loader (Task 60)
# ---------------------------------------------------------------------------


def _default_action_thresholds() -> ActionThresholds:
    """Return ActionThresholds with every field populated.

    The Pydantic model declares each field as required, so we centralize
    the "permissive defaults" baseline here.
    """
    return ActionThresholds(
        max_spend_usd=None,
        require_approval_for_external_send=False,
        custom={},
    )


def _default_rate_limits() -> RateLimits:
    """Return RateLimits with every field populated (None = unlimited)."""
    return RateLimits(
        requests_per_minute=None,
        tokens_per_day=None,
    )


def _defaults_from_registry(persona_id: str) -> PersonaPolicy:
    """Build a :class:`PersonaPolicy` from the legacy policy_registry.

    When the persona is not known to the registry we still return a valid
    PersonaPolicy so callers never have to special-case ``None``.
    """
    registry_policy = get_persona_policy(persona_id)
    fragments: list[str] = []
    if registry_policy is not None:
        # Surface the legacy fragment content so the existing
        # ``build_persona_policy_block`` payload still flows in.
        fragments = [
            f"Persona summary: {registry_policy.summary}",
            f"Approval posture: {registry_policy.approval_posture}",
            f"Output contract: {registry_policy.output_contract}",
        ]
    return PersonaPolicy(
        persona_id=persona_id,
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=_default_action_thresholds(),
        rate_limits=_default_rate_limits(),
        prompt_fragments=fragments,
        classifier_default_mode=None,
        initiative_phases_blocked=[],
    )


# ---------------------------------------------------------------------------
# DB-first loader (Task 61)
# ---------------------------------------------------------------------------


async def _get_supabase() -> Any:
    """Indirection so tests can patch the Supabase client with a MagicMock.

    Returns the async service-role client. Imported lazily to avoid
    triggering Supabase initialization at module import time.
    """
    from app.services.supabase_client import get_async_client

    return await get_async_client()


def _coerce_policy_row(row: dict) -> PersonaPolicy:
    """Coerce a raw persona_policies row into a PersonaPolicy.

    JSONB columns arrive as plain dicts / lists. We fill in default sub-
    models when the row leaves a column empty, since the Pydantic types
    have required fields.
    """
    thresholds_raw = row.get("action_thresholds") or {}
    rate_limits_raw = row.get("rate_limits") or {}

    if isinstance(thresholds_raw, ActionThresholds):
        thresholds = thresholds_raw
    else:
        thresholds = ActionThresholds(
            max_spend_usd=thresholds_raw.get("max_spend_usd"),
            require_approval_for_external_send=bool(
                thresholds_raw.get("require_approval_for_external_send", False)
            ),
            custom=dict(thresholds_raw.get("custom") or {}),
        )

    if isinstance(rate_limits_raw, RateLimits):
        limits = rate_limits_raw
    else:
        limits = RateLimits(
            requests_per_minute=rate_limits_raw.get("requests_per_minute"),
            tokens_per_day=rate_limits_raw.get("tokens_per_day"),
        )

    allowed = row.get("allowed_tool_ids", "*")
    # Postgres stores the literal string "*" as a JSONB scalar; tolerate both.
    if isinstance(allowed, str) and allowed != "*":
        allowed = [allowed]

    return PersonaPolicy(
        persona_id=row.get("persona_id", ""),
        allowed_tool_ids=allowed,
        denied_tool_ids=list(row.get("denied_tool_ids") or []),
        action_thresholds=thresholds,
        rate_limits=limits,
        prompt_fragments=list(row.get("prompt_fragments") or []),
        classifier_default_mode=row.get("classifier_default_mode"),
        initiative_phases_blocked=list(row.get("initiative_phases_blocked") or []),
    )


async def load_persona_policy(user_id: UUID, persona_id: str) -> PersonaPolicy:
    """Load policy from ``persona_policies``; fall back to registry defaults.

    The ``user_id`` is accepted for forward compatibility (per-user policy
    overrides) and is currently unused by the lookup. When the table query
    fails or returns nothing, the policy is reconstructed from
    :mod:`app.personas.policy_registry`.
    """
    del user_id  # reserved for future per-user overrides
    rows: list[dict] = []
    try:
        client = await _get_supabase()
        response = (
            await client.table("persona_policies")
            .select(
                "persona_id, allowed_tool_ids, denied_tool_ids, action_thresholds, "
                "rate_limits, prompt_fragments, classifier_default_mode, "
                "initiative_phases_blocked"
            )
            .eq("persona_id", persona_id)
            .limit(1)
            .execute()
        )
        rows = list(getattr(response, "data", None) or [])
    except Exception as exc:
        logger.warning(
            "persona_policies fetch failed for persona %s: %s — using registry defaults",
            persona_id,
            exc,
        )
        rows = []

    if not rows:
        return _defaults_from_registry(persona_id)

    try:
        return _coerce_policy_row(rows[0])
    except Exception as exc:
        logger.warning(
            "persona_policies row for %s failed validation: %s — using registry defaults",
            persona_id,
            exc,
        )
        return _defaults_from_registry(persona_id)


# ---------------------------------------------------------------------------
# Tool allow / deny gate (Tasks 62, 73)
# ---------------------------------------------------------------------------


def check_tool_allowed(tool_id: str, policy: PersonaPolicy) -> None:
    """Raise :class:`PersonaPolicyError` if ``tool_id`` is not allowed.

    Spec § 13 precedence rules:

    * Explicit allow-list wins over deny-list. If ``tool_id`` appears in
      ``policy.allowed_tool_ids`` (when that is a list), the call proceeds
      even if the same id appears in ``denied_tool_ids``.
    * Wildcard allow (``"*"``) defers to ``denied_tool_ids`` only.
    * Anything else is denied.
    """
    allowed = policy.allowed_tool_ids
    denied = set(policy.denied_tool_ids or [])

    if isinstance(allowed, list):
        if tool_id in allowed:
            return  # explicit allow wins over deny
        raise PersonaPolicyError(
            f"tool '{tool_id}' is not in persona allow-list for '{policy.persona_id}'"
        )

    # allowed == "*" — wildcard, deny-list still applies.
    if tool_id in denied:
        raise PersonaPolicyError(
            f"tool '{tool_id}' is denied by persona '{policy.persona_id}'"
        )


# ---------------------------------------------------------------------------
# Action threshold gate (Task 63)
# ---------------------------------------------------------------------------


_FINANCIAL_TOOL_KEYWORDS: tuple[str, ...] = (
    "stripe",
    "charge",
    "refund",
    "payout",
    "transfer",
    "spend",
)

_EXTERNAL_SEND_TOOL_KEYWORDS: tuple[str, ...] = (
    "gmail_send",
    "send_email",
    "slack_post",
    "sms_send",
    "outbound",
)


def _action_kind(tool_id: str) -> str | None:
    """Classify ``tool_id`` into ``financial_action`` / ``external_send`` / None.

    The classification is conservative — only ids that match one of the
    keyword lists trigger the threshold gate. Everything else falls back
    to allow/deny enforcement.
    """
    if not tool_id:
        return None
    tid = tool_id.lower()
    if any(k in tid for k in _FINANCIAL_TOOL_KEYWORDS):
        return "financial_action"
    if any(k in tid for k in _EXTERNAL_SEND_TOOL_KEYWORDS):
        return "external_send"
    return None


async def _has_valid_approval_token(token: str | None) -> bool:
    """Return True iff ``token`` can be consumed as a confirmation token."""
    if not token:
        return False
    try:
        from app.services.confirmation_tokens import consume_confirmation_token
    except ImportError:
        return False
    try:
        payload = await consume_confirmation_token(token)
    except Exception:
        return False
    return payload is not None


async def check_action_threshold(
    tool_id: str,
    tool_args: dict,
    policy: PersonaPolicy,
) -> None:
    """Raise :class:`PersonaPolicyError` when an action exceeds policy caps.

    Two action kinds are gated:

    * ``financial_action`` — when ``policy.action_thresholds.max_spend_usd``
      is set and ``tool_args["amount_usd"]`` (or ``amount``) exceeds it.
    * ``external_send`` — when
      ``policy.action_thresholds.require_approval_for_external_send`` is
      True.

    Both gates pass when ``tool_args["approval_token"]`` is a valid
    confirmation token.
    """
    kind = _action_kind(tool_id)
    if kind is None:
        return

    thresholds = policy.action_thresholds
    args = tool_args if isinstance(tool_args, dict) else {}
    token = args.get("approval_token")

    if kind == "financial_action":
        cap = thresholds.max_spend_usd
        try:
            amount = float(args.get("amount_usd") or args.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if cap is not None and amount > cap:
            if not await _has_valid_approval_token(token):
                raise PersonaPolicyError(
                    f"action '{tool_id}' (${amount}) exceeds spend cap "
                    f"${cap} for persona '{policy.persona_id}' and no "
                    f"valid approval token is present"
                )
        return

    # kind == "external_send"
    if thresholds.require_approval_for_external_send:
        if not await _has_valid_approval_token(token):
            raise PersonaPolicyError(
                f"action '{tool_id}' requires approval for persona "
                f"'{policy.persona_id}' (no valid approval token present)"
            )


# ---------------------------------------------------------------------------
# Prompt fragments (Task 64)
# ---------------------------------------------------------------------------


def apply_prompt_fragments(policy: PersonaPolicy) -> str:
    """Render the persona's prompt fragments as a deterministic markdown block.

    Returns the empty string when the policy carries no fragments so the
    caller can safely concatenate the result without conditional checks.
    """
    fragments = [f for f in (policy.prompt_fragments or []) if f]
    if not fragments:
        return ""
    lines: list[str] = [f"## Persona Policy ({policy.persona_id})"]
    lines.extend(f"- {f}" for f in fragments)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Violation recorder (Task 65)
# ---------------------------------------------------------------------------


def record_violation(
    audit_violations: list[PolicyViolation],
    kind: str,
    detail: str,
    tool_id: str | None = None,
) -> None:
    """Append a :class:`PolicyViolation` to the audit list.

    ``kind`` must be one of the literals declared on :class:`PolicyViolation`
    (``"tool_denied"``, ``"threshold_exceeded"``, ``"rate_limited"``).
    Pydantic raises if it isn't, surfacing the typo at the caller site.
    """
    audit_violations.append(
        PolicyViolation(kind=kind, detail=detail, tool_id=tool_id)  # type: ignore[arg-type]
    )


__all__ = [
    "apply_prompt_fragments",
    "check_action_threshold",
    "check_tool_allowed",
    "load_persona_policy",
    "record_violation",
]
