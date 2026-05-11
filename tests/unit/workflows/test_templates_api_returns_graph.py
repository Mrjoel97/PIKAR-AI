"""Tests that GET /workflows/templates and GET /workflows/templates/{id}
include the graph_nodes/graph_edges/graph_layout fields in their response
payload (Phase 109 Spec B Phase 1).

These are router-level unit tests with the WorkflowEngine mocked — no
real DB is hit. Heavier full-stack integration coverage lives in
tests/integration/test_workflow_template_graph_projection.py (Plan 109-01).
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.workflows import get_current_user_id
from app.routers.workflows import router as workflows_router


@pytest.fixture
def app_with_router() -> FastAPI:
    """Mount only the workflows router so we don't have to boot the whole app."""
    app = FastAPI()

    async def _fake_user() -> str:
        return "user-test"

    app.dependency_overrides[get_current_user_id] = _fake_user
    app.include_router(workflows_router)
    return app


@pytest.fixture
def client(app_with_router: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_with_router) as c:
        yield c


# Patch the rate limiter at import-time so the decorator does not gate
# requests in tests. Limiter is a fixture-scoped patch applied automatically.
@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Disable slowapi rate limiting for all tests in this module."""
    from app.middleware.rate_limiter import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


def _make_engine(list_rows: list[dict], one_row: dict | None = None):
    """Return a mock WorkflowEngine with list_templates and get_template."""
    engine = MagicMock()
    engine.list_templates = AsyncMock(return_value=list_rows)
    if one_row is not None:
        engine.get_template = AsyncMock(return_value=one_row)
    return engine


_SAMPLE_GRAPH_NODES = [
    {"id": "trigger", "kind": "trigger", "label": "Start"},
    {
        "id": "step-0",
        "kind": "agent-action",
        "label": "Research market",
        "config": {"tool": "deep_research"},
    },
    {"id": "output", "kind": "output", "label": "End"},
]

_SAMPLE_GRAPH_EDGES = [
    {"id": "e0", "source": "trigger", "target": "step-0"},
    {"id": "e1", "source": "step-0", "target": "output"},
]

_SAMPLE_GRAPH_LAYOUT = {
    "trigger": {"x": 0, "y": 0},
    "step-0": {"x": 200, "y": 0},
    "output": {"x": 400, "y": 0},
}


def _template_row(template_id: str, *, with_graph: bool) -> dict:
    row = {
        "id": template_id,
        "name": "Test Template",
        "description": "test",
        "category": "custom",
        "template_key": None,
        "version": 1,
        "lifecycle_status": "published",
        "is_generated": False,
        "personas_allowed": None,
        "published_at": None,
    }
    if with_graph:
        row["graph_nodes"] = _SAMPLE_GRAPH_NODES
        row["graph_edges"] = _SAMPLE_GRAPH_EDGES
        row["graph_layout"] = _SAMPLE_GRAPH_LAYOUT
    else:
        row["graph_nodes"] = None
        row["graph_edges"] = None
        row["graph_layout"] = None
    return row


# ---------- GET /workflows/templates -----------------------------------------


def test_list_templates_returns_graph_fields(client: TestClient):
    """The list endpoint emits graph_nodes/edges/layout for populated rows."""
    rows = [_template_row("abc", with_graph=True)]
    engine = _make_engine(list_rows=rows)

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.get("/workflows/templates")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    item = body[0]
    assert "graph_nodes" in item
    assert "graph_edges" in item
    assert "graph_layout" in item
    assert item["graph_nodes"] is not None and len(item["graph_nodes"]) == 3
    assert item["graph_nodes"][0]["kind"] == "trigger"
    assert item["graph_nodes"][1]["config"] == {"tool": "deep_research"}
    assert item["graph_edges"][0]["source"] == "trigger"
    assert item["graph_layout"]["step-0"]["x"] == 200


def test_list_templates_returns_null_graph_for_legacy_rows(client: TestClient):
    """Rows whose graph columns are NULL come back with graph_*: None."""
    rows = [_template_row("legacy", with_graph=False)]
    engine = _make_engine(list_rows=rows)

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.get("/workflows/templates")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["graph_nodes"] is None
    assert item["graph_edges"] is None
    assert item["graph_layout"] is None


def test_list_templates_handles_mixed_rows(client: TestClient):
    """A populated row + a legacy row coexist in the same response."""
    rows = [
        _template_row("with-graph", with_graph=True),
        _template_row("legacy", with_graph=False),
    ]
    engine = _make_engine(list_rows=rows)

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.get("/workflows/templates")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    with_graph, legacy = body
    assert with_graph["graph_nodes"] is not None
    assert legacy["graph_nodes"] is None


# ---------- GET /workflows/templates/{template_id} ---------------------------


def test_get_template_returns_graph_fields(client: TestClient):
    """The single-template endpoint passes graph fields through."""
    row = _template_row("abc", with_graph=True)
    engine = _make_engine(list_rows=[], one_row=row)

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.get("/workflows/templates/abc")

    assert response.status_code == 200
    body = response.json()
    # get_template returns the raw dict (no response_model), so all DB columns
    # including graph_nodes/edges/layout are echoed through.
    assert body["graph_nodes"] == _SAMPLE_GRAPH_NODES
    assert body["graph_edges"] == _SAMPLE_GRAPH_EDGES
    assert body["graph_layout"] == _SAMPLE_GRAPH_LAYOUT


def test_get_template_returns_legacy_row_with_null_graph(client: TestClient):
    """A legacy row with NULL graph columns echoes None on each field."""
    row = _template_row("legacy", with_graph=False)
    engine = _make_engine(list_rows=[], one_row=row)

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.get("/workflows/templates/legacy")

    assert response.status_code == 200
    body = response.json()
    assert body["graph_nodes"] is None
    assert body["graph_edges"] is None
    assert body["graph_layout"] is None


# ---------- Backward compatibility -------------------------------------------


def test_list_templates_preserves_existing_fields(client: TestClient):
    """Existing callers continue to see id/name/category/etc unchanged."""
    rows = [_template_row("abc", with_graph=True)]
    engine = _make_engine(list_rows=rows)

    with patch("app.routers.workflows.get_workflow_engine", return_value=engine):
        response = client.get("/workflows/templates")

    item = response.json()[0]
    # Spot-check the legacy field set is intact.
    for key in (
        "id",
        "name",
        "description",
        "category",
        "template_key",
        "version",
        "lifecycle_status",
        "is_generated",
        "personas_allowed",
        "last_published_at",
    ):
        assert key in item, f"legacy field {key!r} dropped from response"
