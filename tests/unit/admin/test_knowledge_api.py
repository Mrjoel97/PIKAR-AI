"""Unit tests for admin knowledge REST API endpoints (Phase 12.1).

Tests verify:
- POST /admin/knowledge/upload without auth returns 403
- POST /admin/knowledge/upload with PDF returns 200 with entry_id and chunk_count
- POST /admin/knowledge/upload with image returns 200 with entry_id and description
- POST /admin/knowledge/upload with video returns 202 with entry_id and status=processing
- GET /admin/knowledge/entries returns paginated list
- GET /admin/knowledge/entries?agent_scope=financial returns filtered list
- GET /admin/knowledge/stats returns counts and storage usage
- DELETE /admin/knowledge/entries/{entry_id} removes entry
- GET /admin/knowledge/entries/{entry_id} returns single entry details
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest
from starlette.testclient import TestClient

# Patch targets
_SERVICE_CLIENT_PATCH = "app.routers.admin.knowledge.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.routers.admin.knowledge.execute_async"
_PROCESS_DOCUMENT_PATCH = "app.routers.admin.knowledge.knowledge_service.process_document"
_PROCESS_IMAGE_PATCH = "app.routers.admin.knowledge.knowledge_service.process_image"
_PROCESS_VIDEO_PATCH = "app.routers.admin.knowledge.knowledge_service.process_video"
_GET_STATS_PATCH = "app.routers.admin.knowledge.knowledge_service.get_knowledge_stats"
_SEARCH_PATCH = "app.routers.admin.knowledge.knowledge_service.search_system_knowledge"
_REQUIRE_ADMIN_PATCH = "app.routers.admin.knowledge.require_admin"


def _make_app_with_router():
    """Create a minimal FastAPI app with the knowledge router mounted."""
    from fastapi import FastAPI

    from app.routers.admin.knowledge import router

    app = FastAPI()
    app.include_router(router, prefix="/admin")
    return app


def _build_fake_admin():
    """Return a fake admin user dict."""
    return {"id": "admin-uuid", "email": "admin@test.com"}


def _build_chain(data):
    """Build a Supabase-style query chain mock."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.offset.return_value = chain
    chain.delete.return_value = chain
    chain.update.return_value = chain
    chain.insert.return_value = chain
    chain._return_data = data
    return chain


async def _fake_execute_async(query, **kwargs):
    """Simulate execute_async returning query._return_data."""
    result = MagicMock()
    result.data = getattr(query, "_return_data", [])
    result.count = len(result.data)
    return result


# ---------------------------------------------------------------------------
# Test 1: Upload without auth returns 403
# ---------------------------------------------------------------------------


def test_upload_file_requires_auth():
    """POST /admin/knowledge/upload without auth header returns 403."""
    app = _make_app_with_router()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/admin/knowledge/upload",
        data={"uploaded_by": "admin"},
        files={"file": ("test.pdf", b"fake content", "application/pdf")},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Test 2: Upload PDF returns 200 with entry_id and chunk_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf():
    """POST /admin/knowledge/upload with PDF returns 200 with entry_id and chunk_count."""
    fake_result = {"entry_id": "entry-001", "chunk_count": 5, "status": "completed"}

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    with patch(_PROCESS_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=fake_result):
        client = TestClient(app)
        response = client.post(
            "/admin/knowledge/upload",
            data={"uploaded_by": "admin@test.com"},
            files={"file": ("report.pdf", b"PDF content here", "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["entry_id"] == "entry-001"
    assert data["chunk_count"] == 5


@pytest.mark.asyncio
async def test_upload_xlsx():
    """POST /admin/knowledge/upload should accept spreadsheet MIME types."""
    fake_result = {"entry_id": "entry-002", "chunk_count": 3, "status": "completed"}

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    with patch(_PROCESS_DOCUMENT_PATCH, new_callable=AsyncMock, return_value=fake_result):
        client = TestClient(app)
        response = client.post(
            "/admin/knowledge/upload",
            data={"uploaded_by": "admin@test.com"},
            files={
                "file": (
                    "pipeline.xlsx",
                    b"PK fake xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["entry_id"] == "entry-002"
    assert data["chunk_count"] == 3


@pytest.mark.asyncio
async def test_upload_image():
    """POST /admin/knowledge/upload with image returns 200 with entry_id and description."""
    fake_result = {
        "entry_id": "entry-002",
        "description": "A chart showing quarterly revenue",
        "chunk_count": 1,
        "status": "completed",
    }

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    with patch(_PROCESS_IMAGE_PATCH, new_callable=AsyncMock, return_value=fake_result):
        client = TestClient(app)
        response = client.post(
            "/admin/knowledge/upload",
            data={"uploaded_by": "admin@test.com"},
            files={"file": ("chart.png", b"PNG binary data", "image/png")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["entry_id"] == "entry-002"
    assert "description" in data


@pytest.mark.asyncio
async def test_upload_video():
    """POST /admin/knowledge/upload with video returns 202 with entry_id and status=processing."""
    fake_result = {
        "entry_id": "entry-003",
        "status": "processing",
        "message": "Video queued for background transcription",
    }

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    with patch(_PROCESS_VIDEO_PATCH, new_callable=AsyncMock, return_value=fake_result):
        client = TestClient(app)
        response = client.post(
            "/admin/knowledge/upload",
            data={"uploaded_by": "admin@test.com"},
            files={"file": ("training.mp4", b"video bytes", "video/mp4")},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["entry_id"] == "entry-003"
    assert data["status"] == "processing"


def _get_require_admin_dep():
    """Return the require_admin dependency object from the knowledge router."""
    from app.middleware.admin_auth import require_admin

    return require_admin


# ---------------------------------------------------------------------------
# Test 5: GET /admin/knowledge/entries returns paginated list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_entries():
    """GET /admin/knowledge/entries returns paginated list of entries."""
    fake_entries = [
        {"id": "e1", "filename": "doc1.pdf", "agent_scope": None, "status": "completed"},
        {"id": "e2", "filename": "doc2.pdf", "agent_scope": "financial", "status": "completed"},
    ]

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    client_mock = MagicMock()
    chain = _build_chain(fake_entries)
    client_mock.table.return_value = chain

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client_mock),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=_fake_execute_async),
    ):
        client = TestClient(app)
        response = client.get("/admin/knowledge/entries")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_entries_filtered():
    """GET /admin/knowledge/entries?agent_scope=financial returns filtered list."""
    fake_entries = [
        {"id": "e2", "filename": "doc2.pdf", "agent_scope": "financial", "status": "completed"},
    ]

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    client_mock = MagicMock()
    chain = _build_chain(fake_entries)
    client_mock.table.return_value = chain

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client_mock),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=_fake_execute_async),
    ):
        client = TestClient(app)
        response = client.get("/admin/knowledge/entries?agent_scope=financial")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Test 7: GET /admin/knowledge/stats returns stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_knowledge_stats_endpoint():
    """GET /admin/knowledge/stats returns counts and storage usage."""
    fake_stats = {
        "total_entries": 15,
        "total_embeddings": 72,
        "by_agent": {"financial": 5, "global": 10},
        "storage_bytes": 2048000,
    }

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    with patch(_GET_STATS_PATCH, new_callable=AsyncMock, return_value=fake_stats):
        client = TestClient(app)
        response = client.get("/admin/knowledge/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_entries"] == 15
    assert data["storage_bytes"] == 2048000


# ---------------------------------------------------------------------------
# Test 8: DELETE /admin/knowledge/entries/{entry_id} removes entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_entry():
    """DELETE /admin/knowledge/entries/{entry_id} removes entry and returns deleted=True."""
    fake_entry = [{"id": "entry-001", "file_path": "entry-001/doc.pdf"}]

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    delete_chain = _build_chain([])
    entry_chain = _build_chain(fake_entry)
    emb_chain = _build_chain([])

    call_count = 0

    def _table_side_effect(name: str):
        nonlocal call_count
        call_count += 1
        if name == "admin_knowledge_entries" and call_count == 1:
            return entry_chain
        elif name == "embeddings":
            return emb_chain
        return delete_chain

    client_mock = MagicMock()
    client_mock.table.side_effect = _table_side_effect
    client_mock.storage = MagicMock()
    client_mock.storage.from_.return_value = MagicMock()

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client_mock),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=_fake_execute_async),
    ):
        client = TestClient(app)
        response = client.delete("/admin/knowledge/entries/entry-001")

    assert response.status_code == 200
    data = response.json()
    assert data.get("deleted") is True


# ---------------------------------------------------------------------------
# Test 9: GET /admin/knowledge/entries/{entry_id} returns single entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entry():
    """GET /admin/knowledge/entries/{entry_id} returns single entry details."""
    fake_entry = [{
        "id": "entry-001",
        "filename": "report.pdf",
        "file_type": "document",
        "status": "completed",
        "chunk_count": 8,
        "agent_scope": None,
    }]

    app = _make_app_with_router()
    app.dependency_overrides[_get_require_admin_dep()] = lambda: _build_fake_admin()

    client_mock = MagicMock()
    chain = _build_chain(fake_entry)
    client_mock.table.return_value = chain

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=client_mock),
        patch(_EXECUTE_ASYNC_PATCH, side_effect=_fake_execute_async),
    ):
        client = TestClient(app)
        response = client.get("/admin/knowledge/entries/entry-001")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "entry-001"
    assert data["chunk_count"] == 8
