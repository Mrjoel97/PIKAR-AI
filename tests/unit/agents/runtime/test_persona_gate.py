# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for app.agents.runtime.persona_gate.

Covers W1+W2 plan tasks 60-65 (defaults, DB-first loader, allow/deny gate,
action-threshold gate, prompt-fragment renderer, violation recorder) plus
the wildcard regression in task 73.
"""

from __future__ import annotations

from typing import Literal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime import persona_gate
from app.agents.runtime.types import (
    ActionThresholds,
    PersonaPolicy,
    PersonaPolicyError,
    PolicyViolation,
    RateLimits,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _thresholds(
    *,
    max_spend_usd: float | None = None,
    require_approval_for_external_send: bool = False,
) -> ActionThresholds:
    return ActionThresholds(
        max_spend_usd=max_spend_usd,
        require_approval_for_external_send=require_approval_for_external_send,
        custom={},
    )


def _rate_limits() -> RateLimits:
    return RateLimits(requests_per_minute=None, tokens_per_day=None)


def _policy(
    *,
    persona_id: str = "test",
    allowed: list[str] | Literal["*"] = "*",
    denied: list[str] | None = None,
    thresholds: ActionThresholds | None = None,
    prompt_fragments: list[str] | None = None,
    classifier_default_mode=None,
) -> PersonaPolicy:
    return PersonaPolicy(
        persona_id=persona_id,
        allowed_tool_ids=allowed,
        denied_tool_ids=list(denied or []),
        action_thresholds=thresholds or _thresholds(),
        rate_limits=_rate_limits(),
        prompt_fragments=list(prompt_fragments or []),
        classifier_default_mode=classifier_default_mode,
        initiative_phases_blocked=[],
    )


def _stub_supabase_rows(rows: list[dict], monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Wire ``persona_gate._get_supabase`` to return a MagicMock client.

    The chain ``client.table(...).select(...).eq(...).limit(...).execute()``
    resolves to ``MagicMock(data=rows)``.
    """
    chain = MagicMock()
    chain.execute = AsyncMock(return_value=MagicMock(data=rows))
    chain.eq = MagicMock(return_value=chain)
    chain.select = MagicMock(return_value=chain)
    chain.limit = MagicMock(return_value=chain)
    client = MagicMock(table=MagicMock(return_value=chain))

    async def _fake_get_supabase():
        return client

    monkeypatch.setattr(persona_gate, "_get_supabase", _fake_get_supabase)
    return client


# ---------------------------------------------------------------------------
# Task 60: defaults loader
# ---------------------------------------------------------------------------


def test_defaults_for_solopreneur_returns_policy() -> None:
    policy = persona_gate._defaults_from_registry("solopreneur")
    assert isinstance(policy, PersonaPolicy)
    assert policy.persona_id == "solopreneur"
    assert policy.allowed_tool_ids == "*"
    assert policy.denied_tool_ids == []
    # Registry-derived fragments populate the policy block.
    assert policy.prompt_fragments
    assert any("summary" in frag.lower() for frag in policy.prompt_fragments)


def test_defaults_for_enterprise_includes_approval_posture() -> None:
    policy = persona_gate._defaults_from_registry("enterprise")
    assert policy.persona_id == "enterprise"
    assert any("approval posture" in frag.lower() for frag in policy.prompt_fragments)


def test_defaults_unknown_persona_returns_baseline() -> None:
    policy = persona_gate._defaults_from_registry("totally-unknown")
    assert isinstance(policy, PersonaPolicy)
    assert policy.persona_id == "totally-unknown"
    assert policy.allowed_tool_ids == "*"
    assert policy.denied_tool_ids == []
    assert policy.prompt_fragments == []  # no registry entry, no fragments


# ---------------------------------------------------------------------------
# Task 61: DB-first loader
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_persona_policy_uses_db_row(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_supabase_rows(
        [
            {
                "persona_id": "startup",
                "allowed_tool_ids": ["tool_a", "tool_b"],
                "denied_tool_ids": ["dangerous_tool"],
                "action_thresholds": {
                    "max_spend_usd": 500,
                    "require_approval_for_external_send": True,
                    "custom": {"note": "tight"},
                },
                "rate_limits": {"requests_per_minute": 30, "tokens_per_day": 1000},
                "prompt_fragments": ["Be scrappy"],
                "classifier_default_mode": "direct",
                "initiative_phases_blocked": ["scale"],
            }
        ],
        monkeypatch,
    )
    policy = await persona_gate.load_persona_policy(uuid4(), "startup")
    assert policy.persona_id == "startup"
    assert policy.allowed_tool_ids == ["tool_a", "tool_b"]
    assert "dangerous_tool" in policy.denied_tool_ids
    assert policy.action_thresholds.max_spend_usd == 500
    assert policy.action_thresholds.require_approval_for_external_send is True
    assert policy.rate_limits.requests_per_minute == 30
    assert policy.classifier_default_mode == "direct"
    assert "scale" in policy.initiative_phases_blocked
    assert policy.prompt_fragments == ["Be scrappy"]


@pytest.mark.asyncio
async def test_load_persona_policy_falls_back_to_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_supabase_rows([], monkeypatch)
    policy = await persona_gate.load_persona_policy(uuid4(), "solopreneur")
    assert policy.persona_id == "solopreneur"
    assert policy.allowed_tool_ids == "*"
    assert policy.prompt_fragments  # registry-derived fragments present


@pytest.mark.asyncio
async def test_load_persona_policy_recovers_from_db_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _explode():
        raise RuntimeError("supabase unavailable")

    monkeypatch.setattr(persona_gate, "_get_supabase", _explode)
    policy = await persona_gate.load_persona_policy(uuid4(), "enterprise")
    assert policy.persona_id == "enterprise"
    assert policy.allowed_tool_ids == "*"  # fell back to registry defaults
    assert policy.prompt_fragments  # registry fragments present


@pytest.mark.asyncio
async def test_load_persona_policy_recovers_from_invalid_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ``denied_tool_ids`` is the wrong shape and ``persona_id`` is missing.
    # The coercion path raises and we should fall through to registry.
    _stub_supabase_rows(
        [
            {
                # Force a validation failure by passing a clearly invalid
                # classifier_default_mode that Pydantic will reject.
                "persona_id": "solopreneur",
                "allowed_tool_ids": ["x"],
                "denied_tool_ids": [],
                "action_thresholds": {},
                "rate_limits": {},
                "prompt_fragments": [],
                "classifier_default_mode": "not-a-valid-mode",
                "initiative_phases_blocked": [],
            }
        ],
        monkeypatch,
    )
    policy = await persona_gate.load_persona_policy(uuid4(), "solopreneur")
    # Fell through to registry defaults (allowed_tool_ids back to "*").
    assert policy.allowed_tool_ids == "*"


# ---------------------------------------------------------------------------
# Task 62: tool allow / deny gate
# ---------------------------------------------------------------------------


def test_wildcard_allows_everything_not_denied() -> None:
    persona_gate.check_tool_allowed("any_tool", _policy(allowed="*"))


def test_wildcard_still_respects_deny() -> None:
    with pytest.raises(PersonaPolicyError) as exc:
        persona_gate.check_tool_allowed(
            "blocked_tool", _policy(allowed="*", denied=["blocked_tool"])
        )
    assert "denied" in str(exc.value).lower()


def test_allow_list_precedence_over_deny() -> None:
    # spec § 13: allow-list takes precedence over deny-list.
    persona_gate.check_tool_allowed(
        "tool_a", _policy(allowed=["tool_a"], denied=["tool_a"])
    )


def test_not_in_allow_list_denied() -> None:
    with pytest.raises(PersonaPolicyError) as exc:
        persona_gate.check_tool_allowed("tool_x", _policy(allowed=["tool_a"]))
    assert "allow-list" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Task 63: action threshold gate
# ---------------------------------------------------------------------------


def _threshold_policy() -> PersonaPolicy:
    return _policy(
        persona_id="solo",
        thresholds=_thresholds(
            max_spend_usd=500, require_approval_for_external_send=True
        ),
    )


@pytest.mark.asyncio
async def test_financial_under_threshold_passes() -> None:
    await persona_gate.check_action_threshold(
        "stripe_charge", {"amount_usd": 100}, _threshold_policy()
    )


@pytest.mark.asyncio
async def test_financial_above_threshold_requires_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        persona_gate,
        "_has_valid_approval_token",
        AsyncMock(return_value=False),
    )
    with pytest.raises(PersonaPolicyError) as exc:
        await persona_gate.check_action_threshold(
            "stripe_charge", {"amount_usd": 750}, _threshold_policy()
        )
    assert "spend cap" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_financial_above_threshold_with_valid_token_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        persona_gate,
        "_has_valid_approval_token",
        AsyncMock(return_value=True),
    )
    await persona_gate.check_action_threshold(
        "stripe_charge",
        {"amount_usd": 750, "approval_token": "abc"},
        _threshold_policy(),
    )


@pytest.mark.asyncio
async def test_external_send_requires_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        persona_gate,
        "_has_valid_approval_token",
        AsyncMock(return_value=False),
    )
    with pytest.raises(PersonaPolicyError) as exc:
        await persona_gate.check_action_threshold(
            "gmail_send", {"to": "x@y.com"}, _threshold_policy()
        )
    assert "approval" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_external_send_passes_with_valid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        persona_gate,
        "_has_valid_approval_token",
        AsyncMock(return_value=True),
    )
    await persona_gate.check_action_threshold(
        "gmail_send",
        {"to": "x@y.com", "approval_token": "ok"},
        _threshold_policy(),
    )


@pytest.mark.asyncio
async def test_non_threshold_tool_passes() -> None:
    await persona_gate.check_action_threshold(
        "list_calendar", {}, _threshold_policy()
    )


@pytest.mark.asyncio
async def test_financial_action_with_no_cap_passes() -> None:
    # max_spend_usd is None => no enforcement regardless of amount.
    policy = _policy(thresholds=_thresholds(max_spend_usd=None))
    await persona_gate.check_action_threshold(
        "stripe_charge", {"amount_usd": 10_000}, policy
    )


@pytest.mark.asyncio
async def test_external_send_without_approval_requirement_passes() -> None:
    policy = _policy(
        thresholds=_thresholds(require_approval_for_external_send=False),
    )
    await persona_gate.check_action_threshold(
        "gmail_send", {"to": "x@y.com"}, policy
    )


# ---------------------------------------------------------------------------
# Task 64: prompt fragments renderer
# ---------------------------------------------------------------------------


def test_apply_renders_markdown_block_with_each_fragment() -> None:
    block = persona_gate.apply_prompt_fragments(
        _policy(
            persona_id="enterprise",
            prompt_fragments=["Be governance-aware", "Lead with stakeholder map"],
        )
    )
    assert block.startswith("## Persona Policy (enterprise)")
    assert "- Be governance-aware" in block
    assert "- Lead with stakeholder map" in block


def test_apply_returns_empty_string_when_no_fragments() -> None:
    assert persona_gate.apply_prompt_fragments(_policy(prompt_fragments=[])) == ""


def test_apply_skips_empty_fragments() -> None:
    block = persona_gate.apply_prompt_fragments(
        _policy(prompt_fragments=["", "real fragment", ""])
    )
    assert "- real fragment" in block
    # No bullet rendered for the empties.
    assert block.count("\n- ") == 1


def test_apply_is_deterministic() -> None:
    policy = _policy(prompt_fragments=["a", "b", "c"])
    assert persona_gate.apply_prompt_fragments(
        policy
    ) == persona_gate.apply_prompt_fragments(policy)


# ---------------------------------------------------------------------------
# Task 65: violation recorder
# ---------------------------------------------------------------------------


def test_record_violation_appends_to_list() -> None:
    violations: list[PolicyViolation] = []
    persona_gate.record_violation(
        violations, kind="tool_denied", detail="tool X is denied", tool_id="X"
    )
    assert len(violations) == 1
    assert violations[0].kind == "tool_denied"
    assert violations[0].tool_id == "X"
    assert violations[0].detail == "tool X is denied"


def test_record_violation_supports_no_tool_id() -> None:
    violations: list[PolicyViolation] = []
    persona_gate.record_violation(
        violations, kind="threshold_exceeded", detail="too much"
    )
    assert violations[0].tool_id is None
    assert violations[0].kind == "threshold_exceeded"


def test_record_violation_appends_multiple_entries() -> None:
    violations: list[PolicyViolation] = []
    persona_gate.record_violation(
        violations, kind="tool_denied", detail="x denied", tool_id="x"
    )
    persona_gate.record_violation(
        violations, kind="rate_limited", detail="slow down"
    )
    assert [v.kind for v in violations] == ["tool_denied", "rate_limited"]


# ---------------------------------------------------------------------------
# Task 73: wildcard regression
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_id",
    [
        "calendar_list",
        "vault_search",
        "video_render",
        "image_generate",
        "sheet_read",
        # Specifically NOT a financial / external-send keyword so it doesn't
        # collide with the threshold gate.
        "weird_custom_internal_tool",
    ],
)
def test_wildcard_with_empty_deny_permits(tool_id: str) -> None:
    policy = _policy(persona_id="solopreneur", allowed="*", denied=[])
    persona_gate.check_tool_allowed(tool_id, policy)
