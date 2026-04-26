# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import logging
import os
from typing import Any

import httpx

from app.app_utils.env import get_stripped_env

logger = logging.getLogger(__name__)


class EdgeFunctionClient:
    def __init__(self):
        self.supabase_url = get_stripped_env("SUPABASE_URL")
        self.service_key = get_stripped_env("SUPABASE_SERVICE_ROLE_KEY")
        self.workflow_service_secret = get_stripped_env("WORKFLOW_SERVICE_SECRET")

        if not self.supabase_url or not self.service_key:
            logger.warning(
                "Supabase URL or Service Key missing. Edge Functions may not work."
            )

        self.headers = {
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if self.workflow_service_secret:
            self.headers["X-Service-Secret"] = self.workflow_service_secret
        self.timeout = httpx.Timeout(10.0, read=60.0)  # 10s connect, 60s read

    async def invoke_function(
        self, function_name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Generic method to invoke a Supabase Edge Function."""
        if not self.supabase_url:
            return {"error": "Configuration missing"}

        url = f"{self.supabase_url}/functions/v1/{function_name}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=self.headers)

                if response.status_code >= 400:
                    logger.error(
                        f"Edge Function {function_name} failed: {response.text}"
                    )
                    # Attempt to parse error
                    try:
                        return {
                            "error": response.json().get("error", response.text),
                            "status": response.status_code,
                        }
                    except (ValueError, AttributeError):
                        return {"error": response.text, "status": response.status_code}

                return response.json()
        except Exception as e:
            logger.error(f"Failed to invoke Edge Function {function_name}: {e}")
            return {"error": str(e)}

    async def send_notification(self, notification_id: str) -> dict[str, Any]:
        """Trigger the send-notification function."""
        return await self.invoke_function(
            "send-notification", {"notification_id": notification_id}
        )

    async def execute_workflow(
        self, execution_id: str, action: str = "start"
    ) -> dict[str, Any]:
        """Trigger the execute-workflow function."""
        return await self.invoke_function(
            "execute-workflow", {"execution_id": execution_id, "step_action": action}
        )

    async def generate_widget(
        self, user_id: str, widget_type: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a widget using the Edge Function."""
        payload = {
            "user_id": user_id,
            "widget_type": widget_type,
            "parameters": parameters,
        }
        return await self.invoke_function("generate-widget", payload)

    async def cleanup_sessions(self) -> dict[str, Any]:
        """Trigger session cleanup manually."""
        # Cleanup can be GET or POST, utilizing generic invoke which is POST
        # Our function handles both or we can change invoke to support methods.
        # But invoke uses POST. Our cleanup function supports generic invocation (usually POST).
        return await self.invoke_function("cleanup-sessions", {})


# Singleton instance
edge_function_client = EdgeFunctionClient()
