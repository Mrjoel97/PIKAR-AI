# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A Outbound Client.

Async client for calling external A2A-compatible agents.
Supports agent card discovery, message sending, streaming responses,
and task status querying per the A2A protocol specification.
"""

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default timeouts
DEFAULT_TIMEOUT_SECONDS = 60
DISCOVER_TIMEOUT_SECONDS = 10
STREAM_TIMEOUT_SECONDS = 300


class A2AClientError(Exception):
    """Base error for A2A client operations."""

    def __init__(self, message: str, code: int = -1, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class A2AClient:
    """Async client for communicating with external A2A agents.

    Usage:
        client = A2AClient("https://other-agent.example.com/a2a/agent")
        card = await client.discover()
        result = await client.send_message("Analyze this data", context={"key": "value"})
        await client.close()
    """

    def __init__(
        self,
        base_url: str,
        *,
        auth_token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Discovery ───────────────────────────────────────────────────────

    async def discover(self) -> dict[str, Any]:
        """Fetch the agent card from the well-known endpoint.

        Returns the agent card as a dict with name, description,
        capabilities, skills, protocolVersion, url, etc.
        """
        card_url = f"{self.base_url}/.well-known/agent-card.json"
        try:
            resp = await self._client.get(
                card_url,
                timeout=DISCOVER_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise A2AClientError(
                f"Agent discovery failed: HTTP {exc.response.status_code}",
                code=exc.response.status_code,
            ) from exc
        except Exception as exc:
            raise A2AClientError(f"Agent discovery failed: {exc}") from exc

    # ── Send Message (JSON-RPC) ─────────────────────────────────────────

    async def send_message(
        self,
        text: str,
        *,
        task_id: str | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a message to the remote agent and get a synchronous response.

        Args:
            text: The message text to send.
            task_id: Optional task ID to continue an existing task.
            context: Optional context data for the agent.
            metadata: Optional metadata for the request.

        Returns:
            The JSON-RPC result containing the task response.
        """
        message = {
            "role": "user",
            "parts": [{"type": "text", "text": text}],
        }
        if context:
            message["metadata"] = context

        params: dict[str, Any] = {"message": message}
        if task_id:
            params["taskId"] = task_id
        if metadata:
            params["metadata"] = metadata

        return await self._rpc_call("message/send", params)

    async def send_streaming_message(
        self,
        text: str,
        *,
        task_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a message and stream the response via SSE.

        Yields parsed JSON event objects as they arrive.
        """
        message = {
            "role": "user",
            "parts": [{"type": "text", "text": text}],
        }
        if context:
            message["metadata"] = context

        params: dict[str, Any] = {"message": message}
        if task_id:
            params["taskId"] = task_id

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": params,
        }

        async with self._client.stream(
            "POST",
            self.base_url,
            json=payload,
            timeout=STREAM_TIMEOUT_SECONDS,
            headers={**self._build_headers(), "Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            yield json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse SSE data: %s", data_str)

    # ── Task Status ─────────────────────────────────────────────────────

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Query the status of a previously submitted task."""
        return await self._rpc_call("tasks/get", {"id": task_id})

    async def cancel_task(self, task_id: str) -> dict[str, Any]:
        """Cancel a running task on the remote agent."""
        return await self._rpc_call("tasks/cancel", {"id": task_id})

    # ── JSON-RPC Transport ──────────────────────────────────────────────

    async def _rpc_call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a JSON-RPC 2.0 call."""
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        try:
            resp = await self._client.post(self.base_url, json=payload)
            resp.raise_for_status()
            body = resp.json()

            if "error" in body:
                err = body["error"]
                raise A2AClientError(
                    err.get("message", "Unknown RPC error"),
                    code=err.get("code", -1),
                    data=err.get("data"),
                )

            return body.get("result", body)

        except httpx.HTTPStatusError as exc:
            raise A2AClientError(
                f"RPC call '{method}' failed: HTTP {exc.response.status_code}",
                code=exc.response.status_code,
            ) from exc
        except A2AClientError:
            raise
        except Exception as exc:
            raise A2AClientError(f"RPC call '{method}' failed: {exc}") from exc


# ── Convenience factory ─────────────────────────────────────────────────


def create_a2a_client(
    agent_url: str,
    auth_token: str | None = None,
) -> A2AClient:
    """Create an A2A client for a given agent URL."""
    return A2AClient(agent_url, auth_token=auth_token)
