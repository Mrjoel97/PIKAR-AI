"""Unit tests for ship_service — ship orchestrator, walkthrough scene builder, multi-screen ZIP merge."""

import asyncio
import io
import zipfile
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"


def _make_zip_bytes(filenames: list[str]) -> bytes:
    """Build a minimal in-memory ZIP containing files with given names."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in filenames:
            zf.writestr(name, f"// {name} content")
    return buf.getvalue()


def _make_screen(name: str, html_url: str = "https://example.com/screen.html", screenshot_url: str = "https://example.com/screenshot.png") -> dict:
    return {
        "id": f"screen-{name.lower()}",
        "name": name,
        "html_url": html_url,
        "screenshot_url": screenshot_url,
    }


# ---------------------------------------------------------------------------
# Mock approved screens fixture
# ---------------------------------------------------------------------------

MOCK_SCREENS = [
    _make_screen("Home"),
    _make_screen("Dashboard"),
]

MOCK_PROJECT_DATA = {
    "title": "My Test App",
    "design_system": {"colors": []},
}

# ---------------------------------------------------------------------------
# Test 1: _build_walkthrough_scenes returns intro, per-screen, and outro
# ---------------------------------------------------------------------------


def test_build_walkthrough_scenes_structure():
    """_build_walkthrough_scenes returns intro + one scene per screen + outro."""
    from app.services.ship_service import _build_walkthrough_scenes

    screens = [_make_screen("Home"), _make_screen("Settings")]
    scenes = _build_walkthrough_scenes(screens, "My App")

    assert len(scenes) == 4  # intro + 2 screens + outro
    assert scenes[0]["text"] == "My App"  # intro
    assert scenes[1]["text"] == "Home"
    assert scenes[2]["text"] == "Settings"
    assert scenes[3]["text"] == "Built with Pikar AI"  # outro


# ---------------------------------------------------------------------------
# Test 2: _build_walkthrough_scenes sets correct durations
# ---------------------------------------------------------------------------


def test_build_walkthrough_scenes_durations():
    """_build_walkthrough_scenes sets duration=3 for intro, 4 per screen, 2 for outro."""
    from app.services.ship_service import _build_walkthrough_scenes

    screens = [_make_screen("Home")]
    scenes = _build_walkthrough_scenes(screens, "My App")

    intro = scenes[0]
    screen_scene = scenes[1]
    outro = scenes[2]

    assert intro["duration"] == 3
    assert screen_scene["duration"] == 4
    assert outro["duration"] == 2


# ---------------------------------------------------------------------------
# Test 3: ship_project yields target_started then target_complete for each target
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_project_event_sequence():
    """ship_project yields target_started then target_complete for each target."""
    from app.services.ship_service import ship_project

    fake_zip = _make_zip_bytes(["src/App.tsx"])
    fake_url = "https://storage.example.com/output.zip"

    with (
        patch("app.services.ship_service._fetch_approved_screens", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.ship_service._ship_react", new_callable=AsyncMock, return_value=fake_url),
        patch("app.services.ship_service._ship_pwa", new_callable=AsyncMock, return_value=fake_url),
        patch("app.services.ship_service.get_service_client") as mock_client,
    ):
        mock_fetch.return_value = (MOCK_SCREENS, MOCK_PROJECT_DATA)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.return_value = mock_supabase

        events = []
        async for event in ship_project(TEST_PROJECT_ID, TEST_USER_ID, ["react", "pwa"]):
            events.append(event)

    steps = [e["step"] for e in events]
    assert "target_started" in steps
    assert "target_complete" in steps

    # Should alternate: started, complete, started, complete, ..., ship_complete
    started = [e for e in events if e["step"] == "target_started"]
    completed = [e for e in events if e["step"] == "target_complete"]
    assert len(started) == 2
    assert len(completed) == 2

    # Verify ordering: for each target, started precedes complete
    target_order = [(e["step"], e.get("target")) for e in events if e.get("target")]
    react_events = [(s, t) for s, t in target_order if t == "react"]
    assert react_events[0][0] == "target_started"
    assert react_events[1][0] == "target_complete"


# ---------------------------------------------------------------------------
# Test 4: ship_project yields target_complete with a "url" field
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_project_target_complete_has_url():
    """ship_project yields target_complete events with a non-empty url field."""
    from app.services.ship_service import ship_project

    expected_url = "https://storage.example.com/react.zip"

    with (
        patch("app.services.ship_service._fetch_approved_screens", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.ship_service._ship_react", new_callable=AsyncMock, return_value=expected_url),
        patch("app.services.ship_service.get_service_client") as mock_client,
    ):
        mock_fetch.return_value = (MOCK_SCREENS, MOCK_PROJECT_DATA)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.return_value = mock_supabase

        events = []
        async for event in ship_project(TEST_PROJECT_ID, TEST_USER_ID, ["react"]):
            events.append(event)

    complete_events = [e for e in events if e["step"] == "target_complete"]
    assert len(complete_events) == 1
    assert complete_events[0]["url"] == expected_url


# ---------------------------------------------------------------------------
# Test 5: ship_project yields target_failed (not exception) when target raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_project_target_failed_on_error():
    """ship_project yields target_failed when a target raises, does not propagate."""
    from app.services.ship_service import ship_project

    with (
        patch("app.services.ship_service._fetch_approved_screens", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.ship_service._ship_react", new_callable=AsyncMock, side_effect=RuntimeError("Converter failed")),
        patch("app.services.ship_service.get_service_client") as mock_client,
    ):
        mock_fetch.return_value = (MOCK_SCREENS, MOCK_PROJECT_DATA)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.return_value = mock_supabase

        events = []
        async for event in ship_project(TEST_PROJECT_ID, TEST_USER_ID, ["react"]):
            events.append(event)

    failed_events = [e for e in events if e["step"] == "target_failed"]
    assert len(failed_events) == 1
    assert failed_events[0]["target"] == "react"
    assert "error" in failed_events[0]
    assert "Converter failed" in failed_events[0]["error"]


# ---------------------------------------------------------------------------
# Test 6: ship_project yields ship_complete with downloads dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_project_ship_complete_event():
    """ship_project yields ship_complete with a downloads dict at the end."""
    from app.services.ship_service import ship_project

    react_url = "https://storage.example.com/react.zip"
    pwa_url = "https://storage.example.com/pwa.zip"

    with (
        patch("app.services.ship_service._fetch_approved_screens", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.ship_service._ship_react", new_callable=AsyncMock, return_value=react_url),
        patch("app.services.ship_service._ship_pwa", new_callable=AsyncMock, return_value=pwa_url),
        patch("app.services.ship_service.get_service_client") as mock_client,
    ):
        mock_fetch.return_value = (MOCK_SCREENS, MOCK_PROJECT_DATA)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.return_value = mock_supabase

        events = []
        async for event in ship_project(TEST_PROJECT_ID, TEST_USER_ID, ["react", "pwa"]):
            events.append(event)

    complete_events = [e for e in events if e["step"] == "ship_complete"]
    assert len(complete_events) == 1
    downloads = complete_events[0].get("downloads", {})
    assert downloads.get("react") == react_url
    assert downloads.get("pwa") == pwa_url


# ---------------------------------------------------------------------------
# Test 7: video target calls asyncio.to_thread with render_scenes_direct_to_mp4
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_video_uses_asyncio_to_thread():
    """_ship_video calls asyncio.to_thread with render_scenes_direct_to_mp4 (not direct call)."""
    from app.services.ship_service import ship_project

    fake_mp4 = b"fake-mp4-bytes"
    fake_asset_id = "asset-123"
    fake_video_url = "https://storage.example.com/walkthrough.mp4"

    with (
        patch("app.services.ship_service._fetch_approved_screens", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.ship_service.get_service_client") as mock_client,
        patch("app.services.ship_service.render_scenes_direct_to_mp4") as mock_render,
        patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
        patch("app.services.ship_service._upload_output_bytes", new_callable=AsyncMock, return_value=fake_video_url),
    ):
        mock_fetch.return_value = (MOCK_SCREENS, MOCK_PROJECT_DATA)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.return_value = mock_supabase
        mock_to_thread.return_value = (fake_mp4, fake_asset_id)

        events = []
        async for event in ship_project(TEST_PROJECT_ID, TEST_USER_ID, ["video"]):
            events.append(event)

    # Verify asyncio.to_thread was called (not a direct call to render_scenes_direct_to_mp4)
    assert mock_to_thread.called, "asyncio.to_thread must be called for video target"
    call_args = mock_to_thread.call_args
    # First positional arg should be render_scenes_direct_to_mp4
    assert call_args[0][0] is mock_render, "asyncio.to_thread must wrap render_scenes_direct_to_mp4"


# ---------------------------------------------------------------------------
# Test 8: ship_project advances stage to "done" and status to "exported"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_project_advances_stage():
    """ship_project updates app_projects with stage=done and status=exported after completion."""
    from app.services.ship_service import ship_project

    fake_url = "https://storage.example.com/output.zip"

    with (
        patch("app.services.ship_service._fetch_approved_screens", new_callable=AsyncMock) as mock_fetch,
        patch("app.services.ship_service._ship_react", new_callable=AsyncMock, return_value=fake_url),
        patch("app.services.ship_service.get_service_client") as mock_client,
    ):
        mock_fetch.return_value = (MOCK_SCREENS, MOCK_PROJECT_DATA)
        mock_supabase = MagicMock()
        update_mock = MagicMock()
        update_mock.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.update.return_value = update_mock
        mock_client.return_value = mock_supabase

        events = []
        async for event in ship_project(TEST_PROJECT_ID, TEST_USER_ID, ["react"]):
            events.append(event)

    # Verify the update was called with stage=done and status=exported
    update_calls = mock_supabase.table.return_value.update.call_args_list
    assert len(update_calls) >= 1
    final_update_payload = update_calls[-1][0][0]
    assert final_update_payload.get("stage") == "done"
    assert final_update_payload.get("status") == "exported"


# ---------------------------------------------------------------------------
# Test 9: _ship_react with 2 screens produces single master ZIP with all components
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ship_react_multi_screen_merge():
    """_ship_react merges per-screen ZIPs into one master ZIP with subdirectory prefixes."""
    from app.services.ship_service import _ship_react

    # Two distinct ZIPs — each representing one screen's React output
    home_zip = _make_zip_bytes(["src/components/HeroSection.tsx", "src/index.tsx"])
    dashboard_zip = _make_zip_bytes(["src/components/DashboardChart.tsx", "src/index.tsx"])

    screens = [
        {
            "id": "screen-home",
            "name": "Home",
            "html_url": "https://example.com/home.html",
            "screenshot_url": "https://example.com/home.png",
        },
        {
            "id": "screen-dashboard",
            "name": "Dashboard",
            "html_url": "https://example.com/dashboard.html",
            "screenshot_url": "https://example.com/dash.png",
        },
    ]

    fake_upload_url = "https://storage.example.com/master.zip"

    call_count = 0

    async def fake_convert(html_content, screen_name, design_system=None):
        nonlocal call_count
        call_count += 1
        return home_zip if screen_name == "Home" else dashboard_zip

    with (
        patch("app.services.ship_service.convert_html_to_react_zip", side_effect=fake_convert),
        patch("app.services.ship_service._upload_output_bytes", new_callable=AsyncMock, return_value=fake_upload_url) as mock_upload,
        patch("app.services.ship_service.get_service_client"),
    ):
        # Patch httpx to return fake HTML
        import httpx
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html><body>content</body></html>"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)

            # Use AsyncClient as context manager
            async def fake_get_cm(*args, **kwargs):
                return mock_response

            with patch("httpx.AsyncClient") as mock_http_class:
                mock_http_instance = AsyncMock()
                mock_http_instance.get = AsyncMock(return_value=mock_response)
                mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
                mock_http_instance.__aexit__ = AsyncMock(return_value=False)
                mock_http_class.return_value = mock_http_instance
                mock_response.raise_for_status = MagicMock()
                mock_response.text = "<html><body>content</body></html>"

                result_url = await _ship_react(
                    project_id=TEST_PROJECT_ID,
                    user_id=TEST_USER_ID,
                    screens=screens,
                    design_system=None,
                )

    assert result_url == fake_upload_url
    assert call_count == 2, "convert_html_to_react_zip should be called once per screen"

    # Inspect the master ZIP that was uploaded
    uploaded_zip_bytes = mock_upload.call_args[0][0]
    master_zip = zipfile.ZipFile(io.BytesIO(uploaded_zip_bytes))
    namelist = master_zip.namelist()

    # Both screens' components should appear under screen-specific subdirectories
    assert any("HeroSection.tsx" in name for name in namelist), f"Missing HeroSection.tsx in {namelist}"
    assert any("DashboardChart.tsx" in name for name in namelist), f"Missing DashboardChart.tsx in {namelist}"
