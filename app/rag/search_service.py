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

"""Search service for semantic search in the Knowledge Vault.

Uses pgvector for similarity search on embeddings stored in Supabase.
"""

from typing import Any

from app.rag.embedding_service import generate_embedding


def format_search_results(raw_results: list[dict]) -> list[dict]:
    """Format raw database results for API response.
    
    Args:
        raw_results: Raw results from the database query.
        
    Returns:
        Formatted list of search results.
    """
    formatted = []
    for result in raw_results:
        formatted.append({
            "content": result.get("content", ""),
            "similarity": result.get("similarity", 0.0),
            "metadata": result.get("metadata", {}),
            "source_type": result.get("source_type", ""),
            "source_id": result.get("source_id", ""),
        })
    return formatted


async def semantic_search(
    supabase_client: Any,
    query: str,
    top_k: int = 5,
    user_id: str | None = None,
    agent_id: str | None = None,
    similarity_threshold: float = 0.5
) -> list[dict]:
    """Perform semantic search on the Knowledge Vault.
    
    Args:
        supabase_client: Supabase client instance.
        query: The search query.
        top_k: Number of results to return.
        user_id: Optional user ID for multi-tenant filtering.
        agent_id: Optional agent ID for agent-specific knowledge.
        similarity_threshold: Minimum similarity score (0-1).
        
    Returns:
        List of matching documents with similarity scores.
    """
    if not query or not query.strip():
        return []
    
    # Generate embedding for the query
    query_embedding = generate_embedding(query)
    
    # Build the RPC call for vector similarity search
    # This uses a Postgres function that we'll need to create
    rpc_params = {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "match_threshold": similarity_threshold,
    }
    
    if user_id:
        rpc_params["filter_user_id"] = user_id
    if agent_id:
        rpc_params["filter_agent_id"] = agent_id
    
    # Call the search function
    response = supabase_client.rpc("match_embeddings", rpc_params).execute()
    
    if response.data:
        return format_search_results(response.data)
    
    return []


def search_knowledge_sync(
    supabase_client: Any,
    query: str,
    top_k: int = 5,
    user_id: str | None = None
) -> dict:
    """Synchronous wrapper for semantic search (for use in agent tools).
    
    Args:
        supabase_client: Supabase client instance.
        query: The search query.
        top_k: Number of results to return.
        user_id: Optional user ID for multi-tenant filtering.
        
    Returns:
        Dictionary with 'results' key containing search results.
    """
    if not query or not query.strip():
        return {"results": [], "query": query}
    
    # Generate embedding for the query
    query_embedding = generate_embedding(query)
    
    # Call the match_embeddings function
    try:
        response = supabase_client.rpc(
            "match_embeddings",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "match_threshold": 0.5,
            }
        ).execute()
        
        results = format_search_results(response.data) if response.data else []
        return {"results": results, "query": query}
    
    except Exception as e:
        # Return empty results on error, log for debugging
        print(f"Search error: {e}")
        return {"results": [], "query": query, "error": str(e)}
