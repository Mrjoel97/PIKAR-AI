"""UserWorkflowService - CRUD operations for user-specific workflows.

This service provides Create, Read, Update, Delete operations for dynamic
workflows stored in Supabase. Workflows are user_id scoped and can be
retrieved for pattern matching against new requests.
"""

import os
import re
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from supabase import Client
from app.services.supabase import get_service_client


class UserWorkflowService:
    """Service for managing user-specific dynamic workflows.
    
    All operations are user_id scoped for data isolation.
    Workflows can be matched against new requests to reuse patterns.
    """
    
    def __init__(self):
        self.client: Client = get_service_client()
        self._table_name = "user_workflows"

    # ==========================
    # Create Operations
    # ==========================

    async def save_workflow(
        self,
        user_id: str,
        workflow_name: str,
        workflow_pattern: str,
        agent_ids: List[str],
        request_pattern: str,
        workflow_config: Dict[str, Any],
    ) -> dict:
        """Save a new or updated workflow.
        
        Args:
            user_id: The user's UUID.
            workflow_name: Unique name for the workflow (per user).
            workflow_pattern: Pattern type ('sequential', 'parallel', 'loop').
            agent_ids: List of agent IDs used in the workflow.
            request_pattern: Normalized request pattern for matching.
            workflow_config: Full workflow configuration as JSON.
            
        Returns:
            The created/updated workflow record.
        """
        data = {
            "user_id": user_id,
            "workflow_name": workflow_name,
            "workflow_pattern": workflow_pattern,
            "agent_ids": agent_ids,
            "request_pattern": request_pattern,
            "workflow_config": workflow_config,
        }
        
        # Use upsert to handle both create and update
        response = (
            self.client.table(self._table_name)
            .upsert(data, on_conflict="user_id,workflow_name")
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from save workflow")

    # ==========================
    # Read Operations
    # ==========================

    async def get_workflow(
        self, user_id: str, workflow_name: str
    ) -> Optional[dict]:
        """Retrieve a workflow by name for a user."""
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data

    async def list_workflows(
        self,
        user_id: str,
        pattern_type: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """List workflows for a user with optional filters.
        
        Args:
            user_id: The user's UUID.
            pattern_type: Optional filter by pattern type.
            limit: Maximum number of results.
            
        Returns:
            List of workflow records.
        """
        query = (
            self.client.table(self._table_name)
            .select("*")
            .eq("user_id", user_id)
        )
        
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
        threshold: float = 0.6
    ) -> Optional[dict]:
        """Find a workflow that matches the given request.
        
        Uses simple keyword matching to find similar requests.
        Could be enhanced with embeddings for semantic matching.
        
        Args:
            user_id: The user's UUID.
            request: The user's request text.
            threshold: Minimum similarity score (0-1).
            
        Returns:
            Best matching workflow or None if no match above threshold.
        """
        workflows = await self.list_workflows(user_id, limit=100)
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
            
            # Calculate Jaccard similarity
            if not pattern_keywords:
                continue
            intersection = len(request_keywords & pattern_keywords)
            union = len(request_keywords | pattern_keywords)
            similarity = intersection / union if union > 0 else 0
            
            # Boost by usage count (popular workflows are more likely matches)
            usage_boost = min(0.1, workflow.get("usage_count", 0) * 0.01)
            score = similarity + usage_boost
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = workflow

        return best_match

    # ==========================
    # Update Operations
    # ==========================

    async def update_workflow_usage(
        self, user_id: str, workflow_name: str
    ) -> Optional[dict]:
        """Increment usage count and update last_used_at timestamp.

        Args:
            user_id: The user's UUID.
            workflow_name: The workflow name.

        Returns:
            Updated workflow record or None if not found.
        """
        # First get current usage count
        current = await self.get_workflow(user_id, workflow_name)
        if not current:
            return None

        new_count = (current.get("usage_count") or 0) + 1

        response = (
            self.client.table(self._table_name)
            .update({
                "usage_count": new_count,
                "last_used_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None

    async def update_workflow_config(
        self, user_id: str, workflow_name: str, workflow_config: Dict[str, Any]
    ) -> Optional[dict]:
        """Update the workflow configuration.

        Args:
            user_id: The user's UUID.
            workflow_name: The workflow name.
            workflow_config: New workflow configuration.

        Returns:
            Updated workflow record or None if not found.
        """
        response = (
            self.client.table(self._table_name)
            .update({"workflow_config": workflow_config})
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None

    # ==========================
    # Delete Operations
    # ==========================

    async def delete_workflow(self, user_id: str, workflow_name: str) -> bool:
        """Delete a workflow.

        Args:
            user_id: The user's UUID.
            workflow_name: The workflow name.

        Returns:
            True if deleted, False otherwise.
        """
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("workflow_name", workflow_name)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)

    # ==========================
    # Utilities
    # ==========================

    def normalize_request(self, request: str) -> str:
        """Normalize request text for pattern matching.

        Converts to lowercase, removes punctuation,
        removes stopwords, and normalizes whitespace.

        Args:
            request: Raw request text.

        Returns:
            Normalized request string.
        """
        # Convert to lowercase
        normalized = request.lower()

        # Remove punctuation (keep alphanumeric and spaces)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # Common stopwords to remove
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

        # Split, filter stopwords, and rejoin
        words = normalized.split()
        words = [w for w in words if w not in stopwords and len(w) > 1]

        return ' '.join(words)

    def generate_workflow_name(self, agents: List[str], pattern: str) -> str:
        """Generate a unique workflow name from agents and pattern.

        Args:
            agents: List of agent names.
            pattern: Workflow pattern type.

        Returns:
            Generated workflow name.
        """
        agent_part = '_'.join(sorted(agents)[:3])  # Use first 3 sorted agents
        return f"{pattern}_{agent_part}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


# =============================================================================
# Module-level helpers
# =============================================================================

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

