"""Stitch MCP Service — persistent singleton managing the Stitch Node.js subprocess.

Holds stdio_client + ClientSession alive for the FastAPI process lifetime via
an asyncio background task. Individual tool calls serialize through a Lock.
"""
import asyncio
import json
import logging
import os
from typing import Any

import anyio

logger = logging.getLogger(__name__)

# Module-level singleton
_stitch_service: "StitchMCPService | None" = None
_stitch_task: "asyncio.Task[None] | None" = None


class StitchMCPService:
    """Singleton owning the Stitch MCP subprocess for the FastAPI process lifetime."""

    def __init__(self) -> None:
        """Initialise the service with no active session."""
        self._session = None
        self._lock = asyncio.Lock()
        self._ready = anyio.Event()  # anyio — consistent with mcp library internals
        self._healthy = True

    async def _run(self) -> None:
        """Background coroutine — holds stdio_client + ClientSession open until cancelled."""
        from mcp import ClientSession, StdioServerParameters, stdio_client

        stitch_key = os.environ.get("STITCH_API_KEY", "")
        params = StdioServerParameters(
            command="npx",
            args=["@_davideast/stitch-mcp", "proxy"],
            env={**os.environ, "STITCH_API_KEY": stitch_key},
            cwd=None,
        )
        try:
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    # Log available tools so we know exact names (camelCase vs snake_case)
                    try:
                        tools = await session.list_tools()
                        logger.info(
                            "StitchMCP tools available: %s",
                            [t.name for t in tools.tools],
                        )
                    except Exception as e:
                        logger.warning("Could not list Stitch tools: %s", e)
                    self._session = session
                    self._healthy = True
                    self._ready.set()
                    logger.info("StitchMCPService ready — subprocess alive")
                    # Hang here until asyncio task is cancelled at shutdown
                    await anyio.sleep_forever()
        except asyncio.CancelledError:
            logger.info("StitchMCPService shutting down (task cancelled)")
            raise
        except Exception as e:
            logger.error("StitchMCPService _run() failed: %s", e)
            self._healthy = False
            self._session = None
            # Don't re-raise — let the service degrade gracefully

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a Stitch MCP tool by name. Serialized via Lock.

        Returns parsed JSON dict from the TextContent response.
        Raises RuntimeError if session is not initialized or the call errors.
        """
        from mcp.types import TextContent

        if self._session is None or not self._healthy:
            raise RuntimeError(
                "StitchMCPService not available — subprocess may have crashed"
            )
        async with self._lock:
            result = await self._session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(f"Stitch tool '{name}' returned error: {result.content}")

        # Extract JSON from first TextContent item
        text_item = next(
            (item for item in result.content if isinstance(item, TextContent)), None
        )
        if text_item is None:
            raise RuntimeError(f"Stitch tool '{name}' returned no TextContent")

        try:
            return json.loads(text_item.text)
        except json.JSONDecodeError:
            # Return raw text wrapped in dict if not JSON
            return {"raw": text_item.text}

    def is_ready(self) -> bool:
        """Return True if the MCP session is initialized and healthy."""
        return self._session is not None and self._healthy


def get_stitch_service() -> "StitchMCPService":
    """Return the global StitchMCPService instance.

    Raises RuntimeError if the service was not started (lifespan not run or
    STITCH_API_KEY not set).
    """
    if _stitch_service is None:
        raise RuntimeError(
            "StitchMCPService not initialized — check STITCH_API_KEY and FastAPI lifespan"
        )
    return _stitch_service
