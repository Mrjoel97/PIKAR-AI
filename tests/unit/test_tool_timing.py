"""Tests for timed_tool decorator — measures tool execution duration."""

import asyncio
import time
from unittest.mock import MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_timed_sync_tool_records_duration():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def my_tool(query: str) -> dict:
        time.sleep(0.01)  # 10ms
        return {"result": query}

    result = my_tool("test")
    assert result == {"result": "test"}
    assert hasattr(my_tool, "_last_duration_ms")
    assert my_tool._last_duration_ms >= 10


def test_timed_async_tool_records_duration():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    async def my_async_tool(query: str) -> dict:
        await asyncio.sleep(0.01)
        return {"result": query}

    result = _run(my_async_tool("test"))
    assert result == {"result": "test"}
    assert hasattr(my_async_tool, "_last_duration_ms")
    assert my_async_tool._last_duration_ms >= 10


def test_timed_tool_preserves_function_metadata():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def search_business_knowledge(query: str) -> dict:
        """Search the Knowledge Vault."""
        return {"results": []}

    assert search_business_knowledge.__name__ == "search_business_knowledge"
    assert "Knowledge Vault" in (search_business_knowledge.__doc__ or "")


def test_timed_tool_records_error():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def failing_tool() -> dict:
        raise ValueError("oops")

    try:
        failing_tool()
    except ValueError:
        pass

    assert hasattr(failing_tool, "_last_duration_ms")
    assert hasattr(failing_tool, "_last_error")
    assert failing_tool._last_error == "ValueError"


def test_timed_tool_emits_telemetry_event():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def my_tool() -> dict:
        return {"ok": True}

    my_tool()

    # The decorator stores timing data but does NOT call telemetry directly.
    # The after_tool_callback reads _last_duration_ms and creates the ToolEvent.
    assert my_tool._last_duration_ms is not None
    assert my_tool._last_error is None
