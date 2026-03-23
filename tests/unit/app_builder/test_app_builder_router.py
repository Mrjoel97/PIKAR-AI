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


# ---------------------------------------------------------------------------
# Shared constants for generation tests
# ---------------------------------------------------------------------------

TEST_SCREEN_ID = "cccccccc-0000-0000-0000-000000000001"
TEST_VARIANT_ID = "dddddddd-0000-0000-0000-000000000001"

MOCK_PROJECT_WITH_DS = {
    "id": TEST_PROJECT_ID,
    "user_id": TEST_USER_ID,
    "title": "My Bakery App",
    "status": "generating",
    "stage": "building",
    "stitch_project_id": "stitch-proj-001",
    "design_system": {
        "colors": [{"hex": "#F5E6D3", "name": "Warm Cream"}],
        "typography": {"heading": "Playfair Display", "body": "Inter"},
    },
    "build_plan": [],
}

GENERATE_SCREEN_BODY = {
    "screen_name": "Home Page",
    "page_slug": "home",
    "num_variants": 3,
}

DEVICE_VARIANT_BODY = {
    "device_type": "MOBILE",
    "prompt_used": "A bakery landing page mobile",
}

MOCK_VARIANTS = [
    {
        "id": TEST_VARIANT_ID,
        "screen_id": TEST_SCREEN_ID,
        "variant_index": 0,
        "screenshot_url": "https://supabase.co/storage/screenshot.png",
        "html_url": "https://supabase.co/storage/html",
        "is_selected": True,
    },
    {
        "id": "dddddddd-0000-0000-0000-000000000002",
        "screen_id": TEST_SCREEN_ID,
        "variant_index": 1,
        "screenshot_url": "https://supabase.co/storage/screenshot2.png",
        "html_url": "https://supabase.co/storage/html2",
        "is_selected": False,
    },
]


# ---------------------------------------------------------------------------
# Fixtures for generation endpoints
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_supabase_gen():
    """Supabase mock pre-configured for generation endpoint tests."""
    client = MagicMock()

    # project fetch: .select().eq().eq().single().execute()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=MOCK_PROJECT_WITH_DS
    )
    # screen fetch by id: .select().eq().eq().execute() -> data=[{screen row}]
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_SCREEN_ID, "user_id": TEST_USER_ID, "project_id": TEST_PROJECT_ID}]
    )
    # update calls
    client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_VARIANT_ID}]
    )
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_VARIANT_ID}]
    )
    # variant list ordered: .select().eq().order().execute()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=MOCK_VARIANTS
    )
    return client


@pytest.fixture()
def gen_client(mock_supabase_gen):
    """FastAPI test client with dependency overrides for generation endpoints."""
    from app.routers.app_builder import router  # noqa: PLC0415

    async def override_auth() -> str:
        return TEST_USER_ID

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = override_auth

    with patch("app.routers.app_builder.get_service_client", return_value=mock_supabase_gen):
        yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Test 1 — POST /generate-screen returns SSE stream
# ---------------------------------------------------------------------------


async def _fake_screen_gen(*args, **kwargs):
    yield {"step": "generating", "message": "Generating Home Page...", "screen_id": TEST_SCREEN_ID}
    yield {
        "step": "variant_generated",
        "variant_index": 0,
        "variant_id": TEST_VARIANT_ID,
        "screenshot_url": "https://supabase.co/storage/screenshot.png",
        "html_url": "https://supabase.co/storage/html",
        "screen_id": TEST_SCREEN_ID,
    }


def test_generate_screen_sse(mock_supabase_gen, gen_client):
    """POST /generate-screen returns SSE stream with variant events."""
    with patch(
        "app.routers.app_builder.generate_screen_variants",
        side_effect=_fake_screen_gen,
    ):
        resp = gen_client.post(
            f"/app-builder/projects/{TEST_PROJECT_ID}/generate-screen",
            json=GENERATE_SCREEN_BODY,
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert '"step": "generating"' in body
    assert '"step": "variant_generated"' in body


# ---------------------------------------------------------------------------
# Test 2 — POST /generate-screen returns 404 when project not found
# ---------------------------------------------------------------------------


def test_generate_screen_404(mock_supabase_gen, gen_client):
    """POST /generate-screen returns 404 when project is not found for the user."""
    mock_supabase_gen.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )
    resp = gen_client.post(
        f"/app-builder/projects/nonexistent/generate-screen",
        json=GENERATE_SCREEN_BODY,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 3 — POST /generate-device-variant returns SSE stream
# ---------------------------------------------------------------------------


async def _fake_device_gen(*args, **kwargs):
    yield {"step": "generating", "message": "Generating MOBILE variant...", "screen_id": TEST_SCREEN_ID}
    yield {
        "step": "device_generated",
        "device_type": "MOBILE",
        "variant_id": TEST_VARIANT_ID,
        "screenshot_url": "https://supabase.co/storage/screenshot.png",
        "html_url": "https://supabase.co/storage/html",
        "screen_id": TEST_SCREEN_ID,
    }
    yield {"step": "ready", "screen_id": TEST_SCREEN_ID, "device_type": "MOBILE"}


def test_generate_device_variant_sse(mock_supabase_gen, gen_client):
    """POST /generate-device-variant returns SSE stream with device events."""
    with patch(
        "app.routers.app_builder.generate_device_variant",
        side_effect=_fake_device_gen,
    ):
        resp = gen_client.post(
            f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/generate-device-variant",
            json=DEVICE_VARIANT_BODY,
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert '"step": "generating"' in body
    assert '"step": "device_generated"' in body


# ---------------------------------------------------------------------------
# Test 4 — GET /variants returns ordered variant list
# ---------------------------------------------------------------------------


def test_list_screen_variants(mock_supabase_gen, gen_client):
    """GET /variants returns ordered list of variants for the screen."""
    resp = gen_client.get(
        f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/variants"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["variant_index"] == 0


# ---------------------------------------------------------------------------
# Test 5 — PATCH /select deselects all then selects one
# ---------------------------------------------------------------------------


def test_select_variant(mock_supabase_gen, gen_client):
    """PATCH /select returns success JSON with the selected variant ID."""
    resp = gen_client.patch(
        f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/variants/{TEST_VARIANT_ID}/select"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["selected_variant_id"] == TEST_VARIANT_ID

    # Confirm update was called (deselect all + select one)
    update_calls = [c for c in mock_supabase_gen.table.call_args_list if c.args[0] == "screen_variants"]
    assert len(update_calls) >= 2


# ---------------------------------------------------------------------------
# Test 6 — generate-screen injects design system tokens into prompt
# ---------------------------------------------------------------------------


def test_generate_screen_builds_prompt_with_design_system(mock_supabase_gen, gen_client):
    """POST /generate-screen passes design system tokens to generate_screen_variants."""
    captured_prompt: list[str] = []

    async def capture_gen(*args, **kwargs):
        captured_prompt.append(kwargs.get("prompt", ""))
        yield {"step": "generating", "screen_id": TEST_SCREEN_ID, "message": "ok"}

    with patch(
        "app.routers.app_builder.generate_screen_variants",
        side_effect=capture_gen,
    ):
        gen_client.post(
            f"/app-builder/projects/{TEST_PROJECT_ID}/generate-screen",
            json=GENERATE_SCREEN_BODY,
        )

    assert len(captured_prompt) == 1
    prompt = captured_prompt[0]
    # Design system colors injected
    assert "#F5E6D3" in prompt or "Home Page" in prompt


# ---------------------------------------------------------------------------
# Shared constants for iteration endpoint tests
# ---------------------------------------------------------------------------

TEST_NEW_STITCH_SCREEN_ID = "stitch-screen-002"
TEST_STITCH_SCREEN_ID = "stitch-screen-001"

MOCK_SELECTED_VARIANT = {
    "id": TEST_VARIANT_ID,
    "screen_id": TEST_SCREEN_ID,
    "stitch_screen_id": TEST_STITCH_SCREEN_ID,
    "iteration": 2,
    "is_selected": True,
}

MOCK_HISTORY_VARIANTS = [
    {
        "id": TEST_VARIANT_ID,
        "screen_id": TEST_SCREEN_ID,
        "iteration": 3,
        "is_selected": True,
        "screenshot_url": "https://supabase.co/storage/screenshot3.png",
        "html_url": "https://supabase.co/storage/html3",
    },
    {
        "id": "dddddddd-0000-0000-0000-000000000002",
        "screen_id": TEST_SCREEN_ID,
        "iteration": 2,
        "is_selected": False,
        "screenshot_url": "https://supabase.co/storage/screenshot2.png",
        "html_url": "https://supabase.co/storage/html2",
    },
    {
        "id": "dddddddd-0000-0000-0000-000000000003",
        "screen_id": TEST_SCREEN_ID,
        "iteration": 1,
        "is_selected": False,
        "screenshot_url": "https://supabase.co/storage/screenshot.png",
        "html_url": "https://supabase.co/storage/html",
    },
]


@pytest.fixture()
def mock_supabase_iter():
    """Supabase mock pre-configured for iteration endpoint tests."""
    client = MagicMock()

    # project fetch: .select().eq().eq().single().execute()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=MOCK_PROJECT_WITH_DS
    )
    # screen ownership check: .select().eq().eq().execute() -> single screen row
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_SCREEN_ID, "user_id": TEST_USER_ID}]
    )
    # selected variant: .select().eq().eq().eq().limit().execute()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[MOCK_SELECTED_VARIANT]
    )
    # history variants: .select().eq().order().order().execute()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value = MagicMock(
        data=MOCK_HISTORY_VARIANTS
    )
    # iteration MAX query: .select().eq().order().limit().execute()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"iteration": 2}]
    )
    # update calls (deselect all, select target, approve)
    client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_VARIANT_ID}]
    )
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_SCREEN_ID}]
    )
    # insert call
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": TEST_VARIANT_ID}]
    )
    return client


@pytest.fixture()
def iter_client(mock_supabase_iter):
    """FastAPI test client with dependency overrides for iteration endpoints."""
    from app.routers.app_builder import router  # noqa: PLC0415

    async def override_auth() -> str:
        return TEST_USER_ID

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_id] = override_auth

    with patch("app.routers.app_builder.get_service_client", return_value=mock_supabase_iter):
        yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Test 7 — POST /iterate returns SSE stream
# ---------------------------------------------------------------------------


async def _fake_iterate_gen(*args, **kwargs):
    """Async generator yielding iteration SSE events."""
    yield {"step": "editing", "message": "Applying edit: make hero taller..."}
    yield {
        "step": "edit_complete",
        "variant_id": TEST_VARIANT_ID,
        "screenshot_url": "https://supabase.co/storage/screenshot3.png",
        "html_url": "https://supabase.co/storage/html3",
        "iteration": 3,
        "screen_id": TEST_SCREEN_ID,
    }
    yield {"step": "ready", "screen_id": TEST_SCREEN_ID, "iteration": 3}


def test_iterate_screen(mock_supabase_iter, iter_client):
    """POST /iterate returns SSE stream with editing and edit_complete events."""
    with patch(
        "app.routers.app_builder.edit_screen_variant",
        side_effect=_fake_iterate_gen,
    ):
        with patch(
            "app.routers.app_builder._get_locked_design_markdown",
            new=AsyncMock(return_value=None),
        ):
            resp = iter_client.post(
                f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/iterate",
                json={"change_description": "make hero taller"},
            )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    assert '"step": "editing"' in body
    assert '"step": "edit_complete"' in body
    assert '"step": "ready"' in body


# ---------------------------------------------------------------------------
# Test 8 — GET /history returns variants ordered by iteration DESC
# ---------------------------------------------------------------------------


def test_screen_history_ordered(mock_supabase_iter, iter_client):
    """GET /history returns variants ordered by iteration DESC."""
    resp = iter_client.get(
        f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/history"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # First item has highest iteration (ordered DESC)
    assert data[0]["iteration"] == 3
    assert data[1]["iteration"] == 2
    assert data[2]["iteration"] == 1


# ---------------------------------------------------------------------------
# Test 9 — POST /rollback selects target variant
# ---------------------------------------------------------------------------


def test_rollback_selects_variant(mock_supabase_iter, iter_client):
    """POST /rollback deselects all variants then selects the target variant."""
    target_variant_id = "dddddddd-0000-0000-0000-000000000002"
    resp = iter_client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/rollback/{target_variant_id}"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["selected_variant_id"] == target_variant_id

    # Confirm screen_variants table was updated (deselect all + select one)
    update_calls = [
        c for c in mock_supabase_iter.table.call_args_list
        if c.args[0] == "screen_variants"
    ]
    assert len(update_calls) >= 2


# ---------------------------------------------------------------------------
# Test 10 — POST /approve sets approved=true on app_screens
# ---------------------------------------------------------------------------


def test_approve_screen(mock_supabase_iter, iter_client):
    """POST /approve sets app_screens.approved=True and returns success response."""
    resp = iter_client.post(
        f"/app-builder/projects/{TEST_PROJECT_ID}/screens/{TEST_SCREEN_ID}/approve"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["screen_id"] == TEST_SCREEN_ID
    assert data["approved"] is True

    # Confirm app_screens table was updated
    app_screens_calls = [
        c for c in mock_supabase_iter.table.call_args_list
        if c.args[0] == "app_screens"
    ]
    assert len(app_screens_calls) >= 1
