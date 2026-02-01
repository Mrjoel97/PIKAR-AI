"""ContentService - CRUD operations for content management.

This service provides Create, Read, Update, Delete operations for content
stored in the agent_knowledge table in Supabase with proper RLS authentication.
"""

from typing import Optional
from app.services.base_service import BaseService
from app.rag.knowledge_vault import ingest_document_content


class ContentService(BaseService):
    """Service for managing content in the Knowledge Vault.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the content service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "agent_knowledge"

    async def save_content(self, title: str, content: str, agent_id: str) -> dict:
        """Save generated content to the Knowledge Vault.
        
        Args:
            title: Title of the content.
            content: The text content.
            agent_id: ID of the agent creating the content.
            
        Returns:
            Dictionary with result (success, ids, etc).
        """
        result = await ingest_document_content(
            content=content,
            title=title,
            document_type="generated_content",
            agent_id=agent_id
        )
        return result

    async def get_content(self, content_id: str) -> dict:
        """Retrieve content by ID.
        
        Args:
            content_id: The unique content ID.
            
        Returns:
            The content record.
        """
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("id", content_id)
            .single()
            .execute()
        )
        return response.data

    async def update_content(
        self,
        content_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> dict:
        """Update content.
        
        Args:
            content_id: The unique content ID.
            title: New title (optional).
            content: New content text (optional).
            
        Returns:
            The updated content record.
        """
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
            
        response = (
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", content_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_content(self, content_id: str) -> bool:
        """Delete content by ID.
        
        Args:
            content_id: The unique content ID.
            
        Returns:
            True if deletion was successful.
        """
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("id", content_id)
            .execute()
        )
        return len(response.data) > 0

    async def list_content(
        self,
        content_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """List content with optional filters.
        
        Args:
            content_type: Filter by content type.
            agent_id: Filter by agent ID.
            limit: Maximum number of results (default 50).
            
        Returns:
            List of content records.
        """
        query = self.client.table(self._table_name).select("*")
        
        if content_type:
            query = query.eq("document_type", content_type)
        if agent_id:
            query = query.eq("agent_id", agent_id)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data
