# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A Agent Registry.

Database-backed registry for discovering and managing external A2A agents.
Stores agent cards, health status, and capabilities for multi-agent orchestration.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.supabase_client import get_service_client
from app.a2a.client import A2AClient, A2AClientError

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Manages registration and discovery of external A2A agents."""

    TABLE = "a2a_agent_registry"

    def __init__(self, supabase_client=None):
        self.client = supabase_client or get_service_client()

    async def register(
        self,
        *,
        name: str,
        url: str,
        description: str = "",
        auth_token: Optional[str] = None,
        tags: Optional[List[str]] = None,
        auto_discover: bool = True,
    ) -> Dict[str, Any]:
        """Register an external A2A agent.

        If auto_discover is True, fetches the agent card from the URL
        to populate capabilities and skills automatically.
        """
        agent_card = None
        capabilities = {}
        skills = []
        status = "registered"

        if auto_discover:
            try:
                async with A2AClient(url, auth_token=auth_token) as client:
                    agent_card = await client.discover()
                    capabilities = agent_card.get("capabilities", {})
                    skills = [
                        s.get("name", "") for s in agent_card.get("skills", [])
                    ]
                    # Use card values as defaults if not provided
                    name = name or agent_card.get("name", "Unknown Agent")
                    description = description or agent_card.get("description", "")
                    status = "active"
            except A2AClientError as exc:
                logger.warning("Auto-discovery failed for %s: %s", url, exc)
                status = "unreachable"

        data = {
            "name": name,
            "url": url,
            "description": description,
            "auth_token": auth_token,
            "agent_card": agent_card,
            "capabilities": capabilities,
            "skills": skills,
            "tags": tags or [],
            "status": status,
            "last_health_check": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        res = self.client.table(self.TABLE).upsert(
            data, on_conflict="url"
        ).execute()

        return res.data[0] if res.data else data

    async def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry."""
        res = self.client.table(self.TABLE).delete().eq("id", agent_id).execute()
        return bool(res.data)

    async def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a registered agent by ID."""
        res = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("id", agent_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    async def find_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Find a registered agent by its URL."""
        res = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("url", url)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    async def list_agents(
        self,
        *,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        skill: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List registered agents with optional filters."""
        query = self.client.table(self.TABLE).select("*")

        if status:
            query = query.eq("status", status)
        if tag:
            query = query.contains("tags", [tag])
        if skill:
            query = query.contains("skills", [skill])

        res = query.order("name").limit(limit).execute()
        return res.data or []

    async def search_by_capability(
        self, capability: str
    ) -> List[Dict[str, Any]]:
        """Find agents that have a specific capability (e.g., 'streaming')."""
        # capabilities is stored as JSONB, search for key presence
        res = (
            self.client.table(self.TABLE)
            .select("*")
            .eq("status", "active")
            .execute()
        )
        return [
            agent
            for agent in (res.data or [])
            if (agent.get("capabilities") or {}).get(capability)
        ]

    async def health_check(self, agent_id: str) -> Dict[str, Any]:
        """Ping an agent and update its health status."""
        agent = await self.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        url = agent["url"]
        auth_token = agent.get("auth_token")
        new_status = "unreachable"
        agent_card = agent.get("agent_card")

        try:
            async with A2AClient(url, auth_token=auth_token) as client:
                agent_card = await client.discover()
                new_status = "active"
        except A2AClientError:
            new_status = "unreachable"
        except Exception:
            new_status = "error"

        self.client.table(self.TABLE).update(
            {
                "status": new_status,
                "agent_card": agent_card,
                "last_health_check": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", agent_id).execute()

        return {"id": agent_id, "status": new_status}

    async def health_check_all(self) -> List[Dict[str, Any]]:
        """Run health checks on all registered agents."""
        agents = await self.list_agents()
        results = []
        for agent in agents:
            result = await self.health_check(agent["id"])
            results.append(result)
        return results


# ── Singleton ───────────────────────────────────────────────────────────

_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the singleton AgentRegistry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
