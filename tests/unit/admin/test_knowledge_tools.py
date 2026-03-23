"""Unit tests for AdminAgent knowledge tools (Phase 12.1).

Tests verify:
- upload_knowledge without token returns requires_confirmation
- upload_knowledge with token + document mime delegates to service
- upload_knowledge with token + image mime delegates to service
- upload_knowledge with token + video mime delegates to service
- upload_knowledge passes agent_scope through
- upload_knowledge with agent_scope=None stores as global
- list_knowledge_entries returns entries filtered by agent_scope
- search_knowledge delegates to search_system_knowledge
- delete_knowledge_entry without token returns requires_confirmation
- delete_knowledge_entry with token deletes entry
- get_knowledge_stats_tool returns stats from service
- check_knowledge_duplicate with high similarity returns near_duplicate=True
- check_knowledge_duplicate with low similarity returns near_duplicate=False
- validate_knowledge_relevance checks content against agent domain
- recommend_chunking_strategy returns strategy based on file type and size
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets
_AUTONOMY_PATCH = "app.agents.admin.tools.knowledge._check_autonomy"
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.knowledge.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.knowledge.execute_async"
_KNOWLEDGE_SERVICE_PATCH = "app.agents.admin.tools.knowledge.knowledge_service"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _auto_gate() -> None:
    """Return None to simulate auto-tier (proceed)."""
    return None


def _confirm_gate() -> dict:
    """Return confirm-tier gate dict."""
    return {
        "requires_confirmation": True,
        "confirmation_token": "test-token-uuid",
        "action_details": {
            "action": "upload_knowledge",
            "risk_level": "low",
            "description": "Admin operation: upload_knowledge",
        },
    }


def _build_table_client(table_data: dict) -> MagicMock:
    """Build a mock client that returns different data per table name."""
    client = MagicMock()

    def _table(name: str):
        tbl = MagicMock()
        data = table_data.get(name, [])
        tbl.select.return_value = tbl
        tbl.eq.return_value = tbl
        tbl.gte.return_value = tbl
        tbl.lt.return_value = tbl
        tbl.limit.return_value = tbl
        tbl.order.return_value = tbl
        tbl.update.return_value = tbl
        tbl.insert.return_value = tbl
        tbl.delete.return_value = tbl
        tbl.execute.return_value = MagicMock(data=data)
        return tbl

    client.table.side_effect = _table
    rpc_mock = MagicMock()
    rpc_mock.execute.return_value = MagicMock(data=[])
    client.rpc.return_value = rpc_mock
    return client


# ---------------------------------------------------------------------------
# Tests: upload_knowledge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_knowledge_requires_confirmation():
    """Confirm tier: upload_knowledge without token returns requires_confirmation=True."""
    with patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=_confirm_gate()):
        from app.agents.admin.tools.knowledge import upload_knowledge

        result = await upload_knowledge(
            entry_id="entry-001",
            filename="doc.pdf",
            mime_type="application/pdf",
            agent_scope=None,
            confirmation_token=None,
        )

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result


@pytest.mark.asyncio
async def test_upload_knowledge_with_token_document():
    """Confirm tier + token: upload_knowledge with document mime reads entry from DB."""
    fake_entry = [{
        "id": "entry-001",
        "filename": "doc.pdf",
        "file_type": "document",
        "status": "completed",
        "chunk_count": 5,
        "agent_scope": None,
    }]
    client = _build_table_client({"admin_knowledge_entries": fake_entry})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entry)),
    ):
        from app.agents.admin.tools.knowledge import upload_knowledge

        result = await upload_knowledge(
            entry_id="entry-001",
            filename="doc.pdf",
            mime_type="application/pdf",
            agent_scope=None,
            confirmation_token="fake-token",
        )

    assert result.get("entry_id") == "entry-001"
    assert result.get("status") == "completed"


@pytest.mark.asyncio
async def test_upload_knowledge_with_token_image():
    """Confirm tier + token: upload_knowledge with image mime reads entry from DB."""
    fake_entry = [{
        "id": "entry-002",
        "filename": "photo.png",
        "file_type": "image",
        "status": "completed",
        "chunk_count": 1,
        "agent_scope": "financial",
    }]
    client = _build_table_client({"admin_knowledge_entries": fake_entry})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entry)),
    ):
        from app.agents.admin.tools.knowledge import upload_knowledge

        result = await upload_knowledge(
            entry_id="entry-002",
            filename="photo.png",
            mime_type="image/png",
            agent_scope="financial",
            confirmation_token="fake-token",
        )

    assert result.get("entry_id") == "entry-002"
    assert result.get("file_type") == "image"


@pytest.mark.asyncio
async def test_upload_knowledge_with_token_video():
    """Confirm tier + token: upload_knowledge with video mime reads entry (status=processing)."""
    fake_entry = [{
        "id": "entry-003",
        "filename": "training.mp4",
        "file_type": "video",
        "status": "processing",
        "chunk_count": 0,
        "agent_scope": None,
    }]
    client = _build_table_client({"admin_knowledge_entries": fake_entry})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entry)),
    ):
        from app.agents.admin.tools.knowledge import upload_knowledge

        result = await upload_knowledge(
            entry_id="entry-003",
            filename="training.mp4",
            mime_type="video/mp4",
            agent_scope=None,
            confirmation_token="fake-token",
        )

    assert result.get("entry_id") == "entry-003"
    assert result.get("status") == "processing"


@pytest.mark.asyncio
async def test_upload_with_agent_scope():
    """upload_knowledge passes agent_scope through and returns it in result."""
    fake_entry = [{
        "id": "entry-004",
        "filename": "sales.pdf",
        "file_type": "document",
        "status": "completed",
        "chunk_count": 3,
        "agent_scope": "sales",
    }]
    client = _build_table_client({"admin_knowledge_entries": fake_entry})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entry)),
    ):
        from app.agents.admin.tools.knowledge import upload_knowledge

        result = await upload_knowledge(
            entry_id="entry-004",
            filename="sales.pdf",
            mime_type="application/pdf",
            agent_scope="sales",
            confirmation_token="fake-token",
        )

    assert result.get("agent_scope") == "sales"


@pytest.mark.asyncio
async def test_upload_global_scope():
    """upload_knowledge with agent_scope=None stores as global."""
    fake_entry = [{
        "id": "entry-005",
        "filename": "global.pdf",
        "file_type": "document",
        "status": "completed",
        "chunk_count": 2,
        "agent_scope": None,
    }]
    client = _build_table_client({"admin_knowledge_entries": fake_entry})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entry)),
    ):
        from app.agents.admin.tools.knowledge import upload_knowledge

        result = await upload_knowledge(
            entry_id="entry-005",
            filename="global.pdf",
            mime_type="application/pdf",
            agent_scope=None,
            confirmation_token="fake-token",
        )

    assert result.get("agent_scope") is None


# ---------------------------------------------------------------------------
# Tests: list_knowledge_entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_knowledge_entries():
    """Auto tier: list_knowledge_entries returns entries filtered by agent_scope."""
    fake_entries = [
        {"id": "e1", "filename": "doc1.pdf", "agent_scope": "financial"},
        {"id": "e2", "filename": "doc2.pdf", "agent_scope": "financial"},
    ]
    client = _build_table_client({"admin_knowledge_entries": fake_entries})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entries)),
    ):
        from app.agents.admin.tools.knowledge import list_knowledge_entries

        result = await list_knowledge_entries(agent_scope="financial")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["agent_scope"] == "financial"


# ---------------------------------------------------------------------------
# Tests: search_knowledge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_knowledge():
    """Auto tier: search_knowledge delegates to search_system_knowledge."""
    fake_results = [
        {"content": "Financial data...", "similarity": 0.95, "metadata": {}},
    ]

    mock_service = MagicMock()
    mock_service.search_system_knowledge = AsyncMock(return_value=fake_results)

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_KNOWLEDGE_SERVICE_PATCH, mock_service),
    ):
        from app.agents.admin.tools.knowledge import search_knowledge

        result = await search_knowledge(query="financial reports", agent_name="financial")

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["similarity"] == 0.95
    mock_service.search_system_knowledge.assert_called_once_with(
        query="financial reports", agent_name="financial", top_k=5
    )


# ---------------------------------------------------------------------------
# Tests: delete_knowledge_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_requires_confirmation():
    """Confirm tier: delete_knowledge_entry without token returns requires_confirmation."""
    gate = {
        "requires_confirmation": True,
        "confirmation_token": "token-del",
        "action_details": {"action": "delete_knowledge_entry"},
    }

    with patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=gate):
        from app.agents.admin.tools.knowledge import delete_knowledge_entry

        result = await delete_knowledge_entry(
            entry_id="entry-001",
            confirmation_token=None,
        )

    assert result.get("requires_confirmation") is True


@pytest.mark.asyncio
async def test_delete_with_token():
    """Confirm tier + token: delete_knowledge_entry deletes entry and embeddings."""
    fake_entry = [{"id": "entry-001", "file_path": "entry-001/doc.pdf"}]
    client = _build_table_client({"admin_knowledge_entries": fake_entry})

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_SERVICE_CLIENT_PATCH, return_value=client),
        patch(_EXECUTE_ASYNC_PATCH, new_callable=AsyncMock,
              return_value=MagicMock(data=fake_entry)),
    ):
        from app.agents.admin.tools.knowledge import delete_knowledge_entry

        result = await delete_knowledge_entry(
            entry_id="entry-001",
            confirmation_token="fake-token",
        )

    assert result.get("deleted") is True
    assert result.get("entry_id") == "entry-001"


# ---------------------------------------------------------------------------
# Tests: get_knowledge_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_knowledge_stats_tool():
    """Auto tier: get_knowledge_stats_tool returns stats from service."""
    fake_stats = {
        "total_entries": 10,
        "total_embeddings": 50,
        "by_agent": {"financial": 3, "global": 7},
        "storage_bytes": 1024000,
    }

    mock_service = MagicMock()
    mock_service.get_knowledge_stats = AsyncMock(return_value=fake_stats)

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_KNOWLEDGE_SERVICE_PATCH, mock_service),
    ):
        from app.agents.admin.tools.knowledge import get_knowledge_stats

        result = await get_knowledge_stats()

    assert result["total_entries"] == 10
    assert result["total_embeddings"] == 50
    mock_service.get_knowledge_stats.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: check_knowledge_duplicate (SKIL-09)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_duplicate_detected():
    """check_knowledge_duplicate with high similarity returns near_duplicate=True."""
    high_sim_result = [{"content": "Similar doc", "similarity": 0.95, "metadata": {}}]

    mock_service = MagicMock()
    mock_service.search_system_knowledge = AsyncMock(return_value=high_sim_result)

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_KNOWLEDGE_SERVICE_PATCH, mock_service),
    ):
        from app.agents.admin.tools.knowledge import check_knowledge_duplicate

        result = await check_knowledge_duplicate(
            text_sample="This is a financial document about revenue",
            agent_scope="financial",
            threshold=0.92,
        )

    assert result.get("near_duplicate") is True
    assert result.get("similarity") == 0.95


@pytest.mark.asyncio
async def test_check_duplicate_not_detected():
    """check_knowledge_duplicate with low similarity returns near_duplicate=False."""
    low_sim_result = [{"content": "Different doc", "similarity": 0.70, "metadata": {}}]

    mock_service = MagicMock()
    mock_service.search_system_knowledge = AsyncMock(return_value=low_sim_result)

    with (
        patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None),
        patch(_KNOWLEDGE_SERVICE_PATCH, mock_service),
    ):
        from app.agents.admin.tools.knowledge import check_knowledge_duplicate

        result = await check_knowledge_duplicate(
            text_sample="This is a unique marketing document",
            agent_scope=None,
            threshold=0.92,
        )

    assert result.get("near_duplicate") is False
    assert "closest_similarity" in result


# ---------------------------------------------------------------------------
# Tests: validate_knowledge_relevance (SKIL-09)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_knowledge_relevance():
    """validate_knowledge_relevance checks content against agent domain."""
    with patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None):
        from app.agents.admin.tools.knowledge import validate_knowledge_relevance

        result = await validate_knowledge_relevance(
            text_sample="This document covers quarterly revenue, profit margins, and financial forecasting",
            target_agent="financial",
        )

    assert "relevant" in result
    assert "confidence" in result
    assert "reason" in result
    assert isinstance(result["relevant"], bool)
    assert isinstance(result["confidence"], float)


# ---------------------------------------------------------------------------
# Tests: recommend_chunking_strategy (SKIL-09)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommend_chunking_strategy():
    """recommend_chunking_strategy returns strategy based on file type and size."""
    with patch(_AUTONOMY_PATCH, new_callable=AsyncMock, return_value=None):
        from app.agents.admin.tools.knowledge import recommend_chunking_strategy

        # Standard document >50KB
        result = await recommend_chunking_strategy(
            filename="large_report.pdf",
            file_size_bytes=75_000,
            mime_type="application/pdf",
        )

    assert "chunk_size" in result
    assert "chunk_overlap" in result
    assert "estimated_chunks" in result
    assert "warnings" in result
    assert isinstance(result["warnings"], list)
    # Standard doc >50KB should use chunk_size=500
    assert result["chunk_size"] == 500
    assert result["chunk_overlap"] == 50
