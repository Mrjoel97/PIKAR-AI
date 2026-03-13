"""UserWorkflowService - CRUD operations for user-specific workflows.

This service provides Create, Read, Update, Delete operations for dynamic
workflows stored in Supabase. Workflows are user_id scoped and can be
retrieved for pattern matching against new requests.
"""

import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from supabase import Client

from app.personas.policy_registry import normalize_persona
from app.services.supabase import get_service_client


class UserWorkflowService:
    """Service for managing user-specific dynamic workflows.

    All operations are user_id scoped for data isolation.
    Workflows can be matched against new requests to reuse patterns.
    """

    def __init__(self):
        self.client: Client = get_service_client()
        self._table_name = "user_workflows"

    def _normalize_persona_scope(self, persona_scope: Optional[str]) -> str:
        normalized = normalize_persona(persona_scope)
        if normalized:
            return normalized
        candidate = str(persona_scope or "").strip().lower()
        if candidate == "all":
            return "all"
        return "all"

    def _apply_persona_scope_filter(self, query: Any, persona_scope: Optional[str]) -> Any:
        normalized_scope = self._normalize_persona_scope(persona_scope)
        if normalized_scope == "all":
            return query.eq("persona_scope", "all")
        return query.in_("persona_scope", [normalized_scope, "all"])

    async def save_workflow(
        self,
        user_id: str,
        workflow_name: str,
        workflow_pattern: str,
        agent_ids: List[str],
        request_pattern: str,
        workflow_config: Dict[str, Any],
        persona_scope: Optional[str] = None,
    ) -> dict:
        """Save a new or updated workflow."""
        normalized_scope = self._normalize_persona_scope(persona_scope)
        data = {
            "user_id": user_id,
            "workflow_name": workflow_name,
            "workflow_pattern": workflow_pattern,
            "agent_ids": agent_ids,
            "request_pattern": request_pattern,
            "workflow_config": workflow_config,
            "persona_scope": normalized_scope,
        }

        response = (
            self.client.table(self._table_name)
            .upsert(data, on_conflict="user_id,workflow_name,persona_scope")
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from save workflow")

    async def get_workflow(
        self,
        user_id: str,
        workflow_name: str,
        persona_scope: Optional[str] = None,
    ) -> Optional[dict]:
        """Retrieve a workflow by name for a user."""
        query = (
            self.client.table(self._table_name)
            .select("*")
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
        )
        query = self._apply_persona_scope_filter(query, persona_scope)
        response = query.order("persona_scope").limit(1).single().execute()
        return response.data

    async def list_workflows(
        self,
        user_id: str,
        pattern_type: Optional[str] = None,
        limit: int = 50,
        persona_scope: Optional[str] = None,
    ) -> List[dict]:
        """List workflows for a user with optional filters."""
        query = (
            self.client.table(self._table_name)
            .select("*")
            .eq("user_id", user_id)
        )
        query = self._apply_persona_scope_filter(query, persona_scope)

        if pattern_type:
            query = query.eq("workflow_pattern", pattern_type)

        response = (
            query
            .order("usage_count", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data

    async def find_matching_workflow(
        self,
        user_id: str,
        request: str,
        threshold: float = 0.6,
        persona_scope: Optional[str] = None,
    ) -> Optional[dict]:
        """Find a workflow that matches the given request."""
        workflows = await self.list_workflows(user_id, limit=100, persona_scope=persona_scope)
        if not workflows:
            return None

        normalized_request = self.normalize_request(request)
        request_keywords = set(normalized_request.split())

        best_match = None
        best_score = 0.0

        for workflow in workflows:
            pattern = workflow.get("request_pattern", "")
            if not pattern:
                continue

            pattern_keywords = set(pattern.split())
            if not pattern_keywords:
                continue
            intersection = len(request_keywords & pattern_keywords)
            union = len(request_keywords | pattern_keywords)
            similarity = intersection / union if union > 0 else 0

            usage_boost = min(0.1, workflow.get("usage_count", 0) * 0.01)
            score = similarity + usage_boost

            if score > best_score and score >= threshold:
                best_score = score
                best_match = workflow

        return best_match

    async def update_workflow_usage(
        self,
        user_id: str,
        workflow_name: str,
        persona_scope: Optional[str] = None,
    ) -> Optional[dict]:
        """Increment usage count and update last_used_at timestamp."""
        current = await self.get_workflow(user_id, workflow_name, persona_scope=persona_scope)
        if not current:
            return None

        new_count = (current.get("usage_count") or 0) + 1
        query = (
            self.client.table(self._table_name)
            .update({
                "usage_count": new_count,
                "last_used_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
        )
        query = self._apply_persona_scope_filter(query, persona_scope)
        response = query.execute()
        if response.data:
            return response.data[0]
        return None

    async def update_workflow_config(
        self,
        user_id: str,
        workflow_name: str,
        workflow_config: Dict[str, Any],
        persona_scope: Optional[str] = None,
    ) -> Optional[dict]:
        """Update the workflow configuration."""
        query = (
            self.client.table(self._table_name)
            .update({"workflow_config": workflow_config})
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
        )
        query = self._apply_persona_scope_filter(query, persona_scope)
        response = query.execute()
        if response.data:
            return response.data[0]
        return None

    async def delete_workflow(
        self,
        user_id: str,
        workflow_name: str,
        persona_scope: Optional[str] = None,
    ) -> bool:
        """Delete a workflow."""
        query = (
            self.client.table(self._table_name)
            .delete()
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
        )
        query = self._apply_persona_scope_filter(query, persona_scope)
        response = query.execute()
        return bool(response.data)

    def normalize_request(self, request: str) -> str:
        """Normalize request text for pattern matching."""
        normalized = request.lower()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'i',
            'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it', 'they',
            'them', 'this', 'that', 'these', 'those', 'am', 'what', 'which',
            'who', 'whom', 'please', 'help', 'want', 'like', 'get', 'make',
        }

        words = normalized.split()
        words = [w for w in words if w not in stopwords and len(w) > 1]

        return ' '.join(words)

    def generate_workflow_name(self, agents: List[str], pattern: str) -> str:
        """Generate a unique workflow name from agents and pattern."""
        agent_part = '_'.join(sorted(agents)[:3])
        return f"{pattern}_{agent_part}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


_user_workflow_service: Optional[UserWorkflowService] = None


def get_user_workflow_service() -> UserWorkflowService:
    """Get the singleton UserWorkflowService instance."""
    global _user_workflow_service
    if _user_workflow_service is None:
        _user_workflow_service = UserWorkflowService()
    return _user_workflow_service


__all__ = [
    "UserWorkflowService",
    "get_user_workflow_service",
]
