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

"""Unit tests for RAG services (embedding, ingestion, search)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestEmbeddingService:
    """Tests for the embedding service."""

    def test_generate_embedding_returns_vector(self):
        """Test that generate_embedding returns a list of floats with correct dimension."""
        from app.rag.embedding_service import generate_embedding
        
        with patch('app.rag.embedding_service.TextEmbeddingModel') as mock_model:
            # Mock the embedding response
            mock_embedding = MagicMock()
            mock_embedding.values = [0.1] * 768  # 768-dimensional vector
            mock_model_instance = MagicMock()
            mock_model_instance.get_embeddings.return_value = [mock_embedding]
            mock_model.from_pretrained.return_value = mock_model_instance
            
            result = generate_embedding("test text")
            
            assert isinstance(result, list)
            assert len(result) == 768
            assert all(isinstance(x, float) for x in result)

    def test_generate_embedding_handles_empty_text(self):
        """Test that generate_embedding handles empty text gracefully."""
        from app.rag.embedding_service import generate_embedding
        
        with patch('app.rag.embedding_service.TextEmbeddingModel') as mock_model:
            mock_embedding = MagicMock()
            mock_embedding.values = [0.0] * 768
            mock_model_instance = MagicMock()
            mock_model_instance.get_embeddings.return_value = [mock_embedding]
            mock_model.from_pretrained.return_value = mock_model_instance
            
            result = generate_embedding("")
            
            assert isinstance(result, list)
            assert len(result) == 768


class TestIngestionService:
    """Tests for the ingestion service."""

    def test_chunk_text_creates_proper_chunks(self):
        """Test that chunk_text creates chunks with proper size and overlap."""
        from app.rag.ingestion_service import chunk_text
        
        # Create text that's longer than chunk size
        text = "word " * 200  # ~1000 characters
        
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        # Each chunk should be <= chunk_size (except possibly the last)
        for chunk in chunks[:-1]:
            assert len(chunk) <= 100 + 20  # chunk_size + some tolerance for word boundaries

    def test_chunk_text_handles_short_text(self):
        """Test that chunk_text handles text shorter than chunk size."""
        from app.rag.ingestion_service import chunk_text
        
        text = "This is a short text."
        
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0] == text


class TestSearchService:
    """Tests for the search service."""

    def test_format_search_results(self):
        """Test that search results are formatted correctly."""
        from app.rag.search_service import format_search_results
        
        raw_results = [
            {"content": "Test content 1", "metadata": {"source": "doc1"}, "similarity": 0.95},
            {"content": "Test content 2", "metadata": {"source": "doc2"}, "similarity": 0.85},
        ]
        
        formatted = format_search_results(raw_results)
        
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        assert "content" in formatted[0]
        assert "similarity" in formatted[0]
