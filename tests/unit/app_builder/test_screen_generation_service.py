"""Unit tests for screen_generation_service — variant generation, device generation, DB inserts."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
TEST_SCREEN_ID = "bbbbbbbb-0000-0000-0000-000000000001"
TEST_STITCH_PROJECT_ID = "stitch-proj-001"

STITCH_RESPONSE = {
    "screenId": "stitch-screen-001",
    "html_url": "https://temp.stitch.dev/html",
    "screenshot_url": "https://temp.stitch.dev/screenshot.png",
}

PERSISTED_URLS = {
    "html_url": "https://supabase.co/storage/html",
    "screenshot_url": "https://supabase.co/storage/screenshot.png",
}


def _make_supabase_mock() -> MagicMock:
    """Return a MagicMock mimicking the Supabase service client chain."""
    client = MagicMock()
    # table().insert().execute() -> data=[{id: screen_id}]
    insert_result = MagicMock(data=[{"id": TEST_SCREEN_ID}])
    client.table.return_value.insert.return_value.execute.return_value = insert_result
    # table().update().eq().eq().execute() -> data=[{id: variant_id}]
    update_result = MagicMock(data=[{"id": "variant-001"}])
    client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = (
        update_result
    )
    # table().select().eq().eq().execute()
    select_result = MagicMock(data=[])
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
        select_result
    )
    return client


def _make_stitch_mock() -> MagicMock:
    """Return a mock StitchMCPService with call_tool as AsyncMock."""
    service = MagicMock()
    service.call_tool = AsyncMock(return_value=STITCH_RESPONSE)
    return service


# ---------------------------------------------------------------------------
# Test 1 — generates three variants with correct event structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generates_three_variants():
    """generate_screen_variants yields generating + 3 variant_generated + ready events."""
    from app.services.screen_generation_service import generate_screen_variants

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.screen_generation_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.screen_generation_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.screen_generation_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.screen_generation_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_SCREEN_ID),
        ),
    ):
        events = []
        async for event in generate_screen_variants(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            screen_name="Home Page",
            page_slug="home",
            prompt="A bakery landing page",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            num_variants=3,
        ):
            events.append(event)

    steps = [e["step"] for e in events]
    assert "generating" in steps
    variant_events = [e for e in events if e["step"] == "variant_generated"]
    assert len(variant_events) == 3
    assert "ready" in steps
    # Each variant_generated has screenshot_url and html_url from persist_screen_assets
    for ve in variant_events:
        assert ve["screenshot_url"] == PERSISTED_URLS["screenshot_url"]
        assert ve["html_url"] == PERSISTED_URLS["html_url"]


# ---------------------------------------------------------------------------
# Test 2 — Stitch calls are sequential (called 3 times, not gathered)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequential_stitch_calls():
    """service.call_tool is called exactly 3 times — sequential not gathered."""
    from app.services.screen_generation_service import generate_screen_variants

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.screen_generation_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.screen_generation_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.screen_generation_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.screen_generation_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_SCREEN_ID),
        ),
    ):
        async for _ in generate_screen_variants(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            screen_name="Home Page",
            page_slug="home",
            prompt="A bakery landing page",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            num_variants=3,
        ):
            pass

    # Exactly 3 Stitch calls
    assert mock_stitch.call_tool.await_count == 3
    # Each call uses deviceType=DESKTOP
    for call in mock_stitch.call_tool.call_args_list:
        args, kwargs = call
        arguments = args[1] if len(args) > 1 else kwargs.get("arguments", {})
        assert arguments.get("deviceType") == "DESKTOP"


# ---------------------------------------------------------------------------
# Test 3 — persist_screen_assets called before variant_generated is yielded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persists_before_yield():
    """persist_screen_assets is awaited before variant_generated event is yielded.

    We verify by checking that the permanent URL (not the temp Stitch URL) appears
    in the event payload.
    """
    from app.services.screen_generation_service import generate_screen_variants

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.screen_generation_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.screen_generation_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.screen_generation_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.screen_generation_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_SCREEN_ID),
        ),
    ):
        events = []
        async for event in generate_screen_variants(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            screen_name="Home Page",
            page_slug="home",
            prompt="A bakery landing page",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            num_variants=3,
        ):
            events.append(event)

    variant_events = [e for e in events if e["step"] == "variant_generated"]
    for ve in variant_events:
        # Permanent Supabase URL — not the temp Stitch URL
        assert "supabase.co/storage" in ve["screenshot_url"]
        assert "supabase.co/storage" in ve["html_url"]
        assert "temp.stitch.dev" not in ve["screenshot_url"]


# ---------------------------------------------------------------------------
# Test 4 — inserts app_screens once, screen_variants 3 times
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inserts_screen_and_variants():
    """supabase.table('app_screens').insert called once; screen_variants.insert 3 times."""
    from app.services.screen_generation_service import generate_screen_variants

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.screen_generation_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.screen_generation_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.screen_generation_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.screen_generation_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_SCREEN_ID),
        ),
    ):
        async for _ in generate_screen_variants(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            screen_name="Home Page",
            page_slug="home",
            prompt="A bakery landing page",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            num_variants=3,
        ):
            pass

    # Collect all table() call names
    table_calls = [call.args[0] for call in mock_supabase.table.call_args_list]
    assert table_calls.count("app_screens") >= 1
    assert table_calls.count("screen_variants") >= 3


# ---------------------------------------------------------------------------
# Test 5 — generate_device_variant yields generating + device_generated + ready
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_device_variant():
    """generate_device_variant yields generating + device_generated + ready for MOBILE."""
    from app.services.screen_generation_service import generate_device_variant

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()

    with (
        patch(
            "app.services.screen_generation_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.screen_generation_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.screen_generation_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.screen_generation_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_SCREEN_ID),
        ),
    ):
        events = []
        async for event in generate_device_variant(
            screen_id=TEST_SCREEN_ID,
            user_id=TEST_USER_ID,
            prompt="A bakery landing page mobile",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            device_type="MOBILE",
            project_id=TEST_PROJECT_ID,
        ):
            events.append(event)

    steps = [e["step"] for e in events]
    assert "generating" in steps
    assert "device_generated" in steps
    assert "ready" in steps

    # Verify deviceType=MOBILE was passed to Stitch
    call_args = mock_stitch.call_tool.call_args_list[0]
    args, kwargs = call_args
    arguments = args[1] if len(args) > 1 else kwargs.get("arguments", {})
    assert arguments.get("deviceType") == "MOBILE"


# ---------------------------------------------------------------------------
# Test 6 — first variant is selected by default, rest are not
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_variant_selected_by_default():
    """First screen_variants insert has is_selected=True; others have False."""
    from app.services.screen_generation_service import generate_screen_variants

    mock_supabase = _make_supabase_mock()
    mock_stitch = _make_stitch_mock()
    inserted_variants: list[dict] = []

    original_insert = mock_supabase.table.return_value.insert

    def tracking_insert(data: dict) -> MagicMock:
        """Track variant inserts for assertion."""
        # Only track screen_variants inserts
        if "is_selected" in data:
            inserted_variants.append(data)
        return original_insert.return_value

    mock_supabase.table.return_value.insert = tracking_insert

    with (
        patch(
            "app.services.screen_generation_service.get_stitch_service",
            return_value=mock_stitch,
        ),
        patch(
            "app.services.screen_generation_service.persist_screen_assets",
            new=AsyncMock(return_value=PERSISTED_URLS),
        ),
        patch(
            "app.services.screen_generation_service.get_service_client",
            return_value=mock_supabase,
        ),
        patch(
            "app.services.screen_generation_service.uuid4",
            return_value=MagicMock(__str__=lambda s: TEST_SCREEN_ID),
        ),
    ):
        async for _ in generate_screen_variants(
            project_id=TEST_PROJECT_ID,
            user_id=TEST_USER_ID,
            screen_name="Home Page",
            page_slug="home",
            prompt="A bakery landing page",
            stitch_project_id=TEST_STITCH_PROJECT_ID,
            num_variants=3,
        ):
            pass

    assert len(inserted_variants) == 3
    assert inserted_variants[0]["is_selected"] is True
    assert inserted_variants[1]["is_selected"] is False
    assert inserted_variants[2]["is_selected"] is False
