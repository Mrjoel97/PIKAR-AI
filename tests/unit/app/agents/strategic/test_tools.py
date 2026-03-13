import pytest
from unittest.mock import AsyncMock, patch

from app.agents.strategic.tools import start_initiative_from_idea


@pytest.mark.asyncio
async def test_start_initiative_from_idea_with_braindump():
    with (
        patch('app.agents.tools.brain_dump.get_braindump_document', new_callable=AsyncMock) as mock_get_braindump,
        patch('app.services.request_context.get_current_user_id', return_value='test_user_id'),
        patch('app.autonomy.kernel.AutonomyKernel.orchestrate_idea_to_venture', new_callable=AsyncMock) as mock_orchestrate,
    ):
        mock_get_braindump.return_value = {"content": "This is a test brain dump"}
        mock_orchestrate.return_value = {
            "initiative": {"id": "test_initiative_id"},
            "initiative_id": "test_initiative_id",
            "workflow_execution_id": "exec-1",
            "template_name": "Idea-to-Venture",
            "blockers": [],
            "next_actions": ["Do the thing"],
            "trust_summary": {},
            "verification_status": "pending",
        }

        result = await start_initiative_from_idea(braindump_id="test_braindump_id")

        assert result["success"] is True
        assert result["initiative"]["id"] == "test_initiative_id"
        mock_get_braindump.assert_called_once_with("test_braindump_id")
        mock_orchestrate.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_initiative_from_idea_without_braindump():
    with (
        patch('app.services.request_context.get_current_user_id', return_value='test_user_id'),
        patch('app.autonomy.kernel.AutonomyKernel.orchestrate_idea_to_venture', new_callable=AsyncMock) as mock_orchestrate,
    ):
        mock_orchestrate.return_value = {
            "initiative": {"id": "test_initiative_id"},
            "initiative_id": "test_initiative_id",
            "workflow_execution_id": None,
            "template_name": None,
            "blockers": [{"message": "Missing template"}],
            "next_actions": ["Fix template"],
            "trust_summary": {"last_failure_reason": "Missing template"},
            "verification_status": "blocked",
        }

        result = await start_initiative_from_idea(idea="Test Idea", context="Test Context")

        assert result["success"] is True
        assert result["initiative"]["id"] == "test_initiative_id"
        assert result["blockers"][0]["message"] == "Missing template"
        mock_orchestrate.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_initiative_from_idea_with_braindump_error():
    with patch('app.agents.tools.brain_dump.get_braindump_document', new_callable=AsyncMock) as mock_get_braindump:
        mock_get_braindump.return_value = {"error": "Test Error"}

        result = await start_initiative_from_idea(braindump_id="test_braindump_id")

        assert result["success"] is False
        assert result["error"] == "Test Error"
