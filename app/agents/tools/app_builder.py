"""App Builder agent tools — ADK-compatible synchronous wrappers for Stitch MCP.

These functions are added to agent tool lists directly.
They delegate to StitchMCPService (the persistent singleton) via thread executor.
"""

import asyncio
import concurrent.futures
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Run a coroutine from a sync context, handling running event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=120)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _generate_screen_async(
    prompt: str,
    project_id: str,
    device_type: str = "DESKTOP",
) -> dict[str, Any]:
    """Async inner for generate_app_screen."""
    from app.services.stitch_mcp import get_stitch_service

    service = get_stitch_service()
    # Call generate_screen_from_text (verify actual name at startup via list_tools log)
    return await service.call_tool(
        "generate_screen_from_text",
        {"prompt": prompt, "projectId": project_id, "deviceType": device_type},
    )


def generate_app_screen(
    prompt: str,
    project_id: str,
    device_type: str = "DESKTOP",
) -> dict[str, Any]:
    """Generate a screen via Stitch MCP for the given project.

    Args:
        prompt: Stitch-optimized description of the screen to generate.
        project_id: The Stitch project ID to generate within.
        device_type: "DESKTOP", "MOBILE", or "TABLET".

    Returns:
        Parsed JSON response from Stitch containing screenId and asset URLs.
    """
    try:
        return _run_async(_generate_screen_async(prompt, project_id, device_type))
    except RuntimeError as e:
        logger.error("generate_app_screen failed: %s", e)
        return {"success": False, "error": str(e)}


async def _list_stitch_tools_async() -> dict[str, Any]:
    """List tools exposed by the running Stitch MCP server."""
    from app.services.stitch_mcp import get_stitch_service

    service = get_stitch_service()
    # Piggyback on call_tool's lock pattern; use list_tools directly on session
    async with service._lock:
        tools_result = await service._session.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description} for t in tools_result.tools
        ]
    }


def list_stitch_tools() -> dict[str, Any]:
    """List all tools available from the connected Stitch MCP server.

    Returns:
        Dict with 'tools' list of {name, description}.
    """
    try:
        return _run_async(_list_stitch_tools_async())
    except RuntimeError as e:
        return {"success": False, "error": str(e), "tools": []}


APP_BUILDER_TOOLS = [generate_app_screen, list_stitch_tools]
