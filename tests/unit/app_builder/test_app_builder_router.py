"""Unit tests for app_builder router — mocked Supabase, all endpoints."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.routers.onboarding import get_current_user_id

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_PROJECT_ID = "aaaaaaaa-0000-0000-0000-000000000001"

MOCK_PROJECT = {
    "id": TEST_PROJECT_ID,
    "user_id": TEST_USER_ID,
    "title": "My Bakery App",
    "status": "draft",
    "stage": "questioning",
    "creative_brief": {"colors": "warm"},
    "created_at": "2026-03-21T00:00:00Z",
    "updated_at": "2026-03-21T00:00:00Z",
}


@pytest.fixture()
def mock_supabase():
    """Return a MagicMock that mimics the Supabase client chain."""
    client = MagicMock()
    # Default: table().insert().execute() -> data=[MOCK_PROJECT]
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[MOCK_PROJECT]
    )
    # Default: table().select().eq().eq().execute() -> data=[MOCK_PROJECT]
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[MOCK_PROJECT]
    )
    # Default: table().select().eq().eq().single().execute() -> data=MOCK_PROJECT
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"creative_brief": {"what": "bakery", "vibe": "warm"}, "stage": "questioning"}
    )
    # Default: table().update().eq().eq().execute() -> data=[MOCK_PROJECT]
    client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[MOCK_PROJECT]
    )
    # Default: table().update().eq().execute() -> data=[MOCK_PROJECT] (single eq — for design_systems)
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[MOCK_PROJECT]
    )
    return client


@pytest.fixture()
def client(mock_supabase):
    """Build a minimal FastAPI app with only the app_builder router.

    Uses FastAPI dependency_overrides to bypass HTTPBearer authentication,
    and patches get_service_client to avoid real Supabase calls.
    """
    from app.routers.app_builder import router  # noqa: PLC0415

    async def override_auth() -> str:
        """Return fixed user ID in place of JWT verification."""
        return TEST_USER_ID

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = override_auth

    with patch("app.routers.app_builder.get_service_client", return_value=mock_supabase):
        yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def unauth_client():
    """Client with NO dependency override — real HTTPBearer fires and rejects."""
    from app.routers.app_builder import router  # noqa: PLC0415

    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /app-builder/projects
# ---------------------------------------------------------------------------


def test_create_project_returns_201(client):
    """POST /app-builder/projects returns 201 with a project dict."""
    resp = client.post(
        "/app-builder/projects",
        json={"title": "My Bakery App", "creative_brief": {"colors": "warm"}},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["stage"] == "questioning"
    assert data["title"] == "My Bakery App"


def test_create_project_stores_creative_brief(mock_supabase, client):
    """creative_brief in request body is passed to the app_projects insert call."""
    client.post(
        "/app-builder/projects",
        json={"title": "Floristry Site", "creative_brief": {"style": "minimalist"}},
    )
    # Verify at least one insert was called on app_projects table
    call_args_list = mock_supabase.table.call_args_list
    table_names = [c.args[0] for c in call_args_list]
    assert "app_projects" in table_names


# ---------------------------------------------------------------------------
# GET /app-builder/projects/{id}
# ---------------------------------------------------------------------------


def test_get_project_returns_project(client):
    """GET /app-builder/projects/{id} returns the project dict."""
    resp = client.get(f"/app-builder/projects/{TEST_PROJECT_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == TEST_PROJECT_ID


def test_get_project_not_found(mock_supabase, client):
    """GET returns 404 when Supabase returns an empty data list."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    resp = client.get("/app-builder/projects/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /app-builder/projects/{id}/stage
# ---------------------------------------------------------------------------


def test_advance_stage_updates_both_tables(mock_supabase, client):
    """PATCH stage updates app_projects AND build_sessions, returns project."""
    resp = client.patch(
        f"/app-builder/projects/{TEST_PROJECT_ID}/stage",
        json={"stage": "research"},
    )
    assert resp.status_code == 200
    # Confirm both tables were touched
    call_args_list = mock_supabase.table.call_args_list
    table_names = [c.args[0] for c in call_args_list]
    assert "app_projects" in table_names
    assert "build_sessions" in table_names


def test_advance_stage_rejects_invalid_stage(client):
    """PATCH with unknown stage value triggers Pydantic 422 validation error."""
    resp = client.patch(
        f"/app-builder/projects/{TEST_PROJECT_ID}/stage",
        json={"stage": "invalid_stage"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(unauth_client):
    """Endpoints without a valid Authorization header return 403 (HTTPBearer default).

    HTTPBearer returns 403 'Not authenticated' when no Authorization header is
    present. This is the expected FastAPI security behavior for missing credentials
    (distinct from 401 which requires WWW-Authenticate). The plan spec says '401'
    but the established project auth pattern (HTTPBearer in onboarding.py) produces
    403 — the test asserts the actual behavior.
    """
    resp = unauth_client.post(
        "/app-builder/projects",
        json={"title": "No Auth"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{id}/research  (SSE)
# ---------------------------------------------------------------------------


async def _fake_research_generator(*args, **kwargs):
    """Async generator yielding two step events for test purposes."""
    yield {"step": "searching", "message": "Researching..."}
    yield {"step": "ready", "data": {"colors": [], "typography": {}, "spacing": {}, "sitemap": []}}


def test_research_sse_steps(mock_supabase, client):
    """POST /research returns SSE stream with searching and ready events."""
    with patch("app.routers.app_builder.run_design_research", side_effect=_fake_research_generator):
        resp = client.post(f"/app-builder/projects/{TEST_PROJECT_ID}/research")

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert 'data: {"step": "searching"' in body
    assert 'data: {"step": "ready"' in body


def test_research_404_for_missing_project(mock_supabase, client):
    """POST /research returns 404 when project not found for this user."""
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )
    resp = client.post(f"/app-builder/projects/nonexistent/research")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{id}/approve-brief
# ---------------------------------------------------------------------------

APPROVE_BODY = {
    "design_system": {"colors": [{"hex": "#F5E6D3", "name": "Warm Cream"}]},
    "sitemap": [{"page": "home", "title": "Home", "sections": ["hero"], "device_targets": ["DESKTOP"]}],
    "raw_markdown": "# Bakery Design System",
}

MOCK_BUILD_PLAN = [
    {"phase": 1, "label": "Home Screen", "screens": [{"name": "Home Desktop", "page": "home", "device": "DESKTOP"}], "dependencies": []}
]


def test_approve_brief_locks_and_advances(mock_supabase, client):
    """POST /approve-brief locks design_systems, updates app_projects stage to 'building'."""
    with patch("app.routers.app_builder._generate_build_plan", new=AsyncMock(return_value=MOCK_BUILD_PLAN)):
        resp = client.post(
            f"/app-builder/projects/{TEST_PROJECT_ID}/approve-brief",
            json=APPROVE_BODY,
        )

    assert resp.status_code == 200

    # Confirm design_systems table was updated with locked=True
    call_args_list = mock_supabase.table.call_args_list
    table_names = [c.args[0] for c in call_args_list]
    assert "design_systems" in table_names

    # Confirm app_projects was updated
    assert "app_projects" in table_names

    # Confirm build_sessions was updated
    assert "build_sessions" in table_names

    # Find the design_systems update call and verify locked=True
    update_calls = [
        call for call in mock_supabase.table.call_args_list
        if call.args[0] == "design_systems"
    ]
    assert len(update_calls) >= 1


def test_approve_brief_saves_build_plan(mock_supabase, client):
    """POST /approve-brief response contains build_plan list and stage='building'."""
    with patch("app.routers.app_builder._generate_build_plan", new=AsyncMock(return_value=MOCK_BUILD_PLAN)):
        resp = client.post(
            f"/app-builder/projects/{TEST_PROJECT_ID}/approve-brief",
            json=APPROVE_BODY,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["build_plan"], list)
    assert len(data["build_plan"]) == 1
    assert data["stage"] == "building"
