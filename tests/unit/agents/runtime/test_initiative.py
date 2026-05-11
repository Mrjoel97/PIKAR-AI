# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for :mod:`app.agents.runtime.initiative` (tasks 94-99).

Coverage:
    * Task 94: ``start_initiative`` raises ``InitiativeContractError`` when
      ``goal`` / ``success_criteria`` / ``owners`` are missing.
    * Task 95: ``start_initiative`` creates the row, seeds operational state,
      and emits a start report via ``publication.publish_artifact``.
    * Task 96: ``advance_phase`` blocks when any checklist item in the
      current phase is not ``completed`` / ``skipped``.
    * Task 97: ``advance_phase`` advances and emits a phase-advance report
      when the audit passes.
    * Task 98: ``close_initiative`` raises when phase != 'scale' or when the
      scale-phase checklist still has open items.
    * Task 99: ``close_initiative`` returns a structured ``CloseReport``,
      vaults it, and marks the initiative ``completed`` / ``progress=100``.

External dependencies (``InitiativeService``, ``publication``) are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.agents.runtime import initiative
from app.agents.runtime.initiative import (
    AdvanceResult,
    CloseReport,
)
from app.agents.runtime.types import Artifact, InitiativeContractError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_agent() -> MagicMock:
    """Return a minimal agent stub exposing the attributes the rituals read."""
    agent = MagicMock()
    agent.user_id = uuid4()
    agent.agent_id = "executive"
    return agent


class _PublicationResult:
    """Lightweight stand-in for publication.PublicationResult."""

    def __init__(
        self,
        *,
        execution_id: UUID | None = None,
        vault_document_id: UUID | None = None,
        workspace_event_emitted: bool = True,
    ) -> None:
        self.execution_id = execution_id
        self.vault_document_id = vault_document_id
        self.workspace_event_emitted = workspace_event_emitted


def _install_service(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch ``InitiativeService`` to return a fresh ``MagicMock`` instance.

    Returns the service mock so tests can attach awaitable methods.
    """
    service = MagicMock()
    monkeypatch.setattr(
        initiative, "InitiativeService", MagicMock(return_value=service)
    )
    return service


def _install_publication(
    monkeypatch: pytest.MonkeyPatch,
    *,
    publish_result: _PublicationResult | None = None,
) -> tuple[AsyncMock, AsyncMock]:
    """Patch the publication submodule with awaitable mocks.

    Returns ``(publish_artifact_mock, render_report_markdown_mock)``.
    """
    publish = AsyncMock(return_value=publish_result or _PublicationResult())
    render = AsyncMock(return_value="# stub report")
    monkeypatch.setattr(initiative.publication, "publish_artifact", publish)
    monkeypatch.setattr(initiative.publication, "render_report_markdown", render)
    return publish, render


# ---------------------------------------------------------------------------
# Task 94 — input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_initiative_requires_goal() -> None:
    """Empty/blank ``goal`` must raise ``InitiativeContractError`` with 'goal'."""
    agent = _mock_agent()
    with pytest.raises(InitiativeContractError, match="goal"):
        await initiative.start_initiative(
            agent,
            goal="",
            success_criteria=["x"],
            owners=["financial"],
        )

    with pytest.raises(InitiativeContractError, match="goal"):
        await initiative.start_initiative(
            agent,
            goal="   ",
            success_criteria=["x"],
            owners=["financial"],
        )


@pytest.mark.asyncio
async def test_start_initiative_requires_success_criteria() -> None:
    """Empty ``success_criteria`` must raise with that exact field name."""
    agent = _mock_agent()
    with pytest.raises(InitiativeContractError, match="success_criteria"):
        await initiative.start_initiative(
            agent,
            goal="ship it",
            success_criteria=[],
            owners=["financial"],
        )


@pytest.mark.asyncio
async def test_start_initiative_requires_owners() -> None:
    """Empty ``owners`` must raise with that exact field name."""
    agent = _mock_agent()
    with pytest.raises(InitiativeContractError, match="owners"):
        await initiative.start_initiative(
            agent,
            goal="ship it",
            success_criteria=["x"],
            owners=[],
        )


@pytest.mark.asyncio
async def test_start_initiative_rejects_invalid_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phase outside ``INITIATIVE_PHASES`` must raise."""
    _install_service(monkeypatch)
    _install_publication(monkeypatch)
    agent = _mock_agent()

    with pytest.raises(InitiativeContractError, match="phase"):
        await initiative.start_initiative(
            agent,
            goal="ship it",
            success_criteria=["x"],
            owners=["financial"],
            phase="not_a_real_phase",
        )


# ---------------------------------------------------------------------------
# Task 95 — happy path create + seed + publish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_initiative_calls_service_and_seeds_op_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy-path: row created, op state seeded, report published as ``kind='report'``."""
    agent = _mock_agent()
    created = {
        "id": str(uuid4()),
        "title": "Forecast Q3",
        "phase": "ideation",
    }

    service = _install_service(monkeypatch)
    service.create_initiative = AsyncMock(return_value=created)
    service.update_operational_state = AsyncMock(return_value=created)

    publish, render = _install_publication(monkeypatch)

    result = await initiative.start_initiative(
        agent,
        goal="Forecast Q3 revenue",
        success_criteria=["+/-5%", "three scenarios"],
        owners=["financial", "data"],
    )

    assert result["id"] == created["id"]
    service.create_initiative.assert_awaited_once()
    create_kwargs = service.create_initiative.await_args.kwargs
    assert create_kwargs["title"] == "Forecast Q3 revenue"
    assert create_kwargs["description"] == "Forecast Q3 revenue"
    assert create_kwargs["phase"] == "ideation"
    assert (
        create_kwargs["metadata"]["success_criteria"]
        == ["+/-5%", "three scenarios"]
    )

    service.update_operational_state.assert_awaited_once()
    state_kwargs = service.update_operational_state.await_args.kwargs
    assert state_kwargs["goal"] == "Forecast Q3 revenue"
    assert state_kwargs["success_criteria"] == ["+/-5%", "three scenarios"]
    assert state_kwargs["owner_agents"] == ["financial", "data"]
    assert state_kwargs["current_phase"] == "ideation"

    publish.assert_awaited_once()
    publish_kwargs = publish.await_args.kwargs
    artifact = publish_kwargs["artifact"]
    assert isinstance(artifact, Artifact)
    assert artifact.kind == "report"
    assert artifact.ref.startswith("initiative_start://")
    assert "Forecast Q3 revenue" in artifact.summary
    # render_report_markdown should have been called once to render the report.
    render.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_initiative_uses_explicit_name_when_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``name`` is provided, ``title`` falls back to it instead of ``goal``."""
    agent = _mock_agent()
    created = {"id": str(uuid4()), "title": "Q3 Plan", "phase": "ideation"}
    service = _install_service(monkeypatch)
    service.create_initiative = AsyncMock(return_value=created)
    service.update_operational_state = AsyncMock(return_value=created)
    _install_publication(monkeypatch)

    await initiative.start_initiative(
        agent,
        goal="Forecast Q3 revenue with three scenarios",
        success_criteria=["x"],
        owners=["financial"],
        name="Q3 Plan",
    )

    assert service.create_initiative.await_args.kwargs["title"] == "Q3 Plan"


# ---------------------------------------------------------------------------
# Task 96 — advance_phase blocks on pending checklist items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_advance_phase_blocks_when_items_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pending checklist items must block the advance and surface gaps."""
    initiative_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.list_checklist_items = AsyncMock(
        return_value=[
            {
                "id": str(uuid4()),
                "status": "pending",
                "title": "Need draft",
            },
            {
                "id": str(uuid4()),
                "status": "completed",
                "title": "Done",
            },
        ]
    )
    service.advance_phase = AsyncMock()
    service.get_initiative = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "validation"}
    )
    publish, _ = _install_publication(monkeypatch)

    result = await initiative.advance_phase(
        agent, initiative_id=initiative_id, current_phase="validation"
    )

    assert isinstance(result, AdvanceResult)
    assert result.advanced is False
    assert result.new_phase is None
    assert any("Need draft" in gap for gap in result.gaps)
    assert any("pending" in gap for gap in result.gaps)
    service.advance_phase.assert_not_awaited()
    publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_phase_treats_skipped_items_as_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``status='skipped'`` should NOT block an advance."""
    initiative_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.list_checklist_items = AsyncMock(
        return_value=[
            {"id": str(uuid4()), "status": "skipped", "title": "Skipped"},
            {"id": str(uuid4()), "status": "completed", "title": "Done"},
        ]
    )
    service.advance_phase = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "build"}
    )
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "validation",
            "title": "X",
            "metadata": {},
        }
    )
    _install_publication(monkeypatch)

    result = await initiative.advance_phase(
        agent, initiative_id=initiative_id, current_phase="validation"
    )
    assert result.advanced is True
    assert result.new_phase == "build"


@pytest.mark.asyncio
async def test_advance_phase_rejects_invalid_phase() -> None:
    """``current_phase`` outside ``INITIATIVE_PHASES`` raises."""
    agent = _mock_agent()
    with pytest.raises(InitiativeContractError, match="phase"):
        await initiative.advance_phase(
            agent, initiative_id=uuid4(), current_phase="bogus"
        )


# ---------------------------------------------------------------------------
# Task 97 — advance_phase happy path with report emission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_advance_phase_emits_phase_advance_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the audit passes, a phase-advance report is published."""
    initiative_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.list_checklist_items = AsyncMock(
        return_value=[
            {"id": str(uuid4()), "status": "completed", "title": "Built draft"}
        ]
    )
    service.advance_phase = AsyncMock(
        return_value={"id": str(initiative_id), "phase": "build"}
    )
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "validation",
            "title": "Forecast Q3",
            "metadata": {
                "operational_state": {
                    "goal": "Forecast Q3",
                    "success_criteria": ["+/-5%"],
                    "owner_agents": ["financial"],
                }
            },
        }
    )
    publish, render = _install_publication(
        monkeypatch,
        publish_result=_PublicationResult(
            execution_id=uuid4(),
            vault_document_id=uuid4(),
            workspace_event_emitted=True,
        ),
    )

    result = await initiative.advance_phase(
        agent, initiative_id=initiative_id, current_phase="validation"
    )

    assert result.advanced is True
    assert result.new_phase == "build"
    assert result.gaps == []

    publish.assert_awaited_once()
    artifact = publish.await_args.kwargs["artifact"]
    assert isinstance(artifact, Artifact)
    assert artifact.kind == "report"
    assert artifact.ref.startswith("phase_advance://")
    assert "build" in artifact.summary
    render.assert_awaited_once()


# ---------------------------------------------------------------------------
# Task 98 — close_initiative gating
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_blocked_when_not_in_scale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing before reaching ``'scale'`` raises with that word in the message."""
    initiative_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "build",
            "metadata": {},
        }
    )
    _install_publication(monkeypatch)

    with pytest.raises(InitiativeContractError, match="scale"):
        await initiative.close_initiative(agent, initiative_id=initiative_id)


@pytest.mark.asyncio
async def test_close_blocked_when_scale_items_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Open items in the scale phase block close with 'checklist' in the message."""
    initiative_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "scale",
            "metadata": {},
        }
    )
    service.list_checklist_items = AsyncMock(
        return_value=[
            {"id": str(uuid4()), "status": "pending", "title": "Open item"}
        ]
    )
    _install_publication(monkeypatch)

    with pytest.raises(InitiativeContractError, match="checklist"):
        await initiative.close_initiative(agent, initiative_id=initiative_id)


@pytest.mark.asyncio
async def test_close_blocked_when_initiative_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``get_initiative`` returning falsy raises a 'not found' error."""
    agent = _mock_agent()
    service = _install_service(monkeypatch)
    service.get_initiative = AsyncMock(return_value=None)
    _install_publication(monkeypatch)

    with pytest.raises(InitiativeContractError, match="not found"):
        await initiative.close_initiative(agent, initiative_id=uuid4())


# ---------------------------------------------------------------------------
# Task 99 — close_initiative produces structured CloseReport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_initiative_vaults_and_marks_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy-path close → CloseReport with outcomes, vault id, status=completed/100."""
    initiative_id = uuid4()
    vault_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "scale",
            "metadata": {
                "operational_state": {
                    "goal": "Launch v1",
                    "success_criteria": ["NPS>40", "<1% churn"],
                    "owner_agents": ["marketing", "operations"],
                    "learnings": ["Iterate weekly"],
                    "next_actions": ["Plan v2"],
                }
            },
        }
    )
    service.list_checklist_items = AsyncMock(return_value=[])
    service.update_initiative = AsyncMock(
        return_value={"id": str(initiative_id), "status": "completed"}
    )
    publish, _ = _install_publication(
        monkeypatch,
        publish_result=_PublicationResult(
            execution_id=uuid4(),
            vault_document_id=vault_id,
            workspace_event_emitted=True,
        ),
    )

    report = await initiative.close_initiative(
        agent, initiative_id=initiative_id
    )

    assert isinstance(report, CloseReport)
    assert report.initiative_id == initiative_id
    assert report.vault_document_id == vault_id
    assert len(report.outcomes) == 2
    assert {o["criterion"] for o in report.outcomes} == {"NPS>40", "<1% churn"}
    assert report.learnings == ["Iterate weekly"]
    assert report.follow_ups == ["Plan v2"]
    assert len(report.artifacts) == 1
    assert report.artifacts[0].kind == "report"
    assert report.artifacts[0].ref.startswith("initiative_close://")

    publish.assert_awaited_once()
    publish_kwargs = publish.await_args.kwargs
    assert publish_kwargs["artifact"].kind == "report"

    service.update_initiative.assert_awaited_once()
    update_kwargs = service.update_initiative.await_args.kwargs
    assert update_kwargs["status"] == "completed"
    assert update_kwargs["progress"] == 100


@pytest.mark.asyncio
async def test_close_initiative_skipped_items_are_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``status='skipped'`` scale items do NOT block close."""
    initiative_id = uuid4()
    agent = _mock_agent()

    service = _install_service(monkeypatch)
    service.get_initiative = AsyncMock(
        return_value={
            "id": str(initiative_id),
            "phase": "scale",
            "metadata": {
                "operational_state": {
                    "goal": "Launch",
                    "success_criteria": ["one"],
                    "owner_agents": ["operations"],
                }
            },
        }
    )
    service.list_checklist_items = AsyncMock(
        return_value=[
            {"id": str(uuid4()), "status": "skipped", "title": "x"},
            {"id": str(uuid4()), "status": "completed", "title": "y"},
        ]
    )
    service.update_initiative = AsyncMock(return_value={"id": str(initiative_id)})
    _install_publication(monkeypatch)

    report = await initiative.close_initiative(
        agent, initiative_id=initiative_id
    )
    assert isinstance(report, CloseReport)
    assert len(report.outcomes) == 1
