# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for ``app.agents.runtime.memory_retrieval``.

Covers Tasks 25, 26, 40 of the agent operating model W1+W2 plan:
  * Task 25 — ``_render_prior_work`` formats vault rows as a markdown
    ``## Prior work`` block (or empty string).
  * Task 26 — ``retrieve_relevant_history`` runs the full pipeline:
    query extraction, vault search with agent scope, kind filter,
    initiative priority, render. Falls back to ``""`` on empty query
    and on service failure.
  * Task 40 — ``_apply_recency_boost`` lifts recent reports up the
    ranking as a tiebreaker, never overrides a strong similarity gap,
    and survives missing timestamps.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# google.adk is an optional heavy dep at import-time for app.agents.base_agent.
# We never touch base_agent here, but importing app.skills.registry below is
# safe because the registry module is self-contained.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())

from app.skills.registry import AgentID  # noqa: E402


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _agent(top_k: int = 4) -> MagicMock:
    """Build a stub agent exposing the attributes memory_retrieval reads."""
    a = MagicMock()
    a.agent_id = AgentID.FIN
    a.ops.memory.retrieval_top_k = top_k
    return a


def _task_contract(goal: str, initiative_id: str | None = None) -> MagicMock:
    """Build a duck-typed TaskContract: has .goal + .initiative_id, no .message."""
    c = MagicMock()
    c.goal = goal
    c.initiative_id = initiative_id
    # Remove DirectRequest-only attribute so getattr(c, "message", None) is None.
    del c.message
    return c


def _direct_request(message: str) -> MagicMock:
    """Build a duck-typed DirectRequest: has .message, no .goal or .initiative_id."""
    r = MagicMock()
    r.message = message
    # MagicMock auto-creates attributes on access; delete them so getattr
    # with a default returns the default instead of a MagicMock.
    if hasattr(r, "goal"):
        del r.goal
    if hasattr(r, "initiative_id"):
        del r.initiative_id
    return r


def _row_with_age(sim: float, days_ago: int, goal: str) -> dict:
    """Build a vault row with a ``created_at`` ``days_ago`` in the past."""
    ts = (datetime.now(tz=timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {
        "content": f"# {goal}",
        "similarity": sim,
        "metadata": {"goal": goal, "created_at": ts, "kind": "agent_report"},
    }


# ===========================================================================
# Task 25 — _render_prior_work
# ===========================================================================


def test_render_prior_work_formats_results():
    from app.agents.runtime.memory_retrieval import _render_prior_work

    rows = [
        {
            "content": "## Q2 revenue analysis\nWe found a 12% YoY increase driven by enterprise.",
            "similarity": 0.88,
            "metadata": {
                "agent_id": "FIN",
                "initiative_id": "init-123",
                "goal": "Analyze Q2 revenue",
                "kind": "agent_report",
            },
        },
        {
            "content": "## Q1 forecast vs actual\nVariance: -3% on services.",
            "similarity": 0.71,
            "metadata": {
                "agent_id": "FIN",
                "initiative_id": "init-other",
                "goal": "Forecast Q1",
                "kind": "agent_report",
            },
        },
    ]
    out = _render_prior_work(rows)
    assert "## Prior work" in out
    assert "Analyze Q2 revenue" in out
    assert "Forecast Q1" in out
    assert "0.88" in out
    # Initiative IDs surface in the heading line.
    assert "init-123" in out


def test_render_prior_work_empty():
    from app.agents.runtime.memory_retrieval import _render_prior_work

    assert _render_prior_work([]) == ""
    assert _render_prior_work(None) == ""  # type: ignore[arg-type]


def test_render_prior_work_handles_missing_metadata_gracefully():
    """Rows with no goal/similarity render with safe fallbacks (no exceptions)."""
    from app.agents.runtime.memory_retrieval import _render_prior_work

    rows = [{"content": "raw snippet"}]
    out = _render_prior_work(rows)
    assert "Prior work" in out
    assert "raw snippet" in out
    assert "(no goal recorded)" in out


def test_render_prior_work_truncates_long_snippets():
    """Snippets above the cap are trimmed and end with an ellipsis."""
    from app.agents.runtime.memory_retrieval import _render_prior_work

    long_text = "X" * 1000
    rows = [
        {
            "content": long_text,
            "similarity": 0.5,
            "metadata": {"goal": "g"},
        }
    ]
    out = _render_prior_work(rows)
    # The full 1000-X string is not present; an ellipsis marks the cut.
    assert long_text not in out
    assert "…" in out


# ===========================================================================
# Task 26 — retrieve_relevant_history
# ===========================================================================


def test_retrieve_calls_knowledge_service_with_agent_scope():
    """Vault is called with the agent scope and an over-fetch top_k."""
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(
        return_value=[
            {
                "content": "Q2 went well.",
                "similarity": 0.9,
                "metadata": {
                    "agent_id": "FIN",
                    "goal": "Analyze Q2",
                    "kind": "agent_report",
                },
            }
        ]
    )
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("Analyze Q3 revenue"), _agent()
            )
        )

    fake_search.assert_awaited_once()
    call_kwargs = fake_search.await_args.kwargs
    assert call_kwargs.get("agent_name") == "FIN"
    # 2x over-fetch for the initiative + recency re-ranking passes.
    assert call_kwargs.get("top_k") == 4 * 2
    assert call_kwargs.get("query") == "Analyze Q3 revenue"
    assert "Analyze Q2" in out
    assert "## Prior work" in out


def test_retrieve_falls_back_to_direct_request_message():
    """When .goal is absent, use .message as the query."""
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(return_value=[])
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _direct_request("what's our Q3 revenue?"), _agent()
            )
        )

    assert out == ""
    call_kwargs = fake_search.await_args.kwargs
    assert call_kwargs.get("query") == "what's our Q3 revenue?"
    assert call_kwargs.get("agent_name") == "FIN"


def test_retrieve_prioritizes_same_initiative():
    """Same-initiative rows out-rank otherwise more-similar other-initiative rows."""
    from app.agents.runtime import memory_retrieval

    other_initiative = {
        "content": "other",
        "similarity": 0.95,
        "metadata": {
            "agent_id": "FIN",
            "initiative_id": "other",
            "goal": "Other",
            "kind": "agent_report",
        },
    }
    same_initiative = {
        "content": "same",
        "similarity": 0.70,
        "metadata": {
            "agent_id": "FIN",
            "initiative_id": "init-X",
            "goal": "Same",
            "kind": "agent_report",
        },
    }
    fake_search = AsyncMock(return_value=[other_initiative, same_initiative])

    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("goal text", initiative_id="init-X"),
                _agent(top_k=2),
            )
        )

    same_idx = out.index("Same")
    other_idx = out.index("Other")
    assert same_idx < other_idx


def test_retrieve_empty_query_returns_empty():
    """Empty .goal AND empty .message short-circuits without calling the vault."""
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock()
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(_direct_request(""), _agent())
        )
    assert out == ""
    fake_search.assert_not_awaited()


def test_retrieve_handles_service_failure_gracefully():
    """A vault exception is logged and the function returns an empty string."""
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(side_effect=RuntimeError("vault down"))
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("goal"), _agent()
            )
        )
    assert out == ""


def test_retrieve_filters_to_agent_report_kind():
    """Vault rows that are NOT agent_reports are dropped before rendering."""
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(
        return_value=[
            {
                "content": "training doc body",
                "similarity": 0.99,
                "metadata": {"goal": "ignored", "kind": "admin_training"},
            },
            {
                "content": "real report",
                "similarity": 0.6,
                "metadata": {"goal": "kept", "kind": "agent_report"},
            },
        ]
    )
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("query"), _agent()
            )
        )

    assert "kept" in out
    assert "ignored" not in out


def test_retrieve_honors_top_k_override():
    """An explicit ``top_k`` kwarg overrides ``agent.ops.memory.retrieval_top_k``."""
    from app.agents.runtime import memory_retrieval

    fake_search = AsyncMock(return_value=[])
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("q"), _agent(top_k=4), top_k=10
            )
        )
    assert fake_search.await_args.kwargs.get("top_k") == 20  # 10 * over-fetch


def test_retrieve_truncates_to_eff_top_k():
    """Even when the vault returns more rows than top_k, the render is truncated."""
    from app.agents.runtime import memory_retrieval

    rows = [
        {
            "content": f"report {i}",
            "similarity": 0.9 - i * 0.01,
            "metadata": {"goal": f"goal-{i}", "kind": "agent_report"},
        }
        for i in range(8)
    ]
    fake_search = AsyncMock(return_value=rows)
    with patch.object(memory_retrieval, "search_system_knowledge", fake_search):
        out = asyncio.run(
            memory_retrieval.retrieve_relevant_history(
                _task_contract("q"), _agent(top_k=3)
            )
        )

    # Only the first 3 goals should appear in the rendered block.
    assert "goal-0" in out
    assert "goal-1" in out
    assert "goal-2" in out
    assert "goal-3" not in out


# ===========================================================================
# Task 40 — _apply_recency_boost
# ===========================================================================


def test_recency_boost_prefers_recent_when_similarity_close():
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        _row_with_age(sim=0.81, days_ago=200, goal="old"),
        _row_with_age(sim=0.80, days_ago=3, goal="recent"),
    ]
    out = _apply_recency_boost(rows)
    assert out[0]["metadata"]["goal"] == "recent"


def test_recency_boost_does_not_override_large_similarity_gap():
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        _row_with_age(sim=0.95, days_ago=200, goal="old_relevant"),
        _row_with_age(sim=0.50, days_ago=2, goal="recent_irrelevant"),
    ]
    out = _apply_recency_boost(rows)
    assert out[0]["metadata"]["goal"] == "old_relevant"


def test_recency_boost_handles_missing_timestamps():
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        {"content": "a", "similarity": 0.9, "metadata": {"goal": "a"}},
        {"content": "b", "similarity": 0.85, "metadata": {"goal": "b"}},
    ]
    out = _apply_recency_boost(rows)
    # No timestamps anywhere → only similarity matters → original order kept.
    assert [r["metadata"]["goal"] for r in out] == ["a", "b"]


def test_recency_boost_parses_trailing_z_timestamps():
    """``...Z`` suffix is normalised to ``+00:00`` before fromisoformat."""
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    now = datetime.now(tz=timezone.utc)
    z_form = now.isoformat().replace("+00:00", "Z")
    rows = [
        {
            "content": "x",
            "similarity": 0.70,
            "metadata": {"goal": "today_z", "created_at": z_form},
        },
        {
            "content": "y",
            "similarity": 0.72,
            "metadata": {"goal": "older", "created_at": (now - timedelta(days=29)).isoformat()},
        },
    ]
    out = _apply_recency_boost(rows)
    # today_z gets the max boost (~0.05), bumping its score above 0.72.
    assert out[0]["metadata"]["goal"] == "today_z"


def test_recency_boost_outside_window_no_boost():
    """Rows older than the window get exactly zero boost (sim wins outright)."""
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        _row_with_age(sim=0.60, days_ago=400, goal="ancient"),
        _row_with_age(sim=0.70, days_ago=365, goal="old"),
    ]
    out = _apply_recency_boost(rows)
    assert [r["metadata"]["goal"] for r in out] == ["old", "ancient"]


def test_recency_boost_handles_malformed_timestamps():
    """A non-ISO ``created_at`` value is treated as 'no recency signal'."""
    from app.agents.runtime.memory_retrieval import _apply_recency_boost

    rows = [
        {
            "content": "a",
            "similarity": 0.80,
            "metadata": {"goal": "a", "created_at": "not-a-date"},
        },
        {
            "content": "b",
            "similarity": 0.79,
            "metadata": {"goal": "b", "created_at": 12345},  # wrong type
        },
    ]
    out = _apply_recency_boost(rows)
    assert [r["metadata"]["goal"] for r in out] == ["a", "b"]


# ===========================================================================
# Bonus: _prioritize_same_initiative helper exposed for reuse
# ===========================================================================


def test_prioritize_same_initiative_with_no_initiative_id_is_passthrough():
    from app.agents.runtime.memory_retrieval import _prioritize_same_initiative

    rows = [
        {"metadata": {"initiative_id": "a"}},
        {"metadata": {"initiative_id": "b"}},
    ]
    assert _prioritize_same_initiative(rows, None) == rows
    assert _prioritize_same_initiative(rows, "") == rows


def test_prioritize_same_initiative_handles_uuid_vs_string():
    """initiative_id may arrive as a UUID; comparison happens on string form."""
    import uuid

    from app.agents.runtime.memory_retrieval import _prioritize_same_initiative

    target = uuid.UUID("11111111-1111-1111-1111-111111111111")
    rows = [
        {"metadata": {"initiative_id": "other-id", "goal": "other"}},
        {"metadata": {"initiative_id": str(target), "goal": "same"}},
    ]
    out = _prioritize_same_initiative(rows, target)
    assert out[0]["metadata"]["goal"] == "same"
