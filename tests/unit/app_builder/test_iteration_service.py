"""Unit tests for iteration_service — screen edit, design system injection, iteration tracking."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
TEST_SCREEN_ID = "cccccccc-0000-0000-0000-000000000001"
TEST_STITCH_PROJECT_ID = "stitch-proj-001"
TEST_STITCH_SCREEN_ID = "stitch-screen-001"
TEST_VARIANT_ID = "vvvvvvvv-0000-0000-0000-000000000001"
TEST_NEW_STITCH_SCREEN_ID = "stitch-screen-002"

STITCH_EDIT_RESPONSE = {
    "screenId": TEST_NEW_STITCH_SCREEN_ID,
    "html_url": "https://temp.stitch.dev/html",
    "screenshot_url": "https://temp.stitch.dev/screenshot.png",
}

PERSISTED_URLS = {
    "html_url": "https://supabase.co/storage/html",
    "screenshot_url": "https://supabase.co/storage/screenshot.png",
}


def _make_supabase_mock(iteration_rows: list[dict] | None = None) -> MagicMock:
    """Return a MagicMock mimicking the Supabase service client chain."""
    client = MagicMock()

    # insert().execute() -> data=[{id: variant_id}]
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_VARIANT_ID}]
    )

    # update().eq().eq().execute() -> data=[{id: variant_id}]
    client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_VARIANT_ID}]
    )
    # update().eq().neq().execute() (deselect others pattern)
    client.table.return_value.update.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    # select().eq().order().execute() -> returns iteration rows
    rows = iteration_rows or [{"iteration": 1}]
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=rows
    )

    # design_systems: select().eq().eq().execute()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    return client


def _make_stitch_mock(response: dict | None = None) -> MagicMock:
    """Return a mock StitchMCPService with call_tool as AsyncMock."""
    service = MagicMock()
    service.call_tool = AsyncMock(return_value=response or STITCH_EDIT_RESPONSE)
    return service


# ---------------------------------------------------------------------------
# Test 1 — edit_screen_variant yields correct event sequence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_yields_correct_events():
    """edit_screen_variant yields: editing -> edit_complete -> ready."""
    from app.services.iteration_service import edit_screen_variant

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.iteration_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.iteration_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.iteration_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.iteration_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_VARIANT_ID),
        ),
    ):
        events = []
        async for event in edit_screen_variant(
            project_id=TEST_PROJECT_ID,
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            stitch_screen_id=TEST_STITCH_SCREEN_ID,
            change_description="Make the hero section taller",
            design_system_markdown=None,
            iteration_number=2,
        ):
            events.append(event)

    steps = [e["step"] for e in events]
    assert steps == ["editing", "edit_complete", "ready"]

    edit_complete = next(e for e in events if e["step"] == "edit_complete")
    assert "variant_id" in edit_complete
    assert "screenshot_url" in edit_complete
    assert "html_url" in edit_complete
    assert "iteration" in edit_complete
    assert edit_complete["screenshot_url"] == PERSISTED_URLS["screenshot_url"]
    assert edit_complete["html_url"] == PERSISTED_URLS["html_url"]
    assert edit_complete["iteration"] == 2
    assert edit_complete["screen_id"] == TEST_SCREEN_ID

    ready = next(e for e in events if e["step"] == "ready")
    assert ready["screen_id"] == TEST_SCREEN_ID
    assert ready["iteration"] == 2


# ---------------------------------------------------------------------------
# Test 2 — edit_screens called with selectedScreenIds as array
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_screens_called_with_array():
    """service.call_tool('edit_screens') receives selectedScreenIds as a list, not a bare string."""
    from app.services.iteration_service import edit_screen_variant

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.iteration_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.iteration_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.iteration_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.iteration_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_VARIANT_ID),
        ),
    ):
        async for _ in edit_screen_variant(
            project_id=TEST_PROJECT_ID,
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            stitch_screen_id=TEST_STITCH_SCREEN_ID,
            change_description="Change background to blue",
            design_system_markdown=None,
            iteration_number=2,
        ):
            pass

    # The first call should be edit_screens
    edit_call = mock_stitch.call_tool.call_args_list[0]
    tool_name = edit_call.args[0]
    arguments = edit_call.args[1]

    assert tool_name == "edit_screens"
    assert isinstance(arguments["selectedScreenIds"], list)
    assert arguments["selectedScreenIds"] == [TEST_STITCH_SCREEN_ID]
    assert arguments["projectId"] == TEST_STITCH_PROJECT_ID


# ---------------------------------------------------------------------------
# Test 3 — design system injected when locked (non-None markdown)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_design_system_injected_when_locked():
    """When design_system_markdown is provided, prompt is prefixed with the markdown."""
    from app.services.iteration_service import edit_screen_variant

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()
    design_markdown = "# Design System\n## Colors: #F5E6D3"

    with (
        patch(
            "app.services.iteration_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.iteration_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.iteration_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.iteration_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_VARIANT_ID),
        ),
    ):
        async for _ in edit_screen_variant(
            project_id=TEST_PROJECT_ID,
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            stitch_screen_id=TEST_STITCH_SCREEN_ID,
            change_description="Make hero taller",
            design_system_markdown=design_markdown,
            iteration_number=2,
        ):
            pass

    edit_call = mock_stitch.call_tool.call_args_list[0]
    arguments = edit_call.args[1]
    prompt = arguments["prompt"]

    assert prompt.startswith(design_markdown)
    assert "\n\nEdits: Make hero taller" in prompt


# ---------------------------------------------------------------------------
# Test 4 — no injection when design_system_markdown is None (unlocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_injection_when_unlocked():
    """When design_system_markdown is None, prompt is exactly the change description."""
    from app.services.iteration_service import edit_screen_variant

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.iteration_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.iteration_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.iteration_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.iteration_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_VARIANT_ID),
        ),
    ):
        async for _ in edit_screen_variant(
            project_id=TEST_PROJECT_ID,
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            stitch_screen_id=TEST_STITCH_SCREEN_ID,
            change_description="Make hero taller",
            design_system_markdown=None,
            iteration_number=2,
        ):
            pass

    edit_call = mock_stitch.call_tool.call_args_list[0]
    arguments = edit_call.args[1]
    prompt = arguments["prompt"]

    assert prompt == "Make hero taller"


# ---------------------------------------------------------------------------
# Test 5 — iteration number is stored correctly in the new variants row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iteration_number_incremented():
    """The new screen_variants row is inserted with the given iteration_number."""
    from app.services.iteration_service import edit_screen_variant

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()
    inserted_data: list[dict] = []

    original_insert = mock_supabase.table.return_value.insert

    def tracking_insert(data: dict) -> MagicMock:
        """Track inserts for assertion."""
        if "iteration" in data:
            inserted_data.append(data)
        return original_insert.return_value

    mock_supabase.table.return_value.insert = tracking_insert

    with (
        patch(
            "app.services.iteration_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.iteration_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.iteration_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.iteration_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_VARIANT_ID),
        ),
    ):
        async for _ in edit_screen_variant(
            project_id=TEST_PROJECT_ID,
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            stitch_screen_id=TEST_STITCH_SCREEN_ID,
            change_description="Make hero taller",
            design_system_markdown=None,
            iteration_number=3,
        ):
            pass

    assert len(inserted_data) >= 1
    assert inserted_data[0]["iteration"] == 3
    assert inserted_data[0]["is_selected"] is True
    assert inserted_data[0]["stitch_screen_id"] == TEST_NEW_STITCH_SCREEN_ID


# ---------------------------------------------------------------------------
# Test 6 — _get_locked_design_markdown returns raw_markdown when locked, None when not
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_locked_design_markdown_returns_raw():
    """_get_locked_design_markdown returns raw_markdown when locked=True, None when locked=False."""
    from app.services.iteration_service import _get_locked_design_markdown

    mock_supabase_locked = MagicMock()
    mock_supabase_locked.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"locked": True, "raw_markdown": "# Design System"}]
    )

    mock_supabase_unlocked = MagicMock()
    mock_supabase_unlocked.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"locked": False, "raw_markdown": "# Design System"}]
    )

    mock_supabase_none = MagicMock()
    mock_supabase_none.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    # locked=True -> returns raw_markdown
    with patch(
        "app.services.iteration_service.get_service_client",
        return_value=mock_supabase_locked,
    ):
        result = await _get_locked_design_markdown(TEST_PROJECT_ID, TEST_USER_ID)
    assert result == "# Design System"

    # locked=False -> returns None
    with patch(
        "app.services.iteration_service.get_service_client",
        return_value=mock_supabase_unlocked,
    ):
        result = await _get_locked_design_markdown(TEST_PROJECT_ID, TEST_USER_ID)
    assert result is None

    # No row -> returns None
    with patch(
        "app.services.iteration_service.get_service_client",
        return_value=mock_supabase_none,
    ):
        result = await _get_locked_design_markdown(TEST_PROJECT_ID, TEST_USER_ID)
    assert result is None


# ---------------------------------------------------------------------------
# Test 7 — edit_screens fallback: if html_url missing, calls get_screen
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_screens_fallback_get_screen():
    """When edit_screens response lacks html_url/htmlUrl, get_screen is called as fallback."""
    from app.services.iteration_service import edit_screen_variant

    # Response without html_url
    no_html_response = {
        "screenId": TEST_NEW_STITCH_SCREEN_ID,
        # no html_url or htmlUrl
        "screenshot_url": "https://temp.stitch.dev/screenshot.png",
    }
    # get_screen response with full URLs
    get_screen_response = {
        "screenId": TEST_NEW_STITCH_SCREEN_ID,
        "html_url": "https://temp.stitch.dev/html_via_get",
        "screenshot_url": "https://temp.stitch.dev/screenshot.png",
    }

    mock_supabase = _make_supabase_mock()
    mock_stitch = MagicMock()
    mock_stitch.call_tool = AsyncMock(
        side_effect=[no_html_response, get_screen_response]
    )

    with (
        patch(
            "app.services.iteration_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.iteration_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.iteration_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.iteration_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_VARIANT_ID),
        ),
    ):
        async for _ in edit_screen_variant(
            project_id=TEST_PROJECT_ID,
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            stitch_screen_id=TEST_STITCH_SCREEN_ID,
            change_description="Make hero taller",
            design_system_markdown=None,
            iteration_number=2,
        ):
            pass

    # Two calls: edit_screens + get_screen fallback
    assert mock_stitch.call_tool.await_count == 2
    second_call = mock_stitch.call_tool.call_args_list[1]
    assert second_call.args[0] == "get_screen"
    get_screen_args = second_call.args[1]
    assert get_screen_args["screenId"] == TEST_NEW_STITCH_SCREEN_ID
    assert get_screen_args["projectId"] == TEST_STITCH_PROJECT_ID
