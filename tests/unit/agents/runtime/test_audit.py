# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Consolidated tests for ``app.agents.runtime.audit`` (Tasks 54-59, 72).

Covers:
  * Task 54 — ``_build_audit_prompt`` embeds every todo + criterion.
  * Task 55 — ``_parse_audit_json`` fence-strips and validates shape.
  * Task 56 — ``_call_audit_llm`` uses Flash at low temperature, tolerates
    missing SDK + transient failures.
  * Task 57 — ``audit_against_contract`` happy path + safe fallback.
  * Task 58 — ``persist_audit_report`` writes to ``agent_audit_reports``.
  * Task 59 — ``attach_audit_summary_to_evidence`` updates checklist JSONB.
  * Task 72 — ``ops.audit.fail_on_any_unmet_criterion`` downgrades a
    pass verdict to fail/retry when any criterion is unmet.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import audit
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.runtime.types import (
    Artifact,
    AuditReport,
    ResearchResult,
    TaskContract,
    TodoItem,
)
from app.skills.registry import AgentID

# ---------------------------------------------------------------------------
# Helpers — contract fixtures
# ---------------------------------------------------------------------------


def _todo(title: str, description: str | None = None) -> TodoItem:
    return TodoItem(
        id=uuid4(),
        title=title,
        description=description,
        status="pending",
        evidence=[],
        sort_order=0,
    )


def _research_complete(summary: str = "research ok") -> ResearchResult:
    return ResearchResult(
        summary=summary,
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )


def _initiative_contract(
    todo_items: list[TodoItem] | None = None,
    success_criteria: list[str] | None = None,
    contract_id: UUID | None = None,
) -> TaskContract:
    return TaskContract(
        id=contract_id or uuid4(),
        source="initiative_step",
        goal="Produce Q3 forecast",
        todo_items=list(todo_items or []),
        success_criteria=list(success_criteria or []),
        owners=[AgentID.FIN],
        evidence_required=["draft_artifact"],
        initiative_id=uuid4(),
        initiative_phase="build",
        sibling_steps=[],
    )


def _ops() -> OperationsConfig:
    return OperationsConfig(agent_id="FIN")


# ---------------------------------------------------------------------------
# Task 54 — Prompt builder
# ---------------------------------------------------------------------------


def test_prompt_includes_every_todo_and_criterion() -> None:
    contract = _initiative_contract(
        todo_items=[
            _todo("Pull last 8 quarters"),
            _todo("Model 3 scenarios"),
        ],
        success_criteria=["3 scenarios documented", "Variance < 10%"],
    )

    prompt = audit._build_audit_prompt(
        contract=contract,
        artifacts=[Artifact(kind="doc", ref="vault://x", summary="draft", payload={})],
        research=_research_complete("research ok"),
    )

    assert "Pull last 8 quarters" in prompt
    assert "Model 3 scenarios" in prompt
    assert "3 scenarios documented" in prompt
    assert "Variance < 10%" in prompt
    assert "research ok" in prompt
    assert "vault://x" in prompt
    # Must demand strict JSON output.
    assert "ONLY" in prompt and "JSON" in prompt


def test_prompt_handles_empty_todos_and_criteria() -> None:
    contract = _initiative_contract(todo_items=[], success_criteria=[])
    prompt = audit._build_audit_prompt(
        contract=contract,
        artifacts=[],
        research=_research_complete(""),
    )
    assert "(no todo items)" in prompt
    assert "(none)" in prompt


def test_prompt_includes_todo_description_when_present() -> None:
    contract = _initiative_contract(
        todo_items=[_todo("Build forecast", description="Use last 8 quarters")],
        success_criteria=["accurate"],
    )
    prompt = audit._build_audit_prompt(
        contract=contract,
        artifacts=[],
        research=_research_complete(""),
    )
    assert "Use last 8 quarters" in prompt


# ---------------------------------------------------------------------------
# Task 55 — JSON parser
# ---------------------------------------------------------------------------


def _pass_audit_text(item_id: str | None = None) -> str:
    item_id = item_id or str(uuid4())
    return (
        "```json\n"
        '{"overall_status":"pass",'
        f'"per_item":[{{"item_id":"{item_id}","status":"pass",'
        '"evidence_pointers":["v1"],"gaps":[]}],'
        '"per_criterion":[{"criterion":"c1","met":true,"justification":"ok"}],'
        '"gaps":[],"recoverable":true,"next_action":"submit"}\n'
        "```"
    )


def test_parse_audit_pass() -> None:
    report = audit._parse_audit_json(_pass_audit_text())
    assert report is not None
    assert report.overall_status == "pass"
    assert report.next_action == "submit"
    assert report.per_item[0].status == "pass"


def test_parse_audit_returns_none_on_bad_json() -> None:
    assert audit._parse_audit_json("nope") is None


def test_parse_audit_returns_none_on_non_object() -> None:
    assert audit._parse_audit_json("[1,2,3]") is None


def test_parse_audit_returns_none_on_invalid_status() -> None:
    text = (
        '{"overall_status":"bogus","per_item":[],"per_criterion":[],'
        '"gaps":[],"recoverable":false,"next_action":"submit"}'
    )
    assert audit._parse_audit_json(text) is None


def test_parse_audit_defaults_empty_policy_violations() -> None:
    # No "policy_violations" key — parser must inject [] so model validates.
    text = (
        '{"overall_status":"fail","per_item":[],"per_criterion":[],'
        '"gaps":["x"],"recoverable":true,"next_action":"retry"}'
    )
    report = audit._parse_audit_json(text)
    assert report is not None
    assert report.policy_violations == []


# ---------------------------------------------------------------------------
# Task 56 — `_call_audit_llm`
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_audit_llm_returns_text(monkeypatch) -> None:
    captured: dict = {}

    async def fake_gen(model, contents, config):
        captured["model"] = model
        captured["temperature"] = config.temperature
        captured["max_output_tokens"] = config.max_output_tokens
        return MagicMock(text='{"ok": true}')

    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(side_effect=fake_gen)

    fake_genai = MagicMock()
    fake_genai.Client = MagicMock(return_value=fake_client)

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kw):
            cfg = MagicMock()
            cfg.temperature = kw.get("temperature")
            cfg.max_output_tokens = kw.get("max_output_tokens")
            return cfg

    monkeypatch.setattr(audit, "_load_genai", lambda: (fake_genai, FakeTypes))

    text = await audit._call_audit_llm("prompt")
    assert text == '{"ok": true}'
    assert captured["temperature"] is not None
    assert captured["temperature"] <= 0.2
    assert "flash" in captured["model"].lower()


@pytest.mark.asyncio
async def test_call_audit_llm_returns_none_when_sdk_missing(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_load_genai", lambda: None)
    assert await audit._call_audit_llm("prompt") is None


@pytest.mark.asyncio
async def test_call_audit_llm_returns_none_on_exception(monkeypatch) -> None:
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("boom")
    )

    fake_genai = MagicMock()
    fake_genai.Client = MagicMock(return_value=fake_client)

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kw):
            return MagicMock(**kw)

    monkeypatch.setattr(audit, "_load_genai", lambda: (fake_genai, FakeTypes))
    assert await audit._call_audit_llm("prompt") is None


@pytest.mark.asyncio
async def test_call_audit_llm_returns_none_on_empty_response(monkeypatch) -> None:
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(
        return_value=MagicMock(text="   ")
    )
    fake_genai = MagicMock()
    fake_genai.Client = MagicMock(return_value=fake_client)

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(**kw):
            return MagicMock(**kw)

    monkeypatch.setattr(audit, "_load_genai", lambda: (fake_genai, FakeTypes))
    assert await audit._call_audit_llm("prompt") is None


# ---------------------------------------------------------------------------
# Task 57 — `audit_against_contract` happy path + fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_returns_parsed_report(monkeypatch) -> None:
    contract = _initiative_contract(
        todo_items=[_todo("do a thing")],
        success_criteria=["c1"],
    )
    item_id = str(contract.todo_items[0].id)

    monkeypatch.setattr(
        audit,
        "_call_audit_llm",
        AsyncMock(
            return_value=(
                '{"overall_status":"pass",'
                f'"per_item":[{{"item_id":"{item_id}","status":"pass",'
                '"evidence_pointers":["v"],"gaps":[]}],'
                '"per_criterion":[{"criterion":"c1","met":true,"justification":"ok"}],'
                '"gaps":[],"recoverable":true,"next_action":"submit"}'
            )
        ),
    )

    report = await audit.audit_against_contract(
        contract,
        [Artifact(kind="doc", ref="v://x", summary="s", payload={})],
        _research_complete("s"),
        ops=_ops(),
    )
    assert report.overall_status == "pass"
    assert report.next_action == "submit"


@pytest.mark.asyncio
async def test_audit_falls_back_to_fail_when_llm_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_call_audit_llm", AsyncMock(return_value=None))

    report = await audit.audit_against_contract(
        _initiative_contract(todo_items=[_todo("x")], success_criteria=["c1"]),
        [],
        _research_complete("s"),
        ops=_ops(),
    )
    assert report.overall_status == "fail"
    assert report.next_action == "escalate"
    assert report.recoverable is False
    assert any("LLM unavailable" in g for g in report.gaps)


@pytest.mark.asyncio
async def test_audit_falls_back_to_fail_when_output_unparseable(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_call_audit_llm", AsyncMock(return_value="not json"))

    report = await audit.audit_against_contract(
        _initiative_contract(todo_items=[_todo("x")], success_criteria=["c1"]),
        [],
        _research_complete("s"),
        ops=_ops(),
    )
    assert report.overall_status == "fail"
    assert report.next_action == "escalate"
    assert any("unparseable" in g for g in report.gaps)


# ---------------------------------------------------------------------------
# Task 72 — `fail_on_any_unmet_criterion` overrides over-generous LLM pass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pass_downgraded_to_fail_when_criterion_unmet(monkeypatch) -> None:
    contract = _initiative_contract(
        todo_items=[_todo("x")],
        success_criteria=["c1"],
    )
    monkeypatch.setattr(
        audit,
        "_call_audit_llm",
        AsyncMock(
            return_value=(
                '{"overall_status":"pass","per_item":[],'
                '"per_criterion":[{"criterion":"c1","met":false,'
                '"justification":"weak"}],'
                '"gaps":["c1 unmet"],"recoverable":true,"next_action":"submit"}'
            )
        ),
    )

    ops = _ops()
    ops.audit.fail_on_any_unmet_criterion = True  # belt-and-braces

    report = await audit.audit_against_contract(
        contract,
        [Artifact(kind="doc", ref="r", summary="s", payload={})],
        _research_complete("s"),
        ops=ops,
    )
    assert report.overall_status == "fail"
    assert report.next_action == "retry"


@pytest.mark.asyncio
async def test_pass_preserved_when_flag_disabled(monkeypatch) -> None:
    # When the flag is False, an LLM "pass" with unmet criteria is left
    # alone — caller has explicitly opted out of strict enforcement.
    contract = _initiative_contract(todo_items=[_todo("x")], success_criteria=["c1"])
    monkeypatch.setattr(
        audit,
        "_call_audit_llm",
        AsyncMock(
            return_value=(
                '{"overall_status":"pass","per_item":[],'
                '"per_criterion":[{"criterion":"c1","met":false,'
                '"justification":"weak"}],'
                '"gaps":[],"recoverable":true,"next_action":"submit"}'
            )
        ),
    )

    ops = _ops()
    ops.audit.fail_on_any_unmet_criterion = False

    report = await audit.audit_against_contract(
        contract,
        [Artifact(kind="doc", ref="r", summary="s", payload={})],
        _research_complete("s"),
        ops=ops,
    )
    assert report.overall_status == "pass"
    assert report.next_action == "submit"


# ---------------------------------------------------------------------------
# Task 58 — `persist_audit_report`
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_audit_report_inserts_row(monkeypatch) -> None:
    contract_id = uuid4()
    row_id = uuid4()

    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(row_id)}]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    returned = await audit.persist_audit_report(
        report, agent_id=AgentID.FIN, task_contract_id=contract_id
    )
    assert isinstance(returned, UUID)
    assert returned == row_id

    payload = table_mock.insert.call_args[0][0]
    assert payload["agent_id"] == AgentID.FIN.value
    assert payload["task_contract_id"] == str(contract_id)
    assert payload["overall_status"] == "pass"
    assert payload["recoverable"] is True
    assert payload["next_action"] == "submit"
    assert payload["per_item"] == []
    assert payload["policy_violations"] == []


@pytest.mark.asyncio
async def test_persist_audit_report_serializes_nested_models(monkeypatch) -> None:
    contract_id = uuid4()
    row_id = uuid4()
    item_id = uuid4()

    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": str(row_id)}]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport.model_validate(
        {
            "overall_status": "partial",
            "per_item": [
                {
                    "item_id": str(item_id),
                    "status": "partial",
                    "evidence_pointers": ["v"],
                    "gaps": ["missing chart"],
                }
            ],
            "per_criterion": [
                {"criterion": "c1", "met": False, "justification": "weak"}
            ],
            "gaps": ["chart missing"],
            "policy_violations": [],
            "recoverable": True,
            "next_action": "retry",
        }
    )
    await audit.persist_audit_report(
        report, agent_id=AgentID.FIN, task_contract_id=contract_id
    )

    payload = table_mock.insert.call_args[0][0]
    # JSON-serializable nested rows.
    assert payload["per_item"][0]["item_id"] == str(item_id)
    assert payload["per_item"][0]["status"] == "partial"
    assert payload["per_criterion"][0]["met"] is False
    assert payload["gaps"] == ["chart missing"]


@pytest.mark.asyncio
async def test_persist_audit_report_raises_when_no_row_returned(monkeypatch) -> None:
    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[]))
    table_mock = MagicMock(insert=MagicMock(return_value=insert_mock))
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    with pytest.raises(RuntimeError, match="no row"):
        await audit.persist_audit_report(
            report, agent_id=AgentID.FIN, task_contract_id=uuid4()
        )


# ---------------------------------------------------------------------------
# Task 59 — `attach_audit_summary_to_evidence`
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_skips_when_source_not_initiative_step(monkeypatch) -> None:
    contract = TaskContract(
        id=uuid4(),
        source="department_task",
        goal="g",
        todo_items=[],
        success_criteria=[],
        owners=[],
        evidence_required=[],
        initiative_id=None,
        initiative_phase=None,
        sibling_steps=[],
    )
    table_mock = MagicMock()
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    await audit.attach_audit_summary_to_evidence(contract=contract, report=report)
    # Must not touch Supabase at all when the contract is not an initiative step.
    table_mock.update.assert_not_called()
    client.table.assert_not_called()


@pytest.mark.asyncio
async def test_attach_appends_audit_summary(monkeypatch) -> None:
    checklist_id = uuid4()
    contract = _initiative_contract(
        todo_items=[_todo("x")],
        success_criteria=["c1"],
        contract_id=checklist_id,
    )
    existing_evidence = [{"kind": "draft", "ref": "x"}]

    # Build a chainable select() mock — select().eq().single().execute()
    select_chain = MagicMock()
    select_chain.execute = AsyncMock(
        return_value=MagicMock(data={"evidence": existing_evidence})
    )
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)

    update_chain = MagicMock()
    update_chain.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": str(checklist_id)}])
    )
    update_chain.eq = MagicMock(return_value=update_chain)

    table_mock = MagicMock(
        select=MagicMock(return_value=select_chain),
        update=MagicMock(return_value=update_chain),
    )
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=["minor gap"],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )
    await audit.attach_audit_summary_to_evidence(contract=contract, report=report)

    payload = table_mock.update.call_args[0][0]
    new_evidence = payload["evidence"]
    # Existing evidence preserved.
    assert any(e.get("kind") == "draft" for e in new_evidence)
    # Audit summary appended.
    audit_summary = next(
        (e for e in new_evidence if e.get("kind") == "audit_summary"), None
    )
    assert audit_summary is not None
    assert audit_summary["overall_status"] == "pass"
    assert audit_summary["next_action"] == "submit"
    assert audit_summary["gaps"] == ["minor gap"]


@pytest.mark.asyncio
async def test_attach_handles_missing_evidence_column(monkeypatch) -> None:
    # Row exists but ``evidence`` is None/missing — must still write a
    # one-element list and not crash.
    checklist_id = uuid4()
    contract = _initiative_contract(
        todo_items=[_todo("x")], success_criteria=["c1"], contract_id=checklist_id
    )

    select_chain = MagicMock()
    select_chain.execute = AsyncMock(return_value=MagicMock(data={"evidence": None}))
    select_chain.eq = MagicMock(return_value=select_chain)
    select_chain.single = MagicMock(return_value=select_chain)

    update_chain = MagicMock()
    update_chain.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": str(checklist_id)}])
    )
    update_chain.eq = MagicMock(return_value=update_chain)

    table_mock = MagicMock(
        select=MagicMock(return_value=select_chain),
        update=MagicMock(return_value=update_chain),
    )
    client = MagicMock(table=MagicMock(return_value=table_mock))
    monkeypatch.setattr(audit, "_get_supabase", lambda: client)

    report = AuditReport(
        overall_status="fail",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="retry",
    )
    await audit.attach_audit_summary_to_evidence(contract=contract, report=report)

    payload = table_mock.update.call_args[0][0]
    assert payload["evidence"][0]["kind"] == "audit_summary"
    assert payload["evidence"][0]["overall_status"] == "fail"
