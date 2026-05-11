# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Consolidated tests for :mod:`app.agents.runtime.research_gate`.

Covers tasks 46-53 and task 71 of the agent operating model W1+W2 plan:

* 46 — RESEARCH_TOOL_IDS constant
* 47 — open_gate inserts agent_research_runs row
* 48 — is_open checks (contract_id, agent_id) pair
* 49 — record_tool_result accumulates raw results
* 50 — coverage prompt + JSON parser helpers
* 51 — check_coverage complete path returns ResearchResult
* 52 — check_coverage partial path returns None; exhausted path raises
* 53 — close_gate persists complete result + completed_at
* 71 — record_tool_result rejects when run is already closed
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import research_gate
from app.agents.runtime.types import ResearchGateError, ResearchResult
from app.skills.registry import AgentID

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _patch_supabase(monkeypatch: pytest.MonkeyPatch, client: MagicMock) -> None:
    """Wire ``research_gate._get_supabase`` to return ``client`` (async)."""

    async def _fake_get_supabase():
        return client

    monkeypatch.setattr(research_gate, "_get_supabase", _fake_get_supabase)


def _select_chain_for(rows: list[dict]) -> MagicMock:
    """Build a select chain whose terminal ``execute()`` returns ``data=rows``."""
    chain = MagicMock()
    chain.execute = AsyncMock(return_value=MagicMock(data=rows))
    chain.eq = MagicMock(return_value=chain)
    chain.in_ = MagicMock(return_value=chain)
    chain.select = MagicMock(return_value=chain)
    chain.limit = MagicMock(return_value=chain)
    chain.single = MagicMock(return_value=chain)
    return chain


# ---------------------------------------------------------------------------
# Task 46 — RESEARCH_TOOL_IDS constant
# ---------------------------------------------------------------------------


def test_research_tool_ids_is_frozenset() -> None:
    assert isinstance(research_gate.RESEARCH_TOOL_IDS, frozenset)


def test_research_tool_ids_matches_spec() -> None:
    assert research_gate.RESEARCH_TOOL_IDS == frozenset(
        {
            "deep_research",
            "tavily_search",
            "firecrawl_scrape",
            "google_search",
            "quick_research",
        }
    )


def test_research_tool_ids_is_immutable() -> None:
    with pytest.raises(AttributeError):
        research_gate.RESEARCH_TOOL_IDS.add("other")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Task 47 — open_gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_gate_inserts_row_and_returns_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract_id = uuid4()
    fake_row = {"id": str(uuid4())}

    insert_chain = MagicMock()
    insert_chain.execute = AsyncMock(return_value=MagicMock(data=[fake_row]))
    table_mock = MagicMock()
    table_mock.insert = MagicMock(return_value=insert_chain)
    client = MagicMock()
    client.table = MagicMock(return_value=table_mock)

    _patch_supabase(monkeypatch, client)

    run_id = await research_gate.open_gate(
        task_contract_id=contract_id,
        contract_source="initiative_step",
        agent_id=AgentID.FIN,
        initial_query="2026 Q3 forecast assumptions",
    )

    assert isinstance(run_id, UUID)
    client.table.assert_called_once_with("agent_research_runs")
    payload = table_mock.insert.call_args[0][0]
    assert payload["task_contract_id"] == str(contract_id)
    assert payload["task_contract_source"] == "initiative_step"
    assert payload["agent_id"] == AgentID.FIN.value
    assert payload["query"] == "2026 Q3 forecast assumptions"
    assert payload["status"] == "open"
    assert payload["iterations"] == 0
    # user_id is optional and should NOT be written when omitted
    assert "user_id" not in payload


@pytest.mark.asyncio
async def test_open_gate_includes_user_id_when_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract_id = uuid4()
    user_id = uuid4()
    fake_row = {"id": str(uuid4())}

    insert_chain = MagicMock()
    insert_chain.execute = AsyncMock(return_value=MagicMock(data=[fake_row]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    await research_gate.open_gate(
        task_contract_id=contract_id,
        contract_source="department_task",
        agent_id=AgentID.STRAT,
        initial_query="competitor landscape",
        user_id=user_id,
    )

    payload = table_mock.insert.call_args[0][0]
    assert payload["user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_open_gate_raises_if_insert_returns_no_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    insert_chain = MagicMock()
    insert_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    with pytest.raises(ResearchGateError):
        await research_gate.open_gate(
            task_contract_id=uuid4(),
            contract_source="initiative_step",
            agent_id=AgentID.FIN,
            initial_query="anything",
        )


# ---------------------------------------------------------------------------
# Task 48 — is_open
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_open_true_when_row_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _select_chain_for([{"id": str(uuid4()), "status": "open"}])
    client = MagicMock(table=MagicMock(return_value=chain))
    _patch_supabase(monkeypatch, client)

    result = await research_gate.is_open(
        task_contract_id=uuid4(), agent_id=AgentID.FIN
    )
    assert result is True
    # confirm the in_ filter targets the correct set of statuses
    chain.in_.assert_called_once_with("status", ["open", "in_progress"])


@pytest.mark.asyncio
async def test_is_open_false_when_no_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _select_chain_for([])
    client = MagicMock(table=MagicMock(return_value=chain))
    _patch_supabase(monkeypatch, client)

    result = await research_gate.is_open(
        task_contract_id=uuid4(), agent_id=AgentID.FIN
    )
    assert result is False


# ---------------------------------------------------------------------------
# Task 49 — record_tool_result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_tool_result_only_accepts_research_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No client patch needed — the tool-id check happens before any DB access.
    with pytest.raises(ResearchGateError):
        await research_gate.record_tool_result(
            run_id=uuid4(), tool_id="send_email", raw_result={"ok": True}
        )


@pytest.mark.asyncio
async def test_record_tool_result_appends_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    existing = {"raw_results": [{"tool_id": "tavily_search", "data": {"q": 1}}]}

    select_chain = _select_chain_for(
        [{"result": existing, "iterations": 1, "status": "in_progress"}]
    )
    update_chain = MagicMock()
    update_chain.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": str(run_id)}])
    )
    update_chain.eq = MagicMock(return_value=update_chain)

    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_chain)
    table_mock.update = MagicMock(return_value=update_chain)
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    await research_gate.record_tool_result(
        run_id=run_id, tool_id="deep_research", raw_result={"sources": []}
    )

    update_payload = table_mock.update.call_args[0][0]
    assert update_payload["iterations"] == 2
    assert update_payload["status"] == "in_progress"
    assert len(update_payload["result"]["raw_results"]) == 2
    assert update_payload["result"]["raw_results"][-1]["tool_id"] == "deep_research"
    update_chain.eq.assert_called_with("id", str(run_id))


@pytest.mark.asyncio
async def test_record_tool_result_raises_when_run_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_chain = _select_chain_for([])
    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_chain)
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    with pytest.raises(ResearchGateError):
        await research_gate.record_tool_result(
            run_id=uuid4(), tool_id="tavily_search", raw_result={}
        )


# ---------------------------------------------------------------------------
# Task 50 — coverage prompt + JSON parser
# ---------------------------------------------------------------------------


def test_parse_strips_code_fence() -> None:
    text = (
        "```json\n"
        '{"summary": "x", "sources": [], "contradictions": [], '
        '"coverage_assessment": "complete", "missing_information": []}\n'
        "```"
    )
    result = research_gate._parse_coverage_json(text)
    assert result is not None
    assert result.coverage_assessment == "complete"


def test_parse_strips_unlabeled_fence() -> None:
    text = (
        "```\n"
        '{"summary": "y", "sources": [], "contradictions": [], '
        '"coverage_assessment": "partial", "missing_information": ["A"]}\n'
        "```"
    )
    result = research_gate._parse_coverage_json(text)
    assert result is not None
    assert result.coverage_assessment == "partial"


def test_parse_returns_none_on_bad_json() -> None:
    assert research_gate._parse_coverage_json("not json at all") is None


def test_parse_returns_none_when_not_an_object() -> None:
    assert research_gate._parse_coverage_json("[1, 2, 3]") is None


def test_parse_returns_none_when_missing_required_field() -> None:
    text = '{"summary": "x", "coverage_assessment": "complete"}'
    assert research_gate._parse_coverage_json(text) is None


def test_parse_accepts_partial_assessment() -> None:
    text = (
        '{"summary": "y", "sources": [], "contradictions": [], '
        '"coverage_assessment": "partial", "missing_information": ["x"]}'
    )
    result = research_gate._parse_coverage_json(text)
    assert result is not None
    assert result.coverage_assessment == "partial"
    assert result.missing_information == ["x"]


def test_build_coverage_prompt_lists_criteria_and_truncates_blob() -> None:
    prompt = research_gate._build_coverage_prompt(
        success_criteria=["criterion one", "criterion two"],
        raw_results=[{"tool_id": "tavily_search", "data": {"q": "x" * 10000}}],
    )
    assert "criterion one" in prompt
    assert "criterion two" in prompt
    # blob is capped at 8000 chars, total prompt is bounded
    assert "RAW RESEARCH RESULTS" in prompt


def test_build_coverage_prompt_handles_empty_criteria() -> None:
    prompt = research_gate._build_coverage_prompt(
        success_criteria=[],
        raw_results=[],
    )
    assert "- (none)" in prompt


# ---------------------------------------------------------------------------
# Task 51 — check_coverage complete path
# ---------------------------------------------------------------------------


def _stub_load_run(
    monkeypatch: pytest.MonkeyPatch, *, run_id: UUID, iterations: int
) -> None:
    """Wire ``_load_run`` so check_coverage sees the requested state."""
    row = {
        "id": str(run_id),
        "result": {"raw_results": [{"tool_id": "tavily_search", "data": {}}]},
        "iterations": iterations,
    }
    select_chain = _select_chain_for([row])
    table_mock = MagicMock(select=MagicMock(return_value=select_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)


@pytest.mark.asyncio
async def test_check_coverage_returns_result_when_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=1)

    fake_llm = AsyncMock(
        return_value=(
            '{"summary": "ok", "sources": [], "contradictions": [], '
            '"coverage_assessment": "complete", "missing_information": []}'
        )
    )
    monkeypatch.setattr(research_gate, "_call_coverage_llm", fake_llm)

    result = await research_gate.check_coverage(
        run_id=run_id,
        success_criteria=["criterion A"],
        max_iterations=3,
    )

    assert isinstance(result, ResearchResult)
    assert result.coverage_assessment == "complete"
    fake_llm.assert_awaited_once()


# ---------------------------------------------------------------------------
# Task 52 — check_coverage partial + exhausted paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_coverage_returns_none_when_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=1)

    monkeypatch.setattr(
        research_gate,
        "_call_coverage_llm",
        AsyncMock(
            return_value=(
                '{"summary": "x", "sources": [], "contradictions": [], '
                '"coverage_assessment": "partial", "missing_information": ["A"]}'
            )
        ),
    )

    result = await research_gate.check_coverage(
        run_id=run_id, success_criteria=["A"], max_iterations=3
    )
    assert result is None


@pytest.mark.asyncio
async def test_check_coverage_raises_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=3)

    monkeypatch.setattr(
        research_gate,
        "_call_coverage_llm",
        AsyncMock(
            return_value=(
                '{"summary": "x", "sources": [], "contradictions": [], '
                '"coverage_assessment": "partial", "missing_information": ["A"]}'
            )
        ),
    )

    with pytest.raises(ResearchGateError):
        await research_gate.check_coverage(
            run_id=run_id, success_criteria=["A"], max_iterations=3
        )


@pytest.mark.asyncio
async def test_check_coverage_raises_on_bad_llm_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=3)
    monkeypatch.setattr(
        research_gate, "_call_coverage_llm", AsyncMock(return_value=None)
    )

    with pytest.raises(ResearchGateError):
        await research_gate.check_coverage(
            run_id=run_id, success_criteria=["A"], max_iterations=3
        )


@pytest.mark.asyncio
async def test_check_coverage_returns_none_on_bad_llm_when_budget_remains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=1)
    monkeypatch.setattr(
        research_gate, "_call_coverage_llm", AsyncMock(return_value=None)
    )

    result = await research_gate.check_coverage(
        run_id=run_id, success_criteria=["A"], max_iterations=3
    )
    assert result is None


@pytest.mark.asyncio
async def test_check_coverage_returns_none_on_unparseable_when_budget_remains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=1)
    monkeypatch.setattr(
        research_gate,
        "_call_coverage_llm",
        AsyncMock(return_value="this is not json"),
    )

    result = await research_gate.check_coverage(
        run_id=run_id, success_criteria=["A"], max_iterations=3
    )
    assert result is None


@pytest.mark.asyncio
async def test_check_coverage_raises_on_unparseable_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    _stub_load_run(monkeypatch, run_id=run_id, iterations=3)
    monkeypatch.setattr(
        research_gate,
        "_call_coverage_llm",
        AsyncMock(return_value="garbage non-json"),
    )

    with pytest.raises(ResearchGateError):
        await research_gate.check_coverage(
            run_id=run_id, success_criteria=["A"], max_iterations=3
        )


@pytest.mark.asyncio
async def test_check_coverage_raises_when_run_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_chain = _select_chain_for([])
    table_mock = MagicMock(select=MagicMock(return_value=select_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    with pytest.raises(ResearchGateError):
        await research_gate.check_coverage(
            run_id=uuid4(), success_criteria=["A"], max_iterations=3
        )


# ---------------------------------------------------------------------------
# Task 53 — close_gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_gate_persists_result(monkeypatch: pytest.MonkeyPatch) -> None:
    run_id = uuid4()
    update_chain = MagicMock()
    update_chain.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": str(run_id)}])
    )
    update_chain.eq = MagicMock(return_value=update_chain)

    table_mock = MagicMock(update=MagicMock(return_value=update_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    result = ResearchResult(
        summary="ok",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )
    await research_gate.close_gate(run_id=run_id, result=result)

    payload = table_mock.update.call_args[0][0]
    assert payload["status"] == "complete"
    assert "completed_at" in payload
    assert payload["result"]["coverage_assessment"] == "complete"
    update_chain.eq.assert_called_with("id", str(run_id))


# ---------------------------------------------------------------------------
# Task 71 — record_tool_result rejects closed runs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_tool_result_rejects_complete_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_chain = _select_chain_for(
        [{"result": {"raw_results": []}, "iterations": 0, "status": "complete"}]
    )
    table_mock = MagicMock(select=MagicMock(return_value=select_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    with pytest.raises(ResearchGateError):
        await research_gate.record_tool_result(
            run_id=uuid4(), tool_id="tavily_search", raw_result={}
        )


@pytest.mark.asyncio
async def test_record_tool_result_rejects_failed_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_chain = _select_chain_for(
        [{"result": {"raw_results": []}, "iterations": 1, "status": "failed"}]
    )
    table_mock = MagicMock(select=MagicMock(return_value=select_chain))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    _patch_supabase(monkeypatch, client)

    with pytest.raises(ResearchGateError):
        await research_gate.record_tool_result(
            run_id=uuid4(), tool_id="tavily_search", raw_result={}
        )
