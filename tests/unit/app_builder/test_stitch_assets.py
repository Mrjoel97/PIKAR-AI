"""Unit tests for stitch_assets service — no real Supabase or HTTP calls."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_download_and_persist_returns_public_url():
    """Happy path: download succeeds, upload succeeds, returns public URL."""
    from app.services import stitch_assets

    fake_bytes = b"<html>test</html>"
    fake_public_url = "https://xyz.supabase.co/storage/v1/object/public/stitch-assets/u/p/s.html"

    mock_resp = MagicMock()
    mock_resp.content = fake_bytes
    mock_resp.raise_for_status = MagicMock()

    mock_supabase = MagicMock()
    mock_storage = mock_supabase.storage.from_.return_value
    mock_storage.upload = MagicMock()
    mock_storage.get_public_url.return_value = fake_public_url

    with patch("httpx.AsyncClient") as mock_httpx, \
         patch("app.services.stitch_assets.get_service_client", return_value=mock_supabase):
        mock_httpx.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            get=AsyncMock(return_value=mock_resp)
        ))
        mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await stitch_assets.download_and_persist(
            "https://stitch.example.com/tmp/screen.html?sig=abc",
            "user1/proj1/screen1.html",
            "text/html",
        )

    assert result == fake_public_url
    mock_storage.upload.assert_called_once()


@pytest.mark.asyncio
async def test_persist_screen_assets_both_urls():
    """persist_screen_assets extracts and persists both html and screenshot URLs."""
    from app.services import stitch_assets

    stitch_resp = {
        "screenId": "s1",
        "html_url": "https://stitch.tmp/s1.html?sig=x",
        "screenshot_url": "https://stitch.tmp/s1.png?sig=y",
    }

    async def fake_download(temp_url, storage_path, content_type):
        return f"https://storage.permanent/{storage_path}"

    with patch.object(stitch_assets, "download_and_persist", side_effect=fake_download):
        result = await stitch_assets.persist_screen_assets(
            stitch_response=stitch_resp,
            user_id="u1",
            project_id="p1",
            screen_id="s1",
        )

    assert "u1/p1/s1" in result["html_url"]
    assert "u1/p1/s1" in result["screenshot_url"]


@pytest.mark.asyncio
async def test_persist_screen_assets_no_urls():
    """persist_screen_assets returns None values when Stitch response has no URLs."""
    from app.services import stitch_assets

    result = await stitch_assets.persist_screen_assets(
        stitch_response={"screenId": "s2"},
        user_id="u1", project_id="p1", screen_id="s2",
    )
    assert result["html_url"] is None
    assert result["screenshot_url"] is None
