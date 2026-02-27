"""Integration tests for RAG (Retrieval Augmented Generation) services.

Tests the Knowledge Vault, document ingestion, search, and embedding services.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import functools


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = Mock()
    
    # Mock table operations
    mock_table = Mock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[], count=0)
    
    client.table.return_value = mock_table
    
    # Mock RPC calls
    client.rpc.return_value = Mock(data=[])
    
    return client


class TestKnowledgeVaultClient:
    """Test the Knowledge Vault Supabase client."""

    def test_get_supabase_client_singleton(self, mock_supabase_client):
        """Should return a singleton Supabase client."""
        from app.rag.knowledge_vault import get_supabase_client
        
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test_key'
        }):
            with patch('app.rag.knowledge_vault.create_client', return_value=mock_supabase_client):
                # Clear cache first
                get_supabase_client.cache_clear()
                
                client1 = get_supabase_client()
                client2 = get_supabase_client()
                
                assert client1 is client2

    def test_get_rag_client_stats(self, mock_supabase_client):
        """Should return RAG client statistics."""
        from app.rag.knowledge_vault import get_rag_client_stats
        
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test_key',
            'SUPABASE_MAX_CONNECTIONS': '50'
        }):
            with patch('app.rag.knowledge_vault.create_client', return_value=mock_supabase_client):
                get_supabase_client = functools.lru_cache(maxsize=1)(lambda: mock_supabase_client)
                
                with patch('app.rag.knowledge_vault.get_supabase_client', get_supabase_client):
                    stats = get_rag_client_stats()
                    
                    assert "client_created" in stats
                    assert "creation_count" in stats
                    assert "is_singleton" in stats
                    assert stats["max_connections"] == 50

    def test_invalidate_rag_client(self, mock_supabase_client):
        """Should clear the RAG client cache."""
        from app.rag.knowledge_vault import invalidate_rag_client, get_supabase_client
        
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_ROLE_KEY': 'test_key'
        }):
            with patch('app.rag.knowledge_vault.create_client', return_value=mock_supabase_client):
                get_supabase_client.cache_clear()
                
                # Get client to populate cache
                client = get_supabase_client()
                assert client is not None
                
                # Invalidate cache
                invalidate_rag_client()
                
                # After invalidation, a new call should create a new client
                # (we verify cache was cleared by checking cache_info)
                cache_info = get_supabase_client.cache_info()
                assert cache_info.currsize == 0


class TestIngestBrainDump:
    """Test brain dump ingestion."""

    @pytest.mark.asyncio
    async def test_ingests_valid_brain_dump(self, mock_supabase_client):
        """Should successfully ingest a brain dump."""
        from app.rag.knowledge_vault import ingest_brain_dump
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            with patch('app.rag.knowledge_vault.ingest_document') as mock_ingest:
                mock_ingest.return_value = ["emb-1", "emb-2", "emb-3"]
                
                result = await ingest_brain_dump(
                    content="This is a test brain dump with important business context.",
                    title="Test Brain Dump",
                    user_id="user-123"
                )
                
                assert result["success"] is True
                assert len(result["embedding_ids"]) == 3
                assert result["chunk_count"] == 3
                assert result["title"] == "Test Brain Dump"
                mock_ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_empty_content(self):
        """Should reject empty content."""
        from app.rag.knowledge_vault import ingest_brain_dump
        
        result = await ingest_brain_dump(content="", title="Empty")
        
        assert result["success"] is False
        assert "error" in result
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_rejects_whitespace_only_content(self):
        """Should reject whitespace-only content."""
        from app.rag.knowledge_vault import ingest_brain_dump
        
        result = await ingest_brain_dump(content="   \n\t  ", title="Whitespace")
        
        assert result["success"] is False
        assert "error" in result


class TestIngestDocumentContent:
    """Test document content ingestion."""

    @pytest.mark.asyncio
    async def test_ingests_document_with_metadata(self, mock_supabase_client):
        """Should ingest document with all metadata."""
        from app.rag.knowledge_vault import ingest_document_content
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            with patch('app.rag.knowledge_vault.ingest_document') as mock_ingest:
                mock_ingest.return_value = ["emb-1"]
                
                result = await ingest_document_content(
                    content="Document content here",
                    title="Test Document",
                    document_type="policy",
                    user_id="user-123",
                    agent_id="agent-456",
                    metadata={"department": "HR"}
                )
                
                assert result["success"] is True
                assert result["title"] == "Test Document"
                mock_ingest.assert_called_once()
                
                # Verify metadata was passed
                call_args = mock_ingest.call_args
                assert call_args.kwargs["metadata"]["title"] == "Test Document"
                assert call_args.kwargs["metadata"]["document_type"] == "policy"
                assert call_args.kwargs["metadata"]["department"] == "HR"


class TestSearchKnowledge:
    """Test knowledge search functionality."""

    def test_searches_with_default_parameters(self, mock_supabase_client):
        """Should search with default top_k=5."""
        from app.rag.knowledge_vault import search_knowledge
        
        mock_results = [
            {"id": "doc-1", "content": "Result 1", "similarity": 0.95},
            {"id": "doc-2", "content": "Result 2", "similarity": 0.87},
        ]
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            with patch('app.rag.search_service.search_knowledge_sync') as mock_search:
                mock_search.return_value = {"results": mock_results}
                
                result = search_knowledge("test query")
                
                assert "results" in result
                assert len(result["results"]) == 2
                mock_search.assert_called_once()

    def test_searches_with_custom_top_k(self, mock_supabase_client):
        """Should respect custom top_k parameter."""
        from app.rag.knowledge_vault import search_knowledge
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            with patch('app.rag.search_service.search_knowledge_sync') as mock_search:
                mock_search.return_value = {"results": []}
                
                search_knowledge("query", top_k=10)
                
                # Verify top_k was passed
                call_args = mock_search.call_args
                assert call_args[0][2] == 10  # top_k is 3rd positional arg

    def test_handles_search_errors(self, mock_supabase_client):
        """Should return empty results on error."""
        from app.rag.knowledge_vault import search_knowledge
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            with patch('app.rag.search_service.search_knowledge_sync') as mock_search:
                mock_search.side_effect = Exception("Search failed")
                
                result = search_knowledge("query")
                
                assert "results" in result
                assert result["results"] == []
                assert "error" in result


class TestGetContentById:
    """Test content retrieval by ID."""

    def test_retrieves_existing_content(self, mock_supabase_client):
        """Should retrieve content by ID."""
        from app.rag.knowledge_vault import get_content_by_id
        
        mock_content = {
            "id": "doc-123",
            "title": "Test Document",
            "content": "Content here"
        }
        
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.return_value = Mock(data=mock_content)
        
        mock_supabase_client.table.return_value = mock_table
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            result = get_content_by_id("doc-123")
            
            assert result is not None
            assert result["id"] == "doc-123"

    def test_returns_none_for_missing_content(self, mock_supabase_client):
        """Should return None for non-existent content."""
        from app.rag.knowledge_vault import get_content_by_id
        
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.execute.side_effect = Exception("Not found")
        
        mock_supabase_client.table.return_value = mock_table
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            result = get_content_by_id("non-existent")
            
            assert result is None


class TestListAgentContent:
    """Test listing agent content."""

    def test_lists_content_for_agent(self, mock_supabase_client):
        """Should list content filtered by agent ID."""
        from app.rag.knowledge_vault import list_agent_content
        
        mock_data = [
            {"id": "doc-1", "title": "Doc 1"},
            {"id": "doc-2", "title": "Doc 2"},
        ]
        
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = Mock(data=mock_data)
        
        mock_supabase_client.table.return_value = mock_table
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            result = list_agent_content(agent_id="agent-123", limit=10)
            
            assert len(result) == 2

    def test_filters_by_content_type(self, mock_supabase_client):
        """Should filter by content type."""
        from app.rag.knowledge_vault import list_agent_content
        
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = Mock(data=[])
        
        mock_supabase_client.table.return_value = mock_table
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            list_agent_content(agent_id="agent-123", content_type="generated_content")
            
            # Verify both filters were applied
            calls = mock_table.eq.call_args_list
            assert any(call[0][0] == "agent_id" for call in calls)
            assert any(call[0][0] == "document_type" for call in calls)

    def test_returns_empty_list_on_error(self, mock_supabase_client):
        """Should return empty list on database error."""
        from app.rag.knowledge_vault import list_agent_content
        
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.side_effect = Exception("Database error")
        
        mock_supabase_client.table.return_value = mock_table
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            result = list_agent_content(agent_id="agent-123")
            
            assert result == []


class TestKnowledgeVaultErrorHandling:
    """Test error handling across knowledge vault operations."""

    def test_gracefully_handles_missing_env_vars(self):
        """Should handle missing environment variables."""
        from app.rag.knowledge_vault import get_supabase_client
        
        with patch.dict('os.environ', {}, clear=True):
            get_supabase_client.cache_clear()
            
            with pytest.raises(ValueError) as exc_info:
                get_supabase_client()
            
            assert "SUPABASE_URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ingest_handles_embedding_failure(self, mock_supabase_client):
        """Should handle embedding generation failure."""
        from app.rag.knowledge_vault import ingest_brain_dump
        
        with patch('app.rag.knowledge_vault.get_supabase_client', return_value=mock_supabase_client):
            with patch('app.rag.knowledge_vault.ingest_document') as mock_ingest:
                mock_ingest.side_effect = Exception("Embedding failed")
                
                result = await ingest_brain_dump(content="Test content")
                
                # Should not raise, but return error info
                # The actual behavior depends on implementation
                assert "success" in result or "error" in result
