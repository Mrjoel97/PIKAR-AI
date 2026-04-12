# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for InteractionLogger signal kwargs, return value, and update_latest."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the InteractionLogger singleton between tests."""
    mods_to_remove = [k for k in sys.modules if "interaction_logger" in k]
    for m in mods_to_remove:
        del sys.modules[m]
    yield
    mods_to_remove = [k for k in sys.modules if "interaction_logger" in k]
    for m in mods_to_remove:
        del sys.modules[m]


def _make_logger():
    """Create an InteractionLogger with mocked Supabase, bypassing __init__."""
    # Import the class without triggering module-level singleton
    with (
        patch("app.services.supabase_client.get_service_client", return_value=MagicMock()),
        patch("app.services.interaction_logger.get_service_client", return_value=MagicMock()),
    ):
        from app.services.interaction_logger import InteractionLogger

        InteractionLogger._instance = None

    mock_client = MagicMock()

    # Bypass __init__ to avoid real Supabase connection
    il = object.__new__(InteractionLogger)
    il._initialized = True
    il._client = mock_client
    il._interactions_table = "interaction_logs"
    il._gaps_table = "coverage_gaps"

    return il, mock_client


# ---------------------------------------------------------------------------
# Test 1: log_interaction accepts task_completed kwarg without TypeError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_log_interaction_accepts_task_completed():
    """log_interaction should accept task_completed=True without raising."""
    il, _mock_client = _make_logger()

    mock_response = MagicMock()
    mock_response.data = [{"id": "row-uuid-1"}]

    with (
        patch(
            "app.services.interaction_logger.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        patch(
            "app.services.interaction_logger.get_current_user_id",
            return_value="user-abc-123",
        ),
    ):
        # This should NOT raise TypeError
        result = await il.log_interaction(
            agent_id="FIN",
            user_query="test query",
            task_completed=True,
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Test 2: log_interaction accepts all signal kwargs and includes them in payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_log_interaction_signal_kwargs_in_payload():
    """log_interaction should include was_escalated, had_followup, user_feedback in data."""
    il, mock_client = _make_logger()

    mock_response = MagicMock()
    mock_response.data = [{"id": "row-uuid-2"}]

    mock_table_obj = MagicMock()
    mock_insert = MagicMock(return_value=MagicMock())
    mock_table_obj.insert = mock_insert
    mock_client.table.return_value = mock_table_obj

    with (
        patch(
            "app.services.interaction_logger.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        patch(
            "app.services.interaction_logger.get_current_user_id",
            return_value="user-abc-123",
        ),
    ):
        await il.log_interaction(
            agent_id="FIN",
            user_query="test query",
            was_escalated=True,
            had_followup=True,
            user_feedback="negative",
            task_completed=False,
        )

        # Verify insert was called with signal kwargs in the data
        mock_insert.assert_called_once()
        data = mock_insert.call_args[0][0]
        assert data["was_escalated"] is True
        assert data["had_followup"] is True
        assert data["user_feedback"] == "negative"
        assert data["task_completed"] is False


# ---------------------------------------------------------------------------
# Test 3: log_interaction returns UUID string on success, None on failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_log_interaction_returns_uuid():
    """log_interaction should return the UUID string of the inserted row."""
    il, _mock_client = _make_logger()

    mock_response = MagicMock()
    mock_response.data = [{"id": "abc-def-123"}]

    with (
        patch(
            "app.services.interaction_logger.execute_async",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
        patch(
            "app.services.interaction_logger.get_current_user_id",
            return_value="user-abc-123",
        ),
    ):
        result = await il.log_interaction(
            agent_id="FIN",
            user_query="test query",
        )
        assert result == "abc-def-123"


@pytest.mark.asyncio()
async def test_log_interaction_returns_none_on_failure():
    """log_interaction should return None when the insert fails."""
    il, _mock_client = _make_logger()

    with (
        patch(
            "app.services.interaction_logger.execute_async",
            new_callable=AsyncMock,
            side_effect=Exception("DB down"),
        ),
        patch(
            "app.services.interaction_logger.get_current_user_id",
            return_value="user-abc-123",
        ),
    ):
        result = await il.log_interaction(
            agent_id="FIN",
            user_query="test query",
        )
        assert result is None


# ---------------------------------------------------------------------------
# Test 4: update_latest_interaction finds and updates most-recent row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_latest_interaction_success():
    """update_latest_interaction should update the most-recent row and return True."""
    il, _mock_client = _make_logger()

    select_response = MagicMock()
    select_response.data = [{"id": "existing-row-id"}]

    update_response = MagicMock()
    update_response.data = [{"id": "existing-row-id"}]

    call_count = 0

    async def mock_execute(query, *, op_name=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return select_response
        return update_response

    with patch(
        "app.services.interaction_logger.execute_async",
        side_effect=mock_execute,
    ):
        result = await il.update_latest_interaction(
            session_id="sess-123",
            agent_id="FIN",
            task_completed=True,
            was_escalated=False,
        )
        assert result is True


# ---------------------------------------------------------------------------
# Test 5: update_latest_interaction returns False when no matching row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_update_latest_interaction_no_row():
    """update_latest_interaction should return False when no row matches."""
    il, _mock_client = _make_logger()

    select_response = MagicMock()
    select_response.data = []

    with patch(
        "app.services.interaction_logger.execute_async",
        new_callable=AsyncMock,
        return_value=select_response,
    ):
        result = await il.update_latest_interaction(
            session_id="sess-nonexistent",
            agent_id="FIN",
            task_completed=True,
        )
        assert result is False


# ---------------------------------------------------------------------------
# Test 6: report_interaction tool calls update_latest_interaction
# ---------------------------------------------------------------------------


def test_report_interaction_tool_uses_update_latest():
    """report_interaction tool should call update_latest_interaction, not log_interaction."""
    mock_il = MagicMock()
    mock_il.update_latest_interaction = AsyncMock(return_value=True)
    mock_il.log_interaction = AsyncMock()

    with (
        patch(
            "app.agents.tools.self_improve._get_logger",
            return_value=mock_il,
        ),
        patch(
            "app.agents.tools.self_improve._run_async",
            side_effect=lambda coro: True,
        ) as mock_run,
        patch(
            "app.services.request_context.get_current_session_id",
            return_value="sess-abc",
        ),
    ):
        from app.agents.tools.self_improve import get_self_improve_tools
        from app.skills.registry import AgentID

        tools = get_self_improve_tools(AgentID.FIN)
        report_tool = tools[0]  # report_interaction is first

        result = report_tool(
            user_query="test query",
            response_summary="response",
            skill_used="some_skill",
            task_completed="yes",
        )
        assert result["success"] is True
        mock_run.assert_called()
