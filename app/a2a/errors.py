# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Structured A2A error handling.

Provides JSON-RPC 2.0 compliant error responses for A2A protocol endpoints.
"""

from typing import Any

# Standard JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# A2A-specific error codes (application-defined range: -32000 to -32099)
TASK_NOT_FOUND = -32001
AGENT_UNAVAILABLE = -32002
TASK_CANCELLED = -32003
AGENT_AUTH_REQUIRED = -32004
RATE_LIMITED = -32005


class A2AError(Exception):
    """Structured A2A protocol error with JSON-RPC error code."""

    def __init__(
        self,
        message: str,
        code: int = INTERNAL_ERROR,
        data: Any | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.data = data

    def to_json_rpc(self, request_id: Any = None) -> dict:
        """Format as a JSON-RPC 2.0 error response."""
        error_obj: dict[str, Any] = {
            "code": self.code,
            "message": str(self),
        }
        if self.data is not None:
            error_obj["data"] = self.data

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error_obj,
        }


def task_not_found_error(task_id: str) -> A2AError:
    """Create a TASK_NOT_FOUND error."""
    return A2AError(
        f"Task '{task_id}' not found",
        code=TASK_NOT_FOUND,
        data={"task_id": task_id},
    )


def agent_unavailable_error(agent_name: str, reason: str = "") -> A2AError:
    """Create an AGENT_UNAVAILABLE error."""
    return A2AError(
        f"Agent '{agent_name}' is unavailable" + (f": {reason}" if reason else ""),
        code=AGENT_UNAVAILABLE,
        data={"agent": agent_name},
    )


def invalid_params_error(message: str, details: Any = None) -> A2AError:
    """Create an INVALID_PARAMS error."""
    return A2AError(message, code=INVALID_PARAMS, data=details)
