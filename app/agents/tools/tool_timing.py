"""Tool timing decorator for telemetry.

Wraps tool functions to measure execution duration. The after_tool_callback
reads the timing data from the wrapper and creates ToolEvent records.

Usage:
    @timed_tool
    def my_tool(query: str) -> dict:
        ...

    # After execution:
    my_tool._last_duration_ms  # int
    my_tool._last_error        # str | None
"""

import asyncio
import functools
import time
from typing import Any, Callable


def timed_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that measures tool execution time.

    Sets `_last_duration_ms` and `_last_error` attributes on the wrapper
    after each invocation. The after_tool_callback reads these to create
    ToolEvent records without needing a before_tool_callback.
    """
    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            error_type = None
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                error_type = type(exc).__name__
                raise
            finally:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                async_wrapper._last_duration_ms = elapsed_ms
                async_wrapper._last_error = error_type

        async_wrapper._last_duration_ms = None
        async_wrapper._last_error = None
        async_wrapper._is_timed_tool = True
        return async_wrapper

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            error_type = None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                error_type = type(exc).__name__
                raise
            finally:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                sync_wrapper._last_duration_ms = elapsed_ms
                sync_wrapper._last_error = error_type

        sync_wrapper._last_duration_ms = None
        sync_wrapper._last_error = None
        sync_wrapper._is_timed_tool = True
        return sync_wrapper


def apply_timing(tools: list[Callable]) -> list[Callable]:
    """Apply timed_tool decorator to a list of tools.

    Skips tools that are already timed.
    """
    result = []
    for tool in tools:
        if getattr(tool, "_is_timed_tool", False):
            result.append(tool)
        else:
            result.append(timed_tool(tool))
    return result
