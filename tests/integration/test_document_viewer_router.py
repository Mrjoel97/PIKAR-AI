"""Integration tests for the document-viewer HTTP router.

The tests use FastAPI's ``app.dependency_overrides`` to (a) bypass real
Supabase JWT validation and (b) swap the service factories with
``AsyncMock``-backed stand-ins, so each test exercises the router logic
in isolation (404 / 403 / response shape) without hitting a real database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.routers.document_viewer as document_viewer
import app.routers.onboarding as onboarding_router
from app import fast_api_app


@pytest.fixture
def client():
    """Wire up a TestClient with mocked auth + mocked services.

    Yields a 4-tuple: ``(client, user_id, source_service, version_service)``.
    The two service mocks are :class:`AsyncMock` instances; tests configure
    their return values per-case.

    Both ``_source_service`` and ``_version_service`` are overridden via
    ``app.dependency_overrides`` (rather than ``monkeypatch``) because
    FastAPI captures the dependency callable when the route is registered;
    swapping the module attribute later does not redirect the injection.
    """
    test_user_id = str(uuid4())
    source_service = AsyncMock()
    version_service = AsyncMock()

    async def _override_source_service():
        return source_service

    async def _override_version_service():
        return version_service

    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = (
        lambda: test_user_id
    )
    fast_api_app.app.dependency_overrides[document_viewer._source_service] = (
        _override_source_service
    )
    fast_api_app.app.dependency_overrides[document_viewer._version_service] = (
        _override_version_service
    )

    try:
        with TestClient(fast_api_app.app) as test_client:
            yield test_client, test_user_id, source_service, version_service
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_get_source_returns_404_when_unknown(client) -> None:
    """If ``DocumentSourceService.get`` returns ``None``, the endpoint 404s."""
    test_client, _user_id, source_service, _version_service = client
    source_service.get.return_value = None

    response = test_client.get(f"/documents/{uuid4()}/source")

    assert response.status_code == 404
    # The app's global HTTPException handler maps `detail` to `message`
    # in a structured ErrorResponse envelope.
    assert response.json()["message"] == "Document not found"


def test_get_source_returns_data_when_owned(client) -> None:
    """Happy path: owner gets the full SourceResponse."""
    test_client, user_id, source_service, _version_service = client
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "user_id": user_id,
        "doc_class": "spreadsheet",
        "binary_url": "https://example.test/sheet.xlsx",
        "source": {"rows": [{"a": 1}]},
        "forked_from_upload": True,
    }

    response = test_client.get(f"/documents/{document_id}/source")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "document_id": document_id,
        "doc_class": "spreadsheet",
        "binary_url": "https://example.test/sheet.xlsx",
        "source": {"rows": [{"a": 1}]},
        "forked_from_upload": True,
    }


def test_get_versions_filters_to_user(client) -> None:
    """``GET /versions`` drops rows that belong to other users."""
    test_client, user_id, _source_service, version_service = client
    document_id = str(uuid4())
    other_user = str(uuid4())
    now_iso = datetime.now(UTC).isoformat()
    version_service.list.return_value = [
        {
            "id": "v-mine",
            "user_id": user_id,
            "document_id": document_id,
            "diff_summary": "tweak",
            "binary_url": "https://example.test/v1.pdf",
            "created_at": now_iso,
            "created_by": "agent",
        },
        {
            "id": "v-theirs",
            "user_id": other_user,
            "document_id": document_id,
            "diff_summary": "leak attempt",
            "binary_url": "https://example.test/v2.pdf",
            "created_at": now_iso,
            "created_by": "agent",
        },
    ]

    response = test_client.get(f"/documents/{document_id}/versions")

    assert response.status_code == 200
    versions = response.json()["versions"]
    assert len(versions) == 1
    assert versions[0]["id"] == "v-mine"


def test_revert_404_when_target_version_missing(client) -> None:
    """Unknown ``target_version_id`` → 404 (not 403)."""
    test_client, _user_id, _source_service, version_service = client
    version_service.get.return_value = None

    response = test_client.post(
        f"/documents/{uuid4()}/revert",
        json={"target_version_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Target version not found"


def test_revert_happy_path(client) -> None:
    """Owner reverts: source_svc is updated and a new version is appended."""
    test_client, user_id, source_service, version_service = client
    document_id = str(uuid4())
    target_version_id = str(uuid4())
    new_version_id = str(uuid4())

    version_service.get.return_value = {
        "id": target_version_id,
        "document_id": document_id,
        "user_id": user_id,
        "source_snapshot": {"hello": "world"},
        "binary_url": "https://example.test/old.pdf",
        "diff_summary": "older diff",
        "created_by": "agent",
    }
    version_service.append.return_value = {
        "id": new_version_id,
        "document_id": document_id,
        "user_id": user_id,
        "source_snapshot": {"hello": "world"},
        "binary_url": "https://example.test/old.pdf",
        "diff_summary": f"Reverted to {target_version_id[:8]}",
        "created_by": "user",
    }
    source_service.update_source.return_value = {"document_id": document_id}

    response = test_client.post(
        f"/documents/{document_id}/revert",
        json={"target_version_id": target_version_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["new_version_id"] == new_version_id
    assert payload["new_binary_url"] == "https://example.test/old.pdf"
    assert payload["diff_summary"] == f"Reverted to {target_version_id[:8]}"

    # Verify the side-effects
    source_service.update_source.assert_awaited_once_with(
        document_id=document_id,
        new_source={"hello": "world"},
        new_binary_url="https://example.test/old.pdf",
    )
    version_service.append.assert_awaited_once()
    append_kwargs = version_service.append.await_args.kwargs
    assert append_kwargs["created_by"] == "user"
    assert append_kwargs["user_id"] == user_id
    assert append_kwargs["document_id"] == document_id
