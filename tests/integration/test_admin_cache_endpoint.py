"""Focused tests for /admin/cache/invalidate authorization and safety behavior."""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import app.services.cache as cache_module

# Ensure repo root is importable when running from app/tests
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import fast_api_app


class _StubCacheService:
    def __init__(self) -> None:
        self.invalidated_user_ids: list[str] = []
        self.flush_count = 0

    async def invalidate_user_all(self, user_id: str) -> bool:
        self.invalidated_user_ids.append(user_id)
        return True

    async def flush_all(self) -> bool:
        self.flush_count += 1
        return True


def _set_verify_user(user: dict) -> None:
    fast_api_app.app.dependency_overrides[fast_api_app.verify_token] = lambda: user


def _clear_overrides() -> None:
    fast_api_app.app.dependency_overrides.clear()


def test_admin_cache_invalidate_requires_auth() -> None:
    _clear_overrides()
    with TestClient(fast_api_app.app) as client:
        response = client.post("/admin/cache/invalidate?user_id=test-user")
    # HTTPBearer emits 403 when Authorization header is missing
    assert response.status_code == 403


def test_admin_cache_invalidate_rejects_non_admin(monkeypatch) -> None:
    _set_verify_user({"id": "u1", "email": "member@example.com", "role": "member"})
    stub = _StubCacheService()
    monkeypatch.setattr(cache_module, "get_cache_service", lambda: stub)
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/admin/cache/invalidate?user_id=test-user")
        assert response.status_code == 403
        assert stub.invalidated_user_ids == []
        assert stub.flush_count == 0
    finally:
        _clear_overrides()


def test_admin_cache_invalidate_requires_confirm_for_global_flush(monkeypatch) -> None:
    os.environ["ALLOW_ANY_AUTH_ADMIN_ENDPOINT"] = "1"
    _set_verify_user({"id": "admin-user", "email": "admin@example.com", "role": "admin"})
    stub = _StubCacheService()
    monkeypatch.setattr(cache_module, "get_cache_service", lambda: stub)
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/admin/cache/invalidate")
        assert response.status_code == 400
        assert "confirm_flush_all=true" in response.text
        assert stub.flush_count == 0
    finally:
        _clear_overrides()
        os.environ.pop("ALLOW_ANY_AUTH_ADMIN_ENDPOINT", None)


def test_admin_cache_invalidate_user_scope_succeeds(monkeypatch) -> None:
    os.environ["ALLOW_ANY_AUTH_ADMIN_ENDPOINT"] = "1"
    _set_verify_user({"id": "admin-user", "email": "admin@example.com", "role": "admin"})
    stub = _StubCacheService()
    monkeypatch.setattr(cache_module, "get_cache_service", lambda: stub)
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/admin/cache/invalidate?user_id=user-123")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert "user-123" in body["message"]
        assert stub.invalidated_user_ids == ["user-123"]
        assert stub.flush_count == 0
    finally:
        _clear_overrides()
        os.environ.pop("ALLOW_ANY_AUTH_ADMIN_ENDPOINT", None)


def test_admin_cache_invalidate_global_flush_with_confirm_succeeds(monkeypatch) -> None:
    os.environ["ALLOW_ANY_AUTH_ADMIN_ENDPOINT"] = "1"
    _set_verify_user({"id": "admin-user", "email": "admin@example.com", "role": "admin"})
    stub = _StubCacheService()
    monkeypatch.setattr(cache_module, "get_cache_service", lambda: stub)
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/admin/cache/invalidate?confirm_flush_all=true")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert "All caches invalidated" in body["message"]
        assert stub.invalidated_user_ids == []
        assert stub.flush_count == 1
    finally:
        _clear_overrides()
        os.environ.pop("ALLOW_ANY_AUTH_ADMIN_ENDPOINT", None)
