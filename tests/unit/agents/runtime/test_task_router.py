# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for ``app.agents.runtime.task_router``.

Consolidates Tasks 66, 67, 68, 69, 70, and 74 from the agent operating
model W1+W2 plan into a single test module covering:

  * Constants — DIRECT_VERBS, INITIATIVE_VERBS, DIRECT_LENGTH_THRESHOLD.
  * ``_detect_override`` — slash prefix recognition with case + whitespace
    tolerance.
  * ``_apply_rules`` — verb + length + open-contract heuristics, plus
    ``@agent`` handoff and explicit initiative id.
  * ``_llm_classify`` — Gemini Flash fallback parsing, safe defaults on
    failure / garbage / unavailable LLM.
  * ``classify`` — three-tier waterfall (override -> rule -> persona
    default -> LLM).
  * Integration — ``@agent`` plus open contract, override beats open
    contract, etc.

The LLM client is mocked throughout (``_call_classifier_llm`` is a
module-level coroutine wrapping ``google.genai`` so the patch surface
is small).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.runtime import task_router
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    ActionThresholds,
    ClassifierResult,
    PersonaPolicy,
    RateLimits,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_policy(
    *,
    persona_id: str = "solo",
    default_mode: str | None = None,
) -> PersonaPolicy:
    """Build a minimal ``PersonaPolicy`` for classifier tests."""
    return PersonaPolicy(
        persona_id=persona_id,
        allowed_tool_ids="*",
        denied_tool_ids=[],
        action_thresholds=ActionThresholds(
            max_spend_usd=None,
            require_approval_for_external_send=False,
            custom={},
        ),
        rate_limits=RateLimits(
            requests_per_minute=None,
            tokens_per_day=None,
        ),
        prompt_fragments=[],
        classifier_default_mode=default_mode,  # type: ignore[arg-type]
        initiative_phases_blocked=[],
    )


@pytest.fixture
def ops() -> OperationsConfig:
    """Default ops config for an arbitrary agent."""
    return OperationsConfig.defaults(agent_id="executive")


@pytest.fixture
def empty_policy() -> PersonaPolicy:
    """Persona policy with no default mode — forces LLM fallback when rules don't fire."""
    return _make_policy()


# ---------------------------------------------------------------------------
# Task 66 — constants
# ---------------------------------------------------------------------------


class TestConstants:
    """DIRECT_VERBS / INITIATIVE_VERBS / DIRECT_LENGTH_THRESHOLD per spec § 9."""

    def test_direct_verbs_includes_factual_signals(self) -> None:
        for verb in (
            "what",
            "when",
            "who",
            "where",
            "show",
            "list",
            "find",
            "summarize",
        ):
            assert verb in task_router.DIRECT_VERBS, (
                f"DIRECT_VERBS missing factual signal {verb!r}"
            )

    def test_initiative_verbs_includes_planning_signals(self) -> None:
        for verb in ("plan", "build", "launch", "develop", "orchestrate", "migrate"):
            assert verb in task_router.INITIATIVE_VERBS, (
                f"INITIATIVE_VERBS missing planning signal {verb!r}"
            )

    def test_run_a_campaign_phrase_present(self) -> None:
        # Spec lists "run a campaign" verbatim as an initiative signal.
        assert "run a campaign" in task_router.INITIATIVE_VERBS

    def test_direct_length_threshold_is_80(self) -> None:
        assert task_router.DIRECT_LENGTH_THRESHOLD == 80

    def test_verb_sets_are_immutable_frozensets(self) -> None:
        assert isinstance(task_router.DIRECT_VERBS, frozenset)
        assert isinstance(task_router.INITIATIVE_VERBS, frozenset)


# ---------------------------------------------------------------------------
# Task 67 — _detect_override
# ---------------------------------------------------------------------------


class TestDetectOverride:
    """Slash-prefix override detection."""

    def test_quick_returns_direct(self) -> None:
        assert task_router._detect_override("/quick what is x") == "direct"

    def test_q_shorthand_returns_direct(self) -> None:
        assert task_router._detect_override("/q what is x") == "direct"

    def test_plan_returns_initiative(self) -> None:
        assert (
            task_router._detect_override("/plan launch the new product") == "initiative"
        )

    def test_initiative_long_form_returns_initiative(self) -> None:
        assert (
            task_router._detect_override("/initiative build the thing") == "initiative"
        )

    def test_override_is_case_insensitive(self) -> None:
        assert task_router._detect_override("/QUICK something") == "direct"
        assert task_router._detect_override("  /Plan  build foo") == "initiative"

    def test_leading_whitespace_is_tolerated(self) -> None:
        assert task_router._detect_override("   /quick foo") == "direct"
        assert task_router._detect_override("\t/plan foo") == "initiative"

    def test_no_override_returns_none(self) -> None:
        assert task_router._detect_override("plan the launch") is None
        assert task_router._detect_override("what is q3 revenue") is None

    def test_empty_or_none_input_returns_none(self) -> None:
        assert task_router._detect_override("") is None
        assert task_router._detect_override("   ") is None

    def test_q_in_middle_of_word_is_not_override(self) -> None:
        # "/query" should not be treated as the /q override.
        assert task_router._detect_override("/query something") is None


# ---------------------------------------------------------------------------
# Task 68 — _apply_rules
# ---------------------------------------------------------------------------


class TestApplyRules:
    """Verb + length + open-contract heuristics."""

    def test_open_contract_forces_initiative(self) -> None:
        # Even a short factual question becomes initiative when a contract is open.
        assert (
            task_router._apply_rules("what is x", session_has_open_contract=True)
            == "initiative"
        )

    def test_short_factual_question_is_direct(self) -> None:
        assert (
            task_router._apply_rules(
                "what is our Q3 revenue?",
                session_has_open_contract=False,
            )
            == "direct"
        )

    def test_show_me_short_is_direct(self) -> None:
        assert (
            task_router._apply_rules(
                "show me the latest deal",
                session_has_open_contract=False,
            )
            == "direct"
        )

    def test_long_factual_question_falls_through(self) -> None:
        # Length >= threshold => no direct shortcut, falls through to None.
        long_text = (
            "what is the breakdown of our customer retention curve across cohorts "
            "by region and product line over the past year"
        )
        assert len(long_text) >= task_router.DIRECT_LENGTH_THRESHOLD
        assert (
            task_router._apply_rules(long_text, session_has_open_contract=False) is None
        )

    def test_initiative_verb_overrides_short_length(self) -> None:
        assert (
            task_router._apply_rules(
                "plan the launch",
                session_has_open_contract=False,
            )
            == "initiative"
        )

    def test_build_verb_is_initiative(self) -> None:
        assert (
            task_router._apply_rules(
                "build a churn prediction dashboard",
                session_has_open_contract=False,
            )
            == "initiative"
        )

    def test_run_a_campaign_phrase_is_initiative(self) -> None:
        assert (
            task_router._apply_rules(
                "run a campaign for Q4 launch",
                session_has_open_contract=False,
            )
            == "initiative"
        )

    def test_at_mention_handoff_is_initiative(self) -> None:
        assert (
            task_router._apply_rules(
                "@marketing kick off the holiday campaign please",
                session_has_open_contract=False,
            )
            == "initiative"
        )

    def test_at_mention_after_text_still_triggers_initiative(self) -> None:
        assert (
            task_router._apply_rules(
                "hand this off to @sales now",
                session_has_open_contract=False,
            )
            == "initiative"
        )

    def test_initiative_id_phrase_is_initiative(self) -> None:
        assert (
            task_router._apply_rules(
                "continue on initiative_id 12345",
                session_has_open_contract=False,
            )
            == "initiative"
        )

    def test_plant_word_does_not_trigger_plan_verb(self) -> None:
        # Word-boundary match: "plant" should not be classified as "plan".
        result = task_router._apply_rules(
            "describe the office plant in detail and what kind of fertilizer it needs",
            session_has_open_contract=False,
        )
        assert result != "initiative"

    def test_ambiguous_returns_none(self) -> None:
        assert (
            task_router._apply_rules(
                "tell me something about our customers and how they feel about our new product line",
                session_has_open_contract=False,
            )
            is None
        )

    def test_empty_text_returns_none(self) -> None:
        assert task_router._apply_rules("", session_has_open_contract=False) is None
        assert task_router._apply_rules("   ", session_has_open_contract=False) is None


# ---------------------------------------------------------------------------
# Task 69 — _llm_classify
# ---------------------------------------------------------------------------


class TestLLMClassify:
    """Gemini Flash fallback parsing — heavily mocked."""

    @pytest.mark.asyncio
    async def test_llm_classify_returns_mode_and_confidence(self, monkeypatch) -> None:
        monkeypatch.setattr(
            task_router,
            "_call_classifier_llm",
            AsyncMock(
                return_value='{"mode":"initiative","confidence":0.82,"reasoning":"multi-step plan"}'
            ),
        )
        result = await task_router._llm_classify(
            "design the Q4 launch program for the EMEA region"
        )
        assert result.mode == "initiative"
        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence == pytest.approx(0.82)
        assert "multi-step" in (result.reasoning or "")
        assert result.signal == "llm"

    @pytest.mark.asyncio
    async def test_llm_classify_handles_direct_verdict(self, monkeypatch) -> None:
        monkeypatch.setattr(
            task_router,
            "_call_classifier_llm",
            AsyncMock(
                return_value='{"mode":"direct","confidence":0.7,"reasoning":"single fact"}'
            ),
        )
        result = await task_router._llm_classify("what's the deal value")
        assert result.mode == "direct"
        assert result.signal == "llm"

    @pytest.mark.asyncio
    async def test_llm_classify_strips_code_fence(self, monkeypatch) -> None:
        # Some Gemini responses wrap JSON in ```json ... ``` fences.
        monkeypatch.setattr(
            task_router,
            "_call_classifier_llm",
            AsyncMock(
                return_value='```json\n{"mode":"initiative","confidence":0.9,"reasoning":"r"}\n```'
            ),
        )
        result = await task_router._llm_classify("ambiguous request")
        assert result.mode == "initiative"
        assert result.confidence == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_llm_classify_defaults_to_initiative_on_unparseable(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            task_router, "_call_classifier_llm", AsyncMock(return_value="garbage")
        )
        result = await task_router._llm_classify("ambiguous text here")
        assert result.mode == "initiative"  # safe default
        assert result.confidence == 0.0
        assert result.signal == "llm"

    @pytest.mark.asyncio
    async def test_llm_classify_defaults_when_llm_unavailable(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            task_router, "_call_classifier_llm", AsyncMock(return_value=None)
        )
        result = await task_router._llm_classify("ambiguous text here")
        assert result.mode == "initiative"
        assert result.signal == "llm"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_classify_clamps_out_of_range_confidence(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            task_router,
            "_call_classifier_llm",
            AsyncMock(
                return_value='{"mode":"direct","confidence":2.5,"reasoning":"hi"}'
            ),
        )
        result = await task_router._llm_classify("foo")
        assert result.confidence == 1.0  # clamped to [0, 1]

    @pytest.mark.asyncio
    async def test_llm_classify_unknown_mode_defaults_to_initiative(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            task_router,
            "_call_classifier_llm",
            AsyncMock(
                return_value='{"mode":"chitchat","confidence":0.5,"reasoning":"x"}'
            ),
        )
        result = await task_router._llm_classify("foo")
        assert result.mode == "initiative"

    @pytest.mark.asyncio
    async def test_llm_classify_handles_non_dict_payload(self, monkeypatch) -> None:
        monkeypatch.setattr(
            task_router,
            "_call_classifier_llm",
            AsyncMock(return_value='["not", "an", "object"]'),
        )
        result = await task_router._llm_classify("foo")
        assert result.mode == "initiative"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Task 70 — classify waterfall
# ---------------------------------------------------------------------------


class TestClassifyWaterfall:
    """Three-tier waterfall: override -> rule -> persona default -> LLM."""

    @pytest.mark.asyncio
    async def test_override_takes_first_precedence(self, ops: OperationsConfig) -> None:
        # Persona default + open contract would both push to initiative; override wins.
        result = await task_router.classify(
            "/quick what is q3 revenue",
            ops=ops,
            persona_policy=_make_policy(default_mode="initiative"),
            session_has_open_contract=True,
        )
        assert result.mode == "direct"
        assert result.signal == "override"
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_rule_used_when_no_override(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy
    ) -> None:
        result = await task_router.classify(
            "plan the launch",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=False,
        )
        assert result.mode == "initiative"
        assert result.signal == "rule"

    @pytest.mark.asyncio
    async def test_rule_short_factual_is_direct(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy
    ) -> None:
        result = await task_router.classify(
            "what is our Q3 revenue?",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=False,
        )
        assert result.mode == "direct"
        assert result.signal == "rule"

    @pytest.mark.asyncio
    async def test_persona_default_used_before_llm(
        self, ops: OperationsConfig, monkeypatch
    ) -> None:
        fake_llm = AsyncMock()
        monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
        result = await task_router.classify(
            "tell me something nuanced about retention and our customer mix over the last year",
            ops=ops,
            persona_policy=_make_policy(default_mode="direct"),
            session_has_open_contract=False,
        )
        assert result.mode == "direct"
        assert result.signal == "persona_default"
        fake_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_llm_used_when_all_else_inconclusive(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            task_router,
            "_llm_classify",
            AsyncMock(
                return_value=ClassifierResult(
                    mode="initiative",
                    confidence=0.6,
                    reasoning="amb",
                    signal="llm",
                )
            ),
        )
        result = await task_router.classify(
            "tell me something nuanced about retention and our customer mix over the last year",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=False,
        )
        assert result.signal == "llm"
        assert result.mode == "initiative"

    @pytest.mark.asyncio
    async def test_ops_last_resort_applied_when_llm_returns_zero_confidence(
        self, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        # ops.routing.last_resort_default defaults to "direct".
        ops = OperationsConfig.defaults(agent_id="executive")
        assert ops.routing.last_resort_default == "direct"
        monkeypatch.setattr(
            task_router,
            "_llm_classify",
            AsyncMock(
                return_value=ClassifierResult(
                    mode="initiative",
                    confidence=0.0,  # LLM unavailable -> safe default
                    reasoning="unavailable",
                    signal="llm",
                )
            ),
        )
        result = await task_router.classify(
            "tell me something nuanced about retention and our customer mix over the last year",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=False,
        )
        # ops bias rescues the unavailable LLM tier.
        assert result.mode == "direct"
        assert result.signal == "llm"

    @pytest.mark.asyncio
    async def test_ops_last_resort_does_not_clobber_confident_llm(
        self, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        ops = OperationsConfig.defaults(agent_id="executive")
        monkeypatch.setattr(
            task_router,
            "_llm_classify",
            AsyncMock(
                return_value=ClassifierResult(
                    mode="initiative",
                    confidence=0.8,
                    reasoning="confident",
                    signal="llm",
                )
            ),
        )
        result = await task_router.classify(
            "tell me something nuanced about retention and our customer mix over the last year",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=False,
        )
        # Confident LLM is respected, ops bias does NOT override.
        assert result.mode == "initiative"
        assert result.confidence == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Task 74 — integration: @agent + open contract + override interactions
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end coverage of spec § 9 invariants."""

    @pytest.mark.asyncio
    async def test_quick_override_beats_open_contract(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        fake_llm = AsyncMock()
        monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
        result = await task_router.classify(
            "/quick what's the current MRR",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=True,
        )
        assert result.mode == "direct"
        assert result.signal == "override"
        fake_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_at_agent_overrides_persona_default(
        self, ops: OperationsConfig, monkeypatch
    ) -> None:
        fake_llm = AsyncMock()
        monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
        result = await task_router.classify(
            "@marketing kick off the spring campaign",
            ops=ops,
            persona_policy=_make_policy(default_mode="direct"),
            session_has_open_contract=False,
        )
        assert result.signal == "rule"
        assert result.mode == "initiative"
        fake_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_open_contract_short_question_is_initiative(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        fake_llm = AsyncMock()
        monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
        result = await task_router.classify(
            "what is x?",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=True,
        )
        assert result.mode == "initiative"
        assert result.signal == "rule"
        fake_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_plan_override_with_open_contract_remains_initiative(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        # /plan is redundant when contract already open, but should still resolve
        # cleanly to initiative via the override signal.
        fake_llm = AsyncMock()
        monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
        result = await task_router.classify(
            "/plan add Q5 forecast cells",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=True,
        )
        assert result.mode == "initiative"
        assert result.signal == "override"
        fake_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_at_agent_with_open_contract_uses_rule_tier(
        self, ops: OperationsConfig, empty_policy: PersonaPolicy, monkeypatch
    ) -> None:
        # Both rules push to initiative; rule tier wins (no LLM call).
        fake_llm = AsyncMock()
        monkeypatch.setattr(task_router, "_llm_classify", fake_llm)
        result = await task_router.classify(
            "@finance handle this",
            ops=ops,
            persona_policy=empty_policy,
            session_has_open_contract=True,
        )
        assert result.mode == "initiative"
        assert result.signal == "rule"
        fake_llm.assert_not_awaited()
