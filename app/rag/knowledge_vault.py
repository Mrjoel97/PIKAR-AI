# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Knowledge Vault service for managing business knowledge.

Provides high-level API for ingesting various knowledge sources
(brain dumps, documents, URLs) into the Knowledge Vault.
"""

import os
from typing import Any
from supabase import create_client, Client

from app.rag.ingestion_service import ingest_document


def get_supabase_client() -> Client:
    """Get or create a Supabase client.
    
    Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables required"
        )
    
    return create_client(url, key)


async def ingest_brain_dump(
    content: str,
    title: str | None = None,
    user_id: str | None = None,
    metadata: dict | None = None
) -> dict:
    """Ingest a brain dump into the Knowledge Vault.
    
    Brain dumps are free-form text containing business context,
    ideas, or knowledge that should be searchable by agents.
    
    Args:
        content: The brain dump text content.
        title: Optional title for the brain dump.
        user_id: Optional user ID for multi-tenant isolation.
        metadata: Optional additional metadata.
        
    Returns:
        Dictionary with ingestion results including embedding IDs.
    """
    if not content or not content.strip():
        return {
            "success": False,
            "error": "Content cannot be empty",
            "embedding_ids": []
        }
    
    client = get_supabase_client()
    
    # Prepare metadata
    ingest_metadata = {
        **(metadata or {}),
        "title": title,
        "source": "brain_dump",
    }
    
    # Ingest the document
    embedding_ids = await ingest_document(
        supabase_client=client,
        content=content,
        source_type="brain_dump",
        metadata=ingest_metadata,
        user_id=user_id,
        chunk_size=500,
        chunk_overlap=50
    )
    
    return {
        "success": True,
        "embedding_ids": embedding_ids,
        "chunk_count": len(embedding_ids),
        "title": title
    }


async def ingest_document_content(
    content: str,
    title: str,
    document_type: str = "document",
    user_id: str | None = None,
    agent_id: str | None = None,
    metadata: dict | None = None
) -> dict:
    """Ingest a document into the Knowledge Vault.
    
    Args:
        content: The document text content.
        title: Document title.
        document_type: Type of document (e.g., 'document', 'url', 'email').
        user_id: Optional user ID for multi-tenant isolation.
        agent_id: Optional agent ID for agent-specific knowledge.
        metadata: Optional additional metadata.
        
    Returns:
        Dictionary with ingestion results.
    """
    if not content or not content.strip():
        return {
            "success": False,
            "error": "Content cannot be empty",
            "embedding_ids": []
        }
    
    client = get_supabase_client()
    
    ingest_metadata = {
        **(metadata or {}),
        "title": title,
        "document_type": document_type,
    }
    
    embedding_ids = await ingest_document(
        supabase_client=client,
        content=content,
        source_type=document_type,
        metadata=ingest_metadata,
        user_id=user_id,
        agent_id=agent_id,
        chunk_size=500,
        chunk_overlap=50
    )
    
    return {
        "success": True,
        "embedding_ids": embedding_ids,
        "chunk_count": len(embedding_ids),
        "title": title
    }


def search_knowledge(
    query: str,
    top_k: int = 5,
    user_id: str | None = None
) -> dict:
    """Search the Knowledge Vault synchronously.
    
    This is the main entry point for agent tools to search knowledge.
    
    Args:
        query: The search query.
        top_k: Number of results to return.
        user_id: Optional user ID for multi-tenant filtering.
        
    Returns:
        Dictionary with 'results' key containing search results.
    """
    from app.rag.search_service import search_knowledge_sync
    
    try:
        client = get_supabase_client()
        return search_knowledge_sync(client, query, top_k, user_id)
    except Exception as e:
        # Return empty results on error
        return {
            "results": [],
            "query": query,
            "error": str(e)
        }


def get_content_by_id(content_id: str) -> dict | None:
    """Retrieve a specific content item by its ID.
    
    Args:
        content_id: The unique ID of the content item.
        
    Returns:
        The content record or None if not found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("agent_knowledge")
            .select("*")
            .eq("id", content_id)
            .single()
            .execute()
        )
        return response.data
    except Exception:
        return None


def list_agent_content(
    agent_id: str | None = None,
    content_type: str | None = None,
    limit: int = 50
) -> list:
    """List content items from the Knowledge Vault.
    
    Args:
        agent_id: Optional filter by agent ID.
        content_type: Optional filter by content type (e.g., 'generated_content').
        limit: Maximum number of items to return.
        
    Returns:
        List of content records.
    """
    try:
        client = get_supabase_client()
        query = client.table("agent_knowledge").select("*")
        
        if agent_id:
            query = query.eq("agent_id", agent_id)
        if content_type:
            query = query.eq("document_type", content_type)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception:
        return []

