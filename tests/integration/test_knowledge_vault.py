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

Live tests (class TestKnowledgeVaultIngestion, TestKnowledgeVaultSearch)
require a running Supabase instance:
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY

Concurrency and search-path regression tests (TestConcurrentVaultOperations,
TestSearchPathRegression) use mocks and run in any environment.

Run concurrency/search tests:
    pytest tests/integration/test_knowledge_vault.py -k "concurrent or search or latency" -x
"""

from __future__ import annotations

import asyncio
import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub supabase and heavy transitive imports BEFORE any app module is loaded.
# The test environment has an incomplete supabase package; the mock-based tests
# only care about app.rag.knowledge_vault behaviour, not the Supabase SDK.
# ---------------------------------------------------------------------------

def _stub(path: str, **attrs: object) -> None:
    """Inject a stub module into sys.modules if not already present."""
    if path not in sys.modules:
        mod = types.ModuleType(path)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[path] = mod


# supabase SDK stubs
_stub("supabase._async", AsyncClient=MagicMock, create_client=MagicMock())
_stub("supabase._async.client", AsyncClient=MagicMock, create_client=MagicMock())
_stub("supabase.lib", ClientOptions=MagicMock)
_stub("supabase.lib.client_options", AsyncClientOptions=MagicMock, SyncClientOptions=MagicMock)
_stub("supabase", Client=MagicMock, create_client=MagicMock())

# Stub the supabase_client service so knowledge_vault can be imported cleanly
_MOCK_SUPABASE_CLIENT = MagicMock()
_stub(
    "app.services.supabase_client",
    get_async_client=AsyncMock(return_value=_MOCK_SUPABASE_CLIENT),
    get_client_stats=MagicMock(return_value={"client_created": True, "creation_count": 1, "is_singleton": True, "max_connections": 10}),
    invalidate_client=MagicMock(),
)


# ---------------------------------------------------------------------------
# Live integration tests (skipped without Supabase credentials)
# ---------------------------------------------------------------------------

_live_mark = pytest.mark.skipif(
    not all(
        os.environ.get(var)
        for var in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    ),
    reason="Supabase credentials not provided in environment variables.",
)


@_live_mark
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
            metadata={"test": True},
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


@_live_mark
class TestKnowledgeVaultSearch:
    """Integration tests for Knowledge Vault search."""

    @pytest.mark.asyncio
    async def test_search_knowledge_returns_results(self):
        """Test that searching knowledge returns relevant results."""
        from app.rag.knowledge_vault import search_knowledge

        result = await search_knowledge("business automation", top_k=3)

        assert "results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self):
        """Test that an empty query returns empty results."""
        from app.rag.knowledge_vault import search_knowledge

        result = await search_knowledge("", top_k=5)

        assert "results" in result
        assert result["results"] == []


# ---------------------------------------------------------------------------
# Concurrent ingestion + search regression tests (mock-based, always run)
# ---------------------------------------------------------------------------


def _make_mock_supabase() -> MagicMock:
    """Build a mock Supabase client that supports table and rpc calls."""
    client = MagicMock()

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    insert_execute = AsyncMock(return_value=MagicMock(data=[{"id": "emb-1"}]))
    mock_table.execute = insert_execute
    client.table.return_value = mock_table

    mock_rpc = MagicMock()
    rpc_execute = AsyncMock(
        return_value=MagicMock(
            data=[
                {
                    "content": "matching chunk",
                    "similarity": 0.92,
                    "metadata": {},
                    "source_type": "brain_dump",
                    "source_id": "src-1",
                }
            ]
        )
    )
    mock_rpc.execute = rpc_execute
    client.rpc.return_value = mock_rpc

    return client


class TestConcurrentVaultOperations:
    """Regression coverage for concurrent ingestion + search scenarios.

    These tests verify the v7 contract: overlapping ingestion and search
    against the same user-vault space must not produce corruption,
    duplicate/invalid embedding state, or deadlock/hang.
    """

    @pytest.mark.asyncio
    async def test_concurrent_ingestion_no_duplicate_embedding_ids(self):
        """Concurrent brain-dump ingestions must produce unique embedding IDs.

        Regression: if ingestion shares mutable state across coroutines the
        same UUID may be reused across concurrent calls.
        """
        from app.rag.knowledge_vault import ingest_brain_dump

        mock_client = _make_mock_supabase()

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            AsyncMock(return_value=mock_client),
        ):
            with patch(
                "app.rag.ingestion_service.generate_embeddings_batch",
                return_value=[[0.1] * 768, [0.2] * 768],
            ):
                tasks = [
                    ingest_brain_dump(
                        content=f"Unique content for worker {i} with enough text to produce chunks.",
                        title=f"Worker {i}",
                        user_id="concurrent-user",
                    )
                    for i in range(5)
                ]
                results = await asyncio.gather(*tasks)

        all_ids: list[str] = []
        for r in results:
            assert r["success"] is True, f"Ingestion failed: {r}"
            all_ids.extend(r["embedding_ids"])

        # All embedding IDs across all concurrent calls must be unique
        assert len(all_ids) == len(set(all_ids)), (
            "Duplicate embedding IDs detected across concurrent ingestions"
        )

    @pytest.mark.asyncio
    async def test_concurrent_ingest_and_search_no_deadlock(self):
        """Overlapping ingestion and search must not deadlock or hang.

        Regression: if ingestion and search share a lock without timeout, a
        concurrent scenario can hang indefinitely.
        """
        from app.rag.knowledge_vault import ingest_brain_dump, search_knowledge

        mock_client = _make_mock_supabase()

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            AsyncMock(return_value=mock_client),
        ):
            with patch(
                "app.rag.ingestion_service.generate_embeddings_batch",
                return_value=[[0.1] * 768],
            ):
                with patch(
                    "app.rag.embedding_service.generate_embedding",
                    return_value=[0.1] * 768,
                ):
                    ingest_tasks = [
                        ingest_brain_dump(
                            content=f"Ingestion content {i} for concurrent test scenario.",
                            title=f"Doc {i}",
                            user_id="deadlock-test-user",
                        )
                        for i in range(3)
                    ]
                    search_tasks = [
                        search_knowledge(
                            query=f"search query {i}",
                            top_k=3,
                            user_id="deadlock-test-user",
                        )
                        for i in range(3)
                    ]

                    # Mix ingestion and search concurrently
                    all_tasks = ingest_tasks + search_tasks
                    results = await asyncio.wait_for(
                        asyncio.gather(*all_tasks, return_exceptions=True),
                        timeout=10.0,
                    )

        # Must complete without timeout and without unhandled exceptions
        for r in results:
            assert not isinstance(r, Exception), f"Task raised: {r}"

    @pytest.mark.asyncio
    async def test_concurrent_search_returns_independent_results(self):
        """Concurrent search calls must return independent result sets.

        Regression: if search shares response state across coroutines, result
        sets may be mixed or truncated.
        """
        from app.rag.knowledge_vault import search_knowledge

        call_count = 0

        async def mock_get_client():
            # Each call returns a fresh mock to simulate independent DB queries
            return _make_mock_supabase()

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            side_effect=mock_get_client,
        ):
            with patch(
                "app.rag.embedding_service.generate_embedding",
                return_value=[0.1] * 768,
            ):
                tasks = [
                    search_knowledge(
                        query=f"query for worker {i}",
                        top_k=5,
                        user_id=f"user-{i}",
                    )
                    for i in range(4)
                ]
                results = await asyncio.gather(*tasks)

        # Each result must be a well-formed dict with a results key
        for i, r in enumerate(results):
            assert "results" in r, f"Result {i} missing 'results' key"
            assert isinstance(r["results"], list), f"Result {i} 'results' is not a list"

    @pytest.mark.asyncio
    async def test_concurrent_ingestion_different_users_isolated(self):
        """Ingestions for different users must produce user-scoped embedding records.

        Regression: if user_id is not threaded through correctly under
        concurrent load, embeddings may be attributed to the wrong user.
        """
        from app.rag.knowledge_vault import ingest_brain_dump

        recorded_user_ids: list[str] = []

        async def capture_ingest(supabase_client, content, source_type, metadata, user_id, chunk_size, chunk_overlap):
            recorded_user_ids.append(user_id)
            return [f"emb-{user_id}-0"]

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            AsyncMock(return_value=_make_mock_supabase()),
        ):
            with patch(
                "app.rag.knowledge_vault.ingest_document",
                side_effect=capture_ingest,
            ):
                user_ids = [f"user-{i:03d}" for i in range(5)]
                tasks = [
                    ingest_brain_dump(
                        content=f"Content for {uid}",
                        title=f"Doc for {uid}",
                        user_id=uid,
                    )
                    for uid in user_ids
                ]
                await asyncio.gather(*tasks)

        # Every user_id we passed in must appear exactly once in recorded calls
        assert sorted(recorded_user_ids) == sorted(user_ids), (
            f"User ID isolation broken under concurrent load. "
            f"Expected {sorted(user_ids)}, got {sorted(recorded_user_ids)}"
        )


class TestSearchPathRegression:
    """Regression tests for the search path correctness and latency contract."""

    @pytest.mark.asyncio
    async def test_search_returns_results_from_real_path(self):
        """search_knowledge must call through the real semantic_search path."""
        from app.rag.knowledge_vault import search_knowledge

        mock_client = _make_mock_supabase()

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            AsyncMock(return_value=mock_client),
        ):
            with patch(
                "app.rag.embedding_service.generate_embedding",
                return_value=[0.1] * 768,
            ):
                result = await search_knowledge(
                    query="test query for search path",
                    top_k=3,
                    user_id="search-test-user",
                )

        assert "results" in result
        assert "query" in result
        assert isinstance(result["results"], list)
        # The mock RPC returns one result; verify it is surfaced correctly
        assert len(result["results"]) == 1
        assert result["results"][0]["similarity"] == 0.92

    @pytest.mark.asyncio
    async def test_search_empty_query_bypasses_embedding(self):
        """Empty query must return empty results without calling embedding service."""
        from app.rag.knowledge_vault import search_knowledge

        with patch(
            "app.rag.embedding_service.generate_embedding"
        ) as mock_embed:
            result = await search_knowledge(query="", top_k=5)

        assert result["results"] == []
        mock_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_error_returns_empty_with_error_key(self):
        """Search errors must be caught and returned as empty results with error key."""
        from app.rag.knowledge_vault import search_knowledge

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            AsyncMock(side_effect=RuntimeError("DB connection failed")),
        ):
            result = await search_knowledge(
                query="anything",
                top_k=5,
                user_id="error-test-user",
            )

        assert "results" in result
        assert result["results"] == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_search_latency_is_within_contract(self):
        """Search path must complete well within the 2s latency contract.

        Uses a mock to remove network latency so the test measures code-path
        overhead only. Real latency is measured in run_knowledge_vault_eval.py.
        """
        import time

        from app.rag.knowledge_vault import search_knowledge

        mock_client = _make_mock_supabase()

        with patch(
            "app.rag.knowledge_vault.get_supabase_client",
            AsyncMock(return_value=mock_client),
        ):
            with patch(
                "app.rag.embedding_service.generate_embedding",
                return_value=[0.1] * 768,
            ):
                t_start = time.perf_counter()
                await search_knowledge(query="latency test query", top_k=5)
                elapsed_ms = (time.perf_counter() - t_start) * 1000

        # Code-path overhead (no network) must be well under the 2000ms contract
        assert elapsed_ms < 500, (
            f"Search code-path took {elapsed_ms:.1f}ms — unexpected overhead"
        )
