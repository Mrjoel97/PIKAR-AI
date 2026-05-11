# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for ``app.agents.runtime.skill_injection``.

Covers Tasks 22, 23, 24, 39, and 44 of the agent operating model
W1+W2 plan:

- Task 22 - module skeleton + ``_render_section`` markdown formatting
- Task 23 - ``match_and_inject`` filter chain (floor / agent / allowed_ids)
- Task 24 - ``_matches_any`` glob semantics for ``ops.skills.allowed_ids``
- Task 39 - ``build_consult_applicable_skills_tool`` mid-turn tool factory
- Task 44 - direct-mode exclusion via ``skip_direct_mode`` flag/kwarg
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the google.adk + google.genai surface so importing modules that
# reference ADK types does not require the real SDK during unit tests.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.adk.tools.tool_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())

from app.skills.registry import AgentID, Skill  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _agent_mock(
    *,
    allowed: list[str] | None = None,
    top_k: int = 5,
    floor: float = 0.65,
    agent_id: AgentID = AgentID.FIN,
    skip_direct_mode: bool = False,
) -> MagicMock:
    """Build a mock agent exposing the surface ``match_and_inject`` reads."""
    a = MagicMock()
    a.agent_id = agent_id
    a.user_id = None
    a.persona_id = "founder"
    a.ops.skills.allowed_ids = list(allowed) if allowed is not None else ["*"]
    a.ops.skills.injection.top_k = top_k
    a.ops.skills.injection.similarity_floor = floor
    a.ops.skills.injection.skip_direct_mode = skip_direct_mode
    return a


def _skill(
    name: str,
    *,
    agent_ids: list[AgentID] | None = None,
    description: str | None = None,
    knowledge_summary: str | None = None,
    category: str = "finance",
) -> Skill:
    return Skill(
        name=name,
        description=description or f"{name} description",
        category=category,
        agent_ids=agent_ids or [],
        knowledge_summary=knowledge_summary,
    )


def _request(text: str) -> MagicMock:
    """A duck-typed contract/request — supports both ``goal`` and ``message``."""
    r = MagicMock()
    r.goal = text
    r.message = text
    return r


# ===========================================================================
# Task 22 - render helper & SkillMatch dataclass
# ===========================================================================


def test_render_section_with_skills_includes_score_name_and_summary():
    from app.agents.runtime.skill_injection import SkillMatch, _render_section

    matches = [
        SkillMatch(
            score=0.91,
            skill=_skill(
                "financial_modeling",
                description="DCF, NPV, IRR modeling",
                knowledge_summary="Use 5-year horizon; sensitivity on WACC.",
            ),
        ),
        SkillMatch(
            score=0.74,
            skill=_skill(
                "variance_analysis",
                description="Budget vs actuals investigation",
                knowledge_summary="Decompose price/volume/mix.",
            ),
        ),
    ]
    out = _render_section(matches)
    assert "## Relevant skills" in out
    assert "financial_modeling" in out
    assert "variance_analysis" in out
    assert "0.91" in out
    assert "0.74" in out
    assert "DCF, NPV, IRR modeling" in out
    assert "Use 5-year horizon" in out


def test_render_section_empty_returns_empty_string():
    from app.agents.runtime.skill_injection import _render_section

    assert _render_section([]) == ""


def test_render_section_omits_summary_when_equal_to_description():
    from app.agents.runtime.skill_injection import SkillMatch, _render_section

    s = _skill(
        "duplicate",
        description="Same text",
        knowledge_summary="Same text",
    )
    out = _render_section([SkillMatch(score=0.8, skill=s)])
    # Should appear exactly once; we don't want it duplicated as bullet sub-line.
    assert out.count("Same text") == 1


def test_skill_match_dataclass_holds_score_and_skill():
    from app.agents.runtime.skill_injection import SkillMatch

    s = _skill("x")
    m = SkillMatch(score=0.5, skill=s)
    assert m.score == 0.5
    assert m.skill is s


# ===========================================================================
# Task 24 - ``_matches_any`` glob semantics
# ===========================================================================


def test_matches_any_wildcard_matches_anything():
    from app.agents.runtime.skill_injection import _matches_any

    assert _matches_any("anything", ["*"])
    assert _matches_any("finance:dcf", ["*"])


def test_matches_any_prefix_glob_finance_star():
    from app.agents.runtime.skill_injection import _matches_any

    assert _matches_any("finance:dcf", ["finance:*"])
    assert _matches_any("finance:variance", ["finance:*"])
    assert not _matches_any("hr:bonus", ["finance:*"])


def test_matches_any_exact_match_in_list():
    from app.agents.runtime.skill_injection import _matches_any

    assert _matches_any(
        "compliance:legal-risk-assessment",
        ["compliance:legal-risk-assessment"],
    )
    assert not _matches_any(
        "compliance:other", ["compliance:legal-risk-assessment"]
    )


def test_matches_any_empty_patterns_denies_everything():
    from app.agents.runtime.skill_injection import _matches_any

    assert not _matches_any("anything", [])


def test_matches_any_multi_pattern_union():
    from app.agents.runtime.skill_injection import _matches_any

    patterns = ["finance:*", "compliance:legal-*"]
    assert _matches_any("finance:dcf", patterns)
    assert _matches_any("compliance:legal-review", patterns)
    assert not _matches_any("hr:onboarding", patterns)


# ===========================================================================
# Task 23 - ``match_and_inject`` filter chain
# ===========================================================================


def test_match_and_inject_filters_by_floor_and_allowed_and_agent_ids():
    from app.agents.runtime import skill_injection

    s_pass = _skill("finance:dcf", agent_ids=[AgentID.FIN])
    s_low = _skill("finance:low", agent_ids=[AgentID.FIN])
    s_wrong_agent = _skill("finance:other", agent_ids=[AgentID.HR])
    s_disallowed = _skill("hr:bonus", agent_ids=[])  # not in allowed
    candidates = [
        {"score": 0.91, "skill": s_pass},
        {"score": 0.40, "skill": s_low},  # below floor
        {"score": 0.80, "skill": s_wrong_agent},
        {"score": 0.85, "skill": s_disallowed},
    ]
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = candidates

    agent = _agent_mock(allowed=["finance:*"], top_k=5, floor=0.65)

    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("forecast Q3 revenue"), agent
            )
        )

    assert "finance:dcf" in out
    assert "finance:low" not in out, "score below floor must be dropped"
    assert "finance:other" not in out, "wrong agent_id must be dropped"
    assert "hr:bonus" not in out, "not in allowed_ids must be dropped"


def test_match_and_inject_empty_when_no_matches():
    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = []

    agent = _agent_mock(allowed=["*"])
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("hello"), agent)
        )
    assert out == ""


def test_match_and_inject_respects_top_k():
    from app.agents.runtime import skill_injection

    candidates = [
        {
            "score": 0.95 - i * 0.01,
            "skill": _skill(f"finance:s{i}", agent_ids=[AgentID.FIN]),
        }
        for i in range(10)
    ]
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = candidates

    agent = _agent_mock(allowed=["*"], top_k=3)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("a"), agent, top_k=3)
        )

    rendered = [n for n in (f"finance:s{i}" for i in range(10)) if n in out]
    assert len(rendered) == 3


def test_match_and_inject_wildcard_allowed_passes_everything():
    from app.agents.runtime import skill_injection

    s = _skill("anything:goes", agent_ids=[AgentID.FIN])
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [{"score": 0.8, "skill": s}]

    agent = _agent_mock(allowed=["*"])
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("hi"), agent)
        )
    assert "anything:goes" in out


def test_match_and_inject_empty_query_returns_empty():
    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    # Should not be called - we bail before hitting the registry.
    fake_registry.semantic_search.return_value = [
        {"score": 0.9, "skill": _skill("x", agent_ids=[AgentID.FIN])},
    ]

    agent = _agent_mock(allowed=["*"])
    blank_request = MagicMock()
    blank_request.goal = ""
    blank_request.message = "   "
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(skill_injection.match_and_inject(blank_request, agent))
    assert out == ""
    fake_registry.semantic_search.assert_not_called()


def test_match_and_inject_handles_registry_exception_gracefully():
    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    fake_registry.semantic_search.side_effect = RuntimeError("embedding service down")

    agent = _agent_mock(allowed=["*"])
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("question"), agent)
        )
    # Failure must not break the turn - return empty so caller can no-op.
    assert out == ""


def test_match_and_inject_skill_with_empty_agent_ids_available_to_all():
    from app.agents.runtime import skill_injection

    # agent_ids=[] => skill available to every agent (per Skill docstring).
    s = _skill("global_skill", agent_ids=[])
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [{"score": 0.9, "skill": s}]

    agent = _agent_mock(allowed=["*"], agent_id=AgentID.HR)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(_request("x"), agent)
        )
    assert "global_skill" in out


def test_match_and_inject_kwarg_overrides_win_over_ops():
    from app.agents.runtime import skill_injection

    candidates = [
        {"score": 0.70, "skill": _skill("finance:a", agent_ids=[AgentID.FIN])},
        {"score": 0.66, "skill": _skill("finance:b", agent_ids=[AgentID.FIN])},
    ]
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = candidates

    # Per-ops floor is 0.65 - bumping via kwarg should evict 0.66.
    agent = _agent_mock(allowed=["*"], floor=0.65)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("q"), agent, similarity_floor=0.69
            )
        )
    assert "finance:a" in out
    assert "finance:b" not in out


# ===========================================================================
# Task 39 - ``consult_applicable_skills`` tool factory
# ===========================================================================


def test_consult_applicable_skills_returns_dict_with_block():
    from app.agents.runtime import skill_injection

    agent = _agent_mock(allowed=["*"], top_k=3, floor=0.5)

    fake_block = "## Relevant skills\n- finance:dcf (score 0.91, finance): DCF\n"
    with patch.object(
        skill_injection,
        "match_and_inject",
        AsyncMock(return_value=fake_block),
    ):
        tool = skill_injection.build_consult_applicable_skills_tool(agent)
        result = asyncio.run(tool("forecast revenue"))

    assert result["success"] is True
    assert "finance:dcf" in result["skills_block"]
    assert result["agent_id"] == "FIN"


def test_consult_applicable_skills_returns_empty_block_when_no_matches():
    from app.agents.runtime import skill_injection

    agent = _agent_mock(allowed=["*"], top_k=3, floor=0.99)

    with patch.object(
        skill_injection,
        "match_and_inject",
        AsyncMock(return_value=""),
    ):
        tool = skill_injection.build_consult_applicable_skills_tool(agent)
        result = asyncio.run(tool("something obscure"))

    assert result["success"] is True
    assert result["skills_block"] == ""


def test_consult_applicable_skills_captures_exceptions():
    from app.agents.runtime import skill_injection

    agent = _agent_mock(allowed=["*"])

    async def _raise(*_args, **_kwargs):
        raise RuntimeError("matcher boom")

    with patch.object(skill_injection, "match_and_inject", _raise):
        tool = skill_injection.build_consult_applicable_skills_tool(agent)
        result = asyncio.run(tool("anything"))

    assert result["success"] is False
    assert "matcher boom" in result["error"]


def test_consult_applicable_skills_factory_alias_exists():
    """Both naming conventions are exported for caller flexibility."""
    from app.agents.runtime import skill_injection

    assert (
        skill_injection.consult_applicable_skills_factory
        is skill_injection.build_consult_applicable_skills_tool
    )


def test_consult_tool_named_consult_applicable_skills():
    from app.agents.runtime import skill_injection

    agent = _agent_mock(allowed=["*"])
    tool = skill_injection.build_consult_applicable_skills_tool(agent)
    assert tool.__name__ == "consult_applicable_skills"
    assert tool.__doc__ and "skills" in tool.__doc__.lower()


# ===========================================================================
# Task 44 - direct-mode exclusion
# ===========================================================================


def test_match_and_inject_skips_when_mode_direct_and_kwarg_skip_set():
    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [
        {"score": 0.9, "skill": _skill("x", agent_ids=[AgentID.FIN])},
    ]
    agent = _agent_mock(allowed=["*"])
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("question"),
                agent,
                mode="direct",
                skip_direct_mode=True,
            )
        )

    assert out == ""
    fake_registry.semantic_search.assert_not_called()


def test_match_and_inject_skips_when_ops_flag_set_and_mode_direct():
    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [
        {"score": 0.9, "skill": _skill("x", agent_ids=[AgentID.FIN])},
    ]
    agent = _agent_mock(allowed=["*"], skip_direct_mode=True)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("question"), agent, mode="direct"
            )
        )

    assert out == ""
    fake_registry.semantic_search.assert_not_called()


def test_match_and_inject_runs_when_mode_initiative_even_if_flag_set():
    from app.agents.runtime import skill_injection

    s = _skill("finance:x", agent_ids=[AgentID.FIN])
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [{"score": 0.9, "skill": s}]

    agent = _agent_mock(allowed=["*"], skip_direct_mode=True)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("plan Q3"), agent, mode="initiative"
            )
        )

    assert "finance:x" in out


def test_match_and_inject_default_behavior_inject_for_both_modes():
    """If neither kwarg nor ops flag are set, both modes get injection."""
    from app.agents.runtime import skill_injection

    s = _skill("finance:x", agent_ids=[AgentID.FIN])
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [{"score": 0.9, "skill": s}]

    agent = _agent_mock(allowed=["*"], skip_direct_mode=False)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out_direct = asyncio.run(
            skill_injection.match_and_inject(
                _request("q"), agent, mode="direct"
            )
        )
        out_initiative = asyncio.run(
            skill_injection.match_and_inject(
                _request("q"), agent, mode="initiative"
            )
        )

    assert "finance:x" in out_direct
    assert "finance:x" in out_initiative


def test_match_and_inject_kwarg_overrides_ops_flag_when_explicitly_false():
    """Explicit ``skip_direct_mode=False`` kwarg wins over a truthy ops flag."""
    from app.agents.runtime import skill_injection

    s = _skill("finance:x", agent_ids=[AgentID.FIN])
    fake_registry = MagicMock()
    fake_registry.semantic_search.return_value = [{"score": 0.9, "skill": s}]

    agent = _agent_mock(allowed=["*"], skip_direct_mode=True)
    with patch.object(skill_injection, "skills_registry", fake_registry):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("q"),
                agent,
                mode="direct",
                skip_direct_mode=False,
            )
        )

    assert "finance:x" in out
