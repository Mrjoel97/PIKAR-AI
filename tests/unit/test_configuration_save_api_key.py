"""Tests for POST /configuration/save-api-key and mcp-status updates."""
from unittest.mock import patch

from fastapi.testclient import TestClient


def _client_with_user(user_id: str = "u1") -> TestClient:
    """Build a TestClient with the auth dependency overridden."""
    from app.fast_api_app import app
    from app.routers.onboarding import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app)


def test_save_api_key_writes_stitch_key():
    client = _client_with_user("u1")
    with patch("app.services.user_config.set_user_api_key") as mock_set:
        resp = client.post(
            "/configuration/save-api-key",
            json={"tool_id": "stitch", "api_key": "tvly-abc"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    mock_set.assert_called_once_with("u1", "STITCH_API_KEY", "tvly-abc")


def _err_message(resp) -> str:
    """Return the human-readable error string from this app's custom 400 shape."""
    body = resp.json()
    # The app's error middleware returns {"code":..., "message":..., ...} for 4xx.
    return (body.get("message") or body.get("detail") or "").lower()


def test_save_api_key_rejects_unknown_tool():
    client = _client_with_user("u1")
    resp = client.post(
        "/configuration/save-api-key",
        json={"tool_id": "stripe", "api_key": "sk_test"},
    )
    assert resp.status_code == 400
    assert "tool_id" in _err_message(resp)


def test_save_api_key_rejects_empty_key():
    client = _client_with_user("u1")
    resp = client.post(
        "/configuration/save-api-key",
        json={"tool_id": "stitch", "api_key": "   "},
    )
    assert resp.status_code == 400
    assert "api_key" in _err_message(resp)


def test_save_api_key_rejects_oversize_key():
    client = _client_with_user("u1")
    resp = client.post(
        "/configuration/save-api-key",
        json={"tool_id": "stitch", "api_key": "x" * 1024},
    )
    assert resp.status_code == 400


def test_mcp_status_tavily_firecrawl_always_active(monkeypatch):
    """Tavily and Firecrawl render as configured regardless of env."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    from app.mcp.config import clear_config_cache

    clear_config_cache()

    client = _client_with_user("u1")
    resp = client.get("/configuration/mcp-status")
    assert resp.status_code == 200
    body = resp.json()
    by_id = {t["id"]: t for t in body["built_in_tools"]}
    assert by_id["tavily"]["configured"] is True
    assert "Active" in by_id["tavily"]["status"]
    assert by_id["firecrawl"]["configured"] is True


def test_mcp_status_stitch_uses_user_saved_key(monkeypatch):
    """Stitch shows configured when user has a saved key, even if env is empty."""
    monkeypatch.delenv("STITCH_API_KEY", raising=False)
    from app.mcp.config import clear_config_cache

    clear_config_cache()

    client = _client_with_user("u1")
    with patch(
        "app.services.user_config.get_user_api_key", return_value="user-key"
    ):
        resp = client.get("/configuration/mcp-status")
    assert resp.status_code == 200
    body = resp.json()
    stitch = next(t for t in body["configurable_tools"] if t["id"] == "stitch")
    assert stitch["configured"] is True
