"""Unit tests for StitchMCPService — no real subprocess needed."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


def test_is_ready_false_before_run():
    """Service starts not-ready before _run() initializes the session."""
    from app.services.stitch_mcp import StitchMCPService

    s = StitchMCPService()
    assert s.is_ready() is False


def test_get_stitch_service_raises_when_not_initialized():
    """get_stitch_service() raises RuntimeError when the module singleton is None."""
    import app.services.stitch_mcp as mod

    original = mod._stitch_service
    mod._stitch_service = None
    try:
        with pytest.raises(RuntimeError, match="not initialized"):
            mod.get_stitch_service()
    finally:
        mod._stitch_service = original


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
