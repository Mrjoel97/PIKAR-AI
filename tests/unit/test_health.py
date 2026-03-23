"""Tests for health probe endpoints."""

from fastapi.testclient import TestClient


def test_startup_probe_returns_200_or_503():
    """Startup probe endpoint exists and returns valid response."""
    from app.fast_api_app import app

    client = TestClient(app)
    response = client.get("/health/startup")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert data["status"] in ("ready", "not_ready")


def test_startup_probe_checks_structure():
    """Startup probe response includes expected check keys."""
    from app.fast_api_app import app

    client = TestClient(app)
    response = client.get("/health/startup")
    data = response.json()
    checks = data["checks"]
    assert "supabase" in checks
    assert "gemini_credentials" in checks
    assert "redis" in checks


def test_liveness_probe_always_returns_200():
    """Liveness probe is dependency-free and always returns 200."""
    from app.fast_api_app import app

    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
