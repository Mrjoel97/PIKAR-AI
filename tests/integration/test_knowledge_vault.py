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

"""Integration tests for Knowledge Vault ingestion and retrieval.

These tests require a running Supabase instance with environment variables:
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
"""

import os
import pytest


# Skip all tests in this module if Supabase credentials are not set
pytestmark = pytest.mark.skipif(
    not all(
        os.environ.get(var)
        for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    ),
    reason="Supabase credentials not provided in environment variables.",
)


class TestKnowledgeVaultIngestion:
    """Integration tests for Knowledge Vault ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_brain_dump_creates_embeddings(self):
        """Test that ingesting a brain dump creates embeddings in the database."""
        from app.rag.knowledge_vault import ingest_brain_dump
        
        sample_content = """
        Pikar AI is a business automation platform.
        We help companies automate their workflows using AI agents.
        Our target market includes small businesses and enterprises.
        Key features: Multi-agent orchestration, Knowledge Vault, Visual Workflow Builder.
        """
        
        result = await ingest_brain_dump(
            content=sample_content,
            title="Company Overview",
            metadata={"test": True}
        )
        
        assert result["success"] is True
        assert result["chunk_count"] > 0
        assert len(result["embedding_ids"]) > 0

    @pytest.mark.asyncio
    async def test_ingest_empty_content_fails(self):
        """Test that ingesting empty content returns an error."""
        from app.rag.knowledge_vault import ingest_brain_dump
        
        result = await ingest_brain_dump(content="", title="Empty")
        
        assert result["success"] is False
        assert "error" in result


class TestKnowledgeVaultSearch:
    """Integration tests for Knowledge Vault search."""

    def test_search_knowledge_returns_results(self):
        """Test that searching knowledge returns relevant results."""
        from app.rag.knowledge_vault import search_knowledge
        
        # This test assumes some data has been ingested
        result = search_knowledge("business automation", top_k=3)
        
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_empty_query_returns_empty(self):
        """Test that an empty query returns empty results."""
        from app.rag.knowledge_vault import search_knowledge
        
        result = search_knowledge("", top_k=5)
        
        assert "results" in result
        assert result["results"] == []
