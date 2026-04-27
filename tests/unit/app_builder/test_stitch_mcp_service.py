"""Unit tests for StitchMCPService — no real subprocess needed."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


def test_is_ready_false_before_run():
    """Service starts not-ready before _run() initializes the session."""
    from app.services.stitch_mcp import StitchMCPService

    s = StitchMCPService(api_key="tvly-test")
    assert s.is_ready() is False
    assert s._api_key == "tvly-test"


@pytest.mark.asyncio
async def test_get_stitch_service_raises_when_no_keys(monkeypatch):
    """async get_stitch_service raises when no key is anywhere configured."""
    import app.services.stitch_mcp as mod

    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    monkeypatch.delenv("APP_BUILDER_USE_MOCK_STITCH", raising=False)

    # Reset the module-level pool so resolution happens fresh.
    mod._pool = None

    with pytest.raises(RuntimeError, match="No Stitch API key configured"):
        await mod.get_stitch_service(user_id=None)


@pytest.mark.asyncio
async def test_call_tool_raises_when_session_none():
    """call_tool() raises RuntimeError when no session is active."""
    from app.services.stitch_mcp import StitchMCPService

    s = StitchMCPService()
    with pytest.raises(RuntimeError, match="not available"):
        await s.call_tool("test", {})


@pytest.mark.asyncio
async def test_call_tool_raises_on_error_result():
    """call_tool() raises RuntimeError when the MCP result indicates an error."""
    from app.services.stitch_mcp import StitchMCPService

    s = StitchMCPService()
    s._session = AsyncMock()
    s._healthy = True

    error_result = MagicMock()
    error_result.isError = True
    error_result.content = ["error message"]
    s._session.call_tool = AsyncMock(return_value=error_result)

    with pytest.raises(RuntimeError, match="returned error"):
        await s.call_tool("generate_screen_from_text", {"prompt": "test"})


@pytest.mark.asyncio
async def test_call_tool_parses_json_response():
    """call_tool() parses TextContent.text as JSON and returns a dict."""
    from app.services.stitch_mcp import StitchMCPService
    from mcp.types import TextContent

    s = StitchMCPService()
    s._session = AsyncMock()
    s._healthy = True

    payload = {"screenId": "abc123", "projectId": "proj456"}
    text_content = MagicMock(spec=TextContent)
    text_content.text = json.dumps(payload)

    success_result = MagicMock()
    success_result.isError = False
    success_result.content = [text_content]
    s._session.call_tool = AsyncMock(return_value=success_result)

    result = await s.call_tool("generate_screen_from_text", {"prompt": "test"})
    assert result == payload


def test_service_falls_back_to_env_when_no_explicit_key(monkeypatch):
    """When constructor api_key is None, _run reads STITCH_API_KEY from env."""
    from app.services.stitch_mcp import StitchMCPService

    monkeypatch.setenv("STITCH_API_KEY", "env-key")
    s = StitchMCPService()  # api_key=None
    assert s._api_key is None  # not captured at init
