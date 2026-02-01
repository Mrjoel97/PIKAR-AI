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

"""Ingestion service for chunking and storing documents in the Knowledge Vault.

Handles document chunking, embedding generation, and storage in Supabase.
"""

import os
import uuid
from typing import Any

from app.rag.embedding_service import generate_embeddings_batch


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> list[str]:
    """Split text into overlapping chunks.
    
    Args:
        text: The text to chunk.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.
        
    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []
    
    text = text.strip()
    
    # If text is shorter than chunk size, return as single chunk
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Find the end of this chunk
        end = start + chunk_size
        
        # If we're not at the end, try to break at a word boundary
        if end < len(text):
            # Look for the last space within the chunk
            last_space = text.rfind(' ', start, end)
            if last_space > start:
                end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start forward, accounting for overlap
        new_start = end - chunk_overlap if end < len(text) else end
        
        # Prevent infinite loop by ensuring we always make progress
        if new_start <= start:
            new_start = start + 1
        
        start = new_start
    
    return chunks


async def ingest_document(
    supabase_client: Any,
    content: str,
    source_type: str,
    source_id: str | None = None,
    metadata: dict | None = None,
    user_id: str | None = None,
    agent_id: str | None = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> list[str]:
    """Ingest a document into the Knowledge Vault.
    
    Chunks the document, generates embeddings, and stores in the embeddings table.
    
    Args:
        supabase_client: Supabase client instance.
        content: The document content to ingest.
        source_type: Type of source ('brain_dump', 'document', 'url', 'content').
        source_id: Optional ID of the source record.
        metadata: Optional metadata to store with embeddings.
        user_id: Optional user ID for multi-tenant isolation.
        agent_id: Optional agent ID for agent-specific knowledge.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between chunks.
        
    Returns:
        List of embedding IDs created.
    """
    # Chunk the document
    chunks = chunk_text(content, chunk_size, chunk_overlap)
    
    if not chunks:
        return []
    
    # Generate embeddings for all chunks
    embeddings = generate_embeddings_batch(chunks)
    
    # Prepare records for insertion
    source_id = source_id or str(uuid.uuid4())
    embedding_ids = []
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        embedding_id = str(uuid.uuid4())
        embedding_ids.append(embedding_id)
        
        record = {
            "id": embedding_id,
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "agent_id": agent_id,
            "content": chunk,
            "embedding": embedding,
            "metadata": {
                **(metadata or {}),
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
        }
        
        # Insert into Supabase
        supabase_client.table("embeddings").insert(record).execute()
    
    return embedding_ids


def prepare_embedding_record(
    chunk: str,
    embedding: list[float],
    source_type: str,
    source_id: str,
    chunk_index: int,
    total_chunks: int,
    user_id: str | None = None,
    agent_id: str | None = None,
    metadata: dict | None = None
) -> dict:
    """Prepare an embedding record for insertion.
    
    Utility function for batch operations.
    """
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "source_type": source_type,
        "source_id": source_id,
        "agent_id": agent_id,
        "content": chunk,
        "embedding": embedding,
        "metadata": {
            **(metadata or {}),
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
        }
    }
