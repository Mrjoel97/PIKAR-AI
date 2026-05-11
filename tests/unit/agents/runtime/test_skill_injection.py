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

import pytest

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
# Default-warmed-embeddings fixture (W3 A3-lite + A6)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _force_embeddings_warmed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to the semantic-search code path.

    The W3 A3-lite keyword fallback fires when
    ``skill_injection._embeddings_warmed()`` returns ``False``. In a real
    process that's the case for unit tests (no warming runs) — but the
    existing tests in this file were written assuming the semantic path,
    so we pin it to ``True`` by default. The handful of A3-lite tests
    that want the keyword path override this with their own
    ``patch.object(skill_injection, "_embeddings_warmed", lambda: False)``.
    """
    from app.agents.runtime import skill_injection

    monkeypatch.setattr(skill_injection, "_embeddings_warmed", lambda: True)


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
    assert not _matches_any("compliance:other", ["compliance:legal-risk-assessment"])


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
            skill_injection.match_and_inject(_request("forecast Q3 revenue"), agent)
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
        out = asyncio.run(skill_injection.match_and_inject(_request("hello"), agent))
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
        out = asyncio.run(skill_injection.match_and_inject(_request("hi"), agent))
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
        out = asyncio.run(skill_injection.match_and_inject(_request("question"), agent))
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
        out = asyncio.run(skill_injection.match_and_inject(_request("x"), agent))
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
            skill_injection.match_and_inject(_request("question"), agent, mode="direct")
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
            skill_injection.match_and_inject(_request("q"), agent, mode="direct")
        )
        out_initiative = asyncio.run(
            skill_injection.match_and_inject(_request("q"), agent, mode="initiative")
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


# ===========================================================================
# W3 Section A — Task A6: OTel telemetry on match_and_inject
# ===========================================================================


class _FakeSpan:
    """A minimal stand-in for an OTel Span that records set_attribute calls.

    We don't use the real opentelemetry.sdk here because
    ``tests/unit/conftest.py`` stubs the top-level ``opentelemetry`` module
    with a MagicMock — ``from opentelemetry.sdk.trace import ...`` would
    fail under pytest. The fake captures everything the test needs to
    assert against: span name and the attribute map.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, object] = {}

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def __enter__(self) -> _FakeSpan:
        return self

    def __exit__(self, *exc_info: object) -> bool | None:
        return None


class _FakeTracer:
    """Captures every span created via ``start_as_current_span``."""

    def __init__(self) -> None:
        self.spans: list[_FakeSpan] = []

    def start_as_current_span(self, name: str) -> _FakeSpan:
        span = _FakeSpan(name)
        self.spans.append(span)
        return span


def test_match_and_inject_emits_otel_span_with_attributes():
    """W3-A6: ``match_and_inject`` emits an OTel span
    ``pikar.skill_injection.match`` with attributes useful for tracing the
    matcher hot path (agent_id, mode, query_len, top_k, similarity_floor,
    candidate_count, matched_count). Latency is implicit in the span's
    start/end timestamps.
    """
    from app.agents.runtime import skill_injection

    fake_tracer = _FakeTracer()
    fake_registry = MagicMock()
    fake_registry.semantic_search = MagicMock(
        return_value=[
            {
                "score": 0.82,
                "skill": _skill(
                    "finance:budget_modeling",
                    description="DCF + sensitivity",
                ),
            },
        ]
    )

    agent = _agent_mock(allowed=["finance:*"], top_k=5, floor=0.65)

    with (
        patch.object(skill_injection, "skills_registry", fake_registry),
        patch.object(skill_injection, "_tracer", fake_tracer),
    ):
        asyncio.run(
            skill_injection.match_and_inject(
                _request("draft Q3 budget plan"),
                agent,
                mode="initiative",
            )
        )

    assert len(fake_tracer.spans) == 1, (
        f"expected exactly one span, got: {[s.name for s in fake_tracer.spans]}"
    )
    span = fake_tracer.spans[0]
    assert span.name == "pikar.skill_injection.match"
    # Required attributes — the dashboard / Cloud Trace filters depend on them.
    assert span.attributes.get("pikar.mode") == "initiative"
    assert span.attributes.get("pikar.top_k") == 5
    assert span.attributes.get("pikar.similarity_floor") == 0.65
    assert span.attributes.get("pikar.query_len") == len("draft Q3 budget plan")
    assert span.attributes.get("pikar.candidate_count") == 1
    assert span.attributes.get("pikar.matched_count") == 1
    # agent_id is the AgentID enum's `.value`. The mock fixture defaults to
    # AgentID.FIN whose value is "FIN".
    assert span.attributes.get("pikar.agent_id") == "FIN"


def test_match_and_inject_span_records_zero_matches_when_below_floor():
    """W3-A6: span attributes must report candidate_count and matched_count
    even when no candidates clear the similarity floor. This is the
    high-signal case for the observability dashboard — a non-zero candidate
    count with zero matches means the floor is too aggressive for the
    agent's query mix."""
    from app.agents.runtime import skill_injection

    fake_tracer = _FakeTracer()
    fake_registry = MagicMock()
    # Score below the agent's similarity_floor of 0.65 — candidates exist
    # but none should clear the gate.
    fake_registry.semantic_search = MagicMock(
        return_value=[
            {"score": 0.50, "skill": _skill("finance:noise")},
            {"score": 0.30, "skill": _skill("finance:more_noise")},
        ]
    )

    agent = _agent_mock(allowed=["finance:*"], top_k=5, floor=0.65)

    with (
        patch.object(skill_injection, "skills_registry", fake_registry),
        patch.object(skill_injection, "_tracer", fake_tracer),
    ):
        asyncio.run(
            skill_injection.match_and_inject(
                _request("something tangential"),
                agent,
                mode="initiative",
            )
        )

    span = fake_tracer.spans[0]
    assert span.name == "pikar.skill_injection.match"
    # Either semantic_search returned 0 candidates (pre-filter on threshold)
    # or returned them and match_and_inject's own floor check rejected them.
    # Either way the matched_count is zero.
    assert span.attributes.get("pikar.matched_count") == 0


def test_match_and_inject_span_emitted_on_direct_mode_skip():
    """W3-A6: even when direct-mode skipping suppresses injection, the
    span must still emit so the dashboard can distinguish 'no candidates'
    from 'intentionally skipped'."""
    from app.agents.runtime import skill_injection

    fake_tracer = _FakeTracer()
    agent = _agent_mock(skip_direct_mode=True)

    with patch.object(skill_injection, "_tracer", fake_tracer):
        result = asyncio.run(
            skill_injection.match_and_inject(
                _request("hi"),
                agent,
                mode="direct",
                skip_direct_mode=True,
            )
        )

    assert result == ""
    assert len(fake_tracer.spans) == 1
    span = fake_tracer.spans[0]
    assert span.name == "pikar.skill_injection.match"
    # The dashboard needs a clear signal for skipped turns.
    assert span.attributes.get("pikar.skipped") == "direct_mode"


# ===========================================================================
# W3 Section A — Task A7: performance regression test
# ===========================================================================


def test_match_and_inject_p95_latency_under_budget():
    """W3-A7: Performance regression test. With the semantic-search step
    mocked to return instantly, ``match_and_inject``'s own overhead (config
    resolution, filter loop, attribute setting, markdown render) must keep
    p95 latency well under the 80ms hot-path budget from the W3 plan.

    The test exists to catch regressions like:
    * a synchronous Supabase/Vertex call sneaking into the hot path,
    * an O(n²) loop introduced when the candidate pool grows,
    * lock contention or runaway logging in the matcher.

    Mocked execution should be sub-millisecond per call. The 80ms budget is
    generous on purpose — the test fires loud only when something is
    *seriously* wrong, not on incidental CI variance.
    """
    import time

    from app.agents.runtime import skill_injection

    fake_registry = MagicMock()
    fake_registry.semantic_search = MagicMock(
        return_value=[
            {"score": 0.85, "skill": _skill(f"finance:skill_{i}")} for i in range(10)
        ]
    )
    agent = _agent_mock(allowed=["finance:*"], top_k=5)

    async def _iterations(n: int) -> list[float]:
        out: list[float] = []
        for _ in range(n):
            t0 = time.perf_counter_ns()
            await skill_injection.match_and_inject(
                _request("a representative goal text"),
                agent,
                mode="initiative",
            )
            out.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        return out

    with patch.object(skill_injection, "skills_registry", fake_registry):
        durations = asyncio.run(_iterations(100))

    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    p99 = durations[min(int(len(durations) * 0.99), len(durations) - 1)]

    # The budget catches a 10-100x regression. On mocked I/O p95 should be
    # under a couple of milliseconds in practice.
    assert p95 < 80.0, (
        f"match_and_inject p95 latency {p95:.2f}ms exceeds 80ms budget "
        f"(p50={p50:.2f}ms, p99={p99:.2f}ms). "
        f"Slowest 5: {[f'{d:.2f}' for d in durations[-5:]]}"
    )


# ===========================================================================
# W3 Section A — Task A3-lite: keyword fallback when embeddings cold
# ===========================================================================


def test_keyword_fallback_fires_when_embeddings_cold():
    """W3-A3-lite: when ``skill_embeddings.is_warmed()`` returns False
    (dev environment without Vertex creds, or a fresh process where the
    embedding cache hasn't been warmed yet), ``match_and_inject`` falls
    back to a substring match over skill name/description/summary so
    relevant skills still surface — instead of returning the empty string
    and losing all skill-injection value.

    Production keeps the semantic path because ``is_warmed()`` returns True
    once ``warmup_skill_embeddings()`` has run at startup.
    """
    from app.agents.runtime import skill_injection

    fake_tracer = _FakeTracer()
    fake_registry = MagicMock()
    fake_registry.get_by_agent_id = MagicMock(
        return_value=[
            _skill("finance:budget_modeling", description="DCF, NPV, IRR modeling"),
            _skill("finance:variance_analysis", description="Budget vs actuals"),
            _skill("hr:hiring_funnel", description="Recruiting pipeline tactics"),
        ]
    )
    # semantic_search would return [] when embeddings are cold; mock that.
    fake_registry.semantic_search = MagicMock(return_value=[])

    agent = _agent_mock(allowed=["finance:*", "hr:*"], top_k=5, floor=0.65)

    # Force the embeddings-cold code path.
    with (
        patch.object(skill_injection, "skills_registry", fake_registry),
        patch.object(skill_injection, "_tracer", fake_tracer),
        patch.object(skill_injection, "_embeddings_warmed", lambda: False),
    ):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("draft a DCF budget"),
                agent,
                mode="initiative",
            )
        )

    assert "finance:budget_modeling" in out, (
        "DCF query should surface the budget_modeling skill via keyword fallback"
    )
    # The unrelated HR skill must NOT appear — only substring hits.
    assert "hr:hiring_funnel" not in out

    # Span attribute distinguishes which matcher fired so dashboards can
    # filter ``matcher = "keyword_fallback"`` to spot dev environments
    # leaking into production traces.
    span = fake_tracer.spans[0]
    assert span.attributes.get("pikar.matcher") == "keyword_fallback"
    assert span.attributes.get("pikar.matched_count", 0) >= 1


def test_keyword_fallback_does_not_fire_when_embeddings_warm():
    """W3-A3-lite: when ``is_warmed()`` returns True (production), the
    semantic-search path is used and the keyword fallback never runs.
    The span attribute must say ``matcher = "semantic"``."""
    from app.agents.runtime import skill_injection

    fake_tracer = _FakeTracer()
    fake_registry = MagicMock()
    fake_registry.semantic_search = MagicMock(
        return_value=[
            {"score": 0.88, "skill": _skill("finance:budget_modeling")},
        ]
    )
    # get_by_agent_id should NOT be consulted on the semantic path.
    fake_registry.get_by_agent_id = MagicMock(
        side_effect=AssertionError(
            "get_by_agent_id must not be called when embeddings are warm"
        )
    )

    agent = _agent_mock(allowed=["finance:*"], top_k=5, floor=0.65)

    with (
        patch.object(skill_injection, "skills_registry", fake_registry),
        patch.object(skill_injection, "_tracer", fake_tracer),
        patch.object(skill_injection, "_embeddings_warmed", lambda: True),
    ):
        asyncio.run(
            skill_injection.match_and_inject(
                _request("budget"),
                agent,
                mode="initiative",
            )
        )

    span = fake_tracer.spans[0]
    assert span.attributes.get("pikar.matcher") == "semantic"


def test_keyword_fallback_respects_agent_scope_and_allowed_ids():
    """W3-A3-lite: the keyword path must enforce the same gates as the
    semantic path — agent scope (skill.agent_ids) and allowed_ids glob.
    A skill that substring-matches but is scoped to a different agent OR
    excluded by allowed_ids must NOT appear."""
    from app.agents.runtime import skill_injection
    from app.skills.registry import AgentID

    fake_tracer = _FakeTracer()
    fake_registry = MagicMock()
    fake_registry.get_by_agent_id = MagicMock(
        return_value=[
            # Matches query AND is in scope for AgentID.FIN (default mock id):
            _skill(
                "finance:budget_modeling",
                description="budget DCF NPV",
                agent_ids=[AgentID.FIN],
            ),
            # Matches query BUT scoped to a different agent (HR):
            _skill(
                "hr:budget_negotiation",
                description="budget conversation tactics",
                agent_ids=[AgentID.HR] if hasattr(AgentID, "HR") else [],
            ),
            # Matches query BUT excluded by allowed_ids (no glob hit on data:*):
            _skill(
                "data:budget_dashboard",
                description="budget visualization",
                agent_ids=[],  # available to all agents
            ),
        ]
    )
    fake_registry.semantic_search = MagicMock(return_value=[])

    agent = _agent_mock(
        allowed=["finance:*"],  # only finance:* permitted
        top_k=5,
        floor=0.65,
    )

    with (
        patch.object(skill_injection, "skills_registry", fake_registry),
        patch.object(skill_injection, "_tracer", fake_tracer),
        patch.object(skill_injection, "_embeddings_warmed", lambda: False),
    ):
        out = asyncio.run(
            skill_injection.match_and_inject(
                _request("budget"),
                agent,
                mode="initiative",
            )
        )

    assert "finance:budget_modeling" in out
    assert "data:budget_dashboard" not in out, "allowed_ids glob must filter"
